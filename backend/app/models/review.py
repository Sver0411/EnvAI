from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ReviewRuleSet(Base):
    __tablename__ = "review_rule_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    rules = relationship("ProfessionalRule", back_populates="rule_set", cascade="all, delete-orphan")
    checklists = relationship("ReviewChecklist", back_populates="rule_set", cascade="all, delete-orphan")


class ProfessionalRule(Base):
    __tablename__ = "professional_rules"
    __table_args__ = (UniqueConstraint("rule_set_id", "code", name="uq_professional_rule_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rule_set_id: Mapped[int] = mapped_column(ForeignKey("review_rule_sets.id", ondelete="CASCADE"), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="general", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(32), default="major", nullable=False)
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    rule_set = relationship("ReviewRuleSet", back_populates="rules")


class ReviewChecklist(Base):
    __tablename__ = "review_checklists"
    __table_args__ = (UniqueConstraint("rule_set_id", "code", name="uq_review_checklist_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rule_set_id: Mapped[int] = mapped_column(ForeignKey("review_rule_sets.id", ondelete="CASCADE"), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), default="document", nullable=False)
    section_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    rule_set = relationship("ReviewRuleSet", back_populates="checklists")


class ProfessionalReviewRun(Base):
    __tablename__ = "professional_review_runs"
    __table_args__ = (CheckConstraint("status IN ('pending', 'running', 'completed', 'partial', 'failed')", name="ck_professional_review_runs_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_instance_id: Mapped[int] = mapped_column(ForeignKey("document_instances.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    review_mode: Mapped[str] = mapped_column(String(32), default="full", nullable=False)
    rule_set_id: Mapped[int | None] = mapped_column(ForeignKey("review_rule_sets.id", ondelete="SET NULL"), nullable=True)
    rule_set_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    issues_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    major_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minor_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tasks = relationship("ReviewTask", back_populates="review_run", cascade="all, delete-orphan")
    issues = relationship("ReviewIssue", back_populates="review_run", cascade="all, delete-orphan")


class ReviewTask(Base):
    __tablename__ = "review_tasks"
    __table_args__ = (CheckConstraint("status IN ('pending', 'running', 'completed', 'failed', 'skipped')", name="ck_review_tasks_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    review_run_id: Mapped[int] = mapped_column(ForeignKey("professional_review_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    section_instance_id: Mapped[int | None] = mapped_column(ForeignKey("document_section_instances.id", ondelete="SET NULL"), nullable=True)
    section_group: Mapped[str | None] = mapped_column(String(128), nullable=True)
    review_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rule_set_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    review_run = relationship("ProfessionalReviewRun", back_populates="tasks")
    results = relationship("ReviewChecklistResult", back_populates="task", cascade="all, delete-orphan")


class ReviewIssue(Base):
    __tablename__ = "review_issues"
    __table_args__ = (UniqueConstraint("review_run_id", "fingerprint", name="uq_review_issue_fingerprint"), CheckConstraint("severity IN ('critical', 'major', 'minor', 'info')", name="ck_review_issues_severity"), CheckConstraint("status IN ('open', 'accepted', 'fixed', 'dismissed', 'needs_review', 'stale')", name="ck_review_issues_status"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_instance_id: Mapped[int] = mapped_column(ForeignKey("document_instances.id", ondelete="CASCADE"), index=True, nullable=False)
    review_run_id: Mapped[int] = mapped_column(ForeignKey("professional_review_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    section_instance_id: Mapped[int | None] = mapped_column(ForeignKey("document_section_instances.id", ondelete="SET NULL"), nullable=True)
    draft_version_id: Mapped[int | None] = mapped_column(ForeignKey("section_draft_versions.id", ondelete="SET NULL"), nullable=True)
    issue_source: Mapped[str] = mapped_column(String(32), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_fact_ids: Mapped[list[int] | None] = mapped_column(JSONB, nullable=True)
    related_citation_ids: Mapped[list[int] | None] = mapped_column(JSONB, nullable=True)
    related_knowledge_chunk_ids: Mapped[list[int] | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    dismissal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    review_run = relationship("ProfessionalReviewRun", back_populates="issues")


class ReviewChecklistResult(Base):
    __tablename__ = "review_checklist_results"
    __table_args__ = (UniqueConstraint("review_task_id", "check_code", name="uq_review_checklist_result"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    review_task_id: Mapped[int] = mapped_column(ForeignKey("review_tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    checklist_id: Mapped[int | None] = mapped_column(ForeignKey("review_checklists.id", ondelete="SET NULL"), nullable=True)
    check_code: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task = relationship("ReviewTask", back_populates="results")


class QualityScoreResult(Base):
    __tablename__ = "quality_score_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_instance_id: Mapped[int] = mapped_column(ForeignKey("document_instances.id", ondelete="CASCADE"), index=True, nullable=False)
    review_run_id: Mapped[int | None] = mapped_column(ForeignKey("professional_review_runs.id", ondelete="SET NULL"), nullable=True)
    overall_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    data_integrity_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    citation_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    coverage_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    completeness_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    consistency_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    critical_issue_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    major_issue_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
