"""Reddit scanning and opportunity detection service."""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import HTTPException

from app.db.tables.discovery import (
    create_opportunity,
    get_opportunity_by_project_and_reddit_post,
    get_scan_run_by_id,
    update_opportunity,
    update_scan_run,
)
from app.db.tables.projects import get_brand_profile_by_project

if TYPE_CHECKING:
    from supabase import Client

    from app.schemas.v1.discovery import ScanRequest
from app.services.product.discovery import get_project_search_keywords
from app.services.product.reddit import RedditPost
from app.services.product.reddit_discovery import RedditDiscoveryService
from app.services.product.scoring import (
    MIN_RELEVANT_OPPORTUNITY_SCORE,
    score_post,
)

logger = logging.getLogger(__name__)

# Cap how many rejected posts we persist per scan to keep the
# "Rejected" bucket useful rather than overwhelming.
_MAX_REJECTED_PER_SCAN = 25


def run_scan(db: Client, project: dict, payload: ScanRequest) -> dict:
    """Run a scan for opportunities based on project keywords and subreddits."""
    reddit = RedditDiscoveryService()
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
        rejected_saved = 0
        completed_at: str | None = None
        cutoff = datetime.now(UTC) - timedelta(hours=payload.search_window_hours)
        effective_min_score = max(payload.min_score, MIN_RELEVANT_OPPORTUNITY_SCORE)
        rules_cache: dict[str, list[str]] = {}
        per_subreddit_errors: list[str] = []
        subreddits_queried = 0
        fatal_error = False

        for subreddit in active_subreddits:
            # Soft subreddit-fit gate: below the floor we still scan, but
            # scoring applies a penalty. Previously this was a hard skip.
            rules = rules_cache.setdefault(subreddit["name"].lower(), _safe_subreddit_rules(reddit, subreddit["name"]))
            try:
                posts = reddit.search_posts(
                    search_keywords,
                    subreddits=[subreddit["name"]],
                    limit=payload.max_posts_per_subreddit,
                )
                subreddits_queried += 1
            except Exception as exc:  # noqa: BLE001 - capture root cause in scan metadata
                err_msg = f"{subreddit['name']}: {type(exc).__name__}: {exc}"[:200]
                per_subreddit_errors.append(err_msg)
                logger.warning("Scan: error querying r/%s: %s", subreddit["name"], exc)
                continue
            for post in posts:
                if post.created_at and post.created_at < cutoff.replace(tzinfo=None if post.created_at.tzinfo is None else UTC):
                    continue
                posts_scanned += 1
                score = score_post(post, brand, subreddit, search_keywords, rules)

                # Check if this Reddit post already exists as an opportunity.
                existing = get_opportunity_by_project_and_reddit_post(db, project["id"], post.post_id)

                if score.eligible and score.total >= effective_min_score:
                    new_status = existing.get("status", "new") if existing else "new"
                    if new_status == "rejected":
                        new_status = "new"
                    payload_data = {
                        "score": score.total,
                        "score_reasons": score.reasons,
                        "keyword_hits": score.keyword_hits,
                        "rule_risk": score.rule_risk,
                        "body_excerpt": post.body[:1200],
                        "permalink": post.permalink,
                        "status": new_status,
                    }
                    if existing:
                        update_opportunity(db, existing["id"], payload_data)
                    else:
                        create_opportunity(db, {
                            "project_id": project["id"],
                            "scan_run_id": run["id"],
                            "reddit_post_id": post.post_id,
                            "title": post.title,
                            "author": post.author,
                            "subreddit_name": subreddit["name"],
                            **payload_data,
                        })
                        opportunities_found += 1
                elif not existing and rejected_saved < _MAX_REJECTED_PER_SCAN:
                    # Persist rejected posts so the user can review what Reddit returned.
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
                        "status": "rejected",
                    })
                    rejected_saved += 1

        error_message: str | None = None
        if subreddits_queried == 0 and per_subreddit_errors:
            fatal_error = True
            error_message = (
                "All subreddit discovery requests failed across external search and "
                "public Reddit feeds. Sample errors: "
                + "; ".join(per_subreddit_errors[:3])
            )[:500]
        elif per_subreddit_errors and posts_scanned == 0:
            error_message = (
                f"No posts found. {len(per_subreddit_errors)} subreddit(s) errored "
                f"and {subreddits_queried} returned zero matches. "
                + "; ".join(per_subreddit_errors[:2])
            )[:500]

        # Update scan run with results
        completed_at = datetime.now(UTC).isoformat()
        update_scan_run(db, run["id"], {
            "status": "completed",
            "posts_scanned": posts_scanned,
            "opportunities_found": opportunities_found,
            "error_message": error_message,
            "completed_at": completed_at,
        })

        # Return full scan run record
        updated_run = get_scan_run_by_id(db, run["id"])
        response = _hydrate_scan_run_response(
            updated_run or run,
            search_window_hours=payload.search_window_hours,
            posts_scanned=posts_scanned,
            completed_at=completed_at,
        )
        response["fatal_error"] = fatal_error
        return response
    except Exception as e:
        logger.exception("Scan failed")
        completed_at = datetime.now(UTC).isoformat()
        update_scan_run(db, run["id"], {
            "status": "error",
            "error_message": str(e)[:500],
            "completed_at": completed_at,
        })
        raise


def _safe_subreddit_rules(reddit: RedditDiscoveryService, subreddit_name: str) -> list[str]:
    """Safely fetch subreddit rules with a timeout."""
    try:
        return reddit.subreddit_rules(subreddit_name)
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


def _hydrate_scan_run_response(
    record: dict,
    *,
    search_window_hours: int,
    posts_scanned: int,
    completed_at: str | None,
) -> dict:
    hydrated = dict(record)
    hydrated.setdefault("search_window_hours", search_window_hours)
    hydrated.setdefault("posts_scanned", posts_scanned)
    if completed_at and not hydrated.get("completed_at"):
        hydrated["completed_at"] = completed_at
    return hydrated
