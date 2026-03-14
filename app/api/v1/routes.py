import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.deps import get_current_user, get_current_workspace
from app.db.saas_models import (
    AccountUser,
    AuditEvent,
    BrandProfile,
    DiscoveryKeyword,
    IntegrationSecret,
    Invitation,
    Membership,
    MembershipRole,
    MonitoredSubreddit,
    Opportunity,
    OpportunityStatus,
    Persona,
    PostDraft,
    Project,
    ProjectStatus,
    PromptTemplate,
    Redemption,
    ReplyDraft,
    ScanRun,
    ScanStatus,
    SubredditAnalysis,
    WebhookEndpoint,
    Workspace,
)
from app.db.session import get_db
from app.schemas.v1.auth import AuthLoginRequest, AuthRegisterRequest, AuthResponse, UserResponse, WorkspaceSummary
from app.schemas.v1.product import (
    BrandAnalysisRequest,
    BrandProfileRequest,
    BrandProfileResponse,
    DashboardResponse,
    InvitationRequest,
    InvitationResponse,
    KeywordGenerateRequest,
    KeywordRequest,
    KeywordResponse,
    OpportunityResponse,
    OpportunityStatusRequest,
    PlanResponse,
    PersonaRequest,
    PersonaResponse,
    PostDraftRequest,
    PostDraftResponse,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
    PromptTemplateRequest,
    PromptTemplateResponse,
    RedemptionRequest,
    RedemptionResponse,
    ReplyDraftRequest,
    ReplyDraftResponse,
    ScanRequest,
    ScanRunResponse,
    SecretRequest,
    SecretResponse,
    SubredditDiscoverRequest,
    SubredditRequest,
    SubredditResponse,
    SubscriptionResponse,
    WebhookRequest,
    WebhookResponse,
    WebhookTestRequest,
)
from app.services.product.copilot import ProductCopilot
from app.services.product.encryption import encrypt_text
from app.services.product.entitlements import (
    PLAN_CATALOG,
    count_active_keywords,
    count_active_subreddits,
    count_projects,
    enforce_limit,
    feature_set,
    get_limit,
    get_or_create_subscription,
    seed_plan_entitlements,
    serialize_plan_catalog,
)
from app.services.product.reddit import RedditClient
from app.services.product.scoring import score_post
from app.services.product.security import create_access_token, hash_password, slugify, verify_password


router = APIRouter(prefix="/v1", tags=["v1"])


def _ensure_workspace_membership(db: Session, workspace_id: int, user_id: int) -> Membership:
    membership = db.scalar(
        select(Membership).where(Membership.workspace_id == workspace_id, Membership.user_id == user_id)
    )
    if not membership:
        raise HTTPException(status_code=403, detail="You do not have access to this workspace.")
    return membership


def _get_project(db: Session, workspace_id: int, project_id: int) -> Project:
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id, Project.workspace_id == workspace_id)
        .options(selectinload(Project.brand_profile), selectinload(Project.prompts))
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def _record_audit(
    db: Session,
    *,
    workspace_id: int | None,
    project_id: int | None,
    actor_user_id: int | None,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            workspace_id=workspace_id,
            project_id=project_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        )
    )


def _unique_slug(
    db: Session,
    model: type[Workspace] | type[Project],
    base: str,
    filter_field: str | None = None,
    filter_value: int | None = None,
) -> str:
    candidate = slugify(base)
    suffix = 1
    while True:
        stmt = select(model).where(model.slug == candidate)
        if filter_field and filter_value is not None:
            stmt = stmt.where(getattr(model, filter_field) == filter_value)
        exists = db.scalar(stmt)
        if not exists:
            return candidate
        suffix += 1
        candidate = f"{slugify(base)}-{suffix}"


def _workspace_summary(db: Session, workspace: Workspace, user_id: int) -> WorkspaceSummary:
    membership = _ensure_workspace_membership(db, workspace.id, user_id)
    return WorkspaceSummary(id=workspace.id, name=workspace.name, slug=workspace.slug, role=membership.role.value)


def _subscription_response(db: Session, workspace: Workspace) -> SubscriptionResponse:
    subscription = get_or_create_subscription(db, workspace)
    plan = next((plan for plan in PLAN_CATALOG if plan["code"] == subscription.plan_code), PLAN_CATALOG[0])
    return SubscriptionResponse(
        plan_code=subscription.plan_code,
        status=subscription.status.value,
        current_period_end=subscription.current_period_end,
        features=list(feature_set(subscription.plan_code)),
        limits=dict(plan["limits"]),
    )


def _ensure_default_prompts(db: Session, project_id: int) -> None:
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


def _build_subreddit_analysis(name: str, description: str, rules: list[str]) -> tuple[list[str], list[str], list[str], str]:
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


def _run_scan(db: Session, project: Project, payload: ScanRequest) -> ScanRun:
    reddit = RedditClient()
    brand = project.brand_profile
    active_keywords = db.scalars(
        select(DiscoveryKeyword).where(DiscoveryKeyword.project_id == project.id, DiscoveryKeyword.is_active.is_(True))
    ).all()
    active_subreddits = db.scalars(
        select(MonitoredSubreddit)
        .where(MonitoredSubreddit.project_id == project.id, MonitoredSubreddit.is_active.is_(True))
        .options(selectinload(MonitoredSubreddit.analyses))
    ).all()
    if not active_keywords:
        raise HTTPException(status_code=400, detail="Add discovery keywords before scanning.")
    if not active_subreddits:
        raise HTTPException(status_code=400, detail="Add monitored subreddits before scanning.")

    run = ScanRun(
        project_id=project.id,
        status=ScanStatus.RUNNING,
        search_window_hours=payload.search_window_hours,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        posts_scanned = 0
        opportunities_found = 0
        keywords = [row.keyword for row in active_keywords]
        cutoff = datetime.now(timezone.utc) - timedelta(hours=payload.search_window_hours)
        for subreddit in active_subreddits:
            rules = reddit.subreddit_rules(subreddit.name)
            try:
                posts = reddit.search_posts(subreddit.name, keywords, limit=payload.max_posts_per_subreddit)
            except Exception:
                continue
            for post in posts:
                if post.created_at < cutoff:
                    continue
                posts_scanned += 1
                score = score_post(post, brand, subreddit, keywords, rules)
                if score.total < 25:
                    continue
                opportunity = db.scalar(
                    select(Opportunity).where(
                        Opportunity.project_id == project.id,
                        Opportunity.reddit_post_id == post.post_id,
                    )
                )
                if opportunity:
                    opportunity.score = score.total
                    opportunity.score_reasons = score.reasons
                    opportunity.keyword_hits = score.keyword_hits
                    opportunity.rule_risk = score.rule_risk
                    opportunity.body_excerpt = post.body[:1200]
                    opportunity.permalink = post.permalink
                else:
                    db.add(
                        Opportunity(
                            project_id=project.id,
                            scan_run_id=run.id,
                            reddit_post_id=post.post_id,
                            subreddit_name=post.subreddit,
                            author=post.author,
                            title=post.title,
                            permalink=post.permalink,
                            body_excerpt=post.body[:1200],
                            score=score.total,
                            status=OpportunityStatus.NEW,
                            score_reasons=score.reasons,
                            keyword_hits=score.keyword_hits,
                            rule_risk=score.rule_risk,
                        )
                    )
                    opportunities_found += 1
        run.status = ScanStatus.COMPLETED
        run.posts_scanned = posts_scanned
        run.opportunities_found = opportunities_found
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.scalar(select(ScanRun).where(ScanRun.id == run.id))
        if run:
            run.status = ScanStatus.FAILED
            run.error_message = str(exc)
            run.finished_at = datetime.now(timezone.utc)
            db.add(run)
            db.commit()
        raise
    return run


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: AuthRegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    existing = db.scalar(select(AccountUser).where(AccountUser.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    user = AccountUser(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
    )
    db.add(user)
    db.flush()

    workspace = Workspace(
        name=payload.workspace_name.strip(),
        slug=_unique_slug(db, Workspace, payload.workspace_name),
        owner_user_id=user.id,
    )
    db.add(workspace)
    db.flush()
    db.add(Membership(workspace_id=workspace.id, user_id=user.id, role=MembershipRole.OWNER))
    db.commit()
    seed_plan_entitlements(db)
    get_or_create_subscription(db, workspace)

    token = create_access_token(user.id, user.email)
    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
        workspace=_workspace_summary(db, workspace, user.id),
    )


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: AuthLoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.scalar(select(AccountUser).where(AccountUser.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    workspace = db.scalar(
        select(Workspace).join(Membership).where(Membership.user_id == user.id).order_by(Workspace.id.asc())
    )
    if not workspace:
        raise HTTPException(status_code=403, detail="User has no workspace.")
    token = create_access_token(user.id, user.email)
    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
        workspace=_workspace_summary(db, workspace, user.id),
    )


@router.get("/auth/me", response_model=AuthResponse)
def me(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> AuthResponse:
    token = create_access_token(current_user.id, current_user.email)
    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(current_user),
        workspace=_workspace_summary(db, workspace, current_user.id),
    )


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    projects = db.scalars(select(Project).where(Project.workspace_id == workspace.id).order_by(Project.created_at.desc())).all()
    project_ids = [project.id for project in projects]
    top_opportunities = []
    if project_ids:
        top_opportunities = db.scalars(
            select(Opportunity)
            .where(Opportunity.project_id.in_(project_ids))
            .order_by(Opportunity.score.desc(), Opportunity.created_at.desc())
            .limit(12)
        ).all()
    return DashboardResponse(
        projects=[ProjectResponse.model_validate(project) for project in projects],
        top_opportunities=[OpportunityResponse.model_validate(item) for item in top_opportunities],
        subscription=_subscription_response(db, workspace),
    )


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[ProjectResponse]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    rows = db.scalars(select(Project).where(Project.workspace_id == workspace.id).order_by(Project.created_at.desc())).all()
    return [ProjectResponse.model_validate(row) for row in rows]


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    enforce_limit(db, workspace, "projects", count_projects(db, workspace.id))
    project = Project(
        workspace_id=workspace.id,
        name=payload.name.strip(),
        slug=_unique_slug(db, Project, payload.name, "workspace_id", workspace.id),
        description=payload.description,
        status=ProjectStatus.ACTIVE,
    )
    db.add(project)
    db.flush()
    db.add(BrandProfile(project_id=project.id, brand_name=project.name))
    _record_audit(
        db,
        workspace_id=workspace.id,
        project_id=project.id,
        actor_user_id=current_user.id,
        event_type="project.created",
        entity_type="project",
        entity_id=str(project.id),
        payload={"name": project.name},
    )
    db.commit()
    _ensure_default_prompts(db, project.id)
    db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdateRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, project_id)
    project.name = payload.name.strip()
    project.description = payload.description
    project.status = ProjectStatus(payload.status)
    _record_audit(
        db,
        workspace_id=workspace.id,
        project_id=project.id,
        actor_user_id=current_user.id,
        event_type="project.updated",
        entity_type="project",
        entity_id=str(project.id),
    )
    db.commit()
    db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, project_id)
    db.delete(project)
    _record_audit(
        db,
        workspace_id=workspace.id,
        project_id=project_id,
        actor_user_id=current_user.id,
        event_type="project.deleted",
        entity_type="project",
        entity_id=str(project_id),
    )
    db.commit()
    return {"ok": True}


@router.get("/brand/{project_id}", response_model=BrandProfileResponse)
def get_brand_profile(
    project_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> BrandProfileResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, project_id)
    if not project.brand_profile:
        brand = BrandProfile(project_id=project.id, brand_name=project.name)
        db.add(brand)
        db.commit()
        db.refresh(brand)
        return BrandProfileResponse.model_validate(brand)
    return BrandProfileResponse.model_validate(project.brand_profile)


@router.put("/brand/{project_id}", response_model=BrandProfileResponse)
def update_brand_profile(
    project_id: int,
    payload: BrandProfileRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> BrandProfileResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, project_id)
    brand = project.brand_profile or BrandProfile(project_id=project.id, brand_name=project.name)
    if brand.id is None:
        db.add(brand)
    brand.brand_name = payload.brand_name.strip()
    brand.website_url = str(payload.website_url) if payload.website_url else None
    brand.summary = payload.summary
    brand.voice_notes = payload.voice_notes
    brand.product_summary = payload.product_summary
    brand.target_audience = payload.target_audience
    brand.call_to_action = payload.call_to_action
    brand.reddit_username = payload.reddit_username
    brand.linkedin_url = str(payload.linkedin_url) if payload.linkedin_url else None
    _record_audit(
        db,
        workspace_id=workspace.id,
        project_id=project.id,
        actor_user_id=current_user.id,
        event_type="brand.updated",
        entity_type="brand_profile",
        entity_id=str(project.id),
    )
    db.commit()
    db.refresh(brand)
    return BrandProfileResponse.model_validate(brand)


@router.post("/brand/{project_id}/analyze", response_model=BrandProfileResponse)
def analyze_brand_website(
    project_id: int,
    payload: BrandAnalysisRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> BrandProfileResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, project_id)
    analysis = ProductCopilot().analyze_website(str(payload.website_url))
    brand = project.brand_profile or BrandProfile(project_id=project.id, brand_name=project.name)
    if brand.id is None:
        db.add(brand)
    brand.brand_name = analysis.brand_name
    brand.website_url = str(payload.website_url)
    brand.summary = analysis.summary
    brand.product_summary = analysis.product_summary
    brand.target_audience = analysis.target_audience
    brand.call_to_action = analysis.call_to_action
    brand.voice_notes = analysis.voice_notes
    brand.last_analyzed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(brand)
    return BrandProfileResponse.model_validate(brand)


@router.get("/personas", response_model=list[PersonaResponse])
def list_personas(
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[PersonaResponse]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, project_id)
    rows = db.scalars(select(Persona).where(Persona.project_id == project.id).order_by(Persona.created_at.desc())).all()
    return [PersonaResponse.model_validate(row) for row in rows]


@router.post("/personas", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
def create_persona(
    payload: PersonaRequest,
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> PersonaResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, project_id)
    persona = Persona(project_id=project.id, **payload.model_dump())
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return PersonaResponse.model_validate(persona)


@router.post("/personas/generate", response_model=list[PersonaResponse])
def generate_personas(
    project_id: int = Query(..., ge=1),
    count: int = Query(default=4, ge=1, le=8),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[PersonaResponse]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, project_id)
    generated = ProductCopilot().suggest_personas(project.brand_profile, count=count)
    rows = []
    for item in generated:
        persona = Persona(project_id=project.id, **item)
        db.add(persona)
        rows.append(persona)
    db.commit()
    for row in rows:
        db.refresh(row)
    return [PersonaResponse.model_validate(row) for row in rows]


@router.delete("/personas/{persona_id}")
def delete_persona(
    persona_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    persona = db.scalar(select(Persona).join(Project).where(Persona.id == persona_id, Project.workspace_id == workspace.id))
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found.")
    db.delete(persona)
    db.commit()
    return {"ok": True}


@router.get("/discovery/keywords", response_model=list[KeywordResponse])
def list_keywords(
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[KeywordResponse]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, project_id)
    rows = db.scalars(
        select(DiscoveryKeyword).where(DiscoveryKeyword.project_id == project.id).order_by(DiscoveryKeyword.priority_score.desc())
    ).all()
    return [KeywordResponse.model_validate(row) for row in rows]


@router.post("/discovery/keywords", response_model=KeywordResponse, status_code=status.HTTP_201_CREATED)
def create_keyword(
    payload: KeywordRequest,
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> KeywordResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, project_id)
    if payload.is_active:
        enforce_limit(db, workspace, "keywords", count_active_keywords(db, project.id))
    row = DiscoveryKeyword(project_id=project.id, source="manual", **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return KeywordResponse.model_validate(row)


@router.post("/discovery/keywords/generate", response_model=list[KeywordResponse])
def generate_keywords(
    payload: KeywordGenerateRequest,
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[KeywordResponse]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, project_id)
    personas = db.scalars(select(Persona).where(Persona.project_id == project.id, Persona.is_active.is_(True))).all()
    generated = ProductCopilot().generate_keywords(project.brand_profile, personas, payload.count)
    created: list[DiscoveryKeyword] = []
    for item in generated:
        existing = db.scalar(
            select(DiscoveryKeyword).where(
                DiscoveryKeyword.project_id == project.id,
                DiscoveryKeyword.keyword == item.keyword,
            )
        )
        if existing:
            continue
        if count_active_keywords(db, project.id) >= get_limit(db, workspace, "keywords"):
            break
        row = DiscoveryKeyword(
            project_id=project.id,
            keyword=item.keyword,
            rationale=item.rationale,
            priority_score=item.priority_score,
            source="generated",
            is_active=True,
        )
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return [KeywordResponse.model_validate(row) for row in created]


@router.delete("/discovery/keywords/{keyword_id}")
def delete_keyword(
    keyword_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(
        select(DiscoveryKeyword).join(Project).where(DiscoveryKeyword.id == keyword_id, Project.workspace_id == workspace.id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Keyword not found.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/discovery/subreddits", response_model=list[SubredditResponse])
def list_subreddits(
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[SubredditResponse]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, project_id)
    rows = db.scalars(
        select(MonitoredSubreddit)
        .where(MonitoredSubreddit.project_id == project.id)
        .options(selectinload(MonitoredSubreddit.analyses))
        .order_by(MonitoredSubreddit.fit_score.desc(), MonitoredSubreddit.subscribers.desc())
    ).all()
    return [SubredditResponse.model_validate(row) for row in rows]


@router.post("/discovery/subreddits", response_model=SubredditResponse, status_code=status.HTTP_201_CREATED)
def create_subreddit(
    payload: SubredditRequest,
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> SubredditResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, project_id)
    if payload.is_active:
        enforce_limit(db, workspace, "subreddits", count_active_subreddits(db, project.id))
    row = MonitoredSubreddit(project_id=project.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return SubredditResponse.model_validate(row)


@router.post("/discovery/subreddits/discover", response_model=list[SubredditResponse])
def discover_subreddits(
    payload: SubredditDiscoverRequest,
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[SubredditResponse]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, project_id)
    keywords = db.scalars(
        select(DiscoveryKeyword)
        .where(DiscoveryKeyword.project_id == project.id, DiscoveryKeyword.is_active.is_(True))
        .order_by(DiscoveryKeyword.priority_score.desc())
    ).all()
    if not keywords:
        raise HTTPException(status_code=400, detail="Generate or add keywords before discovering subreddits.")
    reddit = RedditClient()
    created: list[MonitoredSubreddit] = []
    seen_names = {
        row.name.lower()
        for row in db.scalars(select(MonitoredSubreddit).where(MonitoredSubreddit.project_id == project.id)).all()
    }
    for keyword in keywords[:5]:
        try:
            matches = reddit.search_subreddits(keyword.keyword, limit=payload.max_subreddits)
        except Exception:
            continue
        for match in matches:
            if count_active_subreddits(db, project.id) >= get_limit(db, workspace, "subreddits"):
                break
            if match.name.lower() in seen_names:
                continue
            rules = reddit.subreddit_rules(match.name)
            fit_score = min(100, 35 + keyword.priority_score // 2)
            activity_score = min(100, 20 + int(match.subscribers > 10000) * 20 + int(match.subscribers > 100000) * 20)
            row = MonitoredSubreddit(
                project_id=project.id,
                name=match.name,
                title=match.title,
                description=match.description,
                subscribers=match.subscribers,
                activity_score=activity_score,
                fit_score=fit_score,
                rules_summary="\n".join(rules[:5]) if rules else None,
                is_active=True,
            )
            db.add(row)
            db.flush()
            top_post_types, audience_signals, posting_risk, recommendation = _build_subreddit_analysis(
                match.name,
                match.description,
                rules,
            )
            db.add(
                SubredditAnalysis(
                    monitored_subreddit_id=row.id,
                    top_post_types=top_post_types,
                    audience_signals=audience_signals,
                    posting_risk=posting_risk,
                    recommendation=recommendation,
                )
            )
            seen_names.add(match.name.lower())
            created.append(row)
        if len(created) >= payload.max_subreddits:
            break
    db.commit()
    for row in created:
        db.refresh(row)
    return [SubredditResponse.model_validate(row) for row in created]


@router.post("/subreddits/{subreddit_id}/analyze", response_model=SubredditResponse)
def analyze_subreddit(
    subreddit_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> SubredditResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    subreddit = db.scalar(
        select(MonitoredSubreddit)
        .join(Project)
        .where(MonitoredSubreddit.id == subreddit_id, Project.workspace_id == workspace.id)
        .options(selectinload(MonitoredSubreddit.analyses))
    )
    if not subreddit:
        raise HTTPException(status_code=404, detail="Subreddit not found.")
    reddit = RedditClient()
    about = reddit.subreddit_about(subreddit.name)
    rules = reddit.subreddit_rules(subreddit.name)
    subreddit.title = about.get("title") or subreddit.title
    subreddit.description = about.get("public_description") or subreddit.description
    subreddit.subscribers = int(about.get("subscribers") or subreddit.subscribers or 0)
    top_post_types, audience_signals, posting_risk, recommendation = _build_subreddit_analysis(
        subreddit.name,
        subreddit.description or "",
        rules,
    )
    db.add(
        SubredditAnalysis(
            monitored_subreddit_id=subreddit.id,
            top_post_types=top_post_types,
            audience_signals=audience_signals,
            posting_risk=posting_risk,
            recommendation=recommendation,
        )
    )
    db.commit()
    db.refresh(subreddit)
    return SubredditResponse.model_validate(subreddit)


@router.delete("/discovery/subreddits/{subreddit_id}")
def delete_subreddit(
    subreddit_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(
        select(MonitoredSubreddit).join(Project).where(MonitoredSubreddit.id == subreddit_id, Project.workspace_id == workspace.id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Subreddit not found.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/scans", response_model=ScanRunResponse)
def create_scan(
    payload: ScanRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> ScanRunResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, payload.project_id)
    run = _run_scan(db, project, payload)
    return ScanRunResponse.model_validate(run)


@router.get("/opportunities", response_model=list[OpportunityResponse])
def list_opportunities(
    project_id: int = Query(..., ge=1),
    status_filter: str = Query(default="all", alias="status"),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[OpportunityResponse]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    _get_project(db, workspace.id, project_id)
    stmt = select(Opportunity).where(Opportunity.project_id == project_id)
    if status_filter != "all":
        stmt = stmt.where(Opportunity.status == OpportunityStatus(status_filter))
    rows = db.scalars(stmt.order_by(Opportunity.score.desc(), Opportunity.created_at.desc())).all()
    return [OpportunityResponse.model_validate(row) for row in rows]


@router.put("/opportunities/{opportunity_id}/status", response_model=OpportunityResponse)
def update_opportunity_status(
    opportunity_id: int,
    payload: OpportunityStatusRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> OpportunityResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(
        select(Opportunity).join(Project).where(Opportunity.id == opportunity_id, Project.workspace_id == workspace.id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    row.status = OpportunityStatus(payload.status)
    if row.status == OpportunityStatus.POSTED:
        row.posted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return OpportunityResponse.model_validate(row)


@router.post("/drafts/replies", response_model=ReplyDraftResponse, status_code=status.HTTP_201_CREATED)
def generate_reply_draft(
    payload: ReplyDraftRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> ReplyDraftResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    opportunity = db.scalar(
        select(Opportunity)
        .join(Project)
        .where(Opportunity.id == payload.opportunity_id, Project.workspace_id == workspace.id)
        .options(selectinload(Opportunity.reply_drafts))
    )
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    project = _get_project(db, workspace.id, opportunity.project_id)
    _ensure_default_prompts(db, project.id)
    prompts = db.scalars(select(PromptTemplate).where(PromptTemplate.project_id == project.id)).all()
    content, rationale, source_prompt = ProductCopilot().generate_reply(opportunity, project.brand_profile, list(prompts))
    next_version = (db.scalar(select(func.max(ReplyDraft.version)).where(ReplyDraft.opportunity_id == opportunity.id)) or 0) + 1
    draft = ReplyDraft(
        project_id=project.id,
        opportunity_id=opportunity.id,
        content=content,
        rationale=rationale,
        source_prompt=source_prompt,
        version=next_version,
    )
    opportunity.status = OpportunityStatus.DRAFTING
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return ReplyDraftResponse.model_validate(draft)


@router.post("/drafts/posts", response_model=PostDraftResponse, status_code=status.HTTP_201_CREATED)
def generate_post_draft(
    payload: PostDraftRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> PostDraftResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    project = _get_project(db, workspace.id, payload.project_id)
    _ensure_default_prompts(db, project.id)
    prompts = db.scalars(select(PromptTemplate).where(PromptTemplate.project_id == project.id)).all()
    title, body, rationale = ProductCopilot().generate_post(project.brand_profile, list(prompts))
    version = (db.scalar(select(func.max(PostDraft.version)).where(PostDraft.project_id == project.id)) or 0) + 1
    draft = PostDraft(
        project_id=project.id,
        title=title,
        body=body,
        rationale=rationale,
        source_prompt="\n".join(prompt.instructions for prompt in prompts if prompt.prompt_type == "post"),
        version=version,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return PostDraftResponse.model_validate(draft)


@router.get("/prompts", response_model=list[PromptTemplateResponse])
def list_prompts(
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[PromptTemplateResponse]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    _get_project(db, workspace.id, project_id)
    _ensure_default_prompts(db, project_id)
    rows = db.scalars(select(PromptTemplate).where(PromptTemplate.project_id == project_id).order_by(PromptTemplate.prompt_type)).all()
    return [PromptTemplateResponse.model_validate(row) for row in rows]


@router.post("/prompts", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_prompt(
    payload: PromptTemplateRequest,
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> PromptTemplateResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    _get_project(db, workspace.id, project_id)
    row = PromptTemplate(project_id=project_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return PromptTemplateResponse.model_validate(row)


@router.put("/prompts/{prompt_id}", response_model=PromptTemplateResponse)
def update_prompt(
    prompt_id: int,
    payload: PromptTemplateRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> PromptTemplateResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(select(PromptTemplate).join(Project).where(PromptTemplate.id == prompt_id, Project.workspace_id == workspace.id))
    if not row:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return PromptTemplateResponse.model_validate(row)


@router.delete("/prompts/{prompt_id}")
def delete_prompt(
    prompt_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(select(PromptTemplate).join(Project).where(PromptTemplate.id == prompt_id, Project.workspace_id == workspace.id))
    if not row:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/webhooks", response_model=list[WebhookResponse])
def list_webhooks(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[WebhookResponse]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    rows = db.scalars(select(WebhookEndpoint).where(WebhookEndpoint.workspace_id == workspace.id)).all()
    return [WebhookResponse.model_validate(row) for row in rows]


@router.post("/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    payload: WebhookRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> WebhookResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    row = WebhookEndpoint(
        workspace_id=workspace.id,
        target_url=str(payload.target_url),
        event_types=payload.event_types,
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return WebhookResponse.model_validate(row)


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(
    webhook_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id, WebhookEndpoint.workspace_id == workspace.id))
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/webhooks/{webhook_id}/sample-payload")
def webhook_sample_payload(
    webhook_id: int,
    event_type: str = Query(default="opportunity.found"),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id, WebhookEndpoint.workspace_id == workspace.id))
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    return {
        "event_type": event_type,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "workspace_id": workspace.id,
        "project_id": None,
        "payload": {"message": "Sample webhook payload from RedditFlow."},
    }


@router.post("/webhooks/{webhook_id}/test")
def test_webhook(
    webhook_id: int,
    payload: WebhookTestRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id, WebhookEndpoint.workspace_id == workspace.id))
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    sample = {
        "event_type": payload.event_type,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "workspace_id": workspace.id,
        "payload": {"message": "Test event", "source": "redditflow"},
    }
    body = json.dumps(sample).encode("utf-8")
    signature = hmac.new(row.signing_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            row.target_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-RedditFlow-Signature": signature,
                "X-RedditFlow-Event": payload.event_type,
            },
        )
        response.raise_for_status()
    row.last_tested_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "status_code": response.status_code}


@router.get("/secrets", response_model=list[SecretResponse])
def list_secrets(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[SecretResponse]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    rows = db.scalars(select(IntegrationSecret).where(IntegrationSecret.workspace_id == workspace.id)).all()
    return [SecretResponse.model_validate(row) for row in rows]


@router.post("/secrets", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
def upsert_secret(
    payload: SecretRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> SecretResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(
        select(IntegrationSecret).where(
            IntegrationSecret.workspace_id == workspace.id,
            IntegrationSecret.provider == payload.provider,
            IntegrationSecret.label == payload.label,
        )
    )
    encrypted = encrypt_text(payload.value)
    if row:
        row.encrypted_payload = encrypted
    else:
        row = IntegrationSecret(
            workspace_id=workspace.id,
            provider=payload.provider,
            label=payload.label,
            encrypted_payload=encrypted,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return SecretResponse.model_validate(row)


@router.delete("/secrets/{secret_id}")
def delete_secret(
    secret_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(
        select(IntegrationSecret).where(IntegrationSecret.id == secret_id, IntegrationSecret.workspace_id == workspace.id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Secret not found.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/invitations", response_model=list[InvitationResponse])
def list_invitations(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[InvitationResponse]:
    membership = _ensure_workspace_membership(db, workspace.id, current_user.id)
    if membership.role == MembershipRole.MEMBER:
        raise HTTPException(status_code=403, detail="Only admins can manage invitations.")
    rows = db.scalars(select(Invitation).where(Invitation.workspace_id == workspace.id).order_by(Invitation.created_at.desc())).all()
    return [InvitationResponse.model_validate(row) for row in rows]


@router.post("/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: InvitationRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> InvitationResponse:
    membership = _ensure_workspace_membership(db, workspace.id, current_user.id)
    if membership.role == MembershipRole.MEMBER:
        raise HTTPException(status_code=403, detail="Only admins can invite teammates.")
    invitation = Invitation(
        workspace_id=workspace.id,
        email=payload.email.lower(),
        role=MembershipRole(payload.role),
        invited_by_user_id=current_user.id,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return InvitationResponse.model_validate(invitation)


@router.post("/invitations/accept/{token}", response_model=InvitationResponse)
def accept_invitation(
    token: str,
    current_user: AccountUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvitationResponse:
    invitation = db.scalar(select(Invitation).where(Invitation.token == token))
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found.")
    if invitation.accepted_at:
        raise HTTPException(status_code=400, detail="Invitation already accepted.")
    if invitation.email != current_user.email:
        raise HTTPException(status_code=403, detail="Invitation email does not match the current user.")
    existing = db.scalar(
        select(Membership).where(Membership.workspace_id == invitation.workspace_id, Membership.user_id == current_user.id)
    )
    if not existing:
        db.add(Membership(workspace_id=invitation.workspace_id, user_id=current_user.id, role=invitation.role))
    invitation.accepted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(invitation)
    return InvitationResponse.model_validate(invitation)


@router.get("/billing/plans", response_model=list[PlanResponse])
def list_plans() -> list[PlanResponse]:
    return [PlanResponse(**row) for row in serialize_plan_catalog()]


@router.get("/billing/current", response_model=SubscriptionResponse)
def current_billing(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    return _subscription_response(db, workspace)


@router.post("/redemptions", response_model=RedemptionResponse)
def redeem_code(
    payload: RedemptionRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> RedemptionResponse:
    _ensure_workspace_membership(db, workspace.id, current_user.id)
    redemption = db.scalar(select(Redemption).where(Redemption.code == payload.code))
    if not redemption:
        raise HTTPException(status_code=404, detail="Redemption code not found.")
    if redemption.redeemed_at:
        raise HTTPException(status_code=400, detail="Redemption code already used.")
    subscription = get_or_create_subscription(db, workspace)
    subscription.plan_code = redemption.plan_code
    redemption.workspace_id = workspace.id
    redemption.redeemed_by_user_id = current_user.id
    redemption.redeemed_at = datetime.now(timezone.utc)
    db.commit()
    return RedemptionResponse(success=True, plan_code=redemption.plan_code, message="Plan upgraded successfully.")
