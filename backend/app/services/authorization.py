from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import case, exists, select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.project import Project
from app.models.tenant import Organization, OrganizationMember, Plan, ProjectMember
from app.models.user import User
from app.services.platform_service import get_or_create_subscription


ROLE_PERMISSIONS = {
    "owner": {"organization.manage", "members.read", "members.manage", "projects.create", "projects.read", "projects.update", "projects.delete", "knowledge.read", "knowledge.manage", "documents.read", "documents.generate", "documents.review", "documents.export", "usage.read", "templates.read", "templates.manage"},
    "admin": {"members.read", "members.manage", "projects.create", "projects.read", "projects.update", "projects.delete", "knowledge.read", "knowledge.manage", "documents.read", "documents.generate", "documents.review", "documents.export", "usage.read", "templates.read", "templates.manage"},
    "member": {"projects.create", "projects.read", "projects.update", "knowledge.read", "documents.read", "documents.generate", "documents.review", "documents.export", "templates.read"},
    "viewer": {"projects.read", "knowledge.read", "documents.read", "templates.read"},
}
PROJECT_ROLE_PERMISSIONS = {
    "owner": {"projects.read", "projects.update", "projects.delete", "documents.read", "documents.generate", "documents.review", "documents.export"},
    "editor": {"projects.read", "projects.update", "documents.read", "documents.generate", "documents.export"},
    "reviewer": {"projects.read", "documents.read", "documents.review", "documents.export"},
    "viewer": {"projects.read", "documents.read"},
}


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-") or "workspace"
    return normalized[:90]


def create_personal_organization(db: Session, user: User) -> Organization:
    base = _slug(f"personal-{user.username}-{user.id}")
    slug = base
    suffix = 1
    while db.scalar(select(Organization.id).where(Organization.slug == slug)) is not None:
        suffix += 1; slug = f"{base}-{suffix}"
    plan = db.scalar(select(Plan).where(Plan.code == "local_mvp", Plan.active.is_(True)))
    org = Organization(name=f"{user.full_name or user.username} 的工作区", slug=slug, created_by=user.id, plan_id=plan.id if plan else None)
    db.add(org); db.flush()
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="owner", status="active", joined_at=datetime.now(timezone.utc)))
    get_or_create_subscription(db, org.id, plan)
    db.flush()
    return org


def memberships(db: Session, user: User) -> list[OrganizationMember]:
    return list(db.scalars(select(OrganizationMember).where(OrganizationMember.user_id == user.id, OrganizationMember.status == "active").order_by(OrganizationMember.id)))


def current_organization(db: Session, user: User, organization_id: int | None = None) -> Organization:
    query = select(Organization).join(OrganizationMember).where(OrganizationMember.user_id == user.id, OrganizationMember.status == "active", Organization.status == "active")
    if organization_id is not None: query = query.where(Organization.id == organization_id)
    # Without an explicit header, prefer the user's personal workspace. This
    # avoids silently switching to a shared organization after an invitation.
    org = db.scalar(query.order_by(case((Organization.created_by == user.id, 0), else_=1), Organization.id))
    if org is None: raise NotFoundError("当前用户不属于该组织")
    return org


def membership(db: Session, user: User, organization_id: int) -> OrganizationMember:
    row = db.scalar(select(OrganizationMember).where(OrganizationMember.user_id == user.id, OrganizationMember.organization_id == organization_id, OrganizationMember.status == "active"))
    if row is None: raise ForbiddenError("没有该组织的访问权限")
    return row


def require_permission(db: Session, user: User, organization_id: int, permission: str) -> OrganizationMember:
    row = membership(db, user, organization_id)
    if permission not in ROLE_PERMISSIONS.get(row.role, set()): raise ForbiddenError("组织权限不足")
    return row


def project_role(db: Session, user: User, project: Project) -> tuple[OrganizationMember, str | None]:
    if project.organization_id is None:
        if project.owner_id != user.id: raise NotFoundError("项目不存在")
        return OrganizationMember(role="owner", organization_id=0, user_id=user.id), "owner"
    org_member = membership(db, user, project.organization_id)
    if org_member.role in {"owner", "admin"}: return org_member, org_member.role
    assigned = db.scalar(select(ProjectMember).where(ProjectMember.project_id == project.id, ProjectMember.user_id == user.id))
    if assigned is None: raise NotFoundError("项目不存在")
    return org_member, assigned.project_role


def require_project_permission(db: Session, user: User, project: Project, permission: str) -> tuple[OrganizationMember, str | None]:
    org_member, role = project_role(db, user, project)
    if permission in ROLE_PERMISSIONS.get(org_member.role, set()) or permission in PROJECT_ROLE_PERMISSIONS.get(role or "", set()): return org_member, role
    raise ForbiddenError("项目权限不足")
