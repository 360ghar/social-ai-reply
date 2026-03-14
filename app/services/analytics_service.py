from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.db.models import Interaction, InteractionType, User
from app.schemas.analytics import HandleMetric, QueryResponse


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def super_fans(self, min_profiles: int = 15, limit: int = 200) -> QueryResponse:
        stmt = (
            select(
                User.instagram_user_id,
                User.username,
                func.count(distinct(Interaction.target_profile_id)).label("distinct_profiles"),
            )
            .join(Interaction, Interaction.user_id == User.id)
            .where(Interaction.interaction_type == InteractionType.FOLLOWER)
            .group_by(User.id, User.instagram_user_id, User.username)
            .having(func.count(distinct(Interaction.target_profile_id)) >= min_profiles)
            .order_by(func.count(distinct(Interaction.target_profile_id)).desc())
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        results = [
            HandleMetric(
                instagram_user_id=row.instagram_user_id,
                username=row.username,
                metric_count=int(row.distinct_profiles),
                distinct_profiles=int(row.distinct_profiles),
            )
            for row in rows
        ]
        return QueryResponse(query_name="super_fans", threshold=min_profiles, results=results)

    def top_commenters(self, min_comments: int = 3, limit: int = 200) -> QueryResponse:
        stmt = (
            select(
                User.instagram_user_id,
                User.username,
                func.count(Interaction.id).label("metric_count"),
                func.count(distinct(Interaction.target_profile_id)).label("distinct_profiles"),
            )
            .join(Interaction, Interaction.user_id == User.id)
            .where(Interaction.interaction_type == InteractionType.COMMENT)
            .group_by(User.id, User.instagram_user_id, User.username)
            .having(func.count(Interaction.id) >= min_comments)
            .order_by(func.count(Interaction.id).desc())
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        results = [
            HandleMetric(
                instagram_user_id=row.instagram_user_id,
                username=row.username,
                metric_count=int(row.metric_count),
                distinct_profiles=int(row.distinct_profiles),
            )
            for row in rows
        ]
        return QueryResponse(query_name="top_commenters", threshold=min_comments, results=results)

    def frequent_likers(self, min_likes: int = 5, limit: int = 200) -> QueryResponse:
        stmt = (
            select(
                User.instagram_user_id,
                User.username,
                func.count(Interaction.id).label("metric_count"),
                func.count(distinct(Interaction.target_profile_id)).label("distinct_profiles"),
            )
            .join(Interaction, Interaction.user_id == User.id)
            .where(Interaction.interaction_type == InteractionType.LIKE)
            .group_by(User.id, User.instagram_user_id, User.username)
            .having(func.count(Interaction.id) >= min_likes)
            .order_by(func.count(Interaction.id).desc())
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        results = [
            HandleMetric(
                instagram_user_id=row.instagram_user_id,
                username=row.username,
                metric_count=int(row.metric_count),
                distinct_profiles=int(row.distinct_profiles),
            )
            for row in rows
        ]
        return QueryResponse(query_name="frequent_likers", threshold=min_likes, results=results)
