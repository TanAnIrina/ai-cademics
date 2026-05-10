"""
Live progress tracker for AI-cademics.

Thread-safe global state that gets updated during execute_sprint() / execute_break().
Frontend polls GET /api/live every ~1s to render a live progress UI.

Usage in main.py:
    import live_state as live
    
    live.start_sprint(sprint_id, subject)
    live.lesson_generated(len(lesson))
    live.questions_generated(len(questions))
    live.tick_answer(student_name, q_idx, question, grade, reasoning, action)
    live.tick_timeout(student_name, q_idx)
    live.achievement_unlocked(student_name, badge)
    live.end_sprint(sprint_id, summary)
    
    live.start_break(break_id, total_rounds, forbidden_subject)
    live.tick_break_message(speaker, message, mentioned_subject, comforted_peer)
    live.end_break(break_id)
    
    live.end_session()           # call when fully done
    live.snapshot()              # get current state (for /api/live)
"""

import threading
from datetime import datetime
from typing import Optional, Dict, Any, List

_lock = threading.RLock()

MAX_EVENTS = 100
MAX_RECENT_ANSWERS = 20
MAX_BREAK_MESSAGES = 30

_state: Dict[str, Any] = {
    "status": "idle",                # idle | sprint_running | break_running
    "step": None,                    # generating_lesson | generating_questions | asking_questions | break_in_progress | sprint_complete | break_complete
    "started_at": None,              # datetime
    "current_id": None,              # sprint_id or break_id
    "subject": None,
    "progress": {"current": 0, "total": 0},
    "current_student": None,
    "current_question_idx": None,
    "events": [],                    # last MAX_EVENTS events as timeline
    "recent_answers": [],            # last MAX_RECENT_ANSWERS graded answers
    "break_messages": [],            # last MAX_BREAK_MESSAGES break exchanges
    "summary": None,                 # set on completion
}


def _add_event(kind: str, **data):
    """Internal: append an event. MUST be called with _lock held."""
    event = {
        "kind": kind,
        "ts": datetime.now().isoformat(),
        **data,
    }
    _state["events"].append(event)
    if len(_state["events"]) > MAX_EVENTS:
        del _state["events"][:-MAX_EVENTS]


# =============================================================================
# SPRINT lifecycle
# =============================================================================

def start_sprint(sprint_id: str, subject: str, total_questions: int = 10, num_students: int = 2):
    with _lock:
        _state.update({
            "status": "sprint_running",
            "step": "generating_lesson",
            "started_at": datetime.now(),
            "current_id": sprint_id,
            "subject": subject,
            "progress": {"current": 0, "total": total_questions * num_students},
            "current_student": None,
            "current_question_idx": None,
            "events": [],
            "recent_answers": [],
            "break_messages": [],
            "summary": None,
        })
        _add_event("sprint_start", sprint_id=sprint_id, subject=subject)


def lesson_generated(char_count: int):
    with _lock:
        _state["step"] = "generating_questions"
        _add_event("lesson_generated", char_count=char_count)


def questions_generated(count: int):
    with _lock:
        _state["step"] = "asking_questions"
        _add_event("questions_generated", count=count)


def tick_answer(student_name: str, q_idx: int, question: str, grade: int,
                reasoning: Optional[str] = None, action: Optional[Dict] = None):
    with _lock:
        _state["progress"]["current"] += 1
        _state["current_student"] = student_name
        _state["current_question_idx"] = q_idx
        entry = {
            "student": student_name,
            "q_idx": q_idx,
            "question": (question or "")[:120],
            "grade": grade,
            "action": action,
        }
        _state["recent_answers"].append(entry)
        if len(_state["recent_answers"]) > MAX_RECENT_ANSWERS:
            del _state["recent_answers"][:-MAX_RECENT_ANSWERS]
        _add_event(
            "answer",
            student=student_name, q_idx=q_idx, grade=grade,
            action_type=(action or {}).get("type"),
            action_points=(action or {}).get("points"),
            reasoning=(reasoning or "")[:140],
        )


def tick_timeout(student_name: str, q_idx: int):
    with _lock:
        _state["progress"]["current"] += 1
        _add_event("timeout", student=student_name, q_idx=q_idx)


def achievement_unlocked(student_name: str, badge: Dict):
    with _lock:
        _add_event(
            "achievement",
            student=student_name,
            key=badge.get("key"),
            title=badge.get("title"),
            icon=badge.get("icon"),
            rarity=badge.get("rarity"),
            color=badge.get("color"),
        )


def end_sprint(sprint_id: str, summary: Dict):
    with _lock:
        _state["step"] = "sprint_complete"
        _state["summary"] = summary
        _add_event("sprint_complete", sprint_id=sprint_id)


# =============================================================================
# BREAK lifecycle
# =============================================================================

def start_break(break_id: str, total_rounds: int, forbidden_subject: Optional[str] = None):
    with _lock:
        # don't reset started_at if a sprint just ran (keep session-level timer)
        if _state["status"] == "idle" or _state["started_at"] is None:
            _state["started_at"] = datetime.now()
        _state.update({
            "status": "break_running",
            "step": "break_in_progress",
            "current_id": break_id,
            "subject": forbidden_subject,
            "progress": {"current": 0, "total": total_rounds * 2},
            "current_student": None,
            "current_question_idx": None,
            "break_messages": [],
        })
        _add_event("break_start", break_id=break_id)


def tick_break_message(speaker: str, message: str,
                       mentioned_subject: bool = False,
                       comforted_peer: bool = False):
    with _lock:
        _state["progress"]["current"] += 1
        _state["current_student"] = speaker
        msg = {
            "speaker": speaker,
            "message": (message or "")[:300],
            "mentioned_subject": mentioned_subject,
            "comforted_peer": comforted_peer,
        }
        _state["break_messages"].append(msg)
        if len(_state["break_messages"]) > MAX_BREAK_MESSAGES:
            del _state["break_messages"][:-MAX_BREAK_MESSAGES]
        _add_event(
            "break_message",
            speaker=speaker,
            message=msg["message"],
            mentioned_subject=mentioned_subject,
            comforted_peer=comforted_peer,
        )


def end_break(break_id: str):
    with _lock:
        _state["step"] = "break_complete"
        _add_event("break_complete", break_id=break_id)


# =============================================================================
# SESSION lifecycle (resets to idle)
# =============================================================================

def end_session():
    """Mark everything as idle. Keeps last events visible until next start."""
    with _lock:
        _state["status"] = "idle"
        _add_event("session_complete")


def reset():
    """Hard reset (use sparingly)."""
    with _lock:
        _state.update({
            "status": "idle",
            "step": None,
            "started_at": None,
            "current_id": None,
            "subject": None,
            "progress": {"current": 0, "total": 0},
            "current_student": None,
            "current_question_idx": None,
            "events": [],
            "recent_answers": [],
            "break_messages": [],
            "summary": None,
        })


# =============================================================================
# READ
# =============================================================================

def snapshot() -> Dict[str, Any]:
    """Get a JSON-safe copy of current state for the API endpoint."""
    with _lock:
        elapsed = 0
        started_iso = None
        if _state["started_at"] is not None:
            elapsed = int((datetime.now() - _state["started_at"]).total_seconds())
            started_iso = _state["started_at"].isoformat()

        progress = _state["progress"]
        pct = 0
        if progress["total"] > 0:
            pct = round(100 * progress["current"] / progress["total"], 1)

        return {
            "status": _state["status"],
            "step": _state["step"],
            "started_at": started_iso,
            "elapsed_seconds": elapsed,
            "current_id": _state["current_id"],
            "subject": _state["subject"],
            "progress": {**progress, "percent": pct},
            "current_student": _state["current_student"],
            "current_question_idx": _state["current_question_idx"],
            "events": list(_state["events"]),
            "recent_answers": list(_state["recent_answers"]),
            "break_messages": list(_state["break_messages"]),
            "summary": _state["summary"],
        }
