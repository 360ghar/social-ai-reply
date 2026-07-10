"""E2E test for the tweet suggestion + scheduling feature.

Tests the full lifecycle against the mock Supabase client:
1. POST generate suggestions -> creates pending suggestions
2. GET list suggestions -> returns them
3. PATCH approve -> sets status=approved + scheduled_at
4. POST scheduler/run (future time) -> 0 published
5. Manual past-time update -> scheduler attempts publish
6. PATCH reject -> sets status=rejected
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db.tables.tweet_suggestions import (
    bulk_create_suggestions,
    create_suggestion,
    list_suggestions,
    list_suggestions_ready_to_publish,
    update_suggestion,
)
from app.db.tables.tweet_suggestions import update_suggestion as db_update
from app.main import app

# Fixtures


@pytest.fixture(autouse=True)
def register_tweet_suggestions_table(mock_supabase):
    """Add tweet_suggestions table to the mock Supabase."""
    mock_supabase._tables["tweet_suggestions"] = []
    yield


@pytest.fixture(autouse=True)
def stub_x_publisher():
    """Prevent real X API calls during scheduler test."""
    with patch("app.services.product.tweet_scheduler.XPublisher") as mock:
        instance = mock.return_value
        instance.publish_thread.return_value = [{"id": "test_tweet_id", "text": "test content"}]
        yield mock


@pytest.fixture(autouse=True)
def stub_instagram_publisher():
    """Prevent real Instagram Graph API calls during scheduler test."""
    with patch("app.services.product.tweet_scheduler.InstagramPublisher") as mock:
        instance = mock.return_value
        instance.publish_post.return_value = {"id": "test_ig_media_id"}
        yield mock


@pytest.fixture(autouse=True)
def stub_linkedin_publisher():
    """Prevent real LinkedIn API calls during scheduler test."""
    with patch("app.services.product.tweet_scheduler.LinkedInPublisher") as mock:
        instance = mock.return_value
        instance.publish_post.return_value = {"id": "test_linkedin_post_id"}
        yield mock


@pytest.fixture(autouse=True)
def stub_llm():
    """Stub the LLM so tests are deterministic and fast."""
    fake_suggestions = [
        {"content": "5 industry trends shaping 2026 - which one surprised you most?"},
        {"content": "We just shipped a major update. Here is what changed and why it matters."},
        {"content": "Thread: 3 mistakes we made building our product so you don't repeat them."},
        {"content": "A new Instagram caption about visual storytelling #content #marketing #growth"},
        {"content": "Save this Instagram tip for later! #socialmedia #tips #community"},
        {"content": "A professional LinkedIn post about industry insights.\n\nWhat do you think?"},
        {"content": "LinkedIn thought leadership: 3 trends shaping our industry in 2026."},
    ]
    with patch("app.services.product.tweet_suggestion_service.LLMService") as mock:
        instance = mock.return_value
        instance.is_configured = True
        instance.call_json.return_value = fake_suggestions
        yield mock


@pytest.fixture
def authed_client(mock_supabase):
    """Create authenticated test client (same pattern as conftest)."""
    from app.api.v1.deps import get_current_user, get_current_workspace
    from app.api.v1.deps import get_supabase as deps_get_supabase
    from tests.conftest import _create_test_user

    user_data_dict = _create_test_user(mock_supabase, "e2e@test.local", "E2E Tester", "E2E Workspace")
    token = user_data_dict["access_token"]

    def override_get_supabase():
        try:
            yield mock_supabase
        finally:
            pass

    def override_get_current_user():
        return user_data_dict["user"]

    def override_get_current_workspace():
        return user_data_dict["workspace"]

    app.dependency_overrides.clear()
    app.dependency_overrides[deps_get_supabase] = override_get_supabase
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_workspace] = override_get_current_workspace

    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    yield client, user_data_dict
    app.dependency_overrides.clear()


# Test: DB layer


class TestTweetSuggestionsTable:
    """Direct DB table operation tests."""

    def test_create_and_list(self, mock_supabase):
        ws_id = 1
        record = {
            "workspace_id": ws_id,
            "content": "Test tweet content",
            "suggested_for_date": "2026-07-10",
            "status": "pending",
            "platform": "twitter",
        }
        created = create_suggestion(mock_supabase, record)
        assert created["id"] is not None
        assert created["content"] == "Test tweet content"
        assert created["status"] == "pending"

        rows = list_suggestions(mock_supabase, ws_id)
        assert len(rows) == 1

    def test_bulk_create(self, mock_supabase):
        ws_id = 1
        records = [
            {"workspace_id": ws_id, "content": f"Tweet {i}", "suggested_for_date": f"2026-07-{10+i}", "status": "pending", "platform": "twitter"}
            for i in range(3)
        ]
        created = bulk_create_suggestions(mock_supabase, records)
        assert len(created) == 3

    def test_update_status(self, mock_supabase):
        ws_id = 1
        record = {"workspace_id": ws_id, "content": "Approve me", "suggested_for_date": "2026-07-10", "status": "pending", "platform": "twitter"}
        created = create_suggestion(mock_supabase, record)

        updated = update_suggestion(mock_supabase, created["id"], {"status": "approved", "scheduled_at": "2026-07-10T09:00:00+00:00"})
        assert updated["status"] == "approved"
        assert updated["scheduled_at"] is not None

    def test_ready_to_publish(self, mock_supabase):
        ws_id = 1
        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        future = (datetime.now(UTC) + timedelta(hours=24)).isoformat()

        create_suggestion(mock_supabase, {"workspace_id": ws_id, "content": "Due tweet", "suggested_for_date": "2026-07-10", "status": "approved", "platform": "x", "scheduled_at": past})

        create_suggestion(mock_supabase, {"workspace_id": ws_id, "content": "Future tweet", "suggested_for_date": "2026-07-11", "status": "approved", "platform": "x", "scheduled_at": future})

        due = list_suggestions_ready_to_publish(mock_supabase, ws_id)
        assert len(due) == 1
        assert due[0]["content"] == "Due tweet"


# Test: API layer (full E2E)


class TestTweetSuggestionsAPI:
    """Full E2E tests via HTTP against the mock infrastructure.
    Runs as a single sequential method because each fixture gets
    a fresh function-scoped mock_supabase.
    """

    def test_full_lifecycle(self, authed_client, stub_x_publisher, mock_supabase):
        """Run the full generate -> list -> approve -> scheduler -> reject flow."""
        client, user_data = authed_client
        ws = user_data["workspace"]

        # (1) Generate
        payload = {"days": 3, "suggestions_per_day": 1, "platform": "twitter"}
        resp = client.post("/v1/suggestions/generate", json=payload)
        body = resp.json()
        print(f"Step 1 (generate): {resp.status_code}")
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {body}"
        assert body["generated_count"] == 3
        assert len(body["suggestions"]) == 3
        for s in body["suggestions"]:
            assert s["status"] == "pending"
            assert s["workspace_id"] == ws["id"]
            assert s["platform"] in ("x", "twitter"), f"Expected 'x', got '{s['platform']}'"
        suggestions = body["suggestions"]

        # (2) List pending
        resp = client.get("/v1/suggestions", params={"status": "pending"})
        body = resp.json()
        print(f"Step 2 (list): {resp.status_code} [{len(body)} items]")
        assert resp.status_code == 200
        assert len(body) >= 3
        for s in body:
            assert s["status"] == "pending"

        # (3) Approve one
        target = suggestions[0]
        resp = client.patch(f"/v1/suggestions/{target['id']}/approve", json={})
        body = resp.json()
        print(f"Step 3 (approve): {resp.status_code}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {body}"
        assert body["status"] == "approved"
        assert body["scheduled_at"] is not None
        approved = body

        # (4) Scheduler (future time) -> no-op
        resp = client.post("/v1/suggestions/scheduler/run")
        body = resp.json()
        print(f"Step 4 (scheduler, future): {resp.status_code}")
        assert resp.status_code == 200
        assert body["attempted"] == 0
        assert body["published"] == 0
        assert body["failed"] == 0

        # (5) Manually reschedule to past time via DB, then publish
        past_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        updated = db_update(mock_supabase, approved["id"], {"scheduled_at": past_time})
        assert updated is not None
        print(f"Step 5a (db reschedule past): scheduled_at={updated['scheduled_at']}")

        with patch("app.services.product.tweet_scheduler.get_x_token", return_value="mock_token"):
            resp = client.post("/v1/suggestions/scheduler/run")
            body = resp.json()
            print(f"Step 5b (scheduler, past): {resp.status_code}")
            assert resp.status_code == 200
            assert body["attempted"] > 0, f"Expected >0 attempts, got {body}"
            assert body["published"] > 0, f"Expected >0 published, got {body}"

        # (6) Reject a pending suggestion
        resp = client.post("/v1/suggestions/generate", json={"days": 1, "suggestions_per_day": 1, "platform": "twitter"})
        new_suggestions = resp.json()["suggestions"]
        assert len(new_suggestions) > 0
        target_id = new_suggestions[0]["id"]

        resp = client.patch(f"/v1/suggestions/{target_id}/reject", json={})
        body = resp.json()
        print(f"Step 6 (reject): {resp.status_code}")
        assert resp.status_code == 200
        assert body["status"] == "rejected"


class TestInstagramSuggestionLifecycle:
    """Full E2E lifecycle for Instagram suggestions."""

    @pytest.fixture(autouse=True)
    def stub_ig_token(self, mock_supabase):
        """Provide a mock Instagram token in integration_secrets."""
        mock_supabase._tables.setdefault("integration_secrets", [])
        mock_supabase._tables["integration_secrets"].append({
            "id": 100,
            "workspace_id": 1,
            "provider": "instagram",
            "label": "access_token",
            "encrypted_value": "mock-encrypted-ig-token",
        })
        mock_supabase._tables["integration_secrets"].append({
            "id": 101,
            "workspace_id": 1,
            "provider": "instagram",
            "label": "business_account_id",
            "value": "17841400000000000",
        })
        yield

    def test_instagram_generate_approve_schedule(self, authed_client, mock_supabase):
        """Instagram: generate, approve, schedule, and publish via scheduler."""
        client, user_data = authed_client

        # Generate
        payload = {"days": 2, "suggestions_per_day": 1, "platform": "instagram"}
        resp = client.post("/v1/suggestions/generate", json=payload)
        body = resp.json()
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {body}"
        assert body["generated_count"] == 2
        for s in body["suggestions"]:
            assert s["platform"] == "instagram"
        suggestions = body["suggestions"]

        # Approve
        resp = client.patch(f"/v1/suggestions/{suggestions[0]['id']}/approve", json={})
        body = resp.json()
        assert resp.status_code == 200
        assert body["status"] == "approved"
        approved_id = body["id"]

        # Reschedule to past and publish
        past_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        db_update(mock_supabase, approved_id, {"scheduled_at": past_time})

        with (
            patch("app.services.product.tweet_scheduler.get_instagram_token", return_value="mock_ig_token"),
            patch("app.services.product.tweet_scheduler.get_instagram_business_account_id", return_value="17841400000000000"),
        ):
            resp = client.post("/v1/suggestions/scheduler/run", params={"platform": "instagram"})
            body = resp.json()
            assert resp.status_code == 200
            assert body["attempted"] > 0, f"Expected >0 attempts, got {body}"
            assert body["published"] > 0, f"Expected >0 published, got {body}"

        # Verify published
        published = next(
            s for s in mock_supabase._tables["tweet_suggestions"]
            if s["id"] == approved_id
        )
        assert published["status"] == "published"


class TestLinkedInSuggestionLifecycle:
    """Full E2E lifecycle for LinkedIn suggestions."""

    @pytest.fixture(autouse=True)
    def stub_li_token(self, mock_supabase):
        """Provide a mock LinkedIn token in integration_secrets."""
        mock_supabase._tables.setdefault("integration_secrets", [])
        mock_supabase._tables["integration_secrets"].append({
            "id": 200,
            "workspace_id": 1,
            "provider": "linkedin",
            "label": "access_token",
            "encrypted_value": "mock-encrypted-li-token",
        })
        mock_supabase._tables["integration_secrets"].append({
            "id": 201,
            "workspace_id": 1,
            "provider": "linkedin",
            "label": "author_urn",
            "value": "urn:li:organization:123456",
        })
        yield

    def test_linkedin_generate_approve_schedule(self, authed_client, mock_supabase):
        """LinkedIn: generate, approve, schedule, and publish via scheduler."""
        client, user_data = authed_client

        # Generate
        payload = {"days": 2, "suggestions_per_day": 1, "platform": "linkedin"}
        resp = client.post("/v1/suggestions/generate", json=payload)
        body = resp.json()
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {body}"
        assert body["generated_count"] == 2
        for s in body["suggestions"]:
            assert s["platform"] == "linkedin"
        suggestions = body["suggestions"]

        # Approve
        resp = client.patch(f"/v1/suggestions/{suggestions[0]['id']}/approve", json={})
        body = resp.json()
        assert resp.status_code == 200
        assert body["status"] == "approved"
        approved_id = body["id"]

        # Reschedule to past and publish
        past_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        db_update(mock_supabase, approved_id, {"scheduled_at": past_time})

        with (
            patch("app.services.product.tweet_scheduler.get_linkedin_token", return_value="mock_li_token"),
            patch("app.services.product.tweet_scheduler.get_linkedin_author_urn", return_value="urn:li:organization:123456"),
        ):
            resp = client.post("/v1/suggestions/scheduler/run", params={"platform": "linkedin"})
            body = resp.json()
            assert resp.status_code == 200
            assert body["attempted"] > 0, f"Expected >0 attempts, got {body}"
            assert body["published"] > 0, f"Expected >0 published, got {body}"

        # Verify published
        published = next(
            s for s in mock_supabase._tables["tweet_suggestions"]
            if s["id"] == approved_id
        )
        assert published["status"] == "published"


class TestCrossPlatformFiltering:
    """Verify platform filtering in list + scheduler queries."""

    def test_platform_specific_listing(self, authed_client, mock_supabase):
        """Generate for multiple platforms and verify they're independently listable."""
        client, user_data = authed_client

        # Generate for all three platforms
        for plat in ("twitter", "instagram", "linkedin"):
            payload = {"days": 1, "suggestions_per_day": 1, "platform": plat}
            resp = client.post("/v1/suggestions/generate", json=payload)
            assert resp.status_code == 201

        # List by platform
        for plat in ("x", "instagram", "linkedin"):
            resp = client.get("/v1/suggestions", params={"platform": plat})
            body = resp.json()
            assert resp.status_code == 200
            assert len(body) == 1, f"Expected 1 {plat} suggestion, got {len(body)}"
            assert body[0]["platform"] == plat

        # List all (no filter) should return all 3
        resp = client.get("/v1/suggestions")
        body = resp.json()
        assert resp.status_code == 200
        assert len(body) == 3

    def test_ready_to_publish_per_platform(self, mock_supabase):
        """Verify list_suggestions_ready_to_publish filters by platform."""
        from app.db.tables.tweet_suggestions import list_suggestions_ready_to_publish

        ws_id = 1
        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()

        for plat in ("x", "instagram", "linkedin"):
            create_suggestion(mock_supabase, {
                "workspace_id": ws_id, "content": f"{plat} post",
                "suggested_for_date": "2026-07-10",
                "status": "approved", "platform": plat, "scheduled_at": past,
            })

        for plat in ("x", "instagram", "linkedin"):
            due = list_suggestions_ready_to_publish(mock_supabase, ws_id, platform=plat)
            assert len(due) == 1, f"Expected 1 due for {plat}, got {len(due)}"
            assert due[0]["platform"] == plat
