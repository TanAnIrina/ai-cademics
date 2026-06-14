"""Session history.

Finished classrooms are snapshotted into immutable archives. This router is the
'history' tab: a list of past sessions and a full-detail fetch containing the
transcript, grades, sanctions, journals, eval results and observer chat.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/history", tags=["history"])


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
    return {
        "id": row.id,
        "classroom_id": row.classroom_id,
        "name": row.name,
        "subject": row.subject,
        "num_sprints": row.num_sprints,
        "finished_at": row.finished_at.isoformat(),
        "session": json.loads(row.payload),
    }
