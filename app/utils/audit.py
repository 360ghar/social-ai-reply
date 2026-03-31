from sqlalchemy.orm import Session

from app.db.models import AuditEvent


def record_audit(
    db: Session,
    *,
    workspace_id: int | None,
    project_id: int | None,
    actor_user_id: int | None,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            workspace_id=workspace_id,
            project_id=project_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        )
    )
