from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
