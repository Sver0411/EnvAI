from __future__ import annotations

import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings

from .base import DocumentParseError


def ensure_safe_zip(file_path: Path) -> None:
    """在解压 Office Open XML 文件前限制未压缩体积，降低 Zip Bomb 风险。"""
    try:
        with zipfile.ZipFile(file_path) as archive:
            total_size = sum(info.file_size for info in archive.infolist())
    except zipfile.BadZipFile as exc:
        raise DocumentParseError("Office 文件格式无效或已损坏") from exc
    if total_size > settings.max_archive_uncompressed_size_mb * 1024 * 1024:
        raise DocumentParseError("Office 文件解压后超过安全限制")


def to_json_value(value: Any) -> Any:
    """把 Excel 数据转换为可写入 JSONB 的稳定 UTF-8 兼容数据。"""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def ensure_text_limit(text: str) -> str:
    if len(text) > settings.max_plain_text_chars:
        raise DocumentParseError("解析后的文本超过安全限制")
    return text
