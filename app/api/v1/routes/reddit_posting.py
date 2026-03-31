"""Reddit OAuth, posting, and published post endpoints."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_active_project,
    get_current_user,
    get_current_workspace,
)
from app.db.models import (
    AccountUser,
    Project,
    Workspace,
)
from app.db.session import get_db
from app.services.product.reddit import RedditClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["reddit-posting"])


@router.post("/reddit/connect")
def initiate_reddit_oauth(
    payload: dict,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Initiate Reddit OAuth connection."""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    reddit_auth_url = "https://www.reddit.com/api/v1/authorize?client_id=YOUR_CLIENT_ID&response_type=code&state=random_state&redirect_uri=YOUR_CALLBACK_URL&duration=permanent&scope=submit,edit,delete,read"
    return {"auth_url": reddit_auth_url, "message": "Redirect user to this URL to authorize Reddit access."}


@router.post("/reddit/callback")
def handle_reddit_callback(
    payload: dict,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Handle Reddit OAuth callback."""
    from app.db.models import RedditAccount
    from app.services.product.encryption import encrypt_text

    ensure_workspace_membership(db, workspace.id, current_user.id)
    code = payload.get("code")
    if not code:
        raise HTTPException(400, "Authorization code is required.")

    try:
        reddit = RedditAccount(
            workspace_id=workspace.id,
            username=payload.get("username", "connected_account"),
            access_token=encrypt_text(code),
            is_active=True,
        )
        db.add(reddit)
        db.commit()
        db.refresh(reddit)
        return {
            "id": reddit.id, "username": reddit.username, "is_active": reddit.is_active,
            "connected_at": reddit.connected_at.isoformat() if reddit.connected_at else None,
            "message": "Reddit account connected successfully.",
        }
    except Exception as e:
        logger.exception("Failed to connect Reddit account")
        raise HTTPException(500, "Failed to connect Reddit account. Please try again.")


@router.get("/reddit/accounts")
def list_reddit_accounts(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """List connected Reddit accounts."""
    from app.db.models import RedditAccount

    ensure_workspace_membership(db, workspace.id, current_user.id)
    accounts = db.query(RedditAccount).filter(
        RedditAccount.workspace_id == workspace.id
    ).order_by(RedditAccount.connected_at.desc()).all()
    return {
        "items": [
            {"id": acc.id, "username": acc.username, "karma": acc.karma,
             "is_active": acc.is_active,
             "connected_at": acc.connected_at.isoformat() if acc.connected_at else None}
            for acc in accounts
        ]
    }


@router.post("/reddit/post")
def post_to_reddit(
    payload: dict,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Post a comment or thread to Reddit."""
    from app.db.models import PublishedPost, RedditAccount

    ensure_workspace_membership(db, workspace.id, current_user.id)
    reddit_account_id = payload.get("reddit_account_id")
    project_id = payload.get("project_id")
    post_type = payload.get("type", "comment")
    subreddit = payload.get("subreddit")
    content = payload.get("content")
    title = payload.get("title")
    parent_post_id = payload.get("parent_post_id")
    campaign_id = payload.get("campaign_id")

    if not all([reddit_account_id, project_id, subreddit, content]):
        raise HTTPException(400, "Missing required fields: reddit_account_id, project_id, subreddit, content")
    if post_type == "post" and not title:
        raise HTTPException(400, "Title is required for posts.")

    account = db.query(RedditAccount).filter(
        RedditAccount.id == reddit_account_id, RedditAccount.workspace_id == workspace.id
    ).first()
    if not account:
        raise HTTPException(404, "Reddit account not found.")

    proj = db.query(Project).filter(Project.id == project_id, Project.workspace_id == workspace.id).first()
    if not proj:
        raise HTTPException(404, "Project not found.")

    try:
        reddit = RedditClient()
        if post_type == "comment":
            reddit_id = reddit.post_comment(subreddit, parent_post_id, content)
            permalink = f"https://reddit.com/r/{subreddit}/comments/{parent_post_id}/"
        else:
            reddit_id = reddit.post_thread(subreddit, title, content)
            permalink = f"https://reddit.com/r/{subreddit}/comments/{reddit_id}/"

        published = PublishedPost(
            project_id=proj.id, campaign_id=campaign_id, reddit_account_id=account.id,
            type=post_type, reddit_id=reddit_id, subreddit=subreddit,
            title=title, content=content, permalink=permalink,
            parent_post_id=parent_post_id if post_type == "comment" else None,
            status="published",
        )
        db.add(published)
        db.commit()
        db.refresh(published)

        from app.db.models import Notification as NotificationModel
        notification = NotificationModel(
            workspace_id=workspace.id, user_id=current_user.id,
            title=f"Posted to r/{subreddit}",
            body=f"Your {post_type} has been successfully published.",
            type="opportunity", action_url=permalink,
        )
        db.add(notification)
        db.commit()

        return {
            "id": published.id, "type": published.type, "subreddit": published.subreddit,
            "permalink": published.permalink, "status": published.status,
            "published_at": published.published_at.isoformat() if published.published_at else None,
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to post to Reddit: {str(e)}")


@router.get("/reddit/published")
def list_published_posts(
    project_id: int | None = Query(default=None, ge=1),
    limit: int = 20,
    offset: int = 0,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """List published posts with status."""
    from app.db.models import PublishedPost

    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    published_posts = db.query(PublishedPost).filter(
        PublishedPost.project_id == proj.id
    ).order_by(PublishedPost.published_at.desc()).offset(offset).limit(limit).all()
    return {
        "items": [
            {"id": p.id, "type": p.type, "subreddit": p.subreddit, "title": p.title,
             "content": p.content[:100] + "..." if len(p.content) > 100 else p.content,
             "status": p.status, "upvotes": p.upvotes, "permalink": p.permalink,
             "published_at": p.published_at.isoformat() if p.published_at else None}
            for p in published_posts
        ]
    }


@router.post("/reddit/published/{post_id}/check")
def check_published_status(
    post_id: str,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Check current status of a published post."""
    from app.db.models import PublishedPost

    ensure_workspace_membership(db, workspace.id, current_user.id)
    published = db.query(PublishedPost).filter(
        PublishedPost.id == post_id,
        PublishedPost.project_id.in_(select(Project.id).where(Project.workspace_id == workspace.id))
    ).first()
    if not published:
        raise HTTPException(404, "Published post not found.")

    try:
        reddit = RedditClient()
        post_stats = reddit.get_post_stats(published.reddit_id)
        if post_stats:
            published.upvotes = post_stats.get("upvotes", 0)
            published.last_checked_at = datetime.now(timezone.utc)
            if post_stats.get("removed"):
                published.status = "removed"
                published.removal_reason = post_stats.get("removal_reason")
            db.commit()

        return {
            "id": published.id, "status": published.status, "upvotes": published.upvotes,
            "last_checked_at": published.last_checked_at.isoformat() if published.last_checked_at else None,
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to check post status: {str(e)}")
