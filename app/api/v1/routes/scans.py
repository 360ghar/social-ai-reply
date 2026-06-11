"""Scan run endpoints."""
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from supabase import Client

from app.api.v1.deps import ensure_workspace_membership, get_active_project, get_current_user, get_current_workspace
from app.db.supabase_client import get_supabase
from app.db.tables.discovery import create_scan_run, get_scan_run_by_id
from app.db.tables.projects import get_project_by_id
from app.schemas.v1.discovery import ScanRequest, ScanRunResponse
from app.services.product.scanner import run_scan

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["scans"])


def _run_scan_background(db: Client, project: dict, payload: ScanRequest, scan_run_id: str) -> None:
    try:
        run_scan(db, project, payload, scan_run_id=scan_run_id)
    except Exception:  # noqa: BLE001 — run_scan already persisted the error status
        logger.exception("Background scan %s failed", scan_run_id)


@router.post("/scans", response_model=ScanRunResponse)
def create_scan(
    payload: ScanRequest,
    background_tasks: BackgroundTasks,
    project_id: int = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> ScanRunResponse:
    """Start a scan and return immediately; poll GET /v1/scans/{id} for progress."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    effective_project_id = project_id or payload.project_id
    proj = get_active_project(supabase, workspace["id"], effective_project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="No active project found.")

    # Fail fast on setup problems — these used to surface synchronously and the
    # frontend expects a 400, not a scan run that instantly errors.
    from app.db.tables.discovery import list_discovery_keywords_for_project, list_monitored_subreddits_for_project
    if not any(k.get("is_active", True) for k in list_discovery_keywords_for_project(supabase, proj["id"])):
        raise HTTPException(status_code=400, detail="Add discovery keywords before scanning.")
    if not any(s.get("is_active", True) for s in list_monitored_subreddits_for_project(supabase, proj["id"])):
        raise HTTPException(status_code=400, detail="Add monitored subreddits before scanning.")

    run = create_scan_run(supabase, {
        "project_id": proj["id"],
        "status": "running",
        "search_window_hours": payload.search_window_hours,
        "posts_scanned": 0,
        "opportunities_found": 0,
        "started_at": datetime.now(UTC).isoformat(),
    })
    background_tasks.add_task(_run_scan_background, supabase, proj, payload, run["id"])
    return ScanRunResponse.model_validate(run)


@router.get("/scans/{scan_id}", response_model=ScanRunResponse)
def get_scan(
    scan_id: str,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> ScanRunResponse:
    """Poll the status/progress of a scan run."""
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    run = get_scan_run_by_id(supabase, scan_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scan run not found.")
    project = get_project_by_id(supabase, run["project_id"])
    if not project or project.get("workspace_id") != workspace["id"]:
        raise HTTPException(status_code=404, detail="Scan run not found.")
    return ScanRunResponse.model_validate(run)
