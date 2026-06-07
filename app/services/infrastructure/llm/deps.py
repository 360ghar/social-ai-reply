"""Typed dependency classes for Pydantic AI agents.

Dependencies are injected into agent runs via RunContext, giving system prompts,
output validators, and tools access to contextual data without global state.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BrandDeps:
    """Dependencies for brand analysis and reply/post generation."""

    brand_name: str = ""
    summary: str = ""
    product_summary: str = ""
    target_audience: str = ""
    voice_notes: str = ""
    call_to_action: str = ""
    business_domain: str = ""

    @classmethod
    def from_brand_dict(cls, brand: dict | None) -> BrandDeps:
        if not brand:
            return cls()
        return cls(
            brand_name=brand.get("brand_name", ""),
            summary=brand.get("summary", ""),
            product_summary=brand.get("product_summary", ""),
            target_audience=brand.get("target_audience", ""),
            voice_notes=brand.get("voice_notes", ""),
            call_to_action=brand.get("call_to_action", ""),
            business_domain=brand.get("business_domain", ""),
        )


@dataclass
class ReplyDeps:
    """Dependencies for reply draft generation."""

    opportunity_title: str = ""
    opportunity_body: str = ""
    subreddit: str = ""
    score_reasons: list[str] = field(default_factory=list)
    brand: BrandDeps = field(default_factory=BrandDeps)
    prompt_context: str = ""


@dataclass
class PostDeps:
    """Dependencies for post draft generation."""

    brand: BrandDeps = field(default_factory=BrandDeps)
    prompt_context: str = ""
