import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    CrawlRun,
    CrawlStatus,
    Interaction,
    InteractionType,
    ProfileKeywordMap,
    TargetKeyword,
    TargetProfile,
    User,
)
from app.schemas.persona import KeywordSeed
from app.schemas.scraping import ScrapeRequest, ScrapeRunResponse, ScrapedProfileSummary
from app.services.instagram_client import (
    InstagramClientProtocol,
    InstagramCommentLite,
    InstagramMediaLite,
    InstagramUserLite,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScraperEngine:
    def __init__(self, db: Session, instagram_client: InstagramClientProtocol):
        self.db = db
        self.instagram_client = instagram_client
        self._profile_cache: dict[int, TargetProfile] = {}
        self._user_cache: dict[int, User] = {}
        self._keyword_cache: dict[tuple[str, str, str], TargetKeyword] = {}

    def run(self, payload: ScrapeRequest) -> ScrapeRunResponse:
        crawl = CrawlRun(
            status=CrawlStatus.RUNNING,
            business_input=payload.discovery_seed.business_description,
            target_profiles_goal=payload.max_target_profiles,
            started_at=utc_now(),
        )
        self.db.add(crawl)
        self.db.commit()
        self.db.refresh(crawl)

        profiles_discovered = 0
        interactions_collected = 0
        sample_profiles: list[ScrapedProfileSummary] = []

        try:
            self.instagram_client.login()
            sorted_keywords = sorted(payload.discovery_seed.keywords, key=lambda x: x.priority_score, reverse=True)
            for keyword_seed in sorted_keywords:
                if profiles_discovered >= payload.max_target_profiles:
                    break

                candidates = self.instagram_client.search_profiles(
                    keyword=keyword_seed.keyword,
                    amount=payload.per_keyword_cap,
                )
                for candidate in candidates:
                    if profiles_discovered >= payload.max_target_profiles:
                        break

                    if candidate.instagram_user_id <= 0 or not candidate.username:
                        continue

                    min_required = max(payload.min_followers, keyword_seed.min_followers)
                    if candidate.follower_count < min_required:
                        continue

                    target_profile, is_new = self._upsert_target_profile(candidate)
                    keyword_ref = self._get_or_create_keyword(
                        business_input=payload.discovery_seed.business_description,
                        keyword_seed=keyword_seed,
                    )
                    self._link_profile_keyword(target_profile.id, keyword_ref.id)

                    if is_new:
                        profiles_discovered += 1
                        if len(sample_profiles) < 15:
                            sample_profiles.append(
                                ScrapedProfileSummary(
                                    username=target_profile.username,
                                    followers_count=target_profile.followers_count,
                                    keyword=keyword_seed.keyword,
                                )
                            )

                    interactions_collected += self._extract_interactions(target_profile, payload)
                    target_profile.last_scraped_at = utc_now()
                    self.db.commit()

            crawl.status = CrawlStatus.COMPLETED
            crawl.profiles_discovered = profiles_discovered
            crawl.interactions_collected = interactions_collected
            crawl.finished_at = utc_now()
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            crawl.status = CrawlStatus.FAILED
            crawl.error_message = str(exc)
            crawl.finished_at = utc_now()
            self.db.add(crawl)
            self.db.commit()

        return ScrapeRunResponse(
            run_id=crawl.id,
            status=crawl.status.value,
            profiles_discovered=crawl.profiles_discovered,
            interactions_collected=crawl.interactions_collected,
            started_at=crawl.started_at,
            finished_at=crawl.finished_at,
            sample_profiles=sample_profiles,
        )

    def _extract_interactions(self, target_profile: TargetProfile, payload: ScrapeRequest) -> int:
        total = 0
        user_id = target_profile.instagram_user_id

        followers: list[InstagramUserLite] = []
        try:
            followers = self.instagram_client.get_followers(user_id, payload.follower_extract_cap)
        except Exception:
            followers = []
        for follower in followers:
            if follower.instagram_user_id <= 0 or not follower.username:
                continue
            user = self._upsert_user(follower)
            total += self._record_interaction(
                target_profile_id=target_profile.id,
                user_id=user.id,
                interaction_type=InteractionType.FOLLOWER,
                media_id=None,
                comment_text=None,
                interacted_at=None,
            )

        following: list[InstagramUserLite] = []
        try:
            following = self.instagram_client.get_following(user_id, payload.following_extract_cap)
        except Exception:
            following = []
        for followed_account in following:
            if followed_account.instagram_user_id <= 0 or not followed_account.username:
                continue
            user = self._upsert_user(followed_account)
            total += self._record_interaction(
                target_profile_id=target_profile.id,
                user_id=user.id,
                interaction_type=InteractionType.FOLLOWING,
                media_id=None,
                comment_text=None,
                interacted_at=None,
            )

        medias: list[InstagramMediaLite] = []
        try:
            medias = self.instagram_client.get_recent_media(user_id, payload.recent_posts_limit)
        except Exception:
            medias = []
        for media in medias:
            try:
                total += self._extract_media_interactions(target_profile, media, payload)
            except Exception:
                # Skip problematic media objects and continue crawl progress.
                continue

        return total

    def _extract_media_interactions(
        self,
        target_profile: TargetProfile,
        media: InstagramMediaLite,
        payload: ScrapeRequest,
    ) -> int:
        total = 0

        likers = self.instagram_client.get_media_likers(media.media_id, payload.likers_per_post_cap)
        for liker in likers:
            if liker.instagram_user_id <= 0 or not liker.username:
                continue
            user = self._upsert_user(liker)
            total += self._record_interaction(
                target_profile_id=target_profile.id,
                user_id=user.id,
                interaction_type=InteractionType.LIKE,
                media_id=media.media_id,
                comment_text=None,
                interacted_at=media.taken_at,
            )

        comments = self.instagram_client.get_media_comments(media.media_id, payload.commenters_per_post_cap)
        for comment in comments:
            total += self._record_comment_interaction(target_profile, media, comment)
        return total

    def _record_comment_interaction(
        self,
        target_profile: TargetProfile,
        media: InstagramMediaLite,
        comment: InstagramCommentLite,
    ) -> int:
        if comment.user.instagram_user_id <= 0 or not comment.user.username:
            return 0
        user = self._upsert_user(comment.user)
        return self._record_interaction(
            target_profile_id=target_profile.id,
            user_id=user.id,
            interaction_type=InteractionType.COMMENT,
            media_id=media.media_id,
            comment_text=comment.text,
            interacted_at=comment.created_at,
        )

    def _upsert_target_profile(self, profile: InstagramUserLite) -> tuple[TargetProfile, bool]:
        if profile.instagram_user_id in self._profile_cache:
            existing = self._profile_cache[profile.instagram_user_id]
            self._apply_profile_updates(existing, profile)
            return existing, False

        existing = self.db.scalar(
            select(TargetProfile).where(TargetProfile.instagram_user_id == profile.instagram_user_id)
        )
        if existing:
            self._apply_profile_updates(existing, profile)
            self._profile_cache[profile.instagram_user_id] = existing
            return existing, False

        created = TargetProfile(
            instagram_user_id=profile.instagram_user_id,
            username=profile.username,
            full_name=profile.full_name,
            bio=profile.biography,
            followers_count=profile.follower_count,
            following_count=profile.following_count,
            is_private=profile.is_private,
            is_verified=profile.is_verified,
            discovered_at=utc_now(),
            last_scraped_at=None,
        )
        self.db.add(created)
        self.db.flush()
        self._profile_cache[profile.instagram_user_id] = created
        return created, True

    def _apply_profile_updates(self, existing: TargetProfile, incoming: InstagramUserLite) -> None:
        existing.username = incoming.username or existing.username
        existing.full_name = incoming.full_name or existing.full_name
        existing.bio = incoming.biography or existing.bio
        existing.followers_count = max(existing.followers_count, incoming.follower_count)
        existing.following_count = max(existing.following_count, incoming.following_count)
        existing.is_private = incoming.is_private
        existing.is_verified = incoming.is_verified

    def _upsert_user(self, incoming: InstagramUserLite) -> User:
        if incoming.instagram_user_id in self._user_cache:
            existing = self._user_cache[incoming.instagram_user_id]
            self._apply_user_updates(existing, incoming)
            return existing

        existing = self.db.scalar(select(User).where(User.instagram_user_id == incoming.instagram_user_id))
        if existing:
            self._apply_user_updates(existing, incoming)
            self._user_cache[incoming.instagram_user_id] = existing
            return existing

        created = User(
            instagram_user_id=incoming.instagram_user_id,
            username=incoming.username,
            full_name=incoming.full_name,
            is_private=incoming.is_private,
            is_verified=incoming.is_verified,
            follower_count=incoming.follower_count,
            following_count=incoming.following_count,
            profile_pic_url=incoming.profile_pic_url,
        )
        self.db.add(created)
        self.db.flush()
        self._user_cache[incoming.instagram_user_id] = created
        return created

    def _apply_user_updates(self, existing: User, incoming: InstagramUserLite) -> None:
        existing.username = incoming.username or existing.username
        existing.full_name = incoming.full_name or existing.full_name
        existing.is_private = incoming.is_private
        existing.is_verified = incoming.is_verified
        existing.follower_count = max(existing.follower_count, incoming.follower_count)
        existing.following_count = max(existing.following_count, incoming.following_count)
        existing.profile_pic_url = incoming.profile_pic_url or existing.profile_pic_url

    def _get_or_create_keyword(self, business_input: str, keyword_seed: KeywordSeed) -> TargetKeyword:
        cache_key = (business_input, keyword_seed.keyword, keyword_seed.profile_type)
        if cache_key in self._keyword_cache:
            return self._keyword_cache[cache_key]

        existing = self.db.scalar(
            select(TargetKeyword).where(
                TargetKeyword.business_input == business_input,
                TargetKeyword.keyword == keyword_seed.keyword,
                TargetKeyword.profile_type == keyword_seed.profile_type,
            )
        )
        if existing:
            existing.priority_score = keyword_seed.priority_score
            self._keyword_cache[cache_key] = existing
            return existing

        created = TargetKeyword(
            business_input=business_input,
            keyword=keyword_seed.keyword,
            profile_type=keyword_seed.profile_type,
            overlap_reason="Generated by persona engine.",
            priority_score=keyword_seed.priority_score,
        )
        self.db.add(created)
        self.db.flush()
        self._keyword_cache[cache_key] = created
        return created

    def _link_profile_keyword(self, profile_id: int, keyword_id: int) -> None:
        exists = self.db.scalar(
            select(ProfileKeywordMap.id).where(
                ProfileKeywordMap.profile_id == profile_id,
                ProfileKeywordMap.keyword_id == keyword_id,
            )
        )
        if exists:
            return
        self.db.add(ProfileKeywordMap(profile_id=profile_id, keyword_id=keyword_id))
        self.db.flush()

    def _record_interaction(
        self,
        target_profile_id: int,
        user_id: int,
        interaction_type: InteractionType,
        media_id: int | None,
        comment_text: str | None,
        interacted_at: datetime | None,
    ) -> int:
        event_key = self._event_key(
            target_profile_id=target_profile_id,
            user_id=user_id,
            interaction_type=interaction_type,
            media_id=media_id,
            comment_text=comment_text,
            interacted_at=interacted_at,
        )
        exists = self.db.scalar(select(Interaction.id).where(Interaction.event_key == event_key))
        if exists:
            return 0

        self.db.add(
            Interaction(
                event_key=event_key,
                target_profile_id=target_profile_id,
                user_id=user_id,
                interaction_type=interaction_type,
                media_id=media_id,
                comment_text=comment_text,
                interacted_at=interacted_at,
                scraped_at=utc_now(),
            )
        )
        self.db.flush()
        return 1

    def _event_key(
        self,
        target_profile_id: int,
        user_id: int,
        interaction_type: InteractionType,
        media_id: int | None,
        comment_text: str | None,
        interacted_at: datetime | None,
    ) -> str:
        if interaction_type in (InteractionType.FOLLOWER, InteractionType.FOLLOWING):
            return f"{interaction_type.value}:{target_profile_id}:{user_id}"
        if interaction_type == InteractionType.LIKE:
            return f"{interaction_type.value}:{target_profile_id}:{user_id}:{media_id or 0}"

        timestamp = int(interacted_at.timestamp()) if interacted_at else 0
        text_hash = hashlib.sha1((comment_text or "").encode("utf-8")).hexdigest()[:10]
        return f"{interaction_type.value}:{target_profile_id}:{user_id}:{media_id or 0}:{timestamp}:{text_hash}"
