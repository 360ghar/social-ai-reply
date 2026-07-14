"""Tests for source-level redaction (WS4) + the redaction processor.

These prove that the leaky call sites fixed in WS4 no longer emit raw
secrets/PII, that LLM telemetry is emitted as structured kv (not an
f-string blob), and that the masking helper is safe for malformed input.

They are independent of network and of any Supabase/Reddit state.
"""

from __future__ import annotations

import io
import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
import structlog

from app.core.log_context import clear_request_context
from app.core.logging import setup_logging
from app.services.infrastructure.llm.llm_telemetry import LLMCallRecord, record_call
from app.services.product.email_service import _mask_email

REPO_ROOT = Path(__file__).resolve().parent.parent


def _settings(log_format: str = "json", environment: str = "production", level: str = "DEBUG"):
    return SimpleNamespace(log_format=log_format, environment=environment, log_level=level)


def _capture(settings) -> io.StringIO:
    buf = io.StringIO()
    setup_logging(settings)
    root = logging.getLogger()
    for h in root.handlers:
        h.stream = buf
    return buf


@pytest.fixture(autouse=True)
def _reset_structlog():
    clear_request_context()
    yield
    clear_request_context()
    structlog.reset_defaults()


# --- email masking -----------------------------------------------------------

def test_mask_email_standard():
    assert _mask_email("alice@example.com") == "***@example.com"


def test_mask_email_short_user():
    assert _mask_email("b@x.io") == "***@x.io"


def test_mask_email_malformed_returns_safe():
    # Never raises; falls back to '***' so a log call can never crash.
    assert _mask_email("not-an-email") == "***"
    assert _mask_email("") == "***"
    assert _mask_email("@nodomain.com") == "***"
    assert _mask_email("nouser@") == "***"
    assert _mask_email(None) == "***"  # type: ignore[arg-type]
    assert _mask_email(123) == "***"  # type: ignore[arg-type]


# --- LLM telemetry structured output ----------------------------------------

def test_llm_telemetry_structured_fields():
    """record_call emits per-call metrics as top-level JSON keys, not an f-string blob."""
    buf = _capture(_settings(log_format="json"))
    record_call(
        LLMCallRecord(
            agent_name="reply_agent",
            provider="gemini",
            model="gemini-2.0-flash",
            latency_ms=1234.5,
            request_tokens=100,
            response_tokens=200,
            cost_usd=0.000123,
            success=True,
        )
    )

    line = buf.getvalue().strip()
    assert line, "expected at least one log line"
    obj = json.loads(line)

    # Structured kv fields are top-level keys.
    assert obj["event"] == "llm_call"
    assert obj["llm_agent"] == "reply_agent"
    assert obj["llm_provider"] == "gemini"
    assert obj["llm_model"] == "gemini-2.0-flash"
    assert obj["latency_ms"] == 1234.5
    assert obj["tokens_in"] == 100
    assert obj["tokens_out"] == 200
    assert obj["cost_usd"] == 0.000123
    assert obj["llm_success"] is True

    # The event must NOT be an interpolated blob like "llm_call agent=...".
    assert "agent=reply_agent" not in obj["event"]


def test_llm_telemetry_structured_failure():
    """A failed call still emits structured fields (success=False, no crash)."""
    buf = _capture(_settings(log_format="json"))
    record_call(
        LLMCallRecord(
            agent_name="post_agent",
            provider="openai",
            model="gpt-4o",
            latency_ms=50.0,
            success=False,
            error="boom",
        )
    )
    obj = json.loads(buf.getvalue().strip())
    assert obj["llm_success"] is False
    assert obj["llm_agent"] == "post_agent"
    assert obj["latency_ms"] == 50.0


# --- source-level grep-style assertions -------------------------------------

def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text()


def test_no_resp_text_in_reddit_posting_logs():
    """reddit_posting OAuth logs must not reference resp.text or the raw data dict."""
    src = _read("app/api/v1/routes/reddit_posting.py")
    # Find the two log lines around the token-exchange failure handling.
    # They must carry length/status, not the body or payload.
    assert "resp.text[:300]" not in src, "raw resp.text excerpt must not be logged"
    # The 'data' payload must not be logged verbatim.
    assert 'logger.warning("Reddit token exchange returned error payload: %s", data)' not in src


def test_no_raw_params_in_reddit_request_log():
    """reddit.py request-failure log must not include the raw params dict."""
    src = _read("app/services/product/reddit.py")
    assert 'params=%s", response.status_code, path, params' not in src, (
        "raw request params must not be logged"
    )


def test_no_post_title_excerpt_in_platform_scanner_log():
    """platform_scanner must log platform/post_id/score, not a title/body excerpt."""
    src = _read("app/services/product/platform_scanner.py")
    assert "(post.title or post.body)[:50]" not in src
    assert "Post '%s' scored" not in src  # the old f-string template is gone


def test_no_raw_email_in_email_service_logs():
    """email_service must mask recipients in every log line."""
    src = _read("app/services/product/email_service.py")
    # Every logger.* call that names a recipient must go through _mask_email.
    assert "f\"Email not sent to {to_email}" not in src
    assert "f\"Email sent to {to_email}" not in src
    assert "f\"Failed to send email to {to_email}" not in src
    # And the masked helper is actually used.
    assert "_mask_email(to_email)" in src


# --- defense-in-depth: processor still scrubs any residual secret -----------

def test_processor_scrubs_residual_secret():
    """Even if a stray secret slips into a string field, the processor redacts it."""
    buf = _capture(_settings(log_format="json"))
    structlog.get_logger("test.residual").info(
        "debug", url="https://api.example.com?token=eyJhbGciOiJIUzI1NiJ9.supersecretvalue"
    )
    obj = json.loads(buf.getvalue().strip())
    # The long opaque token blob is redacted; the host is preserved.
    assert "[REDACTED]" in obj["url"]
    assert "supersecretvalue" not in obj["url"]


# --- regression: UUID identifiers must survive redaction ---------------------
# A full hyphenated UUID (request_id / session_id) is an identifier, not a
# secret. The 32+ char blob heuristic MUST NOT redact it, or every correlation
# id in production logs becomes "[REDACTED]" and debugging is impossible.

def test_processor_preserves_uuid_identifiers():
    buf = _capture(_settings(log_format="json"))
    rid = "ff55297b-c534-4eed-ac1a-b77de353fd91"
    structlog.get_logger("test.uuid").info("ok", request_id=rid, session_id=rid)
    obj = json.loads(buf.getvalue().strip())
    assert obj["request_id"] == rid, "UUID request_id must survive redaction"
    assert obj["session_id"] == rid, "UUID session_id must survive redaction"


def test_processor_still_redacts_bare_hex_blob():
    """A bare 40-char hex blob (NOT a UUID) is still redacted — the UUID
    exemption must not weaken secret scrubbing."""
    buf = _capture(_settings(log_format="json"))
    secret = "deadbeef" * 5  # 40 hex chars, no hyphens
    structlog.get_logger("test.blob").info("debug", value=secret)
    obj = json.loads(buf.getvalue().strip())
    assert obj["value"] == "[REDACTED]"


def test_processor_scrubs_full_jwt():
    """A Supabase-style JWT (three dot-separated base64url segments) is fully
    redacted — not just the signature segment, because the header+payload
    decode to credential info (alg, sub, etc.)."""
    buf = _capture(_settings(log_format="json"))
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    structlog.get_logger("test.jwt").info("debug", value=jwt)
    obj = json.loads(buf.getvalue().strip())
    assert obj["value"] == "[REDACTED]", f"full JWT must be redacted, got: {obj['value'][:60]}"


def test_processor_redacts_nested_structures():
    """Secrets inside nested dicts and lists must be scrubbed, not just top-level strings."""
    buf = _capture(_settings(log_format="json"))
    structlog.get_logger("test.nested").info(
        "debug",
        metadata={"api_key": "sk-deadbeef12345678901234567890ab", "name": "safe"},
        tags=["Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJ", "ok"],
    )
    obj = json.loads(buf.getvalue().strip())
    # Nested dict: secret string value is redacted, safe value preserved.
    assert obj["metadata"]["api_key"] == "[REDACTED]"
    assert obj["metadata"]["name"] == "safe"
    # Nested list: Bearer token is redacted, plain string preserved.
    assert obj["tags"][0] == "[REDACTED]"
    assert obj["tags"][1] == "ok"
