"""Reply and post draft endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.deps import (
    ensure_default_prompts,
    ensure_workspace_membership,
    get_active_project,
    get_current_user,
    get_current_workspace,
    get_project,
)
from app.db.models import (
    AccountUser,
    Opportunity,
    OpportunityStatus,
    PostDraft,
    Project,
    PromptTemplate,
    ReplyDraft,
    Workspace,
)
from app.db.session import get_db
from app.schemas.v1.product import (
    PostDraftRequest,
    PostDraftResponse,
    PostDraftUpdateRequest,
    ReplyDraftRequest,
    ReplyDraftResponse,
    ReplyDraftUpdateRequest,
)
from app.services.product.copilot import ProductCopilot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["drafts"])


@router.post("/drafts/replies", response_model=ReplyDraftResponse, status_code=status.HTTP_201_CREATED)
def generate_reply_draft(
    payload: ReplyDraftRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> ReplyDraftResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    opportunity = db.scalar(
        select(Opportunity)
        .join(Project)
        .where(Opportunity.id == payload.opportunity_id, Project.workspace_id == workspace.id)
        .options(selectinload(Opportunity.reply_drafts))
    )
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    project = get_project(db, workspace.id, opportunity.project_id)
    ensure_default_prompts(db, project.id)
    prompts = db.scalars(select(PromptTemplate).where(PromptTemplate.project_id == project.id)).all()
    content, rationale, source_prompt = ProductCopilot().generate_reply(opportunity, project.brand_profile, list(prompts))
    next_version = (db.scalar(select(func.max(ReplyDraft.version)).where(ReplyDraft.opportunity_id == opportunity.id)) or 0) + 1
    draft = ReplyDraft(
        project_id=project.id,
        opportunity_id=opportunity.id,
        content=content,
        rationale=rationale,
        source_prompt=source_prompt,
        version=next_version,
    )
    opportunity.status = OpportunityStatus.DRAFTING
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return ReplyDraftResponse.model_validate(draft)


@router.get("/drafts/replies")
def list_reply_drafts(
    status_filter: str = Query(default="drafting", alias="status"),
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """List reply drafts with enriched opportunity data for Content Studio."""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        return []
    try:
        opp_status = OpportunityStatus(status_filter)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid status: {status_filter}")
    latest_draft_sq = (
        select(ReplyDraft.opportunity_id, func.max(ReplyDraft.id).label("max_id"))
        .group_by(ReplyDraft.opportunity_id)
        .subquery()
    )
    rows = db.execute(
        select(ReplyDraft, Opportunity)
        .join(latest_draft_sq, and_(
            ReplyDraft.opportunity_id == latest_draft_sq.c.opportunity_id,
            ReplyDraft.id == latest_draft_sq.c.max_id,
        ))
        .join(Opportunity, Opportunity.id == ReplyDraft.opportunity_id)
        .where(Opportunity.project_id == proj.id, Opportunity.status == opp_status)
        .order_by(ReplyDraft.created_at.desc())
    ).all()
    results = []
    for draft, opp in rows:
        results.append({
            "id": draft.id,
            "opportunity_id": opp.id,
            "content": draft.content,
            "rationale": draft.rationale or "",
            "version": draft.version,
            "created_at": draft.created_at.isoformat() if draft.created_at else None,
            "opportunity_title": opp.title,
            "opportunity_subreddit": opp.subreddit_name,
            "permalink": opp.permalink,
            "body_excerpt": opp.body_excerpt,
        })
    return results


@router.put("/drafts/replies/{draft_id}", response_model=ReplyDraftResponse)
def update_reply_draft(
    draft_id: int,
    payload: ReplyDraftUpdateRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> ReplyDraftResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    draft = db.scalar(
        select(ReplyDraft).join(Project).where(ReplyDraft.id == draft_id, Project.workspace_id == workspace.id)
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Reply draft not found.")
    draft.content = payload.content
    draft.rationale = payload.rationale
    db.commit()
    db.refresh(draft)
    return ReplyDraftResponse.model_validate(draft)


@router.post("/drafts/posts", response_model=PostDraftResponse, status_code=status.HTTP_201_CREATED)
def generate_post_draft(
    payload: PostDraftRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> PostDraftResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    project = get_project(db, workspace.id, payload.project_id)
    ensure_default_prompts(db, project.id)
    prompts = db.scalars(select(PromptTemplate).where(PromptTemplate.project_id == project.id)).all()
    title, body, rationale = ProductCopilot().generate_post(project.brand_profile, list(prompts))
    version = (db.scalar(select(func.max(PostDraft.version)).where(PostDraft.project_id == project.id)) or 0) + 1
    draft = PostDraft(
        project_id=project.id,
        title=title,
        body=body,
        rationale=rationale,
        source_prompt="\n".join(prompt.instructions for prompt in prompts if prompt.prompt_type == "post"),
        version=version,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return PostDraftResponse.model_validate(draft)


@router.get("/drafts/posts", response_model=list[PostDraftResponse])
def list_post_drafts(
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[PostDraftResponse]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        return []
    rows = db.scalars(
        select(PostDraft).where(PostDraft.project_id == proj.id).order_by(PostDraft.created_at.desc())
    ).all()
    return [PostDraftResponse.model_validate(row) for row in rows]


@router.put("/drafts/posts/{draft_id}", response_model=PostDraftResponse)
def update_post_draft(
    draft_id: int,
    payload: PostDraftUpdateRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> PostDraftResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    draft = db.scalar(
        select(PostDraft).join(Project).where(PostDraft.id == draft_id, Project.workspace_id == workspace.id)
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Post draft not found.")
    draft.title = payload.title
    draft.body = payload.body
    draft.rationale = payload.rationale
    db.commit()
    db.refresh(draft)
    return PostDraftResponse.model_validate(draft)
