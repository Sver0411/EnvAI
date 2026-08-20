from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError, ValidationError
from app.core.config import settings
from app.db.session import get_db
from app.models.knowledge import KnowledgeBase, KnowledgeChunk, KnowledgeDocument, KnowledgeIndexRun
from app.models.user import User
from app.schemas.common import Resp
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    KnowledgeBaseUpdate,
    KnowledgeChunkOut,
    KnowledgeDocumentCreate,
    KnowledgeDocumentOut,
    KnowledgeDocumentStatusOut,
    KnowledgeDocumentUpdate,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services import knowledge_service, storage
from app.services import tenant_service
from app.services.authorization import current_organization

router = APIRouter(tags=["knowledge"])


def _kb_out(db: Session, kb: KnowledgeBase) -> KnowledgeBaseOut:
    count = db.scalar(select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.knowledge_base_id == kb.id, KnowledgeDocument.deleted_at.is_(None))) or 0
    return KnowledgeBaseOut.model_validate(kb).model_copy(update={"document_count": count})


def _doc_out(document: KnowledgeDocument) -> KnowledgeDocumentOut:
    categories = [item.category.code for item in document.categories]
    fields = {
        name: getattr(document, name)
        for name in KnowledgeDocumentOut.model_fields
        if name not in {"categories", "chunk_count"}
    }
    return KnowledgeDocumentOut.model_validate({**fields, "categories": categories, "chunk_count": len(document.chunks) if "chunks" in document.__dict__ else 0})


def _parse_metadata(value: str) -> KnowledgeDocumentCreate:
    try:
        payload = json.loads(value or "{}")
    except json.JSONDecodeError as exc:
        raise ValidationError("metadata 必须是有效 JSON") from exc
    return KnowledgeDocumentCreate.model_validate(payload)


@router.post("/knowledge-bases", response_model=Resp[KnowledgeBaseOut])
def create_knowledge_base(data: KnowledgeBaseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[KnowledgeBaseOut]:
    organization = current_organization(db, current_user)
    kb = KnowledgeBase(name=data.name, description=data.description, scope=data.scope, created_by=current_user.id, organization_id=organization.id if data.scope == "private" else None)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return Resp(data=_kb_out(db, kb))


@router.get("/knowledge-bases", response_model=Resp[list[KnowledgeBaseOut]])
def list_knowledge_bases(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[KnowledgeBaseOut]]:
    return Resp(data=[_kb_out(db, kb) for kb in knowledge_service.list_knowledge_bases(db, current_user)])


@router.get("/knowledge-bases/{knowledge_base_id}", response_model=Resp[KnowledgeBaseOut])
def get_knowledge_base(knowledge_base_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[KnowledgeBaseOut]:
    kb = knowledge_service.get_knowledge_base(db, knowledge_base_id)
    if not knowledge_service.can_access_kb(kb, current_user, db):
        raise NotFoundError("知识库不存在")
    return Resp(data=_kb_out(db, kb))


@router.put("/knowledge-bases/{knowledge_base_id}", response_model=Resp[KnowledgeBaseOut])
def update_knowledge_base(knowledge_base_id: int, data: KnowledgeBaseUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[KnowledgeBaseOut]:
    kb = knowledge_service.get_knowledge_base(db, knowledge_base_id)
    knowledge_service.require_manage_kb(kb, current_user, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(kb, field, value)
    db.commit()
    db.refresh(kb)
    return Resp(data=_kb_out(db, kb))


@router.delete("/knowledge-bases/{knowledge_base_id}", response_model=Resp[None])
def delete_knowledge_base(knowledge_base_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[None]:
    kb = knowledge_service.get_knowledge_base(db, knowledge_base_id)
    knowledge_service.require_manage_kb(kb, current_user, db)
    kb.status = "deleted"
    db.commit()
    return Resp(message="知识库已删除")


@router.post("/knowledge-bases/{knowledge_base_id}/documents", response_model=Resp[KnowledgeDocumentOut])
async def upload_knowledge_document(
    knowledge_base_id: int,
    file: UploadFile = File(...),
    metadata: str = Form(default="{}"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Resp[KnowledgeDocumentOut]:
    kb = knowledge_service.get_knowledge_base(db, knowledge_base_id)
    knowledge_service.require_manage_kb(kb, current_user, db)
    payload = _parse_metadata(metadata)
    ext = storage.validate_upload(file)
    safe_name = Path(file.filename or "document").name
    rel_path = f"knowledge/{knowledge_base_id}/{uuid.uuid4().hex}_{safe_name}"
    backend = storage.get_storage()
    saved = False
    try:
        file_size = backend.save(rel_path, file, max_bytes=settings.max_upload_file_size_bytes)
        saved = True
        path = backend.resolve_path(rel_path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        duplicate = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == knowledge_base_id, KnowledgeDocument.sha256 == digest, KnowledgeDocument.deleted_at.is_(None)))
        if duplicate:
            raise ValidationError("知识库中已存在相同文件（SHA256 重复）")
        document = KnowledgeDocument(knowledge_base_id=knowledge_base_id, title=payload.title or safe_name, document_type=payload.document_type, document_number=knowledge_service.normalize_document_number(payload.document_number), issuing_authority=payload.issuing_authority, publish_date=payload.publish_date, effective_date=payload.effective_date, expiry_date=payload.expiry_date, version=payload.version, revision=payload.revision, status=payload.status, source_url=payload.source_url, original_file_name=safe_name, storage_path=rel_path, mime_type=file.content_type, file_size=file_size, sha256=digest, language=payload.language, country=payload.country, province=payload.province, city=payload.city, district=payload.district, source_authority=payload.source_authority, created_by=current_user.id)
        db.add(document)
        db.flush()
        knowledge_service.update_categories(db, document, payload.category_codes)
        if kb.organization_id:
            tenant_service.enforce_quota(db, kb.organization_id, "storage", file_size)
            tenant_service.record_usage(db, organization_id=kb.organization_id, user_id=current_user.id, usage_type="storage_bytes", quantity=file_size, unit="bytes", source_key=f"knowledge_document:{document.id}:storage", related_resource_type="knowledge_document", related_resource_id=document.id)
        db.commit()
        db.refresh(document)
        return Resp(data=_doc_out(document))
    except Exception:
        if saved:
            backend.delete(rel_path)
        raise


@router.get("/knowledge-bases/{knowledge_base_id}/documents", response_model=Resp[list[KnowledgeDocumentOut]])
def list_knowledge_documents(knowledge_base_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[list[KnowledgeDocumentOut]]:
    return Resp(data=[_doc_out(document) for document in knowledge_service.list_documents(db, knowledge_base_id, current_user)])


@router.get("/knowledge-documents/{document_id}", response_model=Resp[KnowledgeDocumentOut])
def get_knowledge_document(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[KnowledgeDocumentOut]:
    return Resp(data=_doc_out(knowledge_service.get_document(db, document_id, current_user)))


@router.put("/knowledge-documents/{document_id}", response_model=Resp[KnowledgeDocumentOut])
def update_knowledge_document(document_id: int, data: KnowledgeDocumentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[KnowledgeDocumentOut]:
    document = knowledge_service.get_document(db, document_id, current_user)
    knowledge_service.require_manage_kb(document.knowledge_base, current_user, db)
    values = data.model_dump(exclude_unset=True)
    codes = values.pop("category_codes", None)
    if "document_number" in values:
        values["document_number"] = knowledge_service.normalize_document_number(values["document_number"])
    for field, value in values.items():
        setattr(document, field, value)
    if codes is not None:
        knowledge_service.update_categories(db, document, codes)
    db.commit()
    db.refresh(document)
    return Resp(data=_doc_out(document))


@router.delete("/knowledge-documents/{document_id}", response_model=Resp[None])
def delete_knowledge_document(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[None]:
    document = knowledge_service.get_document(db, document_id, current_user)
    knowledge_service.require_manage_kb(document.knowledge_base, current_user, db)
    path = document.storage_path
    document.deleted_at = func.now()
    document.index_status = "failed"
    db.commit()
    if path:
        storage.get_storage().delete(path)
    return Resp(message="知识文档已删除")


@router.post("/knowledge-documents/{document_id}/process", response_model=Resp[KnowledgeDocumentStatusOut])
def process_knowledge_document(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[KnowledgeDocumentStatusOut]:
    document = knowledge_service.get_document(db, document_id, current_user)
    knowledge_service.require_manage_kb(document.knowledge_base, current_user, db)
    try:
        run = knowledge_service.process_document(db, document)
    except Exception as exc:
        raise ValidationError(str(exc)) from exc
    return Resp(data=KnowledgeDocumentStatusOut(document_id=document.id, parser_status=document.parser_status, index_status=document.index_status, error_message=document.error_message, chunks_count=run.chunks_created, embedded_count=run.chunks_embedded, latest_run_id=run.id))


@router.get("/knowledge-documents/{document_id}/status", response_model=Resp[KnowledgeDocumentStatusOut])
def knowledge_document_status(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[KnowledgeDocumentStatusOut]:
    document = knowledge_service.get_document(db, document_id, current_user)
    latest = db.scalar(select(KnowledgeIndexRun).where(KnowledgeIndexRun.knowledge_document_id == document.id).order_by(KnowledgeIndexRun.id.desc()))
    count = db.scalar(select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.knowledge_document_id == document.id)) or 0
    embedded = db.scalar(select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.knowledge_document_id == document.id, KnowledgeChunk.embedding_status == "embedded")) or 0
    return Resp(data=KnowledgeDocumentStatusOut(document_id=document.id, parser_status=document.parser_status, index_status=document.index_status, error_message=document.error_message, chunks_count=count, embedded_count=embedded, latest_run_id=latest.id if latest else None))


@router.get("/knowledge-documents/{document_id}/chunks", response_model=Resp[list[KnowledgeChunkOut]])
def knowledge_document_chunks(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), limit: int = Query(default=200, ge=1, le=1000)) -> Resp[list[KnowledgeChunkOut]]:
    document = knowledge_service.get_document(db, document_id, current_user)
    chunks = list(db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.knowledge_document_id == document.id).order_by(KnowledgeChunk.chunk_index).limit(limit)))
    return Resp(data=[KnowledgeChunkOut.model_validate(chunk) for chunk in chunks])


@router.post("/knowledge/search", response_model=Resp[KnowledgeSearchResponse])
def knowledge_search(data: KnowledgeSearchRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Resp[KnowledgeSearchResponse]:
    # search() itself applies metadata filters; private KB visibility is enforced here.
    visible = {kb.id for kb in knowledge_service.list_knowledge_bases(db, current_user)}
    if data.knowledge_base_ids:
        data.knowledge_base_ids = [item for item in data.knowledge_base_ids if item in visible]
    else:
        data.knowledge_base_ids = list(visible)
    results = knowledge_service.search(db, data)
    return Resp(data=KnowledgeSearchResponse(query=data.query, results=results))
