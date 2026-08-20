from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    __table_args__ = (CheckConstraint("scope IN ('system', 'private')", name="ck_knowledge_bases_scope"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[str] = mapped_column(String(32), default="private", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    documents = relationship("KnowledgeDocument", back_populates="knowledge_base", cascade="all, delete-orphan")
    creator = relationship("User")


class KnowledgeCategory(Base):
    __tablename__ = "knowledge_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    documents = relationship("KnowledgeDocumentCategory", back_populates="category", cascade="all, delete-orphan")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'active', 'repealed', 'expired', 'superseded', 'unknown')", name="ck_knowledge_documents_status"),
        CheckConstraint("parser_status IN ('pending', 'parsing', 'parsed', 'failed')", name="ck_knowledge_documents_parser_status"),
        CheckConstraint("index_status IN ('pending', 'chunking', 'chunked', 'embedding', 'indexed', 'failed', 'partial')", name="ck_knowledge_documents_index_status"),
        Index("ix_knowledge_documents_number", "document_number"),
        Index("ix_knowledge_documents_sha256", "sha256"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), default="other", nullable=False)
    document_number: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    issuing_authority: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="zh", nullable=False)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    province: Mapped[str | None] = mapped_column(String(64), nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True)
    district: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_authority: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    parser_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    index_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    parser_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parsed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_content: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    creator = relationship("User")
    categories = relationship("KnowledgeDocumentCategory", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")
    index_runs = relationship("KnowledgeIndexRun", back_populates="document", cascade="all, delete-orphan")


class KnowledgeDocumentCategory(Base):
    __tablename__ = "knowledge_document_categories"
    __table_args__ = (UniqueConstraint("knowledge_document_id", "category_id", name="uq_knowledge_document_category"),)

    knowledge_document_id: Mapped[int] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"), primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("knowledge_categories.id", ondelete="CASCADE"), primary_key=True)
    document = relationship("KnowledgeDocument", back_populates="categories")
    category = relationship("KnowledgeCategory", back_populates="documents")


class DocumentRelation(Base):
    __tablename__ = "knowledge_document_relations"
    __table_args__ = (UniqueConstraint("document_id", "related_document_id", "relation_type", name="uq_knowledge_document_relation"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True, nullable=False)
    related_document_id: Mapped[int] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True, nullable=False)
    relation_type: Mapped[str] = mapped_column(String(32), default="related", nullable=False)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("knowledge_document_id", "chunk_fingerprint", name="uq_knowledge_chunk_fingerprint"),
        Index("ix_knowledge_chunks_document_index", "knowledge_document_id", "chunk_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    knowledge_document_id: Mapped[int] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), default="paragraph", nullable=False)
    section_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    section_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_path: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    article_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    table_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    structured_table: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    character_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    document = relationship("KnowledgeDocument", back_populates="chunks")
    embeddings = relationship("KnowledgeChunkEmbedding", back_populates="chunk", cascade="all, delete-orphan")


class KnowledgeChunkEmbedding(Base):
    __tablename__ = "knowledge_chunk_embeddings"
    __table_args__ = (UniqueConstraint("chunk_id", "provider", "model", "version", name="uq_knowledge_chunk_embedding_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chunk_id: Mapped[int] = mapped_column(ForeignKey("knowledge_chunks.id", ondelete="CASCADE"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[str] = mapped_column(String(64), default="v1", nullable=False)
    distance_metric: Mapped[str] = mapped_column(String(32), default="cosine", nullable=False)
    embedding: Mapped[list[float]] = mapped_column(JSONB, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    api_calls: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chunk = relationship("KnowledgeChunk", back_populates="embeddings")


class KnowledgeIndexRun(Base):
    __tablename__ = "knowledge_index_runs"
    __table_args__ = (CheckConstraint("status IN ('running', 'completed', 'failed', 'partial')", name="ck_knowledge_index_runs_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    knowledge_document_id: Mapped[int] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    stage: Mapped[str] = mapped_column(String(32), default="parse", nullable=False)
    parser_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    chunker_version: Mapped[str] = mapped_column(String(32), default="structure-v1", nullable=False)
    embedding_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    chunks_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunks_embedded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document = relationship("KnowledgeDocument", back_populates="index_runs")
