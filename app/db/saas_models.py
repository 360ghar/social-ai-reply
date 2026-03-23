import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def invitation_expiry() -> datetime:
    return utc_now() + timedelta(days=7)


class MembershipRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ScanStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class OpportunityStatus(str, Enum):
    NEW = "new"
    SAVED = "saved"
    DRAFTING = "drafting"
    POSTED = "posted"
    IGNORED = "ignored"


class SubscriptionStatus(str, Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class AccountUser(Base):
    __tablename__ = "account_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    workspaces_owned: Mapped[list["Workspace"]] = relationship(back_populates="owner")
    memberships: Mapped[list["Membership"]] = relationship(back_populates="user")


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    owner: Mapped["AccountUser"] = relationship(back_populates="workspaces_owned")
    memberships: Mapped[list["Membership"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    invitations: Mapped[list["Invitation"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    subscription: Mapped["Subscription | None"] = relationship(back_populates="workspace", uselist=False)
    webhooks: Mapped[list["WebhookEndpoint"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    secrets: Mapped[list["IntegrationSecret"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), index=True)
    role: Mapped[MembershipRole] = mapped_column(SAEnum(MembershipRole), default=MembershipRole.MEMBER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    workspace: Mapped["Workspace"] = relationship(back_populates="memberships")
    user: Mapped["AccountUser"] = relationship(back_populates="memberships")

    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(SAEnum(ProjectStatus), default=ProjectStatus.ACTIVE, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    workspace: Mapped["Workspace"] = relationship(back_populates="projects")
    brand_profile: Mapped["BrandProfile | None"] = relationship(back_populates="project", uselist=False, cascade="all, delete-orphan")
    personas: Mapped[list["Persona"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    keywords: Mapped[list["DiscoveryKeyword"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    subreddits: Mapped[list["MonitoredSubreddit"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    scan_runs: Mapped[list["ScanRun"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    reply_drafts: Mapped[list["ReplyDraft"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    post_drafts: Mapped[list["PostDraft"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    prompts: Mapped[list["PromptTemplate"]] = relationship(back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("workspace_id", "slug", name="uq_workspace_project_slug"),)


class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True, index=True)
    brand_name: Mapped[str] = mapped_column(String(255))
    website_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    call_to_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    reddit_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project: Mapped["Project"] = relationship(back_populates="brand_profile")


class Persona(Base):
    __tablename__ = "personas_v1"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    pain_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    goals: Mapped[list[str]] = mapped_column(JSON, default=list)
    triggers: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_subreddits: Mapped[list[str]] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(50), default="manual")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project: Mapped["Project"] = relationship(back_populates="personas")


class DiscoveryKeyword(Base):
    __tablename__ = "discovery_keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    keyword: Mapped[str] = mapped_column(String(255))
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority_score: Mapped[int] = mapped_column(Integer, default=50)
    source: Mapped[str] = mapped_column(String(50), default="manual")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project: Mapped["Project"] = relationship(back_populates="keywords")

    __table_args__ = (UniqueConstraint("project_id", "keyword", name="uq_project_keyword"),)


class MonitoredSubreddit(Base):
    __tablename__ = "monitored_subreddits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    subscribers: Mapped[int] = mapped_column(Integer, default=0)
    activity_score: Mapped[int] = mapped_column(Integer, default=0)
    fit_score: Mapped[int] = mapped_column(Integer, default=0)
    rules_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project: Mapped["Project"] = relationship(back_populates="subreddits")
    analyses: Mapped[list["SubredditAnalysis"]] = relationship(back_populates="subreddit", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_project_subreddit"),)


class SubredditAnalysis(Base):
    __tablename__ = "subreddit_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    monitored_subreddit_id: Mapped[int] = mapped_column(
        ForeignKey("monitored_subreddits.id", ondelete="CASCADE"),
        index=True,
    )
    top_post_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    audience_signals: Mapped[list[str]] = mapped_column(JSON, default=list)
    posting_risk: Mapped[list[str]] = mapped_column(JSON, default=list)
    recommendation: Mapped[str] = mapped_column(Text)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    subreddit: Mapped["MonitoredSubreddit"] = relationship(back_populates="analyses")


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    status: Mapped[ScanStatus] = mapped_column(SAEnum(ScanStatus), default=ScanStatus.QUEUED, index=True)
    search_window_hours: Mapped[int] = mapped_column(Integer, default=72)
    posts_scanned: Mapped[int] = mapped_column(Integer, default=0)
    opportunities_found: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="scan_runs")
    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="scan_run")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey("scan_runs.id", ondelete="SET NULL"), index=True, nullable=True)
    reddit_post_id: Mapped[str] = mapped_column(String(64))
    subreddit_name: Mapped[str] = mapped_column(String(255), index=True)
    author: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(512))
    permalink: Mapped[str] = mapped_column(String(1024))
    body_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    status: Mapped[OpportunityStatus] = mapped_column(SAEnum(OpportunityStatus), default=OpportunityStatus.NEW, index=True)
    score_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    keyword_hits: Mapped[list[str]] = mapped_column(JSON, default=list)
    rule_risk: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="opportunities")
    scan_run: Mapped["ScanRun | None"] = relationship(back_populates="opportunities")
    reply_drafts: Mapped[list["ReplyDraft"]] = relationship(back_populates="opportunity", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("project_id", "reddit_post_id", name="uq_project_reddit_post"),)


class ReplyDraft(Base):
    __tablename__ = "reply_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="reply_drafts")
    opportunity: Mapped["Opportunity"] = relationship(back_populates="reply_drafts")


class PostDraft(Base):
    __tablename__ = "post_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="post_drafts")


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True)
    prompt_type: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(255))
    system_prompt: Mapped[str] = mapped_column(Text)
    instructions: Mapped[str] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project: Mapped["Project | None"] = relationship(back_populates="prompts")


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    target_url: Mapped[str] = mapped_column(String(1024))
    signing_secret: Mapped[str] = mapped_column(String(128), default=lambda: secrets.token_urlsafe(24))
    event_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    workspace: Mapped["Workspace"] = relationship(back_populates="webhooks")


class IntegrationSecret(Base):
    __tablename__ = "integration_secrets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(100))
    label: Mapped[str] = mapped_column(String(100))
    encrypted_payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    workspace: Mapped["Workspace"] = relationship(back_populates="secrets")

    __table_args__ = (UniqueConstraint("workspace_id", "provider", "label", name="uq_workspace_secret"),)


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[MembershipRole] = mapped_column(SAEnum(MembershipRole), default=MembershipRole.MEMBER)
    token: Mapped[str] = mapped_column(String(255), unique=True, default=lambda: secrets.token_urlsafe(24))
    invited_by_user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=invitation_expiry)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    workspace: Mapped["Workspace"] = relationship(back_populates="invitations")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True, index=True)
    plan_code: Mapped[str] = mapped_column(String(50), default="free")
    status: Mapped[SubscriptionStatus] = mapped_column(SAEnum(SubscriptionStatus), default=SubscriptionStatus.TRIALING)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    workspace: Mapped["Workspace"] = relationship(back_populates="subscription")


class PlanEntitlement(Base):
    __tablename__ = "plan_entitlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_code: Mapped[str] = mapped_column(String(50), index=True)
    feature_key: Mapped[str] = mapped_column(String(100), index=True)
    limit_value: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (UniqueConstraint("plan_code", "feature_key", name="uq_plan_feature"),)


class Redemption(Base):
    __tablename__ = "redemptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    plan_code: Mapped[str] = mapped_column(String(50))
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True)
    redeemed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("account_users.id", ondelete="SET NULL"), nullable=True)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("account_users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


Index("ix_projects_workspace_status", Project.workspace_id, Project.status)
Index("ix_opportunities_project_status_score", Opportunity.project_id, Opportunity.status, Opportunity.score)


# ── AI Visibility Models ──────────────────────────────────────────

class PromptSet(Base):
    __tablename__ = "prompt_sets"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, default="general")  # intent, persona, funnel, geo
    prompts = Column(JSON, default=list)  # list of prompt strings
    target_models = Column(JSON, default=lambda: ["chatgpt", "perplexity", "gemini", "claude"])
    is_active = Column(Boolean, default=True)
    schedule = Column(String, default="daily")  # daily, weekly, manual
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    project = relationship("Project", backref="prompt_sets")

class PromptRun(Base):
    __tablename__ = "prompt_runs"
    id = Column(Integer, primary_key=True)
    prompt_set_id = Column(Integer, ForeignKey("prompt_sets.id", ondelete="CASCADE"), nullable=False)
    model_name = Column(String, nullable=False)
    prompt_text = Column(String, nullable=False)
    status = Column(String, default="queued")  # queued, running, complete, failed
    error_message = Column(String, nullable=True)
    scheduled_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    prompt_set = relationship("PromptSet", backref="runs")

class AIResponse(Base):
    __tablename__ = "ai_responses"
    id = Column(Integer, primary_key=True)
    prompt_run_id = Column(Integer, ForeignKey("prompt_runs.id", ondelete="CASCADE"), nullable=False)
    model_name = Column(String, nullable=False)
    raw_response = Column(Text, nullable=False)
    brand_mentioned = Column(Boolean, default=False)
    competitor_mentions = Column(JSON, default=list)
    sentiment = Column(String, nullable=True)  # positive, neutral, negative
    response_length = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    prompt_run = relationship("PromptRun", backref="responses")

class BrandMention(Base):
    __tablename__ = "brand_mentions"
    id = Column(Integer, primary_key=True)
    ai_response_id = Column(Integer, ForeignKey("ai_responses.id", ondelete="CASCADE"), nullable=False)
    entity_name = Column(String, nullable=False)
    mention_type = Column(String, default="brand")  # brand, competitor
    context_snippet = Column(String, nullable=True)
    position_in_response = Column(Integer, default=0)
    ai_response = relationship("AIResponse", backref="mentions")

class Citation(Base):
    __tablename__ = "citations"
    id = Column(Integer, primary_key=True)
    ai_response_id = Column(Integer, ForeignKey("ai_responses.id", ondelete="CASCADE"), nullable=False)
    url = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    title = Column(String, nullable=True)
    content_type = Column(String, nullable=True)  # review, comparison, discussion, tutorial
    first_seen_at = Column(DateTime, server_default=func.now())
    ai_response = relationship("AIResponse", backref="citations")

class SourceDomain(Base):
    __tablename__ = "source_domains"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    domain = Column(String, nullable=False)
    total_citations = Column(Integer, default=0)
    avg_influence_score = Column(Float, default=0.0)
    last_cited_at = Column(DateTime, nullable=True)
    category = Column(String, nullable=True)
    project = relationship("Project", backref="source_domains")

class SourceGap(Base):
    __tablename__ = "source_gaps"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    competitor_name = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    citation_count = Column(Integer, default=0)
    gap_type = Column(String, default="competitor_cited_brand_not")
    discovered_at = Column(DateTime, server_default=func.now())
    project = relationship("Project", backref="source_gaps")

class VisibilitySnapshot(Base):
    __tablename__ = "visibility_snapshots"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    model_name = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    total_prompts = Column(Integer, default=0)
    brand_mentioned_count = Column(Integer, default=0)
    share_of_voice = Column(Float, default=0.0)
    top_competitors = Column(JSON, default=list)
    project = relationship("Project", backref="visibility_snapshots")

# ── Notification & Activity Models ────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("account_users.id", ondelete="CASCADE"), nullable=True)
    type = Column(String, nullable=False)  # opportunity, visibility_drop, scan_complete, team, system
    title = Column(String, nullable=False)
    body = Column(String, nullable=True)
    action_url = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("account_users.id", ondelete="CASCADE"), nullable=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(Integer, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())

class UsageMetric(Base):
    __tablename__ = "usage_metrics"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    metric_key = Column(String, nullable=False)
    current_value = Column(Integer, default=0)
    limit_value = Column(Integer, default=0)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
