"""Session management and the in-memory credential store.

Design note on security
------------------------
A logged-in user's *agent* is powered by an LLM provider. The user supplies an
API key at login. We deliberately keep that key **only in process memory**
(keyed by an opaque session token) and never write it to the database or disk.
When the server restarts, sessions expire and users log in again. In a
production deployment you would replace this with a real secrets manager and a
proper OAuth/JWT flow; the interface here (`get_session`, `require_session`)
isolates that concern so it can be swapped without touching the rest of the app.
"""
from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass


@dataclass
class SessionData:
    user_id: int
    role: str
    provider: str
    model: str | None
    agent_name: str
    api_key: str | None  # never persisted


class SessionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, SessionData] = {}

    def create(self, data: SessionData) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[token] = data
        return token

    def get(self, token: str | None) -> SessionData | None:
        if not token:
            return None
        with self._lock:
            return self._sessions.get(token)

    def get_by_user(self, user_id: int) -> SessionData | None:
        with self._lock:
            for data in self._sessions.values():
                if data.user_id == user_id:
                    return data
        return None

    def revoke(self, token: str | None) -> None:
        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()


# Module-level singleton used across the app.
session_store = SessionStore()
