from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.core.config import settings

from .base import BaseDocumentParser, DocumentParseError, ParsedDocumentResult


class ImageParser(BaseDocumentParser):
    name = "pillow"
    extensions = {".png", ".jpg", ".jpeg"}

    def parse(self, file_path: Path) -> ParsedDocumentResult:
        try:
            with Image.open(file_path) as image:
                width, height = image.size
                if width * height > settings.max_image_pixels:
                    raise DocumentParseError("图片像素超过安全限制")
                metadata = {
                    "width": width,
                    "height": height,
                    "format": image.format,
                    "mode": image.mode,
                    "file_size": file_path.stat().st_size,
                    "requires_ocr": True,
                }
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
            raise DocumentParseError("图片文件无效或已损坏") from exc
        return ParsedDocumentResult(
            parser_name=self.name,
            parser_version=self.version,
            plain_text="",
            metadata=metadata,
            warnings=["ocr_not_configured"],
        )
