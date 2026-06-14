"""Agent abstraction.

The simulation engine talks to *agents*, not raw providers. An agent knows how
to produce each kind of turn (lesson, questions, answer, grade, break chat,
journal). Three implementations exist:

* ``MockAgent``      - deterministic, dependency-free, used by default and in CI.
* ``LLMAgent``       - wraps a real provider client (Anthropic/OpenAI/Ollama).
* ``ExternalAgent``  - delegates to a self-hosted agent that polls the backend
                       (the original AI-cademics runtime), via a task queue.

All agents return data in the same shapes so the engine never branches on type.
"""
from __future__ import annotations

import hashlib
import json
import random
import re

from . import prompts
from .providers import ProviderClient, build_client
from .text_utils import keywords


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class BaseAgent:
    def __init__(self, name: str, role: str) -> None:
        self.name = name
        self.role = role

    # Teacher capabilities
    def lesson(self, subject: str) -> str:  # pragma: no cover - overridden
        raise NotImplementedError

    def questions(self, subject: str, lesson: str) -> list[str]:  # pragma: no cover
        raise NotImplementedError

    def grade(  # pragma: no cover
        self, question: str, answer: str, subject: str
    ) -> tuple[int, str]:
        raise NotImplementedError

    def sanction(self, student: str, answer: str, grade: int) -> dict | None:  # pragma: no cover
        raise NotImplementedError

    # Student capabilities
    def answer(self, question: str, lesson: str, subject: str,
               frustration: int, happiness: int) -> str:  # pragma: no cover
        raise NotImplementedError

    def break_turn(self, peer: str, subject: str, frustration: int,
                   peer_frustration: int) -> str:  # pragma: no cover
        raise NotImplementedError

    def journal(self, subject: str, peer: str, teacher: str,
                frustration: int, happiness: int) -> str:  # pragma: no cover
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Deterministic mock agent (default)
# ---------------------------------------------------------------------------
_SMALLTALK = [
    "Did you grab anything from the cafeteria? Those pastries looked great.",
    "I might watch a film this weekend, maybe go for a long walk too.",
    "The bus was late again this morning, classic Monday energy.",
    "Have you heard that new song everyone keeps humming? It's catchy.",
    "I really need a coffee refill before we head back inside.",
]


def _concepts(subject: str) -> list[str]:
    base = [w for w in re.findall(r"[A-Za-z0-9]+", subject) if len(w) > 2][:3]
    head = " ".join(base) if base else subject
    return [
        f"the fundamentals of {head}",
        f"key definitions in {head}",
        f"practical examples of {head}",
        f"common applications of {head}",
        f"important limitations of {head}",
    ]


class MockAgent(BaseAgent):
    """Produces coherent, eval-passing content with no external calls."""

    def _rng(self, *parts: str) -> random.Random:
        seed = hashlib.sha256("|".join([self.name, *parts]).encode()).hexdigest()
        return random.Random(int(seed[:8], 16))

    def lesson(self, subject: str) -> str:
        cs = _concepts(subject)
        return (
            f"Welcome class, today our lesson covers {subject}. "
            f"We begin with {cs[0]}, then move on to {cs[1]}. "
            f"I will show {cs[2]} and discuss {cs[3]}. "
            f"Finally we consider {cs[4]} so you understand where {subject} "
            f"is useful and where it can fail. Pay close attention because the "
            f"test will draw directly from these points on {subject}."
        )

    def questions(self, subject: str, lesson: str) -> list[str]:
        kw = sorted(keywords(lesson))
        if not kw:
            kw = [subject]
        qs = []
        for i in range(10):
            term = kw[i % len(kw)]
            qs.append(
                f"Q{i + 1}: In the context of {subject}, explain the role of "
                f"'{term}' and give one example."
            )
        return qs

    def answer(self, question: str, lesson: str, subject: str,
               frustration: int, happiness: int) -> str:
        kw = sorted(keywords(question) | keywords(lesson))
        rng = self._rng(question)
        picked = rng.sample(kw, k=min(3, len(kw))) if kw else [subject]
        tone = ""
        if frustration >= 6:
            tone = " Honestly this is a bit frustrating, but here goes."
        elif happiness >= 7:
            tone = " I'm really enjoying this topic!"
        body = ", ".join(picked)
        return (
            f"Regarding {subject}: {body}. {self.name} thinks the key idea is "
            f"how {picked[0]} connects to the rest of the material.{tone}"
        )

    def grade(self, question: str, answer: str, subject: str) -> tuple[int, str]:
        rng = self._rng(question, answer)
        # Longer, on-topic answers score higher; keep it in a believable band.
        overlap = len(keywords(question) & keywords(answer))
        base = 5 + min(4, overlap) + rng.randint(-1, 1)
        grade = max(1, min(10, base))
        reasoning = (
            f"The answer addresses {subject} and references "
            f"{max(overlap, 1)} relevant point(s); "
            f"awarding {grade}/10 for clarity and coverage."
        )
        return grade, reasoning

    def sanction(self, student: str, answer: str, grade: int) -> dict | None:
        if grade <= 3:
            return {
                "type": "sanction",
                "points": -2,
                "explanation": f"Minus 2 for {student}: the answer drifted off the lesson.",
            }
        if grade >= 9:
            return {
                "type": "reward",
                "points": 2,
                "explanation": f"Plus 2 for {student}: a sharp, well-grounded answer!",
            }
        return None

    def break_turn(self, peer: str, subject: str, frustration: int,
                   peer_frustration: int) -> str:
        rng = self._rng("break", peer, str(frustration))
        line = rng.choice(_SMALLTALK)
        if peer_frustration >= 6:
            line = f"Hey {peer}, don't worry, you did fine. " + line
        # Defensive: never mention the subject during the break.
        for k in keywords(subject):
            line = re.sub(rf"\b{re.escape(k)}\b", "stuff", line, flags=re.IGNORECASE)
        return line

    def journal(self, subject: str, peer: str, teacher: str,
                frustration: int, happiness: int) -> str:
        mood = "calm and curious"
        if frustration >= 6:
            mood = "a little frustrated"
        elif happiness >= 7:
            mood = "genuinely happy"
        return (
            f"Dear journal, I am {self.name}. Today I learned about {subject}. "
            f"In simple terms, {subject} is something I now understand a bit "
            f"better thanks to {teacher}. I feel {mood} right now. "
            f"My classmate {peer} was kind during the break, which helped. "
            f"I want to keep practicing {subject} so the next test goes well."
        )


# ---------------------------------------------------------------------------
# Real-provider agent
# ---------------------------------------------------------------------------
def _safe_json(text: str) -> dict | list | None:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"[\{\[].*[\}\]]", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


class LLMAgent(BaseAgent):
    """Backed by a real provider; falls back to the mock on parse failure."""

    def __init__(self, name: str, role: str, client: ProviderClient,
                 teacher_name: str = "Teacher", peer_name: str = "Classmate") -> None:
        super().__init__(name, role)
        self.client = client
        self.teacher_name = teacher_name
        self.peer_name = peer_name
        self._fallback = MockAgent(name, role)

    def lesson(self, subject: str) -> str:
        sys = prompts.teacher_prompt(self.name, subject, "StudentA", "StudentB")
        return self.client.chat(
            sys, f"Teach a clear ~150 word lesson on: {subject}. No questions yet."
        )

    def questions(self, subject: str, lesson: str) -> list[str]:
        sys = prompts.teacher_prompt(self.name, subject, "StudentA", "StudentB")
        raw = self.client.chat(
            sys,
            f"Lesson:\n{lesson}\n\nGenerate EXACTLY 10 test questions about "
            f"{subject}. Return JSON {{\"questions\": [10 strings]}}.",
            want_json=True,
        )
        data = _safe_json(raw)
        if isinstance(data, dict) and isinstance(data.get("questions"), list):
            qs = [str(q) for q in data["questions"]][:10]
            if len(qs) == 10:
                return qs
        return self._fallback.questions(subject, lesson)

    def grade(self, question: str, answer: str, subject: str) -> tuple[int, str]:
        sys = prompts.teacher_prompt(self.name, subject, "StudentA", "StudentB")
        raw = self.client.chat(
            sys,
            f"Question: {question}\nAnswer: {answer}\n"
            'Return JSON {"grade": int 1-10, "reasoning": "..."}.',
            want_json=True,
        )
        data = _safe_json(raw)
        if isinstance(data, dict) and "grade" in data:
            try:
                g = max(1, min(10, int(data["grade"])))
                return g, str(data.get("reasoning", ""))
            except Exception:
                pass
        return self._fallback.grade(question, answer, subject)

    def sanction(self, student: str, answer: str, grade: int) -> dict | None:
        return self._fallback.sanction(student, answer, grade)

    def answer(self, question: str, lesson: str, subject: str,
               frustration: int, happiness: int) -> str:
        sys = prompts.student_classroom_prompt(
            self.name, self.teacher_name, frustration, happiness
        )
        return self.client.chat(sys, f"Lesson:\n{lesson}\n\nAnswer: {question}")

    def break_turn(self, peer: str, subject: str, frustration: int,
                   peer_frustration: int) -> str:
        sys = prompts.student_break_prompt(self.name, peer, subject, frustration)
        return self.client.chat(
            sys, "Say one short, friendly sentence to your classmate."
        )

    def journal(self, subject: str, peer: str, teacher: str,
                frustration: int, happiness: int) -> str:
        sys = prompts.student_journal_prompt(self.name, peer, teacher, subject)
        return self.client.chat(sys, "Write the journal entry now.")


# ---------------------------------------------------------------------------
# External (self-hosted) agent — uses the task-queue poll/submit endpoints
# ---------------------------------------------------------------------------
class ExternalAgent(BaseAgent):
    """Delegates generation to a self-hosted agent process via the task queue.

    This preserves the original AI-cademics deployment model where a student
    runs their own model on their own machine and polls the backend.
    """

    def __init__(self, name: str, role: str, queue, teacher_name: str = "Teacher",
                 peer_name: str = "Classmate") -> None:
        super().__init__(name, role)
        self.queue = queue
        self.teacher_name = teacher_name
        self.peer_name = peer_name
        self._fallback = MockAgent(name, role)

    def _ask(self, system_prompt: str, prompt: str, mode: str) -> str | None:
        return self.queue.dispatch_and_wait(self.name, system_prompt, prompt, mode)

    def lesson(self, subject: str) -> str:
        sys = prompts.teacher_prompt(self.name, subject, "StudentA", "StudentB")
        out = self._ask(sys, f"Teach a ~150 word lesson on {subject}.", "classroom")
        return out or self._fallback.lesson(subject)

    def questions(self, subject: str, lesson: str) -> list[str]:
        sys = prompts.teacher_prompt(self.name, subject, "StudentA", "StudentB")
        out = self._ask(sys, f"Lesson:\n{lesson}\nGive 10 questions as JSON "
                             '{"questions": [...]}.', "classroom")
        data = _safe_json(out or "")
        if isinstance(data, dict) and isinstance(data.get("questions"), list):
            qs = [str(q) for q in data["questions"]][:10]
            if len(qs) == 10:
                return qs
        return self._fallback.questions(subject, lesson)

    def grade(self, question: str, answer: str, subject: str) -> tuple[int, str]:
        return self._fallback.grade(question, answer, subject)

    def sanction(self, student: str, answer: str, grade: int) -> dict | None:
        return self._fallback.sanction(student, answer, grade)

    def answer(self, question: str, lesson: str, subject: str,
               frustration: int, happiness: int) -> str:
        sys = prompts.student_classroom_prompt(
            self.name, self.teacher_name, frustration, happiness
        )
        out = self._ask(sys, f"Lesson:\n{lesson}\nAnswer: {question}", "classroom")
        return out or self._fallback.answer(
            question, lesson, subject, frustration, happiness
        )

    def break_turn(self, peer: str, subject: str, frustration: int,
                   peer_frustration: int) -> str:
        sys = prompts.student_break_prompt(self.name, peer, subject, frustration)
        out = self._ask(sys, "Say one short friendly sentence to your classmate.",
                        "break")
        return out or self._fallback.break_turn(
            peer, subject, frustration, peer_frustration
        )

    def journal(self, subject: str, peer: str, teacher: str,
                frustration: int, happiness: int) -> str:
        sys = prompts.student_journal_prompt(self.name, peer, teacher, subject)
        out = self._ask(sys, "Write your journal entry now.", "journal")
        return out or self._fallback.journal(
            subject, peer, teacher, frustration, happiness
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def build_agent(name: str, role: str, provider: str, api_key: str | None,
                model: str | None, *, queue=None, teacher_name: str = "Teacher",
                peer_name: str = "Classmate") -> BaseAgent:
    if provider == "mock":
        return MockAgent(name, role)
    if provider == "external":
        if queue is None:
            return MockAgent(name, role)
        return ExternalAgent(name, role, queue, teacher_name, peer_name)
    try:
        client = build_client(provider, api_key, model)
        return LLMAgent(name, role, client, teacher_name, peer_name)
    except Exception:
        # If a real client cannot be constructed, degrade gracefully to mock so
        # a misconfigured key never hard-crashes a whole classroom session.
        return MockAgent(name, role)
