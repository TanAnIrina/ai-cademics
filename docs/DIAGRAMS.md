# 📐 Diagrame

> Acoperă cerința: **diagrame (UML, arhitectura componentelor, workflowuri) — 1 pct**.
> Diagramele sunt scrise în [Mermaid](https://mermaid.js.org/) și sunt randate automat de GitHub.
> Au fost generate și verificate cu un tool AI — vezi [`AI_USAGE_REPORT.md`](AI_USAGE_REPORT.md#3-diagrame).

## Cuprins
1. [Arhitectura componentelor](#1-arhitectura-componentelor)
2. [Diagrama de clase (modelul de date)](#2-diagrama-de-clase-modelul-de-date)
3. [Diagrama de stări — ciclul de viață al unei săli](#3-diagrama-de-stări--ciclul-de-viață-al-unei-săli)
4. [Diagrama de secvență — un sprint complet](#4-diagrama-de-secvență--un-sprint-complet)
5. [Diagrama de secvență — agent self-hosted (LLM local)](#5-diagrama-de-secvență--agent-self-hosted-llm-local)
6. [Workflow CI/CD](#6-workflow-cicd)

---

## 1. Arhitectura componentelor

```mermaid
flowchart LR
    subgraph Client
        B[Browser<br/>React 18 SPA]
    end

    subgraph Docker["Docker Compose"]
        N[nginx<br/>servește SPA + proxy /api]
        subgraph API["FastAPI backend"]
            R[Routers<br/>auth · classrooms · chat · history · agent]
            E[Engine de simulare<br/>1 thread / sală running]
            EV[Evals<br/>verificări deterministe]
            Q[Task queue in-memory<br/>protocol agenți self-hosted]
            S[Session store in-memory<br/>tokenuri + chei API]
        end
        DB[(SQLite WAL<br/>SQLAlchemy 2)]
    end

    subgraph Agents["Furnizori de agenți AI"]
        M[Mock<br/>determinist, default]
        O[Ollama<br/>LLM-uri locale mici]
        A[Anthropic / OpenAI API]
        SH[agent_client.py<br/>self-hosted]
    end

    B -- "HTTP, polling ~2s" --> N --> R
    R --> E
    E --> EV
    E --> DB
    R --> DB
    R --> S
    E --> M & O & A
    SH -- "poll / submit" --> Q --> E
```

## 2. Diagrama de clase (modelul de date)

Corespunde 1-la-1 cu `backend/app/models.py`.

```mermaid
classDiagram
    class User {
        +int id
        +str name
        +str role
        +str provider
    }
    class Classroom {
        +int id
        +str status
        +str subject
        +int sprint_minutes
        +int break_minutes
        +int num_sprints
    }
    class Membership {
        +int id
        +str seat_role
        +int frustration
        +int happiness
    }
    class Message {
        +int id
        +str phase
        +str speaker
        +str content
        +int sprint
    }
    class Grade {
        +int id
        +int sprint
        +int value
        +str reasoning
    }
    class Sanction {
        +int id
        +str kind
        +str reason
    }
    class Journal {
        +int id
        +int sprint
        +str content
    }
    class EvalResult {
        +int id
        +str scope
        +str check_name
        +bool passed
        +float score
        +str detail
    }
    class ChatMessage {
        +int id
        +str author
        +str content
    }
    class Archive {
        +int id
        +json payload
        +datetime finished_at
    }

    User "1" --> "*" Membership
    Classroom "1" --> "*" Membership
    Classroom "1" --> "*" Message
    Classroom "1" --> "*" Grade
    Classroom "1" --> "*" Sanction
    Classroom "1" --> "*" Journal
    Classroom "1" --> "*" EvalResult
    Classroom "1" --> "*" ChatMessage
    Classroom "1" --> "0..1" Archive : la final
```

## 3. Diagrama de stări — ciclul de viață al unei săli

```mermaid
stateDiagram-v2
    [*] --> waiting : sală creată (seed sau profesor)
    waiting --> waiting : join/leave (locuri libere)
    waiting --> running : al 3-lea loc ocupat<br/>(1 profesor + 2 studenți)
    running --> running : sprint = lesson → test →<br/>grading → break → journal
    running --> finished : ultimul sprint încheiat
    finished --> archived : payload complet salvat în Archive
    archived --> [*] : vizibil doar în History
```

## 4. Diagrama de secvență — un sprint complet

```mermaid
sequenceDiagram
    autonumber
    participant SE as Engine simulare
    participant T as Agent Profesor (LLM)
    participant S1 as Agent Student 1 (LLM)
    participant S2 as Agent Student 2 (LLM)
    participant EV as Evals
    participant DB as SQLite
    participant UI as Browser (polling /live)

    SE->>T: prompt lecție (subiect)
    T-->>SE: lecția
    SE->>DB: salvează Message(lesson)
    SE->>T: prompt test
    T-->>SE: exact 10 întrebări
    SE->>EV: eval_questions (număr + relevanță)
    loop pentru fiecare întrebare
        SE->>S1: întrebarea
        S1-->>SE: răspuns
        SE->>S2: întrebarea
        S2-->>SE: răspuns
        SE->>EV: eval_answer (on-topic)
    end
    SE->>T: prompt notare
    T-->>SE: note 1–10 + justificare (+ sancțiune/recompensă)
    SE->>EV: eval_grade
    SE->>DB: Grade, Sanction, emoții actualizate
    SE->>S1: prompt pauză (subiect interzis)
    S1-->>S2: small talk / consolare
    SE->>EV: eval_break (no subject leak)
    SE->>S1: prompt jurnal
    S1-->>SE: jurnal persoana I, <1000 cuvinte
    SE->>EV: eval_journal
    SE->>DB: Journal, EvalResult
    UI->>DB: GET /api/classrooms/{id}/live (la ~2s)
    DB-->>UI: discuție + note + jurnale + evals
```

## 5. Diagrama de secvență — agent self-hosted (LLM local)

```mermaid
sequenceDiagram
    autonumber
    participant AC as agent_client.py<br/>(Ollama local)
    participant API as FastAPI
    participant Q as Task queue
    participant SE as Engine

    AC->>API: POST /api/auth/login (provider=external)
    AC->>API: POST /api/classrooms/{id}/join
    SE->>Q: publică task (ex. "răspunde la întrebarea 3")
    loop la fiecare ~1s
        AC->>API: GET /api/agent/poll
        API-->>AC: task sau gol
    end
    AC->>AC: generează răspuns cu LLM local
    AC->>API: POST /api/agent/submit
    API->>Q: rezolvă task-ul
    Q-->>SE: răspunsul agentului ⇒ simularea continuă
```

## 6. Workflow CI/CD

```mermaid
flowchart TD
    P[push / pull request] --> CI{ci.yml}
    CI --> L[ruff — lint backend]
    CI --> T[pytest + coverage<br/>38 teste, inclusiv evals]
    CI --> F[npm ci + vite build<br/>artifact frontend-dist]
    L & T & F -->|toate verzi| MQ[merge în main<br/>prin pull request]
    TAG[tag v* sau manual] --> CD{deploy.yml}
    CD --> BI[build imagini Docker<br/>backend + frontend, cache GHA]
    BI --> GATE{DEPLOY_ENABLED == true?}
    GATE -->|da| VPS[SSH pe VPS<br/>docker compose up -d --build]
    GATE -->|nu| SKIP[skip — workflow rămâne verde]
```
