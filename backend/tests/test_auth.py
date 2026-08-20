def _register(client, username="tester", email="tester@example.com", password="secret123"):
    return client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password, "full_name": "测试用户"},
    )


def test_register_success(client):
    resp = _register(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["username"] == "tester"
    assert "password" not in body["data"]
    assert body["data"]["id"] > 0


def test_register_duplicate_email(client):
    _register(client)
    resp = _register(client, username="other", email="tester@example.com")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] != 0
    assert "邮箱" in body["message"]

def test_register_duplicate_username(client):
    _register(client)
    resp = _register(client, username="tester", email="other@example.com")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] != 0
    assert "用户名" in body["message"]

def test_register_weak_password(client):
    resp = _register(client, password="123")
    assert resp.status_code == 200
    assert resp.json()["code"] != 0


def _login(client, username="tester", password="secret123"):
    return client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )


def test_login_success(client):
    _register(client)
    resp = _login(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["access_token"]
    assert body["data"]["user"]["username"] == "tester"


def test_login_wrong_password(client):
    _register(client)
    resp = _login(client, password="wrongpass")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] != 0
    assert "用户名或密码错误" in body["message"]


def test_me_with_token(client):
    _register(client)
    login = _login(client).json()["data"]
    token = login["access_token"]
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["data"]["username"] == "tester"


def test_me_without_token(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 401

def test_me_invalid_token(client):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 200
    assert resp.json()["code"] == 401