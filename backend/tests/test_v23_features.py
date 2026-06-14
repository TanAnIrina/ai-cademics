"""Tests for v2.3: paced interactive lessons, diversified tests, per-sprint subject choice."""
import threading
import time

from app import engine
from tests.conftest import auth, login


def _run(client, *, num_sprints=1, num_students=2, subject="Linear Algebra"):
    t = login(client, "Prof", "teacher")
    cid = client.post("/api/classrooms", headers=auth(t), json={"name": "R"}).json()["id"]
    client.post(f"/api/classrooms/{cid}/join", headers=auth(t),
                json={"config": {"subject": subject, "sprint_minutes": 20,
                                 "break_minutes": 10, "num_sprints": num_sprints,
                                 "num_students": num_students}})
    for i in range(num_students):
        client.post(f"/api/classrooms/{cid}/join",
                    headers=auth(login(client, f"S{i}", "student")), json={})
    return cid


# --- interactive lesson -----------------------------------------------------
def test_lesson_is_an_interactive_discussion(client):
    cid = _run(client, num_sprints=1)
    assert engine.wait_until_finished(cid, timeout=30)
    msgs = client.get(f"/api/classrooms/{cid}/live").json()["messages"]
    lesson = [m for m in msgs if m["phase"] == "lesson"]
    # many turns, not a single block
    assert len(lesson) >= 8
    roles = {m["sender_role"] for m in lesson}
    # both teacher teaching and students asking during the lesson
    assert roles == {"teacher", "student"}
    assert any(m["sender_role"] == "student" for m in lesson)


# --- diversified test -------------------------------------------------------
def test_test_questions_use_diverse_formats(client):
    cid = _run(client, num_sprints=1)
    assert engine.wait_until_finished(cid, timeout=30)
    msgs = client.get(f"/api/classrooms/{cid}/live").json()["messages"]
    test_msg = next(m for m in msgs if m["phase"] == "test" and m["sender_role"] == "teacher")
    text = test_msg["content"].lower()
    forms = ["define", "example", "true or false", "compare", "why does",
             "apply", "scenario", "limitation"]
    present = sum(1 for f in forms if f in text)
    assert present >= 6  # clearly varied, not one repeated template


# --- subject choice mechanism ----------------------------------------------
def test_await_subject_keeps_current_when_disabled(client):
    # conftest sets subject_choice_seconds=0 -> no pause, keep current
    assert engine._await_subject(123456, "Algebra") == "Algebra"


def test_await_subject_returns_teacher_choice(client):
    cid = 765432
    engine.settings.subject_choice_seconds = 5.0  # enable waiting for this test
    try:
        out = {}

        def runner():
            out["v"] = engine._await_subject(cid, "OldSubject")

        th = threading.Thread(target=runner)
        th.start()
        # wait until the engine is actually waiting on a choice
        for _ in range(100):
            if engine.is_choosing(cid):
                break
            time.sleep(0.02)
        engine.submit_next_subject(cid, "  Quantum Computing  ")
        th.join(timeout=5)
        assert out["v"] == "Quantum Computing"  # trimmed
    finally:
        engine.settings.subject_choice_seconds = 0.0


# --- endpoints --------------------------------------------------------------
def test_random_subject_endpoint_returns_a_subject(client):
    cid = _run(client, num_sprints=1)
    r = client.get(f"/api/classrooms/{cid}/random-subject")
    assert r.status_code == 200
    assert isinstance(r.json()["subject"], str) and r.json()["subject"]


def test_next_subject_requires_teacher(client):
    cid = _run(client, num_sprints=1)
    student = login(client, "Nobody", "student")
    r = client.post(f"/api/classrooms/{cid}/next-subject",
                    headers=auth(student), json={"subject": "Hacking"})
    assert r.status_code == 403


def test_next_subject_409_when_not_choosing(client):
    # a fresh classroom (not mid-session) is not waiting for a subject
    t = login(client, "Prof", "teacher")
    cid = client.post("/api/classrooms", headers=auth(t), json={"name": "Idle"}).json()["id"]
    client.post(f"/api/classrooms/{cid}/join", headers=auth(t),
                json={"config": {"subject": "X", "sprint_minutes": 20,
                                 "break_minutes": 10, "num_sprints": 1, "num_students": 2}})
    r = client.post(f"/api/classrooms/{cid}/next-subject",
                    headers=auth(t), json={"subject": "Y"})
    assert r.status_code == 409
