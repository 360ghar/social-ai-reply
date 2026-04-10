"""Analytics overview, trends, and export endpoints."""
import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.api.v1.deps import ensure_workspace_membership, get_active_project, get_current_user, get_current_workspace
from app.db.supabase_client import get_supabase
from app.db.tables.analytics import (
    create_analytics_snapshot,
    get_analytics_snapshot_by_project_and_date,
    list_analytics_snapshots_for_project,
    list_visibility_snapshots_for_project,
)
from app.db.tables.campaigns import list_published_posts_for_project
from app.db.tables.content import list_post_drafts_for_project, list_reply_drafts_for_project
from app.db.tables.discovery import (
    count_opportunities_for_project,
    list_discovery_keywords_for_project,
    list_monitored_subreddits_for_project,
    list_opportunities_for_project,
    list_scan_runs_for_project,
)
from app.services.product.entitlements import count_active_keywords, count_active_subreddits

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["analytics"])


@router.get("/analytics/overview")
def analytics_overview(
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Get dashboard KPIs."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    today_snapshot = get_analytics_snapshot_by_project_and_date(supabase, proj["id"], date.today().isoformat())

    visibility_score = 0
    visibility_snapshots = list_visibility_snapshots_for_project(supabase, proj["id"], limit=1)
    if visibility_snapshots:
        visibility_score = visibility_snapshots[0].get("share_of_voice", 0)

    opportunities_count = count_opportunities_for_project(supabase, proj["id"])

    reply_drafts_count = len(list_reply_drafts_for_project(supabase, proj["id"]))
    post_drafts_count = len(list_post_drafts_for_project(supabase, proj["id"]))
    total_drafts = reply_drafts_count + post_drafts_count

    published_posts = list_published_posts_for_project(supabase, proj["id"], status="published")
    published_count = len(published_posts)

    return {
        "visibility_score": visibility_score,
        "total_opportunities": opportunities_count,
        "total_drafts": total_drafts,
        "total_published": published_count,
        "keywords_count": count_active_keywords(supabase, proj["id"]),
        "subreddits_count": count_active_subreddits(supabase, proj["id"]),
        "today_opportunities": today_snapshot.get("opportunities_found", 0) if today_snapshot else 0,
        "today_posts_published": today_snapshot.get("posts_published", 0) if today_snapshot else 0,
    }


@router.get("/analytics/visibility-trend")
def visibility_trend(
    days: int = 30,
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Get visibility trend over time."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    start_date = date.today() - timedelta(days=days)
    snapshots = list_analytics_snapshots_for_project(supabase, proj["id"], limit=days)
    # Filter by start_date in memory
    snapshots = [s for s in snapshots if s.get("date") and s["date"] >= start_date.isoformat()]

    return {
        "items": [
            {
                "date": s.get("date"),
                "visibility_score": s.get("visibility_score", 0),
                "total_mentions": s.get("total_mentions", 0),
                "positive_mentions": s.get("positive_mentions", 0),
                "negative_mentions": s.get("negative_mentions", 0),
                "neutral_mentions": s.get("neutral_mentions", 0),
            }
            for s in snapshots
        ]
    }


@router.get("/analytics/engagement")
def engagement_metrics(
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Get engagement metrics."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    # Get all opportunities and group by status
    opportunities = list_opportunities_for_project(supabase, proj["id"], limit=1000)
    status_counts = {}
    for opp in opportunities:
        status = opp.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    scan_runs = list_scan_runs_for_project(supabase, proj["id"])

    return {
        "by_status": status_counts,
        "total_scans": len(scan_runs),
    }


@router.get("/analytics/keywords")
def keyword_performance(
    limit: int = 20,
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Get keyword performance data."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    keywords = list_discovery_keywords_for_project(supabase, proj["id"], limit=limit)
    # Filter for active keywords in memory
    keywords = [k for k in keywords if k.get("is_active", True)]
    # Sort by priority_score descending
    keywords.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

    return {
        "items": [
            {"id": k["id"], "keyword": k["keyword"], "priority_score": k.get("priority_score", 0), "rationale": k.get("rationale", "")}
            for k in keywords
        ]
    }


@router.get("/analytics/subreddits")
def subreddit_performance(
    limit: int = 20,
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Get subreddit performance data."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    subreddits = list_monitored_subreddits_for_project(supabase, proj["id"], limit=limit)
    # Filter for active subreddits in memory
    subreddits = [s for s in subreddits if s.get("is_active", True)]
    # Sort by fit_score descending
    subreddits.sort(key=lambda x: x.get("fit_score", 0), reverse=True)

    return {
        "items": [
            {"id": s["id"], "name": s["name"], "subscribers": s.get("subscribers", 0), "activity_score": s.get("activity_score", 0), "fit_score": s.get("fit_score", 0)}
            for s in subreddits
        ]
    }


@router.post("/analytics/snapshot")
def take_analytics_snapshot(
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Take a daily analytics snapshot."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    today = date.today().isoformat()
    existing = get_analytics_snapshot_by_project_and_date(supabase, proj["id"], today)
    if existing:
        return {"message": "Snapshot already taken today.", "id": existing["id"]}

    opportunities_count = count_opportunities_for_project(supabase, proj["id"])
    reply_drafts = list_reply_drafts_for_project(supabase, proj["id"])
    post_drafts = list_post_drafts_for_project(supabase, proj["id"])
    published = list_published_posts_for_project(supabase, proj["id"], status="published")

    top_keywords = list_discovery_keywords_for_project(supabase, proj["id"], limit=5)
    top_subreddits = list_monitored_subreddits_for_project(supabase, proj["id"], limit=5)

    visibility_score = 0.0
    visibility_snapshots = list_visibility_snapshots_for_project(supabase, proj["id"], limit=1)
    if visibility_snapshots:
        visibility_score = visibility_snapshots[0].get("share_of_voice", 0.0)

    snapshot = create_analytics_snapshot(
        supabase,
        {
            "project_id": proj["id"],
            "date": today,
            "visibility_score": visibility_score,
            "total_mentions": 0,
            "positive_mentions": 0,
            "negative_mentions": 0,
            "neutral_mentions": 0,
            "citation_count": 0,
            "opportunities_found": opportunities_count,
            "drafts_created": len(reply_drafts) + len(post_drafts),
            "posts_published": len(published),
            "top_keywords": [k["keyword"] for k in top_keywords],
            "top_subreddits": [s["name"] for s in top_subreddits],
        },
    )

    return {
        "id": snapshot["id"],
        "date": snapshot["date"],
        "opportunities_found": snapshot["opportunities_found"],
        "drafts_created": snapshot["drafts_created"],
        "posts_published": snapshot["posts_published"],
    }


@router.get("/analytics/export")
def export_analytics(
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Export analytics data as JSON."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    snapshots = list_analytics_snapshots_for_project(supabase, proj["id"], limit=100)

    return {
        "project_id": proj["id"],
        "project_name": proj["name"],
        "snapshots": [
            {
                "date": s.get("date"),
                "visibility_score": s.get("visibility_score", 0),
                "total_mentions": s.get("total_mentions", 0),
                "opportunities_found": s.get("opportunities_found", 0),
                "drafts_created": s.get("drafts_created", 0),
                "posts_published": s.get("posts_published", 0),
                "top_keywords": s.get("top_keywords", []),
                "top_subreddits": s.get("top_subreddits", []),
            }
            for s in snapshots
        ]
    }
