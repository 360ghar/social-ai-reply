"""Campaign management endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.api.v1.deps import ensure_workspace_membership, get_active_project, get_current_user, get_current_workspace
from app.db.supabase_client import get_supabase
from app.db.tables.campaigns import (
    create_campaign as create_campaign_db,
)
from app.db.tables.campaigns import (
    delete_campaign as delete_campaign_db,
)
from app.db.tables.campaigns import (
    get_campaign_by_id,
    list_campaigns_for_project,
)
from app.db.tables.campaigns import (
    update_campaign as update_campaign_db,
)
from app.db.tables.projects import get_project_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["campaigns"])


@router.get("/campaigns")
def list_campaigns(
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """List campaigns for a project"""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    campaigns = list_campaigns_for_project(supabase, proj["id"])
    return {
        "items": [
            {
                "id": c["id"],
                "name": c["name"],
                "description": c.get("description", ""),
                "status": c.get("status", "active"),
                "goal": c.get("goal", ""),
                "created_at": c.get("created_at"),
            }
            for c in campaigns
        ]
    }


@router.post("/campaigns")
def create_campaign(
    payload: dict,
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Create a new campaign"""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    proj = get_active_project(supabase, workspace["id"], project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    campaign = create_campaign_db(
        supabase,
        {
            "project_id": proj["id"],
            "name": payload.get("name", "New Campaign"),
            "description": payload.get("description"),
            "status": payload.get("status", "active"),
            "goal": payload.get("goal"),
        },
    )

    return {
        "id": campaign["id"],
        "name": campaign["name"],
        "description": campaign.get("description", ""),
        "status": campaign.get("status", "active"),
        "goal": campaign.get("goal", ""),
        "created_at": campaign.get("created_at"),
    }


@router.put("/campaigns/{campaign_id}")
def update_campaign(
    campaign_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Update a campaign"""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    # Verify campaign belongs to workspace
    campaign = get_campaign_by_id(supabase, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found.")

    # Verify workspace access via project
    proj = get_project_by_id(supabase, campaign["project_id"])
    if not proj or proj["workspace_id"] != workspace["id"]:
        raise HTTPException(404, "Campaign not found.")

    update_data = {}
    if "name" in payload:
        update_data["name"] = payload["name"]
    if "description" in payload:
        update_data["description"] = payload["description"]
    if "status" in payload:
        update_data["status"] = payload["status"]
    if "goal" in payload:
        update_data["goal"] = payload["goal"]

    updated = update_campaign_db(supabase, campaign_id, update_data)

    return {
        "id": updated["id"],
        "name": updated["name"],
        "description": updated.get("description", ""),
        "status": updated.get("status", "active"),
        "goal": updated.get("goal", ""),
        "created_at": updated.get("created_at"),
    }


@router.delete("/campaigns/{campaign_id}")
def delete_campaign(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
):
    """Delete a campaign"""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    campaign = get_campaign_by_id(supabase, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found.")

    # Verify workspace access via project
    proj = get_project_by_id(supabase, campaign["project_id"])
    if not proj or proj["workspace_id"] != workspace["id"]:
        raise HTTPException(404, "Campaign not found.")

    delete_campaign_db(supabase, campaign_id)

    return {"success": True, "message": "Campaign deleted."}
