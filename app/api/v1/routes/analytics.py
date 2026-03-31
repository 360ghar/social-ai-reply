"""Analytics overview, trends, and export endpoints."""
import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.deps import ensure_workspace_membership, get_active_project, get_current_user, get_current_workspace
from app.db.models import (
    AccountUser,
    AnalyticsSnapshot,
    DiscoveryKeyword,
    MonitoredSubreddit,
    Opportunity,
    PostDraft,
    ReplyDraft,
    ScanRun,
    Workspace,
)
from app.db.session import get_db
from app.services.product.entitlements import count_active_keywords, count_active_subreddits

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["analytics"])


@router.get("/analytics/overview")
def analytics_overview(
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Get dashboard KPIs."""
    from app.db.models import VisibilitySnapshot, PublishedPost

    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    today_snapshot = db.query(AnalyticsSnapshot).filter(
        AnalyticsSnapshot.project_id == proj.id,
        AnalyticsSnapshot.date == date.today()
    ).first()

    visibility_score = 0
    visibility_snapshot = db.query(VisibilitySnapshot).filter(
        VisibilitySnapshot.project_id == proj.id
    ).order_by(VisibilitySnapshot.date.desc()).first()
    if visibility_snapshot:
        visibility_score = visibility_snapshot.share_of_voice or 0

    opportunities_count = db.query(func.count(Opportunity.id)).filter(
        Opportunity.project_id == proj.id
    ).scalar() or 0

    reply_drafts_count = db.query(func.count(ReplyDraft.id)).filter(
        ReplyDraft.project_id == proj.id
    ).scalar() or 0
    post_drafts_count = db.query(func.count(PostDraft.id)).filter(
        PostDraft.project_id == proj.id
    ).scalar() or 0
    total_drafts = reply_drafts_count + post_drafts_count

    published_count = db.query(func.count(PublishedPost.id)).filter(
        PublishedPost.project_id == proj.id,
        PublishedPost.status == "published"
    ).scalar() or 0

    return {
        "visibility_score": visibility_score,
        "total_opportunities": opportunities_count,
        "total_drafts": total_drafts,
        "total_published": published_count,
        "keywords_count": count_active_keywords(db, proj.id),
        "subreddits_count": count_active_subreddits(db, proj.id),
        "today_opportunities": today_snapshot.opportunities_found if today_snapshot else 0,
        "today_posts_published": today_snapshot.posts_published if today_snapshot else 0,
    }


@router.get("/analytics/visibility-trend")
def visibility_trend(
    days: int = 30,
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Get visibility trend over time."""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    start_date = date.today() - timedelta(days=days)
    snapshots = db.query(AnalyticsSnapshot).filter(
        AnalyticsSnapshot.project_id == proj.id,
        AnalyticsSnapshot.date >= start_date
    ).order_by(AnalyticsSnapshot.date).all()

    return {
        "items": [
            {
                "date": s.date.isoformat() if s.date else None,
                "visibility_score": s.visibility_score,
                "total_mentions": s.total_mentions,
                "positive_mentions": s.positive_mentions,
                "negative_mentions": s.negative_mentions,
                "neutral_mentions": s.neutral_mentions,
            }
            for s in snapshots
        ]
    }


@router.get("/analytics/engagement")
def engagement_metrics(
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Get engagement metrics."""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    status_counts = db.query(
        Opportunity.status,
        func.count(Opportunity.id).label("count")
    ).filter(Opportunity.project_id == proj.id).group_by(Opportunity.status).all()

    return {
        "by_status": {s.value: c for s, c in status_counts},
        "total_scans": db.query(func.count(ScanRun.id)).filter(ScanRun.project_id == proj.id).scalar() or 0,
    }


@router.get("/analytics/keywords")
def keyword_performance(
    limit: int = 20,
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Get keyword performance data."""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    keywords = db.query(DiscoveryKeyword).filter(
        DiscoveryKeyword.project_id == proj.id,
        DiscoveryKeyword.is_active.is_(True)
    ).order_by(DiscoveryKeyword.priority_score.desc()).limit(limit).all()

    return {
        "items": [
            {"id": k.id, "keyword": k.keyword, "priority_score": k.priority_score, "rationale": k.rationale}
            for k in keywords
        ]
    }


@router.get("/analytics/subreddits")
def subreddit_performance(
    limit: int = 20,
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Get subreddit performance data."""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    subreddits = db.query(MonitoredSubreddit).filter(
        MonitoredSubreddit.project_id == proj.id,
        MonitoredSubreddit.is_active.is_(True)
    ).order_by(MonitoredSubreddit.fit_score.desc()).limit(limit).all()

    return {
        "items": [
            {"id": s.id, "name": s.name, "subscribers": s.subscribers,
             "activity_score": s.activity_score, "fit_score": s.fit_score}
            for s in subreddits
        ]
    }


@router.post("/analytics/snapshot")
def take_analytics_snapshot(
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Take a daily analytics snapshot."""
    from app.db.models import VisibilitySnapshot, PublishedPost

    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    today = date.today()
    existing = db.query(AnalyticsSnapshot).filter(
        AnalyticsSnapshot.project_id == proj.id,
        AnalyticsSnapshot.date == today
    ).first()
    if existing:
        return {"message": "Snapshot already taken today.", "id": existing.id}

    opportunities_count = db.query(func.count(Opportunity.id)).filter(
        Opportunity.project_id == proj.id
    ).scalar() or 0
    reply_drafts = db.query(func.count(ReplyDraft.id)).filter(
        ReplyDraft.project_id == proj.id
    ).scalar() or 0
    post_drafts = db.query(func.count(PostDraft.id)).filter(
        PostDraft.project_id == proj.id
    ).scalar() or 0
    published = db.query(func.count(PublishedPost.id)).filter(
        PublishedPost.project_id == proj.id, PublishedPost.status == "published"
    ).scalar() or 0

    top_keywords = [
        k.keyword for k in db.query(DiscoveryKeyword).filter(
            DiscoveryKeyword.project_id == proj.id, DiscoveryKeyword.is_active.is_(True)
        ).order_by(DiscoveryKeyword.priority_score.desc()).limit(5).all()
    ]
    top_subreddits = [
        s.name for s in db.query(MonitoredSubreddit).filter(
            MonitoredSubreddit.project_id == proj.id, MonitoredSubreddit.is_active.is_(True)
        ).order_by(MonitoredSubreddit.fit_score.desc()).limit(5).all()
    ]

    visibility_score = 0.0
    visibility_snapshot = db.query(VisibilitySnapshot).filter(
        VisibilitySnapshot.project_id == proj.id
    ).order_by(VisibilitySnapshot.date.desc()).first()
    if visibility_snapshot:
        visibility_score = visibility_snapshot.share_of_voice or 0.0

    snapshot = AnalyticsSnapshot(
        project_id=proj.id, date=today, visibility_score=visibility_score,
        total_mentions=0, positive_mentions=0, negative_mentions=0, neutral_mentions=0,
        citation_count=0, opportunities_found=opportunities_count,
        drafts_created=reply_drafts + post_drafts, posts_published=published,
        top_keywords=top_keywords, top_subreddits=top_subreddits,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return {
        "id": snapshot.id,
        "date": snapshot.date.isoformat() if snapshot.date else None,
        "opportunities_found": snapshot.opportunities_found,
        "drafts_created": snapshot.drafts_created,
        "posts_published": snapshot.posts_published,
    }


@router.get("/analytics/export")
def export_analytics(
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Export analytics data as JSON."""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    snapshots = db.query(AnalyticsSnapshot).filter(
        AnalyticsSnapshot.project_id == proj.id
    ).order_by(AnalyticsSnapshot.date.desc()).all()

    return {
        "project_id": proj.id,
        "project_name": proj.name,
        "snapshots": [
            {
                "date": s.date.isoformat() if s.date else None,
                "visibility_score": s.visibility_score,
                "total_mentions": s.total_mentions,
                "opportunities_found": s.opportunities_found,
                "drafts_created": s.drafts_created,
                "posts_published": s.posts_published,
                "top_keywords": s.top_keywords,
                "top_subreddits": s.top_subreddits,
            }
            for s in snapshots
        ]
    }
