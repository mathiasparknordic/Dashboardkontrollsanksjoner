#!/usr/bin/env bash
# Start pn-auth. Binder til 127.0.0.1 (aldri 0.0.0.0) – nginx står foran.
# Én worker: rate-limiteren er per-prosess (holder for Park Nordics volum).
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] && set -a && . ./.env && set +a
exec uvicorn app.main:create_app --factory --host 127.0.0.1 --port "${PORT:-8081}" --workers 1
