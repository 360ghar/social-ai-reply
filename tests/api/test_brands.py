"""API tests for brand profile endpoints."""
import pytest


@pytest.fixture
def authed_with_project(authed_client):
    client, _ = authed_client
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
