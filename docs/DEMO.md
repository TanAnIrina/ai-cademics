# 🎬 Demo live & demo offline (screencast)

> Acoperă cerințele din partea A: **live demo** + **demo offline salvat (ex. YouTube)** + **minim 2 agenți AI cu modele de limbaj mici, locale, ca parte din funcționalitate**.

## Cei 2+ agenți AI din funcționalitate

Aplicația are **3 agenți AI** ca parte centrală a funcționalității (nu agenți de scris cod):

1. **Profesorul** — predă lecția, generează exact 10 întrebări, notează cu justificare, dă sancțiuni/recompense.
2. **Studentul 1** și **Studentul 2** — răspund la test, conversează în pauză (cu subiectul interzis), își scriu jurnalele, au stări emoționale care le influențează tonul.

Agenții pot rula pe **modele de limbaj mici, locale, prin Ollama** (ex. `llama3`, `qwen2`) — exact scenariul din cerință („chiar dacă modelele respective halucinează mult"; halucinațiile sunt chiar măsurate de evals).

## Scenariul demo-ului live (≈5–7 minute)

1. **Pornire:** `docker compose up --build` → deschide `http://localhost:8080`.
2. **Login ca profesor** → creează/alege o sală → setează subiectul (ex. *Graph Theory*), durata sprintului, pauza, numărul de sprinturi; arată graficul live timp-vs-sprinturi.
3. **Agenți locali:** în două terminale, pornește cei doi studenți pe modele mici locale:
   ```bash
   python backend/agent_client.py --role student --name Ada   --classroom 1 --model llama3
   python backend/agent_client.py --role student --name Linus --classroom 1 --model qwen2
   ```
   (alternativ, providerul `ollama` direct din backend; pentru un demo fără GPU/fără chei, providerul `mock` rulează totul determinist)
4. **Simularea pornește automat** la ocuparea celui de-al 3-lea loc — arată live: lecția, cele 10 întrebări, răspunsurile, notele cu justificare, emoțiile per loc.
5. **Evals live:** arată panoul de evaluări automate — care verificări au trecut/picat și de ce (aici se văd halucinațiile modelelor mici).
6. **Pauza + jurnalele:** small talk fără subiect, apoi jurnalele la persoana întâi.
7. **Arhiva:** la final, sesiunea apare în History cu tot conținutul; deschide o sesiune arhivată.
8. **Bonus (1 min):** arată repo-ul — PR-uri, CI verde, acest `docs/`.

## Demo offline (screencast)

- **Tool recomandat:** [OBS Studio](https://obsproject.com/) (gratuit, Windows/Linux/macOS) — Display Capture + microfon; alternativ, înregistrarea nativă din Google Meet/Zoom la prezentarea cu screen sharing.
- **Setări:** 1080p, 30fps, microfon pornit, durata ≤ 10 minute, urmărind scenariul de mai sus.
- **Publicare:** încărcat pe YouTube ca **Unlisted**, iar linkul se adaugă aici și în README:

> 🔗 **Link demo offline (YouTube):** _de completat după înregistrare_

**Sfat pentru înregistrare:** setează `AICADEMICS_SIM_PHASE_SECONDS` la o valoare mică (default `0.4`) ca un sprint complet să ruleze în câteva secunde, și folosește 2 sprinturi ca să se vadă și arhivarea.
