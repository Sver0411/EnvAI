from __future__ import annotations

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.generation import DocumentTemplate, SectionGenerationConfig, TemplateSection


def seed() -> DocumentTemplate:
    with SessionLocal() as db:
        template = db.scalar(select(DocumentTemplate).where(DocumentTemplate.code == "envai_test_emergency_v1"))
        if template:
            return template
        template = DocumentTemplate(name="EnvAI TEST 环境应急预案", code="envai_test_emergency_v1", document_type="emergency_response", description="仅用于本地开发和自动化测试的章节模板", version="v1", status="active")
        db.add(template)
        db.flush()
        definitions = [
            ("1", "企业概况", 1, 10, "facts_only", True, ["company_name", "project_address", "industry_category"], ["product"]),
            ("2", "主要设备", 1, 20, "facts_only", False, [], ["production_equipment"]),
            ("3", "编制依据", 1, 30, "knowledge_only", True, [], []),
            ("4", "原辅材料及环境风险信息", 1, 40, "facts_and_knowledge", True, [], ["raw_material"]),
        ]
        for code, title, level, order, mode, required, fields, entities in definitions:
            section = TemplateSection(template_id=template.id, section_code=code, title=title, level=level, sort_order=order, generation_mode=mode, required=required, enabled=True)
            db.add(section)
            db.flush()
            db.add(SectionGenerationConfig(section_id=section.id, prompt_template="section_base_v1", required_fields=fields, required_entity_types=entities, knowledge_categories=["environmental_risk", "chemical_management"] if mode == "facts_and_knowledge" else (["general_environment"] if mode == "knowledge_only" else []), knowledge_document_types=["law", "regulation", "technical_guideline"] if mode == "knowledge_only" else [], jurisdiction_policy="project", retrieval_query_template={"编制依据": "环保法律法规 环境影响评价技术导则 编制依据", "原辅材料及环境风险信息": "环境风险物质识别 原辅材料 最大存在量"}.get(title, title), max_project_context=8, max_knowledge_context=8, prompt_version="section_base_v1"))
        db.commit()
        db.refresh(template)
        return template


if __name__ == "__main__":
    template = seed()
    print(f"seeded template id={template.id} code={template.code}")
