import hashlib
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    AccountUser,
    BrandProfile,
    Membership,
    Project,
    ProjectStatus,
    PromptTemplate,
    Workspace,
)
from app.db.session import get_db
from app.schemas.v1.auth import WorkspaceSummary
from app.schemas.v1.billing import SubscriptionResponse
from app.services.product.entitlements import (
    PLAN_CATALOG,
    feature_set,
    get_or_create_subscription,
)
from app.services.product.supabase_auth import verify_supabase_jwt
from app.utils.slug import unique_slug as _unique_slug

bearer_scheme = HTTPBearer(auto_error=False)


def _issued_at_utc(payload: dict) -> datetime | None:
    raw_value = payload.get("iat")
    if raw_value is None:
        return None
    if isinstance(raw_value, datetime):
        return raw_value.astimezone(UTC) if raw_value.tzinfo else raw_value.replace(tzinfo=UTC)
    try:
        return datetime.fromtimestamp(float(raw_value), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def _coerce_utc(value: datetime) -> datetime:
    return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _is_token_revoked(user: AccountUser, payload: dict, token: str) -> bool:
    if user.revoked_access_token_hash and _token_hash(token) == user.revoked_access_token_hash:
        return True
    if not user.tokens_invalid_before:
        return False
    issued_at = _issued_at_utc(payload)
    if issued_at is None:
        return True
    return issued_at < _coerce_utc(user.tokens_invalid_before)


def _find_user_by_supabase_identity(db: Session, supabase_uid: str) -> AccountUser | None:
    return db.scalar(
        select(AccountUser).where(
            AccountUser.supabase_user_id == supabase_uid,
            AccountUser.is_active.is_(True),
        )
    )


def _backfill_legacy_user_from_email(db: Session, payload: dict, supabase_uid: str) -> AccountUser | None:
    email = str(payload.get("email", "")).strip().lower()
    if not email:
        return None

    user = db.scalar(
        select(AccountUser).where(
            AccountUser.email == email,
            AccountUser.supabase_user_id.is_(None),
            AccountUser.is_active.is_(True),
        )
    )
    if not user:
        return None

    user.supabase_user_id = supabase_uid
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AccountUser:
    """Validate the Supabase JWT and return the local AccountUser.

    The token's `sub` claim contains the Supabase user UUID which maps
    to AccountUser.supabase_user_id in our local database.
    """
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    try:
        payload = verify_supabase_jwt(credentials.credentials)
        supabase_uid = payload["sub"]
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc
    user = _find_user_by_supabase_identity(db, supabase_uid)
    if not user:
        user = _backfill_legacy_user_from_email(db, payload, supabase_uid)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if _is_token_revoked(user, payload, credentials.credentials):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please sign in again.")
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AccountUser | None:
    """Like get_current_user but returns None instead of raising when unauthenticated."""
    if not credentials:
        return None
    try:
        payload = verify_supabase_jwt(credentials.credentials)
        supabase_uid = payload["sub"]
    except Exception:
        return None
    user = _find_user_by_supabase_identity(db, supabase_uid)
    if not user:
        user = _backfill_legacy_user_from_email(db, payload, supabase_uid)
    if not user:
        return None
    if _is_token_revoked(user, payload, credentials.credentials):
        return None
    return user


def get_current_workspace(
    current_user: AccountUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workspace:
    membership = db.scalar(
        select(Membership).where(Membership.user_id == current_user.id).order_by(Membership.id.asc())
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No workspace membership found.")
    workspace = db.scalar(select(Workspace).where(Workspace.id == membership.workspace_id))
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    return workspace


# ── Shared query helpers ──────────────────────────────────────────


def ensure_workspace_membership(db: Session, workspace_id: int, user_id: int) -> Membership:
    membership = db.scalar(
        select(Membership).where(Membership.workspace_id == workspace_id, Membership.user_id == user_id)
    )
    if not membership:
        raise HTTPException(status_code=403, detail="You do not have access to this workspace.")
    return membership


def get_project(db: Session, workspace_id: int, project_id: int) -> Project:
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id, Project.workspace_id == workspace_id)
        .options(selectinload(Project.brand_profile), selectinload(Project.prompts))
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def get_active_project(db: Session, workspace_id: int, project_id: int | None = None) -> Project | None:
    if project_id is not None:
        selected = db.scalar(
            select(Project)
            .where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
                Project.status == ProjectStatus.ACTIVE,
            )
            .options(selectinload(Project.brand_profile), selectinload(Project.prompts))
        )
        if selected:
            return selected
    return db.scalar(
        select(Project)
        .where(Project.workspace_id == workspace_id, Project.status == ProjectStatus.ACTIVE)
        .order_by(Project.created_at.desc())
        .options(selectinload(Project.brand_profile), selectinload(Project.prompts))
    )


def ensure_default_project(db: Session, workspace: Workspace) -> Project:
    project = get_active_project(db, workspace.id)
    if project:
        return project

    base_name = (workspace.name or "").strip() or "Default"
    if not base_name.lower().endswith("project"):
        base_name = f"{base_name} Project"

    project = Project(
        workspace_id=workspace.id,
        name=base_name,
        slug=_unique_slug(db, Project, base_name, "workspace_id", workspace.id),
        status=ProjectStatus.ACTIVE,
    )
    db.add(project)
    db.flush()
    db.add(BrandProfile(project_id=project.id, brand_name=project.name))
    db.commit()
    ensure_default_prompts(db, project.id)
    db.refresh(project)
    return get_project(db, workspace.id, project.id)


def ensure_default_prompts(db: Session, project_id: int) -> None:
    defaults = [
        (
            "reply",
            "Helpful Reply",
            "You write grounded Reddit replies that help first and pitch never.",
            "Start with empathy, answer the actual question, avoid hard CTAs, and only mention the product when invited.",
        ),
        (
            "post",
            "Educational Post",
            "You write Reddit posts that teach from direct experience.",
            "Use first-hand lessons, concrete examples, and end with an invitation for discussion rather than a promo CTA.",
        ),
        (
            "analysis",
            "Signal Review",
            "You summarize opportunities with clarity and no fluff.",
            "Highlight why the thread matters, what the risk is, and how the brand can contribute credibly.",
        ),
    ]
    existing_types = {
        row.prompt_type
        for row in db.scalars(select(PromptTemplate).where(PromptTemplate.project_id == project_id)).all()
    }
    changed = False
    for prompt_type, name, system_prompt, instructions in defaults:
        if prompt_type in existing_types:
            continue
        db.add(
            PromptTemplate(
                project_id=project_id,
                prompt_type=prompt_type,
                name=name,
                system_prompt=system_prompt,
                instructions=instructions,
                is_default=True,
            )
        )
        changed = True
    if changed:
        db.commit()


def workspace_summary(db: Session, workspace: Workspace, user_id: int) -> WorkspaceSummary:
    membership = ensure_workspace_membership(db, workspace.id, user_id)
    return WorkspaceSummary(id=workspace.id, name=workspace.name, slug=workspace.slug, role=membership.role.value)


def subscription_response(db: Session, workspace: Workspace) -> SubscriptionResponse:
    subscription = get_or_create_subscription(db, workspace)
    plan = next((plan for plan in PLAN_CATALOG if plan["code"] == subscription.plan_code), PLAN_CATALOG[0])
    return SubscriptionResponse(
        plan_code=subscription.plan_code,
        status=subscription.status.value,
        current_period_end=subscription.current_period_end,
        features=list(feature_set(subscription.plan_code)),
        limits=dict(plan["limits"]),
    )


def build_subreddit_analysis(name: str, description: str, rules: list[str]) -> tuple[list[str], list[str], list[str], str]:
    text = f"{name} {description}".lower()
    top_post_types = []
    if "help" in text or "question" in text:
        top_post_types.append("questions")
    if "case study" in text or "showcase" in text:
        top_post_types.append("case studies")
    if not top_post_types:
        top_post_types = ["discussion", "advice"]
    audience_signals = []
    if "startup" in text or "founder" in text:
        audience_signals.append("founders")
    if "marketing" in text or "growth" in text:
        audience_signals.append("marketers")
    if "saas" in text or "software" in text:
        audience_signals.append("software buyers")
    if not audience_signals:
        audience_signals = ["broad interest audience"]
    recommendation = "Engage with helpful, specific replies and avoid promotional language."
    posting_risk = [rule for rule in rules[:5]]
    return top_post_types, audience_signals, posting_risk, recommendation


# Backwards-compatible aliases used by route files during migration
_ensure_workspace_membership = ensure_workspace_membership
_get_project = get_project
_get_active_project = get_active_project
_ensure_default_project = ensure_default_project
_ensure_default_prompts = ensure_default_prompts
_workspace_summary = workspace_summary
_subscription_response = subscription_response
_build_subreddit_analysis = build_subreddit_analysis
