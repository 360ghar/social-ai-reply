"""Entitlements and subscription management.

This module handles plan-based feature gating and subscription management.
"""

from collections.abc import Iterable

from fastapi import HTTPException
from supabase import Client

from app.db.tables.workspaces import (
    create_subscription,
    get_subscription_by_workspace,
)

# Feature flag constants used for entitlement checks in route handlers.
FEATURE_AUTO_PIPELINE = "auto_pipeline"

PLAN_CATALOG = [
    {
        "code": "free",
        "name": "Free",
        "price_monthly": 0,
        "features": [
            "Unlimited projects",
            "Unlimited keywords",
            "Unlimited communities",
            "AI visibility tracking",
            "Analytics & reporting",
            "Campaign management",
            "Auto-pipeline setup",
            "Reddit posting (unlimited)",
            "All product capabilities unlocked",
        ],
        "limits": {"projects": 999999, "keywords": 999999, "subreddits": 999999},
    },
    {
        "code": "internal",
        "name": "Internal",
        "price_monthly": 0,
        "features": [
            "Unlimited projects",
            "Unlimited keywords",
            "Unlimited communities",
            "All product capabilities unlocked",
        ],
        "limits": {"projects": 999999, "keywords": 999999, "subreddits": 999999},
    },
]


def seed_plan_entitlements(supabase: Client) -> None:
    """Seed plan entitlements in the database.

    No-op in the Supabase era. Entitlements are managed via Supabase dashboard
    or migrations. The free/internal plans have hardcoded unlimited limits via
    get_limit() and PLAN_CATALOG. Kept for API compatibility — callers should
    not need to know this is a no-op.
    """


def get_or_create_subscription(supabase: Client, workspace: dict) -> dict:
    """Get or create a subscription for a workspace.

    For the private workspace, always returns an active 'free' plan.
    """
    subscription = get_subscription_by_workspace(supabase, workspace["id"])

    if subscription:
        if subscription["status"] != "active":
            subscription = update_subscription(supabase, subscription["id"], {"status": "active"})
        return subscription

    return create_subscription(
        supabase,
        {
            "workspace_id": workspace["id"],
            "plan_code": "free",
            "status": "active",
        },
    )


def update_subscription(supabase: Client, subscription_id: int, update_data: dict) -> dict:
    """Update a subscription."""
    from app.db.tables.workspaces import update_subscription as _update

    result = _update(supabase, subscription_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Subscription not found.")
    return result


def get_limit(supabase: Client, workspace: dict, feature_key: str) -> int:
    """Get the limit for a feature.

    For the private workspace, always returns unlimited (999999).
    """
    return 999999


def enforce_limit(supabase: Client, workspace: dict, feature_key: str, current_count: int) -> None:
    """Raise HTTPException if current_count has reached the plan limit for feature_key."""
    limit = get_limit(supabase, workspace, feature_key)
    if current_count >= limit:
        raise HTTPException(
            status_code=402,
            detail=f"Plan limit reached for {feature_key} ({current_count}/{limit}). Upgrade your plan to add more.",
        )


def count_projects(supabase: Client, workspace_id: int) -> int:
    """Count projects in a workspace."""
    from app.db.tables.projects import list_projects_for_workspace

    projects = list_projects_for_workspace(supabase, workspace_id)
    return len(projects)


def count_active_keywords(supabase: Client, project_id: int) -> int:
    """Count active keywords for a project."""
    from app.db.tables.discovery import list_keywords_for_project

    keywords = list_keywords_for_project(supabase, project_id)
    return sum(1 for k in keywords if k.get("is_active", True))


def count_active_subreddits(supabase: Client, project_id: int) -> int:
    """Count active subreddits for a project."""
    from app.db.tables.discovery import list_subreddits_for_project

    subreddits = list_subreddits_for_project(supabase, project_id)
    return sum(1 for s in subreddits if s.get("is_active", True))


def serialize_plan_catalog() -> list[dict]:
    """Serialize the plan catalog for API responses."""
    return [{k: v for k, v in plan.items() if k != "limits"} | {"limits": dict(plan["limits"])} for plan in PLAN_CATALOG]


def feature_set(plan_code: str) -> Iterable[str]:
    """Get the features for a plan code."""
    for plan in PLAN_CATALOG:
        if plan["code"] == plan_code:
            return plan["features"]
    return ()


def has_feature(supabase: Client, workspace: dict, feature_key: str) -> bool:
    """Return True if the workspace's active plan grants access to the named feature.

    Feature keys (e.g. FEATURE_AUTO_PIPELINE) are matched against human-readable
    feature strings in PLAN_CATALOG via case-insensitive substring match.
    """
    subscription = get_or_create_subscription(supabase, workspace)
    plan_features = [f.lower() for f in feature_set(subscription["plan_code"])]
    feature_lower = feature_key.lower().replace("_", " ")
    return any(feature_lower in f for f in plan_features)
