"""E-postvarsel til brukere (velkomst + passord-nullstilling).

Sendes via SMTP2GO-relay (egen no-reply-bruker), ikke direkte mot Microsoft 365
(jf. BYGGESTANDARD §5). Relayet «venter på Digiflow», så standardmodus er **dry-run**:
mangler SMTP_HOST/SMTP_USER skrives meldingen til EPOST_OUTBOX (eller logges) og
INGENTING sendes. Når relayet er klart settes SMTP_*-variablene, og det samme kodet
sender på ekte.

Best effort: e-post skal ALDRI velte opprettelse/nullstilling. Feiler sendingen,
logges det og admin har fortsatt det midlertidige passordet i retursvaret.
"""
from __future__ import annotations

import logging
import os
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage

from .config import Settings

log = logging.getLogger("pn-auth.epost")


def _velkomst(navn: str, brukernavn: str, temp_passord: str, portal_url: str) -> tuple[str, str]:
    emne = "Tilgang til Park Nordic kontrollverktøy"
    tekst = (
        f"Hei {navn},\n\n"
        f"Du har fått en bruker i Park Nordic sitt kontrollverktøy.\n\n"
        f"  Innlogging:        {portal_url}\n"
        f"  Brukernavn:        {brukernavn}\n"
        f"  Midlertidig passord: {temp_passord}\n\n"
        f"Du må bytte passord første gang du logger inn.\n\n"
        f"Dashbordet viser systemene du har fått tilgang til. Trenger du tilgang til "
        f"flere, ta kontakt med en administrator.\n\n"
        f"Hilsen\nPark Nordic\n"
    )
    return emne, tekst


def _nullstilt(navn: str, temp_passord: str, portal_url: str) -> tuple[str, str]:
    emne = "Nytt midlertidig passord – Park Nordic kontrollverktøy"
    tekst = (
        f"Hei {navn},\n\n"
        f"Passordet ditt er nullstilt av en administrator.\n\n"
        f"  Innlogging:          {portal_url}\n"
        f"  Midlertidig passord: {temp_passord}\n\n"
        f"Du må bytte passord ved neste innlogging. Var det ikke du som ba om dette, "
        f"si fra til en administrator.\n\n"
        f"Hilsen\nPark Nordic\n"
    )
    return emne, tekst


def _send(cfg: Settings, til: str, emne: str, tekst: str) -> str:
    """Returnerer 'sendt' | 'dry-run' | 'feil'. Kaster aldri."""
    msg = EmailMessage()
    msg["From"] = cfg.smtp_from
    msg["To"] = til
    msg["Subject"] = emne
    msg.set_content(tekst)

    if not cfg.epost_aktiv:
        # Dry-run: skriv til outbox hvis satt, ellers bare logg.
        if cfg.epost_outbox:
            try:
                os.makedirs(cfg.epost_outbox, exist_ok=True)
                navn = f"{datetime.now():%Y%m%d_%H%M%S}_{til.replace('@', '_at_')}.eml"
                with open(os.path.join(cfg.epost_outbox, navn), "wb") as f:
                    f.write(bytes(msg))
            except Exception as e:  # outbox-feil skal ikke velte noe
                log.warning("Kunne ikke skrive e-post til outbox: %s", e)
        log.info("E-post (dry-run, ikke sendt) til %s: %s", til, emne)
        return "dry-run"

    try:
        if cfg.smtp_starttls:
            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=20) as s:
                s.starttls(context=ssl.create_default_context())
                if cfg.smtp_user:
                    s.login(cfg.smtp_user, cfg.smtp_pass or "")
                s.send_message(msg)
        else:
            with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=20,
                                  context=ssl.create_default_context()) as s:
                if cfg.smtp_user:
                    s.login(cfg.smtp_user, cfg.smtp_pass or "")
                s.send_message(msg)
        log.info("E-post sendt til %s: %s", til, emne)
        return "sendt"
    except Exception as e:
        log.error("E-post til %s feilet: %s", til, e)
        return "feil"


def send_velkomst(cfg: Settings, *, til: str, navn: str, brukernavn: str,
                  temp_passord: str) -> str:
    emne, tekst = _velkomst(navn, brukernavn, temp_passord, cfg.portal_url)
    return _send(cfg, til, emne, tekst)


def send_nullstilt(cfg: Settings, *, til: str, navn: str, temp_passord: str) -> str:
    emne, tekst = _nullstilt(navn, temp_passord, cfg.portal_url)
    return _send(cfg, til, emne, tekst)
