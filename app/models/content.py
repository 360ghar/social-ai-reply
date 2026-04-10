"""Pydantic models for content-related tables: reply drafts, post drafts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReplyDraft(BaseModel):
    """Model for reply_drafts table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    opportunity_id: int
    content: str = Field(min_length=1)
    persona_used: str | None = None
    keywords_used: list[str] | None = None
    is_approved: bool = False
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PostDraft(BaseModel):
    """Model for post_drafts table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)
    target_subreddit: str | None = None
    is_approved: bool = False
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
