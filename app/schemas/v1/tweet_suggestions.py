from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class SuggestionGenerateRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=31, description="Number of days to generate suggestions for")
    suggestions_per_day: int = Field(default=1, ge=1, le=5, description="Suggestions per day")
    platform: str = Field(default="twitter", pattern="^(twitter|x|linkedin|instagram)$")


class SuggestionGenerateResponse(BaseModel):
    generated_count: int
    suggestions: list["TweetSuggestionResponse"]


class TweetSuggestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    content: str
    suggested_for_date: date
    status: str
    platform: str
    scheduled_at: str | None = None
    published_at: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str


class SuggestionApproveRequest(BaseModel):
    scheduled_at: datetime | None = Field(
        default=None,
        description="Override scheduling time. Defaults to suggested_for_date at 09:00 UTC.",
    )


class SuggestionRejectRequest(BaseModel):
    pass


class SuggestionListQuery(BaseModel):
    status: str | None = Field(default=None, pattern="^(pending|approved|publishing|rejected|published)$")
    platform: str | None = Field(default=None, pattern="^(twitter|x|linkedin|instagram)$")
    from_date: date | None = None
    to_date: date | None = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
