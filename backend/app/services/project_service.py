from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.export import ReportFigure
from app.core.exceptions import NotFoundError
from app.models.project import Project
from app.models.user import User
from app.models.parsed_document import ParsedDocument
from app.models.project_file import ProjectFile
from app.repositories.project_repository import (
    CompanyProfileRepository,
    ProjectFileRepository,
    ProjectRepository,
)
from app.schemas.company_profile import CompanyProfileWrite
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.repositories.parsed_document_repository import ParsedDocumentRepository
from app.services.authorization import require_project_permission


def create_project(db: Session, owner_id: int, data: ProjectCreate) -> Project:
    return ProjectRepository.create(db, owner_id, data)


def get_project(db: Session, project_id: int, owner_id: int) -> Project:
    project = ProjectRepository.get(db, project_id, owner_id)
    if project is None:
        raise NotFoundError("项目不存在")
    return project


def list_projects(db: Session, owner_id: int, page: int, page_size: int) -> tuple[list[Project], int]:
    return ProjectRepository.list(db, owner_id, page, page_size)


def update_project(db: Session, project_id: int, owner_id: int, data: ProjectUpdate) -> Project:
    project = get_project(db, project_id, owner_id)
    require_project_permission(db, db.get(User, owner_id), project, "projects.update")
    return ProjectRepository.update(db, project, data)


def delete_project(db: Session, project_id: int, owner_id: int) -> None:
    project = get_project(db, project_id, owner_id)
    require_project_permission(db, db.get(User, owner_id), project, "projects.delete")
    # 图表引用项目文件时使用 RESTRICT，先清理这些引用，避免项目明明有
    # 删除权限却因为历史报告图表而静默失败。
    file_ids = select(ProjectFile.id).where(ProjectFile.project_id == project.id)
    db.execute(delete(ReportFigure).where(ReportFigure.project_file_id.in_(file_ids)))
    ProjectRepository.delete(db, project)


def get_company_profile(db: Session, project_id: int, owner_id: int):
    get_project(db, project_id, owner_id)  # 校验项目归属
    profile = CompanyProfileRepository.get(db, project_id)
    if profile is None:
        raise NotFoundError("企业资料尚未填写")
    return profile


def upsert_company_profile(db: Session, project_id: int, owner_id: int, data: CompanyProfileWrite):
    project = get_project(db, project_id, owner_id)
    require_project_permission(db, db.get(User, owner_id), project, "projects.update")
    return CompanyProfileRepository.upsert(db, project_id, data.model_dump(exclude_unset=True))


def list_project_files(db: Session, project_id: int, owner_id: int):
    get_project(db, project_id, owner_id)  # 校验项目归属
    return ProjectFileRepository.list(db, project_id)


def get_project_file(db: Session, project_id: int, file_id: int, owner_id: int):
    get_project(db, project_id, owner_id)  # 校验项目归属
    record = ProjectFileRepository.get(db, project_id, file_id)
    if record is None:
        raise NotFoundError("项目文件不存在")
    return record


def delete_project_file(db: Session, project_id: int, file_id: int, owner_id: int):
    record = get_project_file(db, project_id, file_id, owner_id)
    require_project_permission(db, db.get(User, owner_id), record.project, "projects.update")
    ProjectFileRepository.delete(db, record)
    return record


def get_parsed_document(db: Session, project_id: int, file_id: int, owner_id: int) -> ParsedDocument:
    get_project_file(db, project_id, file_id, owner_id)
    document = ParsedDocumentRepository.get(db, file_id)
    if document is None:
        raise NotFoundError("文件尚未解析")
    return document


def get_parse_status(db: Session, project_id: int, file_id: int, owner_id: int) -> tuple[ProjectFile, ParsedDocument | None]:
    file_record = get_project_file(db, project_id, file_id, owner_id)
    return file_record, ParsedDocumentRepository.get(db, file_id)
