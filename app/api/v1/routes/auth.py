"""Authentication routes — all identity operations delegate to Supabase Auth.

FastAPI handles business logic (workspace creation, profile records, entitlements)
while Supabase handles credentials, sessions, password resets, and email verification.
"""

import hashlib
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    bearer_scheme,
    ensure_default_project,
    get_current_user,
    get_current_workspace,
    workspace_summary,
)
from app.db.models import (
    AccountUser,
    Membership,
    MembershipRole,
    Workspace,
)
from app.db.session import get_db
from app.schemas.v1.auth import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResponse,
    ForgotPasswordRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    UserResponse,
)
from app.services.product.entitlements import get_or_create_subscription, seed_plan_entitlements
from app.services.product.supabase_auth import (
    SupabaseAuthError,
    admin_delete_user,
    extract_user_from_response,
    refresh_session,
    reset_password_for_email,
    sign_in_with_password,
    sign_out,
    sign_up,
    update_user_password,
)
from app.utils.datetime import utc_now
from app.utils.slug import unique_slug as _unique_slug

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["auth"])


def _legacy_password_placeholder() -> str:
    """Populate legacy DB schemas that still require a non-null password hash."""
    return f"supabase-managed:{secrets.token_hex(32)}"


def _workspace_for_user(db: Session, user_id: int) -> Workspace | None:
    return db.scalar(select(Workspace).join(Membership).where(Membership.user_id == user_id).order_by(Workspace.id.asc()))


def _legacy_user_by_email(db: Session, email: str) -> AccountUser | None:
    return db.scalar(
        select(AccountUser).where(
            AccountUser.email == email,
            AccountUser.supabase_user_id.is_(None),
            AccountUser.is_active.is_(True),
        )
    )


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: AuthRegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Register a new user.

    1. Create the identity in Supabase Auth.
    2. Create a local AccountUser record linked by supabase_user_id.
    3. Create workspace, membership, subscription, and default project.
    4. Return Supabase session tokens + local user/workspace info.
    """
    email = payload.email.lower()

    # Short-circuit on ANY existing email — legacy users must use /auth/login
    # to link their account, which requires proving ownership via password.
    existing = db.scalar(select(AccountUser).where(AccountUser.email == email))
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Email already registered. Please sign in to link your account.",
        )

    # Create user in Supabase
    try:
        supabase_data = sign_up(email, payload.password, payload.full_name.strip())
    except SupabaseAuthError as exc:
        if exc.status_code == 422 or "already registered" in exc.message.lower():
            raise HTTPException(status_code=409, detail="Email already registered.") from exc
        logger.error("Supabase sign_up failed: %s", exc)
        raise HTTPException(status_code=502, detail="Authentication service error.") from exc

    sb_user = extract_user_from_response(supabase_data)
    access_token = supabase_data.get("access_token", "")
    refresh_token = supabase_data.get("refresh_token")

    # Create local user + workspace. If anything fails, clean up the
    # Supabase user so we don't leave an orphaned remote identity.
    try:
        user = AccountUser(
            supabase_user_id=sb_user.id,
            email=email,
            password_hash=_legacy_password_placeholder(),
            full_name=payload.full_name.strip(),
        )
        db.add(user)
        db.flush()

        workspace = Workspace(
            name=payload.workspace_name.strip(),
            slug=_unique_slug(db, Workspace, payload.workspace_name),
            owner_user_id=user.id,
        )
        db.add(workspace)
        db.flush()
        db.add(Membership(workspace_id=workspace.id, user_id=user.id, role=MembershipRole.OWNER))

        # Provision entitlements, subscription, and default project BEFORE
        # committing so a failure rolls back the entire registration atomically.
        seed_plan_entitlements(db)
        get_or_create_subscription(db, workspace)
        ensure_default_project(db, workspace)
        db.commit()
    except Exception:
        db.rollback()
        try:
            admin_delete_user(sb_user.id)
        except Exception:
            logger.error("Failed to clean up Supabase user %s after local provisioning failure", sb_user.id)
        raise

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
        workspace=workspace_summary(db, workspace, user.id),
    )


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: AuthLoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Sign in via Supabase Auth, return session tokens + local user/workspace."""
    email = payload.email.lower()

    try:
        supabase_data = sign_in_with_password(email, payload.password)
    except SupabaseAuthError as exc:
        if exc.status_code == 400:
            raise HTTPException(status_code=401, detail="Invalid email or password.") from exc
        logger.error("Supabase sign_in failed: %s", exc)
        raise HTTPException(status_code=502, detail="Authentication service error.") from exc

    sb_user = extract_user_from_response(supabase_data)
    access_token = supabase_data.get("access_token", "")
    refresh_token = supabase_data.get("refresh_token")

    # Look up local user by Supabase ID (active users only)
    user = db.scalar(
        select(AccountUser).where(AccountUser.supabase_user_id == sb_user.id, AccountUser.is_active.is_(True))
    )
    if not user:
        user = _legacy_user_by_email(db, email)
        if user:
            user.supabase_user_id = sb_user.id
            if sb_user.full_name:
                user.full_name = sb_user.full_name
            if not user.password_hash:
                user.password_hash = _legacy_password_placeholder()
            db.add(user)
            db.commit()
            db.refresh(user)
    if not user:
        raise HTTPException(status_code=401, detail="User not found. Please register first.")

    workspace = _workspace_for_user(db, user.id)
    if not workspace:
        raise HTTPException(status_code=403, detail="User has no workspace.")

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
        workspace=workspace_summary(db, workspace, user.id),
    )


@router.get("/auth/me", response_model=AuthResponse)
def me(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Return the current user's profile and workspace.

    The access_token is echoed back (it's still valid since the dependency
    validated it). Frontend uses this to confirm session validity on mount.
    """
    # The frontend keeps its own Supabase token; we don't need to return it
    return AuthResponse(
        access_token="",  # Frontend keeps the Supabase token it already has
        user=UserResponse.model_validate(current_user),
        workspace=workspace_summary(db, workspace, current_user.id),
    )


@router.post("/auth/forgot-password")
def forgot_password(payload: ForgotPasswordRequest) -> dict:
    """Send a password reset email via Supabase.

    Always returns ok: true to avoid revealing whether the email exists.
    """
    reset_password_for_email(payload.email.lower())
    return {"ok": True}


@router.post("/auth/reset-password")
def reset_password_endpoint(payload: ResetPasswordRequest) -> dict:
    """Update the user's password using the Supabase access token.

    After Supabase redirects the user back with a session, the frontend
    sends the access_token + new password here. We call Supabase to update.
    """
    try:
        update_user_password(payload.access_token, payload.password)
    except SupabaseAuthError as exc:
        raise HTTPException(status_code=400, detail="Could not reset password. Link may have expired.") from exc
    return {"ok": True, "message": "Password updated. You can now log in."}


@router.post("/auth/refresh")
def refresh_token_endpoint(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Exchange a Supabase refresh token for a new access token."""
    try:
        supabase_data = refresh_session(payload.refresh_token)
    except SupabaseAuthError as exc:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.") from exc

    sb_user = extract_user_from_response(supabase_data)
    user = db.scalar(
        select(AccountUser).where(AccountUser.supabase_user_id == sb_user.id, AccountUser.is_active.is_(True))
    )
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")

    workspace = db.scalar(
        select(Workspace).join(Membership).where(Membership.user_id == user.id).order_by(Workspace.id.asc())
    )
    if not workspace:
        raise HTTPException(status_code=403, detail="User has no workspace.")

    return AuthResponse(
        access_token=supabase_data.get("access_token", ""),
        refresh_token=supabase_data.get("refresh_token"),
        user=UserResponse.model_validate(user),
        workspace=workspace_summary(db, workspace, user.id),
    )


@router.post("/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    current_user: AccountUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Sign out — invalidate the session on Supabase side.

    The frontend should also clear its local storage.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required.")

    raw_token = credentials.credentials
    current_user.tokens_invalid_before = utc_now().replace(microsecond=0)
    current_user.revoked_access_token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    db.add(current_user)
    db.commit()

    try:
        sign_out(raw_token)
    except SupabaseAuthError:
        logger.warning("Supabase sign_out failed for user %s", current_user.id, exc_info=True)
        return {"ok": True, "warning": "Local session revoked but remote sign-out failed."}
    except Exception as exc:
        logger.error("Unexpected error during sign_out for user %s", current_user.id, exc_info=True)
        raise HTTPException(status_code=502, detail="Remote sign-out failed.") from exc

    return {"ok": True}
