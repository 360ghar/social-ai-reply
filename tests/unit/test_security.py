"""Unit tests for security module — slugify, webhook validation.

Password hashing and JWT tests have been removed as authentication
is now handled by Supabase Auth. See tests/unit/test_supabase_auth.py
for Supabase-related tests.
"""

import pytest

from app.services.product.security import (
    slugify,
    validate_webhook_url,
)


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
    def test_valid_external_url_passes(self):
        validate_webhook_url("https://example.com/webhook")

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            validate_webhook_url("not-a-url")

    def test_empty_url_raises(self):
        with pytest.raises(ValueError):
            validate_webhook_url("")

    def test_internal_url_blocked(self):
        with pytest.raises(ValueError):
            validate_webhook_url("http://localhost:9000/hook")
