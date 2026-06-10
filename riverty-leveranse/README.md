# Riverty daglig leveranse – «Paid by PN»

Bygger og leverer den daglige tekstfilen med sanksjoner Park Nordic selv dekker.
Spec: `RIVERTY_leveranse_spec.md` (handoff-pakken).

> **Status:** klar og dummy-testet mot loopback-SFTP. Settes i drift **etter** testfasen
> og felles auth, jf. spec. Riverty-tilgang (host/nøkkel) og endelig SQL mot `parknordic.db`
> kobles på av Thomas.

## Filformat (bekreftet)
- Ren `.txt`, **ett sanksjonsnummer per linje**, ingen header, ingen skilletegn.
- Filnavn: `PaidByPN_YYYYMMDD_HHMM.txt`.
- «etc...» og tomme/whitespace-numre avvises – dette er en **betalingsfil**.

## Forretningsregler (avklart med PN)
| Spørsmål | Beslutning (utgangspunkt) | I koden |
|----------|---------------------------|---------|
| Sende fil på dager uten saker? | **Nei** – kun når det foreligger saker. Riverty korrigerer ev. | tom dag → `SKIPPET`, ingen fil |
| Feilretur / sikkerhetsventil | Varsel ved feil | enhver feil → `FEILET` + `varsle()`-hook |
| Kvittering | Tas ut fra rapportoversikt | hver kjøring loggføres i `leveranse_logg` (SQLite) |

## Kjøre
```bash
pip install -r requirements.txt
python -m pytest -q            # 9 tester: format, validering, full SFTP-flyt, tom dag, feil, dry-run

# Dry-run (skriv lokalt, før Riverty-tilgang er på plass):
RIVERTY_DRYRUN_DIR=/tmp/riverty-out SANKSJON_DB=/sti/parknordic.db python3 run_leveranse.py

# Produksjon (SFTP, host key pinnet):
RIVERTY_SFTP_HOST=... RIVERTY_SFTP_USER=... RIVERTY_SFTP_KEY=... \
RIVERTY_KNOWN_HOSTS=/etc/parknordic/known_hosts \
SANKSJON_DB=/opt/parknordic/parknordic.db LEVERANSE_DB=/opt/parknordic/riverty_leveranse.db \
python3 run_leveranse.py
```

## Hva Thomas må koble på
1. **Numrene**: `hent_dagens_numre()` i `run_leveranse.py` har en SQL-**mal** – tilpass
   tabell/kolonner til faktisk `parknordic.db`. Kilden skal være sanksjonssystemets
   «betalt av PN»-saker, aldri en manuell liste. Vurder å markere sendte saker
   (`levert_riverty = 1`) i samme transaksjon for å unngå dobbeltlevering.
2. **Riverty-tilgang**: host, bruker, **SSH-nøkkel** og `known_hosts` (host key pinning –
   ingen blind `AutoAdd` mot Riverty i prod).
3. **Planlegging**: systemd timer / cron i `Europe/Oslo`. Tidspunkt avklares med Riverty.
4. **Varsling**: koble `varsle()` til e-post (SMTP2GO) når relayet er klart – samme
   mønster som `pn-auth/app/epost.py`.

## Må fortsatt avklares med Riverty
- Eksakt **tidspunkt** på døgnet fila forventes.
- Får vi **kvittering/feilretur** når et nummer ikke gjenkjennes, eller stille? (Påvirker
  hvor mye vi kan stole på vår egen logg alene.)
