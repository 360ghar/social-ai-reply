"""LLM response caching with TTL.

Caches agent run results keyed by (agent_id, prompt, deps_hash) to avoid
re-calling the LLM for identical inputs within the TTL window.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_LOCK = threading.Lock()
_MAX_CACHE_ENTRIES = 1024

DEFAULT_CACHE_TTL = 300.0  # 5 minutes


def _make_cache_key(agent_name: str, prompt: str, deps_hash: str) -> str:
    raw = f"{agent_name}:{prompt}:{deps_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _deps_hash(deps: Any) -> str:
    """Create a stable hash from a deps dataclass."""
    try:
        if hasattr(deps, "__dict__"):
            raw = json.dumps(deps.__dict__, default=str, sort_keys=True)
        else:
            raw = json.dumps(deps, default=str, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()
    except Exception:
        return hashlib.sha256(str(deps).encode()).hexdigest()


def get_cached(agent_name: str, prompt: str, deps: Any) -> Any | None:
    """Return cached result if present and not expired, else None."""
    key = _make_cache_key(agent_name, prompt, _deps_hash(deps))
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            _CACHE.pop(key, None)
            return None
    logger.debug("Cache hit for agent=%s key=%s", agent_name, key[:12])
    return value


def set_cached(agent_name: str, prompt: str, deps: Any, value: Any, ttl: float = DEFAULT_CACHE_TTL) -> None:
    """Store a result in the cache with TTL."""
    key = _make_cache_key(agent_name, prompt, _deps_hash(deps))
    with _CACHE_LOCK:
        if len(_CACHE) >= _MAX_CACHE_ENTRIES:
            now = time.monotonic()
            expired = [k for k, (exp, _) in _CACHE.items() if now >= exp]
            for k in expired:
                _CACHE.pop(k, None)
            if len(_CACHE) >= _MAX_CACHE_ENTRIES and _CACHE:
                oldest_key = min(_CACHE.items(), key=lambda item: item[1][0])[0]
                _CACHE.pop(oldest_key, None)
        _CACHE[key] = (time.monotonic() + ttl, value)
    logger.debug("Cache set for agent=%s key=%s ttl=%.0fs", agent_name, key[:12], ttl)


def clear_cache() -> None:
    """Clear all cached entries."""
    with _CACHE_LOCK:
        _CACHE.clear()
