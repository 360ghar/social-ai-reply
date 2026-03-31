"""Unit tests for security module — JWT, password hashing, slugify, webhook validation."""
import pytest

from app.services.product.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    slugify,
    validate_webhook_url,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify_success(self):
        pw = "SuperSecret123!"
        hashed = hash_password(pw)
        assert hashed != pw
        assert verify_password(pw, hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_different_hashes_for_same_password(self):
        pw = "same-password"
        h1 = hash_password(pw)
        h2 = hash_password(pw)
        assert h1 != h2


class TestAccessToken:
    def test_create_and_decode_token(self):
        token = create_access_token(user_id=42, email="test@example.com")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_token_contains_user_id(self):
        token = create_access_token(user_id=99, email="test@example.com")
        payload = decode_access_token(token)
        assert payload["sub"] == "99"

    def test_invalid_token_raises(self):
        with pytest.raises(Exception):
            decode_access_token("invalid-token")


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
        # Use a public URL — internal/private IPs are blocked
        validate_webhook_url("https://example.com/webhook")  # no exception

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            validate_webhook_url("not-a-url")

    def test_empty_url_raises(self):
        with pytest.raises(ValueError):
            validate_webhook_url("")

    def test_internal_url_blocked(self):
        with pytest.raises(ValueError):
            validate_webhook_url("http://localhost:9000/hook")
