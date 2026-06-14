"""Classroom endpoints.

Read endpoints (list, detail, live view, estimate) are open to anonymous
observers. Mutating endpoints (create, join, leave, configure) require a
session and enforce roles: a classroom has exactly one teacher slot and two
student slots, and the session auto-starts when all three are filled.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import current_user
from ..engine import maybe_start, request_stop, wait_until_finished

router = APIRouter(prefix="/api/classrooms", tags=["classrooms"])

_PHASE_ORDER = [
    models.PHASE_LESSON, models.PHASE_TEST, models.PHASE_GRADING,
    models.PHASE_BREAK, models.PHASE_JOURNAL,
]


def _progress(c: models.Classroom) -> float:
    if c.status == models.STATUS_FINISHED:
        return 1.0
    if c.status == models.STATUS_WAITING:
        return 0.0
    if c.num_sprints <= 0:
        return 0.0
    try:
        phase_idx = _PHASE_ORDER.index(c.phase) + 1
    except ValueError:
        phase_idx = 0
    done = (c.current_sprint - 1) + phase_idx / len(_PHASE_ORDER)
    return max(0.0, min(1.0, done / c.num_sprints))


def classroom_out(c: models.Classroom) -> schemas.ClassroomOut:
    members = []
    occupied = set()
    for m in c.memberships:
        occupied.add(m.slot)
        members.append(schemas.MemberOut(
            slot=m.slot, agent_name=m.agent_name,
            display_name=m.user.display_name if m.user else m.agent_name,
            role=m.user.role if m.user else "student",
            frustration=m.frustration, happiness=m.happiness,
            confidence=m.confidence, curiosity=m.curiosity,
            boredom=m.boredom, anxiety=m.anxiety,
        ))
    active_slots = [models.SLOT_TEACHER, *models.student_slots(c.max_students)]
    free = [s for s in active_slots if s not in occupied]
    return schemas.ClassroomOut(
        id=c.id, name=c.name, status=c.status, subject=c.subject,
        sprint_minutes=c.sprint_minutes, break_minutes=c.break_minutes,
        num_sprints=c.num_sprints, max_students=c.max_students,
        scheduled_start=c.scheduled_start, current_sprint=c.current_sprint,
        phase=c.phase, members=members, free_slots=free, progress=round(_progress(c), 3),
    )


def _get_classroom(db: Session, cid: int) -> models.Classroom:
    c = db.get(models.Classroom, cid)
    if c is None:
        raise HTTPException(404, "Classroom not found")
    return c


def _active_membership(db: Session, user_id: int) -> models.Membership | None:
    return (
        db.query(models.Membership)
        .join(models.Classroom)
        .filter(models.Membership.user_id == user_id)
        .filter(models.Classroom.status.in_([models.STATUS_WAITING, models.STATUS_RUNNING]))
        .first()
    )


# --- Time estimate (powers the teacher's "time vs sessions" chart) ----------
@router.get("/estimate", response_model=schemas.EstimateResponse)
def estimate(
    sprint_minutes: int = Query(20, ge=1, le=180),
    break_minutes: int = Query(10, ge=0, le=120),
    max_sprints: int = Query(8, ge=1, le=24),
):
    """Total wall-clock minutes for 1..max_sprints sprints.

    Each sprint is ``sprint_minutes`` of class; every sprint except the last is
    followed by a ``break_minutes`` break.
    """
    points = []
    for n in range(1, max_sprints + 1):
        total = n * sprint_minutes + (n - 1) * break_minutes
        points.append(schemas.EstimatePoint(num_sprints=n, total_minutes=total))
    return schemas.EstimateResponse(
        sprint_minutes=sprint_minutes, break_minutes=break_minutes, points=points
    )


@router.get("", response_model=list[schemas.ClassroomOut])
def list_classrooms(db: Session = Depends(get_db)):
    rows = (
        db.query(models.Classroom)
        .filter(models.Classroom.status != models.STATUS_FINISHED)
        .order_by(models.Classroom.id)
        .all()
    )
    return [classroom_out(c) for c in rows]


@router.post("", response_model=schemas.ClassroomOut)
def create_classroom(
    req: schemas.CreateClassroomRequest,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role != models.ROLE_TEACHER:
        raise HTTPException(403, "Only teachers can create classrooms")
    c = models.Classroom(name=req.name, status=models.STATUS_WAITING)
    db.add(c)
    db.commit()
    db.refresh(c)
    return classroom_out(c)


@router.get("/{cid}", response_model=schemas.ClassroomOut)
def get_classroom(cid: int, db: Session = Depends(get_db)):
    return classroom_out(_get_classroom(db, cid))


@router.post("/{cid}/join", response_model=schemas.ClassroomOut)
def join_classroom(
    cid: int,
    req: schemas.JoinRequest,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    c = _get_classroom(db, cid)
    if c.status != models.STATUS_WAITING:
        raise HTTPException(409, "Classroom is not accepting new members")
    if _active_membership(db, user.id):
        raise HTTPException(409, "You are already in an active classroom")

    occupied = {m.slot for m in c.memberships}

    if user.role == models.ROLE_TEACHER:
        if models.SLOT_TEACHER in occupied:
            raise HTTPException(409, "The teacher slot is already taken")
        if req.config is None:
            raise HTTPException(422, "Teacher must provide a classroom configuration")
        c.subject = req.config.subject
        c.sprint_minutes = req.config.sprint_minutes
        c.break_minutes = req.config.break_minutes
        c.num_sprints = req.config.num_sprints
        c.max_students = req.config.num_students
        c.scheduled_start = req.config.scheduled_start
        slot = models.SLOT_TEACHER
    else:
        active = models.student_slots(c.max_students)
        free_student = next((s for s in active if s not in occupied), None)
        if free_student is None:
            raise HTTPException(409, "All student seats are taken")
        slot = free_student

    db.add(models.Membership(
        classroom_id=c.id, user_id=user.id, slot=slot,
        agent_name=user.agent_name, frustration=0, happiness=5,
    ))
    db.commit()
    db.refresh(c)

    if len(c.memberships) == 1 + c.max_students:
        maybe_start(c.id)
        db.refresh(c)
    return classroom_out(c)


@router.post("/{cid}/configure", response_model=schemas.ClassroomOut)
def configure_classroom(
    cid: int,
    config: schemas.TeacherConfig,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    c = _get_classroom(db, cid)
    if c.status != models.STATUS_WAITING:
        raise HTTPException(409, "Cannot reconfigure a started classroom")
    teacher_m = next((m for m in c.memberships if m.slot == models.SLOT_TEACHER), None)
    if teacher_m is None or teacher_m.user_id != user.id:
        raise HTTPException(403, "Only the classroom's teacher can configure it")
    c.subject = config.subject
    c.sprint_minutes = config.sprint_minutes
    c.break_minutes = config.break_minutes
    c.num_sprints = config.num_sprints
    # Don't shrink capacity below the students who have already taken a seat.
    seated_students = sum(1 for m in c.memberships if m.slot != models.SLOT_TEACHER)
    c.max_students = max(config.num_students, seated_students)
    c.scheduled_start = config.scheduled_start
    db.commit()
    db.refresh(c)
    # Applying a schedule/capacity change may make a full room eligible to start.
    if len(c.memberships) == 1 + c.max_students:
        maybe_start(c.id)
        db.refresh(c)
    return classroom_out(c)


@router.post("/{cid}/leave", response_model=schemas.ClassroomOut)
def leave_classroom(
    cid: int,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    c = _get_classroom(db, cid)
    if c.status != models.STATUS_WAITING:
        raise HTTPException(409, "Cannot leave a classroom once the session has started")
    m = next((m for m in c.memberships if m.user_id == user.id), None)
    if m is None:
        raise HTTPException(404, "You are not a member of this classroom")
    # If the teacher leaves, clear the configuration they set.
    if m.slot == models.SLOT_TEACHER:
        c.subject = None
    db.delete(m)
    db.commit()
    db.refresh(c)
    return classroom_out(c)


@router.get("/{cid}/live", response_model=schemas.LiveView)
def live_view(cid: int, db: Session = Depends(get_db)):
    c = _get_classroom(db, cid)
    messages = (
        db.query(models.Message).filter_by(classroom_id=cid)
        .order_by(models.Message.id).all()
    )
    grades = (
        db.query(models.Grade).filter_by(classroom_id=cid)
        .order_by(models.Grade.id).all()
    )
    journals = (
        db.query(models.Journal).filter_by(classroom_id=cid)
        .order_by(models.Journal.id).all()
    )
    evals = (
        db.query(models.EvalResult).filter_by(classroom_id=cid)
        .order_by(models.EvalResult.id).all()
    )
    return schemas.LiveView(
        classroom=classroom_out(c),
        messages=[schemas.MessageOut.model_validate(m) for m in messages],
        grades=[schemas.GradeOut.model_validate(g) for g in grades],
        journals=[schemas.JournalOut.model_validate(j) for j in journals],
        evals=[schemas.EvalOut.model_validate(e) for e in evals],
    )


def _delete_classroom_rows(db: Session, cid: int) -> None:
    """Remove a classroom and every row that references it (delete is permanent)."""
    for model in (
        models.Message, models.Grade, models.Sanction, models.Journal,
        models.EvalResult, models.EmotionSnapshot, models.ChatMessage,
        models.LessonRating, models.Archive, models.Membership,
    ):
        db.query(model).filter_by(classroom_id=cid).delete(synchronize_session=False)
    db.query(models.Classroom).filter_by(id=cid).delete(synchronize_session=False)
    db.commit()


@router.delete("/{cid}", status_code=204)
def delete_classroom(
    cid: int,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Stop an active session (if running) and permanently delete the classroom.

    Teacher-only: a teacher may delete a classroom they own (their teacher seat),
    or any teacher-less room (e.g. an empty seeded room).
    """
    if user.role != models.ROLE_TEACHER:
        raise HTTPException(403, "Only teachers can stop and delete classrooms")
    c = _get_classroom(db, cid)
    teacher_m = next((m for m in c.memberships if m.slot == models.SLOT_TEACHER), None)
    if teacher_m is not None and teacher_m.user_id != user.id:
        raise HTTPException(403, "Only this classroom's teacher can delete it")

    # Stop a running session and give the engine thread a moment to wind down
    # before we remove the rows it might still be writing to.
    if c.status == models.STATUS_RUNNING:
        request_stop(cid)
        wait_until_finished(cid, timeout=5.0)

    _delete_classroom_rows(db, cid)
    return Response(status_code=204)


@router.get("/{cid}/stats", response_model=schemas.StatsResponse)
def classroom_stats(cid: int, db: Session = Depends(get_db)):
    """Emotion evolution, grade trajectory and sanction tallies for the stats view."""
    c = _get_classroom(db, cid)
    snaps = (
        db.query(models.EmotionSnapshot).filter_by(classroom_id=cid)
        .order_by(models.EmotionSnapshot.sprint_index, models.EmotionSnapshot.id).all()
    )
    grades = (
        db.query(models.Grade).filter_by(classroom_id=cid)
        .order_by(models.Grade.sprint_index, models.Grade.id).all()
    )
    sanctions = db.query(models.Sanction).filter_by(classroom_id=cid).all()

    tally: dict[str, dict] = {}
    for s in sanctions:
        t = tally.setdefault(s.student_name, {"sanctions": 0, "rewards": 0, "net": 0})
        if s.type == "sanction":
            t["sanctions"] += 1
        else:
            t["rewards"] += 1
        t["net"] += s.points

    return schemas.StatsResponse(
        classroom=classroom_out(c),
        emotion_names=list(models.EMOTIONS),
        emotions=[schemas.EmotionPoint.model_validate(s) for s in snaps],
        grades=[
            schemas.GradePoint(sprint_index=g.sprint_index,
                               student_name=g.student_name, grade=g.grade)
            for g in grades
        ],
        sanctions=[
            schemas.SanctionTally(student_name=name, sanctions=v["sanctions"],
                                  rewards=v["rewards"], net_points=v["net"])
            for name, v in tally.items()
        ],
    )
