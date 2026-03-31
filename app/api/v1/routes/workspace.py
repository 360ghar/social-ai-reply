import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_active_project,
    get_current_user,
    get_current_workspace,
)
from app.db.models import (
    AccountUser,
    MembershipRole,
    Workspace,
)
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["workspace"])


@router.delete("/workspace")
def delete_workspace(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    membership = ensure_workspace_membership(db, workspace.id, current_user.id)
    if membership.role != MembershipRole.OWNER:
        raise HTTPException(status_code=403, detail="Only the workspace owner can delete this workspace.")
    db.delete(workspace)
    db.commit()
    return {"ok": True}


@router.get("/activity")
def list_activity(
    limit: int = 20, offset: int = 0,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    from app.db.models import ActivityLog
    ensure_workspace_membership(db, workspace.id, current_user.id)
    items = db.query(ActivityLog).filter(ActivityLog.workspace_id == workspace.id) \
        .order_by(ActivityLog.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "items": [
            {"id": a.id, "action": a.action, "entity_type": a.entity_type,
             "entity_id": a.entity_id, "metadata": a.metadata_json,
             "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in items
        ]
    }


@router.get("/usage")
def get_usage(
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    ensure_workspace_membership(db, workspace.id, current_user.id)
    # Usage is informational only because the workspace is fully unlocked.
    selected_project = get_active_project(db, workspace.id, project_id)
    active_project_id = selected_project.id if selected_project else None
    from app.services.product.entitlements import count_projects, count_active_keywords, count_active_subreddits
    return {
        "plan": "unlocked",
        "metrics": {
            "projects": {"used": count_projects(db, workspace.id), "limit": 999999},
            "keywords": {"used": count_active_keywords(db, active_project_id) if active_project_id else 0, "limit": 999999},
            "subreddits": {"used": count_active_subreddits(db, active_project_id) if active_project_id else 0, "limit": 999999},
        },
    }
