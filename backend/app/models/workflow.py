from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentSectionInstance(Base):
    __tablename__ = "document_section_instances"
    __table_args__ = (CheckConstraint("status IN ('empty', 'blocked', 'ready', 'queued', 'generating', 'generated', 'warning', 'reviewing', 'revision_required', 'approved', 'locked', 'stale', 'not_applicable')", name="ck_document_section_instances_status"), UniqueConstraint("document_instance_id", "template_section_id", name="uq_document_section_instance"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_instance_id: Mapped[int] = mapped_column(ForeignKey("document_instances.id", ondelete="CASCADE"), index=True, nullable=False)
    template_section_id: Mapped[int] = mapped_column(ForeignKey("template_sections.id", ondelete="RESTRICT"), index=True, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("document_section_instances.id", ondelete="CASCADE"), index=True, nullable=True)
    section_code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="empty", nullable=False)
    generation_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    current_draft_id: Mapped[int | None] = mapped_column(ForeignKey("section_drafts.id", ondelete="SET NULL"), nullable=True)
    approved_version_id: Mapped[int | None] = mapped_column(ForeignKey("section_draft_versions.id", ondelete="SET NULL"), nullable=True)
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stale_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    document_instance = relationship("DocumentInstance", back_populates="section_instances")
    template_section = relationship("TemplateSection")
    parent = relationship("DocumentSectionInstance", remote_side=[id], back_populates="children")
    children = relationship("DocumentSectionInstance", back_populates="parent", cascade="all, delete-orphan")
    current_draft = relationship("SectionDraft", foreign_keys=[current_draft_id])
    approved_version = relationship("SectionDraftVersion", foreign_keys=[approved_version_id])
    dependencies = relationship("SectionDependency", foreign_keys="SectionDependency.section_instance_id", back_populates="section_instance", cascade="all, delete-orphan")


class SectionDependency(Base):
    __tablename__ = "section_dependencies"
    __table_args__ = (UniqueConstraint("section_instance_id", "depends_on_section_instance_id", "dependency_type", name="uq_section_dependency"), CheckConstraint("dependency_type IN ('generation', 'review', 'approval')", name="ck_section_dependency_type"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    section_instance_id: Mapped[int] = mapped_column(ForeignKey("document_section_instances.id", ondelete="CASCADE"), index=True, nullable=False)
    depends_on_section_instance_id: Mapped[int] = mapped_column(ForeignKey("document_section_instances.id", ondelete="CASCADE"), index=True, nullable=False)
    dependency_type: Mapped[str] = mapped_column(String(32), default="generation", nullable=False)

    section_instance = relationship("DocumentSectionInstance", foreign_keys=[section_instance_id], back_populates="dependencies")
    depends_on = relationship("DocumentSectionInstance", foreign_keys=[depends_on_section_instance_id])


class BatchGenerationRun(Base):
    __tablename__ = "batch_generation_runs"
    __table_args__ = (CheckConstraint("status IN ('pending', 'running', 'completed', 'partial', 'failed')", name="ck_batch_generation_runs_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_instance_id: Mapped[int] = mapped_column(ForeignKey("document_instances.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    total_sections: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    queued_sections: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_sections: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_sections: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocked_sections: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    partial_sections: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document_instance = relationship("DocumentInstance")
    starter = relationship("User")
    items = relationship("BatchGenerationItem", back_populates="batch_run", cascade="all, delete-orphan")


class BatchGenerationItem(Base):
    __tablename__ = "batch_generation_items"
    __table_args__ = (CheckConstraint("status IN ('queued', 'running', 'completed', 'partial', 'failed', 'blocked', 'skipped')", name="ck_batch_generation_items_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_run_id: Mapped[int] = mapped_column(ForeignKey("batch_generation_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    section_instance_id: Mapped[int] = mapped_column(ForeignKey("document_section_instances.id", ondelete="CASCADE"), index=True, nullable=False)
    generation_run_id: Mapped[int | None] = mapped_column(ForeignKey("section_generation_runs.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    batch_run = relationship("BatchGenerationRun", back_populates="items")
    section_instance = relationship("DocumentSectionInstance")
    generation_run = relationship("SectionGenerationRun")


class SectionReview(Base):
    __tablename__ = "section_reviews"
    __table_args__ = (CheckConstraint("status IN ('approved', 'revision_required', 'rejected')", name="ck_section_reviews_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    section_instance_id: Mapped[int] = mapped_column(ForeignKey("document_section_instances.id", ondelete="CASCADE"), index=True, nullable=False)
    draft_version_id: Mapped[int | None] = mapped_column(ForeignKey("section_draft_versions.id", ondelete="SET NULL"), nullable=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    section_instance = relationship("DocumentSectionInstance")
    reviewer = relationship("User")


class DocumentValidationRun(Base):
    __tablename__ = "document_validation_runs"
    __table_args__ = (CheckConstraint("status IN ('running', 'completed', 'failed')", name="ck_document_validation_runs_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_instance_id: Mapped[int] = mapped_column(ForeignKey("document_instances.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    issues_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    issues = relationship("DocumentValidationIssue", back_populates="validation_run", cascade="all, delete-orphan")


class DocumentValidationIssue(Base):
    __tablename__ = "document_validation_issues"
    __table_args__ = (CheckConstraint("severity IN ('critical', 'warning', 'info')", name="ck_document_validation_issues_severity"), CheckConstraint("status IN ('open', 'resolved', 'ignored')", name="ck_document_validation_issues_status"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    validation_run_id: Mapped[int] = mapped_column(ForeignKey("document_validation_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    section_a_id: Mapped[int | None] = mapped_column(ForeignKey("document_section_instances.id", ondelete="SET NULL"), nullable=True)
    section_b_id: Mapped[int | None] = mapped_column(ForeignKey("document_section_instances.id", ondelete="SET NULL"), nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    field_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    validation_run = relationship("DocumentValidationRun", back_populates="issues")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True)
    document_instance_id: Mapped[int | None] = mapped_column(ForeignKey("document_instances.id", ondelete="CASCADE"), index=True, nullable=True)
    section_instance_id: Mapped[int | None] = mapped_column(ForeignKey("document_section_instances.id", ondelete="CASCADE"), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
