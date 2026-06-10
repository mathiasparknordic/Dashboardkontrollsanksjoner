"""E-postvarsel ved opprettelse/nullstilling – dry-run skriver til outbox, sender ingenting."""
import os


def _login(client, brukernavn, passord):
    r = client.post("/auth/login", json={"brukernavn": brukernavn, "passord": passord})
    assert r.status_code == 200
    return r


def _build(tmp_path, monkeypatch):
    outbox = tmp_path / "outbox"
    monkeypatch.setenv("AUTH_SECRET", "y" * 40)
    monkeypatch.setenv("PN_AUTH_DB", str(tmp_path / "e.db"))
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("COOKIE_DOMAIN", "")
    monkeypatch.setenv("EPOST_OUTBOX", str(outbox))
    # SMTP_* bevisst ikke satt => dry-run, ingen nettverk.
    from app.config import load_settings
    from app.main import create_app
    from app import db, security
    from fastapi.testclient import TestClient
    cfg = load_settings()
    app = create_app(cfg)
    conn = db.connect(cfg.db_path)
    cur = conn.execute(
        "INSERT INTO users (username,email,name,password_hash,active,must_change_password)"
        " VALUES ('admin','admin@parknordic.no','Admin',?,1,0)",
        (security.hash_password("hemmelig123"),))
    conn.execute("INSERT INTO permissions (user_id,admin) VALUES (?,1)", (cur.lastrowid,))
    conn.commit(); conn.close()
    return TestClient(app), outbox


def test_create_user_sends_dry_run_to_outbox(tmp_path, monkeypatch):
    client, outbox = _build(tmp_path, monkeypatch)
    _login(client, "admin", "hemmelig123")
    r = client.post("/auth/users", json={
        "username": "kari", "email": "kari@parknordic.no", "name": "Kari Nordmann",
        "passord": "midlertidig1", "permissions": {"sanksjon": True}})
    assert r.status_code == 201
    assert r.json()["epost"] == "dry-run"          # ingenting sendt, men forsøkt
    eml = list(outbox.glob("*.eml"))
    assert len(eml) == 1
    innhold = eml[0].read_text()
    assert "kari" in innhold and "midlertidig1" in innhold   # brukernavn + midl. passord med
    assert "kari@parknordic.no" in innhold


def test_reset_password_emails_user(tmp_path, monkeypatch):
    client, outbox = _build(tmp_path, monkeypatch)
    _login(client, "admin", "hemmelig123")
    cre = client.post("/auth/users", json={
        "username": "per", "email": "per@parknordic.no", "name": "Per",
        "passord": "startpassord1", "permissions": {"oppdrag": True}})
    uid = cre.json()["id"]
    for f in outbox.glob("*.eml"):
        f.unlink()
    r = client.post(f"/auth/users/{uid}/reset-password", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["epost"] == "dry-run"
    assert body["temp_passord"]                      # auto-generert temp returnert til admin
    eml = list(outbox.glob("*.eml"))
    assert len(eml) == 1
    assert body["temp_passord"] in eml[0].read_text()
