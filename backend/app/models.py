"""ORM models.

The schema captures everything needed for the live view *and* the permanent
history archive: users + roles, classrooms with their slot memberships, the
agent transcript, grades, sanctions, journals, automated eval results and the
per-classroom observer chatroom.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


# Role constants ---------------------------------------------------------------
ROLE_TEACHER = "teacher"
ROLE_STUDENT = "student"

# Slot constants ---------------------------------------------------------------
SLOT_TEACHER = "teacher"
SLOT_STUDENT_A = "student_a"
SLOT_STUDENT_B = "student_b"
# Up to five students are supported; a classroom's ``max_students`` decides how
# many of these slots are active. The first two keep their historical names so
# existing data and 2-student sessions are unaffected.
STUDENT_SLOTS = ("student_a", "student_b", "student_c", "student_d", "student_e")
MAX_STUDENTS = len(STUDENT_SLOTS)


def student_slots(n: int) -> tuple[str, ...]:
    """The active student slots for a classroom that seats ``n`` students."""
    return STUDENT_SLOTS[: max(1, min(MAX_STUDENTS, n))]

# Classroom status -------------------------------------------------------------
STATUS_WAITING = "waiting"
STATUS_RUNNING = "running"
STATUS_FINISHED = "finished"

# Phases -----------------------------------------------------------------------
PHASE_IDLE = "idle"
PHASE_LESSON = "lesson"
PHASE_TEST = "test"
PHASE_GRADING = "grading"
PHASE_BREAK = "break"
PHASE_JOURNAL = "journal"
PHASE_DONE = "done"
PHASE_STOPPED = "stopped"
# Between sprints the teacher may pick the next subject; the session pauses here.
PHASE_CHOOSING = "choosing"

# Emotions tracked per agent (each 0..10) -------------------------------------
# Positive: happiness, confidence, curiosity. Negative: frustration, boredom,
# anxiety. The engine evolves these from grades, sanctions, peer support and the
# passage of sprints, and snapshots them each sprint for the statistics view.
EMOTIONS = ("happiness", "frustration", "confidence", "curiosity", "boredom", "anxiety")

# Journal authors --------------------------------------------------------------
JOURNAL_STUDENT = "student"
JOURNAL_TEACHER = "teacher"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # teacher | student
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="mock")
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    agent_name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    memberships: Mapped[list[Membership]] = relationship(back_populates="user")


class Classroom(Base):
    __tablename__ = "classrooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=STATUS_WAITING)
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sprint_minutes: Mapped[int] = mapped_column(Integer, default=20)
    break_minutes: Mapped[int] = mapped_column(Integer, default=10)
    num_sprints: Mapped[int] = mapped_column(Integer, default=2)
    max_students: Mapped[int] = mapped_column(Integer, default=2)
    # If set, the session will not auto-start before this time even when full.
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    current_sprint: Mapped[int] = mapped_column(Integer, default=0)
    phase: Mapped[str] = mapped_column(String(16), default=PHASE_IDLE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    memberships: Mapped[list[Membership]] = relationship(
        back_populates="classroom", cascade="all, delete-orphan"
    )
    messages: Mapped[list[Message]] = relationship(
        back_populates="classroom", cascade="all, delete-orphan"
    )


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("classroom_id", "slot", name="uq_classroom_slot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    slot: Mapped[str] = mapped_column(String(16), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(80), nullable=False)
    # Emotional state (each 0..10). See models.EMOTIONS.
    frustration: Mapped[int] = mapped_column(Integer, default=0)
    happiness: Mapped[int] = mapped_column(Integer, default=5)
    confidence: Mapped[int] = mapped_column(Integer, default=5)
    curiosity: Mapped[int] = mapped_column(Integer, default=5)
    boredom: Mapped[int] = mapped_column(Integer, default=0)
    anxiety: Mapped[int] = mapped_column(Integer, default=2)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    classroom: Mapped[Classroom] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class Message(Base):
    """A single line of the agent transcript (lesson, question, answer, break chat)."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"))
    sprint_index: Mapped[int] = mapped_column(Integer, default=0)
    phase: Mapped[str] = mapped_column(String(16))
    sender: Mapped[str] = mapped_column(String(80))
    sender_role: Mapped[str] = mapped_column(String(16))  # teacher | student | system
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    classroom: Mapped[Classroom] = relationship(back_populates="messages")


class Grade(Base):
    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"))
    sprint_index: Mapped[int] = mapped_column(Integer, default=0)
    student_name: Mapped[str] = mapped_column(String(80))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    grade: Mapped[int] = mapped_column(Integer)
    reasoning: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Sanction(Base):
    __tablename__ = "sanctions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"))
    sprint_index: Mapped[int] = mapped_column(Integer, default=0)
    student_name: Mapped[str] = mapped_column(String(80))
    type: Mapped[str] = mapped_column(String(16))  # sanction | reward
    points: Mapped[int] = mapped_column(Integer, default=0)
    explanation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Journal(Base):
    __tablename__ = "journals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"))
    sprint_index: Mapped[int] = mapped_column(Integer, default=0)
    student_name: Mapped[str] = mapped_column(String(80))
    # "student" | "teacher" — lets the UI split Student Journals / Teacher Journal.
    author_role: Mapped[str] = mapped_column(String(16), default=JOURNAL_STUDENT)
    content: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class EmotionSnapshot(Base):
    """An agent's emotional state captured at the end of one sprint.

    Powers the statistics view's emotion-evolution charts.
    """

    __tablename__ = "emotion_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"))
    sprint_index: Mapped[int] = mapped_column(Integer, default=0)
    slot: Mapped[str] = mapped_column(String(16))
    agent_name: Mapped[str] = mapped_column(String(80))
    happiness: Mapped[int] = mapped_column(Integer, default=0)
    frustration: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    curiosity: Mapped[int] = mapped_column(Integer, default=0)
    boredom: Mapped[int] = mapped_column(Integer, default=0)
    anxiety: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class EvalResult(Base):
    """Result of one automated agent-evaluation check."""

    __tablename__ = "eval_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"))
    sprint_index: Mapped[int] = mapped_column(Integer, default=0)
    scope: Mapped[str] = mapped_column(String(40))  # e.g. "teacher_questions", "Qwen_journal"
    check_name: Mapped[str] = mapped_column(String(60))
    passed: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ChatMessage(Base):
    """Observer-to-observer chat, scoped per classroom."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"))
    nickname: Mapped[str] = mapped_column(String(60))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class LessonRating(Base):
    """An observer's star rating (1-5) of the teaching, optionally per sprint."""

    __tablename__ = "lesson_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"))
    sprint_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nickname: Mapped[str] = mapped_column(String(60))
    stars: Mapped[int] = mapped_column(Integer)  # 1..5
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Archive(Base):
    """Immutable snapshot of a finished classroom session (full history)."""

    __tablename__ = "archives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"))
    name: Mapped[str] = mapped_column(String(120))
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    num_sprints: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[str] = mapped_column(Text)  # JSON blob of the whole session
    finished_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
