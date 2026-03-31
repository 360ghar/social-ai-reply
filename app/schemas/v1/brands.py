from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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
