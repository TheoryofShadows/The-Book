/* The Book and Me -- optional reader accounts.
 *
 * One file, no dependencies, no build step: it is deployed as the Pages
 * "advanced mode" worker (_worker.js) and answers /api/*; every other request
 * is handed straight to the static site (env.ASSETS), so nothing about the
 * reader changes for somebody who never signs in.
 *
 * What it does:
 *   - sign-in by an emailed one-time link (no passwords exist anywhere)
 *   - a session in an HttpOnly cookie that only /api/* ever receives
 *   - per-item, last-write-wins sync of the reader's own data
 *   - export of everything held, and deletion of all of it
 *   - the "a new chapter every week" email list: POST /api/subscribe and
 *     /api/unsubscribe, stored in the subscribers table (0002_subscribers.sql)
 *
 * Bindings it reads (all optional except DB when it is used for real):
 *   DB              a D1 database (see migrations/0001_accounts.sql)
 *   RESEND_API_KEY  secret; sends the sign-in email through Resend
 *   EMAIL           a Cloudflare Email Service `send_email` binding (alternative)
 *   MAIL_FROM       "Name <address@domain>" for the sign-in email
 *   SITE_ORIGIN     e.g. https://thebookandme.com ; defaults to the request's origin
 *   MAIL_DAILY_CAP  most emails per day, whole site, sign-in and weekly together
 *                   (default 80; never above Resend's free 100 a day)
 *   WEEKLY_SECRET   secret; signs the unsubscribe links and is the password the
 *                   scheduler (.github/workflows/weekly-email.yml) sends to /api/weekly/run
 *   AUTH_DEV_MODE   "1" returns the link in the response -- honoured ONLY on localhost
 */

export const LIMITS = {
  tokenTtlMs: 15 * 60 * 1000,
  sessionTtlMs: 30 * 24 * 3600 * 1000,
  tombstoneMs: 90 * 24 * 3600 * 1000,
  bodyBytes: 1024 * 1024,
  changesPerSync: 500,
  valueBytes: 32 * 1024,
  itemsPerUser: 3000,
  perEmailPerHour: 5,
  perIpPerHour: 15,
  dailyMailCap: 80,
  skewMs: 60 * 1000
};

const SESSION_COOKIE = "tbm_session";
const KEY_OK = /^(?:last|saved:[^\s]{1,160}|diary:[^\s]{1,160}|set:[a-z0-9-]{1,40})$/;
const EMAIL_OK = /^[^\s@<>"',;:]+@[^\s@<>"',;:]+\.[^\s@<>"',;:]+$/;

/* ---------------------------------------------------------------- crypto */

const enc = new TextEncoder();

function b64url(bytes) {
  let s = "";
  for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function randomToken(bytes) {
  const b = new Uint8Array(bytes || 32);
  crypto.getRandomValues(b);
  return b64url(b);
}

export async function sha256(text) {
  const d = await crypto.subtle.digest("SHA-256", enc.encode(text));
  return b64url(new Uint8Array(d));
}

/* ----------------------------------------------------------------- stores */

/* The storage the handler talks to. Two implementations of one interface:
   D1 for real, and a Map for tests and local development. */

export class D1Store {
  constructor(db) { this.db = db; }

  async hit(key, bucket) {
    const r = await this.db.prepare(
      "INSERT INTO rate(k,bucket,n) VALUES(?1,?2,1) " +
      "ON CONFLICT(k,bucket) DO UPDATE SET n=n+1 RETURNING n").bind(key, bucket).first();
    return r ? r.n : 1;
  }
  async purge(now) {
    await this.db.batch([
      this.db.prepare("DELETE FROM login_tokens WHERE expires_at < ?1").bind(now),
      this.db.prepare("DELETE FROM sessions WHERE expires_at < ?1").bind(now),
      this.db.prepare("DELETE FROM rate WHERE bucket < ?1").bind(Math.floor(now / 3600000) - 48),
      this.db.prepare("DELETE FROM items WHERE d = 1 AND srv < ?1").bind(now - LIMITS.tombstoneMs)
    ]);
  }
  async putToken(hash, email, created, expires) {
    await this.db.prepare("INSERT INTO login_tokens(hash,email,created_at,expires_at) VALUES(?1,?2,?3,?4)")
      .bind(hash, email, created, expires).run();
  }
  async takeToken(hash, now) {
    const r = await this.db.prepare(
      "DELETE FROM login_tokens WHERE hash = ?1 AND expires_at > ?2 RETURNING email")
      .bind(hash, now).first();
    return r ? r.email : null;
  }
  async upsertUser(email, now, newId) {
    await this.db.prepare(
      "INSERT INTO users(id,email,created_at,last_seen) VALUES(?1,?2,?3,?3) " +
      "ON CONFLICT(email) DO UPDATE SET last_seen = ?3").bind(newId, email, now).run();
    return this.db.prepare("SELECT id,email FROM users WHERE email = ?1").bind(email).first();
  }
  async getUser(id) {
    return this.db.prepare("SELECT id,email,created_at FROM users WHERE id = ?1").bind(id).first();
  }
  async putSession(hash, userId, created, expires) {
    await this.db.prepare("INSERT INTO sessions(hash,user_id,created_at,expires_at) VALUES(?1,?2,?3,?4)")
      .bind(hash, userId, created, expires).run();
  }
  async getSession(hash, now) {
    return this.db.prepare(
      "SELECT user_id,created_at,expires_at FROM sessions WHERE hash = ?1 AND expires_at > ?2")
      .bind(hash, now).first();
  }
  async extendSession(hash, expires) {
    await this.db.prepare("UPDATE sessions SET expires_at = ?2 WHERE hash = ?1").bind(hash, expires).run();
  }
  async delSession(hash) {
    await this.db.prepare("DELETE FROM sessions WHERE hash = ?1").bind(hash).run();
  }
  async countItems(userId) {
    const r = await this.db.prepare("SELECT COUNT(*) AS n FROM items WHERE user_id = ?1").bind(userId).first();
    return r ? r.n : 0;
  }
  /* One statement for the whole batch (D1's free plan allows 50 queries per
     request). A change is applied only if it is newer than what is held. */
  async upsertItems(userId, changes, now) {
    if (!changes.length) return;
    await this.db.prepare(
      "INSERT INTO items(user_id,k,v,t,d,srv) " +
      "SELECT ?1, json_extract(value,'$.k'), json_extract(value,'$.v'), " +
      "json_extract(value,'$.t'), json_extract(value,'$.d'), ?2 FROM json_each(?3) WHERE true " +
      "ON CONFLICT(user_id,k) DO UPDATE SET v = excluded.v, t = excluded.t, d = excluded.d, " +
      "srv = excluded.srv WHERE excluded.t > items.t")
      .bind(userId, now, JSON.stringify(changes)).run();
  }
  async itemsSince(userId, since) {
    const r = await this.db.prepare(
      "SELECT k,v,t,d FROM items WHERE user_id = ?1 AND srv > ?2 ORDER BY srv LIMIT 3500")
      .bind(userId, since).all();
    return r.results || [];
  }
  async allItems(userId) {
    const r = await this.db.prepare(
      "SELECT k,v,t,d FROM items WHERE user_id = ?1 AND d = 0 ORDER BY k").bind(userId).all();
    return r.results || [];
  }
  /* The weekly-chapter list. The table is made here, if it is missing, so the
     list works on the database production already has without a migration
     being applied by hand. Signing up twice keeps the first date. */
  async subscribe(email, now, source) {
    await this.db.batch([
      this.db.prepare("CREATE TABLE IF NOT EXISTS subscribers (email TEXT PRIMARY KEY, created_at INTEGER NOT NULL, source TEXT)"),
      this.db.prepare("INSERT INTO subscribers(email,created_at,source) VALUES(?1,?2,?3) " +
        "ON CONFLICT(email) DO NOTHING").bind(email, now, source)
    ]);
  }
  async unsubscribe(email) {
    await this.db.batch(WEEKLY_TABLES.map(t => this.db.prepare(t)).concat([
      this.db.prepare("DELETE FROM subscribers WHERE email = ?1").bind(email),
      this.db.prepare("DELETE FROM subscriber_progress WHERE email = ?1").bind(email)
    ]));
  }
  /* The weekly send. Who is due: signed up before this week's send began and
     not yet sent anything since it began. pos is the next chapter's index. */
  async weeklyDue(weekStart, limit) {
    await this.db.batch(WEEKLY_TABLES.map(t => this.db.prepare(t)));
    const r = await this.db.prepare(
      "SELECT s.email AS email, COALESCE(p.pos, 0) AS pos FROM subscribers s " +
      "LEFT JOIN subscriber_progress p ON p.email = s.email " +
      "WHERE s.created_at < ?1 AND (p.last_sent IS NULL OR p.last_sent < ?1) " +
      "ORDER BY s.created_at, s.email LIMIT ?2").bind(weekStart, limit).all();
    return r.results || [];
  }
  async weeklyCount() {
    await this.db.batch(WEEKLY_TABLES.map(t => this.db.prepare(t)));
    const r = await this.db.prepare("SELECT COUNT(*) AS n FROM subscribers").first();
    return r ? r.n : 0;
  }
  /* One statement for the whole list, so a send of any size stays inside
     D1's 50 queries per request. sent is [{email, pos}] with pos the NEXT index. */
  async weeklyMarkSent(sent, now) {
    if (!sent.length) return;
    await this.db.prepare(
      "INSERT INTO subscriber_progress(email,pos,last_sent) " +
      "SELECT json_extract(value,'$.email'), json_extract(value,'$.pos'), ?1 FROM json_each(?2) WHERE true " +
      "ON CONFLICT(email) DO UPDATE SET pos = excluded.pos, last_sent = excluded.last_sent")
      .bind(now, JSON.stringify(sent)).run();
  }
  async peek(key, bucket) {
    const r = await this.db.prepare("SELECT n FROM rate WHERE k = ?1 AND bucket = ?2").bind(key, bucket).first();
    return r ? r.n : 0;
  }
  async add(key, bucket, n) {
    if (!n) return;
    await this.db.prepare(
      "INSERT INTO rate(k,bucket,n) VALUES(?1,?2,?3) " +
      "ON CONFLICT(k,bucket) DO UPDATE SET n=n+?3").bind(key, bucket, n).run();
  }
  async monthSent(month) {
    await this.db.batch(WEEKLY_TABLES.map(t => this.db.prepare(t)));
    const r = await this.db.prepare("SELECT n FROM mail_month WHERE month = ?1").bind(month).first();
    return r ? r.n : 0;
  }
  async addMonth(month, n) {
    if (!n) return;
    await this.db.prepare("INSERT INTO mail_month(month,n) VALUES(?1,?2) " +
      "ON CONFLICT(month) DO UPDATE SET n=n+?2").bind(month, n).run();
  }
  async deleteUser(userId, email) {
    await this.db.batch([
      this.db.prepare("DELETE FROM items WHERE user_id = ?1").bind(userId),
      this.db.prepare("DELETE FROM sessions WHERE user_id = ?1").bind(userId),
      this.db.prepare("DELETE FROM login_tokens WHERE email = ?1").bind(email),
      this.db.prepare("DELETE FROM users WHERE id = ?1").bind(userId)
    ]);
  }
}

export class MemoryStore {
  constructor() {
    this.users = new Map(); this.tokens = new Map(); this.sessions = new Map();
    this.items = new Map(); this.rate = new Map(); this.subscribers = new Map();
    this.progress = new Map(); this.months = new Map();
  }
  async subscribe(email, now, source) {
    if (!this.subscribers.has(email)) this.subscribers.set(email, { created_at: now, source });
  }
  async unsubscribe(email) { this.subscribers.delete(email); this.progress.delete(email); }
  async weeklyDue(weekStart, limit) {
    return [...this.subscribers.entries()]
      .filter(([em, s]) => s.created_at < weekStart &&
        !(this.progress.has(em) && this.progress.get(em).last_sent >= weekStart))
      .sort((a, b) => a[1].created_at - b[1].created_at || (a[0] < b[0] ? -1 : 1))
      .slice(0, limit)
      .map(([em]) => ({ email: em, pos: this.progress.has(em) ? this.progress.get(em).pos : 0 }));
  }
  async weeklyCount() { return this.subscribers.size; }
  async weeklyMarkSent(sent, now) { for (const x of sent) this.progress.set(x.email, { pos: x.pos, last_sent: now }); }
  async peek(key, bucket) { return this.rate.get(key + "|" + bucket) || 0; }
  async add(key, bucket, n) { const k = key + "|" + bucket; this.rate.set(k, (this.rate.get(k) || 0) + n); }
  async monthSent(month) { return this.months.get(month) || 0; }
  async addMonth(month, n) { this.months.set(month, (this.months.get(month) || 0) + n); }
  async hit(key, bucket) {
    const k = key + "|" + bucket; const n = (this.rate.get(k) || 0) + 1; this.rate.set(k, n); return n;
  }
  async purge(now) {
    for (const [h, t] of this.tokens) if (t.expires_at < now) this.tokens.delete(h);
    for (const [h, s] of this.sessions) if (s.expires_at < now) this.sessions.delete(h);
  }
  async putToken(hash, email, created, expires) {
    this.tokens.set(hash, { email, created_at: created, expires_at: expires });
  }
  async takeToken(hash, now) {
    const t = this.tokens.get(hash);
    if (!t) return null;
    this.tokens.delete(hash);
    return t.expires_at > now ? t.email : null;
  }
  async upsertUser(email, now, newId) {
    let u = [...this.users.values()].find(x => x.email === email);
    if (!u) { u = { id: newId, email, created_at: now, last_seen: now }; this.users.set(u.id, u); }
    else u.last_seen = now;
    return { id: u.id, email: u.email };
  }
  async getUser(id) { return this.users.get(id) || null; }
  async putSession(hash, userId, created, expires) {
    this.sessions.set(hash, { user_id: userId, created_at: created, expires_at: expires });
  }
  async getSession(hash, now) {
    const s = this.sessions.get(hash);
    return s && s.expires_at > now ? { ...s } : null;
  }
  async extendSession(hash, expires) { const s = this.sessions.get(hash); if (s) s.expires_at = expires; }
  async delSession(hash) { this.sessions.delete(hash); }
  _mine(userId) { return [...this.items.entries()].filter(([k]) => k.startsWith(userId + "\n")); }
  async countItems(userId) { return this._mine(userId).length; }
  async upsertItems(userId, changes, now) {
    for (const c of changes) {
      const key = userId + "\n" + c.k;
      const have = this.items.get(key);
      if (!have || c.t > have.t) this.items.set(key, { k: c.k, v: c.v, t: c.t, d: c.d, srv: now });
    }
  }
  async itemsSince(userId, since) {
    return this._mine(userId).map(([, r]) => r).filter(r => r.srv > since)
      .sort((a, b) => a.srv - b.srv).map(r => ({ k: r.k, v: r.v, t: r.t, d: r.d }));
  }
  async allItems(userId) {
    return this._mine(userId).map(([, r]) => r).filter(r => !r.d)
      .sort((a, b) => (a.k < b.k ? -1 : 1)).map(r => ({ k: r.k, v: r.v, t: r.t, d: r.d }));
  }
  async deleteUser(userId, email) {
    for (const [k] of this._mine(userId)) this.items.delete(k);
    for (const [h, s] of this.sessions) if (s.user_id === userId) this.sessions.delete(h);
    for (const [h, t] of this.tokens) if (t.email === email) this.tokens.delete(h);
    this.users.delete(userId);
  }
}

/* ------------------------------------------------------------------ mail */

/* Made here, IF NOT EXISTS, like the subscribers table: see
   migrations/0003_weekly.sql for what each holds. */
const WEEKLY_TABLES = [
  "CREATE TABLE IF NOT EXISTS subscribers (email TEXT PRIMARY KEY, created_at INTEGER NOT NULL, source TEXT)",
  "CREATE TABLE IF NOT EXISTS subscriber_progress (email TEXT PRIMARY KEY, pos INTEGER NOT NULL, last_sent INTEGER NOT NULL)",
  "CREATE TABLE IF NOT EXISTS mail_month (month TEXT PRIMARY KEY, n INTEGER NOT NULL)"
];

/* Resend's free plan: 100 emails a day, 3,000 a month, one batch call takes
   up to 100. The weekly send leaves room under the day's cap for sign-in
   links, and stops well short of the month. */
export const WEEKLY = {
  resendPerDay: 100,
  resendPerMonth: 3000,
  monthHeadroom: 200,
  signInReserve: 10,
  batch: 100,
  // Sunday 13:00 UTC (8 am US Eastern in winter, 9 am in summer), less an
  // hour's slack so a late or early cron still lands in the right week.
  anchor: Date.UTC(2026, 10, 1, 12, 0, 0),
  weekMs: 7 * 24 * 3600 * 1000
};

export function weekStart(t) {
  const k = Math.floor((t - WEEKLY.anchor) / WEEKLY.weekMs);
  return WEEKLY.anchor + k * WEEKLY.weekMs;
}

async function hmac(secret, text) {
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return b64url(new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(text))));
}

export async function unsubscribeToken(secret, email) {
  return (await hmac(secret, "unsubscribe:v1:" + email)).slice(0, 32);
}

function sameText(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

export function weeklyMessage(ch, link, unsubscribe, opts) {
  const test = opts && opts.test;
  const name = ch.title + (ch.part ? " \u00b7 " + ch.part : "");
  const subject = (test ? "[Test] " : "") + "This week's chapter: " + name;
  const footer = "You are getting this because this address signed up for \"A new chapter every week\" " +
    "at thebookandme.com. One email a week, nothing else.";
  const text =
    "This week's chapter from the Enoch reading plan: " + name + "\n\n" +
    "\u201c" + ch.excerpt + "\u201d\n\n" +
    "Read or listen to the whole chapter:\n" + link + "\n\n" +
    "-- \n" + footer + "\n" +
    "Unsubscribe (one click): " + unsubscribe + "\n" +
    "The Book and Me \u00b7 https://thebookandme.com/\n";
  const html =
    '<div style="font-family:Georgia,serif;font-size:17px;line-height:1.5;color:#222;max-width:560px">' +
    "<p>This week's chapter from the Enoch reading plan:</p>" +
    '<h2 style="font-size:21px;margin:0 0 12px">' + esc(name) + "</h2>" +
    '<blockquote style="margin:0 0 16px;padding-left:14px;border-left:3px solid #ccc">' + esc(ch.excerpt) + "</blockquote>" +
    '<p><a href="' + esc(link) + '">Read or listen to the whole chapter</a></p>' +
    '<hr style="border:0;border-top:1px solid #ddd;margin:24px 0 12px">' +
    '<p style="font-family:Arial,sans-serif;font-size:12px;color:#666">' + esc(footer) +
    ' <a href="' + esc(unsubscribe) + '" style="color:#666">Unsubscribe</a> (one click).<br>' +
    'The Book and Me &middot; <a href="https://thebookandme.com/" style="color:#666">thebookandme.com</a></p></div>';
  return { subject, text, html, headers: {
    "List-Unsubscribe": "<" + unsubscribe + ">",
    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"
  } };
}

/* Up to 100 messages in one Resend call; [{to, msg}]. */
async function resendBatch(env, list) {
  const from = env.MAIL_FROM || "The Book and Me <login@thebookandme.com>";
  const r = await fetch("https://api.resend.com/emails/batch", {
    method: "POST",
    headers: { "Authorization": "Bearer " + env.RESEND_API_KEY, "Content-Type": "application/json" },
    body: JSON.stringify(list.map(x => ({ from, to: [x.to], subject: x.msg.subject, text: x.msg.text,
                                          html: x.msg.html, headers: x.msg.headers })))
  });
  if (!r.ok) throw new Error("resend " + r.status + " " + (await r.text()).slice(0, 200));
}

export function signInMessage(link) {
  const text =
    "Here is your sign-in link for The Book and Me:\n\n" + link + "\n\n" +
    "It works once and expires in 15 minutes. If you did not ask for it, ignore this " +
    "email -- nothing happens unless the link is opened.\n\n" +
    "Signing in is optional: it only keeps your saved verses, notes, diary and " +
    "reading place in step across your devices.\n";
  const html =
    "<p>Here is your sign-in link for <strong>The Book and Me</strong>:</p>" +
    '<p><a href="' + link + '">Sign in</a></p>' +
    "<p>It works once and expires in 15 minutes. If you did not ask for it, ignore this " +
    "email &mdash; nothing happens unless the link is opened.</p>" +
    "<p>Signing in is optional: it only keeps your saved verses, notes, diary and " +
    "reading place in step across your devices.</p>";
  return { subject: "Your sign-in link for The Book and Me", text, html };
}

/* Which way mail goes out, decided from the bindings that exist. Returns null
   when nothing is configured: the sign-in form then says so honestly instead of
   pretending an email is on its way. */
export function chooseMailer(env, opts) {
  const from = env.MAIL_FROM || "The Book and Me <login@thebookandme.com>";
  if (env.RESEND_API_KEY) {
    return { name: "resend", send: async (to, msg) => {
      const r = await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: { "Authorization": "Bearer " + env.RESEND_API_KEY, "Content-Type": "application/json" },
        body: JSON.stringify({ from, to: [to], subject: msg.subject, text: msg.text, html: msg.html })
      });
      if (!r.ok) throw new Error("resend " + r.status);
    } };
  }
  if (env.EMAIL && typeof env.EMAIL.send === "function") {
    return { name: "cloudflare-email", send: async (to, msg) => {
      await env.EMAIL.send({ from, to, subject: msg.subject, text: msg.text, html: msg.html });
    } };
  }
  if (env.AUTH_DEV_MODE === "1" && opts && opts.local) {
    return { name: "dev", dev: true, send: async () => {} };
  }
  return null;
}

/* ---------------------------------------------------------------- helpers */

const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer",
  "content-security-policy": "default-src 'none'; frame-ancestors 'none'"
};

function json(status, body, extra) {
  return new Response(JSON.stringify(body), { status, headers: Object.assign({}, JSON_HEADERS, extra || {}) });
}

function noticePage(status, ok, message, heading) {
  const safe = String(message || "Thank you.").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const html = '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">' +
    '<meta name="viewport" content="width=device-width, initial-scale=1">' +
    '<meta name="robots" content="noindex"><title>The Book and Me</title>' +
    '<link rel="stylesheet" href="/assets/app.css"></head><body><main id="main"><div class="wrap">' +
    "<h1>" + (heading || (ok ? "Signed up" : "Not yet")) + "</h1><p>" + safe + "</p>" +
    '<p><a class="chip" href="/enoch-reading-plan/">Enoch reading plan</a> <a class="chip" href="/">The Book</a></p>' +
    "</div></main></body></html>";
  return new Response(html, { status, headers: {
    "content-type": "text/html; charset=utf-8", "cache-control": "no-store",
    "x-content-type-options": "nosniff", "referrer-policy": "no-referrer",
    "content-security-policy": "default-src 'none'; style-src 'self'; frame-ancestors 'none'; form-action 'self'"
  } });
}

function isLocal(url) {
  return url.hostname === "localhost" || url.hostname === "127.0.0.1" || url.hostname === "[::1]";
}

function cookieValue(request, name) {
  const raw = request.headers.get("cookie") || "";
  for (const part of raw.split(/;\s*/)) {
    const i = part.indexOf("=");
    if (i > 0 && part.slice(0, i) === name) return part.slice(i + 1);
  }
  return null;
}

function sessionCookie(value, url, maxAge) {
  return SESSION_COOKIE + "=" + value + "; Max-Age=" + maxAge + "; Path=/api; HttpOnly; SameSite=Lax" +
    (isLocal(url) && url.protocol === "http:" ? "" : "; Secure");
}

async function readJson(request) {
  const len = Number(request.headers.get("content-length") || 0);
  if (len > LIMITS.bodyBytes) return { error: "too_large" };
  const ct = request.headers.get("content-type") || "";
  if (!/^application\/json\b/i.test(ct)) return { error: "bad_type" };
  const text = await request.text();
  if (text.length > LIMITS.bodyBytes) return { error: "too_large" };
  try { return { body: JSON.parse(text) }; } catch (e) { return { error: "bad_json" }; }
}

/* ---------------------------------------------------------------- handler */

export function createHandler(deps) {
  const now = deps.now || (() => Date.now());

  async function session(request, store) {
    const raw = cookieValue(request, SESSION_COOKIE);
    if (!raw || raw.length < 20 || raw.length > 200) return null;
    const hash = await sha256("session:" + raw);
    const s = await store.getSession(hash, now());
    if (!s) return null;
    const user = await store.getUser(s.user_id);
    if (!user) return null;
    // Sliding expiry, written at most once a day.
    if (s.expires_at - now() < LIMITS.sessionTtlMs - 24 * 3600 * 1000) {
      await store.extendSession(hash, now() + LIMITS.sessionTtlMs);
    }
    return { user, hash };
  }

  async function handle(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "");
    const store = deps.store(env);
    const method = request.method;

    if (path === "/api/health" && method === "GET") {
      const m = chooseMailer(env, { local: isLocal(url) });
      return json(200, { ok: true, accounts: !!store, mail: m ? m.name : null });
    }
    if (!store) return json(503, { error: "accounts_not_configured" });

    // The two routes a browser on this site does not call: the scheduler,
    // which proves itself with WEEKLY_SECRET, and the one-click unsubscribe
    // a mail program posts (RFC 8058), which proves itself with the signed
    // token in the link. Neither carries this site's Origin.
    if (path === "/api/weekly/run" && method === "POST") return weeklyRun(request, env, url, store);
    if (path === "/api/unsubscribe" && url.searchParams.has("t")) return oneClickUnsubscribe(request, env, url, store);

    if (method === "POST") {
      // Same-origin only. A browser always sends Origin on a cross-site POST.
      if (request.headers.get("origin") !== url.origin) return json(403, { error: "bad_origin" });
    } else if (method !== "GET") {
      return json(405, { error: "method" }, { allow: "GET, POST" });
    }

    if (path === "/api/subscribe" && method === "POST") return subscribe(request, url, store, true);
    if (path === "/api/unsubscribe" && method === "POST") return subscribe(request, url, store, false);
    if (path === "/api/auth/request" && method === "POST") return requestLink(request, env, url, store);
    if (path === "/api/auth/verify" && method === "POST") return verify(request, env, url, store);

    const s = await session(request, store);
    if (path === "/api/me" && method === "GET") {
      if (!s) return json(200, { signedIn: false });
      return json(200, { signedIn: true, email: s.user.email, items: await store.countItems(s.user.id) });
    }
    if (!s) return json(401, { error: "signed_out" });

    if (path === "/api/sync" && method === "POST") return sync(request, store, s);
    if (path === "/api/export" && method === "GET") return exportData(store, s);
    if (path === "/api/signout" && method === "POST") {
      await store.delSession(s.hash);
      return json(200, { ok: true }, { "set-cookie": sessionCookie("", url, 0) });
    }
    if (path === "/api/delete" && method === "POST") {
      const r = await readJson(request);
      if (r.error || !r.body || r.body.confirm !== "delete") return json(400, { error: "confirm_required" });
      await store.deleteUser(s.user.id, s.user.email);
      return json(200, { ok: true, deleted: true }, { "set-cookie": sessionCookie("", url, 0) });
    }
    return json(404, { error: "not_found" });
  }

  /* The signup form on the static pages is a plain HTML form -- those pages
     run no script -- so this takes a form post as well as JSON, and answers a
     form with a small page rather than with JSON. It never says whether an
     address was already on the list. */
  async function subscribe(request, url, store, joining) {
    const ct = request.headers.get("content-type") || "";
    const form = /^application\/x-www-form-urlencoded\b/i.test(ct);
    let body = {};
    if (form) {
      const text = await request.text();
      if (text.length > 4096) return json(413, { error: "too_large" });
      body = Object.fromEntries(new URLSearchParams(text));
    } else {
      const r = await readJson(request);
      if (r.error) return json(r.error === "too_large" ? 413 : 400, { error: r.error });
      body = r.body || {};
    }
    const answer = (status, ok, message) => form
      ? noticePage(status, ok, message, ok && !joining ? "Unsubscribed" : undefined)
      : json(status, ok ? { ok: true } : { error: message });
    const email = (typeof body.email === "string" ? body.email : "").trim().toLowerCase();
    if (email.length > 254 || !EMAIL_OK.test(email)) return answer(400, false, "That doesn't look like an email address. Go back and check it.");
    if (body.website) return answer(200, true, "");
    const ip = request.headers.get("cf-connecting-ip") || "unknown";
    const hour = Math.floor(now() / 3600000);
    if ((await store.hit("s:" + await sha256("ip:" + ip), hour)) > LIMITS.perIpPerHour) {
      return answer(429, false, "Too many tries from here just now. Please try again in an hour.");
    }
    const from = typeof body.from === "string" && /^\/[a-z0-9\/-]{0,200}$/.test(body.from) ? body.from : null;
    if (joining) await store.subscribe(email, now(), from);
    else await store.unsubscribe(email);
    return answer(200, true, joining
      ? "Thank you. You're on the list for a new chapter every week."
      : "Done. That address is off the list.");
  }

  async function oneClickUnsubscribe(request, env, url, store) {
    if (request.method !== "GET" && request.method !== "POST") return json(405, { error: "method" }, { allow: "GET, POST" });
    const email = (url.searchParams.get("e") || "").trim().toLowerCase();
    const t = url.searchParams.get("t") || "";
    const good = env.WEEKLY_SECRET && EMAIL_OK.test(email) &&
      sameText(t, await unsubscribeToken(env.WEEKLY_SECRET, email));
    if (!good) {
      return noticePage(400, false, "That unsubscribe link is not valid. Write to us and we will remove your address by hand.", "Not done");
    }
    await store.unsubscribe(email);
    if (request.method === "POST") return json(200, { ok: true });
    return noticePage(200, true, "Done. " + email + " is off the list, and no more weekly chapters will be sent to it.", "Unsubscribed");
  }

  /* POST /api/weekly/run, Authorization: Bearer <WEEKLY_SECRET>.
       {"mode":"dry"}                 who would get what, nothing sent
       {"mode":"test","to":"a@b.c"}   one email, the plan's first chapter, marked [Test];
                                       touches no subscriber
       {"mode":"send"}                the real weekly send (what the cron calls)  */
  async function weeklyRun(request, env, url, store) {
    const auth = request.headers.get("authorization") || "";
    if (!env.WEEKLY_SECRET || !sameText(auth, "Bearer " + env.WEEKLY_SECRET)) return json(401, { error: "unauthorized" });
    const r = await readJson(request);
    if (r.error) return json(400, { error: r.error });
    const body = r.body || {};
    const mode = body.mode;
    if (!["dry", "test", "send"].includes(mode)) return json(400, { error: "mode" });
    if (!env.ASSETS) return json(503, { error: "no_assets" });
    const origin = (env.SITE_ORIGIN || url.origin).replace(/\/+$/, "");
    const res = await env.ASSETS.fetch(new Request(origin + "/data/weekly.json"));
    if (!res.ok) return json(503, { error: "no_weekly_order" });
    const order = (await res.json()).chapters || [];
    if (!order.length) return json(503, { error: "no_weekly_order" });

    const t = now();
    const day = Math.floor(t / 86400000) * 24;
    const month = new Date(t).toISOString().slice(0, 7);
    const cap = Math.min(Number(env.MAIL_DAILY_CAP) || LIMITS.dailyMailCap, WEEKLY.resendPerDay);
    const usedToday = await store.peek("global", day);
    const usedMonth = await store.monthSent(month);
    const room = Math.max(0, Math.min(
      cap - WEEKLY.signInReserve - usedToday,
      WEEKLY.resendPerMonth - WEEKLY.monthHeadroom - usedMonth));
    const build = async (to, pos, test) => {
      const ch = order[pos % order.length];
      const unsub = origin + "/api/unsubscribe?e=" + encodeURIComponent(to) +
        "&t=" + (await unsubscribeToken(env.WEEKLY_SECRET, to));
      return { to, pos, chapter: ch.title, msg: weeklyMessage(ch, origin + ch.url, unsub, { test }) };
    };

    if (mode === "test") {
      const to = (typeof body.to === "string" ? body.to : "").trim().toLowerCase();
      if (!EMAIL_OK.test(to)) return json(400, { error: "bad_email" });
      if (room < 1) return json(429, { error: "daily_cap" });
      if (!env.RESEND_API_KEY) return json(503, { error: "email_not_configured" });
      const one = await build(to, 0, true);
      await resendBatch(env, [one]);
      await store.add("global", day, 1);
      await store.addMonth(month, 1);
      return json(200, { ok: true, mode, sent: 1, chapter: one.chapter, subject: one.msg.subject });
    }

    const ws = weekStart(t);
    const total = await store.weeklyCount();
    const due = await store.weeklyDue(ws, Math.min(room, WEEKLY.batch * 4));
    const msgs = [];
    for (const d of due) msgs.push(await build(d.email, d.pos, false));
    const summary = { ok: true, mode, subscribers: total, weekStart: new Date(ws).toISOString(),
                      room, due: due.length, chapters: order.length };
    if (mode === "dry") {
      // No addresses: the scheduler's log is public. Which chapters, and how many.
      const by = {};
      for (const m of msgs) by[m.chapter] = (by[m.chapter] || 0) + 1;
      summary.preview = by;
      const one = await build("you@example.com", msgs.length ? msgs[0].pos : 0, false);
      summary.sample = { subject: one.msg.subject, text: one.msg.text };
      return json(200, summary);
    }
    if (!env.RESEND_API_KEY) return json(503, { error: "email_not_configured" });
    let sent = 0;
    for (let i = 0; i < msgs.length; i += WEEKLY.batch) {
      const chunk = msgs.slice(i, i + WEEKLY.batch);
      try {
        await resendBatch(env, chunk);
      } catch (e) {
        summary.error = String(e.message || e).slice(0, 300);
        break;
      }
      // Recorded per chunk, so a failure later never re-sends what went.
      await store.weeklyMarkSent(chunk.map(m => ({ email: m.to, pos: (m.pos + 1) % order.length })), now());
      await store.add("global", day, chunk.length);
      await store.addMonth(month, chunk.length);
      sent += chunk.length;
    }
    summary.sent = sent;
    return json(summary.error ? 502 : 200, summary);
  }

  async function requestLink(request, env, url, store) {
    const r = await readJson(request);
    if (r.error) return json(r.error === "too_large" ? 413 : 400, { error: r.error });
    const raw = r.body && typeof r.body.email === "string" ? r.body.email : "";
    const email = raw.trim().toLowerCase();
    if (email.length > 254 || !EMAIL_OK.test(email)) return json(400, { error: "bad_email" });
    // A filled hidden field means a script, not a reader. Answer as if it worked.
    if (r.body && r.body.website) return json(200, { ok: true });

    const mailer = chooseMailer(env, { local: isLocal(url) });
    if (!mailer) return json(503, { error: "email_not_configured" });

    const t = now();
    const hour = Math.floor(t / 3600000), day = Math.floor(t / 86400000) * 24; // buckets are in hours
    const ip = request.headers.get("cf-connecting-ip") || "unknown";
    const eh = await sha256("email:" + email), ih = await sha256("ip:" + ip);
    if ((await store.hit("e:" + eh, hour)) > LIMITS.perEmailPerHour ||
        (await store.hit("i:" + ih, hour)) > LIMITS.perIpPerHour) {
      return json(429, { error: "rate_limited" }, { "retry-after": "3600" });
    }
    const cap = Number(env.MAIL_DAILY_CAP) || LIMITS.dailyMailCap;
    if ((await store.hit("global", day)) > cap) return json(429, { error: "daily_cap" }, { "retry-after": "3600" });

    await store.purge(t);
    const token = randomToken(32);
    await store.putToken(await sha256("login:" + token), email, t, t + LIMITS.tokenTtlMs);
    const origin = (env.SITE_ORIGIN || url.origin).replace(/\/+$/, "");
    const link = origin + "/#/account/verify/" + token;
    if (mailer.dev) return json(200, { ok: true, devLink: link });
    try {
      await mailer.send(email, signInMessage(link));
    } catch (e) {
      return json(502, { error: "mail_failed" });
    }
    return json(200, { ok: true });
  }

  async function verify(request, env, url, store) {
    const r = await readJson(request);
    if (r.error) return json(400, { error: r.error });
    const token = r.body && typeof r.body.token === "string" ? r.body.token : "";
    if (token.length < 20 || token.length > 200) return json(400, { error: "bad_token" });
    const t = now();
    const email = await store.takeToken(await sha256("login:" + token), t);
    if (!email) return json(400, { error: "expired_or_used" });
    const user = await store.upsertUser(email, t, randomToken(16));
    const sid = randomToken(32);
    await store.putSession(await sha256("session:" + sid), user.id, t, t + LIMITS.sessionTtlMs);
    return json(200, { ok: true, email: user.email, items: await store.countItems(user.id) },
      { "set-cookie": sessionCookie(sid, url, Math.floor(LIMITS.sessionTtlMs / 1000)) });
  }

  async function sync(request, store, s) {
    const r = await readJson(request);
    if (r.error) return json(r.error === "too_large" ? 413 : 400, { error: r.error });
    const b = r.body || {};
    const since = Number.isFinite(b.since) ? Math.max(0, b.since - 2000) : 0; // small overlap: idempotent
    const incoming = Array.isArray(b.changes) ? b.changes : [];
    if (incoming.length > LIMITS.changesPerSync) return json(413, { error: "too_many_changes" });
    const t = now();
    const clean = [];
    for (const c of incoming) {
      if (!c || typeof c.k !== "string" || !KEY_OK.test(c.k)) return json(400, { error: "bad_key" });
      const del = c.d ? 1 : 0;
      let v = null;
      if (!del) {
        if (typeof c.v !== "string" || c.v.length > LIMITS.valueBytes) return json(400, { error: "bad_value", key: c.k });
        try { JSON.parse(c.v); } catch (e) { return json(400, { error: "bad_value", key: c.k }); }
        v = c.v;
      }
      const ct = Number.isFinite(c.t) ? Math.max(0, Math.min(Math.floor(c.t), t + LIMITS.skewMs)) : t;
      clean.push({ k: c.k, v, t: ct, d: del });
    }
    if (clean.length) {
      const have = await store.countItems(s.user.id);
      if (have + clean.length > LIMITS.itemsPerUser + LIMITS.changesPerSync) {
        // Cheap guard first; exact check only matters near the ceiling.
        if (have >= LIMITS.itemsPerUser) return json(413, { error: "too_many_items" });
      }
      await store.upsertItems(s.user.id, clean, t);
    }
    const items = await store.itemsSince(s.user.id, since);
    return json(200, { now: t, items });
  }

  async function exportData(store, s) {
    const rows = await store.allItems(s.user.id);
    const out = { format: "thebook-account-export", version: 1, exported: new Date(now()).toISOString(),
                  email: s.user.email, items: rows.map(r => ({ key: r.k, changed: r.t, value: JSON.parse(r.v) })) };
    return new Response(JSON.stringify(out, null, 2), { status: 200, headers: Object.assign({}, JSON_HEADERS, {
      "content-disposition": 'attachment; filename="the-book-account-data.json"' }) });
  }

  return handle;
}

/* The deployed entry point. */
const handler = createHandler({
  store: env => (env.DB ? new D1Store(env.DB) : null)
});

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/api" || url.pathname.startsWith("/api/")) {
      try {
        return await handler(request, env);
      } catch (e) {
        return json(500, { error: "server_error" });
      }
    }
    return env.ASSETS.fetch(request);
  }
};
