"""Unit tests for the Supabase auth service module."""

from unittest.mock import MagicMock, patch

import jwt
import pytest

from app.services.product.supabase_auth import (
    SupabaseAuthError,
    extract_user_from_response,
    verify_supabase_jwt,
)


class TestExtractUserFromResponse:
    def test_extracts_user_from_signup_response(self):
        data = {
            "access_token": "token-123",
            "user": {
                "id": "uuid-abc",
                "email": "test@example.com",
                "email_confirmed_at": "2025-01-01T00:00:00Z",
                "user_metadata": {"full_name": "Test User"},
            },
        }
        user = extract_user_from_response(data)
        assert user.id == "uuid-abc"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.email_confirmed_at == "2025-01-01T00:00:00Z"

    def test_extracts_user_from_flat_response(self):
        data = {
            "id": "uuid-xyz",
            "email": "flat@example.com",
            "user_metadata": {},
        }
        user = extract_user_from_response(data)
        assert user.id == "uuid-xyz"
        assert user.email == "flat@example.com"
        assert user.full_name is None


class TestVerifySupabaseJwt:
    def test_raises_when_no_secret_configured(self):
        token = jwt.encode(
            {"sub": "user-123", "aud": "authenticated", "exp": 9999999999},
            "placeholder-secret-with-32-bytes-minimum",
            algorithm="HS256",
        )
        with patch("app.services.product.supabase_auth.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(supabase_jwt_secret="")
            with pytest.raises(ValueError, match="SUPABASE_JWT_SECRET is not configured"):
                verify_supabase_jwt(token)

    def test_raises_on_invalid_token(self):
        with patch("app.services.product.supabase_auth.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(supabase_jwt_secret="test-secret-32-chars-min-ok-here")
            with pytest.raises(jwt.PyJWTError):
                verify_supabase_jwt("invalid-token")


class TestSupabaseAuthError:
    def test_error_attributes(self):
        err = SupabaseAuthError(400, "Bad request")
        assert err.status_code == 400
        assert err.message == "Bad request"
        assert "400" in str(err)
        assert "Bad request" in str(err)
