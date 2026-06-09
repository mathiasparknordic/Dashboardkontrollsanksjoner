-- Park Nordic – felles auth: skjema for master-databasen.
-- Master-DB = Sanksjon sin SQLite (parknordic.db). Disse tabellene legges TIL der;
-- den eksisterende `users`-tabellen i Sanksjon gjenbrukes/utvides av migrasjonen
-- (se migrate.py). Brukes også frittstående av pn-auth ved en ren installasjon.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id                   INTEGER PRIMARY KEY,
  username             TEXT UNIQUE NOT NULL,
  email                TEXT UNIQUE NOT NULL,
  password_hash        TEXT NOT NULL,            -- bcrypt
  name                 TEXT NOT NULL,
  active               INTEGER NOT NULL DEFAULT 1,
  must_change_password INTEGER NOT NULL DEFAULT 0, -- settes ved overgang/reset
  created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS permissions (
  user_id      INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  oppdrag      INTEGER NOT NULL DEFAULT 0,
  sanksjon     INTEGER NOT NULL DEFAULT 0,
  datakvalitet INTEGER NOT NULL DEFAULT 0,
  admin        INTEGER NOT NULL DEFAULT 0
);

-- Sporbarhet på tilgangsendringer (fakturagrunnlag mot BaneNor/Riverty → verdt å ha).
CREATE TABLE IF NOT EXISTS access_log (
  id      INTEGER PRIMARY KEY,
  actor   INTEGER REFERENCES users(id),   -- hvem gjorde endringen
  target  INTEGER REFERENCES users(id),   -- hvem ble endret
  endring TEXT NOT NULL,                   -- f.eks. "sanksjon: 0→1", "opprettet", "deaktivert"
  ts      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_access_log_target ON access_log(target);
CREATE INDEX IF NOT EXISTS idx_access_log_ts ON access_log(ts);
