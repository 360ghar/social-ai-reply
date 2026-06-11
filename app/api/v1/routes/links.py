"""Tracked link (ROI attribution) endpoints.

Two routers live here:
- ``router`` — authenticated /v1 endpoints for creating/listing links and the ROI rollup.
- ``public_router`` — the unauthenticated ``GET /r/{code}`` redirect that logs clicks.
"""
import hashlib
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from supabase import Client

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_active_project,
    get_current_user,
    get_current_workspace,
    get_project,
)
from app.db.supabase_client import get_supabase
from app.db.tables.tracked_links import (
    count_clicks_for_links,
    create_link_click,
    create_tracked_link,
    get_roi_rollup,
    get_tracked_link_by_code,
    list_tracked_links_for_project,
)
from app.schemas.v1.links import (
    RoiRollupResponse,
    RoiRollupRow,
    TrackedLinkCreateRequest,
    TrackedLinkResponse,
)
from app.utils.utm import append_utm, build_utm_params, generate_link_code

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["links"])
public_router = APIRouter(tags=["links-public"])

MAX_CODE_ATTEMPTS = 5
USER_AGENT_HASH_LENGTH = 16


def _hash_user_agent(user_agent: str | None) -> str | None:
    """Hash a raw user-agent so it is never stored verbatim."""
    if not user_agent:
        return None
    return hashlib.sha256(user_agent.encode("utf-8")).hexdigest()[:USER_AGENT_HASH_LENGTH]


def _generate_unique_code(supabase: Client) -> str:
    """Generate a link code that does not collide with an existing one."""
    for _ in range(MAX_CODE_ATTEMPTS):
        code = generate_link_code()
        if get_tracked_link_by_code(supabase, code) is None:
            return code
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Could not allocate a unique link code. Please retry.",
    )


def _link_response(row: dict[str, Any], click_count: int = 0) -> TrackedLinkResponse:
    """Build a TrackedLinkResponse from a tracked_links row."""
    utm_params = row.get("utm_params") or {}
    return TrackedLinkResponse(
        id=row["id"],
        project_id=row["project_id"],
        code=row["code"],
        destination_url=row["destination_url"],
        opportunity_id=row.get("opportunity_id"),
        reply_draft_id=row.get("reply_draft_id"),
        utm_params=utm_params,
        created_at=row["created_at"],
        short_path=f"/r/{row['code']}",
        tracked_url=append_utm(row["destination_url"], utm_params),
        click_count=click_count,
    )


@router.post("/links", response_model=TrackedLinkResponse, status_code=status.HTTP_201_CREATED)
def create_tracked_link_endpoint(
    payload: TrackedLinkCreateRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> TrackedLinkResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    project = get_project(supabase, workspace["id"], payload.project_id)

    utm_params = build_utm_params(project["slug"], payload.opportunity_id)
    code = _generate_unique_code(supabase)

    link_data = {
        "project_id": project["id"],
        "code": code,
        "destination_url": payload.destination_url,
        "opportunity_id": payload.opportunity_id,
        "reply_draft_id": payload.reply_draft_id,
        "utm_params": utm_params,
    }
    link = create_tracked_link(supabase, link_data)
    return _link_response(link)


@router.get("/links", response_model=list[TrackedLinkResponse])
def list_tracked_links_endpoint(
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[TrackedLinkResponse]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    project = get_active_project(supabase, workspace["id"], project_id)
    if not project:
        return []

    links = list_tracked_links_for_project(supabase, project["id"])
    click_counts = count_clicks_for_links(supabase, [link["id"] for link in links])
    return [_link_response(link, click_counts.get(link["id"], 0)) for link in links]


@router.get("/analytics/roi", response_model=RoiRollupResponse)
def roi_rollup_endpoint(
    project_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> RoiRollupResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    project = get_active_project(supabase, workspace["id"], project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    rows = get_roi_rollup(supabase, project["id"])
    return RoiRollupResponse(
        project_id=project["id"],
        rows=[RoiRollupRow.model_validate(row) for row in rows],
    )


@public_router.get("/r/{code}")
def follow_tracked_link(
    code: str,
    request: Request,
    supabase: Client = Depends(get_supabase),
) -> RedirectResponse:
    """Public redirect for a tracked link. Logs a click, never stores raw user-agents."""
    try:
        link = get_tracked_link_by_code(supabase, code)
    except Exception:  # noqa: BLE001 — public surface: degrade to 404, never 500
        logger.exception("Tracked-link lookup failed for code %s", code)
        link = None
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found.")

    try:
        create_link_click(
            supabase,
            {
                "tracked_link_id": link["id"],
                "referrer": request.headers.get("referer"),
                "user_agent_hash": _hash_user_agent(request.headers.get("user-agent")),
            },
        )
    except Exception:
        logger.exception("Failed to log click for tracked link %s", link["id"])

    destination = append_utm(link["destination_url"], link.get("utm_params") or {})
    return RedirectResponse(destination, status_code=status.HTTP_302_FOUND)
