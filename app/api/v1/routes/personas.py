"""Persona management endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_current_user,
    get_current_workspace,
    get_project,
)
from app.db.models import AccountUser, Persona, Project, Workspace
from app.db.session import get_db
from app.schemas.v1.product import PersonaRequest, PersonaResponse
from app.services.product.copilot import ProductCopilot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["personas"])


@router.get("/personas", response_model=list[PersonaResponse])
def list_personas(
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[PersonaResponse]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    project = get_project(db, workspace.id, project_id)
    rows = db.scalars(select(Persona).where(Persona.project_id == project.id).order_by(Persona.created_at.desc())).all()
    return [PersonaResponse.model_validate(row) for row in rows]


@router.post("/personas", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
def create_persona(
    payload: PersonaRequest,
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> PersonaResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    project = get_project(db, workspace.id, project_id)
    persona = Persona(project_id=project.id, **payload.model_dump())
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return PersonaResponse.model_validate(persona)


@router.post("/personas/generate", response_model=list[PersonaResponse])
def generate_personas(
    project_id: int = Query(..., ge=1),
    count: int = Query(default=4, ge=1, le=8),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[PersonaResponse]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    project = get_project(db, workspace.id, project_id)
    generated = ProductCopilot().suggest_personas(project.brand_profile, count=count)
    rows = []
    for item in generated:
        persona = Persona(project_id=project.id, **item)
        db.add(persona)
        rows.append(persona)
    db.commit()
    for row in rows:
        db.refresh(row)
    return [PersonaResponse.model_validate(row) for row in rows]


@router.delete("/personas/{persona_id}")
def delete_persona(
    persona_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    persona = db.scalar(select(Persona).join(Project).where(Persona.id == persona_id, Project.workspace_id == workspace.id))
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found.")
    db.delete(persona)
    db.commit()
    return {"ok": True}
