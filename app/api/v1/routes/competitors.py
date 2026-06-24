"""Competitor intelligence routes."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

if TYPE_CHECKING:
    from supabase import Client

from app.api.v1.deps import get_current_user, get_current_workspace
from app.db.supabase_client import get_supabase
from app.db.tables.competitors import (
    get_competitor_stats,
    list_competitor_mentions,
)
from app.schemas.v1.competitors import (
    CompetitorMentionResponse,
    CompetitorStatsResponse,
)
from app.services.product.competitor_intel import get_project_competitors

router = APIRouter(prefix="/competitors", tags=["competitors"])


@router.get("/mentions")
def list_mentions(
    competitor_name: str | None = None,
    sentiment: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[CompetitorMentionResponse]:
    """List competitor mentions for the active project."""
    projects = supabase.table("projects").select("id").eq("workspace_id", workspace["id"]).execute()
    if not projects.data:
        return []
    project_id = projects.data[0]["id"]
    mentions = list_competitor_mentions(
        supabase,
        project_id,
        competitor_name=competitor_name,
        sentiment=sentiment,
        limit=limit,
        offset=offset,
    )
    return [CompetitorMentionResponse.model_validate(m) for m in mentions]


@router.get("/stats")
def get_stats(
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[CompetitorStatsResponse]:
    """Return aggregated competitor stats for the active project."""
    projects = supabase.table("projects").select("id").eq("workspace_id", workspace["id"]).execute()
    if not projects.data:
        return []
    project_id = projects.data[0]["id"]
    stats = get_competitor_stats(supabase, project_id)
    return [CompetitorStatsResponse.model_validate(s) for s in stats]


@router.get("/list")
def list_competitors(
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[str]:
    """Return the competitor names from the company profile."""
    projects = supabase.table("projects").select("id").eq("workspace_id", workspace["id"]).execute()
    if not projects.data:
        return []
    return get_project_competitors(supabase, projects.data[0]["id"])
