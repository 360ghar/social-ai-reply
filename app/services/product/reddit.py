import logging
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_SEARCH_VARIANT_STOP_WORDS = {
    "a",
    "an",
    "and",
    "every",
    "entire",
    "for",
    "how",
    "in",
    "of",
    "on",
    "or",
    "our",
    "physical",
    "physically",
    "simplifies",
    "the",
    "to",
    "while",
    "with",
}


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

    @property
    def url(self) -> str:
        return self.permalink

    @property
    def created_utc(self) -> int:
        created_at = self.created_at if self.created_at.tzinfo else self.created_at.replace(tzinfo=UTC)
        return int(created_at.timestamp())

    def as_discovery_record(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "body": self.body,
            "subreddit": self.subreddit,
            "url": self.url,
            "score": self.score,
            "num_comments": self.num_comments,
            "created_utc": self.created_utc,
        }


def _chunk_keywords(keywords: list[str], size: int) -> list[list[str]]:
    return [keywords[idx:idx + size] for idx in range(0, len(keywords), size)]


def _smart_group_keywords(keywords: list[str], size: int) -> list[list[str]]:
    """Group keywords by token overlap so semantically related terms
    are searched together.  Falls back to positional chunking when
    there's no overlap.
    """
    if len(keywords) <= size:
        return [keywords] if keywords else []

    # Build token sets for each keyword
    kw_tokens = [(kw, set(kw.lower().split())) for kw in keywords]
    used: set[int] = set()
    groups: list[list[str]] = []

    for i, (kw, tokens) in enumerate(kw_tokens):
        if i in used:
            continue
        group = [kw]
        used.add(i)
        for j, (other_kw, other_tokens) in enumerate(kw_tokens):
            if j in used:
                continue
            if len(group) >= size:
                break
            # Group if keywords share at least one meaningful token
            shared = tokens & other_tokens
            # Exclude very short shared tokens (e.g. "ai", "vr")
            meaningful_shared = {t for t in shared if len(t) >= 3}
            if meaningful_shared:
                group.append(other_kw)
                used.add(j)
        groups.append(group)

    # Pick up any remaining ungrouped keywords
    remaining = [kw for i, (kw, _) in enumerate(kw_tokens) if i not in used]
    if remaining:
        groups.extend(_chunk_keywords(remaining, size))

    return groups


def _build_search_query(subreddit: str, keywords: list[str]) -> str:
    cleaned = [keyword.strip().replace('"', "") for keyword in keywords if keyword and keyword.strip()]
    if not cleaned:
        return f"subreddit:{subreddit}"
    quoted = [f'"{keyword}"' for keyword in cleaned]
    if len(quoted) == 1:
        return f"subreddit:{subreddit} {quoted[0]}"
    return f"subreddit:{subreddit} ({' OR '.join(quoted)})"


def _search_keyword_variants(keyword: str) -> list[str]:
    cleaned = keyword.strip().replace('"', "")
    if not cleaned:
        return []

    variants = [cleaned]
    lowered_tokens = [token for token in cleaned.lower().split() if token]
    meaningful_tokens = [
        token for token in lowered_tokens
        if len(token) >= 3 and token not in _SEARCH_VARIANT_STOP_WORDS
    ]

    if len(meaningful_tokens) >= 2:
        variants.append(" ".join(meaningful_tokens[:3]))
        variants.append(" ".join(meaningful_tokens[-2:]))
        if len(meaningful_tokens) >= 3:
            variants.append(" ".join(meaningful_tokens[-3:]))

    deduped: list[str] = []
    seen: set[str] = set()
    for variant in variants:
        normalized = " ".join(variant.split())
        if len(normalized) < 3 or normalized in seen:
            continue
        deduped.append(normalized)
        seen.add(normalized)
    return deduped


def _rerank_by_keyword_relevance(posts: list[RedditPost], keywords: list[str]) -> list[RedditPost]:
    """Sort *posts* by keyword relevance first, then by recency.

    Posts that match more keywords are returned first.  Among posts with
    equal keyword relevance the most recent ones come first.

    Improvements over the original:
    - Title matches are worth 2x body-only matches (title = core topic).
    - Multi-word keyword matches score higher than single-word (more specific).
    - Upvotes provide a small tiebreaker for equally relevant posts.
    """
    lowered_keywords = [kw.lower() for kw in keywords]

    def _score(post: RedditPost) -> tuple[int, float]:
        title_lower = post.title.lower()
        body_lower = post.body.lower()
        full_text = f"{title_lower} {body_lower}"
        tokens = set(full_text.split())
        relevance = 0
        for kw in lowered_keywords:
            word_count = len(kw.split())
            specificity_mult = 2 if word_count >= 2 else 1
            if kw in title_lower:
                # Title match: highest value
                relevance += 5 * specificity_mult
            elif kw in full_text:
                # Body-only match
                relevance += 3 * specificity_mult
            elif " " in kw:
                kw_tokens = kw.split()
                if sum(1 for t in kw_tokens if t in tokens) >= len(kw_tokens) - 1:
                    relevance += 1
        # Small upvote tiebreaker (0–2 points)
        upvote_bonus = min(post.score // 50, 2) if post.score > 0 else 0
        return relevance + upvote_bonus, post.created_at.timestamp()

    return sorted(posts, key=_score, reverse=True)


class RedditClient:
    """Legacy Reddit client wrapper.

    Read-only discovery calls delegate to `RedditDiscoveryService`, which works
    without Reddit OAuth. The lower-level `_get()` path is retained for the
    remaining posting/status functionality and for future provider swaps.
    """

    _OAUTH_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    _OAUTH_BASE_URL = "https://oauth.reddit.com"
    # Refresh slightly before the advertised expiry to avoid edge-case 401s.
    _TOKEN_REFRESH_MARGIN_SECONDS = 60

    def __init__(self) -> None:
        settings = get_settings()
        self._client_id = (settings.reddit_client_id or "").strip() or None
        self._client_secret = (settings.reddit_client_secret or "").strip() or None
        self._oauth_enabled = bool(self._client_id and self._client_secret)
        self._discovery_service: Any | None = None

        if self._oauth_enabled:
            self.base_url = self._OAUTH_BASE_URL
        else:
            self.base_url = settings.reddit_base_url.rstrip("/")

        self.headers = {"User-Agent": settings.reddit_user_agent}
        self.timeout = 12.0
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True,
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._last_request_time: float = 0.0
        self._min_interval: float = 0.75
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    def __del__(self) -> None:
        with suppress(Exception):
            self._client.close()

    # ── OAuth helpers ───────────────────────────────────────────────
    def _ensure_access_token(self, *, force_refresh: bool = False) -> str | None:
        """Return a valid bearer token, refreshing if needed. Returns
        ``None`` when OAuth is not configured (public mode)."""
        if not self._oauth_enabled:
            return None
        if not force_refresh and self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        try:
            response = httpx.post(
                self._OAUTH_TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(self._client_id or "", self._client_secret or ""),
                headers={"User-Agent": self.headers["User-Agent"]},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            logger.warning("Failed to fetch Reddit OAuth token: %s", exc)
            # Don't keep retrying on every call — wait before next attempt.
            self._access_token = None
            self._token_expires_at = time.time() + 30
            raise
        token = payload.get("access_token")
        expires_in = int(payload.get("expires_in") or 3600)
        if not token:
            raise RuntimeError("Reddit OAuth token response did not include access_token.")
        self._access_token = token
        self._token_expires_at = time.time() + max(expires_in - self._TOKEN_REFRESH_MARGIN_SECONDS, 60)
        return token

    def _auth_headers(self) -> dict[str, str]:
        token = self._ensure_access_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def _cache_key(self, path: str, params: dict[str, Any] | None = None) -> str:
        if not params:
            return path
        return f"{path}?{urlencode(sorted(params.items()), doseq=True)}"

    def _get_discovery_service(self):
        if self._discovery_service is None:
            from app.services.product.reddit_discovery import RedditDiscoveryService

            self._discovery_service = RedditDiscoveryService()
        return self._discovery_service

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        cache_key = self._cache_key(path, params)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

        response: httpx.Response | None = None
        for attempt in range(3):
            try:
                response = self._client.get(path, params=params, headers=self._auth_headers())
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                logger.warning("Reddit connection error on %s (attempt %d/3): %s", path, attempt + 1, exc)
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise
            self._last_request_time = time.monotonic()
            if response.status_code == 401 and self._oauth_enabled:
                # Token may have been revoked/expired — force a refresh and retry.
                logger.info("Reddit 401 on %s; refreshing OAuth token and retrying", path)
                try:
                    self._ensure_access_token(force_refresh=True)
                except httpx.HTTPError:
                    response.raise_for_status()
                continue
            if response.status_code == 429:
                wait = min(2 ** attempt * 2, 10)
                logger.warning(
                    "Reddit 429 rate-limited on %s; waiting %ds (attempt %d/3)",
                    path,
                    wait,
                    attempt + 1,
                )
                time.sleep(wait)
                continue
            if response.status_code >= 400:
                logger.warning("Reddit HTTP %d on %s params=%s", response.status_code, path, params)
            response.raise_for_status()
            payload = response.json()
            self._cache[cache_key] = payload
            return payload

        if response is None:
            raise RuntimeError(f"Reddit request did not execute for {path}")
        response.raise_for_status()
        return response.json()

    def search_subreddits(self, keyword: str, limit: int = 10) -> list[RedditSubredditMatch]:
        return self._get_discovery_service().search_subreddits(keyword, limit=limit)

    def list_subreddit_posts(self, subreddit: str, sort: str = "hot", limit: int = 10) -> list[RedditPost]:
        return self._get_discovery_service().list_subreddit_posts(subreddit, sort=sort, limit=limit)

    def subreddit_about(self, name: str) -> dict[str, Any]:
        return self._get_discovery_service().subreddit_about(name)

    def subreddit_rules(self, name: str) -> list[str]:
        return self._get_discovery_service().subreddit_rules(name)

    def search_posts(self, subreddit: str, keywords: list[str], limit: int = 20, sort: str = "new") -> list[RedditPost]:
        return self._get_discovery_service().search_posts(keywords, subreddits=[subreddit], limit=limit)[:limit]

        if not keywords:
            return []

        per_query_limit = max(3, min(limit, 10))
        posts_by_id: dict[str, RedditPost] = {}

        # ── Phase 1: grouped keyword search ─────────────────────────
        # Group keywords by token overlap so semantically related terms
        # are searched together, producing more focused results.
        ordered_keywords = keywords[:12]
        keyword_groups = _smart_group_keywords(ordered_keywords, size=4)

        for group in keyword_groups:
            query = _build_search_query(subreddit, group)
            try:
                data = self._get("/search.json", params={"q": query, "sort": sort, "limit": per_query_limit})
            except httpx.HTTPError:
                continue
            self._merge_posts(posts_by_id, data, subreddit)

        # ── Phase 2: single-keyword fallback ────────────────────────
        if not posts_by_id and len(keyword_groups) > 1:
            for keyword in ordered_keywords[:6]:
                query = _build_search_query(subreddit, [keyword])
                try:
                    data = self._get("/search.json", params={"q": query, "sort": sort, "limit": per_query_limit})
                except httpx.HTTPError:
                    continue
                self._merge_posts(posts_by_id, data, subreddit)

        # Phase 2b: if exact phrases only yielded a handful of posts,
        # broaden the search with compressed phrase variants such as
        # "transaction process" instead of "entire transaction process".
        low_yield_threshold = max(2, min(limit // 3, 4))
        if len(posts_by_id) <= low_yield_threshold:
            for keyword in ordered_keywords[:8]:
                variants = _search_keyword_variants(keyword)[1:]
                for variant in variants[:2]:
                    query = _build_search_query(subreddit, [variant])
                    try:
                        data = self._get("/search.json", params={"q": query, "sort": sort, "limit": per_query_limit})
                    except httpx.HTTPError:
                        continue
                    self._merge_posts(posts_by_id, data, subreddit)
                if len(posts_by_id) >= limit:
                    break

        # ── Phase 3: rerank by keyword relevance ────────────────────
        # Instead of sorting purely by recency, score each post by how
        # many search keywords it actually contains, weighted by whether
        # the match is an exact phrase or just token overlap.
        posts = _rerank_by_keyword_relevance(list(posts_by_id.values()), ordered_keywords)
        return posts[:limit]

    def _merge_posts(self, posts_by_id: dict[str, RedditPost], data: dict[str, Any], subreddit: str) -> None:
        for child in data.get("data", {}).get("children", []):
            payload = child.get("data", {})
            post = self._parse_post_payload(payload, subreddit)
            if post.post_id and post.title and post.subreddit.lower() == subreddit.lower():
                posts_by_id[post.post_id] = post

    def _parse_post_payload(self, payload: dict[str, Any], subreddit: str) -> RedditPost:
        created_ts = float(payload.get("created_utc") or 0.0)
        return RedditPost(
            post_id=payload.get("id", ""),
            subreddit=payload.get("subreddit", subreddit),
            title=payload.get("title", ""),
            author=payload.get("author", "[deleted]"),
            permalink=f"https://www.reddit.com{payload.get('permalink', '')}",
            body=payload.get("selftext", "") or "",
            created_at=datetime.fromtimestamp(created_ts, tz=UTC) if created_ts else datetime.now(UTC),
            num_comments=int(payload.get("num_comments") or 0),
            score=int(payload.get("score") or 0),
        )

    @staticmethod
    def _keyword_relevance_score(post: RedditPost, keywords: list[str]) -> int:
        """Score how many *keywords* are present in the post text.

        Exact-phrase matches contribute 3 points, partial token overlap
        contributes 1 point.  The result is used purely for ordering — the
        real opportunity score is computed separately by ``score_post``.
        """
        text = f"{post.title} {post.body}".lower()
        tokens = set(text.split())
        relevance = 0
        for kw in keywords:
            if kw in text:
                relevance += 3
            elif " " in kw:
                kw_tokens = kw.split()
                if sum(1 for t in kw_tokens if t in tokens) >= len(kw_tokens) - 1:
                    relevance += 1
        return relevance

    def post_comment(self, subreddit: str, parent_id: str, text: str) -> str:
        raise NotImplementedError

    def post_thread(self, subreddit: str, title: str, body: str) -> str:
        raise NotImplementedError

    def get_post_stats(self, reddit_id: str) -> dict[str, Any]:
        try:
            data = self._get(f"/{reddit_id}.json")
        except httpx.HTTPError:
            return {}
        children = data if isinstance(data, list) else data.get("data", {}).get("children", [])
        if not children:
            return {}
        post_data = (
            children[0].get("data", {}).get("children", [{}])[0].get("data", {})
            if isinstance(children[0].get("data"), dict) and "children" in children[0].get("data", {})
            else (children[0].get("data", {}) if isinstance(children[0], dict) else {})
        )
        return {
            "upvotes": post_data.get("score", 0),
            "num_comments": post_data.get("num_comments", 0),
            "removed": post_data.get("removed_by_category") is not None,
            "removal_reason": post_data.get("removed_by_category"),
        }
