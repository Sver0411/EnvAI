from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, QuotaExceededError, ValidationError
from app.models.project import Project
from app.models.tenant import Organization, OrganizationInvitation, OrganizationMember, Plan, ProjectMember, UsageEvent
from app.models.commercial import OrganizationSubscription, QuotaAdjustment
from app.models.user import User
from app.services.authorization import current_organization, membership, require_permission, require_project_permission
from app.services.platform_service import get_or_create_subscription


def create_organization(db: Session, user: User, name: str, slug: str | None) -> Organization:
    slug = slug or f"workspace-{user.id}-{secrets.token_hex(3)}"
    if db.scalar(select(Organization).where(Organization.slug == slug)): raise ConflictError("组织 slug 已存在")
    plan = db.scalar(select(Plan).where(Plan.code == "local_mvp", Plan.active.is_(True)))
    org = Organization(name=name, slug=slug, created_by=user.id, plan_id=plan.id if plan else None); db.add(org); db.flush()
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="owner", status="active", joined_at=datetime.now(timezone.utc)))
    get_or_create_subscription(db, org.id, plan)
    db.commit(); db.refresh(org); return org


def get_org(db: Session, user: User, organization_id: int) -> Organization:
    membership(db, user, organization_id)
    org = db.get(Organization, organization_id)
    if org is None or org.status != "active": raise NotFoundError("组织不存在")
    return org


def list_orgs(db: Session, user: User) -> list[Organization]:
    return list(db.scalars(select(Organization).join(OrganizationMember).where(OrganizationMember.user_id == user.id, OrganizationMember.status == "active", Organization.status != "archived").order_by(Organization.id)))


def list_members(db: Session, user: User, organization_id: int) -> list[OrganizationMember]:
    get_org(db, user, organization_id); require_permission(db, user, organization_id, "members.read"); return list(db.scalars(select(OrganizationMember).where(OrganizationMember.organization_id == organization_id, OrganizationMember.status != "removed").order_by(OrganizationMember.id)))


def update_member(db: Session, user: User, organization_id: int, member_id: int, role: str) -> OrganizationMember:
    require_permission(db, user, organization_id, "members.manage")
    member = db.scalar(select(OrganizationMember).where(OrganizationMember.id == member_id, OrganizationMember.organization_id == organization_id, OrganizationMember.status != "removed"))
    if member is None: raise NotFoundError("组织成员不存在")
    if member.role == "owner" and role != "owner" and (db.scalar(select(func.count()).select_from(OrganizationMember).where(OrganizationMember.organization_id == organization_id, OrganizationMember.role == "owner", OrganizationMember.status == "active")) or 0) <= 1: raise ValidationError("组织至少需要保留一个 owner")
    member.role = role; db.commit(); db.refresh(member); return member


def remove_member(db: Session, user: User, organization_id: int, member_id: int) -> None:
    require_permission(db, user, organization_id, "members.manage")
    member = db.scalar(select(OrganizationMember).where(OrganizationMember.id == member_id, OrganizationMember.organization_id == organization_id, OrganizationMember.status == "active"))
    if member is None: raise NotFoundError("组织成员不存在")
    if member.role == "owner" and (db.scalar(select(func.count()).select_from(OrganizationMember).where(OrganizationMember.organization_id == organization_id, OrganizationMember.role == "owner", OrganizationMember.status == "active")) or 0) <= 1: raise ValidationError("不能移除组织最后一个 owner")
    member.status = "removed"; db.commit()


def create_invitation(db: Session, user: User, organization_id: int, email: str, role: str) -> tuple[OrganizationInvitation, str]:
    require_permission(db, user, organization_id, "members.manage")
    enforce_quota(db, organization_id, "member")
    token = secrets.token_urlsafe(32); invitation = OrganizationInvitation(organization_id=organization_id, email=email.strip().lower(), role=role, token_hash=hashlib.sha256(token.encode()).hexdigest(), invited_by=user.id, expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.invitation_expires_hours)); db.add(invitation); db.commit(); db.refresh(invitation); return invitation, token


def accept_invitation(db: Session, user: User, token: str) -> OrganizationMember:
    digest = hashlib.sha256(token.encode()).hexdigest(); invitation = db.scalar(select(OrganizationInvitation).where(OrganizationInvitation.token_hash == digest))
    if invitation is None or invitation.status != "pending": raise ValidationError("邀请不存在或已使用")
    if invitation.expires_at < datetime.now(timezone.utc): invitation.status = "expired"; db.commit(); raise ValidationError("邀请已过期")
    if user.email.lower() != invitation.email.lower(): raise ForbiddenError("邀请邮箱与当前用户不匹配")
    existing = db.scalar(select(OrganizationMember).where(OrganizationMember.organization_id == invitation.organization_id, OrganizationMember.user_id == user.id))
    member = existing or OrganizationMember(organization_id=invitation.organization_id, user_id=user.id)
    member.role = invitation.role; member.status = "active"; member.joined_at = datetime.now(timezone.utc)
    if existing is None: db.add(member)
    invitation.status = "accepted"; invitation.accepted_at = datetime.now(timezone.utc); db.commit(); db.refresh(member); return member


def list_project_members(db: Session, user: User, project_id: int) -> list[ProjectMember]:
    project = db.get(Project, project_id)
    if project is None: raise NotFoundError("项目不存在")
    require_project_permission(db, user, project, "projects.read")
    return list(db.scalars(select(ProjectMember).where(ProjectMember.project_id == project_id).order_by(ProjectMember.id)))


def upsert_project_member(db: Session, user: User, project_id: int, target_user_id: int, project_role: str) -> ProjectMember:
    project = db.get(Project, project_id)
    if project is None: raise NotFoundError("项目不存在")
    if project.organization_id is None: raise ValidationError("旧项目尚未绑定组织")
    require_permission(db, user, project.organization_id, "projects.update")
    if db.scalar(select(OrganizationMember.id).where(OrganizationMember.organization_id == project.organization_id, OrganizationMember.user_id == target_user_id, OrganizationMember.status == "active")) is None: raise ValidationError("目标用户不是组织成员")
    item = db.scalar(select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == target_user_id))
    if item is None: item = ProjectMember(project_id=project_id, user_id=target_user_id); db.add(item)
    item.project_role = project_role; db.commit(); db.refresh(item); return item


def record_usage(db: Session, *, organization_id: int, usage_type: str, quantity: int, unit: str, source_key: str, user_id: int | None = None, project_id: int | None = None, provider: str | None = None, model: str | None = None, operation: str | None = None, related_resource_type: str | None = None, related_resource_id: int | None = None, metadata: dict | None = None) -> UsageEvent:
    existing = db.scalar(select(UsageEvent).where(UsageEvent.organization_id == organization_id, UsageEvent.source_key == source_key))
    if existing: return existing
    event = UsageEvent(organization_id=organization_id, user_id=user_id, project_id=project_id, usage_type=usage_type, operation=operation, quantity=max(0, int(quantity)), unit=unit, source_key=source_key, provider=provider, model=model, related_resource_type=related_resource_type, related_resource_id=related_resource_id, metadata_json=metadata or {})
    db.add(event); db.flush(); return event


def usage_summary(db: Session, user: User, organization_id: int) -> dict:
    org = get_org(db, user, organization_id); require_permission(db, user, organization_id, "usage.read")
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = list(db.execute(select(UsageEvent.usage_type, func.coalesce(func.sum(UsageEvent.quantity), 0)).where(UsageEvent.organization_id == org.id, UsageEvent.created_at >= month_start).group_by(UsageEvent.usage_type)))
    sub = db.scalar(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == org.id))
    plan = db.get(Plan, sub.plan_id if sub else org.plan_id) if (sub or org.plan_id) else None
    snapshot = sub.entitlement_snapshot if sub and sub.entitlement_snapshot else None
    member_count = db.scalar(select(func.count()).select_from(OrganizationMember).where(OrganizationMember.organization_id == org.id, OrganizationMember.status == "active")) or 0
    project_count = db.scalar(select(func.count()).select_from(Project).where(Project.organization_id == org.id)) or 0
    return {"organization_id": org.id, "period": month_start.strftime("%Y-%m"), "totals": {str(key): int(value) for key, value in rows}, "member_count": member_count, "project_count": project_count, "storage_bytes": sum(int(value) for key, value in rows if key == "storage_bytes"), "limits": {"member_limit": snapshot.get("max_members", plan.member_limit) if snapshot and plan else (plan.member_limit if plan else None), "project_limit": snapshot.get("max_projects", plan.project_limit) if snapshot and plan else (plan.project_limit if plan else None), "ai_token_limit": snapshot.get("monthly_llm_tokens", plan.ai_token_limit) if snapshot and plan else (plan.ai_token_limit if plan else None), "storage_bytes_limit": snapshot.get("storage_bytes", plan.storage_bytes_limit) if snapshot and plan else (plan.storage_bytes_limit if plan else None)}}


def enforce_quota(db: Session, organization_id: int, quota: str, additional: int = 1) -> None:
    org = db.get(Organization, organization_id)
    if org is None or org.status != "active": raise ForbiddenError("组织当前不可用")
    sub = db.scalar(select(OrganizationSubscription).where(OrganizationSubscription.organization_id == organization_id))
    plan = db.get(Plan, sub.plan_id if sub else org.plan_id) if (sub or org.plan_id) else None
    if not plan: return
    limits = sub.entitlement_snapshot if sub and sub.entitlement_snapshot else {}
    member_limit = int(limits.get("max_members", plan.member_limit)); project_limit = int(limits.get("max_projects", plan.project_limit))
    ai_limit = int(limits.get("monthly_llm_tokens", plan.ai_token_limit)); storage_limit = int(limits.get("storage_bytes", plan.storage_bytes_limit))
    now = datetime.now(timezone.utc)
    adjustment = db.scalar(select(func.coalesce(func.sum(QuotaAdjustment.amount), 0)).where(QuotaAdjustment.organization_id == organization_id, QuotaAdjustment.quota_type == quota, QuotaAdjustment.period_start <= now, QuotaAdjustment.period_end >= now)) or 0
    if quota == "member" and (db.scalar(select(func.count()).select_from(OrganizationMember).where(OrganizationMember.organization_id == organization_id, OrganizationMember.status == "active")) or 0) + additional > member_limit + int(adjustment): raise QuotaExceededError("当前组织成员数量已达到上限")
    if quota == "project" and (db.scalar(select(func.count()).select_from(Project).where(Project.organization_id == organization_id)) or 0) + additional > project_limit + int(adjustment): raise QuotaExceededError("当前组织项目数量已达到上限")
    if quota == "storage":
        current = db.scalar(select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(UsageEvent.organization_id == organization_id, UsageEvent.usage_type == "storage_bytes")) or 0
        if int(current) + additional > storage_limit + int(adjustment): raise QuotaExceededError("当前组织存储额度已达到上限")
    if quota == "ai":
        current = db.scalar(select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(UsageEvent.organization_id == organization_id, UsageEvent.usage_type.in_(["llm_input_tokens", "llm_output_tokens", "embedding_tokens"]))) or 0
        if int(current) + additional > ai_limit + int(adjustment): raise QuotaExceededError("当前组织本月 AI 使用额度已达到上限")
