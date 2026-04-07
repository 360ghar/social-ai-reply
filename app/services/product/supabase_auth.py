"""Supabase Auth service — handles all communication with Supabase Auth API.

This module is the single point of integration between RedditFlow and Supabase Auth.
FastAPI remains the backend for business logic; Supabase handles identity only.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

import httpx
import jwt
from jwt import PyJWK

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ── JWKS cache (thread-safe, refreshed on key-miss) ─────────────

_jwks_cache: dict[str, PyJWK] = {}
_jwks_lock = threading.Lock()

# ── Data classes ─────────────────────────────────────────────────


@dataclass
class SupabaseUser:
    """Minimal representation of a Supabase auth user."""

    id: str  # Supabase UUID
    email: str
    email_confirmed_at: str | None = None
    full_name: str | None = None


# ── JWT verification (used by FastAPI dependencies) ──────────────


def _fetch_jwks() -> dict[str, PyJWK]:
    """Fetch the JSON Web Key Set from Supabase and return a kid→PyJWK map."""
    settings = get_settings()
    resp = httpx.get(
        f"{settings.supabase_url}/auth/v1/.well-known/jwks.json",
        headers={"apikey": settings.supabase_anon_key},
        timeout=10,
    )
    resp.raise_for_status()
    keys = {}
    for key_data in resp.json().get("keys", []):
        kid = key_data.get("kid")
        if kid:
            keys[kid] = PyJWK(key_data)
    return keys


def _get_signing_key(kid: str) -> PyJWK:
    """Look up a signing key by kid, refreshing the JWKS cache if needed."""
    global _jwks_cache
    with _jwks_lock:
        if kid in _jwks_cache:
            return _jwks_cache[kid]
        # Key not found — refresh cache
        _jwks_cache = _fetch_jwks()
        if kid in _jwks_cache:
            return _jwks_cache[kid]
    raise ValueError(f"Signing key '{kid}' not found in Supabase JWKS.")


def verify_supabase_jwt(token: str) -> dict:
    """Decode and verify a Supabase-issued JWT.

    Fetches the public key from Supabase's JWKS endpoint to verify
    ES256-signed tokens. Falls back to HS256 with the JWT secret
    for backwards compatibility.
    Returns the decoded payload dict on success, raises on failure.
    """
    settings = get_settings()

    # Peek at the token header to determine algorithm and key
    try:
        header = jwt.get_unverified_header(token)
    except jwt.DecodeError as exc:
        raise jwt.InvalidTokenError("Malformed token header.") from exc

    alg = header.get("alg", "HS256")
    kid = header.get("kid")

    if alg == "HS256":
        # Legacy / simple Supabase setup: symmetric HMAC
        secret = settings.supabase_jwt_secret
        if not secret:
            raise ValueError("SUPABASE_JWT_SECRET is not configured.")
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"require": ["sub", "exp", "aud"]},
        )

    # Asymmetric (ES256, RS256, etc.) — use JWKS public key
    if not kid:
        raise jwt.InvalidTokenError("Token missing 'kid' header for asymmetric verification.")
    if not settings.supabase_url:
        raise ValueError("SUPABASE_URL is not configured.")

    signing_key = _get_signing_key(kid)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=[alg],
        audience="authenticated",
        options={"require": ["sub", "exp", "aud"]},
    )


# ── Supabase Admin API helpers (server-side, uses service role key) ──


def _admin_headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }


def _auth_url(path: str) -> str:
    settings = get_settings()
    return f"{settings.supabase_url}/auth/v1{path}"


def sign_up(email: str, password: str, full_name: str) -> dict:
    """Create a new user via Supabase Admin API and return session tokens.

    Uses the service-role admin endpoint to create a pre-confirmed user,
    then signs them in immediately to get access/refresh tokens.
    This avoids the email-confirmation-required issue with the public signup.
    """
    # Step 1: Create confirmed user via admin API
    resp = httpx.post(
        _auth_url("/admin/users"),
        headers=_admin_headers(),
        json={
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"full_name": full_name},
        },
        timeout=15,
    )
    data = resp.json()
    if resp.status_code >= 400:
        msg = data.get("msg") or data.get("message") or data.get("error_description") or str(data)
        raise SupabaseAuthError(resp.status_code, msg)

    user_data = data  # Admin API returns the user object directly

    # Step 2: Sign in to get access + refresh tokens
    try:
        session_data = sign_in_with_password(email, password)
    except SupabaseAuthError as exc:
        # Avoid leaving behind a half-created Supabase account that the app
        # cannot establish a usable session for.
        admin_delete_user(user_data["id"])
        raise SupabaseAuthError(exc.status_code, exc.message) from exc

    # Merge user info into session response
    session_data["user"] = user_data
    return session_data


def sign_in_with_password(email: str, password: str) -> dict:
    """Authenticate an existing user via email + password.

    Returns session with access_token, refresh_token, user, etc.
    """
    settings = get_settings()
    resp = httpx.post(
        _auth_url("/token?grant_type=password"),
        headers={
            "apikey": settings.supabase_anon_key,
            "Content-Type": "application/json",
        },
        json={"email": email, "password": password},
        timeout=15,
    )
    data = resp.json()
    if resp.status_code >= 400:
        msg = data.get("error_description") or data.get("msg") or data.get("message") or str(data)
        raise SupabaseAuthError(resp.status_code, msg)
    return data


def sign_out(access_token: str) -> None:
    """Invalidate a user's session on Supabase side.

    Raises SupabaseAuthError if Supabase returns an error response,
    so callers can decide whether to treat sign-out failure as critical.
    """
    settings = get_settings()
    resp = httpx.post(
        _auth_url("/logout"),
        headers={
            "apikey": settings.supabase_anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )
    if resp.status_code >= 400:
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        msg = data.get("error_description") or data.get("msg") or data.get("message") or f"Logout failed ({resp.status_code})"
        logger.warning("Supabase sign_out failed: %s %s", resp.status_code, msg)
        raise SupabaseAuthError(resp.status_code, msg)


def reset_password_for_email(email: str) -> None:
    """Send a password reset email via Supabase.

    Supabase handles token generation, email delivery, and the reset flow.
    """
    settings = get_settings()
    redirect_url = f"{settings.frontend_url}/reset-password"
    resp = httpx.post(
        _auth_url("/recover"),
        headers={
            "apikey": settings.supabase_anon_key,
            "Content-Type": "application/json",
        },
        json={"email": email, "redirect_to": redirect_url},
        timeout=15,
    )
    if resp.status_code >= 400:
        # Don't reveal whether the email exists — just log server-side
        logger.warning("Supabase password reset request failed: %s", resp.text)


def update_user_password(access_token: str, new_password: str) -> dict:
    """Update the authenticated user's password using their access token.

    Used after Supabase redirects the user back with a valid session.
    """
    settings = get_settings()
    resp = httpx.put(
        _auth_url("/user"),
        headers={
            "apikey": settings.supabase_anon_key,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={"password": new_password},
        timeout=15,
    )
    data = resp.json()
    if resp.status_code >= 400:
        msg = data.get("msg") or data.get("message") or str(data)
        raise SupabaseAuthError(resp.status_code, msg)
    return data


def get_user_by_token(access_token: str) -> dict:
    """Fetch the current user's profile from Supabase using their access token."""
    settings = get_settings()
    resp = httpx.get(
        _auth_url("/user"),
        headers={
            "apikey": settings.supabase_anon_key,
            "Authorization": f"Bearer {access_token}",
        },
        timeout=10,
    )
    data = resp.json()
    if resp.status_code >= 400:
        msg = data.get("msg") or data.get("message") or str(data)
        raise SupabaseAuthError(resp.status_code, msg)
    return data


def admin_get_user(supabase_user_id: str) -> dict:
    """Fetch a user by ID using the admin/service-role API."""
    resp = httpx.get(
        _auth_url(f"/admin/users/{supabase_user_id}"),
        headers=_admin_headers(),
        timeout=10,
    )
    data = resp.json()
    if resp.status_code >= 400:
        msg = data.get("msg") or data.get("message") or str(data)
        raise SupabaseAuthError(resp.status_code, msg)
    return data


def admin_delete_user(supabase_user_id: str) -> None:
    """Delete a user via the admin API (used for workspace deletion cleanup)."""
    resp = httpx.delete(
        _auth_url(f"/admin/users/{supabase_user_id}"),
        headers=_admin_headers(),
        timeout=10,
    )
    if resp.status_code >= 400:
        logger.warning("Failed to delete Supabase user %s: %s", supabase_user_id, resp.text)


def refresh_session(refresh_token: str) -> dict:
    """Exchange a refresh token for a new access token."""
    settings = get_settings()
    resp = httpx.post(
        _auth_url("/token?grant_type=refresh_token"),
        headers={
            "apikey": settings.supabase_anon_key,
            "Content-Type": "application/json",
        },
        json={"refresh_token": refresh_token},
        timeout=15,
    )
    data = resp.json()
    if resp.status_code >= 400:
        msg = data.get("error_description") or data.get("msg") or str(data)
        raise SupabaseAuthError(resp.status_code, msg)
    return data


# ── Helpers ──────────────────────────────────────────────────────


def extract_user_from_response(data: dict) -> SupabaseUser:
    """Extract a SupabaseUser from a Supabase auth response (sign_up or sign_in)."""
    user_data = data.get("user", data)
    metadata = user_data.get("user_metadata", {})
    return SupabaseUser(
        id=user_data["id"],
        email=user_data.get("email", ""),
        email_confirmed_at=user_data.get("email_confirmed_at"),
        full_name=metadata.get("full_name"),
    )


# ── Exceptions ───────────────────────────────────────────────────


class SupabaseAuthError(Exception):
    """Raised when a Supabase Auth API call fails."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Supabase Auth error ({status_code}): {message}")
