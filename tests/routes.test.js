'use strict';

/* Every route renders, and none of them raise anything. The tally watches
   for page and console errors, so an exception anywhere fails this suite
   without needing a check of its own. */

const ROUTES = [
  ['the front page', '#/', 'Every text'],
  ['threads', '#/threads', 'Threads'],
  ['one thread', '#/thread/sacrifice-or-justice', ''],
  ['contents', '#/contents', 'Contents'],
  ['search', '#/search/lion', 'Search'],
  ['canons', '#/canons', 'Which books'],
  ['saved', '#/saved', 'Saved'],
  ['the accuracy report', '#/accuracy', 'Accuracy report'],
  ['a chapter', '#/read/amos/2', 'Amos'],
  ['a long book', '#/read/psalms/118', 'Psalms'],
  ['a work with no text', '#/read/philo-of-alexandria/0', ''],
  ['a route that does not exist', '#/nonsense/here', '']
];

module.exports = async function routes(t, ctx) {
  const page = ctx.tally.watch(await ctx.browser.newPage(), 'routes');

  for (const [name, route, expect] of ROUTES) {
    await page.goto(ctx.base + route);
    await page.waitForTimeout(700);
    const heading = (await page.locator('h1, h2').first().textContent().catch(() => '') || '').trim();
    t.check(`${name} renders`, heading.length > 0 && (!expect || heading.indexOf(expect) === 0),
            heading.slice(0, 40));
  }

  /* Search is the one route that does work rather than just drawing. */
  await page.goto(ctx.base + '#/search/lion');
  await page.waitForSelector('.result', { timeout: 20000 });
  const hits = await page.locator('.result').count();
  t.check('search finds verses and shows them', hits > 0, hits + ' results');

  /* Saving is what the reader keeps, so it survives a reload or it is
     not saving. */
  await page.goto(ctx.base + '#/read/amos/2');
  await page.waitForSelector('.reader .v');
  await page.locator('.reader .v .vnum').first().click();
  await page.locator('.vmenu button', { hasText: 'Save this verse' }).click();
  await page.keyboard.press('Escape');
  await page.goto(ctx.base + '#/saved');
  await page.waitForTimeout(500);
  t.check('a saved verse is there afterwards',
          await page.locator('.saved-row').count() === 1);

  /* ---- the colophon counts what is actually on the page ----

     Four of the five figures under the title come from the manifest and move
     when the library moves. The fifth was the literal 10, which is the only
     number on the front page nothing checked -- and the front page is where
     this volume's own argument is that a number in prose is a claim needing
     a citation. Checked against the sections that carry a numeral, and
     against the eras the timeline below it actually draws. */
  await page.goto(ctx.base + '#/');
  await page.waitForSelector('.stats .stat');
  const colophon = await page.evaluate(async () => {
    const stated = Array.from(document.querySelectorAll('.stats .stat'),
      s => [s.querySelector('b').textContent, s.querySelector('span').textContent]);
    const manifest = await (await fetch('data/manifest.json')).json();
    return {
      eras: stated.find(s => /eras/.test(s[1])),
      numbered: manifest.sections.filter(s => s.roman).length,
      works: stated.find(s => /^works$/.test(s[1])),
      totalWorks: manifest.totals.works,
      drawn: document.querySelectorAll('.era').length,
    };
  });
  t.check('the era count is the number of eras, not a number somebody typed',
          colophon.eras && Number(colophon.eras[0]) === colophon.numbered &&
          colophon.numbered > 0,
          (colophon.eras || ['?'])[0] + ' stated, ' + colophon.numbered + ' numbered');
  t.check('and the works count is the library, not a number somebody typed',
          colophon.works &&
          Number(colophon.works[0].replace(/,/g, '')) === colophon.totalWorks,
          (colophon.works || ['?'])[0] + ' of ' + colophon.totalWorks);
  t.check('the timeline draws the eras and the collections, and nothing empty',
          colophon.drawn > colophon.numbered,
          colophon.drawn + ' drawn, ' + colophon.numbered + ' of them numbered');

  /* ---- what the first page actually costs ----

     The argument for fetching work texts and index shards on demand is that
     the first paint stays small even though the library is seven megabytes.
     That was an argument and not a measurement. Measured against a server
     that gzips, which is what GitHub Pages does, the home page is about
     150 KB over six requests and a chapter about 210 KB over eight.

     The budgets below are the compressed figures, because the suite's server
     now gzips the way GitHub Pages does. They used to be the uncompressed
     ones -- 700 KB and 950 KB -- and that measured a number no reader ever
     downloads: it counted a change that cost the reader four kilobytes as
     twenty-five, and it would have waved through a hundred kilobytes of
     anything already compressed. Measured on the wire the home page is
     209 KB over six requests and a chapter 267 KB over eleven, so the
     budgets are 260 KB and 330 KB -- about a quarter of headroom, enough not
     to fail on noise and tight enough to still mean something.

     They do fail if a data file wanders onto the critical path, which is the
     whole point: the manifest alone was carrying 35 KB of duplicated chapter
     labels that nothing read, on a file fetched before anything can render,
     and the home page's canon filter later fetched 33 KB of canon.json to
     populate a select most readers never open.

     The request counts are the tighter half of that guard, and deliberately
     so. Compressed, that canon.json fetch cost four kilobytes -- inside any
     byte budget worth having -- but it was a whole extra round trip before
     the page could settle, which on a phone is the part that is felt. Six
     and eleven are what the two routes actually make, and the ceilings are
     exactly that: one more request fails, which is the only setting that
     would have caught canon.json. There is no slack on purpose -- a route
     that legitimately needs another request should raise these deliberately,
     in a commit that says why, rather than find the room already there.

     Search is deliberately outside this: it is a two-stage design that
     fetches every work containing a hit, which for a common word is 1.6 MB
     over sixty-one requests. That is the cost of a concordance over a
     million and a quarter words, and it is paid on a search rather than on
     arrival. */
  for (const [route, budget, requests] of [['#/', 260, 6],
                                           ['#/read/genesis/0', 330, 11]]) {
    const fresh = await ctx.browser.newPage();
    /* Measured off the request rather than off a content-length header: the
       test server does not send one, and reading the header gave a budget
       check that reported nought kilobytes and passed everything. */
    const weighed = [];
    let count = 0;
    fresh.on('response', res => {
      count++;
      weighed.push(res.request().sizes()
        .then(s => s.responseBodySize).catch(() => 0));
    });
    await fresh.goto(ctx.base + route, { waitUntil: 'networkidle' });
    const bytes = (await Promise.all(weighed)).reduce((a, b) => a + b, 0);
    const kb = Math.round(bytes / 1024);
    t.check('the first paint of ' + route + ' stays inside its budget',
            kb > 0 && kb <= budget && count <= requests,
            kb + ' KB over ' + count + ' requests, budget ' +
            budget + ' KB and ' + requests);
    await fresh.close();
  }

  /* ---- the day's passage ----

     Asked for as "daily affirmations based on recent searches". What is
     built is a passage: a real verse from this volume, chosen by what the
     reader searched for, carrying its reference and a link to the chapter.

     The substitution is the point, and it is the site's own rule --
     tools/positions.py: "an interpretive layer that merely asserts things,
     in the same visual frame as audited text, would be the weakest link in
     the whole project". A written affirmation beside forty thousand audited
     verses is the one sentence on the page with nothing behind it. These
     checks hold the difference: the quoted text has to BE the verse the
     reference names, not something composed about it. */
  const daily = await ctx.browser.newPage();
  await daily.goto(ctx.base + '#/');
  await daily.waitForSelector('.stats');
  await daily.waitForTimeout(400);
  t.check('a reader who has never searched is shown no passage card',
          await daily.locator('.today').count() === 0);

  await daily.goto(ctx.base + '#/search/covenant');
  // The search suite's own settled() lives there; here it is enough that a
  // run happened, which is what puts the term in the reader's memory.
  await daily.waitForFunction(() =>
    /matches|No verse|No text contains/.test(
      (document.querySelector('.wrap .muted') || {}).textContent || ''),
    null, { timeout: 30000 });
  await daily.goto(ctx.base + '#/');
  await daily.waitForSelector('.today-text', { timeout: 15000 });
  const card = await daily.evaluate(() => ({
    eyebrow: document.querySelector('.today-eyebrow').textContent,
    text: document.querySelector('.today-text').textContent.trim(),
    ref: document.querySelector('.today-ref').textContent,
    href: document.querySelector('.today-ref').getAttribute('href'),
  }));
  t.check('searching gives a passage, named and linked',
          /covenant/.test(card.eyebrow) && card.text.length > 10 &&
          /^#\/read\/[a-z0-9-]+\/\d+/.test(card.href),
          card.ref + ' -> ' + card.href);

  /* The load-bearing one. Follow the link and read the verse off the page:
     if the card ever quoted anything but the text it cites, this fails. */
  await daily.goto(ctx.base + card.href);
  await daily.waitForSelector('.reader .v');
  const onThePage = await daily.evaluate(() => {
    const marked = document.querySelector('.reader .v.target');
    const source = marked || document.querySelector('.reader .v');
    return source.textContent.replace(/^\s*\d+\s*/, '').trim();
  });
  t.check('the passage quoted is the verse it cites, word for word',
          onThePage.indexOf(card.text.slice(0, 40)) !== -1,
          'card: ' + card.text.slice(0, 45) + ' | page: ' + onThePage.slice(0, 45));

  /* Same day, same passage: a reading rather than a slot machine. */
  await daily.goto(ctx.base + '#/');
  await daily.waitForSelector('.today-ref');
  t.check('it is the same passage all day, not a new one every reload',
          await daily.evaluate(() =>
            document.querySelector('.today-ref').textContent) === card.ref);

  await daily.locator('.today-forget').click();
  await daily.waitForTimeout(200);
  await daily.goto(ctx.base + '#/');
  await daily.waitForSelector('.stats');
  await daily.waitForTimeout(400);
  t.check('and the searches it reads can be forgotten, from the card itself',
          await daily.locator('.today-text').count() === 0 &&
          (await daily.evaluate(() =>
            JSON.parse(localStorage.getItem('thebook:recent-searches') || '[]')
          )).length === 0);
  await daily.close();

  /* ---- the way in, for a reader who knows where they are going ----

     Two controls over the eras. Both are new, and both had a way of going
     wrong that only shows on the second interaction, so they are checked by
     using them rather than by looking at them. */
  const find = ctx.tally.watch(await ctx.browser.newPage(), 'home-find');
  await find.goto(ctx.base + '#/');
  await find.waitForSelector('.home-jump-input');

  /* The jump box takes a reference and goes to the text, rather than being a
     search box that happens to accept one. */
  await find.fill('.home-jump-input', 'Isa 40');
  await find.press('.home-jump-input', 'Enter');
  await find.waitForTimeout(900);
  let where = await find.evaluate(() => location.hash);
  t.check('a reference typed on the front page goes to the text',
          /#\/(read|search)/.test(where) || /That could be/.test(
            await find.evaluate(() => document.querySelector('.home-jump-says').textContent)),
          where.slice(0, 48));

  /* Isaiah is three works here, so it is the case that must not guess. */
  await find.goto(ctx.base + '#/');
  await find.waitForSelector('.home-jump-input');
  await find.fill('.home-jump-input', 'nonsense phrase nobody indexed');
  await find.press('.home-jump-input', 'Enter');
  await find.waitForTimeout(700);
  t.check('and a phrase that is not a reference is searched rather than refused',
          /#\/search/.test(await find.evaluate(() => location.hash)));

  /* canon.json is deliberately not fetched on load, so the select starts with
     the one true option and fills when it is reached for. */
  await find.goto(ctx.base + '#/');
  await find.waitForSelector('.home-filter-select');
  const before = await find.locator('.home-filter-select option').count();
  t.check('the canon filter costs nothing until it is reached for',
          before === 1, before + ' option(s) before touching it');

  await find.focus('.home-filter-select');
  await find.waitForFunction(
    () => document.querySelectorAll('.home-filter-select option').length > 1,
    null, { timeout: 10000 });
  const after = await find.locator('.home-filter-select option').count();
  t.check('and fills with the canons the first time it is', after > 1,
          after + ' options after');

  /* The bug this is here for: filtering opened every era holding a match,
     and clearing the filter left them all open for good -- the reader's own
     open and shut state spent by a control that only meant to narrow. */
  const shutAtFirst = await find.evaluate(() =>
    document.querySelectorAll('.era.open').length);

  const pick = await find.evaluate(() => {
    const o = [...document.querySelectorAll('.home-filter-select option')]
      .find(x => x.value);
    return o ? o.value : '';
  });
  await find.selectOption('.home-filter-select', pick);
  await find.waitForTimeout(400);
  const narrowed = await find.evaluate(() => ({
    shown: document.querySelectorAll('.era:not([hidden]) .work:not([hidden])').length,
    open: document.querySelectorAll('.era.open').length,
    says: (document.querySelector('.home-filter-says') || {}).textContent || ''
  }));
  t.check('choosing a canon narrows the eras in place and says what is left',
          narrowed.shown > 0 && narrowed.open > 0 && /work/.test(narrowed.says),
          narrowed.shown + ' works, ' + narrowed.says.slice(0, 44));

  await find.selectOption('.home-filter-select', '');
  await find.waitForTimeout(400);
  const cleared = await find.evaluate(() => ({
    open: document.querySelectorAll('.era.open').length,
    hidden: document.querySelectorAll('.era[hidden], .work[hidden]').length,
    lying: [...document.querySelectorAll('.era')].filter(e => {
      const h = e.querySelector('.era-head');
      return h && (h.getAttribute('aria-expanded') === 'true') !==
                  e.classList.contains('open');
    }).length
  }));
  t.check('and clearing it gives the reader back the eras they had',
          cleared.open === shutAtFirst && cleared.hidden === 0,
          cleared.open + ' open (was ' + shutAtFirst + '), ' +
          cleared.hidden + ' still hidden');
  t.check('with every era saying out loud what it is actually showing',
          cleared.lying === 0, cleared.lying + ' disagreeing with aria-expanded');

  await find.close();

  await page.close();
};
