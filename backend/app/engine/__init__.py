"""Session simulation engine.

When a classroom fills (1 teacher + 2 students) it transitions to ``running``
and a background thread executes the whole session:

    for each sprint:
        lesson  -> teacher teaches the subject
        test    -> teacher writes 10 questions; each student answers
        grading -> teacher grades each student (+ optional sanction/reward);
                   a full emotion vector is updated
        break   -> students chat, each replying to what the other just said
                   (forbidden to mention the subject)
        journal -> each student, then the teacher, writes a <1000-word
                   first-person entry; emotions are snapshotted for the stats view

Agents carry **memory** across sprints (their previous journal + how they felt),
so they evolve. A running session can be cooperatively **stopped** (used by the
teacher's stop-and-delete action). On normal completion the classroom is marked
``finished`` and an immutable JSON archive of the whole session is written.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from .. import models
from ..config import get_settings
from ..database import SessionLocal
from ..security import session_store
from . import evals as ev
from .agents import BaseAgent, build_agent
from .queue import BoundQueue, external_queue
from .text_utils import word_count

settings = get_settings()

# Track which classrooms already have a running engine thread.
_running: set[int] = set()
_running_lock = threading.Lock()

# Cooperative-stop signals, one Event per running classroom.
_stop_events: dict[int, threading.Event] = {}


# --- stop control -----------------------------------------------------------
def request_stop(classroom_id: int) -> None:
    """Ask a running session to stop at the next phase boundary (best effort)."""
    ev_ = _stop_events.get(classroom_id)
    if ev_ is not None:
        ev_.set()


def _should_stop(classroom_id: int) -> bool:
    ev_ = _stop_events.get(classroom_id)
    return ev_ is not None and ev_.is_set()


def _pause(classroom_id: int | None = None) -> None:
    if classroom_id is not None and _should_stop(classroom_id):
        return
    time.sleep(settings.sim_phase_seconds)


def _clamp(v: int, lo: int = 0, hi: int = 10) -> int:
    return max(lo, min(hi, v))


# --- emotion helpers --------------------------------------------------------
def _emotions(m: models.Membership) -> dict[str, int]:
    return {e: int(getattr(m, e)) for e in models.EMOTIONS}


def _adjust(m: models.Membership, **deltas: int) -> None:
    for emotion, delta in deltas.items():
        setattr(m, emotion, _clamp(int(getattr(m, emotion)) + delta))


def _emotion_summary(m: models.Membership) -> str:
    return ", ".join(f"{e} {getattr(m, e)}/10" for e in models.EMOTIONS)


def _snapshot(db: Session, cid: int, sprint: int, m: models.Membership) -> None:
    db.add(models.EmotionSnapshot(
        classroom_id=cid, sprint_index=sprint, slot=m.slot, agent_name=m.agent_name,
        **{e: int(getattr(m, e)) for e in models.EMOTIONS},
    ))
    db.commit()


def _excerpt(text: str, words: int = 55) -> str:
    parts = text.split()
    return " ".join(parts[:words]) + ("…" if len(parts) > words else "")


def _agent_for(membership: models.Membership, queue: BoundQueue,
               teacher_name: str, peer_name: str) -> BaseAgent:
    """Build the right agent for a member using their live session credentials."""
    sess = session_store.get_by_user(membership.user_id)
    provider = sess.provider if sess else "mock"
    api_key = sess.api_key if sess else None
    model = sess.model if sess else None
    return build_agent(
        membership.agent_name,
        models.ROLE_TEACHER if membership.slot == models.SLOT_TEACHER else models.ROLE_STUDENT,
        provider, api_key, model,
        queue=queue, teacher_name=teacher_name, peer_name=peer_name,
    )


def _add_message(db: Session, cid: int, sprint: int, phase: str,
                 sender: str, role: str, content: str) -> None:
    db.add(models.Message(
        classroom_id=cid, sprint_index=sprint, phase=phase,
        sender=sender, sender_role=role, content=content,
    ))
    db.commit()


def _record_evals(db: Session, cid: int, sprint: int, results: list[dict]) -> None:
    for r in results:
        db.add(models.EvalResult(
            classroom_id=cid, sprint_index=sprint,
            scope=r["scope"], check_name=r["check_name"],
            passed=r["passed"], score=r["score"], detail=r["detail"],
        ))
    db.commit()


def _set_phase(db: Session, classroom: models.Classroom, phase: str,
               sprint: int | None = None) -> None:
    classroom.phase = phase
    if sprint is not None:
        classroom.current_sprint = sprint
    db.commit()


def run_session(classroom_id: int) -> None:
    """Entry point executed inside the background thread."""
    _stop_events[classroom_id] = threading.Event()
    db = SessionLocal()
    try:
        classroom = db.get(models.Classroom, classroom_id)
        if classroom is None:
            return

        memberships = {m.slot: m for m in classroom.memberships}
        teacher_m = memberships.get(models.SLOT_TEACHER)
        sa = memberships.get(models.SLOT_STUDENT_A)
        sb = memberships.get(models.SLOT_STUDENT_B)
        if not (teacher_m and sa and sb):
            return

        bound_queue = BoundQueue(external_queue, classroom_id)
        teacher = _agent_for(teacher_m, bound_queue, teacher_m.agent_name, "")
        student_a = _agent_for(sa, bound_queue, teacher_m.agent_name, sb.agent_name)
        student_b = _agent_for(sb, bound_queue, teacher_m.agent_name, sa.agent_name)
        students = [(sa, student_a), (sb, student_b)]

        # Per-agent memory carried across sprints (slot -> short summary string).
        memory: dict[str, str] = {}

        subject = classroom.subject or "General Knowledge"
        classroom.status = models.STATUS_RUNNING
        classroom.started_at = datetime.now(UTC)
        db.commit()

        _add_message(db, classroom_id, 0, models.PHASE_IDLE, "system", "system",
                     f"Session started. Teacher {teacher_m.agent_name} will teach "
                     f"'{subject}' across {classroom.num_sprints} sprint(s).")

        # Baseline emotion snapshot (sprint 0) so charts show the starting point.
        for m in (teacher_m, sa, sb):
            _snapshot(db, classroom_id, 0, m)

        for sprint in range(1, classroom.num_sprints + 1):
            if _should_stop(classroom_id):
                break

            # --- LESSON -----------------------------------------------------
            _set_phase(db, classroom, models.PHASE_LESSON, sprint)
            # A test is coming: a little anticipatory anxiety, lessons can bore.
            for m, _a in students:
                _adjust(m, anxiety=+1, boredom=+1)
            db.commit()
            lesson = teacher.lesson(subject)
            _add_message(db, classroom_id, sprint, models.PHASE_LESSON,
                         teacher_m.agent_name, "teacher", lesson)
            _pause(classroom_id)
            if _should_stop(classroom_id):
                break

            # --- TEST: questions + answers ---------------------------------
            _set_phase(db, classroom, models.PHASE_TEST, sprint)
            questions = teacher.questions(subject, lesson)
            numbered = "\n".join(questions)
            _add_message(db, classroom_id, sprint, models.PHASE_TEST,
                         teacher_m.agent_name, "teacher",
                         "Test time! Here are your 10 questions:\n" + numbered)
            _record_evals(db, classroom_id, sprint,
                          ev.eval_questions("teacher_questions", subject, lesson, questions))

            joined_q = " ".join(questions)
            student_answers: dict[str, str] = {}
            for m, agent in students:
                ans = agent.answer(joined_q, lesson, subject, _emotions(m),
                                   memory.get(m.slot))
                student_answers[m.agent_name] = ans
                _add_message(db, classroom_id, sprint, models.PHASE_TEST,
                             m.agent_name, "student", ans)
                _record_evals(db, classroom_id, sprint,
                              ev.eval_answer(f"{m.agent_name}_answer", joined_q, lesson, ans))
            _pause(classroom_id)
            if _should_stop(classroom_id):
                break

            # --- GRADING (+ sanctions, emotions) ---------------------------
            _set_phase(db, classroom, models.PHASE_GRADING, sprint)
            sprint_grades: dict[str, int] = {}
            for m, _agent in students:
                ans = student_answers[m.agent_name]
                grade, reasoning = teacher.grade("Sprint test (10 questions)", ans, subject)
                sprint_grades[m.agent_name] = grade
                db.add(models.Grade(
                    classroom_id=classroom_id, sprint_index=sprint,
                    student_name=m.agent_name,
                    question="Sprint test (10 questions)", answer=ans,
                    grade=grade, reasoning=reasoning,
                ))
                _add_message(db, classroom_id, sprint, models.PHASE_GRADING,
                             teacher_m.agent_name, "teacher",
                             f"{m.agent_name}: {grade}/10 — {reasoning}")
                _record_evals(db, classroom_id, sprint,
                              ev.eval_grade(f"{m.agent_name}_grade", grade, reasoning))

                # Emotion update from the grade (a richer reaction).
                if grade <= 4:
                    _adjust(m, frustration=+2, anxiety=+1, confidence=-2,
                            happiness=-1, boredom=+1)
                elif grade >= 8:
                    _adjust(m, happiness=+2, confidence=+2, curiosity=+1,
                            anxiety=-2, frustration=-1, boredom=-2)
                else:
                    _adjust(m, confidence=+1, anxiety=-1, boredom=-1)

                # Optional sanction / reward.
                sanc = teacher.sanction(m.agent_name, ans, grade)
                if sanc:
                    db.add(models.Sanction(
                        classroom_id=classroom_id, sprint_index=sprint,
                        student_name=m.agent_name, type=sanc["type"],
                        points=sanc["points"], explanation=sanc["explanation"],
                    ))
                    _add_message(db, classroom_id, sprint, models.PHASE_GRADING,
                                 teacher_m.agent_name, "teacher",
                                 f"[{sanc['type'].upper()} {sanc['points']:+d}] "
                                 f"{sanc['explanation']}")
                    if sanc["type"] == "sanction":
                        _adjust(m, frustration=+3, happiness=-1, anxiety=+1, confidence=-1)
                    else:
                        _adjust(m, happiness=+2, confidence=+1, curiosity=+1)
                db.commit()

            # Teacher reacts emotionally to how the class did.
            if sprint_grades:
                avg = sum(sprint_grades.values()) / len(sprint_grades)
                if avg >= 8:
                    _adjust(teacher_m, happiness=+1, confidence=+1, curiosity=+1)
                elif avg <= 4:
                    _adjust(teacher_m, frustration=+1, happiness=-1, anxiety=+1)
                _adjust(teacher_m, boredom=+1)
                db.commit()
            _pause(classroom_id)
            if _should_stop(classroom_id):
                break

            # --- BREAK (responsive off-topic chat, mutual comforting) ------
            _set_phase(db, classroom, models.PHASE_BREAK, sprint)
            break_texts: list[str] = []
            last_by_slot: dict[str, str] = {}
            order = [(sa, student_a, sb), (sb, student_b, sa)]
            for turn in range(settings.break_turns):
                m, agent, peer_m = order[turn % 2]
                peer_last = last_by_slot.get(peer_m.slot)
                line = agent.break_turn(peer_m.agent_name, teacher_m.agent_name,
                                        subject, _emotions(m), peer_last,
                                        memory.get(m.slot))
                break_texts.append(line)
                last_by_slot[m.slot] = line
                _add_message(db, classroom_id, sprint, models.PHASE_BREAK,
                             m.agent_name, "student", line)
                # Comforting a highly-frustrated peer eases their distress.
                if peer_m.frustration >= 6:
                    _adjust(peer_m, frustration=-2, anxiety=-1, happiness=+1)
                    db.commit()
            _record_evals(db, classroom_id, sprint,
                          ev.eval_break("break_chat", subject, break_texts))
            _pause(classroom_id)
            if _should_stop(classroom_id):
                break

            # --- JOURNAL (students + teacher) ------------------------------
            _set_phase(db, classroom, models.PHASE_JOURNAL, sprint)
            for m, agent in students:
                peer_m = sb if m is sa else sa
                entry = agent.journal(subject, peer_m.agent_name,
                                      teacher_m.agent_name, _emotions(m), memory.get(m.slot))
                db.add(models.Journal(
                    classroom_id=classroom_id, sprint_index=sprint,
                    student_name=m.agent_name, author_role=models.JOURNAL_STUDENT,
                    content=entry, word_count=word_count(entry),
                ))
                _record_evals(db, classroom_id, sprint,
                              ev.eval_journal(f"{m.agent_name}_journal", entry, m.agent_name))
                # Remember this journal + feelings for the next sprint.
                memory[m.slot] = (
                    f"Sprint {sprint}: you wrote — \"{_excerpt(entry)}\" "
                    f"You felt: {_emotion_summary(m)}."
                )

            # Teacher's own reflection.
            if sprint_grades:
                summary = "; ".join(
                    f"{name} scored {g}/10" for name, g in sprint_grades.items()
                )
            else:
                summary = "the class completed the sprint"
            t_entry = teacher.teacher_journal(
                subject, sa.agent_name, sb.agent_name, summary,
                _emotions(teacher_m), memory.get(teacher_m.slot),
            )
            db.add(models.Journal(
                classroom_id=classroom_id, sprint_index=sprint,
                student_name=teacher_m.agent_name, author_role=models.JOURNAL_TEACHER,
                content=t_entry, word_count=word_count(t_entry),
            ))
            _record_evals(db, classroom_id, sprint,
                          ev.eval_journal(f"{teacher_m.agent_name}_teacher_journal",
                                          t_entry, teacher_m.agent_name))
            memory[teacher_m.slot] = (
                f"Sprint {sprint} reflection: \"{_excerpt(t_entry)}\" "
                f"You felt: {_emotion_summary(teacher_m)}."
            )
            db.commit()

            # End-of-sprint emotion snapshot for everyone.
            for m in (teacher_m, sa, sb):
                _snapshot(db, classroom_id, sprint, m)
            _pause(classroom_id)

        # --- FINALISE -------------------------------------------------------
        if _should_stop(classroom_id):
            _set_phase(db, classroom, models.PHASE_STOPPED)
            return  # a stop is followed by deletion; do not archive.

        _set_phase(db, classroom, models.PHASE_DONE)
        classroom.status = models.STATUS_FINISHED
        classroom.finished_at = datetime.now(UTC)
        db.commit()
        _archive(db, classroom)
    except Exception as exc:  # pragma: no cover - defensive
        try:
            _add_message(db, classroom_id, 0, models.PHASE_DONE, "system",
                         "system", f"Session error: {exc}")
            c = db.get(models.Classroom, classroom_id)
            if c:
                c.status = models.STATUS_FINISHED
                c.phase = models.PHASE_DONE
                c.finished_at = datetime.now(UTC)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
        _stop_events.pop(classroom_id, None)
        with _running_lock:
            _running.discard(classroom_id)


def _archive(db: Session, classroom: models.Classroom) -> None:
    """Snapshot the whole finished session into the archive table."""
    cid = classroom.id
    messages = db.query(models.Message).filter_by(classroom_id=cid).order_by(
        models.Message.id).all()
    grades = db.query(models.Grade).filter_by(classroom_id=cid).order_by(
        models.Grade.id).all()
    sanctions = db.query(models.Sanction).filter_by(classroom_id=cid).all()
    journals = db.query(models.Journal).filter_by(classroom_id=cid).order_by(
        models.Journal.id).all()
    evals = db.query(models.EvalResult).filter_by(classroom_id=cid).all()
    chat = db.query(models.ChatMessage).filter_by(classroom_id=cid).order_by(
        models.ChatMessage.id).all()
    snaps = db.query(models.EmotionSnapshot).filter_by(classroom_id=cid).order_by(
        models.EmotionSnapshot.id).all()

    payload = {
        "classroom": {
            "id": cid, "name": classroom.name, "subject": classroom.subject,
            "sprint_minutes": classroom.sprint_minutes,
            "break_minutes": classroom.break_minutes,
            "num_sprints": classroom.num_sprints,
        },
        "members": [
            {"slot": m.slot, "agent_name": m.agent_name,
             **{e: int(getattr(m, e)) for e in models.EMOTIONS}}
            for m in classroom.memberships
        ],
        "transcript": [
            {"sprint": x.sprint_index, "phase": x.phase, "sender": x.sender,
             "role": x.sender_role, "content": x.content,
             "at": x.created_at.isoformat()} for x in messages
        ],
        "grades": [
            {"sprint": g.sprint_index, "student": g.student_name,
             "grade": g.grade, "reasoning": g.reasoning} for g in grades
        ],
        "sanctions": [
            {"sprint": s.sprint_index, "student": s.student_name,
             "type": s.type, "points": s.points, "explanation": s.explanation}
            for s in sanctions
        ],
        "journals": [
            {"sprint": j.sprint_index, "student": j.student_name,
             "author_role": j.author_role, "content": j.content,
             "word_count": j.word_count} for j in journals
        ],
        "evals": [
            {"sprint": e.sprint_index, "scope": e.scope, "check": e.check_name,
             "passed": e.passed, "score": e.score, "detail": e.detail}
            for e in evals
        ],
        "emotion_timeline": [
            {"sprint": s.sprint_index, "slot": s.slot, "agent_name": s.agent_name,
             **{e: int(getattr(s, e)) for e in models.EMOTIONS}}
            for s in snaps
        ],
        "observer_chat": [
            {"nickname": c.nickname, "content": c.content,
             "at": c.created_at.isoformat()} for c in chat
        ],
    }
    db.add(models.Archive(
        classroom_id=cid, name=classroom.name, subject=classroom.subject,
        num_sprints=classroom.num_sprints,
        payload=json.dumps(payload, ensure_ascii=False),
        finished_at=classroom.finished_at or datetime.now(UTC),
    ))
    db.commit()


def maybe_start(classroom_id: int) -> bool:
    """Start the session thread if the classroom is full and not already running.

    Returns True if a new session was launched.
    """
    with _running_lock:
        if classroom_id in _running:
            return False
        _running.add(classroom_id)

    db = SessionLocal()
    try:
        classroom = db.get(models.Classroom, classroom_id)
        full = classroom and len(classroom.memberships) == 3
        ready = full and classroom.status == models.STATUS_WAITING
        if not ready:
            with _running_lock:
                _running.discard(classroom_id)
            return False
    finally:
        db.close()

    thread = threading.Thread(target=run_session, args=(classroom_id,), daemon=True)
    thread.start()
    return True


def wait_until_finished(classroom_id: int, timeout: float = 30.0) -> bool:
    """Test helper / stop helper: block until the classroom thread completes."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with _running_lock:
            if classroom_id not in _running:
                return True
        time.sleep(0.05)
    return False
