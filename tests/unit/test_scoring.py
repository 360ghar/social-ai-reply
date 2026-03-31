"""Unit tests for post scoring module."""
from datetime import datetime, timezone

from app.services.product.reddit import RedditPost
from app.services.product.scoring import score_post


def _make_brand():
    from app.db.models import BrandProfile
    return BrandProfile(
        id=1, project_id=1,
        brand_name="TestBrand",
        summary="A test brand for unit testing.",
        product_summary="Test product.",
        target_audience="developers",
    )


def _make_subreddit():
    from app.db.models import MonitoredSubreddit
    return MonitoredSubreddit(
        id=1, project_id=1,
        name="test", title="Test", description="A test subreddit",
        subscribers=1000, fit_score=50,
    )


def _make_post(**overrides):
    defaults = dict(
        post_id="p1", subreddit="test", title="Looking for a good tool",
        author="user1", permalink="https://reddit.com/r/test/p1",
        body="I need help finding something",
        created_at=datetime.now(timezone.utc),
        num_comments=5, score=10,
    )
    defaults.update(overrides)
    return RedditPost(**defaults)


class TestScorePost:
    def test_returns_score_result(self):
        brand = _make_brand()
        subreddit = _make_subreddit()
        post = _make_post(title="Looking for a test tool for developers")
        keywords = ["test tool"]
        rules = []

        result = score_post(post, brand, subreddit, keywords, rules)
        assert hasattr(result, "total")
        assert hasattr(result, "reasons")
        assert hasattr(result, "keyword_hits")
        assert hasattr(result, "rule_risk")

    def test_irrelevant_post_still_returns_result(self):
        brand = _make_brand()
        subreddit = _make_subreddit()
        post = _make_post(title="My cat is cute", body="Just look at this photo")
        keywords = ["enterprise software"]
        rules = []

        result = score_post(post, brand, subreddit, keywords, rules)
        assert isinstance(result.total, (int, float))

    def test_keyword_hits_detected(self):
        brand = _make_brand()
        subreddit = _make_subreddit()
        post = _make_post(title="Need a test brand solution", body="test brand is great")
        keywords = ["test brand"]
        rules = []

        result = score_post(post, brand, subreddit, keywords, rules)
        assert len(result.keyword_hits) > 0
