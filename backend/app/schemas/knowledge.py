from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    scope: str = Field(default="private", pattern="^(system|private)$")


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = Field(default=None, pattern="^(active|disabled)$")


class KnowledgeBaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None
    scope: str
    status: str
    created_by: int
    organization_id: int | None = None
    created_at: datetime
    updated_at: datetime
    document_count: int = 0


class KnowledgeDocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    document_type: str = "other"
    document_number: str | None = None
    issuing_authority: str | None = None
    publish_date: date | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    version: str | None = None
    revision: str | None = None
    status: str = Field(default="unknown", pattern="^(draft|active|repealed|expired|superseded|unknown)$")
    source_url: str | None = None
    language: str = "zh"
    country: str | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None
    source_authority: str = "unknown"
    category_codes: list[str] = Field(default_factory=list)

    @field_validator("document_number")
    @classmethod
    def normalize_number(cls, value: str | None) -> str | None:
        if not value:
            return value
        import re
        value = re.sub(r"\s+", " ", value.strip().upper())
        value = re.sub(r"^([A-Z]{1,4})\s*(\d+)[ -]?(\d{4})$", r"\1 \2-\3", value)
        return value


class KnowledgeDocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    document_type: str | None = None
    document_number: str | None = None
    issuing_authority: str | None = None
    publish_date: date | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    version: str | None = None
    revision: str | None = None
    status: str | None = Field(default=None, pattern="^(draft|active|repealed|expired|superseded|unknown)$")
    source_url: str | None = None
    language: str | None = None
    country: str | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None
    source_authority: str | None = None
    category_codes: list[str] | None = None


class KnowledgeDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    knowledge_base_id: int
    title: str
    document_type: str
    document_number: str | None
    issuing_authority: str | None
    publish_date: date | None
    effective_date: date | None
    expiry_date: date | None
    version: str | None
    revision: str | None
    status: str
    source_url: str | None
    original_file_name: str
    mime_type: str | None
    file_size: int
    sha256: str
    language: str
    country: str | None
    province: str | None
    city: str | None
    district: str | None
    source_authority: str
    parser_status: str
    index_status: str
    parser_name: str | None
    parser_version: str | None
    error_message: str | None
    created_by: int | None
    created_at: datetime
    updated_at: datetime
    categories: list[str] = Field(default_factory=list)
    chunk_count: int = 0


class KnowledgeChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    knowledge_document_id: int
    chunk_index: int
    content: str
    content_type: str
    section_title: str | None
    section_level: int | None
    section_path: list[str] | None
    article_number: str | None
    page_start: int | None
    page_end: int | None
    table_index: int | None
    structured_table: dict[str, Any] | None
    token_count: int
    character_count: int
    metadata_json: dict[str, Any] | None
    content_hash: str
    chunk_fingerprint: str
    embedding_status: str


class KnowledgeDocumentStatusOut(BaseModel):
    document_id: int
    parser_status: str
    index_status: str
    error_message: str | None
    chunks_count: int
    embedded_count: int
    latest_run_id: int | None = None


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    knowledge_base_ids: list[int] = Field(default_factory=list)
    document_types: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    jurisdictions: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    effective_date: date | None = None
    document_number: str | None = None
    top_k: int = Field(default=10, ge=1, le=100)


class KnowledgeSearchResult(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    document_number: str | None
    document_type: str
    categories: list[str]
    jurisdiction: dict[str, str | None]
    version: str | None
    status: str
    section_title: str | None
    section_path: list[str] | None
    article_number: str | None
    page_start: int | None
    page_end: int | None
    content: str
    vector_score: float | None
    keyword_score: float
    rerank_score: float | None
    final_score: float


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeSearchResult]
