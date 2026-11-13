-- Esquema D1 del tauler veïnal. Aplicar con:
--   npx wrangler d1 execute cerdanyola-board --remote --file=schema.sql

CREATE TABLE IF NOT EXISTS posts (
  id         TEXT PRIMARY KEY,                       -- base32 minúsculas, 12 caracteres
  cat        TEXT NOT NULL CHECK (cat IN ('help','give','deal')),
  lang       TEXT NOT NULL CHECK (lang IN ('ca','es','en')),
  title      TEXT NOT NULL,
  body       TEXT NOT NULL,
  name       TEXT NOT NULL,
  contact    TEXT,                                   -- teléfono/WhatsApp/Telegram, opcional y visible
  price      TEXT,                                   -- solo para cat='deal'
  email      TEXT NOT NULL,                          -- nunca se publica
  token_hash TEXT NOT NULL,                          -- SHA-256 hex del token de autor
  status     TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','live','hidden','deleted')),
  created    INTEGER NOT NULL,
  confirmed  INTEGER,
  expires    INTEGER,
  renewals   INTEGER NOT NULL DEFAULT 0,
  warned     INTEGER NOT NULL DEFAULT 0,
  ip_day     TEXT,                                   -- hash IP+día (límites)
  ip_fixed   TEXT,                                   -- hash IP (baneos)
  flagged    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS posts_status_expires ON posts (status, expires);

CREATE TABLE IF NOT EXISTS reports (
  post_id TEXT NOT NULL,
  ip_day  TEXT NOT NULL,
  created INTEGER NOT NULL,
  reason  TEXT,
  PRIMARY KEY (post_id, ip_day)
);

CREATE TABLE IF NOT EXISTS rate (
  key   TEXT PRIMARY KEY,
  n     INTEGER NOT NULL,
  reset INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS bans (
  kind    TEXT NOT NULL CHECK (kind IN ('ip','email')),
  value   TEXT NOT NULL,
  note    TEXT,
  created INTEGER NOT NULL,
  PRIMARY KEY (kind, value)
);
