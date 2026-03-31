from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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
