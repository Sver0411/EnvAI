import secrets

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Resp
from app.schemas.tenant import InvitationCreate, InvitationOut, MemberRoleUpdate, OrganizationCreate, OrganizationMemberOut, OrganizationOut, OrganizationUpdate, ProjectMemberCreate, ProjectMemberOut, UsageSummaryOut
from app.services import tenant_service
from app.services.authorization import current_organization

router = APIRouter(tags=["organizations"])


@router.post("/organizations", response_model=Resp[OrganizationOut])
def create_organization(data: OrganizationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[OrganizationOut]:
    return Resp(data=OrganizationOut.model_validate(tenant_service.create_organization(db, current_user, data.name, data.slug)))


@router.get("/organizations", response_model=Resp[list[OrganizationOut]])
def list_organizations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[OrganizationOut]]:
    return Resp(data=[OrganizationOut.model_validate(item) for item in tenant_service.list_orgs(db, current_user)])


@router.get("/organizations/{organization_id}", response_model=Resp[OrganizationOut])
def get_organization(organization_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[OrganizationOut]:
    return Resp(data=OrganizationOut.model_validate(tenant_service.get_org(db, current_user, organization_id)))


@router.put("/organizations/{organization_id}", response_model=Resp[OrganizationOut])
def update_organization(organization_id: int, data: OrganizationUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[OrganizationOut]:
    org = tenant_service.get_org(db, current_user, organization_id); from app.services.authorization import require_permission
    require_permission(db, current_user, organization_id, "organization.manage"); org.name = data.name; db.commit(); db.refresh(org); return Resp(data=OrganizationOut.model_validate(org))


@router.get("/organizations/{organization_id}/members", response_model=Resp[list[OrganizationMemberOut]])
def get_members(organization_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[OrganizationMemberOut]]:
    return Resp(data=[OrganizationMemberOut.model_validate(item) for item in tenant_service.list_members(db, current_user, organization_id)])


@router.put("/organizations/{organization_id}/members/{member_id}", response_model=Resp[OrganizationMemberOut])
def update_member(organization_id: int, member_id: int, data: MemberRoleUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[OrganizationMemberOut]:
    return Resp(data=OrganizationMemberOut.model_validate(tenant_service.update_member(db, current_user, organization_id, member_id, data.role)))


@router.delete("/organizations/{organization_id}/members/{member_id}", response_model=Resp[None])
def remove_member(organization_id: int, member_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[None]:
    tenant_service.remove_member(db, current_user, organization_id, member_id); return Resp(message="成员已移除")


@router.post("/organizations/{organization_id}/invitations", response_model=Resp[InvitationOut])
def create_invitation(organization_id: int, data: InvitationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[InvitationOut]:
    invitation, token = tenant_service.create_invitation(db, current_user, organization_id, data.email, data.role); return Resp(data=InvitationOut.model_validate(invitation).model_copy(update={"token": token}))


@router.post("/invitations/{token}/accept", response_model=Resp[OrganizationMemberOut])
def accept_invitation(token: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[OrganizationMemberOut]:
    return Resp(data=OrganizationMemberOut.model_validate(tenant_service.accept_invitation(db, current_user, token)))


@router.get("/projects/{project_id}/members", response_model=Resp[list[ProjectMemberOut]])
def get_project_members(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[ProjectMemberOut]]:
    return Resp(data=[ProjectMemberOut.model_validate(item) for item in tenant_service.list_project_members(db, current_user, project_id)])


@router.post("/projects/{project_id}/members", response_model=Resp[ProjectMemberOut])
def add_project_member(project_id: int, data: ProjectMemberCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ProjectMemberOut]:
    return Resp(data=ProjectMemberOut.model_validate(tenant_service.upsert_project_member(db, current_user, project_id, data.user_id, data.project_role)))


@router.get("/organizations/{organization_id}/usage", response_model=Resp[UsageSummaryOut])
def get_usage(organization_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[UsageSummaryOut]:
    return Resp(data=UsageSummaryOut.model_validate(tenant_service.usage_summary(db, current_user, organization_id)))


@router.get("/organizations/{organization_id}/plan", response_model=Resp[dict])
def get_plan(organization_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[dict]:
    summary = tenant_service.usage_summary(db, current_user, organization_id); return Resp(data=summary["limits"])
