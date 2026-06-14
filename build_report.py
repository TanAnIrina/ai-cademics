#!/usr/bin/env python3
"""Generate the AI-cademics change & architecture report as a polished PDF."""
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    ListFlowable,
    ListItem,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

OUT = "docs/AI-cademics_Change_Report.pdf"

# ---- palette (print-friendly take on the app's chalkboard theme) ----
INK = colors.HexColor("#16201b")
SLATE = colors.HexColor("#33413a")
AMBER = colors.HexColor("#b9852a")
AMBER_SOFT = colors.HexColor("#f3e6c8")
TEAL = colors.HexColor("#2c7d77")
TEAL_SOFT = colors.HexColor("#dbeeec")
GREEN = colors.HexColor("#5a8a44")
RED = colors.HexColor("#c25a44")
PAPER = colors.HexColor("#fcfbf7")
CODE_BG = colors.HexColor("#f1f0ea")
LINE = colors.HexColor("#d9d6cc")
MUTE = colors.HexColor("#6a7670")

styles = getSampleStyleSheet()


def S(name, **kw):
    base = kw.pop("parent", styles["Normal"])
    return ParagraphStyle(name, parent=base, **kw)


BODY = S("body", fontName="Helvetica", fontSize=10, leading=15, textColor=INK,
         spaceAfter=7, alignment=TA_LEFT)
LEDE = S("lede", parent=BODY, fontSize=11, leading=16, textColor=SLATE)
H1 = S("h1", fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=INK,
       spaceBefore=6, spaceAfter=4)
H2 = S("h2", fontName="Helvetica-Bold", fontSize=13.5, leading=18, textColor=AMBER,
       spaceBefore=16, spaceAfter=4)
H3 = S("h3", fontName="Helvetica-Bold", fontSize=11, leading=15, textColor=TEAL,
       spaceBefore=10, spaceAfter=3)
EYEBROW = S("eyebrow", fontName="Helvetica-Bold", fontSize=8, leading=11,
            textColor=AMBER, spaceAfter=2)
CODE = S("code", fontName="Courier", fontSize=8.4, leading=12, textColor=INK,
         backColor=CODE_BG, borderColor=LINE, borderWidth=0.5,
         borderPadding=(7, 7, 7, 7), spaceBefore=4, spaceAfter=8, leftIndent=2)
SMALL = S("small", parent=BODY, fontSize=8.6, leading=12, textColor=MUTE)
CELL = S("cell", parent=BODY, fontSize=8.8, leading=12, spaceAfter=0)
CELL_B = S("cellb", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)
CELL_MONO = S("cellmono", parent=CELL, fontName="Courier", fontSize=8.2)
TITLE = S("title", fontName="Helvetica-Bold", fontSize=34, leading=38,
          textColor=colors.white, alignment=TA_LEFT)
SUBTITLE = S("subtitle", fontName="Helvetica", fontSize=13, leading=18,
             textColor=AMBER_SOFT, alignment=TA_LEFT)


class Banner(Flowable):
    """Coloured title banner used on the cover."""

    def __init__(self, width, height=5.6 * cm):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        c.setFillColor(INK)
        c.roundRect(0, 0, self.width, self.height, 10, fill=1, stroke=0)
        c.setFillColor(AMBER)
        c.roundRect(0, self.height - 9, self.width, 9, 4, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 30)
        c.drawString(20, self.height - 52, "AI-cademics")
        c.setFillColor(AMBER_SOFT)
        c.setFont("Helvetica", 13)
        c.drawString(22, self.height - 74, "Change & Architecture Report")
        c.setFillColor(TEAL_SOFT)
        c.setFont("Courier", 9.5)
        c.drawString(22, 22, "v2.0  ·  multi-agent classroom simulation  ·  full-stack rebuild")
        # chalk mark
        c.setFillColor(colors.HexColor("#e7b84e"))
        c.setFont("Helvetica", 40)
        c.drawRightString(self.width - 20, self.height - 56, "\U0001F393")


def chip(text, fill, fg=colors.white):
    t = Table([[Paragraph(f'<font color="#ffffff">{text}</font>'
                          if fg == colors.white else text, CELL)]],
              colWidths=[None])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t


def rule(color=LINE, w=0.8, space=8):
    return HRFlowable(width="100%", thickness=w, color=color,
                      spaceBefore=space, spaceAfter=space)


def code(text):
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe = safe.replace("\n", "<br/>").replace(" ", "&nbsp;")
    return Paragraph(safe, CODE)


def bullets(items, style=BODY):
    return ListFlowable(
        [ListItem(Paragraph(t, style), value="•", leftIndent=12) for t in items],
        bulletType="bullet", start="•", leftIndent=10, spaceBefore=1, spaceAfter=7,
    )


def kv_table(rows, col0=4.0 * cm, header=None):
    data = []
    if header:
        data.append([Paragraph(header[0], CELL_B), Paragraph(header[1], CELL_B)])
    for k, v in rows:
        data.append([Paragraph(k, S("k", parent=CELL, fontName="Helvetica-Bold")),
                     Paragraph(v, CELL)])
    t = Table(data, colWidths=[col0, None])
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), TEAL),
                  ("TOPPADDING", (0, 0), (-1, 0), 6),
                  ("BOTTOMPADDING", (0, 0), (-1, 0), 6)]
    t.setStyle(TableStyle(style))
    return t


def api_table(rows):
    head = [Paragraph("Method", CELL_B), Paragraph("Endpoint", CELL_B),
            Paragraph("Auth", CELL_B), Paragraph("Purpose", CELL_B)]
    data = [head]
    for m, e, a, p in rows:
        mc = {"GET": TEAL, "POST": AMBER}.get(m, SLATE)
        data.append([
            Paragraph(f'<font color="#ffffff"><b>{m}</b></font>',
                      S("m", parent=CELL, backColor=mc, alignment=TA_CENTER)),
            Paragraph(e, CELL_MONO),
            Paragraph(a, S("a", parent=CELL, fontSize=8, textColor=MUTE)),
            Paragraph(p, CELL),
        ])
    t = Table(data, colWidths=[1.5 * cm, 5.4 * cm, 2.0 * cm, None], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PAPER, colors.HexColor("#f5f3ec")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


# ============================ build the story ============================
story = []

# ---- cover ----
story.append(Spacer(1, 1.4 * cm))
story.append(Banner(A4[0] - 4 * cm))
story.append(Spacer(1, 0.9 * cm))
story.append(Paragraph(
    "This report documents the end-to-end rebuild of <b>AI-cademics</b>, a multi-agent "
    "classroom simulation in which an AI teacher and two AI students run timed learning "
    "sprints while human observers watch the discussion, grades, journals and "
    "prompt-compliance evals unfold live. It covers what changed from the original "
    "project, the new architecture, every feature, the data model, the simulation "
    "engine, testing, CI/CD and how to run the system.", LEDE))
story.append(Spacer(1, 0.5 * cm))
meta = kv_table([
    ("Project", "AI-cademics — multi-agent classroom simulation"),
    ("Version", "2.0 (full-stack rebuild)"),
    ("Origin", "github.com/bbiAncah/ai-cademics"),
    ("Backend", "FastAPI · SQLAlchemy 2 · SQLite · pytest · ruff"),
    ("Frontend", "React 18 · React Router 6 · Vite"),
    ("Delivery", "Docker Compose · GitHub Actions CI/CD"),
], col0=3.3 * cm)
story.append(meta)
story.append(NextPageTemplate("body"))
story.append(PageBreak())

# ---- 1. From the original to v2 ----
story.append(Paragraph("1 · From the original to v2", H1))
story.append(rule(AMBER, 1.4))
story.append(Paragraph(
    "The original AI-cademics was a single backend script: a teacher LLM and two student "
    "LLMs (Qwen and Llama) talked to each other in 20-minute sprints with 10-minute breaks, "
    "tracked simple frustration / happiness emotions, and had students write reflective "
    "journals. There was no persistence, no roles, no way to watch, and nothing to verify "
    "that the agents actually followed their prompts.", BODY))
story.append(Paragraph(
    "v2 keeps that simulation at its heart — the prompts, the phase rhythm and the emotion "
    "model all carry over — but rebuilds everything around it into a usable product:", BODY))

comp = [
    ["Area", "Original", "AI-cademics v2"],
    ["Persistence", "None (in-memory only)", "SQLite via SQLAlchemy; full session archive"],
    ["Accounts", "None", "Token login; teacher / student roles; anonymous observers"],
    ["Classrooms", "One hard-coded run", "Many rooms, 3 seats each, auto-start when full"],
    ["Watching", "Console output", "Live web UI: discussion, grades, journals, evals"],
    ["Agents", "Hard-coded Qwen / Llama", "Pluggable providers: mock, Anthropic, OpenAI, Ollama, self-hosted"],
    ["Verification", "None", "Deterministic automated evals of prompt compliance"],
    ["Chat", "None", "Per-classroom observer chatroom"],
    ["History", "None", "Dedicated archive of every finished session"],
    ["Delivery", "Run a script", "Docker Compose, CI tests, optional VPS deploy"],
]
ct = Table(comp, colWidths=[3.0 * cm, 4.8 * cm, None], repeatRows=1)
ct.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), INK),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8.8),
    ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
    ("TEXTCOLOR", (0, 1), (0, -1), SLATE),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PAPER, colors.HexColor("#f5f3ec")]),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
]))
story.append(ct)
story.append(Paragraph(
    "Original sources are preserved verbatim under <font face='Courier'>backend/legacy/</font> "
    "for provenance and are excluded from linting.", SMALL))

# ---- 2. Architecture ----
story.append(Paragraph("2 · Architecture at a glance", H1))
story.append(rule(AMBER, 1.4))
story.append(Paragraph(
    "Two services. A FastAPI backend owns all state and runs each classroom simulation in "
    "its own background thread; a React single-page app renders the live view and polls the "
    "backend over a same-origin <font face='Courier'>/api</font> path (Vite proxies it in "
    "development, nginx in production).", BODY))
story.append(code(
    "Browser (React SPA)\n"
    "      |  HTTP, polling every ~2s\n"
    "      v\n"
    "nginx  --/api-->  FastAPI  --->  SQLite (SQLAlchemy, WAL)\n"
    "                     |\n"
    "                     +-- simulation thread per classroom\n"
    "                     +-- in-memory session store (API keys, never persisted)\n"
    "                     +-- in-memory task queue (self-hosted agents poll/submit)"))
story.append(Paragraph(
    "A deliberate design choice: the default agent provider is a <b>deterministic mock</b>. "
    "The whole simulation therefore runs — and is tested in CI — with no external API keys "
    "or GPU. Real providers (Anthropic, OpenAI, Ollama) and a self-hosted agent runtime plug "
    "in behind the same interface.", BODY))

story.append(Paragraph("Project layout", H3))
story.append(code(
    "ai-cademics/\n"
    "  backend/\n"
    "    app/\n"
    "      main.py            FastAPI app, CORS, startup seed\n"
    "      config.py          env-driven settings\n"
    "      database.py        SQLAlchemy engine (SQLite, WAL)\n"
    "      models.py          ORM tables\n"
    "      schemas.py         Pydantic request/response models\n"
    "      security.py        in-memory session store\n"
    "      deps.py            auth dependencies\n"
    "      routers/           auth, classrooms, chat, history, agent\n"
    "      engine/            simulation: agents, prompts, providers,\n"
    "                         evals, queue, run_session()\n"
    "    agent_client.py      standalone self-hosted agent\n"
    "    tests/               38 pytest tests\n"
    "  frontend/\n"
    "    src/  pages/  components/  api.js  auth.jsx  usePolling.js\n"
    "  .github/workflows/     ci.yml, deploy.yml\n"
    "  docker-compose.yml  Makefile  docs/"))

# ---- 3. Roles & access ----
story.append(PageBreak())
story.append(Paragraph("3 · Roles, login & access control", H1))
story.append(rule(AMBER, 1.4))
story.append(Paragraph(
    "Login takes a display name, a role and a model provider. The backend creates a user "
    "record and returns an opaque session token. If a provider needs an API key, that key is "
    "kept only in an in-memory session store keyed by the token — it is never written to the "
    "database or disk, and it disappears when the user signs out or the server restarts.", BODY))
story.append(kv_table([
    ("Observer (no login)", "Browse classrooms and history, watch live sessions, use the observer "
        "chat. Cannot take a seat or change anything."),
    ("Student", "Everything an observer can do, plus claim one of the two student seats in a "
        "waiting room."),
    ("Teacher", "Can additionally create classrooms and claim the teacher seat, which sets the "
        "subject and the sprint / break / count configuration."),
], col0=4.2 * cm, header=("Role", "What they can do")))
story.append(Paragraph(
    "A user can only occupy one active classroom at a time, and a room has exactly one teacher "
    "slot plus two student slots enforced by a unique constraint in the database.", SMALL))

# ---- 4. The classroom lifecycle ----
story.append(Paragraph("4 · The classroom lifecycle", H1))
story.append(rule(AMBER, 1.4))
story.append(Paragraph(
    "A classroom moves through three states. It opens <b>waiting</b>; as soon as all three "
    "seats fill it flips to <b>running</b> and the simulation thread starts; when the last "
    "sprint finishes it becomes <b>finished</b> and is snapshotted into the archive.", BODY))
story.append(code(
    "waiting  --(3rd seat filled)-->  running  --(last sprint done)-->  finished\n"
    "   ^ teacher sets subject & timing                     |\n"
    "   ^ students/teacher may leave                        +--> archived to /api/history"))
story.append(Paragraph("Each sprint runs five phases in order:", BODY))
story.append(kv_table([
    ("Lesson", "The teacher explains the subject, referencing concrete concepts."),
    ("Test", "The teacher poses exactly 10 questions tied to the lesson; each student answers."),
    ("Grading", "The teacher grades each student 1–10 with written reasoning; emotions update, "
        "and a creative sanction or reward may be issued."),
    ("Break", "Students chat off-topic and comfort each other — they must not mention the subject."),
    ("Journal", "Each student writes a first-person reflection of under 1000 words."),
], col0=2.6 * cm, header=("Phase", "What happens")))
story.append(Paragraph(
    "Phase delays are compressed by a configurable <font face='Courier'>sim_phase_seconds</font> "
    "so a full session can complete in seconds for a demo or in realistic time in production.", SMALL))

# ---- 5. Feature checklist ----
story.append(PageBreak())
story.append(Paragraph("5 · Requirements, point by point", H1))
story.append(rule(AMBER, 1.4))
story.append(Paragraph("Every requested capability and where it lives:", BODY))
req = [
    ("Token & API login for agents", "auth router + in-memory session store"),
    ("Classrooms with 1 teacher + 2 students", "unique slot constraint; auto-start on full"),
    ("Observer view of rooms & progress", "classrooms list + live view, open to anonymous users"),
    ("Live discussion, grades, journals", "GET /classrooms/{id}/live, polled by the UI"),
    ("Pick which room to join with your key", "join endpoint; provider/key chosen at login"),
    ("Login as student or teacher; assign role", "role set at login, enforced on every mutation"),
    ("Not logged in = observer only", "optional vs required session dependencies"),
    ("Teacher sets subject & sprint config", "teacher join/configure with TeacherConfig"),
    ("Show total time vs number of sessions", "GET /estimate + custom SVG chart in the UI"),
    ("Finished rooms saved to history", "archive table + /api/history endpoints"),
    ("Per-classroom observer chatroom", "chat router, scoped strictly per room"),
    ("Automated agent evals", "deterministic checks in engine/evals.py"),
    ("Friendlier UI", "React SPA, chalkboard theme, live polling"),
    ("CI/CD pipeline", "GitHub Actions: lint, test, build, optional deploy"),
    ("Document every step (this PDF)", "generated and shipped in the zip"),
]
data = [[Paragraph("✓", S("ok", parent=CELL, textColor=GREEN, fontName="Helvetica-Bold",
                          alignment=TA_CENTER)),
         Paragraph(r, CELL), Paragraph(w, S("w", parent=CELL, textColor=MUTE))]
        for r, w in req]
rt = Table(data, colWidths=[0.7 * cm, 7.2 * cm, None])
rt.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [PAPER, colors.HexColor("#f5f3ec")]),
    ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
]))
story.append(rt)

# ---- 6. Simulation engine ----
story.append(PageBreak())
story.append(Paragraph("6 · The simulation engine", H1))
story.append(rule(AMBER, 1.4))
story.append(Paragraph(
    "<font face='Courier'>run_session()</font> drives one classroom. It builds the three agents "
    "from each member's chosen provider, then loops over the sprints and phases, writing every "
    "message, grade, sanction and journal to the database as it goes and recording eval results "
    "alongside them. Emotions evolve from grades and sanctions: a low grade raises frustration, "
    "a high one raises happiness, and during the break a happier peer can comfort a frustrated "
    "one. When the loop ends, the whole session is serialised into the archive.", BODY))

story.append(Paragraph("Agent providers", H3))
story.append(kv_table([
    ("mock (default)", "Deterministic, seedable agent. Needs no network; designed so its output "
        "satisfies every prompt rule — this is what CI runs."),
    ("anthropic / openai", "Calls the respective chat API with the user's key and chosen model; "
        "JSON-structured phases fall back to the mock on a parse error."),
    ("ollama", "Talks to a local Ollama server for fully offline real-model runs."),
    ("self-hosted", "The backend enqueues tasks; the user's own process polls and submits answers."),
], col0=3.6 * cm))

story.append(Paragraph("Automated evals", H3))
story.append(Paragraph(
    "Evals are pure functions over the agents' output, so they return identical verdicts in CI "
    "and in production. They are the project's answer to “did the agent actually respect its "
    "prompt?” and cover:", BODY))
story.append(bullets([
    "<b>question_count</b> — the teacher asked exactly ten questions.",
    "<b>question_relevance</b> — at least 60% of questions share vocabulary with the lesson.",
    "<b>answer_on_topic</b> — a student's answer overlaps the question / lesson.",
    "<b>grade_validity</b> — every grade is an integer in 1–10 with written reasoning.",
    "<b>break_off_topic</b> — no subject term leaked into the break chat.",
    "<b>journal_word_limit</b> &amp; <b>journal_first_person</b> — under 1000 words, written in "
    "the first person, mentioning the student's own name.",
]))

# ---- 7. Data model ----
story.append(PageBreak())
story.append(Paragraph("7 · Data model", H1))
story.append(rule(AMBER, 1.4))
story.append(kv_table([
    ("User", "Display name, role, provider and model (no secrets)."),
    ("Classroom", "Name, status, subject, sprint/break minutes, number of sprints, current "
        "sprint and phase."),
    ("Membership", "Links a user to a classroom slot, with per-seat frustration / happiness."),
    ("Message", "One line of discussion: sprint, phase, sender, role, content."),
    ("Grade", "Per student per sprint: the grade and the teacher's reasoning."),
    ("Sanction", "Optional creative sanction or reward with a point delta."),
    ("Journal", "A student's reflection with its word count."),
    ("EvalResult", "One eval check: scope, name, pass/fail, score and detail."),
    ("ChatMessage", "An observer chat line scoped to a classroom."),
    ("Archive", "A finished session serialised to JSON for the history view."),
], col0=3.1 * cm, header=("Table", "Holds")))

# ---- 8. API ----
story.append(Paragraph("8 · HTTP API", H1))
story.append(rule(AMBER, 1.4))
story.append(api_table([
    ("POST", "/api/auth/login", "none", "Create a user + session, return a token"),
    ("GET", "/api/auth/me", "token", "Current user"),
    ("POST", "/api/auth/logout", "token", "Revoke the session"),
    ("GET", "/api/classrooms", "none", "List active rooms (observer-friendly)"),
    ("POST", "/api/classrooms", "teacher", "Create a classroom"),
    ("GET", "/api/classrooms/{id}", "none", "One classroom's state"),
    ("GET", "/api/classrooms/estimate", "none", "Total time per sprint count (chart)"),
    ("POST", "/api/classrooms/{id}/join", "token", "Take a seat (teacher sets config)"),
    ("POST", "/api/classrooms/{id}/configure", "teacher", "Re-configure before start"),
    ("POST", "/api/classrooms/{id}/leave", "token", "Leave a waiting room"),
    ("GET", "/api/classrooms/{id}/live", "none", "Discussion + grades + journals + evals"),
    ("GET", "/api/classrooms/{id}/chat", "none", "Read the observer chat"),
    ("POST", "/api/classrooms/{id}/chat", "nickname", "Post to the observer chat"),
    ("GET", "/api/history", "none", "List archived sessions"),
    ("GET", "/api/history/{id}", "none", "Full archived session"),
    ("GET", "/api/agent/poll", "token", "Self-hosted agent fetches a task"),
    ("POST", "/api/agent/submit", "token", "Self-hosted agent returns an answer"),
]))

# ---- 9. Testing & CI ----
story.append(PageBreak())
story.append(Paragraph("9 · Testing & continuous integration", H1))
story.append(rule(AMBER, 1.4))
story.append(Paragraph(
    "The backend ships with <b>38 pytest tests</b> that all pass, and the code is clean under "
    "<b>ruff</b>. Because the default agent is deterministic, the suite exercises a complete "
    "simulation end-to-end without any external service:", BODY))
story.append(bullets([
    "<b>Auth</b> — login, role assignment, token revocation, validation.",
    "<b>Classrooms</b> — observer vs authed access, role enforcement, seat logic, "
    "the one-room-at-a-time rule, and the time-estimate maths.",
    "<b>Simulation</b> — a full session runs to completion and produces the expected number "
    "of grades and journals, then archives correctly.",
    "<b>Evals</b> — each check is unit-tested on both a passing and a failing input.",
    "<b>Chat &amp; history</b> — per-room isolation, pagination, and the archived chat snapshot.",
]))
story.append(Paragraph("Pipelines (GitHub Actions)", H3))
story.append(kv_table([
    ("ci.yml", "On every push and PR: install, ruff, pytest with coverage for the backend; "
        "npm ci and a production build for the frontend, uploaded as an artifact."),
    ("deploy.yml", "On a version tag or manual run: build both Docker images with layer "
        "caching. An optional SSH step deploys to a VPS, gated on a repo variable so it stays "
        "green before any server exists."),
], col0=2.6 * cm))

# ---- 10. Running it ----
story.append(Paragraph("10 · Running it", H1))
story.append(rule(AMBER, 1.4))
story.append(Paragraph("Local development", H3))
story.append(code(
    "# backend  (http://localhost:8000, docs at /docs)\n"
    "cd backend && pip install -r requirements-dev.txt\n"
    "uvicorn app.main:app --reload\n\n"
    "# frontend (http://localhost:5173)\n"
    "cd frontend && npm install && npm run dev"))
story.append(Paragraph("Everything at once with Docker", H3))
story.append(code(
    "docker compose up --build      # then open http://localhost:8080\n"
    "# or simply:  make up"))
story.append(Paragraph("Self-hosted agent", H3))
story.append(code(
    "python backend/agent_client.py --role student --name Ada \\\n"
    "    --classroom 1 --model llama3"))
story.append(Paragraph(
    "A Makefile wraps the common tasks — <font face='Courier'>make install / test / lint / "
    "build / up / down</font>. Configuration is entirely environment-driven (see "
    "<font face='Courier'>.env.example</font>): database location, the compressed phase delay, "
    "how many demo rooms to seed, CORS origins and the teacher defaults.", BODY))
story.append(Spacer(1, 6))
story.append(rule(AMBER, 1.2))
story.append(Paragraph(
    "AI-cademics v2 — a small simulation grown into a watchable, testable, deployable product. "
    "The classroom still runs the same lesson; now anyone can pull up a chair and watch.", SMALL))


# ============================ frame / page chrome ============================
def cover_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.restoreState()


def body_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    # header band
    canvas.setFillColor(INK)
    canvas.rect(0, A4[1] - 1.15 * cm, A4[0], 1.15 * cm, fill=1, stroke=0)
    canvas.setFillColor(AMBER)
    canvas.rect(0, A4[1] - 1.2 * cm, A4[0], 0.05 * cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(2 * cm, A4[1] - 0.78 * cm, "AI-cademics")
    canvas.setFillColor(AMBER_SOFT)
    canvas.setFont("Helvetica", 8.5)
    canvas.drawString(3.9 * cm, A4[1] - 0.78 * cm, "Change & Architecture Report")
    # footer
    canvas.setFillColor(MUTE)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(2 * cm, 1.05 * cm, "Multi-agent classroom simulation · v2.0")
    canvas.drawRightString(A4[0] - 2 * cm, 1.05 * cm, f"Page {doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, 1.35 * cm, A4[0] - 2 * cm, 1.35 * cm)
    canvas.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4,
                      leftMargin=2 * cm, rightMargin=2 * cm,
                      topMargin=2 * cm, bottomMargin=2 * cm,
                      title="AI-cademics — Change & Architecture Report",
                      author="AI-cademics")
cover_frame = Frame(2 * cm, 2 * cm, A4[0] - 4 * cm, A4[1] - 4 * cm, id="cover")
body_frame = Frame(2 * cm, 1.7 * cm, A4[0] - 4 * cm, A4[1] - 3.6 * cm, id="body")
doc.addPageTemplates([
    PageTemplate(id="cover", frames=[cover_frame], onPage=cover_bg),
    PageTemplate(id="body", frames=[body_frame], onPage=body_bg),
])
doc.build(story)
print("wrote", OUT)
