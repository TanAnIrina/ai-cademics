"""Tests for the v2.2 additions: N students, scheduling, ratings, PDF export."""
from datetime import UTC, datetime, timedelta

from app import engine
from tests.conftest import auth, login


def _make(client, *, num_students=2, num_sprints=1, scheduled_start=None, name="Room"):
    """Create a classroom, fill teacher + num_students seats; return classroom id."""
    t = login(client, "Prof", "teacher")
    cid = client.post("/api/classrooms", headers=auth(t), json={"name": name}).json()["id"]
    cfg = {"subject": "Graph Theory", "sprint_minutes": 20, "break_minutes": 10,
           "num_sprints": num_sprints, "num_students": num_students}
    if scheduled_start is not None:
        cfg["scheduled_start"] = scheduled_start
    client.post(f"/api/classrooms/{cid}/join", headers=auth(t), json={"config": cfg})
    for i in range(num_students):
        s = login(client, f"Stud{i}", "student")
        client.post(f"/api/classrooms/{cid}/join", headers=auth(s), json={})
    return cid


# --- N students -------------------------------------------------------------
def test_classroom_supports_three_students(client):
    cid = _make(client, num_students=3, num_sprints=2)
    room = client.get(f"/api/classrooms/{cid}").json()
    assert room["max_students"] == 3
    student_slots = [m["slot"] for m in room["members"] if m["role"] == "student"]
    assert set(student_slots) == {"student_a", "student_b", "student_c"}
    assert room["free_slots"] == []  # full -> session starts

    assert engine.wait_until_finished(cid, timeout=30)
    lv = client.get(f"/api/classrooms/{cid}/live").json()
    # 3 students graded + journal each sprint; teacher journals once per sprint
    assert len(lv["grades"]) == 3 * 2
    student_journals = [j for j in lv["journals"] if j["author_role"] == "student"]
    assert len(student_journals) == 3 * 2
    # statistics snapshot every agent (teacher + 3 students) per sprint + baseline
    stats = client.get(f"/api/classrooms/{cid}/stats").json()
    assert len(stats["emotions"]) == (2 + 1) * 4


def test_five_students_is_the_cap(client):
    cid = _make(client, num_students=5, num_sprints=1)
    room = client.get(f"/api/classrooms/{cid}").json()
    assert room["max_students"] == 5
    assert len([m for m in room["members"] if m["role"] == "student"]) == 5
    assert engine.wait_until_finished(cid, timeout=30)


def test_third_student_rejected_when_capacity_is_two(client):
    cid = _make(client, num_students=2, num_sprints=1)
    extra = login(client, "Extra", "student")
    # room is full (and likely running/finished); joining must fail
    r = client.post(f"/api/classrooms/{cid}/join", headers=auth(extra), json={})
    assert r.status_code in (409, 404)


# --- scheduling -------------------------------------------------------------
def test_scheduled_room_does_not_start_before_time(client):
    future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    cid = _make(client, num_students=2, scheduled_start=future)
    room = client.get(f"/api/classrooms/{cid}").json()
    assert room["scheduled_start"] is not None
    # full but scheduled in the future -> must remain waiting, not running
    assert room["status"] == "waiting"


def test_past_schedule_starts_immediately(client):
    past = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    cid = _make(client, num_students=2, scheduled_start=past)
    # a past schedule should not block the auto-start
    assert engine.wait_until_finished(cid, timeout=30)
    assert client.get(f"/api/classrooms/{cid}").json()["status"] == "finished"


# --- lesson ratings ---------------------------------------------------------
def test_observer_can_rate_lesson(client):
    cid = _make(client, num_students=2, num_sprints=1)
    engine.wait_until_finished(cid, timeout=30)
    # ratings are open (no auth), like the observer chat
    r = client.post(f"/api/classrooms/{cid}/ratings",
                    json={"nickname": "watcher", "stars": 5, "comment": "Great lesson!"})
    assert r.status_code == 200
    r2 = client.post(f"/api/classrooms/{cid}/ratings",
                     json={"nickname": "other", "stars": 3, "comment": ""})
    summary = r2.json()
    assert summary["count"] == 2
    assert summary["average"] == 4.0
    assert {x["nickname"] for x in summary["ratings"]} == {"watcher", "other"}


def test_rating_validation_rejects_out_of_range(client):
    cid = _make(client, num_students=2, num_sprints=1)
    r = client.post(f"/api/classrooms/{cid}/ratings",
                    json={"nickname": "x", "stars": 9})
    assert r.status_code == 422


# --- PDF export -------------------------------------------------------------
def test_pdf_export_of_archived_session(client):
    cid = _make(client, num_students=2, num_sprints=1)
    assert engine.wait_until_finished(cid, timeout=30)
    archive_id = client.get("/api/history").json()[0]["id"]
    r = client.get(f"/api/history/{archive_id}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"
    assert len(r.content) > 800


def test_ratings_posted_after_finish_appear_in_history(client):
    cid = _make(client, num_students=2, num_sprints=1)
    assert engine.wait_until_finished(cid, timeout=30)
    # rate AFTER the session ended (the common observer flow)
    client.post(f"/api/classrooms/{cid}/ratings", json={"nickname": "late", "stars": 4})
    archive_id = client.get("/api/history").json()[0]["id"]
    detail = client.get(f"/api/history/{archive_id}").json()
    ratings = detail["session"]["ratings"]
    assert any(r["nickname"] == "late" for r in ratings)
