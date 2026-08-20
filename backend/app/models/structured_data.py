from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProjectScopedMixin:
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    verification_status: Mapped[str] = mapped_column(String(32), default="ai_extracted", nullable=False)
    source_fact_id: Mapped[int | None] = mapped_column(
        ForeignKey("extracted_facts.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Product(Base, ProjectScopedMixin):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('ai_extracted', 'user_verified')",
            name="ck_products_verification_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    annual_capacity: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    specification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    project = relationship("Project", back_populates="products")


class ProductionEquipment(Base, ProjectScopedMixin):
    __tablename__ = "production_equipment"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('ai_extracted', 'user_verified')",
            name="ck_production_equipment_verification_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    power: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    power_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    project = relationship("Project", back_populates="equipment")


class RawMaterial(Base, ProjectScopedMixin):
    __tablename__ = "raw_materials"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('ai_extracted', 'user_verified')",
            name="ck_raw_materials_verification_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    annual_usage: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    annual_usage_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    max_storage: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    storage_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    storage_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cas_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    physical_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hazardous: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    risk_material: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    project = relationship("Project", back_populates="raw_materials")


class EnvironmentalFacility(Base, ProjectScopedMixin):
    __tablename__ = "environmental_facilities"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('ai_extracted', 'user_verified')",
            name="ck_environmental_facilities_verification_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    facility_type: Mapped[str] = mapped_column(String(32), default="other", nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    treatment_target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    capacity: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    capacity_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    project = relationship("Project", back_populates="environmental_facilities")


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'partial')",
            name="ck_extraction_runs_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    files_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    facts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conflicts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extractor_version: Mapped[str] = mapped_column(String(32), default="rule-v1", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), default="structured-v1", nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    project = relationship("Project", back_populates="extraction_runs")
    facts = relationship("ExtractedFact", back_populates="extraction_run", cascade="all, delete-orphan")


class ExtractedFact(Base):
    __tablename__ = "extracted_facts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'conflict', 'superseded')",
            name="ck_extracted_facts_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    extraction_run_id: Mapped[int] = mapped_column(
        ForeignKey("extraction_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    project_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_files.id", ondelete="SET NULL"), index=True, nullable=True
    )
    parsed_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("parsed_documents.id", ondelete="SET NULL"), nullable=True
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    raw_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), default="rule", nullable=False)
    source_location: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(32), default="rule-v1", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), default="structured-v1", nullable=False)
    provider_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    project = relationship("Project", back_populates="extracted_facts")
    extraction_run = relationship("ExtractionRun", back_populates="facts")
    project_file = relationship("ProjectFile")


class DataConflict(Base):
    __tablename__ = "data_conflicts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'resolved', 'ignored')",
            name="ck_data_conflicts_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    extraction_run_id: Mapped[int] = mapped_column(
        ForeignKey("extraction_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    value_a: Mapped[str] = mapped_column(Text, nullable=False)
    value_b: Mapped[str] = mapped_column(Text, nullable=False)
    fact_a_id: Mapped[int | None] = mapped_column(ForeignKey("extracted_facts.id", ondelete="SET NULL"), nullable=True)
    fact_b_id: Mapped[int | None] = mapped_column(ForeignKey("extracted_facts.id", ondelete="SET NULL"), nullable=True)
    source_a: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    source_b: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    project = relationship("Project", back_populates="data_conflicts")
