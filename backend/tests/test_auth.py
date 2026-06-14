from tests.conftest import auth, login


def test_login_returns_token_and_role(client):
    r = client.post("/api/auth/login", json={"display_name": "Prof", "role": "teacher"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token"]
    assert body["user"]["role"] == "teacher"
    assert body["user"]["display_name"] == "Prof"


def test_login_strips_display_name(client):
    r = client.post("/api/auth/login", json={"display_name": "  Ada  ", "role": "student"})
    assert r.json()["user"]["display_name"] == "Ada"


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_current_user(client):
    token = login(client, "Linus", "student")
    r = client.get("/api/auth/me", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["role"] == "student"


def test_logout_revokes_token(client):
    token = login(client, "Prof", "teacher")
    assert client.post("/api/auth/logout", headers=auth(token)).status_code == 200
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 401


def test_invalid_role_rejected(client):
    r = client.post("/api/auth/login", json={"display_name": "X", "role": "admin"})
    assert r.status_code == 422
