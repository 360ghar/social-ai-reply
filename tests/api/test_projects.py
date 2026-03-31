"""API tests for projects and dashboard endpoints."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def authed_client(client):
    resp = client.post("/v1/auth/register", json={
        "email": "project@example.com",
        "password": "strongpass123",
        "full_name": "Project User",
        "workspace_name": "Project WS",
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


class TestProjects:
    def test_create_project(self, authed_client):
        resp = authed_client.post("/v1/projects", json={
            "name": "Test Project",
            "description": "A test project",
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "Test Project"

    def test_list_projects(self, authed_client):
        authed_client.post("/v1/projects", json={"name": "P1", "description": ""})
        authed_client.post("/v1/projects", json={"name": "P2", "description": ""})
        resp = authed_client.get("/v1/projects")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_update_project(self, authed_client):
        create = authed_client.post("/v1/projects", json={"name": "Original", "description": ""})
        pid = create.json()["id"]
        resp = authed_client.put(f"/v1/projects/{pid}", json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_delete_project(self, authed_client):
        create = authed_client.post("/v1/projects", json={"name": "ToDelete", "description": ""})
        pid = create.json()["id"]
        resp = authed_client.delete(f"/v1/projects/{pid}")
        assert resp.status_code == 200

    def test_unauthenticated_access(self, client):
        resp = client.get("/v1/projects")
        assert resp.status_code == 401
