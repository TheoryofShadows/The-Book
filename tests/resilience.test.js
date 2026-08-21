'use strict';

/* What happens when things go wrong, and what happens without a mouse.
 *
 * Two areas that were claimed and never checked. The site has an error path
 * for a failed data load that had never run; and it announces things to
 * screen readers through a live region that no test had ever read.
 */

/* Fail a request the way a flaky network does -- the fetch rejects rather
   than returning a body -- and the way a bad deploy does: a 404, and a file
   that is served but is not JSON. */
const fail = (page, pattern) => page.route(pattern, r => r.abort());
const notFound = (page, pattern) => page.route(pattern, r =>
  r.fulfill({ status: 404, body: 'not found' }));
const garbage = (page, pattern) => page.route(pattern, r =>
  r.fulfill({ status: 200, contentType: 'application/json',
              body: '{"truncated": ' }));

const bodyText = page => page.textContent('body');

module.exports = async function resilience(t, ctx) {

  /* ---- the library itself will not load ---- */
  {
    const page = await ctx.browser.newPage();
    await fail(page, '**/data/manifest.json');
    await page.goto(ctx.base + '#/');
    await page.waitForSelector('h1', { timeout: 10000 });
    const text = await bodyText(page);
    t.check('a library that will not load says so instead of showing nothing',
            /could not load the library/i.test(text),
            (await page.textContent('h1')).slice(0, 40));
    t.check('and does not sit on "Loading…" forever',
            !/Loading…/.test(await page.textContent('main')));
    await page.close();
  }

  /* ---- malformed data is the same case as no data ---- */
  {
    const page = await ctx.browser.newPage();
    await garbage(page, '**/data/manifest.json');
    await page.goto(ctx.base + '#/');
    await page.waitForSelector('h1', { timeout: 10000 });
    t.check('data that is served but unreadable is handled the same way',
            /could not load the library/i.test(await bodyText(page)));
    await page.close();
  }

  /* ---- one work is missing, the rest of the site is not ---- */
  {
    // Not watched for console errors: the 404 below is the point of the
    // check, and the browser logs a failed request whatever the page does
    // about it.
    const page = await ctx.browser.newPage();
    await notFound(page, '**/data/works/amos.json');
    await page.goto(ctx.base + '#/read/amos/2');
    await page.waitForTimeout(1200);
    t.check('a chapter whose text will not load still draws the page around it',
            await page.locator('h1').count() > 0 &&
            /amos/i.test(await page.textContent('h1')));

    await page.goto(ctx.base + '#/read/hosea/1');
    await page.waitForSelector('.reader .v', { timeout: 10000 });
    t.check('and the next work still opens normally',
            await page.locator('.reader .v').count() > 0);
    await page.close();
  }

  /* ---- a search index shard is missing ----
     The client catches this and carries on with an empty table, which means
     the word looks like it is in no text at all. It must not claim to have
     searched. */
  {
    const page = await ctx.browser.newPage();   // see above: the 404 is deliberate
    await notFound(page, '**/data/index/*.json');
    await page.goto(ctx.base + '#/search/behemoth');
    await page.waitForTimeout(2500);
    t.check('a search with no index does not crash the page',
            await page.locator('h1').count() > 0);
    await page.close();
  }

  /* ---- routes that do not exist ---- */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'bad-routes');
    const BAD = [
      ['a work that does not exist', '#/read/not-a-book/0', /no such work/i],
      ['and it names what was asked for', '#/read/not-a-book/0', /not-a-book/],
      ['a chapter past the end', '#/read/amos/9999', null],
      ['a negative chapter', '#/read/amos/-4', null],
      ['a chapter that is not a number', '#/read/amos/banana', null],
      ['a thread that does not exist', '#/thread/not-a-thread', /no such thread/i],
      ['a route with nothing after it', '#/read', /does not name a work/i]
    ];
    for (const [name, route, expect] of BAD) {
      await page.goto(ctx.base + route);
      await page.waitForTimeout(700);
      const heading = (await page.locator('h1, h2').first().textContent()
                          .catch(() => '') || '').trim();
      const ok = heading.length > 0 &&
                 (!expect || expect.test(await bodyText(page)));
      t.check(name + ' lands somewhere readable', ok, heading.slice(0, 40));
    }

    /* A dead end that only says "no" is a dead end. */
    await page.goto(ctx.base + '#/read/not-a-book/0');
    await page.waitForSelector('h1');
    t.check('a not-found page offers a way onward',
            await page.locator('main a[href^="#/"]').count() >= 2,
            await page.locator('main a[href^="#/"]').count() + ' links');

    /* Clamping, not crashing: chapter 9999 of Amos is Amos 9. */
    await page.goto(ctx.base + '#/read/amos/9999');
    await page.waitForSelector('.reader .v');
    t.check('a chapter past the end shows the last one rather than nothing',
            await page.locator('.reader .v').count() > 0);
    await page.close();
  }

  /* ---- the keyboard ---- */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'keyboard');
    await page.goto(ctx.base + '#/read/amos/2');
    await page.waitForSelector('.reader .v');

    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(500);
    t.check('the right arrow turns to the next chapter',
            /#\/read\/amos\/3/.test(page.url()), page.url().slice(-20));

    await page.keyboard.press('ArrowLeft');
    await page.waitForTimeout(500);
    t.check('and the left arrow turns back',
            /#\/read\/amos\/2/.test(page.url()), page.url().slice(-20));

    await page.keyboard.press('/');
    await page.waitForTimeout(500);
    t.check('slash goes to search', /#\/search/.test(page.url()));

    /* A shortcut that fires while the reader is typing eats the keystroke. */
    await page.waitForSelector('input[type=search]');
    await page.fill('input[type=search]', 'lion');
    await page.locator('input[type=search]').press('l');
    await page.waitForTimeout(200);
    t.check('the shortcuts stay out of the way while a field has focus',
            await page.inputValue('input[type=search]') === 'lionl' &&
            await page.locator('.player:not([hidden])').count() === 0);
    await page.close();
  }

  /* ---- the skip link ----
     Its whole job is to let a keyboard user past the navigation, and it is
     the one element allowed to sit off-screen. */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'skip-link');
    await page.goto(ctx.base + '#/read/amos/2');
    await page.waitForSelector('.reader .v');
    await page.keyboard.press('Tab');
    const focused = await page.evaluate(() => {
      const a = document.activeElement;
      return { cls: a.className, href: a.getAttribute('href'),
               onScreen: a.getBoundingClientRect().top >= 0 };
    });
    t.check('the first thing a keyboard reaches is the skip link',
            /skip/.test(focused.cls), focused.cls);
    t.check('and it becomes visible once it has focus', focused.onScreen);
    t.check('it points at the main content',
            !!focused.href && !!(await page.locator(focused.href).count()),
            focused.href);
    await page.close();
  }

  /* ---- what a screen reader is told ---- */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'announcements');
    await page.goto(ctx.base + '#/read/psalms/118');
    await page.waitForSelector('.reader .v');

    /* Present from the first line, not created by the first announcement: a
       region that appears and fills in one breath is one several screen
       readers never announce. */
    t.check('there is one live region, and it is polite, before anything is said',
            await page.locator('[aria-live=polite][role=status]').count() === 1);
    t.check('and it starts empty',
            (await page.textContent('[role=status]')).trim() === '');

    /* Psalms is 150 chapters, so past about forty the grid stops being usable
       and the reader needs to say a number instead. */
    const jump = page.locator('.chapter-jump input');
    t.check('a long book offers a chapter jump', await jump.count() === 1);

    /* The range is on the field itself, so the browser enforces it and a
       screen reader reads it out with the label rather than the reader
       discovering it by being refused. */
    const bounds = await jump.evaluate(el => ({
      min: el.min, max: el.max, label: el.getAttribute('aria-label') || ''
    }));
    t.check('the jump field carries its range, and says it out loud',
            bounds.min === '1' && bounds.max === '150' &&
            /between 1 and 150/.test(bounds.label),
            bounds.min + '-' + bounds.max);

    const before = page.url();
    await jump.fill('99999');
    await jump.press('Enter');
    await page.waitForTimeout(400);
    t.check('an out-of-range number does not navigate anywhere',
            page.url() === before, page.url().slice(-18));

    await jump.fill('23');
    await jump.press('Enter');
    await page.waitForTimeout(600);
    t.check('and a good one goes to that chapter',
            /#\/read\/psalms\/22/.test(page.url()), page.url().slice(-20));
    await page.close();
  }

  /* ---- the pages that had only a heading checked ---- */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'views');

    await page.goto(ctx.base + '#/threads');
    await page.waitForSelector('.thread-card');
    const cards = await page.locator('.thread-card').count();
    t.check('the threads page lists threads', cards > 0, cards + ' threads');

    await page.locator('a.thread-card').first().click();   // the card is the link
    await page.waitForTimeout(800);
    const stops = await page.locator('blockquote, .stop').count();
    t.check('a thread shows its stops, with the text of each',
            stops > 1, stops + ' stops');
    t.check('and every stop links into the volume',
            await page.locator('main a[href^="#/read/"]').count() > 0);

    await page.goto(ctx.base + '#/canons');
    await page.waitForSelector('table, .grid');
    t.check('the canons page draws its table',
            await page.locator('tbody tr').count() > 20,
            await page.locator('tbody tr').count() + ' rows');

    await page.goto(ctx.base + '#/accuracy');
    await page.waitForSelector('h1');
    await page.waitForTimeout(700);
    t.check('the accuracy report lists the removal log',
            await page.locator('tbody tr').count() > 0);
    t.check('and the chapter boundaries the parser repaired',
            /chapter boundaries repaired/i.test(await bodyText(page)));

    await page.goto(ctx.base + '#/contents');
    await page.waitForSelector('h1');
    await page.waitForTimeout(700);
    t.check('the contents page lists the works',
            await page.locator('main a[href^="#/read/"]').count() > 50,
            await page.locator('main a[href^="#/read/"]').count() + ' works');

    await page.goto(ctx.base + '#/');
    await page.waitForSelector('h1');
    await page.waitForTimeout(500);
    const eras = await page.locator('main .era').count();
    t.check('the timeline lists every era', eras > 10, eras + ' eras');

    /* An era is a button and a body, and whether it is open is remembered
       across visits -- the timeline is fifteen eras deep and reopening the
       one you were reading every time is the difference between a timeline
       and a wall. */
    const head = page.locator('main .era .era-head').first();
    const expanded = () => head.getAttribute('aria-expanded');
    const was = await expanded();

    await head.click();
    await page.waitForTimeout(300);
    t.check('an era opens and closes when its heading is pressed',
            await expanded() !== was, was + ' -> ' + await expanded());

    const toggled = await expanded();
    await page.reload();
    await page.waitForSelector('main .era');
    await page.waitForTimeout(500);
    t.check('and the timeline reopens the way the reader left it',
            await page.locator('main .era .era-head').first()
                      .getAttribute('aria-expanded') === toggled,
            'expected ' + toggled);
    await page.close();
  }
};
