from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Page

ProjectType = Literal["environmental_impact", "emergency_response", "risk_assessment", "other"]
ProjectStatus = Literal["draft", "collecting_data", "analyzing", "generating", "reviewing", "completed"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    project_type: ProjectType = "other"
    company_name: str | None = Field(default=None, max_length=255)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    project_type: ProjectType | None = None
    company_name: str | None = Field(default=None, max_length=255)
    status: ProjectStatus | None = None
    description: str | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    project_type: ProjectType
    company_name: str | None
    status: ProjectStatus
    description: str | None
    owner_id: int
    organization_id: int | None = None
    created_at: datetime
    updated_at: datetime


class ProjectPage(Page[ProjectOut]):
    pass
