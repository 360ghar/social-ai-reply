"""LLM client for Gemini API calls."""

from __future__ import annotations

import json
import logging
import os
import re

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for LLM API calls (Gemini primary)."""

    def __init__(self, enabled: bool = True) -> None:
        settings = get_settings()
        self.enabled = enabled and bool(settings.gemini_api_key or settings.openai_api_key)
        self.enabled = self.enabled and "PYTEST_CURRENT_TEST" not in os.environ
        self.model = settings.gemini_model or "gemini-2-flash-preview"
        self.api_url = settings.gemini_api_url or "https://generativelanguage.googleapis.com/v1beta"
        self.api_key = settings.gemini_api_key or settings.openai_api_key

    def call(self, system_prompt: str, user_content: str, temperature: float = 0.2) -> dict | list | None:
        """Call the LLM API and return parsed JSON response."""
        if not self.enabled or not self.api_key:
            return None
        try:
            url = f"{self.api_url}/models/{self.model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"{system_prompt}\n\n{user_content}"}]}
                ],
                "generationConfig": {
                    "temperature": temperature,
                    "responseMimeType": "application/json"
                }
            }
            resp = httpx.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
            return _parse_json_payload(text)
        except Exception:
            logger.exception("LLM API call failed")
            return None


def _parse_json_payload(text: str) -> dict | list | None:
    """Parse JSON from LLM response text, handling markdown code blocks."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    decoder = json.JSONDecoder()
    candidates = [
        cleaned,
        cleaned[cleaned.find("{"):] if "{" in cleaned else "",
        cleaned[cleaned.find("["):] if "[" in cleaned else "",
    ]
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            payload, _index = decoder.raw_decode(candidate)
            return payload
        except json.JSONDecodeError:
            continue
    return None
