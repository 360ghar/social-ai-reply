from datetime import datetime

from pydantic import BaseModel, Field


class SubscriptionResponse(BaseModel):
    plan_code: str
    status: str
    current_period_end: datetime | None
    features: list[str]
    limits: dict[str, int]


class PlanResponse(BaseModel):
    code: str
    name: str
    price_monthly: int
    features: list[str]
    limits: dict[str, int]


class BillingUpgradeRequest(BaseModel):
    plan_code: str = Field(min_length=2, max_length=50)


class RedemptionRequest(BaseModel):
    code: str = Field(min_length=4, max_length=100)


class RedemptionResponse(BaseModel):
    success: bool
    plan_code: str
    message: str
