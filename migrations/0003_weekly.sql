-- The weekly chapter email (worker/worker.js runs these itself, IF NOT EXISTS,
-- before it first needs them, so nobody has to apply this file by hand).
--
-- subscriber_progress: where each subscriber is in the Enoch reading plan.
--   email      the address, as in subscribers
--   pos        index of the NEXT chapter to send, into /data/weekly.json
--   last_sent  when the last weekly email went to it (ms since 1970)
-- Unsubscribing deletes the row along with the subscriber.
--
-- mail_month: how many emails the site sent in a calendar month (UTC), e.g.
--   '2026-11', so the weekly send stays inside Resend's free 3,000 a month.

CREATE TABLE IF NOT EXISTS subscriber_progress (
  email     TEXT PRIMARY KEY,
  pos       INTEGER NOT NULL,
  last_sent INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS mail_month (
  month TEXT PRIMARY KEY,
  n     INTEGER NOT NULL
);
