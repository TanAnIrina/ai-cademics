"""
ai-cademics — Student Journals module.

After each sprint, students write a personal journal entry reflecting on:
- what they learned
- how they felt
- their relationship with teacher and peer
- what they want to do better

Word limit: 1000 (US 11). We allow longer journals but flag them.

This is a separate module so we don't touch database.py.
Initializes its own table on import.
"""

import database as db
from datetime import datetime
from typing import Optional, List, Dict


JOURNAL_WORD_LIMIT = 1000


SCHEMA = """
CREATE TABLE IF NOT EXISTS journals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sprint_id TEXT,
    student_name TEXT NOT NULL,
    subject TEXT,
    content TEXT NOT NULL,
    word_count INTEGER DEFAULT 0,
    over_word_limit BOOLEAN DEFAULT 0,
    written_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sprint_id) REFERENCES sprints(id) ON DELETE SET NULL,
    FOREIGN KEY (student_name) REFERENCES students(name)
);

CREATE INDEX IF NOT EXISTS idx_journals_student ON journals(student_name);
CREATE INDEX IF NOT EXISTS idx_journals_sprint  ON journals(sprint_id);
"""


def init_schema():
    with db.get_db() as conn:
        conn.executescript(SCHEMA)
    print("[DB] Journals schema initialized")


def count_words(text: str) -> int:
    if not text:
        return 0
    return len(text.strip().split())


def save_journal(student_name: str, content: str, sprint_id: Optional[str] = None,
                 subject: Optional[str] = None) -> Dict:
    """Persist a journal entry. Returns the stored dict with word_count + over_limit flag."""
    wc = count_words(content)
    over = wc > JOURNAL_WORD_LIMIT
    
    with db.get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO journals
                (sprint_id, student_name, subject, content, word_count, over_word_limit)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sprint_id, student_name, subject, content, wc, over),
        )
        journal_id = cursor.lastrowid
    
    return {
        "id": journal_id,
        "sprint_id": sprint_id,
        "student_name": student_name,
        "subject": subject,
        "content": content,
        "word_count": wc,
        "over_word_limit": over,
        "written_at": datetime.now().isoformat(),
    }


def get_journal(journal_id: int) -> Optional[Dict]:
    with db.get_db() as conn:
        row = conn.execute("SELECT * FROM journals WHERE id = ?", (journal_id,)).fetchone()
        return dict(row) if row else None


def get_journals_for_student(student_name: str, limit: int = 50) -> List[Dict]:
    with db.get_db() as conn:
        rows = conn.execute(
            """SELECT j.*, s.subject as sprint_subject
               FROM journals j
               LEFT JOIN sprints s ON s.id = j.sprint_id
               WHERE j.student_name = ?
               ORDER BY j.written_at DESC
               LIMIT ?""",
            (student_name, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_journals_for_sprint(sprint_id: str) -> List[Dict]:
    with db.get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM journals WHERE sprint_id = ? ORDER BY student_name""",
            (sprint_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_journals(limit: int = 100) -> List[Dict]:
    with db.get_db() as conn:
        rows = conn.execute(
            """SELECT j.*, s.subject as sprint_subject
               FROM journals j
               LEFT JOIN sprints s ON s.id = j.sprint_id
               ORDER BY j.written_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_stats() -> Dict:
    with db.get_db() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM journals").fetchone()["c"]
        over = conn.execute("SELECT COUNT(*) as c FROM journals WHERE over_word_limit = 1").fetchone()["c"]
        avg_wc = conn.execute("SELECT ROUND(AVG(word_count)) as w FROM journals").fetchone()["w"]
        return {
            "total_journals": total,
            "over_limit_count": over,
            "average_word_count": int(avg_wc) if avg_wc else 0,
            "word_limit": JOURNAL_WORD_LIMIT,
        }


# Initialize on import
init_schema()
