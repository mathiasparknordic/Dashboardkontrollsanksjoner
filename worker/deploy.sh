#!/usr/bin/env bash
# Ruller ut medisin-varsel-Workeren til Cloudflare via API.
# Krever: CF_ACCOUNT_ID, VAPID_PRIVATE_KEY (miljøvariabler) og et API-token med
# «Workers Scripts: Edit» + «Workers KV Storage: Edit» (CLOUDFLARE_API_TOKEN,
# eller at omgivelsene legger på Authorization selv).
set -euo pipefail
cd "$(dirname "$0")"
: "${CF_ACCOUNT_ID:?mangler CF_ACCOUNT_ID}"; : "${VAPID_PRIVATE_KEY:?mangler VAPID_PRIVATE_KEY}"
NAME="${WORKER_NAME:-hjemmetavla-push}"
API="https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID"
AUTH="Authorization: Bearer ${CLOUDFLARE_API_TOKEN:-dummy}"
cf(){ curl -sS --max-time 60 -H "$AUTH" "$@"; }

npx --yes esbuild@0.24.0 src/index.mjs --bundle --format=esm --target=es2022 --outfile=dist/worker.mjs --log-level=warning

# KV-navnerom (gjenbruk hvis det finnes)
KV=$(cf "$API/storage/kv/namespaces?per_page=100" | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const r=JSON.parse(s).result||[];const n=r.find(x=>x.title==="hjemmetavla-push-cfg");console.log(n?n.id:"")})')
if [ -z "$KV" ]; then
  KV=$(cf -X POST "$API/storage/kv/namespaces" -H 'content-type: application/json' -d '{"title":"hjemmetavla-push-cfg"}' | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const j=JSON.parse(s);if(!j.success){console.error(s);process.exit(1)}console.log(j.result.id)})')
fi
echo "KV: $KV"

node -e '
const fs=require("fs");
fs.writeFileSync("dist/meta.json", JSON.stringify({main_module:"worker.mjs",compatibility_date:"2026-01-01",
  bindings:[{type:"kv_namespace",name:"CFG",namespace_id:process.argv[1]},
            {type:"secret_text",name:"VAPID_PRIVATE_KEY",text:process.env.VAPID_PRIVATE_KEY}]}));' "$KV"
cf -X PUT "$API/workers/scripts/$NAME" -F 'metadata=@dist/meta.json;type=application/json' \
   -F 'worker.mjs=@dist/worker.mjs;type=application/javascript+module' | head -c 300; echo
rm -f dist/meta.json   # inneholder hemmeligheten
cf -X PUT "$API/workers/scripts/$NAME/schedules" -H 'content-type: application/json' -d '[{"cron":"* * * * *"}]' | head -c 200; echo
cf -X POST "$API/workers/scripts/$NAME/subdomain" -H 'content-type: application/json' -d '{"enabled":true}' | head -c 200; echo
echo "Underdomene:"; cf "$API/workers/subdomain" | head -c 200; echo
