"""Reusable FastAPI dependencies."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import SessionData, session_store


def _extract_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    # Allow the raw token too, for convenience.
    return authorization.strip() or None


def optional_session(
    authorization: str | None = Header(default=None),
) -> SessionData | None:
    """Returns the session if a valid token is present, else ``None``.

    Used by read-only endpoints so anonymous observers are allowed through.
    """
    token = _extract_token(authorization)
    return session_store.get(token)


def require_session(
    authorization: str | None = Header(default=None),
) -> SessionData:
    token = _extract_token(authorization)
    data = session_store.get(token)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Log in to perform this action.",
        )
    return data


def current_user(
    session: SessionData = Depends(require_session),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user
