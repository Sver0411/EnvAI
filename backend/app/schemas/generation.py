from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TemplateSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    template_id: int
    parent_id: int | None
    section_code: str
    title: str
    level: int
    sort_order: int
    description: str | None
    generation_mode: str
    required: bool
    enabled: bool
    children: list["TemplateSectionOut"] = Field(default_factory=list)


class DocumentTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    document_type: str
    description: str | None
    version: str
    status: str
    sections: list[TemplateSectionOut] = Field(default_factory=list)


class DocumentInstanceCreate(BaseModel):
    template_id: int
    title: str | None = None
    reference_date: date | None = None


class DocumentInstanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    template_id: int
    title: str
    status: str
    reference_date: date | None
    created_by: int
    organization_id: int | None = None
    created_at: datetime
    updated_at: datetime


class MissingInformation(BaseModel):
    field: str
    reason: str


class GenerationCitation(BaseModel):
    source_id: str
    claim: str


class SectionPreflightOut(BaseModel):
    ready: bool
    missing_fields: list[MissingInformation] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    project_fact_count: int = 0
    project_source_count: int = 0
    knowledge_source_count: int = 0


class SectionDraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    document_instance_id: int
    template_id: int
    section_id: int
    generation_run_id: int | None
    content: str
    ai_original_content: str | None
    status: str
    version: int
    citations: list[GenerationCitation] = Field(default_factory=list)
    missing_information: list[MissingInformation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generation_metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class SectionDraftUpdate(BaseModel):
    content: str = Field(min_length=1)


class SectionViewOut(BaseModel):
    section: TemplateSectionOut
    draft: SectionDraftOut | None = None


class GenerationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    document_instance_id: int
    section_id: int
    status: str
    ai_provider: str | None
    model: str | None
    prompt_version: str | None
    input_tokens: int | None
    output_tokens: int | None
    project_fact_count: int
    project_source_count: int
    knowledge_source_count: int
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None


class GenerationSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_type: str
    source_id: int
    context_source_id: str
    rank: int | None
    score: float | None
    metadata_json: dict[str, Any] | None


class SectionCitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_type: str
    source_id: int
    context_source_id: str
    claim_text: str
    citation_order: int


DocumentTemplateOut.model_rebuild()
