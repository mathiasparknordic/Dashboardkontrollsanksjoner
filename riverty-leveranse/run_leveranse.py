#!/usr/bin/env python3
"""
Riverty daglig leveranse – cron-/scheduler-inngang.

Kjør én gang per dag (Europe/Oslo). Henter dagens «betalt av PN»-numre fra
sanksjonssystemet, bygger PaidByPN_*.txt og laster opp via SFTP. Tom dag => ingen fil.

  AUTH-løst miljø, eksempel (systemd timer eller cron):
    RIVERTY_SFTP_HOST=sftp.riverty.no RIVERTY_SFTP_USER=parknordic \
    RIVERTY_SFTP_KEY=/etc/parknordic/riverty_ed25519 \
    RIVERTY_KNOWN_HOSTS=/etc/parknordic/known_hosts \
    SANKSJON_DB=/opt/parknordic/parknordic.db \
    LEVERANSE_DB=/opt/parknordic/riverty_leveranse.db \
    python3 run_leveranse.py

  Dry-run (skriv lokalt i stedet for SFTP – før Riverty-tilgang er på plass):
    RIVERTY_DRYRUN_DIR=/tmp/riverty-out SANKSJON_DB=... python3 run_leveranse.py
"""
from __future__ import annotations

import logging
import os
import sqlite3
import sys

import riverty

log = logging.getLogger("riverty")


def _krev(navn: str) -> str:
    v = os.environ.get(navn)
    if not v:
        raise SystemExit(f"Miljøvariabel {navn} må være satt.")
    return v


def hent_dagens_numre():
    """Hent «betalt av PN»-sanksjonsnumre fra Sanksjon-DB. ALDRI håndplukket.

    Spørringen her er en MAL – Thomas tilpasser tabell-/kolonnenavn til den faktiske
    parknordic.db. Det viktige: kilden er sanksjonssystemets «paid by PN»-saker for
    dagens leveranse, ikke en manuell liste.
    """
    db = _krev("SANKSJON_DB")
    sql = os.environ.get(
        "SANKSJON_SQL",
        # Mal – juster til faktisk skjema:
        "SELECT sanksjonsnummer FROM sanksjoner "
        "WHERE behandling = 'betalt_av_pn' AND levert_riverty = 0",
    )
    with sqlite3.connect(db) as c:
        return [rad[0] for rad in c.execute(sql).fetchall()]


def config_fra_env() -> tuple[riverty.SftpConfig | None, str | None]:
    """Returnerer (SftpConfig, dry_run_dir). Nøyaktig én av dem er satt."""
    dry = os.environ.get("RIVERTY_DRYRUN_DIR")
    if dry:
        return None, dry
    known = os.environ.get("RIVERTY_KNOWN_HOSTS")
    if not known:
        # Sikkerhet: i prod SKAL vertens nøkkel pinnes. Ingen blind AutoAdd mot Riverty.
        raise SystemExit("RIVERTY_KNOWN_HOSTS må settes i produksjon (host key pinning).")
    cfg = riverty.SftpConfig(
        host=_krev("RIVERTY_SFTP_HOST"),
        port=int(os.environ.get("RIVERTY_SFTP_PORT", "22")),
        username=_krev("RIVERTY_SFTP_USER"),
        password=os.environ.get("RIVERTY_SFTP_PASS"),
        key_file=os.environ.get("RIVERTY_SFTP_KEY"),
        remote_dir=os.environ.get("RIVERTY_REMOTE_DIR", riverty.REMOTE_DIR),
        known_hosts=known,
    )
    return cfg, None


def varsle(r: riverty.Resultat) -> None:
    """Sikkerhetsventil ved feil. Kobles til e-post (SMTP2GO) når relayet er klart."""
    log.error("VARSEL – Riverty-leveranse feilet: %s (fil=%s)", r.feilmelding, r.filnavn)
    # TODO (etter SMTP2GO): send e-post til drift/økonomi. Se pn-auth/app/epost.py-mønsteret.


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg, dry = config_fra_env()
    leveranse_db = os.environ.get("LEVERANSE_DB", "riverty_leveranse.db")
    r = riverty.lever_dagens(hent_dagens_numre, cfg, db_sti=leveranse_db,
                             varsle=varsle, lokal_mappe=dry)
    print(f"{r.status}: {r.filnavn or '(ingen fil)'} – {r.antall} sanksjoner")
    return 0 if r.status in ("SENDT", "SKIPPET") else 1


if __name__ == "__main__":
    sys.exit(main())
