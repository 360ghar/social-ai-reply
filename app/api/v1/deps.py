from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    AccountUser,
    BrandProfile,
    Membership,
    MembershipRole,
    Project,
    ProjectStatus,
    PromptTemplate,
    Subscription,
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
from app.services.product.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AccountUser:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (ValueError, KeyError, IndexError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc
    except Exception as exc:
        # Catch jwt.DecodeError, jwt.ExpiredSignatureError, etc.
        import jwt as _jwt

        if isinstance(exc, _jwt.PyJWTError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc
        raise
    user = db.scalar(select(AccountUser).where(AccountUser.id == user_id, AccountUser.is_active.is_(True)))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
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
_ensure_default_prompts = ensure_default_prompts
_workspace_summary = workspace_summary
_subscription_response = subscription_response
_build_subreddit_analysis = build_subreddit_analysis
