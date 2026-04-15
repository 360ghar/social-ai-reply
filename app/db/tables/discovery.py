"""Discovery table operations: personas, keywords, monitored subreddits, opportunities, scan runs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

PERSONAS_TABLE = "personas_v1"
DISCOVERY_KEYWORDS_TABLE = "discovery_keywords"
MONITORED_SUBREDDITS_TABLE = "monitored_subreddits"
SCAN_RUNS_TABLE = "scan_runs"
OPPORTUNITIES_TABLE = "opportunities"
SUBREDDITS_ANALYSES_TABLE = "subreddits_analyses"  # note: plural "subreddits_", DB name is authoritative


# Persona operations
def get_persona_by_id(db: Client, persona_id: int) -> dict[str, Any] | None:
    """Get a persona by ID."""
    result = db.table(PERSONAS_TABLE).select("*").eq("id", persona_id).execute()
    return result.data[0] if result.data else None


def create_persona(db: Client, persona_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new persona."""
    result = db.table(PERSONAS_TABLE).insert(persona_data).execute()
    return result.data[0]


def update_persona(db: Client, persona_id: int, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a persona."""
    result = db.table(PERSONAS_TABLE).update(update_data).eq("id", persona_id).execute()
    return result.data[0] if result.data else None


def delete_persona(db: Client, persona_id: int) -> None:
    """Delete a persona."""
    db.table(PERSONAS_TABLE).delete().eq("id", persona_id).execute()


# Discovery keyword operations
def get_discovery_keyword_by_id(db: Client, keyword_id: int) -> dict[str, Any] | None:
    """Get a discovery keyword by ID."""
    result = db.table(DISCOVERY_KEYWORDS_TABLE).select("*").eq("id", keyword_id).execute()
    return result.data[0] if result.data else None


def list_keywords_for_project(db: Client, project_id: int) -> list[dict[str, Any]]:
    """List all discovery keywords for a project, ordered by priority."""
    result = (
        db.table(DISCOVERY_KEYWORDS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .order("priority_score", desc=True)
        .execute()
    )
    return list(result.data)


def create_discovery_keyword(db: Client, keyword_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new discovery keyword."""
    result = db.table(DISCOVERY_KEYWORDS_TABLE).insert(keyword_data).execute()
    return result.data[0]


def update_discovery_keyword(db: Client, keyword_id: int, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a discovery keyword."""
    result = db.table(DISCOVERY_KEYWORDS_TABLE).update(update_data).eq("id", keyword_id).execute()
    return result.data[0] if result.data else None


def delete_discovery_keyword(db: Client, keyword_id: int) -> None:
    """Delete a discovery keyword."""
    db.table(DISCOVERY_KEYWORDS_TABLE).delete().eq("id", keyword_id).execute()


def get_keyword_by_project_and_keyword(db: Client, project_id: int, keyword: str) -> dict[str, Any] | None:
    """Get a discovery keyword by project ID and keyword string."""
    result = (
        db.table(DISCOVERY_KEYWORDS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .eq("keyword", keyword)
        .execute()
    )
    return result.data[0] if result.data else None


# Monitored subreddit operations
def get_monitored_subreddit_by_id(db: Client, subreddit_id: int) -> dict[str, Any] | None:
    """Get a monitored subreddit by ID."""
    result = db.table(MONITORED_SUBREDDITS_TABLE).select("*").eq("id", subreddit_id).execute()
    return result.data[0] if result.data else None


def list_subreddits_for_project(db: Client, project_id: int) -> list[dict[str, Any]]:
    """List all monitored subreddits for a project."""
    result = (
        db.table(MONITORED_SUBREDDITS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .order("fit_score", desc=True)
        .execute()
    )
    return list(result.data)


def create_monitored_subreddit(db: Client, subreddit_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new monitored subreddit."""
    result = db.table(MONITORED_SUBREDDITS_TABLE).insert(subreddit_data).execute()
    return result.data[0]


def update_monitored_subreddit(db: Client, subreddit_id: int, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a monitored subreddit."""
    result = db.table(MONITORED_SUBREDDITS_TABLE).update(update_data).eq("id", subreddit_id).execute()
    return result.data[0] if result.data else None


def delete_monitored_subreddit(db: Client, subreddit_id: int) -> None:
    """Delete a monitored subreddit."""
    db.table(MONITORED_SUBREDDITS_TABLE).delete().eq("id", subreddit_id).execute()


def get_subreddit_by_project_and_name(db: Client, project_id: int, name: str) -> dict[str, Any] | None:
    """Get a monitored subreddit by project ID and subreddit name."""
    result = (
        db.table(MONITORED_SUBREDDITS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .eq("name", name)
        .execute()
    )
    return result.data[0] if result.data else None


def create_subreddit_analysis(db: Client, analysis_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new subreddit analysis record."""
    result = db.table(SUBREDDITS_ANALYSES_TABLE).insert(analysis_data).execute()
    return result.data[0]


# Scan run operations
def get_scan_run_by_id(db: Client, scan_run_id: str) -> dict[str, Any] | None:
    """Get a scan run by ID."""
    result = db.table(SCAN_RUNS_TABLE).select("*").eq("id", scan_run_id).execute()
    return result.data[0] if result.data else None


def list_scan_runs_for_project(db: Client, project_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """List scan runs for a project."""
    result = (
        db.table(SCAN_RUNS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(result.data)


def create_scan_run(db: Client, scan_run_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new scan run."""
    result = db.table(SCAN_RUNS_TABLE).insert(scan_run_data).execute()
    return result.data[0]


def update_scan_run(db: Client, scan_run_id: str, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a scan run."""
    result = db.table(SCAN_RUNS_TABLE).update(update_data).eq("id", scan_run_id).execute()
    return result.data[0] if result.data else None


def delete_scan_run(db: Client, scan_run_id: str) -> None:
    """Delete a scan run."""
    db.table(SCAN_RUNS_TABLE).delete().eq("id", scan_run_id).execute()


# Opportunity operations
def get_opportunity_by_id(db: Client, opportunity_id: int) -> dict[str, Any] | None:
    """Get an opportunity by ID."""
    result = db.table(OPPORTUNITIES_TABLE).select("*").eq("id", opportunity_id).execute()
    return result.data[0] if result.data else None


def get_opportunity_by_project_and_reddit_post(
    db: Client,
    project_id: int,
    reddit_post_id: str,
) -> dict[str, Any] | None:
    """Get an opportunity by project ID and Reddit post ID."""
    result = (
        db.table(OPPORTUNITIES_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .eq("reddit_post_id", reddit_post_id)
        .execute()
    )
    return result.data[0] if result.data else None


def list_opportunities_for_project(
    db: Client,
    project_id: int,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List opportunities for a project with optional status filter."""
    query = db.table(OPPORTUNITIES_TABLE).select("*").eq("project_id", project_id)
    if status:
        query = query.eq("status", status)
    result = query.order("score", desc=True).range(offset, offset + limit - 1).execute()
    return list(result.data)


def create_opportunity(db: Client, opportunity_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new opportunity."""
    result = db.table(OPPORTUNITIES_TABLE).insert(opportunity_data).execute()
    return result.data[0]


def update_opportunity(db: Client, opportunity_id: int, update_data: dict[str, Any]) -> dict[str, Any] | None:
    """Update an opportunity."""
    result = db.table(OPPORTUNITIES_TABLE).update(update_data).eq("id", opportunity_id).execute()
    return result.data[0] if result.data else None


def delete_opportunity(db: Client, opportunity_id: int) -> None:
    """Delete an opportunity."""
    db.table(OPPORTUNITIES_TABLE).delete().eq("id", opportunity_id).execute()


def bulk_create_opportunities(db: Client, opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bulk create multiple opportunities."""
    if not opportunities:
        return []
    result = db.table(OPPORTUNITIES_TABLE).insert(opportunities).execute()
    return list(result.data)


def count_opportunities_for_project(db: Client, project_id: int, status: str | None = None) -> int:
    """Count opportunities for a project."""
    query = db.table(OPPORTUNITIES_TABLE).select("id", count="exact").eq("project_id", project_id)
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return result.count if hasattr(result, "count") and result.count is not None else 0


def list_personas_for_project(db: Client, project_id: int, source: str | None = None, limit: int = 100, include_inactive: bool = False) -> list[dict[str, Any]]:
    """List personas for a project with optional source filter."""
    query = db.table(PERSONAS_TABLE).select("*").eq("project_id", project_id)
    if source:
        query = query.eq("source", source)
    if not include_inactive:
        query = query.eq("is_active", True)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return list(result.data)


def list_discovery_keywords_for_project(db: Client, project_id: int, source: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """List discovery keywords for a project with optional source filter."""
    query = db.table(DISCOVERY_KEYWORDS_TABLE).select("*").eq("project_id", project_id)
    if source:
        query = query.eq("source", source)
    result = query.order("priority_score", desc=True).limit(limit).execute()
    return list(result.data)


def list_monitored_subreddits_for_project(db: Client, project_id: int, limit: int = 100) -> list[dict[str, Any]]:
    """List monitored subreddits for a project."""
    result = (
        db.table(MONITORED_SUBREDDITS_TABLE)
        .select("*")
        .eq("project_id", project_id)
        .order("fit_score", desc=True)
        .limit(limit)
        .execute()
    )
    return list(result.data)
