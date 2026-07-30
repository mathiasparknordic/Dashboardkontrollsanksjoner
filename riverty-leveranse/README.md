# Riverty daglig leveranse – «Paid by PN»

Bygger og leverer den daglige tekstfilen med sanksjoner Park Nordic selv dekker.
Spec: `RIVERTY_leveranse_spec.md` (handoff-pakken).

> **Status:** klar og dummy-testet mot loopback-SFTP. Settes i drift **etter** testfasen
> og felles auth, jf. spec. Riverty-tilgang (host/nøkkel) og endelig SQL mot `parknordic.db`
> kobles på av Thomas.

> ⚠️ **`run_leveranse.py` er STILLAS/MAL, ikke en ferdig produksjonsfil.** SQL-en i
> `hent_dagens_numre()` er en plassholder (antatte tabell-/kolonnenavn), og markering av
> leverte saker (mot dobbeltlevering) MANGLER bevisst. Kun SFTP-oppsettet er
> produksjonsklart. **Ikke kopier fila rått over en tilpasset produksjonsversjon** – legg
> SFTP-endringene *oppå* produksjonsfila. Se banneret øverst i `run_leveranse.py`.

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

# Produksjon (SFTP, host key pinnet) – bekreftet Riverty-oppsett:
RIVERTY_SFTP_HOST=file.gothiagroup.com RIVERTY_SFTP_PORT=22 RIVERTY_SFTP_USER=ParkNordic \
RIVERTY_SFTP_KEY=/home/thomas/.ssh/parknas_from_ppk \
RIVERTY_KNOWN_HOSTS=/home/thomas/.ssh/known_hosts_riverty \
RIVERTY_REMOTE_DIR="/To Riverty" \
SANKSJON_DB=/opt/parknordic/parknordic.db LEVERANSE_DB=/opt/parknordic/riverty_leveranse.db \
python3 run_leveranse.py
```

## SFTP-konfigurasjon (alt fra miljøet – ingenting hardkodet)
| Miljøvariabel | Påkrevd | Beskrivelse |
|---------------|---------|-------------|
| `RIVERTY_SFTP_HOST` | ja | Vertsnavn (`file.gothiagroup.com`) |
| `RIVERTY_SFTP_PORT` | nei | Port, default `22` |
| `RIVERTY_SFTP_USER` | ja | Brukernavn (`ParkNordic`) |
| `RIVERTY_SFTP_KEY`  | ja* | Sti til privat SSH-nøkkel (OpenSSH-format) |
| `RIVERTY_KNOWN_HOSTS` | ja | Sti til known_hosts (host key pinning – ingen blind AutoAdd i prod) |
| `RIVERTY_REMOTE_DIR` | ja | Mål-katalog på Riverty-serveren, f.eks. `"/To Riverty"` |

\* Nøkkel eller passord må finnes; i prod brukes SSH-nøkkel.

> ⚠️ **Verdier med mellomrom MÅ siteres.** `RIVERTY_REMOTE_DIR` er `/To Riverty`
> (med mellomrom). Skriv den alltid med anførselstegn:
> ```
> RIVERTY_REMOTE_DIR="/To Riverty"     # riktig
> RIVERTY_REMOTE_DIR=/To Riverty       # FEIL – Bash tolker «Riverty» som en kommando
> ```
> Uten anførselstegn feiler Bash ved `source` av miljøfila (og det blir uryddig i en
> systemd `EnvironmentFile`). Selve stien håndterer mellomrom fint i koden – fella er
> kun shell-siteringen. Gjelder enhver verdi med mellomrom.

> **Bytte mål-katalog:** når Riverty bekrefter endelig mappe er hele endringen å
> sette `RIVERTY_REMOTE_DIR` – ingen kodeendring. Den gamle stien
> `/Park_Nordic/to_Arvato/PaidByPN` er fjernet fra koden.

### Eksempel: `/etc/riverty-leveranse.env` (systemd `EnvironmentFile`)
```
RIVERTY_SFTP_HOST=file.gothiagroup.com
RIVERTY_SFTP_PORT=22
RIVERTY_SFTP_USER=ParkNordic
RIVERTY_SFTP_KEY=/home/thomas/.ssh/parknas_from_ppk
RIVERTY_KNOWN_HOSTS=/home/thomas/.ssh/known_hosts_riverty
RIVERTY_REMOTE_DIR="/To Riverty"
SANKSJON_DB=/opt/parknordic/parknordic_komplett/data/parknordic.db
LEVERANSE_DB=/opt/riverty-leveranse/riverty_leveranse.db
```
> **Merk databasen:** den reelle sanksjonsdatabasen er
> `/opt/parknordic/parknordic_komplett/data/parknordic.db` – *ikke*
> `/opt/parknordic/parknordic.db` (sistnevnte har kun auth-tabeller).

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
