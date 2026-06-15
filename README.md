# 🎓 AI-cademics

**A multi-agent classroom simulation you can watch live.**

An AI **teacher** and two AI **students** run timed learning sprints — lesson →
test → grading → break → journal — while human **observers** watch the discussion,
grades, journals and prompt-compliance evals unfold in real time. Teachers
configure the subject and pacing; students take a seat; everyone else watches and
chats.

> 📄 A complete write-up of the architecture and every change lives in
> [`docs/AI-cademics_Change_Report.pdf`](docs/AI-cademics_Change_Report.pdf).

## 📋 Product Backlog

**32 user stories pe 8 epics**, prioritizate MoSCoW. Sprinturile 1–3 au livrat produsul de bază (v2); Sprintul 4 iterația de rafinare (v2.1); Sprintul 5 scalarea și exportul (v2.2); Sprintul 6 lecția interactivă în timp real (v2.3). Criteriile de acceptare complete și mapările la cod/teste sunt în [`docs/BACKLOG.md`](docs/BACKLOG.md).

**Epics**
1. **Acces și gestionarea profilului** — login, roluri (profesor / student / observator), profil.
2. **Sesiunea de clasă și interacțiunea** — predare → test → notare, configurare sprint, pornire automată.
3. **Emoții, pauze și acțiuni disciplinare** — jurnal, sancțiuni/recompense, pauză cu consolare.
4. **Analiză și urmărirea performanței** — note + justificări, emoții live, rezultate evals.
5. **Observatori și arhivă** — chat de observator, istoric și arhivă completă.
6. **Iterația v2.1** — dialog responsiv în pauză, memorie între sprinturi, emoții extinse, statistici, stop & delete, jurnal de profesor.
7. **Iterația v2.2** — până la 5 studenți per sală, programarea sesiunilor, rating de lecție, export PDF, statistici păstrate în istoric.
8. **Iterația v2.3** — lecție ca discuție secvențială desfășurată în timp real, test diversificat, alegerea subiectului înainte de fiecare sprint.

| ID | User story | Epic | MoSCoW | Pts | Sprint | Status |
|----|------------|------|--------|-----|--------|--------|
| US 4 | Predare, testare și evaluare | 2 | Must | 8 | 1 | ✅ |
| US 6 | Pornire automată a clasei | 2 | Must | 5 | 1 | ✅ |
| US 7 | Jurnal de învățare | 3 | Must | 3 | 1 | ✅ |
| US 9 | Pauză + consolare reciprocă | 3 | Must | 5 | 1 | ✅ |
| US 1 | Login & săli active | 1 | Must | 5 | 2 | ✅ |
| US 2 | Roluri și permisiuni | 1 | Must | 5 | 2 | ✅ |
| US 12 | Evals automate vizibile | 4 | Must | 5 | 2 | ✅ |
| US 5 | Configurare sprint de profesor | 2 | Should | 3 | 2 | ✅ |
| US 10 | Note + justificări vizibile | 4 | Should | 3 | 3 | ✅ |
| US 11 | Emoții live per loc | 4 | Should | 3 | 3 | ✅ |
| US 14 | Istoric & arhivă | 5 | Should | 5 | 3 | ✅ |
| US 13 | Chat observatori | 5 | Could | 2 | 3 | ✅ |
| US 3 | Profil cu nume | 1 | Could | 1 | 2 | ✅ |
| US 8 | Sancțiuni & recompense | 3 | Could | 3 | 3 | ✅ |
| US 21 | Claritatea rolurilor (profesor vs coleg) | 6 | Must | 2 | 4 | ✅ |
| US 15 | Dialog responsiv în pauză | 6 | Should | 3 | 4 | ✅ |
| US 19 | Model emoțional extins (6 emoții) | 6 | Should | 5 | 4 | ✅ |
| US 22 | Jurnal de profesor separat | 6 | Should | 3 | 4 | ✅ |
| US 20 | Pagină de statistici | 6 | Should | 5 | 4 | ✅ |
| US 17 | Stop & delete sală (profesor) | 6 | Should | 3 | 4 | ✅ |
| US 16 | Continuitate / memorie între sprinturi | 6 | Could | 5 | 4 | ✅ |
| US 18 | ID sală vizibil pentru agenți | 6 | Could | 1 | 4 | ✅ |
| US 24 | Mai mulți studenți per sală (2–5) | 7 | Should | 8 | 5 | ✅ |
| US 23 | Statistici păstrate în istoric | 7 | Should | 3 | 5 | ✅ |
| US 27 | Export PDF al sesiunii | 7 | Should | 5 | 5 | ✅ |
| US 26 | Rating de lecție (observatori) | 7 | Should | 3 | 5 | ✅ |
| US 25 | Programarea sesiunilor | 7 | Could | 5 | 5 | ✅ |
| US 28 | Emoțiile profesorului în statistici | 7 | Could | 2 | 5 | ✅ |
| US 30 | Lecție ca discuție secvențială | 8 | Should | 8 | 6 | ✅ |
| US 29 | Sprint proporțional cu timpul ales | 8 | Should | 5 | 6 | ✅ |
| US 31 | Test diversificat | 8 | Should | 3 | 6 | ✅ |
| US 32 | Alegerea subiectului per sprint | 8 | Should | 5 | 6 | ✅ |

---

## ✨ Highlights

- **Roles & access** — log in as a **teacher** or **student**; browse and watch as an
  **anonymous observer**. API keys are held in server memory only, never persisted.
- **Classrooms** — every room seats **1 teacher + 2–5 students** and starts the moment
  all seats fill, or at a **scheduled start time** the teacher sets.
- **Live everything** — the lesson is a **sequential discussion** (the teacher
  teaches a part, a student asks, the teacher answers), paced to span the chosen
  sprint length, plus grades with reasoning, student **and teacher** journals, six
  per-seat emotions and eval results, all polled live.
- **Real-time pacing** — a 20-minute sprint's teaching actually unfolds over ~20
  minutes (configurable via `time_scale`), instead of finishing instantly.
- **Diversified tests** — each 10-question test mixes formats (definition, example,
  true/false, compare, why, application, scenario, limitation, …).
- **Per-sprint subjects** — between sprints the teacher picks the next subject (type
  one, keep the current, or roll a **random** general topic) before it begins.
- **Six dynamic emotions** — happiness, frustration, confidence, curiosity, boredom and
  anxiety evolve from grades, sanctions, peer support and the passage of sprints, for
  students **and the teacher**.
- **Memory & continuity** — agents remember their previous journal and how they felt,
  so they evolve coherently across sprints.
- **Statistics, live and archived** — per-agent emotion-evolution charts, a grade
  trajectory and sanction tallies, on a dedicated page **and in the History archive**.
- **Observer feedback** — anyone watching can **rate the lesson** 1–5 stars with a comment.
- **PDF export** — download a full report of any archived session (summary, grades,
  stats, sanctions, ratings, journals).
- **Teacher controls** — set the subject, pacing and student count (with a live
  **time-vs-sprints** chart), and **stop & delete** a classroom.
- **Automated evals** — deterministic checks verify the agents actually respect their
  prompts (10 questions, on-topic answers, valid grades, no subject leak in breaks,
  first-person journals under 1000 words).
- **History** — finished sessions are archived in full and browsable.
- **Observer chat** — an independent chatroom per classroom.
- **Pluggable agents** — `mock` (default, deterministic, no keys needed), `anthropic`,
  `openai`, `ollama`, or a **self-hosted** agent you run yourself.

---

## 🚀 Quickstart

### Option A — Docker (whole stack)

```bash
docker compose up --build      # then open http://localhost:8080
# or: make up
```

### Option B — Local development

```bash
# Backend → http://localhost:8000  (interactive docs at /docs)
cd backend
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# Frontend → http://localhost:5173  (proxies /api to the backend)
cd frontend
npm install
npm run dev
```

The backend seeds a few empty demo classrooms on first start. Sign in as a teacher
to set a subject and student count, then as students (or point self-hosted agents at
the room) to fill the seats and watch the session begin. With the default **mock**
provider you need no API keys at all.

---

## 🧩 How a session works

A classroom moves through three states:

```
waiting ──(3rd seat filled)──▶ running ──(last sprint done)──▶ finished ──▶ archived
```

Each **sprint** runs five phases:

| Phase | What happens |
|-------|--------------|
| **Lesson** | The teacher explains the subject with concrete concepts. |
| **Test** | The teacher poses exactly 10 questions; each student answers. |
| **Grading** | The teacher grades 1–10 with reasoning; six emotions update; a creative sanction/reward may follow. |
| **Break** | Students chat off-topic, **each replying to what the other just said**, and comfort each other — the subject is off-limits. |
| **Journal** | Each student writes a first-person reflection under 1000 words; the **teacher writes one too**. |

Phase delays are compressed by `AICADEMICS_SIM_PHASE_SECONDS` so a full run can finish
in seconds for a demo, or take realistic time in production.

---

## 🏗️ Architecture

```
Browser (React SPA)
      │  HTTP, polling ~2s
      ▼
nginx ──/api──▶ FastAPI ──▶ SQLite (SQLAlchemy, WAL)
                   │
                   ├─ one simulation thread per running classroom
                   ├─ in-memory session store (API keys, never persisted)
                   └─ in-memory task queue (self-hosted agents poll/submit)
```

- **Backend** — FastAPI · SQLAlchemy 2 · SQLite · Pydantic. The simulation engine
  (`app/engine/`) is provider-agnostic; the default agent is a deterministic mock so
  the whole thing runs and is tested without external services.
- **Frontend** — React 18 · React Router 6 · Vite, with a hand-rolled SVG chart (no
  charting dependency) and a chalkboard-inspired design system.

```
ai-cademics/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, startup seed
│   │   ├── config.py          # env-driven settings
│   │   ├── database.py        # SQLAlchemy engine (SQLite, WAL)
│   │   ├── models.py          # ORM tables
│   │   ├── schemas.py         # Pydantic models
│   │   ├── security.py        # in-memory session store
│   │   ├── deps.py            # auth dependencies
│   │   ├── routers/           # auth, classrooms, chat, history, agent
│   │   └── engine/            # agents, prompts, providers, evals, queue
│   ├── agent_client.py        # standalone self-hosted agent
│   └── tests/                 # 61 pytest tests
├── frontend/
│   └── src/                   # pages, components, api.js, auth.jsx, usePolling.js
├── .github/workflows/         # ci.yml, deploy.yml  ·  .github/ISSUE_TEMPLATE/, PR template
├── docker-compose.yml · Makefile
└── docs/                       # BACKLOG · DIAGRAMS · TESTING · GIT_WORKFLOW ·
                                # BUG_REPORTS · AI_USAGE_REPORT · DEMO · Change Report PDF
```

---

## 🔌 API overview

All endpoints are under `/api`. Read endpoints (list, detail, live, estimate,
history, chat) are open to observers; mutating endpoints require a session token and
enforce roles.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/auth/login` | Create a user + session, return a token |
| GET/POST | `/api/auth/me`, `/api/auth/logout` | Current user / revoke session |
| GET/POST | `/api/classrooms` | List active rooms / create (teacher) |
| GET | `/api/classrooms/estimate` | Total time per sprint count (chart) |
| POST | `/api/classrooms/{id}/join` · `/configure` · `/leave` | Seat & config management |
| DELETE | `/api/classrooms/{id}` | Stop & delete a classroom (teacher-only) |
| GET | `/api/classrooms/{id}/live` | Discussion + grades + journals (student & teacher) + evals |
| GET | `/api/classrooms/{id}/stats` | Emotion evolution, grade trajectory, sanction tallies |
| GET/POST | `/api/classrooms/{id}/chat` | Observer chatroom |
| GET/POST | `/api/classrooms/{id}/ratings` | Observer lesson ratings (1–5 stars) |
| GET | `/api/classrooms/{id}/random-subject` | A random general subject (the 🎲 button) |
| POST | `/api/classrooms/{id}/next-subject` | Teacher picks the next sprint's subject (resumes the paused session) |
| GET | `/api/history` · `/api/history/{id}` | Archived sessions |
| GET | `/api/history/{id}/pdf` | PDF export of an archived session |
| GET/POST | `/api/agent/poll` · `/api/agent/submit` | Self-hosted agent protocol |

Full interactive docs are served at `/docs` when the backend is running.

---

## 🤖 Self-hosted agents

Run your own agent process (a local Ollama model, or the built-in offline fallback):

```bash
python backend/agent_client.py --role teacher --name Prof --classroom 1 \
    --subject "Graph Theory" --model llama3
python backend/agent_client.py --role student --name Ada   --classroom 1 --model llama3
python backend/agent_client.py --role student --name Linus --classroom 1 --model qwen2
```

It logs in with `provider=external`, joins the room, polls for each phase's task,
generates a reply locally, and submits it. This replaces the original
`student_agent_*.py` scripts (kept under `backend/legacy/` for reference).

---

## ✅ Testing & CI/CD

```bash
make test     # 61 pytest tests (full simulation runs via the mock provider)
make lint     # ruff
make build    # production frontend build
```

GitHub Actions:

- **`ci.yml`** — on every push/PR: ruff + pytest (with coverage) for the backend, and
  `npm ci` + build for the frontend.
- **`deploy.yml`** — on a version tag or manual run: build both Docker images; an
  optional SSH step deploys to a VPS, gated on a repo variable so it stays green until
  a server is configured.

---

## ⚙️ Configuration

Everything is environment-driven (prefix `AICADEMICS_`). See `.env.example`:

| Variable | Default | Meaning |
|----------|---------|---------|
| `AICADEMICS_DATABASE_URL` | `sqlite:///./aicademics.db` | Database location |
| `AICADEMICS_SIM_PHASE_SECONDS` | `0.4` | Compressed delay between phases |
| `AICADEMICS_SEED_CLASSROOMS` | `3` | Demo rooms created on first start |
| `AICADEMICS_CORS_ORIGINS` | `localhost:5173,localhost:8080` | Allowed CORS origins |
| `AICADEMICS_DEFAULT_SPRINT_MINUTES` / `_BREAK_MINUTES` / `_NUM_SPRINTS` | `20` / `10` / `2` | Teacher defaults |
| `AICADEMICS_BREAK_TURNS` | `4` | Turns of break-time small talk |
| `AICADEMICS_SCHEDULER` | `1` | Background ticker that starts scheduled rooms (set `0` to disable) |
| `AICADEMICS_TIME_SCALE` | `1.0` | Real-time multiplier for the lesson/break (a 20-min sprint ≈ 20 min; lower to compress demos, tests use `0`) |
| `AICADEMICS_SUBJECT_CHOICE_SECONDS` | `180` | How long the engine waits between sprints for the teacher to pick the next subject before keeping the current one (`0` = don't pause) |
