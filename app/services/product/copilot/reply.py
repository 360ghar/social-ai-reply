"""Reply draft generation from opportunity and brand context."""

from __future__ import annotations

import json

from app.services.product.copilot.llm_client import LLMClient


def generate_reply(
    opportunity: dict,
    brand: dict | None,
    prompts: list[dict],
    use_ai: bool = True,
) -> tuple[str, str, str]:
    """
    Generate a reply draft for a Reddit opportunity.

    Returns:
        Tuple of (content, rationale, source_prompt).
    """
    llm = LLMClient(enabled=use_ai)

    prompt_context = "\n".join(
        f"{prompt.get('name', '')}: {prompt.get('instructions', '')}"
        for prompt in prompts
        if prompt.get('prompt_type') == "reply"
    )

    if llm.enabled:
        ai_reply = _ai_reply(llm, opportunity, brand, prompt_context)
        if ai_reply:
            return ai_reply

    # Fallback: non-AI template
    cta = (brand.get("call_to_action") if brand and brand.get("call_to_action") else "offer a concise next step").strip(".")
    brand_name = brand.get("brand_name") if brand else "our team"
    content = (
        "You're not the only one dealing with this. A practical way to approach it is to start with the "
        "constraint that is slowing progress the most, test one small fix, and compare the before/after signal. "
        "We've seen teams similar to yours benefit from documenting what changed and why before expanding "
        "the solution."
    )
    rationale = (
        "The draft stays non-promotional, responds to the stated problem, and leaves room for a follow-up "
        f"where {brand_name} can help if the thread invites it."
    )
    source_prompt = prompt_context or cta
    return content, rationale, source_prompt


def _ai_reply(
    llm: LLMClient,
    opportunity: dict,
    brand: dict | None,
    prompt_context: str,
) -> tuple[str, str, str] | None:
    """Generate reply using LLM."""
    try:
        system_prompt = (
            "Write a useful Reddit reply. Avoid spam, avoid sounding salesy, do not mention the company unless "
            "asked. Return JSON with content and rationale."
        )
        brand_context = {
            "brand_name": brand.get("brand_name") if brand else "",
            "summary": brand.get("summary") if brand else "",
            "voice_notes": brand.get("voice_notes") if brand else "",
            "cta": brand.get("call_to_action") if brand else "",
        }
        user_content = json.dumps({
            "opportunity": {
                "title": opportunity.get("title", ""),
                "body_excerpt": opportunity.get("body_excerpt", ""),
                "subreddit": opportunity.get("subreddit", ""),
            },
            "brand": brand_context,
            "prompt_context": prompt_context,
        })
        payload = llm.call(system_prompt, user_content, temperature=0.4)
        if not payload:
            return None
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        if not isinstance(payload, dict):
            return None
        content = (payload.get("content") or "").strip()
        if not content:
            return None
        return content, payload.get("rationale") or "AI generated reply draft.", prompt_context
    except Exception:
        return None
