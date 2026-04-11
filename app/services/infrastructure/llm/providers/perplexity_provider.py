"""Perplexity LLM provider — uses OpenAI SDK with Perplexity base URL."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.services.infrastructure.llm._json_helpers import parse_json_payload
from app.services.infrastructure.llm.providers._registry import register

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)

PERPLEXITY_BASE_URL = "https://api.perplexity.ai"


class PerplexityProvider:
    """Perplexity provider using the OpenAI SDK.

    Perplexity exposes an OpenAI-compatible API, so we reuse the SDK
    with a different base_url.
    """

    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_settings(cls, settings: Settings) -> PerplexityProvider | None:
        if not settings.perplexity_api_key:
            return None
        import httpx
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.perplexity_api_key,
            base_url=PERPLEXITY_BASE_URL,
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        return cls(client, settings.perplexity_model)

    @property
    def name(self) -> str:
        return "perplexity"

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any] | list[Any] | None:
        try:
            # Perplexity does not reliably support response_format,
            # so we request normal text and parse JSON from it.
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
            )
            text = resp.choices[0].message.content if resp.choices else None
            return parse_json_payload(text) if text else None
        except Exception:
            logger.exception("Perplexity chat_json failed")
            return None

    def chat_text(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str | None:
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content if resp.choices else None
        except Exception:
            logger.exception("Perplexity chat_text failed")
            return None


register("perplexity", PerplexityProvider)
