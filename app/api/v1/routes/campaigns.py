import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import ensure_workspace_membership, get_active_project, get_current_user, get_current_workspace
from app.db.models import AccountUser, Campaign, Project, Workspace
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["campaigns"])


@router.get("/campaigns")
def list_campaigns(
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """List campaigns for a project"""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    campaigns = db.query(Campaign).filter(Campaign.project_id == proj.id).order_by(Campaign.created_at.desc()).all()
    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "status": c.status,
                "goal": c.goal,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in campaigns
        ]
    }


@router.post("/campaigns")
def create_campaign(
    payload: dict,
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Create a new campaign"""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    campaign = Campaign(
        project_id=proj.id,
        name=payload.get("name", "New Campaign"),
        description=payload.get("description"),
        status=payload.get("status", "active"),
        goal=payload.get("goal"),
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return {
        "id": campaign.id,
        "name": campaign.name,
        "description": campaign.description,
        "status": campaign.status,
        "goal": campaign.goal,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
    }


@router.put("/campaigns/{campaign_id}")
def update_campaign(
    campaign_id: str,
    payload: dict,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Update a campaign"""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.project_id.in_(select(Project.id).where(Project.workspace_id == workspace.id))
    ).first()
    if not campaign:
        raise HTTPException(404, "Campaign not found.")

    if "name" in payload:
        campaign.name = payload["name"]
    if "description" in payload:
        campaign.description = payload["description"]
    if "status" in payload:
        campaign.status = payload["status"]
    if "goal" in payload:
        campaign.goal = payload["goal"]

    db.commit()
    db.refresh(campaign)

    return {
        "id": campaign.id,
        "name": campaign.name,
        "description": campaign.description,
        "status": campaign.status,
        "goal": campaign.goal,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
    }


@router.delete("/campaigns/{campaign_id}")
def delete_campaign(
    campaign_id: str,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Delete a campaign"""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.project_id.in_(select(Project.id).where(Project.workspace_id == workspace.id))
    ).first()
    if not campaign:
        raise HTTPException(404, "Campaign not found.")

    db.delete(campaign)
    db.commit()

    return {"success": True, "message": "Campaign deleted."}
