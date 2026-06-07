"""Unit tests for Agent-Reach integration: client, adapters, and discovery services."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from app.services.product.reddit import RedditPost
from app.services.product.social_post import SocialPost

# ── Reddit adapter tests ──────────────────────────────────────────────

class TestRdtCliAdapter:
    """Tests for rdt-cli JSON → RedditPost parsing."""

    def test_parse_rdt_posts_basic(self):
        from app.services.infrastructure.agent_reach.reddit_adapter import parse_rdt_posts

        children = [
            {
                "id": "abc123",
                "title": "Best project management tool?",
                "selftext": "Looking for recommendations",
                "author": "seeker42",
                "permalink": "/r/projectmanagement/comments/abc123/best_tool/",
                "subreddit": "projectmanagement",
                "num_comments": 15,
                "score": 42,
                "created_utc": 1771351753.0,
            },
        ]
        posts = parse_rdt_posts(children)
        assert len(posts) == 1
        post = posts[0]
        assert post.post_id == "abc123"
        assert post.title == "Best project management tool?"
        assert post.body == "Looking for recommendations"
        assert post.author == "seeker42"
        assert post.subreddit == "projectmanagement"
        assert post.num_comments == 15
        assert post.score == 42
        assert post.permalink.startswith("https://www.reddit.com")

    def test_parse_rdt_posts_skips_malformed(self):
        from app.services.infrastructure.agent_reach.reddit_adapter import parse_rdt_posts

        children = [
            {"id": "", "title": "No ID"},  # missing id
            {"id": "abc", "title": ""},  # missing title
            {"id": "def", "title": "Valid", "subreddit": "test"},  # valid
        ]
        posts = parse_rdt_posts(children)
        assert len(posts) == 1
        assert posts[0].post_id == "def"

    def test_parse_rdt_posts_empty(self):
        from app.services.infrastructure.agent_reach.reddit_adapter import parse_rdt_posts

        assert parse_rdt_posts([]) == []

    def test_parse_rdt_posts_permalink_prefix(self):
        from app.services.infrastructure.agent_reach.reddit_adapter import parse_rdt_posts

        children = [
            {
                "id": "p1",
                "title": "Test",
                "permalink": "/r/test/comments/p1/test/",
                "subreddit": "test",
                "created_utc": 1771351753.0,
            },
        ]
        posts = parse_rdt_posts(children)
        assert posts[0].permalink == "https://www.reddit.com/r/test/comments/p1/test/"

    def test_parse_rdt_posts_full_permalink(self):
        from app.services.infrastructure.agent_reach.reddit_adapter import parse_rdt_posts

        children = [
            {
                "id": "p2",
                "title": "Test",
                "permalink": "https://www.reddit.com/r/test/comments/p2/test/",
                "subreddit": "test",
                "created_utc": 1771351753.0,
            },
        ]
        posts = parse_rdt_posts(children)
        assert posts[0].permalink == "https://www.reddit.com/r/test/comments/p2/test/"

    def test_parse_rdt_read_nested_structure(self):
        from app.services.infrastructure.agent_reach.reddit_adapter import parse_rdt_read

        data = {"data": [[{"id": "p1", "title": "Test", "subreddit": "test"}], []]}
        post = parse_rdt_read(data)
        assert post is not None
        assert post.post_id == "p1"
        assert post.title == "Test"
        assert post.subreddit == "test"

    def test_parse_rdt_read_returns_none_on_empty(self):
        from app.services.infrastructure.agent_reach.reddit_adapter import parse_rdt_read

        result = parse_rdt_read({})
        assert result is None


# ── Twitter adapter tests ────────────────────────────────────────────

class TestTwitterCliAdapter:
    """Tests for twitter-cli JSON → SocialPost parsing."""

    def test_parse_twitter_results_basic(self):
        from app.services.infrastructure.agent_reach.twitter_adapter import parse_twitter_results

        tweets = [
            {
                "id": "2049818223869382769",
                "text": "Project management tool directly in Codex!",
                "author": {
                    "screenName": "b_nnett",
                    "name": "Bennett",
                },
                "metrics": {
                    "likes": 907,
                    "retweets": 41,
                    "replies": 33,
                    "views": 189589,
                },
                "createdAtISO": "2026-04-30T11:48:43+00:00",
            },
        ]
        posts = parse_twitter_results(tweets)
        assert len(posts) == 1
        post = posts[0]
        assert post.post_id == "2049818223869382769"
        assert post.platform == "twitter"
        assert post.body == "Project management tool directly in Codex!"
        assert post.author == "b_nnett"
        assert post.score == 907
        assert post.num_comments == 33
        assert post.extra_metrics["retweets"] == 41
        assert post.extra_metrics["views"] == 189589

    def test_parse_twitter_results_skips_empty(self):
        from app.services.infrastructure.agent_reach.twitter_adapter import parse_twitter_results

        tweets = [
            {"id": "", "text": "No ID"},  # missing id
            {"id": "123", "text": ""},  # missing text
            {"id": "456", "text": "Valid tweet"},  # valid
        ]
        posts = parse_twitter_results(tweets)
        assert len(posts) == 1
        assert posts[0].post_id == "456"

    def test_parse_twitter_results_empty(self):
        from app.services.infrastructure.agent_reach.twitter_adapter import parse_twitter_results

        assert parse_twitter_results([]) == []

    def test_parse_twitter_date_legacy_format(self):
        from app.services.infrastructure.agent_reach.twitter_adapter import parse_twitter_results

        tweets = [
            {
                "id": "legacy1",
                "text": "Legacy date tweet",
                "author": {"screenName": "user1"},
                "metrics": {"likes": 5, "retweets": 0, "replies": 0, "views": 10},
                "createdAt": "Thu Apr 30 11:48:43 +0000 2026",
            },
        ]
        posts = parse_twitter_results(tweets)
        assert len(posts) == 1
        assert posts[0].post_id == "legacy1"
        assert posts[0].body == "Legacy date tweet"
        assert posts[0].created_at.year == 2026
        assert posts[0].created_at.month == 4
        assert posts[0].created_at.day == 30


# ── SocialPost tests ─────────────────────────────────────────────────

class TestSocialPost:
    """Tests for the SocialPost shared model."""

    def test_from_reddit_post(self):
        reddit_post = RedditPost(
            post_id="abc123",
            subreddit="projectmanagement",
            title="Best project management tool?",
            author="seeker42",
            permalink="https://www.reddit.com/r/projectmanagement/comments/abc123/",
            body="Looking for recommendations",
            created_at=datetime.now(UTC),
            num_comments=15,
            score=42,
        )
        social = SocialPost.from_reddit_post(reddit_post)
        assert social.post_id == "abc123"
        assert social.platform == "reddit"
        assert social.community == "projectmanagement"
        assert social.title == "Best project management tool?"

    def test_as_opportunity_dict_reddit(self):
        post = SocialPost(
            post_id="abc123",
            platform="reddit",
            title="Test post",
            body="Test body",
            author="user1",
            url="https://www.reddit.com/r/test/comments/abc123/",
            created_at=datetime.now(UTC),
            score=42,
            num_comments=10,
            community="test",
        )
        opp = post.as_opportunity_dict(
            project_id=1,
            scan_run_id="run-1",
            score=50,
            score_reasons=["keyword match"],
        )
        assert opp["project_id"] == 1
        assert opp["reddit_post_id"] == "abc123"
        assert opp["platform"] == "reddit"
        assert opp["subreddit_name"] == "test"

    def test_as_opportunity_dict_twitter(self):
        post = SocialPost(
            post_id="tweet123",
            platform="twitter",
            title="",
            body="Great tool for PM!",
            author="tweeter",
            url="https://x.com/tweeter/status/tweet123",
            created_at=datetime.now(UTC),
            score=907,
            num_comments=33,
            community="",
        )
        opp = post.as_opportunity_dict(
            project_id=2,
            score=40,
        )
        assert opp["reddit_post_id"] == "twitter:tweet123"
        assert opp["platform"] == "twitter"
        assert "PM" in opp["title"]

    def test_to_reddit_post_compatible(self):
        post = SocialPost(
            post_id="tweet123",
            platform="twitter",
            title="",
            body="Great tool!",
            author="tweeter",
            url="https://x.com/tweeter/status/tweet123",
            created_at=datetime.now(UTC),
            score=100,
            num_comments=5,
            community="",
        )
        reddit_compat = post.to_reddit_post_compatible()
        assert isinstance(reddit_compat, RedditPost)
        assert reddit_compat.post_id == "tweet123"
        assert reddit_compat.subreddit == "twitter"
        assert reddit_compat.score == 100


# ── AgentReachClient tests (mocked subprocess) ───────────────────────

class TestAgentReachClient:
    """Tests for the AgentReachClient wrapper."""

    def test_rdt_not_available(self, monkeypatch):
        from app.services.infrastructure.agent_reach.client import AgentReachClient

        client = AgentReachClient()
        client._enabled = True
        client._tool_available["rdt"] = False
        assert client.rdt_available is False

    def test_twitter_not_available(self, monkeypatch):
        from app.services.infrastructure.agent_reach.client import AgentReachClient

        client = AgentReachClient()
        client._enabled = True
        client._tool_available["twitter"] = False
        assert client.twitter_available is False

    def test_rdt_search_returns_none_when_unavailable(self):
        from app.services.infrastructure.agent_reach.client import AgentReachClient

        client = AgentReachClient()
        client._enabled = False
        result = client.rdt_search("test query")
        assert result is None

    def test_twitter_search_returns_none_when_unavailable(self):
        from app.services.infrastructure.agent_reach.client import AgentReachClient

        client = AgentReachClient()
        client._enabled = False
        result = client.twitter_search("test query")
        assert result is None

    def test_rdt_search_returns_none_on_ok_false(self, monkeypatch):
        from app.services.infrastructure.agent_reach.client import AgentReachClient

        client = AgentReachClient()
        client._enabled = True
        client._tool_available["rdt"] = True
        mock_output = {"ok": False, "error": "rate limited"}
        with patch.object(client, "_run", return_value=mock_output):
            result = client.rdt_search("test query")
            assert result is None

    def test_rdt_search_returns_none_when_run_returns_none(self, monkeypatch):
        from app.services.infrastructure.agent_reach.client import AgentReachClient

        client = AgentReachClient()
        client._enabled = True
        client._tool_available["rdt"] = True
        with patch.object(client, "_run", return_value=None):
            result = client.rdt_search("test query")
            assert result is None

    def test_twitter_search_returns_none_on_ok_false(self, monkeypatch):
        from app.services.infrastructure.agent_reach.client import AgentReachClient

        client = AgentReachClient()
        client._enabled = True
        client._tool_available["twitter"] = True
        mock_output = {"ok": False, "error": "rate limited"}
        with patch.object(client, "_run", return_value=mock_output):
            result = client.twitter_search("test query")
            assert result is None

    def test_rdt_read_returns_none_when_unavailable(self, monkeypatch):
        from app.services.infrastructure.agent_reach.client import AgentReachClient

        client = AgentReachClient()
        client._enabled = True
        client._tool_available["rdt"] = False
        result = client.rdt_read("abc123")
        assert result is None

    def test_rdt_search_parses_json_output(self, monkeypatch):
        from app.services.infrastructure.agent_reach.client import AgentReachClient

        client = AgentReachClient()
        client._enabled = True
        client._tool_available["rdt"] = True
        mock_output = {
            "ok": True,
            "data": {
                "data": {
                    "children": [
                        {
                            "kind": "t3",
                            "data": {
                                "id": "abc123",
                                "title": "Test post",
                                "selftext": "Body text",
                                "subreddit": "test",
                                "author": "user1",
                                "permalink": "/r/test/comments/abc123/",
                                "num_comments": 5,
                                "score": 10,
                                "created_utc": 1771351753.0,
                            },
                        },
                    ],
                },
            },
        }
        with patch.object(client, "_run", return_value=mock_output):
            results = client.rdt_search("test query")
            assert results is not None
            assert len(results) == 1
            assert results[0]["id"] == "abc123"

    def test_twitter_search_parses_json_output(self, monkeypatch):
        from app.services.infrastructure.agent_reach.client import AgentReachClient

        client = AgentReachClient()
        client._enabled = True
        client._tool_available["twitter"] = True
        mock_output = {
            "ok": True,
            "data": [
                {
                    "id": "tweet123",
                    "text": "Hello world",
                    "author": {"screenName": "user1"},
                    "metrics": {"likes": 10, "retweets": 2, "replies": 1, "views": 100},
                    "createdAtISO": "2026-04-30T11:48:43+00:00",
                },
            ],
        }
        with patch.object(client, "_run", return_value=mock_output):
            results = client.twitter_search("test query")
            assert results is not None
            assert len(results) == 1
            assert results[0]["id"] == "tweet123"

# ── TwitterDiscoveryService tests ────────────────────────────────────

class TestTwitterDiscoveryService:
    """Tests for the Twitter discovery service."""

    def test_search_tweets_returns_empty_when_unavailable(self, monkeypatch):
        from app.services.product.twitter_discovery import TwitterDiscoveryService

        service = TwitterDiscoveryService()
        service._client._enabled = False

        results = service.search_tweets(["test keyword"])
        assert results == []

    def test_search_tweets_deduplicates(self, monkeypatch):
        from app.services.product.twitter_discovery import TwitterDiscoveryService

        service = TwitterDiscoveryService()
        service._client._enabled = True
        service._client._tool_available["twitter"] = True
        tweet_data = [
            {
                "id": "tweet1",
                "text": "First tweet",
                "author": {"screenName": "user1"},
                "metrics": {"likes": 10, "retweets": 1, "replies": 0, "views": 50},
                "createdAtISO": "2026-04-30T11:48:43+00:00",
            },
        ]
        # Return the same tweet for both "top" and "latest" searches
        monkeypatch.setattr(
            service._client,
            "twitter_search",
            lambda *a, **kw: tweet_data,
        )

        results = service.search_tweets(["test"])
        # Should deduplicate — only one tweet1
        assert sum(1 for p in results if p.post_id == "tweet1") == 1
