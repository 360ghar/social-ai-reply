"""Pydantic models for workspace-related tables."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class WorkspaceStatus(StrEnum):
    """Status values for workspace."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class MembershipRole(StrEnum):
    """Role values for membership."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Workspace(BaseModel):
    """Model for workspaces table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str = Field(min_length=1, max_length=255)
    slug: str
    status: WorkspaceStatus
    created_at: datetime
    updated_at: datetime


class Membership(BaseModel):
    """Model for memberships table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    user_id: int
    role: MembershipRole
    created_at: datetime
    updated_at: datetime


class Invitation(BaseModel):
    """Model for invitations table."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: int
    email: EmailStr
    role: MembershipRole
    token: str
    expires_at: datetime
    created_at: datetime
    updated_at: datetime


class Subscription(BaseModel):
    """Model for subscriptions table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    plan_code: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    created_at: datetime
    updated_at: datetime


class PlanEntitlement(BaseModel):
    """Model for plan_entitlements table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_code: str
    feature_key: str
    value: str
    created_at: datetime


class Redemption(BaseModel):
    """Model for redemptions table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    plan_code: str
    redeemed_by_user_id: int | None = None
    redeemed_at: datetime | None = None
    created_at: datetime
