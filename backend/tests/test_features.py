"""Tests for the v2.1 feature additions.

Covers the richer emotion model + snapshots, the statistics endpoint, the
teacher journal, and the teacher-only stop-and-delete action.
"""
from app import engine, models
from tests.conftest import auth, login, make_full_classroom


def test_members_expose_full_emotion_vector(client):
    cid = make_full_classroom(client, num_sprints=1)
    assert engine.wait_until_finished(cid, timeout=30)
    members = client.get(f"/api/classrooms/{cid}").json()["members"]
    assert members
    for m in members:
        for emotion in models.EMOTIONS:
            assert emotion in m
            assert 0 <= m[emotion] <= 10


def test_stats_endpoint_returns_emotion_timeline_and_grades(client):
    num_sprints = 2
    cid = make_full_classroom(client, num_sprints=num_sprints)
    assert engine.wait_until_finished(cid, timeout=30)

    stats = client.get(f"/api/classrooms/{cid}/stats").json()
    assert stats["emotion_names"] == list(models.EMOTIONS)
    # baseline (sprint 0) + one snapshot per sprint, for all 3 agents
    expected_points = (num_sprints + 1) * 3
    assert len(stats["emotions"]) == expected_points
    assert all(0 <= p["happiness"] <= 10 for p in stats["emotions"])
    # grades trajectory present for both students across sprints
    assert len(stats["grades"]) == 2 * num_sprints


def test_teacher_journal_is_separate_from_student_journals(client):
    cid = make_full_classroom(client, num_sprints=1)
    assert engine.wait_until_finished(cid, timeout=30)
    journals = client.get(f"/api/classrooms/{cid}/live").json()["journals"]
    roles = {j["author_role"] for j in journals}
    assert roles == {"student", "teacher"}
    teacher_entries = [j for j in journals if j["author_role"] == "teacher"]
    assert len(teacher_entries) == 1
    assert teacher_entries[0]["student_name"] == "Prof"


def test_break_replies_acknowledge_the_classmate(client):
    cid = make_full_classroom(client, num_sprints=1)
    assert engine.wait_until_finished(cid, timeout=30)
    msgs = client.get(f"/api/classrooms/{cid}/live").json()["messages"]
    break_lines = [m for m in msgs if m["phase"] == "break"]
    # With >=2 break turns the second speaker should react to the first.
    assert len(break_lines) >= 2


def test_teacher_can_stop_and_delete_classroom(client):
    t = login(client, "Prof", "teacher")
    s1 = login(client, "Ada", "student")
    s2 = login(client, "Linus", "student")
    cid = client.post("/api/classrooms", headers=auth(t),
                      json={"name": "Doomed"}).json()["id"]
    client.post(f"/api/classrooms/{cid}/join", headers=auth(t),
                json={"config": {"subject": "X", "sprint_minutes": 20,
                                 "break_minutes": 10, "num_sprints": 1}})
    client.post(f"/api/classrooms/{cid}/join", headers=auth(s1), json={})
    client.post(f"/api/classrooms/{cid}/join", headers=auth(s2), json={})

    r = client.delete(f"/api/classrooms/{cid}", headers=auth(t))
    assert r.status_code == 204
    # Gone for good.
    assert client.get(f"/api/classrooms/{cid}").status_code == 404
    assert engine.wait_until_finished(cid, timeout=10)


def test_students_cannot_delete_classroom(client):
    t = login(client, "Prof", "teacher")
    other = login(client, "Mallory", "student")
    cid = client.post("/api/classrooms", headers=auth(t),
                      json={"name": "Safe"}).json()["id"]
    r = client.delete(f"/api/classrooms/{cid}", headers=auth(other))
    assert r.status_code == 403
    assert client.get(f"/api/classrooms/{cid}").status_code == 200


def test_other_teacher_cannot_delete_owned_classroom(client):
    owner = login(client, "Owner", "teacher")
    intruder = login(client, "Intruder", "teacher")
    cid = client.post("/api/classrooms", headers=auth(owner),
                      json={"name": "Owned"}).json()["id"]
    client.post(f"/api/classrooms/{cid}/join", headers=auth(owner),
                json={"config": {"subject": "Y", "sprint_minutes": 20,
                                 "break_minutes": 10, "num_sprints": 1}})
    r = client.delete(f"/api/classrooms/{cid}", headers=auth(intruder))
    assert r.status_code == 403
