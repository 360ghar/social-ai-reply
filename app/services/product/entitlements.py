from collections.abc import Iterable

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    DiscoveryKeyword,
    MonitoredSubreddit,
    PlanEntitlement,
    Project,
    Subscription,
    SubscriptionStatus,
    Workspace,
)


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


def seed_plan_entitlements(db: Session) -> None:
    existing = {
        (row.plan_code, row.feature_key): row
        for row in db.scalars(select(PlanEntitlement)).all()
    }
    changed = False
    for plan in PLAN_CATALOG:
        for feature_key, limit_value in plan["limits"].items():
            key = (plan["code"], feature_key)
            row = existing.get(key)
            if row:
                if row.limit_value != limit_value:
                    row.limit_value = limit_value
                    changed = True
                continue
            db.add(
                PlanEntitlement(
                    plan_code=plan["code"],
                    feature_key=feature_key,
                    limit_value=limit_value,
                    description=f"{plan['name']} limit for {feature_key}",
                )
            )
            changed = True
    if changed:
        db.commit()


def get_or_create_subscription(db: Session, workspace: Workspace) -> Subscription:
    subscription = db.scalar(select(Subscription).where(Subscription.workspace_id == workspace.id))
    if subscription:
        changed = False
        if subscription.plan_code not in ("free", "internal"):
            subscription.plan_code = "free"
            changed = True
        if subscription.status != SubscriptionStatus.ACTIVE:
            subscription.status = SubscriptionStatus.ACTIVE
            changed = True
        if subscription.current_period_end is not None:
            subscription.current_period_end = None
            changed = True
        if changed:
            db.commit()
            db.refresh(subscription)
        return subscription
    subscription = Subscription(workspace_id=workspace.id, plan_code="free", status=SubscriptionStatus.ACTIVE)
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def get_limit(db: Session, workspace: Workspace, feature_key: str) -> int:
    # The private workspace always runs in unlocked mode.
    return 999999


def enforce_limit(db: Session, workspace: Workspace, feature_key: str, current_count: int) -> None:
    # Limits are intentionally disabled for the internal workspace.
    pass


def count_projects(db: Session, workspace_id: int) -> int:
    return db.scalar(select(func.count(Project.id)).where(Project.workspace_id == workspace_id)) or 0


def count_active_keywords(db: Session, project_id: int) -> int:
    return db.scalar(
        select(func.count(DiscoveryKeyword.id)).where(
            DiscoveryKeyword.project_id == project_id,
            DiscoveryKeyword.is_active.is_(True),
        )
    ) or 0


def count_active_subreddits(db: Session, project_id: int) -> int:
    return db.scalar(
        select(func.count(MonitoredSubreddit.id)).where(
            MonitoredSubreddit.project_id == project_id,
            MonitoredSubreddit.is_active.is_(True),
        )
    ) or 0


def serialize_plan_catalog() -> list[dict]:
    return [{k: v for k, v in plan.items() if k != "limits"} | {"limits": dict(plan["limits"])} for plan in PLAN_CATALOG]


def feature_set(plan_code: str) -> Iterable[str]:
    for plan in PLAN_CATALOG:
        if plan["code"] == plan_code:
            return plan["features"]
    return ()
