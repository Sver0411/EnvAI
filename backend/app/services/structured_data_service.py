from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.company_profile import CompanyProfile
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.structured_data import (
    DataConflict,
    EnvironmentalFacility,
    ExtractedFact,
    Product,
    ProductionEquipment,
    RawMaterial,
)
from app.services import project_service
from app.services.extraction_service import ENTITY_MODELS, ExtractionService, latest_run


def run_extraction(db: Session, project_id: int):
    return ExtractionService().run_project(db, project_id)


def get_project_data(db: Session, project_id: int, owner_id: int) -> dict[str, Any]:
    project_service.get_project(db, project_id, owner_id)
    profile = db.scalar(select(CompanyProfile).where(CompanyProfile.project_id == project_id))
    facts = list(
        db.scalars(
            select(ExtractedFact)
            .where(ExtractedFact.project_id == project_id)
            .order_by(ExtractedFact.created_at.desc(), ExtractedFact.id.desc())
        )
    )
    files = {row.id: row.filename for row in db.execute(select(ProjectFile.id, ProjectFile.filename).where(ProjectFile.project_id == project_id))}
    conflicts = list(
        db.scalars(
            select(DataConflict)
            .where(DataConflict.project_id == project_id)
            .order_by(DataConflict.created_at.desc(), DataConflict.id.desc())
        )
    )
    return {
        "profile": profile,
        "products": list(db.scalars(select(Product).where(Product.project_id == project_id).order_by(Product.id))),
        "equipment": list(db.scalars(select(ProductionEquipment).where(ProductionEquipment.project_id == project_id).order_by(ProductionEquipment.id))),
        "raw_materials": list(db.scalars(select(RawMaterial).where(RawMaterial.project_id == project_id).order_by(RawMaterial.id))),
        "environmental_facilities": list(db.scalars(select(EnvironmentalFacility).where(EnvironmentalFacility.project_id == project_id).order_by(EnvironmentalFacility.id))),
        "facts": [(fact, files.get(fact.project_file_id)) for fact in facts],
        "conflicts": conflicts,
        "latest_run": latest_run(db, project_id),
    }


def list_facts(db: Session, project_id: int, owner_id: int):
    project_service.get_project(db, project_id, owner_id)
    return get_project_data(db, project_id, owner_id)["facts"]


def list_conflicts(db: Session, project_id: int, owner_id: int):
    project_service.get_project(db, project_id, owner_id)
    return get_project_data(db, project_id, owner_id)["conflicts"]


def accept_fact(db: Session, project_id: int, fact_id: int, owner_id: int) -> ExtractedFact:
    project_service.get_project(db, project_id, owner_id)
    fact = db.scalar(select(ExtractedFact).where(ExtractedFact.id == fact_id, ExtractedFact.project_id == project_id))
    if fact is None:
        raise NotFoundError("抽取事实不存在")
    fact.status = "accepted"
    fact.verification_status = "user_verified"
    fact.updated_by = owner_id
    _apply_fact_to_final_data(db, fact, owner_id)
    db.commit()
    return fact


def reject_fact(db: Session, project_id: int, fact_id: int, owner_id: int) -> ExtractedFact:
    project_service.get_project(db, project_id, owner_id)
    fact = db.scalar(select(ExtractedFact).where(ExtractedFact.id == fact_id, ExtractedFact.project_id == project_id))
    if fact is None:
        raise NotFoundError("抽取事实不存在")
    fact.status = "rejected"
    fact.verification_status = "user_verified"
    fact.updated_by = owner_id
    for model in ENTITY_MODELS.values():
        row = db.scalar(select(model).where(model.source_fact_id == fact.id, model.verification_status == "ai_extracted"))
        if row is not None:
            db.delete(row)
    db.commit()
    return fact


def resolve_conflict(db: Session, project_id: int, conflict_id: int, owner_id: int, resolution: str, note: str | None):
    project_service.get_project(db, project_id, owner_id)
    conflict = db.scalar(select(DataConflict).where(DataConflict.id == conflict_id, DataConflict.project_id == project_id))
    if conflict is None:
        raise NotFoundError("数据冲突不存在")
    if conflict.status != "open":
        raise ValidationError("该冲突已经处理")
    if resolution == "use_a":
        chosen, rejected = conflict.fact_a_id, conflict.fact_b_id
    elif resolution == "use_b":
        chosen, rejected = conflict.fact_b_id, conflict.fact_a_id
    else:
        chosen, rejected = None, None
    if chosen:
        accept_fact(db, project_id, chosen, owner_id)
    if rejected:
        reject_fact(db, project_id, rejected, owner_id)
    conflict.status = "ignored" if resolution == "ignore" else "resolved"
    conflict.resolution = note or resolution
    conflict.resolved_by = owner_id
    conflict.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return conflict


def update_entity(db: Session, project_id: int, owner_id: int, entity_type: str, entity_id: int, data: dict[str, Any]):
    project_service.get_project(db, project_id, owner_id)
    model = ENTITY_MODELS.get(entity_type)
    if model is None:
        raise ValidationError("不支持的结构化实体")
    row = db.scalar(select(model).where(model.id == entity_id, model.project_id == project_id))
    if row is None:
        raise NotFoundError("结构化数据不存在")
    for field, value in data.items():
        if hasattr(row, field) and field not in {"id", "project_id", "source_fact_id", "verification_status"}:
            setattr(row, field, value)
    row.verification_status = "user_verified"
    row.updated_by = owner_id
    db.commit()
    db.refresh(row)
    return row


def delete_entity(db: Session, project_id: int, owner_id: int, entity_type: str, entity_id: int) -> None:
    project_service.get_project(db, project_id, owner_id)
    model = ENTITY_MODELS.get(entity_type)
    if model is None:
        raise ValidationError("不支持的结构化实体")
    row = db.scalar(select(model).where(model.id == entity_id, model.project_id == project_id))
    if row is None:
        raise NotFoundError("结构化数据不存在")
    db.delete(row)
    db.commit()


def _apply_fact_to_final_data(db: Session, fact: ExtractedFact, owner_id: int) -> None:
    if fact.entity_type == "company_profile":
        profile = db.scalar(select(CompanyProfile).where(CompanyProfile.project_id == fact.project_id))
        if profile is None:
            profile = CompanyProfile(project_id=fact.project_id)
            db.add(profile)
        if hasattr(profile, fact.field_name):
            setattr(profile, fact.field_name, fact.raw_value)
        return
    model = ENTITY_MODELS.get(fact.entity_type)
    if model is None:
        return
    row = db.scalar(select(model).where(model.project_id == fact.project_id, model.name == fact.entity_key))
    if row is None:
        row = model(project_id=fact.project_id, name=fact.entity_key)
        db.add(row)
    row.source_fact_id = fact.id
    row.verification_status = "user_verified"
    row.updated_by = owner_id
    if hasattr(row, fact.field_name) and fact.field_name != "name":
        if fact.field_name in {"annual_capacity", "annual_usage", "max_storage", "quantity", "power", "capacity"}:
            value = (fact.normalized_value or {}).get("value")
            setattr(row, fact.field_name, Decimal(str(value)) if value not in (None, "") else None)
        else:
            setattr(row, fact.field_name, fact.raw_value)
    if fact.field_name == "annual_usage" and fact.unit:
        row.annual_usage_unit = fact.unit
    if fact.field_name == "max_storage" and fact.unit:
        row.storage_unit = fact.unit
    if fact.field_name == "annual_capacity" and fact.unit:
        row.unit = fact.unit
    if fact.field_name == "quantity" and fact.unit:
        row.unit = fact.unit
