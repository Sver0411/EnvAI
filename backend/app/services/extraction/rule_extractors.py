from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .content_selector import DocumentContentSelector, SourceChunk
from .normalizers import NumberNormalizer, UnitNormalizer


@dataclass(slots=True)
class ExtractionCandidate:
    entity_type: str
    entity_key: str
    field_name: str
    raw_value: str
    normalized_value: dict[str, Any] | None
    raw_unit: str | None
    unit: str | None
    confidence: Decimal
    source_type: str
    source_location: dict[str, Any]
    source_text: str


def _candidate(
    entity_type: str,
    entity_key: str,
    field_name: str,
    value: Any,
    chunk: SourceChunk,
    unit: str | None = None,
    confidence: str = "0.95",
) -> ExtractionCandidate:
    raw = "" if value is None else str(value).strip()
    number = NumberNormalizer.parse(value)
    normalized = {"value": str(number) if number is not None else raw}
    if unit:
        normalized["unit"] = UnitNormalizer.normalize(unit)
    return ExtractionCandidate(
        entity_type=entity_type,
        entity_key=entity_key.strip(),
        field_name=field_name,
        raw_value=raw,
        normalized_value=normalized,
        raw_unit=unit,
        unit=UnitNormalizer.normalize(unit),
        confidence=Decimal(confidence),
        source_type=chunk.source_type,
        source_location=chunk.source_location,
        source_text=chunk.text,
    )


def _column(headers: list[Any], keywords: tuple[str, ...]) -> int | None:
    for index, header in enumerate(headers):
        text = str(header or "").lower().replace(" ", "")
        if any(keyword in text for keyword in keywords):
            return index
    return None


def _table_rows(parsed_document, kinds: tuple[str, ...]):
    content = parsed_document.structured_content or {}
    for table in content.get("tables", []):
        rows = table.get("rows", [])
        if rows:
            yield rows, lambda index, table=table: SourceChunk(
                " | ".join("" if cell is None else str(cell) for cell in rows[index]),
                {"table": table.get("index"), "row": index + 1},
                "table",
            )
    for sheet in content.get("sheets", []):
        rows = sheet.get("rows", [])
        if rows:
            yield rows, lambda index, sheet=sheet: SourceChunk(
                " | ".join("" if cell is None else str(cell) for cell in rows[index]),
                {"sheet": sheet.get("name"), "row": index + 1},
                "sheet",
            )


class RuleBasedExtractor:
    version = "rule-v1"
    prompt_version = "structured-v1"

    def extract(
        self,
        parsed_document,
        filename: str,
        file_id: int,
        parsed_document_id: int,
        enabled_extractors: set[str] | None = None,
    ) -> list[ExtractionCandidate]:
        enabled = enabled_extractors or {"company", "product", "equipment", "raw_material", "facility"}
        candidates: list[ExtractionCandidate] = []
        if "company" in enabled:
            candidates.extend(self._company(parsed_document))
        if "product" in enabled:
            candidates.extend(self._products(parsed_document))
        if "equipment" in enabled:
            candidates.extend(self._equipment(parsed_document))
        if "raw_material" in enabled:
            candidates.extend(self._materials(parsed_document))
        if "facility" in enabled:
            candidates.extend(self._facilities(parsed_document))
        for candidate in candidates:
            candidate.source_location.update(file_id=file_id, parsed_document_id=parsed_document_id)
        return candidates

    def _text_chunks(self, parsed_document) -> list[SourceChunk]:
        selected = DocumentContentSelector.select(
            parsed_document,
            ["建设单位", "企业名称", "项目地址", "主要产品", "主要设备", "原辅材料", "环保设施"],
        )
        if selected:
            return selected
        return [SourceChunk(str(parsed_document.plain_text or ""), {}, "text")] if parsed_document.plain_text else []

    def _company(self, parsed_document) -> list[ExtractionCandidate]:
        results = []
        patterns = {
            "company_name": (r"(?:建设单位|企业名称|公司名称|单位名称)\s*[:：|]\s*([^\n|]+)", "company_name"),
            "project_address": (r"(?:项目所在地|项目地址|建设地址)\s*[:：|]\s*([^\n|]+)", "project_address"),
            "legal_representative": (r"(?:法定代表人|法人代表)\s*[:：|]\s*([^\n|]+)", "legal_representative"),
            "industry_category": (r"(?:行业类别|所属行业)\s*[:：|]\s*([^\n|]+)", "industry_category"),
        }
        for chunk in self._text_chunks(parsed_document):
            for field, (pattern, entity_key) in patterns.items():
                match = re.search(pattern, chunk.text, re.IGNORECASE)
                if match:
                    results.append(_candidate("company_profile", "project", field, match.group(1), chunk, confidence="0.82"))
        return results

    def _products(self, parsed_document) -> list[ExtractionCandidate]:
        results = []
        for rows, make_chunk in _table_rows(parsed_document, ("产品", "产量")):
            headers = rows[0]
            name_col = _column(headers, ("产品", "产品名称", "名称"))
            capacity_col = _column(headers, ("年产", "产能", "产量", "年生产"))
            unit_col = _column(headers, ("单位",))
            if name_col is None:
                continue
            for index, row in enumerate(rows[1:], start=1):
                if name_col >= len(row) or not str(row[name_col] or "").strip():
                    continue
                name = str(row[name_col]).strip()
                results.append(_candidate("product", name, "name", name, make_chunk(index)))
                if capacity_col is not None and capacity_col < len(row):
                    value = row[capacity_col]
                    unit = row[unit_col] if unit_col is not None and unit_col < len(row) else None
                    number, detected_unit = NumberNormalizer.value_and_unit(value, unit)
                    if number is not None:
                        results.append(_candidate("product", name, "annual_capacity", value, make_chunk(index), detected_unit))
        if not results:
            pattern = re.compile(r"(?:主要产品|产品)\s*[:：]\s*([^\n]+)")
            value_pattern = re.compile(r"([^,，;；|]+?)\s*([-+]?\d[\d,.]*(?:\.\d+)?)\s*([^\s,，;；|]+)?")
            for chunk in self._text_chunks(parsed_document):
                match = pattern.search(chunk.text)
                if not match:
                    continue
                item = value_pattern.search(match.group(1))
                if item:
                    name, value, unit = item.group(1).strip(), item.group(2), item.group(3)
                    results.append(_candidate("product", name, "name", name, chunk, confidence="0.82"))
                    results.append(_candidate("product", name, "annual_capacity", value, chunk, unit, confidence="0.82"))
        return results

    def _equipment(self, parsed_document) -> list[ExtractionCandidate]:
        results = []
        for rows, make_chunk in _table_rows(parsed_document, ("设备", "机器")):
            headers = rows[0]
            name_col = _column(headers, ("设备名称", "设备", "名称", "机器"))
            model_col = _column(headers, ("型号", "规格"))
            quantity_col = _column(headers, ("数量", "台数"))
            unit_col = _column(headers, ("单位",))
            if name_col is None:
                continue
            for index, row in enumerate(rows[1:], start=1):
                if name_col >= len(row) or not str(row[name_col] or "").strip():
                    continue
                name = str(row[name_col]).strip()
                chunk = make_chunk(index)
                results.append(_candidate("production_equipment", name, "name", name, chunk))
                if model_col is not None and model_col < len(row) and row[model_col] not in (None, ""):
                    results.append(_candidate("production_equipment", name, "model", row[model_col], chunk))
                if quantity_col is not None and quantity_col < len(row):
                    unit = row[unit_col] if unit_col is not None and unit_col < len(row) else None
                    number, detected_unit = NumberNormalizer.value_and_unit(row[quantity_col], unit)
                    if number is not None:
                        results.append(_candidate("production_equipment", name, "quantity", row[quantity_col], chunk, detected_unit))
        if not results:
            pattern = re.compile(r"(?:主要设备|生产设备|设备清单)\s*[:：]\s*([^\n]+)")
            value_pattern = re.compile(r"([^,，;；|]+?)\s*([-+]?\d[\d,.]*(?:\.\d+)?)\s*(台|套|个)")
            for chunk in self._text_chunks(parsed_document):
                match = pattern.search(chunk.text)
                if not match:
                    continue
                for item in value_pattern.finditer(match.group(1)):
                    name, quantity, unit = item.group(1).strip(), item.group(2), item.group(3)
                    results.append(_candidate("production_equipment", name, "name", name, chunk, confidence="0.82"))
                    results.append(_candidate("production_equipment", name, "quantity", quantity, chunk, unit, confidence="0.82"))
        return results

    def _materials(self, parsed_document) -> list[ExtractionCandidate]:
        results = []
        for rows, make_chunk in _table_rows(parsed_document, ("原辅", "原料", "辅料", "化学品")):
            headers = rows[0]
            name_col = _column(headers, ("原辅材料名称", "原材料", "辅料", "物料", "名称"))
            usage_col = _column(headers, ("年用量", "年使用量", "消耗量", "用量"))
            unit_col = _column(headers, ("单位",))
            storage_col = _column(headers, ("最大储量", "储存量", "库存"))
            location_col = _column(headers, ("储存位置", "存放位置", "仓库"))
            cas_col = _column(headers, ("cas", "cas号"))
            if name_col is None:
                continue
            for index, row in enumerate(rows[1:], start=1):
                if name_col >= len(row) or not str(row[name_col] or "").strip():
                    continue
                name = str(row[name_col]).strip()
                chunk = make_chunk(index)
                results.append(_candidate("raw_material", name, "name", name, chunk))
                if usage_col is not None and usage_col < len(row):
                    unit = row[unit_col] if unit_col is not None and unit_col < len(row) else None
                    number, detected_unit = NumberNormalizer.value_and_unit(row[usage_col], unit)
                    if number is not None:
                        results.append(_candidate("raw_material", name, "annual_usage", row[usage_col], chunk, detected_unit))
                if storage_col is not None and storage_col < len(row):
                    unit = row[unit_col] if unit_col is not None and unit_col < len(row) else None
                    number, detected_unit = NumberNormalizer.value_and_unit(row[storage_col], unit)
                    if number is not None:
                        results.append(_candidate("raw_material", name, "max_storage", row[storage_col], chunk, detected_unit))
                if location_col is not None and location_col < len(row) and row[location_col] not in (None, ""):
                    results.append(_candidate("raw_material", name, "storage_location", row[location_col], chunk))
                if cas_col is not None and cas_col < len(row) and row[cas_col] not in (None, ""):
                    results.append(_candidate("raw_material", name, "cas_number", row[cas_col], chunk))
        if not results:
            pattern = re.compile(r"(?:原辅材料|主要原料|原材料)\s*[:：]\s*([^\n]+)")
            value_pattern = re.compile(r"([^,，;；|]+?)\s*([-+]?\d[\d,.]*(?:\.\d+)?)\s*([^\s,，;；|]+)?")
            for chunk in self._text_chunks(parsed_document):
                match = pattern.search(chunk.text)
                if not match:
                    continue
                for item in value_pattern.finditer(match.group(1)):
                    name, value, unit = item.group(1).strip(), item.group(2), item.group(3)
                    results.append(_candidate("raw_material", name, "name", name, chunk, confidence="0.82"))
                    results.append(_candidate("raw_material", name, "annual_usage", value, chunk, unit, confidence="0.82"))
        return results

    def _facilities(self, parsed_document) -> list[ExtractionCandidate]:
        results = []
        for chunk in DocumentContentSelector.select(parsed_document, ["环保设施", "治理设施", "除尘器", "活性炭", "污水处理"]):
            text = chunk.text.strip()
            match = re.search(r"(?:环保设施|治理设施)\s*[:：]\s*([^\n|]+)", text)
            if match:
                name = match.group(1).strip()
                results.append(_candidate("environmental_facility", name, "name", name, chunk, confidence="0.82"))
        return results
