from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=3, max_length=128, pattern=r"^[a-z0-9][a-z0-9-]*$")


class OrganizationUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; name: str; slug: str; status: str; created_by: int; plan_id: int | None; created_at: datetime


class OrganizationMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; organization_id: int; user_id: int; role: str; status: str; joined_at: datetime | None; created_at: datetime


class MemberRoleUpdate(BaseModel):
    role: Literal["owner", "admin", "member", "viewer"]


class InvitationCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: Literal["admin", "member", "viewer"] = "member"


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; organization_id: int; email: str; role: str; status: str; expires_at: datetime; created_at: datetime
    token: str | None = None


class ProjectMemberCreate(BaseModel):
    user_id: int
    project_role: Literal["owner", "editor", "reviewer", "viewer"] = "viewer"


class ProjectMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; project_id: int; user_id: int; project_role: str; created_at: datetime


class UsageSummaryOut(BaseModel):
    organization_id: int; period: str; totals: dict[str, int]; member_count: int; project_count: int; storage_bytes: int; limits: dict[str, int | None]
