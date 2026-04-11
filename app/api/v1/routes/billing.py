"""Billing endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_current_user,
    get_current_workspace,
    subscription_response,
)
from app.db.supabase_client import get_supabase
from app.schemas.v1.billing import (
    BillingUpgradeRequest,
    PlanResponse,
    RedemptionRequest,
    RedemptionResponse,
    SubscriptionResponse,
)
from app.services.product.entitlements import PLAN_CATALOG, get_or_create_subscription, serialize_plan_catalog, update_subscription

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["billing"])


@router.get("/billing/plans", response_model=list[PlanResponse])
def list_plans() -> list[PlanResponse]:
    return [PlanResponse(**row) for row in serialize_plan_catalog()]


@router.get("/billing/current", response_model=SubscriptionResponse)
def current_billing(
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> SubscriptionResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    return subscription_response(supabase, workspace)


@router.post("/billing/upgrade", response_model=SubscriptionResponse)
def upgrade_billing(
    payload: BillingUpgradeRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> SubscriptionResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    valid_codes = {plan["code"] for plan in PLAN_CATALOG}
    if payload.plan_code not in valid_codes:
        raise HTTPException(status_code=400, detail=f"Invalid plan code '{payload.plan_code}'. Valid options: {sorted(valid_codes)}")
    subscription = get_or_create_subscription(supabase, workspace)
    update_subscription(supabase, subscription["id"], {"plan_code": payload.plan_code})
    return subscription_response(supabase, workspace)


@router.post("/redemptions", response_model=RedemptionResponse)
def redeem_code(
    payload: RedemptionRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> RedemptionResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    _ = payload.code
    return RedemptionResponse(
        success=True,
        plan_code="internal",
        message="This workspace is already fully unlocked.",
    )
