from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.datetime import utc_now

if TYPE_CHECKING:
    from app.db.models.project import Project


class PromptSet(Base):
    __tablename__ = "prompt_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(255), default="general")
    prompts: Mapped[list[str]] = mapped_column(JSON, default=list)
    target_models: Mapped[list[str]] = mapped_column(
        JSON, default=lambda: ["chatgpt", "perplexity", "gemini", "claude"]
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    schedule: Mapped[str] = mapped_column(String(255), default="daily")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project: Mapped["Project"] = relationship(back_populates="prompt_sets")  # noqa: F821
    runs: Mapped[list["PromptRun"]] = relationship(back_populates="prompt_set", cascade="all, delete-orphan")


class PromptRun(Base):
    __tablename__ = "prompt_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_set_id: Mapped[int] = mapped_column(ForeignKey("prompt_sets.id", ondelete="CASCADE"), index=True)
    model_name: Mapped[str] = mapped_column(String(255))
    prompt_text: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(50), default="queued")
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    prompt_set: Mapped["PromptSet"] = relationship(back_populates="runs")
    responses: Mapped[list["AIResponse"]] = relationship(back_populates="prompt_run", cascade="all, delete-orphan")


class AIResponse(Base):
    __tablename__ = "ai_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_run_id: Mapped[int] = mapped_column(ForeignKey("prompt_runs.id", ondelete="CASCADE"), index=True)
    model_name: Mapped[str] = mapped_column(String(255))
    raw_response: Mapped[str] = mapped_column(Text)
    brand_mentioned: Mapped[bool] = mapped_column(Boolean, default=False)
    competitor_mentions: Mapped[list] = mapped_column(JSON, default=list)
    sentiment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    response_length: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    prompt_run: Mapped["PromptRun"] = relationship(back_populates="responses")
    mentions: Mapped[list["BrandMention"]] = relationship(back_populates="ai_response", cascade="all, delete-orphan")
    citations: Mapped[list["Citation"]] = relationship(back_populates="ai_response", cascade="all, delete-orphan")


class BrandMention(Base):
    __tablename__ = "brand_mentions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ai_response_id: Mapped[int] = mapped_column(ForeignKey("ai_responses.id", ondelete="CASCADE"), index=True)
    entity_name: Mapped[str] = mapped_column(String(255))
    mention_type: Mapped[str] = mapped_column(String(50), default="brand")
    context_snippet: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    position_in_response: Mapped[int] = mapped_column(Integer, default=0)

    ai_response: Mapped["AIResponse"] = relationship(back_populates="mentions")


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ai_response_id: Mapped[int] = mapped_column(ForeignKey("ai_responses.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(1024))
    domain: Mapped[str] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    ai_response: Mapped["AIResponse"] = relationship(back_populates="citations")


class SourceDomain(Base):
    __tablename__ = "source_domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    domain: Mapped[str] = mapped_column(String(255))
    total_citations: Mapped[int] = mapped_column(Integer, default=0)
    avg_influence_score: Mapped[float] = mapped_column(Float, default=0.0)
    last_cited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="source_domains")  # noqa: F821


class SourceGap(Base):
    __tablename__ = "source_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    competitor_name: Mapped[str] = mapped_column(String(255))
    domain: Mapped[str] = mapped_column(String(255))
    citation_count: Mapped[int] = mapped_column(Integer, default=0)
    gap_type: Mapped[str] = mapped_column(String(100), default="competitor_cited_brand_not")
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="source_gaps")  # noqa: F821


class VisibilitySnapshot(Base):
    __tablename__ = "visibility_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    model_name: Mapped[str] = mapped_column(String(255))
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    total_prompts: Mapped[int] = mapped_column(Integer, default=0)
    brand_mentioned_count: Mapped[int] = mapped_column(Integer, default=0)
    share_of_voice: Mapped[float] = mapped_column(Float, default=0.0)
    top_competitors: Mapped[list] = mapped_column(JSON, default=list)

    project: Mapped["Project"] = relationship(back_populates="visibility_snapshots")  # noqa: F821
