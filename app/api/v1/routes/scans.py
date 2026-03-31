"""Scan run endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.deps import ensure_workspace_membership, get_active_project, get_current_user, get_current_workspace
from app.db.models import AccountUser, Workspace
from app.db.session import get_db
from app.schemas.v1.product import ScanRequest, ScanRunResponse
from app.services.product.scanner import run_scan

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["scans"])


@router.post("/scans", response_model=ScanRunResponse)
def create_scan(
    payload: ScanRequest,
    project_id: int = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> ScanRunResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="No active project found.")
    result = run_scan(db, proj, payload)
    return ScanRunResponse.model_validate(result)
