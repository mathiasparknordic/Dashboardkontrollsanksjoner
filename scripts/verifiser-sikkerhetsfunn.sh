#!/usr/bin/env bash
# Read-only verifisering av sikkerhetsfunnene mot en live host (GET/HEAD – ikke-destruktivt).
# Ingen innlogging, ingen fuzzing, ingen skriv. Kjør etter steg 1 i DEPLOY.md.
#
#   ./scripts/verifiser-sikkerhetsfunn.sh https://kontrollverktoy.parknordic.no
#
# Merk: build-verten er utenfor nettverkspolicyen i Claude-byggemiljøet, så denne må
# kjøres fra et nett som når kontrollverktoy.parknordic.no (f.eks. Thomas' maskin).
set -u
BASE="${1:-https://kontrollverktoy.parknordic.no}"
pass=0; fail=0
ok(){   echo "  ✅ $1"; pass=$((pass+1)); }
bad(){  echo "  ❌ $1"; fail=$((fail+1)); }

hdrs="$(curl -sS -m 15 -D - -o /dev/null "$BASE/" || true)"
has(){ printf '%s' "$hdrs" | grep -iq "$1"; }

echo "== $BASE =="
echo "[#7] Sikkerhetsheadere"
has '^strict-transport-security'  && ok "HSTS satt"                || bad "HSTS mangler"
has '^x-content-type-options'     && ok "X-Content-Type-Options"   || bad "X-Content-Type-Options mangler"
has '^x-frame-options'            && ok "X-Frame-Options"          || bad "X-Frame-Options mangler"
has '^referrer-policy'            && ok "Referrer-Policy"          || bad "Referrer-Policy mangler"
if printf '%s' "$hdrs" | grep -iqE '^server: *nginx/[0-9]'; then bad "server_tokens lekker versjon"; else ok "server_tokens off (ingen versjon)"; fi

echo "[#1] DEBUG/Swagger på Sanksjon (forvent 404)"
for p in /sanksjon/api/docs /sanksjon/api/openapi.json; do
  code="$(curl -sS -m 15 -o /dev/null -w '%{http_code}' "$BASE$p" || echo 000)"
  [ "$code" = "404" ] && ok "$p → 404" || bad "$p → $code (skal være 404)"
done

echo "[felles auth] pn-auth helse (om deployet)"
code="$(curl -sS -m 15 -o /dev/null -w '%{http_code}' "$BASE/auth/health" || echo 000)"
[ "$code" = "200" ] && ok "/auth/health → 200" || echo "  ℹ /auth/health → $code (ikke deployet ennå?)"

echo "[#9] TLS – kun 1.2/1.3 (TLS 1.0 skal feile)"
if curl -sS -m 15 --tlsv1.0 --tls-max 1.0 -o /dev/null "$BASE/" 2>/dev/null; then
  bad "TLS 1.0 godtas"; else ok "TLS 1.0 avvist"; fi

echo "-----"; echo "OK: $pass   AVVIK: $fail"
[ "$fail" -eq 0 ]
