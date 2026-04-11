"""LLM provider registry and factory functions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.core.config import get_settings

if TYPE_CHECKING:
    from app.services.infrastructure.llm.base import LLMProvider

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, type] = {}


def register(name: str, cls: type) -> None:
    """Register a provider class by name."""
    _REGISTRY[name] = cls


def get_provider(name: str | None = None) -> LLMProvider:
    """Get a provider by name, or the default from LLM_PROVIDER env var."""
    settings = get_settings()
    provider_name = name or settings.llm_provider

    cls = _REGISTRY.get(provider_name)
    if not cls:
        raise ValueError(f"Unknown LLM provider: {provider_name!r}. Available: {list(_REGISTRY.keys())}")

    instance = cls.from_settings(settings)
    if instance is None:
        raise ValueError(f"Provider {provider_name!r} is not configured (missing API key?)")

    return instance


def get_configured_providers() -> dict[str, LLMProvider]:
    """Return all providers that have valid credentials configured.

    Used by VisibilityRunner to call multiple models.
    """
    settings = get_settings()
    result: dict[str, LLMProvider] = {}

    for name, cls in _REGISTRY.items():
        try:
            instance = cls.from_settings(settings)
            if instance is not None and instance.is_configured:
                result[name] = instance
        except Exception:
            logger.debug("Provider %r failed to initialize, skipping", name)

    return result
