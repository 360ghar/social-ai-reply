import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class RedditSubredditMatch:
    name: str
    title: str
    description: str
    subscribers: int


@dataclass
class RedditPost:
    post_id: str
    subreddit: str
    title: str
    author: str
    permalink: str
    body: str
    created_at: datetime
    num_comments: int
    score: int


class RedditClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.reddit_base_url.rstrip("/")
        self.headers = {"User-Agent": settings.reddit_user_agent}
        self.timeout = 12.0
        self._last_request_time: float = 0.0
        self._min_interval: float = 1.5  # seconds between Reddit requests

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        # Rate-limit: wait between requests to avoid Reddit 429s
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

        for attempt in range(3):
            with httpx.Client(base_url=self.base_url, headers=self.headers, timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(path, params=params)
                self._last_request_time = time.monotonic()
                if response.status_code == 429:
                    wait = min(2 ** attempt * 2, 10)
                    logger.warning("Reddit 429 rate-limited on %s — waiting %ds (attempt %d/3)", path, wait, attempt + 1)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return response.json()
        # Final attempt failed — raise
        response.raise_for_status()
        return response.json()

    def search_subreddits(self, keyword: str, limit: int = 10) -> list[RedditSubredditMatch]:
        data = self._get("/subreddits/search.json", params={"q": keyword, "limit": limit, "sort": "relevance"})
        matches: list[RedditSubredditMatch] = []
        for child in data.get("data", {}).get("children", []):
            payload = child.get("data", {})
            matches.append(
                RedditSubredditMatch(
                    name=payload.get("display_name", ""),
                    title=payload.get("title", ""),
                    description=payload.get("public_description", "") or payload.get("description", ""),
                    subscribers=int(payload.get("subscribers") or 0),
                )
            )
        return [match for match in matches if match.name]

    def subreddit_about(self, name: str) -> dict[str, Any]:
        data = self._get(f"/r/{name}/about.json")
        return data.get("data", {})

    def subreddit_rules(self, name: str) -> list[str]:
        try:
            data = self._get(f"/r/{name}/about/rules.json")
        except httpx.HTTPError:
            return []
        rules = []
        for rule in data.get("rules", []):
            short_name = rule.get("short_name")
            description = rule.get("description")
            if short_name and description:
                rules.append(f"{short_name}: {description}")
            elif short_name:
                rules.append(short_name)
        return rules

    def search_posts(self, subreddit: str, keywords: list[str], limit: int = 20, sort: str = "new") -> list[RedditPost]:
        # Reddit's per-subreddit search endpoint has proven unreliable from some environments.
        # Use global search with a subreddit filter, then merge and dedupe results across keywords.
        if not keywords:
            return []

        per_query_limit = max(3, min(limit, 10))
        posts_by_id: dict[str, RedditPost] = {}
        for keyword in keywords[:8]:
            query = f'subreddit:{subreddit} "{keyword}"'
            try:
                data = self._get("/search.json", params={"q": query, "sort": sort, "limit": per_query_limit})
            except httpx.HTTPError:
                continue
            for child in data.get("data", {}).get("children", []):
                payload = child.get("data", {})
                created_ts = float(payload.get("created_utc") or 0.0)
                post = RedditPost(
                    post_id=payload.get("id", ""),
                    subreddit=payload.get("subreddit", subreddit),
                    title=payload.get("title", ""),
                    author=payload.get("author", "[deleted]"),
                    permalink=f"https://www.reddit.com{payload.get('permalink', '')}",
                    body=payload.get("selftext", "") or "",
                    created_at=datetime.fromtimestamp(created_ts, tz=timezone.utc) if created_ts else datetime.now(timezone.utc),
                    num_comments=int(payload.get("num_comments") or 0),
                    score=int(payload.get("score") or 0),
                )
                if post.post_id and post.title and post.subreddit.lower() == subreddit.lower():
                    posts_by_id[post.post_id] = post

        posts = sorted(posts_by_id.values(), key=lambda row: row.created_at, reverse=True)
        return posts[:limit]

    # ── Write operations (require OAuth, not yet implemented) ──────

    def post_comment(self, subreddit: str, parent_id: str, text: str) -> str:
        """Post a comment to a Reddit thread. Requires Reddit OAuth."""
        raise NotImplementedError("Reddit posting requires OAuth integration. Connect a Reddit account first.")

    def post_thread(self, subreddit: str, title: str, body: str) -> str:
        """Submit a new thread to a subreddit. Requires Reddit OAuth."""
        raise NotImplementedError("Reddit posting requires OAuth integration. Connect a Reddit account first.")

    def get_post_stats(self, reddit_id: str) -> dict[str, Any]:
        """Fetch upvotes, comments, and removal status for a post."""
        try:
            data = self._get(f"/{reddit_id}.json")
        except httpx.HTTPError:
            return {}
        children = data if isinstance(data, list) else data.get("data", {}).get("children", [])
        if not children:
            return {}
        post_data = children[0].get("data", {}).get("children", [{}])[0].get("data", {}) if isinstance(children[0].get("data"), dict) and "children" in children[0].get("data", {}) else (children[0].get("data", {}) if isinstance(children[0], dict) else {})
        return {
            "upvotes": post_data.get("score", 0),
            "num_comments": post_data.get("num_comments", 0),
            "removed": post_data.get("removed_by_category") is not None,
            "removal_reason": post_data.get("removed_by_category"),
        }
