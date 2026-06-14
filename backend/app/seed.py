"""Seed helpers: create a few empty demo classrooms on first startup.

Idempotent — does nothing if any classroom already exists, so restarting the
server never duplicates rooms.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from .config import get_settings
from .models import STATUS_WAITING, Classroom

_DEMO_NAMES = [
    "Room Alpha",
    "Room Beta",
    "Room Gamma",
    "Room Delta",
    "Room Epsilon",
]


def seed_classrooms(db: Session) -> int:
    """Ensure a starter set of empty waiting classrooms exists.

    Returns the number of classrooms created.
    """
    settings = get_settings()
    existing = db.query(Classroom).count()
    if existing > 0:
        return 0

    count = max(0, min(settings.seed_classrooms, len(_DEMO_NAMES)))
    created = 0
    for name in _DEMO_NAMES[:count]:
        db.add(
            Classroom(
                name=name,
                status=STATUS_WAITING,
                sprint_minutes=settings.default_sprint_minutes,
                break_minutes=settings.default_break_minutes,
                num_sprints=settings.default_num_sprints,
            )
        )
        created += 1
    db.commit()
    return created
