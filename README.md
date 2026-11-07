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
- **Egendefinert oppgave** med kategori-velger og **emoji**: appen gjetter en
  passende emoji automatisk ut fra teksten (f.eks. «gå tur» → 🚶, «vaske bad» →
  🧽, «ringe» → 📞) mens du skriver, så egne oppgaver ikke blir like. Trykk
  emoji-knappen for å velge en selv, eller 🪄 for å la appen velge.
- **Rediger oppgave:** trykk på et gjøremål for å åpne et redigerings-ark –
  endre **dato** (hurtigvalg I dag / I morgen / ±1 dag + datovelger), tittel,
  **emoji** og kategori, eller slett. Flyttede oppgaver dukker opp på ny dato hos begge.
- **Underpunkter:** åpne en oppgave og legg inn en sjekkliste (f.eks.
  «Avfallsstasjonen» → brannslukker, kurv, hageavfall). Skill flere med komma,
  huk av underveis, × fjerner. Kortet viser fremdrift (☑ 2/5) og hva som
  gjenstår. Snarvei: skriv «Avfallsstasjonen: kurv, hageavfall» i feltet for
  egen oppgave. Underpunkter lagres med en gang og synkes som del av oppgaven.
- **Egne hurtigvalg** (⚙️ Innstillinger) som deles med alle på lista.
- **Daglige rutiner** (⚙️ Innstillinger): oppgaver som legges inn automatisk
  hver dag (forhåndsfylt med pusse tenner William, gå tur med Charlie, oppvask,
  vaske lekematte, gi inhalasjon). Legg til egne selv. Sync-trygt – ingen
  duplikater mellom telefonene, og en du sletter kommer ikke tilbake samme dag.
- **Redigerbare kategorier** (⚙️ Innstillinger) – gi dem egne navn og farger,
  eller lag nye. Fargevelgeren viser navnene tydelig.
- **Handleliste** (🛒-fanen) – en delt liste der den ene legger til varer
  hjemmefra og den andre krysser dem av i butikken. Hurtigvalg for vanlige
  varer, rask inntasting (skill flere med komma), auto-emoji, avhukede varer
  synker ned, og «Fjern avhukede» rydder etter handleturen. Synkes i sanntid.
- **Forfalte oppgaver:** et eget felt øverst i Planlagt samler gjøremål som
  ligger på en tidligere dato uten å være fullført, med etikett for hvor lenge
  siden. Flytt én til i dag, «Flytt alle til i dag», rediger dato, eller fullfør
  – alt fra feltet. Et tall-merke på Planlagt-fanen viser antallet.
- **Fikse hjemme** (🛠️-fanen) – punkter per rom, delt i *Fikse* og *Kjøpe*,
  forhåndsfylt med lista over det som skal gjøres før salg. Legg til raskt
  (skill flere med komma), trykk på et punkt for å redigere tittel, rom, type
  og notat, eller planlegge det på **én dag** eller **over flere dager**
  (hurtigvalg for helgen, i dag + i morgen, neste 7 dager). Planlagte punkter
  får egen turkis prikk i kalenderen og vises under Planlagt på hver av dagene
  («Dag 2 av 3»). Visning per rom (med fremdrift) eller etter dato, filter for
  Fikse/Kjøpe, og kjøpepunkter kan sendes rett til handlelista. Synkes som
  `fix` i Firebase; startlista legges inn én gang per husholdning, og slettinger
  lagres som myk sletting så de ikke dukker opp igjen fra en annen telefon.
- **Medisiner** (💊-fanen) – en enkel medisin-sporing i stil med Medisafe:
  legg inn medisiner med dose, antall, ikon, ett eller flere tidspunkt og hvilke
  dager. Dagens doser vises gruppert per klokkeslett; trykk sjekk-knappen og velg
  **Nå / På planlagt tid / Velg tidspunkt** for å registrere at den er tatt
  (grønn markering med «Tatt kl …»). Forfalte doser får en diskret gul utheving,
  og et tall-merke på fanen viser hvor mange som gjenstår i dag. Egen logg over
  nylig tatt, pause-bryter per medisin, og alt synkes mellom telefonene.
  **Push-varsel** (valgfritt, se under) minner deg på når det er tid.
- **Renovasjon / kildesortering** (⚙️ Innstillinger) – henter faktiske
  tømmedatoer for adressen fra Min Renovasjon (Horten kommune) og viser en
  **diskret, men tydelig stripe** øverst i Planlagt de dagene det hentes
  (restavfall 🗑️, papp/papir 📦, glass/metall 🫙, plast 🛍️), med chips for hver
  fraksjon og et «sett fram i kveld»-hint kvelden før. Hentedager får en liten
  ♻-markering i kalenderen. Matavfall hentes ofte og er skjult som standard
  (kan slås på). Ingen avkryssing – påminnelsen er ren informasjon og blir
  aldri forfalt. Datoene hentes på telefonen og caches lokalt, og appen
  **sjekker automatisk** (uten godkjenning) at ventedagene fortsatt stemmer og
  oppdaterer dem når de blir gamle.
- **Historikk** over alt som er gjort, gruppert per dag med tidspunkt (og en
  merknad hvis noe ble fullført på en annen dag enn planlagt).
- **Deling og sanntids-synk** (⚙️ Innstillinger) via Firebase Realtime Database
  (REST + `EventSource`, ingen SDK/CDN).
- **Fremdriftsring**, streak og konfetti når du huker av. 🎉
- **Sveip tilbake** – dra fingeren fra venstre kant mot høyre for å gå tilbake
  (lukker et åpent ark, forlater innstillinger til fanen du kom fra, eller går
  tilbake til Planlagt), slik man er vant til i iOS-apper.
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

## Medisin-varsler (push) – oppsett

Selve medisin-sporingen virker uten noe oppsett. For å få **push-varsel** på
telefonen når det er tid for en medisin (også når appen er lukket), sender en
gratis, planlagt **GitHub Actions**-jobb varslene. Du setter det opp én gang:

**Forutsetninger:** appen må være lagt til på **Hjem-skjerm** (iOS 16.4+) og åpnet
derfra, og **delt liste** må være tilkoblet (⚙️ → Deling og synk) – medisinene og
abonnementene ligger i den samme Firebase-basen som jobben leser fra.

1. **Legg inn tre «repository secrets»** i GitHub: repoet → **Settings → Secrets
   and variables → Actions → New repository secret**:
   - `FIREBASE_DB_URL` – database-URL-en din (⚙️ → 💊 Medisin & varsler viser
     verdien med «Kopier» når synk er tilkoblet).
   - `FIREBASE_HOUSEHOLD` – husholdnings-koden din (samme sted).
   - `VAPID_PRIVATE_KEY` – den private nøkkelen (få den av den som satte opp
     appen; den **må ikke** sjekkes inn i koden).
2. **Slå på varsler i appen:** ⚙️ → 💊 Medisin & varsler → **Slå på varsler**
   (eller «Få påminnelse» øverst i 💊-fanen), og godta varsler. Gjenta på hver
   telefon som skal få varsel.
3. Ferdig. Jobben kjører hvert 5. minutt (`.github/workflows/med-reminders.yml`)
   og sender et varsel når en dose er forfalt og ikke registrert som tatt. Den
   sender aldri samme dose to ganger, og rydder bort abonnement som er utløpt.
   Du kan kjøre den manuelt fra **Actions**-fanen (workflow_dispatch) for å teste.

Teknisk: web-push med VAPID, abonnement lagres i Firebase under husholdningen
(`pushSubs`), avsenderkoden ligger i `push/` (`send.mjs` + ren, testbar
`due.mjs`, `node test.mjs`). Den offentlige VAPID-nøkkelen er innebygd i appen og
jobben; kun den private nøkkelen er hemmelig.

## Filer

| Fil | Rolle |
|-----|-------|
| `index.html` | Hele appen (HTML + CSS + JS) |
| `manifest.webmanifest` | PWA-manifest (navn, farger, ikoner) |
| `sw.js` | Service worker – offline-cache + mottak av push-varsler |
| `push/` | Avsender for medisin-varsler (`send.mjs`, `due.mjs`, `test.mjs`) |
| `.github/workflows/med-reminders.yml` | Planlagt jobb som sender push-varslene |
| `icon-180/192/512.png`, `icon-maskable-512.png` | Hjem-skjerm-ikoner |
| `.nojekyll` | Deaktiverer Jekyll på GitHub Pages |
