"""Unit tests for the Supabase auth service module."""

from unittest.mock import MagicMock, patch

import jwt
import pytest

import app.services.product.supabase_auth as supabase_auth
from app.core.constants.timeouts import JWKS_CACHE_TTL, JWKS_REFRESH_COOLDOWN
from app.services.product.supabase_auth import (
    SupabaseAuthError,
    _get_signing_key,
    admin_delete_user,
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


class TestJwksCache:
    @pytest.fixture(autouse=True)
    def _reset_cache(self):
        supabase_auth._jwks_cache = {}
        supabase_auth._jwks_fetched_at = 0.0
        yield
        supabase_auth._jwks_cache = {}
        supabase_auth._jwks_fetched_at = 0.0

    def test_cached_key_returned_without_refetch(self):
        key = MagicMock()
        with (
            patch.object(supabase_auth, "_fetch_jwks", return_value={"kid-1": key}) as mock_fetch,
            patch.object(supabase_auth.time, "monotonic", return_value=1000.0),
        ):
            assert _get_signing_key("kid-1") is key
            assert _get_signing_key("kid-1") is key
            assert mock_fetch.call_count == 1

    def test_refetches_after_ttl_expiry(self):
        old_key, new_key = MagicMock(), MagicMock()
        clock = [1000.0]
        with (
            patch.object(supabase_auth, "_fetch_jwks", side_effect=[{"kid-1": old_key}, {"kid-1": new_key}]) as mock_fetch,
            patch.object(supabase_auth.time, "monotonic", side_effect=lambda: clock[0]),
        ):
            assert _get_signing_key("kid-1") is old_key
            clock[0] += JWKS_CACHE_TTL + 1
            assert _get_signing_key("kid-1") is new_key
            assert mock_fetch.call_count == 2

    def test_unknown_kid_refresh_respects_cooldown(self):
        key = MagicMock()
        clock = [1000.0]
        with (
            patch.object(supabase_auth, "_fetch_jwks", return_value={"kid-1": key}) as mock_fetch,
            patch.object(supabase_auth.time, "monotonic", side_effect=lambda: clock[0]),
        ):
            _get_signing_key("kid-1")
            # Within cooldown: an unknown kid must not trigger another fetch.
            clock[0] += JWKS_REFRESH_COOLDOWN / 2
            with pytest.raises(ValueError, match="not found"):
                _get_signing_key("kid-unknown")
            assert mock_fetch.call_count == 1
            # After cooldown the refresh is allowed again.
            clock[0] += JWKS_REFRESH_COOLDOWN
            with pytest.raises(ValueError, match="not found"):
                _get_signing_key("kid-unknown")
            assert mock_fetch.call_count == 2


class TestSupabaseAuthError:
    def test_error_attributes(self):
        err = SupabaseAuthError(400, "Bad request")
        assert err.status_code == 400
        assert err.message == "Bad request"
        assert "400" in str(err)
        assert "Bad request" in str(err)


class TestAdminDeleteUser:
    @patch("app.services.product.supabase_auth.httpx.delete")
    @patch(
        "app.services.product.supabase_auth._admin_headers",
        side_effect=SupabaseAuthError(503, "Missing service role key"),
    )
    def test_admin_delete_user_treats_missing_admin_auth_as_best_effort(self, _mock_headers, mock_delete):
        admin_delete_user("user-123")
        mock_delete.assert_not_called()
