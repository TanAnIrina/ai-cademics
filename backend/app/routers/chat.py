"""Observer chatroom.

Each classroom has an independent chatroom where viewers (observers) talk to
each other while watching. Posting only requires a nickname — observers are not
authenticated — but the content is scoped strictly to one classroom.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/classrooms", tags=["chat"])


@router.get("/{cid}/chat", response_model=list[schemas.ChatOut])
def get_chat(
    cid: int,
    after_id: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if db.get(models.Classroom, cid) is None:
        raise HTTPException(404, "Classroom not found")
    rows = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.classroom_id == cid)
        .filter(models.ChatMessage.id > after_id)
        .order_by(models.ChatMessage.id)
        .limit(limit)
        .all()
    )
    return [schemas.ChatOut.model_validate(r) for r in rows]


@router.post("/{cid}/chat", response_model=schemas.ChatOut)
def post_chat(cid: int, msg: schemas.ChatPost, db: Session = Depends(get_db)):
    if db.get(models.Classroom, cid) is None:
        raise HTTPException(404, "Classroom not found")
    row = models.ChatMessage(
        classroom_id=cid, nickname=msg.nickname.strip(), content=msg.content.strip()
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return schemas.ChatOut.model_validate(row)
