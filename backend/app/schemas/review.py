from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class ReviewStartIn(BaseModel):
    mode: str = Field(default="full", pattern="^(rules_only|ai_only|full)$")

class ProfessionalReviewRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; document_instance_id: int; status: str; review_mode: str; rule_set_id: int | None; rule_set_version: str | None; ai_provider: str | None; ai_model: str | None; issues_count: int; critical_count: int; major_count: int; minor_count: int; input_tokens: int | None; output_tokens: int | None; ai_calls: int; error_message: str | None; started_by: int; started_at: datetime; completed_at: datetime | None

class ReviewIssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; document_instance_id: int; review_run_id: int; section_instance_id: int | None; issue_source: str; issue_type: str; severity: str; title: str; description: str; evidence: dict[str, Any] | None; suggestion: str | None; confidence: float | None; status: str; dismissal_reason: str | None; created_at: datetime

class DismissIssueIn(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)

class QualityScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; document_instance_id: int; review_run_id: int | None; overall_score: float; data_integrity_score: float; citation_score: float; coverage_score: float; completeness_score: float; consistency_score: float; critical_issue_count: int; major_issue_count: int; quality_passed: bool; created_at: datetime

class QualityGateOut(BaseModel):
    passed: bool; blocking_issues: int; critical: int; major: int; score: float | None = None; reason: str | None = None

class ReviewChecklistItemOut(BaseModel):
    id: int; code: str; name: str; required: bool; status: str; message: str | None = None; reviewed_at: datetime | None = None

class ChecklistCompleteIn(BaseModel):
    status: str = Field(pattern="^(pass|fail|warning|not_applicable|needs_review)$")
    message: str | None = None
