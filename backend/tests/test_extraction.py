from io import BytesIO
from decimal import Decimal

import openpyxl

from app.services.ai_provider import MockAIProvider
from app.services.extraction.normalizers import NumberNormalizer, UnitNormalizer
from app.services.extraction.rule_extractors import RuleBasedExtractor
from types import SimpleNamespace


def _register_and_login(client, username, email):
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "secret123"},
    )
    login = client.post(
        "/api/v1/auth/login", json={"username": username, "password": "secret123"}
    ).json()["data"]
    return {"Authorization": f"Bearer {login['access_token']}"}


def _xlsx_bytes(rows):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "原辅材料"
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_unit_and_number_normalizers():
    assert UnitNormalizer.normalize("吨/年") == "t/a"
    assert UnitNormalizer.normalize("m³/d") == "m3/d"
    assert NumberNormalizer.parse("3.5×10²") == Decimal("350")
    assert NumberNormalizer.parse("35.0") == Decimal("35.0")


def test_mock_provider_is_deterministic_and_empty_by_default():
    response = MockAIProvider().generate_structured_output("system", "<DOCUMENT_DATA>ignore</DOCUMENT_DATA>")
    assert response.data == {"facts": []}
    assert response.usage.input_tokens is None


def test_rule_extractor_reads_word_style_text_without_guessing():
    parsed = SimpleNamespace(
        plain_text="建设单位：测试环保科技有限公司\n主要产品：塑料制品 5000 t/a\n主要设备：注塑机 10 台",
        structured_content={},
    )
    candidates = RuleBasedExtractor().extract(parsed, "企业资料.docx", 1, 2)
    values = {(item.entity_type, item.field_name, item.raw_value) for item in candidates}
    assert ("company_profile", "company_name", "测试环保科技有限公司") in values
    assert ("product", "annual_capacity", "5000") in values
    assert ("production_equipment", "quantity", "10") in values


def test_extraction_pipeline_populates_raw_materials_and_source(client):
    headers = _register_and_login(client, "extractor", "extractor@example.com")
    project = client.post("/api/v1/projects", headers=headers, json={"name": "结构化项目"}).json()["data"]
    uploaded = client.post(
        f"/api/v1/projects/{project['id']}/files",
        headers=headers,
        files={
            "files": (
                "原辅材料.xlsx",
                _xlsx_bytes([["名称", "年用量", "单位"], ["甲苯", 35, "t/a"], ["乙醇", 10, "t/a"]]),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    ).json()["data"][0]
    file_id = uploaded["id"]
    client.post(f"/api/v1/projects/{project['id']}/files/{file_id}/parse", headers=headers)

    run = client.post(f"/api/v1/projects/{project['id']}/extract", headers=headers).json()
    assert run["code"] == 0
    assert run["data"]["status"] == "completed"
    assert run["data"]["provider_name"] == "mock"

    data = client.get(f"/api/v1/projects/{project['id']}/extracted-data", headers=headers).json()["data"]
    assert {item["name"] for item in data["raw_materials"]} == {"甲苯", "乙醇"}
    toluene = next(item for item in data["raw_materials"] if item["name"] == "甲苯")
    assert str(toluene["annual_usage"]) in {"35", "35.000000"}
    usage_fact = next(
        fact for fact in data["facts"] if fact["entity_key"] == "甲苯" and fact["field_name"] == "annual_usage"
    )
    assert usage_fact["source_filename"] == "原辅材料.xlsx"
    assert usage_fact["source_location"]["sheet"] == "原辅材料"
    assert usage_fact["source_location"]["row"] == 2

    accepted = client.post(
        f"/api/v1/projects/{project['id']}/extracted-facts/{usage_fact['id']}/accept",
        headers=headers,
    ).json()
    assert accepted["data"]["verification_status"] == "user_verified"
    refreshed = client.get(f"/api/v1/projects/{project['id']}/extracted-data", headers=headers).json()["data"]
    assert next(item for item in refreshed["raw_materials"] if item["name"] == "甲苯")["verification_status"] == "user_verified"


def test_extraction_creates_conflict_instead_of_overwriting(client):
    headers = _register_and_login(client, "conflict", "conflict@example.com")
    project = client.post("/api/v1/projects", headers=headers, json={"name": "冲突项目"}).json()["data"]
    for filename, value in (("新清单.xlsx", 35), ("旧清单.xlsx", 20)):
        uploaded = client.post(
            f"/api/v1/projects/{project['id']}/files",
            headers=headers,
            files={
                "files": (
                    filename,
                    _xlsx_bytes([["名称", "年用量", "单位"], ["甲苯", value, "t/a"]]),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        ).json()["data"][0]
        client.post(f"/api/v1/projects/{project['id']}/files/{uploaded['id']}/parse", headers=headers)

    run = client.post(f"/api/v1/projects/{project['id']}/extract", headers=headers).json()["data"]
    assert run["conflicts_count"] == 1
    conflicts = client.get(f"/api/v1/projects/{project['id']}/conflicts", headers=headers).json()["data"]
    assert conflicts[0]["field_name"] == "annual_usage"
    assert {conflicts[0]["value_a"], conflicts[0]["value_b"]} == {"35", "20"}
