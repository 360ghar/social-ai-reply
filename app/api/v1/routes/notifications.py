import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import ensure_workspace_membership, get_current_user, get_current_workspace
from app.db.models import AccountUser, Notification as NotificationModel, Workspace
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["notifications"])


@router.get("/notifications")
def list_notifications(
    limit: int = 20,
    offset: int = 0,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """List notifications for current user"""
    ensure_workspace_membership(db, workspace.id, current_user.id)

    notifications = db.query(NotificationModel).filter(
        NotificationModel.workspace_id == workspace.id,
        (NotificationModel.user_id == current_user.id) | (NotificationModel.user_id.is_(None))
    ).order_by(NotificationModel.created_at.desc()).offset(offset).limit(limit).all()

    unread_count = db.query(NotificationModel).filter(
        NotificationModel.workspace_id == workspace.id,
        (NotificationModel.user_id == current_user.id) | (NotificationModel.user_id.is_(None)),
        NotificationModel.is_read.is_(False)
    ).count()

    return {
        "items": [
            {
                "id": n.id,
                "title": n.title,
                "body": n.body,
                "message": n.body,
                "type": n.type,
                "link": n.action_url,
                "action_url": n.action_url,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ],
        "unread_count": unread_count,
    }


@router.put("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Mark a notification as read"""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    notification = db.query(NotificationModel).filter(
        NotificationModel.id == notification_id,
        NotificationModel.workspace_id == workspace.id,
    ).first()
    if not notification:
        raise HTTPException(404, "Notification not found.")

    notification.is_read = True
    db.commit()
    db.refresh(notification)

    return {"id": notification.id, "is_read": notification.is_read}


@router.put("/notifications/read-all")
def mark_all_read(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read"""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    db.query(NotificationModel).filter(
        NotificationModel.workspace_id == workspace.id,
        (NotificationModel.user_id == current_user.id) | (NotificationModel.user_id.is_(None)),
        NotificationModel.is_read.is_(False)
    ).update({NotificationModel.is_read: True}, synchronize_session=False)
    db.commit()

    return {"success": True, "message": "All notifications marked as read."}


@router.delete("/notifications/{notification_id}")
def delete_notification(
    notification_id: str,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Delete a notification"""
    ensure_workspace_membership(db, workspace.id, current_user.id)
    notification = db.query(NotificationModel).filter(
        NotificationModel.id == notification_id,
        NotificationModel.workspace_id == workspace.id,
    ).first()
    if not notification:
        raise HTTPException(404, "Notification not found.")

    db.delete(notification)
    db.commit()

    return {"success": True, "message": "Notification deleted."}
