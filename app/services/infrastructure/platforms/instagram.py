"""Instagram platform adapter — powered by RapidAPI (instagram-scraper-stable-api).

Uses the instagram-scraper-stable-api.p.rapidapi.com API from the RapidAPI
marketplace (by RockSolid APIs).  The API supports keyword search via
POST /search_ig.php which returns matching users and hashtags.

CONFIRMED (via live API test):
  Endpoint: POST /search_ig.php
  Content-Type: application/x-www-form-urlencoded
  Body field: search_query=<search term>
  Response: {"users": [{"position": N, "user": {...}}], "hashtags": [...]}

NOTE: The search result user objects do NOT include ``follower_count`` or
``biography``.  Follower count is approximated from the
``search_social_context`` string (e.g. "87.6M followers").  Biography
defaults to empty string.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.infrastructure.platforms.base import PlatformAdapter
from app.services.infrastructure.platforms.models import UnifiedComment, UnifiedPost
from app.services.infrastructure.platforms.rapidapi_client import RapidAPIClient, RapidAPIError

logger = logging.getLogger(__name__)

DEFAULT_INSTAGRAM_API_HOST = "instagram-scraper-stable-api.p.rapidapi.com"
INSTAGRAM_SEARCH_ENDPOINT = "/search_ig.php"


def _parse_follower_count(social_context: str) -> int:
    """Extract approximate follower count from search_social_context string.

    Handles formats like "87.6M followers", "685M followers", "9.4M followers".
    """
    if not social_context:
        return 0
    match = re.search(r"([\d.]+)\s*([KM]?)\s*follower", social_context, re.IGNORECASE)
    if not match:
        return 0
    value = float(match.group(1))
    suffix = match.group(2).upper()
    if suffix == "M":
        return int(value * 1_000_000)
    if suffix == "K":
        return int(value * 1_000)
    return int(value)


class InstagramAdapter(PlatformAdapter):
    """Instagram adapter using RapidAPI Instagram Scraper Stable API.

    Endpoints used:
      - POST /search_ig.php  — global search (returns users + hashtags)
        Content-Type: application/x-www-form-urlencoded
        Field: search_query
    """

    platform_name = "instagram"

    def __init__(self, api_host: str | None = None):
        self.api_host = api_host or DEFAULT_INSTAGRAM_API_HOST
        try:
            self.client = RapidAPIClient(self.api_host)
            self._available = True
        except ValueError:
            logger.warning("RapidAPI key not configured — Instagram adapter unavailable")
            self._available = False

    # ------------------------------------------------------------------
    # Internal HTTP helper — POST form-urlencoded
    # ------------------------------------------------------------------

    async def _post_form(
        self,
        endpoint: str,
        *,
        data: dict[str, str] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make a form-urlencoded POST request to the Instagram API.

        Args:
            endpoint: API path (e.g., ``/search_ig.php``).
            data: Form fields.

        Returns:
            Parsed JSON response.

        Raises:
            RapidAPIError: On non-200 responses after retries.
        """
        settings = get_settings()
        headers = {
            "x-rapidapi-key": settings.rapidapi_key,
            "x-rapidapi-host": self.api_host,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        url = f"https://{self.api_host}{endpoint}"

        max_retries = 1
        retry_delay = 2.0

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=15.0) as http:
                    response = await http.post(url, headers=headers, data=data or {})

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 429:
                    wait = retry_delay * (2**attempt)
                    logger.warning(
                        "Rate limited by %s, waiting %.1fs (attempt %d)",
                        self.api_host,
                        wait,
                        attempt + 1,
                    )
                    await asyncio.sleep(wait)
                    continue

                if response.status_code >= 500:
                    wait = retry_delay * (2**attempt)
                    logger.warning(
                        "Server error %d from %s, retrying in %.1fs",
                        response.status_code,
                        self.api_host,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                error_body = response.text[:500]
                if error_body.startswith("{\"error\":"):
                    error_data = response.json()
                    if isinstance(error_data, dict):
                        error_body = error_data.get("error", error_body)
                raise RapidAPIError(response.status_code, error_body, self.api_host)

            except httpx.HTTPError as e:
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    continue
                raise RapidAPIError(0, str(e), self.api_host) from e

        raise RapidAPIError(0, "Max retries exceeded", self.api_host)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_user_as_post(self, user: dict[str, Any]) -> UnifiedPost | None:
        """Convert a search-result user entry into a UnifiedPost.

        The /search_ig.php endpoint returns users with fields:
          - ``username`` (str)
          - ``full_name`` (str)
          - ``pk`` (int/str) — internal user ID
          - ``is_verified`` (bool)
          - ``profile_pic_url`` (str)
          - ``search_social_context`` (str, optional) — e.g. "87.6M followers"
        """
        if not isinstance(user, dict):
            return None

        username = user.get("username") or user.get("screen_name") or ""
        if not username:
            return None

        pk = str(user.get("pk", user.get("id", "")))
        full_name = user.get("full_name") or user.get("fullName") or ""
        is_verified = user.get("is_verified", False)
        social_context = user.get("search_social_context", "")
        follower_count = _parse_follower_count(social_context)

        parts = []
        if full_name:
            parts.append(full_name)
        if social_context:
            parts.append(f"Context: {social_context}")
        if is_verified:
            parts.append("Verified account")

        body = "\n".join(parts) if parts else f"Instagram user @{username}"
        profile_url = f"https://www.instagram.com/{username}/"

        media_urls: list[str] = []
        pic_url = user.get("profile_pic_url") or user.get("profile_pic") or user.get("avatar", "")
        if pic_url:
            media_urls.append(pic_url)

        try:
            post = UnifiedPost(
                platform="instagram",
                external_id=f"ig_user_{pk}" if pk else f"ig_user_{username}",
                author=username,
                author_id=pk,
                title=f"@{username}" + (f" — {full_name}" if full_name else ""),
                body=body,
                url=profile_url,
                hashtags=[],
                upvotes=follower_count,
                comments_count=0,
                shares=0,
                views=0,
                created_at=None,
                media_urls=media_urls,
                raw_data=user,
            )
            post.compute_engagement_score()
            return post
        except Exception as e:
            logger.debug("Failed to create UnifiedPost from Instagram user @%s: %s", username, e)
            return None

    def _parse_hashtag_as_post(self, hashtag: dict[str, Any]) -> UnifiedPost | None:
        """Convert a search-result hashtag entry into a UnifiedPost."""
        if not isinstance(hashtag, dict):
            return None

        name = hashtag.get("name", "")
        if not name:
            return None

        media_count = int(hashtag.get("media_count", hashtag.get("mediaCount", 0)))
        hashtag_id = str(hashtag.get("id", ""))
        tag_url = f"https://www.instagram.com/explore/tags/{name}/"

        try:
            post = UnifiedPost(
                platform="instagram",
                external_id=f"ig_hashtag_{hashtag_id}" if hashtag_id else f"ig_hashtag_{name}",
                author="instagram",
                author_id="",
                title=f"#{name} — {media_count:,} posts",
                body=f"Instagram hashtag #{name} with {media_count:,} total posts. "
                     f"This is a high-activity topic on Instagram that may be relevant for engagement.",
                url=tag_url,
                hashtags=[name],
                upvotes=media_count,
                comments_count=0,
                shares=0,
                views=0,
                created_at=None,
                media_urls=[],
                raw_data=hashtag,
            )
            post.compute_engagement_score()
            return post
        except Exception as e:
            logger.debug("Failed to create UnifiedPost from Instagram hashtag #%s: %s", name, e)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search_posts(
        self,
        keywords: list[str],
        *,
        limit: int = 50,
        sort: str = "relevance",
        time_filter: str = "week",
    ) -> list[UnifiedPost]:
        """Search Instagram using the Search (Users + Hashtags) endpoint.

        Uses POST /search_ig.php with form-urlencoded body containing
        ``search_query``.  Returns matching users and hashtags as UnifiedPosts.

        Args:
            keywords: Search terms to query.
            limit: Maximum total posts to return.
            sort: Ignored (API doesn't support sort).
            time_filter: Ignored (API doesn't support time filters).

        Returns:
            Combined list of user profiles and hashtags as UnifiedPosts.
        """
        if not self._available:
            logger.warning("Instagram adapter not available (no RAPIDAPI_KEY)")
            return []

        all_posts: list[UnifiedPost] = []
        seen_ids: set[str] = set()

        for keyword in keywords:
            query = keyword.strip()
            if not query:
                continue

            try:
                data = await self._post_form(
                    INSTAGRAM_SEARCH_ENDPOINT,
                    data={"search_query": query},
                )
            except RapidAPIError as e:
                logger.error("Instagram search failed for '%s': %s", query, e)
                continue

            if not isinstance(data, dict):
                continue

            # Parse users (wrapped in {position, user} objects)
            users = data.get("users", [])
            if isinstance(users, list):
                for user_entry in users[:10]:
                    if not isinstance(user_entry, dict):
                        continue
                    user = user_entry.get("user", user_entry)
                    post = self._parse_user_as_post(user)
                    if post and post.external_id not in seen_ids:
                        seen_ids.add(post.external_id)
                        all_posts.append(post)

            # Parse hashtags
            hashtags = data.get("hashtags", [])
            if isinstance(hashtags, list):
                for hashtag_entry in hashtags[:5]:
                    if not isinstance(hashtag_entry, dict):
                        continue
                    post = self._parse_hashtag_as_post(hashtag_entry)
                    if post and post.external_id not in seen_ids:
                        seen_ids.add(post.external_id)
                        all_posts.append(post)

            if len(all_posts) >= limit:
                break

        logger.info(
            "[instagram] Search across %d keywords returned %d results (users + hashtags)",
            len(keywords),
            len(all_posts),
        )
        return all_posts[:limit]

    async def get_post_comments(
        self,
        post_id: str,
        *,
        limit: int = 20,
    ) -> list[UnifiedComment]:
        """Get comments on an Instagram post.

        Currently not implemented for this API.  Returns empty list.
        """
        logger.debug("[instagram] get_post_comments not implemented (post %s)", post_id)
        return []

    async def get_trending(
        self,
        *,
        topic: str | None = None,
        limit: int = 25,
    ) -> list[UnifiedPost]:
        """Get trending Instagram content by searching for a topic."""
        if not self._available:
            return []

        query = topic or "trending"
        return await self.search_posts([query], limit=limit)

    async def health_check(self) -> bool:
        """Verify the Instagram API is reachable."""
        if not self._available:
            return False
        try:
            data = await self._post_form(
                INSTAGRAM_SEARCH_ENDPOINT,
                data={"search_query": "test"},
            )
            return isinstance(data, dict) and "users" in data
        except Exception:
            return False
