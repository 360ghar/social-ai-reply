"""Unit tests for security module — slugify, webhook validation.

Password hashing and JWT tests have been removed as authentication
is now handled by Supabase Auth. See tests/unit/test_supabase_auth.py
for Supabase-related tests.
"""

import socket
from unittest.mock import patch

import pytest

from app.services.product.security import (
    slugify,
    validate_webhook_url,
)

# Deterministic DNS result for tests — avoids real network lookups.
_EXAMPLE_COM_ADDRINFO = [
    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.215.14", 0)),
]


class TestSlugify:
    def test_basic_slug(self):
        result = slugify("Hello World")
        assert "hello" in result
        assert "world" in result

    def test_special_characters_removed(self):
        result = slugify("Foo & Bar!!!")
        assert "&" not in result

    def test_empty_string_returns_default(self):
        result = slugify("")
        assert result == "workspace"


class TestWebhookValidation:
    @patch("app.services.product.security.socket.getaddrinfo", return_value=_EXAMPLE_COM_ADDRINFO)
    def test_valid_external_url_passes(self, _mock_dns):
        validate_webhook_url("https://example.com/webhook")

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            validate_webhook_url("not-a-url")

    def test_empty_url_raises(self):
        with pytest.raises(ValueError):
            validate_webhook_url("")

    @patch(
        "app.services.product.security.socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))],
    )
    def test_internal_url_blocked(self, _mock_dns):
        with pytest.raises(ValueError):
            validate_webhook_url("http://localhost:9000/hook")
