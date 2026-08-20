from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.generation import DocumentInstance
from app.models.user import User
from app.models.workflow import BatchGenerationItem, BatchGenerationRun, DocumentSectionInstance, DocumentValidationIssue, DocumentValidationRun
from app.schemas.common import Resp
from app.schemas.workflow import BatchGenerationRequest, BatchGenerationRunOut, DocumentPreflightOut, DocumentSectionInstanceOut, ReadinessOut, SectionDependencyIn, SectionReviewIn, SectionReviewOut, ValidationIssueOut, ValidationRunOut
from app.services import generation_service, workflow_service

router = APIRouter(tags=["workflow"])


def _instance(instance_id: int, db: Session, user: User) -> DocumentInstance:
    return generation_service.get_instance(db, instance_id, user)


@router.get("/document-instances/{instance_id}/overview", response_model=Resp[dict])
def document_overview(instance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[dict]:
    instance = _instance(instance_id, db, current_user)
    workflow_service.mark_stale_sections(db, instance, current_user)
    summary = workflow_service.document_preflight(db, instance, current_user)
    sections = workflow_service.list_section_instances(db, instance)
    return Resp(data={"instance": {"id": instance.id, "title": instance.title, "status": instance.status, "template_version": instance.template_version}, "summary": summary, "sections": [DocumentSectionInstanceOut.model_validate(section).model_dump(mode="json") for section in sections]})


@router.post("/document-instances/{instance_id}/preflight", response_model=Resp[DocumentPreflightOut])
def document_preflight(instance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[DocumentPreflightOut]:
    instance = _instance(instance_id, db, current_user)
    workflow_service.mark_stale_sections(db, instance, current_user)
    return Resp(data=DocumentPreflightOut.model_validate(workflow_service.document_preflight(db, instance, current_user)))


@router.post("/document-instances/{instance_id}/generate", response_model=Resp[BatchGenerationRunOut])
def batch_generate(instance_id: int, data: BatchGenerationRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[BatchGenerationRunOut]:
    instance = _instance(instance_id, db, current_user)
    run = workflow_service.batch_generate(db, instance, current_user, data.section_ids)
    return Resp(data=BatchGenerationRunOut.model_validate(run))


@router.get("/batch-generation-runs/{run_id}", response_model=Resp[BatchGenerationRunOut])
def get_batch_run(run_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[BatchGenerationRunOut]:
    run = db.scalar(select(BatchGenerationRun).join(DocumentInstance).where(BatchGenerationRun.id == run_id, DocumentInstance.created_by == current_user.id))
    if run is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("批量生成任务不存在")
    return Resp(data=BatchGenerationRunOut.model_validate(run))


@router.get("/batch-generation-runs/{run_id}/items", response_model=Resp[list[dict]])
def get_batch_items(run_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[dict]]:
    run = db.scalar(select(BatchGenerationRun).join(DocumentInstance).where(BatchGenerationRun.id == run_id, DocumentInstance.created_by == current_user.id))
    if run is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("批量生成任务不存在")
    items = list(db.scalars(select(BatchGenerationItem).where(BatchGenerationItem.batch_run_id == run_id).order_by(BatchGenerationItem.id)))
    return Resp(data=[{"id": item.id, "section_instance_id": item.section_instance_id, "generation_run_id": item.generation_run_id, "status": item.status, "error_message": item.error_message} for item in items])


@router.post("/document-sections/{section_instance_id}/review", response_model=Resp[SectionReviewOut])
def review_section(section_instance_id: int, data: SectionReviewIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[SectionReviewOut]:
    section = workflow_service.get_section_instance(db, section_instance_id, current_user)
    review = workflow_service.review_section(db, section, current_user, data.status, data.comment)
    return Resp(data=SectionReviewOut.model_validate(review))


@router.post("/document-sections/{section_instance_id}/dependencies", response_model=Resp[dict])
def add_section_dependency(section_instance_id: int, data: SectionDependencyIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[dict]:
    section = workflow_service.get_section_instance(db, section_instance_id, current_user)
    depends_on = workflow_service.get_section_instance(db, data.depends_on_section_instance_id, current_user)
    dependency = workflow_service.add_dependency(db, section, depends_on, data.dependency_type)
    return Resp(data={"id": dependency.id, "section_instance_id": dependency.section_instance_id, "depends_on_section_instance_id": dependency.depends_on_section_instance_id, "dependency_type": dependency.dependency_type})


@router.post("/document-sections/{section_instance_id}/lock", response_model=Resp[None])
def lock_section(section_instance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[None]:
    section = workflow_service.get_section_instance(db, section_instance_id, current_user)
    workflow_service.lock_section(db, section, current_user)
    return Resp(message="章节已锁定")


@router.post("/document-sections/{section_instance_id}/unlock", response_model=Resp[None])
def unlock_section(section_instance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[None]:
    section = workflow_service.get_section_instance(db, section_instance_id, current_user)
    workflow_service.unlock_section(db, section, current_user)
    return Resp(message="章节已解锁")


@router.post("/document-instances/{instance_id}/validate", response_model=Resp[ValidationRunOut])
def validate_document(instance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ValidationRunOut]:
    instance = _instance(instance_id, db, current_user)
    run = workflow_service.validate_document(db, instance, current_user)
    return Resp(data=ValidationRunOut.model_validate(run))


@router.get("/document-instances/{instance_id}/validation-issues", response_model=Resp[list[ValidationIssueOut]])
def validation_issues(instance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[ValidationIssueOut]]:
    instance = _instance(instance_id, db, current_user)
    latest = db.scalar(select(DocumentValidationRun).where(DocumentValidationRun.document_instance_id == instance.id).order_by(DocumentValidationRun.id.desc()))
    if latest is None:
        return Resp(data=[])
    issues = list(db.scalars(select(DocumentValidationIssue).where(DocumentValidationIssue.validation_run_id == latest.id).order_by(DocumentValidationIssue.severity, DocumentValidationIssue.id)))
    return Resp(data=[ValidationIssueOut.model_validate(issue) for issue in issues])


@router.get("/document-instances/{instance_id}/readiness", response_model=Resp[ReadinessOut])
def document_readiness(instance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[ReadinessOut]:
    instance = _instance(instance_id, db, current_user)
    return Resp(data=ReadinessOut.model_validate(workflow_service.readiness(db, instance, current_user)))
