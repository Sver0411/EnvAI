from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentTemplate(Base):
    __tablename__ = "document_templates"
    __table_args__ = (CheckConstraint("status IN ('draft', 'active', 'disabled')", name="ck_document_templates_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    review_rule_set_id: Mapped[int | None] = mapped_column(ForeignKey("review_rule_sets.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    sections = relationship("TemplateSection", back_populates="template", cascade="all, delete-orphan", order_by="TemplateSection.sort_order")
    instances = relationship("DocumentInstance", back_populates="template")


class TemplateSection(Base):
    __tablename__ = "template_sections"
    __table_args__ = (UniqueConstraint("template_id", "section_code", name="uq_template_section_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("document_templates.id", ondelete="CASCADE"), index=True, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("template_sections.id", ondelete="CASCADE"), index=True, nullable=True)
    section_code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_mode: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    required: Mapped[bool] = mapped_column(default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    template = relationship("DocumentTemplate", back_populates="sections")
    parent = relationship("TemplateSection", remote_side=[id], back_populates="children")
    children = relationship("TemplateSection", back_populates="parent", cascade="all, delete-orphan")
    config = relationship("SectionGenerationConfig", back_populates="section", cascade="all, delete-orphan", uselist=False)


class SectionGenerationConfig(Base):
    __tablename__ = "section_generation_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("template_sections.id", ondelete="CASCADE"), unique=True, nullable=False)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    required_entity_types: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    required_fields: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    knowledge_categories: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    knowledge_document_types: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    jurisdiction_policy: Mapped[str] = mapped_column(String(32), default="project", nullable=False)
    retrieval_query_template: Mapped[str | None] = mapped_column(String(500), nullable=True)
    max_project_context: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_knowledge_context: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    temperature: Mapped[float] = mapped_column(default=0.2, nullable=False)
    generation_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(64), default="section-v1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    section = relationship("TemplateSection", back_populates="config")


class DocumentInstance(Base):
    __tablename__ = "document_instances"
    __table_args__ = (CheckConstraint("status IN ('draft', 'collecting_data', 'ready_for_generation', 'generating', 'in_review', 'revision_required', 'ready_for_export', 'completed', 'archived')", name="ck_document_instances_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), index=True, nullable=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("document_templates.id", ondelete="RESTRICT"), index=True, nullable=False)
    template_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    reference_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project = relationship("Project")
    template = relationship("DocumentTemplate", back_populates="instances")
    creator = relationship("User")
    drafts = relationship("SectionDraft", back_populates="document_instance", cascade="all, delete-orphan")
    runs = relationship("SectionGenerationRun", back_populates="document_instance", cascade="all, delete-orphan")
    section_instances = relationship("DocumentSectionInstance", back_populates="document_instance", cascade="all, delete-orphan", order_by="DocumentSectionInstance.sort_order")


class SectionGenerationRun(Base):
    __tablename__ = "section_generation_runs"
    __table_args__ = (CheckConstraint("status IN ('pending', 'retrieving', 'generating', 'validating', 'completed', 'partial', 'failed', 'blocked')", name="ck_section_generation_runs_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    document_instance_id: Mapped[int] = mapped_column(ForeignKey("document_instances.id", ondelete="CASCADE"), index=True, nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("template_sections.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    ai_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    project_fact_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    project_source_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    knowledge_source_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retrieval_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document_instance = relationship("DocumentInstance", back_populates="runs")
    section = relationship("TemplateSection")
    sources = relationship("GenerationSource", back_populates="run", cascade="all, delete-orphan")
    citations = relationship("SectionCitation", back_populates="run", cascade="all, delete-orphan")
    draft = relationship("SectionDraft", back_populates="generation_run", uselist=False)


class SectionDraft(Base):
    __tablename__ = "section_drafts"
    __table_args__ = (UniqueConstraint("document_instance_id", "section_id", name="uq_section_draft_instance_section"), CheckConstraint("status IN ('draft', 'generated', 'reviewed', 'approved', 'rejected', 'partial', 'blocked')", name="ck_section_drafts_status"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    document_instance_id: Mapped[int] = mapped_column(ForeignKey("document_instances.id", ondelete="CASCADE"), index=True, nullable=False)
    template_id: Mapped[int] = mapped_column(ForeignKey("document_templates.id", ondelete="CASCADE"), nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("template_sections.id", ondelete="CASCADE"), index=True, nullable=False)
    generation_run_id: Mapped[int | None] = mapped_column(ForeignKey("section_generation_runs.id", ondelete="SET NULL"), nullable=True)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    ai_original_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    citations: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    missing_information: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    generation_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    document_instance = relationship("DocumentInstance", back_populates="drafts")
    generation_run = relationship("SectionGenerationRun", back_populates="draft")
    section = relationship("TemplateSection")
    creator = relationship("User")
    versions = relationship("SectionDraftVersion", back_populates="draft", cascade="all, delete-orphan", order_by="SectionDraftVersion.version")


class SectionDraftVersion(Base):
    __tablename__ = "section_draft_versions"
    __table_args__ = (UniqueConstraint("draft_id", "version", name="uq_section_draft_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("section_drafts.id", ondelete="CASCADE"), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    saved_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    draft = relationship("SectionDraft", back_populates="versions")
    saver = relationship("User")


class GenerationSource(Base):
    __tablename__ = "generation_sources"
    __table_args__ = (UniqueConstraint("generation_run_id", "context_source_id", name="uq_generation_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    generation_run_id: Mapped[int] = mapped_column(ForeignKey("section_generation_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    context_source_id: Mapped[str] = mapped_column(String(32), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)

    run = relationship("SectionGenerationRun", back_populates="sources")


class SectionCitation(Base):
    __tablename__ = "section_citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    section_draft_id: Mapped[int] = mapped_column(ForeignKey("section_drafts.id", ondelete="CASCADE"), index=True, nullable=False)
    generation_run_id: Mapped[int] = mapped_column(ForeignKey("section_generation_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    context_source_id: Mapped[str] = mapped_column(String(32), nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    citation_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    draft = relationship("SectionDraft")
    run = relationship("SectionGenerationRun", back_populates="citations")
