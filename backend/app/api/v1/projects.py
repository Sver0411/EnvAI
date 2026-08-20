from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.db.session import get_db
from app.models.user import User
from app.repositories.project_repository import ProjectFileRepository
from app.schemas.common import Resp
from app.schemas.company_profile import CompanyProfileOut, CompanyProfileWrite
from app.schemas.project import (
    ProjectCreate,
    ProjectOut,
    ProjectPage,
    ProjectUpdate,
)
from app.schemas.project_file import ProjectFileOut
from app.schemas.parsed_document import ParsedDocumentOut, ParsedDocumentStatusOut
from app.schemas.structured_data import (
    ConflictResolveIn,
    DataConflictOut,
    ExtractedFactOut,
    ExtractionRunOut,
    EnvironmentalFacilityOut,
    ProductOut,
    ProductionEquipmentOut,
    RawMaterialOut,
    StructuredDataUpdate,
    StructuredProjectDataOut,
)
from app.services import document_parsing_service, project_service, storage
from app.services.document_parser import DocumentParseError
from app.services import structured_data_service
from app.services.authorization import current_organization
from app.services.authorization import require_project_permission
from app.models.tenant import ProjectMember
from app.services import tenant_service

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("", response_model=Resp[ProjectOut])
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[ProjectOut]:
    project = project_service.create_project(db, current_user.id, data)
    organization = current_organization(db, current_user)
    tenant_service.enforce_quota(db, organization.id, "project")
    project.organization_id = organization.id
    db.add(ProjectMember(project_id=project.id, user_id=current_user.id, project_role="owner"))
    db.commit()
    db.refresh(project)
    return Resp(data=ProjectOut.model_validate(project))


@router.get("", response_model=Resp[ProjectPage])
def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[ProjectPage]:
    items, total = project_service.list_projects(db, current_user.id, page, page_size)
    return Resp(
        data=ProjectPage(
            items=[ProjectOut.model_validate(p) for p in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/{project_id}", response_model=Resp[ProjectOut])
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[ProjectOut]:
    project = project_service.get_project(db, project_id, current_user.id)
    return Resp(data=ProjectOut.model_validate(project))


@router.put("/{project_id}", response_model=Resp[ProjectOut])
def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[ProjectOut]:
    project = project_service.update_project(db, project_id, current_user.id, data)
    db.commit()
    db.refresh(project)
    return Resp(data=ProjectOut.model_validate(project))


@router.delete("/{project_id}", response_model=Resp[None])
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[None]:
    file_paths = [record.storage_path for record in project_service.list_project_files(db, project_id, current_user.id)]
    project_service.delete_project(db, project_id, current_user.id)
    db.commit()
    backend = storage.get_storage()
    for path in file_paths:
        if path:
            backend.delete(path)
    return Resp(message="已删除")


@router.get("/{project_id}/profile", response_model=Resp[CompanyProfileOut])
def get_company_profile(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[CompanyProfileOut]:
    profile = project_service.get_company_profile(db, project_id, current_user.id)
    return Resp(data=CompanyProfileOut.model_validate(profile))


@router.put("/{project_id}/profile", response_model=Resp[CompanyProfileOut])
def upsert_company_profile(
    project_id: int,
    data: CompanyProfileWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[CompanyProfileOut]:
    profile = project_service.upsert_company_profile(db, project_id, current_user.id, data)
    db.commit()
    db.refresh(profile)
    return Resp(data=CompanyProfileOut.model_validate(profile))


@router.get("/{project_id}/files", response_model=Resp[list[ProjectFileOut]])
def list_project_files(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[list[ProjectFileOut]]:
    files = project_service.list_project_files(db, project_id, current_user.id)
    return Resp(data=[ProjectFileOut.model_validate(f) for f in files])


@router.post("/{project_id}/files", response_model=Resp[list[ProjectFileOut]])
async def upload_project_file(
    project_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[list[ProjectFileOut]]:
    project = project_service.get_project(db, project_id, current_user.id)
    require_project_permission(db, current_user, project, "projects.update")
    if len(files) > settings.max_upload_files_per_request:
        raise ValidationError(f"单次最多上传 {settings.max_upload_files_per_request} 个文件")
    backend = storage.get_storage()
    records = []
    saved_paths: list[str] = []
    try:
        for file in files:
            ext = storage.validate_upload(file)
            rel_path = ProjectFileRepository.build_storage_path(project_id, file.filename or "file")
            file_size = backend.save(
                rel_path,
                file,
                max_bytes=settings.max_upload_file_size_bytes,
            )
            saved_paths.append(rel_path)
            records.append(
                ProjectFileRepository.create(
                    db,
                    project_id=project_id,
                    uploader_id=current_user.id,
                    filename=Path(file.filename or "file").name,
                    file_type=ext.lstrip("."),
                    file_size=file_size,
                    storage_path=rel_path,
                )
            )
        organization = current_organization(db, current_user)
        tenant_service.enforce_quota(db, organization.id, "storage", sum(record.file_size for record in records))
        db.commit()
        for record in records:
            tenant_service.record_usage(db, organization_id=organization.id, user_id=current_user.id, project_id=project_id, usage_type="storage_bytes", quantity=record.file_size, unit="bytes", source_key=f"project_file:{record.id}:storage", related_resource_type="project_file", related_resource_id=record.id)
        db.commit()
        for record in records:
            db.refresh(record)
    except Exception:
        # 首个文件校验失败时尚未写入数据库；避免中断外层测试事务。
        if records:
            db.rollback()
        for path in saved_paths:
            backend.delete(path)
        raise
    return Resp(data=[ProjectFileOut.model_validate(record) for record in records])


@router.get("/{project_id}/files/{file_id}/download")
def download_project_file(
    project_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    record = project_service.get_project_file(db, project_id, file_id, current_user.id)
    if not record.storage_path:
        raise ValidationError("文件存储路径不存在")
    path = storage.get_storage().resolve_path(record.storage_path)
    if not path.is_file():
        raise ValidationError("文件实体不存在")
    return FileResponse(path, filename=record.filename, media_type="application/octet-stream")


@router.get("/{project_id}/files/{file_id}", response_model=Resp[ProjectFileOut])
def get_project_file(
    project_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[ProjectFileOut]:
    record = project_service.get_project_file(db, project_id, file_id, current_user.id)
    return Resp(data=ProjectFileOut.model_validate(record))


@router.delete("/{project_id}/files/{file_id}", response_model=Resp[None])
def delete_project_file(
    project_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[None]:
    record = project_service.delete_project_file(db, project_id, file_id, current_user.id)
    storage_path = record.storage_path
    db.commit()
    if storage_path:
        storage.get_storage().delete(storage_path)
    return Resp(message="文件已删除")


def _status_response(file_record, document) -> ParsedDocumentStatusOut:
    if document is None:
        return ParsedDocumentStatusOut(project_file_id=file_record.id, status="pending")
    content = document.structured_content or {}
    return ParsedDocumentStatusOut(
        project_file_id=file_record.id,
        status=document.status,
        parser_name=document.parser_name,
        parser_version=document.parser_version,
        error_message=document.error_message,
        parsed_at=document.parsed_at,
        warnings=list(content.get("warnings", [])),
    )


@router.post("/{project_id}/files/{file_id}/parse", response_model=Resp[ParsedDocumentStatusOut])
def parse_project_file(
    project_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[ParsedDocumentStatusOut]:
    file_record = project_service.get_project_file(db, project_id, file_id, current_user.id)
    try:
        document = document_parsing_service.parse_file(db, file_record)
    except DocumentParseError as exc:
        raise ValidationError(str(exc)) from exc
    return Resp(data=_status_response(file_record, document))


@router.get("/{project_id}/files/{file_id}/parse-status", response_model=Resp[ParsedDocumentStatusOut])
def get_parse_status(
    project_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[ParsedDocumentStatusOut]:
    file_record, document = project_service.get_parse_status(db, project_id, file_id, current_user.id)
    return Resp(data=_status_response(file_record, document))


@router.get("/{project_id}/files/{file_id}/parsed", response_model=Resp[ParsedDocumentOut])
def get_parsed_document(
    project_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[ParsedDocumentOut]:
    document = project_service.get_parsed_document(db, project_id, file_id, current_user.id)
    return Resp(data=ParsedDocumentOut.model_validate(document))


def _fact_out(fact, filename: str | None = None) -> ExtractedFactOut:
    return ExtractedFactOut.model_validate(fact).model_copy(update={"source_filename": filename})


def _structured_data_out(data: dict) -> StructuredProjectDataOut:
    profile = data["profile"]
    return StructuredProjectDataOut(
        profile=CompanyProfileOut.model_validate(profile).model_dump(mode="json") if profile else None,
        products=[ProductOut.model_validate(item) for item in data["products"]],
        equipment=[ProductionEquipmentOut.model_validate(item) for item in data["equipment"]],
        raw_materials=[RawMaterialOut.model_validate(item) for item in data["raw_materials"]],
        environmental_facilities=[EnvironmentalFacilityOut.model_validate(item) for item in data["environmental_facilities"]],
        facts=[_fact_out(fact, filename) for fact, filename in data["facts"]],
        conflicts=[DataConflictOut.model_validate(item) for item in data["conflicts"]],
        latest_run=ExtractionRunOut.model_validate(data["latest_run"]) if data["latest_run"] else None,
    )


@router.post("/{project_id}/extract", response_model=Resp[ExtractionRunOut])
def extract_project_data(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[ExtractionRunOut]:
    project_service.get_project(db, project_id, current_user.id)
    try:
        run = structured_data_service.run_extraction(db, project_id)
    except Exception as exc:
        raise ValidationError("项目抽取失败，请检查已解析文件") from exc
    return Resp(data=ExtractionRunOut.model_validate(run))


@router.get("/{project_id}/extraction-status", response_model=Resp[ExtractionRunOut | None])
def get_extraction_status(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[ExtractionRunOut | None]:
    project_service.get_project(db, project_id, current_user.id)
    run = structured_data_service.latest_run(db, project_id)
    return Resp(data=ExtractionRunOut.model_validate(run) if run else None)


@router.get("/{project_id}/extracted-data", response_model=Resp[StructuredProjectDataOut])
def get_extracted_data(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[StructuredProjectDataOut]:
    return Resp(data=_structured_data_out(structured_data_service.get_project_data(db, project_id, current_user.id)))


@router.get("/{project_id}/extracted-facts", response_model=Resp[list[ExtractedFactOut]])
def get_extracted_facts(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[list[ExtractedFactOut]]:
    return Resp(data=[_fact_out(fact, filename) for fact, filename in structured_data_service.list_facts(db, project_id, current_user.id)])


@router.get("/{project_id}/conflicts", response_model=Resp[list[DataConflictOut]])
def get_data_conflicts(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[list[DataConflictOut]]:
    return Resp(data=[DataConflictOut.model_validate(item) for item in structured_data_service.list_conflicts(db, project_id, current_user.id)])


@router.post("/{project_id}/extracted-facts/{fact_id}/accept", response_model=Resp[ExtractedFactOut])
def accept_extracted_fact(
    project_id: int,
    fact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[ExtractedFactOut]:
    fact = structured_data_service.accept_fact(db, project_id, fact_id, current_user.id)
    filename = next((name for item, name in structured_data_service.list_facts(db, project_id, current_user.id) if item.id == fact.id), None)
    return Resp(data=_fact_out(fact, filename))


@router.post("/{project_id}/extracted-facts/{fact_id}/reject", response_model=Resp[ExtractedFactOut])
def reject_extracted_fact(
    project_id: int,
    fact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[ExtractedFactOut]:
    fact = structured_data_service.reject_fact(db, project_id, fact_id, current_user.id)
    return Resp(data=_fact_out(fact))


@router.post("/{project_id}/conflicts/{conflict_id}/resolve", response_model=Resp[DataConflictOut])
def resolve_data_conflict(
    project_id: int,
    conflict_id: int,
    data: ConflictResolveIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[DataConflictOut]:
    conflict = structured_data_service.resolve_conflict(
        db, project_id, conflict_id, current_user.id, data.resolution, data.note
    )
    return Resp(data=DataConflictOut.model_validate(conflict))


def _update_structured_entity(project_id: int, entity_type: str, entity_id: int, data: StructuredDataUpdate, db: Session, current_user: User):
    return structured_data_service.update_entity(
        db, project_id, current_user.id, entity_type, entity_id, data.model_dump(exclude_unset=True)
    )


@router.put("/{project_id}/products/{entity_id}", response_model=Resp[ProductOut])
def update_product(project_id: int, entity_id: int, data: StructuredDataUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ProductOut]:
    return Resp(data=ProductOut.model_validate(_update_structured_entity(project_id, "product", entity_id, data, db, current_user)))


@router.put("/{project_id}/equipment/{entity_id}", response_model=Resp[ProductionEquipmentOut])
def update_equipment(project_id: int, entity_id: int, data: StructuredDataUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ProductionEquipmentOut]:
    return Resp(data=ProductionEquipmentOut.model_validate(_update_structured_entity(project_id, "production_equipment", entity_id, data, db, current_user)))


@router.put("/{project_id}/raw-materials/{entity_id}", response_model=Resp[RawMaterialOut])
def update_raw_material(project_id: int, entity_id: int, data: StructuredDataUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[RawMaterialOut]:
    return Resp(data=RawMaterialOut.model_validate(_update_structured_entity(project_id, "raw_material", entity_id, data, db, current_user)))


@router.put("/{project_id}/environmental-facilities/{entity_id}", response_model=Resp[EnvironmentalFacilityOut])
def update_environmental_facility(project_id: int, entity_id: int, data: StructuredDataUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[EnvironmentalFacilityOut]:
    return Resp(data=EnvironmentalFacilityOut.model_validate(_update_structured_entity(project_id, "environmental_facility", entity_id, data, db, current_user)))


def _delete_structured_entity(project_id: int, entity_type: str, entity_id: int, db: Session, current_user: User) -> Resp[None]:
    structured_data_service.delete_entity(db, project_id, current_user.id, entity_type, entity_id)
    return Resp(message="结构化数据已删除")


@router.delete("/{project_id}/products/{entity_id}", response_model=Resp[None])
def delete_product(project_id: int, entity_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[None]:
    return _delete_structured_entity(project_id, "product", entity_id, db, current_user)


@router.delete("/{project_id}/equipment/{entity_id}", response_model=Resp[None])
def delete_equipment(project_id: int, entity_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[None]:
    return _delete_structured_entity(project_id, "production_equipment", entity_id, db, current_user)


@router.delete("/{project_id}/raw-materials/{entity_id}", response_model=Resp[None])
def delete_raw_material(project_id: int, entity_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[None]:
    return _delete_structured_entity(project_id, "raw_material", entity_id, db, current_user)
