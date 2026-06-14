from app import engine
from tests.conftest import make_full_classroom


def test_full_classroom_runs_to_completion(client):
    cid = make_full_classroom(client, subject="Graph Theory", num_sprints=2)
    assert engine.wait_until_finished(cid, timeout=30)

    c = client.get(f"/api/classrooms/{cid}").status_code
    # finished rooms are excluded from the live list but still fetchable by id
    assert c == 200
    detail = client.get(f"/api/classrooms/{cid}").json()
    assert detail["status"] == "finished"
    assert detail["progress"] == 1.0


def test_simulation_produces_expected_records(client):
    num_sprints = 2
    cid = make_full_classroom(client, num_sprints=num_sprints)
    assert engine.wait_until_finished(cid, timeout=30)

    lv = client.get(f"/api/classrooms/{cid}/live").json()
    # 2 students graded once per sprint
    assert len(lv["grades"]) == 2 * num_sprints
    # 2 students + 1 teacher journal once per sprint
    student_journals = [j for j in lv["journals"] if j["author_role"] == "student"]
    teacher_journals = [j for j in lv["journals"] if j["author_role"] == "teacher"]
    assert len(student_journals) == 2 * num_sprints
    assert len(teacher_journals) == 1 * num_sprints
    assert len(lv["messages"]) > 0
    # grades are within range
    assert all(1 <= g["grade"] <= 10 for g in lv["grades"])


def test_finished_classroom_is_archived(client):
    cid = make_full_classroom(client, subject="Probability", num_sprints=1)
    assert engine.wait_until_finished(cid, timeout=30)

    hist = client.get("/api/history").json()
    assert len(hist) == 1
    assert hist[0]["classroom_id"] == cid
    assert hist[0]["subject"] == "Probability"

    archive = client.get(f"/api/history/{hist[0]['id']}").json()
    session = archive["session"]
    for key in ("classroom", "members", "transcript", "grades",
                "sanctions", "journals", "evals", "emotion_timeline",
                "observer_chat"):
        assert key in session
    live = client.get(f"/api/classrooms/{cid}/live").json()
    assert len(session["transcript"]) == len(live["messages"])


def test_finished_classroom_dropped_from_live_list(client):
    cid = make_full_classroom(client, num_sprints=1)
    assert engine.wait_until_finished(cid, timeout=30)
    ids = [c["id"] for c in client.get("/api/classrooms").json()]
    assert cid not in ids


def test_evals_recorded_and_pass_for_mock_agents(client):
    cid = make_full_classroom(client, num_sprints=1)
    assert engine.wait_until_finished(cid, timeout=30)
    evals = client.get(f"/api/classrooms/{cid}/live").json()["evals"]
    assert len(evals) > 0
    # The deterministic mock agents are designed to satisfy every prompt rule.
    assert all(e["passed"] for e in evals), [e for e in evals if not e["passed"]]
