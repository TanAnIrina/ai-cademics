# 🐞 Raportarea bug-urilor și rezolvarea prin pull request

> Acoperă cerința: **raportare bug și rezolvare cu pull request — 1 pct.**

## Procesul

1. **Raportare** — bug-ul se deschide ca **GitHub Issue** folosind template-ul
   [`.github/ISSUE_TEMPLATE/bug_report.yml`](../.github/ISSUE_TEMPLATE/bug_report.yml)
   (pași de reproducere, comportament așteptat vs. observat, loguri).
2. **Diagnoză** — traceback-ul + fișierele relevante se analizează cu un tool AI pentru a localiza cauza.
3. **Fix** — se creează un branch `fix/<nume>` din `main`, cu commit-uri care referă issue-ul (`Fixes #<nr>`).
4. **Pull request** — PR-ul leagă issue-ul, trece prin CI (lint + 38 teste) și prin review de coleg.
5. **Închidere** — la merge, issue-ul se închide automat prin `Fixes #<nr>`.

## Bug-uri documentate

### BUG-1 — Agenții nu mai răspundeau după prima rundă
- **Simptom:** după primul sprint, scripturile agenților rămâneau blocate în așteptare; simularea nu mai avansa.
- **Cauză:** gestionarea greșită a stării conversației între runde în scripturile agenților.
- **Rezolvare:** branch `fix/agents` → **PR #13** (merged în `main`).
- **Prevenție:** în v2, avansarea fazelor este testată automat în `backend/tests/test_simulation.py` (o simulare completă rulează în CI cu providerul mock).

### BUG-2 — Progresul sesiunii nu se salva corect
- **Simptom:** la întreruperea aplicației, progresul sprintului curent se pierdea.
- **Cauză:** scrierea în baza de date se făcea doar la finalul sesiunii, nu după fiecare fază.
- **Rezolvare:** commit `381eed5 — issue: fixed saving progress` pe branch-ul `feature/save-progress`, integrat prin merge în `main`.
- **Prevenție:** în v2, fiecare fază persistă imediat (`Message`, `Grade`, `Journal`, `EvalResult`), iar testele `test_chat_history.py` verifică faptul că arhiva conține tot conținutul.

### BUG-3 — Butonul de reset lăsa sala într-o stare inconsistentă
- **Simptom:** după reset, sprintul repornit afișa date din rularea anterioară.
- **Rezolvare:** serie de commit-uri pe `feature/reset_sprint` (`reset button`, `reset button 2/3`, `fixed`), integrate prin **PR #10**, care a inclus și rezolvarea unui conflict prin `Merge branch 'main' into feature/reset_sprint`.
- **Prevenție:** în v2, ciclul de viață al sălii este un automat de stări explicit (`waiting → running → finished → archived`, vezi [`DIAGRAMS.md`](DIAGRAMS.md#3-diagrama-de-stări--ciclul-de-viață-al-unei-săli)), testat în `test_classrooms.py` și `test_simulation.py`.
