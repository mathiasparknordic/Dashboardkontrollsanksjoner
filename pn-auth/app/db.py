"""Tynt datalag mot SQLite (master-DB = Sanksjon sin parknordic.db)."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(db_path: str) -> None:
    """Idempotent: oppretter tabellene hvis de mangler."""
    parent = os.path.dirname(os.path.abspath(db_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = connect(db_path)
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def user_with_permissions(conn: sqlite3.Connection, *, user_id: int | None = None,
                          login: str | None = None) -> sqlite3.Row | None:
    """Hent én bruker + tilganger. Slå opp på id, eller på username/email (login)."""
    base = (
        "SELECT u.id, u.username, u.email, u.name, u.password_hash, u.active, "
        "u.must_change_password, "
        "COALESCE(p.oppdrag,0) AS oppdrag, COALESCE(p.sanksjon,0) AS sanksjon, "
        "COALESCE(p.datakvalitet,0) AS datakvalitet, COALESCE(p.admin,0) AS admin "
        "FROM users u LEFT JOIN permissions p ON p.user_id = u.id "
    )
    if user_id is not None:
        return conn.execute(base + "WHERE u.id = ?", (user_id,)).fetchone()
    if login is not None:
        key = login.strip().lower()
        return conn.execute(
            base + "WHERE lower(u.username) = ? OR lower(u.email) = ?", (key, key)
        ).fetchone()
    return None


def list_users(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT u.id, u.username, u.email, u.name, u.active, u.must_change_password, "
        "u.created_at, "
        "COALESCE(p.oppdrag,0) AS oppdrag, COALESCE(p.sanksjon,0) AS sanksjon, "
        "COALESCE(p.datakvalitet,0) AS datakvalitet, COALESCE(p.admin,0) AS admin "
        "FROM users u LEFT JOIN permissions p ON p.user_id = u.id ORDER BY u.name COLLATE NOCASE"
    ).fetchall()


def log_change(conn: sqlite3.Connection, actor: int | None, target: int, endring: str) -> None:
    conn.execute(
        "INSERT INTO access_log (actor, target, endring) VALUES (?, ?, ?)",
        (actor, target, endring),
    )
