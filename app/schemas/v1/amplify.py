"""Amplification engine request/response schemas (X threads, LinkedIn posts)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TWEET_MAX_CHARS = 280


class AmplifyRequest(BaseModel):
    """Create an amplified post draft from a reply draft or opportunity."""

    reply_draft_id: int | None = Field(default=None, ge=1)
    opportunity_id: int | None = Field(default=None, ge=1)
    target: Literal["x", "linkedin"]
    voice_profile_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_source(self) -> "AmplifyRequest":
        if self.reply_draft_id is None and self.opportunity_id is None:
            raise ValueError("Provide reply_draft_id or opportunity_id.")
        return self


class AmplifyDraftResponse(BaseModel):
    """An amplified post draft (X thread or LinkedIn post)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    platform: str
    thread_json: list[str] = Field(default_factory=list)
    content: str | None = None
    status: str = "draft"
    source_reply_draft_id: int | None = None
    source_opportunity_id: int | None = None
    created_at: datetime


class AmplifyUpdateRequest(BaseModel):
    """Edit an amplified draft (thread tweets and/or linkedin content)."""

    thread_json: list[str] | None = None
    content: str | None = Field(default=None, min_length=1, max_length=40000)

    @model_validator(mode="after")
    def validate_payload(self) -> "AmplifyUpdateRequest":
        if self.thread_json is None and self.content is None:
            raise ValueError("Provide thread_json or content to update.")
        if self.thread_json is not None and not self.thread_json:
            raise ValueError("thread_json must contain at least one tweet.")
        return self


class PublishedTweet(BaseModel):
    """A single published tweet in a thread."""

    id: str
    text: str
    url: str


class PublishResponse(BaseModel):
    """Result of publishing an X thread."""

    post_draft_id: int
    platform: str = "x"
    tweet_ids: list[str]
    tweets: list[PublishedTweet]
