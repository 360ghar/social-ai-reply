"""Request/response schemas for tracked links and ROI attribution."""

from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TrackedLinkCreateRequest(BaseModel):
    project_id: int = Field(ge=1)
    destination_url: str = Field(min_length=1, max_length=2048)
    opportunity_id: int | None = Field(default=None, ge=1)
    reply_draft_id: int | None = Field(default=None, ge=1)

    @field_validator("destination_url")
    @classmethod
    def validate_destination_url(cls, value: str) -> str:
        value = value.strip()
        parts = urlsplit(value)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise ValueError("destination_url must be a valid http(s) URL.")
        return value


class TrackedLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    code: str
    destination_url: str
    opportunity_id: int | None = None
    reply_draft_id: int | None = None
    utm_params: dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    short_path: str
    tracked_url: str
    click_count: int = 0


class RoiRollupRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    group_by: str
    key: str
    links: int = 0
    clicks: int = 0


class RoiRollupResponse(BaseModel):
    project_id: int
    rows: list[RoiRollupRow] = Field(default_factory=list)
