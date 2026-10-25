# Optional reader accounts

thebookandme.com works with no account and always will: saved verses, notes, the
diary, the reading place and the settings live in the browser's localStorage. An
account is an **optional** extra that keeps those in step across a reader's devices.

Nothing in the site's first paint changes. A reader who never signs in never
downloads `assets/sync.js`, never makes a request under `/api/`, and is never
given a cookie (tests/accounts.test.js holds all three).

## Pieces

| Path | What it is |
| --- | --- |
| `worker/worker.js` | The whole backend. One dependency-free ES module, deployed as the Pages "advanced mode" `_worker.js`. `_routes.json` (`/api/*` only) means pages and assets never pass through it. |
| `migrations/0001_accounts.sql` | The D1 schema (users, login_tokens, sessions, items, rate). |
| `docs/assets/sync.js` | The browser half: Account page, the one-time "keep my place" note, change tracking, sync. Loaded on demand by `app.js`. |
| `tests/worker.test.js` | The API with no browser (memory store, and D1-on-SQLite when `node:sqlite` exists). |
| `tests/accounts.test.js` | Two browsers against the real handler: merge on first sign-in, convergence, deletion, sign-out, export. |
| `tools/deploy_cloudflare.py` | Now also ships `_worker.js` + `_routes.json`, and takes `--branch` (see below). |

## How sign-in works

1. The reader enters an email on `#/account`. `POST /api/auth/request` stores
   the SHA-256 of a random token (15 minutes) and emails a link
   `https://thebookandme.com/#/account/verify/<token>`.
2. The token is in the URL **fragment**, so it is never sent to a server, logged,
   or put in a Referer. Opening the link shows a button; only pressing it calls
   `POST /api/auth/verify`, so mail scanners that pre-fetch links cannot burn it.
3. Verify creates the user if new and a session. The cookie `tbm_session` is
   `HttpOnly; Secure; SameSite=Lax; Path=/api`, 30 days sliding; only its hash is stored.
4. Every state-changing request must carry `Origin` equal to the site origin and
   `Content-Type: application/json`.

Abuse limits (all stored as hashes): 5 links/hour/address, 15/hour/connection,
80/day for the whole site (`MAIL_DAILY_CAP`), a honeypot field. Responses never
reveal whether an address already has an account.

## What syncs

`saved:<id>` (saved verses, notes), `diary:<id>`, `last` (reading place) and
`set:<name>` for theme, text size, verse-per-line, listening rate/pace/continue,
contents and timeline mode, and the canon mark. Per-item, **last write wins** by
timestamp (clamped to server time + 60 s). Deletions are tombstones (no content,
purged after 90 days). The first sign-in on a device merges: its items go up with
their own old dates (a verse keeps the day it was saved), so nothing local is
discarded and a newer copy already on the server is not overwritten.

Deliberately **not** synced: recent searches, audio position, voice choice, panel
open/closed state. There is **no streak**: the site refuses one on purpose (see
the comment above `diaryShape` in app.js).

Limits: 500 changes/request, 32 KB/item, 3,000 items/user, 1 MB/request.

## Deploying (LIVE on production since 2026-10-25)

Free tier only. Production is the Pages project `thebookandme`, account
`575b607656db70c0664da716f53b4a18`.

1. **Create the D1 database** (free): dashboard > Storage & databases > D1 > Create
   `thebookandme-accounts`, or via the Cloudflare API/MCP. Note its UUID.
2. **Apply the schema:** paste `migrations/0001_accounts.sql` into the D1 console
   (or `wrangler d1 execute thebookandme-accounts --remote --file migrations/0001_accounts.sql`).
3. **Bind it to production:** Pages project > Settings > Bindings > Add > D1 database,
   variable name `DB`, Production environment. (API: PATCH the project's
   `deployment_configs.production.d1_databases = {"DB": {"id": "<uuid>"}}`.)
4. **Mail.** Cloudflare Email Sending to arbitrary recipients needs Workers Paid and
   its binding cannot be attached to a Pages project, so the free path is
   [Resend](https://resend.com) (free: 3,000/month, 100/day):
   - make an account, add and verify `thebookandme.com` (it adds DNS records in Cloudflare),
     **leave open and click tracking OFF** (click tracking rewrites the link and would break it);
   - create an API key with *Sending access* only;
   - add it to Pages > Settings > Variables and Secrets > Production as the **secret**
     `RESEND_API_KEY`; optionally `MAIL_FROM` = `The Book and Me <login@thebookandme.com>`
     (production uses `The Book and Me <signin@thebookandme.com>`).
   - If you pick a different provider, change `MAIL_PROVIDER` in `tools/build_pages.py`
     so the Privacy page names the right company.
5. **Deploy** from this branch after review/merge:
   `bash tools/deploy_cloudflare.sh` (production, `--branch main`).
   A preview that does not touch production: `bash tools/deploy_cloudflare.sh --branch feat-accounts`.
6. Smoke test: `curl https://thebookandme.com/api/health` should say `{"ok":true,"accounts":true,"mail":"resend"}`;
   then sign in with your own address on `#/account`.

Until steps 1-4 are done, deploying is safe but the Account page will say sign-in
"is not switched on yet" — and the Privacy page (which describes accounts) would be
ahead of reality, so do the steps first or revert that wording.

## Free-tier limits that matter

* Pages Functions / Workers free: 100,000 requests/day (only `/api/*` counts), 10 ms CPU per request.
* D1 free: 5 GB, 5 M rows read/day, 100 k rows written/day (enforced; queries fail until 00:00 UTC), up to 10 databases.
  A normal sync is ~5 queries and a handful of rows; a first sign-in with 500 items writes ~1,000 rows.
* Resend free: 100/day and 3,000/month. The site-wide cap (80/day) keeps below it.
* If any limit is hit the site still works: sync/sign-in say so, local data is untouched.

## Operating it

* Look at a user's data: D1 console `SELECT k, t, d FROM items WHERE user_id = ?`. Do not read values without cause.
* Delete someone by request: `DELETE FROM items WHERE user_id=?; DELETE FROM sessions WHERE user_id=?; DELETE FROM users WHERE id=?;`
* Roll back: remove the D1 binding (Pages > Settings > Bindings). `/api/*` returns 503 and the site is otherwise unchanged.

## Production state (2026-10-25)

* D1 database `thebookandme-accounts` (`dce57c27-778d-40cc-91f8-1b67e454da2d`) bound as `DB` to the Pages **production** environment;
  the preview environment keeps `thebookandme-accounts-preview` (`3e2f5569-b5c6-4283-8668-7876252e4a1a`).
* Production secret `RESEND_API_KEY` (a Resend send-only key; it cannot list or read mail) and variable
  `MAIL_FROM` = `The Book and Me <signin@thebookandme.com>`. Resend domain thebookandme.com verified; open/click tracking off.
* `curl https://thebookandme.com/api/health` -> `{"ok":true,"accounts":true,"mail":"resend"}`.
* Production deployment before accounts went live: `cc7b308b-3310-4b25-a779-a71066755f8a`.

## Rolling back

Pick the smallest step that fixes the problem.

1. **Stop accounts, keep everything else** (fastest, the site is otherwise unchanged): Pages project `thebookandme` > Settings >
   Bindings > remove D1 binding `DB` from Production (or API: PATCH the project with
   `deployment_configs.production.d1_databases = {"DB": null}`), then redeploy
   (`bash tools/deploy_cloudflare.sh`). `/api/*` then answers 503 and the Account page says sign-in is unavailable.
2. **Stop only the emails:** delete the `RESEND_API_KEY` secret (and redeploy). Sign-in then says it is not switched on;
   existing sessions keep syncing. Or revoke the key in the Resend dashboard (sign-in then answers 502 `mail_failed`).
3. **Go back to the pre-accounts site:** Pages > Deployments > the production deployment `cc7b308b-3310-4b25-a779-a71066755f8a`
   > Rollback to this deployment. (The Privacy page of that deployment describes no accounts.) If accounts stay switched
   off for good, also remove the D1 binding and delete the D1 database, which erases all stored reader data.
4. Keep the Privacy page truthful in every case: if accounts are rolled back, so is the page (step 3 does both).
