"""Content scheduler — background publishing worker for X, Instagram, and LinkedIn.

Checks for approved, due suggestions and publishes them via the
appropriate platform publisher. Designed to be called periodically
(every 5-15 min) from an interval-based mechanism or a manual trigger
endpoint.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.db.tables.tweet_suggestions import (
    claim_suggestion_for_publish,
    list_suggestions_ready_to_publish,
    mark_suggestion_failed,
    mark_suggestion_published,
)
from app.services.infrastructure.instagram_publisher import (
    InstagramPublisher,
    get_instagram_business_account_id,
    get_instagram_token,
)
from app.services.infrastructure.linkedin_publisher import (
    LinkedInPublisher,
    get_linkedin_author_urn,
    get_linkedin_token,
)
from app.services.infrastructure.x_publisher import XPublisher, get_x_token

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)

ALL_PLATFORMS = ("x", "instagram", "linkedin")


def _resolve_publisher_info(
    platform: str,
) -> tuple[Any, Any, Any] | None:
    """Return ``(publisher_class, token_func, extra_kwargs_func)`` for
    *platform*, or None if the platform is unknown.

    Token and extra-arg functions are returned as zero-arg callables
    (thunks) that resolve the import at call time.  This ensures
    ``unittest.mock.patch`` on module-level names works correctly in
    tests.
    """
    mapping: dict[str, tuple[Any, Any, Any]] = {
        "x": (
            XPublisher,
            lambda db, wid: get_x_token(db, wid),
            lambda db, wid: {},
        ),
        "instagram": (
            InstagramPublisher,
            lambda db, wid: get_instagram_token(db, wid),
            lambda db, wid: {"business_account_id": get_instagram_business_account_id(db, wid)},
        ),
        "linkedin": (
            LinkedInPublisher,
            lambda db, wid: get_linkedin_token(db, wid),
            lambda db, wid: {"author_urn": get_linkedin_author_urn(db, wid)},
        ),
    }
    return mapping.get(platform)


def _build_publisher(
    db: Client,
    workspace_id: int,
    platform: str,
) -> Any | None:
    """Instantiate the correct publisher for *platform*, or None if
    credentials are missing."""
    info = _resolve_publisher_info(platform)
    if not info:
        logger.warning("Unknown platform '%s' — no publisher available.", platform)
        return None

    publisher_cls, token_fn, extra_fn = info
    token = token_fn(db, workspace_id)
    if not token:
        logger.warning(
            "No %s access token configured for workspace %d.",
            platform,
            workspace_id,
        )
        return None

    extra_kwargs = extra_fn(db, workspace_id)
    if any(v is None for v in extra_kwargs.values()):
        missing = [k for k, v in extra_kwargs.items() if v is None]
        logger.warning(
            "Missing %s configuration for workspace %d: %s.",
            platform,
            workspace_id,
            ", ".join(missing),
        )
        return None

    try:
        return publisher_cls(token=token, **extra_kwargs)
    except TypeError:
        return publisher_cls(token=token)


def publish_due_suggestions(
    db: Client,
    workspace_id: int,
    platform: str = "x",
) -> dict[str, int]:
    due = list_suggestions_ready_to_publish(db, workspace_id, platform=platform)
    if not due:
        return {"attempted": 0, "published": 0, "failed": 0}

    publisher = _build_publisher(db, workspace_id, platform)
    if not publisher:
        return {"attempted": len(due), "published": 0, "failed": len(due)}

    published_count = 0
    failed_count = 0

    for suggestion in due:
        suggestion_id = suggestion["id"]
        # Atomic claim: only proceed if THIS call won the race
        claim_token = claim_suggestion_for_publish(db, suggestion_id)
        if claim_token is None:
            logger.info("Skipping suggestion %d — already claimed by another worker", suggestion_id)
            continue

        content = suggestion["content"]
        media_url = suggestion.get("media_url") or None
        try:
            if platform == "x":
                results = publisher.publish_thread([content])
                published_id = results[0]["id"] if results else None
            elif platform == "instagram":
                result = publisher.publish_post(content, media_url=media_url)
                published_id = result.get("id")
            elif platform == "linkedin":
                result = publisher.publish_post(content)
                published_id = result.get("id")
            else:
                raise RuntimeError(f"Unsupported platform: {platform}")

            if not mark_suggestion_published(db, suggestion_id, claim_token):
                logger.warning(
                    "Lost claim on suggestion %d — another worker took over",
                    suggestion_id,
                )
                continue
            published_count += 1
            logger.info(
                "Published suggestion %d for workspace %d (%s id: %s)",
                suggestion_id, workspace_id, platform, published_id,
            )
        except Exception as exc:
            error_msg = str(exc)[:500]
            logger.error(
                "Failed to publish suggestion %d for workspace %d (%s): %s",
                suggestion_id, workspace_id, platform, error_msg,
            )
            mark_suggestion_failed(db, suggestion_id, claim_token, error_msg)
            failed_count += 1

    return {
        "attempted": len(due),
        "published": published_count,
        "failed": failed_count,
    }


def publish_due_suggestions_for_all_platforms(
    db: Client,
    workspace_id: int,
) -> dict[str, dict[str, int]]:
    """Run publish_due_suggestions for every supported platform on one workspace."""
    results: dict[str, dict[str, int]] = {}
    for platform in ALL_PLATFORMS:
        try:
            outcome = publish_due_suggestions(db, workspace_id, platform)
            results[platform] = outcome
            logger.info(
                "Workspace %d / %s: attempted=%d published=%d failed=%d",
                workspace_id,
                platform,
                outcome["attempted"],
                outcome["published"],
                outcome["failed"],
            )
        except Exception as exc:
            logger.exception("Scheduler failed for workspace %d / %s: %s", workspace_id, platform, exc)
            results[platform] = {"attempted": 0, "published": 0, "failed": 0}
    return results


def publish_all_workspaces(
    db: Client,
    platform: str | None = None,
) -> list[dict[str, int | str]]:
    """Iterate over all workspaces and publish due suggestions.

    If *platform* is specified, only that platform is published.
    If None, all platforms are published for each workspace.
    """
    results: list[dict[str, int | str]] = []
    platforms = [platform] if platform else ALL_PLATFORMS

    for plat in platforms:
        workspace_ids = _list_workspaces_with_creds(db, plat)
        for wid in workspace_ids:
            try:
                outcome = publish_due_suggestions(db, wid, plat)
                outcome["workspace_id"] = wid
                outcome["platform"] = plat
                results.append(outcome)
            except Exception as exc:
                logger.exception("Scheduler failed for workspace %d (%s): %s", wid, plat, exc)
                results.append({
                    "workspace_id": wid,
                    "platform": plat,
                    "attempted": 0,
                    "published": 0,
                    "failed": 0,
                    "error": str(exc)[:300],
                })
    return results


def _list_workspaces_with_creds(db: Client, platform: str) -> list[int]:
    """Return workspace ids that have an integration secret for *platform*."""
    provider_map = {
        "x": ("x", "twitter"),
        "instagram": ("instagram",),
        "linkedin": ("linkedin",),
    }
    providers = provider_map.get(platform, (platform,))
    try:
        result = (
            db.table("integration_secrets")
            .select("workspace_id")
            .in_("provider", providers)
            .execute()
        )
        seen: set[int] = set()
        for row in (result.data or []):
            wid = row.get("workspace_id")
            if wid is not None:
                seen.add(int(wid))
        return sorted(seen)
    except Exception as exc:
        logger.warning("Failed to list workspaces with %s creds: %s", platform, exc)
        return []
