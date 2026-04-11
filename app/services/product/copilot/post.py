"""Post draft generation from brand context."""

from __future__ import annotations

import json

from app.services.product.copilot.llm_client import LLMClient


def generate_post(
    brand: dict | None,
    prompts: list[dict],
) -> tuple[str, str, str]:
    """
    Generate a Reddit post draft from brand context.

    Returns:
        Tuple of (title, body, rationale).

    Raises:
        RuntimeError: If the LLM call fails or returns no usable content.
    """
    llm = LLMClient()

    prompt_context = "\n".join(
        f"{prompt.get('name', '')}: {prompt.get('instructions', '')}"
        for prompt in prompts
        if prompt.get('prompt_type') == "post"
    )

    ai_post = _ai_post(llm, brand, prompt_context)
    if ai_post:
        return ai_post

    raise RuntimeError(
        "Failed to generate post draft — the LLM returned no usable response. "
        "Check that your LLM provider API key is configured and try again."
    )


def _ai_post(llm: LLMClient, brand: dict | None, prompt_context: str) -> tuple[str, str, str] | None:
    """Generate post using LLM."""
    try:
        system_prompt = "Return JSON with title, body, and rationale for a non-promotional Reddit post."
        user_content = json.dumps({
            "brand_name": brand.get("brand_name") if brand else "",
            "summary": brand.get("summary") if brand else "",
            "voice_notes": brand.get("voice_notes") if brand else "",
            "prompt_context": prompt_context,
        })
        payload = llm.call(system_prompt, user_content, temperature=0.5)
        if not payload:
            return None
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        if not isinstance(payload, dict):
            return None
        title = (payload.get("title") or "").strip()
        body = (payload.get("body") or "").strip()
        if not title or not body:
            return None
        return title, body, payload.get("rationale") or "AI generated post draft."
    except Exception:
        return None
