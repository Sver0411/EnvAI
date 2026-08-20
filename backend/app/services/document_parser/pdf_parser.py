from __future__ import annotations

from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover - 兼容旧版 PyMuPDF
    import fitz

from app.core.config import settings

from .base import BaseDocumentParser, DocumentParseError, ParsedDocumentResult
from .normalizer import TextNormalizer
from .utils import ensure_text_limit


class PDFParser(BaseDocumentParser):
    name = "pymupdf"
    extensions = {".pdf"}

    def parse(self, file_path: Path) -> ParsedDocumentResult:
        try:
            document = fitz.open(file_path)
        except (fitz.FileDataError, RuntimeError) as exc:
            raise DocumentParseError("PDF 文件无效或已损坏") from exc

        try:
            if document.page_count > settings.max_pdf_pages:
                raise DocumentParseError(f"PDF 页数超过 {settings.max_pdf_pages} 页限制")
            pages: list[dict] = []
            full_text_parts: list[str] = []
            extracted_characters = 0
            for index, page in enumerate(document, start=1):
                text = TextNormalizer.normalize(page.get_text("text"))
                pages.append({"page": index, "text": text})
                extracted_characters += len(text)
                full_text_parts.append(f"--- Page {index} ---\n\n{text}")
            warnings: list[str] = []
            requires_ocr = document.page_count > 0 and extracted_characters < settings.scanned_pdf_min_text_chars
            if requires_ocr:
                warnings.append("possible_scanned_pdf")
            metadata = {
                "page_count": document.page_count,
                "source_metadata": {key: value for key, value in document.metadata.items() if value},
                "requires_ocr": requires_ocr,
            }
            return ParsedDocumentResult(
                parser_name=self.name,
                parser_version=self.version,
                plain_text=ensure_text_limit(TextNormalizer.normalize("\n\n".join(full_text_parts))),
                pages=pages,
                metadata=metadata,
                warnings=warnings,
            )
        finally:
            document.close()
