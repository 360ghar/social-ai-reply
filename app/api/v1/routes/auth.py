"""Authentication routes — all identity operations delegate to Supabase Auth.

FastAPI handles business logic (workspace creation, profile records, entitlements)
while Supabase handles credentials, sessions, password resets, and email verification.
"""

import hashlib
import logging

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    _is_token_revoked,
    bearer_scheme,
    ensure_default_project,
    get_current_user,
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
    AuthRegisterRequest,
    AuthResponse,
    OAuthCompleteRequest,
    UserResponse,
)
from app.services.product.entitlements import get_or_create_subscription, seed_plan_entitlements
from app.services.product.supabase_auth import (
    SupabaseAuthError,
    admin_delete_user,
    extract_user_from_response,
    sign_out,
    sign_up,
    verify_supabase_jwt,
)
from app.utils.datetime import utc_now
from app.utils.slug import unique_slug as _unique_slug

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["auth"])


def _workspace_for_user(db: Session, user_id: int) -> Workspace | None:
    """Return the user's canonical (first-joined) workspace.

    Ordering by ``Membership.id`` matches ``deps.get_current_workspace`` so
    that ``/auth/me``, ``/auth/oauth-complete`` and every subsequent
    authenticated request agree on which workspace is the default tenant for
    a multi-workspace user.
    """
    membership = db.scalar(
        select(Membership)
        .where(Membership.user_id == user_id)
        .order_by(Membership.id.asc())
    )
    if membership is None:
        return None
    return db.scalar(select(Workspace).where(Workspace.id == membership.workspace_id))


def _verify_bearer(credentials: HTTPAuthorizationCredentials | None) -> tuple[str, dict]:
    """Verify the bearer token and return (raw_token, jwt_payload)."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    try:
        payload = verify_supabase_jwt(credentials.credentials)
    except (jwt.InvalidTokenError, jwt.DecodeError, jwt.ExpiredSignatureError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc
    except ValueError as exc:
        logger.error("JWT verification is misconfigured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable.",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error verifying JWT: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication service unavailable.") from exc
    return credentials.credentials, payload


def _provision_workspace(db: Session, user: AccountUser, workspace_name: str) -> Workspace:
    """Create workspace, membership, subscription, and default project for a user."""
    workspace = Workspace(
        name=workspace_name.strip(),
        slug=_unique_slug(db, Workspace, workspace_name),
        owner_user_id=user.id,
    )
    db.add(workspace)
    db.flush()
    db.add(Membership(workspace_id=workspace.id, user_id=user.id, role=MembershipRole.OWNER))
    seed_plan_entitlements(db)
    get_or_create_subscription(db, workspace)
    ensure_default_project(db, workspace)
    return workspace


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: AuthRegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Register a new user with email and password.

    1. Create the identity in Supabase Auth.
    2. Create a local AccountUser record linked by supabase_user_id.
    3. Create workspace, membership, subscription, and default project.
    4. Return Supabase session tokens + local user/workspace info.
    """
    email = payload.email.lower()

    existing = db.scalar(select(AccountUser).where(AccountUser.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

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

    try:
        user = AccountUser(
            supabase_user_id=sb_user.id,
            email=email,
            full_name=payload.full_name.strip(),
        )
        db.add(user)
        db.flush()

        workspace = _provision_workspace(db, user, payload.workspace_name)
        db.commit()
    except IntegrityError as exc:
        # Two concurrent registrations with the same email raced past the
        # pre-check. The Supabase identity we just minted is orphaned — clean
        # it up and surface 409 so the client sees a consistent error.
        db.rollback()
        try:
            admin_delete_user(sb_user.id)
        except Exception:
            logger.error("Failed to clean up Supabase user %s after integrity error", sb_user.id)
        raise HTTPException(status_code=409, detail="Email already registered.") from exc
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


@router.get("/auth/me", response_model=AuthResponse)
def me(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Return the current user's profile and workspace.

    Returns 404 if the user has no local account (e.g. first-time OAuth user
    needing workspace setup).
    """
    raw_token, payload = _verify_bearer(credentials)
    supabase_uid = payload["sub"]

    user = db.scalar(
        select(AccountUser).where(AccountUser.supabase_user_id == supabase_uid)
    )

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no_local_account")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="account_deactivated")

    if _is_token_revoked(user, payload, raw_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please sign in again.")

    workspace = _workspace_for_user(db, user.id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no workspace.")

    return AuthResponse(
        access_token="",
        user=UserResponse.model_validate(user),
        workspace=workspace_summary(db, workspace, user.id),
    )


@router.post("/auth/oauth-complete", response_model=AuthResponse)
def oauth_complete(
    payload: OAuthCompleteRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Complete OAuth registration by creating a local account and workspace.

    Called after a first-time OAuth user (e.g. Google sign-in) authenticates
    with Supabase but has no local AccountUser record yet.

    Idempotent: if called twice concurrently for the same Supabase user, the
    losing request catches ``IntegrityError``, rolls back, re-queries by
    ``supabase_user_id``, and returns the winning row with 200.
    """
    raw_token, jwt_payload = _verify_bearer(credentials)
    supabase_uid = jwt_payload["sub"]
    email = jwt_payload.get("email", "")
    metadata = jwt_payload.get("user_metadata") or {}
    full_name = (
        metadata.get("full_name")
        or metadata.get("name")
        or (email.split("@")[0] if email else "")
    )

    def _respond_existing(existing_user: AccountUser) -> JSONResponse:
        """Return the 200 response for a user that already has a local row.

        Validates the token against revocation, syncs an updated email from
        Supabase, and lazy-provisions a workspace for legacy rows missing
        one. Also invoked from the IntegrityError recovery path below.
        """
        if not existing_user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="account_deactivated")
        if _is_token_revoked(existing_user, jwt_payload, raw_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please sign in again.",
            )
        # Sync email if changed in Supabase (e.g. via account settings)
        if email and email != existing_user.email:
            conflict = db.scalar(
                select(AccountUser).where(
                    AccountUser.email == email,
                    AccountUser.id != existing_user.id,
                )
            )
            if conflict:
                raise HTTPException(status_code=409, detail="Email already registered.")
            existing_user.email = email
            db.add(existing_user)
            try:
                db.commit()
                db.refresh(existing_user)
            except IntegrityError as exc:
                # Concurrent sync raced us to the same email — rollback and
                # reload to pick up the committed value.
                db.rollback()
                db.refresh(existing_user)
                if existing_user.email != email:
                    raise HTTPException(
                        status_code=409,
                        detail="Email already registered.",
                    ) from exc
        workspace = _workspace_for_user(db, existing_user.id)
        if not workspace:
            workspace = _provision_workspace(db, existing_user, payload.workspace_name)
            db.commit()
        return JSONResponse(
            content=AuthResponse(
                access_token="",
                user=UserResponse.model_validate(existing_user),
                workspace=workspace_summary(db, workspace, existing_user.id),
            ).model_dump(),
            status_code=status.HTTP_200_OK,
        )

    # Return existing account if already provisioned
    existing = db.scalar(
        select(AccountUser).where(AccountUser.supabase_user_id == supabase_uid)
    )
    if existing:
        return _respond_existing(existing)

    # Provisioning path: require a usable email from the OAuth provider.
    # NOTE: this guard runs AFTER the existing-account lookup so a
    # previously-provisioned user whose provider later stopped returning an
    # email (e.g. GitHub making it private) can still sign in via the
    # existing-user path.
    if not email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="OAuth provider did not return an email address.",
        )

    # Fast-path: reject if email is already taken by a different account.
    # Also caught by the IntegrityError branch below — this just gives a
    # clearer error in the common case and avoids a wasted INSERT.
    email_taken = db.scalar(select(AccountUser).where(AccountUser.email == email))
    if email_taken:
        raise HTTPException(status_code=409, detail="Email already registered.")

    try:
        user = AccountUser(
            supabase_user_id=supabase_uid,
            email=email,
            full_name=full_name,
        )
        db.add(user)
        db.flush()
        workspace = _provision_workspace(db, user, payload.workspace_name)
        db.commit()
    except IntegrityError as exc:
        # Race: another request wrote the same supabase_user_id or email
        # between our pre-check and flush. Distinguish:
        #   (a) winner keyed by our supabase_uid -> idempotent 200
        #   (b) winner is a different Supabase identity with our email -> 409
        db.rollback()
        winner = db.scalar(
            select(AccountUser).where(AccountUser.supabase_user_id == supabase_uid)
        )
        if winner is not None:
            return _respond_existing(winner)
        raise HTTPException(status_code=409, detail="Email already registered.") from exc
    except Exception:
        db.rollback()
        raise

    return JSONResponse(
        content=AuthResponse(
            access_token="",
            user=UserResponse.model_validate(user),
            workspace=workspace_summary(db, workspace, user.id),
        ).model_dump(),
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    current_user: AccountUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Sign out — invalidate the session on Supabase side."""
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
