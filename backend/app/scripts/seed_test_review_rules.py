from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.review import ProfessionalRule, ReviewChecklist, ReviewRuleSet
from app.models.generation import DocumentTemplate


RULES = [
    ("TEST_RISK_SECTION", "风险物质分析章节", "environmental_risk", "major", "relationship", {"condition": "risk_material_exists", "required_title": "风险"}),
    ("TEST_RAW_MATERIAL_COVERAGE", "原辅材料覆盖", "raw_material", "major", "presence", {"entity": "raw_material", "section_title": "风险"}),
    ("TEST_LEGAL_CITATION", "编制依据引用", "legal_basis", "major", "citation", {"section_title": "编制依据"}),
    ("TEST_CITATION_ACTIVE", "引用有效性", "citation", "major", "citation", {}),
    ("TEST_CASE_CONTAMINATION", "案例企业污染", "company_information", "critical", "consistency", {"check": "case_contamination"}),
    ("TEST_UNSUPPORTED_NUMBER", "无依据关键数字", "consistency", "major", "threshold", {"check": "unsupported_numbers"}),
    ("TEST_DUPLICATE_CONTENT", "章节重复内容", "document_structure", "minor", "consistency", {"check": "duplicate_content"}),
]


def seed() -> ReviewRuleSet:
    with SessionLocal() as db:
        rule_set = db.scalar(select(ReviewRuleSet).where(ReviewRuleSet.code == "envai_test_emergency_review_v1"))
        if rule_set:
            existing_codes = {item.code for item in db.scalars(select(ProfessionalRule).where(ProfessionalRule.rule_set_id == rule_set.id))}
            for code, name, category, severity, rule_type, config in RULES:
                if code not in existing_codes:
                    db.add(ProfessionalRule(rule_set_id=rule_set.id, code=code, name=name, category=category, severity=severity, rule_type=rule_type, config=config, version="v1"))
            template = db.scalar(select(DocumentTemplate).where(DocumentTemplate.code == "envai_test_emergency_v1"))
            if template and template.review_rule_set_id != rule_set.id:
                template.review_rule_set_id = rule_set.id
            db.commit(); db.refresh(rule_set)
            return rule_set
        rule_set = ReviewRuleSet(name="EnvAI TEST Emergency Review V1", code="envai_test_emergency_review_v1", description="仅供本地开发与自动化测试，不代表真实法规或官方审核规范", version="v1", status="active")
        db.add(rule_set); db.flush()
        for code, name, category, severity, rule_type, config in RULES:
            db.add(ProfessionalRule(rule_set_id=rule_set.id, code=code, name=name, category=category, severity=severity, rule_type=rule_type, config=config, version="v1"))
        for index, (code, name) in enumerate([("company_facts", "企业基本信息与结构化事实一致"), ("citation_quality", "引用来源有效且相关"), ("risk_coverage", "环境风险分析覆盖已确认风险物质")], 1):
            db.add(ReviewChecklist(rule_set_id=rule_set.id, code=code, name=name, scope_type="section", required=True, sort_order=index))
        template = db.scalar(select(DocumentTemplate).where(DocumentTemplate.code == "envai_test_emergency_v1"))
        if template:
            template.review_rule_set_id = rule_set.id
        db.commit(); db.refresh(rule_set); return rule_set


if __name__ == "__main__":
    result = seed(); print(f"seeded review rule set id={result.id} code={result.code}")
