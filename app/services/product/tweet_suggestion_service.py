"""Tweet suggestion generation service.

Generates batches of tweet suggestions for a date range using the
existing LLM pipeline, then stores them with status='pending'.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.db.tables.tweet_suggestions import bulk_create_suggestions
from app.services.infrastructure.llm.service import LLMService

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)

_SUGGESTION_SYSTEM_PROMPT = (
    "You are a social media content strategist for a B2B/B2C brand. "
    "Generate engaging, platform-native social media post suggestions. "
    "Each suggestion must be self-contained, ready-to-post content that "
    "provides genuine value to the audience — no hard selling. "
    "Return ONLY a JSON array of objects, each with a 'content' field (string)."
)


def _build_user_prompt(
    platform: str,
    count: int,
    brand_context: str | None = None,
    existing_content: list[str] | None = None,
) -> str:
    parts = [f"Generate {count} distinct {platform} post suggestions."]
    if brand_context:
        parts.append(f"\nBrand context:\n{brand_context}")
    if existing_content:
        parts.append(
            "\nAvoid duplicating these existing topics:\n"
            + "\n".join(f"- {c[:100]}" for c in existing_content)
        )
    platform_instructions = {
        "twitter": (
            "Each suggestion must be under 280 characters. "
            "Use 1-3 relevant hashtags. Vary the content — mix educational, "
            "entertaining, promotional, and community-building posts."
        ),
        "x": (
            "Each suggestion must be under 280 characters. "
            "Use 1-3 relevant hashtags. Vary the content — mix educational, "
            "entertaining, promotional, and community-building posts."
        ),
        "instagram": (
            "Write Instagram caption-style content: shorter, conversational, "
            "and visual-focused. Use 5-10 relevant hashtags spread across the "
            "caption or at the end. Include a clear call-to-action (e.g. "
            "'double-tap if you agree', 'save this for later', 'share with a "
            "friend'). Keep captions between 50-200 characters. "
            "Emphasize aesthetics, emotion, and community."
        ),
        "linkedin": (
            "Write LinkedIn post-style content: longer, professional tone, "
            "and value-driven. Each post should be 150-500 characters. "
            "Use at most 3-5 relevant hashtags (avoid hashtag stuffing). "
            "Structure posts with a strong hook, insight or data point, "
            "and an open-ended question or call-to-action. "
            "Focus on thought leadership, industry insights, and "
            "professional storytelling."
        ),
    }
    instruction = platform_instructions.get(platform, platform_instructions["x"])
    parts.append(f"\n\nEach suggestion must be a complete, ready-to-post message. {instruction}")
    return "\n".join(parts)


def generate_suggestions(
    db: Client,
    workspace_id: int,
    platform: str,
    days: int,
    suggestions_per_day: int,
    brand_context: str | None = None,
) -> list[dict[str, Any]]:
    total_needed = days * suggestions_per_day
    llm = LLMService()
    if not llm.is_configured:
        logger.warning("LLM not configured; using template suggestions")
        suggestions = _generate_template_suggestions(total_needed, platform)
    else:
        existing = _fetch_existing_content(db, workspace_id, platform, days)
        prompt = _build_user_prompt(platform, total_needed, brand_context, existing)
        result = llm.call_json(
            system_prompt=_SUGGESTION_SYSTEM_PROMPT,
            user_content=prompt,
            temperature=0.8,
        )
        suggestions = _parse_llm_result(result, total_needed)

    records = _build_suggestion_records(
        workspace_id, platform, suggestions, days, suggestions_per_day
    )
    inserted = bulk_create_suggestions(db, records)
    logger.info("Generated %d %s suggestions for workspace %d", len(inserted), platform, workspace_id)
    return inserted


def _fetch_existing_content(
    db: Client,
    workspace_id: int,
    platform: str,
    days: int,
) -> list[str]:
    from app.db.tables.tweet_suggestions import list_suggestions_for_date_range

    today = date.today()
    end = today + timedelta(days=days)
    rows = list_suggestions_for_date_range(db, workspace_id, today, end, platform)
    return [row.get("content", "") for row in rows if row.get("content")]


def _parse_llm_result(
    result: dict[str, Any] | list[Any] | None,
    expected_count: int,
) -> list[dict[str, Any]]:
    if not result:
        return _generate_template_suggestions(expected_count, "twitter")

    if isinstance(result, list):
        items = result
    elif isinstance(result, dict):
        items = result.get("suggestions", result.get("posts", [result]))
    else:
        return _generate_template_suggestions(expected_count, "twitter")

    validated = []
    for item in items:
        if isinstance(item, dict) and item.get("content"):
            raw = item["content"]
            if isinstance(raw, list):
                raw = " ".join(str(c) for c in raw if not isinstance(c, (dict, list)))
            content = str(raw).strip()
            if content:
                validated.append({"content": content})
        elif isinstance(item, str):
            content = item.strip()
            if content:
                validated.append({"content": content})
    return validated or _generate_template_suggestions(expected_count, "twitter")


def _build_suggestion_records(
    workspace_id: int,
    platform: str,
    suggestions: list[dict[str, Any]],
    days: int,
    suggestions_per_day: int,
) -> list[dict[str, Any]]:
    today = date.today()
    records: list[dict[str, Any]] = []
    for i, suggestion in enumerate(suggestions):
        day_offset = i // suggestions_per_day
        if day_offset >= days:
            break
        suggested_date = today + timedelta(days=day_offset)
        records.append({
            "workspace_id": workspace_id,
            "content": suggestion["content"],
            "suggested_for_date": suggested_date.isoformat(),
            "status": "pending",
            "platform": platform,
        })
    return records


def _generate_template_suggestions(count: int, platform: str) -> list[dict[str, Any]]:
    templates = [
        "5 industry trends shaping {year} — which one surprised you most?",
        "We just shipped a major update. Here's what changed and why it matters.",
        "Thread: 3 mistakes we made building our product so you don't repeat them.",
        "Big news: our community just crossed 10K members! Thank you.",
        "What's the one tool you couldn't run your business without?",
        "Case study: How {customer} saved 40% on operational costs using our solution.",
        "Hot take: The best software is the one your team actually wants to use.",
        "We're hiring! Looking for a senior engineer who cares about craftsmanship.",
        "Behind the scenes: How we designed our latest feature in 72 hours.",
        "The ROI of good documentation: a thread.",
    ]
    year = datetime.now(UTC).year
    results = []
    for i in range(count):
        template = templates[i % len(templates)]
        content = template.replace("{year}", str(year)).replace("{customer}", "Acme Corp")
        if platform in ("twitter", "x"):
            content = content[:280]
        elif platform == "instagram":
            content = content[:2200]
            content += "\n\n#trending #innovation #growth #community #mustread"
        elif platform == "linkedin":
            content = content[:3000]
        results.append({"content": content})
    return results
