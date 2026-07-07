"""Tweet suggestion table operations: CRUD for the content scheduling system."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)

SUGGESTIONS_TABLE = "tweet_suggestions"


def get_suggestion_by_id(db: Client, suggestion_id: int) -> dict[str, Any] | None:
    result = db.table(SUGGESTIONS_TABLE).select("*").eq("id", suggestion_id).execute()
    return result.data[0] if result.data else None


def list_suggestions(
    db: Client,
    workspace_id: int,
    status: str | None = None,
    platform: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    query = (
        db.table(SUGGESTIONS_TABLE)
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("suggested_for_date", desc=False)
        .order("created_at", desc=False)
        .range(offset, offset + limit - 1)
    )
    if status:
        query = query.eq("status", status)
    if platform:
        query = query.eq("platform", platform)
    if from_date:
        query = query.gte("suggested_for_date", from_date.isoformat())
    if to_date:
        query = query.lte("suggested_for_date", to_date.isoformat())
    result = query.execute()
    return list(result.data)


def count_suggestions(
    db: Client,
    workspace_id: int,
    status: str | None = None,
) -> int:
    query = db.table(SUGGESTIONS_TABLE).select("*", count="exact").eq("workspace_id", workspace_id)
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return result.count or 0


def create_suggestion(db: Client, data: dict[str, Any]) -> dict[str, Any]:
    result = db.table(SUGGESTIONS_TABLE).insert(data).execute()
    return result.data[0]


def bulk_create_suggestions(db: Client, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not records:
        return []
    result = db.table(SUGGESTIONS_TABLE).insert(records).execute()
    return list(result.data)


def update_suggestion(db: Client, suggestion_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    result = db.table(SUGGESTIONS_TABLE).update(data).eq("id", suggestion_id).execute()
    return result.data[0] if result.data else None


def delete_suggestion(db: Client, suggestion_id: int) -> None:
    db.table(SUGGESTIONS_TABLE).delete().eq("id", suggestion_id).execute()


def list_suggestions_ready_to_publish(
    db: Client,
    workspace_id: int,
    now: datetime | None = None,
    platform: str = "x",
) -> list[dict[str, Any]]:
    if now is None:
        now = datetime.now(UTC)
    result = (
        db.table(SUGGESTIONS_TABLE)
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("status", "approved")
        .eq("platform", platform)
        .is_("published_at", "null")
        .lte("scheduled_at", now.isoformat())
        .order("scheduled_at", desc=False)
        .execute()
    )
    return list(result.data)


def list_suggestions_for_date_range(
    db: Client,
    workspace_id: int,
    start_date: date,
    end_date: date,
    platform: str = "twitter",
) -> list[dict[str, Any]]:
    result = (
        db.table(SUGGESTIONS_TABLE)
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("platform", platform)
        .gte("suggested_for_date", start_date.isoformat())
        .lte("suggested_for_date", end_date.isoformat())
        .order("suggested_for_date", desc=False)
        .execute()
    )
    return list(result.data)
