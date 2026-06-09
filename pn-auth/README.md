# pn-auth – Park Nordics felles auth- og tilgangstjeneste

Liten FastAPI-tjeneste som eier brukere og tilganger for alle de interne fagsystemene.
Én innlogging, ett sted å styre tilgang. Bak nginx på subpath `/auth`. Master-DB er
Sanksjon sin SQLite (`parknordic.db`). Se `../FELLES_AUTH_spec.md` for kontrakten og
`../DEPLOY.md` for utrulling.

## Kjøre lokalt / teste

```bash
cd pn-auth
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                       # 23 tester (auth + admin + migrasjon)
```

Start tjenesten (binder til 127.0.0.1):

```bash
cp .env.example .env       # fyll inn AUTH_SECRET (openssl rand -hex 32) + PN_AUTH_DB
./run.sh
```

## API (kort)

| Endepunkt | Hva |
|-----------|-----|
| `POST /auth/login` | `{brukernavn, passord}` → setter cookie `pn_auth` (JWT) |
| `POST /auth/logout` | sletter cookie |
| `GET /auth/me` | `{user, permissions}` + rullerende fornyelse; 401 hvis ikke innlogget |
| `GET /auth/verify?system=…` | 200/401 for nginx `auth_request` (Datakvalitet) |
| `POST /auth/change-password` | bruker setter nytt passord (tvungen ved overgang) |
| `GET /auth/users` *(admin)* | liste med tilganger |
| `POST /auth/users` *(admin)* | opprett bruker |
| `PUT /auth/users/{id}/permissions` *(admin)* | sett tilgang per system (loggføres) |
| `PUT /auth/users/{id}/active` *(admin)* | aktiver/deaktiver |
| `POST /auth/users/{id}/reset-password` *(admin)* | nullstill (temporært passord) |

## Sikkerhetsbaseline (innebygd)

- **Secret-or-die:** mangler/svak `AUTH_SECRET` (<32 tegn) → tjenesten starter ikke.
- **DEBUG=false:** ingen Swagger/OpenAPI eksponert (verifisert i test).
- **Cookie:** `httpOnly`, `secure`, `sameSite=lax`, domene `.parknordic.no`.
- **Rate-limit** på `/auth/login` (per IP, default 5/15 min).
- Bind til `127.0.0.1` (`run.sh`/systemd), bcrypt-hashing, stateless JWT (ingen delt sesjonslager).

## Migrasjon

```bash
python migrate.py --db /opt/parknordic/parknordic.db \
    --oppdrag-json /opt/banenor/data/data.json --dry-run   # kjør ALLTID dry-run først
```
