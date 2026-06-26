"""Enhanced Instagram adapter — user-first search with smart keyword shortening.

When a user configures a custom scraper for Instagram, this adapter uses their
API credentials but applies smart scanning logic:
  1. Shorten long discovery keywords to 2-3 word Instagram-friendly queries
  2. Prioritize user profile results over hashtags
  3. Fall back to DynamicAdapter LLM parsing for unknown API response formats

Supports known Instagram APIs:
  - instagram-looter2.p.rapidapi.com (GET /search?query=...)
  - instagram-cheapest.p.rapidapi.com (various endpoints)
  - Any other Instagram API via DynamicAdapter fallback
"""
from __future__ import annotations

import logging
import re
from typing import Any

from app.services.infrastructure.platforms.base import PlatformAdapter
from app.services.infrastructure.platforms.models import UnifiedComment, UnifiedPost
from app.services.infrastructure.platforms.rapidapi_client import RapidAPIClient, RapidAPIError

logger = logging.getLogger(__name__)


class InstagramEnhancedAdapter(PlatformAdapter):
    """Instagram adapter that uses custom API credentials with smart scanning.

    Prioritizes user profile search over hashtags, and shortens long keywords
    to work better with Instagram's search.
    """

    platform_name = "instagram"

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.config = config
        self.api_host = config.get("api_host", "instagram-looter2.p.rapidapi.com")
        self.search_endpoint = config.get("search_endpoint", "/search")
        self.search_param_name = config.get("search_param_name", "query")
        self.items_json_path = config.get("items_json_path", "")
        api_key = config.get("api_key")
        try:
            self.client = RapidAPIClient(self.api_host, api_key=api_key)
            self._available = True
        except ValueError:
            logger.warning("RapidAPI key not configured — Instagram enhanced adapter unavailable")
            self._available = False

    # ------------------------------------------------------------------
    # Keyword shortening
    # ------------------------------------------------------------------

    @staticmethod
    def _shorten_keywords(keywords: list[str], max_queries: int = 10) -> list[str]:
        """Convert long discovery keywords to short Instagram-friendly queries.

        Instagram search works best with 1-3 word terms.
        "tired of blurry property photos in gurugram" → "property photos", "gurugram real estate"
        """
        stop_words = {
            "with", "from", "that", "this", "have", "will", "your", "what",
            "when", "where", "which", "there", "their", "about", "been",
            "some", "them", "than", "just", "also", "into", "most", "much",
            "know", "find", "need", "good", "best", "hard", "many", "very",
            "more", "like", "make", "does", "each", "only", "over", "such",
            "take", "even", "well", "back", "give", "want", "someone",
            "tired", "looking", "anyone", "recommend", "alternative",
            "for", "the", "and", "how", "can", "but",
        }

        short_queries: list[str] = []
        seen: set[str] = set()

        for kw in keywords:
            kw_clean = kw.strip().lower()

            # If already short (1-3 words), use directly
            words = kw_clean.split()
            if len(words) <= 3:
                if kw_clean not in seen:
                    short_queries.append(kw_clean)
                    seen.add(kw_clean)
                continue

            # For long keywords, extract meaningful 2-word pairs
            meaningful = [w.strip(".,!?;:'\"()[]") for w in words if len(w) >= 3 and w not in stop_words]
            if len(meaningful) >= 2:
                # Take first 2 meaningful words
                pair = " ".join(meaningful[:2])
                if pair not in seen:
                    short_queries.append(pair)
                    seen.add(pair)
                # Also try last 2 meaningful words (different angle)
                if len(meaningful) >= 4:
                    pair2 = " ".join(meaningful[-2:])
                    if pair2 not in seen:
                        short_queries.append(pair2)
                        seen.add(pair2)
            elif meaningful:
                single = meaningful[0]
                if single not in seen:
                    short_queries.append(single)
                    seen.add(single)

        return short_queries[:max_queries]

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_user_as_post(user_wrapper: dict[str, Any]) -> UnifiedPost | None:
        """Convert a search-result user entry into a UnifiedPost."""
        user = user_wrapper.get("user", user_wrapper)
        if not isinstance(user, dict):
            return None

        username = user.get("username", "")
        if not username:
            return None

        full_name = user.get("full_name", "")
        bio = user.get("biography", user.get("bio", ""))
        pk = str(user.get("pk", user.get("id", "")))
        is_verified = user.get("is_verified", False)
        follower_count = int(user.get("follower_count", user.get("followers", 0)) or 0)

        parts = []
        if full_name:
            parts.append(full_name)
        if bio:
            parts.append(bio)
        if is_verified:
            parts.append("✓ Verified account")

        body = "\n".join(parts) if parts else f"Instagram user @{username}"
        profile_url = f"https://www.instagram.com/{username}/"

        # Extract hashtags from bio
        hashtags: list[str] = []
        if bio:
            hashtags = re.findall(r"#(\w+)", bio)

        try:
            post = UnifiedPost(
                platform="instagram",
                external_id=f"ig_user_{pk}" if pk else f"ig_user_{username}",
                author=username,
                author_id=pk,
                title=f"@{username}" + (f" — {full_name}" if full_name else ""),
                body=body,
                url=profile_url,
                hashtags=hashtags,
                upvotes=follower_count,
                comments_count=0,
                shares=0,
                views=0,
                created_at=None,
                media_urls=[],
                raw_data=user,
            )
            post.compute_engagement_score()
            return post
        except Exception as e:
            logger.debug("Failed to parse Instagram user @%s: %s", username, e)
            return None

    @staticmethod
    def _parse_hashtag_as_post(hashtag_wrapper: dict[str, Any]) -> UnifiedPost | None:
        """Convert a search-result hashtag entry into a UnifiedPost."""
        hashtag = hashtag_wrapper.get("hashtag", hashtag_wrapper)
        if not isinstance(hashtag, dict):
            return None

        name = hashtag.get("name", "")
        if not name:
            return None

        media_count = int(hashtag.get("media_count", 0))
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
                     f"High-activity topic on Instagram that may be relevant for engagement.",
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
            logger.debug("Failed to parse Instagram hashtag #%s: %s", name, e)
            return None

    # ------------------------------------------------------------------
    # Dynamic response parsing (for unknown API formats)
    # ------------------------------------------------------------------

    def _extract_items(self, data: Any) -> list[dict[str, Any]]:
        """Extract items array from API response using configured json_path."""
        from app.services.infrastructure.platforms.dynamic_adapter import extract_json_path

        json_path = self.items_json_path
        # Strip leading $ if present (common user mistake)
        if json_path and json_path.startswith("$."):
            json_path = json_path[2:]

        items = extract_json_path(data, json_path)
        if isinstance(items, list):
            return items
        if isinstance(data, list):
            return data
        return []

    def _try_parse_users_from_items(self, items: list[dict[str, Any]]) -> list[UnifiedPost]:
        """Try to parse items as user profiles (various API formats)."""
        posts: list[UnifiedPost] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            # Try multiple field name patterns for user data
            username = item.get("username", item.get("user", {}).get("username", "") if isinstance(item.get("user"), dict) else "")
            if username:
                post = self._parse_user_as_post(item)
                if post:
                    posts.append(post)
        return posts

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
        """Search Instagram with user-first strategy.

        1. Shortens long keywords to Instagram-friendly queries
        2. Parses users first (up to 10 per keyword), hashtags second (up to 3)
        3. Falls back to DynamicAdapter-style parsing for unknown API formats
        """
        if not self._available:
            logger.warning("Instagram enhanced adapter not available")
            return []

        all_posts: list[UnifiedPost] = []
        seen_ids: set[str] = set()

        # Shorten keywords for Instagram search
        short_keywords = self._shorten_keywords(keywords, max_queries=8)
        logger.info("[instagram-enhanced] Shortened %d keywords → %d queries: %s",
                     len(keywords), len(short_keywords), short_keywords[:5])

        for query in short_keywords:
            if len(all_posts) >= limit:
                break

            try:
                data = await self.client.get(
                    self.search_endpoint,
                    params={self.search_param_name: query},
                )
            except RapidAPIError as e:
                logger.error("[instagram-enhanced] Search failed for '%s': %s", query, e)
                continue

            if not isinstance(data, (dict, list)):
                continue

            # ── Strategy 1: Known format (instagram-looter2 style) ──
            if isinstance(data, dict) and ("users" in data or "hashtags" in data):
                # Parse users FIRST (priority)
                users = data.get("users", [])
                for user_wrapper in users[:10]:
                    if not isinstance(user_wrapper, dict):
                        continue
                    post = self._parse_user_as_post(user_wrapper)
                    if post and post.external_id not in seen_ids:
                        seen_ids.add(post.external_id)
                        all_posts.append(post)

                # Parse hashtags SECOND (lower priority, fewer items)
                hashtags = data.get("hashtags", [])
                for hashtag_wrapper in hashtags[:3]:
                    if not isinstance(hashtag_wrapper, dict):
                        continue
                    post = self._parse_hashtag_as_post(hashtag_wrapper)
                    if post and post.external_id not in seen_ids:
                        seen_ids.add(post.external_id)
                        all_posts.append(post)

            # ── Strategy 2: Unknown format — try to find users in items ──
            else:
                items = self._extract_items(data)
                user_posts = self._try_parse_users_from_items(items[:10])
                for post in user_posts:
                    if post.external_id not in seen_ids:
                        seen_ids.add(post.external_id)
                        all_posts.append(post)

                # If no users found, fall back to DynamicAdapter LLM parsing
                if not user_posts and items:
                    logger.info("[instagram-enhanced] Unknown format for '%s', using LLM fallback", query)
                    try:
                        from app.services.infrastructure.platforms.dynamic_adapter import DynamicAdapter
                        dynamic = DynamicAdapter(self.config)
                        dynamic_posts = await dynamic.search_posts([query], limit=10)
                        for post in dynamic_posts:
                            if post.external_id not in seen_ids:
                                seen_ids.add(post.external_id)
                                all_posts.append(post)
                    except Exception as e:
                        logger.warning("[instagram-enhanced] LLM fallback failed: %s", e)

        logger.info(
            "[instagram-enhanced] Search across %d queries returned %d results",
            len(short_keywords), len(all_posts),
        )
        return all_posts[:limit]

    async def get_post_comments(
        self,
        post_id: str,
        *,
        limit: int = 20,
    ) -> list[UnifiedComment]:
        """Get comments — not supported by most Instagram APIs."""
        # If a comments endpoint is configured, try it
        comments_endpoint = self.config.get("comments_endpoint")
        if not comments_endpoint:
            return []

        param_name = self.config.get("comments_param_name", "id")
        try:
            data = await self.client.get(
                comments_endpoint,
                params={param_name: post_id},
            )
            items = self._extract_items(data)
            comments: list[UnifiedComment] = []
            for item in items[:limit]:
                if not isinstance(item, dict):
                    continue
                text = item.get("text", item.get("body", item.get("comment", "")))
                if not text:
                    continue
                c = UnifiedComment(
                    platform="instagram",
                    external_id=str(item.get("id", item.get("pk", ""))),
                    post_id=post_id,
                    author=str(item.get("username", item.get("author", "unknown"))),
                    author_id=str(item.get("user_id", "")),
                    body=str(text),
                    upvotes=int(item.get("like_count", item.get("likes", 0)) or 0),
                    created_at=None,
                    raw_data=item,
                )
                comments.append(c)
            return comments
        except Exception as e:
            logger.warning("[instagram-enhanced] Comments fetch failed: %s", e)
            return []

    async def get_trending(
        self,
        *,
        topic: str | None = None,
        limit: int = 25,
    ) -> list[UnifiedPost]:
        if not self._available:
            return []
        query = topic or "trending"
        return await self.search_posts([query], limit=limit)

    async def health_check(self) -> bool:
        if not self._available:
            return False
        try:
            await self.client.get(
                self.search_endpoint,
                params={self.search_param_name: "test"},
            )
            return True
        except Exception:
            return False
