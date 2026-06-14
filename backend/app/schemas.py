"""Pydantic schemas for the public API."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Role = Literal["teacher", "student"]
Provider = Literal["mock", "anthropic", "openai", "ollama", "external"]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    role: Role
    provider: Provider = "mock"
    model: str | None = None
    agent_name: str | None = Field(default=None, max_length=80)
    # The API key powers *this user's* agent. It is held in server memory for
    # the lifetime of the session and never written to disk.
    api_key: str | None = None

    @field_validator("display_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("display_name cannot be blank")
        return v


class UserOut(BaseModel):
    id: int
    display_name: str
    role: str
    provider: str
    model: str | None = None
    agent_name: str

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    token: str
    user: UserOut


# ---------------------------------------------------------------------------
# Classrooms
# ---------------------------------------------------------------------------
class TeacherConfig(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    sprint_minutes: int = Field(default=20, ge=1, le=180)
    break_minutes: int = Field(default=10, ge=0, le=120)
    num_sprints: int = Field(default=2, ge=1, le=12)
    num_students: int = Field(default=2, ge=2, le=5)
    # Optional: schedule the session to start no earlier than this time.
    scheduled_start: datetime | None = None


class CreateClassroomRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class JoinRequest(BaseModel):
    # Teacher must supply config when joining; students supply nothing.
    config: TeacherConfig | None = None


class MemberOut(BaseModel):
    slot: str
    agent_name: str
    display_name: str
    role: str
    frustration: int
    happiness: int
    confidence: int
    curiosity: int
    boredom: int
    anxiety: int


class ClassroomOut(BaseModel):
    id: int
    name: str
    status: str
    subject: str | None
    sprint_minutes: int
    break_minutes: int
    num_sprints: int
    max_students: int
    scheduled_start: datetime | None
    current_sprint: int
    phase: str
    members: list[MemberOut]
    free_slots: list[str]
    progress: float  # 0..1


class EstimateRequest(BaseModel):
    sprint_minutes: int = Field(ge=1, le=180)
    break_minutes: int = Field(ge=0, le=120)
    max_sprints: int = Field(default=8, ge=1, le=24)


class EstimatePoint(BaseModel):
    num_sprints: int
    total_minutes: int


class EstimateResponse(BaseModel):
    sprint_minutes: int
    break_minutes: int
    points: list[EstimatePoint]


# ---------------------------------------------------------------------------
# Live view
# ---------------------------------------------------------------------------
class MessageOut(BaseModel):
    id: int
    sprint_index: int
    phase: str
    sender: str
    sender_role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class GradeOut(BaseModel):
    sprint_index: int
    student_name: str
    question: str
    answer: str
    grade: int
    reasoning: str

    class Config:
        from_attributes = True


class JournalOut(BaseModel):
    sprint_index: int
    student_name: str
    author_role: str
    content: str
    word_count: int

    class Config:
        from_attributes = True


class EvalOut(BaseModel):
    sprint_index: int
    scope: str
    check_name: str
    passed: bool
    score: float
    detail: str

    class Config:
        from_attributes = True


class LiveView(BaseModel):
    classroom: ClassroomOut
    messages: list[MessageOut]
    grades: list[GradeOut]
    journals: list[JournalOut]
    evals: list[EvalOut]


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
class EmotionPoint(BaseModel):
    sprint_index: int
    slot: str
    agent_name: str
    happiness: int
    frustration: int
    confidence: int
    curiosity: int
    boredom: int
    anxiety: int

    class Config:
        from_attributes = True


class GradePoint(BaseModel):
    sprint_index: int
    student_name: str
    grade: int


class SanctionTally(BaseModel):
    student_name: str
    sanctions: int
    rewards: int
    net_points: int


class StatsResponse(BaseModel):
    classroom: ClassroomOut
    emotion_names: list[str]
    emotions: list[EmotionPoint]
    grades: list[GradePoint]
    sanctions: list[SanctionTally]


# ---------------------------------------------------------------------------
# Observer chat
# ---------------------------------------------------------------------------
class ChatPost(BaseModel):
    nickname: str = Field(min_length=1, max_length=60)
    content: str = Field(min_length=1, max_length=2000)


class ChatOut(BaseModel):
    id: int
    nickname: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Lesson ratings (observers)
# ---------------------------------------------------------------------------
class RatingPost(BaseModel):
    nickname: str = Field(min_length=1, max_length=60)
    stars: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)
    sprint_index: int | None = None


class RatingOut(BaseModel):
    id: int
    sprint_index: int | None
    nickname: str
    stars: int
    comment: str
    created_at: datetime

    class Config:
        from_attributes = True


class RatingSummary(BaseModel):
    count: int
    average: float
    ratings: list[RatingOut]


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
class ArchiveSummary(BaseModel):
    id: int
    classroom_id: int
    name: str
    subject: str | None
    num_sprints: int
    finished_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# External agent runtime
# ---------------------------------------------------------------------------
class AgentTask(BaseModel):
    task_id: str
    system_prompt: str
    prompt: str
    mode: str


class AgentSubmit(BaseModel):
    task_id: str
    content: str
