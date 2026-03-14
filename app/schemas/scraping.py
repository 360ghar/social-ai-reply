from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.persona import DiscoverySeed


class ScrapeRequest(BaseModel):
    discovery_seed: DiscoverySeed
    challenge_code: str | None = Field(default=None, description="Optional 6-digit Instagram challenge code")
    max_target_profiles: int = Field(default=1000, ge=10, le=5000)
    min_followers: int = Field(default=1000, ge=100, le=500000)
    per_keyword_cap: int = Field(default=150, ge=10, le=500)
    follower_extract_cap: int = Field(default=300, ge=20, le=2000)
    following_extract_cap: int = Field(default=200, ge=20, le=2000)
    recent_posts_limit: int = Field(default=8, ge=1, le=20)
    commenters_per_post_cap: int = Field(default=80, ge=10, le=500)
    likers_per_post_cap: int = Field(default=150, ge=10, le=1000)
    run_async: bool = False


class ScrapedProfileSummary(BaseModel):
    username: str
    followers_count: int
    keyword: str


class ScrapeRunResponse(BaseModel):
    run_id: str
    status: str
    profiles_discovered: int
    interactions_collected: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    sample_profiles: list[ScrapedProfileSummary] = []
