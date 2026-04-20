from datetime import UTC, datetime

import pytest

from app.services.product.reddit import RedditPost
from app.services.product.reddit_discovery import RedditDiscoveryService, SearchResult


def test_search_posts_combines_external_search_and_subreddit_feed(monkeypatch):
    service = RedditDiscoveryService()

    monkeypatch.setattr(
        service,
        "_search_web",
        lambda query, limit: [
            SearchResult(url="https://www.reddit.com/r/RealEstate/comments/ext123/thread", title="Verify listings", snippet=""),
        ],
    )
    monkeypatch.setattr(
        service,
        "_fetch_post_from_url",
        lambda url: RedditPost(
            post_id="ext123",
            subreddit="RealEstate",
            title="How do you verify property details before buying?",
            author="buyer42",
            permalink=url,
            body="Trying to avoid fake listings and compare trustworthy homes.",
            created_at=datetime.now(UTC),
            num_comments=6,
            score=18,
        ),
    )
    monkeypatch.setattr(
        service,
        "_search_posts_in_subreddit_feed",
        lambda subreddit, keywords, limit: [
            RedditPost(
                post_id="feed456",
                subreddit=subreddit,
                title="Any checklist for validating apartment listings?",
                author="buyer77",
                permalink=f"https://www.reddit.com/r/{subreddit}/comments/feed456/thread",
                body="Looking for tips before I tour a property.",
                created_at=datetime.now(UTC),
                num_comments=4,
                score=12,
            )
        ],
    )

    posts = service.search_posts(
        ["verified property details"],
        subreddits=["RealEstate"],
        limit=5,
    )

    assert [post.post_id for post in posts] == ["ext123", "feed456"]
    assert posts[0].as_discovery_record()["url"].startswith("https://www.reddit.com/r/RealEstate/comments/")


def test_search_posts_filters_external_results_to_allowed_subreddits(monkeypatch):
    service = RedditDiscoveryService()

    monkeypatch.setattr(
        service,
        "_search_web",
        lambda query, limit: [
            SearchResult(url="https://www.reddit.com/r/RealEstate/comments/good123/thread", title="good", snippet=""),
            SearchResult(url="https://www.reddit.com/r/HBO/comments/bad123/thread", title="bad", snippet=""),
        ],
    )
    monkeypatch.setattr(
        service,
        "_fetch_post_from_url",
        lambda url: RedditPost(
            post_id="good123" if "good123" in url else "bad123",
            subreddit="RealEstate" if "good123" in url else "HBO",
            title="How do home buyers verify listings?" if "good123" in url else "Best HBO episode?",
            author="user1",
            permalink=url,
            body="Need validation help." if "good123" in url else "Need a streaming recommendation.",
            created_at=datetime.now(UTC),
            num_comments=3,
            score=11,
        ),
    )
    monkeypatch.setattr(service, "_search_posts_in_subreddit_feed", lambda subreddit, keywords, limit: [])

    posts = service.search_posts(["home buyers"], subreddits=["RealEstate"], limit=5)

    assert [post.post_id for post in posts] == ["good123"]


def test_search_subreddits_derives_candidates_from_external_results(monkeypatch):
    service = RedditDiscoveryService()

    monkeypatch.setattr(
        service,
        "_search_web",
        lambda query, limit: [
            SearchResult(url="https://www.reddit.com/r/saas/comments/abc123/thread", title="SaaS growth", snippet=""),
            SearchResult(url="https://www.reddit.com/r/saas/comments/def456/thread", title="SaaS founders", snippet=""),
            SearchResult(url="https://www.reddit.com/r/AskReddit/comments/ghi789/thread", title="AskReddit", snippet=""),
        ],
    )
    monkeypatch.setattr(
        service,
        "subreddit_about",
        lambda subreddit: {
            "display_name": subreddit,
            "title": "SaaS" if subreddit.lower() == "saas" else "AskReddit",
            "public_description": "Software founders discussing growth" if subreddit.lower() == "saas" else "General prompts",
            "subscribers": 120000 if subreddit.lower() == "saas" else 1000,
        },
    )

    matches = service.search_subreddits("saas growth", limit=2)

    assert [match.name for match in matches] == ["saas", "AskReddit"]


def test_search_posts_raises_when_every_discovery_mode_fails(monkeypatch):
    service = RedditDiscoveryService()

    def raise_external(query, limit):
        raise RuntimeError("search provider unavailable")

    def raise_feed(subreddit, keywords, limit):
        raise RuntimeError("reddit feed unavailable")

    monkeypatch.setattr(service, "_search_web", raise_external)
    monkeypatch.setattr(service, "_search_posts_in_subreddit_feed", raise_feed)

    with pytest.raises(RuntimeError, match="All Reddit discovery methods failed"):
        service.search_posts(["home buyers"], subreddits=["RealEstate"], limit=5)
