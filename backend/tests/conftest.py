"""Shared pytest fixtures.

Configures a throwaway SQLite database and an effectively-instant simulation
clock *before* the application package is imported, then resets all tables and
in-memory session/queue state between tests for full isolation.
"""
from __future__ import annotations

import os
import tempfile

# Must be set before importing anything under ``app`` so the cached settings and
# the module-level SQLAlchemy engine pick them up.
_TMP_DB = os.path.join(tempfile.gettempdir(), "aicademics_test.db")
os.environ["AICADEMICS_DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ["AICADEMICS_SIM_PHASE_SECONDS"] = "0"
os.environ["AICADEMICS_BREAK_TURNS"] = "2"
os.environ["AICADEMICS_SEED_CLASSROOMS"] = "0"
os.environ["AICADEMICS_SCHEDULER"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import engine  # noqa: E402
from app.database import Base, SessionLocal, init_db  # noqa: E402
from app.database import engine as db_engine  # noqa: E402
from app.engine.queue import external_queue  # noqa: E402
from app.main import app  # noqa: E402
from app.security import session_store  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_state():
    """Fresh schema and clean in-memory state around every test."""
    Base.metadata.drop_all(bind=db_engine)
    Base.metadata.create_all(bind=db_engine)
    session_store.clear()
    with engine._running_lock:  # type: ignore[attr-defined]
        engine._running.clear()  # type: ignore[attr-defined]
    external_queue._tasks.clear()  # type: ignore[attr-defined]
    external_queue._responses.clear()  # type: ignore[attr-defined]
    yield


@pytest.fixture()
def client():
    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def login(client, display_name: str, role: str, provider: str = "mock") -> str:
    """Helper: log a user in and return their bearer token."""
    r = client.post(
        "/api/auth/login",
        json={"display_name": display_name, "role": role, "provider": provider},
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_full_classroom(client, subject: str = "Graph Theory", num_sprints: int = 2) -> int:
    """Create a classroom and fill all three slots; returns the classroom id."""
    t = login(client, "Prof", "teacher")
    s1 = login(client, "Ada", "student")
    s2 = login(client, "Linus", "student")

    cid = client.post("/api/classrooms", headers=auth(t), json={"name": "Test Room"}).json()["id"]
    client.post(
        f"/api/classrooms/{cid}/join",
        headers=auth(t),
        json={"config": {"subject": subject, "sprint_minutes": 20,
                         "break_minutes": 10, "num_sprints": num_sprints}},
    )
    client.post(f"/api/classrooms/{cid}/join", headers=auth(s1), json={})
    client.post(f"/api/classrooms/{cid}/join", headers=auth(s2), json={})
    return cid
