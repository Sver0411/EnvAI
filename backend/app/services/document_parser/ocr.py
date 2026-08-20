"""OCR 扩展边界；Phase 2 默认不安装重量级 OCR 引擎。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class OCRResult:
    text: str
    blocks: list[dict]


class OCRProvider:
    def extract_text(self, file_path: Path) -> OCRResult:
        raise NotImplementedError


class NoopOCRProvider(OCRProvider):
    """明确返回未配置状态，避免把图片误报成已完成 OCR。"""

    def extract_text(self, file_path: Path) -> OCRResult:
        return OCRResult(text="", blocks=[])
