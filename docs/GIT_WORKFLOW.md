# 🌿 Source control cu Git

> Acoperă cerința: **source control cu git (branch creation, merge/rebase, pull requests, minim 5 commits/student) — 1 pct.**

## Strategia de branching

- `main` — mereu funcțional; protejat prin pull request-uri.
- `feature/<nume>` — câte un branch per user story / funcționalitate.
- `fix/<nume>` — branch-uri pentru bug-uri raportate (vezi [`BUG_REPORTS.md`](BUG_REPORTS.md)).
- Integrarea se face prin **pull request** cu review; conflictele se rezolvă prin `merge` (istoricul conține și `Merge branch ...` rezultate din sincronizări `git pull` între colegi).

## Branch-uri create în repository

`feature/achivements`, `feature/added-database`, `feature/agentic-evals`, `feature/diary-break`, `feature/journal`, `feature/new-behavioral-changes`, `feature/reset_sprint`, `feature/save-progress`, `feature/websockets`, `fix/agents`, `frontend`.

## Pull request-uri reprezentative

| PR | Branch | Conținut |
|----|--------|----------|
| #4 | `feature/achivements` | Sistemul de achievements |
| #5 | `feature/websockets` | Streaming live către frontend |
| #10 | `feature/reset_sprint` | Buton de reset al sprintului (a inclus și rezolvare de conflicte prin merge din `main`) |
| #11 | `feature/journal` | Logica jurnalelor studenților |
| #13 | `fix/agents` | Bugfix pe scripturile agenților (raportat ca issue, rezolvat prin PR) |

## Commits per student (minim 5/student)

Statistici din `git log` (`git shortlog -sn`):

| Student | Conturi git | Commits |
|---------|-------------|---------|
| Bianca Amanea | `bbiAncah` | 24 |
| Irina Tănase | `TanAnIrina`, `Irina Tanase` | 17 |
| Antonia Voinescu | `Antonia Voinescu`, `anto-v` | 5 |

Total: **46 de commits** pe `main`, plus commits adiționale pe branch-urile de feature ne-merge-uite.

## Reguli de echipă

1. Niciun commit direct pe `main` pentru schimbări funcționale — totul prin PR.
2. Mesaje de commit descriptive; pentru schimbări mari, mesajul și descrierea PR-ului se redactează cu un tool AI pe baza diff-ului (vezi [`AI_USAGE_REPORT.md`](AI_USAGE_REPORT.md#4-source-control-git)).
3. CI (`ci.yml`) trebuie să fie verde înainte de merge.
4. Branch-urile de fix pornesc dintr-un issue GitHub care descrie bug-ul (template în `.github/ISSUE_TEMPLATE/bug_report.yml`).

## Cum aducem v2 în repository (fără a pierde istoricul)

```bash
git checkout -b v2-rebuild
# se copiază conținutul v2 peste working tree
git add -A
git commit -m "v2: full-stack rebuild (FastAPI + React + tests + CI/CD)"
git push -u origin v2-rebuild
# apoi se deschide un PR "v2 rebuild" -> main, cu review de la colegi
```
