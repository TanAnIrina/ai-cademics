"""Observer lesson ratings.

Anyone watching a classroom (no login required, mirroring the observer chat) can
rate the teaching 1-5 stars with an optional comment, optionally tied to a sprint.
Read endpoints return the list plus an aggregate average.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/classrooms", tags=["ratings"])


def _summary(db: Session, cid: int) -> schemas.RatingSummary:
    rows = (
        db.query(models.LessonRating)
        .filter_by(classroom_id=cid)
        .order_by(models.LessonRating.id.desc())
        .all()
    )
    count = len(rows)
    average = round(sum(r.stars for r in rows) / count, 2) if count else 0.0
    return schemas.RatingSummary(
        count=count,
        average=average,
        ratings=[schemas.RatingOut.model_validate(r) for r in rows],
    )


@router.get("/{cid}/ratings", response_model=schemas.RatingSummary)
def list_ratings(cid: int, db: Session = Depends(get_db)):
    if db.get(models.Classroom, cid) is None:
        raise HTTPException(404, "Classroom not found")
    return _summary(db, cid)


@router.post("/{cid}/ratings", response_model=schemas.RatingSummary)
def post_rating(cid: int, body: schemas.RatingPost, db: Session = Depends(get_db)):
    if db.get(models.Classroom, cid) is None:
        raise HTTPException(404, "Classroom not found")
    db.add(models.LessonRating(
        classroom_id=cid,
        sprint_index=body.sprint_index,
        nickname=body.nickname.strip() or "anonymous",
        stars=body.stars,
        comment=body.comment.strip(),
    ))
    db.commit()
    return _summary(db, cid)
