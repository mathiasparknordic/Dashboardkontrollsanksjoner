# Røyktest før `LAUNCHER_MODUS=false` (steg 7)

Browser-flyten er ikke kjørt i nettleser i byggemiljøet (ingen headless browser, og
build-verten er utenfor nettverkspolicyen). Kjør derfor denne manuelle røyktesten før
du vipper portalen over på felles innlogging. Alle API-kallene portalen gjør er
allerede verifisert mot en live pn-auth-instans – dette dekker selve nettleser-UI-et.

## A. Lokalt oppsett (rask paritet)

```bash
# 1) pn-auth med dev-CORS mot portalen (kun for lokal test)
cd pn-auth && . .venv/bin/activate
AUTH_SECRET=$(openssl rand -hex 32) PN_AUTH_DB=/tmp/royktest.db \
  DEBUG=true COOKIE_SECURE=false COOKIE_DOMAIN= DEV_CORS_ORIGIN=http://localhost:8080 \
  ./run.sh &        # 127.0.0.1:8081

# 2) opprett en admin å logge inn med
AUTH_SECRET=dummy PN_AUTH_DB=/tmp/royktest.db python - <<'PY'
from app import db, security
p="/tmp/royktest.db"; db.init_schema(p); c=db.connect(p)
cur=c.execute("INSERT INTO users (username,email,name,password_hash,active,must_change_password)"
 " VALUES ('admin','admin@parknordic.no','Admin',?,1,0)",(security.hash_password('hemmelig123'),))
c.execute("INSERT INTO permissions (user_id,sanksjon,admin) VALUES (?,1,1)",(cur.lastrowid,)); c.commit()
PY

# 3) i parknordic_dashboard.html: sett LAUNCHER_MODUS = false, og pek API-kallene mot
#    http://localhost:8081 (legg ev. en <base> eller kjør portalen bak nginx, se B).
python3 -m http.server 8080      # serve portal-mappa
```

> Cookien er host-basert, så `localhost:8080` ↔ `:8081` deler `pn_auth`. I produksjon
> er alt same-origin via nginx-subpath, så `DEV_CORS_ORIGIN` skal IKKE settes der.

## B. Anbefalt: test bak nginx (ekte paritet)
Bruk `integrasjon/nginx/kontrollverktoy.parknordic.no.conf` lokalt slik at portal,
`/auth/`, `/oppdrag/`, `/sanksjon/` og `/datakvalitet/` ligger på samme origin. Da
tester du også `auth_request`, trailing-slash-reglene og redirect-til-portal.

## Sjekkliste (akseptansekriterier)

- [ ] **Logg inn én gang** → dashbordet vises; admin-nav «Brukere og tilganger» er synlig for admin, skjult for ikke-admin.
- [ ] **Kun systemer med tilgang vises** → en bruker uten `oppdrag`/`datakvalitet` ser ikke de kortene/lenkene.
- [ ] **Direkte URL til system uten tilgang** (skriv `/sanksjon/...` for en bruker uten `sanksjon`) → **avvist server-side** (401/403 fra dependency/middleware, ev. redirect til portal). UI-skjuling alene teller ikke.
- [ ] **Bytt mellom systemer** (Oppdrag ↔ Sanksjon ↔ Datakvalitet) → ingen ny innlogging (samme `pn_auth`-cookie).
- [ ] **«Tilbake» i nettleseren etter innlogging** → ingen loop; `bootstrapSession()` gjenoppretter sesjonen.
- [ ] **Tvungen passordbytte**: logg inn som ny/nullstilt bruker → «Endre passord»-modal åpnes (`must_change_password`).
- [ ] **Admin gir tilgang**: kryss av `datakvalitet` for en bruker → Lagre → brukeren ser tilgangen ved neste `/auth/me` (innen token-TTL).
- [ ] **Admin fjerner tilgang / deaktiverer**: brukeren mister tilgang ved neste poll; deaktivert bruker kastes ut (401).
- [ ] **Loggføring**: `SELECT * FROM access_log` viser hvem som endret hva (fakturagrunnlag).
- [ ] **Logg ut** → `pn_auth` slettes; alle systemer krever ny innlogging.
- [ ] **Ingen egen innlogging igjen**: åpne Oppdrag/Sanksjon uinnlogget → sendes til portalen, ikke en egen login-side. *(Krever steg 4 utført.)*

## Rydd opp
```bash
kill %1 %2 2>/dev/null; rm -f /tmp/royktest.db*
```
