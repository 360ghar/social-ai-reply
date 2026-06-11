"""Voice profile request/response schemas."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

ExampleReply = Annotated[str, Field(max_length=2000)]


class VoiceProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    example_replies: list[str] = Field(default_factory=list)
    tone_descriptors: list[str] = Field(default_factory=list)
    banned_phrases: list[str] = Field(default_factory=list)
    style_guide: str | None = None
    is_default: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class VoiceProfileCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    example_replies: list[ExampleReply] = Field(default_factory=list, max_length=5)
    tone_descriptors: list[str] = Field(default_factory=list)
    banned_phrases: list[str] = Field(default_factory=list)
    style_guide: str | None = Field(default=None, max_length=8000)
    is_default: bool = False


class VoiceProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    example_replies: list[ExampleReply] | None = Field(default=None, max_length=5)
    tone_descriptors: list[str] | None = None
    banned_phrases: list[str] | None = None
    style_guide: str | None = Field(default=None, max_length=8000)
    is_default: bool | None = None
