# 🎓 AI-cademics

**A multi-agent classroom simulation you can watch live.**

An AI **teacher** and two AI **students** run timed learning sprints — lesson →
test → grading → break → journal — while human **observers** watch the discussion,
grades, journals and prompt-compliance evals unfold in real time. Teachers
configure the subject and pacing; students take a seat; everyone else watches and
chats.

This is a full-stack rebuild (v2) of the original AI-cademics simulation. The core
classroom — its prompts, phase rhythm and emotion model — is preserved and wrapped
in a real product: accounts and roles, a live web UI, automated agent evaluations,
a session archive, Docker delivery and CI/CD.

> 📄 A complete write-up of the architecture and every change lives in
> [`docs/AI-cademics_Change_Report.pdf`](docs/AI-cademics_Change_Report.pdf).

---

## 📋 Cerințe proiect — checklist (pentru evaluare)

### A. Implementarea

| Cerință | Unde se găsește |
|---------|-----------------|
| Live demo | Scenariu pas-cu-pas în [`docs/DEMO.md`](docs/DEMO.md); deploy public pe domeniu cu HTTPS în [`docs/DEPLOY.md`](docs/DEPLOY.md) |
| **Minim 2 agenți AI** în funcționalitate (modele de limbaj mici, locale) | **3 agenți**: 1 profesor + 2 studenți, rulabili pe modele locale mici prin Ollama (`llama3`, `qwen2`) — vezi [`docs/DEMO.md`](docs/DEMO.md) și [Self-hosted agents](#-self-hosted-agents) |
| Demo offline (screencast / YouTube) | Link + instrucțiuni în [`docs/DEMO.md`](docs/DEMO.md#demo-offline-screencast) |

### B. Procesul de dezvoltare software cu AI

| Cerință | Punctaj | Unde se găsește |
|---------|---------|-----------------|
| User stories (minim 10) + backlog | 2 pct | [`docs/BACKLOG.md`](docs/BACKLOG.md) — 14 user stories pe 5 epics + tabel de backlog (MoSCoW, story points, status) |
| Diagrame (UML, arhitectură, workflowuri) | 1 pct | [`docs/DIAGRAMS.md`](docs/DIAGRAMS.md) — 6 diagrame Mermaid: componente, clase, stări, 2× secvență, CI/CD |
| Source control cu git (branches, merge, PRs, ≥5 commits/student) | 1 pct | [`docs/GIT_WORKFLOW.md`](docs/GIT_WORKFLOW.md) — 11 branch-uri, 5 PR-uri documentate, statistici commits/student |
| Teste automate (inclusiv evals pentru agenți) | 2 pct | [`docs/TESTING.md`](docs/TESTING.md) — 38 teste pytest + 7 evals deterministe per agent, rulate în CI |
| Raportare bug + rezolvare cu pull request | 1 pct | [`docs/BUG_REPORTS.md`](docs/BUG_REPORTS.md) — 3 bug-uri documentate cu PR-uri + template de issue |
| Pipeline CI/CD | 1 pct | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (lint + teste + build) și [`deploy.yml`](.github/workflows/deploy.yml) (imagini Docker + deploy opțional pe VPS) |
| Raport despre folosirea toolurilor AI | 2 pct | [`docs/AI_USAGE_REPORT.md`](docs/AI_USAGE_REPORT.md) — pe fiecare etapă, cu prompturi, limite și lecții |

---

## ✨ Highlights

- **Roles & access** — log in as a **teacher** or **student**; browse and watch as an
  **anonymous observer**. API keys are held in server memory only, never persisted.
- **Classrooms** — every room seats exactly **1 teacher + 2 students** and starts the
  moment all three seats fill.
- **Live everything** — discussion, grades with reasoning, first-person journals,
  per-seat emotions and eval results, all polled live.
- **Teacher controls** — set the subject, sprint length, break length and number of
  sprints, with a live **time-vs-sprints** chart.
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
to set a subject, then as two students (or point self-hosted agents at the room) to
fill the seats and watch the session begin. With the default **mock** provider you
need no API keys at all.

### Option C — Deploy public pe un domeniu (HTTPS automat)

Pentru a face aplicația accesibilă pe internet, pe un domeniu, cu certificat HTTPS
automat (Let's Encrypt via Caddy):

```bash
cp .env.prod.example .env.prod        # setează DOMAIN și ACME_EMAIL
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

Ghidul complet (DNS, droplet, firewall, deploy automat din GitHub) este în
[`docs/DEPLOY.md`](docs/DEPLOY.md).

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
| **Grading** | The teacher grades 1–10 with reasoning; emotions update; a creative sanction/reward may follow. |
| **Break** | Students chat off-topic and comfort each other — the subject is off-limits. |
| **Journal** | Each student writes a first-person reflection under 1000 words. |

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
│   └── tests/                 # 38 pytest tests
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
| GET | `/api/classrooms/{id}/live` | Discussion + grades + journals + evals |
| GET/POST | `/api/classrooms/{id}/chat` | Observer chatroom |
| GET | `/api/history` · `/api/history/{id}` | Archived sessions |
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
make test     # 38 pytest tests (full simulation runs via the mock provider)
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

---

## 📜 License & origin

Rebuilt from [github.com/bbiAncah/ai-cademics](https://github.com/bbiAncah/ai-cademics).
Original agent scripts are preserved under `backend/legacy/`.
