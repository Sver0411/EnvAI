from app.models.generation import DocumentTemplate, SectionGenerationConfig, TemplateSection
from app.models.knowledge import KnowledgeBase, KnowledgeCategory, KnowledgeChunk, KnowledgeChunkEmbedding, KnowledgeDocument, KnowledgeDocumentCategory
from app.models.user import User
from app.services.embedding import MockEmbeddingProvider
from app.services.generation_service import ContextItem, RetrievalContext, strip_markdown, validate_citations, validate_numbers


def _auth(client, suffix="gen"):
    client.post("/api/v1/auth/register", json={"username": f"{suffix}user", "email": f"{suffix}@example.com", "password": "secret123"})
    token = client.post("/api/v1/auth/login", json={"username": f"{suffix}user", "password": "secret123"}).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _template(db):
    template = DocumentTemplate(name="TEST 章节模板", code="test_generation_template", document_type="emergency_response", status="active")
    db.add(template)
    db.flush()
    section = TemplateSection(template_id=template.id, section_code="1", title="企业概况", level=1, sort_order=1, generation_mode="facts_only", required=True)
    db.add(section)
    db.flush()
    db.add(SectionGenerationConfig(section_id=section.id, prompt_template="section_base_v1", required_fields=["company_name", "project_address"], required_entity_types=[], prompt_version="test-v1"))
    db.commit()
    return template.id, section.id


def test_section_generation_preflight_and_mock_output(client, db):
    headers = _auth(client)
    template_id, section_id = _template(db)
    project = client.post("/api/v1/projects", headers=headers, json={"name": "章节生成测试项目"}).json()["data"]
    instance = client.post(f"/api/v1/projects/{project['id']}/document-instances", headers=headers, json={"template_id": template_id}).json()["data"]
    blocked = client.post(f"/api/v1/document-instances/{instance['id']}/sections/{section_id}/preflight", headers=headers).json()["data"]
    assert blocked["ready"] is False
    client.put(f"/api/v1/projects/{project['id']}/profile", headers=headers, json={"company_name": "测试环保科技有限公司", "project_address": "江苏省苏州市测试园区"})
    ready = client.post(f"/api/v1/document-instances/{instance['id']}/sections/{section_id}/preflight", headers=headers).json()["data"]
    assert ready["ready"] is True
    run = client.post(f"/api/v1/document-instances/{instance['id']}/sections/{section_id}/generate", headers=headers).json()["data"]
    assert run["status"] == "completed"
    view = client.get(f"/api/v1/document-instances/{instance['id']}/sections/{section_id}", headers=headers).json()["data"]
    assert "测试环保科技有限公司" in view["draft"]["content"]
    assert view["draft"]["citations"][0]["source_id"] == "P001"
    updated = client.put(f"/api/v1/section-drafts/{view['draft']['id']}", headers=headers, json={"content": "用户审核后的章节内容"}).json()["data"]
    assert updated["status"] == "reviewed"
    assert updated["version"] == 2


def test_generation_access_is_project_owner_scoped(client, db):
    headers_a = _auth(client, "owner_a")
    headers_b = _auth(client, "owner_b")
    template_id, _ = _template(db)
    project = client.post("/api/v1/projects", headers=headers_a, json={"name": "私有章节项目"}).json()["data"]
    instance = client.post(f"/api/v1/projects/{project['id']}/document-instances", headers=headers_a, json={"template_id": template_id}).json()["data"]
    assert client.get(f"/api/v1/document-instances/{instance['id']}", headers=headers_b).json()["code"] == 404


def test_knowledge_only_section_uses_active_source(client, db):
    headers = _auth(client, "knowledge_gen")
    user = db.query(User).filter(User.username == "knowledge_genuser").one()
    template = DocumentTemplate(name="知识依据模板", code="knowledge_generation_template", document_type="emergency_response", status="active")
    db.add(template)
    db.flush()
    section = TemplateSection(template_id=template.id, section_code="1", title="编制依据", level=1, sort_order=1, generation_mode="knowledge_only", required=True)
    db.add(section)
    db.flush()
    db.add(SectionGenerationConfig(section_id=section.id, prompt_template="section_base_v1", knowledge_categories=["general_environment"], knowledge_document_types=["technical_guideline"], retrieval_query_template="环境风险 技术依据", prompt_version="test-knowledge-v1"))
    category = KnowledgeCategory(code="general_environment", name="综合环保")
    db.add(category)
    db.flush()
    kb = KnowledgeBase(name="系统测试知识库", scope="system", created_by=user.id)
    db.add(kb)
    db.flush()
    document = KnowledgeDocument(knowledge_base_id=kb.id, title="测试环境技术规范", document_type="technical_guideline", document_number="HJ TEST-2026", original_file_name="test.txt", storage_path="knowledge/test.txt", mime_type="text/plain", file_size=10, sha256="a" * 64, status="active", parser_status="parsed", index_status="indexed", province="江苏省", created_by=user.id)
    db.add(document)
    db.flush()
    document.categories.append(KnowledgeDocumentCategory(category=category))
    chunk = KnowledgeChunk(knowledge_document_id=document.id, chunk_index=0, content="环境风险识别应依据本测试技术规范。", content_type="article", section_title="风险识别", content_hash="b" * 64, chunk_fingerprint="c" * 64, token_count=20, character_count=20, embedding_status="embedded")
    db.add(chunk)
    db.flush()
    provider = MockEmbeddingProvider()
    db.add(KnowledgeChunkEmbedding(chunk_id=chunk.id, provider=provider.name, model=provider.model, dimension=provider.dimension, version=provider.version, embedding=provider.embed_texts([chunk.content])[0]))
    db.commit()
    project = client.post("/api/v1/projects", headers=headers, json={"name": "知识依据项目"}).json()["data"]
    instance = client.post(f"/api/v1/projects/{project['id']}/document-instances", headers=headers, json={"template_id": template.id}).json()["data"]
    preflight = client.post(f"/api/v1/document-instances/{instance['id']}/sections/{section.id}/preflight", headers=headers).json()["data"]
    assert preflight["ready"] is True
    run = client.post(f"/api/v1/document-instances/{instance['id']}/sections/{section.id}/generate", headers=headers).json()["data"]
    assert run["status"] == "completed"
    view = client.get(f"/api/v1/document-instances/{instance['id']}/sections/{section.id}", headers=headers).json()["data"]
    assert any(item["source_id"] == "K001" for item in view["draft"]["citations"])


def test_citation_and_numeric_validators_reject_untrusted_output():
    context = RetrievalContext(project_facts=[ContextItem("P001", "project_fact", 1, "设备数量：10 台", {"field_name": "quantity"})])
    citations, warnings = validate_citations({"citations": [{"source_id": "K999", "claim": "不存在"}]}, {"P001": context.project_facts[0]})
    assert citations == []
    assert "K999" in warnings[0]
    assert validate_numbers("设备数量为 12 台。", context)


def test_generated_content_is_plain_text_not_markdown():
    text = strip_markdown("## 污染防治措施\n**一、废气**\n- 安装设施\n1. 定期维护\n[依据](https://example.com)")
    assert "##" not in text and "**" not in text and "[依据]" not in text
    assert "污染防治措施" in text and "一、废气" in text and "1、定期维护" in text
