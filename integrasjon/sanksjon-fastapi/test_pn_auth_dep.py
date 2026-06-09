"""Kontrakttest for Sanksjon-avhengigheten mot et token pn-auth lager.

Kjør fra repo-rot med pn-auth sitt venv:
    PYTHONPATH=pn-auth:integrasjon/sanksjon-fastapi pn-auth/.venv/bin/python \
        -m pytest integrasjon/sanksjon-fastapi/ -q
"""
import os

os.environ.setdefault("AUTH_SECRET", "x" * 40)

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import pn_auth  # noqa: E402
from app import security  # fra pn-auth (delt token-fabrikk)  # noqa: E402

SECRET = "x" * 40


def _app():
    app = FastAPI()

    @app.get("/sanksjon/api/ping")
    def ping(bruker: dict = Depends(pn_auth.require_sanksjon)):
        return {"bruker": bruker["email"]}

    return TestClient(app)


def _token(perms):
    return security.make_token(secret=SECRET, user_id=3, name="T", email="t@parknordic.no",
                               permissions=perms, ttl_min=60)


def test_uten_token_401():
    assert _app().get("/sanksjon/api/ping").status_code == 401


def test_med_sanksjon_tilgang_200():
    c = _app()
    c.cookies.set("pn_auth", _token({"sanksjon": 1}))
    r = c.get("/sanksjon/api/ping")
    assert r.status_code == 200 and r.json()["bruker"] == "t@parknordic.no"


def test_uten_sanksjon_tilgang_403():
    c = _app()
    c.cookies.set("pn_auth", _token({"oppdrag": 1}))
    assert c.get("/sanksjon/api/ping").status_code == 403


def test_admin_har_tilgang_200():
    c = _app()
    c.cookies.set("pn_auth", _token({"admin": 1}))
    assert c.get("/sanksjon/api/ping").status_code == 200


def test_tuklet_token_401():
    c = _app()
    c.cookies.set("pn_auth", _token({"sanksjon": 1})[:-3] + "abc")
    assert c.get("/sanksjon/api/ping").status_code == 401
