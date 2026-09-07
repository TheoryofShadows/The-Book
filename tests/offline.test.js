'use strict';

/* The single-file build is the same code with the data inlined. If it stops
   working the claim that the library runs offline stops being true. */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { workingEngine, runPython } = require('./harness');

module.exports = async function offline(t, ctx) {
  const out = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'thebook-')), 'the-book.html');
  try {
    runPython([path.join(ctx.root, 'tools', 'build_standalone.py'),
                             path.join(ctx.root, 'docs'), out], { stdio: 'pipe' });
  } catch (e) {
    t.check('the single-file build runs', false, String(e.message).split('\n')[0]);
    return;
  }
  t.check('the single-file build runs', fs.existsSync(out),
          Math.round(fs.statSync(out).size / 1048576) + ' MB');

  const page = ctx.tally.watch(await ctx.browser.newPage(), 'offline');
  await page.addInitScript(workingEngine(30));
  // file://, so nothing can be fetched even if the code tried to
  await page.goto('file://' + out + '#/read/amos/2');
  await page.waitForSelector('.reader .v', { timeout: 30000 });
  t.check('it reads from a file with no server at all', true);
  t.check('and still offers to read the chapter aloud',
          await page.locator('[data-listen]').count() === 1);
  await page.locator('[data-listen]').click();
  t.check('which works with no network',
          await page.waitForFunction(() => window.__spoken && window.__spoken.length >= 2,
                                     null, { timeout: 6000 }).then(() => true).catch(() => false));

  /* The recorded reading is fetched from an archive, so this is the one build
     that must not offer it: a voice in the drawer that cannot be reached from
     a file:// URL with the network off is exactly the dead link the footer
     download is cut to avoid. The device engine is the whole story here. */
  const drawer = await page.evaluate(() => Array.from(
    document.querySelectorAll('select[aria-label="Voice"] optgroup'), g => g.label));
  t.check('and the offline copy does not offer a voice it would have to fetch',
          drawer.indexOf('Read aloud') === -1, JSON.stringify(drawer));

  /* The build used to name the data files it inlined one by one, so anything
     added later was quietly missing here and the feature resting on it died
     with only a failed fetch to show for it. These are the ones that were
     lost: what survives, the definitions, the places and the threads. */
  const bundled = await page.evaluate(() => Object.keys(window.__BOOK__ || {}));
  const missing = ['manuscripts.json', 'threads.json', 'lexicon-aliases.json']
    .filter(f => bundled.indexOf(f) < 0);
  t.check('every data file the site fetches is in the offline copy',
          missing.length === 0 && bundled.some(k => k.indexOf('lexicon/') === 0) &&
          bundled.some(k => k.indexOf('places/') === 0),
          missing.length ? 'missing ' + missing.join(', ') : bundled.length + ' files');

  // Amos has no surviving witness of its own; Habakkuk does (the Qumran
  // commentary), so that is the chapter to ask.
  await page.goto('file://' + out + '#/read/habakkuk/0');
  await page.waitForSelector('.reader .v');
  await page.waitForTimeout(400);
  t.check('the manuscripts panel is there offline',
          await page.locator('details.witnesses').count() > 0);

  await page.goto('file://' + out + '#/threads');
  await page.waitForTimeout(600);
  t.check('the threads page works offline',
          await page.locator('.thread-card').count() > 0);

  /* The served page offers this file for download. Inlined here that link
     would point from the offline copy at the offline copy, resolving to a
     file:// path beside it that is not there -- a dead link in the one build
     whose whole claim is that nothing it needs is anywhere else. It is cut
     out by the online-only markers in index.html, and this is what notices
     if that stops happening. */
  const selfLink = await page.locator('a[href$="the-book.html"]').count();
  t.check('and it does not link to itself for a copy it already is',
          selfLink === 0, selfLink ? selfLink + ' such links' : 'none');

  /* Nothing else on the page may point at a file either: every remaining
     link is a route, an anchor, or an outside address that a reader with no
     network simply cannot follow rather than one this build broke. */
  const local = await page.evaluate(() => Array.from(document.querySelectorAll('a[href]'))
    .map(a => a.getAttribute('href'))
    .filter(h => h && !/^(#|https?:|mailto:|data:)/.test(h)));
  t.check('and no link in it points at a file that is not there',
          local.length === 0, local.slice(0, 4).join(', '));

  await page.goto('file://' + out + '#/read/amos/2');
  await page.waitForSelector('.reader .v');
  await page.evaluate(() => {
    const w = document.querySelector('.reader .v').lastChild;
    const r = document.createRange();
    r.setStart(w, 5); r.setEnd(w, 9);
    const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
  });
  await page.keyboard.press('d');
  t.check('word definitions work offline',
          await page.waitForSelector('.lex', { timeout: 4000 }).then(() => true).catch(() => false));
  await page.close();
  /* The map suite checks the same single-file build, and building a 12 MB
     copy twice to check two things about it is a minute of CI for nothing.
     Hand it over; run.js clears the directory once every suite is done. */
  ctx.standalone = out;
  ctx.cleanup.push(path.dirname(out));
};
