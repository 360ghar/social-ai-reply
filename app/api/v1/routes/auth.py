import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, get_current_workspace, workspace_summary
from app.db.models import (
    AccountUser,
    Membership,
    MembershipRole,
    PasswordResetToken,
    Workspace,
)
from app.db.session import get_db
from app.schemas.v1.auth import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResponse,
    UserResponse,
    WorkspaceSummary,
)
from app.services.product.entitlements import get_or_create_subscription, seed_plan_entitlements
from app.services.product.security import create_access_token, hash_password, verify_password
from app.utils.slug import unique_slug as _unique_slug

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["auth"])


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: AuthRegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    existing = db.scalar(select(AccountUser).where(AccountUser.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    user = AccountUser(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
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
    db.commit()
    seed_plan_entitlements(db)
    get_or_create_subscription(db, workspace)

    token = create_access_token(user.id, user.email)
    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
        workspace=workspace_summary(db, workspace, user.id),
    )


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: AuthLoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.scalar(select(AccountUser).where(AccountUser.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    workspace = db.scalar(
        select(Workspace).join(Membership).where(Membership.user_id == user.id).order_by(Workspace.id.asc())
    )
    if not workspace:
        raise HTTPException(status_code=403, detail="User has no workspace.")
    token = create_access_token(user.id, user.email)
    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
        workspace=workspace_summary(db, workspace, user.id),
    )


@router.get("/auth/me", response_model=AuthResponse)
def me(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> AuthResponse:
    token = create_access_token(current_user.id, current_user.email)
    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(current_user),
        workspace=workspace_summary(db, workspace, current_user.id),
    )


@router.post("/auth/forgot-password")
def forgot_password(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email", "").strip().lower()
    if not email:
        raise HTTPException(400, "Email is required.")
    user = db.scalar(select(AccountUser).where(AccountUser.email == email))
    if not user:
        return {"ok": True}  # Don't reveal if email exists
    token = secrets.token_urlsafe(48)
    expires = datetime.utcnow() + timedelta(hours=1)
    db.add(PasswordResetToken(user_id=user.id, token=token, expires_at=expires))
    db.commit()
    from app.services.product.email_service import EmailService
    EmailService.send_password_reset(user.email, token, user.full_name)
    return {"ok": True}


@router.post("/auth/reset-password")
def reset_password(payload: dict, db: Session = Depends(get_db)):
    token = payload.get("token", "")
    new_password = payload.get("password", "")
    if not token or len(new_password) < 8:
        raise HTTPException(400, "Token and password (min 8 chars) required.")
    reset = db.scalar(select(PasswordResetToken).where(
        PasswordResetToken.token == token,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > datetime.utcnow(),
    ))
    if not reset:
        raise HTTPException(400, "Invalid or expired reset link.")
    user = db.scalar(select(AccountUser).where(AccountUser.id == reset.user_id))
    user.password_hash = hash_password(new_password)
    reset.used_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "message": "Password updated. You can now log in."}
