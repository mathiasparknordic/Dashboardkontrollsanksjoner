"""Tester migrasjonen mot en syntetisk master-DB + Oppdrag data.json."""
import json
import sqlite3
from pathlib import Path

import migrate
from app import db, security


def _make_master(path):
    """Etterligner Sanksjon sin DB: 2 ansatte, bcrypt-hash, ingen permissions-tabell ennå."""
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT UNIQUE,"
        " name TEXT, password_hash TEXT, active INTEGER DEFAULT 1)")
    for u, e, n in [("mathias", "mathias@parknordic.no", "Mathias"),
                    ("anders", "anders@parknordic.no", "Anders")]:
        conn.execute("INSERT INTO users (username,email,name,password_hash) VALUES (?,?,?,?)",
                     (u, e, n, security.hash_password("start123")))
    conn.commit()
    conn.close()


def _make_oppdrag_json(path):
    data = [
        {"brukernavn": "thomas", "epost": "thomas@parknordic.no", "navn": "Thomas",
         "passordHash": security.hash_password("opp123"), "admin": True},
        {"brukernavn": "mathias", "epost": "mathias@parknordic.no", "navn": "Mathias",
         "passordHash": "x"},  # finnes allerede i master → skal hoppes over
    ]
    Path(path).write_text(json.dumps(data), encoding="utf-8")


def test_dry_run_changes_nothing(tmp_path):
    master = tmp_path / "parknordic.db"
    _make_master(master)
    oj = tmp_path / "data.json"
    _make_oppdrag_json(oj)
    s = migrate.migrate(str(master), str(oj), dry_run=True)
    assert s["imported"] == 1 and s["skipped_existing"] == 1
    # ingenting skrevet (utenom schema-tabeller): ingen permissions-rader
    conn = sqlite3.connect(master)
    assert conn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0] == 0
    conn.close()


def test_real_run_seeds_and_imports(tmp_path):
    master = tmp_path / "parknordic.db"
    _make_master(master)
    oj = tmp_path / "data.json"
    _make_oppdrag_json(oj)

    s = migrate.migrate(str(master), str(oj), dry_run=False)
    assert s["master_users"] == 2
    assert s["perms_seeded"] == 2     # begge Sanksjon-ansatte fikk sanksjon=1
    assert s["imported"] == 1         # kun thomas (mathias fantes)
    assert s["skipped_existing"] == 1

    conn = db.connect(str(master))
    # Sanksjon-ansatte har sanksjon=1
    row = db.user_with_permissions(conn, login="anders@parknordic.no")
    assert row["sanksjon"] == 1 and row["oppdrag"] == 0
    # Importert Oppdrag-admin har oppdrag=1 + admin=1
    t = db.user_with_permissions(conn, login="thomas@parknordic.no")
    assert t["oppdrag"] == 1 and t["admin"] == 1
    # alle må sette nytt passord ved overgang
    musts = [r["must_change_password"] for r in conn.execute(
        "SELECT must_change_password FROM users").fetchall()]
    assert all(m == 1 for m in musts)
    conn.close()


def test_idempotent(tmp_path):
    master = tmp_path / "parknordic.db"
    _make_master(master)
    oj = tmp_path / "data.json"
    _make_oppdrag_json(oj)
    migrate.migrate(str(master), str(oj), dry_run=False)
    s2 = migrate.migrate(str(master), str(oj), dry_run=False)
    assert s2["imported"] == 0 and s2["perms_seeded"] == 0  # ingen dobbel-import
    conn = sqlite3.connect(master)
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 3
    conn.close()
