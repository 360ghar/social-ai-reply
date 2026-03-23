from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)


class ProjectUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    status: str = Field(default="active", pattern="^(active|archived)$")


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    name: str
    slug: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class BrandProfileRequest(BaseModel):
    brand_name: str = Field(min_length=2, max_length=255)
    website_url: HttpUrl | None = None
    summary: str | None = Field(default=None, max_length=4000)
    voice_notes: str | None = Field(default=None, max_length=4000)
    product_summary: str | None = Field(default=None, max_length=4000)
    target_audience: str | None = Field(default=None, max_length=4000)
    call_to_action: str | None = Field(default=None, max_length=4000)
    reddit_username: str | None = Field(default=None, max_length=255)
    linkedin_url: HttpUrl | None = None


class BrandAnalysisRequest(BaseModel):
    website_url: HttpUrl


class BrandProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    brand_name: str
    website_url: str | None
    summary: str | None
    voice_notes: str | None
    product_summary: str | None
    target_audience: str | None
    call_to_action: str | None
    reddit_username: str | None
    linkedin_url: str | None
    last_analyzed_at: datetime | None


class PersonaRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    role: str | None = Field(default=None, max_length=255)
    summary: str = Field(min_length=10, max_length=4000)
    pain_points: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)
    preferred_subreddits: list[str] = Field(default_factory=list)
    source: str = "manual"
    is_active: bool = True


class PersonaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    role: str | None
    summary: str
    pain_points: list[str]
    goals: list[str]
    triggers: list[str]
    preferred_subreddits: list[str]
    source: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


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
    finished_at: datetime | None
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
    status: str = Field(pattern="^(new|saved|drafting|posted|ignored)$")


class ReplyDraftRequest(BaseModel):
    opportunity_id: int


class ReplyDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    opportunity_id: int
    content: str
    rationale: str | None
    source_prompt: str | None
    version: int
    created_at: datetime


class PostDraftRequest(BaseModel):
    project_id: int


class PostDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    body: str
    rationale: str | None
    source_prompt: str | None
    version: int
    created_at: datetime


class PromptTemplateRequest(BaseModel):
    prompt_type: str = Field(pattern="^(reply|post|analysis)$")
    name: str = Field(min_length=2, max_length=255)
    system_prompt: str = Field(min_length=10, max_length=8000)
    instructions: str = Field(default="", max_length=8000)
    is_default: bool = False


class PromptTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    prompt_type: str
    name: str
    system_prompt: str
    instructions: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


class WebhookRequest(BaseModel):
    target_url: HttpUrl
    event_types: list[str] = Field(default_factory=lambda: ["opportunity.found"])
    is_active: bool = True


class WebhookUpdateRequest(BaseModel):
    is_active: bool


class WebhookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    target_url: str
    event_types: list[str]
    is_active: bool
    last_tested_at: datetime | None
    created_at: datetime


class WebhookTestRequest(BaseModel):
    event_type: str = "opportunity.found"


class SecretRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=100)
    label: str = Field(min_length=2, max_length=100)
    value: str = Field(min_length=4, max_length=8000)


class SecretResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    provider: str
    label: str
    created_at: datetime
    updated_at: datetime


class InvitationRequest(BaseModel):
    email: EmailStr
    role: str = Field(pattern="^(owner|admin|member)$")


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: int
    email: str
    role: str
    token: str
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime


class SubscriptionResponse(BaseModel):
    plan_code: str
    status: str
    current_period_end: datetime | None
    features: list[str]
    limits: dict[str, int]


class PlanResponse(BaseModel):
    code: str
    name: str
    price_monthly: int
    features: list[str]
    limits: dict[str, int]


class BillingUpgradeRequest(BaseModel):
    plan_code: str = Field(min_length=2, max_length=50)


class RedemptionRequest(BaseModel):
    code: str = Field(min_length=4, max_length=100)


class RedemptionResponse(BaseModel):
    success: bool
    plan_code: str
    message: str


class SetupStatus(BaseModel):
    brand_configured: bool = False
    personas_count: int = 0
    subreddits_count: int = 0

class DashboardResponse(BaseModel):
    projects: list[ProjectResponse]
    top_opportunities: list[OpportunityResponse]
    subscription: SubscriptionResponse
    setup_status: SetupStatus = SetupStatus()
