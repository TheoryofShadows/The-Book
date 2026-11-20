'use strict';

/* The account API, with no browser.
 *
 *   node tests/worker.test.js
 *
 * Runs the real worker/worker.js handler against an in-memory store, and again
 * against the D1 store on SQLite (node:sqlite, Node 22.13+) when that is
 * available -- it is skipped, and says so, on older Node. Nothing here touches
 * the network or Cloudflare.
 */

const path = require('path');
const { pathToFileURL } = require('url');

let passed = 0; const failed = [];
function check(name, ok, detail) {
  if (ok) passed++; else failed.push(name + (detail ? ' -- ' + detail : ''));
  console.log(`  ${ok ? 'ok  ' : 'FAIL'}  ${name}${!ok && detail ? '  (' + detail + ')' : ''}`);
}

/* A D1 look-alike on node:sqlite: prepare().bind().run/first/all and batch(). */
function d1Shim(DatabaseSync, sql) {
  const db = new DatabaseSync(':memory:');
  db.exec(sql);
  const wrap = (text) => {
    // Prepared when first run, as D1 does: a batch may create a table that a
    // later statement in the same batch writes to.
    let prepared = null;
    const stmt = new Proxy({}, { get: (_, k) => { prepared = prepared || db.prepare(text); return prepared[k].bind(prepared); } });
    let args = [];
    const o = {
      bind: (...a) => { args = a; return o; },
      run: async () => { stmt.run(...args); return { success: true }; },
      first: async () => { const r = stmt.get(...args); return r === undefined ? null : { ...r }; },
      all: async () => ({ results: stmt.all(...args).map(r => ({ ...r })) }),
      _exec: () => stmt.run(...args)
    };
    return o;
  };
  return {
    prepare: wrap,
    batch: async (list) => { for (const s of list) s._exec(); return []; }
  };
}

async function suite(label, W, makeStore) {
  console.log('\n' + label);
  const ORIGIN = 'https://thebookandme.test';
  let clock = 1_800_000_000_000;
  const sent = [];
  const env = {
    SITE_ORIGIN: ORIGIN,
    EMAIL: { send: async (m) => { sent.push(m); } },
    MAIL_FROM: 'The Book and Me <login@thebookandme.com>'
  };
  const store = makeStore();
  const handler = W.createHandler({ store: () => store, now: () => clock });

  let ipCounter = 0;
  async function call(method, p, { body, cookie, origin = ORIGIN, type = 'application/json', ip, e = env } = {}) {
    const headers = {};
    if (origin !== null && method === 'POST') headers.origin = origin;
    if (type && body !== undefined) headers['content-type'] = type;
    if (cookie) headers.cookie = cookie;
    headers['cf-connecting-ip'] = ip || ('203.0.113.' + (++ipCounter % 250));
    const res = await handler(new Request(ORIGIN + p, {
      method, headers, body: body === undefined ? undefined : (typeof body === 'string' ? body : JSON.stringify(body))
    }), e);
    let json = null;
    const text = await res.text();
    try { json = JSON.parse(text); } catch (err) { /* export is JSON too */ }
    return { status: res.status, json, headers: res.headers, text };
  }
  const cookieOf = (r) => (r.headers.get('set-cookie') || '').split(';')[0];
  async function signIn(email, e) {
    sent.length = 0;
    const r = await call('POST', '/api/auth/request', { body: { email }, e: e || env });
    if (r.status !== 200) throw new Error('request failed ' + r.status + ' ' + r.text);
    const token = /#\/account\/verify\/([\w-]+)/.exec(sent[0].text)[1];
    const v = await call('POST', '/api/auth/verify', { body: { token } });
    return { cookie: cookieOf(v), token, verify: v };
  }

  // ---- sign-in
  check('health says accounts are on and which mail path', (await call('GET', '/api/health')).json.mail === 'cloudflare-email');
  check('health with no mail binding says null, not a guess',
        (await call('GET', '/api/health', { e: { SITE_ORIGIN: ORIGIN } })).json.mail === null);
  {
    const r = await call('POST', '/api/auth/request', { body: { email: 'a@b.co' }, e: { SITE_ORIGIN: ORIGIN } });
    check('no mailer configured -> 503 email_not_configured (nothing pretends to be sent)',
          r.status === 503 && r.json.error === 'email_not_configured');
  }
  check('a malformed address is refused',
        (await call('POST', '/api/auth/request', { body: { email: 'nope' } })).status === 400);
  check('an address with header-injection characters is refused',
        (await call('POST', '/api/auth/request', { body: { email: 'a@b.co\r\nBcc: x@y.z' } })).status === 400);
  check('a cross-origin POST is refused',
        (await call('POST', '/api/auth/request', { body: { email: 'a@b.co' }, origin: 'https://evil.test' })).status === 403);
  check('a POST with no Origin is refused',
        (await call('POST', '/api/auth/request', { body: { email: 'a@b.co' }, origin: null })).status === 403);
  check('a form-encoded POST is refused',
        (await call('POST', '/api/auth/request', { body: 'email=a@b.co', type: 'application/x-www-form-urlencoded' })).status === 400);
  check('the hidden field makes a silent no-op, with no email sent', await (async () => {
    sent.length = 0;
    const r = await call('POST', '/api/auth/request', { body: { email: 'bot@b.co', website: 'x' } });
    return r.status === 200 && sent.length === 0;
  })());

  const a = await signIn('Reader.One@Example.com');
  check('the sign-in email carries a link on the site origin, token in the fragment',
        /^https:\/\/thebookandme\.test\/#\/account\/verify\/[\w-]{40,}$/m.test(sent[0].text) && sent[0].to === 'reader.one@example.com');
  check('the sign-in email is plain-explanatory and has no tracking pixel', !/<img/i.test(sent[0].html));
  const setCookie = a.verify.headers.get('set-cookie') || '';
  check('the session cookie is HttpOnly, Secure, SameSite=Lax and scoped to /api',
        /HttpOnly/.test(setCookie) && /Secure/.test(setCookie) && /SameSite=Lax/.test(setCookie) && /Path=\/api/.test(setCookie), setCookie);
  check('a link is single-use', (await call('POST', '/api/auth/verify', { body: { token: a.token } })).json.error === 'expired_or_used');
  {
    sent.length = 0;
    await call('POST', '/api/auth/request', { body: { email: 'late@example.com' } });
    const token = /verify\/([\w-]+)/.exec(sent[0].text)[1];
    clock += 16 * 60 * 1000;
    const r = await call('POST', '/api/auth/verify', { body: { token } });
    check('a link expires after 15 minutes', r.status === 400 && r.json.error === 'expired_or_used');
  }
  check('a made-up token is refused', (await call('POST', '/api/auth/verify', { body: { token: 'x'.repeat(43) } })).status === 400);
  check('the same address gets the same account', (await signIn('reader.one@example.com')).verify.json.email === 'reader.one@example.com');

  // ---- sessions
  check('me with no cookie says signed out', (await call('GET', '/api/me')).json.signedIn === false);
  check('me with the cookie says who', (await call('GET', '/api/me', { cookie: a.cookie })).json.email === 'reader.one@example.com');
  check('sync without a session is 401', (await call('POST', '/api/sync', { body: { changes: [] } })).status === 401);
  check('a forged cookie is 401', (await call('POST', '/api/sync', { body: { changes: [] }, cookie: 'tbm_session=' + 'a'.repeat(43) })).status === 401);

  // ---- sync: last write wins per item
  const b = await signIn('reader.one@example.com'); // second device, same user
  const T = clock;
  let r = await call('POST', '/api/sync', { cookie: a.cookie, body: { since: 0, changes: [
    { k: 'saved:amos/2/v1', v: JSON.stringify({ id: 'amos/2/v1', note: 'first' }), t: T - 1000 },
    { k: 'last', v: JSON.stringify({ work: 'amos', chapter: 1 }), t: T - 500 },
    { k: 'set:theme', v: '"dark"', t: T - 500 }
  ] } });
  check('device A pushes three items', r.status === 200 && Array.isArray(r.json.items));
  r = await call('POST', '/api/sync', { cookie: b.cookie, body: { since: 0, changes: [] } });
  check('device B pulls all three', r.json.items.length === 3);
  const cursor = r.json.now;
  await call('POST', '/api/sync', { cookie: b.cookie, body: { since: cursor, changes: [
    { k: 'saved:amos/2/v1', v: JSON.stringify({ id: 'amos/2/v1', note: 'newer from B' }), t: T + 10 }] } });
  await call('POST', '/api/sync', { cookie: a.cookie, body: { since: cursor, changes: [
    { k: 'saved:amos/2/v1', v: JSON.stringify({ id: 'amos/2/v1', note: 'older from A' }), t: T + 5 }] } });
  clock += 5000;
  r = await call('POST', '/api/sync', { cookie: a.cookie, body: { since: 0, changes: [] } });
  const note = JSON.parse(r.json.items.find(i => i.k === 'saved:amos/2/v1').v).note;
  check('the newer edit wins, not the later arrival', note === 'newer from B', note);
  clock += 5000;
  await call('POST', '/api/sync', { cookie: b.cookie, body: { since: 0, changes: [{ k: 'saved:amos/2/v1', d: 1, t: T + 50 }] } });
  r = await call('POST', '/api/sync', { cookie: a.cookie, body: { since: 0, changes: [] } });
  const dead = r.json.items.find(i => i.k === 'saved:amos/2/v1');
  check('a deletion reaches the other device as a tombstone with no content', dead && dead.d === 1 && dead.v === null);
  check('an older edit cannot resurrect a deleted item', await (async () => {
    await call('POST', '/api/sync', { cookie: a.cookie, body: { changes: [{ k: 'saved:amos/2/v1', v: '{"id":"amos/2/v1"}', t: T + 20 }] } });
    const x = await call('POST', '/api/sync', { cookie: b.cookie, body: { since: 0, changes: [] } });
    return x.json.items.find(i => i.k === 'saved:amos/2/v1').d === 1;
  })());
  check('since returns only what changed after it', await (async () => {
    const x = await call('POST', '/api/sync', { cookie: a.cookie, body: { since: clock + 100000, changes: [] } });
    return x.json.items.length === 0;
  })());
  check('a time far in the future is clamped, so a bad clock cannot pin an item forever', await (async () => {
    await call('POST', '/api/sync', { cookie: a.cookie, body: { changes: [{ k: 'set:reader-size', v: '1.2', t: clock + 10 * 365 * 86400000 }] } });
    await call('POST', '/api/sync', { cookie: b.cookie, body: { changes: [{ k: 'set:reader-size', v: '1.3', t: clock + 3 * 60 * 1000 }] } });
    const x = await call('POST', '/api/sync', { cookie: a.cookie, body: { since: 0, changes: [] } });
    return JSON.parse(x.json.items.find(i => i.k === 'set:reader-size').t) <= clock + 60 * 1000;
  })());

  // ---- validation and limits
  const bad = async (change) => (await call('POST', '/api/sync', { cookie: a.cookie, body: { changes: [change] } })).status;
  check('a key outside the allowed shapes is refused', await bad({ k: 'admin:x', v: '1', t: 1 }) === 400);
  check('a key with whitespace is refused', await bad({ k: 'saved:a b', v: '1', t: 1 }) === 400);
  check('a value that is not JSON text is refused', await bad({ k: 'set:theme', v: 'not json{', t: 1 }) === 400);
  check('a value over 32 KB is refused', await bad({ k: 'diary:x', v: JSON.stringify('x'.repeat(40000)), t: 1 }) === 400);
  check('more than 500 changes in one request is refused',
        (await call('POST', '/api/sync', { cookie: a.cookie, body: { changes: Array.from({ length: 501 }, (_, i) => ({ k: 'set:a' + i, v: '1', t: 1 })) } })).status === 413);

  // ---- isolation
  const other = await signIn('someone.else@example.com');
  r = await call('POST', '/api/sync', { cookie: other.cookie, body: { since: 0, changes: [] } });
  check("another reader never sees this reader's items", r.status === 200 && r.json.items.length === 0);

  // ---- export, signout, delete
  r = await call('GET', '/api/export', { cookie: a.cookie });
  const exp = JSON.parse(r.text);
  check('export is an attachment with the reader\'s own live items and email',
        /attachment/.test(r.headers.get('content-disposition')) && exp.email === 'reader.one@example.com' &&
        exp.items.some(i => i.key === 'last') && !exp.items.some(i => i.key === 'saved:amos/2/v1'));
  check('export of another reader does not contain it', JSON.parse((await call('GET', '/api/export', { cookie: other.cookie })).text).items.length === 0);

  r = await call('POST', '/api/signout', { cookie: b.cookie, body: {} });
  check('sign-out clears the cookie', /Max-Age=0/.test(r.headers.get('set-cookie')));
  check('and that session is dead, while the other device still works',
        (await call('GET', '/api/me', { cookie: b.cookie })).json.signedIn === false &&
        (await call('GET', '/api/me', { cookie: a.cookie })).json.signedIn === true);

  check('delete needs the explicit confirmation', (await call('POST', '/api/delete', { cookie: a.cookie, body: {} })).status === 400);
  r = await call('POST', '/api/delete', { cookie: a.cookie, body: { confirm: 'delete' } });
  check('delete succeeds and clears the cookie', r.status === 200 && /Max-Age=0/.test(r.headers.get('set-cookie')));
  check('every session of a deleted account is dead', (await call('GET', '/api/me', { cookie: a.cookie })).json.signedIn === false);
  const again = await signIn('reader.one@example.com');
  check('signing in again makes a new, empty account',
        again.verify.json.items === 0 &&
        (await call('POST', '/api/sync', { cookie: again.cookie, body: { since: 0, changes: [] } })).json.items.length === 0);
  check('the other reader is untouched by it',
        (await call('GET', '/api/me', { cookie: other.cookie })).json.signedIn === true);

  // ---- abuse limits
  {
    const e2 = { SITE_ORIGIN: ORIGIN, EMAIL: { send: async () => {} } };
    let codes = [];
    for (let i = 0; i < 7; i++) codes.push((await call('POST', '/api/auth/request', { body: { email: 'flood@example.com' }, e: e2 })).status);
    check('the sixth sign-in link for one address in an hour is refused', codes.slice(0, 5).every(c => c === 200) && codes[5] === 429, codes.join());
    codes = [];
    for (let i = 0; i < 17; i++) codes.push((await call('POST', '/api/auth/request', { body: { email: 'user' + i + '@example.com' }, ip: '198.51.100.7', e: e2 })).status);
    check('one connection is limited too', codes.includes(429) && codes[0] === 200, codes.join());
    const e3 = { SITE_ORIGIN: ORIGIN, MAIL_DAILY_CAP: '3', EMAIL: { send: async () => {} } };
    clock += 3 * 86400000;
    codes = [];
    for (let i = 0; i < 5; i++) codes.push((await call('POST', '/api/auth/request', { body: { email: 'cap' + i + '@example.com' }, e: e3 })).status);
    check('the site-wide daily cap protects the mail quota', codes.filter(c => c === 200).length === 3 && codes[4] === 429, codes.join());
  }

  // ---- mail providers and dev mode
  {
    const calls = [];
    const realFetch = global.fetch;
    global.fetch = async (u, init) => { calls.push({ u: String(u), init }); return new Response('{}', { status: 200 }); };
    clock += 3 * 86400000;
    const r1 = await call('POST', '/api/auth/request', { body: { email: 'viaresend@example.com' }, e: { SITE_ORIGIN: ORIGIN, RESEND_API_KEY: 'test-key', MAIL_FROM: 'X <x@y.z>' } });
    global.fetch = realFetch;
    const payload = calls[0] && JSON.parse(calls[0].init.body);
    check('Resend path posts to the Resend API with the key and recipient',
          r1.status === 200 && calls[0].u === 'https://api.resend.com/emails' &&
          calls[0].init.headers.Authorization === 'Bearer test-key' && payload.to[0] === 'viaresend@example.com' && payload.from === 'X <x@y.z>');
    check('the API key never appears in a response', !JSON.stringify(r1.json).includes('test-key'));
    global.fetch = async () => new Response('no', { status: 500 });
    const r2 = await call('POST', '/api/auth/request', { body: { email: 'fails@example.com' }, e: { SITE_ORIGIN: ORIGIN, RESEND_API_KEY: 'k' } });
    global.fetch = realFetch;
    check('a provider failure is reported as mail_failed, not as success', r2.status === 502 && r2.json.error === 'mail_failed');
    const remote = await call('POST', '/api/auth/request', { body: { email: 'dev@example.com' }, e: { AUTH_DEV_MODE: '1', SITE_ORIGIN: ORIGIN } });
    check('dev mode is ignored on a real host (a link would be an account takeover)', remote.status === 503 && !remote.json.devLink);
  }

  // ---- the weekly chapter email
  {
    const order = { chapters: [
      { title: '1 Enoch 1', part: 'The Book of the Watchers', url: '/read/1-enoch/1/', excerpt: 'The words of the blessing of Enoch.' },
      { title: '1 Enoch 2', part: 'The Book of the Watchers', url: '/read/1-enoch/2/', excerpt: 'Observe ye everything.' }
    ] };
    const wenv = { SITE_ORIGIN: ORIGIN, RESEND_API_KEY: 'rk', MAIL_FROM: 'X <x@y.z>', WEEKLY_SECRET: 'sekrit',
                   ASSETS: { fetch: async () => new Response(JSON.stringify(order)) } };
    const calls = [];
    const realFetch = global.fetch;
    global.fetch = async (u, init) => { calls.push({ u: String(u), body: JSON.parse(init.body) }); return new Response('{"data":[]}', { status: 200 }); };
    const run = (body, auth = 'Bearer sekrit') => handler(new Request(ORIGIN + '/api/weekly/run', {
      method: 'POST', headers: { 'content-type': 'application/json', authorization: auth }, body: JSON.stringify(body) }), wenv)
      .then(async r => ({ status: r.status, json: await r.json() }));
    clock += 30 * 86400000;
    check('the weekly run refuses a wrong secret', (await run({ mode: 'send' }, 'Bearer nope')).status === 401);
    check('the weekly run refuses with no secret configured',
          (await handler(new Request(ORIGIN + '/api/weekly/run', { method: 'POST', headers: { 'content-type': 'application/json', authorization: 'Bearer ' } , body: '{"mode":"dry"}' }), { ...wenv, WEEKLY_SECRET: '' })).status === 401);
    await call('POST', '/api/subscribe', { body: { email: 'weekly.one@example.com' } });
    await call('POST', '/api/subscribe', { body: { email: 'weekly.two@example.com' } });
    let d = await run({ mode: 'dry' });
    check('a dry run sends nothing and says nobody is due before the week begins',
          d.status === 200 && calls.length === 0 && d.json.due === 0, JSON.stringify(d.json));
    clock = W.weekStart(clock) + W.WEEKLY.weekMs + 3600000; // the next Sunday, 13:00 UTC
    d = await run({ mode: 'dry' });
    check('a dry run counts who would get which chapter, names nobody, and sends nothing',
          d.json.due === 2 && d.json.preview['1 Enoch 1'] === 2 && !JSON.stringify(d.json).includes('weekly.one') && calls.length === 0, JSON.stringify(d.json));
    const t1 = await run({ mode: 'test', to: 'owner@example.com' });
    const m = calls[0] && calls[0].body[0];
    check('a test send is one email, marked [Test], through the Resend batch API',
          t1.status === 200 && calls.length === 1 && calls[0].u === 'https://api.resend.com/emails/batch' &&
          m.to[0] === 'owner@example.com' && /^\[Test\] This week's chapter: 1 Enoch 1/.test(m.subject), JSON.stringify(t1.json));
    check('the email has the chapter link, the excerpt, a plain footer and one-click unsubscribe headers',
          m.text.includes(ORIGIN + '/read/1-enoch/1/') && m.text.includes('The words of the blessing of Enoch.') &&
          /Unsubscribe \(one click\): https:\/\/thebookandme\.test\/api\/unsubscribe\?e=owner%40example\.com&t=[\w-]{32}/.test(m.text) &&
          m.headers['List-Unsubscribe-Post'] === 'List-Unsubscribe=One-Click' && !/<img/i.test(m.html));
    check('a test send moves nobody along', (await run({ mode: 'dry' })).json.due === 2);
    calls.length = 0;
    let s1 = await run({ mode: 'send' });
    check('the send goes to every due subscriber, each their next chapter',
          s1.json.sent === 2 && calls.length === 1 && calls[0].body.length === 2 &&
          calls[0].body.every(x => /1 Enoch 1/.test(x.subject)), JSON.stringify(s1.json));
    calls.length = 0;
    s1 = await run({ mode: 'send' });
    check('a second run the same week sends nothing', s1.json.sent === 0 && calls.length === 0);
    clock += W.WEEKLY.weekMs;
    s1 = await run({ mode: 'send' });
    check('the next week brings the next chapter', s1.json.sent === 2 && calls[0].body.every(x => /1 Enoch 2/.test(x.subject)));
    const link = /Unsubscribe \(one click\): (\S+)/.exec(calls[0].body[0].text)[1].replace(ORIGIN, '');
    const who = decodeURIComponent(/e=([^&]+)/.exec(link)[1]);
    let u = await handler(new Request(ORIGIN + link.replace(/t=[\w-]+/, 't=' + 'x'.repeat(32))), wenv);
    check('a forged unsubscribe token is refused', u.status === 400);
    u = await handler(new Request(ORIGIN + link), wenv);
    check('the unsubscribe link works in one click (GET) and says so', u.status === 200 && /Unsubscribed/.test(await u.text()));
    calls.length = 0;
    clock += W.WEEKLY.weekMs;
    s1 = await run({ mode: 'send' });
    check('an unsubscribed address gets nothing more', s1.json.sent === 1 && calls[0].body[0].to[0] !== who);
    const other = calls[0].body[0].to[0];
    const link2 = /Unsubscribe \(one click\): (\S+)/.exec(calls[0].body[0].text)[1];
    const p = await handler(new Request(link2, { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: 'List-Unsubscribe=One-Click' }), wenv);
    check('the RFC 8058 one-click POST from a mail program works without an Origin', p.status === 200);
    calls.length = 0;
    clock += W.WEEKLY.weekMs;
    s1 = await run({ mode: 'send' });
    check('and that address is off the list too', s1.json.sent === 0 && s1.json.subscribers === 0, other);
    // the cap: fill the day, and the send waits rather than going over
    await call('POST', '/api/subscribe', { body: { email: 'weekly.three@example.com' } });
    clock += W.WEEKLY.weekMs;
    const day = Math.floor(clock / 86400000) * 24;
    await store.add('global', day, 75);
    calls.length = 0;
    s1 = await run({ mode: 'send' });
    check('the weekly send keeps sign-in room under the daily cap and waits for another day',
          s1.json.sent === 0 && s1.json.room === 0 && calls.length === 0, JSON.stringify(s1.json));
    clock += 86400000;
    s1 = await run({ mode: 'send' });
    check('the next day picks up who the cap left over', s1.json.sent === 1);
    global.fetch = realFetch;
  }

  // ---- the deployed entry point hands everything else to the static site
  {
    const env2 = { ASSETS: { fetch: async () => new Response('static') } };
    const res = await W.default.fetch(new Request(ORIGIN + '/read/genesis/1/'), env2);
    check('non-API requests go straight to the static site', await res.text() === 'static');
    const res2 = await W.default.fetch(new Request(ORIGIN + '/api/me'), env2);
    check('/api with no database configured says so', res2.status === 503 && (await res2.json()).error === 'accounts_not_configured');
  }
}

async function main() {
  const W = await import(pathToFileURL(path.join(__dirname, '..', 'worker', 'worker.js')).href);
  await suite('worker, in-memory store', W, () => new W.MemoryStore());

  let sqlite = null;
  try { sqlite = require('node:sqlite'); } catch (e) { /* older Node */ }
  if (sqlite) {
    const sql = require('fs').readFileSync(path.join(__dirname, '..', 'migrations', '0001_accounts.sql'), 'utf8');
    await suite('worker, D1 store on SQLite (migration applied as shipped)', W,
                () => new W.D1Store(d1Shim(sqlite.DatabaseSync, sql)));
  } else {
    console.log('\nworker, D1 store: skipped (needs node:sqlite, Node 22.13 or newer)');
  }

  console.log(`\n${passed} passed, ${failed.length} failed`);
  if (failed.length) { failed.forEach(f => console.log('  . ' + f)); process.exit(1); }
}
main().catch(e => { console.error(e); process.exit(1); });
