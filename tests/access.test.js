'use strict';

/* The site against axe-core, on every route and in both themes.
 *
 * Colour contrast is checked in tests/python/test_palette.py, off the
 * stylesheet, because that catches it before a browser is involved. This is
 * the rest of it: names on controls, roles that match behaviour, landmarks,
 * headings in order, and the things a keyboard can and cannot reach.
 *
 * It found one thing on its first run, and a real one. A table too wide for
 * the screen sits in a box that scrolls sideways, and a box that scrolls and
 * cannot be focused is a box a keyboard cannot scroll -- so on the accuracy
 * report the right-hand columns were reachable with a pointer and by no
 * other means. The boxes are focusable, named and announced as regions now.
 *
 * The map is opened before the scan on a reading route, because a canvas,
 * its controls and the list beside it are the densest thing here and they
 * are built after the page is.
 */

const fs = require('fs');
const path = require('path');

const AXE = fs.readFileSync(
  path.join(__dirname, 'node_modules', 'axe-core', 'axe.min.js'), 'utf8');

const ROUTES = ['#/', '#/threads', '#/contents', '#/canons', '#/search/shepherd',
                '#/saved', '#/accuracy', '#/method', '#/timeline',
                '#/read/genesis/0', '#/read/amos/2'];

module.exports = async function access(t, ctx) {
  for (const scheme of ['light', 'dark']) {
    const page = ctx.tally.watch(
      await ctx.browser.newPage({ colorScheme: scheme }), 'access ' + scheme);

    const found = [];
    for (const route of ROUTES) {
      await page.goto(ctx.base + route, { waitUntil: 'networkidle' });
      await page.waitForTimeout(400);

      if (route.startsWith('#/read')) {
        const summary = page.locator('.chapter-map > summary');
        if (await summary.count()) {
          await summary.click();
          await page.waitForSelector('.map-canvas, .chapter-map .empty',
                                     { timeout: 15000 });
          await page.waitForTimeout(400);
        }
      }

      await page.addScriptTag({ content: AXE });
      const result = await page.evaluate(async () => await window.axe.run(
        document,
        { runOnly: { type: 'tag',
                     values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } }));
      result.violations.forEach(v => found.push(
        `${route}: ${v.id} (${v.impact}) — ${v.nodes.length} node(s)`));
    }

    t.check(`nothing fails WCAG A or AA in the ${scheme} theme`,
            found.length === 0,
            found.length ? found.slice(0, 4).join(' | ')
                         : ROUTES.length + ' routes clean');
    await page.close();
  }

  /* ---- and the fix that finding produced, held on its own ---- */
  const page = ctx.tally.watch(await ctx.browser.newPage(), 'access keys');
  await page.goto(ctx.base + '#/accuracy');
  await page.waitForSelector('.scroller');
  const reachable = await page.evaluate(() => Array.from(
    document.querySelectorAll('.scroller'),
    s => ({ tabindex: s.getAttribute('tabindex'),
            role: s.getAttribute('role'),
            named: !!s.getAttribute('aria-label') })));
  t.check('a table that scrolls sideways can be scrolled without a pointer',
          reachable.length > 0 &&
          reachable.every(s => s.tabindex === '0' && s.role === 'region' && s.named),
          reachable.length + ' scrollable region(s)');

  /* The skip link is the first thing a keyboard reaches and the one control
     whose whole job is to be found by one. */
  await page.goto(ctx.base + '#/');
  await page.waitForSelector('.wrap');
  await page.keyboard.press('Tab');
  const first = await page.evaluate(() => {
    const a = document.activeElement;
    return { text: (a.textContent || '').trim(), href: a.getAttribute('href'),
             visible: a.getBoundingClientRect().top >= 0 };
  });
  t.check('the first tab stop is the skip link, and it shows itself',
          /skip/i.test(first.text) && first.href === '#main' && first.visible,
          first.text + ' -> ' + first.href);

  await page.close();
};
