"""Prompt template CRUD endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.api.v1.deps import (
    ensure_default_prompts,
    ensure_workspace_membership,
    get_current_user,
    get_current_workspace,
    get_project,
)
from app.db.supabase_client import get_supabase
from app.db.tables.projects import (
    create_prompt_template,
    delete_prompt_template,
    get_prompt_template_by_id,
    list_prompt_templates_for_project,
    update_prompt_template,
)
from app.schemas.v1.product import PromptTemplateRequest, PromptTemplateResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["prompts"])


@router.get("/prompts", response_model=list[PromptTemplateResponse])
def list_prompts(
    project_id: int = Query(..., ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[PromptTemplateResponse]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    get_project(supabase, workspace["id"], project_id)
    ensure_default_prompts(supabase, project_id)

    rows = list_prompt_templates_for_project(supabase, project_id)
    # Sort by prompt_type
    rows.sort(key=lambda x: x.get("prompt_type", ""))
    return [PromptTemplateResponse.model_validate(row) for row in rows]


@router.post("/prompts", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_prompt(
    payload: PromptTemplateRequest,
    project_id: int = Query(..., ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> PromptTemplateResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    get_project(supabase, workspace["id"], project_id)

    template_data = {"project_id": project_id, **payload.model_dump()}
    row = create_prompt_template(supabase, template_data)
    return PromptTemplateResponse.model_validate(row)


@router.put("/prompts/{prompt_id}", response_model=PromptTemplateResponse)
def update_prompt(
    prompt_id: int,
    payload: PromptTemplateRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> PromptTemplateResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    row = get_prompt_template_by_id(supabase, prompt_id)
    if not row:
        raise HTTPException(status_code=404, detail="Prompt not found.")

    # Verify workspace access via project
    get_project(supabase, workspace["id"], row["project_id"])

    updated = update_prompt_template(supabase, prompt_id, payload.model_dump())
    return PromptTemplateResponse.model_validate(updated)


@router.delete("/prompts/{prompt_id}")
def delete_prompt(
    prompt_id: int,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> dict[str, bool]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    row = get_prompt_template_by_id(supabase, prompt_id)
    if not row:
        raise HTTPException(status_code=404, detail="Prompt not found.")

    # Verify workspace access via project
    get_project(supabase, workspace["id"], row["project_id"])

    delete_prompt_template(supabase, prompt_id)
    return {"ok": True}
