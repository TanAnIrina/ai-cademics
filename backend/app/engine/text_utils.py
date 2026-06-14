"""Tiny text helpers shared by the mock agent and the evaluators."""
from __future__ import annotations

import re

_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "your", "with", "this",
    "that", "from", "have", "has", "was", "were", "will", "what", "when",
    "where", "which", "into", "about", "their", "them", "they", "then", "than",
    "also", "some", "such", "very", "just", "like", "over", "under", "between",
    "context", "explain", "question", "answer", "lesson", "today", "based",
    "describe", "provide", "concept", "concepts", "subject", "topic",
}

_WORD_RE = re.compile(r"[a-z0-9]+")


def keywords(text: str, min_len: int = 4) -> set[str]:
    """Lower-cased content words of length >= ``min_len``, minus stopwords."""
    if not text:
        return set()
    return {
        w for w in _WORD_RE.findall(text.lower())
        if len(w) >= min_len and w not in _STOPWORDS
    }


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))
