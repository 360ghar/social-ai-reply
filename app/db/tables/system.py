"""System table operations: notifications, activity logs, usage metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

NOTIFICATIONS_TABLE = "notifications"
ACTIVITY_LOGS_TABLE = "activity_logs"
USAGE_METRICS_TABLE = "usage_metrics"


# Notification operations
def get_notification_by_id(db: Client, notification_id: int) -> dict[str, Any] | None:
    """Get a notification by ID."""
    result = db.table(NOTIFICATIONS_TABLE).select("*").eq("id", notification_id).execute()
    return result.data[0] if result.data else None


def list_notifications_for_workspace(
    db: Client,
    workspace_id: int,
    limit: int = 50,
    unread_only: bool = False,
) -> list[dict[str, Any]]:
    """List notifications for a workspace."""
    query = db.table(NOTIFICATIONS_TABLE).select("*").eq("workspace_id", workspace_id)
    if unread_only:
        query = query.eq("is_read", False)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return list(result.data)


def create_notification(db: Client, notification_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new notification."""
    result = db.table(NOTIFICATIONS_TABLE).insert(notification_data).execute()
    return result.data[0]


def update_notification(db: Client, notification_id: int, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a notification."""
    result = db.table(NOTIFICATIONS_TABLE).update(update_data).eq("id", notification_id).execute()
    return result.data[0] if result.data else None


def delete_notification(db: Client, notification_id: int) -> None:
    """Delete a notification."""
    db.table(NOTIFICATIONS_TABLE).delete().eq("id", notification_id).execute()


def mark_notification_read(db: Client, notification_id: int) -> dict[str, Any] | None:
    """Mark a notification as read."""
    return update_notification(db, notification_id, {"is_read": True})


# Activity log operations
def get_activity_log_by_id(db: Client, log_id: int) -> dict[str, Any] | None:
    """Get an activity log by ID."""
    result = db.table(ACTIVITY_LOGS_TABLE).select("*").eq("id", log_id).execute()
    return result.data[0] if result.data else None


def list_activity_logs_for_workspace(
    db: Client,
    workspace_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List activity logs for a workspace."""
    result = (
        db.table(ACTIVITY_LOGS_TABLE)
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return list(result.data)


def create_activity_log(db: Client, log_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new activity log."""
    result = db.table(ACTIVITY_LOGS_TABLE).insert(log_data).execute()
    return result.data[0]


def delete_activity_log(db: Client, log_id: int) -> None:
    """Delete an activity log."""
    db.table(ACTIVITY_LOGS_TABLE).delete().eq("id", log_id).execute()


# Usage metric operations
def get_usage_metric_by_id(db: Client, metric_id: int) -> dict[str, Any] | None:
    """Get a usage metric by ID."""
    result = db.table(USAGE_METRICS_TABLE).select("*").eq("id", metric_id).execute()
    return result.data[0] if result.data else None


def get_usage_metric_by_workspace_and_key(
    db: Client,
    workspace_id: int,
    metric_key: str,
) -> dict[str, Any] | None:
    """Get a usage metric by workspace ID and metric key."""
    result = (
        db.table(USAGE_METRICS_TABLE)
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("metric_key", metric_key)
        .execute()
    )
    return result.data[0] if result.data else None


def list_usage_metrics_for_workspace(db: Client, workspace_id: int) -> list[dict[str, Any]]:
    """List usage metrics for a workspace."""
    result = (
        db.table(USAGE_METRICS_TABLE)
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("metric_key")
        .execute()
    )
    return list(result.data)


def create_usage_metric(db: Client, metric_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new usage metric."""
    result = db.table(USAGE_METRICS_TABLE).insert(metric_data).execute()
    return result.data[0]


def update_usage_metric(db: Client, metric_id: int, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a usage metric."""
    result = db.table(USAGE_METRICS_TABLE).update(update_data).eq("id", metric_id).execute()
    return result.data[0] if result.data else None


def delete_usage_metric(db: Client, metric_id: int) -> None:
    """Delete a usage metric."""
    db.table(USAGE_METRICS_TABLE).delete().eq("id", metric_id).execute()
