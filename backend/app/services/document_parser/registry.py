from __future__ import annotations

from .base import BaseDocumentParser, DocumentParseError
from .docx_parser import DOCXParser
from .excel_parser import ExcelParser
from .image_parser import ImageParser
from .pdf_parser import PDFParser


class ParserRegistry:
    def __init__(self, parsers: list[BaseDocumentParser] | None = None) -> None:
        self.parsers = parsers or [PDFParser(), DOCXParser(), ExcelParser(), ImageParser()]

    def get_parser(self, extension: str) -> BaseDocumentParser:
        for parser in self.parsers:
            if parser.supports(extension):
                return parser
        raise DocumentParseError(f"暂不支持解析 {extension or '该类型'} 文件")


parser_registry = ParserRegistry()
