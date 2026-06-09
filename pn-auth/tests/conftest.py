import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TEST_SECRET = "x" * 40  # >= 32 tegn


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_SECRET", TEST_SECRET)
    monkeypatch.setenv("PN_AUTH_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("COOKIE_SECURE", "false")  # TestClient er http
    monkeypatch.setenv("COOKIE_DOMAIN", "")
    monkeypatch.setenv("LOGIN_RATE_MAX", "5")
    from app.config import load_settings
    return load_settings()


@pytest.fixture
def app(cfg):
    from app.main import create_app
    return create_app(cfg)


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def seed(cfg):
    """Lag en admin og en vanlig sanksjon-bruker direkte i DBen."""
    from app import db, security

    def _seed():
        conn = db.connect(cfg.db_path)
        try:
            def add(username, email, name, pwd, perms, must=0):
                cur = conn.execute(
                    "INSERT INTO users (username,email,name,password_hash,active,must_change_password)"
                    " VALUES (?,?,?,?,1,?)",
                    (username, email, name, security.hash_password(pwd), must))
                uid = cur.lastrowid
                conn.execute(
                    "INSERT INTO permissions (user_id,oppdrag,sanksjon,datakvalitet,admin)"
                    " VALUES (?,?,?,?,?)",
                    (uid, perms.get("oppdrag", 0), perms.get("sanksjon", 0),
                     perms.get("datakvalitet", 0), perms.get("admin", 0)))
                return uid
            ids = {
                "admin": add("admin", "admin@parknordic.no", "Admin", "hemmelig123",
                             {"admin": 1}),
                "sanks": add("mathias", "mathias@parknordic.no", "Mathias", "nordic1234",
                             {"sanksjon": 1}),
            }
            conn.commit()
            return ids
        finally:
            conn.close()
    return _seed
