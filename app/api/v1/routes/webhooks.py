"""Webhook CRUD and testing endpoints."""
import hashlib
import hmac
import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import ensure_workspace_membership, get_current_user, get_current_workspace
from app.db.models import AccountUser, WebhookEndpoint, Workspace
from app.db.session import get_db
from app.schemas.v1.product import (
    WebhookRequest,
    WebhookResponse,
    WebhookTestRequest,
    WebhookUpdateRequest,
)
from app.services.product.security import validate_webhook_url
from app.utils.audit import record_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["webhooks"])


@router.get("/webhooks", response_model=list[WebhookResponse])
def list_webhooks(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[WebhookResponse]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    rows = db.scalars(select(WebhookEndpoint).where(WebhookEndpoint.workspace_id == workspace.id)).all()
    return [WebhookResponse.model_validate(row) for row in rows]


@router.post("/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    payload: WebhookRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> WebhookResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    try:
        validate_webhook_url(str(payload.target_url))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    row = WebhookEndpoint(
        workspace_id=workspace.id,
        target_url=str(payload.target_url),
        event_types=payload.event_types,
        is_active=payload.is_active if payload.is_active is not None else True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    record_audit(
        db, workspace_id=workspace.id, project_id=None, actor_user_id=current_user.id,
        event_type="webhook.created", entity_type="WebhookEndpoint", entity_id=str(row.id),
    )
    return WebhookResponse.model_validate(row)


@router.patch("/webhooks/{webhook_id}", response_model=WebhookResponse)
def update_webhook(
    webhook_id: int,
    payload: WebhookUpdateRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> WebhookResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(
        select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id, WebhookEndpoint.workspace_id == workspace.id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return WebhookResponse.model_validate(row)


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(
    webhook_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(
        select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id, WebhookEndpoint.workspace_id == workspace.id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/webhooks/{webhook_id}/sample-payload")
def webhook_sample_payload(
    webhook_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(
        select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id, WebhookEndpoint.workspace_id == workspace.id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    return {
        "event": "opportunity.found",
        "timestamp": "2024-01-15T10:30:00Z",
        "data": {
            "opportunity_id": 1,
            "title": "Sample Reddit Post",
            "subreddit": "example",
            "score": 85,
            "url": "https://reddit.com/r/example/comments/abc123",
        },
    }


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    payload: WebhookTestRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(
        select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id, WebhookEndpoint.workspace_id == workspace.id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found.")

    test_payload = {
        "event": "webhook.test",
        "timestamp": "2024-01-15T10:30:00Z",
        "data": {"test": True, "message": "Test webhook delivery"},
    }
    body = json.dumps(test_payload)
    signature = hmac.new(row.signing_secret.encode(), body.encode(), hashlib.sha256).hexdigest() if row.signing_secret else ""

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature,
                "X-Webhook-Event": "webhook.test",
            }
            resp = await client.post(row.target_url, content=body, headers=headers)
        return {
            "delivered": True,
            "status_code": resp.status_code,
            "response_body": resp.text[:500],
        }
    except Exception as e:
        return {"delivered": False, "error": str(e)}
