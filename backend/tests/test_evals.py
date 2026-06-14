"""Unit tests for the automated agent evals.

These are pure functions, so we test both the passing and the failing path of
every check directly — no simulation needed.
"""
from app.engine import evals


def _by_name(results, name):
    return next(r for r in results if r["check_name"] == name)


# --- questions -------------------------------------------------------------
def test_question_count_pass_and_fail():
    ten = [f"What is concept {i} in graph theory?" for i in range(10)]
    res = evals.eval_questions("teacher", "graph theory", "graph theory vertices edges", ten)
    assert _by_name(res, "question_count")["passed"]

    res = evals.eval_questions("teacher", "graph theory", "graph theory vertices", ten[:5])
    assert not _by_name(res, "question_count")["passed"]


def test_question_relevance_pass_and_fail():
    lesson = "graph theory covers vertices edges paths cycles connectivity"
    relevant = [f"Explain vertices and edges in graph {i}" for i in range(10)]
    res = evals.eval_questions("teacher", "graph theory", lesson, relevant)
    assert _by_name(res, "question_relevance")["passed"]

    irrelevant = ["What did you eat for breakfast today friend?" for _ in range(10)]
    res = evals.eval_questions("teacher", "graph theory", lesson, irrelevant)
    assert not _by_name(res, "question_relevance")["passed"]


# --- answer ----------------------------------------------------------------
def test_answer_on_topic_pass_and_fail():
    q = "Explain vertices and edges"
    lesson = "graph theory vertices edges"
    on = evals.eval_answer("student", q, lesson, "vertices connect via edges in a graph")
    assert on[0]["passed"]

    off = evals.eval_answer("student", q, lesson, "purple monday breakfast running")
    assert not off[0]["passed"]


# --- grade -----------------------------------------------------------------
def test_grade_validity():
    assert evals.eval_grade("teacher", 7, "Solid reasoning shown.")[0]["passed"]
    assert not evals.eval_grade("teacher", 0, "out of range")[0]["passed"]
    assert not evals.eval_grade("teacher", 11, "too high")[0]["passed"]
    assert not evals.eval_grade("teacher", 7, "")[0]["passed"]


# --- break -----------------------------------------------------------------
def test_break_off_topic_pass_and_fail():
    ok = evals.eval_break("student", "calculus", ["how was your weekend?", "i relaxed a lot"])
    assert ok[0]["passed"]

    leaked = evals.eval_break(
        "student", "calculus", ["i kept thinking about calculus during break"]
    )
    assert not leaked[0]["passed"]


# --- journal ---------------------------------------------------------------
def test_journal_word_limit():
    short = evals.eval_journal("student", "I learned a lot today, it was Ada speaking.", "Ada")
    assert _by_name(short, "journal_word_limit")["passed"]

    long_text = "Ada " + " ".join(["word"] * 1200)
    res = evals.eval_journal("student", long_text, "Ada")
    assert not _by_name(res, "journal_word_limit")["passed"]


def test_journal_first_person_requires_pronoun_and_name():
    good = evals.eval_journal("student", "I felt that Ada understood the lesson well today.", "Ada")
    assert _by_name(good, "journal_first_person")["passed"]

    no_name = evals.eval_journal("student", "I felt good about the lesson today.", "Ada")
    assert not _by_name(no_name, "journal_first_person")["passed"]

    no_pronoun = evals.eval_journal("student", "Ada the lesson was about graphs.", "Ada")
    assert not _by_name(no_pronoun, "journal_first_person")["passed"]
