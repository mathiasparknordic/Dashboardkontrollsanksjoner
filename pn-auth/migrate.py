#!/usr/bin/env python3
"""Migrasjon → master-DB for felles auth (FELLES_AUTH_spec.md §4).

Gjør (idempotent):
  1. Legger til `permissions` + `access_log` i master-DBen (Sanksjon sin SQLite),
     og kolonnen `must_change_password` på `users` hvis den mangler.
  2. Gir eksisterende master-brukere (de ~10 i Sanksjon) starttilgang `sanksjon=1`.
  3. Importerer Oppdrag-brukere fra data.json som mangler, med `oppdrag=1`.
  4. Passord: hashene er ikke garantert kompatible på tvers. Standard er å BEHOLDE
     eksisterende hash der den finnes OG sette `must_change_password=1`, slik at alle
     setter nytt passord ved overgang. Brukere uten brukbar hash må admin nullstille.

Kjør ALLTID --dry-run først, og ta backup av DBen før reell kjøring.

  python migrate.py --db /opt/parknordic/parknordic.db \
      --oppdrag-json /opt/banenor/data/data.json --dry-run

VIKTIG: Sanksjon sitt reelle `users`-skjema er ikke i denne pakken. Skriptet oppdager
kolonnenavn defensivt og stopper med tydelig melding hvis det ikke kjenner dem igjen –
verifiser mappingen mot den faktiske DBen før reell kjøring.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import db as dbmod  # noqa: E402
from app import security  # noqa: E402

# Kandidat-kolonnenavn i et eksisterende users-skjema → vårt kanoniske navn.
COL_ALIASES = {
    "username": ["username", "brukernavn", "user", "brukernavn_lower"],
    "email": ["email", "epost", "e_post", "e_postadresse", "mail"],
    "name": ["name", "navn", "fullt_navn", "fullnavn"],
    "password_hash": ["password_hash", "passord_hash", "passordhash", "hash", "passord"],
    "active": ["active", "aktiv", "enabled"],
}


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _resolve(cols: list[str], canonical: str, required: bool = True) -> str | None:
    lower = {c.lower(): c for c in cols}
    for cand in COL_ALIASES[canonical]:
        if cand in lower:
            return lower[cand]
    if required:
        raise SystemExit(
            f"FEIL: fant ingen kolonne for '{canonical}' i users (så: {cols}). "
            f"Forventet en av {COL_ALIASES[canonical]}. Juster COL_ALIASES og kjør på nytt."
        )
    return None


def _pick(user: dict, keys: list[str]):
    for k in keys:
        if k in user and user[k] not in (None, ""):
            return user[k]
    return None


def _load_oppdrag_users(path: str) -> list[dict]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        for key in ("brukere", "users", "data"):
            if isinstance(raw.get(key), list):
                raw = raw[key]
                break
        else:
            # dict keyed by username → liste
            raw = [{"_key": k, **(v if isinstance(v, dict) else {})} for k, v in raw.items()]
    out = []
    for u in raw:
        username = _pick(u, ["brukernavn", "username", "user", "_key"])
        email = _pick(u, ["epost", "email", "e_post", "mail"])
        name = _pick(u, ["navn", "name", "fulltNavn"]) or username
        phash = _pick(u, ["passordHash", "passord_hash", "password_hash", "hash", "passord"])
        systemer = u.get("systemer") if isinstance(u.get("systemer"), dict) else {}
        is_admin = bool(u.get("admin"))
        if not (username or email):
            continue
        out.append({
            "username": username or email,
            "email": email or f"{username}@parknordic.no",
            "name": name,
            "password_hash": phash,
            "admin": is_admin,
            "systemer": systemer,
        })
    return out


def migrate(db_path: str, oppdrag_json: str | None, *, dry_run: bool,
            default_master_sanksjon: bool = True) -> dict:
    dbmod.init_schema(db_path)  # legger til permissions/access_log (+ users hvis tom DB)
    conn = dbmod.connect(db_path)
    summary = {"master_users": 0, "perms_seeded": 0, "imported": 0, "skipped_existing": 0,
               "no_hash": []}
    try:
        cols = _table_columns(conn, "users")
        c_user = _resolve(cols, "username")
        c_email = _resolve(cols, "email")
        c_name = _resolve(cols, "name")
        c_hash = _resolve(cols, "password_hash")
        c_active = _resolve(cols, "active", required=False)
        if "must_change_password" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0")

        # 2. Starttilgang for eksisterende master-brukere (Sanksjon-ansatte).
        existing = conn.execute(f"SELECT id, {c_email} AS email, {c_user} AS username FROM users").fetchall()
        summary["master_users"] = len(existing)
        known = {(r["email"] or "").lower() for r in existing} | {(r["username"] or "").lower() for r in existing}
        for r in existing:
            has_perm = conn.execute("SELECT 1 FROM permissions WHERE user_id=?", (r["id"],)).fetchone()
            if not has_perm:
                conn.execute(
                    "INSERT INTO permissions (user_id, sanksjon) VALUES (?, ?)",
                    (r["id"], 1 if default_master_sanksjon else 0))
                dbmod.log_change(conn, None, r["id"], "migrasjon: starttilgang sanksjon=1")
                summary["perms_seeded"] += 1

        # 3. Importer Oppdrag-brukere som mangler.
        if oppdrag_json:
            for u in _load_oppdrag_users(oppdrag_json):
                ident = (u["email"] or "").lower()
                uname = (u["username"] or "").lower()
                if ident in known or uname in known:
                    summary["skipped_existing"] += 1
                    continue
                phash = u["password_hash"] or security.hash_password(security_random())
                if not u["password_hash"]:
                    summary["no_hash"].append(u["username"])
                cur = conn.execute(
                    f"INSERT INTO users ({c_user}, {c_email}, {c_name}, {c_hash}, "
                    f"{('must_change_password')}{(',' + c_active) if c_active else ''}) "
                    f"VALUES (?, ?, ?, ?, 1{', 1' if c_active else ''})",
                    (u["username"], u["email"], u["name"], phash))
                uid = cur.lastrowid
                sysm = u["systemer"] or {}
                conn.execute(
                    "INSERT INTO permissions (user_id, oppdrag, sanksjon, datakvalitet, admin) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (uid,
                     int(bool(sysm.get("oppdrag", True))),   # Oppdrag-brukere → oppdrag=1
                     int(bool(sysm.get("sanksjon", False))),
                     int(bool(sysm.get("datakvalitet", False))),
                     int(bool(u["admin"]))))
                dbmod.log_change(conn, None, uid, "migrasjon: importert fra Oppdrag")
                known.add(ident)
                known.add(uname)
                summary["imported"] += 1

        # Tving nytt passord ved overgang (brief: brukere setter nytt passord).
        conn.execute("UPDATE users SET must_change_password = 1 WHERE must_change_password = 0")

        if dry_run:
            conn.rollback()
        else:
            conn.commit()
    finally:
        conn.close()
    return summary


def security_random() -> str:
    import secrets
    return "Pn-" + secrets.token_urlsafe(12)


def main() -> None:
    ap = argparse.ArgumentParser(description="Migrer til felles-auth master-DB")
    ap.add_argument("--db", required=True, help="Master-DB (Sanksjon sin parknordic.db)")
    ap.add_argument("--oppdrag-json", help="Oppdrag data.json (valgfri)")
    ap.add_argument("--dry-run", action="store_true", help="Vis hva som ville skjedd, ruller tilbake")
    args = ap.parse_args()
    s = migrate(args.db, args.oppdrag_json, dry_run=args.dry_run)
    print(("[DRY-RUN] " if args.dry_run else "") + "Migrasjon fullført:")
    print(f"  Master-brukere funnet:        {s['master_users']}")
    print(f"  Tilgang seedet (sanksjon=1):  {s['perms_seeded']}")
    print(f"  Importert fra Oppdrag:        {s['imported']}")
    print(f"  Hoppet over (fantes fra før): {s['skipped_existing']}")
    if s["no_hash"]:
        print(f"  ⚠ Uten brukbar passord-hash (må nullstilles av admin): {s['no_hash']}")


if __name__ == "__main__":
    main()
