from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.datetime import utc_now

if TYPE_CHECKING:
    from app.db.models.integrations import RedditAccount
    from app.db.models.project import Project


class Campaign(Base):
    """Group related engagement tasks into campaigns"""

    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project: Mapped["Project"] = relationship(back_populates="campaigns")  # noqa: F821
    published_posts: Mapped[list["PublishedPost"]] = relationship(  # noqa: F821
        back_populates="campaign", cascade="all, delete-orphan"
    )


class PublishedPost(Base):
    """Track posts/comments published to Reddit"""

    __tablename__ = "published_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[str | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reddit_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("reddit_accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(String(50))
    reddit_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subreddit: Mapped[str] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    permalink: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    parent_post_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="published")
    upvotes: Mapped[int] = mapped_column(Integer, default=0)
    comment_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    removal_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reply_draft_id: Mapped[int | None] = mapped_column(
        ForeignKey("reply_drafts.id", ondelete="SET NULL"), nullable=True
    )
    post_draft_id: Mapped[int | None] = mapped_column(
        ForeignKey("post_drafts.id", ondelete="SET NULL"), nullable=True
    )

    project: Mapped["Project"] = relationship(back_populates="published_posts")  # noqa: F821
    campaign: Mapped["Campaign | None"] = relationship(back_populates="published_posts")
    reddit_account: Mapped["RedditAccount | None"] = relationship(back_populates="published_posts")  # noqa: F821
