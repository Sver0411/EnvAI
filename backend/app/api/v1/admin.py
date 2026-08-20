from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_platform_admin
from app.db.session import get_db
from app.models.commercial import AIModelPricing, FeatureFlag, OrganizationSubscription, PlatformAuditEvent, SystemAnnouncement
from app.models.tenant import Organization, OrganizationMember, Plan
from app.models.user import User
from app.schemas.commercial import AnnouncementIn, AnnouncementOut, FeatureFlagIn, FeatureFlagOut, PlanCreate, PlanOut, PlanUpdate, QuotaAdjustmentIn, SubscriptionOut
from app.schemas.common import Page, Resp
from app.services import platform_service

router = APIRouter(prefix="/admin", tags=["platform-admin"])


def _window(days: int | None) -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    return end - timedelta(days=days or 30), end


@router.get("/dashboard", response_model=Resp[dict])
def get_dashboard(days: int = Query(30, ge=1, le=366), db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    start, end = _window(days); return Resp(data=platform_service.dashboard(db, start, end))


@router.get("/organizations", response_model=Resp[Page[dict]])
def get_organizations(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), search: str | None = None,
                      db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    items, total = platform_service.list_organizations(db, page=page, page_size=page_size, search=search)
    return Resp(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/organizations/{organization_id}", response_model=Resp[dict])
def get_organization(organization_id: int, db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    return Resp(data=platform_service.organization_detail(db, organization_id))


@router.post("/organizations/{organization_id}/suspend", response_model=Resp[dict])
def suspend_organization(organization_id: int, reason: str = Query(..., min_length=1, max_length=500), db: Session = Depends(get_db), actor: User = Depends(require_platform_admin)):
    return Resp(data={"id": platform_service.set_organization_status(db, actor, organization_id, "suspended", reason).id, "status": "suspended"})


@router.post("/organizations/{organization_id}/activate", response_model=Resp[dict])
def activate_organization(organization_id: int, db: Session = Depends(get_db), actor: User = Depends(require_platform_admin)):
    org = platform_service.set_organization_status(db, actor, organization_id, "active"); return Resp(data={"id": org.id, "status": org.status})


@router.post("/organizations/{organization_id}/archive", response_model=Resp[dict])
def archive_organization(organization_id: int, db: Session = Depends(get_db), actor: User = Depends(require_platform_admin)):
    org = platform_service.set_organization_status(db, actor, organization_id, "archived"); return Resp(data={"id": org.id, "status": org.status})


@router.get("/users", response_model=Resp[Page[dict]])
def get_users(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), search: str | None = None,
              db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    users, total = platform_service.list_users(db, page=page, page_size=page_size, search=search)
    items = [{"id": u.id, "username": u.username, "email": u.email, "full_name": u.full_name, "status": u.status,
              "platform_role": u.platform_role, "is_active": u.is_active, "last_login_at": u.last_login_at, "created_at": u.created_at} for u in users]
    return Resp(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.post("/users/{user_id}/suspend", response_model=Resp[dict])
def suspend_user(user_id: int, db: Session = Depends(get_db), actor: User = Depends(require_platform_admin)):
    user = platform_service.set_user_status(db, actor, user_id, "suspended"); return Resp(data={"id": user.id, "status": user.status})


@router.post("/users/{user_id}/activate", response_model=Resp[dict])
def activate_user(user_id: int, db: Session = Depends(get_db), actor: User = Depends(require_platform_admin)):
    user = platform_service.set_user_status(db, actor, user_id, "active"); return Resp(data={"id": user.id, "status": user.status})


@router.get("/users/{user_id}", response_model=Resp[dict])
def get_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    user = db.get(User, user_id)
    if not user: return Resp(code=404, message="用户不存在")
    memberships = db.execute(select(OrganizationMember.organization_id, OrganizationMember.role, OrganizationMember.status).where(OrganizationMember.user_id == user.id)).all()
    return Resp(data={"id": user.id, "username": user.username, "email": user.email, "full_name": user.full_name, "status": user.status, "platform_role": user.platform_role, "last_login_at": user.last_login_at, "created_at": user.created_at, "organizations": [{"organization_id": i, "role": r, "status": s} for i, r, s in memberships]})


@router.get("/plans", response_model=Resp[list[PlanOut]])
def get_plans(db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    return Resp(data=[PlanOut.model_validate(x) for x in db.scalars(select(Plan).order_by(Plan.display_order, Plan.id))])


@router.post("/plans", response_model=Resp[PlanOut])
def create_plan(data: PlanCreate, db: Session = Depends(get_db), actor: User = Depends(require_platform_admin)):
    return Resp(data=PlanOut.model_validate(platform_service.plan_create(db, actor, data)))


@router.put("/plans/{plan_id}", response_model=Resp[PlanOut])
def update_plan(plan_id: int, data: PlanUpdate, db: Session = Depends(get_db), actor: User = Depends(require_platform_admin)):
    return Resp(data=PlanOut.model_validate(platform_service.plan_update(db, actor, plan_id, data)))


@router.post("/plans/{plan_id}/{action}", response_model=Resp[dict])
def plan_status(plan_id: int, action: str, db: Session = Depends(get_db), actor: User = Depends(require_platform_admin)):
    if action not in {"activate", "deactivate"}: return Resp(code=422, message="无效的套餐操作")
    plan = db.get(Plan, plan_id)
    if plan is None: return Resp(code=404, message="套餐不存在")
    plan.active = action == "activate"; plan.status = "active" if plan.active else "inactive"
    platform_service.audit(db, actor, "plan_status_changed", target_type="plan", target_id=plan.id, metadata={"status": plan.status}); db.commit()
    return Resp(data={"id": plan.id, "status": plan.status})


@router.get("/subscriptions", response_model=Resp[list[SubscriptionOut]])
def get_subscriptions(db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    return Resp(data=[SubscriptionOut.model_validate(x) for x in db.scalars(select(OrganizationSubscription).order_by(OrganizationSubscription.id.desc()))])


@router.get("/subscriptions/{subscription_id}", response_model=Resp[SubscriptionOut])
def get_subscription(subscription_id: int, db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    row = db.get(OrganizationSubscription, subscription_id)
    if not row: return Resp(code=404, message="订阅不存在")
    return Resp(data=SubscriptionOut.model_validate(row))


@router.get("/costs", response_model=Resp[list[dict]])
def get_costs(days: int = Query(30, ge=1, le=366), organization_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    start, end = _window(days); return Resp(data=platform_service.cost_summary(db, start, end, organization_id))


@router.post("/organizations/{organization_id}/quota-adjustments", response_model=Resp[dict])
def adjust_quota(organization_id: int, data: QuotaAdjustmentIn, db: Session = Depends(get_db), actor: User = Depends(require_platform_admin)):
    row = platform_service.add_adjustment(db, actor, organization_id, data)
    return Resp(data={"id": row.id, "organization_id": row.organization_id, "quota_type": row.quota_type, "amount": row.amount, "period_start": row.period_start, "period_end": row.period_end})


@router.get("/jobs", response_model=Resp[list[dict]])
def get_jobs(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    # Job metadata only. Content, prompts, files, and private knowledge chunks
    # are intentionally excluded from the platform console.
    from app.models.workflow import BatchGenerationRun, DocumentValidationRun
    rows = []
    for row in db.scalars(select(BatchGenerationRun).order_by(BatchGenerationRun.id.desc()).limit(limit)):
        rows.append({"type": "generation", "id": row.id, "status": row.status, "started_at": row.started_at, "completed_at": row.completed_at, "error": None})
    for row in db.scalars(select(DocumentValidationRun).order_by(DocumentValidationRun.id.desc()).limit(limit)):
        rows.append({"type": "validation", "id": row.id, "status": row.status, "started_at": row.started_at, "completed_at": row.completed_at, "error": None})
    return Resp(data=rows[:limit])


@router.get("/feature-flags", response_model=Resp[list[FeatureFlagOut]])
def get_flags(db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    return Resp(data=[FeatureFlagOut.model_validate(x) for x in db.scalars(select(FeatureFlag).order_by(FeatureFlag.key, FeatureFlag.organization_id))])


@router.post("/feature-flags", response_model=Resp[FeatureFlagOut])
def create_flag(data: FeatureFlagIn, db: Session = Depends(get_db), actor: User = Depends(require_platform_admin)):
    flag = FeatureFlag(**data.model_dump()); db.add(flag); db.flush(); platform_service.audit(db, actor, "feature_flag_changed", organization_id=flag.organization_id, target_type="feature_flag", target_id=flag.id, metadata={"new": data.model_dump()}); db.commit(); db.refresh(flag)
    return Resp(data=FeatureFlagOut.model_validate(flag))


@router.put("/feature-flags/{flag_id}", response_model=Resp[FeatureFlagOut])
def update_flag(flag_id: int, data: FeatureFlagIn, db: Session = Depends(get_db), actor: User = Depends(require_platform_admin)):
    flag = db.get(FeatureFlag, flag_id)
    if not flag: return Resp(code=404, message="功能开关不存在")
    old = {"enabled": flag.enabled, "organization_id": flag.organization_id}
    flag.enabled = data.enabled; flag.description = data.description
    platform_service.audit(db, actor, "feature_flag_changed", organization_id=flag.organization_id, target_type="feature_flag", target_id=flag.id, metadata={"old": old, "new": data.model_dump()}); db.commit(); db.refresh(flag)
    return Resp(data=FeatureFlagOut.model_validate(flag))


@router.get("/announcements", response_model=Resp[list[AnnouncementOut]])
def get_announcements(db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    return Resp(data=[AnnouncementOut.model_validate(x) for x in db.scalars(select(SystemAnnouncement).order_by(SystemAnnouncement.id.desc()))])


@router.post("/announcements", response_model=Resp[AnnouncementOut])
def create_announcement(data: AnnouncementIn, db: Session = Depends(get_db), actor: User = Depends(require_platform_admin)):
    row = SystemAnnouncement(**data.model_dump(), created_by=actor.id); db.add(row); db.flush(); platform_service.audit(db, actor, "announcement_created", target_type="announcement", target_id=row.id); db.commit(); db.refresh(row)
    return Resp(data=AnnouncementOut.model_validate(row))


@router.get("/audit", response_model=Resp[list[dict]])
def get_audit(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    rows = list(db.scalars(select(PlatformAuditEvent).order_by(PlatformAuditEvent.id.desc()).limit(limit)))
    return Resp(data=[{"id": x.id, "actor_user_id": x.actor_user_id, "organization_id": x.organization_id, "action": x.action, "target_type": x.target_type, "target_id": x.target_id, "metadata": x.metadata_json, "created_at": x.created_at} for x in rows])
