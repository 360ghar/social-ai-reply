"""Tracked link and link click table operations for ROI attribution."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

TRACKED_LINKS_TABLE = "tracked_links"
LINK_CLICKS_TABLE = "link_clicks"
OPPORTUNITIES_TABLE = "opportunities"

UNATTRIBUTED_KEY = "unattributed"


# Tracked link operations
def create_tracked_link(db: Client, link_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new tracked link."""
    result = db.table(TRACKED_LINKS_TABLE).insert(link_data).execute()
    return result.data[0]


def get_tracked_link_by_id(db: Client, link_id: int) -> dict[str, Any] | None:
    """Get a tracked link by ID."""
    result = db.table(TRACKED_LINKS_TABLE).select("*").eq("id", link_id).execute()
    return result.data[0] if result.data else None


def get_tracked_link_by_code(db: Client, code: str) -> dict[str, Any] | None:
    """Get a tracked link by its short code."""
    result = db.table(TRACKED_LINKS_TABLE).select("*").eq("code", code).execute()
    return result.data[0] if result.data else None


def list_tracked_links_for_project(db: Client, project_id: int) -> list[dict[str, Any]]:
    """List all tracked links for a project."""
    result = (
        db.table(TRACKED_LINKS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )
    return list(result.data)


# Link click operations
def create_link_click(db: Client, click_data: dict[str, Any]) -> dict[str, Any]:
    """Log a click on a tracked link."""
    result = db.table(LINK_CLICKS_TABLE).insert(click_data).execute()
    return result.data[0]


def count_clicks_for_links(db: Client, link_ids: list[int]) -> dict[int, int]:
    """Count clicks per tracked link. Returns {link_id: click_count}."""
    counts: dict[int, int] = {link_id: 0 for link_id in link_ids}
    if not link_ids:
        return counts
    result = (
        db.table(LINK_CLICKS_TABLE)
        .select("tracked_link_id")
        .in_("tracked_link_id", link_ids)
        .execute()
    )
    for row in result.data:
        link_id = row.get("tracked_link_id")
        if link_id is not None:
            counts[link_id] = counts.get(link_id, 0) + 1
    return counts


# ROI rollup
def get_roi_rollup(db: Client, project_id: int) -> list[dict[str, Any]]:
    """Aggregate tracked-link and click counts per subreddit and buying stage.

    Joins tracked_links to their opportunities client-side and returns rows
    shaped as ``{"group_by": "subreddit"|"buying_stage", "key": ..., "links": n, "clicks": n}``.
    Links without an attributable opportunity fall under the "unattributed" key.
    """
    links = list_tracked_links_for_project(db, project_id)
    if not links:
        return []

    click_counts = count_clicks_for_links(db, [link["id"] for link in links])

    opportunity_ids = sorted({link["opportunity_id"] for link in links if link.get("opportunity_id")})
    opportunities: dict[int, dict[str, Any]] = {}
    if opportunity_ids:
        result = (
            db.table(OPPORTUNITIES_TABLE)
            .select("id, subreddit_name, buying_stage")
            .in_("id", opportunity_ids)
            .execute()
        )
        opportunities = {row["id"]: row for row in result.data}

    subreddit_agg: dict[str, dict[str, int]] = {}
    stage_agg: dict[str, dict[str, int]] = {}

    for link in links:
        opportunity = opportunities.get(link.get("opportunity_id") or 0, {})
        subreddit_key = opportunity.get("subreddit_name") or UNATTRIBUTED_KEY
        stage_key = opportunity.get("buying_stage") or UNATTRIBUTED_KEY
        clicks = click_counts.get(link["id"], 0)

        for agg, key in ((subreddit_agg, subreddit_key), (stage_agg, stage_key)):
            entry = agg.setdefault(key, {"links": 0, "clicks": 0})
            entry["links"] += 1
            entry["clicks"] += clicks

    rows: list[dict[str, Any]] = []
    for group_by, agg in (("subreddit", subreddit_agg), ("buying_stage", stage_agg)):
        for key in sorted(agg):
            rows.append(
                {
                    "group_by": group_by,
                    "key": key,
                    "links": agg[key]["links"],
                    "clicks": agg[key]["clicks"],
                }
            )
    return rows
