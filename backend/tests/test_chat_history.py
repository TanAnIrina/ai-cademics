from app import engine
from tests.conftest import auth, login, make_full_classroom


# --- observer chat ---------------------------------------------------------
def test_chat_post_and_fetch(client):
    t = login(client, "Prof", "teacher")
    cid = client.post("/api/classrooms", headers=auth(t), json={"name": "R"}).json()["id"]

    # no auth needed to chat
    r = client.post(f"/api/classrooms/{cid}/chat", json={"nickname": "viewer1", "content": "hello"})
    assert r.status_code == 200
    assert r.json()["nickname"] == "viewer1"

    msgs = client.get(f"/api/classrooms/{cid}/chat").json()
    assert len(msgs) == 1
    assert msgs[0]["content"] == "hello"


def test_chat_is_per_classroom(client):
    t = login(client, "Prof", "teacher")
    c1 = client.post("/api/classrooms", headers=auth(t), json={"name": "A"}).json()["id"]
    c2 = client.post("/api/classrooms", headers=auth(t), json={"name": "B"}).json()["id"]

    client.post(f"/api/classrooms/{c1}/chat", json={"nickname": "v", "content": "in room A"})
    assert len(client.get(f"/api/classrooms/{c1}/chat").json()) == 1
    assert len(client.get(f"/api/classrooms/{c2}/chat").json()) == 0


def test_chat_after_id_pagination(client):
    t = login(client, "Prof", "teacher")
    cid = client.post("/api/classrooms", headers=auth(t), json={"name": "R"}).json()["id"]
    first = client.post(
        f"/api/classrooms/{cid}/chat", json={"nickname": "v", "content": "1"}
    ).json()
    client.post(f"/api/classrooms/{cid}/chat", json={"nickname": "v", "content": "2"})
    newer = client.get(f"/api/classrooms/{cid}/chat", params={"after_id": first["id"]}).json()
    assert len(newer) == 1 and newer[0]["content"] == "2"


def test_chat_unknown_classroom_404(client):
    assert client.get("/api/classrooms/9999/chat").status_code == 404
    assert client.post("/api/classrooms/9999/chat",
                       json={"nickname": "v", "content": "x"}).status_code == 404


# --- history ---------------------------------------------------------------
def test_history_empty_initially(client):
    assert client.get("/api/history").json() == []


def test_history_unknown_archive_404(client):
    assert client.get("/api/history/9999").status_code == 404


def test_history_records_observer_chat_snapshot(client):
    cid = make_full_classroom(client, subject="Logic", num_sprints=1)
    # leave an observer message before completion
    client.post(f"/api/classrooms/{cid}/chat", json={"nickname": "fan", "content": "go team"})
    assert engine.wait_until_finished(cid, timeout=30)

    archive = client.get("/api/history").json()[0]
    full = client.get(f"/api/history/{archive['id']}").json()
    chat = full["session"]["observer_chat"]
    assert any(m["content"] == "go team" for m in chat)
