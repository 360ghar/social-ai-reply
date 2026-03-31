"""API tests for auth endpoints — register, login, me."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db


@pytest.fixture
def client(db_session):
    """Provide a FastAPI TestClient with DB dependency overridden."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestRegister:
    def test_register_success(self, client):
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

    def test_register_duplicate_email(self, client):
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


class TestLogin:
    def test_login_success(self, client):
        client.post("/v1/auth/register", json={
            "email": "login@example.com",
            "password": "strongpass123",
            "full_name": "Login User",
            "workspace_name": "Login WS",
        })
        resp = client.post("/v1/auth/login", json={
            "email": "login@example.com",
            "password": "strongpass123",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client):
        client.post("/v1/auth/register", json={
            "email": "wrong@example.com",
            "password": "strongpass123",
            "full_name": "Wrong User",
            "workspace_name": "Wrong WS",
        })
        resp = client.post("/v1/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrong-password",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "whatever",
        })
        assert resp.status_code == 401


class TestMe:
    def test_me_with_valid_token(self, client):
        reg = client.post("/v1/auth/register", json={
            "email": "me@example.com",
            "password": "strongpass123",
            "full_name": "Me User",
            "workspace_name": "Me WS",
        })
        token = reg.json()["access_token"]
        resp = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["user"]["email"] == "me@example.com"

    def test_me_without_token(self, client):
        resp = client.get("/v1/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token(self, client):
        # Invalid tokens should return 401 regardless of specific JWT error
        resp = client.get("/v1/auth/me", headers={"Authorization": "Bearer invalid-token-here"})
        assert resp.status_code == 401
