"""
Riverty daglig leveranse – «Paid by PN».

Spec: RIVERTY_leveranse_spec.md. Bygger og leverer den daglige filen med sanksjoner
Park Nordic selv dekker (ikke krever inn fra bilist).

Bekreftet format:
  - Ren tekstfil (.txt), ETT sanksjonsnummer per linje.
  - INGEN header, ingen kolonner, ingen skilletegn.
  - Filnavn med tidsstempel: PaidByPN_YYYYMMDD_HHMM.txt
  - «etc...» skal ALDRI stå i en ekte fil.

Forretningsregler (avklart med PN):
  - Sendes KUN på dager der det foreligger saker. Tom dag => ingen fil (utgangspunkt;
    Riverty korrigerer ev. om de heller vil ha tom fil).
  - Feilretur = sikkerhetsventil: enhver feil i bygging/opplasting/verifisering gir
    status=FEILET og kaller et varsle-hook (e-post kobles på senere).
  - Kvittering: hver kjøring loggføres i leveranse_logg (SQLite) slik at en
    rapportoversikt kan hente ut hva som ble sendt når.

Dette er en BETALINGSfil – den må være korrekt og fullstendig. Numrene skal komme
fra sanksjonssystemet («betalt av PN»-saker), aldri håndplukkes. I denne modulen er
kilden et injisert callable (collect_numbers) – Thomas kobler den mot Sanksjon-DB.
"""
from __future__ import annotations

import logging
import posixpath
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Iterable, Optional

log = logging.getLogger("riverty")

REMOTE_DIR = "/Park_Nordic/to_Arvato/PaidByPN"
FORBUDTE = {"etc", "etc.", "etc...", "..."}


# --------------------------------------------------------------------------- #
# Bygging / validering av filinnholdet
# --------------------------------------------------------------------------- #
def rens_numre(numre: Iterable) -> list[str]:
    """Normaliser, valider og dedupliser (bevarer rekkefølge).

    Kaster ValueError ved tomt/ugyldig nummer eller «etc...»-aktig søppel – en
    betalingsfil skal aldri inneholde tvilsomme linjer.
    """
    sett: set[str] = set()
    ut: list[str] = []
    for raa in numre:
        n = str(raa).strip()
        if not n:
            raise ValueError("Tomt sanksjonsnummer i kilden.")
        if any(c.isspace() for c in n):
            raise ValueError(f"Sanksjonsnummer inneholder mellomrom: {n!r}")
        if n.lower() in FORBUDTE:
            raise ValueError(f"Ugyldig plassholder i kilden: {n!r} (jf. «etc...»-regelen).")
        if n in sett:
            log.warning("Duplikat sanksjonsnummer hoppet over: %s", n)
            continue
        sett.add(n)
        ut.append(n)
    return ut


def bygg_filinnhold(numre: list[str]) -> str:
    """Ett nummer per linje, ingen header, avsluttende linjeskift. Forutsetter renset liste."""
    return "".join(f"{n}\n" for n in numre)


def filnavn(ts: Optional[datetime] = None) -> str:
    ts = ts or datetime.now()
    return f"PaidByPN_{ts:%Y%m%d_%H%M}.txt"


# --------------------------------------------------------------------------- #
# Leveranse-resultat + logg (kvittering)
# --------------------------------------------------------------------------- #
@dataclass
class Resultat:
    status: str                      # SENDT | SKIPPET | FEILET
    filnavn: Optional[str] = None
    antall: int = 0
    numre: list[str] = field(default_factory=list)
    fjernsti: Optional[str] = None
    bytes: int = 0
    feilmelding: Optional[str] = None
    ts: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


def init_logg(db_sti: str) -> None:
    with sqlite3.connect(db_sti) as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS leveranse_logg (
                   id INTEGER PRIMARY KEY,
                   ts TEXT NOT NULL,
                   status TEXT NOT NULL,
                   filnavn TEXT,
                   antall INTEGER NOT NULL DEFAULT 0,
                   bytes INTEGER NOT NULL DEFAULT 0,
                   numre TEXT,
                   feilmelding TEXT
               )"""
        )


def skriv_logg(db_sti: str, r: Resultat) -> None:
    init_logg(db_sti)
    with sqlite3.connect(db_sti) as c:
        c.execute(
            "INSERT INTO leveranse_logg (ts,status,filnavn,antall,bytes,numre,feilmelding)"
            " VALUES (?,?,?,?,?,?,?)",
            (r.ts, r.status, r.filnavn, r.antall, r.bytes, ",".join(r.numre), r.feilmelding),
        )


# --------------------------------------------------------------------------- #
# Opplasting (SFTP) + lokal dry-run
# --------------------------------------------------------------------------- #
@dataclass
class SftpConfig:
    host: str
    port: int = 22
    username: str = ""
    password: Optional[str] = None
    key_file: Optional[str] = None
    remote_dir: str = REMOTE_DIR
    timeout: int = 20
    known_hosts: Optional[str] = None     # sti til known_hosts; None => krev i prod (se from_env)


def _ensure_remote_dir(sftp, remote_dir: str) -> None:
    deler, sti = remote_dir.strip("/").split("/"), ""
    for d in deler:
        sti = f"{sti}/{d}"
        try:
            sftp.stat(sti)
        except IOError:
            sftp.mkdir(sti)


def last_opp_sftp(innhold: str, navn: str, cfg: SftpConfig) -> tuple[str, int]:
    """Last opp via SFTP, verifiser at fjernfilen har riktig størrelse. Returnerer (fjernsti, bytes)."""
    import paramiko

    data = innhold.encode("utf-8")
    klient = paramiko.SSHClient()
    if cfg.known_hosts:
        klient.load_host_keys(cfg.known_hosts)
        klient.set_missing_host_key_policy(paramiko.RejectPolicy())
    else:
        # Kun for dummy/test. I prod SKAL known_hosts settes (se from_env).
        klient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        klient.connect(
            hostname=cfg.host, port=cfg.port, username=cfg.username,
            password=cfg.password, key_filename=cfg.key_file,
            timeout=cfg.timeout, allow_agent=False, look_for_keys=False,
        )
        sftp = klient.open_sftp()
        try:
            _ensure_remote_dir(sftp, cfg.remote_dir)
            fjernsti = posixpath.join(cfg.remote_dir, navn)
            with sftp.open(fjernsti, "wb") as f:
                f.write(data)
            sendt = sftp.stat(fjernsti).st_size          # verifiser opplasting
            if sendt != len(data):
                raise IOError(f"Størrelse stemmer ikke: lastet {len(data)}, fjern {sendt}.")
            return fjernsti, sendt
        finally:
            sftp.close()
    finally:
        klient.close()


def _varsle_default(r: Resultat) -> None:
    log.error("RIVERTY-LEVERANSE FEILET: %s", r.feilmelding)


# --------------------------------------------------------------------------- #
# Hovedinngang
# --------------------------------------------------------------------------- #
def lever_dagens(
    collect_numbers: Callable[[], Iterable],
    cfg: Optional[SftpConfig],
    *,
    db_sti: Optional[str] = None,
    ts: Optional[datetime] = None,
    varsle: Callable[[Resultat], None] = _varsle_default,
    lokal_mappe: Optional[str] = None,     # dry-run: skriv hit i stedet for SFTP
) -> Resultat:
    """Bygg dagens fil og lever den. Tom dag => SKIPPET (ingen fil). Feil => FEILET + varsle."""
    navn = filnavn(ts)
    try:
        numre = rens_numre(collect_numbers())
    except Exception as e:                       # ugyldig kilde – ikke send noe
        r = Resultat(status="FEILET", filnavn=navn, feilmelding=f"Kilde/validering: {e}")
        if db_sti:
            skriv_logg(db_sti, r)
        varsle(r)
        return r

    if not numre:                                # forretningsregel: ingen saker => ingen fil
        r = Resultat(status="SKIPPET", filnavn=None, feilmelding="Ingen saker i dag.")
        if db_sti:
            skriv_logg(db_sti, r)
        log.info("Riverty: ingen saker i dag – ingen fil sendt.")
        return r

    innhold = bygg_filinnhold(numre)
    try:
        if lokal_mappe:                          # dry-run mot lokal mappe
            import os
            os.makedirs(lokal_mappe, exist_ok=True)
            sti = os.path.join(lokal_mappe, navn)
            with open(sti, "w", encoding="utf-8") as f:
                f.write(innhold)
            fjernsti, nbytes = sti, len(innhold.encode("utf-8"))
        else:
            if cfg is None:
                raise ValueError("SftpConfig mangler og lokal_mappe er ikke satt.")
            fjernsti, nbytes = last_opp_sftp(innhold, navn, cfg)
    except Exception as e:
        r = Resultat(status="FEILET", filnavn=navn, antall=len(numre), numre=numre,
                     feilmelding=f"Opplasting: {e}")
        if db_sti:
            skriv_logg(db_sti, r)
        varsle(r)                                # sikkerhetsventil
        return r

    r = Resultat(status="SENDT", filnavn=navn, antall=len(numre), numre=numre,
                 fjernsti=fjernsti, bytes=nbytes)
    if db_sti:
        skriv_logg(db_sti, r)
    log.info("Riverty: sendte %d sanksjoner som %s (%d bytes).", r.antall, navn, nbytes)
    return r
