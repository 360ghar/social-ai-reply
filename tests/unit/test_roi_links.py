"""Unit tests for ROI attribution: UTM utils, tracked link helpers, and the public redirect."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException

from app.api.v1.routes.links import _hash_user_agent, _link_response, follow_tracked_link
from app.db.tables.tracked_links import count_clicks_for_links, get_roi_rollup, get_tracked_link_by_code
from app.utils.utm import append_utm, build_utm_params, generate_link_code

# ── Fake Supabase query/client stubs (conftest MockSupabaseClient lacks these tables) ──


class _Result:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class FakeQuery:
    def __init__(self, rows):
        self._rows = [dict(r) for r in rows]

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self._rows = [r for r in self._rows if r.get(column) == value]
        return self

    def in_(self, column, values):
        self._rows = [r for r in self._rows if r.get(column) in values]
        return self

    def order(self, *args, **kwargs):
        return self

    def execute(self):
        return _Result(list(self._rows))


class FakeDB:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return FakeQuery(self._tables.get(name, []))


# ── UTM building / merging ──


class TestBuildUtmParams:
    def test_basic_params(self):
        params = build_utm_params("my-project", None)
        assert params == {
            "utm_source": "reddit",
            "utm_medium": "community",
            "utm_campaign": "my-project",
        }

    def test_includes_opportunity_content(self):
        params = build_utm_params("my-project", 42)
        assert params["utm_content"] == "opp-42"

    def test_custom_platform(self):
        params = build_utm_params("my-project", None, platform="linkedin")
        assert params["utm_source"] == "linkedin"


class TestAppendUtm:
    def test_appends_to_bare_url(self):
        url = append_utm("https://example.com/page", {"utm_source": "reddit"})
        parts = urlsplit(url)
        assert parts.scheme == "https"
        assert parts.netloc == "example.com"
        assert parse_qs(parts.query) == {"utm_source": ["reddit"]}

    def test_preserves_existing_query_params(self):
        url = append_utm("https://example.com/page?ref=abc&x=1", {"utm_source": "reddit"})
        query = parse_qs(urlsplit(url).query)
        assert query["ref"] == ["abc"]
        assert query["x"] == ["1"]
        assert query["utm_source"] == ["reddit"]

    def test_overrides_existing_utm_params(self):
        url = append_utm(
            "https://example.com/page?utm_source=google&utm_campaign=old",
            {"utm_source": "reddit", "utm_campaign": "new"},
        )
        query = parse_qs(urlsplit(url).query)
        assert query["utm_source"] == ["reddit"]
        assert query["utm_campaign"] == ["new"]

    def test_does_not_double_encode(self):
        url = append_utm("https://example.com/page?q=a%20b", {"utm_source": "reddit"})
        query = parse_qs(urlsplit(url).query)
        assert query["q"] == ["a b"]
        assert "a%2520b" not in url

    def test_preserves_fragment_and_path(self):
        url = append_utm("https://example.com/a/b#section", {"utm_source": "reddit"})
        parts = urlsplit(url)
        assert parts.path == "/a/b"
        assert parts.fragment == "section"

    def test_empty_params_returns_url_unchanged(self):
        assert append_utm("https://example.com/page?x=1", {}) == "https://example.com/page?x=1"


class TestGenerateLinkCode:
    def test_length_is_eight(self):
        assert len(generate_link_code()) == 8

    def test_url_safe_characters(self):
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        for _ in range(50):
            assert set(generate_link_code()) <= allowed

    def test_codes_are_random(self):
        codes = {generate_link_code() for _ in range(200)}
        assert len(codes) == 200


# ── Table helpers ──


class TestTrackedLinkHelpers:
    def test_get_tracked_link_by_code(self):
        db = FakeDB({"tracked_links": [{"id": 1, "code": "abc12345", "destination_url": "https://x.com"}]})
        link = get_tracked_link_by_code(db, "abc12345")
        assert link is not None
        assert link["id"] == 1

    def test_get_tracked_link_by_code_missing(self):
        db = FakeDB({"tracked_links": []})
        assert get_tracked_link_by_code(db, "nope") is None

    def test_count_clicks_for_links(self):
        db = FakeDB(
            {
                "link_clicks": [
                    {"id": 1, "tracked_link_id": 1},
                    {"id": 2, "tracked_link_id": 1},
                    {"id": 3, "tracked_link_id": 2},
                    {"id": 4, "tracked_link_id": 99},  # not requested
                ]
            }
        )
        counts = count_clicks_for_links(db, [1, 2, 3])
        assert counts == {1: 2, 2: 1, 3: 0}

    def test_count_clicks_empty_input(self):
        db = MagicMock()
        assert count_clicks_for_links(db, []) == {}
        db.table.assert_not_called()


class TestRoiRollup:
    def _db(self):
        return FakeDB(
            {
                "tracked_links": [
                    {"id": 1, "project_id": 10, "code": "c1", "opportunity_id": 100},
                    {"id": 2, "project_id": 10, "code": "c2", "opportunity_id": 101},
                    {"id": 3, "project_id": 10, "code": "c3", "opportunity_id": None},
                    {"id": 4, "project_id": 99, "code": "c4", "opportunity_id": 100},  # other project
                ],
                "link_clicks": [
                    {"id": 1, "tracked_link_id": 1},
                    {"id": 2, "tracked_link_id": 1},
                    {"id": 3, "tracked_link_id": 2},
                    {"id": 4, "tracked_link_id": 4},  # other project's link
                ],
                "opportunities": [
                    {"id": 100, "subreddit_name": "saas", "buying_stage": "evaluation"},
                    {"id": 101, "subreddit_name": "startups", "buying_stage": "evaluation"},
                ],
            }
        )

    def test_aggregates_per_subreddit_and_stage(self):
        rows = get_roi_rollup(self._db(), 10)
        by_group = {(r["group_by"], r["key"]): r for r in rows}

        assert by_group[("subreddit", "saas")] == {
            "group_by": "subreddit", "key": "saas", "links": 1, "clicks": 2,
        }
        assert by_group[("subreddit", "startups")]["clicks"] == 1
        assert by_group[("subreddit", "unattributed")] == {
            "group_by": "subreddit", "key": "unattributed", "links": 1, "clicks": 0,
        }
        # Both attributed links share the same buying stage
        assert by_group[("buying_stage", "evaluation")] == {
            "group_by": "buying_stage", "key": "evaluation", "links": 2, "clicks": 3,
        }
        assert by_group[("buying_stage", "unattributed")]["links"] == 1

    def test_returns_empty_for_project_without_links(self):
        assert get_roi_rollup(self._db(), 12345) == []


# ── Public redirect handler ──


def _make_request(headers=None):
    request = MagicMock()
    request.headers = headers or {}
    return request


def _link_row(**overrides):
    row = {
        "id": 7,
        "project_id": 10,
        "code": "abc12345",
        "destination_url": "https://example.com/pricing",
        "opportunity_id": 42,
        "reply_draft_id": None,
        "utm_params": {"utm_source": "reddit", "utm_medium": "community", "utm_campaign": "proj"},
        "created_at": datetime.now(UTC).isoformat(),
    }
    row.update(overrides)
    return row


class TestFollowTrackedLink:
    def test_valid_code_redirects_and_logs_click(self):
        link = _link_row()
        request = _make_request({"referer": "https://reddit.com/r/saas", "user-agent": "Mozilla/5.0"})
        with (
            patch("app.api.v1.routes.links.get_tracked_link_by_code", return_value=link) as get_mock,
            patch("app.api.v1.routes.links.create_link_click") as click_mock,
        ):
            response = follow_tracked_link("abc12345", request, supabase=MagicMock())

        assert response.status_code == 302
        location = response.headers["location"]
        query = parse_qs(urlsplit(location).query)
        assert query["utm_source"] == ["reddit"]
        assert query["utm_campaign"] == ["proj"]
        assert location.startswith("https://example.com/pricing")

        get_mock.assert_called_once()
        click_mock.assert_called_once()
        click_data = click_mock.call_args[0][1]
        assert click_data["tracked_link_id"] == 7
        assert click_data["referrer"] == "https://reddit.com/r/saas"
        # Raw UA is never stored — only a 16-char sha256 prefix
        assert click_data["user_agent_hash"] == _hash_user_agent("Mozilla/5.0")
        assert len(click_data["user_agent_hash"]) == 16
        assert "Mozilla" not in click_data["user_agent_hash"]

    def test_unknown_code_raises_404(self):
        with (
            patch("app.api.v1.routes.links.get_tracked_link_by_code", return_value=None),
            pytest.raises(HTTPException) as exc_info,
        ):
            follow_tracked_link("missing0", _make_request(), supabase=MagicMock())
        assert exc_info.value.status_code == 404

    def test_click_log_failure_still_redirects(self):
        link = _link_row()
        with (
            patch("app.api.v1.routes.links.get_tracked_link_by_code", return_value=link),
            patch("app.api.v1.routes.links.create_link_click", side_effect=RuntimeError("db down")),
        ):
            response = follow_tracked_link("abc12345", _make_request(), supabase=MagicMock())
        assert response.status_code == 302

    def test_missing_user_agent_hashes_to_none(self):
        assert _hash_user_agent(None) is None
        assert _hash_user_agent("") is None


class TestLinkResponseBuilder:
    def test_short_path_and_tracked_url(self):
        response = _link_response(_link_row(), click_count=3)
        assert response.short_path == "/r/abc12345"
        assert response.click_count == 3
        query = parse_qs(urlsplit(response.tracked_url).query)
        assert query["utm_source"] == ["reddit"]

    def test_handles_null_utm_params(self):
        response = _link_response(_link_row(utm_params=None))
        assert response.utm_params == {}
        assert response.tracked_url == "https://example.com/pricing"
