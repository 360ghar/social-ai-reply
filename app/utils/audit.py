"""Audit logging utilities."""

from supabase import Client

from app.db.tables.system import create_activity_log


def record_audit(
    supabase: Client,
    *,
    workspace_id: int | None,
    project_id: int | None,
    actor_user_id: int | None,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict | None = None,
) -> None:
    """Record an audit event.

    Args:
        supabase: Supabase client instance.
        workspace_id: Workspace ID (if applicable).
        project_id: Project ID (if applicable).
        actor_user_id: User ID who performed the action.
        event_type: Type of event (e.g., "project.created").
        entity_type: Type of entity (e.g., "Project").
        entity_id: ID of the entity.
        payload: Optional additional data.
    """
    create_activity_log(
        supabase,
        {
            "workspace_id": workspace_id,
            "project_id": project_id,
            "actor_user_id": actor_user_id,
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metadata_json": payload or {},
        },
    )
