from __future__ import annotations


class ExtractionPlanner:
    """基于文件名、Sheet 名和已解析结构选择首版抽取器，不引入 Agent。"""

    def plan(self, filename: str, parsed_document) -> set[str]:
        name = filename.lower()
        content = parsed_document.structured_content or {}
        searchable = " ".join(
            [name]
            + [str(item.get("name", "")) for item in content.get("sheets", [])]
            + [str(item.get("text", "")) for item in content.get("paragraphs", [])[:20]]
        ).lower()
        plan = {"company", "product", "equipment", "raw_material", "facility"}
        if any(keyword in searchable for keyword in ("原辅", "原料", "化学品")):
            plan.add("raw_material")
        return plan
