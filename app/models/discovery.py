"""Pydantic models for discovery-related tables."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OpportunityStatus(StrEnum):
    """Status values for opportunity."""

    NEW = "new"
    IN_REVIEW = "in_review"
    DRAFTED = "drafted"
    POSTED = "posted"
    DISMISSED = "dismissed"


class ScanStatus(StrEnum):
    """Status values for scan run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Persona(BaseModel):
    """Model for personas_v1 table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    demographics: str | None = None
    goals: str | None = None
    pain_points: str | None = None
    is_active: bool = True
    source: str | None = None
    created_at: datetime
    updated_at: datetime


class DiscoveryKeyword(BaseModel):
    """Model for discovery_keywords table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    keyword: str = Field(min_length=1, max_length=255)
    priority_score: int = Field(ge=0, le=100, default=50)
    source: str | None = None
    created_at: datetime
    updated_at: datetime


class MonitoredSubreddit(BaseModel):
    """Model for monitored_subreddits table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str = Field(min_length=1, max_length=255)
    subscribers: int | None = None
    fit_score: float = Field(default=0.0, ge=0.0, le=1.0)
    last_scanned_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class Opportunity(BaseModel):
    """Model for opportunities table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    reddit_post_id: str
    subreddit: str
    title: str
    body_excerpt: str | None = None
    author: str | None = None
    score: int = 0
    url: str
    status: OpportunityStatus
    created_at: datetime
    updated_at: datetime


class ScanRun(BaseModel):
    """Model for scan_runs table."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: int
    status: ScanStatus
    keywords_used: list[str] | None = None
    subreddits_scanned: list[str] | None = None
    opportunities_found: int = 0
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
