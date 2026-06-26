"""Tests for the structlog-based logging configuration (WS1).

These tests configure logging into an in-memory ``io.StringIO`` handler and
assert:

1. prod (JSON) renderer emits one JSON object per line with bound contextvars
   AND arbitrary custom key/value fields (the HARD REQUIREMENT that the old
   hand-rolled formatter violated).
2. dev (Console) renderer contains the event text.
3. contextvars stamped via ``app.core.log_context`` appear on plain stdlib
   ``logging.getLogger().info(...)`` output (proves legacy calls are upgraded
   for free).
4. the redaction processor scrubs Bearer tokens and long base64/hex blobs.

Each test re-runs ``setup_logging`` against a fresh buffer so there is no
cross-test pollution, and a finalizer restores structlog/logging defaults.
"""

from __future__ import annotations

import io
import json
import logging
from types import SimpleNamespace

import pytest
import structlog

from app.core.log_context import bind_request_context, clear_request_context, request_log_scope
from app.core.logging import setup_logging


def _settings(log_format: str = "json", environment: str = "production", level: str = "DEBUG"):
    """Build a lightweight Settings-like object without triggering env validation."""
    return SimpleNamespace(
        log_format=log_format,
        environment=environment,
        log_level=level,
    )


def _capture(settings) -> io.StringIO:
    """Configure logging and route the root handler into a fresh StringIO buffer."""
    buf = io.StringIO()
    setup_logging(settings)
    root = logging.getLogger()
    for h in root.handlers:
        h.stream = buf
    return buf


@pytest.fixture(autouse=True)
def _reset_structlog():
    """Ensure each test starts with clean contextvars and ends with a clean slate."""
    clear_request_context()
    yield
    clear_request_context()
    # Reset structlog config so a stale wrapper_class can't leak into other tests.
    structlog.reset_defaults()


def test_prod_json_renders_contextvars_and_custom_kv():
    """JSON renderer: request_id (contextvar) + arbitrary custom kv survive."""
    buf = _capture(_settings(log_format="json"))
    bind_request_context("req-json-1")
    try:
        structlog.get_logger("test.json").info(
            "json_event", correlation_id="corr-9", user_id=42
        )
    finally:
        clear_request_context()

    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    assert len(lines) == 1, f"expected exactly one JSON line, got {lines!r}"
    obj = json.loads(lines[0])

    # Core fields
    assert obj["event"] == "json_event"
    assert obj["level"] == "info"
    assert "timestamp" in obj and obj["timestamp"]
    # Contextvar stamped
    assert obj["request_id"] == "req-json-1"
    # HARD REQUIREMENT: arbitrary custom kv are top-level keys (not dropped)
    assert obj["correlation_id"] == "corr-9"
    assert obj["user_id"] == 42


def test_dev_console_renders_event_text():
    """Console renderer: the human-readable event text is present (ANSI ok)."""
    buf = _capture(_settings(log_format="console", environment="development"))
    structlog.get_logger("test.console").info("console_event_text", extra_kv="visible")
    text = buf.getvalue()
    assert "console_event_text" in text
    # ConsoleRenderer shows extra kv fields by default too
    assert "extra_kv" in text


def test_stdlib_calls_inherit_contextvars():
    """A plain stdlib logger.info picks up bound request_id — legacy calls upgraded for free."""
    buf = _capture(_settings(log_format="json"))
    bind_request_context("req-stdlib-7")
    try:
        logging.getLogger("some.legacy.module").info("stdlib legacy message")
    finally:
        clear_request_context()

    obj = json.loads(buf.getvalue().strip())
    assert obj["event"] == "stdlib legacy message"
    assert obj["request_id"] == "req-stdlib-7"
    assert obj["level"] == "info"


def test_redaction_scrubs_bearer_and_blobs():
    """Redaction processor scrubs Authorization/Bearer and long base64 blobs."""
    buf = _capture(_settings(log_format="json"))
    long_blob = "dGhpcyBpcyBhIHZlcnkgbG9uZyBiYXNlNjQgYmxvYiBzdHJpbmc"  # > 32 chars
    logging.getLogger("test.redact").info(
        "Auth header Authorization: Bearer eyJhbGciOiJIUzI1NiJ9 and blob " + long_blob
    )
    line = buf.getvalue().strip()
    obj = json.loads(line)
    msg = obj["event"]
    assert "[REDACTED]" in msg
    assert "Bearer eyJ" not in msg
    assert long_blob not in msg


def test_redaction_preserves_typed_fields():
    """Redaction must NOT touch int/float/bool/None values."""
    buf = _capture(_settings(log_format="json"))
    structlog.get_logger("test.types").info(
        "typed_event", count=42, ratio=3.14, flag=True, nothing=None, name="ok"
    )
    obj = json.loads(buf.getvalue().strip())
    assert obj["count"] == 42
    assert obj["ratio"] == 3.14
    assert obj["flag"] is True
    assert obj["nothing"] is None
    assert obj["name"] == "ok"


def test_request_log_scope_contextmanager_clears_on_exit():
    """request_log_scope binds context then clears it, even across exceptions."""
    buf = _capture(_settings(log_format="json"))
    with request_log_scope(request_id="req-scope-1"):
        logging.getLogger("test.scope").info("inside scope")
    # After exit, a fresh log line carries no request_id
    logging.getLogger("test.scope").info("outside scope")

    lines = [json.loads(ln) for ln in buf.getvalue().splitlines() if ln.strip()]
    inside, outside = lines
    assert inside["request_id"] == "req-scope-1"
    assert "request_id" not in outside


def test_request_log_scope_clears_on_exception():
    """Context is cleared even when the body raises."""
    buf = _capture(_settings(log_format="json"))
    with pytest.raises(RuntimeError), request_log_scope(request_id="req-exc"):
        raise RuntimeError("boom")
    logging.getLogger("test.exc").info("after exception")
    obj = json.loads(buf.getvalue().strip())
    assert "request_id" not in obj
