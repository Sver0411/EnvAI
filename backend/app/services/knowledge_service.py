from __future__ import annotations

import hashlib
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models.knowledge import (
    KnowledgeBase,
    KnowledgeCategory,
    KnowledgeChunk,
    KnowledgeChunkEmbedding,
    KnowledgeDocument,
    KnowledgeDocumentCategory,
    KnowledgeIndexRun,
)
from app.models.user import User
from app.services.authorization import current_organization, require_permission
from app.services import tenant_service
from app.services import storage
from app.services.document_parser import DocumentParseError, parser_registry
from app.services.embedding import EmbeddingError, cosine_similarity, get_embedding_provider
from app.services.knowledge_chunker import build_knowledge_chunks, chunk_fingerprint
from app.services.reranker import get_reranker

DEFAULT_CATEGORIES = {
    "general_environment": "综合环保",
    "environmental_impact_assessment": "环境影响评价",
    "emergency_response": "应急响应",
    "environmental_risk": "环境风险",
    "waste_gas": "废气",
    "wastewater": "废水",
    "solid_waste": "固体废物",
    "hazardous_waste": "危险废物",
    "noise": "噪声",
    "soil": "土壤",
    "groundwater": "地下水",
    "air": "大气",
    "water": "水环境",
    "ecology": "生态",
    "pollution_permit": "排污许可",
    "acceptance": "竣工验收",
    "chemical_management": "化学品管理",
    "other": "其他",
}


def normalize_document_number(value: str | None) -> str | None:
    if not value:
        return value
    value = re.sub(r"\s+", " ", value.strip().upper())
    return re.sub(r"^([A-Z]{1,4})\s*(\d+)[ -]?(\d{4})$", r"\1 \2-\3", value)


def normalize_query(value: str) -> str:
    value = value.strip().upper().replace("　", " ")
    value = re.sub(r"\s+", " ", value)
    return normalize_document_number(value) or value


def _tokens(value: str) -> list[str]:
    value = normalize_query(value)
    words = re.findall(r"[\u4e00-\u9fff]|[A-Z0-9][A-Z0-9_.\-/]*", value)
    # 对标准号保留完整 token，同时保留数字和字母片段。
    return list(dict.fromkeys(words + ([value] if value else [])))


def ensure_categories(db: Session) -> None:
    existing = {code for code in db.scalars(select(KnowledgeCategory.code))}
    for code, name in DEFAULT_CATEGORIES.items():
        if code not in existing:
            db.add(KnowledgeCategory(code=code, name=name))
    db.flush()


def get_knowledge_base(db: Session, kb_id: int) -> KnowledgeBase:
    kb = db.scalar(select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.status != "deleted"))
    if kb is None:
        raise NotFoundError("知识库不存在")
    return kb


def can_manage_kb(kb: KnowledgeBase, user: User, db: Session | None = None) -> bool:
    if kb.created_by == user.id:
        return True
    if db is not None and kb.organization_id:
        try:
            require_permission(db, user, kb.organization_id, "knowledge.manage")
            return True
        except Exception:
            return False
    return False


def require_manage_kb(kb: KnowledgeBase, user: User, db: Session | None = None) -> None:
    if not can_manage_kb(kb, user, db):
        raise ForbiddenError("没有管理该知识库的权限")


def can_access_kb(kb: KnowledgeBase, user: User, db: Session) -> bool:
    if kb.scope == "system" or kb.created_by == user.id:
        return True
    try:
        return bool(kb.organization_id and current_organization(db, user).id == kb.organization_id)
    except Exception:
        return False


def list_knowledge_bases(db: Session, user: User) -> list[KnowledgeBase]:
    org = current_organization(db, user)
    return list(db.scalars(select(KnowledgeBase).where(KnowledgeBase.status != "deleted", or_(KnowledgeBase.scope == "system", KnowledgeBase.created_by == user.id, KnowledgeBase.organization_id == org.id)).order_by(KnowledgeBase.created_at.desc())))


def list_documents(db: Session, kb_id: int, user: User) -> list[KnowledgeDocument]:
    kb = get_knowledge_base(db, kb_id)
    if not can_access_kb(kb, user, db):
        raise NotFoundError("知识库不存在")
    return list(db.scalars(select(KnowledgeDocument).options(selectinload(KnowledgeDocument.categories), selectinload(KnowledgeDocument.chunks)).where(KnowledgeDocument.knowledge_base_id == kb_id, KnowledgeDocument.deleted_at.is_(None)).order_by(KnowledgeDocument.created_at.desc())))


def get_document(db: Session, document_id: int, user: User) -> KnowledgeDocument:
    document = db.scalar(select(KnowledgeDocument).options(selectinload(KnowledgeDocument.knowledge_base), selectinload(KnowledgeDocument.categories), selectinload(KnowledgeDocument.chunks)).where(KnowledgeDocument.id == document_id, KnowledgeDocument.deleted_at.is_(None)))
    if document is None or not can_access_kb(document.knowledge_base, user, db):
        raise NotFoundError("知识文档不存在")
    return document


def update_categories(db: Session, document: KnowledgeDocument, codes: list[str]) -> None:
    ensure_categories(db)
    wanted = {code for code in codes}
    categories = {item.code: item for item in db.scalars(select(KnowledgeCategory).where(KnowledgeCategory.code.in_(wanted)))}
    missing = wanted - categories.keys()
    if missing:
        raise ValidationError(f"未知知识分类：{', '.join(sorted(missing))}")
    document.categories.clear()
    for category in categories.values():
        document.categories.append(KnowledgeDocumentCategory(category=category))
    db.flush()


def process_document(db: Session, document: KnowledgeDocument) -> KnowledgeIndexRun:
    backend = storage.get_storage()
    run = KnowledgeIndexRun(knowledge_document_id=document.id, status="running", stage="parse")
    db.add(run)
    document.parser_status = "parsing"
    document.index_status = "pending"
    document.error_message = None
    db.flush()
    try:
        path = backend.resolve_path(document.storage_path)
        parser = parser_registry.get_parser(Path(document.original_file_name).suffix.lower())
        result = parser.parse(path)
        document.parser_name = result.parser_name
        document.parser_version = result.parser_version
        document.parsed_text = result.plain_text
        document.parsed_content = result.structured_content()
        document.parser_status = "parsed"
        run.parser_version = result.parser_version
        run.stage = "chunking"
        drafts = build_knowledge_chunks(document.parsed_content, document.parsed_text)
        for old in list(document.chunks):
            db.delete(old)
        db.flush()
        chunks: list[KnowledgeChunk] = []
        for index, draft in enumerate(drafts):
            content_hash, fingerprint, token_count = chunk_fingerprint(document.id, draft)
            chunk = KnowledgeChunk(knowledge_document_id=document.id, chunk_index=index, content=draft.content, content_type=draft.content_type, section_title=draft.section_title, section_level=draft.section_level, section_path=draft.section_path or None, article_number=draft.article_number, page_start=draft.page_start, page_end=draft.page_end, table_index=draft.table_index, structured_table=draft.structured_table, token_count=token_count, character_count=len(draft.content), metadata_json=draft.metadata, content_hash=content_hash, chunk_fingerprint=fingerprint, embedding_status="pending")
            db.add(chunk)
            chunks.append(chunk)
        db.flush()
        run.chunks_created = len(chunks)
        run.token_count = sum(chunk.token_count for chunk in chunks)
        run.stage = "embedding"
        document.index_status = "embedding"
        provider = get_embedding_provider()
        run.embedding_provider, run.embedding_model = provider.name, provider.model
        for start in range(0, len(chunks), 32):
            batch = chunks[start : start + 32]
            vectors = provider.embed_texts([chunk.content for chunk in batch])
            if len(vectors) != len(batch) or any(len(vector) != provider.dimension for vector in vectors):
                raise EmbeddingError("Embedding 返回向量维度不匹配")
            for chunk, vector in zip(batch, vectors):
                chunk.embeddings.append(KnowledgeChunkEmbedding(chunk=chunk, provider=provider.name, model=provider.model, dimension=provider.dimension, version=provider.version, distance_metric="cosine", embedding=vector, token_count=chunk.token_count))
                chunk.embedding_status = "embedded"
                run.chunks_embedded += 1
                db.flush()
                _write_native_embedding(db, chunk.id, vector)
            run.embedding_calls += 1
            db.flush()
        run.stage = "index"
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        document.index_status = "indexed" if run.chunks_embedded == run.chunks_created else "partial"
        if document.knowledge_base.organization_id:
            tenant_service.enforce_quota(db, document.knowledge_base.organization_id, "ai", run.token_count)
            tenant_service.record_usage(db, organization_id=document.knowledge_base.organization_id, user_id=document.created_by, usage_type="embedding_tokens", quantity=run.token_count, unit="tokens", source_key=f"knowledge_index_run:{run.id}:embedding_tokens", provider=run.embedding_provider, model=run.embedding_model, related_resource_type="knowledge_index_run", related_resource_id=run.id)
        db.commit()
        return run
    except Exception as exc:
        db.rollback()
        # 保证失败状态可查询。
        document = db.get(KnowledgeDocument, document.id)
        run = db.get(KnowledgeIndexRun, run.id) if run.id else None
        if document:
            document.parser_status = "failed" if document.parser_status != "parsed" else document.parser_status
            document.index_status = "failed"
            document.error_message = str(exc)[:500]
        if run:
            run.status = "failed"
            run.error_message = str(exc)[:500]
            run.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise DocumentParseError(str(exc)) from exc


def _write_native_embedding(db: Session, chunk_id: int, vector: list[float]) -> None:
    """写入可选 pgvector 列；没有迁移该列的测试/旧环境自动跳过。"""
    if len(vector) != 64:
        return
    if "knowledge_native_vector" not in db.info:
        db.info["knowledge_native_vector"] = bool(db.scalar(text("""SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='knowledge_chunk_embeddings' AND column_name='embedding_vector')""")))
    available = db.info["knowledge_native_vector"]
    if not available:
        return
    literal = "[" + ",".join(f"{float(value):.8f}" for value in vector) + "]"
    db.execute(text("UPDATE knowledge_chunk_embeddings SET embedding_vector = CAST(:value AS vector) WHERE chunk_id = :chunk_id"), {"value": literal, "chunk_id": chunk_id})


def _metadata_match(document: KnowledgeDocument, request) -> bool:
    if request.document_types and document.document_type not in request.document_types:
        return False
    if request.knowledge_base_ids and document.knowledge_base_id not in request.knowledge_base_ids:
        return False
    if request.statuses and document.status not in request.statuses:
        return False
    if request.document_number and normalize_query(request.document_number) not in normalize_query(document.document_number or ""):
        return False
    jurisdictions = [item for item in (document.country, document.province, document.city, document.district) if item]
    if request.jurisdictions and not any(value in jurisdictions for value in request.jurisdictions):
        return False
    if request.effective_date and document.effective_date and document.effective_date > request.effective_date:
        return False
    if request.categories:
        codes = {item.category.code for item in document.categories}
        if not codes.intersection(request.categories):
            return False
    return True


def search(db: Session, request) -> list[dict]:
    query = normalize_query(request.query)
    base_query = select(KnowledgeChunk).options(selectinload(KnowledgeChunk.document).selectinload(KnowledgeDocument.categories), selectinload(KnowledgeChunk.embeddings)).join(KnowledgeDocument).where(KnowledgeDocument.deleted_at.is_(None), KnowledgeDocument.index_status.in_(["indexed", "partial"]))
    if request.knowledge_base_ids:
        # Tenant visibility is applied in SQL before keyword/vector ranking;
        # untrusted content from another organization never enters reranking.
        base_query = base_query.where(KnowledgeDocument.knowledge_base_id.in_(request.knowledge_base_ids))
    chunks = list(db.scalars(base_query))
    chunks = [chunk for chunk in chunks if _metadata_match(chunk.document, request)]
    terms = _tokens(query)
    keyword_ranked: list[tuple[KnowledgeChunk, float]] = []
    for chunk in chunks:
        haystack = " ".join([chunk.content, chunk.section_title or "", chunk.document.title, chunk.document.document_number or ""]).upper()
        hits = sum(1 for term in terms if term and term in haystack)
        if hits:
            score = hits / max(len(terms), 1)
            if chunk.document.document_number and query.replace(" ", "") in chunk.document.document_number.replace(" ", ""):
                score += 1.0
            keyword_ranked.append((chunk, score))
    keyword_ranked.sort(key=lambda item: item[1], reverse=True)
    keyword_ranked = keyword_ranked[: settings.search_keyword_top_k]
    provider = get_embedding_provider()
    query_vector = provider.embed_texts([query])[0]
    vector_ranked: list[tuple[KnowledgeChunk, float]] = []
    native_scores = _native_vector_scores(db, query_vector, request.knowledge_base_ids)
    if native_scores:
        vector_ranked = [(chunk, native_scores[chunk.id]) for chunk in chunks if chunk.id in native_scores]
    else:
        for chunk in chunks:
            if chunk.embeddings:
                vector_ranked.append((chunk, cosine_similarity(query_vector, chunk.embeddings[0].embedding)))
    vector_ranked.sort(key=lambda item: item[1], reverse=True)
    vector_ranked = vector_ranked[: settings.search_vector_top_k]
    keyword_scores = {chunk.id: score for chunk, score in keyword_ranked}
    vector_scores = {chunk.id: score for chunk, score in vector_ranked}
    keyword_positions = {chunk.id: index + 1 for index, (chunk, _) in enumerate(keyword_ranked)}
    vector_positions = {chunk.id: index + 1 for index, (chunk, _) in enumerate(vector_ranked)}
    candidates = {chunk.id: chunk for chunk, _ in keyword_ranked + vector_ranked}
    results = []
    for chunk in candidates.values():
        rrf = (1 / (60 + keyword_positions[chunk.id]) if chunk.id in keyword_positions else 0) + (1 / (60 + vector_positions[chunk.id]) if chunk.id in vector_positions else 0)
        # active 文档优先，但历史版本仍参与检索。
        if chunk.document.status == "active":
            rrf *= 1.05
        results.append({"chunk_id": chunk.id, "document_id": chunk.document.id, "document_title": chunk.document.title, "document_number": chunk.document.document_number, "document_type": chunk.document.document_type, "categories": [item.category.code for item in chunk.document.categories], "jurisdiction": {"country": chunk.document.country, "province": chunk.document.province, "city": chunk.document.city, "district": chunk.document.district}, "version": chunk.document.version, "status": chunk.document.status, "section_title": chunk.section_title, "section_path": chunk.section_path, "article_number": chunk.article_number, "page_start": chunk.page_start, "page_end": chunk.page_end, "content": chunk.content, "vector_score": vector_scores.get(chunk.id), "keyword_score": keyword_scores.get(chunk.id, 0.0), "rerank_score": None, "final_score": rrf})
    results.sort(key=lambda item: item["final_score"], reverse=True)
    return get_reranker().rerank(query, results[: request.top_k])


def _native_vector_scores(db: Session, vector: list[float], knowledge_base_ids: list[int] | None = None) -> dict[int, float]:
    """优先使用 pgvector cosine distance；无原生列时返回空字典触发 JSON 回退。"""
    if "knowledge_native_vector" not in db.info:
        db.info["knowledge_native_vector"] = bool(db.scalar(text("""SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='knowledge_chunk_embeddings' AND column_name='embedding_vector')""")))
    if not db.info["knowledge_native_vector"]:
        return {}
    literal = "[" + ",".join(f"{float(value):.8f}" for value in vector) + "]"
    tenant_clause = ""
    params = {"value": literal}
    if knowledge_base_ids:
        tenant_clause = " AND kc.knowledge_document_id IN (SELECT id FROM knowledge_documents WHERE knowledge_base_id = ANY(:kb_ids))"
        params["kb_ids"] = knowledge_base_ids
    rows = db.execute(text(f"SELECT e.chunk_id, 1 - (e.embedding_vector <=> CAST(:value AS vector)) AS score FROM knowledge_chunk_embeddings e JOIN knowledge_chunks kc ON kc.id = e.chunk_id WHERE e.embedding_vector IS NOT NULL{tenant_clause}"), params).all()  # nosec B608
    return {int(chunk_id): float(score) for chunk_id, score in rows}
