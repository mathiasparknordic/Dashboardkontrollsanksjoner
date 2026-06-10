"""Dummy-test av Riverty-leveranseflyten mot en lokal (loopback) SFTP-server."""
import os
import sqlite3
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import riverty  # noqa: E402
from tests.sftp_dummy import dummy_sftp  # noqa: E402


# ---- Filformat / validering ------------------------------------------------ #
def test_filformat_ett_nummer_per_linje_ingen_header():
    numre = riverty.rens_numre(["1001", "1002", "1003"])
    innhold = riverty.bygg_filinnhold(numre)
    assert innhold == "1001\n1002\n1003\n"
    assert "," not in innhold and ";" not in innhold          # ingen skilletegn
    assert not innhold.lower().startswith("sanksjon")          # ingen header


def test_filnavn_har_tidsstempel():
    n = riverty.filnavn(datetime(2026, 6, 10, 8, 5))
    assert n == "PaidByPN_20260610_0805.txt"


def test_avviser_etc_og_tomt_og_mellomrom():
    for daarlig in (["etc..."], ["1001", ""], ["10 01"], ["..."]):
        with pytest.raises(ValueError):
            riverty.rens_numre(daarlig)


def test_dedupliserer_bevarer_rekkefolge():
    assert riverty.rens_numre(["1001", "1002", "1001", "1003"]) == ["1001", "1002", "1003"]


# ---- Hel flyt mot dummy-SFTP ----------------------------------------------- #
def test_leverer_til_sftp_og_verifiserer(tmp_path):
    root = tmp_path / "sftproot"
    root.mkdir()
    db = str(tmp_path / "logg.db")
    with dummy_sftp(str(root)) as (host, port, user, pw):
        cfg = riverty.SftpConfig(host=host, port=port, username=user, password=pw)
        r = riverty.lever_dagens(lambda: ["5001", "5002", "5003"], cfg,
                                 db_sti=db, ts=datetime(2026, 6, 10, 8, 0))
    assert r.status == "SENDT"
    assert r.antall == 3
    levert = root / "Park_Nordic" / "to_Arvato" / "PaidByPN" / "PaidByPN_20260610_0800.txt"
    assert levert.read_text() == "5001\n5002\n5003\n"          # byte-for-byte
    rad = sqlite3.connect(db).execute(
        "SELECT status, antall, filnavn FROM leveranse_logg").fetchone()
    assert rad == ("SENDT", 3, "PaidByPN_20260610_0800.txt")   # kvittering loggført


def test_tom_dag_gir_ingen_fil(tmp_path):
    root = tmp_path / "sftproot"; root.mkdir()
    db = str(tmp_path / "logg.db")
    with dummy_sftp(str(root)) as (host, port, user, pw):
        cfg = riverty.SftpConfig(host=host, port=port, username=user, password=pw)
        r = riverty.lever_dagens(lambda: [], cfg, db_sti=db)
    assert r.status == "SKIPPET"
    # ingen fil skrevet noe sted under PaidByPN
    pn = root / "Park_Nordic" / "to_Arvato" / "PaidByPN"
    assert not pn.exists() or not any(pn.iterdir())
    status = sqlite3.connect(db).execute("SELECT status FROM leveranse_logg").fetchone()[0]
    assert status == "SKIPPET"


def test_feil_ved_opplasting_gir_feilet_og_varsler(tmp_path):
    db = str(tmp_path / "logg.db")
    varsler = []
    # Peker på en port der ingen lytter -> connect feiler -> FEILET + varsle.
    cfg = riverty.SftpConfig(host="127.0.0.1", port=1, username="x", password="y", timeout=3)
    r = riverty.lever_dagens(lambda: ["9001"], cfg, db_sti=db, varsle=varsler.append)
    assert r.status == "FEILET"
    assert len(varsler) == 1 and varsler[0].status == "FEILET"   # sikkerhetsventil utløst
    status = sqlite3.connect(db).execute("SELECT status FROM leveranse_logg").fetchone()[0]
    assert status == "FEILET"


def test_ugyldig_kilde_sender_ingenting(tmp_path):
    db = str(tmp_path / "logg.db")
    varsler = []
    r = riverty.lever_dagens(lambda: ["1001", "etc..."], None, db_sti=db, varsle=varsler.append)
    assert r.status == "FEILET"
    assert len(varsler) == 1


def test_dry_run_lokal_mappe(tmp_path):
    db = str(tmp_path / "logg.db")
    ut = tmp_path / "outbox"
    r = riverty.lever_dagens(lambda: ["7001", "7002"], None, db_sti=db,
                             lokal_mappe=str(ut), ts=datetime(2026, 6, 10, 9, 30))
    assert r.status == "SENDT"
    assert (ut / "PaidByPN_20260610_0930.txt").read_text() == "7001\n7002\n"
