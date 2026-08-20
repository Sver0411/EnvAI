from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ReportTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; name: str; code: str; document_type: str; version: str; status: str; original_file_name: str; file_size: int; engine: str; created_at: datetime


class ExportPreflightOut(BaseModel):
    ready: bool; blocking_issues: list[str]; warnings: list[str]; selected_template: str | None = None; selected_template_id: int | None = None; snapshot_required: bool = True; pdf_available: bool = False


class SnapshotCreateIn(BaseModel):
    is_draft_export: bool = False


class ReportSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; document_instance_id: int; snapshot_number: int; status: str; document_title: str; template_id: int; template_version: str; quality_review_run_id: int | None; content_hash: str; metadata_json: dict[str, Any] | None; created_at: datetime


class ExportStartIn(BaseModel):
    formats: list[Literal['docx', 'pdf']] = Field(min_length=1)
    report_template_id: int | None = None


class ExportArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; export_job_id: int; format: str; file_name: str; mime_type: str; file_size: int; sha256: str; created_at: datetime


class ReportExportJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; report_snapshot_id: int; report_template_id: int; status: str; requested_formats: list[str]; docx_status: str; pdf_status: str; exporter_version: str; render_manifest: dict[str, Any] | None; error_message: str | None; started_at: datetime; completed_at: datetime | None


class ReportFigureIn(BaseModel):
    project_file_id: int
    section_instance_id: int | None = None
    caption: str = Field(min_length=1, max_length=500)
    sort_order: int = 0
    width_inches: float = Field(default=5.8, ge=1.0, le=6.5)


class ReportFigureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; document_instance_id: int; project_file_id: int; section_instance_id: int | None; caption: str; sort_order: int; width_inches: float; enabled: bool; created_at: datetime
