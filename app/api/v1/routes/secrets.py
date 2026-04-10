"""Integration secrets CRUD endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.api.v1.deps import ensure_workspace_membership, get_current_user, get_current_workspace
from app.db.supabase_client import get_supabase
from app.db.tables.integrations import (
    create_integration_secret,
    delete_integration_secret,
    get_integration_secret_by_id,
    get_integration_secret_by_provider_and_label,
    list_integration_secrets_for_workspace,
    update_integration_secret,
)
from app.schemas.v1.product import SecretRequest, SecretResponse
from app.utils.encryption import encrypt_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["secrets"])


@router.get("/secrets", response_model=list[SecretResponse])
def list_secrets(
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> list[SecretResponse]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    rows = list_integration_secrets_for_workspace(supabase, workspace["id"])
    return [SecretResponse.model_validate(row) for row in rows]


@router.post("/secrets", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
def upsert_secret(
    payload: SecretRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> SecretResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    row = get_integration_secret_by_provider_and_label(
        supabase,
        workspace["id"],
        payload.provider,
        payload.label,
    )
    encrypted = encrypt_text(payload.value)
    if row:
        updated = update_integration_secret(supabase, row["id"], {"encrypted_payload": encrypted})
        return SecretResponse.model_validate(updated)
    else:
        row = create_integration_secret(
            supabase,
            {
                "workspace_id": workspace["id"],
                "provider": payload.provider,
                "label": payload.label,
                "encrypted_payload": encrypted,
            },
        )
        return SecretResponse.model_validate(row)


@router.delete("/secrets/{secret_id}")
def delete_secret(
    secret_id: int,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> dict[str, bool]:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    row = get_integration_secret_by_id(supabase, secret_id)
    if not row:
        raise HTTPException(status_code=404, detail="Secret not found.")
    if row["workspace_id"] != workspace["id"]:
        raise HTTPException(status_code=404, detail="Secret not found.")
    delete_integration_secret(supabase, secret_id)
    return {"ok": True}
