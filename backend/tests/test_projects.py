from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import fitz


def _minimal_xlsx() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/workbook.xml", "<workbook/>")
    return buffer.getvalue()


def _pdf_bytes() -> bytes:
    buffer = BytesIO()
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Environmental project 35 t/a")
    document.save(buffer)
    document.close()
    return buffer.getvalue()


def _register_and_login(client, username="owner", email="owner@example.com", password="secret123"):
    reg = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    ).json()["data"]
    login = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    ).json()["data"]
    return reg, {"Authorization": f"Bearer {login['access_token']}"}


def test_create_project(client):
    user, headers = _register_and_login(client)
    resp = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "某某公司突发环境事件应急预案", "project_type": "emergency_response", "company_name": "某某有限公司"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["name"] == "某某公司突发环境事件应急预案"
    assert data["project_type"] == "emergency_response"
    assert data["status"] == "draft"
    assert data["owner_id"] == user["id"]


def test_list_projects_isolation_between_users(client):
    _, headers_a = _register_and_login(client, username="alice", email="a@example.com")
    _, headers_b = _register_and_login(client, username="bob", email="b@example.com")
    client.post("/api/v1/projects", headers=headers_a, json={"name": "项目A"})
    client.post("/api/v1/projects", headers=headers_b, json={"name": "项目B"})
    resp = client.get("/api/v1/projects", headers=headers_a)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["name"] == "项目A"


def test_get_project_detail(client):
    _, headers = _register_and_login(client)
    created = client.post("/api/v1/projects", headers=headers, json={"name": "风险评估项目"}).json()["data"]
    resp = client.get(f"/api/v1/projects/{created['id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "风险评估项目"


def test_get_project_not_found(client):
    _, headers = _register_and_login(client)
    resp = client.get("/api/v1/projects/9999", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == 404


def test_update_project(client):
    _, headers = _register_and_login(client)
    created = client.post("/api/v1/projects", headers=headers, json={"name": "旧名称"}).json()["data"]
    resp = client.put(
        f"/api/v1/projects/{created['id']}",
        headers=headers,
        json={"name": "新名称", "status": "collecting_data"},
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["name"] == "新名称"
    assert body["data"]["status"] == "collecting_data"


def test_delete_project(client):
    _, headers = _register_and_login(client)
    created = client.post("/api/v1/projects", headers=headers, json={"name": "待删除"}).json()["data"]
    resp = client.delete(f"/api/v1/projects/{created['id']}", headers=headers)
    assert resp.json()["code"] == 0
    resp2 = client.get(f"/api/v1/projects/{created['id']}", headers=headers)
    assert resp2.json()["code"] == 404


def test_cannot_access_others_project(client):
    _, headers_a = _register_and_login(client, username="alice", email="a@example.com")
    _, headers_b = _register_and_login(client, username="bob", email="b@example.com")
    created = client.post("/api/v1/projects", headers=headers_a, json={"name": "A的项目"}).json()["data"]
    resp = client.get(f"/api/v1/projects/{created['id']}", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json()["code"] == 404


def test_upsert_company_profile(client):
    _, headers = _register_and_login(client)
    p = client.post("/api/v1/projects", headers=headers, json={"name": "应急预案项目"}).json()["data"]
    payload = {
        "company_name": "某某环保科技有限公司",
        "credit_code": "91330100MA27XXXXXX",
        "legal_representative": "张三",
        "contact_name": "李四",
        "contact_phone": "13800000000",
        "raw_materials": [
            {"name": "甲苯", "annual_usage": "35", "unit": "t/a", "max_storage": "10", "storage_location": "甲类仓库", "cas_number": "108-88-3"}
        ],
    }
    resp = client.put(f"/api/v1/projects/{p['id']}/profile", headers=headers, json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["company_name"] == "某某环保科技有限公司"
    assert body["data"]["raw_materials"][0]["name"] == "甲苯"

    got = client.get(f"/api/v1/projects/{p['id']}/profile", headers=headers).json()
    assert got["data"]["credit_code"] == "91330100MA27XXXXXX"


def test_upload_and_list_files(client):
    _, headers = _register_and_login(client)
    p = client.post("/api/v1/projects", headers=headers, json={"name": "有附件的项目"}).json()["data"]
    upload = client.post(
        f"/api/v1/projects/{p['id']}/files",
        headers=headers,
        files=[
            ("files", ("环评报告.pdf", b"%PDF-1.4 fake content", "application/pdf")),
            (
                "files",
                (
                    "企业资料.xlsx",
                    _minimal_xlsx(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            ),
        ],
    )
    body = upload.json()
    assert body["code"] == 0
    assert len(body["data"]) == 2
    assert body["data"][0]["filename"] == "环评报告.pdf"
    assert body["data"][0]["parse_status"] == "uploaded"

    lst = client.get(f"/api/v1/projects/{p['id']}/files", headers=headers).json()
    assert lst["code"] == 0
    assert len(lst["data"]) == 2


def test_upload_unsupported_type(client):
    _, headers = _register_and_login(client)
    p = client.post("/api/v1/projects", headers=headers, json={"name": "项目"}).json()["data"]
    resp = client.post(
        f"/api/v1/projects/{p['id']}/files",
        headers=headers,
        files={"files": ("malware.exe", b"MZ...", "application/octet-stream")},
    )
    assert resp.status_code == 200
    assert resp.json()["code"] != 0


def test_upload_rejects_mismatched_content_type(client):
    _, headers = _register_and_login(client)
    p = client.post("/api/v1/projects", headers=headers, json={"name": "项目"}).json()["data"]
    resp = client.post(
        f"/api/v1/projects/{p['id']}/files",
        headers=headers,
        files={"files": ("伪装图片.jpg", b"%PDF-1.4", "application/pdf")},
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 422


def test_download_and_delete_file(client):
    _, headers = _register_and_login(client)
    p = client.post("/api/v1/projects", headers=headers, json={"name": "文件管理项目"}).json()["data"]
    upload = client.post(
        f"/api/v1/projects/{p['id']}/files",
        headers=headers,
        files={"files": ("资料.pdf", b"%PDF-1.4 fake content", "application/pdf")},
    ).json()["data"]
    file_id = upload[0]["id"]

    download = client.get(f"/api/v1/projects/{p['id']}/files/{file_id}/download", headers=headers)
    assert download.status_code == 200
    assert download.content == b"%PDF-1.4 fake content"
    assert "attachment" in download.headers["content-disposition"]

    deleted = client.delete(f"/api/v1/projects/{p['id']}/files/{file_id}", headers=headers)
    assert deleted.json()["code"] == 0
    files = client.get(f"/api/v1/projects/{p['id']}/files", headers=headers).json()["data"]
    assert files == []


def test_parse_status_and_result_are_owner_protected(client):
    _, headers = _register_and_login(client, username="parser_owner", email="parser-owner@example.com")
    _, other_headers = _register_and_login(client, username="parser_other", email="parser-other@example.com")
    project = client.post(
        "/api/v1/projects", headers=headers, json={"name": "解析项目"}
    ).json()["data"]
    uploaded = client.post(
        f"/api/v1/projects/{project['id']}/files",
        headers=headers,
        files={"files": ("资料.pdf", _pdf_bytes(), "application/pdf")},
    ).json()["data"][0]
    file_id = uploaded["id"]

    pending = client.get(
        f"/api/v1/projects/{project['id']}/files/{file_id}/parse-status", headers=headers
    ).json()
    assert pending["data"]["status"] == "pending"

    parsed = client.post(
        f"/api/v1/projects/{project['id']}/files/{file_id}/parse", headers=headers
    ).json()
    assert parsed["code"] == 0
    assert parsed["data"]["status"] == "parsed"
    listed = client.get(f"/api/v1/projects/{project['id']}/files", headers=headers).json()["data"]
    assert listed[0]["parse_status"] == "parsed"

    result = client.get(
        f"/api/v1/projects/{project['id']}/files/{file_id}/parsed", headers=headers
    ).json()
    assert result["code"] == 0
    assert "35 t/a" in result["data"]["plain_text"]
    assert result["data"]["metadata"]["page_count"] == 1

    forbidden = client.get(
        f"/api/v1/projects/{project['id']}/files/{file_id}/parsed", headers=other_headers
    ).json()
    assert forbidden["code"] == 404


def test_parse_failure_is_saved_without_server_error(client):
    _, headers = _register_and_login(client, username="parse_failed", email="parse-failed@example.com")
    project = client.post(
        "/api/v1/projects", headers=headers, json={"name": "损坏文件解析项目"}
    ).json()["data"]
    uploaded = client.post(
        f"/api/v1/projects/{project['id']}/files",
        headers=headers,
        files={"files": ("损坏.pdf", b"%PDF-1.4 not a real pdf", "application/pdf")},
    ).json()["data"][0]

    response = client.post(
        f"/api/v1/projects/{project['id']}/files/{uploaded['id']}/parse", headers=headers
    ).json()
    assert response["code"] == 0
    assert response["data"]["status"] == "failed"
    assert response["data"]["error_message"]
