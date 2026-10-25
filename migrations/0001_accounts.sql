-- Optional reader accounts for thebookandme.com (Cloudflare D1).
-- Apply with:  wrangler d1 migrations apply thebookandme-accounts --remote
-- or run the statements through the Cloudflare API (see ACCOUNTS.md).
--
-- What is stored, and nothing else:
--   users         the email address a reader signed in with
--   login_tokens  SHA-256 of a one-time sign-in link, deleted when used or after 15 minutes
--   sessions      SHA-256 of a session cookie, deleted at sign-out or after 30 days
--   items         the reader's own saved verses, notes, diary entries, place and settings
--   rate          counters keyed by a hash (never an address), for abuse limits

CREATE TABLE IF NOT EXISTS users (
  id         TEXT PRIMARY KEY,
  email      TEXT NOT NULL UNIQUE,
  created_at INTEGER NOT NULL,
  last_seen  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS login_tokens (
  hash       TEXT PRIMARY KEY,
  email      TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  hash       TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS items (
  user_id TEXT    NOT NULL,
  k       TEXT    NOT NULL,
  v       TEXT,
  t       INTEGER NOT NULL,           -- when the reader last changed it (client clock, clamped)
  d       INTEGER NOT NULL DEFAULT 0, -- 1 = deleted (kept as a tombstone so other devices learn of it)
  srv     INTEGER NOT NULL,           -- when the server stored it, for "what changed since"
  PRIMARY KEY (user_id, k)
);
CREATE INDEX IF NOT EXISTS items_srv ON items(user_id, srv);

CREATE TABLE IF NOT EXISTS rate (
  k      TEXT    NOT NULL,
  bucket INTEGER NOT NULL,
  n      INTEGER NOT NULL,
  PRIMARY KEY (k, bucket)
);
