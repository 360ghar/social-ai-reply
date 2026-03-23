import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InteractionType(str, Enum):
    FOLLOWER = "follower"
    FOLLOWING = "following"
    LIKE = "like"
    COMMENT = "comment"


class CrawlStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TargetKeyword(Base):
    __tablename__ = "target_keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    business_input: Mapped[str] = mapped_column(String(255), index=True)
    keyword: Mapped[str] = mapped_column(String(255), index=True)
    profile_type: Mapped[str] = mapped_column(String(255))
    overlap_reason: Mapped[str] = mapped_column(Text)
    priority_score: Mapped[int] = mapped_column(Integer, default=50)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    profile_links: Mapped[list["ProfileKeywordMap"]] = relationship(back_populates="keyword_ref")

    __table_args__ = (
        UniqueConstraint("business_input", "keyword", "profile_type", name="uq_keyword_business_type"),
    )


class TargetProfile(Base):
    __tablename__ = "target_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instagram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    followers_count: Mapped[int] = mapped_column(Integer, default=0)
    following_count: Mapped[int] = mapped_column(Integer, default=0)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    keyword_links: Mapped[list["ProfileKeywordMap"]] = relationship(back_populates="profile_ref")
    interactions: Mapped[list["Interaction"]] = relationship(back_populates="target_profile")


class ProfileKeywordMap(Base):
    __tablename__ = "profile_keyword_map"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("target_profiles.id", ondelete="CASCADE"), index=True)
    keyword_id: Mapped[int] = mapped_column(ForeignKey("target_keywords.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    profile_ref: Mapped["TargetProfile"] = relationship(back_populates="keyword_links")
    keyword_ref: Mapped["TargetKeyword"] = relationship(back_populates="profile_links")

    __table_args__ = (
        UniqueConstraint("profile_id", "keyword_id", name="uq_profile_keyword"),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instagram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255), index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    following_count: Mapped[int] = mapped_column(Integer, default=0)
    profile_pic_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    interactions: Mapped[list["Interaction"]] = relationship(back_populates="user")

    __table_args__ = (
        UniqueConstraint("instagram_user_id", name="uq_users_instagram_user_id"),
    )


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    target_profile_id: Mapped[int] = mapped_column(
        ForeignKey("target_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    interaction_type: Mapped[InteractionType] = mapped_column(SAEnum(InteractionType), index=True)
    media_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    comment_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    interacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    target_profile: Mapped["TargetProfile"] = relationship(back_populates="interactions")
    user: Mapped["User"] = relationship(back_populates="interactions")


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[CrawlStatus] = mapped_column(SAEnum(CrawlStatus), default=CrawlStatus.QUEUED, index=True)
    business_input: Mapped[str] = mapped_column(String(255), index=True)
    target_profiles_goal: Mapped[int] = mapped_column(Integer, default=1000)
    profiles_discovered: Mapped[int] = mapped_column(Integer, default=0)
    interactions_collected: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


Index("ix_interactions_user_target_type", Interaction.user_id, Interaction.target_profile_id, Interaction.interaction_type)
Index("ix_interactions_target_type", Interaction.target_profile_id, Interaction.interaction_type)
