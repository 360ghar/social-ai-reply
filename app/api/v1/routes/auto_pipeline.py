"""Auto-pipeline run and management endpoints."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_active_project,
    get_current_user,
    get_current_workspace,
)
from app.db.models import (
    AccountUser,
    AutoPipeline,
    DiscoveryKeyword,
    MonitoredSubreddit,
    Opportunity,
    OpportunityStatus,
    Persona,
    Project,
    PromptTemplate,
    ReplyDraft,
    Workspace,
)
from app.db.session import get_db
from app.services.product.pipeline import run_auto_pipeline_background

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["auto-pipeline"])


@router.post("/auto-pipeline/run")
def start_auto_pipeline(
    background_tasks: BackgroundTasks,
    payload: dict = Body(...),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Start the full auto-pipeline from website URL."""
    ensure_workspace_membership(db, workspace.id, current_user.id)

    website_url = payload.get("website_url")
    project_id = payload.get("project_id")

    if not website_url:
        raise HTTPException(400, "website_url is required.")

    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    pipeline = AutoPipeline(
        project_id=proj.id,
        website_url=website_url,
        status="analyzing",
        progress=0,
        current_step="Analyzing website...",
        started_at=datetime.now(timezone.utc),
    )
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)

    background_tasks.add_task(
        run_auto_pipeline_background,
        pipeline.id,
        website_url,
        proj.id,
        workspace.id,
        current_user.id,
    )

    return {
        "id": pipeline.id,
        "project_id": pipeline.project_id,
        "website_url": pipeline.website_url,
        "status": pipeline.status,
        "progress": pipeline.progress,
        "current_step": pipeline.current_step,
        "personas_count": pipeline.personas_generated,
        "keywords_count": pipeline.keywords_generated,
        "subreddits_count": pipeline.subreddits_found,
        "opportunities_count": pipeline.opportunities_found,
        "drafts_count": pipeline.drafts_generated,
        "brand_summary": pipeline.brand_summary,
        "created_at": pipeline.created_at.isoformat() if pipeline.created_at else None,
    }


@router.get("/auto-pipeline/{pipeline_id}")
def get_auto_pipeline(
    pipeline_id: str,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Get pipeline status and results."""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    pipeline = db.query(AutoPipeline).filter(
        AutoPipeline.id == pipeline_id,
        AutoPipeline.project_id.in_(select(Project.id).where(Project.workspace_id == workspace.id))
    ).first()
    if not pipeline:
        raise HTTPException(404, "Pipeline not found.")

    response = {
        "id": pipeline.id,
        "project_id": pipeline.project_id,
        "website_url": pipeline.website_url,
        "status": pipeline.status,
        "progress": pipeline.progress,
        "current_step": pipeline.current_step,
        "brand_summary": pipeline.brand_summary,
        "personas_count": pipeline.personas_generated,
        "keywords_count": pipeline.keywords_generated,
        "subreddits_count": pipeline.subreddits_found,
        "opportunities_count": pipeline.opportunities_found,
        "drafts_count": pipeline.drafts_generated,
        "started_at": pipeline.started_at.isoformat() if pipeline.started_at else None,
        "completed_at": pipeline.completed_at.isoformat() if pipeline.completed_at else None,
        "error_message": pipeline.error_message,
    }

    if pipeline.status == "ready":
        proj = db.query(Project).filter(Project.id == pipeline.project_id).first()
        if proj:
            personas = db.query(Persona).filter(Persona.project_id == proj.id, Persona.source == "generated").all()
            keywords = db.query(DiscoveryKeyword).filter(DiscoveryKeyword.project_id == proj.id, DiscoveryKeyword.source == "generated").all()
            subreddits = db.query(MonitoredSubreddit).filter(MonitoredSubreddit.project_id == proj.id).all()
            opportunities = db.query(Opportunity).filter(
                Opportunity.project_id == proj.id, Opportunity.status == OpportunityStatus.NEW
            ).order_by(Opportunity.score.desc()).limit(20).all()
            drafts = db.query(ReplyDraft).filter(ReplyDraft.project_id == proj.id).options(selectinload(ReplyDraft.opportunity)).all()

            response["results"] = {
                "brand_summary": pipeline.brand_summary or "",
                "personas": [
                    {"name": p.name, "role": p.role or "", "summary": p.summary, "pain_points": p.pain_points or []}
                    for p in personas
                ],
                "keywords": [
                    {"keyword": k.keyword, "score": k.priority_score, "source": k.source}
                    for k in keywords
                ],
                "subreddits": [
                    {"name": s.name, "fit_score": s.fit_score, "subscribers": s.subscribers, "description": s.description or ""}
                    for s in subreddits
                ],
                "opportunities": [
                    {"title": o.title, "subreddit": o.subreddit_name, "score": o.score, "author": o.author}
                    for o in opportunities
                ],
                "drafts": [
                    {"title": (d.opportunity.title if d.opportunity else "") or "Reply Draft",
                     "content": d.content, "opportunity_title": d.opportunity.title if d.opportunity else ""}
                    for d in drafts[:10]
                ],
            }

    return response


@router.get("/auto-pipeline")
def list_auto_pipelines(
    project_id: int | None = Query(default=None, ge=1),
    limit: int = 20,
    offset: int = 0,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """List all pipeline runs."""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    pipelines = db.query(AutoPipeline).filter(
        AutoPipeline.project_id == proj.id
    ).order_by(AutoPipeline.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "items": [
            {
                "id": p.id, "project_id": p.project_id, "website_url": p.website_url,
                "status": p.status, "progress": p.progress,
                "personas_count": p.personas_generated, "keywords_count": p.keywords_generated,
                "subreddits_count": p.subreddits_found, "opportunities_count": p.opportunities_found,
                "drafts_count": p.drafts_generated,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in pipelines
        ]
    }


@router.post("/auto-pipeline/{pipeline_id}/execute")
def execute_auto_pipeline(
    pipeline_id: str,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Execute the sales package (publish all drafts)."""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    pipeline = db.query(AutoPipeline).filter(
        AutoPipeline.id == pipeline_id,
        AutoPipeline.project_id.in_(select(Project.id).where(Project.workspace_id == workspace.id))
    ).first()
    if not pipeline:
        raise HTTPException(404, "Pipeline not found.")

    if pipeline.status != "ready":
        raise HTTPException(400, "Pipeline is not ready for execution. Please complete the setup first.")

    reply_drafts = db.query(ReplyDraft).filter(ReplyDraft.project_id == pipeline.project_id).all()

    pipeline.status = "executed"
    pipeline.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "id": pipeline.id,
        "status": pipeline.status,
        "drafted_replies": len(reply_drafts),
        "message": "Sales package has been executed. Drafts are ready for review and posting."
    }
