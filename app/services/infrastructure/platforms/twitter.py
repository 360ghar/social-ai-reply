"""Twitter/X platform adapter — powered by RapidAPI (twitter-api45.p.rapidapi.com).

Uses "Twitter API" by Alexander Vikhorev on the RapidAPI marketplace.

Verified endpoints:
  - GET /search.php              — keyword search (query params)
  - GET /timeline.php            — user timeline
  - GET /user_info.php           — user profile lookup

Search strategy:
  1. Build query from keywords with ``-is:retweet lang:en`` filters
  2. GET /search.php with ``search_type="Top"`` for quality results
  3. Parse tweet objects into UnifiedPost
"""
from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.services.infrastructure.platforms.base import PlatformAdapter
from app.services.infrastructure.platforms.models import UnifiedComment, UnifiedPost
from app.services.infrastructure.platforms.rapidapi_client import RapidAPIClient, RapidAPIError

logger = logging.getLogger(__name__)

DEFAULT_TWITTER_API_HOST = "twitter-api45.p.rapidapi.com"

_TWITTER_DATE_FMT = "%a %b %d %H:%M:%S %z %Y"


class TwitterAdapter(PlatformAdapter):
    """Twitter/X adapter using RapidAPI (twitter-api45 by Alexander Vikhorev).

    Uses GET /search.php with query params.  Response is an object with
    a ``tweets`` array containing tweet objects.
    """

    platform_name = "twitter"

    def __init__(self, api_host: str | None = None) -> None:
        self.api_host = api_host or DEFAULT_TWITTER_API_HOST
        try:
            self.client = RapidAPIClient(self.api_host)
            self._available = True
        except ValueError:
            logger.warning("RapidAPI key not configured — Twitter adapter disabled")
            self._available = False

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_timestamp(raw: dict[str, Any]) -> datetime | None:
        """Parse a tweet's creation timestamp.

        Tries ``created_at`` string first (e.g.
        ``"Fri Nov 07 09:12:36 +0000 2025"``).
        """
        created_at = raw.get("created_at")
        if created_at and isinstance(created_at, str):
            with contextlib.suppress(ValueError):
                return datetime.strptime(created_at, _TWITTER_DATE_FMT).replace(tzinfo=UTC)
        return None

    @staticmethod
    def _extract_media(raw: dict[str, Any]) -> list[str]:
        """Collect media URLs from a tweet result.

        Handles both simple ``media_url``/``video_url`` fields and the
        ``media`` array returned by twitter-api45.
        """
        urls: list[str] = []
        if raw.get("media_url"):
            urls.append(str(raw["media_url"]))
        if raw.get("video_url"):
            urls.append(str(raw["video_url"]))
        media_list = raw.get("media")
        if isinstance(media_list, list):
            for m in media_list:
                if isinstance(m, dict):
                    url = m.get("media_url_https") or m.get("url") or ""
                    if url:
                        urls.append(url)
        return urls

    @staticmethod
    def _get_int(value: Any, *alternatives: str) -> int:
        """Extract an int from a dict field, trying multiple keys."""
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            with contextlib.suppress(ValueError):
                return int(value)
        return 0

    @staticmethod
    def _get_int_from(raw: dict[str, Any], *keys: str) -> int:
        """Try multiple keys to get an int value from a dict."""
        for key in keys:
            val = raw.get(key)
            if val is not None:
                if isinstance(val, int):
                    return val
                if isinstance(val, str):
                    with contextlib.suppress(ValueError):
                        return int(val)
        return 0

    def _parse_tweet(self, raw: dict[str, Any]) -> UnifiedPost:
        """Convert a twitter-api45 search result into a :class:`UnifiedPost`.

        twitter-api45 response fields:
          - ``tweet_id`` (str)
          - ``text`` (str)
          - ``screen_name`` (str) — username/handle
          - ``user_info`` (dict) — nested user profile
          - ``favorites`` / ``favorite_count`` (int) — likes
          - ``retweets`` / ``retweet_count`` (int) — retweets
          - ``replies`` / ``reply_count`` (int) — reply count
          - ``views`` (int or str) — view count
          - ``quotes`` (int) — quote count
          - ``bookmarks`` (int) — bookmark count
          - ``created_at`` (str) — e.g. "Fri Nov 07 09:12:36 +0000 2025"
          - ``entities`` (dict) — hashtags, urls, user_mentions
          - ``media`` (list) — media attachments
        """
        user_info: dict[str, Any] = raw.get("user_info") or {}
        username = raw.get("screen_name") or user_info.get("screen_name") or ""
        display_name = user_info.get("name") or username
        tweet_id = str(raw.get("tweet_id") or "")

        url = f"https://x.com/{username}/status/{tweet_id}" if username and tweet_id else ""

        text = raw.get("text") or ""
        hashtags: list[str] = []
        entities = raw.get("entities")
        if isinstance(entities, dict):
            hashtag_list = entities.get("hashtags", [])
            if isinstance(hashtag_list, list):
                for h in hashtag_list:
                    if isinstance(h, dict):
                        tag = h.get("text", "")
                    elif isinstance(h, str):
                        tag = h
                    else:
                        continue
                    if tag:
                        hashtags.append(tag.lower())
        for word in text.split():
            if word.startswith("#") and len(word) > 1:
                tag = word.lstrip("#").lower()
                if tag not in hashtags:
                    hashtags.append(tag)

        return UnifiedPost(
            platform="twitter",
            external_id=tweet_id,
            author=display_name,
            author_id=username,
            title=None,
            body=text,
            url=url,
            subreddit=None,
            hashtags=hashtags,
            upvotes=self._get_int_from(raw, "favorites", "favorite_count", "likeCount"),
            comments_count=self._get_int_from(raw, "replies", "reply_count"),
            shares=self._get_int_from(raw, "retweets", "retweet_count"),
            views=self._get_int_from(raw, "views", "view_count"),
            created_at=self._parse_timestamp(raw),
            media_urls=self._extract_media(raw),
            raw_data=raw,
        )

    @staticmethod
    def _build_query(keywords: list[str]) -> str:
        """Build a Twitter search query from keywords.

        Joins keywords with OR to match tweets containing ANY keyword,
        then appends ``-is:retweet lang:en`` to filter retweets and
        restrict to English tweets.
        """
        parts = []
        for kw in keywords:
            kw = kw.strip()
            if not kw:
                continue
            if " " in kw:
                parts.append(f'"{kw}"')
            else:
                parts.append(kw)
        base = " OR ".join(parts)
        return f"({base}) -is:retweet lang:en"

    # ------------------------------------------------------------------
    # PlatformAdapter interface
    # ------------------------------------------------------------------

    async def search_posts(
        self,
        keywords: list[str],
        *,
        limit: int = 50,
        sort: str = "relevance",
        time_filter: str = "week",
    ) -> list[UnifiedPost]:
        """Search Twitter for tweets matching *keywords*.

        Batches keywords into groups of 5, searches each batch via
        ``GET /search.php`` with ``search_type="Top"``, and
        deduplicates results.

        The twitter-api45 search endpoint returns tweets sorted by
        relevance when ``search_type="Top"``.
        """
        if not self._available:
            return []

        batch_size = 5
        kw_batches = [keywords[i:i + batch_size] for i in range(0, len(keywords), batch_size)]
        kw_batches = kw_batches[:4]

        all_posts: list[UnifiedPost] = []
        seen_ids: set[str] = set()
        per_page = min(limit, 20)
        search_type = "Top"

        for batch in kw_batches:
            query = self._build_query(batch)

            try:
                data = await self.client.get(
                    "/search.php",
                    params={
                        "query": query,
                        "search_type": search_type,
                    },
                )
            except RapidAPIError as e:
                logger.warning("Twitter search failed for '%s': %s", query[:60], e)
                continue

            results: list[dict[str, Any]] = []
            if isinstance(data, dict):
                results = data.get("timeline", data.get("tweets", []))
            elif isinstance(data, list):
                results = data

            for item in results[:per_page]:
                if not isinstance(item, dict):
                    continue
                tweet_id = str(item.get("tweet_id", ""))
                if tweet_id in seen_ids or not tweet_id:
                    continue
                seen_ids.add(tweet_id)
                with contextlib.suppress(Exception):
                    post = self._parse_tweet(item)
                    post.compute_engagement_score()
                    all_posts.append(post)

            if len(all_posts) >= limit:
                break

        logger.info("[twitter] Search across %d batches returned %d tweets", len(kw_batches), len(all_posts))
        return all_posts[:limit]

    async def get_post_comments(
        self,
        post_id: str,
        *,
        limit: int = 20,
    ) -> list[UnifiedComment]:
        """Get replies to a tweet.

        twitter-api45 does not expose a direct tweet-reply endpoint via
        the search API, so this returns an empty list.
        """
        logger.debug("[twitter] get_post_comments not supported — returning empty list for %s", post_id)
        return []

    async def get_trending(
        self,
        *,
        topic: str | None = None,
        limit: int = 25,
    ) -> list[UnifiedPost]:
        """Get trending/popular tweets."""
        if not self._available:
            return []

        keywords = [topic] if topic else ["trending"]
        return await self.search_posts(keywords, limit=limit, sort="relevance")

    async def health_check(self) -> bool:
        """Verify the Twitter adapter can reach the API."""
        if not self._available:
            return False

        try:
            data = await self.client.get(
                "/search.php",
                params={"query": "test", "search_type": "Top"},
            )
            if isinstance(data, dict):
                return bool(data.get("timeline")) or "timeline" in data
            return False
        except Exception:
            return False
