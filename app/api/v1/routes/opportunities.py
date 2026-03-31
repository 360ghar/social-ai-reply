"""Opportunity listing and status management endpoints."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.deps import ensure_workspace_membership, get_active_project, get_current_user, get_current_workspace
from app.db.models import (
    AccountUser,
    Opportunity,
    OpportunityStatus,
    Project,
    ReplyDraft,
    Workspace,
)
from app.db.session import get_db
from app.schemas.v1.product import OpportunityResponse, OpportunityStatusRequest

logger = logging.getLogger(__name__)

_VALID_TRANSITIONS: dict[str, set[str]] = {
    "new": {"saved", "drafting", "ignored"},
    "saved": {"drafting", "ignored"},
    "drafting": {"posted", "saved", "ignored"},
    "posted": set(),
    "ignored": {"new"},
}

router = APIRouter(prefix="/v1", tags=["opportunities"])


@router.get("/opportunities", response_model=list[OpportunityResponse])
def list_opportunities(
    status_filter: str = Query(default="new", alias="status"),
    project_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[OpportunityResponse]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        return []
    opp_status = OpportunityStatus(status_filter)
    stmt = (
        select(Opportunity)
        .where(Opportunity.project_id == proj.id, Opportunity.status == opp_status)
        .order_by(Opportunity.score.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = db.scalars(stmt).all()
    return [OpportunityResponse.model_validate(row) for row in rows]


@router.put("/opportunities/{opportunity_id}/status", response_model=OpportunityResponse)
def update_opportunity_status(
    opportunity_id: int,
    payload: OpportunityStatusRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> OpportunityResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    opportunity = db.scalar(
        select(Opportunity)
        .join(Project)
        .where(Opportunity.id == opportunity_id, Project.workspace_id == workspace.id)
        .options(selectinload(Opportunity.reply_drafts))
    )
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    current = opportunity.status.value
    target = payload.status
    if target not in _VALID_TRANSITIONS.get(current, set()):
        raise HTTPException(status_code=422, detail=f"Cannot transition from '{current}' to '{target}'.")
    opportunity.status = OpportunityStatus(target)
    if target == "posted":
        opportunity.posted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(opportunity)
    return OpportunityResponse.model_validate(opportunity)
