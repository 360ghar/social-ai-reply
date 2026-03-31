import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import ensure_workspace_membership, get_current_user, get_current_workspace
from app.db.models import (
    AccountUser,
    Invitation,
    Membership,
    MembershipRole,
    Workspace,
)
from app.db.session import get_db
from app.schemas.v1.product import InvitationRequest, InvitationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["invitations"])


@router.get("/invitations", response_model=list[InvitationResponse])
def list_invitations(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[InvitationResponse]:
    membership = ensure_workspace_membership(db, workspace.id, current_user.id)
    if membership.role == MembershipRole.MEMBER:
        raise HTTPException(status_code=403, detail="Only admins can manage invitations.")
    rows = db.scalars(select(Invitation).where(Invitation.workspace_id == workspace.id).order_by(Invitation.created_at.desc())).all()
    return [InvitationResponse.model_validate(row) for row in rows]


@router.post("/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: InvitationRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> InvitationResponse:
    membership = ensure_workspace_membership(db, workspace.id, current_user.id)
    if membership.role == MembershipRole.MEMBER:
        raise HTTPException(status_code=403, detail="Only admins can invite teammates.")

    # Check if email is already a workspace member
    target_user = db.scalar(select(AccountUser).where(AccountUser.email == payload.email.lower()))
    if target_user:
        existing_member = db.scalar(
            select(Membership).where(
                Membership.workspace_id == workspace.id,
                Membership.user_id == target_user.id,
            )
        )
        if existing_member:
            raise HTTPException(status_code=409, detail="User is already a member of this workspace.")

    # Check for pending invitation
    pending = db.scalar(
        select(Invitation).where(
            Invitation.workspace_id == workspace.id,
            Invitation.email == payload.email.lower(),
            Invitation.accepted_at.is_(None),
            Invitation.expires_at > datetime.now(timezone.utc),
        )
    )
    if pending:
        raise HTTPException(status_code=409, detail="A pending invitation already exists for this email.")

    invitation = Invitation(
        workspace_id=workspace.id,
        email=payload.email.lower(),
        role=MembershipRole(payload.role),
        invited_by_user_id=current_user.id,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return InvitationResponse.model_validate(invitation)


@router.post("/invitations/accept/{token}", response_model=InvitationResponse)
def accept_invitation(
    token: str,
    current_user: AccountUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvitationResponse:
    invitation = db.scalar(select(Invitation).where(Invitation.token == token))
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found.")
    if invitation.accepted_at:
        raise HTTPException(status_code=400, detail="Invitation already accepted.")
    if invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Invitation has expired.")
    if invitation.email != current_user.email:
        raise HTTPException(status_code=403, detail="Invitation email does not match the current user.")
    existing = db.scalar(
        select(Membership).where(Membership.workspace_id == invitation.workspace_id, Membership.user_id == current_user.id)
    )
    if not existing:
        db.add(Membership(workspace_id=invitation.workspace_id, user_id=current_user.id, role=invitation.role))
    invitation.accepted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(invitation)
    return InvitationResponse.model_validate(invitation)
