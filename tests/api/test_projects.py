"""API tests for projects and dashboard endpoints."""


class TestProjects:
    def test_dashboard_bootstraps_default_project_and_subscription(self, authed_client, mock_supabase):
        client, _ = authed_client
        # Clear any existing projects
        mock_supabase.table("projects").delete().execute()

        resp = client.get("/v1/dashboard")
        assert resp.status_code == 200

        payload = resp.json()
        assert len(payload["projects"]) == 1
        assert payload["projects"][0]["status"] == "active"
        assert payload["subscription"]["plan_code"]

    def test_create_project(self, authed_client):
        client, _ = authed_client
        resp = client.post("/v1/projects", json={
            "name": "Test Project",
            "description": "A test project",
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "Test Project"

    def test_list_projects(self, authed_client):
        client, _ = authed_client
        client.post("/v1/projects", json={"name": "P1", "description": ""})
        client.post("/v1/projects", json={"name": "P2", "description": ""})
        resp = client.get("/v1/projects")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_update_project(self, authed_client):
        client, _ = authed_client
        create = client.post("/v1/projects", json={"name": "Original", "description": ""})
        pid = create.json()["id"]
        resp = client.put(f"/v1/projects/{pid}", json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_delete_project(self, authed_client):
        client, _ = authed_client
        create = client.post("/v1/projects", json={"name": "ToDelete", "description": ""})
        pid = create.json()["id"]
        resp = client.delete(f"/v1/projects/{pid}")
        assert resp.status_code == 200

    def test_unauthenticated_access(self, client):
        resp = client.get("/v1/projects")
        assert resp.status_code == 401

    def test_auto_pipeline_list_bootstraps_default_project(self, authed_client, mock_supabase):
        client, _ = authed_client
        mock_supabase.table("projects").delete().execute()

        resp = client.get("/v1/auto-pipeline")
        assert resp.status_code == 200
        assert resp.json() == {"items": []}
