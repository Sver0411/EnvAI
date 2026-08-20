from io import BytesIO

import fitz
from app.services.knowledge_chunker import build_knowledge_chunks


def _pdf_bytes() -> bytes:
    buffer = BytesIO()
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Test environmental risk specification\nHJ TEST-2026\n1 Scope\nThis document defines risk material identification requirements.\n2 Terms\nRisk materials require identification.")
    document.save(buffer)
    document.close()
    return buffer.getvalue()


def _auth(client):
    client.post("/api/v1/auth/register", json={"username": "kbuser", "email": "kbuser@example.com", "password": "secret123"})
    token = client.post("/api/v1/auth/login", json={"username": "kbuser", "password": "secret123"}).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_knowledge_process_and_search(client):
    headers = _auth(client)
    kb = client.post("/api/v1/knowledge-bases", headers=headers, json={"name": "测试法规库", "scope": "private"}).json()["data"]
    uploaded = client.post(f"/api/v1/knowledge-bases/{kb['id']}/documents", headers=headers, files={"file": ("测试规范.pdf", _pdf_bytes(), "application/pdf")}, data={"metadata": '{"title":"测试环境风险技术规范","document_type":"technical_guideline","document_number":"HJ TEST-2026","status":"active","category_codes":["environmental_risk"]}'}).json()
    assert uploaded["code"] == 0, uploaded
    document_id = uploaded["data"]["id"]
    assert uploaded["data"]["categories"] == ["environmental_risk"]
    processed = client.post(f"/api/v1/knowledge-documents/{document_id}/process", headers=headers).json()
    assert processed["code"] == 0, processed
    assert processed["data"]["index_status"] == "indexed"
    chunks = client.get(f"/api/v1/knowledge-documents/{document_id}/chunks", headers=headers).json()["data"]
    assert chunks
    search = client.post("/api/v1/knowledge/search", headers=headers, json={"query": "risk material", "top_k": 5}).json()
    assert search["code"] == 0
    assert any("risk" in item["content"].lower() for item in search["data"]["results"])


def test_structure_chunker_detects_article_and_table():
    chunks = build_knowledge_chunks({"tables": [{"index": 0, "rows": [["污染物", "限值"], ["颗粒物", "120"]]}]}, "第一章 总则\n第一条 本条款用于测试。\n第二条 继续测试。")
    assert any(chunk.article_number == "一" for chunk in chunks)
    table = next(chunk for chunk in chunks if chunk.content_type == "table")
    assert table.structured_table == {"headers": ["污染物", "限值"], "rows": [["颗粒物", "120"]]}


def test_private_knowledge_base_isolation(client):
    headers_a = _auth(client)
    client.post("/api/v1/auth/register", json={"username": "kbuserb", "email": "kbuserb@example.com", "password": "secret123"})
    token_b = client.post("/api/v1/auth/login", json={"username": "kbuserb", "password": "secret123"}).json()["data"]["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    kb = client.post("/api/v1/knowledge-bases", headers=headers_a, json={"name": "私有库", "scope": "private"}).json()["data"]
    assert client.get(f"/api/v1/knowledge-bases/{kb['id']}", headers=headers_b).json()["code"] == 404
