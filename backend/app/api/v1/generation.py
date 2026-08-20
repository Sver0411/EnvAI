from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.generation import DocumentInstance, GenerationSource, SectionCitation, SectionDraft, SectionGenerationRun, TemplateSection
from app.models.workflow import DocumentSectionInstance
from app.models.user import User
from app.schemas.common import Resp
from app.schemas.generation import (
    DocumentInstanceCreate,
    DocumentInstanceOut,
    DocumentTemplateOut,
    GenerationRunOut,
    GenerationSourceOut,
    SectionCitationOut,
    SectionDraftOut,
    SectionDraftUpdate,
    SectionPreflightOut,
    SectionViewOut,
    TemplateSectionOut,
)
from app.services import generation_service

router = APIRouter(tags=["generation"])


def _section_out(section: TemplateSection, children: list[TemplateSection] | None = None) -> TemplateSectionOut:
    values = {name: getattr(section, name) for name in TemplateSectionOut.model_fields if name != "children"}
    return TemplateSectionOut.model_validate({**values, "children": [_section_out(child) for child in (children if children is not None else section.children)]})


def _template_out(template) -> DocumentTemplateOut:
    roots = [section for section in template.sections if section.parent_id is None]
    by_parent: dict[int | None, list] = {}
    for section in template.sections:
        by_parent.setdefault(section.parent_id, []).append(section)
    def build(section):
        return _section_out(section, by_parent.get(section.id, []))
    return DocumentTemplateOut.model_validate({"id": template.id, "name": template.name, "code": template.code, "document_type": template.document_type, "description": template.description, "version": template.version, "status": template.status, "sections": [build(root) for root in sorted(roots, key=lambda item: item.sort_order)]})


def _draft_out(draft: SectionDraft | None) -> SectionDraftOut | None:
    if draft is None:
        return None
    citations = [item if isinstance(item, dict) else {"source_id": str(item), "claim": ""} for item in (draft.citations or [])]
    return SectionDraftOut.model_validate({"id": draft.id, "project_id": draft.project_id, "document_instance_id": draft.document_instance_id, "template_id": draft.template_id, "section_id": draft.section_id, "generation_run_id": draft.generation_run_id, "content": generation_service.strip_markdown(draft.content or ""), "ai_original_content": generation_service.strip_markdown(draft.ai_original_content or ""), "status": draft.status, "version": draft.version, "citations": citations, "missing_information": generation_service.normalize_missing_information(draft.missing_information), "warnings": draft.warnings or [], "generation_metadata": draft.generation_metadata, "created_at": draft.created_at, "updated_at": draft.updated_at})


@router.get("/document-templates", response_model=Resp[list[DocumentTemplateOut]])
def list_document_templates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[DocumentTemplateOut]]:
    return Resp(data=[_template_out(template) for template in generation_service.list_templates(db)])


@router.get("/document-templates/{template_id}/sections", response_model=Resp[list[TemplateSectionOut]])
def get_template_sections(template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[TemplateSectionOut]]:
    template = generation_service.get_template(db, template_id)
    return Resp(data=_template_out(template).sections)


@router.post("/projects/{project_id}/document-instances", response_model=Resp[DocumentInstanceOut])
def create_document_instance(project_id: int, data: DocumentInstanceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[DocumentInstanceOut]:
    instance = generation_service.create_instance(db, project_id, current_user, data.template_id, data.title, data.reference_date)
    return Resp(data=DocumentInstanceOut.model_validate(instance))


@router.get("/projects/{project_id}/document-instances", response_model=Resp[list[DocumentInstanceOut]])
def list_document_instances(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[DocumentInstanceOut]]:
    generation_service.project_service.get_project(db, project_id, current_user.id)
    rows = list(db.scalars(select(DocumentInstance).where(DocumentInstance.project_id == project_id, DocumentInstance.created_by == current_user.id).order_by(DocumentInstance.created_at.desc())))
    return Resp(data=[DocumentInstanceOut.model_validate(row) for row in rows])


@router.get("/document-instances/{instance_id}", response_model=Resp[DocumentInstanceOut])
def get_document_instance(instance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[DocumentInstanceOut]:
    return Resp(data=DocumentInstanceOut.model_validate(generation_service.get_instance(db, instance_id, current_user)))


def _instance_section(db: Session, instance: DocumentInstance, section_id: int) -> TemplateSection:
    return generation_service.get_section(db, instance.template_id, section_id)


@router.get("/document-instances/{instance_id}/sections/{section_id}", response_model=Resp[SectionViewOut])
def get_instance_section(instance_id: int, section_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[SectionViewOut]:
    instance = generation_service.get_instance(db, instance_id, current_user)
    section = _instance_section(db, instance, section_id)
    draft = db.scalar(select(SectionDraft).where(SectionDraft.document_instance_id == instance.id, SectionDraft.section_id == section.id))
    return Resp(data=SectionViewOut(section=_section_out(section), draft=_draft_out(draft)))


@router.post("/document-instances/{instance_id}/sections/{section_id}/preflight", response_model=Resp[SectionPreflightOut])
def section_preflight(instance_id: int, section_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[SectionPreflightOut]:
    instance = generation_service.get_instance(db, instance_id, current_user)
    section = _instance_section(db, instance, section_id)
    result, _ = generation_service.preflight(db, instance, section, current_user)
    return Resp(data=result)


@router.post("/document-instances/{instance_id}/sections/{section_id}/generate", response_model=Resp[GenerationRunOut])
def generate_section(instance_id: int, section_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[GenerationRunOut]:
    instance = generation_service.get_instance(db, instance_id, current_user)
    section = _instance_section(db, instance, section_id)
    snapshot = db.scalar(select(DocumentSectionInstance).where(DocumentSectionInstance.document_instance_id == instance.id, DocumentSectionInstance.template_section_id == section.id))
    if snapshot and snapshot.status == "locked":
        from app.core.exceptions import ValidationError
        raise ValidationError("章节已锁定，解锁后才能重新生成")
    run = generation_service.generate_section(db, instance, section, current_user)
    return Resp(data=GenerationRunOut.model_validate(run))


@router.get("/generation-runs/{run_id}", response_model=Resp[GenerationRunOut])
def get_generation_run(run_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[GenerationRunOut]:
    run = db.scalar(select(SectionGenerationRun).where(SectionGenerationRun.id == run_id, SectionGenerationRun.project_id.in_(select(DocumentInstance.project_id).where(DocumentInstance.created_by == current_user.id))))
    if run is None:
        raise NotFoundError("生成运行不存在")
    return Resp(data=GenerationRunOut.model_validate(run))


@router.get("/generation-runs/{run_id}/sources", response_model=Resp[list[GenerationSourceOut]])
def get_generation_sources(run_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[GenerationSourceOut]]:
    run = db.scalar(select(SectionGenerationRun).where(SectionGenerationRun.id == run_id, SectionGenerationRun.project_id.in_(select(DocumentInstance.project_id).where(DocumentInstance.created_by == current_user.id))))
    if run is None:
        raise NotFoundError("生成运行不存在")
    rows = list(db.scalars(select(GenerationSource).where(GenerationSource.generation_run_id == run_id).order_by(GenerationSource.rank)))
    return Resp(data=[GenerationSourceOut.model_validate({"id": row.id, "source_type": row.source_type, "source_id": row.source_id, "context_source_id": row.context_source_id, "rank": row.rank, "score": row.score, "metadata_json": row.metadata_json}) for row in rows])


@router.put("/section-drafts/{draft_id}", response_model=Resp[SectionDraftOut])
def update_section_draft(draft_id: int, data: SectionDraftUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[SectionDraftOut]:
    return Resp(data=_draft_out(generation_service.update_draft(db, draft_id, current_user, data.content)))


@router.get("/section-drafts/{draft_id}/citations", response_model=Resp[list[SectionCitationOut]])
def get_section_citations(draft_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[SectionCitationOut]]:
    draft = db.scalar(select(SectionDraft).where(SectionDraft.id == draft_id, SectionDraft.created_by == current_user.id))
    if draft is None:
        raise NotFoundError("章节草稿不存在")
    rows = list(db.scalars(select(SectionCitation).where(SectionCitation.section_draft_id == draft_id).order_by(SectionCitation.citation_order)))
    return Resp(data=[SectionCitationOut.model_validate(row) for row in rows])
