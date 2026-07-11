"""Tweet suggestion management endpoints: generate, list, approve, reject."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_current_user,
    get_current_workspace,
)
from app.db.supabase_client import get_supabase
from app.db.tables.tweet_suggestions import (
    get_suggestion_by_id,
    list_suggestions,
    update_suggestion,
)
from app.schemas.v1.tweet_suggestions import (
    SuggestionApproveRequest,
    SuggestionGenerateRequest,
    SuggestionGenerateResponse,
    SuggestionRejectRequest,
    TweetSuggestionResponse,
)
from app.services.product.tweet_scheduler import (
    ALL_PLATFORMS,
    publish_due_suggestions,
)
from app.services.product.tweet_suggestion_service import generate_suggestions

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["tweet_suggestions"])


@router.post(
    "/suggestions/generate",
    response_model=SuggestionGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_suggestion_batch(
    payload: SuggestionGenerateRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> SuggestionGenerateResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    platform = "x" if payload.platform == "twitter" else payload.platform

    inserted = generate_suggestions(
        db=supabase,
        workspace_id=workspace["id"],
        platform=platform,
        days=payload.days,
        suggestions_per_day=payload.suggestions_per_day,
        brand_context=None,
    )
    return SuggestionGenerateResponse(
        generated_count=len(inserted),
        suggestions=[TweetSuggestionResponse.model_validate(r) for r in inserted],
    )


@router.get("/suggestions", response_model=list[TweetSuggestionResponse])
def list_suggestion_batch(
    status: str | None = Query(default=None, alias="status"),
    platform: str | None = Query(default=None, alias="platform"),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[TweetSuggestionResponse]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])

    rows = list_suggestions(
        db=supabase,
        workspace_id=workspace["id"],
        status=status,
        platform=platform,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    return [TweetSuggestionResponse.model_validate(r) for r in rows]


@router.patch(
    "/suggestions/{suggestion_id}/approve",
    response_model=TweetSuggestionResponse,
)
def approve_suggestion(
    suggestion_id: int,
    payload: SuggestionApproveRequest | None = None,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> TweetSuggestionResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    payload = payload or SuggestionApproveRequest()

    suggestion = get_suggestion_by_id(supabase, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found.")
    if suggestion["workspace_id"] != workspace["id"]:
        raise HTTPException(status_code=403, detail="Suggestion does not belong to this workspace.")
    if suggestion["status"] != "pending":
        raise HTTPException(
            status_code=422,
            detail=f"Cannot approve suggestion with status '{suggestion['status']}'. Only 'pending' suggestions can be approved.",
        )

    suggested_date: str = suggestion["suggested_for_date"]
    if payload.scheduled_at:
        scheduled = payload.scheduled_at
    else:
        schedule_time = datetime.combine(
            datetime.strptime(suggested_date, "%Y-%m-%d").date(),
            datetime.min.time(),
        )
        scheduled = schedule_time.replace(hour=9, minute=0, tzinfo=UTC)
        now = datetime.now(UTC)
        if scheduled <= now:
            scheduled += timedelta(days=1)

    updated = update_suggestion(supabase, suggestion_id, {
        "status": "approved",
        "scheduled_at": scheduled.isoformat(),
    })
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update suggestion.")
    return TweetSuggestionResponse.model_validate(updated)


@router.patch(
    "/suggestions/{suggestion_id}/reject",
    response_model=TweetSuggestionResponse,
)
def reject_suggestion(
    suggestion_id: int,
    payload: SuggestionRejectRequest | None = None,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> TweetSuggestionResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    payload = payload or SuggestionRejectRequest()

    suggestion = get_suggestion_by_id(supabase, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found.")
    if suggestion["workspace_id"] != workspace["id"]:
        raise HTTPException(status_code=403, detail="Suggestion does not belong to this workspace.")
    if suggestion["status"] not in ("pending", "approved"):
        raise HTTPException(
            status_code=422,
            detail=f"Cannot reject suggestion with status '{suggestion['status']}'. Only 'pending' or 'approved' suggestions can be rejected.",
        )

    updated = update_suggestion(supabase, suggestion_id, {"status": "rejected"})
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update suggestion.")
    return TweetSuggestionResponse.model_validate(updated)


@router.post("/suggestions/scheduler/run")
def run_scheduler(
    platform: str | None = Query(
        default=None,
        alias="platform",
        description=f"Platform to publish. One of {', '.join(ALL_PLATFORMS)}. If omitted, defaults to 'x'.",
    ),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> dict:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    target_platform = platform or "x"
    result = publish_due_suggestions(supabase, workspace["id"], target_platform)
    return result



