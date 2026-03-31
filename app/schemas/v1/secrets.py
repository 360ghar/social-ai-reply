from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
