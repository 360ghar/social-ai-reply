"""Pydantic models for miscellaneous tables: campaigns, webhooks, integrations, notifications, etc."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CampaignStatus(StrEnum):
    """Status values for campaign."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class PublishedPostStatus(StrEnum):
    """Status values for published post."""

    PUBLISHED = "published"
    SCHEDULED = "scheduled"
    DRAFT = "draft"
    FAILED = "failed"


class NotificationType(StrEnum):
    """Type values for notification."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class Campaign(BaseModel):
    """Model for campaigns table."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: int
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: CampaignStatus
    start_date: datetime | None = None
    end_date: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PublishedPost(BaseModel):
    """Model for published_posts table."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str | None = None
    project_id: int
    reddit_post_id: str
    subreddit: str
    title: str
    content: str
    url: str | None = None
    status: PublishedPostStatus
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class WebhookEndpoint(BaseModel):
    """Model for webhook_endpoints table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    url: str = Field(min_length=1, max_length=2048)
    secret: str
    events: list[str] | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class IntegrationSecret(BaseModel):
    """Model for integration_secrets table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    provider: str
    label: str
    encrypted_value: str
    created_at: datetime
    updated_at: datetime


class RedditAccount(BaseModel):
    """Model for reddit_accounts table."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: int
    username: str
    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    connected_at: datetime
    updated_at: datetime


class Notification(BaseModel):
    """Model for notifications table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    user_id: int
    type: NotificationType
    title: str
    message: str
    is_read: bool = False
    link: str | None = None
    created_at: datetime


class ActivityLog(BaseModel):
    """Model for activity_logs table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    user_id: int | None = None
    action: str
    entity_type: str | None = None
    entity_id: int | None = None
    metadata_json: dict | None = None
    created_at: datetime


class UsageMetric(BaseModel):
    """Model for usage_metrics table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    metric_key: str
    metric_value: int = 0
    period_start: datetime
    period_end: datetime
    created_at: datetime
    updated_at: datetime
