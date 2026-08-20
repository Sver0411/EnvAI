from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.parsed_document import ParsedDocument
from app.models.project_file import ProjectFile
from app.repositories.parsed_document_repository import ParsedDocumentRepository
from app.services import storage
from app.services.document_parser import DocumentParseError, parser_registry
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _warnings(document: ParsedDocument) -> list[str]:
    content = document.structured_content or {}
    return list(content.get("warnings", []))


def _save_failure(db: Session, file_id: int, error_message: str, parser_name: str | None = None) -> ParsedDocument:
    document = ParsedDocumentRepository.get(db, file_id)
    project_file = db.get(ProjectFile, file_id)
    if document is None or project_file is None:
        raise NotFoundError("项目文件不存在")
    document.status = "failed"
    document.parser_name = parser_name
    document.error_message = error_message[:500]
    document.parsed_at = None
    project_file.parse_status = "failed"
    db.commit()
    return document


def parse_file(db: Session, project_file: ProjectFile) -> ParsedDocument:
    """同步执行一次解析；调度方式与解析业务解耦，未来可直接移入任务队列。"""
    document = ParsedDocumentRepository.get_or_create(db, project_file.id)
    if document.status == "parsing":
        raise DocumentParseError("文件正在解析，请稍后再试")
    document.status = "parsing"
    document.error_message = None
    project_file.parse_status = "parsing"
    db.commit()

    started = time.monotonic()
    parser_name: str | None = None
    try:
        extension = Path(project_file.filename).suffix.lower()
        parser = parser_registry.get_parser(extension)
        parser_name = parser.name
        backend = storage.get_storage()
        if not project_file.storage_path:
            raise DocumentParseError("文件存储路径不存在")
        file_path = backend.resolve_path(project_file.storage_path)
        if not file_path.is_file():
            raise DocumentParseError("文件实体不存在")
        result = parser.parse(file_path)
    except DocumentParseError as exc:
        logger.warning(
            "parse_failed file_id=%s project_id=%s parser=%s duration_ms=%s reason=%s",
            project_file.id,
            project_file.project_id,
            parser_name,
            round((time.monotonic() - started) * 1000),
            str(exc),
        )
        return _save_failure(db, project_file.id, str(exc), parser_name)
    except Exception:
        logger.exception(
            "parse_failed file_id=%s project_id=%s parser=%s duration_ms=%s",
            project_file.id,
            project_file.project_id,
            parser_name,
            round((time.monotonic() - started) * 1000),
        )
        return _save_failure(db, project_file.id, "文件解析失败，请检查文件内容", parser_name)

    document = ParsedDocumentRepository.get(db, project_file.id)
    project_file = db.get(ProjectFile, project_file.id)
    if document is None or project_file is None:
        raise NotFoundError("项目文件不存在")
    document.parser_name = result.parser_name
    document.parser_version = result.parser_version
    document.status = "parsed"
    document.plain_text = result.plain_text
    document.structured_content = result.structured_content()
    document.document_metadata = result.metadata
    document.error_message = None
    document.parsed_at = datetime.now(timezone.utc)
    project_file.parse_status = "parsed"
    db.commit()
    logger.info(
        "parse_completed file_id=%s project_id=%s parser=%s duration_ms=%s",
        project_file.id,
        project_file.project_id,
        result.parser_name,
        round((time.monotonic() - started) * 1000),
    )
    return document
