# datakvalitet-relay

Server-side relay for Datakvalitet sin AI-chat. Flytter Anthropic-kallet vekk fra
nettleseren: nøkkel + konfidensielle data blir server-side, bak samme auth som resten.

- `POST /datakvalitet/api/chat` `{system, messages}` → `{text}`. Krever `pn_auth` med
  `permissions.datakvalitet` (eller admin). Rate-limit. Nøkkel fra miljø (secret-or-die).
- Ligger på subpath `/datakvalitet/api/*` (FastAPI), bak nginx `proxy_pass` (uten trailing
  slash) og samme `auth_request` som beskytter de statiske filene.

## Kjøre / teste
```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
AUTH_SECRET=$(openssl rand -hex 32) ANTHROPIC_API_KEY=sk-... ./run.sh   # 127.0.0.1:8082
python -m pytest -q
```

## Deploy (Thomas)
- Egen servicebruker (svc-datakvalitet) + systemd-herding (se `integrasjon/systemd/`).
- nginx: `location /datakvalitet/api/ { proxy_pass http://127.0.0.1:8082; }` bak `auth_request`.
- `.env`: AUTH_SECRET (delt), ANTHROPIC_API_KEY (server-side), DEBUG=false.
