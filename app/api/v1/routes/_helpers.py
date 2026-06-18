"""Shared helpers for agent route modules (SEO, GEO, Articles, UGC, Technical-SEO).

Provides:
- ``get_company_opportunities``: batch-fetches opportunities for a company
  across all workspace projects in a single query, fixing the N+1 pattern
  where each route independently did: get_company → list_projects →
  list_opportunities_for_project → filter (Issue #19).
- ``get_first_project_for_workspace``: convenience wrapper that resolves the
  first project ID for a workspace.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.db.tables.company import get_company_by_id
from app.db.tables.projects import list_projects_for_workspace

if TYPE_CHECKING:
    from supabase import Client


def get_first_project_for_workspace(db: Client, workspace_id: int) -> int | None:
    """Return the first project ID for a workspace, or None."""
    projects = list_projects_for_workspace(db, workspace_id)
    return projects[0]["id"] if projects else None


def get_company_opportunities(
    db: Client,
    workspace_id: int,
    company_id: int,
    *,
    platform: str | None = None,
    opportunity_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Fetch filtered opportunities for a company in fewer DB calls.

    Instead of fetching per-project and filtering in Python (N+1 pattern),
    this fetches all workspace projects once and batches opportunities into a
    single query using .in_("project_id", ...) (Issue #19).

    Args:
        platform: If set, filter to opportunities with this platform value.
        opportunity_type: If set, filter by opportunity_type.
        limit/offset: Pagination.
    """
    company = get_company_by_id(db, company_id)
    if not company or company.get("workspace_id") != workspace_id:
        return []

    projects = list_projects_for_workspace(db, workspace_id)
    project_ids = [p["id"] for p in projects]
    if not project_ids:
        return []

    # Fetch opportunities for ALL workspace projects in one batched query.
    # list_opportunities_for_project accepts a single project_id, so for the
    # N+1 fix we query the opportunities table directly with in_().
    from app.db.tables.discovery import OPPORTUNITIES_TABLE

    query = db.table(OPPORTUNITIES_TABLE).select("*").in_("project_id", project_ids)
    if platform:
        query = query.eq("platform", platform)
    if opportunity_type:
        query = query.eq("opportunity_type", opportunity_type)
    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return list(result.data)
