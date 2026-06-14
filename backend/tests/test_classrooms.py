from tests.conftest import auth, login


# --- anonymous / observer access -------------------------------------------
def test_anonymous_can_list_classrooms(client):
    login(client, "Prof", "teacher")  # create at least one room
    cid = client.post(
        "/api/classrooms",
        headers=auth(login(client, "Prof2", "teacher")),
        json={"name": "Open Room"},
    ).json()["id"]
    r = client.get("/api/classrooms")
    assert r.status_code == 200
    assert any(c["id"] == cid for c in r.json())


def test_anonymous_cannot_create_or_join(client):
    assert client.post("/api/classrooms", json={"name": "X"}).status_code == 401
    # create a room as teacher, then try to join anonymously
    t = login(client, "Prof", "teacher")
    cid = client.post("/api/classrooms", headers=auth(t), json={"name": "R"}).json()["id"]
    assert client.post(f"/api/classrooms/{cid}/join", json={}).status_code == 401


# --- role enforcement ------------------------------------------------------
def test_student_cannot_create_classroom(client):
    s = login(client, "Ada", "student")
    r = client.post("/api/classrooms", headers=auth(s), json={"name": "Nope"})
    assert r.status_code == 403


def test_teacher_can_create_classroom(client):
    t = login(client, "Prof", "teacher")
    r = client.post("/api/classrooms", headers=auth(t), json={"name": "Mathlab"})
    assert r.status_code == 200
    assert r.json()["name"] == "Mathlab"
    assert r.json()["status"] == "waiting"
    assert set(r.json()["free_slots"]) == {"teacher", "student_a", "student_b"}


def test_teacher_join_requires_config(client):
    t = login(client, "Prof", "teacher")
    cid = client.post("/api/classrooms", headers=auth(t), json={"name": "R"}).json()["id"]
    r = client.post(f"/api/classrooms/{cid}/join", headers=auth(t), json={})
    assert r.status_code == 422


def test_teacher_join_sets_subject_and_takes_teacher_slot(client):
    t = login(client, "Prof", "teacher")
    cid = client.post("/api/classrooms", headers=auth(t), json={"name": "R"}).json()["id"]
    r = client.post(
        f"/api/classrooms/{cid}/join",
        headers=auth(t),
        json={"config": {"subject": "Topology", "sprint_minutes": 15,
                         "break_minutes": 5, "num_sprints": 3}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["subject"] == "Topology"
    assert body["sprint_minutes"] == 15 and body["num_sprints"] == 3
    assert "teacher" not in body["free_slots"]


def test_user_cannot_be_in_two_active_classrooms(client):
    t = login(client, "Prof", "teacher")
    c1 = client.post("/api/classrooms", headers=auth(t), json={"name": "A"}).json()["id"]
    c2 = client.post("/api/classrooms", headers=auth(t), json={"name": "B"}).json()["id"]
    cfg = {"config": {"subject": "S", "sprint_minutes": 20, "break_minutes": 10, "num_sprints": 1}}
    assert client.post(f"/api/classrooms/{c1}/join", headers=auth(t), json=cfg).status_code == 200
    assert client.post(f"/api/classrooms/{c2}/join", headers=auth(t), json=cfg).status_code == 409


def test_second_teacher_cannot_take_teacher_slot(client):
    t1 = login(client, "Prof1", "teacher")
    t2 = login(client, "Prof2", "teacher")
    cid = client.post("/api/classrooms", headers=auth(t1), json={"name": "R"}).json()["id"]
    cfg = {"config": {"subject": "S", "sprint_minutes": 20, "break_minutes": 10, "num_sprints": 1}}
    client.post(f"/api/classrooms/{cid}/join", headers=auth(t1), json=cfg)
    r = client.post(f"/api/classrooms/{cid}/join", headers=auth(t2), json=cfg)
    assert r.status_code == 409


def test_students_fill_remaining_slots(client):
    t = login(client, "Prof", "teacher")
    s1 = login(client, "Ada", "student")
    s2 = login(client, "Linus", "student")
    s3 = login(client, "Grace", "student")
    cid = client.post("/api/classrooms", headers=auth(t), json={"name": "R"}).json()["id"]
    cfg = {"config": {"subject": "S", "sprint_minutes": 20, "break_minutes": 10, "num_sprints": 1}}
    client.post(f"/api/classrooms/{cid}/join", headers=auth(t), json=cfg)
    assert client.post(f"/api/classrooms/{cid}/join", headers=auth(s1), json={}).status_code == 200
    assert client.post(f"/api/classrooms/{cid}/join", headers=auth(s2), json={}).status_code == 200
    # third student: room no longer waiting (full -> started) => 409
    assert client.post(f"/api/classrooms/{cid}/join", headers=auth(s3), json={}).status_code == 409


# --- configure / leave -----------------------------------------------------
def test_only_classroom_teacher_can_configure(client):
    t1 = login(client, "Prof1", "teacher")
    t2 = login(client, "Prof2", "teacher")
    cid = client.post("/api/classrooms", headers=auth(t1), json={"name": "R"}).json()["id"]
    cfg = {"config": {"subject": "S", "sprint_minutes": 20, "break_minutes": 10, "num_sprints": 1}}
    client.post(f"/api/classrooms/{cid}/join", headers=auth(t1), json=cfg)
    new = {"subject": "New", "sprint_minutes": 30, "break_minutes": 5, "num_sprints": 4}
    bad = client.post(f"/api/classrooms/{cid}/configure", headers=auth(t2), json=new)
    assert bad.status_code == 403
    r = client.post(f"/api/classrooms/{cid}/configure", headers=auth(t1), json=new)
    assert r.status_code == 200 and r.json()["num_sprints"] == 4


def test_teacher_leaving_clears_subject(client):
    t = login(client, "Prof", "teacher")
    cid = client.post("/api/classrooms", headers=auth(t), json={"name": "R"}).json()["id"]
    cfg = {"config": {"subject": "Calculus", "sprint_minutes": 20,
                      "break_minutes": 10, "num_sprints": 1}}
    client.post(f"/api/classrooms/{cid}/join", headers=auth(t), json=cfg)
    r = client.post(f"/api/classrooms/{cid}/leave", headers=auth(t))
    assert r.status_code == 200
    assert r.json()["subject"] is None
    assert "teacher" in r.json()["free_slots"]


# --- estimate (time vs sessions chart) -------------------------------------
def test_estimate_math(client):
    r = client.get("/api/classrooms/estimate",
                   params={"sprint_minutes": 20, "break_minutes": 10, "max_sprints": 3})
    assert r.status_code == 200
    pts = r.json()["points"]
    assert pts[0] == {"num_sprints": 1, "total_minutes": 20}
    assert pts[1] == {"num_sprints": 2, "total_minutes": 50}
    assert pts[2] == {"num_sprints": 3, "total_minutes": 80}


def test_estimate_is_reachable_anonymously(client):
    # /estimate must be matched before /{cid}; anonymous observers can use it.
    assert client.get("/api/classrooms/estimate").status_code == 200
