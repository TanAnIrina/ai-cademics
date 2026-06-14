"""Endpoints for the optional self-hosted ('external') agent runtime.

A user who logged in with ``provider=external`` runs their own agent process
(see ``backend/agent_client.py``). That process authenticates with its session
token, polls this endpoint for work, runs a local model, and submits the result.
This mirrors the poll/submit protocol of the original AI-cademics project.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_session
from ..engine.queue import external_queue
from ..models import STATUS_RUNNING, STATUS_WAITING, Classroom, Membership
from ..schemas import AgentSubmit, AgentTask
from ..security import SessionData

router = APIRouter(prefix="/api/agent", tags=["agent"])


def _active_membership(db: Session, user_id: int) -> Membership | None:
    return (
        db.query(Membership)
        .join(Classroom, Classroom.id == Membership.classroom_id)
        .filter(
            Membership.user_id == user_id,
            Classroom.status.in_([STATUS_WAITING, STATUS_RUNNING]),
        )
        .first()
    )


@router.get("/poll", response_model=AgentTask | None)
def poll(
    session: SessionData = Depends(require_session),
    db: Session = Depends(get_db),
):
    """Return the next pending task for this agent, or ``null`` if none."""
    membership = _active_membership(db, session.user_id)
    if membership is None:
        return None
    task = external_queue.poll(membership.classroom_id, membership.agent_name)
    return task


@router.post("/submit")
def submit(
    payload: AgentSubmit,
    session: SessionData = Depends(require_session),
    db: Session = Depends(get_db),
):
    """Submit the agent's answer for a previously polled task."""
    membership = _active_membership(db, session.user_id)
    if membership is None:
        raise HTTPException(status_code=409, detail="Not currently in an active classroom")
    external_queue.submit(payload.task_id, payload.content)
    return {"ok": True}
