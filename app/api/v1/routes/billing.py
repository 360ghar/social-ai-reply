import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_current_user,
    get_current_workspace,
    subscription_response,
)
from app.db.models import AccountUser, Workspace
from app.db.session import get_db
from app.schemas.v1.product import (
    BillingUpgradeRequest,
    PlanResponse,
    RedemptionRequest,
    RedemptionResponse,
    SubscriptionResponse,
)
from app.services.product.entitlements import serialize_plan_catalog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["billing"])


@router.get("/billing/plans", response_model=list[PlanResponse])
def list_plans() -> list[PlanResponse]:
    return [PlanResponse(**row) for row in serialize_plan_catalog()]


@router.get("/billing/current", response_model=SubscriptionResponse)
def current_billing(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    return subscription_response(db, workspace)


@router.post("/billing/upgrade", response_model=SubscriptionResponse)
def upgrade_billing(
    payload: BillingUpgradeRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    # The workspace is always unlocked, so plan changes are a no-op.
    _ = payload.plan_code
    return subscription_response(db, workspace)


@router.post("/redemptions", response_model=RedemptionResponse)
def redeem_code(
    payload: RedemptionRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> RedemptionResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    _ = payload.code
    return RedemptionResponse(
        success=True,
        plan_code="internal",
        message="This workspace is already fully unlocked.",
    )
