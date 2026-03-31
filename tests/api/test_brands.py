"""API tests for brand profile endpoints."""
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
def authed_with_project(client):
    reg = client.post("/v1/auth/register", json={
        "email": "brand@example.com",
        "password": "strongpass123",
        "full_name": "Brand User",
        "workspace_name": "Brand WS",
    })
    token = reg.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    proj = client.post("/v1/projects", json={"name": "Brand Project", "description": ""})
    return client, proj.json()["id"]


class TestBrandProfile:
    def test_get_brand_initially_none(self, authed_with_project):
        client, pid = authed_with_project
        resp = client.get(f"/v1/brand/{pid}")
        # Brand may not exist yet — either 404 or null brand is acceptable
        assert resp.status_code in (200, 404)

    def test_update_brand_profile(self, authed_with_project):
        client, pid = authed_with_project
        resp = client.put(f"/v1/brand/{pid}", json={
            "brand_name": "TestBrand",
            "website_url": "https://example.com",
            "summary": "A test brand",
            "voice_notes": "Professional",
        })
        assert resp.status_code == 200
        assert resp.json()["brand_name"] == "TestBrand"

    def test_update_brand_twice(self, authed_with_project):
        client, pid = authed_with_project
        client.put(f"/v1/brand/{pid}", json={"brand_name": "First", "summary": "v1"})
        resp = client.put(f"/v1/brand/{pid}", json={"brand_name": "Second", "summary": "v2"})
        assert resp.status_code == 200
        assert resp.json()["brand_name"] == "Second"
