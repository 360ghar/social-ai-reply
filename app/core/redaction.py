"""Best-effort secret redaction structlog processor.

This is a DEFENSE-IN-DEPTH measure: it scrubs common secret patterns from the
string-valued fields of every log event_dict before rendering. It is NOT a
security boundary — never rely on it as the only control. The right fix is to
avoid logging secrets in the first place; this processor catches accidental
leakage (e.g. an Authorization header echoed into a debug message).

It only operates on STRING values. Typed fields (int/float/bool/None) and
non-string objects are passed through untouched, so numeric IDs and booleans are
never mangled.

Patterns, compiled once at module load:
  - ``Bearer <token>`` and ``Authorization: <value>`` (case-insensitive)
  - dict/JSON-ish key=value pairs where the key is one of the well-known
    secret names (password, api_key, apikey, secret, token, access_token,
    refresh_token) — the value following the key is redacted.
  - standalone base64/hex blobs that are >= 32 chars long. The length floor
    avoids eating short UUIDs, slugs, and small IDs. Hyphenated UUIDs are
    explicitly exempted (see ``_UUID_RE``) — they are identifiers like
    request_id/session_id, never secrets; redacting them would break log
    correlation. Bare 32-char hex (no hyphens) is still treated as secret.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = ["redact", "_redact"]

_REDACTED = "[REDACTED]"

# Order matters only for readability; each pattern is applied independently.
_BEARER_RE = re.compile(r"(?i)Bearer\s+\S+")
_AUTH_HEADER_RE = re.compile(r"(?i)Authorization\s*:\s*\S+")

# Matches `"<secret_key>": "<value>"`, `"<secret_key>": <bareword>`, or
# `<secret_key>=<value>`. Captures the key (group 1) and keeps it, redacting
# only the value portion. Supports JSON-ish quotes and url/query form.
_SECRET_KV_RE = re.compile(
    r'(?i)(["\']?(?:password|api_key|apikey|secret|token|access_token|refresh_token)["\']?\s*[:=]\s*)'
    r"""(?:"([^"]*)"|'([^']*)'|([^\s"'\]},;]+))"""
)

# Full JWT tokens: Supabase keys, service-role keys, and other JWT credentials
# are three dot-separated base64url segments. The header and payload decode to
# JSON (always starting with `eyJ` = `{"` in base64url), so the blob regex
# alone only catches the ≥32-char signature segment, leaving the credential
# partially exposed. We catch the whole token FIRST. Must run before _BLOB_RE.
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")

# Standalone opaque blob: base64 (+/=) or hex (-), at least 32 chars.
# Underscores excluded — they appear in snake_case identifiers which are
# legitimate log data, not secrets.
_BLOB_RE = re.compile(r"[A-Za-z0-9+/=-]{32,}")

# Hyphenated UUIDs are legitimate identifiers (request_id, session_id) and MUST
# survive redaction, or every correlation id in production logs becomes
# "[REDACTED]". Real secrets (JWTs, API keys, OAuth tokens) are never
# UUID-formatted, so exempting this exact shape is safe. Bare 32-char hex
# (no hyphens) is NOT exempted — it stays treated as a potential secret.
_UUID_RE = re.compile(
    r"\A[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z"
)


def _blob_repl(match: re.Match) -> str:
    """Redact an opaque blob, but preserve hyphenated UUIDs (identifiers)."""
    token = match.group(0)
    return token if _UUID_RE.match(token) else _REDACTED


def _redact_string(value: str) -> str:
    """Apply all redaction patterns to a single string."""
    value = _BEARER_RE.sub(_REDACTED, value)
    value = _AUTH_HEADER_RE.sub(_REDACTED, value)
    value = _SECRET_KV_RE.sub(lambda m: f"{m.group(1)}{_REDACTED}", value)
    # JWTs before blobs — catch the whole token before the blob regex
    # processes segments individually (leaving header+payload exposed).
    value = _JWT_RE.sub(_REDACTED, value)
    value = _BLOB_RE.sub(_blob_repl, value)
    return value


def redact(
    _logger: Any = None, _method_name: str = "", event_dict: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Structlog processor that scrubs secrets from string-valued event fields.

    Usable both as ``redact`` (structlog processor protocol) and called directly
    with an event_dict.
    """
    # structlog calls processors as (logger, method_name, event_dict); allow the
    # direct-call convenience form ``redact(event_dict)`` too.
    if event_dict is None:
        # direct call: redact(event_dict) — only arg is the dict
        if isinstance(_logger, dict):
            event_dict = _logger
            _logger = None
        else:
            return {}

    out: dict[str, Any] = {}
    for key, val in event_dict.items():
        if isinstance(val, str):
            out[key] = _redact_string(val)
        else:
            out[key] = val
    return out


# Alias matching the conventional structlog processor signature name used in the
# logging chain. Both names point at the same callable.
_redact = redact
