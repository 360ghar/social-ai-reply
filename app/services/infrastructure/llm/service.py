"""LLM service facades — unified entry points for all LLM operations."""

from __future__ import annotations

import logging
from typing import Any

import app.services.infrastructure.llm.providers  # noqa: F401 — trigger provider registration
from app.services.infrastructure.llm.providers._registry import (
    get_configured_providers,
    get_provider,
)

logger = logging.getLogger(__name__)

# Canonical model-name mapping for visibility
_MODEL_ALIASES: dict[str, str] = {
    "chatgpt": "openai",
    "openai": "openai",
    "perplexity": "perplexity",
    "gemini": "gemini",
    "claude": "claude",
}

_DEFAULT_VISIBILITY_SYSTEM = (
    "You are a helpful assistant. Answer the user's question thoroughly with specific "
    "product and brand recommendations where relevant. Include URLs to sources when possible."
)


class LLMService:
    """Unified facade for single-provider LLM operations.

    Wraps provider selection and exposes simple call_json/call_text methods.
    This is the primary interface for copilot modules.
    """

    def __init__(self, provider_name: str | None = None) -> None:
        try:
            self._provider = get_provider(provider_name)
        except ValueError as e:
            raise RuntimeError(
                f"No LLM provider available — cannot make LLM calls. "
                f"Ensure a valid LLM_PROVIDER is configured and the required API key is set. "
                f"Details: {e}"
            ) from e

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def is_enabled(self) -> bool:
        return self._provider is not None and self._provider.is_configured

    def call_json(
        self,
        system_prompt: str,
        user_content: str,
        temperature: float = 0.2,
    ) -> dict[str, Any] | list[Any] | None:
        """Call LLM and return parsed JSON. Drop-in replacement for LLMClient.call()."""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
            return self._provider.chat_json(messages, temperature=temperature)
        except Exception:
            logger.exception("LLM call_json failed via %s", self._provider.name)
            return None

    def call_text(
        self,
        prompt: str,
        system_message: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str | None:
        """Call LLM and return raw text response."""
        try:
            messages: list[dict[str, str]] = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})
            return self._provider.chat_text(
                messages, temperature=temperature, max_tokens=max_tokens
            )
        except Exception:
            logger.exception("LLM call_text failed via %s", self._provider.name)
            return None


class VisibilityRunner:
    """Runs prompts across all configured providers.

    Replaces ModelRunner from visibility.py with a cleaner abstraction.
    Each model name maps to a registered provider via _MODEL_ALIASES.
    """

    def __init__(self) -> None:
        self._providers = get_configured_providers()

    def run_prompt(self, prompt: str, model_name: str) -> str | None:
        """Run a prompt on a specific model by name."""
        provider_key = _MODEL_ALIASES.get(model_name)
        provider = self._providers.get(provider_key) if provider_key else None

        if not provider:
            raise RuntimeError(
                f"No configured provider for model {model_name!r}. "
                f"Ensure the required API key is set for this provider."
            )

        try:
            messages = [
                {"role": "system", "content": _DEFAULT_VISIBILITY_SYSTEM},
                {"role": "user", "content": prompt},
            ]
            return provider.chat_text(
                messages, temperature=0.7, max_tokens=2048
            )
        except Exception as e:
            logger.error("Provider %s error: %s", provider_key, e)
            raise RuntimeError(
                f"Failed to run prompt on {model_name!r} via provider {provider_key!r}: {e}"
            ) from e

    def run_all(self, prompt: str, model_names: list[str]) -> dict[str, str | None]:
        """Run a prompt on all specified models. Returns {model_name: response}."""
        return {name: self.run_prompt(prompt, name) for name in model_names}
