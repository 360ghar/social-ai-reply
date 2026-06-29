"""Free-tier multi-source scraper.

Provides adapters for platforms that expose public data without paid API keys:
  - Reddit     — public JSON RSS (no auth, just rotate User-Agent)
  - HackerNews — Algolia search API (completely free, no key needed)
  - GitHub     — REST search API (60 req/hr unauthenticated, 5k with GH_TOKEN)
  - DuckDuckGo — HTML scraping for competitor discovery ("brand vs", "alternatives")

Each adapter returns a list of dicts matching the unified SocialPost schema so
the existing relevance engine can score them without modification.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared schema
# ---------------------------------------------------------------------------

@dataclass
class FreePost:
    """Unified post from any free source."""

    id: str
    source: str                    # "reddit" | "hackernews" | "github" | "ddg"
    platform: str = "reddit"       # matches existing platform enum in DB
    title: str = ""
    body: str = ""
    url: str = ""
    author: str = ""
    score: int = 0
    comments_count: int = 0
    subreddit: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    external_id: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "platform": self.platform,
            "title": self.title,
            "body": self.body,
            "url": self.url,
            "author": self.author,
            "score": self.score,
            "num_comments": self.comments_count,
            "subreddit": self.subreddit,
            "created_at": self.created_at.isoformat(),
            "external_id": self.external_id,
            "selftext": self.body,
            "permalink": self.url,
            "tags": self.tags,
        }


# ---------------------------------------------------------------------------
# Shared HTTP helpers
# ---------------------------------------------------------------------------

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_HEADERS = {
    "User-Agent": _UA,
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


def _get_json(url: str, params: dict | None = None, timeout: float = 15.0) -> Any:
    """Simple GET returning parsed JSON, or None on failure."""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=_HEADERS, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("GET %s failed: %s", url, exc)
        return None


def _get_html(url: str, params: dict | None = None, timeout: float = 15.0) -> str:
    """Simple GET returning HTML text, or empty string on failure."""
    headers = {**_HEADERS, "Accept": "text/html,application/xhtml+xml,*/*"}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            return resp.text
    except Exception as exc:
        logger.warning("HTML GET %s failed: %s", url, exc)
        return ""


# ---------------------------------------------------------------------------
# Reddit free JSON API
# ---------------------------------------------------------------------------

def scrape_reddit_json(
    keywords: list[str],
    subreddits: list[str],
    hours_back: int = 72,
    max_per_subreddit: int = 25,
) -> list[FreePost]:
    """Scrape Reddit via public .json endpoints — no auth required.

    Searches each subreddit for each keyword, deduplicates by post ID.
    Rotates the query so each (subreddit, keyword) pair gets at most one call.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=hours_back)
    seen: set[str] = set()
    posts: list[FreePost] = []

    for sub in subreddits:
        # Use a combined query for all keywords to minimise requests
        combined = " OR ".join(f'"{kw}"' if " " in kw else kw for kw in keywords[:8])
        url = f"https://www.reddit.com/r/{sub}/search.json"
        params = {
            "q": combined,
            "sort": "new",
            "restrict_sr": "1",
            "limit": max_per_subreddit,
            "t": "week",
        }
        data = _get_json(url, params=params)
        if not data:
            continue

        children = data.get("data", {}).get("children", [])
        for child in children:
            p = child.get("data", {})
            post_id = p.get("id", "")
            if not post_id or post_id in seen:
                continue
            seen.add(post_id)

            created = datetime.fromtimestamp(p.get("created_utc", 0), tz=UTC)
            if created < cutoff:
                continue

            posts.append(FreePost(
                id=f"reddit_{post_id}",
                source="reddit",
                platform="reddit",
                title=p.get("title", ""),
                body=p.get("selftext", ""),
                url=f"https://reddit.com{p.get('permalink', '')}",
                author=p.get("author", ""),
                score=p.get("score", 0),
                comments_count=p.get("num_comments", 0),
                subreddit=sub,
                created_at=created,
                external_id=post_id,
            ))
        time.sleep(0.5)  # be polite to Reddit

    logger.info("Reddit JSON scrape: %d posts from %d subreddits", len(posts), len(subreddits))
    return posts


# ---------------------------------------------------------------------------
# HackerNews — Algolia API (100% free, no key needed)
# ---------------------------------------------------------------------------

def scrape_hackernews(
    keywords: list[str],
    hours_back: int = 168,
    max_results: int = 30,
) -> list[FreePost]:
    """Search HackerNews via the Algolia API.

    URL: https://hn.algolia.com/api/v1/search
    Tags=story|comment, numericFilters for recency.
    Free, no authentication, 10k requests/hour.
    """
    cutoff_ts = int((datetime.now(UTC) - timedelta(hours=hours_back)).timestamp())
    seen: set[str] = set()
    posts: list[FreePost] = []

    for kw in keywords[:6]:  # cap queries to avoid hammering
        params = {
            "query": kw,
            "tags": "story",
            "numericFilters": f"created_at_i>{cutoff_ts}",
            "hitsPerPage": min(max_results, 20),
        }
        data = _get_json("https://hn.algolia.com/api/v1/search", params=params)
        if not data:
            continue

        for hit in data.get("hits", []):
            obj_id = hit.get("objectID", "")
            if not obj_id or obj_id in seen:
                continue
            seen.add(obj_id)

            created_ts = hit.get("created_at_i", 0)
            created = datetime.fromtimestamp(created_ts, tz=UTC) if created_ts else datetime.now(UTC)

            posts.append(FreePost(
                id=f"hn_{obj_id}",
                source="hackernews",
                platform="hackernews",
                title=hit.get("title", ""),
                body=hit.get("story_text") or hit.get("comment_text") or "",
                url=hit.get("url") or f"https://news.ycombinator.com/item?id={obj_id}",
                author=hit.get("author", ""),
                score=hit.get("points", 0),
                comments_count=hit.get("num_comments", 0),
                subreddit="",
                created_at=created,
                external_id=obj_id,
                tags=["hackernews"],
            ))
        time.sleep(0.2)

    logger.info("HackerNews scrape: %d posts across %d keywords", len(posts), min(len(keywords), 6))
    return posts


# ---------------------------------------------------------------------------
# GitHub — Issues + Discussions search (60 req/hr unauthenticated)
# ---------------------------------------------------------------------------

def scrape_github(
    keywords: list[str],
    hours_back: int = 168,
    max_results: int = 20,
    github_token: str | None = None,
) -> list[FreePost]:
    """Search GitHub issues and discussions for keyword mentions.

    Free without a token (60 req/hr). With GITHUB_TOKEN env var: 5,000 req/hr.
    """
    cutoff = (datetime.now(UTC) - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    headers = {**_HEADERS, "Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    seen: set[str] = set()
    posts: list[FreePost] = []

    for kw in keywords[:4]:  # conservative to stay within rate limit
        query = f"{kw} in:title,body created:>{cutoff}"
        params = {"q": query, "sort": "created", "order": "desc", "per_page": min(max_results, 10)}
        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                resp = client.get(
                    "https://api.github.com/search/issues",
                    headers=headers,
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("GitHub search failed for %r: %s", kw, exc)
            continue

        for item in data.get("items", []):
            item_id = str(item.get("id", ""))
            if not item_id or item_id in seen:
                continue
            seen.add(item_id)

            created_str = item.get("created_at", "")
            try:
                created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            except Exception:
                created = datetime.now(UTC)

            html_url = item.get("html_url", "")
            is_discussion = "discussions" in html_url
            posts.append(FreePost(
                id=f"gh_{item_id}",
                source="github",
                platform="github",
                title=item.get("title", ""),
                body=item.get("body") or "",
                url=html_url,
                author=item.get("user", {}).get("login", ""),
                score=item.get("reactions", {}).get("+1", 0),
                comments_count=item.get("comments", 0),
                subreddit="",
                created_at=created,
                external_id=item_id,
                tags=["github", "discussion" if is_discussion else "issue"],
            ))
        time.sleep(0.5)

    logger.info("GitHub scrape: %d results across %d keywords", len(posts), min(len(keywords), 4))
    return posts


# ---------------------------------------------------------------------------
# DuckDuckGo competitor discovery (no API, HTML scraping)
# ---------------------------------------------------------------------------

def find_competitors_ddg(
    company_name: str,
    max_results: int = 10,
) -> list[str]:
    """Find competitor names by scraping DuckDuckGo search results.

    Queries: "{company_name} vs", "{company_name} alternative"
    Extracts capitalized product names from result titles and snippets.
    No API key needed — uses the DDG HTML endpoint.

    Returns deduplicated list of competitor names.
    """
    competitors: list[str] = []
    seen: set[str] = set()

    queries = [
        f"{company_name} vs",
        f"{company_name} alternatives",
        f'"{company_name}" competitor',
    ]

    # Pattern: "X vs Y", "Compared to Y", "Better than Y", "Y vs X"
    vs_pattern = re.compile(
        r'\b(?:vs\.?|versus|vs|alternative(?:s)? to|compared to|unlike|better than)\s+'
        r'([A-Z][A-Za-z0-9][A-Za-z0-9\s\-\.]{1,30}?)(?:\s*[\.,\?\!\)]|$)',
        re.MULTILINE,
    )
    # Also capture "Y vs {company}" pattern
    reverse_pattern = re.compile(
        r'([A-Z][A-Za-z0-9][A-Za-z0-9\s\-\.]{1,30}?)\s+vs\.?\s+' + re.escape(company_name),
        re.IGNORECASE | re.MULTILINE,
    )

    for query in queries:
        html = _get_html(
            "https://html.duckduckgo.com/html/",
            params={"q": query, "kl": "wt-wt"},
        )
        if not html:
            continue

        # Extract text from result titles and snippets
        title_re = re.compile(r'class="result__a"[^>]*>(.*?)</a>', re.DOTALL)
        snippet_re = re.compile(r'class="result__snippet"[^>]*>(.*?)</(?:td|div)', re.DOTALL)
        tag_re = re.compile(r'<[^>]+>')

        texts: list[str] = []
        for m in title_re.finditer(html):
            texts.append(tag_re.sub(" ", m.group(1)))
        for m in snippet_re.finditer(html):
            texts.append(tag_re.sub(" ", m.group(1)))

        combined = " ".join(texts)

        for pattern in (vs_pattern, reverse_pattern):
            for m in pattern.finditer(combined):
                name = m.group(1).strip().rstrip(".")
                name_clean = re.sub(r'\s+', ' ', name)
                # Skip if it's the company itself or too generic
                if (
                    name_clean.lower() == company_name.lower()
                    or len(name_clean) < 2
                    or len(name_clean) > 40
                    or name_clean.lower() in {"the", "a", "an", "and", "or", "but"}
                ):
                    continue
                key = name_clean.lower()
                if key not in seen:
                    seen.add(key)
                    competitors.append(name_clean)

        time.sleep(1.0)  # DDG rate limit respect

    competitors = competitors[:max_results]
    logger.info("DDG competitor discovery for %r: found %s", company_name, competitors)
    return competitors


# ---------------------------------------------------------------------------
# Unified free scan — runs all sources in parallel via threads
# ---------------------------------------------------------------------------

def scan_free_sources(
    keywords: list[str],
    subreddits: list[str],
    hours_back: int = 72,
    include_hn: bool = True,
    include_github: bool = True,
    github_token: str | None = None,
) -> list[FreePost]:
    """Run Reddit, HN, and GitHub scrapers and merge results.

    Designed to be called from within a thread pool so it doesn't block the
    event loop. Returns a flat list sorted by score desc.
    """
    import concurrent.futures as cf

    results: list[FreePost] = []

    with cf.ThreadPoolExecutor(max_workers=3, thread_name_prefix="free_scraper") as pool:
        futures: dict[cf.Future, str] = {}

        futures[pool.submit(scrape_reddit_json, keywords, subreddits, hours_back)] = "reddit"
        if include_hn:
            futures[pool.submit(scrape_hackernews, keywords, hours_back)] = "hackernews"
        if include_github:
            futures[pool.submit(scrape_github, keywords, hours_back, 20, github_token)] = "github"

        for future, source in futures.items():
            try:
                batch = future.result(timeout=30)
                results.extend(batch)
                logger.info("Free source %r returned %d posts", source, len(batch))
            except Exception as exc:
                logger.warning("Free source %r failed: %s", source, exc)

    results.sort(key=lambda p: p.score, reverse=True)
    return results
