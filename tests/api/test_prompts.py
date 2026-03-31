"""API tests for prompt template endpoints."""
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
        "email": "prompts@example.com",
        "password": "strongpass123",
        "full_name": "Prompt User",
        "workspace_name": "Prompt WS",
    })
    token = reg.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    proj = client.post("/v1/projects", json={"name": "Prompt Project", "description": ""})
    return client, proj.json()["id"]


class TestPrompts:
    def test_default_prompts_seeded(self, authed_with_project):
        client, pid = authed_with_project
        resp = client.get(f"/v1/prompts?project_id={pid}")
        assert resp.status_code == 200
        prompts = resp.json()
        assert len(prompts) >= 3
        types = {p["prompt_type"] for p in prompts}
        assert "reply" in types
        assert "post" in types

    def test_create_custom_prompt(self, authed_with_project):
        client, pid = authed_with_project
        resp = client.post(f"/v1/prompts?project_id={pid}", json={
            "prompt_type": "reply",
            "name": "Custom Reply",
            "system_prompt": "You write helpful and grounded replies that assist the user.",
            "instructions": "Answer the question directly.",
            "is_default": False,
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "Custom Reply"

    def test_update_prompt(self, authed_with_project):
        client, pid = authed_with_project
        prompts = client.get(f"/v1/prompts?project_id={pid}").json()
        prompt_id = prompts[0]["id"]
        resp = client.put(f"/v1/prompts/{prompt_id}", json={
            "prompt_type": prompts[0]["prompt_type"],
            "name": "Updated Name",
            "system_prompt": "You are an updated system prompt for writing great replies.",
            "instructions": "Updated instructions here.",
            "is_default": False,
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    def test_delete_prompt(self, authed_with_project):
        client, pid = authed_with_project
        create = client.post(f"/v1/prompts?project_id={pid}", json={
            "prompt_type": "analysis",
            "name": "To Delete",
            "system_prompt": "You analyze opportunities with clarity and no fluff at all times.",
        })
        assert create.status_code == 201, f"Create failed: {create.text}"
        prompt_id = create.json()["id"]
        resp = client.delete(f"/v1/prompts/{prompt_id}")
        assert resp.status_code == 200

    def test_list_prompts_requires_project_id(self, authed_with_project):
        client, _ = authed_with_project
        resp = client.get("/v1/prompts")
        assert resp.status_code == 422  # project_id is required
