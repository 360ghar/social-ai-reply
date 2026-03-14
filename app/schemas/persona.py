from datetime import datetime

from pydantic import BaseModel, Field


class BusinessInputRequest(BaseModel):
    business_description: str = Field(min_length=5, max_length=400)
    locale: str | None = Field(default=None, description="Optional market/city/country hint")
    max_personas: int = Field(default=12, ge=3, le=30)
    default_min_followers: int = Field(default=1000, ge=100, le=500000)


class AdjacentPersona(BaseModel):
    keyword: str = Field(min_length=2, max_length=80)
    profile_type: str = Field(min_length=2, max_length=120)
    overlap_reason: str = Field(min_length=10, max_length=400)
    priority_score: int = Field(ge=1, le=100)


class KeywordSeed(BaseModel):
    keyword: str
    profile_type: str
    priority_score: int
    min_followers: int


class DiscoverySeed(BaseModel):
    business_description: str
    generated_at: datetime
    keywords: list[KeywordSeed]


class PersonaPlanResponse(BaseModel):
    business_description: str
    generated_at: datetime
    targets: list[AdjacentPersona]
    discovery_seed: DiscoverySeed
