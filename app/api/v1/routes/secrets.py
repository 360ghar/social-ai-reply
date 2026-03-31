"""Integration secrets CRUD endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import ensure_workspace_membership, get_current_user, get_current_workspace
from app.db.models import AccountUser, IntegrationSecret, Workspace
from app.db.session import get_db
from app.schemas.v1.product import SecretRequest, SecretResponse
from app.services.product.encryption import encrypt_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["secrets"])


@router.get("/secrets", response_model=list[SecretResponse])
def list_secrets(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[SecretResponse]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    rows = db.scalars(select(IntegrationSecret).where(IntegrationSecret.workspace_id == workspace.id)).all()
    return [SecretResponse.model_validate(row) for row in rows]


@router.post("/secrets", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
def upsert_secret(
    payload: SecretRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> SecretResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(
        select(IntegrationSecret).where(
            IntegrationSecret.workspace_id == workspace.id,
            IntegrationSecret.provider == payload.provider,
            IntegrationSecret.label == payload.label,
        )
    )
    encrypted = encrypt_text(payload.value)
    if row:
        row.encrypted_payload = encrypted
    else:
        row = IntegrationSecret(
            workspace_id=workspace.id,
            provider=payload.provider,
            label=payload.label,
            encrypted_payload=encrypted,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return SecretResponse.model_validate(row)


@router.delete("/secrets/{secret_id}")
def delete_secret(
    secret_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(
        select(IntegrationSecret).where(IntegrationSecret.id == secret_id, IntegrationSecret.workspace_id == workspace.id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Secret not found.")
    db.delete(row)
    db.commit()
    return {"ok": True}
