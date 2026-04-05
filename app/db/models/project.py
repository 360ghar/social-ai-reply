from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import ProjectStatus
from app.utils.datetime import utc_now

if TYPE_CHECKING:
    from app.db.models.discovery import (
        DiscoveryKeyword,
        MonitoredSubreddit,
        Opportunity,
        ScanRun,
    )
    from app.db.models.workspace import Workspace


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus), default=ProjectStatus.ACTIVE, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    workspace: Mapped["Workspace"] = relationship(back_populates="projects")  # noqa: F821
    brand_profile: Mapped["BrandProfile | None"] = relationship(
        back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    personas: Mapped[list["Persona"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    keywords: Mapped[list["DiscoveryKeyword"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    subreddits: Mapped[list["MonitoredSubreddit"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    scan_runs: Mapped[list["ScanRun"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    opportunities: Mapped[list["Opportunity"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    reply_drafts: Mapped[list["ReplyDraft"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    post_drafts: Mapped[list["PostDraft"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    prompts: Mapped[list["PromptTemplate"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    prompt_sets: Mapped[list["PromptSet"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    source_domains: Mapped[list["SourceDomain"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    source_gaps: Mapped[list["SourceGap"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    visibility_snapshots: Mapped[list["VisibilitySnapshot"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    campaigns: Mapped[list["Campaign"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    published_posts: Mapped[list["PublishedPost"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    analytics_snapshots: Mapped[list["AnalyticsSnapshot"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    auto_pipelines: Mapped[list["AutoPipeline"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_workspace_project_slug"),
        Index("ix_projects_workspace_status", "workspace_id", "status"),
    )


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
    business_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
