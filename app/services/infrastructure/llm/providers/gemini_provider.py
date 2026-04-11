"""Gemini LLM provider — uses httpx for the Gemini REST API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx

from app.services.infrastructure.llm._json_helpers import parse_json_payload
from app.services.infrastructure.llm.providers._registry import register

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Gemini provider using the native REST API via httpx.

    Gemini's API is not OpenAI-compatible, so we use httpx directly.
    """

    def __init__(self, api_key: str, model: str, api_url: str) -> None:
        self._api_key = api_key
        self._model = model
        self._api_url = api_url.rstrip("/")

    @classmethod
    def from_settings(cls, settings: Settings) -> GeminiProvider | None:
        if not settings.gemini_api_key:
            return None
        return cls(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            api_url=settings.gemini_api_url,
        )

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any] | list[Any] | None:
        try:
            prompt = self._format_messages(messages)
            url = f"{self._api_url}/models/{self._model}:generateContent"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "responseMimeType": "application/json",
                },
            }
            resp = httpx.post(
                url,
                json=payload,
                headers={"x-goog-api-key": self._api_key},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "{}")
            )
            return parse_json_payload(text)
        except Exception:
            logger.exception("Gemini chat_json failed")
            return None

    def chat_text(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str | None:
        try:
            prompt = self._format_messages(messages)
            url = f"{self._api_url}/models/{self._model}:generateContent"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            }
            resp = httpx.post(
                url,
                json=payload,
                headers={"x-goog-api-key": self._api_key},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text")
            )
        except Exception:
            logger.exception("Gemini chat_text failed")
            return None

    @staticmethod
    def _format_messages(messages: list[dict[str, str]]) -> str:
        """Format messages into a single prompt string with role labels for Gemini."""
        parts: list[str] = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                parts.append(f"[System Instructions]\n{msg['content']}")
            elif role == "assistant":
                parts.append(f"[Assistant]\n{msg['content']}")
            else:
                parts.append(msg["content"])
        return "\n\n".join(parts)


register("gemini", GeminiProvider)
