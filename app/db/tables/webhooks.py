"""Webhook endpoint table operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

WEBHOOK_ENDPOINTS_TABLE = "webhook_endpoints"


def get_webhook_endpoint_by_id(db: Client, endpoint_id: int) -> dict[str, Any] | None:
    """Get a webhook endpoint by ID."""
    result = db.table(WEBHOOK_ENDPOINTS_TABLE).select("*").eq("id", endpoint_id).execute()
    return result.data[0] if result.data else None


def list_webhook_endpoints_for_workspace(db: Client, workspace_id: int) -> list[dict[str, Any]]:
    """List webhook endpoints for a workspace."""
    result = (
        db.table(WEBHOOK_ENDPOINTS_TABLE)
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("created_at", desc=True)
        .execute()
    )
    return list(result.data)


def create_webhook_endpoint(db: Client, endpoint_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new webhook endpoint."""
    result = db.table(WEBHOOK_ENDPOINTS_TABLE).insert(endpoint_data).execute()
    return result.data[0]


def update_webhook_endpoint(
    db: Client,
    endpoint_id: int,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Update a webhook endpoint."""
    result = db.table(WEBHOOK_ENDPOINTS_TABLE).update(update_data).eq("id", endpoint_id).execute()
    return result.data[0] if result.data else None


def delete_webhook_endpoint(db: Client, endpoint_id: int) -> None:
    """Delete a webhook endpoint."""
    db.table(WEBHOOK_ENDPOINTS_TABLE).delete().eq("id", endpoint_id).execute()
