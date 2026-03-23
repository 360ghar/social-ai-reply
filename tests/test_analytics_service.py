from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import Interaction, InteractionType, TargetProfile, User
from app.services.analytics_service import AnalyticsService


def setup_db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return session_local()


def seed_data(db: Session) -> None:
    p1 = TargetProfile(instagram_user_id=101, username="profile_a", followers_count=10000, following_count=500)
    p2 = TargetProfile(instagram_user_id=102, username="profile_b", followers_count=12000, following_count=700)
    p3 = TargetProfile(instagram_user_id=103, username="profile_c", followers_count=8000, following_count=300)

    u1 = User(instagram_user_id=1001, username="lead_one")
    u2 = User(instagram_user_id=1002, username="lead_two")
    u3 = User(instagram_user_id=1003, username="lead_three")
    db.add_all([p1, p2, p3, u1, u2, u3])
    db.flush()

    rows = [
        Interaction(
            event_key="follower:1:1",
            target_profile_id=p1.id,
            user_id=u1.id,
            interaction_type=InteractionType.FOLLOWER,
            scraped_at=datetime.now(timezone.utc),
        ),
        Interaction(
            event_key="follower:2:1",
            target_profile_id=p2.id,
            user_id=u1.id,
            interaction_type=InteractionType.FOLLOWER,
            scraped_at=datetime.now(timezone.utc),
        ),
        Interaction(
            event_key="follower:3:1",
            target_profile_id=p3.id,
            user_id=u1.id,
            interaction_type=InteractionType.FOLLOWER,
            scraped_at=datetime.now(timezone.utc),
        ),
        Interaction(
            event_key="follower:1:2",
            target_profile_id=p1.id,
            user_id=u2.id,
            interaction_type=InteractionType.FOLLOWER,
            scraped_at=datetime.now(timezone.utc),
        ),
        Interaction(
            event_key="like:1:2:2001",
            target_profile_id=p1.id,
            user_id=u2.id,
            interaction_type=InteractionType.LIKE,
            media_id=2001,
            scraped_at=datetime.now(timezone.utc),
        ),
        Interaction(
            event_key="like:2:2:2002",
            target_profile_id=p2.id,
            user_id=u2.id,
            interaction_type=InteractionType.LIKE,
            media_id=2002,
            scraped_at=datetime.now(timezone.utc),
        ),
        Interaction(
            event_key="like:3:2:2003",
            target_profile_id=p3.id,
            user_id=u2.id,
            interaction_type=InteractionType.LIKE,
            media_id=2003,
            scraped_at=datetime.now(timezone.utc),
        ),
        Interaction(
            event_key="like:1:2:2004",
            target_profile_id=p1.id,
            user_id=u2.id,
            interaction_type=InteractionType.LIKE,
            media_id=2004,
            scraped_at=datetime.now(timezone.utc),
        ),
        Interaction(
            event_key="like:2:2:2005",
            target_profile_id=p2.id,
            user_id=u2.id,
            interaction_type=InteractionType.LIKE,
            media_id=2005,
            scraped_at=datetime.now(timezone.utc),
        ),
        Interaction(
            event_key="comment:1:3:3001:1:abc",
            target_profile_id=p1.id,
            user_id=u3.id,
            interaction_type=InteractionType.COMMENT,
            media_id=3001,
            comment_text="Great",
            scraped_at=datetime.now(timezone.utc),
        ),
        Interaction(
            event_key="comment:2:3:3002:2:def",
            target_profile_id=p2.id,
            user_id=u3.id,
            interaction_type=InteractionType.COMMENT,
            media_id=3002,
            comment_text="Love this",
            scraped_at=datetime.now(timezone.utc),
        ),
        Interaction(
            event_key="comment:3:3:3003:3:ghi",
            target_profile_id=p3.id,
            user_id=u3.id,
            interaction_type=InteractionType.COMMENT,
            media_id=3003,
            comment_text="Helpful",
            scraped_at=datetime.now(timezone.utc),
        ),
    ]
    db.add_all(rows)
    db.commit()


def test_super_fans_query():
    db = setup_db()
    seed_data(db)
    service = AnalyticsService(db)
    response = service.super_fans(min_profiles=2, limit=10)
    assert response.results[0].username == "lead_one"
    assert response.results[0].distinct_profiles == 3


def test_top_commenters_query():
    db = setup_db()
    seed_data(db)
    service = AnalyticsService(db)
    response = service.top_commenters(min_comments=2, limit=10)
    assert response.results[0].username == "lead_three"
    assert response.results[0].metric_count == 3


def test_frequent_likers_query():
    db = setup_db()
    seed_data(db)
    service = AnalyticsService(db)
    response = service.frequent_likers(min_likes=4, limit=10)
    assert response.results[0].username == "lead_two"
    assert response.results[0].metric_count == 5
