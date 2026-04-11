"""LLM provider protocol definition."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Transport-level interface for LLM providers.

    Providers handle API communication only. Prompt construction
    and response parsing are the caller's responsibility.
    """

    @property
    def name(self) -> str:
        """Unique provider identifier (e.g., 'openai', 'gemini')."""
        ...

    @property
    def is_configured(self) -> bool:
        """Whether this provider has valid credentials."""
        ...

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any] | list[Any] | None:
        """Send messages and return parsed JSON response."""
        ...

    def chat_text(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str | None:
        """Send messages and return raw text response."""
        ...
