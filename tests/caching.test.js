'use strict';

/* Whether the service worker keeps the promise it is under.
 *
 * tests/python/test_sw.py checks the stamp and reads the worker for the
 * shapes that trade freshness for speed. Neither of those is evidence that
 * the thing works: a worker can be network-first in every line and still hand
 * back a cached chapter, because what a browser does with a fetch handler is
 * not readable from the handler.
 *
 * So this runs one. It serves a copy of the site out of a temporary
 * directory -- a copy, because the point of the checks below is to change a
 * file underneath a running browser and see which version it answers with,
 * and doing that to docs/ would be editing the repository while testing it.
 *
 * The claim being tested is narrow and is the whole reason the worker is
 * allowed to exist: online, the answer is always the network's, however good
 * the cached copy looks. Offline, the answer is the last one really fetched,
 * and the page says so.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { serve } = require('./harness');

const PROBE = 'data/probe.json';

function build(root) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sw-'));
  const site = path.join(dir, 'docs');
  /* The generated pages and the twelve-megabyte copy are not needed by any
     check here and are most of the bytes. */
  fs.cpSync(path.join(root, 'docs'), site, {
    recursive: true,
    filter: src => !/[\\/](read|contents)$|the-book\.html$/.test(src)
  });
  fs.writeFileSync(path.join(site, PROBE), JSON.stringify({ says: 'first' }));
  execFileSync('python3', [path.join(root, 'tools', 'build_sw.py'), site],
               { stdio: 'pipe' });
  return { dir, site };
}

/* The worker installs, activates and claims the page. Until it has, every
   check below would be measuring a page with no worker at all and passing
   for the wrong reason. */
async function controlled(page) {
  return page.evaluate(() => navigator.serviceWorker.ready
    .then(() => new Promise(done => {
      if (navigator.serviceWorker.controller) return done(true);
      navigator.serviceWorker.addEventListener('controllerchange',
                                               () => done(true));
      setTimeout(() => done(!!navigator.serviceWorker.controller), 4000);
    })));
}

const read = (page, url) => page.evaluate(
  u => fetch(u, { cache: 'no-store' }).then(r => r.json()).then(j => j.says)
        .catch(e => 'THREW: ' + e.message), url);

module.exports = async function (t, ctx) {
  const { dir, site } = build(ctx.root);
  ctx.cleanup.push(dir);
  const server = await serve(site);

  /* Its own context, so the worker and its caches cannot outlive this suite
     and leak into another one. */
  const browser = ctx.browser;
  const context = await browser.newContext();
  /* Not watched for console errors, on the same grounds as the bad-routes
     page in resilience.test.js: the failures are the point. Reading
     something never cached with the network off is meant to be a 503, and
     the browser logs every one of them. A watched page here would report
     the worker doing its job as five defects. */
  const page = await context.newPage();

  try {
    await page.goto(server.url);
    t.check('the worker takes control of the page', await controlled(page));

    const version = await page.evaluate(() =>
      fetch('sw.js').then(r => r.text())
        .then(s => (s.match(/var VERSION = "([0-9a-f]+)"/) || [])[1]));
    t.check('and it carries a stamp', /^[0-9a-f]{12}$/.test(version), version);

    /* ---------------- the promise ---------------- */

    t.check('a first read gets what is on the server',
            await read(page, PROBE) === 'first');

    /* Changed underneath the running browser. A worker that answered from
       its cache here would be indistinguishable from a working one to
       anybody reading the code, and would be serving yesterday's text. */
    fs.writeFileSync(path.join(site, PROBE), JSON.stringify({ says: 'second' }));

    const online = await read(page, PROBE);
    t.check('online, a changed file is read again from the network, not the cache',
            online === 'second', online);

    fs.writeFileSync(path.join(site, PROBE), JSON.stringify({ says: 'third' }));
    const again = await read(page, PROBE);
    t.check('and again, so it is not a one-off revalidation',
            again === 'third', again);

    /* ---------------- the fallback ---------------- */

    await context.setOffline(true);

    const offline = await read(page, PROBE);
    t.check('offline, the last thing really fetched is served',
            offline === 'third', offline);

    const never = await page.evaluate(() =>
      fetch('data/never-asked-for.json').then(r => r.status).catch(() => 'failed'));
    t.check('and something never fetched is not invented',
            never === 503 || never === 'failed', String(never));

    /* ---------------- saying so ---------------- */

    await page.evaluate(() => window.dispatchEvent(new Event('offline')));
    await page.waitForTimeout(120);
    const noted = await page.locator('.offline-note').count();
    t.check('the page says it is offline rather than looking identical',
            noted === 1, noted + ' notice(s)');

    const wording = await page.locator('.offline-note').innerText();
    t.check('and does not claim more than navigator.onLine knows',
            /may not be current/.test(wording), wording.slice(0, 60));

    await page.evaluate(() => window.dispatchEvent(new Event('online')));
    await page.waitForTimeout(120);
    t.check('and takes it back when the network returns',
            (await page.locator('.offline-note').count()) === 0);

    await context.setOffline(false);

    /* ---------------- a navigation with nothing behind it ---------------- */

    await context.setOffline(true);
    const shell = await page.goto(server.url + 'read/genesis/1/',
                                  { waitUntil: 'load' }).catch(() => null);
    t.check('an offline navigation to a page never fetched still opens the reader',
            !!shell && (await page.locator('.topbar').count()) === 1,
            shell ? String(shell.status()) : 'no response');
    await context.setOffline(false);

    /* ---------------- a new deploy ---------------- */

    /* The stamp is a hash of what the worker serves, so touching the reader
       is a new worker and a new cache. The old one has to go, or a file
       deleted upstream is served from it for good. */
    const before = await page.evaluate(() => caches.keys());
    fs.appendFileSync(path.join(site, 'assets', 'app.css'), '\n/* deploy */\n');
    execFileSync('python3', [path.join(ctx.root, 'tools', 'build_sw.py'), site],
                 { stdio: 'pipe' });

    await page.goto(server.url);
    await page.evaluate(() => navigator.serviceWorker.getRegistration()
      .then(r => r && r.update()));
    await page.waitForTimeout(1200);
    await page.goto(server.url);
    await controlled(page);

    const after = await page.evaluate(() => caches.keys());
    t.check('a changed site is a changed stamp and a fresh set of caches',
            after.length > 0 && after.every(n => before.indexOf(n) === -1),
            'was [' + before + '], now [' + after + ']');

  } finally {
    await page.close();
    await context.close();
    await server.close();
  }
};
