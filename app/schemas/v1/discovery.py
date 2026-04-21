from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KeywordRequest(BaseModel):
    keyword: str = Field(min_length=2, max_length=255)
    rationale: str | None = Field(default=None, max_length=2000)
    priority_score: int = Field(default=50, ge=1, le=100)
    is_active: bool = True


class KeywordGenerateRequest(BaseModel):
    count: int = Field(default=12, ge=1, le=50)


class KeywordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    keyword: str
    rationale: str | None
    priority_score: int
    source: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SubredditRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    subscribers: int = Field(default=0, ge=0)
    activity_score: int = Field(default=0, ge=0, le=100)
    fit_score: int = Field(default=0, ge=0, le=100)
    rules_summary: str | None = Field(default=None, max_length=4000)
    is_active: bool = True


class SubredditDiscoverRequest(BaseModel):
    max_subreddits: int = Field(default=10, ge=1, le=50)


class SubredditAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    top_post_types: list[str]
    audience_signals: list[str]
    posting_risk: list[str]
    recommendation: str
    analyzed_at: datetime


class SubredditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    title: str | None
    description: str | None
    subscribers: int
    activity_score: int
    fit_score: int
    rules_summary: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    analyses: list[SubredditAnalysisResponse] = Field(default_factory=list)


class ScanRequest(BaseModel):
    project_id: int
    search_window_hours: int = Field(default=72, ge=1, le=720)
    max_posts_per_subreddit: int = Field(default=10, ge=1, le=50)
    min_score: int = Field(default=25, ge=0, le=100)


class ScanRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: int
    status: str
    search_window_hours: int
    posts_scanned: int
    opportunities_found: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class OpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    scan_run_id: str | None
    reddit_post_id: str
    subreddit_name: str
    author: str
    title: str
    permalink: str
    body_excerpt: str | None
    score: int
    status: str
    score_reasons: list[str]
    keyword_hits: list[str]
    rule_risk: list[str]
    created_at: datetime
    updated_at: datetime
    posted_at: datetime | None


class OpportunityStatusRequest(BaseModel):
    status: str = Field(pattern="^(new|saved|drafting|posted|ignored|rejected)$")
