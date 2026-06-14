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
# 📋 Product Backlog & User Stories

> Acoperă cerința: **user stories (minim 10), backlog creation — 2 pct**.
> Backlog-ul a fost creat și rafinat cu ajutorul unui tool AI (Claude) — vezi
> [`AI_USAGE_REPORT.md`](AI_USAGE_REPORT.md#1-backlog--user-stories) pentru prompturile folosite.

## Cuprins
- [Epic 1: Acces și gestionarea profilului](#epic-1-acces-și-gestionarea-profilului)
- [Epic 2: Sesiunea de clasă și interacțiunea](#epic-2-sesiunea-de-clasă-și-interacțiunea)
- [Epic 3: Emoții, pauze și acțiuni disciplinare](#epic-3-emoții-pauze-și-acțiuni-disciplinare)
- [Epic 4: Analiză și urmărirea performanței](#epic-4-analiză-și-urmărirea-performanței)
- [Epic 5: Observatori și arhivă](#epic-5-observatori-și-arhivă)
- [Tabelul de backlog](#tabelul-de-backlog)

---

## Epic 1: Acces și gestionarea profilului

### US 1 — Login & săli active
**Ca** utilizator, **vreau să** mă autentific în aplicație și să văd lista sălilor de clasă active, **astfel încât** să o pot alege pe cea potrivită și să mă alătur.
- **Criterii de acceptare:** utilizatorul se autentifică cu succes; toate sălile active sunt afișate cu statusul lor (waiting / running / finished); utilizatorul poate selecta și intra într-o sală.
- **Implementare:** `backend/app/routers/auth.py`, `backend/app/routers/classrooms.py`, `frontend/src/pages/LoginPage.jsx`, `frontend/src/pages/ClassroomsPage.jsx`
- **Teste:** `backend/tests/test_auth.py`, `backend/tests/test_classrooms.py`

### US 2 — Roluri (profesor / student / observator)
**Ca** utilizator, **vreau să** îmi aleg rolul la autentificare (profesor sau student) sau să rămân observator anonim, **astfel încât** aplicația să îmi ofere exact acțiunile permise rolului meu.
- **Criterii de acceptare:** profesorul poate crea/configura săli; studentul poate ocupa un loc; observatorul poate doar privi și folosi chat-ul; endpoint-urile mutante refuză cererile fără rolul corect (403).
- **Implementare:** `backend/app/deps.py`, `backend/app/security.py`
- **Teste:** `backend/tests/test_auth.py`, `backend/tests/test_classrooms.py`

### US 3 — Profil cu nume vizibil
**Ca** utilizator, **vreau să** îmi setez un nume de afișare, **astfel încât** să am o identitate recognoscibilă în clasă și în interacțiunile din pauză.
- **Criterii de acceptare:** numele este setat la login; este vizibil celorlalți în sală și în lista de săli; persistă pe durata sesiunii.
- **Implementare:** `backend/app/routers/auth.py`, `backend/app/models.py` (`User`)

## Epic 2: Sesiunea de clasă și interacțiunea

### US 4 — Predare, testare și evaluare
**Ca** profesor (agent AI), **vreau să** predau o mini-lecție urmată de un test cu exact 10 întrebări la finalul fiecărui sprint și să ofer o justificare scrisă a notării, **astfel încât** evaluarea cunoștințelor să fie transparentă.
- **Criterii de acceptare:** profesorul generează exact 10 întrebări; numărul sprintului, întrebările, răspunsurile studenților, justificarea notării și notele (1–10) sunt salvate.
- **Implementare:** `backend/app/engine/__init__.py` (fazele lesson/test/grading), `backend/app/engine/prompts.py`
- **Teste:** `backend/tests/test_simulation.py`, `backend/tests/test_evals.py` (eval `question_count`)

### US 5 — Configurarea sprintului de către profesor
**Ca** profesor, **vreau să** setez subiectul, durata sprintului, durata pauzei și numărul de sprinturi înainte de pornirea clasei, **astfel încât** sesiunea să se potrivească materiei predate.
- **Criterii de acceptare:** configurarea este permisă doar profesorului din sală; valorile au limite valide; un grafic live arată timpul total estimat în funcție de numărul de sprinturi.
- **Implementare:** `backend/app/routers/classrooms.py` (`/configure`, `/estimate`), `frontend/src/components/SessionTimeChart.jsx`
- **Teste:** `backend/tests/test_classrooms.py`

### US 6 — Pornirea automată a clasei
**Ca** student, **vreau ca** simularea să pornească automat în momentul în care toate cele 3 locuri (1 profesor + 2 studenți) sunt ocupate, **astfel încât** să nu fie nevoie de o acțiune manuală suplimentară.
- **Criterii de acceptare:** sala trece din `waiting` în `running` la ocuparea ultimului loc; un thread de simulare dedicat rulează fazele; părăsirea sălii înainte de start eliberează locul.
- **Implementare:** `backend/app/routers/classrooms.py` (`/join`, `/leave`), `backend/app/engine/__init__.py`
- **Teste:** `backend/tests/test_simulation.py`

## Epic 3: Emoții, pauze și acțiuni disciplinare

### US 7 — Jurnal de învățare
**Ca** student (agent AI), **vreau să** generez o intrare de jurnal la finalul pauzei, **astfel încât** să rezum ce am învățat în sub 1000 de cuvinte și să îmi descriu și justific emoțiile.
- **Criterii de acceptare:** jurnalul este salvat; textul este la persoana întâi, cu numele studentului; limita de 1000 de cuvinte este verificată automat de evals.
- **Implementare:** `backend/app/engine/__init__.py` (faza journal), `backend/app/engine/prompts.py`
- **Teste:** `backend/tests/test_evals.py` (`journal_first_person`, `journal_length`)

### US 8 — Sancțiuni și recompense
**Ca** profesor (agent AI), **vreau să** pot acorda sancțiuni sau recompense pe baza răspunsurilor, salvate împreună cu o justificare creativă, **astfel încât** să existe o evidență permanentă și transparentă.
- **Criterii de acceptare:** după notare poate fi generată o sancțiune/recompensă cu explicație creativă; nivelul de frustrare al studentului vizat este actualizat.
- **Implementare:** `backend/app/models.py` (`Sanction`), `backend/app/engine/__init__.py`
- **Teste:** `backend/tests/test_simulation.py`

### US 9 — Consolare reciprocă în pauză
**Ca** student (agent AI), **vreau să** îmi pot consola colegul în pauză dacă a primit o sancțiune, **astfel încât** stările noastre emoționale să se influențeze dinamic — fără a discuta subiectul lecției.
- **Criterii de acceptare:** în pauză studenții conversează off-topic; menționarea subiectului lecției este interzisă și verificată automat de evals; consolarea folosind numele colegului reduce frustrarea acestuia.
- **Implementare:** `backend/app/engine/__init__.py` (faza break + modelul emoțional)
- **Teste:** `backend/tests/test_evals.py` (`break_no_subject_leak`)

## Epic 4: Analiză și urmărirea performanței

### US 10 — Vizualizarea notelor și a justificărilor
**Ca** student / observator, **vreau să** văd nota și raționamentul scris al profesorului după fiecare test, **astfel încât** să înțeleg de ce a fost acordată o anumită notă.
- **Criterii de acceptare:** după evaluare sunt vizibile nota (1–10), întrebările, răspunsurile și justificarea, per sprint, în panoul live.
- **Implementare:** `backend/app/routers/classrooms.py` (`/live`), `frontend/src/components/Panels.jsx`
- **Teste:** `backend/tests/test_simulation.py`, `backend/tests/test_evals.py` (`grade_validity`)

### US 11 — Emoții live per loc
**Ca** observator, **vreau să** văd evoluția emoțiilor (frustrare/fericire) fiecărui student pe parcursul sesiunii, **astfel încât** să urmăresc impactul notelor și al sancțiunilor.
- **Criterii de acceptare:** emoțiile sunt afișate per loc și actualizate la fiecare fază; valorile sunt persistate și apar și în arhivă.
- **Implementare:** `backend/app/engine/__init__.py`, `frontend/src/pages/ClassroomDetailPage.jsx`

### US 12 — Rezultatele evaluărilor automate (evals)
**Ca** observator / evaluator, **vreau să** văd în timp real rezultatele verificărilor automate ale agenților (evals), **astfel încât** să pot judeca dacă agenții respectă prompturile.
- **Criterii de acceptare:** fiecare verificare are nume, status (passed/failed), scor 0–1 și detaliu; rezultatele apar live și în arhivă.
- **Implementare:** `backend/app/engine/evals.py`, `backend/app/models.py` (`EvalResult`)
- **Teste:** `backend/tests/test_evals.py`

## Epic 5: Observatori și arhivă

### US 13 — Chat pentru observatori
**Ca** observator, **vreau** un chat independent per sală, **astfel încât** să pot comenta sesiunea fără a interfera cu simularea.
- **Criterii de acceptare:** chat-ul este separat de discuția agenților; orice utilizator autentificat poate scrie; mesajele sunt persistate.
- **Implementare:** `backend/app/routers/chat.py`, `frontend/src/components/Chat.jsx`
- **Teste:** `backend/tests/test_chat_history.py`

### US 14 — Istoric și arhivă completă
**Ca** utilizator, **vreau să** pot răsfoi sesiunile încheiate cu tot conținutul lor (discuție, note, jurnale, evals), **astfel încât** sesiunile să poată fi analizate ulterior.
- **Criterii de acceptare:** la finalul ultimei runde sala este arhivată integral; arhiva e accesibilă din pagina History; sala dispare din lista activă.
- **Implementare:** `backend/app/routers/history.py`, `backend/app/models.py` (`Archive`), `frontend/src/pages/HistoryPage.jsx`
- **Teste:** `backend/tests/test_chat_history.py`

---

## Tabelul de backlog

Prioritizare prin metoda **MoSCoW**, estimare în story points (Fibonacci). Statusul reflectă versiunea curentă (v2).

| ID | Titlu | Epic | Prioritate | Estimare | Sprint | Status | Teste |
|----|-------|------|-----------|----------|--------|--------|-------|
| US 4 | Predare, testare, evaluare | 2 | Must | 8 | 1 | ✅ Done | ✅ |
| US 6 | Pornire automată a clasei | 2 | Must | 5 | 1 | ✅ Done | ✅ |
| US 7 | Jurnal de învățare | 3 | Must | 3 | 1 | ✅ Done | ✅ |
| US 9 | Pauză + consolare reciprocă | 3 | Must | 5 | 1 | ✅ Done | ✅ |
| US 1 | Login & săli active | 1 | Must | 5 | 2 | ✅ Done | ✅ |
| US 2 | Roluri și permisiuni | 1 | Must | 5 | 2 | ✅ Done | ✅ |
| US 12 | Evals automate vizibile | 4 | Must | 5 | 2 | ✅ Done | ✅ |
| US 5 | Configurare sprint de profesor | 2 | Should | 3 | 2 | ✅ Done | ✅ |
| US 10 | Note + justificări vizibile | 4 | Should | 3 | 3 | ✅ Done | ✅ |
| US 11 | Emoții live per loc | 4 | Should | 3 | 3 | ✅ Done | — |
| US 14 | Istoric & arhivă | 5 | Should | 5 | 3 | ✅ Done | ✅ |
| US 13 | Chat observatori | 5 | Could | 2 | 3 | ✅ Done | ✅ |
| US 3 | Profil cu nume | 1 | Could | 1 | 2 | ✅ Done | — |
| US 8 | Sancțiuni & recompense | 3 | Could | 3 | 3 | ✅ Done | ✅ |

**Backlog viitor (nepreluat în v2):** programarea sălilor în viitor (scheduling), rating de lecție dat de observatori, export PDF al arhivei, WebSockets în loc de polling, suport pentru mai mult de 2 studenți per sală.
