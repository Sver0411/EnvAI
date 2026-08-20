from app.models.tenant import Organization, UsageEvent
from app.services.tenant_service import record_usage


def _register(client, username, email):
    client.post("/api/v1/auth/register", json={"username": username, "email": email, "password": "secret123"})
    token = client.post("/api/v1/auth/login", json={"username": username, "password": "secret123"}).json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    org = client.get("/api/v1/organizations", headers=headers).json()["data"][0]
    return headers, org


def test_organization_project_and_knowledge_isolation(client, db):
    a_headers, a_org = _register(client, "tenant_a", "tenant_a@example.com")
    b_headers, b_org = _register(client, "tenant_b", "tenant_b@example.com")
    project = client.post("/api/v1/projects", headers=a_headers, json={"name": "A 私有项目"}).json()["data"]
    assert client.get(f"/api/v1/projects/{project['id']}", headers=b_headers).json()["code"] == 404
    invitation = client.post(f"/api/v1/organizations/{a_org['id']}/invitations", headers=a_headers, json={"email": "tenant_b@example.com", "role": "viewer"}).json()["data"]
    assert client.post(f"/api/v1/invitations/{invitation['token']}/accept", headers=b_headers).json()["code"] == 0
    b_a_headers = {**b_headers, "X-Organization-ID": str(a_org["id"])}
    assert client.get(f"/api/v1/projects/{project['id']}", headers=b_a_headers).json()["code"] == 404
    assert client.post(f"/api/v1/projects/{project['id']}/members", headers=a_headers, json={"user_id": client.get("/api/v1/organizations/" + str(a_org["id"]) + "/members", headers=a_headers).json()["data"][-1]["user_id"], "project_role": "viewer"}).json()["code"] == 0
    assert client.get(f"/api/v1/projects/{project['id']}", headers=b_a_headers).json()["code"] == 0
    kb = client.post("/api/v1/knowledge-bases", headers=a_headers, json={"name": "A 私有知识库", "scope": "private"}).json()["data"]
    assert kb["id"] not in {item["id"] for item in client.get("/api/v1/knowledge-bases", headers=b_headers).json()["data"]}


def test_usage_event_is_idempotent(db):
    org = db.query(Organization).first()
    if org is None:
        return
    first = record_usage(db, organization_id=org.id, usage_type="docx_export", quantity=1, unit="export", source_key="test:one")
    second = record_usage(db, organization_id=org.id, usage_type="docx_export", quantity=99, unit="export", source_key="test:one")
    assert first.id == second.id
