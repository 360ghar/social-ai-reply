"""Reddit3 platform adapter — smart scanning via reddit3.p.rapidapi.com.

Uses the Reddit3 API from RapidAPI marketplace which exposes:
  - GET /v1/search?search=...          — search across all of Reddit
  - GET /v1/subreddit?name=...         — browse a specific subreddit
  - GET /v1/post-details?post_id=...   — post details with comments

Scanning strategy:
  1. Keyword search → discover relevant subreddits from results
  2. Browse top discovered subreddits for more posts
  3. Fetch comments on high-engagement posts (converted to pseudo-posts)
  Budget: ~5-8 API calls per scan
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from app.services.infrastructure.platforms.base import PlatformAdapter
from app.services.infrastructure.platforms.models import UnifiedComment, UnifiedPost
from app.services.infrastructure.platforms.rapidapi_client import RapidAPIClient, RapidAPIError

logger = logging.getLogger(__name__)


class Reddit3Adapter(PlatformAdapter):
    """Reddit adapter using the Reddit3 RapidAPI (reddit3.p.rapidapi.com).

    Smart scanning flow:
      1. Search keywords → get posts + discover subreddit names
      2. Browse top 3 discovered subreddits for additional posts
      3. Fetch comments on top-scoring posts
    """

    platform_name = "reddit"

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.config = config
        self.api_host = config.get("api_host", "reddit3.p.rapidapi.com")
        self.search_endpoint = config.get("search_endpoint", "/v1/reddit/search")
        self.search_param_name = config.get("search_param_name", "search")

        # Derive subreddit endpoint from search endpoint (e.g., /v1/reddit/search -> /v1/reddit/subreddit/popular)
        base_path = self.search_endpoint.rsplit("/", 1)[0]  # /v1/reddit
        self.subreddit_endpoint = f"{base_path}/subreddit/popular"

        self.comments_endpoint = config.get("comments_endpoint")
        self.comments_param_name = config.get("comments_param_name", "post_id")

        api_key = config.get("api_key")
        self._subreddits: list[str] = []
        try:
            self.client = RapidAPIClient(self.api_host, api_key=api_key)
            self._available = True
        except ValueError:
            logger.warning("RapidAPI key not configured — Reddit3 adapter unavailable")
            self._available = False

    def set_subreddits(self, subreddits: list[str]) -> None:
        """Set monitored subreddits for filtering/prioritization."""
        self._subreddits = [s.lower().replace("r/", "") for s in subreddits]

    # ------------------------------------------------------------------
    # Internal API helpers
    # ------------------------------------------------------------------

    async def _api_get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request via the RapidAPIClient."""
        if not self._available or not self.client:
            return {}
        try:
            data = await self.client.get(endpoint, params=params)
            return data if isinstance(data, dict) else {"items": data} if isinstance(data, list) else {}
        except RapidAPIError as e:
            logger.warning("[reddit3] API call %s failed: %s", endpoint, e)
            raise

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_post(item: dict[str, Any]) -> UnifiedPost | None:
        """Parse a Reddit3 API post item into UnifiedPost."""
        if not isinstance(item, dict):
            return None

        external_id = str(item.get("id", item.get("name", "")))
        if not external_id:
            return None

        subreddit = str(item.get("subreddit", ""))
        if subreddit.startswith("r/"):
            subreddit = subreddit[2:]

        permalink = str(item.get("permalink", ""))
        if permalink and not permalink.startswith("http"):
            permalink = f"https://www.reddit.com{permalink}"

        created_utc = item.get("created_utc") or item.get("created")
        created_at = None
        if created_utc and isinstance(created_utc, (int, float)):
            with contextlib.suppress(ValueError, OSError):
                created_at = datetime.fromtimestamp(created_utc, tz=UTC)

        title = str(item.get("title", ""))
        body = str(item.get("selftext", item.get("body", "")))
        author = str(item.get("author", "unknown"))
        upvotes = int(item.get("ups", item.get("score", 0)) or 0)
        comments_count = int(item.get("num_comments", 0) or 0)

        try:
            post = UnifiedPost(
                platform="reddit",
                external_id=external_id,
                author=author,
                author_id=str(item.get("author_fullname", "")),
                title=title,
                body=body,
                url=permalink,
                subreddit=subreddit,
                upvotes=upvotes,
                comments_count=comments_count,
                shares=0,
                views=0,
                created_at=created_at,
                media_urls=[],
                raw_data={},
            )
            post.compute_engagement_score()
            return post
        except Exception as e:
            logger.debug("Failed to parse Reddit3 post %s: %s", external_id, e)
            return None

    @staticmethod
    def _parse_comment_as_post(item: dict[str, Any]) -> UnifiedPost | None:
        """Convert a comment into a pseudo-post for opportunity scoring."""
        if not isinstance(item, dict):
            return None

        body = str(item.get("body", item.get("text", "")))
        if not body or len(body) < 20:
            return None

        external_id = f"comment_{item.get('id', item.get('name', ''))}"
        subreddit = str(item.get("subreddit", ""))
        if subreddit.startswith("r/"):
            subreddit = subreddit[2:]

        permalink = str(item.get("permalink", ""))
        if permalink and not permalink.startswith("http"):
            permalink = f"https://www.reddit.com{permalink}"

        created_utc = item.get("created_utc")
        created_at = None
        if created_utc and isinstance(created_utc, (int, float)):
            with contextlib.suppress(ValueError, OSError):
                created_at = datetime.fromtimestamp(created_utc, tz=UTC)

        # Use parent post title if available, otherwise use comment body truncated
        title = str(item.get("link_title", body[:100]))

        try:
            post = UnifiedPost(
                platform="reddit",
                external_id=external_id,
                author=str(item.get("author", "unknown")),
                author_id="",
                title=title,
                body=body,
                url=permalink,
                subreddit=subreddit,
                upvotes=int(item.get("score", item.get("ups", 0)) or 0),
                comments_count=0,
                shares=0,
                views=0,
                created_at=created_at,
                media_urls=[],
                raw_data={"source_type": "comment"},
            )
            post.compute_engagement_score()
            return post
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Broad term extraction (reused from RedditAdapter)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_broad_terms(keywords: list[str], subreddits: list[str]) -> list[str]:
        """Extract short, broad search terms from specific keyword phrases.

        Discovery keywords are often very specific (e.g. "tired of fake property
        listings gurugram").  Reddit search works better with short 1-2 word terms
        like "real estate" or "property investment".
        """
        stop_words = {
            "with", "from", "that", "this", "have", "will", "your", "what",
            "when", "where", "which", "there", "their", "about", "been",
            "some", "them", "than", "just", "also", "into", "most", "much",
            "know", "find", "need", "good", "best", "hard", "many", "very",
            "more", "like", "make", "does", "each", "only", "over", "such",
            "take", "even", "well", "back", "give", "want", "someone",
            "tired", "platform", "service", "online", "operators", "founders",
            "workflows", "assisted", "noise", "trusted", "verified",
        }

        word_freq: Counter[str] = Counter()
        for kw in keywords:
            words = kw.lower().split()
            for w in words:
                w = w.strip(".,!?;:'\"()[]")
                if len(w) >= 4 and w not in stop_words:
                    word_freq[w] += 1

        top_words = [w for w, _ in word_freq.most_common(15)]

        queries: list[str] = []
        seen: set[str] = set()

        # 2-word combinations from top words
        for i, w1 in enumerate(top_words[:8]):
            for w2 in top_words[i + 1 : i + 4]:
                term = f"{w1} {w2}"
                if term not in seen:
                    queries.append(term)
                    seen.add(term)

        # Add subreddit names as search terms
        for sub in subreddits[:5]:
            sub_clean = sub.lower().replace("_", " ")
            if sub_clean not in seen and len(sub_clean) >= 4:
                queries.append(sub_clean)
                seen.add(sub_clean)

        # Add single high-frequency domain words
        for w in top_words[:5]:
            if w not in seen:
                queries.append(w)
                seen.add(w)

        return queries[:10]

    # ------------------------------------------------------------------
    # Core scanning methods
    # ------------------------------------------------------------------

    async def search_posts(
        self,
        keywords: list[str],
        *,
        limit: int = 50,
        sort: str = "relevance",
        time_filter: str = "week",
    ) -> list[UnifiedPost]:
        """Search Reddit via Reddit3 API and discover subreddits."""
        if not self._available:
            return []

        all_posts: list[UnifiedPost] = []
        seen_ids: set[str] = set()

        # Extract broad search terms
        broad_terms = self._extract_broad_terms(keywords, self._subreddits)
        logger.info("[reddit3] Broad search terms: %s", broad_terms[:8])

        # Build 2 OR-combined queries for search
        queries: list[str] = []
        if broad_terms:
            queries.append(" OR ".join(broad_terms[:4]))
            if len(broad_terms) > 4:
                queries.append(" OR ".join(broad_terms[4:8]))

        if not queries:
            queries = ["discussion advice help"]

        # ── Step 1: Keyword search (1-2 API calls) ──
        discovered_subreddits: Counter[str] = Counter()

        for query in queries[:2]:
            try:
                data = await self._api_get(
                    self.search_endpoint,
                    params={self.search_param_name: query},
                )
                posts_raw = data.get("body", data.get("data", {}).get("posts", []))
                if not isinstance(posts_raw, list):
                    posts_raw = []

                for item in posts_raw:
                    post = self._parse_post(item)
                    if post and post.external_id not in seen_ids:
                        all_posts.append(post)
                        seen_ids.add(post.external_id)
                        # Track subreddits for discovery
                        if post.subreddit:
                            discovered_subreddits[post.subreddit.lower()] += 1

                logger.info("[reddit3] Search '%s' → %d posts", query[:50], len(posts_raw))
            except Exception as e:
                logger.warning("[reddit3] Search failed for '%s': %s", query[:40], e)

            if len(queries) > 1:
                await asyncio.sleep(0.5)

        # ── Step 2: Browse top discovered subreddits (2-3 API calls) ──
        # Combine user-monitored subreddits with discovered ones
        priority_subs = list(self._subreddits)
        for sub, _count in discovered_subreddits.most_common(5):
            if sub not in priority_subs:
                priority_subs.append(sub)

        # Browse top 3 subreddits for additional posts
        for sub_name in priority_subs[:3]:
            try:
                data = await self._api_get(
                    self.subreddit_endpoint,
                    params={"name": sub_name},
                )
                posts_raw = data.get("body", [])
                if not isinstance(posts_raw, list):
                    posts_raw = []

                new_count = 0
                for item in posts_raw[:15]:
                    post = self._parse_post(item)
                    if post and post.external_id not in seen_ids:
                        all_posts.append(post)
                        seen_ids.add(post.external_id)
                        new_count += 1

                logger.info("[reddit3] Subreddit r/%s → %d new posts", sub_name, new_count)
            except Exception as e:
                logger.warning("[reddit3] Subreddit browse r/%s failed: %s", sub_name, e)

            await asyncio.sleep(0.5)

        # ── Step 3: Fetch comments on top posts (1-2 API calls) ──
        # Sort by engagement and fetch details for top posts
        top_posts = sorted(all_posts, key=lambda p: p.engagement_score, reverse=True)[:3]

        if self.comments_endpoint:
            for post in top_posts:
                if post.external_id.startswith("comment_"):
                    continue
                try:
                    data = await self._api_get(
                        self.comments_endpoint,
                        params={self.comments_param_name: post.external_id},
                    )
                    comments_raw = data.get("body", {})
                    if isinstance(comments_raw, dict):
                        comments_raw = comments_raw.get("comments", [])
                    if not isinstance(comments_raw, list):
                        comments_raw = []

                    for comment_item in comments_raw[:10]:
                        comment_post = self._parse_comment_as_post(comment_item)
                        if comment_post and comment_post.external_id not in seen_ids:
                            all_posts.append(comment_post)
                            seen_ids.add(comment_post.external_id)

                    logger.info("[reddit3] Post %s → %d comments", post.external_id[:20], len(comments_raw))
                except Exception as e:
                    logger.warning("[reddit3] Post details failed for %s: %s", post.external_id[:20], e)

                await asyncio.sleep(0.5)

        # ── Step 4: Filter by monitored subreddits ──
        if self._subreddits:
            sub_set = {s.lower() for s in self._subreddits}
            before = len(all_posts)
            filtered = []
            for post in all_posts:
                if post.subreddit and post.subreddit.lower() in sub_set:
                    filtered.append(post)
                elif post.upvotes >= 5 or post.comments_count >= 3:
                    # Keep high-engagement posts from non-monitored subreddits
                    filtered.append(post)
                elif post.external_id.startswith("comment_"):
                    # Always keep comments (already filtered to relevant posts)
                    filtered.append(post)
            all_posts = filtered
            logger.info("[reddit3] Filtered %d → %d posts (monitored subs + high engagement)", before, len(all_posts))

        logger.info("[reddit3] Total: %d posts from smart scan", len(all_posts))
        return all_posts[:limit]

    async def search_and_enrich(
        self,
        keywords: list[str],
        *,
        limit: int = 50,
        fetch_comments: bool = False,
        comments_per_post: int = 10,
        time_filter: str = "week",
    ) -> list[UnifiedPost]:
        """Override base — our search_posts already does subreddit discovery + comments."""
        return await self.search_posts(keywords, limit=limit, time_filter=time_filter)

    async def get_post_comments(
        self,
        post_id: str,
        *,
        limit: int = 20,
    ) -> list[UnifiedComment]:
        """Fetch comments for a specific post."""
        if not self._available or not self.comments_endpoint:
            return []
        try:
            data = await self._api_get(
                self.comments_endpoint,
                params={self.comments_param_name: post_id},
            )
            comments_raw = data.get("body", {})
            if isinstance(comments_raw, dict):
                comments_raw = comments_raw.get("comments", [])
            if not isinstance(comments_raw, list):
                return []

            comments: list[UnifiedComment] = []
            for item in comments_raw[:limit]:
                if not isinstance(item, dict):
                    continue
                body = str(item.get("body", item.get("text", "")))
                if not body:
                    continue
                c = UnifiedComment(
                    platform="reddit",
                    external_id=str(item.get("id", "")),
                    post_id=post_id,
                    author=str(item.get("author", "unknown")),
                    author_id="",
                    body=body,
                    upvotes=int(item.get("score", item.get("ups", 0)) or 0),
                    created_at=None,
                    raw_data=item,
                )
                comments.append(c)
            return comments
        except Exception as e:
            logger.warning("[reddit3] Failed to get comments for %s: %s", post_id, e)
            return []

    async def get_trending(
        self,
        *,
        topic: str | None = None,
        limit: int = 25,
    ) -> list[UnifiedPost]:
        """Get trending posts via search."""
        if not self._available:
            return []
        query = topic or "trending"
        return await self.search_posts([query], limit=limit)

    async def health_check(self) -> bool:
        """Verify the Reddit3 API is reachable."""
        if not self._available:
            return False
        try:
            await self._api_get(self.search_endpoint, params={self.search_param_name: "test"})
            return True
        except Exception:
            return False
