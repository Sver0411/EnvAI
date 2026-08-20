from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SourceChunk:
    text: str
    source_location: dict[str, Any]
    source_type: str


class DocumentContentSelector:
    """在当前项目 ParsedDocument 内按关键词选择片段，不使用向量检索。"""

    @staticmethod
    def select(parsed_document, keywords: list[str]) -> list[SourceChunk]:
        content = parsed_document.structured_content or {}
        needle = tuple(item.lower() for item in keywords)
        chunks: list[SourceChunk] = []

        def add(text: str, location: dict[str, Any], source_type: str) -> None:
            if text and any(word in text.lower() for word in needle):
                chunks.append(SourceChunk(text, location, source_type))

        for page in content.get("pages", []):
            add(str(page.get("text", "")), {"page": page.get("page")}, "pdf_page")
        for paragraph in content.get("paragraphs", []):
            add(
                str(paragraph.get("text", "")),
                {"paragraph": paragraph.get("index"), "style": paragraph.get("style")},
                "paragraph",
            )
        for table in content.get("tables", []):
            for row_index, row in enumerate(table.get("rows", [])):
                text = " | ".join("" if cell is None else str(cell) for cell in row)
                add(text, {"table": table.get("index"), "row": row_index + 1}, "table")
        for sheet in content.get("sheets", []):
            for row_index, row in enumerate(sheet.get("rows", [])):
                text = " | ".join("" if cell is None else str(cell) for cell in row)
                add(text, {"sheet": sheet.get("name"), "row": row_index + 1}, "sheet")
        return chunks
