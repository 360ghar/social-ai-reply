"""API regressions for notifications and webhooks authorization/security."""
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import (
    AccountUser,
    Membership,
    MembershipRole,
    Notification,
    WebhookEndpoint,
)
from app.services.product.security import hash_password


def _register_owner(client: TestClient) -> dict:
    response = client.post(
        "/v1/auth/register",
        json={
            "email": "owner@example.com",
            "password": "strongpass123",
            "full_name": "Owner User",
            "workspace_name": "Owner Workspace",
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    client.headers.update({"Authorization": f"Bearer {payload['access_token']}"})
    return payload


def _add_member(db_session, workspace_id: int, email: str = "member@example.com") -> AccountUser:
    member = AccountUser(
        email=email,
        password_hash=hash_password("strongpass123"),
        full_name="Member User",
    )
    db_session.add(member)
    db_session.flush()
    db_session.add(Membership(workspace_id=workspace_id, user_id=member.id, role=MembershipRole.MEMBER))
    db_session.commit()
    db_session.refresh(member)
    return member


class TestNotificationAuthorization:
    def test_mark_read_cannot_touch_another_users_personal_notification(self, client, db_session):
        payload = _register_owner(client)
        workspace_id = payload["workspace"]["id"]
        member = _add_member(db_session, workspace_id)

        notification = Notification(
            workspace_id=workspace_id,
            user_id=member.id,
            type="mention",
            title="Member-only notification",
            body="Private notification body",
            is_read=False,
        )
        db_session.add(notification)
        db_session.commit()
        db_session.refresh(notification)

        response = client.put(f"/v1/notifications/{notification.id}/read")

        assert response.status_code == 404
        db_session.refresh(notification)
        assert notification.is_read is False

    def test_delete_cannot_touch_another_users_personal_notification(self, client, db_session):
        payload = _register_owner(client)
        workspace_id = payload["workspace"]["id"]
        member = _add_member(db_session, workspace_id, email="member-delete@example.com")

        notification = Notification(
            workspace_id=workspace_id,
            user_id=member.id,
            type="mention",
            title="Delete-protected notification",
            body="Private notification body",
        )
        db_session.add(notification)
        db_session.commit()
        db_session.refresh(notification)

        response = client.delete(f"/v1/notifications/{notification.id}")

        assert response.status_code == 404
        still_exists = db_session.scalar(select(Notification).where(Notification.id == notification.id))
        assert still_exists is not None

    def test_mark_read_cannot_touch_workspace_wide_notification(self, client, db_session):
        payload = _register_owner(client)
        workspace_id = payload["workspace"]["id"]

        notification = Notification(
            workspace_id=workspace_id,
            user_id=None,
            type="mention",
            title="Workspace-wide notification",
            body="Visible to every member",
            is_read=False,
        )
        db_session.add(notification)
        db_session.commit()
        db_session.refresh(notification)

        response = client.put(f"/v1/notifications/{notification.id}/read")

        assert response.status_code == 404
        db_session.refresh(notification)
        assert notification.is_read is False

    def test_delete_cannot_touch_workspace_wide_notification(self, client, db_session):
        payload = _register_owner(client)
        workspace_id = payload["workspace"]["id"]

        notification = Notification(
            workspace_id=workspace_id,
            user_id=None,
            type="mention",
            title="Shared notification",
            body="Visible to every member",
        )
        db_session.add(notification)
        db_session.commit()
        db_session.refresh(notification)

        response = client.delete(f"/v1/notifications/{notification.id}")

        assert response.status_code == 404
        still_exists = db_session.scalar(select(Notification).where(Notification.id == notification.id))
        assert still_exists is not None

    def test_mark_all_read_only_updates_current_users_personal_notifications(self, client, db_session):
        payload = _register_owner(client)
        workspace_id = payload["workspace"]["id"]

        personal_notification = Notification(
            workspace_id=workspace_id,
            user_id=payload["user"]["id"],
            type="mention",
            title="Personal notification",
            body="Should be marked read",
            is_read=False,
        )
        shared_notification = Notification(
            workspace_id=workspace_id,
            user_id=None,
            type="mention",
            title="Workspace-wide notification",
            body="Should remain unread",
            is_read=False,
        )
        db_session.add_all([personal_notification, shared_notification])
        db_session.commit()
        db_session.refresh(personal_notification)
        db_session.refresh(shared_notification)

        response = client.put("/v1/notifications/read-all")

        assert response.status_code == 200
        db_session.refresh(personal_notification)
        db_session.refresh(shared_notification)
        assert personal_notification.is_read is True
        assert shared_notification.is_read is False


class TestWebhookSecurity:
    def test_test_webhook_revalidates_stored_target_url(self, client, db_session):
        payload = _register_owner(client)
        workspace_id = payload["workspace"]["id"]

        webhook = WebhookEndpoint(
            workspace_id=workspace_id,
            target_url="http://localhost:9000/hook",
            signing_secret="test-secret",
            event_types=["webhook.test"],
            is_active=True,
        )
        db_session.add(webhook)
        db_session.commit()
        db_session.refresh(webhook)

        response = client.post(f"/v1/webhooks/{webhook.id}/test", json={"event_type": "webhook.test"})

        assert response.status_code == 422
        assert response.json()["detail"] == "Internal URLs are not allowed."
