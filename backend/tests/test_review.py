from app.models.generation import DocumentTemplate, SectionGenerationConfig, TemplateSection
from app.models.review import ProfessionalRule, ReviewRuleSet


def _auth(client):
    client.post("/api/v1/auth/register", json={"username": "reviewuser", "email": "review@example.com", "password": "secret123"})
    token = client.post("/api/v1/auth/login", json={"username": "reviewuser", "password": "secret123"}).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _template_and_rules(db):
    rule_set = ReviewRuleSet(name="TEST Review", code="test_review_rules", version="v1", status="active")
    db.add(rule_set); db.flush()
    db.add_all([
        ProfessionalRule(rule_set_id=rule_set.id, code="case", name="TEST 案例污染", severity="critical", rule_type="consistency", config={"check": "case_contamination"}),
        ProfessionalRule(rule_set_id=rule_set.id, code="number", name="TEST 无依据数字", severity="major", rule_type="threshold", config={"check": "unsupported_numbers"}),
    ])
    template = DocumentTemplate(name="TEST 审核模板", code="test_review_template", document_type="emergency_response", status="active", review_rule_set_id=rule_set.id)
    db.add(template); db.flush()
    section = TemplateSection(template_id=template.id, section_code="1", title="企业概况", level=1, sort_order=1, generation_mode="facts_only", required=True)
    db.add(section); db.flush()
    db.add(SectionGenerationConfig(section_id=section.id, prompt_template="section_base_v1", required_fields=["company_name", "project_address"], prompt_version="review-v1"))
    db.commit(); return template.id, section.id


def test_professional_rules_quality_gate_and_dismiss(client, db):
    headers = _auth(client)
    template_id, section_id = _template_and_rules(db)
    project = client.post("/api/v1/projects", headers=headers, json={"name": "审查测试项目"}).json()["data"]
    client.put(f"/api/v1/projects/{project['id']}/profile", headers=headers, json={"company_name": "江苏测试环保科技有限公司", "project_address": "江苏省苏州市测试园区"})
    instance = client.post(f"/api/v1/projects/{project['id']}/document-instances", headers=headers, json={"template_id": template_id}).json()["data"]
    client.post(f"/api/v1/document-instances/{instance['id']}/generate", headers=headers, json={})
    overview = client.get(f"/api/v1/document-instances/{instance['id']}/overview", headers=headers).json()["data"]
    section_instance = overview["sections"][0]
    view = client.get(f"/api/v1/document-instances/{instance['id']}/sections/{section_id}", headers=headers).json()["data"]
    client.put(f"/api/v1/section-drafts/{view['draft']['id']}", headers=headers, json={"content": "浙江ABC化工有限公司事故废水产生量约为 500 m³。"})
    run = client.post(f"/api/v1/document-instances/{instance['id']}/reviews", headers=headers, json={"mode": "rules_only"}).json()["data"]
    assert run["status"] == "completed"
    issues = client.get(f"/api/v1/document-instances/{instance['id']}/review-issues", headers=headers).json()["data"]
    kinds = {item["issue_type"] for item in issues}
    assert "case_contamination" in kinds
    assert "unsupported_numeric_claim" in kinds
    gate = client.get(f"/api/v1/document-instances/{instance['id']}/quality-gate", headers=headers).json()["data"]
    assert gate["passed"] is False
    dismissed = client.post(f"/api/v1/review-issues/{issues[0]['id']}/dismiss", headers=headers, json={"reason": "TEST 人工确认"}).json()["data"]
    assert dismissed["status"] == "dismissed"


def test_review_access_isolation(client, db):
    headers = _auth(client)
    template_id, _ = _template_and_rules(db)
    project = client.post("/api/v1/projects", headers=headers, json={"name": "私有审核项目"}).json()["data"]
    instance = client.post(f"/api/v1/projects/{project['id']}/document-instances", headers=headers, json={"template_id": template_id}).json()["data"]
    client.post("/api/v1/auth/register", json={"username": "otherreview", "email": "otherreview@example.com", "password": "secret123"})
    other = client.post("/api/v1/auth/login", json={"username": "otherreview", "password": "secret123"}).json()["data"]["access_token"]
    assert client.get(f"/api/v1/document-instances/{instance['id']}/reviews", headers={"Authorization": f"Bearer {other}"}).json()["code"] == 404
