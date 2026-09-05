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

     Measured at 743px on a 568px iPhone SE, which is a Bible you arrive at
     and see no Bible on. Gated as a number because it drifts back a row at a
     time and is noticed by nobody until somebody opens Genesis on a phone.

     Two checks rather than one. The budget catches slow drift; the fold
     catches the thing the budget is a proxy for, and says it in the terms
     that matter -- there is scripture on the screen when the page opens. */
  {
    const { devices } = require('playwright');
    for (const name of ['iPhone SE', 'iPhone 14 Pro', 'Pixel 7']) {
      const phone = await ctx.browser.newContext({ ...devices[name] });
      const page = await phone.newPage();
      await page.goto(ctx.base + '#/read/genesis/0');
      await page.waitForSelector('.reader .v');
      const seen = await page.evaluate(() => ({
        top: Math.round(document.querySelector('.reader .v')
               .getBoundingClientRect().top + window.scrollY),
        vh: window.innerHeight
      }));
      t.check('on ' + name + ', the scripture starts within its budget',
              seen.top <= 420, seen.top + 'px, budget 420');
      t.check('and is on screen when the page opens',
              seen.top < seen.vh, seen.top + 'px into a ' + seen.vh + 'px screen');
      await phone.close();
    }
  }

  /* ---- and where the apparatus went to make room ----

     Reordered rather than removed, so what has to be checked is that it is
     still all there and still reachable, on both sides of the breakpoint. A
     phone turned on its side crosses it -- a 14 Pro is 393px upright and 852
     across -- so the move has to work in both directions and not once. */
  {
    const { devices } = require('playwright');
    const look = () => ({
      navInHead: !!document.querySelector('.reader-head .chapter-nav'),
      notesFirst: !!(document.querySelector('.work-notes') &&
        (document.querySelector('.work-notes').compareDocumentPosition(
          document.querySelector('.reader')) & Node.DOCUMENT_POSITION_FOLLOWING)),
      links: document.querySelectorAll('.chapter-strip a').length,
      note: !!document.querySelector('.note-block')
    });

    const desk = await ctx.browser.newContext({ viewport: { width: 1280, height: 900 } });
    const wide = await desk.newPage();
    await wide.goto(ctx.base + '#/read/genesis/0');
    await wide.waitForSelector('.reader .v');
    const onDesk = await wide.evaluate(look);
    t.check('on a wide screen the apparatus is where it always was',
            onDesk.navInHead && onDesk.notesFirst, JSON.stringify(onDesk));
    await desk.close();

    const phone = await ctx.browser.newContext({ ...devices['iPhone 14 Pro'] });
    const page = await phone.newPage();
    await page.goto(ctx.base + '#/read/genesis/0');
    await page.waitForSelector('.reader .v');

    const up = await page.evaluate(look);
    t.check('on a phone it is after the chapter instead',
            !up.navInHead && !up.notesFirst, JSON.stringify(up));
    t.check('and nothing was dropped to get it there',
            up.links === 50 && up.note, up.links + ' chapter links, note ' + up.note);

    await page.setViewportSize({ width: 852, height: 393 });
    await page.waitForTimeout(250);
    const turned = await page.evaluate(look);
    t.check('turning the phone sideways puts it back above',
            turned.navInHead && turned.notesFirst, JSON.stringify(turned));

    await page.setViewportSize({ width: 393, height: 852 });
    await page.waitForTimeout(250);
    const back = await page.evaluate(look);
    t.check('and turning it upright moves it down again',
            !back.navInHead && !back.notesFirst && back.links === 50,
            JSON.stringify(back));
    await phone.close();
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


  /* ---- the transport, under a thumb ----

     The player is what somebody holds a phone for: it is fixed over the page
     while the voice reads, and its buttons are pressed one-handed, often
     without looking straight at them. They were 35px, and the play button 42
     -- the smallest controls on the site after the chapter numbers, on the
     panel where a mis-tap stops the reading.

     Two numbers are gated because the fix has a cost and the cost has a
     limit. Making them thumb-sized took the panel from 177px to 254, which
     over a 568px phone is nearly half the screen covered while the highlight
     is trying to show where the voice has got to; scoping it to the transport
     and leaving the settings row alone brought it back to 209. So: the
     controls are 44px, and the panel does not grow past what that costs. */
  {
    const { devices } = require('playwright');
    const phone = await ctx.browser.newContext({ ...devices['iPhone SE'] });
    await phone.addInitScript(workingEngine(20));
    const page = await phone.newPage();
    await page.goto(ctx.base + '#/read/genesis/0');
    await page.waitForSelector('.reader .v');
    await page.locator('button[data-listen]').first().click();
    await page.waitForSelector('.player:not([hidden])');

    const seen = await page.evaluate(() => {
      const p = document.querySelector('.player');
      const small = [...p.querySelectorAll('.player-line:not(.player-opts) .player-btn')]
        .map(b => { const r = b.getBoundingClientRect();
                    return { n: b.getAttribute('aria-label') || '?',
                             w: Math.round(r.width), h: Math.round(r.height) }; })
        .filter(b => b.w < 44 || b.h < 44);
      return { small, height: Math.round(p.getBoundingClientRect().height),
               fixed: getComputedStyle(p).position === 'fixed' };
    });

    t.check('every transport control is a 44px target on a touch screen',
            seen.small.length === 0,
            seen.small.map(b => b.n + ' ' + b.w + 'x' + b.h).join(', ') || 'all 44+');
    t.check('and the panel is drawn over the page rather than pushed into it',
            seen.fixed, seen.fixed ? 'fixed' : 'NOT fixed');
    t.check('and does not cover more of the phone than that costs',
            seen.height <= 215, seen.height + 'px, budget 215');
    await phone.close();
  }

};
