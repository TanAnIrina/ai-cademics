# 🌍 Punerea aplicației pe internet (domeniu + HTTPS)

Acest ghid pune AI-cademics pe un domeniu public, cu **HTTPS automat** (Let's Encrypt prin Caddy). Exemplul folosește un droplet DigitalOcean (Ubuntu) și domeniul `numecreativ.dev`, dar pașii sunt identici pe orice VPS.

Rezultatul: aplicația va fi accesibilă la `https://aicademics.numecreativ.dev`.

```
internet ──HTTPS──▶ Caddy (cert Let's Encrypt) ──▶ nginx (SPA + /api) ──▶ FastAPI ──▶ SQLite
```

---

## 0. De ce ai nevoie
- Un VPS cu IP public (ex. droplet Ubuntu 22.04+).
- Un domeniu pe care îl controlezi (DNS administrabil).
- Acces SSH la server.

## 1. DNS — leagă domeniul de server

În panoul de DNS al domeniului, creează un **A record** care arată spre IP-ul dropletului:

| Tip | Nume (host) | Valoare |
|-----|-------------|---------|
| A | `aicademics` | `<IP-ul-dropletului>` |

Asta îți dă `aicademics.numecreativ.dev`. (Dacă vrei pe domeniul rădăcină, fă A record pe `@`.)

Verifică propagarea (poate dura câteva minute):
```bash
dig +short aicademics.numecreativ.dev
# trebuie să întoarcă IP-ul dropletului
```

## 2. Pe server — instalează Docker

```bash
ssh root@<IP-ul-dropletului>

# Docker Engine + plugin compose, oficial
curl -fsSL https://get.docker.com | sh
docker compose version    # confirmă că merge
```

## 3. Deschide porturile 80 și 443

Caddy are nevoie de 80 (provizionarea certificatului) și 443 (HTTPS). Dacă folosești firewall-ul ufw:
```bash
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable
```
Dacă ai și un **DigitalOcean Cloud Firewall** pe droplet, deschide acolo aceleași porturi (80, 443).

> ⚠️ Memento din proiectele tale anterioare: dacă `systemd-resolved` ocupă vreun port, nu e cazul aici — Caddy folosește 80/443, nu 53. Dar verifică să nu ai deja un nginx/apache pe server care ocupă 80: `sudo ss -tlnp | grep ':80'`. Dacă da, oprește-l (`systemctl stop nginx`).

## 4. Adu codul pe server

```bash
git clone https://github.com/TanAnIrina/ai-cademics.git ~/aicademics
cd ~/aicademics
```
(După ce faci merge la branch-ul `v2-rebuild` în `main`. Până atunci: `git clone -b v2-rebuild ...`.)

## 5. Configurează producția

```bash
cp .env.prod.example .env.prod
nano .env.prod
```
Completează:
```
DOMAIN=aicademics.numecreativ.dev
ACME_EMAIL=adresa-ta@email.com
```

## 6. Pornește stack-ul

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

Prima pornire durează un pic (build + Caddy cere certificatul de la Let's Encrypt). Urmărește logurile:
```bash
docker compose -f docker-compose.prod.yml logs -f caddy
# cauți linii de tip "certificate obtained successfully"
```

## 7. Verifică

Deschide în browser:
```
https://aicademics.numecreativ.dev
```
Ar trebui să vezi aplicația, cu lacăt verde (certificat valid). Docs API la `https://aicademics.numecreativ.dev/api` → redirecționează către backend; UI-ul interactiv FastAPI e la `/docs` doar dacă îl expui (vezi nota de mai jos).

---

## Operare

**Stare / loguri / oprire:**
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml down        # oprește
```

**Actualizare după ce împingi cod nou:**
```bash
cd ~/aicademics
git pull
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

**Persistența datelor:** baza SQLite trăiește în volumul Docker `aicademics-data`, iar certificatele în `caddy-data` — supraviețuiesc unui `down`/`up` și unui restart al serverului. Backup:
```bash
docker run --rm -v aicademics_aicademics-data:/data -v $PWD:/backup alpine \
  tar czf /backup/aicademics-db-$(date +%F).tar.gz -C /data .
```

---

## Deploy automat din GitHub (opțional)

`.github/workflows/deploy.yml` poate face deploy-ul singur la fiecare tag `v*`. Activează-l așa:

1. Pe server, asigură-te că repo-ul e clonat în `~/aicademics` și că `.env.prod` există.
2. În GitHub → Settings → Secrets and variables → Actions, adaugă:
   - **Variable** `DEPLOY_ENABLED` = `true`
   - **Secrets**: `VPS_HOST` (IP), `VPS_USER` (ex. `root`), `VPS_SSH_KEY` (cheia privată SSH).
3. Creează un tag de release:
   ```bash
   git tag v2.0.0 && git push origin v2.0.0
   ```
   Workflow-ul construiește imaginile și rulează pe server `docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build`.

Fără variabila `DEPLOY_ENABLED`, pasul de deploy se sare și workflow-ul rămâne verde — deci e safe și fără server configurat.

---

## Variante

**Subdomeniu vs. rădăcină** — schimbă doar `DOMAIN` în `.env.prod` (și A record-ul DNS). Caddy cere automat certificatul potrivit.

**Mai multe domenii / și `www`** — în `Caddyfile`, pune ambele nume pe primul rând:
```
aicademics.numecreativ.dev, www.aicademics.numecreativ.dev {
    ...
}
```

**Expunerea `/docs` (Swagger UI)** — backend-ul servește docs la `/docs`, dar nginx face proxy doar pe `/api`. Pentru demo poți arăta docs prin tunel SSH local (`ssh -L 8000:localhost:8000 ...` după ce publici temporar portul backend) sau adăugând o locație `/docs` și `/openapi.json` în `frontend/nginx.conf`. Nu e necesar pentru funcționarea aplicației.

**Agenți pe modele locale (Ollama) pe server** — dropleturile mici nu au GPU; modelele mici rulează pe CPU, încet. Pentru demo-ul live, providerul `mock` (default) e suficient și determinist. Dacă vrei totuși Ollama pe server, instalează-l separat și pune `AICADEMICS_*` corespunzător; altfel rulează agenții self-hosted de pe laptopul tău, pointați spre domeniu (vezi secțiunea Self-hosted agents din README).
