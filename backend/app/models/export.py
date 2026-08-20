from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReportTemplate(Base):
    __tablename__ = "report_templates"
    __table_args__ = (UniqueConstraint("code", "version", name="uq_report_template_code_version"), CheckConstraint("status IN ('active', 'inactive', 'archived')", name="ck_report_templates_status"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engine: Mapped[str] = mapped_column(String(32), default="docxtpl", nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ReportTemplateMapping(Base):
    __tablename__ = "report_template_mappings"
    __table_args__ = (UniqueConstraint("report_template_id", "document_template_id", name="uq_report_template_document_template"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_template_id: Mapped[int] = mapped_column(ForeignKey("report_templates.id", ondelete="RESTRICT"), nullable=False)
    document_template_id: Mapped[int] = mapped_column(ForeignKey("document_templates.id", ondelete="RESTRICT"), nullable=False)
    section_mappings: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ReportSnapshot(Base):
    __tablename__ = "report_snapshots"
    __table_args__ = (UniqueConstraint("document_instance_id", "snapshot_number", name="uq_report_snapshot_number"), CheckConstraint("status IN ('formal', 'draft')", name="ck_report_snapshots_status"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_instance_id: Mapped[int] = mapped_column(ForeignKey("document_instances.id", ondelete="CASCADE"), index=True, nullable=False)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), index=True, nullable=True)
    snapshot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="formal", nullable=False)
    document_title: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[int] = mapped_column(ForeignKey("document_templates.id", ondelete="RESTRICT"), nullable=False)
    template_version: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_review_run_id: Mapped[int | None] = mapped_column(ForeignKey("professional_review_runs.id", ondelete="SET NULL"), nullable=True)
    snapshot_content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ReportExportJob(Base):
    __tablename__ = "report_export_jobs"
    __table_args__ = (CheckConstraint("status IN ('pending', 'rendering', 'docx_completed', 'converting_pdf', 'completed', 'partial', 'failed')", name="ck_report_export_jobs_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_snapshot_id: Mapped[int] = mapped_column(ForeignKey("report_snapshots.id", ondelete="CASCADE"), index=True, nullable=False)
    report_template_id: Mapped[int] = mapped_column(ForeignKey("report_templates.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    requested_formats: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    docx_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    pdf_status: Mapped[str] = mapped_column(String(32), default="not_requested", nullable=False)
    exporter_version: Mapped[str] = mapped_column(String(32), default="docx_exporter_v1", nullable=False)
    render_manifest: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExportArtifact(Base):
    __tablename__ = "export_artifacts"
    __table_args__ = (UniqueConstraint("export_job_id", "format", name="uq_export_artifact_format"), CheckConstraint("format IN ('docx', 'pdf')", name="ck_export_artifacts_format"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    export_job_id: Mapped[int] = mapped_column(ForeignKey("report_export_jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ReportFigure(Base):
    __tablename__ = "report_figures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_instance_id: Mapped[int] = mapped_column(ForeignKey("document_instances.id", ondelete="CASCADE"), index=True, nullable=False)
    project_file_id: Mapped[int] = mapped_column(ForeignKey("project_files.id", ondelete="RESTRICT"), nullable=False)
    section_instance_id: Mapped[int | None] = mapped_column(ForeignKey("document_section_instances.id", ondelete="SET NULL"), nullable=True)
    caption: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    width_inches: Mapped[float] = mapped_column(nullable=False, default=5.8)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
