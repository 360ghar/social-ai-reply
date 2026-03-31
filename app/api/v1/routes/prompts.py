"""Prompt template CRUD endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    ensure_default_prompts,
    ensure_workspace_membership,
    get_current_user,
    get_current_workspace,
    get_project,
)
from app.db.models import AccountUser, Project, PromptTemplate, Workspace
from app.db.session import get_db
from app.schemas.v1.product import PromptTemplateRequest, PromptTemplateResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["prompts"])


@router.get("/prompts", response_model=list[PromptTemplateResponse])
def list_prompts(
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[PromptTemplateResponse]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    get_project(db, workspace.id, project_id)
    ensure_default_prompts(db, project_id)
    rows = db.scalars(select(PromptTemplate).where(PromptTemplate.project_id == project_id).order_by(PromptTemplate.prompt_type)).all()
    return [PromptTemplateResponse.model_validate(row) for row in rows]


@router.post("/prompts", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_prompt(
    payload: PromptTemplateRequest,
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> PromptTemplateResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    get_project(db, workspace.id, project_id)
    row = PromptTemplate(project_id=project_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return PromptTemplateResponse.model_validate(row)


@router.put("/prompts/{prompt_id}", response_model=PromptTemplateResponse)
def update_prompt(
    prompt_id: int,
    payload: PromptTemplateRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> PromptTemplateResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(select(PromptTemplate).join(Project).where(PromptTemplate.id == prompt_id, Project.workspace_id == workspace.id))
    if not row:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return PromptTemplateResponse.model_validate(row)


@router.delete("/prompts/{prompt_id}")
def delete_prompt(
    prompt_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(select(PromptTemplate).join(Project).where(PromptTemplate.id == prompt_id, Project.workspace_id == workspace.id))
    if not row:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    db.delete(row)
    db.commit()
    return {"ok": True}
