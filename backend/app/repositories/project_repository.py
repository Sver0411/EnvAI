from datetime import datetime
from pathlib import Path
import uuid

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app.models.company_profile import CompanyProfile
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.tenant import OrganizationMember, ProjectMember
from app.schemas.project import ProjectCreate, ProjectUpdate


def _visible_project_query(owner_id: int):
    organization_admin = exists(select(OrganizationMember.id).where(OrganizationMember.organization_id == Project.organization_id, OrganizationMember.user_id == owner_id, OrganizationMember.status == "active", OrganizationMember.role.in_(["owner", "admin"])))
    assigned_member = exists(select(ProjectMember.id).where(ProjectMember.project_id == Project.id, ProjectMember.user_id == owner_id))
    return or_(Project.owner_id == owner_id, and_(Project.organization_id.is_not(None), or_(organization_admin, assigned_member)))


class ProjectRepository:
    @staticmethod
    def create(db: Session, owner_id: int, data: ProjectCreate) -> Project:
        project = Project(name=data.name, project_type=data.project_type, company_name=data.company_name, description=data.description, owner_id=owner_id)
        db.add(project); db.flush(); return project

    @staticmethod
    def get(db: Session, project_id: int, owner_id: int) -> Project | None:
        return db.scalar(select(Project).where(Project.id == project_id, _visible_project_query(owner_id)))

    @staticmethod
    def list(db: Session, owner_id: int, page: int, page_size: int) -> tuple[list[Project], int]:
        visible = _visible_project_query(owner_id)
        total = db.scalar(select(func.count()).select_from(Project).where(visible)) or 0
        items = list(db.scalars(select(Project).where(visible).order_by(Project.created_at.desc()).offset((page - 1) * page_size).limit(page_size)))
        return items, total

    @staticmethod
    def update(db: Session, project: Project, data: ProjectUpdate) -> Project:
        for field, value in data.model_dump(exclude_unset=True).items(): setattr(project, field, value)
        project.updated_at = datetime.utcnow(); db.flush(); return project

    @staticmethod
    def delete(db: Session, project: Project) -> None:
        db.delete(project); db.flush()


class CompanyProfileRepository:
    @staticmethod
    def get(db: Session, project_id: int) -> CompanyProfile | None:
        return db.scalar(select(CompanyProfile).where(CompanyProfile.project_id == project_id))

    @staticmethod
    def upsert(db: Session, project_id: int, payload: dict) -> CompanyProfile:
        profile = CompanyProfileRepository.get(db, project_id)
        if profile is None: profile = CompanyProfile(project_id=project_id); db.add(profile)
        for field, value in payload.items(): setattr(profile, field, value)
        db.flush(); return profile


class ProjectFileRepository:
    @staticmethod
    def build_storage_path(project_id: int, filename: str) -> str:
        safe_name = Path(filename).name
        return str(Path(f"projects/{project_id}") / f"{uuid.uuid4().hex}_{safe_name}")

    @staticmethod
    def create(db: Session, *, project_id: int, uploader_id: int, filename: str, file_type: str, file_size: int, storage_path: str) -> ProjectFile:
        record = ProjectFile(project_id=project_id, uploader_id=uploader_id, filename=filename, file_type=file_type, file_size=file_size, storage_path=storage_path, parse_status="uploaded")
        db.add(record); db.flush(); return record

    @staticmethod
    def list(db: Session, project_id: int) -> list[ProjectFile]:
        return list(db.scalars(select(ProjectFile).where(ProjectFile.project_id == project_id).order_by(ProjectFile.created_at.desc())))

    @staticmethod
    def get(db: Session, project_id: int, file_id: int) -> ProjectFile | None:
        return db.scalar(select(ProjectFile).where(ProjectFile.id == file_id, ProjectFile.project_id == project_id))

    @staticmethod
    def delete(db: Session, record: ProjectFile) -> None:
        db.delete(record); db.flush()
