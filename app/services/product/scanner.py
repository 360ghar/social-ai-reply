"""Reddit scanning and opportunity detection service."""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import HTTPException

from app.db.tables.discovery import (
    create_opportunity,
    get_opportunity_by_project_and_reddit_post,
    update_opportunity,
)
from app.db.tables.projects import get_brand_profile_by_project

if TYPE_CHECKING:
    from supabase import Client

    from app.schemas.v1.discovery import ScanRequest
from app.services.product.discovery import get_project_search_keywords
from app.services.product.reddit import RedditClient, RedditPost
from app.services.product.scoring import (
    MIN_RELEVANT_OPPORTUNITY_SCORE,
    MIN_SUBREDDIT_FIT_FOR_AUTOMATION,
    score_post,
)

logger = logging.getLogger(__name__)


def run_scan(db: Client, project: dict, payload: ScanRequest) -> dict:
    """Run a scan for opportunities based on project keywords and subreddits."""
    reddit = RedditClient()
    brand = get_brand_profile_by_project(db, project["id"])

    # Get active keywords
    from app.db.tables.discovery import list_discovery_keywords_for_project
    active_keywords = list_discovery_keywords_for_project(db, project["id"])
    active_keywords = [k for k in active_keywords if k.get("is_active", True)]
    active_keywords.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

    # Get active subreddits
    from app.db.tables.discovery import list_monitored_subreddits_for_project
    active_subreddits = list_monitored_subreddits_for_project(db, project["id"])
    active_subreddits = [s for s in active_subreddits if s.get("is_active", True)]
    active_subreddits.sort(key=lambda x: x.get("fit_score", 0), reverse=True)

    if not active_keywords:
        raise HTTPException(status_code=400, detail="Add discovery keywords before scanning.")
    if not active_subreddits:
        raise HTTPException(status_code=400, detail="Add monitored subreddits before scanning.")

    search_keywords = get_project_search_keywords(db, project, limit=12)
    if not search_keywords:
        raise HTTPException(status_code=400, detail="Add more specific discovery keywords before scanning.")

    # Create scan run record
    from app.db.tables.discovery import create_scan_run
    run = create_scan_run(db, {
        "project_id": project["id"],
        "status": "running",
        "search_window_hours": payload.search_window_hours,
        "started_at": datetime.now(UTC).isoformat(),
    })

    try:
        posts_scanned = 0
        opportunities_found = 0
        cutoff = datetime.now(UTC) - timedelta(hours=payload.search_window_hours)
        effective_min_score = max(payload.min_score, MIN_RELEVANT_OPPORTUNITY_SCORE)
        rules_cache: dict[str, list[str]] = {}

        for subreddit in active_subreddits:
            if subreddit.get("fit_score", 0) < MIN_SUBREDDIT_FIT_FOR_AUTOMATION:
                continue
            rules = rules_cache.setdefault(subreddit["name"].lower(), _safe_subreddit_rules(reddit, subreddit["name"]))
            try:
                posts = reddit.search_posts(subreddit["name"], search_keywords, limit=payload.max_posts_per_subreddit)
            except Exception:
                continue
            for post in posts:
                if post.created_at and post.created_at < cutoff.replace(tzinfo=None if post.created_at.tzinfo is None else UTC):
                    continue
                posts_scanned += 1
                score = score_post(post, brand, subreddit, search_keywords, rules)
                if not score.eligible or score.total < effective_min_score:
                    continue

                # Check if opportunity already exists
                opportunity = get_opportunity_by_project_and_reddit_post(db, project["id"], post.post_id)
                if opportunity:
                    update_opportunity(db, opportunity["id"], {
                        "score": score.total,
                        "score_reasons": score.reasons,
                        "keyword_hits": score.keyword_hits,
                        "rule_risk": score.rule_risk,
                        "body_excerpt": post.body[:1200],
                        "permalink": post.permalink,
                    })
                else:
                    create_opportunity(db, {
                        "project_id": project["id"],
                        "scan_run_id": run["id"],
                        "reddit_post_id": post.post_id,
                        "title": post.title,
                        "author": post.author,
                        "subreddit_name": subreddit["name"],
                        "body_excerpt": post.body[:1200],
                        "permalink": post.permalink,
                        "score": score.total,
                        "score_reasons": score.reasons,
                        "keyword_hits": score.keyword_hits,
                        "rule_risk": score.rule_risk,
                        "status": "new",
                    })
                    opportunities_found += 1

        # Update scan run with results
        from app.db.tables.discovery import get_scan_run_by_id, update_scan_run
        update_scan_run(db, run["id"], {
            "status": "completed",
            "posts_scanned": posts_scanned,
            "opportunities_found": opportunities_found,
            "completed_at": datetime.now(UTC).isoformat(),
        })

        # Return full scan run record
        updated_run = get_scan_run_by_id(db, run["id"])
        return updated_run
    except Exception as e:
        logger.exception("Scan failed")
        update_scan_run(db, run["id"], {
            "status": "error",
            "error_message": str(e)[:500],
            "completed_at": datetime.now(UTC).isoformat(),
        })
        raise


def _safe_subreddit_rules(reddit: RedditClient, subreddit_name: str) -> list[str]:
    """Safely fetch subreddit rules with a timeout."""
    try:
        return reddit.get_subreddit_rules(subreddit_name)
    except Exception:
        return []


def revalidate_opportunity(db: Client, project: dict, opportunity: dict) -> tuple[bool, int]:
    """Re-score an opportunity to ensure it still meets the threshold.

    Uses stored opportunity data since we don't have real-time Reddit access.
    """
    brand = get_brand_profile_by_project(db, project["id"])

    from app.db.tables.discovery import list_discovery_keywords_for_project, list_monitored_subreddits_for_project
    keywords = [k["keyword"] for k in list_discovery_keywords_for_project(db, project["id"]) if k.get("is_active", True)]
    subreddit = next(
        (s for s in list_monitored_subreddits_for_project(db, project["id"]) if s["name"] == opportunity["subreddit_name"]),
        None,
    )

    # Create a RedditPost from stored opportunity data
    from datetime import datetime
    post = RedditPost(
        post_id=opportunity.get("reddit_post_id", ""),
        subreddit=opportunity.get("subreddit_name", ""),
        title=opportunity.get("title", ""),
        author=opportunity.get("author", ""),
        permalink=opportunity.get("permalink", ""),
        body=opportunity.get("body_excerpt", ""),
        created_at=datetime.now(UTC),
        num_comments=0,
        score=opportunity.get("score", 0),
    )

    score = score_post(post, brand, subreddit, keywords, [])
    return score.eligible, score.total
