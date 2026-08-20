"""Seed the first production-oriented EnvAI writing templates.

This is intentionally data, not a migration: teams can review and version the
section definitions independently of schema changes.  Running the script is
idempotent and does not touch the existing test template.
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.generation import DocumentTemplate, SectionGenerationConfig, TemplateSection
from app.models.review import ProfessionalRule, ReviewChecklist, ReviewRuleSet


TEMPLATES = [
    {
        "name": "环境影响评价报告（标准版）",
        "code": "envai_environmental_impact_v1",
        "document_type": "environmental_impact",
        "description": "基于企业资料、项目事实和有效环保知识库生成环境影响评价报告草稿。",
        "review_code": "envai_environmental_impact_review_v1",
        "sections": [
            ("1", "项目概况", "facts_only", True, ["company_name", "project_address", "industry_category"], ["company_profile", "product"], [], []),
            ("2", "工程分析", "facts_and_knowledge", True, ["products", "annual_output", "production_process"], ["product", "production_equipment", "raw_material"], ["environmental_impact_assessment", "general_environment"], ["technical_guideline", "case_study"]),
            ("3", "环境现状与环境保护目标", "facts_and_knowledge", True, ["project_address"], ["company_profile"], ["air", "water", "ecology", "general_environment"], ["technical_guideline", "monitoring_plan"]),
            ("4", "污染防治措施及其可行性分析", "facts_and_knowledge", True, [], ["environmental_facility", "raw_material"], ["waste_gas", "wastewater", "solid_waste", "noise", "pollution_permit"], ["technical_guideline", "compliance_checklist"]),
            ("5", "环境风险评价", "facts_and_knowledge", True, [], ["raw_material", "environmental_facility"], ["environmental_risk", "chemical_management", "emergency_response"], ["technical_guideline", "emergency_plan"]),
            ("6", "环境影响评价结论与建议", "facts_and_knowledge", True, [], ["company_profile", "environmental_facility"], ["general_environment", "acceptance"], ["technical_guideline", "compliance_checklist"]),
        ],
        "rules": [
            ("EIA_REQUIRED_1", "项目概况必须完成", "major", "section_requirement", {"section_code": "1"}),
            ("EIA_REQUIRED_2", "工程分析必须完成", "major", "section_requirement", {"section_code": "2"}),
            ("EIA_REQUIRED_4", "污染防治措施必须完成", "critical", "section_requirement", {"section_code": "4"}),
            ("EIA_REQUIRED_5", "环境风险评价必须完成", "critical", "section_requirement", {"section_code": "5"}),
            ("EIA_CITATION", "环评章节应保留有效依据引用", "major", "citation", {}),
            ("EIA_NUMBERS", "报告中的关键数字必须有项目事实依据", "major", "threshold", {"check": "unsupported_numbers"}),
            ("EIA_DUPLICATE", "报告章节不得完全重复", "minor", "consistency", {"check": "duplicate_content"}),
            ("EIA_COMPANY_NAME", "报告不得混入其他企业名称", "critical", "consistency", {"check": "case_contamination"}),
        ],
        "checklists": [
            ("company_facts", "企业事实与结构化数据一致", "document"),
            ("legal_basis", "法规、标准和技术导则引用有效", "document"),
            ("pollution_control", "污染防治措施与污染源匹配", "document"),
            ("risk_analysis", "环境风险识别和防控措施完整", "document"),
        ],
    },
    {
        "name": "突发环境事件应急预案（标准版）",
        "code": "envai_emergency_response_v1",
        "document_type": "emergency_response",
        "description": "基于企业风险物质、设施台账和应急知识库生成突发环境事件应急预案草稿。",
        "review_code": "envai_emergency_response_review_v1",
        "sections": [
            ("1", "总则", "knowledge_only", True, [], [], ["emergency_response", "general_environment"], ["law", "technical_guideline"]),
            ("2", "企业概况与环境风险分析", "facts_and_knowledge", True, ["company_name", "project_address", "industry_category"], ["company_profile", "raw_material", "environmental_facility"], ["environmental_risk", "chemical_management"], ["emergency_plan", "technical_guideline"]),
            ("3", "应急组织体系与职责", "facts_and_knowledge", True, [], ["company_profile"], ["emergency_response"], ["emergency_plan", "compliance_checklist"]),
            ("4", "预防、预警与信息报告", "facts_and_knowledge", True, [], ["raw_material", "environmental_facility"], ["environmental_risk", "emergency_response"], ["emergency_plan", "technical_guideline"]),
            ("5", "应急响应与现场处置", "facts_and_knowledge", True, [], ["raw_material", "environmental_facility"], ["emergency_response", "chemical_management", "wastewater"], ["emergency_plan", "case_study"]),
            ("6", "应急保障、培训与演练", "facts_and_knowledge", True, [], ["company_profile", "environmental_facility"], ["emergency_response", "general_environment"], ["emergency_plan", "drill_record"]),
            ("7", "附件与附录", "facts_and_knowledge", False, [], ["environmental_facility", "raw_material"], ["emergency_response", "environmental_risk"], ["emergency_plan", "compliance_checklist"]),
        ],
        "rules": [
            ("ERP_REQUIRED_1", "总则必须完成", "major", "section_requirement", {"section_code": "1"}),
            ("ERP_REQUIRED_2", "环境风险分析必须完成", "critical", "section_requirement", {"section_code": "2"}),
            ("ERP_REQUIRED_5", "现场处置必须完成", "critical", "section_requirement", {"section_code": "5"}),
            ("ERP_RISK_MATERIAL", "风险物质必须出现在风险分析中", "critical", "presence", {"entity": "raw_material", "section_title": "风险"}),
            ("ERP_CITATION", "应急依据引用必须有效", "major", "citation", {}),
            ("ERP_NUMBERS", "应急资源数量必须有企业事实依据", "major", "threshold", {"check": "unsupported_numbers"}),
            ("ERP_COMPANY_NAME", "预案不得混入其他企业名称", "critical", "consistency", {"check": "case_contamination"}),
        ],
        "checklists": [
            ("company_risk", "企业风险物质和风险单元已核实", "document"),
            ("response_roles", "应急组织和职责明确", "document"),
            ("disposal_measures", "现场处置措施可执行", "document"),
            ("resources_drills", "应急资源、培训和演练安排完整", "document"),
        ],
    },
]


def _ensure_review_rule_set(db, definition: dict) -> ReviewRuleSet:
    rule_set = db.scalar(select(ReviewRuleSet).where(ReviewRuleSet.code == definition["review_code"]))
    if rule_set is None:
        rule_set = ReviewRuleSet(
            name=f"{definition['name']}专业审核规则",
            code=definition["review_code"],
            description="EnvAI 内置专业质量门禁规则，必须结合项目所在地和现行法规由专业人员复核。",
            version="v1",
            status="active",
        )
        db.add(rule_set)
        db.flush()
    existing_rules = {item.code for item in db.scalars(select(ProfessionalRule).where(ProfessionalRule.rule_set_id == rule_set.id))}
    for code, name, severity, rule_type, config in definition["rules"]:
        if code not in existing_rules:
            db.add(ProfessionalRule(rule_set_id=rule_set.id, code=code, name=name, category="document_quality", severity=severity, rule_type=rule_type, config=config, version="v1"))
    existing_checklists = {item.code for item in db.scalars(select(ReviewChecklist).where(ReviewChecklist.rule_set_id == rule_set.id))}
    for index, (code, name, scope_type) in enumerate(definition["checklists"], 1):
        if code not in existing_checklists:
            db.add(ReviewChecklist(rule_set_id=rule_set.id, code=code, name=name, scope_type=scope_type, required=True, sort_order=index))
    db.flush()
    return rule_set


def seed() -> list[DocumentTemplate]:
    templates: list[DocumentTemplate] = []
    with SessionLocal() as db:
        for definition in TEMPLATES:
            template = db.scalar(select(DocumentTemplate).where(DocumentTemplate.code == definition["code"]))
            rule_set = _ensure_review_rule_set(db, definition)
            if template is None:
                template = DocumentTemplate(
                    name=definition["name"],
                    code=definition["code"],
                    document_type=definition["document_type"],
                    description=definition["description"],
                    version="v1",
                    status="active",
                    review_rule_set_id=rule_set.id,
                )
                db.add(template)
                db.flush()
            elif template.review_rule_set_id != rule_set.id:
                template.review_rule_set_id = rule_set.id

            existing_sections = {item.section_code: item for item in db.scalars(select(TemplateSection).where(TemplateSection.template_id == template.id))}
            for index, (code, title, mode, required, required_fields, entity_types, categories, document_types) in enumerate(definition["sections"], 1):
                section = existing_sections.get(code)
                if section is None:
                    section = TemplateSection(template_id=template.id, section_code=code, title=title, level=1, sort_order=index * 10, generation_mode=mode, required=required, enabled=True, description=f"{title}的项目化生成章节")
                    db.add(section)
                    db.flush()
                else:
                    section.title = title
                    section.generation_mode = mode
                    section.required = required
                    section.enabled = True
                    section.sort_order = index * 10
                config = db.scalar(select(SectionGenerationConfig).where(SectionGenerationConfig.section_id == section.id))
                query = f"{title} 环境影响评价 突发环境事件 应急预案"
                if config is None:
                    config = SectionGenerationConfig(section_id=section.id, prompt_template="section_base_v1", required_entity_types=entity_types, required_fields=required_fields, knowledge_categories=categories, knowledge_document_types=document_types, jurisdiction_policy="project", retrieval_query_template=query, max_project_context=10, max_knowledge_context=10, temperature=0.1, generation_schema={"type": "object", "required": ["content", "citations", "missing_information", "warnings"]}, prompt_version="section-v1")
                    db.add(config)
                else:
                    config.required_entity_types = entity_types
                    config.required_fields = required_fields
                    config.knowledge_categories = categories
                    config.knowledge_document_types = document_types
                    config.retrieval_query_template = query
                    config.generation_schema = {"type": "object", "required": ["content", "citations", "missing_information", "warnings"]}
            db.commit()
            db.refresh(template)
            db.expunge(template)
            templates.append(template)
        return templates


if __name__ == "__main__":
    for template in seed():
        print(f"seeded template id={template.id} code={template.code}")
