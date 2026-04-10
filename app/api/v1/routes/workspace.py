"""Workspace management endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_active_project,
    get_current_user,
    get_current_workspace,
)
from app.db.supabase_client import get_supabase
from app.db.tables import (
    delete_workspace as delete_workspace_db,
)
from app.db.tables.system import list_activity_logs_for_workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["workspace"])


@router.delete("/workspace")
def delete_workspace(
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> dict[str, bool]:
    membership = ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    if membership.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only the workspace owner can delete this workspace.")

    delete_workspace_db(supabase, workspace["id"])
    return {"ok": True}


@router.get("/activity")
def list_activity(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    items = list_activity_logs_for_workspace(supabase, workspace["id"], limit=limit, offset=offset)
    return {
        "items": [
            {
                "id": a["id"],
                "action": a["action"],
                "entity_type": a.get("entity_type"),
                "entity_id": a.get("entity_id"),
                "metadata": a.get("metadata_json", {}),
                "created_at": a["created_at"] if a.get("created_at") else None,
            }
            for a in items
        ]
    }


@router.get("/usage")
def get_usage(
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    selected_project = get_active_project(supabase, workspace["id"], project_id)
    active_project_id = selected_project["id"] if selected_project else None

    from app.services.product.entitlements import count_active_keywords, count_active_subreddits, count_projects

    return {
        "plan": "unlocked",
        "metrics": {
            "projects": {"used": count_projects(supabase, workspace["id"]), "limit": 999999},
            "keywords": {"used": count_active_keywords(supabase, active_project_id) if active_project_id else 0, "limit": 999999},
            "subreddits": {"used": count_active_subreddits(supabase, active_project_id) if active_project_id else 0, "limit": 999999},
        },
    }
