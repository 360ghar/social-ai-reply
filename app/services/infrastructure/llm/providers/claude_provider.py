"""Anthropic Claude LLM provider — uses httpx for the Anthropic REST API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx

from app.services.infrastructure.llm._json_helpers import parse_json_payload
from app.services.infrastructure.llm.providers._registry import register

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class ClaudeProvider:
    """Claude provider using the Anthropic REST API via httpx.

    Anthropic's API is not OpenAI-compatible, so we use httpx directly.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    @classmethod
    def from_settings(cls, settings: Settings) -> ClaudeProvider | None:
        if not settings.anthropic_api_key:
            return None
        return cls(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
        )

    @property
    def name(self) -> str:
        return "claude"

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
            system_msg, user_messages = self._split_messages(messages)
            resp = httpx.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": 4096,
                    "system": system_msg,
                    "messages": user_messages,
                    "temperature": temperature,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("content", [{}])[0].get("text", "")
            return parse_json_payload(text) if text else None
        except Exception:
            logger.exception("Claude chat_json failed")
            return None

    def chat_text(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str | None:
        try:
            system_msg, user_messages = self._split_messages(messages)
            resp = httpx.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": max_tokens,
                    "system": system_msg,
                    "messages": user_messages,
                    "temperature": temperature,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("content", [{}])[0].get("text")
        except Exception:
            logger.exception("Claude chat_text failed")
            return None

    @staticmethod
    def _split_messages(
        messages: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, str]]]:
        """Extract system message and user/assistant messages for Anthropic API."""
        system_parts: list[str] = []
        user_messages: list[dict[str, str]] = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                user_messages.append(msg)
        system_msg = "\n\n".join(system_parts) if system_parts else ""
        return system_msg, user_messages


register("claude", ClaudeProvider)
