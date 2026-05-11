"""
Database module for AI-cademics.
SQLite persistence for sprints, grades, achievements, emotions history.

Auto-creates database on first import.

V1.1 changes:
- Added create_sprint_stub() — inserts minimal sprint row at sprint START, so
  FK-referenced inserts (emotions_history, grades, etc.) work mid-sprint.
- save_sprint() is now idempotent — UPDATE if a stub exists, INSERT otherwise.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict
from contextlib import contextmanager
import os

DB_PATH = os.environ.get("AICADEMICS_DB", "ai_cademics.db")


# =============================================================================
# CONNECTION
# =============================================================================

@contextmanager
def get_db():
    """Context manager for DB connections with auto-close."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =============================================================================
# SCHEMA INITIALIZATION
# =============================================================================

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    name TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    total_sprints INTEGER DEFAULT 0,
    total_perfect_scores INTEGER DEFAULT 0,
    total_sanctions INTEGER DEFAULT 0,
    total_rewards INTEGER DEFAULT 0,
    total_comforts_given INTEGER DEFAULT 0,
    total_slang_penalties INTEGER DEFAULT 0,
    cumulative_grade REAL DEFAULT 0,
    grade_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sprints (
    id TEXT PRIMARY KEY,
    sprint_number INTEGER NOT NULL,
    subject TEXT NOT NULL,
    lesson TEXT,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    duration_seconds REAL,
    session_id TEXT
);

CREATE TABLE IF NOT EXISTS grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sprint_id TEXT NOT NULL,
    student_name TEXT NOT NULL,
    question_idx INTEGER NOT NULL,
    question TEXT NOT NULL,
    answer TEXT,
    grade INTEGER,
    reasoning TEXT,
    has_slang BOOLEAN DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sprint_id) REFERENCES sprints(id),
    FOREIGN KEY (student_name) REFERENCES students(name)
);

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sprint_id TEXT NOT NULL,
    student_name TEXT NOT NULL,
    grade_id INTEGER,
    action_type TEXT NOT NULL,
    points INTEGER NOT NULL,
    explanation TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sprint_id) REFERENCES sprints(id),
    FOREIGN KEY (grade_id) REFERENCES grades(id)
);

CREATE TABLE IF NOT EXISTS breaks (
    id TEXT PRIMARY KEY,
    sprint_id TEXT,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    subject_forbidden TEXT,
    FOREIGN KEY (sprint_id) REFERENCES sprints(id)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    break_id TEXT NOT NULL,
    round_num INTEGER NOT NULL,
    speaker TEXT NOT NULL,
    message TEXT NOT NULL,
    mentioned_subject BOOLEAN DEFAULT 0,
    comforted_peer BOOLEAN DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (break_id) REFERENCES breaks(id)
);

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    achievement_key TEXT NOT NULL,
    sprint_id TEXT,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_name, achievement_key),
    FOREIGN KEY (student_name) REFERENCES students(name)
);

CREATE TABLE IF NOT EXISTS emotions_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    frustration INTEGER NOT NULL,
    happiness INTEGER NOT NULL,
    sprint_id TEXT,
    context TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_name) REFERENCES students(name),
    FOREIGN KEY (sprint_id) REFERENCES sprints(id)
);

CREATE INDEX IF NOT EXISTS idx_grades_sprint ON grades(sprint_id);
CREATE INDEX IF NOT EXISTS idx_grades_student ON grades(student_name);
CREATE INDEX IF NOT EXISTS idx_emotions_student ON emotions_history(student_name);
CREATE INDEX IF NOT EXISTS idx_messages_break ON messages(break_id);
"""


def init_db():
    """Initialize database with schema."""
    with get_db() as conn:
        conn.executescript(SCHEMA)
        conn.execute("""
            INSERT OR IGNORE INTO students (name, model) VALUES
                ('Qwen', 'qwen3:4b'),
                ('Llama', 'llama3.2:3b')
        """)
    print(f"[DB] Initialized at: {DB_PATH}")


# =============================================================================
# STUDENTS
# =============================================================================

def get_student(name: str) -> Optional[Dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM students WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None


def get_all_students() -> List[Dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def increment_student_counter(name: str, column: str, by: int = 1):
    with get_db() as conn:
        conn.execute(
            f"UPDATE students SET {column} = {column} + ? WHERE name = ?",
            (by, name)
        )


# =============================================================================
# SPRINTS
# =============================================================================

def get_total_sprints() -> int:
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as count FROM sprints").fetchone()
        return row["count"] if row else 0


# ─── NEW IN V1.1 ─────────────────────────────────────────────────────────────
def create_sprint_stub(sprint_id: str, subject: str, started_at: str,
                       session_id: Optional[str] = None):
    """
    Insert minimal sprint row at the START of a sprint, so FK-referenced
    inserts (emotions_history, grades, actions) work mid-sprint.
    
    save_sprint() will later UPDATE this row with full data (lesson, ended_at,
    duration, grades, etc.).
    
    Idempotent: safe to call multiple times — INSERT OR IGNORE skips if exists.
    """
    sprint_number = get_total_sprints() + 1
    with get_db() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO sprints
                (id, sprint_number, subject, started_at, session_id)
            VALUES (?, ?, ?, ?, ?)
        """, (sprint_id, sprint_number, subject, started_at, session_id))


def save_sprint(sprint_data: Dict):
    """
    Save (or finalize) a complete sprint to database.
    
    V1.1: idempotent w.r.t. the sprint row — if a stub exists (from
    create_sprint_stub), it UPDATEs the full data; otherwise INSERTs new.
    Grades/actions are always inserted (this should only be called once
    per sprint after answers are collected).
    """
    sprint_id = sprint_data["sprint_id"]
    
    with get_db() as conn:
        # ── 1. Upsert the sprint row ──────────────────────────────────────
        existing = conn.execute("SELECT id FROM sprints WHERE id = ?", (sprint_id,)).fetchone()
        
        if existing:
            # Stub exists — UPDATE with full data
            conn.execute("""
                UPDATE sprints SET
                    subject = COALESCE(?, subject),
                    lesson = ?,
                    ended_at = ?,
                    duration_seconds = ?,
                    session_id = COALESCE(?, session_id)
                WHERE id = ?
            """, (
                sprint_data.get("subject"),
                sprint_data.get("lesson"),
                sprint_data.get("ended_at"),
                sprint_data.get("duration_seconds"),
                sprint_data.get("session_id"),
                sprint_id,
            ))
        else:
            # No stub — fresh INSERT (legacy path)
            sprint_number = get_total_sprints() + 1
            conn.execute("""
                INSERT INTO sprints
                    (id, sprint_number, subject, lesson, started_at, ended_at, duration_seconds, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sprint_id,
                sprint_number,
                sprint_data.get("subject"),
                sprint_data.get("lesson"),
                sprint_data.get("started_at"),
                sprint_data.get("ended_at"),
                sprint_data.get("duration_seconds"),
                sprint_data.get("session_id")
            ))
        
        # ── 2. Insert grades + actions + counter updates (unchanged) ──────
        for student_name, answers in sprint_data.get("answers", {}).items():
            for answer in answers:
                cursor = conn.execute("""
                    INSERT INTO grades 
                        (sprint_id, student_name, question_idx, question, answer, grade, reasoning, has_slang)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sprint_id,
                    student_name,
                    answer.get("question_idx"),
                    answer.get("question"),
                    answer.get("answer"),
                    answer.get("grade"),
                    answer.get("reasoning"),
                    answer.get("has_slang", False)
                ))
                grade_id = cursor.lastrowid
                
                if answer.get("grade") is not None:
                    conn.execute("""
                        UPDATE students 
                        SET cumulative_grade = cumulative_grade + ?,
                            grade_count = grade_count + 1
                        WHERE name = ?
                    """, (answer["grade"], student_name))
                
                action = answer.get("action")
                if action:
                    conn.execute("""
                        INSERT INTO actions 
                            (sprint_id, student_name, grade_id, action_type, points, explanation)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        sprint_id, student_name, grade_id,
                        action.get("type"),
                        action.get("points", 0),
                        action.get("explanation")
                    ))
                    
                    if action.get("type") == "sanction":
                        conn.execute("UPDATE students SET total_sanctions = total_sanctions + 1 WHERE name = ?", (student_name,))
                    elif action.get("type") == "reward":
                        conn.execute("UPDATE students SET total_rewards = total_rewards + 1 WHERE name = ?", (student_name,))
                
                if answer.get("grade") == 10:
                    conn.execute("UPDATE students SET total_perfect_scores = total_perfect_scores + 1 WHERE name = ?", (student_name,))
        
        for student_name in sprint_data.get("answers", {}).keys():
            conn.execute("UPDATE students SET total_sprints = total_sprints + 1 WHERE name = ?", (student_name,))
    
    return sprint_id


def get_sprint(sprint_id: str) -> Optional[Dict]:
    with get_db() as conn:
        sprint = conn.execute("SELECT * FROM sprints WHERE id = ?", (sprint_id,)).fetchone()
        if not sprint:
            return None
        
        sprint_dict = dict(sprint)
        grades = conn.execute("""
            SELECT g.*, a.action_type, a.points as action_points, a.explanation as action_explanation
            FROM grades g
            LEFT JOIN actions a ON a.grade_id = g.id
            WHERE g.sprint_id = ?
            ORDER BY g.student_name, g.question_idx
        """, (sprint_id,)).fetchall()
        
        sprint_dict["grades"] = [dict(g) for g in grades]
        return sprint_dict


def get_recent_sprints(limit: int = 10) -> List[Dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM sprints ORDER BY started_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


# =============================================================================
# BREAKS & MESSAGES
# =============================================================================

def save_break(break_data: Dict, sprint_id: Optional[str] = None):
    break_id = break_data["break_id"]
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO breaks (id, sprint_id, started_at, ended_at, subject_forbidden)
            VALUES (?, ?, ?, ?, ?)
        """, (
            break_id, sprint_id,
            break_data.get("started_at"),
            break_data.get("ended_at"),
            break_data.get("subject_forbidden")
        ))
        
        for msg in break_data.get("conversation", []):
            conn.execute("""
                INSERT INTO messages 
                    (break_id, round_num, speaker, message, mentioned_subject, comforted_peer)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                break_id,
                msg.get("round", 0),
                msg.get("speaker"),
                msg.get("message"),
                msg.get("mentioned_subject", False),
                msg.get("comforted_peer", False)
            ))
            
            if msg.get("comforted_peer"):
                conn.execute("UPDATE students SET total_comforts_given = total_comforts_given + 1 WHERE name = ?", (msg.get("speaker"),))
    
    return break_id


# =============================================================================
# ACHIEVEMENTS
# =============================================================================

def unlock_achievement(student_name: str, achievement_key: str, sprint_id: Optional[str] = None) -> bool:
    """Returns True if newly unlocked, False if already had it."""
    with get_db() as conn:
        try:
            conn.execute("""
                INSERT INTO achievements (student_name, achievement_key, sprint_id)
                VALUES (?, ?, ?)
            """, (student_name, achievement_key, sprint_id))
            return True
        except sqlite3.IntegrityError:
            return False


def get_student_achievements(student_name: str) -> List[Dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM achievements WHERE student_name = ? ORDER BY unlocked_at DESC
        """, (student_name,)).fetchall()
        return [dict(r) for r in rows]


def has_achievement(student_name: str, achievement_key: str) -> bool:
    with get_db() as conn:
        row = conn.execute("""
            SELECT 1 FROM achievements WHERE student_name = ? AND achievement_key = ?
        """, (student_name, achievement_key)).fetchone()
        return row is not None


# =============================================================================
# EMOTIONS HISTORY
# =============================================================================

def record_emotion(student_name: str, frustration: int, happiness: int,
                    sprint_id: Optional[str] = None, context: str = ""):
    """
    V1.1: defensive — convert empty-string sprint_id to None so the FK is
    treated as NULL (which is allowed) rather than referencing a non-existent
    sprint with id=''.
    """
    if sprint_id == "":
        sprint_id = None
    with get_db() as conn:
        conn.execute("""
            INSERT INTO emotions_history (student_name, frustration, happiness, sprint_id, context)
            VALUES (?, ?, ?, ?, ?)
        """, (student_name, frustration, happiness, sprint_id, context))


def get_emotion_history(student_name: str, limit: int = 100) -> List[Dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM emotions_history 
            WHERE student_name = ? ORDER BY recorded_at DESC LIMIT ?
        """, (student_name, limit)).fetchall()
        return [dict(r) for r in rows]


# =============================================================================
# LEADERBOARD & STATS
# =============================================================================

def get_leaderboard() -> List[Dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT 
                name, model, total_sprints, total_perfect_scores,
                total_sanctions, total_rewards, total_comforts_given,
                CASE WHEN grade_count > 0 THEN ROUND(cumulative_grade / grade_count, 2) ELSE 0 END as average_grade,
                grade_count as total_questions_answered
            FROM students
            ORDER BY average_grade DESC, total_perfect_scores DESC
        """).fetchall()
        return [dict(r) for r in rows]


def get_student_progression(student_name: str) -> List[Dict]:
    """Get student's grade progression across sprints."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT 
                s.id as sprint_id, s.sprint_number, s.subject, s.started_at,
                ROUND(AVG(g.grade), 2) as average_grade,
                COUNT(g.id) as questions_count
            FROM sprints s
            LEFT JOIN grades g ON g.sprint_id = s.id AND g.student_name = ?
            GROUP BY s.id
            HAVING questions_count > 0
            ORDER BY s.started_at ASC
        """, (student_name,)).fetchall()
        return [dict(r) for r in rows]


def get_global_stats() -> Dict:
    with get_db() as conn:
        sprints = conn.execute("SELECT COUNT(*) as c FROM sprints").fetchone()["c"]
        breaks = conn.execute("SELECT COUNT(*) as c FROM breaks").fetchone()["c"]
        grades = conn.execute("SELECT COUNT(*) as c FROM grades").fetchone()["c"]
        achievements = conn.execute("SELECT COUNT(*) as c FROM achievements").fetchone()["c"]
        avg = conn.execute("SELECT ROUND(AVG(grade), 2) as avg FROM grades WHERE grade IS NOT NULL").fetchone()
        avg_grade = avg["avg"] if avg and avg["avg"] else 0
        
        return {
            "total_sprints": sprints,
            "total_breaks": breaks,
            "total_questions_graded": grades,
            "total_achievements_unlocked": achievements,
            "global_average_grade": avg_grade
        }


def reset_database():
    with get_db() as conn:
        conn.executescript("""
            DROP TABLE IF EXISTS achievements;
            DROP TABLE IF EXISTS emotions_history;
            DROP TABLE IF EXISTS messages;
            DROP TABLE IF EXISTS breaks;
            DROP TABLE IF EXISTS actions;
            DROP TABLE IF EXISTS grades;
            DROP TABLE IF EXISTS sprints;
            DROP TABLE IF EXISTS students;
        """)
    init_db()


def delete_sprint_progress(sprint_id: Optional[str]):
    """
    Delete all DB records tied to a specific sprint id.
    Used when a running sprint is cancelled/reset.
    """
    if not sprint_id:
        return
    with get_db() as conn:
        # Delete break messages for breaks linked to this sprint
        conn.execute("""
            DELETE FROM messages
            WHERE break_id IN (SELECT id FROM breaks WHERE sprint_id = ?)
        """, (sprint_id,))
        # Delete breaks linked to sprint
        conn.execute("DELETE FROM breaks WHERE sprint_id = ?", (sprint_id,))
        # Delete dependent rows
        conn.execute("DELETE FROM actions WHERE sprint_id = ?", (sprint_id,))
        conn.execute("DELETE FROM grades WHERE sprint_id = ?", (sprint_id,))
        conn.execute("DELETE FROM emotions_history WHERE sprint_id = ?", (sprint_id,))
        conn.execute("DELETE FROM achievements WHERE sprint_id = ?", (sprint_id,))
        # Finally delete sprint row
        conn.execute("DELETE FROM sprints WHERE id = ?", (sprint_id,))


# Initialize on import
init_db()
