"""Agent abstraction.

The simulation engine talks to *agents*, not raw providers. An agent knows how
to produce each kind of turn (lesson, questions, answer, grade, break chat,
journal, teacher journal). Three implementations exist:

* ``MockAgent``      - deterministic, dependency-free, used by default and in CI.
* ``LLMAgent``       - wraps a real provider client (Anthropic/OpenAI/Ollama).
* ``ExternalAgent``  - delegates to a self-hosted agent that polls the backend
                       (the original AI-cademics runtime), via a task queue.

All agents share one interface so the engine never branches on type. Student
turns receive a full ``emotions`` dict and an optional ``memory`` string (their
own history from earlier sprints); break turns also receive ``peer_last`` (what
the classmate just said) so replies actually acknowledge each other.
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

    def teacher_journal(self, subject: str, student_names: list[str], class_summary: str,
                        emotions: dict, memory: str | None = None) -> str:  # pragma: no cover
        raise NotImplementedError

    # Student capabilities
    def answer(self, question: str, lesson: str, subject: str,
               emotions: dict, memory: str | None = None) -> str:  # pragma: no cover
        raise NotImplementedError

    def break_turn(self, peer: str, teacher: str, subject: str, emotions: dict,
                   peer_last: str | None, memory: str | None = None) -> str:  # pragma: no cover
        raise NotImplementedError

    def journal(self, subject: str, peer: str, teacher: str,
                emotions: dict, memory: str | None = None) -> str:  # pragma: no cover
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


def _dominant_emotion(emotions: dict) -> str:
    """Return a short phrase for the strongest feeling, for mock tone."""
    if not emotions:
        return "calm"
    # Negative feelings win ties so distress is never hidden.
    order = ["frustration", "anxiety", "boredom", "confidence", "curiosity", "happiness"]
    best = max(order, key=lambda k: (emotions.get(k, 0), -order.index(k)))
    if emotions.get(best, 0) < 4:
        return "calm"
    return best


def _mask_subject(text: str, subject: str) -> str:
    for k in keywords(subject):
        text = re.sub(rf"\b{re.escape(k)}\b", "stuff", text, flags=re.IGNORECASE)
    return text


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
               emotions: dict, memory: str | None = None) -> str:
        kw = sorted(keywords(question) | keywords(lesson))
        rng = self._rng(question)
        picked = rng.sample(kw, k=min(3, len(kw))) if kw else [subject]
        mood = _dominant_emotion(emotions)
        tone = {
            "frustration": " Honestly this is a bit frustrating, but here goes.",
            "anxiety": " I'm not totally sure, I hope this is right…",
            "boredom": " Anyway. Quick version:",
            "confidence": " I've got this.",
            "curiosity": " This part actually makes me wonder about more.",
            "happiness": " I'm really enjoying this topic!",
        }.get(mood, "")
        recall = ""
        if memory and rng.random() < 0.6:
            recall = " Building on what stuck with me last time, "
        body = ", ".join(picked)
        return (
            f"Regarding {subject}: {recall}{body}. {self.name} thinks the key idea "
            f"is how {picked[0]} connects to the rest of the material.{tone}"
        )

    def grade(self, question: str, answer: str, subject: str) -> tuple[int, str]:
        rng = self._rng(question, answer)
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

    def teacher_journal(self, subject: str, student_names: list[str], class_summary: str,
                        emotions: dict, memory: str | None = None) -> str:
        mood = _dominant_emotion(emotions)
        feel = {
            "frustration": "a little exasperated",
            "anxiety": "slightly worried about their progress",
            "boredom": "wishing for sharper engagement",
            "confidence": "confident in my plan",
            "curiosity": "curious how they'll grow",
            "happiness": "pleased with the room",
        }.get(mood, "steady")
        recall = ""
        if memory:
            recall = " Compared with my earlier note today, the rhythm is settling. "
        roster = ", ".join(student_names) if student_names else "my students"
        return (
            f"Teacher's journal — I am {self.name}. Today I taught {subject} to "
            f"{roster}. {class_summary} As their teacher I feel {feel}.{recall}"
            f"Next sprint I want to ask sharper questions and check that {roster} "
            f"stay with me on the harder parts of {subject}."
        )

    def break_turn(self, peer: str, teacher: str, subject: str, emotions: dict,
                   peer_last: str | None, memory: str | None = None) -> str:
        rng = self._rng("break", peer, str(emotions.get("frustration", 0)),
                        peer_last or "")
        opener = ""
        if peer_last:
            # Echo the substantive tail of the peer's line (not its opener), so
            # replies read as genuine acknowledgement rather than recursive echo.
            words = _mask_subject(peer_last, subject).split()
            snippet = " ".join(words[-7:]).rstrip(".,!?")
            opener = rng.choice([
                f"Oh, \"{snippet}\" — same here, honestly. ",
                f"Ha, {peer}, you're right about that. ",
                f"Yeah, I get what you mean about {snippet}. ",
                f"Right?? {snippet}... so true. ",
            ])
        line = rng.choice(_SMALLTALK)
        if emotions.get("frustration", 0) >= 6:
            opener = f"Hey {peer}, don't stress, you did fine. " + opener
        return _mask_subject(opener + line, subject)

    def journal(self, subject: str, peer: str, teacher: str,
                emotions: dict, memory: str | None = None) -> str:
        mood = _dominant_emotion(emotions)
        mood_word = {
            "frustration": "a little frustrated",
            "anxiety": "anxious about the next test",
            "boredom": "a bit restless",
            "confidence": "quietly confident",
            "curiosity": "curious to learn more",
            "happiness": "genuinely happy",
        }.get(mood, "calm and curious")
        recall = ""
        if memory:
            recall = (
                " Looking back at how I felt earlier today, my mood has shifted, "
                "and I can see myself changing across these sprints. "
            )
        return (
            f"Dear journal, I am {self.name}. Today I learned about {subject}. "
            f"In simple terms, {subject} is something I now understand a bit "
            f"better thanks to my teacher {teacher}. I feel {mood_word} right now."
            f"{recall} My classmate {peer} (not the teacher) was kind during the "
            f"break, which helped. I want to keep practising {subject} so the next "
            f"test goes well."
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

    def teacher_journal(self, subject: str, student_names: list[str], class_summary: str,
                        emotions: dict, memory: str | None = None) -> str:
        sys = prompts.teacher_journal_prompt(
            self.name, subject, student_names, class_summary, emotions, memory
        )
        try:
            return self.client.chat(sys, "Write your teaching journal entry now.")
        except Exception:
            return self._fallback.teacher_journal(subject, student_names, class_summary,
                                                  emotions, memory)

    def answer(self, question: str, lesson: str, subject: str,
               emotions: dict, memory: str | None = None) -> str:
        sys = prompts.student_classroom_prompt(
            self.name, self.teacher_name, self.peer_name, emotions, memory
        )
        try:
            return self.client.chat(sys, f"Lesson:\n{lesson}\n\nAnswer: {question}")
        except Exception:
            return self._fallback.answer(question, lesson, subject, emotions, memory)

    def break_turn(self, peer: str, teacher: str, subject: str, emotions: dict,
                   peer_last: str | None, memory: str | None = None) -> str:
        sys = prompts.student_break_prompt(
            self.name, peer, teacher, subject, emotions, peer_last, memory
        )
        try:
            return self.client.chat(sys, "Reply to your classmate now.")
        except Exception:
            return self._fallback.break_turn(peer, teacher, subject, emotions,
                                             peer_last, memory)

    def journal(self, subject: str, peer: str, teacher: str,
                emotions: dict, memory: str | None = None) -> str:
        sys = prompts.student_journal_prompt(
            self.name, peer, teacher, subject, emotions, memory
        )
        try:
            return self.client.chat(sys, "Write the journal entry now.")
        except Exception:
            return self._fallback.journal(subject, peer, teacher, emotions, memory)


# ---------------------------------------------------------------------------
# External (self-hosted) agent — uses the task-queue poll/submit endpoints
# ---------------------------------------------------------------------------
class ExternalAgent(BaseAgent):
    """Delegates generation to a self-hosted agent process via the task queue."""

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

    def teacher_journal(self, subject: str, student_names: list[str], class_summary: str,
                        emotions: dict, memory: str | None = None) -> str:
        sys = prompts.teacher_journal_prompt(
            self.name, subject, student_names, class_summary, emotions, memory
        )
        out = self._ask(sys, "Write your teaching journal entry now.", "journal")
        return out or self._fallback.teacher_journal(subject, student_names, class_summary,
                                                     emotions, memory)

    def answer(self, question: str, lesson: str, subject: str,
               emotions: dict, memory: str | None = None) -> str:
        sys = prompts.student_classroom_prompt(
            self.name, self.teacher_name, self.peer_name, emotions, memory
        )
        out = self._ask(sys, f"Lesson:\n{lesson}\nAnswer: {question}", "classroom")
        return out or self._fallback.answer(question, lesson, subject, emotions, memory)

    def break_turn(self, peer: str, teacher: str, subject: str, emotions: dict,
                   peer_last: str | None, memory: str | None = None) -> str:
        sys = prompts.student_break_prompt(
            self.name, peer, teacher, subject, emotions, peer_last, memory
        )
        out = self._ask(sys, "Reply to your classmate now.", "break")
        return out or self._fallback.break_turn(peer, teacher, subject, emotions,
                                                peer_last, memory)

    def journal(self, subject: str, peer: str, teacher: str,
                emotions: dict, memory: str | None = None) -> str:
        sys = prompts.student_journal_prompt(
            self.name, peer, teacher, subject, emotions, memory
        )
        out = self._ask(sys, "Write your journal entry now.", "journal")
        return out or self._fallback.journal(subject, peer, teacher, emotions, memory)


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
        return MockAgent(name, role)
