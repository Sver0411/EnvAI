from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ParsedDocument(Base):
    """项目文件的可追溯解析结果；每个文件仅保留当前有效的一份结果。"""

    __tablename__ = "parsed_documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'parsing', 'parsed', 'failed')",
            name="ck_parsed_documents_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_file_id: Mapped[int] = mapped_column(
        ForeignKey("project_files.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    parser_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    plain_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_content: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    document_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project_file = relationship("ProjectFile", back_populates="parsed_document")
