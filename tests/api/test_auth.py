"""API tests for auth endpoints with Supabase integration.

These tests use mocked Supabase JWT verification (see conftest.py).
Auth endpoints that call Supabase directly (register) are tested
with mocked supabase_auth service functions.
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from tests.conftest import _create_test_user, _make_test_token

from app.db.models import AccountUser
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
        assert user.supabase_user_id is not None

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

    def test_register_rejects_existing_email(self, client, db_session):
        """Registration must reject emails that already exist locally."""
        _create_test_user(db_session, "existing@example.com", "Existing User", "Existing WS")

        resp = client.post("/v1/auth/register", json={
            "email": "existing@example.com",
            "password": "strongpass123",
            "full_name": "Existing User",
            "workspace_name": "New Workspace",
        })

        assert resp.status_code == 409


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

    def test_me_returns_404_for_unknown_user(self, client, db_session):
        """When a JWT is valid but no local user exists, /auth/me should return
        404 with 'no_local_account' to signal the OAuth setup flow."""
        supabase_uid = str(uuid.uuid4())

        with patch(
            "app.api.v1.routes.auth.verify_supabase_jwt",
            return_value={
                "sub": supabase_uid,
                "aud": "authenticated",
                "exp": 9999999999,
                "iat": 1000000000,
                "email": "unknown@example.com",
                "role": "authenticated",
            },
        ):
            resp = client.get("/v1/auth/me", headers={"Authorization": "Bearer test-token"})

        assert resp.status_code == 404
        assert resp.json()["detail"] == "no_local_account"


class TestOAuthComplete:
    def test_oauth_complete_creates_user_and_workspace(self, client, db_session):
        supabase_uid = str(uuid.uuid4())

        with patch(
            "app.api.v1.routes.auth.verify_supabase_jwt",
            return_value={
                "sub": supabase_uid,
                "aud": "authenticated",
                "exp": 9999999999,
                "iat": 1000000000,
                "email": "oauth@example.com",
                "role": "authenticated",
                "user_metadata": {"full_name": "OAuth User"},
            },
        ):
            resp = client.post(
                "/v1/auth/oauth-complete",
                json={"workspace_name": "OAuth Workspace"},
                headers={"Authorization": "Bearer test-token"},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["user"]["email"] == "oauth@example.com"
        assert data["user"]["supabase_user_id"] == supabase_uid
        assert data["workspace"]["name"] == "OAuth Workspace"

        user = db_session.scalar(select(AccountUser).where(AccountUser.email == "oauth@example.com"))
        assert user is not None
        assert user.supabase_user_id == supabase_uid
        assert user.full_name == "OAuth User"

    def test_oauth_complete_rejects_duplicate_email(self, client, db_session):
        """OAuth complete should reject if email is already taken by another account."""
        _create_test_user(db_session, "taken@example.com", "Taken User", "Taken WS")
        supabase_uid = str(uuid.uuid4())

        with patch(
            "app.api.v1.routes.auth.verify_supabase_jwt",
            return_value={
                "sub": supabase_uid,
                "aud": "authenticated",
                "exp": 9999999999,
                "iat": 1000000000,
                "email": "taken@example.com",
                "role": "authenticated",
                "user_metadata": {"full_name": "Another User"},
            },
        ):
            resp = client.post(
                "/v1/auth/oauth-complete",
                json={"workspace_name": "New WS"},
                headers={"Authorization": "Bearer test-token"},
            )

        assert resp.status_code == 409

    def test_oauth_complete_requires_auth(self, client):
        resp = client.post("/v1/auth/oauth-complete", json={"workspace_name": "Test WS"})
        assert resp.status_code == 401

    def test_oauth_complete_requires_workspace_name(self, client, db_session):
        supabase_uid = str(uuid.uuid4())

        with patch(
            "app.api.v1.routes.auth.verify_supabase_jwt",
            return_value={
                "sub": supabase_uid,
                "aud": "authenticated",
                "exp": 9999999999,
                "iat": 1000000000,
                "email": "test@example.com",
                "role": "authenticated",
            },
        ):
            resp = client.post(
                "/v1/auth/oauth-complete",
                json={},
                headers={"Authorization": "Bearer test-token"},
            )

        assert resp.status_code == 422


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
    def test_me_rejects_deactivated_user(self, client, db_session):
        """Deactivated users must not be able to access /auth/me."""
        data = _create_test_user(db_session, "deactivated@example.com", "Deactivated", "Deactivated WS")
        user = db_session.scalar(select(AccountUser).where(AccountUser.email == "deactivated@example.com"))
        user.is_active = False
        db_session.add(user)
        db_session.commit()

        resp = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
        assert resp.status_code == 404
