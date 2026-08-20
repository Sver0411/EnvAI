from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import secrets
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.commercial import (AIModelPricing, FeatureFlag, OrganizationSubscription, Order, PaymentAttempt,
    PlatformAuditEvent, QuotaAdjustment, SystemAnnouncement, UsageCost)
from app.models.project import Project
from app.models.export import ReportExportJob
from app.models.workflow import BatchGenerationRun, DocumentValidationRun
from app.models.review import ProfessionalReviewRun
from app.models.tenant import Organization, OrganizationMember, Plan, UsageEvent
from app.models.user import User


def audit(db: Session, actor: User, action: str, *, organization_id: int | None = None,
          target_type: str | None = None, target_id: Any = None, metadata: dict | None = None) -> None:
    db.add(PlatformAuditEvent(actor_user_id=actor.id, organization_id=organization_id, action=action,
                              target_type=target_type, target_id=str(target_id) if target_id is not None else None,
                              metadata_json=metadata or {}))


def dashboard(db: Session, start: datetime, end: datetime) -> dict[str, int | str]:
    def count(model, predicate=None):
        q = select(func.count()).select_from(model)
        if predicate is not None: q = q.where(predicate)
        return int(db.scalar(q) or 0)
    usage_q = select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(UsageEvent.created_at >= start, UsageEvent.created_at < end)
    tokens = int(db.scalar(usage_q.where(UsageEvent.usage_type.in_(["llm_input_tokens", "llm_output_tokens", "embedding_tokens"]))) or 0)
    return {
        "start": start.isoformat(), "end": end.isoformat(),
        "organizations": count(Organization), "active_organizations": count(Organization, Organization.status == "active"),
        "users": count(User), "active_users": count(User, User.status == "active"),
        "projects": count(Project), "documents_generated": count(UsageEvent, UsageEvent.usage_type.in_(["docx_export", "pdf_export"])),
        "ai_requests": count(UsageEvent, UsageEvent.created_at >= start), "llm_tokens": tokens,
        "embedding_usage": int(db.scalar(usage_q.where(UsageEvent.usage_type == "embedding_tokens")) or 0),
        "storage_bytes": int(db.scalar(select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(UsageEvent.usage_type == "storage_bytes")) or 0),
        "exports": count(UsageEvent, UsageEvent.created_at >= start),
        "failed_jobs": count(BatchGenerationRun, BatchGenerationRun.status == "failed") + count(DocumentValidationRun, DocumentValidationRun.status == "failed") + count(ProfessionalReviewRun, ProfessionalReviewRun.status == "failed") + count(ReportExportJob, ReportExportJob.status == "failed"),
    }


def list_organizations(db: Session, *, page: int, page_size: int, search: str | None = None) -> tuple[list[dict], int]:
    q = select(Organization).order_by(Organization.id.desc())
    if search:
        pattern = f"%{search}%"
        q = q.outerjoin(User, User.id == Organization.created_by).where(or_(Organization.name.ilike(pattern), Organization.slug.ilike(pattern), User.email.ilike(pattern)))
    total = int(db.scalar(select(func.count()).select_from(q.subquery())) or 0)
    orgs = list(db.scalars(q.offset((page - 1) * page_size).limit(page_size)))
    result = []
    for org in orgs:
        members = int(db.scalar(select(func.count()).select_from(OrganizationMember).where(OrganizationMember.organization_id == org.id, OrganizationMember.status == "active")) or 0)
        projects = int(db.scalar(select(func.count()).select_from(Project).where(Project.organization_id == org.id)) or 0)
        usage = int(db.scalar(select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(UsageEvent.organization_id == org.id)) or 0)
        result.append({"id": org.id, "name": org.name, "slug": org.slug, "status": org.status, "plan_id": org.plan_id,
                       "members_count": members, "projects_count": projects, "usage": usage, "created_at": org.created_at})
    return result, total


def organization_detail(db: Session, organization_id: int) -> dict:
    org = db.get(Organization, organization_id)
    if not org: raise NotFoundError("组织不存在")
    items, _ = list_organizations(db, page=1, page_size=1, search=org.slug)
    return items[0] if items else {"id": org.id, "name": org.name, "status": org.status}


def set_organization_status(db: Session, actor: User, organization_id: int, status: str, reason: str | None = None) -> Organization:
    if status == "suspended" and not reason: raise ValidationError("暂停组织必须填写原因")
    org = db.get(Organization, organization_id)
    if not org: raise NotFoundError("组织不存在")
    org.status = status
    if status == "suspended": org.suspension_reason, org.suspended_by, org.suspended_at = reason, actor.id, datetime.now(timezone.utc)
    elif status == "active": org.suspension_reason, org.suspended_by, org.suspended_at = None, None, None
    audit(db, actor, f"organization_{status}", organization_id=org.id, target_type="organization", target_id=org.id, metadata={"reason": reason} if reason else {})
    db.commit(); db.refresh(org); return org


def list_users(db: Session, *, page: int, page_size: int, search: str | None = None) -> tuple[list[User], int]:
    q = select(User).order_by(User.id.desc())
    if search: q = q.where(or_(User.email.ilike(f"%{search}%"), User.username.ilike(f"%{search}%")))
    total = int(db.scalar(select(func.count()).select_from(q.subquery())) or 0)
    return list(db.scalars(q.offset((page - 1) * page_size).limit(page_size))), total


def set_user_status(db: Session, actor: User, user_id: int, status: str) -> User:
    user = db.get(User, user_id)
    if not user: raise NotFoundError("用户不存在")
    user.status = status; user.is_active = status == "active"
    audit(db, actor, f"user_{status}", target_type="user", target_id=user.id)
    db.commit(); db.refresh(user); return user


def plan_create(db: Session, actor: User, data) -> Plan:
    if db.scalar(select(Plan).where(Plan.code == data.code)): raise ConflictError("套餐 code 已存在")
    plan = Plan(**data.model_dump()); plan.active = True; plan.status = "active"
    db.add(plan); db.flush(); audit(db, actor, "plan_created", target_type="plan", target_id=plan.id, metadata=data.model_dump(mode="json")); db.commit(); db.refresh(plan); return plan


def plan_update(db: Session, actor: User, plan_id: int, data) -> Plan:
    plan = db.get(Plan, plan_id)
    if not plan: raise NotFoundError("套餐不存在")
    old = {key: getattr(plan, key) for key in data.model_dump(exclude_unset=True)}
    for key, value in data.model_dump(exclude_unset=True).items(): setattr(plan, key, value)
    audit(db, actor, "plan_updated", target_type="plan", target_id=plan.id, metadata={"old": old, "new": data.model_dump(exclude_unset=True, mode="json")})
    db.commit(); db.refresh(plan); return plan


def ensure_snapshot(plan: Plan) -> dict[str, Any]:
    return {"max_members": plan.member_limit, "max_projects": plan.project_limit, "monthly_llm_tokens": plan.ai_token_limit,
            "storage_bytes": plan.storage_bytes_limit, "features": plan.features or {}, "plan_id": plan.id,
            "price_amount": str(plan.price_amount), "price_currency": plan.price_currency}


def get_or_create_subscription(db: Session, organization_id: int, plan: Plan | None = None) -> OrganizationSubscription | None:
    sub = db.scalar(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == organization_id))
    if sub: return sub
    org = db.get(Organization, organization_id); plan = plan or (db.get(Plan, org.plan_id) if org and org.plan_id else None)
    if not plan: return None
    now = datetime.now(timezone.utc); end = now + timedelta(days=365 if plan.billing_period == "year" else 30)
    sub = OrganizationSubscription(organization_id=organization_id, plan_id=plan.id, status="trial" if plan.trial_days else "active",
        trial_ends_at=now + timedelta(days=plan.trial_days) if plan.trial_days else None, current_period_start=now,
        current_period_end=end, price_amount=plan.price_amount, price_currency=plan.price_currency, entitlement_snapshot=ensure_snapshot(plan))
    db.add(sub); db.flush(); return sub


def create_order(db: Session, actor: User, organization_id: int, plan_id: int) -> Order:
    plan = db.get(Plan, plan_id)
    if not plan or not plan.active or plan.status != "active": raise ValidationError("套餐不存在或已停用")
    if not db.get(Organization, organization_id): raise NotFoundError("组织不存在")
    number = f"ENV{datetime.now(timezone.utc):%Y%m%d%H%M%S}{secrets.token_hex(4).upper()}"
    order = Order(organization_id=organization_id, order_number=number, subtotal=plan.price_amount, total_amount=plan.price_amount,
                  currency=plan.price_currency, plan_id=plan.id, created_by=actor.id)
    db.add(order); db.commit(); db.refresh(order); return order


def complete_mock_payment(db: Session, actor: User, order_id: int, *, success: bool, request_id: str | None = None) -> PaymentAttempt:
    order = db.get(Order, order_id)
    if not order: raise NotFoundError("订单不存在")
    if order.created_by != actor.id and actor.platform_role not in {"platform_admin", "platform_super_admin"}:
        # Organization owner authorization is checked by the API before calling this method.
        raise ForbiddenError("无权操作该订单")
    if order.status == "paid": raise ConflictError("订单已支付")
    if order.status != "pending": raise ValidationError("订单当前状态不能支付")
    req = request_id or secrets.token_urlsafe(16)
    existing = db.scalar(select(PaymentAttempt).where(PaymentAttempt.provider == "mock", PaymentAttempt.request_id == req))
    if existing: return existing
    attempt = PaymentAttempt(order_id=order.id, provider="mock", status="succeeded" if success else "failed", amount=order.total_amount,
        currency=order.currency, request_id=req, external_payment_id=f"mock_{secrets.token_hex(8)}", completed_at=datetime.now(timezone.utc) if success else None,
        error_code=None if success else "MOCK_FAILED", error_message=None if success else "模拟支付失败")
    db.add(attempt)
    if success:
        order.status = "paid"
        plan = db.get(Plan, order.plan_id); sub = get_or_create_subscription(db, order.organization_id, plan)
        if sub:
            now = datetime.now(timezone.utc); sub.plan_id = plan.id; sub.status = "active"; sub.price_amount = plan.price_amount; sub.price_currency = plan.price_currency
            sub.current_period_start = now; sub.current_period_end = now + timedelta(days=365 if plan.billing_period == "year" else 30); sub.entitlement_snapshot = ensure_snapshot(plan)
            org = db.get(Organization, order.organization_id); org.plan_id = plan.id
        audit(db, actor, "order_marked_paid", organization_id=order.organization_id, target_type="order", target_id=order.id)
    db.commit(); db.refresh(attempt); return attempt


def active_announcements(db: Session, organization_id: int | None = None, now: datetime | None = None) -> list[SystemAnnouncement]:
    now = now or datetime.now(timezone.utc)
    rows = list(db.scalars(select(SystemAnnouncement).where(SystemAnnouncement.enabled.is_(True), SystemAnnouncement.starts_at <= now,
        or_(SystemAnnouncement.ends_at.is_(None), SystemAnnouncement.ends_at >= now)).order_by(SystemAnnouncement.starts_at.desc())))
    return [row for row in rows if row.audience == "all" or (organization_id is not None and organization_id in (row.organization_ids or []))]


def feature_enabled(db: Session, key: str, organization_id: int | None = None) -> bool:
    if organization_id is not None:
        override = db.scalar(select(FeatureFlag).where(FeatureFlag.key == key, FeatureFlag.organization_id == organization_id))
        if override is not None: return bool(override.enabled)
    global_flag = db.scalar(select(FeatureFlag).where(FeatureFlag.key == key, FeatureFlag.organization_id.is_(None)))
    return bool(global_flag.enabled) if global_flag is not None else False


def add_adjustment(db: Session, actor: User, organization_id: int, data) -> QuotaAdjustment:
    if data.period_end <= data.period_start: raise ValidationError("额度有效期无效")
    item = QuotaAdjustment(organization_id=organization_id, created_by=actor.id, **data.model_dump())
    db.add(item); audit(db, actor, "quota_adjusted", organization_id=organization_id, target_type="organization", target_id=organization_id, metadata=data.model_dump(mode="json")); db.commit(); db.refresh(item); return item


def cost_summary(db: Session, start: datetime, end: datetime, organization_id: int | None = None) -> list[dict]:
    q = select(UsageEvent.provider, UsageEvent.model, UsageEvent.operation, UsageEvent.usage_type, func.count(UsageEvent.id), func.coalesce(func.sum(UsageEvent.quantity), 0), func.coalesce(func.sum(UsageCost.estimated_cost), 0)).join(UsageCost, UsageCost.usage_event_id == UsageEvent.id, isouter=True).where(UsageEvent.created_at >= start, UsageEvent.created_at < end)
    if organization_id is not None: q = q.where(UsageEvent.organization_id == organization_id)
    rows = db.execute(q.group_by(UsageEvent.provider, UsageEvent.model, UsageEvent.usage_type)).all()
    return [{"provider": p or "unknown", "model": m or "unknown", "operation": op or t, "requests": int(c), "tokens": int(n), "estimated_cost": Decimal(cost or 0)} for p, m, op, t, c, n, cost in rows]
