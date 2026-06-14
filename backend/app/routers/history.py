"""Session history.

Finished classrooms are snapshotted into immutable archives. This router is the
'history' tab: a list of past sessions and a full-detail fetch containing the
transcript, grades, sanctions, journals, eval results and observer chat.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..pdf_report import build_pdf

router = APIRouter(prefix="/api/history", tags=["history"])


def _live_ratings(db: Session, classroom_id: int) -> list[dict]:
    """Current ratings for a classroom, in the archive payload shape.

    Observers often rate after a session ends, so the snapshot taken at finish
    time can be stale; we overlay the live rows (while the classroom still exists).
    """
    rows = (
        db.query(models.LessonRating)
        .filter_by(classroom_id=classroom_id)
        .order_by(models.LessonRating.id)
        .all()
    )
    return [
        {"sprint": r.sprint_index, "nickname": r.nickname, "stars": r.stars,
         "comment": r.comment, "at": r.created_at.isoformat()} for r in rows
    ]


@router.get("", response_model=list[schemas.ArchiveSummary])
def list_history(db: Session = Depends(get_db)):
    rows = (
        db.query(models.Archive)
        .order_by(models.Archive.finished_at.desc())
        .all()
    )
    return [schemas.ArchiveSummary.model_validate(r) for r in rows]


@router.get("/{archive_id}")
def get_history(archive_id: int, db: Session = Depends(get_db)):
    row = db.get(models.Archive, archive_id)
    if row is None:
        raise HTTPException(404, "Archive not found")
    session = json.loads(row.payload)
    live = _live_ratings(db, row.classroom_id)
    if live:
        session["ratings"] = live
    return {
        "id": row.id,
        "classroom_id": row.classroom_id,
        "name": row.name,
        "subject": row.subject,
        "num_sprints": row.num_sprints,
        "finished_at": row.finished_at.isoformat(),
        "session": session,
    }


@router.get("/{archive_id}/pdf")
def export_pdf(archive_id: int, db: Session = Depends(get_db)):
    """Download a PDF export of the session (transcript summary, grades, stats, journals)."""
    row = db.get(models.Archive, archive_id)
    if row is None:
        raise HTTPException(404, "Archive not found")
    session = json.loads(row.payload)
    live = _live_ratings(db, row.classroom_id)
    if live:
        session["ratings"] = live
    archive = {
        "id": row.id,
        "name": row.name,
        "subject": row.subject,
        "num_sprints": row.num_sprints,
        "finished_at": row.finished_at.isoformat(),
        "session": session,
    }
    pdf_bytes = build_pdf(archive)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (row.name or "session"))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="aicademics-{safe}.pdf"'},
    )
