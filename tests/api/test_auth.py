"""API tests for auth endpoints with Supabase integration.

These tests use mocked Supabase JWT verification (see conftest.py).
Auth endpoints that call Supabase directly (register, login) are tested
with mocked supabase_auth service functions.
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from tests.conftest import _create_test_user, _make_test_token

from app.db.models import AccountUser, Membership, Workspace
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client(db_session):
    """Provide a FastAPI TestClient with DB override.

    Supabase JWT mocking is handled by the autouse ``mock_supabase_auth``
    fixture in conftest.py — no need to duplicate the patch here.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()


def _mock_supabase_signup(email, password, full_name):
    """Mock for supabase_auth.sign_up that returns a fake Supabase response."""
    uid = str(uuid.uuid4())
    return {
        "access_token": _make_test_token(uid),
        "refresh_token": f"refresh-{uid}",
        "user": {
            "id": uid,
            "email": email,
            "email_confirmed_at": "2025-01-01T00:00:00Z",
            "user_metadata": {"full_name": full_name},
        },
    }


def _mock_supabase_signin(email, password):
    """Mock for supabase_auth.sign_in_with_password."""
    # We need to look up the real supabase_user_id, but in mocked tests
    # we'll create the user first, so the test controls the ID.
    # This mock is only for the Supabase API call part.
    uid = str(uuid.uuid4())
    return {
        "access_token": _make_test_token(uid),
        "refresh_token": f"refresh-{uid}",
        "user": {
            "id": uid,
            "email": email,
            "email_confirmed_at": "2025-01-01T00:00:00Z",
            "user_metadata": {"full_name": "Test User"},
        },
    }


def _create_legacy_local_user(db_session, email: str, full_name: str, workspace_name: str) -> tuple[AccountUser, Workspace]:
    _create_test_user(db_session, email, full_name, workspace_name)
    user = db_session.scalar(select(AccountUser).where(AccountUser.email == email))
    assert user is not None
    user.supabase_user_id = None
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    workspace = db_session.scalar(
        select(Workspace).join(Membership).where(Membership.user_id == user.id).order_by(Workspace.id.asc())
    )
    assert workspace is not None
    return user, workspace


class TestRegister:
    @patch("app.api.v1.routes.auth.sign_up", side_effect=_mock_supabase_signup)
    def test_register_success(self, mock_signup, client, db_session):
        resp = client.post("/v1/auth/register", json={
            "email": "new@example.com",
            "password": "strongpass123",
            "full_name": "New User",
            "workspace_name": "New WS",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "new@example.com"
        assert "supabase_user_id" in data["user"]
        user = db_session.scalar(select(AccountUser).where(AccountUser.email == "new@example.com"))
        assert user is not None
        assert user.password_hash is not None
        assert user.password_hash.startswith("supabase-managed:")

    @patch("app.api.v1.routes.auth.sign_up", side_effect=_mock_supabase_signup)
    def test_register_duplicate_email(self, mock_signup, client):
        payload = {
            "email": "dup@example.com",
            "password": "strongpass123",
            "full_name": "Dup User",
            "workspace_name": "Dup WS",
        }
        client.post("/v1/auth/register", json=payload)
        resp = client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 409

    def test_register_missing_fields(self, client):
        resp = client.post("/v1/auth/register", json={"email": "a@b.com"})
        assert resp.status_code == 422

    def test_register_rejects_existing_legacy_email(self, client, db_session):
        """Registration must reject emails that already exist locally,
        even for legacy users without a supabase_user_id. They should use
        /auth/login to link their Supabase identity instead."""
        _create_legacy_local_user(
            db_session,
            "legacy-register@example.com",
            "Legacy Register",
            "Legacy Workspace",
        )

        resp = client.post("/v1/auth/register", json={
            "email": "legacy-register@example.com",
            "password": "strongpass123",
            "full_name": "Legacy Register",
            "workspace_name": "New Workspace",
        })

        assert resp.status_code == 409
        assert "sign in" in resp.json()["detail"].lower()


class TestLogin:
    @patch("app.api.v1.routes.auth.sign_in_with_password")
    def test_login_backfills_existing_legacy_user(self, mock_signin, client, db_session):
        legacy_user, workspace = _create_legacy_local_user(
            db_session,
            "legacy-login@example.com",
            "Legacy Login",
            "Legacy Login Workspace",
        )
        supabase_uid = str(uuid.uuid4())
        mock_signin.return_value = {
            "access_token": _make_test_token(supabase_uid),
            "refresh_token": f"refresh-{supabase_uid}",
            "user": {
                "id": supabase_uid,
                "email": legacy_user.email,
                "email_confirmed_at": "2025-01-01T00:00:00Z",
                "user_metadata": {"full_name": "Legacy Login"},
            },
        }

        resp = client.post("/v1/auth/login", json={
            "email": legacy_user.email,
            "password": "strongpass123",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["id"] == legacy_user.id
        assert data["user"]["supabase_user_id"] == supabase_uid
        assert data["workspace"]["id"] == workspace.id

        db_session.refresh(legacy_user)
        assert legacy_user.supabase_user_id == supabase_uid


class TestMe:
    def test_me_with_valid_token(self, client, db_session):
        data = _create_test_user(db_session, "me@example.com", "Me User", "Me WS")
        token = data["access_token"]
        resp = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["user"]["email"] == "me@example.com"

    def test_me_without_token(self, client):
        resp = client.get("/v1/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token(self, client):
        resp = client.get("/v1/auth/me", headers={"Authorization": "Bearer invalid-token-here"})
        assert resp.status_code == 401

    def test_me_rejects_unlinked_legacy_user(self, client, db_session):
        """Legacy users without a supabase_user_id cannot use /auth/me.

        They must link their account via /auth/login first. The auth
        dependency no longer auto-backfills legacy users by email.
        """
        _create_legacy_local_user(
            db_session,
            "legacy-me@example.com",
            "Legacy Me",
            "Legacy Me Workspace",
        )
        supabase_uid = str(uuid.uuid4())

        with patch(
            "app.api.v1.deps.verify_supabase_jwt",
            return_value={
                "sub": supabase_uid,
                "aud": "authenticated",
                "exp": 9999999999,
                "iat": 1000000000,
                "email": "legacy-me@example.com",
                "role": "authenticated",
            },
        ):
            resp = client.get("/v1/auth/me", headers={"Authorization": "Bearer test-token"})

        assert resp.status_code == 401


class TestLogout:
    @patch("app.api.v1.routes.auth.sign_out")
    def test_logout_revokes_current_token(self, mock_sign_out, client, db_session):
        data = _create_test_user(db_session, "logout@example.com", "Logout User", "Logout WS")
        token = data["access_token"]

        resp = client.post("/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        mock_sign_out.assert_called_once_with(token)

        follow_up = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert follow_up.status_code == 401
        assert follow_up.json()["detail"] == "Session expired. Please sign in again."

    def test_logout_requires_auth(self, client):
        resp = client.post("/v1/auth/logout")
        assert resp.status_code == 401


class TestDeactivatedUser:
    @patch("app.api.v1.routes.auth.sign_in_with_password")
    def test_login_rejects_deactivated_user(self, mock_signin, client, db_session):
        """Deactivated users must not be able to log in."""
        _create_test_user(db_session, "deactivated@example.com", "Deactivated", "Deactivated WS")
        user = db_session.scalar(select(AccountUser).where(AccountUser.email == "deactivated@example.com"))
        supabase_uid = user.supabase_user_id
        user.is_active = False
        db_session.add(user)
        db_session.commit()

        mock_signin.return_value = {
            "access_token": _make_test_token(supabase_uid),
            "refresh_token": f"refresh-{supabase_uid}",
            "user": {
                "id": supabase_uid,
                "email": "deactivated@example.com",
                "email_confirmed_at": "2025-01-01T00:00:00Z",
                "user_metadata": {"full_name": "Deactivated"},
            },
        }

        resp = client.post("/v1/auth/login", json={
            "email": "deactivated@example.com",
            "password": "strongpass123",
        })
        assert resp.status_code == 401

    @patch("app.api.v1.routes.auth.refresh_session")
    def test_refresh_rejects_deactivated_user(self, mock_refresh, client, db_session):
        """Deactivated users must not be able to refresh tokens."""
        _create_test_user(db_session, "deactivated-refresh@example.com", "Deactivated", "Deactivated WS")
        user = db_session.scalar(select(AccountUser).where(AccountUser.email == "deactivated-refresh@example.com"))
        supabase_uid = user.supabase_user_id
        user.is_active = False
        db_session.add(user)
        db_session.commit()

        mock_refresh.return_value = {
            "access_token": _make_test_token(supabase_uid),
            "refresh_token": f"refresh-new-{supabase_uid}",
            "user": {
                "id": supabase_uid,
                "email": "deactivated-refresh@example.com",
                "email_confirmed_at": "2025-01-01T00:00:00Z",
                "user_metadata": {"full_name": "Deactivated"},
            },
        }

        resp = client.post("/v1/auth/refresh", json={"refresh_token": "some-refresh-token"})
        assert resp.status_code == 401
