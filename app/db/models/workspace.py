from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import MembershipRole, SubscriptionStatus
from app.utils.datetime import invitation_expiry, utc_now

if TYPE_CHECKING:
    from app.db.models.content import PromptTemplate
    from app.db.models.discovery import (
        DiscoveryKeyword,
        MonitoredSubreddit,
        Opportunity,
        ScanRun,
    )
    from app.db.models.integrations import IntegrationSecret, RedditAccount, WebhookEndpoint
    from app.db.models.user import AccountUser


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    owner: Mapped["AccountUser"] = relationship(back_populates="workspaces_owned")  # noqa: F821
    memberships: Mapped[list["Membership"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")  # noqa: F821
    invitations: Mapped[list["Invitation"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    subscription: Mapped["Subscription | None"] = relationship(back_populates="workspace", uselist=False)
    webhooks: Mapped[list["WebhookEndpoint"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")  # noqa: F821
    secrets: Mapped[list["IntegrationSecret"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")  # noqa: F821
    reddit_accounts: Mapped[list["RedditAccount"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")  # noqa: F821


class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), index=True)
    role: Mapped[MembershipRole] = mapped_column(SAEnum(MembershipRole), default=MembershipRole.MEMBER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    workspace: Mapped["Workspace"] = relationship(back_populates="memberships")
    user: Mapped["AccountUser"] = relationship(back_populates="memberships")  # noqa: F821

    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),)


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[MembershipRole] = mapped_column(SAEnum(MembershipRole), default=MembershipRole.MEMBER)
    token: Mapped[str] = mapped_column(String(255), unique=True, default=lambda: secrets.token_urlsafe(24))
    invited_by_user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=invitation_expiry)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    workspace: Mapped["Workspace"] = relationship(back_populates="invitations")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True, index=True)
    plan_code: Mapped[str] = mapped_column(String(50), default="free")
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(SubscriptionStatus), default=SubscriptionStatus.TRIALING
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    workspace: Mapped["Workspace"] = relationship(back_populates="subscription")


class PlanEntitlement(Base):
    __tablename__ = "plan_entitlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_code: Mapped[str] = mapped_column(String(50), index=True)
    feature_key: Mapped[str] = mapped_column(String(100), index=True)
    limit_value: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (UniqueConstraint("plan_code", "feature_key", name="uq_plan_feature"),)


class Redemption(Base):
    __tablename__ = "redemptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    plan_code: Mapped[str] = mapped_column(String(50))
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True)
    redeemed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("account_users.id", ondelete="SET NULL"), nullable=True
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
