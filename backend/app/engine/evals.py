"""Automated agent evaluations.

These are deterministic, dependency-free checks that verify each agent respects
the constraints in its system prompt. Because they are pure functions over the
produced text, they run identically in CI and in production, and they form the
basis of the eval gate exposed in the UI and the history archive.

Every check returns a dict::

    {"scope": str, "check_name": str, "passed": bool, "score": float, "detail": str}

``score`` is a 0..1 quality signal; ``passed`` is the hard gate.
"""
from __future__ import annotations

import re

from .text_utils import keywords, word_count

# First-person markers for the journal check.
_FIRST_PERSON = {"i", "i'm", "im", "my", "me", "myself", "i've", "ive"}

RELEVANCE_THRESHOLD = 0.6
ANSWER_OVERLAP_MIN = 1


def _check(scope, name, passed, score, detail):
    return {
        "scope": scope,
        "check_name": name,
        "passed": bool(passed),
        "score": round(float(score), 3),
        "detail": detail,
    }


def eval_questions(scope: str, subject: str, lesson: str,
                   questions: list[str]) -> list[dict]:
    """Teacher questions must number 10 and be relevant to the lesson taught."""
    results = []
    count_ok = len(questions) == 10
    results.append(_check(
        scope, "question_count", count_ok, 1.0 if count_ok else 0.0,
        f"Generated {len(questions)} questions (expected 10).",
    ))

    lesson_kw = keywords(lesson) | keywords(subject)
    if questions:
        relevant = sum(1 for q in questions if keywords(q) & lesson_kw)
        ratio = relevant / len(questions)
    else:
        ratio = 0.0
    passed = ratio >= RELEVANCE_THRESHOLD
    results.append(_check(
        scope, "question_relevance", passed, ratio,
        f"{int(ratio * 100)}% of questions share vocabulary with the lesson "
        f"(threshold {int(RELEVANCE_THRESHOLD * 100)}%).",
    ))
    return results


def eval_answer(scope: str, question: str, lesson: str, answer: str) -> list[dict]:
    """A student's answer should be on-topic w.r.t. the question/lesson."""
    target = keywords(question) | keywords(lesson)
    overlap = keywords(answer) & target
    score = (len(overlap) / max(1, len(keywords(answer)))) if answer else 0.0
    passed = len(overlap) >= ANSWER_OVERLAP_MIN
    return [_check(
        scope, "answer_on_topic", passed, score,
        f"Answer shares {len(overlap)} keyword(s) with the question/lesson.",
    )]


def eval_grade(scope: str, grade: int, reasoning: str) -> list[dict]:
    """The grade must be in range 1..10 with a non-empty justification."""
    in_range = isinstance(grade, int) and 1 <= grade <= 10
    has_reason = bool(reasoning and reasoning.strip())
    passed = in_range and has_reason
    return [_check(
        scope, "grade_validity", passed, 1.0 if passed else 0.0,
        f"grade={grade} in [1,10]={in_range}; reasoning_present={has_reason}.",
    )]


def eval_break(scope: str, subject: str, break_texts: list[str]) -> list[dict]:
    """Break chat is forbidden from mentioning the subject just taught."""
    subject_kw = keywords(subject)
    joined = " ".join(break_texts).lower()
    leaked = sorted(k for k in subject_kw if re.search(rf"\b{re.escape(k)}\b", joined))
    passed = not leaked
    score = 1.0 if passed else 0.0
    detail = (
        "No subject vocabulary leaked into the break chat."
        if passed else f"Leaked subject terms: {', '.join(leaked)}."
    )
    return [_check(scope, "break_off_topic", passed, score, detail)]


def eval_journal(scope: str, content: str, student_name: str) -> list[dict]:
    """Journal must be under 1000 words and written in the first person."""
    results = []
    wc = word_count(content)
    under = wc < 1000
    results.append(_check(
        scope, "journal_word_limit", under, min(1.0, wc / 1000.0),
        f"{wc} words (limit 1000).",
    ))

    tokens = set(re.findall(r"[a-z']+", content.lower()))
    first_person = bool(tokens & _FIRST_PERSON)
    has_name = student_name.lower() in content.lower()
    passed = first_person and has_name
    results.append(_check(
        scope, "journal_first_person", passed, 1.0 if passed else 0.0,
        f"first_person={first_person}; mentions_own_name={has_name}.",
    ))
    return results
