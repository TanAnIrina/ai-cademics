# 📋 Product Backlog & User Stories

> Acoperă cerința: **user stories (minim 10), backlog creation — 2 pct**.
> **28 user stories pe 7 epics**, prioritizate MoSCoW, cu estimări în story points
> și status. Backlog-ul a fost creat și rafinat cu ajutorul unui tool AI (Claude) —
> vezi [`AI_USAGE_REPORT.md`](AI_USAGE_REPORT.md#1-backlog--user-stories) pentru prompturi.

## Cuprins
- [Epic 1: Acces și gestionarea profilului](#epic-1-acces-și-gestionarea-profilului)
- [Epic 2: Sesiunea de clasă și interacțiunea](#epic-2-sesiunea-de-clasă-și-interacțiunea)
- [Epic 3: Emoții, pauze și acțiuni disciplinare](#epic-3-emoții-pauze-și-acțiuni-disciplinare)
- [Epic 4: Analiză și urmărirea performanței](#epic-4-analiză-și-urmărirea-performanței)
- [Epic 5: Observatori și arhivă](#epic-5-observatori-și-arhivă)
- [Epic 6: Iterația v2.1 — interacțiune, memorie și analiză](#epic-6-iterația-v21--interacțiune-memorie-și-analiză)
- [Epic 7: Iterația v2.2 — scalare, planificare și export](#epic-7-iterația-v22--scalare-planificare-și-export)
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
**Ca** observator, **vreau să** văd emoțiile fiecărui agent pe parcursul sesiunii, **astfel încât** să urmăresc impactul notelor și al sancțiunilor.
- **Criterii de acceptare:** emoțiile sunt afișate per loc și actualizate la fiecare fază; valorile sunt persistate și apar și în arhivă. (Extins în US 19 la 6 emoții.)
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

## Epic 6: Iterația v2.1 — interacțiune, memorie și analiză

> A doua iterație de backlog (Sprint 4): rafinarea interacțiunii dintre agenți, a
> modelului emoțional și a instrumentelor de analiză, pe baza feedback-ului după v2.

### US 15 — Dialog responsiv în pauză
**Ca** observator, **vreau ca** fiecare student să răspundă explicit la ce tocmai a spus colegul (nu replici paralele, fără legătură), **astfel încât** pauza să arate ca o conversație reală în care se ascultă reciproc.
- **Criterii de acceptare:** la fiecare tură, replica anterioară a colegului este injectată în prompt; răspunsul recunoaște și continuă ce a spus celălalt; subiectul lecției rămâne interzis.
- **Implementare:** `backend/app/engine/__init__.py` (bucla break cu `peer_last`/`last_by_slot`), `backend/app/engine/prompts.py` (`student_break_prompt`), `backend/app/engine/agents.py` (`break_turn`)
- **Teste:** `backend/tests/test_features.py` (`test_break_replies_acknowledge_the_classmate`)

### US 16 — Continuitate emoțională și memorie între sprinturi
**Ca** observator, **vreau ca** agenții să își amintească ce au simțit și ce au scris în jurnal în sprinturile anterioare, **astfel încât** comportamentul lor să evolueze coerent de-a lungul sesiunii.
- **Criterii de acceptare:** la sprinturile următoare, un rezumat al jurnalului anterior + starea emoțională sunt injectate în prompturi (răspuns, pauză, jurnal); profesorul are propria memorie pentru reflecție.
- **Implementare:** `backend/app/engine/__init__.py` (dicționarul `memory` per slot), `backend/app/engine/prompts.py` (`_memory_block`), `backend/app/engine/agents.py` (parametrul `memory`)
- **Teste:** acoperit de `backend/tests/test_simulation.py` + verificare end-to-end (jurnalul de la sprintul 2 referă continuitatea)

### US 17 — Oprirea și ștergerea unei săli (doar profesor)
**Ca** profesor, **vreau** un buton care oprește o sesiune activă și șterge definitiv sala cu toate datele ei, **astfel încât** să pot curăța sălile de test sau să închid o sesiune scăpată de sub control.
- **Criterii de acceptare:** doar profesorul care deține sala (sau o sală fără profesor) poate șterge; o sesiune `running` este oprită cooperativ înainte de ștergere; studenții și ceilalți profesori primesc 403.
- **Implementare:** `backend/app/engine/__init__.py` (`request_stop`/`_should_stop`/`PHASE_STOPPED`), `backend/app/routers/classrooms.py` (`DELETE /api/classrooms/{id}`), `frontend/src/pages/ClassroomDetailPage.jsx` (`handleDelete`)
- **Teste:** `backend/tests/test_features.py` (`test_teacher_can_stop_and_delete_classroom`, `test_students_cannot_delete_classroom`, `test_other_teacher_cannot_delete_owned_classroom`)

### US 18 — ID-ul sălii vizibil pentru agenții self-hosted
**Ca** utilizator care rulează agenți locali, **vreau să** văd ID-ul sălii direct pe pagina clasei, **astfel încât** să știu exact ce valoare să dau la `--classroom` în comandă.
- **Criterii de acceptare:** pagina clasei afișează un badge `ID <n> · --classroom <n>` cu explicație; ID-ul apare și pe pagina de statistici.
- **Implementare:** `frontend/src/pages/ClassroomDetailPage.jsx`, `frontend/src/pages/ClassroomStatsPage.jsx`

### US 19 — Model emoțional extins și dinamic
**Ca** observator, **vreau** un set mai bogat de emoții (nu doar frustrare/fericire) care evoluează din note, sancțiuni, suportul colegilor și trecerea sprinturilor, **astfel încât** stările agenților să fie nuanțate și credibile.
- **Criterii de acceptare:** 6 emoții (happiness, frustration, confidence, curiosity, boredom, anxiety), fiecare 0–10, afișate per loc; se actualizează diferențiat la note mici/medii/mari și la sancțiuni/recompense; tonul răspunsurilor reflectă emoția dominantă.
- **Implementare:** `backend/app/models.py` (`EMOTIONS` + coloane `Membership`), `backend/app/engine/__init__.py` (`_adjust` + actualizările emoționale), `frontend/src/components/ui.jsx` (`EmotionBars`)
- **Teste:** `backend/tests/test_features.py` (`test_members_expose_full_emotion_vector`)

### US 20 — Pagină de statistici a clasei
**Ca** observator / evaluator, **vreau** o pagină separată cu evoluția clasei și a emoțiilor agenților, **astfel încât** să pot analiza vizual cum s-a schimbat sesiunea în timp.
- **Criterii de acceptare:** grafice de evoluție a emoțiilor per agent (o linie/emoție pe sprinturi), traiectoria notelor per student și totalurile de sancțiuni/recompense; un snapshot emoțional este salvat la fiecare sprint (plus un baseline la start).
- **Implementare:** `backend/app/models.py` (`EmotionSnapshot`), `backend/app/routers/classrooms.py` (`GET /api/classrooms/{id}/stats`), `frontend/src/pages/ClassroomStatsPage.jsx`
- **Teste:** `backend/tests/test_features.py` (`test_stats_endpoint_returns_emotion_timeline_and_grades`)

### US 21 — Claritatea rolurilor (profesor vs coleg)
**Ca** student (agent AI), **vreau să** știu clar cine este profesorul (autoritate care notează) și cine este colegul (egal), **astfel încât** să nu mă adresez profesorului ca unui coleg și invers.
- **Criterii de acceptare:** prompturile definesc explicit cele două roluri; în jurnal studentul distinge sentimentele față de profesor de cele față de coleg; rolurile nu mai sunt confundate.
- **Implementare:** `backend/app/engine/prompts.py` (`student_classroom_prompt`, `student_break_prompt`, `student_journal_prompt`)
- **Teste:** acoperit de `backend/tests/test_simulation.py` + verificare end-to-end (jurnalul spune „my teacher … my classmate (not the teacher)")

### US 22 — Jurnal de profesor separat
**Ca** observator, **vreau** un jurnal al profesorului într-un tab separat de jurnalele studenților, **astfel încât** să văd reflecția profesorului asupra fiecărui sprint.
- **Criterii de acceptare:** tab-ul „Journal" este împărțit în „Student Journals" și „Teacher Journal"; profesorul scrie o reflecție la persoana întâi la finalul fiecărui sprint (<1000 cuvinte), marcată cu `author_role=teacher`; split-ul apare și în istoric.
- **Implementare:** `backend/app/models.py` (`Journal.author_role`), `backend/app/engine/__init__.py` (`teacher_journal`), `backend/app/engine/prompts.py` (`teacher_journal_prompt`), `backend/app/engine/agents.py` (`teacher_journal`), `frontend/src/components/Panels.jsx` (`TeacherJournal`), `frontend/src/pages/ClassroomDetailPage.jsx`
- **Teste:** `backend/tests/test_features.py` (`test_teacher_journal_is_separate_from_student_journals`), `backend/tests/test_simulation.py`

## Epic 7: Iterația v2.2 — scalare, planificare și export

> A treia iterație (Sprint 5): scalarea numărului de studenți, planificarea
> sesiunilor, feedback de la observatori și export de date.

### US 23 — Statisticile păstrate în istoric
**Ca** utilizator, **vreau** ca pagina unei sesiuni arhivate să includă același tab de statistici ca sesiunea live, **astfel încât** evoluția emoțiilor și a notelor să poată fi analizată și după încheiere.
- **Criterii de acceptare:** arhiva conține `emotion_timeline`; pagina History afișează un tab „Statistics" cu graficele de evoluție a emoțiilor, traiectoria notelor și sancțiunile, reconstruite din payload.
- **Implementare:** `frontend/src/components/Stats.jsx` (componentă comună `StatsView`), `frontend/src/pages/HistoryDetailPage.jsx`, `frontend/src/pages/ClassroomStatsPage.jsx`

### US 24 — Mai mulți studenți per sală
**Ca** profesor, **vreau să** pot configura între 2 și 5 studenți într-o sală, **astfel încât** simularea să acopere clase mai mari, nu doar perechi.
- **Criterii de acceptare:** profesorul alege numărul de studenți la configurare; locurile (`student_a..student_e`) se completează dinamic; pauza devine round-robin (fiecare răspunde celui anterior); notele, jurnalele și snapshot-urile emoționale acoperă toți studenții; implicit rămâne 2 (compatibilitate).
- **Implementare:** `backend/app/models.py` (`STUDENT_SLOTS`, `student_slots`, `max_students`), `backend/app/engine/__init__.py` (bucla generalizată pe N studenți), `backend/app/routers/classrooms.py`, `frontend/src/pages/ClassroomDetailPage.jsx`, `frontend/src/components/ClassroomCard.jsx`
- **Teste:** `backend/tests/test_v22_features.py` (`test_classroom_supports_three_students`, `test_five_students_is_the_cap`, `test_third_student_rejected_when_capacity_is_two`)

### US 25 — Programarea sesiunilor
**Ca** profesor, **vreau să** programez ora de start a unei sesiuni, **astfel încât** sala să nu pornească automat înainte de momentul ales, chiar dacă toate locurile sunt ocupate.
- **Criterii de acceptare:** profesorul setează opțional `scheduled_start`; o sală plină dar programată în viitor rămâne `waiting`; un ticker de fundal pornește sălile ajunse la scadență; o oră trecută nu blochează startul.
- **Implementare:** `backend/app/models.py` (`scheduled_start`), `backend/app/engine/__init__.py` (`_schedule_reached`, `_scheduler_loop`, `start_scheduler`), `backend/app/routers/classrooms.py`, `frontend/src/pages/ClassroomDetailPage.jsx`
- **Teste:** `backend/tests/test_v22_features.py` (`test_scheduled_room_does_not_start_before_time`, `test_past_schedule_starts_immediately`)

### US 26 — Rating de lecție de la observatori
**Ca** observator, **vreau să** dau o notă (1–5 stele) și un comentariu lecției, **astfel încât** să ofer feedback fără să fiu autentificat.
- **Criterii de acceptare:** oricine poate trimite un rating (ca la chat-ul de observator); se afișează media și numărul de rating-uri; rating-urile sunt incluse în arhivă și în export; rating-urile date după încheiere apar în istoric.
- **Implementare:** `backend/app/models.py` (`LessonRating`), `backend/app/routers/ratings.py`, `frontend/src/components/RatingPanel.jsx`, `frontend/src/pages/HistoryDetailPage.jsx`
- **Teste:** `backend/tests/test_v22_features.py` (`test_observer_can_rate_lesson`, `test_rating_validation_rejects_out_of_range`, `test_ratings_posted_after_finish_appear_in_history`)

### US 27 — Export PDF al sesiunii și statisticilor
**Ca** utilizator, **vreau să** descarc un PDF al unei sesiuni arhivate, **astfel încât** să am un raport portabil cu rezumat, note, statistici, sancțiuni, rating-uri și jurnale.
- **Criterii de acceptare:** un endpoint generează un PDF la cerere din payload-ul arhivei (rezumat, tabel note, tabel emoții finale per agent, sancțiuni, rating-uri, jurnale); un buton de descărcare există pe pagina History.
- **Implementare:** `backend/app/pdf_report.py` (fpdf2), `backend/app/routers/history.py` (`GET /api/history/{id}/pdf`), `frontend/src/pages/HistoryDetailPage.jsx`
- **Teste:** `backend/tests/test_v22_features.py` (`test_pdf_export_of_archived_session`)

### US 28 — Emoțiile profesorului în statistici
**Ca** observator, **vreau să** văd și evoluția emoțională a profesorului în pagina de statistici, **astfel încât** să urmăresc cum reacționează la performanța clasei.
- **Criterii de acceptare:** profesorul primește un snapshot emoțional la fiecare sprint (alături de studenți); emoțiile profesorului evoluează din media notelor și din predarea repetată; pagina de statistici afișează un grafic dedicat profesorului.
- **Implementare:** `backend/app/engine/__init__.py` (snapshot + reacția emoțională a profesorului), `frontend/src/components/Stats.jsx`

---

## Tabelul de backlog

Prioritizare prin metoda **MoSCoW**, estimare în story points (Fibonacci). Statusul reflectă versiunea curentă (v2.1). Sprinturile 1–3 au livrat produsul de bază (v2); Sprintul 4 a livrat iterația de rafinare (v2.1).

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
| US 21 | Claritatea rolurilor (profesor vs coleg) | 6 | Must | 2 | 4 | ✅ Done | ✅ |
| US 15 | Dialog responsiv în pauză | 6 | Should | 3 | 4 | ✅ Done | ✅ |
| US 19 | Model emoțional extins (6 emoții) | 6 | Should | 5 | 4 | ✅ Done | ✅ |
| US 22 | Jurnal de profesor separat | 6 | Should | 3 | 4 | ✅ Done | ✅ |
| US 20 | Pagină de statistici | 6 | Should | 5 | 4 | ✅ Done | ✅ |
| US 17 | Stop & delete sală (profesor) | 6 | Should | 3 | 4 | ✅ Done | ✅ |
| US 16 | Continuitate / memorie între sprinturi | 6 | Could | 5 | 4 | ✅ Done | — |
| US 18 | ID sală vizibil pentru agenți | 6 | Could | 1 | 4 | ✅ Done | — |
| US 24 | Mai mulți studenți per sală (2–5) | 7 | Should | 8 | 5 | ✅ Done | ✅ |
| US 23 | Statistici păstrate în istoric | 7 | Should | 3 | 5 | ✅ Done | — |
| US 27 | Export PDF al sesiunii | 7 | Should | 5 | 5 | ✅ Done | ✅ |
| US 26 | Rating de lecție (observatori) | 7 | Should | 3 | 5 | ✅ Done | ✅ |
| US 25 | Programarea sesiunilor | 7 | Could | 5 | 5 | ✅ Done | ✅ |
| US 28 | Emoțiile profesorului în statistici | 7 | Could | 2 | 5 | ✅ Done | — |

**Backlog viitor (nepreluat încă):** WebSockets în loc de polling (push live, latență mai mică), rating de lecție per sprint (nu doar pe sală), export PDF cu grafice randate ca imagini, programare recurentă a sesiunilor, integrare cu un model de limbaj pentru rezumarea automată a sesiunii.
