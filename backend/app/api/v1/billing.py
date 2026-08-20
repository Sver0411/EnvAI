from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_platform_admin
from app.core.config import settings
from app.core.exceptions import ForbiddenError, ValidationError
from app.db.session import get_db
from app.models.commercial import OrganizationSubscription, Order
from app.models.tenant import Organization, Plan
from app.models.user import User
from app.schemas.commercial import OrderCreate, OrderOut, PaymentAttemptOut, SubscriptionOut
from app.schemas.common import Resp
from app.services import platform_service
from app.services.authorization import require_permission

router = APIRouter(tags=["billing"])


@router.get("/billing/plans", response_model=Resp[list[dict]])
def list_public_plans(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.scalars(select(Plan).where(Plan.active.is_(True), Plan.is_public.is_(True)).order_by(Plan.display_order, Plan.id)).all()
    return Resp(data=[{"id": p.id, "code": p.code, "name": p.name, "description": p.description, "member_limit": p.member_limit,
                      "project_limit": p.project_limit, "ai_token_limit": p.ai_token_limit, "storage_bytes_limit": p.storage_bytes_limit,
                      "features": p.features or {}, "billing_period": p.billing_period, "price_amount": p.price_amount,
                      "price_currency": p.price_currency, "trial_days": p.trial_days} for p in rows])


def _org_owner(db: Session, user: User, organization_id: int) -> None:
    require_permission(db, user, organization_id, "organization.manage")


@router.post("/billing/orders", response_model=Resp[OrderOut])
def create_order(data: OrderCreate, organization_id: int = Query(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _org_owner(db, current_user, organization_id)
    return Resp(data=OrderOut.model_validate(platform_service.create_order(db, current_user, organization_id, data.plan_id)))


@router.get("/billing/orders", response_model=Resp[list[OrderOut]])
def list_orders(organization_id: int = Query(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _org_owner(db, current_user, organization_id)
    rows = db.scalars(select(Order).where(Order.organization_id == organization_id).order_by(Order.id.desc())).all()
    return Resp(data=[OrderOut.model_validate(x) for x in rows])


@router.get("/billing/orders/{order_id}", response_model=Resp[OrderOut])
def get_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = db.get(Order, order_id)
    if not order: return Resp(code=404, message="订单不存在")
    _org_owner(db, current_user, order.organization_id)
    return Resp(data=OrderOut.model_validate(order))


@router.get("/organizations/{organization_id}/subscription", response_model=Resp[SubscriptionOut | None])
def get_subscription(organization_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _org_owner(db, current_user, organization_id)
    sub = platform_service.get_or_create_subscription(db, organization_id)
    db.commit()
    return Resp(data=SubscriptionOut.model_validate(sub) if sub else None)


@router.post("/organizations/{organization_id}/subscription/cancel", response_model=Resp[SubscriptionOut])
def cancel_subscription(organization_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _org_owner(db, current_user, organization_id)
    sub = db.scalar(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == organization_id))
    if not sub: return Resp(code=404, message="订阅不存在")
    sub.cancel_at_period_end = True; db.commit(); db.refresh(sub)
    return Resp(data=SubscriptionOut.model_validate(sub))


@router.post("/dev/payments/{order_id}/simulate-success", response_model=Resp[PaymentAttemptOut])
def simulate_success(order_id: int, request_id: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if settings.environment == "production" or settings.payment_provider != "mock": raise ValidationError("生产环境不允许模拟支付")
    order = db.get(Order, order_id)
    if not order: return Resp(code=404, message="订单不存在")
    _org_owner(db, current_user, order.organization_id)
    return Resp(data=PaymentAttemptOut.model_validate(platform_service.complete_mock_payment(db, current_user, order_id, success=True, request_id=request_id)))


@router.post("/dev/payments/{order_id}/simulate-failure", response_model=Resp[PaymentAttemptOut])
def simulate_failure(order_id: int, request_id: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if settings.environment == "production" or settings.payment_provider != "mock": raise ValidationError("生产环境不允许模拟支付")
    order = db.get(Order, order_id)
    if not order: return Resp(code=404, message="订单不存在")
    _org_owner(db, current_user, order.organization_id)
    return Resp(data=PaymentAttemptOut.model_validate(platform_service.complete_mock_payment(db, current_user, order_id, success=False, request_id=request_id)))
