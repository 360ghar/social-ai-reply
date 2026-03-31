from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.datetime import utc_now

if TYPE_CHECKING:
    from app.db.models.workspace import Workspace


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    target_url: Mapped[str] = mapped_column(String(1024))
    signing_secret: Mapped[str] = mapped_column(String(128), default=lambda: secrets.token_urlsafe(24))
    event_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    workspace: Mapped["Workspace"] = relationship(back_populates="webhooks")  # noqa: F821


class IntegrationSecret(Base):
    __tablename__ = "integration_secrets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(100))
    label: Mapped[str] = mapped_column(String(100))
    encrypted_payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    workspace: Mapped["Workspace"] = relationship(back_populates="secrets")  # noqa: F821

    __table_args__ = (UniqueConstraint("workspace_id", "provider", "label", name="uq_workspace_secret"),)


class RedditAccount(Base):
    """Connected Reddit account for posting"""

    __tablename__ = "reddit_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    username: Mapped[str] = mapped_column(String(255))
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    karma: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    workspace: Mapped["Workspace"] = relationship(back_populates="reddit_accounts")  # noqa: F821
    published_posts: Mapped[list["PublishedPost"]] = relationship(  # noqa: F821
        back_populates="reddit_account", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("workspace_id", "username", name="uq_workspace_reddit_username"),)
