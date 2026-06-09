# Park Nordic – felles innlogging og tilgangsstyring: utrulling

**Til:** Thomas (deploy) · **Fra:** changeset bygget og testet mot en kopi.
**Status:** `pn-auth` + migrasjon er ferdig og testet (33 tester grønt: 23 pytest, 5
node:test, 5 FastAPI-dep). Integrasjonsmodulene (Node/FastAPI/nginx/systemd) er
drop-in, kontrakt-testet mot samme JWT. Portalen (`parknordic_dashboard.html`) har
felles innlogging + admin-skjerm bak `LAUNCHER_MODUS`.

> **Hvorfor drop-in og ikke direkte i Oppdrag/Sanksjon:** kildekoden til Oppdrag
> (`/opt/banenor`) og Sanksjon (`/opt/parknordic`) er ikke i dette repoet. Modulene
> under `integrasjon/` er laget for å limes inn med minimale, presise endringer –
> se hvert avsnitt. Verifiser mot den faktiske koden før du melder ferdig.

---

## Hva er i changesettet

```
pn-auth/                    Felles auth-tjeneste (FastAPI). FERDIG + testet.
  app/                      config (secret-or-die), db, security (bcrypt+JWT+ratelimit), main (API)
  migrate.py                Master-DB-migrasjon (Sanksjon SQLite + import Oppdrag data.json)
  schema.sql  requirements.txt  .env.example  run.sh  README.md  tests/
integrasjon/
  oppdrag-node/pnAuth.js    Express-middleware (verifiserer pn_auth, krever permissions.oppdrag)
  sanksjon-fastapi/pn_auth.py  FastAPI-avhengighet (krever permissions.sanksjon)
  nginx/kontrollverktoy.parknordic.no.conf  Headere/HSTS/TLS + auth_request for Datakvalitet
  systemd/                  pn-auth.service + herdet banenor.service / parknordic.service
parknordic_dashboard.html   Portal: felles innlogging + «Brukere og tilganger» (LAUNCHER_MODUS)
DEPLOY.md                   Dette dokumentet
```

---

## Rekkefølge (følg `CLAUDE_CODE_BRIEF.md` – ufravikelig)

### Steg 0 – generér delt hemmelighet
```bash
openssl rand -hex 32      # → AUTH_SECRET. SAMME verdi i pn-auth, Oppdrag og Sanksjon.
```

### Steg 1 – LUKK SIKKERHETSFUNNENE FØRST (`SIKKERHETSGJENNOMGANG.md`)
Fundamentet må være tett før adgangskontrollen settes i drift.

| # | Funn | Lukkes av |
|---|------|-----------|
| 1 | Sanksjon DEBUG=True → Swagger eksponert | Sett `DEBUG=false` i Sanksjon-`.env`; verifiser `/sanksjon/api/docs` → 404. pn-auth har dette innebygd (testet). |
| 2 | Node `SESSION_SECRET || "bytt-meg"` | Fjern reserveverdien; stopp hvis nøkkel mangler (mønster i `integrasjon/oppdrag-node/pnAuth.js#getSecret`). |
| 3 | Node 18 EOL | Oppgrader til Node 22 LTS (testet mot v22). |
| 4 | `User=thomas` på tjenestene | Bruk dedikerte servicebrukere + herding: `integrasjon/systemd/*.service`. |
| 5 | Node binder 0.0.0.0 | `app.listen(PORT, "127.0.0.1")` / `Environment=HOST=127.0.0.1` (se `banenor.service`). |
| 6 | Ingen rate-limit på Node-login | Blir irrelevant: Node-login fjernes (steg 4). pn-auth rate-limiter (testet). |
| 7 | Manglende nginx-headere/HSTS, `server_tokens` | `integrasjon/nginx/…conf` (HSTS, X-CTO, X-Frame, Referrer-Policy, server_tokens off). |
| 8 | SameSite på Node-cookie | Bortfaller med fjernet Node-sesjon; pn_auth-cookien er `SameSite=Lax` (testet). |
| 9 | Gammel TLS globalt | `ssl_protocols TLSv1.2 TLSv1.3;` i `nginx.conf` http-blokk. |
| 10 | `/api/helse` lekker brukerantall | pn-auth `/auth/health` lekker ingenting (testet). Vurder å stramme Sanksjons helsesjekk. |
| 11 | Avhengighetsrevisjon | `pip-audit` / `npm audit` etter oppgradering. |
| 12 | Inkonsistente størrelsesgrenser | Samkjør nginx/Node/`MAX_PDF_SIZE_MB` (kommentert i nginx-confen). |

### Steg 2 – Master-DB + migrasjon
```bash
# Ta backup først!
cp /opt/parknordic/parknordic.db /opt/parknordic/parknordic.db.bak
cd pn-auth && . .venv/bin/activate
python migrate.py --db /opt/parknordic/parknordic.db \
    --oppdrag-json /opt/banenor/data/data.json --dry-run     # SE på utskriften
python migrate.py --db /opt/parknordic/parknordic.db \
    --oppdrag-json /opt/banenor/data/data.json                # reell kjøring
```
Migrasjonen legger til `permissions`/`access_log`, gir Sanksjon-ansatte `sanksjon=1`,
importerer Oppdrag-brukere (`oppdrag=1`), og setter `must_change_password=1` for alle
(brukere setter nytt passord ved overgang). **Verifiser kolonnemappingen** mot det
faktiske users-skjemaet (skriptet stopper med melding hvis det ikke kjenner kolonnene –
juster `COL_ALIASES` i `migrate.py`).

### Steg 3 – Sett opp pn-auth
```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin svc-pnauth
sudo mkdir -p /opt/pn-auth && sudo cp -r pn-auth/* /opt/pn-auth/
cd /opt/pn-auth && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
sudo cp .env.example .env       # fyll inn AUTH_SECRET + PN_AUTH_DB=/opt/parknordic/parknordic.db
sudo install -m644 /repo/integrasjon/systemd/pn-auth.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now pn-auth
curl -s http://127.0.0.1:8081/auth/health      # {"status":"ok"}
```

### Steg 4 – Koble Oppdrag + Sanksjon på, og fjern det gamle HELT
- **Oppdrag (Node):** legg `integrasjon/oppdrag-node/pnAuth.js` i `/opt/banenor`.
  ```js
  const { pnAuth } = require('./pnAuth');
  app.use('/oppdrag/api', pnAuth({ system: 'oppdrag' }));
  ```
  Fjern så: `/api/login`-ruten, express-session-innlogging, brukerlisten i `data.json`
  som autentiseringskilde, og **innloggingssiden**. Uinnlogget → redirect til portalen `/`.
  La PWA-en/service workeren på roten stå urørt.
- **Sanksjon (FastAPI):** legg `integrasjon/sanksjon-fastapi/pn_auth.py` ved `main.py`.
  ```python
  from pn_auth import require_sanksjon
  # på beskyttede ruter: bruker: dict = Depends(require_sanksjon)
  ```
  Fjern `pn_session`-innlogging, egen brukertabell som auth-kilde, **og «Brukere med
  tilgang»-skjermen** (erstattes av portalens admin-skjerm). 401 på HTML → redirect til `/`.
- Begge: sett `AUTH_SECRET` (samme) og `COOKIE_NAME=pn_auth` i deres `.env`.

### Steg 5 – Datakvalitet bak nginx `auth_request`
Bruk `location /datakvalitet/` + `/_pn_auth_dk` fra nginx-confen (peker på
`/auth/verify?system=datakvalitet`). Kun innloggede med tilgang slipper inn; resten → portal.

### Steg 6 – Admin-skjerm «Brukere og tilganger»
Ligger i portalen (`parknordic_dashboard.html`, nav «Brukere og tilganger», kun admin).
Oppretter brukere og gir/fjerner tilgang per system mot pn-auths admin-endepunkter;
endringer loggføres i `access_log` (testet).

### Steg 7 – Aktiver felles innlogging
Sett `LAUNCHER_MODUS = false` i `parknordic_dashboard.html` når steg 1–6 er verifisert.
Da bruker portalen `/auth/*`, forhåndsutfyller ikke demo-innlogging, og gjenoppretter
sesjon fra cookien ved lasting (ingen loop).

---

## Akseptansekriterier – status

| Kriterium | Dekkes av | Verifisert |
|-----------|-----------|------------|
| Logg inn én gang → kun systemer med tilgang vises | portal `/auth/me` + systemkort/admin-nav | Live-flow + pytest |
| Direkte URL til system uten tilgang → avvist server-side | Node-mw / FastAPI-dep / nginx auth_request | node:test, FastAPI-dep-test, `verify`-test |
| Bytte system uten ny innlogging | felles `pn_auth`-cookie på `.parknordic.no` | Live-flow (cookie deles) |
| «Tilbake» etter innlogging → ingen loop | `bootstrapSession()` (én kilde til sannhet) | Kodegjennomgang* |
| Ingen egen innlogging/brukeradmin igjen | Steg 4 (fjerning) | **Manuelt hos Thomas** |
| Logg ut → alle krever ny innlogging | `/auth/logout` sletter felles cookie | pytest `test_logout` |
| Admin gir/fjerner tilgang per system; loggføres | admin-endepunkter + `access_log` | pytest `test_admin_*` |
| Sikkerhetsfunn i steg 1 lukket | tabell over | pn-auth innebygd testet; Node/nginx = manuelt |

\* Browser-UI er ikke kjørt i nettleser i dette miljøet (ingen headless browser, og
prod-host er utenfor nettverkspolicyen). JS er syntaks-sjekket, og alle API-kallene
portalen gjør er kjørt mot en live pn-auth-instans. Røyktest i nettleser anbefales før steg 7.

---

## Test selv

```bash
# pn-auth + migrasjon
cd pn-auth && . .venv/bin/activate && python -m pytest -q
# Node-middleware (kontrakt mot pn_auth-token)
node --test integrasjon/oppdrag-node/pnAuth.test.js
# FastAPI-avhengighet
PYTHONPATH=pn-auth:integrasjon/sanksjon-fastapi AUTH_SECRET=$(python3 -c "print('x'*40)") \
  pn-auth/.venv/bin/python -m pytest integrasjon/sanksjon-fastapi/ -q
```

## Husk: felles auth = single point of failure
Når enkelt-innloggingene er borte, stopper alt hvis pn-auth er nede. `Restart=always`
er satt; legg på overvåking/helsesjekk mot `/auth/health` og alarm ved nedetid.

*Park Nordic AS – internt. Konfidensielt.*
