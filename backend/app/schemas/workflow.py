from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentSectionInstanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_instance_id: int
    template_section_id: int
    parent_id: int | None
    section_code: str
    title: str
    level: int
    sort_order: int
    status: str
    generation_enabled: bool
    current_draft_id: int | None
    approved_version_id: int | None
    blocked_reason: str | None
    stale_reason: str | None
    updated_at: datetime


class DocumentPreflightOut(BaseModel):
    total_sections: int
    ready_sections: int
    blocked_sections: int
    completed_sections: int
    missing_data_sections: int
    conflict_sections: int
    warnings: list[str] = Field(default_factory=list)
    missing_fields: list[dict[str, Any]] = Field(default_factory=list)


class BatchGenerationRequest(BaseModel):
    section_ids: list[int] = Field(default_factory=list)


class BatchGenerationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_instance_id: int
    status: str
    total_sections: int
    queued_sections: int
    completed_sections: int
    failed_sections: int
    blocked_sections: int
    partial_sections: int
    started_by: int
    started_at: datetime
    completed_at: datetime | None


class SectionReviewIn(BaseModel):
    status: str = Field(pattern="^(approved|revision_required|rejected)$")
    comment: str | None = None


class SectionDependencyIn(BaseModel):
    depends_on_section_instance_id: int
    dependency_type: str = Field(default="generation", pattern="^(generation|review|approval)$")


class SectionReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    section_instance_id: int
    draft_version_id: int | None
    reviewer_id: int
    status: str
    comment: str | None
    created_at: datetime


class ValidationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_instance_id: int
    status: str
    issues_count: int
    critical_count: int
    warning_count: int
    created_by: int
    started_at: datetime
    completed_at: datetime | None


class ValidationIssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    validation_run_id: int
    issue_type: str
    severity: str
    section_a_id: int | None
    section_b_id: int | None
    entity_type: str | None
    field_name: str | None
    expected_value: str | None
    actual_value: str | None
    message: str
    status: str
    created_at: datetime


class ReadinessOut(BaseModel):
    ready_for_export: bool
    blocking_reasons: list[str]
    warnings: list[str]
    required_sections: int
    approved_sections: int
