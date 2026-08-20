"""保守的文本清洗；只清理编码噪声，不改写专业数据。"""
from __future__ import annotations

import re
import unicodedata


class TextNormalizer:
    @staticmethod
    def normalize(value: str | None) -> str:
        if not value:
            return ""
        value = unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n")
        value = "".join(
            char for char in value if char in {"\n", "\t"} or unicodedata.category(char) != "Cc"
        )
        lines = [re.sub(r"[ \t]{2,}", " ", line).rstrip() for line in value.split("\n")]
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
