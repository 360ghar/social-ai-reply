"""Auto-pipeline run and management endpoints."""
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from supabase import Client

from app.api.v1.deps import (
    ensure_default_project,
    ensure_workspace_membership,
    get_active_project,
    get_current_user,
    get_current_workspace,
)
from app.db.supabase_client import get_supabase
from app.db.tables.analytics import create_auto_pipeline, get_auto_pipeline_by_id, list_auto_pipelines_for_project
from app.db.tables.content import list_reply_drafts_for_project
from app.db.tables.discovery import (
    list_discovery_keywords_for_project,
    list_monitored_subreddits_for_project,
    list_opportunities_for_project,
    list_personas_for_project,
)
from app.db.tables.projects import get_project_by_id
from app.services.product.pipeline import run_auto_pipeline_background

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["auto-pipeline"])


@router.post("/auto-pipeline/run")
def start_auto_pipeline(
    background_tasks: BackgroundTasks,
    payload: dict = Body(...),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Start the full auto-pipeline from website URL."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    website_url = payload.get("website_url")
    project_id = payload.get("project_id")

    if not website_url:
        raise HTTPException(400, "website_url is required.")

    proj = get_active_project(supabase, workspace["id"], project_id) or ensure_default_project(supabase, workspace)

    pipeline = create_auto_pipeline(
        supabase,
        {
            "project_id": proj["id"],
            "website_url": website_url,
            "status": "analyzing",
            "progress": 0,
            "current_step": "Analyzing website...",
            "started_at": datetime.now(UTC).isoformat(),
        },
    )

    background_tasks.add_task(
        run_auto_pipeline_background,
        pipeline["id"],
        website_url,
        proj["id"],
        workspace["id"],
        current_user["id"],
    )

    return {
        "id": pipeline["id"],
        "project_id": pipeline["project_id"],
        "website_url": pipeline["website_url"],
        "status": pipeline["status"],
        "progress": pipeline["progress"],
        "current_step": pipeline["current_step"],
        "personas_count": pipeline["personas_generated"],
        "keywords_count": pipeline["keywords_generated"],
        "subreddits_count": pipeline["subreddits_found"],
        "opportunities_count": pipeline["opportunities_found"],
        "drafts_count": pipeline["drafts_generated"],
        "brand_summary": pipeline["brand_summary"],
        "created_at": pipeline.get("created_at"),
    }


@router.get("/auto-pipeline/{pipeline_id}")
def get_auto_pipeline(
    pipeline_id: str,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Get pipeline status and results."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    # Get all project IDs for this workspace
    from app.db.tables.projects import list_projects_for_workspace
    projects = list_projects_for_workspace(supabase, workspace["id"])
    project_ids = [p["id"] for p in projects]

    # Fetch pipeline once and verify it belongs to workspace
    pipeline = get_auto_pipeline_by_id(supabase, pipeline_id)
    if not pipeline or pipeline["project_id"] not in project_ids:
        raise HTTPException(404, "Pipeline not found.")

    response = {
        "id": pipeline["id"],
        "project_id": pipeline["project_id"],
        "website_url": pipeline["website_url"],
        "status": pipeline["status"],
        "progress": pipeline["progress"],
        "current_step": pipeline["current_step"],
        "brand_summary": pipeline["brand_summary"],
        "personas_count": pipeline["personas_generated"],
        "keywords_count": pipeline["keywords_generated"],
        "subreddits_count": pipeline["subreddits_found"],
        "opportunities_count": pipeline["opportunities_found"],
        "drafts_count": pipeline["drafts_generated"],
        "started_at": pipeline.get("started_at"),
        "completed_at": pipeline.get("completed_at"),
        "error_message": pipeline.get("error_message"),
    }

    if pipeline["status"] == "ready":
        proj = get_project_by_id(supabase, pipeline["project_id"])
        if proj:
            # N+1 FIX: Batch load all related data instead of querying per-entity
            personas = list_personas_for_project(supabase, proj["id"], source="generated")
            keywords = list_discovery_keywords_for_project(supabase, proj["id"], source="generated")
            subreddits = list_monitored_subreddits_for_project(supabase, proj["id"])
            opportunities = list_opportunities_for_project(supabase, proj["id"], status="new", limit=20)
            drafts = list_reply_drafts_for_project(supabase, proj["id"])

            response["results"] = {
                "brand_summary": pipeline["brand_summary"] or "",
                "personas": [
                    {"name": p["name"], "role": p.get("role", ""), "summary": p["summary"], "pain_points": p.get("pain_points", [])}
                    for p in personas
                ],
                "keywords": [
                    {"keyword": k["keyword"], "score": k.get("priority_score", 0), "source": k.get("source", "")}
                    for k in keywords
                ],
                "subreddits": [
                    {"name": s["name"], "fit_score": s.get("fit_score", 0), "subscribers": s.get("subscribers", 0), "description": s.get("description", "")}
                    for s in subreddits
                ],
                "opportunities": [
                    {"title": o["title"], "subreddit": o["subreddit_name"], "score": o.get("score", 0), "author": o.get("author", "")}
                    for o in opportunities
                ],
                "drafts": [
                    {"title": d.get("opportunity_title", "Reply Draft") or "Reply Draft", "content": d["content"]}
                    for d in drafts[:10]
                ],
            }

    return response


@router.get("/auto-pipeline")
def list_auto_pipelines(
    project_id: int | None = Query(default=None, ge=1),
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """List all pipeline runs."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id) or ensure_default_project(supabase, workspace)

    pipelines = list_auto_pipelines_for_project(supabase, proj["id"], limit=limit, offset=offset)

    return {
        "items": [
            {
                "id": p["id"],
                "project_id": p["project_id"],
                "website_url": p["website_url"],
                "status": p["status"],
                "progress": p["progress"],
                "personas_count": p["personas_generated"],
                "keywords_count": p["keywords_generated"],
                "subreddits_count": p["subreddits_found"],
                "opportunities_count": p["opportunities_found"],
                "drafts_count": p["drafts_generated"],
                "created_at": p.get("created_at"),
            }
            for p in pipelines
        ]
    }


@router.post("/auto-pipeline/{pipeline_id}/execute")
def execute_auto_pipeline(
    pipeline_id: str,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Execute the sales package (publish all drafts)."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    # Get all project IDs for this workspace
    from app.db.tables.projects import list_projects_for_workspace
    projects = list_projects_for_workspace(supabase, workspace["id"])
    project_ids = [p["id"] for p in projects]

    # Fetch pipeline once and verify it belongs to workspace
    pipeline = get_auto_pipeline_by_id(supabase, pipeline_id)
    if not pipeline or pipeline["project_id"] not in project_ids:
        raise HTTPException(404, "Pipeline not found.")

    if pipeline["status"] != "ready":
        raise HTTPException(400, "Pipeline is not ready for execution. Please complete the setup first.")

    reply_drafts = list_reply_drafts_for_project(supabase, pipeline["project_id"])

    # Update pipeline status
    from app.db.tables.analytics import update_auto_pipeline
    update_auto_pipeline(
        supabase,
        pipeline["id"],
        {
            "status": "executed",
            "updated_at": datetime.now(UTC).isoformat(),
        },
    )

    return {
        "id": pipeline["id"],
        "status": "executed",
        "drafted_replies": len(reply_drafts),
        "message": "Sales package has been executed. Drafts are ready for review and posting.",
    }
