# 🤖 Raport: folosirea toolurilor de AI în dezvoltarea software

> Acoperă cerința: **raport despre folosirea toolurilor de AI în timpul dezvoltării software — 2 pct.**
> Cerința generală „toate aspectele trebuie să implice utilizarea unor tooluri de AI" este detaliată mai jos, pe fiecare etapă a procesului.

## Tooluri folosite

| Tool | Rol în proiect |
|------|----------------|
| **Claude (claude.ai / Sonnet & Opus)** | Tool principal: arhitectură, generare de cod backend/frontend, teste, evals, diagrame, documentație, debugging, CI/CD |
| **GitHub Copilot** | Autocomplete în editor pentru cod repetitiv (componente React, scheme Pydantic) |
| **Ollama (llama3, qwen2)** | LLM-uri locale mici care joacă rolul agenților din aplicație și sunt folosite la testarea manuală a agenților |
| **ChatGPT** | Brainstorming inițial pentru temă și pentru formularea user story-urilor |

---

## 1. Backlog & user stories

- User story-urile inițiale (12) au fost redactate pornind de la o descriere liberă a ideii („o clasă simulată de LLM-uri cu sprinturi, pauze și emoții"), pe care un asistent AI a transformat-o în formatul standard *As a / I want to / so that* cu criterii de acceptare.
- Prompt reprezentativ: *„Transformă această descriere de proiect într-un product backlog cu user stories grupate pe epics, fiecare cu criterii de acceptare verificabile."*
- AI-ul a propus și prioritizarea MoSCoW + estimările în story points din [`BACKLOG.md`](BACKLOG.md#tabelul-de-backlog); echipa a ajustat manual prioritățile (de ex. chat-ul observatorilor a fost retrogradat la *Could*).
- **Verificare umană:** fiecare criteriu de acceptare a fost confruntat cu ce este realizabil în timpul disponibil; story-urile nerealizabile au fost mutate explicit în secțiunea „Backlog viitor".

## 2. Implementare (cod)

- Versiunea v1 (scripturile `legacy/`) a fost scrisă manual, cu Copilot pentru autocomplete.
- Versiunea v2 (rebuild full-stack) a fost dezvoltată în sesiuni iterative cu Claude:
  - schelet FastAPI + SQLAlchemy generat din specificația backlog-ului;
  - engine-ul de simulare (faze, thread per sală, model emoțional) — generat și apoi rafinat prin prompturi de tip *„păstrează prompturile și ritmul fazelor din scripturile originale, dar fă providerul de LLM interschimbabil"*;
  - frontend React generat componentă cu componentă, cu tema „chalkboard" cerută explicit;
  - protocolul de agenți self-hosted (`/api/agent/poll`, `/api/agent/submit`) — proiectat împreună cu AI-ul pentru a permite modele locale Ollama drept agenți.
- **Limite întâlnite:** AI-ul a propus inițial WebSockets; am ales polling pentru simplitate și testabilitate. Câteva detalii SQLite (modul WAL, `check_same_thread`) au necesitat corecturi manuale după erori la rulare.

## 3. Diagrame

- Diagramele Mermaid din [`DIAGRAMS.md`](DIAGRAMS.md) au fost generate de AI direct din codul sursă (`models.py`, `engine/`, workflow-urile GitHub Actions), apoi verificate manual ca fiecare clasă/relație să corespundă codului real.
- Prompt reprezentativ: *„Generează o diagramă de clase Mermaid 1-la-1 cu modelele SQLAlchemy din acest fișier."*

## 4. Source control (git)

- Mesajele de commit pentru schimbările mari și descrierile de pull request au fost redactate cu ajutorul AI-ului, pe baza diff-ului.
- Strategia de branching (branch-uri `feature/*` și `fix/*`, merge prin PR) este documentată în [`GIT_WORKFLOW.md`](GIT_WORKFLOW.md); AI-ul a fost folosit și pentru rezolvarea conflictelor de merge (explicarea diff-urilor conflictuale).

## 5. Teste automate & evals

- Cele **38 de teste pytest** au fost generate de AI pe baza endpoint-urilor și a engine-ului, apoi rulate și corectate local; vezi [`TESTING.md`](TESTING.md).
- **Evals pentru agenți** (`backend/app/engine/evals.py`): ideea verificărilor (exact 10 întrebări, răspunsuri on-topic, note valide, fără scurgerea subiectului în pauză, jurnal la persoana I sub 1000 cuvinte) vine direct din prompturile agenților; AI-ul a transformat fiecare regulă din prompt într-o verificare deterministă, fără dependențe, care rulează identic în CI și în producție.
- **Lecție:** evals deterministe (keyword overlap, numărare, regex) sunt mult mai potrivite pentru CI decât evals „LLM-as-judge", care ar fi nedeterministe și ar cere chei API în pipeline.

## 6. Bug reporting & rezolvare

- Bug-urile au fost diagnosticate cu AI (lipirea traceback-ului + fișierele relevante); fix-urile au mers prin PR-uri dedicate — exemple concrete în [`BUG_REPORTS.md`](BUG_REPORTS.md).
- Template-urile de issue (`.github/ISSUE_TEMPLATE/`) au fost generate cu AI.

## 7. CI/CD

- `ci.yml` și `deploy.yml` au fost scrise integral cu AI, inclusiv detalii pe care nu le cunoșteam: cache pip/npm pe lockfile, cache de layere Docker prin GitHub Actions (`type=gha`), și gating-ul deploy-ului pe variabila `DEPLOY_ENABLED` ca workflow-ul să rămână verde fără un server configurat.

## 8. Documentație

- README-ul, acest raport și restul fișierelor din `docs/` au fost redactate cu AI și revizuite de echipă.
- Raportul de modificări v1→v2 ([`AI-cademics_Change_Report.pdf`](AI-cademics_Change_Report.pdf)) a fost generat programatic (`build_report.py`), scriptul fiind la rândul lui produs cu AI.

---

## Evaluare critică: ce a mers bine / ce nu

**A mers bine**
- Viteză: rebuild-ul complet (backend + frontend + teste + CI) a durat zile, nu săptămâni.
- Calitate constantă a codului „plictisitor" (scheme Pydantic, CRUD, componente React).
- Transformarea regulilor din prompturi în evals automate — o sarcină pe care probabil nu am fi abordat-o singuri atât de sistematic.

**A mers prost / a necesitat intervenție umană**
- Halucinații ocazionale de API (parametri inexistenți la SQLAlchemy 2 / FastAPI) — prinse de teste și de ruff.
- AI-ul tinde să „suprainginerizeze"; a trebuit să cerem explicit soluții simple (polling în loc de WebSockets, SQLite în loc de Postgres).
- Codul generat trebuie întotdeauna rulat și citit: am tratat fiecare bucată generată ca pe un PR de la un coleg, nu ca pe un adevăr.

**Concluzie:** AI-ul a funcționat ca un coleg de echipă foarte rapid, dar care are nevoie de review. Combinația care a dat cele mai bune rezultate: specificație clară (backlog) → generare → rulare teste → corectare iterativă.
