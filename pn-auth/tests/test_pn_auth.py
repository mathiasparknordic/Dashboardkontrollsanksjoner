"""Tester pn-auth mot akseptansekriteriene + sikkerhetsbaselinen."""
import importlib

import pytest


def login(client, brukernavn, passord):
    return client.post("/auth/login", json={"brukernavn": brukernavn, "passord": passord})


# ---- Sikkerhetsbaseline -------------------------------------------------
def test_secret_or_die_missing(monkeypatch):
    """Mangler/svak AUTH_SECRET → appen stopper (ingen hardkodet reserve)."""
    from app.config import ConfigError, load_settings
    monkeypatch.setenv("PN_AUTH_DB", "/tmp/x.db")
    monkeypatch.delenv("AUTH_SECRET", raising=False)
    with pytest.raises(ConfigError):
        load_settings()
    monkeypatch.setenv("AUTH_SECRET", "kort")
    with pytest.raises(ConfigError):
        load_settings()


def test_swagger_disabled_when_not_debug(client):
    """SIKKERHETSFUNN #1: ingen API-dok eksponert når DEBUG=false."""
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404


def test_swagger_enabled_in_debug(cfg, monkeypatch):
    monkeypatch.setenv("DEBUG", "true")
    from app.config import load_settings
    from app.main import create_app
    from fastapi.testclient import TestClient
    c = TestClient(create_app(load_settings()))
    assert c.get("/auth/openapi.json").status_code == 200


def test_health_no_user_count_leak(client):
    r = client.get("/auth/health")
    assert r.status_code == 200
    assert "antall_brukere" not in r.text and "brukere" not in r.text


# ---- Innlogging / sesjon ------------------------------------------------
def test_login_sets_httponly_cookie_and_me(client, seed):
    seed()
    r = login(client, "mathias@parknordic.no", "nordic1234")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["email"] == "mathias@parknordic.no"
    assert body["permissions"]["sanksjon"] == 1
    set_cookie = r.headers.get("set-cookie", "").lower()
    assert "pn_auth=" in set_cookie and "httponly" in set_cookie and "samesite=lax" in set_cookie
    # /me virker med cookien
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["permissions"]["sanksjon"] == 1


def test_login_with_username_or_email(client, seed):
    seed()
    assert login(client, "mathias", "nordic1234").status_code == 200
    assert login(client, "MATHIAS@PARKNORDIC.NO", "nordic1234").status_code == 200


def test_wrong_password_and_unknown_user_same_message(client, seed):
    seed()
    a = login(client, "mathias@parknordic.no", "feil")
    b = login(client, "finnesikke@parknordic.no", "uansett")
    assert a.status_code == b.status_code == 401
    assert a.json()["detail"] == b.json()["detail"]


def test_me_requires_login(client):
    assert client.get("/auth/me").status_code == 401


def test_logout_clears_session(client, seed):
    seed()
    login(client, "mathias@parknordic.no", "nordic1234")
    assert client.get("/auth/me").status_code == 200
    client.post("/auth/logout")
    client.cookies.clear()  # nettleseren ville fjernet cookien
    assert client.get("/auth/me").status_code == 401


def test_inactive_user_cannot_login(client, seed, cfg):
    ids = seed()
    from app import db
    conn = db.connect(cfg.db_path)
    conn.execute("UPDATE users SET active=0 WHERE id=?", (ids["sanks"],))
    conn.commit(); conn.close()
    assert login(client, "mathias@parknordic.no", "nordic1234").status_code == 401


def test_rate_limit_on_login(client, seed):
    seed()
    for _ in range(5):
        login(client, "mathias@parknordic.no", "feil")
    # 6. forsøk (også med riktig passord) blokkeres
    r = login(client, "mathias@parknordic.no", "nordic1234")
    assert r.status_code == 429


# ---- Tilgang per system (/verify, brukt av nginx auth_request) ----------
def test_verify_per_system(client, seed):
    seed()
    login(client, "mathias@parknordic.no", "nordic1234")  # kun sanksjon
    assert client.get("/auth/verify", params={"system": "sanksjon"}).status_code == 200
    assert client.get("/auth/verify", params={"system": "datakvalitet"}).status_code == 401
    assert client.get("/auth/verify").status_code == 200  # bare "er innlogget"


def test_admin_implies_all_systems(client, seed):
    seed()
    login(client, "admin@parknordic.no", "hemmelig123")
    for s in ("oppdrag", "sanksjon", "datakvalitet"):
        assert client.get("/auth/verify", params={"system": s}).status_code == 200


# ---- Admin: brukere og tilganger ----------------------------------------
def test_non_admin_cannot_use_admin_endpoints(client, seed):
    seed()
    login(client, "mathias@parknordic.no", "nordic1234")
    assert client.get("/auth/users").status_code == 403


def test_admin_create_grant_revoke_and_logged(client, seed, cfg):
    seed()
    login(client, "admin@parknordic.no", "hemmelig123")
    # opprett bruker
    r = client.post("/auth/users", json={
        "username": "kari", "email": "kari@parknordic.no", "name": "Kari",
        "passord": "midlertidig9", "permissions": {"oppdrag": True}})
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    # gi sanksjon, fjern oppdrag
    r = client.put(f"/auth/users/{uid}/permissions",
                   json={"oppdrag": False, "sanksjon": True, "datakvalitet": False, "admin": False})
    assert r.status_code == 200
    assert r.json()["permissions"] == {"oppdrag": 0, "sanksjon": 1, "datakvalitet": 0, "admin": 0}
    # endringen er loggført (sporbarhet = fakturagrunnlag)
    from app import db
    conn = db.connect(cfg.db_path)
    logs = [row["endring"] for row in conn.execute(
        "SELECT endring FROM access_log WHERE target=? ORDER BY id", (uid,))]
    conn.close()
    assert "opprettet" in logs
    assert any("sanksjon: 0→1" in x for x in logs)
    assert any("oppdrag: 1→0" in x for x in logs)


def test_admin_deactivate_then_user_blocked(client, seed, cfg):
    ids = seed()
    login(client, "admin@parknordic.no", "hemmelig123")
    assert client.put(f"/auth/users/{ids['sanks']}/active",
                      json={"active": False}).status_code == 200
    client.cookies.clear()
    assert login(client, "mathias@parknordic.no", "nordic1234").status_code == 401


def test_duplicate_user_conflict(client, seed):
    seed()
    login(client, "admin@parknordic.no", "hemmelig123")
    payload = {"username": "mathias", "email": "mathias@parknordic.no",
               "name": "X", "passord": "midlertidig9"}
    assert client.post("/auth/users", json=payload).status_code == 409


def test_reset_password_forces_change_and_temp_returned(client, seed):
    ids = seed()
    login(client, "admin@parknordic.no", "hemmelig123")
    r = client.post(f"/auth/users/{ids['sanks']}/reset-password", json={})
    assert r.status_code == 200
    temp = r.json()["temp_passord"]
    assert temp
    # nytt midlertidig passord virker, og må endres
    client.cookies.clear()
    lr = login(client, "mathias@parknordic.no", temp)
    assert lr.status_code == 200
    assert lr.json()["must_change_password"] is True


def test_change_password_flow(client, seed):
    seed()
    login(client, "mathias@parknordic.no", "nordic1234")
    r = client.post("/auth/change-password",
                    json={"gammelt_passord": "nordic1234", "nytt_passord": "ny-laaang-pwd9"})
    assert r.status_code == 200
    client.cookies.clear()
    assert login(client, "mathias@parknordic.no", "ny-laaang-pwd9").status_code == 200


def test_permission_change_propagates_on_me(client, seed, cfg):
    """Admin gir tilgang → slår inn ved brukerens neste /me (rullerende token)."""
    ids = seed()
    # brukeren logger inn (kun sanksjon)
    from fastapi.testclient import TestClient
    from app.main import create_app
    user_client = TestClient(create_app(cfg))
    login(user_client, "mathias@parknordic.no", "nordic1234")
    assert user_client.get("/auth/me").json()["permissions"]["datakvalitet"] == 0
    # admin gir datakvalitet
    login(client, "admin@parknordic.no", "hemmelig123")
    client.put(f"/auth/users/{ids['sanks']}/permissions",
               json={"sanksjon": True, "datakvalitet": True})
    # ved neste /me ser brukeren den nye tilgangen
    assert user_client.get("/auth/me").json()["permissions"]["datakvalitet"] == 1
