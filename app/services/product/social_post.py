"""Shared social post model for multi-platform discovery.

Provides a unified dataclass that normalises posts from any platform
(Reddit, Twitter, etc.) into a common shape. Factory methods convert
platform-specific objects into SocialPost instances.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class SocialPost:
    """A normalised social media post from any platform."""

    post_id: str
    platform: str  # "reddit", "twitter", etc.
    title: str
    body: str
    author: str
    url: str
    created_at: datetime
    score: int
    num_comments: int
    community: str  # subreddit name, twitter handle context, etc.
    extra_metrics: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_reddit_post(cls, post: Any) -> SocialPost:
        """Create a SocialPost from a RedditPost dataclass instance."""
        return cls(
            post_id=post.post_id,
            platform="reddit",
            title=post.title,
            body=post.body,
            author=post.author,
            url=post.permalink,
            created_at=post.created_at,
            score=post.score,
            num_comments=post.num_comments,
            community=post.subreddit,
        )

    def as_opportunity_dict(
        self,
        *,
        project_id: int,
        scan_run_id: str | None = None,
        score: int = 0,
        score_reasons: list[str] | None = None,
        keyword_hits: list[str] | None = None,
        rule_risk: list[str] | None = None,
        status: str = "new",
    ) -> dict[str, Any]:
        """Convert to a dict suitable for the opportunities table insert.

        Maps platform-specific fields to the common opportunity schema.
        """
        # For Reddit, use reddit_post_id; for Twitter, use the tweet URL as the identifier
        reddit_post_id = self.post_id if self.platform == "reddit" else f"{self.platform}:{self.post_id}"

        return {
            "project_id": project_id,
            "scan_run_id": scan_run_id,
            "reddit_post_id": reddit_post_id,
            "subreddit_name": self.community,
            "author": self.author,
            "title": self.title or f"[{self.platform}] {self.body[:80]}",
            "permalink": self.url,
            "body_excerpt": self.body[:1200],
            "score": score,
            "score_reasons": score_reasons or [],
            "keyword_hits": keyword_hits or [],
            "rule_risk": rule_risk or [],
            "status": status,
            "platform": self.platform,
        }

    def to_reddit_post_compatible(self) -> Any:
        """Create a RedditPost-compatible object for the scoring pipeline.

        Allows the existing score_post() function to score Twitter posts
        by mapping Twitter fields to the RedditPost shape. Not all fields
        have direct equivalents, so we approximate.
        """
        from app.services.product.reddit import RedditPost

        return RedditPost(
            post_id=self.post_id,
            subreddit=self.community or self.platform,
            title=self.title or self.body[:200],
            author=self.author,
            permalink=self.url,
            body=self.body,
            created_at=self.created_at if self.created_at.tzinfo else self.created_at.replace(tzinfo=UTC),
            num_comments=self.num_comments,
            score=self.score,
        )
