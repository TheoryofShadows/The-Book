'use strict';

/* Whether a phone can install this, asked of a browser rather than of the
 * files.
 *
 * tests/python/test_webmanifest.py already holds the manifest to the icons
 * and colours it names, and that is a check of agreement between files. It
 * cannot answer the question that actually matters, which is whether a
 * browser standing on a page can reach any of it. The manifest is linked
 * relatively and the 2,709 generated pages sit at three different depths, so
 * the link on a chapter page is ../../../site.webmanifest and the one on the
 * contents hub is ../site.webmanifest. Both are arithmetic, and arithmetic
 * done by hand in a string is exactly the thing to make a browser check.
 *
 * What this cannot do is install anything. There is no Add to Home Screen in
 * a headless Chromium and no iOS here at all, so the install itself, the name
 * under the icon and the standalone window are left to a real device and are
 * not claimed anywhere in here.
 */

module.exports = async function (t, ctx) {
  const page = ctx.tally.watch(await ctx.browser.newPage(), 'installable');

  /* ---------------- the front page ---------------- */

  await page.goto(ctx.base);

  const href = await page.getAttribute('link[rel=manifest]', 'href');
  t.check('the front page links a manifest', href === 'site.webmanifest', href);

  /* Resolved by the browser against the page it is on, which is the whole
     point: a href that looks right in the source and resolves to nothing is
     the failure being hunted here. */
  const resolved = await page.evaluate(() =>
    document.querySelector('link[rel=manifest]').href);

  const res = await page.request.get(resolved);
  t.check('and the browser can fetch it from where that resolves',
          res.status() === 200, resolved + ' -> ' + res.status());

  t.check('served as a manifest rather than as bytes',
          (res.headers()['content-type'] || '').indexOf('manifest+json') !== -1,
          res.headers()['content-type']);

  let manifest = null;
  try { manifest = JSON.parse(await res.text()); } catch (e) { /* reported below */ }
  t.check('the manifest parses in the browser', !!manifest,
          manifest ? 'ok' : 'did not parse');

  /* Everything above is this file's own reading of the manifest, and a
     reading can agree with itself and still be wrong about what a browser
     will do with it. This asks Chrome. Page.getAppManifest returns the
     errors the browser's own parser raised, so an invalid display value, a
     colour it cannot read or a field it rejects shows up here as a sentence
     from the browser rather than as a check nobody wrote. */
  const cdp = await page.context().newCDPSession(page);
  const seen = await cdp.send('Page.getAppManifest');
  t.check('Chrome parses the manifest with no errors of its own',
          Array.isArray(seen.errors) && seen.errors.length === 0,
          (seen.errors || []).map(e => e.message).join('; ') || 'none');

  /* ---------------- the icons ---------------- */

  /* A manifest naming an icon that 404s is a manifest that installs a blank
     square, and nothing on the page shows it: the fetch happens at install
     time, on somebody's phone, once. */
  if (manifest) {
    for (const icon of manifest.icons) {
      const url = new URL(icon.src, resolved).href;
      const got = await page.request.get(url);
      const body = await got.body();
      t.check('the ' + icon.sizes + ' icon is really served',
              got.status() === 200 && body.length > 0,
              icon.src + ' -> ' + got.status() + ', ' + body.length + ' bytes');

      /* The PNG header, so a JSON entry cannot claim a size the file is not.
         Width and height are the two big-endian words after the IHDR tag. */
      const w = body.readUInt32BE(16), h = body.readUInt32BE(20);
      t.check('and is the ' + icon.sizes + ' it says it is',
              w + 'x' + h === icon.sizes, w + 'x' + h);
    }

    t.check('start_url resolves to the reader, not to a chapter',
            new URL(manifest.start_url, resolved).href === ctx.base,
            new URL(manifest.start_url, resolved).href);
  }

  /* ---------------- the half iOS reads ---------------- */

  /* iOS installs from these and not from the manifest, so their absence is a
     platform lost with nothing else changing. */
  for (const name of ['mobile-web-app-capable',
                      'apple-mobile-web-app-capable',
                      'apple-mobile-web-app-title']) {
    const got = await page.getAttribute('meta[name="' + name + '"]', 'content');
    t.check(name + ' is on the page', !!got, String(got));
  }

  const bar = await page.getAttribute(
    'meta[name="apple-mobile-web-app-status-bar-style"]', 'content');
  t.check('the status bar is not translucent, which would put the header under it',
          bar && bar !== 'black-translucent', String(bar));

  /* ---------------- the depths ---------------- */

  /* Where the arithmetic in build_pages.py either holds or does not. A phone
     arriving from a search result lands on one of these, not on the page
     above, so if the link resolves to nothing here then installing from
     search -- which is most installing -- is what is broken. */
  for (const [where, path] of [['a chapter, three deep', 'read/genesis/1/'],
                               ['a work, two deep', 'read/genesis/'],
                               ['the contents hub, one deep', 'contents/']]) {
    await page.goto(ctx.base + path);
    const at = await page.evaluate(() => {
      const link = document.querySelector('link[rel=manifest]');
      return link ? link.href : null;
    });
    t.check('the manifest resolves from ' + where,
            at === ctx.base + 'site.webmanifest', String(at));

    const reached = at ? (await page.request.get(at)).status() : 0;
    t.check('and is fetchable from ' + where, reached === 200, String(reached));

    const title = await page.getAttribute(
      'meta[name="apple-mobile-web-app-title"]', 'content');
    t.check('and ' + where + ' carries the tags iOS installs from',
            title === 'The Book', String(title));
  }

  await page.close();
};
