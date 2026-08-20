from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.generation import DocumentInstance, GenerationSource, SectionCitation, SectionDraft, SectionDraftVersion, SectionGenerationRun, TemplateSection
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.company_profile import CompanyProfile
from app.models.structured_data import DataConflict, EnvironmentalFacility, ExtractedFact, Product, ProductionEquipment, RawMaterial
from app.models.user import User
from app.models.workflow import (
    AuditEvent,
    BatchGenerationItem,
    BatchGenerationRun,
    DocumentSectionInstance,
    DocumentValidationIssue,
    DocumentValidationRun,
    SectionDependency,
    SectionReview,
)
from app.schemas.generation import SectionPreflightOut
from app.services import generation_service
from app.services.authorization import require_project_permission


def audit(db: Session, user: User, action: str, instance: DocumentInstance | None = None, section: DocumentSectionInstance | None = None, metadata: dict[str, Any] | None = None) -> None:
    db.add(AuditEvent(user_id=user.id, project_id=instance.project_id if instance else None, document_instance_id=instance.id if instance else None, section_instance_id=section.id if section else None, action=action, metadata_json=metadata or {}))


def get_section_instance(db: Session, section_instance_id: int, user: User) -> DocumentSectionInstance:
    section = db.scalar(select(DocumentSectionInstance).join(DocumentInstance).where(DocumentSectionInstance.id == section_instance_id, DocumentInstance.created_by == user.id))
    if section is None:
        raise NotFoundError("报告章节不存在")
    return section


def list_section_instances(db: Session, instance: DocumentInstance) -> list[DocumentSectionInstance]:
    return list(db.scalars(select(DocumentSectionInstance).where(DocumentSectionInstance.document_instance_id == instance.id).order_by(DocumentSectionInstance.sort_order, DocumentSectionInstance.id)))


def _dependency_ready(db: Session, section: DocumentSectionInstance) -> tuple[bool, str | None]:
    dependencies = list(db.scalars(select(SectionDependency).where(SectionDependency.section_instance_id == section.id)))
    for dependency in dependencies:
        required = db.get(DocumentSectionInstance, dependency.depends_on_section_instance_id)
        if required is None:
            return False, "依赖章节不存在"
        if dependency.dependency_type == "generation" and required.status not in {"generated", "warning", "reviewing", "revision_required", "approved", "locked"}:
            return False, f"依赖章节 {required.section_code} 尚未生成"
        if dependency.dependency_type == "review" and required.status not in {"reviewing", "revision_required", "approved", "locked"}:
            return False, f"依赖章节 {required.section_code} 尚未进入审核"
        if dependency.dependency_type == "approval" and required.status not in {"approved", "locked"}:
            return False, f"依赖章节 {required.section_code} 尚未审核通过"
    return True, None


def calculate_section_status(db: Session, instance: DocumentInstance, section: DocumentSectionInstance, user: User, *, persist: bool = True) -> SectionPreflightOut:
    if section.status in {"locked", "not_applicable"}:
        return SectionPreflightOut(ready=False, warnings=["章节已锁定或标记为不适用"])
    dependency_ready, dependency_reason = _dependency_ready(db, section)
    template_section = db.get(TemplateSection, section.template_section_id)
    if template_section is None:
        section.status, section.blocked_reason = "blocked", "模板章节不存在"
        return SectionPreflightOut(ready=False, conflicts=["模板章节不存在"])
    result, _ = generation_service.preflight(db, instance, template_section, user)
    if section.status == "stale":
        result.ready = False
        result.warnings.append(section.stale_reason or "章节来源已更新，请重新检查")
        return result
    if not dependency_ready:
        result.ready = False
        result.warnings.append(dependency_reason or "章节依赖未满足")
    draft = db.scalar(select(SectionDraft).where(SectionDraft.document_instance_id == instance.id, SectionDraft.section_id == template_section.id))
    latest_review = db.scalar(select(SectionReview).where(SectionReview.section_instance_id == section.id).order_by(SectionReview.id.desc()))
    current_version = db.scalar(select(SectionDraftVersion).where(SectionDraftVersion.draft_id == draft.id, SectionDraftVersion.version == draft.version)) if draft else None
    review_matches_current = bool(latest_review and current_version and latest_review.draft_version_id == current_version.id)
    if draft is None:
        section.status = "ready" if result.ready else "blocked"
    elif review_matches_current and latest_review.status == "approved":
        section.current_draft_id = draft.id
        section.approved_version_id = latest_review.draft_version_id
        # 兼容早期审核记录：旧版本可能只保存了 SectionReview，没有同步
        # 草稿状态。只要审核记录明确对应当前版本，就把草稿状态修复为已通过，
        # 这样章节列表和编辑器不会出现“已审核通过 / 等待复核”两套状态。
        if draft.status != "approved":
            draft.status = "approved"
        section.status = "approved"
    elif review_matches_current and latest_review.status in {"revision_required", "rejected"}:
        section.current_draft_id = draft.id
        section.status = "revision_required"
    elif draft.status in {"approved", "locked"}:
        section.current_draft_id = draft.id
        section.status = draft.status
    elif draft.status == "reviewed":
        section.current_draft_id = draft.id
        section.status = "reviewing"
    elif draft.status == "rejected":
        section.current_draft_id = draft.id
        section.status = "revision_required"
    elif draft.status == "partial":
        section.current_draft_id = draft.id
        section.status = "warning"
    else:
        section.current_draft_id = draft.id
        if draft.generation_run_id:
            section.source_fingerprint = _fingerprint(draft.generation_run_id, db)
        section.status = "generated" if not (draft.warnings or draft.missing_information) else "warning"
    section.blocked_reason = None if result.ready else "；".join(result.conflicts + [item.reason for item in result.missing_fields] + result.warnings)[:1000]
    if persist:
        db.flush()
    return result


def document_preflight(db: Session, instance: DocumentInstance, user: User) -> dict[str, Any]:
    sections = list_section_instances(db, instance)
    summary = {"total_sections": len(sections), "ready_sections": 0, "blocked_sections": 0, "completed_sections": 0, "missing_data_sections": 0, "conflict_sections": 0, "warnings": [], "missing_fields": []}
    for section in sections:
        result = calculate_section_status(db, instance, section, user)
        if section.status == "ready": summary["ready_sections"] += 1
        if section.status == "blocked": summary["blocked_sections"] += 1
        if section.status in {"generated", "warning", "reviewing", "revision_required", "approved", "locked", "stale"}: summary["completed_sections"] += 1
        if result.missing_fields:
            summary["missing_data_sections"] += 1
            summary["missing_fields"].extend({"field": item.field, "reason": item.reason, "section_id": section.id, "section_title": section.title} for item in result.missing_fields)
        if result.conflicts:
            summary["conflict_sections"] += 1
        summary["warnings"].extend(result.warnings)
    instance.status = "ready_for_generation" if summary["ready_sections"] else ("collecting_data" if summary["blocked_sections"] else "draft")
    db.flush()
    return summary


def _has_cycle(db: Session, instance_id: int) -> bool:
    graph: dict[int, list[int]] = {}
    rows = list(db.scalars(select(DocumentSectionInstance).where(DocumentSectionInstance.document_instance_id == instance_id)))
    for section in rows:
        graph[section.id] = [dependency.depends_on_section_instance_id for dependency in section.dependencies]
    visiting: set[int] = set(); visited: set[int] = set()
    def visit(node: int) -> bool:
        if node in visiting: return True
        if node in visited: return False
        visiting.add(node)
        if any(visit(child) for child in graph.get(node, [])): return True
        visiting.remove(node); visited.add(node); return False
    return any(visit(node) for node in graph)


def add_dependency(db: Session, section: DocumentSectionInstance, depends_on: DocumentSectionInstance, dependency_type: str) -> SectionDependency:
    if section.document_instance_id != depends_on.document_instance_id:
        raise ValidationError("章节依赖必须属于同一份报告")
    dependency = SectionDependency(section_instance_id=section.id, depends_on_section_instance_id=depends_on.id, dependency_type=dependency_type)
    db.add(dependency); db.flush()
    if _has_cycle(db, section.document_instance_id):
        db.delete(dependency); db.flush()
        raise ValidationError("章节依赖存在循环")
    db.commit()
    return dependency


def _fingerprint(run_id: int, db: Session) -> str:
    sources = list(db.scalars(select(GenerationSource).where(GenerationSource.generation_run_id == run_id).order_by(GenerationSource.context_source_id)))
    raw = "|".join(f"{item.source_type}:{item.source_id}:{item.context_source_id}" for item in sources)
    return hashlib.sha256(raw.encode()).hexdigest()


def mark_stale_sections(db: Session, instance: DocumentInstance, user: User) -> int:
    changed = 0
    for section in list_section_instances(db, instance):
        # 审核通过/锁定代表用户已经确认了当前版本。资料更新后，重新
        # 生成或编辑会显式改变草稿状态；不要在概览刷新时把已审核章节
        # 再次降级成 stale，造成“刚审核通过又显示未通过”的错觉。
        if section.status in {"approved", "locked"}:
            continue
        if section.status in {"empty", "blocked", "ready", "not_applicable"} or not section.current_draft:
            continue
        run = db.get(SectionGenerationRun, section.current_draft.generation_run_id) if section.current_draft.generation_run_id else None
        if run is None:
            continue
        stale = False; reason = None
        for source in list(db.scalars(select(GenerationSource).where(GenerationSource.generation_run_id == run.id))):
            if source.source_type == "project_fact":
                fact = db.get(ExtractedFact, source.source_id)
                entity_type = (source.metadata_json or {}).get("entity_type")
                model_map = {"company_profile": CompanyProfile, "product": Product, "production_equipment": ProductionEquipment, "raw_material": RawMaterial, "environmental_facility": EnvironmentalFacility}
                entity = fact or (db.get(model_map[entity_type], source.source_id) if entity_type in model_map else None)
                if entity and entity.updated_at and entity.updated_at >= run.started_at:
                    stale, reason = True, "引用的项目事实已更新"; break
            if source.source_type == "knowledge_chunk":
                chunk = db.get(KnowledgeChunk, source.source_id)
                document = db.get(KnowledgeDocument, chunk.knowledge_document_id) if chunk else None
                if document and document.status != "active":
                    stale, reason = True, "引用的知识文档已失效或被替代"; break
        if stale:
            section.status = "stale"; section.stale_reason = reason; changed += 1
            audit(db, user, "section_marked_stale", instance, section, {"reason": reason})
    db.flush(); return changed


def batch_generate(db: Session, instance: DocumentInstance, user: User, section_ids: list[int] | None = None) -> BatchGenerationRun:
    require_project_permission(db, user, db.get(DocumentInstance, instance.id).project, "documents.generate")
    active = db.scalar(select(BatchGenerationRun).where(BatchGenerationRun.document_instance_id == instance.id, BatchGenerationRun.status.in_(["pending", "running"])))
    if active:
        raise ConflictError("该报告已有批量生成任务正在执行")
    document_preflight(db, instance, user)
    sections = list_section_instances(db, instance)
    selected = set(section_ids or [])
    candidates = [section for section in sections if (not selected or section.id in selected) and section.status == "ready" and section.generation_enabled]
    run = BatchGenerationRun(document_instance_id=instance.id, started_by=user.id, status="running", total_sections=len(candidates), queued_sections=len(candidates))
    db.add(run); db.flush()
    audit(db, user, "batch_generation_started", instance, metadata={"section_count": len(candidates)})
    instance.status = "generating"
    for section in candidates:
        item = BatchGenerationItem(batch_run_id=run.id, section_instance_id=section.id, status="running")
        db.add(item); db.flush(); section.status = "generating"; db.commit()
        try:
            template_section = db.get(TemplateSection, section.template_section_id)
            generation_run = generation_service.generate_section(db, instance, template_section, user)
            item.generation_run_id = generation_run.id
            item.status = "completed" if generation_run.status == "completed" else ("partial" if generation_run.status == "partial" else "failed")
            draft = db.scalar(select(SectionDraft).where(SectionDraft.document_instance_id == instance.id, SectionDraft.section_id == template_section.id))
            section.current_draft_id = draft.id if draft else None
            section.source_fingerprint = _fingerprint(generation_run.id, db)
            section.status = "generated" if item.status == "completed" else "warning"
            if item.status == "completed": run.completed_sections += 1
            elif item.status == "partial": run.partial_sections += 1
            else: run.failed_sections += 1
        except Exception as exc:
            item.status = "failed"; item.error_message = str(exc)[:500]; section.status = "blocked"; section.blocked_reason = str(exc)[:500]; run.failed_sections += 1
        db.commit()
    run.status = "completed" if run.failed_sections == 0 and run.partial_sections == 0 else ("partial" if run.completed_sections or run.partial_sections else "failed")
    run.completed_at = datetime.now(timezone.utc)
    instance.status = "in_review" if run.completed_sections else "revision_required"
    audit(db, user, "batch_generation_completed", instance, metadata={"status": run.status, "completed": run.completed_sections, "failed": run.failed_sections})
    db.commit(); db.refresh(run); return run


def review_section(db: Session, section: DocumentSectionInstance, user: User, status: str, comment: str | None) -> SectionReview:
    instance = db.get(DocumentInstance, section.document_instance_id)
    require_project_permission(db, user, instance.project, "documents.review")
    if status not in {"approved", "revision_required", "rejected"}:
        raise ValidationError("不支持的审核状态")
    if not section.current_draft_id:
        draft = db.scalar(select(SectionDraft).where(SectionDraft.document_instance_id == section.document_instance_id, SectionDraft.section_id == section.template_section_id))
        if draft:
            section.current_draft_id = draft.id
            db.flush()
    if status == "approved" and not section.current_draft_id:
        raise ValidationError("章节尚未生成，不能审核通过")
    draft = db.get(SectionDraft, section.current_draft_id) if section.current_draft_id else None
    version = None
    if draft:
        version = db.scalar(select(SectionDraftVersion).where(SectionDraftVersion.draft_id == draft.id, SectionDraftVersion.version == draft.version))
        if version is None:
            version = SectionDraftVersion(draft_id=draft.id, version=draft.version, content=draft.content, status=status, saved_by=user.id)
            db.add(version); db.flush()
    review = SectionReview(section_instance_id=section.id, draft_version_id=version.id if version else None, reviewer_id=user.id, status=status, comment=comment)
    db.add(review)
    if draft:
        # 概览刷新时会根据草稿状态重新计算章节状态；只更新
        # DocumentSectionInstance 会被旧的 generated 状态覆盖。
        draft.status = "approved" if status == "approved" else "rejected"
    section.status = "approved" if status == "approved" else "revision_required"
    if status == "approved" and version:
        section.approved_version_id = version.id
    audit(db, user, "section_reviewed", section.document_instance, section, {"status": status})
    db.commit(); db.refresh(review); return review


def lock_section(db: Session, section: DocumentSectionInstance, user: User) -> None:
    instance = db.get(DocumentInstance, section.document_instance_id)
    require_project_permission(db, user, instance.project, "documents.review")
    if section.status != "approved":
        raise ValidationError("只有审核通过的章节才能锁定")
    section.status = "locked"; audit(db, user, "section_locked", section.document_instance, section); db.commit()


def unlock_section(db: Session, section: DocumentSectionInstance, user: User) -> None:
    instance = db.get(DocumentInstance, section.document_instance_id)
    require_project_permission(db, user, instance.project, "documents.review")
    if section.status != "locked":
        raise ValidationError("章节当前不是锁定状态")
    section.status = "approved"; audit(db, user, "section_unlocked", section.document_instance, section); db.commit()


def validate_document(db: Session, instance: DocumentInstance, user: User) -> DocumentValidationRun:
    run = DocumentValidationRun(document_instance_id=instance.id, created_by=user.id, status="running")
    db.add(run); db.flush()
    sections = list_section_instances(db, instance)
    drafts = {section.id: section.current_draft for section in sections if section.current_draft}
    facts = list(db.scalars(select(ExtractedFact).where(ExtractedFact.project_id == instance.project_id, ExtractedFact.status == "accepted")))
    for section in sections:
        draft = drafts.get(section.id)
        if not draft: continue
        if draft.missing_information:
            details = "；".join(
                f"{item.get('field') or '资料'}：{item.get('reason') or '请补充该项信息'}"
                for item in draft.missing_information
                if isinstance(item, dict)
            ) or "请查看本章资料中的待补充项"
            db.add(DocumentValidationIssue(
                validation_run_id=run.id,
                issue_type="missing_information",
                severity="critical" if section.template_section.required else "warning",
                section_a_id=section.id,
                message=f"{section.title}还缺少：{details}",
                expected_value=None,
                actual_value=details,
            ))
        if section.status == "stale":
            db.add(DocumentValidationIssue(validation_run_id=run.id, issue_type="stale_source", severity="warning", section_a_id=section.id, message=section.stale_reason or "章节来源已变化"))
        citations = list(db.scalars(select(SectionCitation).where(SectionCitation.section_draft_id == draft.id, SectionCitation.generation_run_id == draft.generation_run_id))) if draft.generation_run_id else []
        for citation in citations:
            if citation.source_type == "knowledge_chunk":
                chunk = db.get(KnowledgeChunk, citation.source_id)
                document = db.get(KnowledgeDocument, chunk.knowledge_document_id) if chunk else None
                if document is None or document.status != "active":
                    db.add(DocumentValidationIssue(validation_run_id=run.id, issue_type="citation_invalid", severity="warning", section_a_id=section.id, message="章节引用的专业知识来源已失效或不存在"))
        if re.search(r"\b(?:GB|HJ|DB)\s*\d", draft.content.upper()) and not any(citation.source_type == "knowledge_chunk" for citation in citations):
            db.add(DocumentValidationIssue(validation_run_id=run.id, issue_type="citation_missing", severity="warning", section_a_id=section.id, message="正文包含标准号，但未关联知识库引用"))
        for fact in facts:
            if not fact.raw_value or not draft.content: continue
            if fact.field_name in {"annual_usage", "max_storage", "quantity", "annual_capacity", "capacity", "power"} and fact.entity_key in draft.content and re.search(r"\d+(?:\.\d+)?", fact.raw_value):
                expected = _normalize_quantity(fact.raw_value, fact.unit)
                actual_match = re.search(rf"{re.escape(fact.entity_key)}[^。；\n]{{0,80}}?(\d+(?:\.\d+)?)\s*(t/a|kg/a|台|套|m²|m2)?", draft.content, flags=re.IGNORECASE)
                actual = _normalize_quantity(actual_match.group(1), actual_match.group(2)) if actual_match else None
                if expected is not None and actual is not None and abs(expected - actual) < 1e-8:
                    continue
            if fact.raw_value in draft.content:
                continue
            if fact.field_name in {"annual_usage", "max_storage", "quantity", "annual_capacity", "capacity", "power"} and fact.entity_key in draft.content and re.search(r"\d+(?:\.\d+)?", fact.raw_value):
                db.add(DocumentValidationIssue(validation_run_id=run.id, issue_type="numeric_mismatch", severity="critical", section_a_id=section.id, entity_type=fact.entity_type, field_name=fact.field_name, expected_value=fact.raw_value, actual_value=draft.content[:500], message=f"章节 {section.title} 中 {fact.entity_key} 的 {fact.field_name} 与已确认事实不一致"))
    open_conflicts = list(db.scalars(select(DataConflict).where(DataConflict.project_id == instance.project_id, DataConflict.status == "open")))
    for conflict in open_conflicts:
        db.add(DocumentValidationIssue(validation_run_id=run.id, issue_type="unresolved_conflict", severity="critical", message=f"存在未解决冲突：{conflict.entity_type}.{conflict.entity_key}.{conflict.field_name}"))
    db.flush()
    run.issues_count = len(run.issues); run.critical_count = sum(1 for issue in run.issues if issue.severity == "critical"); run.warning_count = sum(1 for issue in run.issues if issue.severity == "warning"); run.status = "completed"; run.completed_at = datetime.now(timezone.utc)
    audit(db, user, "document_validation_completed", instance, metadata={"issues": run.issues_count, "critical": run.critical_count}); db.commit(); db.refresh(run); return run


def _normalize_quantity(value: str, unit: str | None) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    unit = (unit or "").lower().replace(" ", "")
    if unit == "kg/a": return numeric / 1000
    return numeric


def readiness(db: Session, instance: DocumentInstance, user: User) -> dict[str, Any]:
    document_preflight(db, instance, user)
    sections = list_section_instances(db, instance)
    required = [section for section in sections if section.template_section.required if hasattr(section, "template_section")]
    # 模板关系可能未预加载，使用数据库补齐 required 标志。
    required = [section for section in sections if (db.get(TemplateSection, section.template_section_id).required if db.get(TemplateSection, section.template_section_id) else True)]
    blocking: list[str] = []
    for section in required:
        if section.status not in {"approved", "locked"}:
            blocking.append(f"必填章节 {section.section_code} 尚未审核通过（{section.status}）")
        if section.status == "stale": blocking.append(f"必填章节 {section.section_code} 来源已过期")
    latest = db.scalar(select(DocumentValidationRun).where(DocumentValidationRun.document_instance_id == instance.id).order_by(DocumentValidationRun.id.desc()))
    if latest:
        critical = list(db.scalars(select(DocumentValidationIssue).where(DocumentValidationIssue.validation_run_id == latest.id, DocumentValidationIssue.severity == "critical", DocumentValidationIssue.status == "open")))
        blocking.extend(issue.message for issue in critical)
    # Phase 7 质量门禁：已有质量审核结果且未通过时，不能进入导出就绪状态。
    try:
        from app.services.review_service import quality_gate
        gate = quality_gate(db, instance.id, user)
        if gate.get("reason") is None and not gate.get("passed"):
            blocking.append(f"专业质量门禁未通过：Critical {gate.get('critical', 0)}，Major {gate.get('major', 0)}")
    except Exception:
        pass
    ready = not blocking
    if ready: instance.status = "ready_for_export"
    db.commit()
    return {"ready_for_export": ready, "blocking_reasons": list(dict.fromkeys(blocking)), "warnings": [section.stale_reason for section in sections if section.stale_reason], "required_sections": len(required), "approved_sections": sum(1 for section in required if section.status in {"approved", "locked"})}
