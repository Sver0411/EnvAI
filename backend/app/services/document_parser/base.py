"""所有文档解析器使用的统一数据结构与异常类型。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class DocumentParseError(Exception):
    """可安全展示给用户的文档解析错误。"""


@dataclass(slots=True)
class ParsedDocumentResult:
    parser_name: str
    parser_version: str
    plain_text: str
    pages: list[dict[str, Any]] = field(default_factory=list)
    paragraphs: list[dict[str, Any]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    sheets: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def structured_content(self) -> dict[str, Any]:
        """保持不同类型文档的 API 返回结构一致。"""
        return {
            "pages": self.pages,
            "paragraphs": self.paragraphs,
            "tables": self.tables,
            "sheets": self.sheets,
            "warnings": self.warnings,
        }


class BaseDocumentParser(ABC):
    name: str
    version = "1.0"
    extensions: set[str]

    def supports(self, extension: str) -> bool:
        return extension.lower() in self.extensions

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocumentResult:
        """解析本地文件并返回标准化结果。"""
