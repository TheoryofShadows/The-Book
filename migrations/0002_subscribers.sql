-- The weekly-chapter email list for thebookandme.com (Cloudflare D1, the same
-- database as 0001_accounts.sql). worker/worker.js also runs this statement
-- itself, with IF NOT EXISTS, before its first write, so the table exists
-- without anyone having to apply this file by hand.
--
-- What is stored, and nothing else:
--   email       the address somebody typed into "A new chapter every week"
--   created_at  when they signed up (ms since 1970)
--   source      the page they signed up from, e.g. /enoch-reading-plan/
--
-- Read the list:   SELECT email, created_at, source FROM subscribers ORDER BY created_at;
-- Remove someone:  DELETE FROM subscribers WHERE email = '...';

CREATE TABLE IF NOT EXISTS subscribers (
  email      TEXT PRIMARY KEY,
  created_at INTEGER NOT NULL,
  source     TEXT
);
