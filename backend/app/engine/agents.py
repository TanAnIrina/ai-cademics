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
    def teach(self, subject: str, kind: str, index: int, total: int,
              prior: str) -> str:  # pragma: no cover - overridden
        """One teaching turn. kind is "intro", "segment" or "recap"."""
        raise NotImplementedError

    def address_question(self, subject: str, question: str,
                         segment: str) -> str:  # pragma: no cover
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
    def ask_in_lesson(self, subject: str, segment: str, emotions: dict,
                      memory: str | None = None) -> str:  # pragma: no cover
        raise NotImplementedError

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


_QUESTION_FORMS = [
    "Define '{t}' as it is used in {s}.",
    "Give a concrete example of '{t}' in {s}.",
    "True or false: '{t}' is central to {s}. Justify your answer.",
    "Compare '{t}' with '{t2}' in the context of {s}.",
    "Why does '{t}' matter when working with {s}?",
    "How would you apply '{t}' to solve a problem in {s}?",
    "Describe a scenario in {s} where '{t}' is essential.",
    "What is one limitation or pitfall of '{t}' in {s}?",
    "In one sentence, summarise the role of '{t}' in {s}.",
    "Complete the idea: in {s}, '{t}' is mainly used to ____.",
]


def _diverse_questions(subject: str, lesson: str) -> list[str]:
    """Ten test questions of varied formats, grounded in the lesson vocabulary."""
    kw = sorted(keywords(lesson)) or [subject]
    out = []
    for i in range(10):
        t = kw[i % len(kw)]
        t2 = kw[(i + 1) % len(kw)]
        out.append(f"Q{i + 1}: " + _QUESTION_FORMS[i % len(_QUESTION_FORMS)].format(
            t=t, t2=t2, s=subject))
    return out


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

    def teach(self, subject: str, kind: str, index: int, total: int,
              prior: str) -> str:
        cs = _concepts(subject)
        if kind == "intro":
            agenda = "; ".join(cs[: min(total, len(cs))])
            return (
                f"Alright class, settle in — today we study {subject}. We'll work "
                f"through {total} parts, step by step: {agenda}. Stop me with questions "
                f"as we go; the test at the end builds on everything we cover."
            )
        if kind == "recap":
            return (
                f"Let's recap {subject}. We moved one idea at a time from the basics "
                f"through to applications and limitations. Make sure you can connect "
                f"each part to the next — the test draws on the whole discussion."
            )
        concept = cs[(index - 1) % len(cs)]
        build = ("Building on what we just covered, " if index > 1
                 else "Let's start with the foundation. ")
        return (
            f"Part {index} of {total} on {subject}: {build}{concept}. The key thing "
            f"to grasp is how this fits with the rest of {subject}, and where it shows "
            f"up in practice. Think about that as we continue."
        )

    def address_question(self, subject: str, question: str, segment: str) -> str:
        kw = sorted(keywords(question) | keywords(segment))
        rng = self._rng("addr", question)
        term = rng.choice(kw) if kw else subject
        return (
            f"Good question. In {subject}, '{term}' works by tying the current idea to "
            f"the bigger picture. For instance, picture a simple case where '{term}' is "
            f"exactly what you need — that's the intuition to carry into the test."
        )

    def questions(self, subject: str, lesson: str) -> list[str]:
        return _diverse_questions(subject, lesson)

    def ask_in_lesson(self, subject: str, segment: str, emotions: dict,
                      memory: str | None = None) -> str:
        rng = self._rng("ask", segment)
        kw = sorted(keywords(segment) | keywords(subject))
        term = rng.choice(kw) if kw else subject
        opener = {
            "anxiety": "Sorry, I'm a little lost — ",
            "boredom": "Hm, ",
            "confidence": "Quick one — ",
            "curiosity": "Ooh, ",
            "frustration": "Wait, ",
            "happiness": "This is interesting — ",
        }.get(_dominant_emotion(emotions), "")
        forms = [
            f"{opener}could you explain '{term}' a bit more?",
            f"{opener}how does '{term}' connect to what we did before?",
            f"{opener}can you give an example of '{term}'?",
            f"{opener}why does '{term}' matter for {subject}?",
        ]
        return rng.choice(forms)

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

    def teach(self, subject: str, kind: str, index: int, total: int,
              prior: str) -> str:
        sys = prompts.teacher_prompt(self.name, subject, "StudentA", "StudentB")
        if kind == "intro":
            ask = (f"Open your lesson on {subject}: greet the class and outline the "
                   f"{total} parts you'll teach, step by step. ~60 words. No questions yet.")
        elif kind == "recap":
            ask = (f"Give a short closing recap (~60 words) of your lesson on {subject}. "
                   f"Discussion so far:\n{prior[-1500:]}")
        else:
            ask = (f"Teach part {index} of {total} of your lesson on {subject}, building "
                   f"on what came before. Cover ONE new sub-topic clearly in ~70 words. "
                   f"Discussion so far:\n{prior[-1500:]}")
        try:
            return self.client.chat(sys, ask)
        except Exception:
            return self._fallback.teach(subject, kind, index, total, prior)

    def address_question(self, subject: str, question: str, segment: str) -> str:
        sys = prompts.teacher_prompt(self.name, subject, "StudentA", "StudentB")
        try:
            return self.client.chat(
                sys, f"A student asked: {question}\nYou were teaching: {segment}\n"
                     f"Answer them clearly and briefly (~60 words), then invite the class on.")
        except Exception:
            return self._fallback.address_question(subject, question, segment)

    def questions(self, subject: str, lesson: str) -> list[str]:
        sys = prompts.teacher_prompt(self.name, subject, "StudentA", "StudentB")
        raw = self.client.chat(
            sys,
            f"Lesson discussion:\n{lesson[-2500:]}\n\nGenerate EXACTLY 10 test "
            f"questions about {subject}, drawn from the lesson, using DIVERSE formats "
            f"(definition, example, true/false, compare, why, application, scenario, "
            f"limitation, one-sentence summary, fill-in-the-blank). "
            f'Return JSON {{"questions": [10 strings]}}.',
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

    def ask_in_lesson(self, subject: str, segment: str, emotions: dict,
                      memory: str | None = None) -> str:
        sys = prompts.student_classroom_prompt(
            self.name, self.teacher_name, self.peer_name, emotions, memory
        )
        try:
            return self.client.chat(
                sys, f"Your teacher just said:\n{segment}\n\nAsk ONE short, relevant "
                     f"question, or make a brief comment, about it.")
        except Exception:
            return self._fallback.ask_in_lesson(subject, segment, emotions, memory)

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

    def teach(self, subject: str, kind: str, index: int, total: int,
              prior: str) -> str:
        sys = prompts.teacher_prompt(self.name, subject, "StudentA", "StudentB")
        if kind == "intro":
            ask = f"Open your lesson on {subject}: outline the {total} parts you'll teach."
        elif kind == "recap":
            ask = f"Give a short recap of your lesson on {subject}.\nSo far:\n{prior[-1500:]}"
        else:
            ask = (f"Teach part {index}/{total} of {subject}, one new sub-topic, building "
                   f"on:\n{prior[-1500:]}")
        out = self._ask(sys, ask, "classroom")
        return out or self._fallback.teach(subject, kind, index, total, prior)

    def address_question(self, subject: str, question: str, segment: str) -> str:
        sys = prompts.teacher_prompt(self.name, subject, "StudentA", "StudentB")
        out = self._ask(sys, f"A student asked: {question}\nYou were teaching: {segment}\n"
                             f"Answer briefly.", "classroom")
        return out or self._fallback.address_question(subject, question, segment)

    def questions(self, subject: str, lesson: str) -> list[str]:
        sys = prompts.teacher_prompt(self.name, subject, "StudentA", "StudentB")
        out = self._ask(sys, f"Lesson:\n{lesson}\nGive 10 DIVERSE test questions "
                             "(definition, example, true/false, compare, why, application, "
                             "scenario, limitation, summary, fill-in) as JSON "
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

    def ask_in_lesson(self, subject: str, segment: str, emotions: dict,
                      memory: str | None = None) -> str:
        sys = prompts.student_classroom_prompt(
            self.name, self.teacher_name, self.peer_name, emotions, memory
        )
        out = self._ask(sys, f"Teacher said:\n{segment}\nAsk one short question about it.",
                        "classroom")
        return out or self._fallback.ask_in_lesson(subject, segment, emotions, memory)

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
