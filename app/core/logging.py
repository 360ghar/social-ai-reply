"""Structured logging configuration built on structlog.

All stdlib ``logging.getLogger(...).info(...)`` calls (~340 across the codebase)
are routed through a structlog ``ProcessorFormatter`` so they inherit the new
unified rendering — ConsoleRenderer (colorized, dev) or JSONRenderer (one JSON
object per line, prod) — WITHOUT being rewritten. New code is encouraged to use
``structlog.get_logger()`` for first-class key/value logging.

Context fields (request_id/user_id/workspace_id/project_id/route) are merged
onto every record from ``structlog.contextvars`` via ``merge_contextvars``, so
anything bound through ``app.core.log_context`` (or directly via structlog) is
stamped on both structlog-native and legacy stdlib log calls.

If you change the renderer list, keep in mind the HARD REQUIREMENT: arbitrary
key/value fields MUST survive rendering in BOTH renderers. ConsoleRenderer shows
extra fields by default; JSONRenderer emits them as top-level keys. Do not add a
processor that drops unknown keys.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import structlog

from app.core.constants.app import DEFAULT_LOG_FORMAT, DEFAULT_LOG_LEVEL
from app.core.redaction import redact

# Sensible callsite subset — full CallsiteParameterAdder adds ~10 fields; we
# keep only the ones useful for triage: source file, function, line number.
_CALLSITE_PARAMS = (
    structlog.processors.CallsiteParameter.FILENAME,
    structlog.processors.CallsiteParameter.FUNC_NAME,
    structlog.processors.CallsiteParameter.LINENO,
)

if TYPE_CHECKING:
    from app.core.config import Settings

# Re-exported so legacy importers (e.g. app.services.product) keep working.
__all__ = ["logger", "setup_logging"]

logger = logging.getLogger(__name__)

# Third-party loggers that are noisy at INFO and have no business value there.
# Silenced to WARNING in _silence_third_party().
_NOISY_LOGGERS = (
    "httpx",
    "httpcore",
    "urllib3",
    "supabase",
    "postgrest",
    "openai",
    "anthropic",
    "google.auth",
    "google.generativeai",
    "apscheduler",
    "sqlalchemy",
    "uvicorn.access",
)

_VALID_FORMATS = {"auto", "console", "json"}


def _resolve_format(log_format: str, environment: str) -> str:
    """``auto`` → console in dev, json in production."""
    fmt = log_format.strip().lower()
    if fmt not in _VALID_FORMATS:
        fmt = DEFAULT_LOG_FORMAT
    if fmt == "auto":
        return "console" if environment.strip().lower() != "production" else "json"
    return fmt


def _build_renderer(fmt: str):
    if fmt == "console":
        return structlog.dev.ConsoleRenderer(colors=True)
    return structlog.processors.JSONRenderer()


def _silence_third_party() -> None:
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def setup_logging(settings: Settings | str | None = None, level: str | None = None) -> None:
    """Configure root logging with structlog's ProcessorFormatter chain.

    Accepts a ``Settings`` object (preferred — reads ``log_level``, ``log_format``,
    ``environment``) for backwards compatibility also accepts a bare level
    string. When called with no args, falls back to the module defaults.
    """
    # Backwards-compat: legacy callers passed a level string (e.g. "INFO").
    if isinstance(settings, str) or settings is None:
        env = "development"
        log_level = (settings or level or DEFAULT_LOG_LEVEL).upper()
        log_format = DEFAULT_LOG_FORMAT
    else:
        env = getattr(settings, "environment", "development")
        log_level = (level or getattr(settings, "log_level", DEFAULT_LOG_LEVEL)).upper()
        log_format = getattr(settings, "log_format", DEFAULT_LOG_FORMAT)

    numeric_level = getattr(logging, log_level, logging.INFO)
    fmt = _resolve_format(log_format, env)
    renderer = _build_renderer(fmt)

    # Processors applied to BOTH structlog-native records and foreign (stdlib)
    # records via foreign_pre_chain. Order matters: merge contextvars first so
    # everything downstream sees the bound fields. format_exc_info is included
    # so stdlib logger.exception() calls reliably render tracebacks.
    shared_meta = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.CallsiteParameterAdder(parameters=_CALLSITE_PARAMS),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_meta
        + [
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_meta,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            redact,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(numeric_level)

    _silence_third_party()
    return root
