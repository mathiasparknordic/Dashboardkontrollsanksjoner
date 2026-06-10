"""Konfigurasjon for pn-auth.

Sikkerhetsbaseline (SIKKERHETSGJENNOMGANG.md / BYGGESTANDARD §6):
- Hemmeligheter hentes fra miljø. Mangler de, STOPPER appen – ingen hardkodet reserve.
- DEBUG=false som standard. Når DEBUG=false skrus API-dok (Swagger) av i main.py.
- App-en bindes til 127.0.0.1 (se run.sh / systemd), aldri 0.0.0.0.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Manglende/ugyldig konfigurasjon – appen skal stoppe."""


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    auth_secret: str
    db_path: str
    debug: bool
    cookie_name: str
    cookie_domain: str | None
    cookie_secure: bool
    token_ttl_min: int
    root_path: str
    login_rate_max: int
    login_rate_window_s: int
    # CORS kun i DEBUG (utvikling). I produksjon er portalen same-origin via nginx.
    dev_cors_origin: str | None
    # E-post (SMTP2GO-relay, ikke direkte mot M365 – jf. BYGGESTANDARD §5).
    # Mangler host/bruker => dry-run: meldingen skrives til EPOST_OUTBOX, ingenting sendes.
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_pass: str | None
    smtp_from: str
    smtp_starttls: bool
    portal_url: str
    epost_outbox: str | None

    @property
    def epost_aktiv(self) -> bool:
        return bool(self.smtp_host and self.smtp_user)


def load_settings() -> Settings:
    """Les og valider miljøet. Kaster ConfigError hvis noe kritisk mangler."""
    secret = os.environ.get("AUTH_SECRET", "")
    if len(secret) < 32:
        raise ConfigError(
            "AUTH_SECRET må være satt og minst 32 tegn (delt hemmelighet for JWT "
            "på tvers av Oppdrag/Sanksjon/Datakvalitet). Appen stopper."
        )

    db_path = os.environ.get("PN_AUTH_DB", "").strip()
    if not db_path:
        raise ConfigError("PN_AUTH_DB må peke på master-databasen (Sanksjon sin SQLite).")

    return Settings(
        auth_secret=secret,
        db_path=db_path,
        debug=_bool("DEBUG", False),
        cookie_name=os.environ.get("COOKIE_NAME", "pn_auth"),
        cookie_domain=(os.environ.get("COOKIE_DOMAIN") or None),
        cookie_secure=_bool("COOKIE_SECURE", True),
        token_ttl_min=int(os.environ.get("TOKEN_TTL_MIN", "60")),
        root_path=os.environ.get("ROOT_PATH", "/auth"),
        login_rate_max=int(os.environ.get("LOGIN_RATE_MAX", "5")),
        login_rate_window_s=int(os.environ.get("LOGIN_RATE_WINDOW_S", str(15 * 60))),
        dev_cors_origin=(os.environ.get("DEV_CORS_ORIGIN") or None),
        smtp_host=(os.environ.get("SMTP_HOST") or None),
        smtp_port=int(os.environ.get("SMTP_PORT", "587")),
        smtp_user=(os.environ.get("SMTP_USER") or None),
        smtp_pass=(os.environ.get("SMTP_PASS") or None),
        smtp_from=os.environ.get("SMTP_FROM", "no-reply@parknordic.no"),
        smtp_starttls=_bool("SMTP_STARTTLS", True),
        portal_url=os.environ.get("PORTAL_URL", "https://kontrollverktoy.parknordic.no/"),
        epost_outbox=(os.environ.get("EPOST_OUTBOX") or None),
    )
