# Hjemmetavla 🏠✅

En liten, selvstendig **to-do med kalender** for oppgaver i hjemmet. Ren
frontend (HTML/CSS/JS i én fil) – ingen server, ingen bygging, ingen innlogging.
Data lagres lokalt i nettleseren (`localStorage`), med valgfri **sanntids-deling**
mellom flere (f.eks. deg og partneren din).

## Funksjoner

- **Planlegg dagen i forveien** – appen åpner på **i morgen** som standard, men
  du kan bytte til **i dag** med ett trykk på forsiden, eller endre hva som
  vises ved oppstart i innstillingene.
- **Kalender** med prikker på dager som har oppgaver (fargekodet per kategori,
  grønn når alt er gjort). Trykk en dato for å planlegge akkurat den dagen.
- **Hurtigvalg** for de vanligste oppgavene:
  🐕 Gå tur med Charlie · 🧹 Vaske huset · 🌀 Støvsuge ·
  🍼 Bade William · 🛁 Bade Charlie · 🧺 Vaske klær
- **Egendefinert oppgave** med kategori-velger.
- **Egne hurtigvalg** (⚙️ Innstillinger) som deles med alle på lista.
- **Redigerbare kategorier** (⚙️ Innstillinger) – gi dem egne navn og farger,
  eller lag nye. Fargevelgeren viser navnene tydelig.
- **Historikk** over alt som er gjort, gruppert per dag med tidspunkt.
- **Deling og sanntids-synk** (⚙️ Innstillinger) via Firebase Realtime Database
  (REST + `EventSource`, ingen SDK/CDN).
- **Fremdriftsring**, streak og konfetti når du huker av. 🎉
- **iPhone-tilpasset PWA** – kan legges til på hjem-skjermen som en app/widget.

## Kjøre appen

**Åpne direkte:** dobbeltklikk `index.html` – fungerer i enhver nettleser.

**Via GitHub Pages (i nettleseren):**

1. Repo → **Settings → Pages**.
2. **Build and deployment → Source: Deploy from a branch**.
3. Velg branch **`main`** og mappe **`/ (root)`**, lagre.
4. Etter et par minutter er appen på
   `https://<bruker>.github.io/<repo>/`.

`.nojekyll` sørger for at alle filer serveres uendret.

**Legge til på iPhone (hjem-skjerm/widget):** åpne Pages-URL-en i **Safari** →
del-knappen → **Legg til på Hjem-skjerm**. Ikon + fullskjerm-modus er satt opp via
`manifest.webmanifest` og `apple-touch-icon`. `sw.js` cacher appen for offline-bruk.

## Deling og synk (valgfritt)

Uten synk er alt lokalt i din nettleser. For å dele samme liste med andre:

1. Opprett et gratis **Firebase**-prosjekt og en **Realtime Database**
   (`console.firebase.google.com` → Build → Realtime Database).
2. Sett databasereglene til å tillate lesing/skriving på husholdninger:
   ```json
   { "rules": { "households": { "$h": { ".read": true, ".write": true } } } }
   ```
3. I appen: **⚙️ → Deling og synk** → lim inn database-URL-en, velg en hemmelig
   husholdnings-kode, trykk **Koble til**.
4. Trykk **🔗 Del lenke med andre** og send lenken. Motparten åpner den og
   trykker **Koble til delt liste** – da er dere synkronisert i sanntid.

Teknisk: skriving med `fetch` (PUT/DELETE) mot REST-endepunktet, sanntid via
`EventSource` (Firebase SSE) – ingen Firebase-SDK, ingen ekstra CDN. Merk: hvem
som helst med URL **og** kode kan se/endre listen, så bruk en kode som er
vanskelig å gjette.

## Filer

| Fil | Rolle |
|-----|-------|
| `index.html` | Hele appen (HTML + CSS + JS) |
| `manifest.webmanifest` | PWA-manifest (navn, farger, ikoner) |
| `sw.js` | Service worker – offline-cache av app-skallet |
| `icon-180/192/512.png`, `icon-maskable-512.png` | Hjem-skjerm-ikoner |
| `.nojekyll` | Deaktiverer Jekyll på GitHub Pages |
