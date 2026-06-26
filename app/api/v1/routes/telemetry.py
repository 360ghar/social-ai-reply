"""Client-side telemetry endpoint.

Accepts structured log events from the browser (errors, unhandled rejections,
key interaction events) and re-emits them as a single structured log line so
production user-reported issues are debuggable from server logs.

Design notes:
- **Optional auth**: events may fire before login. We accept the request
  unauthenticated but never trust a client-supplied user id — identity is
  derived only from a valid JWT when present (``get_current_user_optional``).
- **No secrets/PII**: the ``props`` dict is sanitized server-side (secret keys
  dropped, long values truncated, key count capped). The structlog ``redact``
  processor is a further defense-in-depth layer.
- **Cheap**: one log line per request, no DB writes, no LLM calls.
"""
from __future__ import annotations

import re
from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.v1.deps import get_current_user_optional

log = structlog.get_logger("app.api.v1.routes.telemetry")

router = APIRouter(prefix="/v1", tags=["telemetry"])

# ── Sanitization constants ───────────────────────────────────────

# Keys whose values are dropped entirely (never logged).
# Optional [_-]? after each keyword lets \b fire at underscore boundaries,
# catching compound keys like access_token, refresh_token, id_token.
_SECRET_KEY_RE = re.compile(r"(?i)\b(?:password|token|secret|authorization|api[_-]?key|auth|cookie|session)[_-]?")
_MAX_PROP_KEYS = 20
_MAX_PROP_VALUE_LEN = 500
_MAX_MESSAGE_LEN = 2000
_MAX_STACK_LEN = 8000
_MAX_URL_LEN = 500
_MAX_EVENT_LEN = 128
_MAX_SESSION_ID_LEN = 64
# Reject payloads larger than this (8 KB) wholesale.
_MAX_PAYLOAD_BYTES = 8 * 1024


# ── Schemas ──────────────────────────────────────────────────────


ClientLogLevel = Literal["debug", "info", "warning", "error"]


class ClientEventRequest(BaseModel):
    """A single client-side log event."""

    event: str = Field(min_length=1, max_length=_MAX_EVENT_LEN)
    level: ClientLogLevel = "error"
    message: str | None = Field(default=None, max_length=_MAX_MESSAGE_LEN)
    stack: str | None = Field(default=None, max_length=_MAX_STACK_LEN)
    url: str | None = Field(default=None, max_length=_MAX_URL_LEN)
    session_id: str | None = Field(default=None, max_length=_MAX_SESSION_ID_LEN)
    props: dict[str, Any] | None = None

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="after")
    def _bound_payload_size(self) -> ClientEventRequest:
        """Reject payloads whose serialized size exceeds the 8 KB cap."""
        raw = self.model_dump_json()
        if len(raw.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
            raise ValueError("client event payload too large (max 8KB)")
        return self


class ClientEventResponse(BaseModel):
    status: str = "ok"


# ── Sanitization ─────────────────────────────────────────────────


def _sanitize_props(props: dict[str, Any] | None) -> dict[str, Any]:
    """Drop secret keys, cap key count, truncate long string values."""
    if not props or not isinstance(props, dict):
        return {}
    out: dict[str, Any] = {}
    for key, value in props.items():
        if not isinstance(key, str) or _SECRET_KEY_RE.search(key):
            continue
        if len(out) >= _MAX_PROP_KEYS:
            break
        if isinstance(value, str):
            out[key] = value[:_MAX_PROP_VALUE_LEN]
        elif isinstance(value, (int, float, bool)) or value is None:
            out[key] = value
        else:
            # Arrays/objects: stringify + truncate rather than log nested.
            try:
                out[key] = str(value)[:_MAX_PROP_VALUE_LEN]
            except Exception:
                continue
    return out


def _truncate(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value if len(value) <= limit else value[:limit]


# ── Handler ──────────────────────────────────────────────────────


@router.post("/telemetry/client-event", response_model=ClientEventResponse, status_code=status.HTTP_202_ACCEPTED)
def record_client_event(
    payload: ClientEventRequest,
    request: Request,
    current_user: dict | None = Depends(get_current_user_optional),
) -> ClientEventResponse:
    """Record a single client-side event as a structured log line.

    Works pre-login (``current_user`` is None when no/invalid JWT is present).
    Identity is derived only from the JWT — never from client-supplied props.
    """
    sanitized = _sanitize_props(payload.props)
    message = _truncate(payload.message, _MAX_MESSAGE_LEN)
    client_url = _truncate(payload.url, _MAX_URL_LEN)

    # Structured kv fields — structlog renderer handles the formatting.
    # The raw stack is intentionally NOT inlined into the event dict (it can
    # be large); it is appended to ``client_message`` only at warning/error
    # level so it is searchable alongside the error description.
    emit: dict[str, Any] = {
        **sanitized,
        "client_event": payload.event,
        "level": payload.level,
        "client_message": message,
        "client_url": client_url,
        "session_id": payload.session_id,
        "user_id": current_user["id"] if current_user else None,
    }

    if payload.level in ("warning", "error") and payload.stack:
        # Truncate the stack for the field but keep it attached so error
        # reports are actionable without a separate lookup.
        emit["client_stack"] = _truncate(payload.stack, _MAX_STACK_LEN)

    # Map client level to actual structlog level so LOG_LEVEL filtering works.
    _log_fn = getattr(log, payload.level, log.info)
    _log_fn("client_event", **emit)

    # Debug-level stack (full) emitted separately so it never bloats the
    # primary line; only useful when triaging a specific event.
    if payload.level == "debug" and payload.stack:
        log.debug("client_event_stack", client_event=payload.event, client_stack=_truncate(payload.stack, _MAX_STACK_LEN))

    return ClientEventResponse(status="ok")
