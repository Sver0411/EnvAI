from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PlanCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    member_limit: int = Field(ge=0)
    project_limit: int = Field(ge=0)
    ai_token_limit: int = Field(ge=0)
    storage_bytes_limit: int = Field(ge=0)
    features: dict[str, bool] = Field(default_factory=dict)
    billing_period: Literal["month", "year", "once"] = "month"
    price_amount: Decimal = Field(default=Decimal("0"), ge=0)
    price_currency: str = Field(default="CNY", min_length=3, max_length=3)
    display_order: int = 0
    is_public: bool = True
    trial_days: int = Field(default=0, ge=0, le=365)


class PlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    member_limit: int | None = Field(default=None, ge=0)
    project_limit: int | None = Field(default=None, ge=0)
    ai_token_limit: int | None = Field(default=None, ge=0)
    storage_bytes_limit: int | None = Field(default=None, ge=0)
    features: dict[str, bool] | None = None
    billing_period: Literal["month", "year", "once"] | None = None
    price_amount: Decimal | None = Field(default=None, ge=0)
    price_currency: str | None = Field(default=None, min_length=3, max_length=3)
    display_order: int | None = None
    is_public: bool | None = None
    trial_days: int | None = Field(default=None, ge=0, le=365)


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; code: str; name: str; description: str | None
    member_limit: int; project_limit: int; ai_token_limit: int; storage_bytes_limit: int
    features: dict[str, bool] | None; active: bool; status: str
    billing_period: str; price_amount: Decimal; price_currency: str
    display_order: int; is_public: bool; trial_days: int


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; organization_id: int; plan_id: int; status: str
    started_at: datetime; trial_ends_at: datetime | None
    current_period_start: datetime; current_period_end: datetime | None
    cancel_at_period_end: bool; cancelled_at: datetime | None
    price_amount: Decimal; price_currency: str; billing_provider: str
    entitlement_snapshot: dict[str, Any] | None
    next_plan_id: int | None; change_effective_at: datetime | None


class OrderCreate(BaseModel):
    plan_id: int
    # Deliberately no amount/currency/organization_id: backend computes them.


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; organization_id: int; order_number: str; order_type: str; status: str
    currency: str; subtotal: Decimal; discount_amount: Decimal; total_amount: Decimal
    plan_id: int | None; created_by: int; created_at: datetime


class PaymentAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; order_id: int; provider: str; status: str; amount: Decimal; currency: str
    external_payment_id: str | None; request_id: str; error_code: str | None; error_message: str | None
    created_at: datetime; completed_at: datetime | None


class FeatureFlagIn(BaseModel):
    key: str = Field(min_length=2, max_length=128, pattern=r"^[a-z0-9_.-]+$")
    description: str | None = None
    enabled: bool = False
    organization_id: int | None = None


class FeatureFlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; key: str; description: str | None; enabled: bool; organization_id: int | None


class AnnouncementIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    type: Literal["info", "warning", "maintenance", "release"] = "info"
    starts_at: datetime
    ends_at: datetime | None = None
    audience: Literal["all", "specific_organizations"] = "all"
    organization_ids: list[int] | None = None
    enabled: bool = True


class AnnouncementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; title: str; content: str; type: str; starts_at: datetime; ends_at: datetime | None
    audience: str; organization_ids: list[int] | None; enabled: bool; created_by: int; created_at: datetime


class QuotaAdjustmentIn(BaseModel):
    quota_type: Literal["ai", "storage", "member", "project"]
    amount: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=500)
    period_start: datetime
    period_end: datetime

