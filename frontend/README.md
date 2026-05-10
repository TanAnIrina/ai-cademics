# ai-cademics frontend

React + Vite frontend pentru backendul tău (Main.py + database.py + achievements.py).

## Pornire

```bash
npm install
npm run dev
```

Apoi deschide `http://localhost:5173`.

> Backendul tău (Main.py) trebuie să ruleze pe `http://localhost:8000`.
> Dacă rulezi pe alt IP/port, schimbă în `src/api.js` linia:
> ```js
> export const API_BASE = "http://192.168.1.42:8000";
> ```

## Pagini

| Tab | Endpoint-uri folosite |
|---|---|
| **Dashboard** | `GET /`, `/api/leaderboard`, `/api/stats`, `/api/emotions`, `/api/sprints?limit=8` |
| **Students** | `/api/students`, `/api/students/{name}`, `/api/students/{name}/progression`, `/api/students/{name}/emotions/history` |
| **Sprints** | `/api/sprints`, `/api/sprints/{id}` |
| **Achievements** | `/api/achievements`, `/api/students/{name}/badges` |
| **Run** | `POST /api/sprint/run`, `/api/break/run`, `/api/session/run`, `/api/emotions/reset`, `/api/db/reset` |

## Mapare către backend

Toate endpoint-urile sunt centralizate în `src/api.js` — dacă schimbi ceva în Main.py
(rute, parametri), modifici doar acolo, restul componentelor consumă prin acele funcții.

## Note despre sprinturi lungi

`POST /api/sprint/run` blochează minute (LLM-urile durează). Frontendul:
- arată un spinner cu cronometru
- dezactivează butoanele cât rulează
- afișează rezultatul cu summary, badges deblocate, conversația de break

Pentru progres live (Q1 → Q2 → ...) ar trebui adăugat WebSocket sau Server-Sent Events
în Main.py. Acum frontendul așteaptă răspunsul final și afișează totul deodată.

## Structură

```
src/
├── api.js              # toate apelurile către backend, într-un singur loc
├── App.jsx             # tab navigation
├── main.jsx            # React entry
├── styles.css          # toate stilurile
├── components/
│   └── UI.jsx          # Loading / ErrorBox helpers
└── pages/
    ├── Dashboard.jsx
    ├── StudentsPage.jsx       # listă + detail (charts, badges)
    ├── SprintsPage.jsx        # listă + detail (lecție, întrebări, răspunsuri)
    ├── AchievementsPage.jsx   # galerie cu rarity colors
    └── RunPage.jsx            # butoane Sprint / Break / Full Session
```

## Achievements — rarity colors

Sistemul tău de rarities din `achievements.py` e mapat vizual:
- 🔘 **common** — gri (#9CA3AF)
- 🟢 **uncommon** — verde (#10B981)
- 🔵 **rare** — albastru (#3B82F6)
- 🟣 **epic** — mov (#8B5CF6)
- 🟡 **legendary** — auriu (#F59E0B)

Badge-urile deblocate au glow în culoarea rarității, cele locked sunt grayscale.
