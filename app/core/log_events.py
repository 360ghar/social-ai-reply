"""Structured flow-event logging helpers built on structlog.

WS3 (logging overhaul) provides a small, consistent API for emitting
``<flow>.start`` / ``<flow>.ok`` / ``<flow>.failed`` events around
high-value request flows (draft generation, visibility runs, voice analysis,
entitlement enforcement, scans, auth, billing).

Why this module exists
----------------------
structlog's ``ProcessorFormatter`` does NOT surface stdlib
``logger.info(..., extra={...})`` attributes onto the rendered record. For
structured key/value event data you MUST go through a structlog logger.
This module is the single place that owns that contract so route/service
code stays consistent.

Convention
----------
* **No PII** — never log emails, names, tokens, full post/reply content,
  or anything that could identify a user or leak a secret. Prefer ids.
* **No f-string payloads** — event data is always passed as ``key=value``
  keyword args so it survives as discrete fields in JSON output.
* **Reserved names** — structlog uses ``event`` as the message key; do not
  pass an ``event`` kwarg. Avoid ``message``, ``module``, ``level``,
  ``logger``, ``name`` — they collide with logging internals.
* **Context fields** (``request_id``/``user_id``/``workspace_id``/
  ``project_id``/``route``) are auto-merged from contextvars by WS2's
  middleware/deps wiring — do not set them here.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = [
    "event_logger",
    "log_event",
    "timed",
]


def event_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a named structlog logger for ad-hoc structured events.

    Prefer :func:`timed` for start/ok/failed flows; use this when you only
    need a single event (e.g. ``entitlement.enforced``).
    """
    return structlog.get_logger(name)


def log_event(event: str, level: int | str = "info", **fields: Any) -> None:
    """Emit a single structured event.

    ``level`` may be a stdlib level int or a level name string ("info",
    "warning", "error", "debug"). The event string becomes the record's
    message key; all ``fields`` are attached as top-level JSON keys.
    """
    log: structlog.stdlib.BoundLogger = structlog.get_logger()
    level_name = level if isinstance(level, str) else logging.getLevelName(level).lower()
    getattr(log, level_name)(event, **fields)


@contextmanager
def timed(name: str, **fields: Any) -> Iterator[structlog.stdlib.BoundLogger]:
    """Emit ``<name>.start`` on entry, ``<name>.ok`` on success, ``<name>.failed`` on error.

    On success emits ``<name>.ok`` with ``latency_ms`` (wall-clock ms, 2dp).
    On exception emits ``<name>.failed`` with ``latency_ms`` and the
    exception traceback (via structlog ``log.exception``), then re-raises.

    Example::

        with timed("draft.generate", opportunity_id=opp_id,
                   variant_count=payload.variants, draft_type="reply"):
            ...

    Identity/request context is auto-merged from contextvars — do not pass
    ``user_id``/``workspace_id``/``project_id``/``request_id``/``route``.
    """
    log: structlog.stdlib.BoundLogger = structlog.get_logger().bind(event_prefix=name, **fields)
    log.info(name + ".start", **fields)
    start = time.perf_counter()
    try:
        yield log
    except Exception:
        log.exception(name + ".failed", latency_ms=round((time.perf_counter() - start) * 1000, 2))
        raise
    else:
        log.info(name + ".ok", latency_ms=round((time.perf_counter() - start) * 1000, 2))
