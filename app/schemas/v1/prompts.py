from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
