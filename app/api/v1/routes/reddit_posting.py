"""Reddit OAuth, posting, and published post endpoints."""
import logging
import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_active_project,
    get_current_user,
    get_current_workspace,
)
from app.db.supabase_client import get_supabase
from app.db.tables.campaigns import (
    create_published_post,
    get_published_post_by_id,
    list_published_posts_for_project,
    update_published_post,
)
from app.db.tables.projects import get_project_by_id
from app.services.product.reddit import RedditClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["reddit-posting"])

# In-memory store for pending OAuth state tokens: state → workspace_id
_pending_oauth_states: dict[str, int] = {}


@router.post("/reddit/connect")
def initiate_reddit_oauth(
    payload: dict,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Initiate Reddit OAuth connection."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    state = secrets.token_urlsafe(32)
    _pending_oauth_states[state] = workspace["id"]
    reddit_auth_url = f"https://www.reddit.com/api/v1/authorize?client_id=YOUR_CLIENT_ID&response_type=code&state={state}&redirect_uri=YOUR_CALLBACK_URL&duration=permanent&scope=submit,edit,delete,read"
    return {"auth_url": reddit_auth_url, "state": state, "message": "Redirect user to this URL to authorize Reddit access."}


@router.post("/reddit/callback")
def handle_reddit_callback(
    payload: dict,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Handle Reddit OAuth callback."""
    from app.db.tables.integrations import create_reddit_account
    from app.utils.encryption import encrypt_text

    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    code = payload.get("code")
    if not code:
        raise HTTPException(400, "Authorization code is required.")

    state = payload.get("state")
    expected_wid = _pending_oauth_states.pop(state, None)
    if expected_wid is None:
        raise HTTPException(400, "Invalid or expired state parameter.")
    if expected_wid != workspace["id"]:
        raise HTTPException(403, "State mismatch.")

    try:
        reddit = create_reddit_account(
            supabase,
            {
                "workspace_id": workspace["id"],
                "username": payload.get("username", "connected_account"),
                "access_token": encrypt_text(code),
                "is_active": True,
            },
        )
        return {
            "id": reddit["id"],
            "username": reddit["username"],
            "is_active": reddit["is_active"],
            "connected_at": reddit.get("connected_at"),
            "message": "Reddit account connected successfully.",
        }
    except Exception as exc:
        logger.exception("Failed to connect Reddit account")
        raise HTTPException(500, "Failed to connect Reddit account. Please try again.") from exc


@router.get("/reddit/accounts")
def list_reddit_accounts(
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """List connected Reddit accounts."""
    from app.db.tables.integrations import list_reddit_accounts_for_workspace

    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    accounts = list_reddit_accounts_for_workspace(supabase, workspace["id"])
    return {
        "items": [
            {"id": acc["id"], "username": acc["username"], "karma": acc.get("karma", 0), "is_active": acc.get("is_active", True), "connected_at": acc.get("connected_at")}
            for acc in accounts
        ]
    }


@router.delete("/reddit/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reddit_account(
    account_id: str,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Delete a connected Reddit account."""
    from app.db.tables.integrations import delete_reddit_account as _delete
    from app.db.tables.integrations import get_reddit_account_by_id

    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    account = get_reddit_account_by_id(supabase, account_id)
    if not account or account["workspace_id"] != workspace["id"]:
        raise HTTPException(404, "Reddit account not found.")
    _delete(supabase, account_id)


@router.post("/reddit/post")
def post_to_reddit(
    payload: dict,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Post a comment or thread to Reddit."""
    from app.db.tables.integrations import get_reddit_account_by_id
    from app.db.tables.system import create_notification

    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
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

    account = get_reddit_account_by_id(supabase, reddit_account_id)
    if not account:
        raise HTTPException(404, "Reddit account not found.")
    if account["workspace_id"] != workspace["id"]:
        raise HTTPException(404, "Reddit account not found.")

    proj = get_project_by_id(supabase, project_id)
    if not proj or proj["workspace_id"] != workspace["id"]:
        raise HTTPException(404, "Project not found.")

    try:
        reddit = RedditClient()
        if post_type == "comment":
            reddit_id = reddit.post_comment(subreddit, parent_post_id, content)
            permalink = f"https://reddit.com/r/{subreddit}/comments/{parent_post_id}/"
        else:
            reddit_id = reddit.post_thread(subreddit, title, content)
            permalink = f"https://reddit.com/r/{subreddit}/comments/{reddit_id}/"

        published = create_published_post(
            supabase,
            {
                "project_id": proj["id"],
                "campaign_id": campaign_id,
                "reddit_account_id": account["id"],
                "type": post_type,
                "reddit_id": reddit_id,
                "subreddit": subreddit,
                "title": title,
                "content": content,
                "permalink": permalink,
                "parent_post_id": parent_post_id if post_type == "comment" else None,
                "status": "published",
            },
        )

        create_notification(
            supabase,
            {
                "workspace_id": workspace["id"],
                "user_id": current_user["id"],
                "title": f"Posted to r/{subreddit}",
                "body": f"Your {post_type} has been successfully published.",
                "type": "opportunity",
                "action_url": permalink,
            },
        )

        return {
            "id": published["id"],
            "type": published["type"],
            "subreddit": published["subreddit"],
            "permalink": published["permalink"],
            "status": published["status"],
            "published_at": published.get("published_at"),
        }
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="Reddit posting is not yet available. Copy the draft and post manually — auto-posting is coming soon.") from None
    except Exception as e:
        raise HTTPException(500, f"Failed to post to Reddit: {str(e)}") from e


@router.get("/reddit/published")
def list_published_posts(
    project_id: int | None = Query(default=None, ge=1),
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """List published posts with status."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    published_posts = list_published_posts_for_project(supabase, proj["id"])
    # Apply pagination
    published_posts = published_posts[offset : offset + limit]

    return {
        "items": [
            {
                "id": p["id"],
                "type": p["type"],
                "subreddit": p["subreddit"],
                "title": p.get("title", ""),
                "content": p.get("content", "")[:100] + "..." if len(p.get("content", "")) > 100 else p.get("content", ""),
                "status": p.get("status", "published"),
                "upvotes": p.get("upvotes", 0),
                "permalink": p["permalink"],
                "published_at": p.get("published_at"),
            }
            for p in published_posts
        ]
    }


@router.post("/reddit/published/{post_id}/check")
def check_published_status(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Check current status of a published post."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    published = get_published_post_by_id(supabase, post_id)
    if not published:
        raise HTTPException(404, "Published post not found.")

    # Verify workspace access via project
    proj = get_project_by_id(supabase, published["project_id"])
    if not proj or proj["workspace_id"] != workspace["id"]:
        raise HTTPException(404, "Published post not found.")

    try:
        reddit = RedditClient()
        post_stats = reddit.get_post_stats(published["reddit_id"])
        if post_stats:
            update_published_post(
                supabase,
                post_id,
                {
                    "upvotes": post_stats.get("upvotes", 0),
                    "last_checked_at": datetime.now(UTC).isoformat(),
                },
            )
            if post_stats.get("removed"):
                update_published_post(
                    supabase,
                    post_id,
                    {
                        "status": "removed",
                        "removal_reason": post_stats.get("removal_reason"),
                    },
                )

        return {
            "id": published["id"],
            "status": published.get("status", "published"),
            "upvotes": published.get("upvotes", 0),
            "last_checked_at": published.get("last_checked_at"),
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to check post status: {str(e)}") from e
