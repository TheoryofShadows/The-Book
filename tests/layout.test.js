'use strict';

/* Layout, at the sizes this is actually read at. Most of the traffic is a
   phone, so the phone widths are the ones with the most checks. */

const { workingEngine } = require('./harness');

const PHONES = [320, 360, 390, 430];

/* Scrolling is smooth site-wide, so a fixed wait is a bet on how fast the
   machine is -- one that CI loses. These jump instead, and every assertion
   about the bar waits for the state rather than for the clock. */
const jumpScroll = page => page.evaluate(
  () => { document.documentElement.style.scrollBehavior = 'auto'; });

const tucked = page => page.evaluate(
  () => document.querySelector('.topbar').classList.contains('tucked'));

async function waitTucked(page, want, ms) {
  return page.waitForFunction(
    w => document.querySelector('.topbar').classList.contains('tucked') === w,
    want, { timeout: ms || 4000 }).then(() => true).catch(() => false);
}

const ROUTES = ['#/', '#/threads', '#/contents', '#/search/lion', '#/canons',
                '#/saved', '#/accuracy', '#/read/amos/2', '#/read/psalms/118'];

module.exports = async function layout(t, ctx) {
  for (const width of PHONES) {
    const page = ctx.tally.watch(
      await ctx.browser.newPage({ viewport: { width, height: 760 } }), width + 'px');
    await page.goto(ctx.base + '#/read/amos/2');
    await page.waitForSelector('.reader .v');
    await jumpScroll(page);

    const links = await page.evaluate(vw => Array.from(document.querySelectorAll('.nav a'))
      .map(a => {
        const b = a.getBoundingClientRect();
        return { text: a.textContent.trim(), on: b.left >= -1 && b.right <= vw + 1 && b.width > 0 };
      }), width);
    t.check(`${width}px: every nav link is fully on screen`,
            links.length === 7 && links.every(l => l.on),
            links.filter(l => !l.on).map(l => l.text).join(', ') || 'all seven');

    const nav = await page.evaluate(() => {
      const b = document.querySelector('.nav').getBoundingClientRect();
      return { y: Math.round(b.y), w: Math.round(b.width) };
    });
    t.check(`${width}px: the nav has a full-width row of its own`,
            nav.w >= width - 30 && nav.y > 20, `y ${nav.y}, ${nav.w}px wide`);

    t.check(`${width}px: nothing scrolls sideways`,
            await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));

    /* The bar is sticky and two rows tall, so it earns its keep by leaving. */
    // The class goes on first and the bar then slides; wait for it to have
    // actually left, which is the thing being claimed.
    await page.evaluate(() => window.scrollTo(0, 600));
    t.check(`${width}px: reading down puts the bar away`,
            await page.waitForFunction(
              () => document.querySelector('.topbar').getBoundingClientRect().bottom <= 1,
              null, { timeout: 4000 }).then(() => true).catch(() => false));

    await page.evaluate(() => window.scrollTo(0, 380));
    t.check(`${width}px: turning back up brings it straight back`,
            await waitTucked(page, false));

    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(200);
    await page.evaluate(() => window.scrollTo(0, 90));
    await page.waitForTimeout(400);
    t.check(`${width}px: it stays put near the top of the page`, !(await tucked(page)));

    await page.evaluate(() => window.scrollTo(0, 900));
    await waitTucked(page, true);
    await page.evaluate(() => { location.hash = '#/accuracy'; });
    await page.waitForSelector('h1');
    t.check(`${width}px: a new page opens with the bar showing`, !(await tucked(page)));
    await page.close();
  }

  /* Nothing anywhere may push the page sideways. The skip link is parked
     off-screen on purpose and is the one thing allowed to be out there. */
  const page = ctx.tally.watch(
    await ctx.browser.newPage({ viewport: { width: 360, height: 760 } }), 'overflow');
  for (const route of ROUTES) {
    await page.goto(ctx.base + route);
    await page.waitForTimeout(600);
    const spill = await page.evaluate(vw => {
      const out = [];
      document.querySelectorAll('body *').forEach(e => {
        if (e.classList.contains('skip')) return;
        const b = e.getBoundingClientRect();
        if (!b.width || (b.right <= vw + 1 && b.left >= -1)) return;
        for (let p = e; p && p !== document.body; p = p.parentElement) {
          const o = getComputedStyle(p).overflowX;
          if (o === 'auto' || o === 'scroll' || o === 'hidden') return;   // scrolls itself
        }
        out.push(e.tagName.toLowerCase() + '.' + String(e.className).split(' ')[0]);
      });
      return { page: document.documentElement.scrollWidth > vw + 1, out: out.slice(0, 4) };
    }, 360);
    t.check(`360px: ${route} stays inside the screen`, !spill.page && !spill.out.length,
            spill.out.join(', '));
  }
  await page.close();

  /* A table head that covers its own first row is a table that lies about
     what it contains, and the first row is the one that gets hidden: the
     contents opened on The Song of the Sea and showed the header instead.
     Checked at the widths where the wrapper does and does not scroll, since
     the bug came from the wrapper. */
  const heads = ctx.tally.watch(
    await ctx.browser.newPage({ viewport: { width: 1280, height: 900 } }), 'table heads');
  for (const width of [360, 760, 1280]) {
    await heads.setViewportSize({ width, height: 900 });
    for (const route of ['#/contents', '#/canons', '#/accuracy', '#/method']) {
      await heads.goto(ctx.base + route);
      await heads.waitForSelector('table.grid tbody tr');
      const covered = await heads.evaluate(() => {
        const bad = [];
        document.querySelectorAll('table.grid').forEach((table, i) => {
          const th = table.querySelector('thead th');
          const td = table.querySelector('tbody tr td');
          if (!th || !td) return;
          const head = th.getBoundingClientRect();
          const row = td.getBoundingClientRect();
          // Touching is right -- the head sits on the row's top edge. Any
          // further down and it is printed over the first line of data.
          if (head.bottom > row.top + 1)
            bad.push('table ' + i + ': head reaches ' + Math.round(head.bottom) +
                     ', row "' + td.textContent.trim().slice(0, 24) +
                     '" starts at ' + Math.round(row.top));
        });
        return bad;
      });
      t.check(`${width}px: ${route} shows the first row of every table`,
              covered.length === 0, covered.join('; '));
    }
  }
  await heads.close();

  /* The player is fixed to the bottom; the page has to give that space back. */
  const reader = ctx.tally.watch(
    await ctx.browser.newPage({ viewport: { width: 390, height: 780 } }), 'player');
  await reader.addInitScript(workingEngine(400));
  await reader.goto(ctx.base + '#/read/amos/2');
  await reader.waitForSelector('.reader .v');
  await reader.locator('[data-listen]').click();
  await reader.waitForSelector('.player:not([hidden])');
  await jumpScroll(reader);
  await reader.evaluate(() => window.scrollTo(0, 800));
  const barGone = await waitTucked(reader, true);
  t.check('the player stays put while the bar tucks away',
          barGone && await reader.evaluate(() => !document.querySelector('.player').hidden));
  await reader.locator('.player-play').click();          // stop it moving the page under us
  await reader.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await reader.waitForTimeout(500);
  t.check('and never covers the end of the page',
          await reader.evaluate(() => {
            const foot = document.querySelector('.foot .keys').getBoundingClientRect();
            const player = document.querySelector('.player').getBoundingClientRect();
            return foot.bottom <= player.top + 1;
          }));
  await reader.close();

  /* A desk is not a phone and keeps what it had. */
  const desk = ctx.tally.watch(
    await ctx.browser.newPage({ viewport: { width: 1280, height: 800 } }), 'desktop');
  await desk.goto(ctx.base + '#/read/amos/2');
  await desk.waitForSelector('.reader .v');
  t.check('desktop: the nav is still one row beside the wordmark',
          await desk.evaluate(() => new Set(Array.from(document.querySelectorAll('.nav a'))
            .map(a => Math.round(a.getBoundingClientRect().y))).size) === 1);
  await jumpScroll(desk);
  await desk.evaluate(() => window.scrollTo(0, 1200));
  await desk.waitForTimeout(400);
  t.check('desktop: the bar stays where it is',
          await desk.evaluate(() => !document.querySelector('.topbar').classList.contains('tucked') &&
                                    document.querySelector('.topbar').getBoundingClientRect().y === 0));

  /* ---- the chapter you are in is in the strip you are shown ----

     The strip is two rows deep and scrolls past that, so on a long book the
     chapter you are reading is usually not in the first two rows. It used to
     open at the top regardless: Psalm 119 showed you 1 to 60 and left you to
     hunt. Checked on the long book and the short one, because the fix must
     not scroll a book that fits. */
  for (const [route, expect] of [['#/read/psalms/118', '119'],
                                 ['#/read/genesis/0', '1']]) {
    await desk.goto(ctx.base + route);
    await desk.waitForSelector('.chapter-strip a[aria-current="true"]');
    await desk.waitForTimeout(300);
    const where = await desk.evaluate(() => {
      const strip = document.querySelector('.chapter-strip');
      const here = strip.querySelector('[aria-current="true"]');
      const s = strip.getBoundingClientRect(), h = here.getBoundingClientRect();
      return { label: here.textContent,
               inView: h.top >= s.top - 1 && h.bottom <= s.bottom + 1 };
    });
    t.check('the chapter strip opens on the chapter you are in',
            where.label === expect && where.inView,
            route + ' -> ' + where.label + (where.inView ? ', in view' : ', OFF SCREEN'));
  }
  await desk.close();

  /* ---- how far down the scripture starts on a phone ----

     A number rather than an opinion, because this is the kind of thing that
     drifts back a row at a time and nobody notices until a reader opens
     Genesis on a phone and sees a header, a breadcrumb, a title, a chapter
     box, fifty chapter numbers, a note, a dating panel and five buttons.
     Measured at 743px on a 568px iPhone SE, which is a Bible you arrive at
     and see no Bible on.

     The budget is per device and deliberately not "above the fold on all of
     them": clearing it on the smallest phone needs either the nav in one
     scrolling row or the apparatus moved below the text, and both reverse a
     decision this site has made on purpose and written down. What is gated
     is what was won without reversing anything -- so that it stays won. */
  {
    const { devices } = require('playwright');
    const BUDGET = [['iPhone SE', 710], ['iPhone 14 Pro', 670], ['Pixel 7', 670]];
    for (const [name, budget] of BUDGET) {
      const phone = await ctx.browser.newContext({ ...devices[name] });
      const page = await phone.newPage();
      await page.goto(ctx.base + '#/read/genesis/0');
      await page.waitForSelector('.reader .v');
      const top = await page.evaluate(() => Math.round(
        document.querySelector('.reader .v').getBoundingClientRect().top + window.scrollY));
      t.check('on ' + name + ', the scripture starts within its budget',
              top <= budget, top + 'px, budget ' + budget);
      await phone.close();
    }
  }

  /* The chapter numbers are the control a thumb uses most and were the
     smallest targets on the site at 25px. They sit in a box of a fixed
     height that scrolls, so making them meet the 44px Apple asks for costs
     no room on the page at all -- which is why it is done here and not
     argued about. */
  {
    const { devices } = require('playwright');
    const phone = await ctx.browser.newContext({ ...devices['iPhone SE'] });
    const page = await phone.newPage();
    await page.goto(ctx.base + '#/read/genesis/0');
    await page.waitForSelector('.chapter-strip a');
    const box = await page.evaluate(() => {
      const a = document.querySelector('.chapter-strip a').getBoundingClientRect();
      return { w: Math.round(a.width), h: Math.round(a.height) };
    });
    t.check('a chapter number is a 44px target on a phone',
            box.w >= 44 && box.h >= 44, box.w + 'x' + box.h);
    await phone.close();
  }

};
