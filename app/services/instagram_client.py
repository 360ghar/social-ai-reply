import random
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from app.services.proxy_pool import ProxyPool
from app.services.rate_limiter import AccountRateLimiter


@dataclass
class InstagramUserLite:
    instagram_user_id: int
    username: str
    full_name: str | None = None
    biography: str | None = None
    follower_count: int = 0
    following_count: int = 0
    is_private: bool = False
    is_verified: bool = False
    profile_pic_url: str | None = None


@dataclass
class InstagramMediaLite:
    media_id: int
    taken_at: datetime | None = None


@dataclass
class InstagramCommentLite:
    user: InstagramUserLite
    text: str | None
    created_at: datetime | None


class InstagramClientProtocol(Protocol):
    def login(self) -> None:
        pass

    def search_profiles(self, keyword: str, amount: int) -> list[InstagramUserLite]:
        pass

    def get_followers(self, user_id: int, amount: int) -> list[InstagramUserLite]:
        pass

    def get_following(self, user_id: int, amount: int) -> list[InstagramUserLite]:
        pass

    def get_recent_media(self, user_id: int, amount: int) -> list[InstagramMediaLite]:
        pass

    def get_media_likers(self, media_id: int, amount: int) -> list[InstagramUserLite]:
        pass

    def get_media_comments(self, media_id: int, amount: int) -> list[InstagramCommentLite]:
        pass


class NoopInstagramClient:
    def login(self) -> None:
        return

    def search_profiles(self, keyword: str, amount: int) -> list[InstagramUserLite]:
        return []

    def get_followers(self, user_id: int, amount: int) -> list[InstagramUserLite]:
        return []

    def get_following(self, user_id: int, amount: int) -> list[InstagramUserLite]:
        return []

    def get_recent_media(self, user_id: int, amount: int) -> list[InstagramMediaLite]:
        return []

    def get_media_likers(self, media_id: int, amount: int) -> list[InstagramUserLite]:
        return []

    def get_media_comments(self, media_id: int, amount: int) -> list[InstagramCommentLite]:
        return []


class InstagrapiClientAdapter:
    def __init__(
        self,
        username: str,
        password: str,
        session_dir: str,
        rate_limiter: AccountRateLimiter,
        proxy_pool: ProxyPool,
        challenge_code: str | None = None,
    ) -> None:
        from instagrapi import Client

        self._username = username
        self._password = password
        self._rate_limiter = rate_limiter
        self._proxy_pool = proxy_pool
        self._challenge_code = challenge_code
        self._session_file = Path(session_dir) / f"{username}.json"
        self._session_file.parent.mkdir(parents=True, exist_ok=True)
        self._client = Client()
        self._client.challenge_code_handler = self._challenge_code_handler
        self._logged_in = False

    def set_challenge_code(self, challenge_code: str | None) -> None:
        self._challenge_code = challenge_code

    def mark_logged_out(self) -> None:
        self._logged_in = False

    def login(self) -> None:
        if self._logged_in:
            return

        self._apply_next_proxy()
        if self._session_file.exists() and self._try_resume_session():
            self._logged_in = True
            return

        self._fresh_login()
        self._logged_in = True

    def _try_resume_session(self) -> bool:
        try:
            self._client.load_settings(str(self._session_file))
            # Validate cookie/session state without forcing full re-auth.
            self._client.get_timeline_feed()
            self._client.dump_settings(str(self._session_file))
            return True
        except Exception:
            return False

    def _fresh_login(self) -> None:
        try:
            self._client.login(self._username, self._password)
            self._client.dump_settings(str(self._session_file))
        except Exception:
            # Retry once with a clean client instance.
            self._client = self._client.__class__()
            self._client.challenge_code_handler = self._challenge_code_handler
            self._apply_next_proxy()
            self._client.login(self._username, self._password)
            self._client.dump_settings(str(self._session_file))

    def search_profiles(self, keyword: str, amount: int) -> list[InstagramUserLite]:
        raw = self._with_retries(self._client.search_users, keyword) or []
        users: list[InstagramUserLite] = []
        for user_short in raw:
            mapped = self._map_user(user_short)
            if mapped.instagram_user_id <= 0 or not mapped.username:
                continue
            if mapped.follower_count == 0 and mapped.instagram_user_id > 0:
                try:
                    info = self._with_retries(self._client.user_info, mapped.instagram_user_id)
                    mapped = self._map_user(info)
                except Exception:
                    pass
            users.append(mapped)
            if len(users) >= amount:
                break
        return users

    def get_followers(self, user_id: int, amount: int) -> list[InstagramUserLite]:
        raw = self._with_retries(self._client.user_followers, user_id, amount=amount) or {}
        values = raw.values() if isinstance(raw, dict) else raw
        users = [self._map_user(item) for item in values]
        return users[:amount]

    def get_following(self, user_id: int, amount: int) -> list[InstagramUserLite]:
        raw = self._with_retries(self._client.user_following, user_id, amount=amount) or {}
        values = raw.values() if isinstance(raw, dict) else raw
        users = [self._map_user(item) for item in values]
        return users[:amount]

    def get_recent_media(self, user_id: int, amount: int) -> list[InstagramMediaLite]:
        raw = self._with_retries(self._client.user_medias, user_id, amount) or []
        medias: list[InstagramMediaLite] = []
        for media in raw:
            media_id = self._to_int(getattr(media, "pk", None))
            if media_id <= 0:
                media_id = self._extract_media_pk(getattr(media, "id", None))
            if media_id <= 0:
                continue
            medias.append(
                InstagramMediaLite(
                    media_id=media_id,
                    taken_at=getattr(media, "taken_at", None),
                )
            )
        return medias

    def get_media_likers(self, media_id: int, amount: int) -> list[InstagramUserLite]:
        raw = self._with_retries(self._client.media_likers, media_id) or []
        return [self._map_user(item) for item in raw][:amount]

    def get_media_comments(self, media_id: int, amount: int) -> list[InstagramCommentLite]:
        raw = self._with_retries(self._client.media_comments, media_id, amount=amount) or []
        comments: list[InstagramCommentLite] = []
        for comment in raw[:amount]:
            mapped_user = self._map_user(getattr(comment, "user", None))
            comments.append(
                InstagramCommentLite(
                    user=mapped_user,
                    text=getattr(comment, "text", None),
                    created_at=getattr(comment, "created_at_utc", None) or getattr(comment, "created_at", None),
                )
            )
        return comments

    def _with_retries(self, fn, *args, **kwargs):
        last_exc: Exception | None = None
        for attempt in range(3):
            self._rate_limiter.wait_for_slot()
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                message = str(exc).lower()
                if "login_required" in message:
                    self.mark_logged_out()
                    try:
                        self.login()
                        continue
                    except Exception:
                        pass
                self._apply_next_proxy()
                backoff = min(15, 2 ** attempt + random.uniform(0.5, 1.8))
                time.sleep(backoff)
        if last_exc:
            raise RuntimeError(str(last_exc)) from last_exc
        return None

    def _apply_next_proxy(self) -> None:
        proxy = self._proxy_pool.next_proxy()
        if proxy:
            try:
                self._client.set_proxy(proxy)
            except Exception:
                pass

    def _challenge_code_handler(self, username: str, choice) -> str:
        if self._challenge_code:
            return str(self._challenge_code).strip()
        raise RuntimeError(
            "Instagram challenge code required for login. "
            "Set INSTAGRAM_CHALLENGE_CODE in .env or provide challenge_code in scrape request."
        )

    def _extract_media_pk(self, raw_id) -> int:
        if raw_id is None:
            return 0
        raw = str(raw_id).strip()
        if not raw:
            return 0
        if "_" in raw:
            raw = raw.split("_", 1)[0]
        return self._to_int(raw)

    def _map_user(self, source) -> InstagramUserLite:
        if source is None:
            return InstagramUserLite(instagram_user_id=0, username="")
        return InstagramUserLite(
            instagram_user_id=self._to_int(getattr(source, "pk", None) or getattr(source, "id", None)),
            username=str(getattr(source, "username", "") or ""),
            full_name=getattr(source, "full_name", None),
            biography=getattr(source, "biography", None),
            follower_count=self._to_int(getattr(source, "follower_count", 0)),
            following_count=self._to_int(getattr(source, "following_count", 0)),
            is_private=bool(getattr(source, "is_private", False)),
            is_verified=bool(getattr(source, "is_verified", False)),
            profile_pic_url=str(getattr(source, "profile_pic_url", "") or "") or None,
        )

    @staticmethod
    def _to_int(value) -> int:
        try:
            return int(value)
        except Exception:
            return 0
