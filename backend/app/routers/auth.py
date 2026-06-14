"""Authentication endpoints.

A user logs in by declaring a role (teacher/student), an LLM provider and,
optionally, the API key that will power their agent. We persist the user
profile and issue an opaque bearer token; the API key lives only in memory.
Observers never log in — read-only endpoints accept anonymous requests.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import current_user
from ..security import SessionData, session_store

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.LoginResponse)
def login(req: schemas.LoginRequest, db: Session = Depends(get_db)):
    agent_name = (req.agent_name or req.display_name).strip()
    user = models.User(
        display_name=req.display_name,
        role=req.role,
        provider=req.provider,
        model=req.model,
        agent_name=agent_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = session_store.create(SessionData(
        user_id=user.id,
        role=user.role,
        provider=user.provider,
        model=user.model,
        agent_name=user.agent_name,
        api_key=req.api_key,
    ))
    return schemas.LoginResponse(token=token, user=schemas.UserOut.model_validate(user))


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(current_user)):
    return schemas.UserOut.model_validate(user)


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    token = None
    if authorization:
        parts = authorization.split()
        token = parts[1] if len(parts) == 2 else authorization
    session_store.revoke(token)
    return {"status": "logged_out"}
