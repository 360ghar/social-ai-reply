from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip_nonempty(value: str, field_name: str, min_len: int = 2) -> str:
    value = value.strip()
    if len(value) < min_len:
        raise ValueError(f"{field_name} must be at least {min_len} characters after trimming whitespace.")
    return value


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class WorkspaceUpdateRequest(BaseModel):
    """Partial workspace update request. All fields optional."""

    name: str | None = Field(default=None, min_length=2, max_length=255)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v):
        if v is None:
            return None
        return _strip_nonempty(v, "workspace name")


class UserProfileUpdateRequest(BaseModel):
    """Partial user profile update. Email changes go through Supabase Auth separately."""

    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    notification_preferences: dict[str, bool] | None = None

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_full_name(cls, v):
        if v is None:
            return None
        return _strip_nonempty(v, "full_name")


class NotificationPreferences(BaseModel):
    email_notifications: bool = True
    digest_email: bool = False
    slack_notifications: bool = False


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    is_active: bool
    notification_preferences: NotificationPreferences = Field(default_factory=NotificationPreferences)
    created_at: datetime | None = None
