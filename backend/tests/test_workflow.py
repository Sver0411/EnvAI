from app.models.generation import DocumentTemplate, SectionGenerationConfig, TemplateSection


def _auth(client, suffix="workflow"):
    client.post("/api/v1/auth/register", json={"username": f"{suffix}user", "email": f"{suffix}@example.com", "password": "secret123"})
    token = client.post("/api/v1/auth/login", json={"username": f"{suffix}user", "password": "secret123"}).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _template(db):
    template = DocumentTemplate(name="工作流测试模板", code="workflow_template", document_type="emergency_response", status="active", version="v2")
    db.add(template); db.flush()
    section_a = TemplateSection(template_id=template.id, section_code="1", title="企业概况", level=1, sort_order=1, generation_mode="facts_only", required=True)
    section_b = TemplateSection(template_id=template.id, section_code="2", title="主要设备", level=1, sort_order=2, generation_mode="facts_only", required=False)
    db.add_all([section_a, section_b]); db.flush()
    db.add_all([
        SectionGenerationConfig(section_id=section_a.id, prompt_template="section_base_v1", required_fields=["company_name", "project_address"], prompt_version="workflow-v1"),
        SectionGenerationConfig(section_id=section_b.id, prompt_template="section_base_v1", required_fields=["building_area"], required_entity_types=["production_equipment"], prompt_version="workflow-v1"),
    ])
    db.commit(); return template.id


def test_document_snapshot_batch_review_lock_and_readiness(client, db):
    headers = _auth(client)
    template_id = _template(db)
    project = client.post("/api/v1/projects", headers=headers, json={"name": "完整报告工作流测试"}).json()["data"]
    client.put(f"/api/v1/projects/{project['id']}/profile", headers=headers, json={"company_name": "测试公司", "project_address": "江苏省苏州市测试园区"})
    instance = client.post(f"/api/v1/projects/{project['id']}/document-instances", headers=headers, json={"template_id": template_id}).json()["data"]
    overview = client.get(f"/api/v1/document-instances/{instance['id']}/overview", headers=headers).json()["data"]
    assert overview["instance"]["template_version"] == "v2"
    assert overview["summary"]["total_sections"] == 2
    assert overview["summary"]["ready_sections"] == 1
    section_id = next(item["id"] for item in overview["sections"] if item["section_code"] == "1")
    batch = client.post(f"/api/v1/document-instances/{instance['id']}/generate", headers=headers, json={}).json()["data"]
    assert batch["status"] == "completed"
    assert batch["completed_sections"] == 1
    reviewed = client.post(f"/api/v1/document-sections/{section_id}/review", headers=headers, json={"status": "approved", "comment": "已核对"}).json()["data"]
    assert reviewed["status"] == "approved"
    refreshed = client.get(f"/api/v1/document-instances/{instance['id']}/overview", headers=headers).json()["data"]
    assert next(item for item in refreshed["sections"] if item["id"] == section_id)["status"] == "approved"
    section_snapshot = next(item for item in refreshed["sections"] if item["id"] == section_id)
    section_view = client.get(f"/api/v1/document-instances/{instance['id']}/sections/{section_snapshot['template_section_id']}", headers=headers).json()["data"]
    assert section_view["draft"]["status"] == "approved"
    saved = client.put(f"/api/v1/section-drafts/{section_view['draft']['id']}", headers=headers, json={"content": section_view["draft"]["content"]}).json()["data"]
    assert saved["status"] == "approved"
    refreshed_after_noop_save = client.get(f"/api/v1/document-instances/{instance['id']}/overview", headers=headers).json()["data"]
    assert next(item for item in refreshed_after_noop_save["sections"] if item["id"] == section_id)["status"] == "approved"
    assert client.post(f"/api/v1/document-sections/{section_id}/lock", headers=headers).json()["code"] == 0
    validation = client.post(f"/api/v1/document-instances/{instance['id']}/validate", headers=headers).json()["data"]
    assert validation["status"] == "completed"
    readiness = client.get(f"/api/v1/document-instances/{instance['id']}/readiness", headers=headers).json()["data"]
    assert readiness["ready_for_export"] is True


def test_document_instance_access_isolation(client, db):
    headers_a = _auth(client, "workflow_a")
    headers_b = _auth(client, "workflow_b")
    template_id = _template(db)
    project = client.post("/api/v1/projects", headers=headers_a, json={"name": "A报告"}).json()["data"]
    instance = client.post(f"/api/v1/projects/{project['id']}/document-instances", headers=headers_a, json={"template_id": template_id}).json()["data"]
    assert client.get(f"/api/v1/document-instances/{instance['id']}/overview", headers=headers_b).json()["code"] == 404


def test_dependency_cycle_is_rejected(client, db):
    headers = _auth(client, "dependency")
    template_id = _template(db)
    project = client.post("/api/v1/projects", headers=headers, json={"name": "依赖测试"}).json()["data"]
    instance = client.post(f"/api/v1/projects/{project['id']}/document-instances", headers=headers, json={"template_id": template_id}).json()["data"]
    sections = client.get(f"/api/v1/document-instances/{instance['id']}/overview", headers=headers).json()["data"]["sections"]
    first, second = sections[0]["id"], sections[1]["id"]
    assert client.post(f"/api/v1/document-sections/{second}/dependencies", headers=headers, json={"depends_on_section_instance_id": first, "dependency_type": "generation"}).json()["code"] == 0
    cycle = client.post(f"/api/v1/document-sections/{first}/dependencies", headers=headers, json={"depends_on_section_instance_id": second, "dependency_type": "generation"}).json()
    assert cycle["code"] == 422


def test_generated_section_becomes_stale_after_profile_update(client, db):
    headers = _auth(client, "stale")
    template_id = _template(db)
    project = client.post("/api/v1/projects", headers=headers, json={"name": "过期检测测试"}).json()["data"]
    client.put(f"/api/v1/projects/{project['id']}/profile", headers=headers, json={"company_name": "旧名称", "project_address": "江苏省苏州市测试园区"})
    instance = client.post(f"/api/v1/projects/{project['id']}/document-instances", headers=headers, json={"template_id": template_id}).json()["data"]
    client.post(f"/api/v1/document-instances/{instance['id']}/generate", headers=headers, json={})
    client.put(f"/api/v1/projects/{project['id']}/profile", headers=headers, json={"company_name": "新名称", "project_address": "江苏省苏州市测试园区"})
    overview = client.get(f"/api/v1/document-instances/{instance['id']}/overview", headers=headers).json()["data"]
    assert any(section["status"] == "stale" for section in overview["sections"])
