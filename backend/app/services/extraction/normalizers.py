from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation


class UnitNormalizer:
    _UNIT_MAP = {
        "吨/年": "t/a",
        "吨/每年": "t/a",
        "t/a": "t/a",
        "t·a-1": "t/a",
        "t·a^-1": "t/a",
        "kg/a": "kg/a",
        "千克/年": "kg/a",
        "公斤/年": "kg/a",
        "m³/d": "m3/d",
        "m3/d": "m3/d",
        "立方米/天": "m3/d",
        "mg/m³": "mg/m3",
        "mg/m3": "mg/m3",
        "毫克/立方米": "mg/m3",
        "台": "台",
        "套": "套",
        "个": "个",
    }

    @classmethod
    def normalize(cls, unit: str | None) -> str | None:
        if not unit:
            return None
        key = unit.strip().lower().replace(" ", "").replace("／", "/")
        return cls._UNIT_MAP.get(key, unit.strip())


class NumberNormalizer:
    _NUMBER = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?")
    _SCIENTIFIC = re.compile(r"([-+]?\d+(?:\.\d+)?)\s*[×x]\s*10\s*\^?\s*([-+]?[\d⁰¹²³⁴⁵⁶⁷⁸⁹][\d⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]*)")
    _SUPERSCRIPT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻", "0123456789+-")

    @classmethod
    def parse(cls, value: str | int | float | Decimal | None) -> Decimal | None:
        if value is None or value == "":
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        text = str(value).strip().replace("，", "").replace(",", "")
        scientific = cls._SCIENTIFIC.search(text)
        try:
            if scientific:
                exponent = scientific.group(2).translate(cls._SUPERSCRIPT)
                return Decimal(scientific.group(1)) * (Decimal(10) ** int(exponent))
            match = cls._NUMBER.search(text)
            return Decimal(match.group(0)) if match else None
        except (InvalidOperation, ValueError):
            return None

    @classmethod
    def value_and_unit(cls, value: str | int | float | Decimal | None, unit: str | None = None):
        raw = "" if value is None else str(value)
        parsed = cls.parse(value)
        detected_unit = unit
        if not detected_unit:
            detected_unit = re.sub(cls._NUMBER, "", raw).replace("约", "").strip(" ：:，,") or None
        return parsed, detected_unit
