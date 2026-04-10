"""Pydantic models for user-related tables."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AccountUser(BaseModel):
    """Model for account_users table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    supabase_user_id: str = Field(min_length=1)
    email: EmailStr
    full_name: str | None = None
    avatar_url: str | None = None
    created_at: datetime
    updated_at: datetime
