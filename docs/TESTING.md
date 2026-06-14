# ✅ Teste automate & evals pentru agenți

> Acoperă cerința: **teste automate (inclusiv evals pentru agenți) — 2 pct.**

## Rulare

```bash
cd backend
pip install -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing     # sau: make test
```

Testele rulează automat în CI la fiecare push și pull request ([`ci.yml`](../.github/workflows/ci.yml)). Întreaga suită folosește providerul **mock** (determinist), deci nu are nevoie de chei API sau de rețea — o simulare completă de clasă rulează efectiv în pipeline.

## Suita de teste — 38 de teste pytest

| Fișier | Acoperă |
|--------|---------|
| `tests/test_auth.py` | Login, sesiuni, logout, roluri, acces refuzat fără token |
| `tests/test_classrooms.py` | Creare săli, join/leave pe locuri, configurare doar de profesor, validări, estimarea timpului |
| `tests/test_simulation.py` | Pornirea automată la ocuparea locurilor, rularea completă a fazelor (lesson → test → grading → break → journal), generarea notelor, jurnalelor și emoțiilor, arhivarea |
| `tests/test_chat_history.py` | Chat-ul observatorilor, arhiva completă a sesiunilor încheiate, endpoint-urile de istoric |
| `tests/test_evals.py` | Toate verificările de evals, pe cazuri pozitive și negative |
| `tests/conftest.py` | Fixture-uri: aplicație pe DB SQLite temporar, clienți autentificați per rol, fază de simulare comprimată |

## Evals pentru agenți (`backend/app/engine/evals.py`)

Fiecare regulă din prompturile agenților este transformată într-o **verificare deterministă** care rulează atât în producție (rezultatele apar live în UI și în arhivă), cât și în CI:

| Eval | Agent | Regula din prompt verificată |
|------|-------|------------------------------|
| `question_count` | Profesor | Testul are **exact 10 întrebări** |
| `question_relevance` | Profesor | ≥60% din întrebări împart vocabular cu lecția predată |
| `answer_on_topic` | Student | Răspunsul are suprapunere de cuvinte-cheie cu întrebarea/lecția |
| `grade_validity` | Profesor | Nota este întreg în 1–10 și are justificare nevidă |
| `break_no_subject_leak` | Student | În pauză **nu se menționează subiectul lecției** (regulă critică din prompt) |
| `journal_first_person` | Student | Jurnalul este scris la persoana întâi |
| `journal_length` | Student | Jurnalul are **sub 1000 de cuvinte** |

Fiecare verificare întoarce `{scope, check_name, passed, score (0..1), detail}` — `passed` este poarta dură, `score` e un semnal de calitate. Rezultatele sunt persistate (`EvalResult`) și afișate per sesiune.

**De ce evals deterministe și nu LLM-as-judge?** Pentru că trebuie să ruleze identic în CI (fără chei API, fără nedeterminism) și pentru că regulile din prompturi sunt verificabile mecanic (numărare, suprapunere de cuvinte-cheie, regex). Modelele mici locale halucinează mult — exact de aceea poarta de calitate trebuie să fie în afara modelului.

## Acoperire și calitate

- `pytest --cov=app` rulează în CI cu raport `term-missing`.
- Lint: `ruff check .` (stil + erori comune), tot în CI.
- Frontend: build de producție (`npm run build`) în CI — eșuează la erori de sintaxă/import.
