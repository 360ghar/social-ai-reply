"""Pydantic models for visibility-related tables."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PromptRunStatus(StrEnum):
    """Status values for prompt run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class PromptSet(BaseModel):
    """Model for prompt_sets table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class PromptRun(BaseModel):
    """Model for prompt_runs table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    prompt_set_id: int
    model_name: str
    status: PromptRunStatus
    scheduled_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime


class AIResponse(BaseModel):
    """Model for ai_responses table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    prompt_run_id: int
    input_text: str
    output_text: str
    brand_mentioned: bool = False
    tokens_used: int = 0
    latency_ms: int = 0
    created_at: datetime


class BrandMention(BaseModel):
    """Model for brand_mentions table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ai_response_id: int
    mention_text: str
    context: str | None = None
    created_at: datetime


class Citation(BaseModel):
    """Model for citations table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ai_response_id: int
    url: str
    title: str | None = None
    excerpt: str | None = None
    domain: str | None = None
    first_seen_at: datetime
    created_at: datetime


class SourceDomain(BaseModel):
    """Model for source_domains table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    domain: str = Field(min_length=1, max_length=255)
    total_citations: int = 0
    created_at: datetime
    updated_at: datetime


class SourceGap(BaseModel):
    """Model for source_gaps table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    domain: str = Field(min_length=1, max_length=255)
    citation_count: int = 0
    discovered_at: datetime
    created_at: datetime
