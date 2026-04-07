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
from tests.conftest import _create_test_user, _make_test_token, _mock_verify_supabase_jwt

from app.db.models import AccountUser, Membership, Workspace
from app.db.session import get_db
from app.main import app
from app.services.product.supabase_auth import SupabaseAuthError


@pytest.fixture
def client(db_session):
    """Provide a FastAPI TestClient with DB + Supabase JWT mocked."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db

    with patch(
        "app.api.v1.deps.verify_supabase_jwt",
        side_effect=_mock_verify_supabase_jwt,
    ):
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

    @patch("app.api.v1.routes.auth.sign_up")
    def test_register_links_existing_legacy_user(self, mock_signup, client, db_session):
        legacy_user, workspace = _create_legacy_local_user(
            db_session,
            "legacy-register@example.com",
            "Legacy Register",
            "Legacy Workspace",
        )
        supabase_uid = str(uuid.uuid4())
        mock_signup.return_value = {
            "access_token": _make_test_token(supabase_uid),
            "refresh_token": f"refresh-{supabase_uid}",
            "user": {
                "id": supabase_uid,
                "email": legacy_user.email,
                "email_confirmed_at": "2025-01-01T00:00:00Z",
                "user_metadata": {"full_name": "Legacy Register"},
            },
        }

        resp = client.post("/v1/auth/register", json={
            "email": legacy_user.email,
            "password": "strongpass123",
            "full_name": "Legacy Register",
            "workspace_name": "Ignored New Workspace",
        })

        assert resp.status_code == 201
        data = resp.json()
        assert data["user"]["id"] == legacy_user.id
        assert data["user"]["supabase_user_id"] == supabase_uid
        assert data["workspace"]["id"] == workspace.id

        db_session.refresh(legacy_user)
        assert legacy_user.supabase_user_id == supabase_uid

    @patch("app.api.v1.routes.auth.sign_in_with_password")
    @patch("app.api.v1.routes.auth.sign_up")
    def test_register_links_legacy_user_when_supabase_user_already_exists(
        self,
        mock_signup,
        mock_signin,
        client,
        db_session,
    ):
        legacy_user, workspace = _create_legacy_local_user(
            db_session,
            "legacy-existing@example.com",
            "Legacy Existing",
            "Legacy Existing Workspace",
        )
        supabase_uid = str(uuid.uuid4())
        mock_signup.side_effect = SupabaseAuthError(422, "User already registered")
        mock_signin.return_value = {
            "access_token": _make_test_token(supabase_uid),
            "refresh_token": f"refresh-{supabase_uid}",
            "user": {
                "id": supabase_uid,
                "email": legacy_user.email,
                "email_confirmed_at": "2025-01-01T00:00:00Z",
                "user_metadata": {"full_name": "Legacy Existing"},
            },
        }

        resp = client.post("/v1/auth/register", json={
            "email": legacy_user.email,
            "password": "strongpass123",
            "full_name": "Legacy Existing",
            "workspace_name": "Ignored Existing Workspace",
        })

        assert resp.status_code == 201
        data = resp.json()
        assert data["user"]["id"] == legacy_user.id
        assert data["user"]["supabase_user_id"] == supabase_uid
        assert data["workspace"]["id"] == workspace.id


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

    def test_me_backfills_existing_legacy_user(self, client, db_session):
        legacy_user, workspace = _create_legacy_local_user(
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
                "email": legacy_user.email,
                "role": "authenticated",
            },
        ):
            resp = client.get("/v1/auth/me", headers={"Authorization": "Bearer test-token"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["id"] == legacy_user.id
        assert data["workspace"]["id"] == workspace.id

        db_session.refresh(legacy_user)
        assert legacy_user.supabase_user_id == supabase_uid


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
