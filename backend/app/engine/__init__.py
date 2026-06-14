"""Session simulation engine.

When a classroom fills (1 teacher + N students) it transitions to ``running``
and a background thread executes the whole session:

    for each sprint:
        choose  -> (between sprints) the teacher picks the next subject
        lesson  -> an interactive discussion: the teacher teaches a part, a
                   student asks about it, the teacher answers; repeated for
                   several segments and paced to span the chosen sprint length
        test    -> teacher writes 10 questions of diverse formats; each student
                   answers
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


def _sleep(seconds: float, classroom_id: int | None = None) -> None:
    """Sleep for ``seconds`` but wake early if a stop is requested."""
    if seconds <= 0:
        return
    end = time.monotonic() + seconds
    while True:
        remaining = end - time.monotonic()
        if remaining <= 0:
            return
        if classroom_id is not None and _should_stop(classroom_id):
            return
        time.sleep(min(0.5, remaining))


# --- between-sprint subject choice -----------------------------------------
_subject_events: dict[int, threading.Event] = {}
_subject_values: dict[int, str] = {}


def submit_next_subject(classroom_id: int, subject: str) -> None:
    """Teacher's choice for the next sprint; wakes the waiting engine thread."""
    _subject_values[classroom_id] = subject
    ev_ = _subject_events.get(classroom_id)
    if ev_ is not None:
        ev_.set()


def is_choosing(classroom_id: int) -> bool:
    return classroom_id in _subject_events


def _await_subject(classroom_id: int, current: str) -> str:
    """Block until the teacher picks the next subject, or keep ``current``.

    Returns immediately with ``current`` when ``subject_choice_seconds`` is 0
    (tests/demo) or on stop/timeout.
    """
    wait_s = settings.subject_choice_seconds
    if wait_s <= 0:
        return current
    ev_ = threading.Event()
    _subject_events[classroom_id] = ev_
    _subject_values.pop(classroom_id, None)
    try:
        end = time.monotonic() + wait_s
        while time.monotonic() < end:
            if _should_stop(classroom_id):
                break
            if ev_.wait(timeout=min(0.5, max(0.0, end - time.monotonic()))):
                break
    finally:
        _subject_events.pop(classroom_id, None)
    chosen = (_subject_values.pop(classroom_id, None) or "").strip()
    return chosen or current


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
        active_slots = models.student_slots(classroom.max_students)
        student_ms = [memberships[s] for s in active_slots if s in memberships]
        if not (teacher_m and student_ms and len(student_ms) == len(active_slots)):
            return

        bound_queue = BoundQueue(external_queue, classroom_id)
        teacher = _agent_for(teacher_m, bound_queue, teacher_m.agent_name, "")

        def _others(m: models.Membership) -> str:
            names = [o.agent_name for o in student_ms if o is not m]
            return ", ".join(names) if names else "your classmate"

        students = [
            (m, _agent_for(m, bound_queue, teacher_m.agent_name, _others(m)))
            for m in student_ms
        ]
        all_members = [teacher_m, *student_ms]

        # Per-agent memory carried across sprints (slot -> short summary string).
        memory: dict[str, str] = {}

        subject = classroom.subject or "General Knowledge"
        classroom.status = models.STATUS_RUNNING
        classroom.started_at = datetime.now(UTC)
        db.commit()

        roster = " and ".join(m.agent_name for m in student_ms)
        _add_message(db, classroom_id, 0, models.PHASE_IDLE, "system", "system",
                     f"Session started. Teacher {teacher_m.agent_name} will teach "
                     f"'{subject}' to {roster} across {classroom.num_sprints} sprint(s).")

        # Baseline emotion snapshot (sprint 0) so charts show the starting point.
        for m in all_members:
            _snapshot(db, classroom_id, 0, m)

        for sprint in range(1, classroom.num_sprints + 1):
            if _should_stop(classroom_id):
                break

            # --- CHOOSE NEXT SUBJECT (between sprints) ----------------------
            if sprint > 1:
                _set_phase(db, classroom, models.PHASE_CHOOSING, sprint)
                subject = _await_subject(classroom_id, subject)
                if _should_stop(classroom_id):
                    break
                classroom.subject = subject
                db.commit()
                _add_message(db, classroom_id, sprint, models.PHASE_IDLE, "system",
                             "system", f"Sprint {sprint} subject: {subject}.")

            # --- LESSON (interactive discussion, paced over ~sprint_minutes) -
            _set_phase(db, classroom, models.PHASE_LESSON, sprint)
            # A test is coming: a little anticipatory anxiety, lessons can bore.
            for m, _a in students:
                _adjust(m, anxiety=+1, boredom=+1)
            db.commit()

            num_segments = max(2, min(6, classroom.sprint_minutes // 4))
            total_msgs = 2 + 3 * num_segments  # intro + (teach+ask+reply)*segs + recap
            lesson_seconds = classroom.sprint_minutes * 60 * settings.time_scale
            per_msg = (lesson_seconds / total_msgs) if total_msgs else 0.0
            discussion: list[str] = []

            def _say(sender: str, role: str, text: str,
                     _sprint: int = sprint, _per: float = per_msg,
                     _disc: list = discussion) -> None:
                _add_message(db, classroom_id, _sprint, models.PHASE_LESSON,
                             sender, role, text)
                _disc.append(text)
                _sleep(_per, classroom_id)

            _say(teacher_m.agent_name, "teacher",
                 teacher.teach(subject, "intro", 0, num_segments, ""))
            for seg_i in range(1, num_segments + 1):
                if _should_stop(classroom_id):
                    break
                seg = teacher.teach(subject, "segment", seg_i, num_segments,
                                    "\n".join(discussion))
                _say(teacher_m.agent_name, "teacher", seg)
                sm, sagent = students[(seg_i - 1) % len(students)]
                q = sagent.ask_in_lesson(subject, seg, _emotions(sm), memory.get(sm.slot))
                _say(sm.agent_name, "student", q)
                _say(teacher_m.agent_name, "teacher",
                     teacher.address_question(subject, q, seg))
            if not _should_stop(classroom_id):
                _say(teacher_m.agent_name, "teacher",
                     teacher.teach(subject, "recap", num_segments, num_segments,
                                   "\n".join(discussion)))

            lesson = "\n".join(discussion)
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
                    _adjust(teacher_m, happiness=+2, confidence=+1, curiosity=+1, frustration=-1)
                elif avg >= 6:
                    _adjust(teacher_m, happiness=+1, confidence=+1, anxiety=-1)
                elif avg <= 4:
                    _adjust(teacher_m, frustration=+2, happiness=-1, anxiety=+1, confidence=-1)
                else:
                    _adjust(teacher_m, anxiety=-1)
                # Teaching the same material repeatedly: confidence grows, novelty fades.
                _adjust(teacher_m, confidence=+1, boredom=+1, curiosity=-1)
                db.commit()
            _pause(classroom_id)
            if _should_stop(classroom_id):
                break

            # --- BREAK (responsive off-topic chat, mutual comforting) ------
            _set_phase(db, classroom, models.PHASE_BREAK, sprint)
            break_texts: list[str] = []
            last_line: str | None = None
            last_speaker: models.Membership | None = None
            n = len(students)
            break_per_turn = (
                classroom.break_minutes * 60 * settings.time_scale / settings.break_turns
                if settings.break_turns else 0.0
            )
            for turn in range(settings.break_turns):
                m, agent = students[turn % n]
                # Address whoever spoke immediately before (round-robin).
                peer_m = last_speaker if last_speaker is not None else students[(turn + 1) % n][0]
                line = agent.break_turn(peer_m.agent_name, teacher_m.agent_name,
                                        subject, _emotions(m), last_line,
                                        memory.get(m.slot))
                break_texts.append(line)
                _add_message(db, classroom_id, sprint, models.PHASE_BREAK,
                             m.agent_name, "student", line)
                # Comforting a highly-frustrated peer eases their distress.
                if last_speaker is not None and peer_m.frustration >= 6:
                    _adjust(peer_m, frustration=-2, anxiety=-1, happiness=+1)
                    db.commit()
                last_line = line
                last_speaker = m
                _sleep(break_per_turn, classroom_id)
            _record_evals(db, classroom_id, sprint,
                          ev.eval_break("break_chat", subject, break_texts))
            if _should_stop(classroom_id):
                break

            # --- JOURNAL (students + teacher) ------------------------------
            _set_phase(db, classroom, models.PHASE_JOURNAL, sprint)
            for m, agent in students:
                others = [o.agent_name for o in student_ms if o is not m]
                peer_label = ", ".join(others) if others else "your classmate"
                entry = agent.journal(subject, peer_label,
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
                subject, [m.agent_name for m in student_ms], summary,
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
            for m in all_members:
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
        _subject_events.pop(classroom_id, None)
        _subject_values.pop(classroom_id, None)
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
    ratings = db.query(models.LessonRating).filter_by(classroom_id=cid).order_by(
        models.LessonRating.id).all()

    payload = {
        "classroom": {
            "id": cid, "name": classroom.name, "subject": classroom.subject,
            "sprint_minutes": classroom.sprint_minutes,
            "break_minutes": classroom.break_minutes,
            "num_sprints": classroom.num_sprints,
            "max_students": classroom.max_students,
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
        "ratings": [
            {"sprint": r.sprint_index, "nickname": r.nickname, "stars": r.stars,
             "comment": r.comment, "at": r.created_at.isoformat()} for r in ratings
        ],
    }
    db.add(models.Archive(
        classroom_id=cid, name=classroom.name, subject=classroom.subject,
        num_sprints=classroom.num_sprints,
        payload=json.dumps(payload, ensure_ascii=False),
        finished_at=classroom.finished_at or datetime.now(UTC),
    ))
    db.commit()


def _is_full(classroom: models.Classroom) -> bool:
    return len(classroom.memberships) == 1 + classroom.max_students


def _schedule_reached(classroom: models.Classroom) -> bool:
    """True if the room has no schedule, or its scheduled start time has arrived."""
    if classroom.scheduled_start is None:
        return True
    start = classroom.scheduled_start
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    return datetime.now(UTC) >= start


def maybe_start(classroom_id: int) -> bool:
    """Start the session thread if the classroom is full, due, and not already running.

    Returns True if a new session was launched.
    """
    with _running_lock:
        if classroom_id in _running:
            return False
        _running.add(classroom_id)

    db = SessionLocal()
    try:
        classroom = db.get(models.Classroom, classroom_id)
        ready = (
            classroom is not None
            and classroom.status == models.STATUS_WAITING
            and _is_full(classroom)
            and _schedule_reached(classroom)
        )
        if not ready:
            with _running_lock:
                _running.discard(classroom_id)
            return False
    finally:
        db.close()

    thread = threading.Thread(target=run_session, args=(classroom_id,), daemon=True)
    thread.start()
    return True


def _scheduler_loop(interval: float = 5.0) -> None:
    """Background ticker: start full rooms whose scheduled time has arrived."""
    while True:
        time.sleep(interval)
        try:
            db = SessionLocal()
            try:
                rooms = (
                    db.query(models.Classroom)
                    .filter(models.Classroom.status == models.STATUS_WAITING)
                    .filter(models.Classroom.scheduled_start.isnot(None))
                    .all()
                )
                due = [
                    c.id for c in rooms if _is_full(c) and _schedule_reached(c)
                ]
            finally:
                db.close()
            for cid in due:
                maybe_start(cid)
        except Exception:  # pragma: no cover - defensive, keep the ticker alive
            pass


def start_scheduler() -> None:
    """Launch the scheduler ticker once (called at app startup).

    Disabled when ``AICADEMICS_SCHEDULER=0`` (used by the test suite, where the
    join/configure paths already exercise schedule handling synchronously).
    """
    import os

    if os.environ.get("AICADEMICS_SCHEDULER", "1") == "0":
        return
    thread = threading.Thread(target=_scheduler_loop, daemon=True)
    thread.start()


def wait_until_finished(classroom_id: int, timeout: float = 30.0) -> bool:
    """Test helper / stop helper: block until the classroom thread completes."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with _running_lock:
            if classroom_id not in _running:
                return True
        time.sleep(0.05)
    return False
