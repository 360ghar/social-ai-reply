from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import OpportunityStatus, ScanStatus
from app.utils.datetime import utc_now

if TYPE_CHECKING:
    from app.db.models.project import Project


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

    project: Mapped["Project"] = relationship(back_populates="keywords")  # noqa: F821

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

    project: Mapped["Project"] = relationship(back_populates="subreddits")  # noqa: F821
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
    status: Mapped[ScanStatus] = mapped_column(
        SAEnum(ScanStatus), default=ScanStatus.QUEUED, index=True
    )
    search_window_hours: Mapped[int] = mapped_column(Integer, default=72)
    posts_scanned: Mapped[int] = mapped_column(Integer, default=0)
    opportunities_found: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="scan_runs")  # noqa: F821
    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="scan_run")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    scan_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("scan_runs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    reddit_post_id: Mapped[str] = mapped_column(String(64))
    subreddit_name: Mapped[str] = mapped_column(String(255), index=True)
    author: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(512))
    permalink: Mapped[str] = mapped_column(String(1024))
    body_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    status: Mapped[OpportunityStatus] = mapped_column(
        SAEnum(OpportunityStatus), default=OpportunityStatus.NEW, index=True
    )
    score_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    keyword_hits: Mapped[list[str]] = mapped_column(JSON, default=list)
    rule_risk: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="opportunities")  # noqa: F821
    scan_run: Mapped["ScanRun | None"] = relationship(back_populates="opportunities")
    reply_drafts: Mapped[list["ReplyDraft"]] = relationship(  # noqa: F821
        back_populates="opportunity", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("project_id", "reddit_post_id", name="uq_project_reddit_post"),
        Index("ix_opportunities_project_status_score", "project_id", "status", "score"),
    )
