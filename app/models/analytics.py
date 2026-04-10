"""Pydantic models for analytics-related tables."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnalyticsSnapshot(BaseModel):
    """Model for analytics_snapshots table."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: int
    date: str
    total_opportunities: int = 0
    new_opportunities: int = 0
    drafted_replies: int = 0
    posted_replies: int = 0
    visibility_score: float = 0.0
    created_at: datetime


class AuditEvent(BaseModel):
    """Model for audit_events table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    actor_user_id: int | None = None
    event_type: str
    entity_type: str
    entity_id: int | None = None
    metadata_json: dict | None = None
    created_at: datetime


class AutoPipeline(BaseModel):
    """Model for auto_pipelines table."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: int
    status: str
    config_json: dict | None = None
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class VisibilitySnapshot(BaseModel):
    """Model for visibility_snapshots table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    date: str
    total_prompt_runs: int = 0
    total_ai_responses: int = 0
    brand_mentions_count: int = 0
    citations_count: int = 0
    created_at: datetime
