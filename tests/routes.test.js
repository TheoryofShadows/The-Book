'use strict';

/* Every route renders, and none of them raise anything. The tally watches
   for page and console errors, so an exception anywhere fails this suite
   without needing a check of its own. */

const ROUTES = [
  ['the timeline', '#/', 'Every text'],
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

     The budgets below are the *uncompressed* figures, because this suite's
     own server does not gzip -- 507 KB and 718 KB -- with about a third of
     headroom so they do not fail on noise. They do fail if a data file
     wanders onto the critical path, which is the whole point: the manifest
     alone was carrying 35 KB of duplicated chapter labels that nothing
     read, on a file fetched before anything can render.

     Search is deliberately outside this: it is a two-stage design that
     fetches every work containing a hit, which for a common word is 1.6 MB
     over sixty-one requests. That is the cost of a concordance over a
     million and a quarter words, and it is paid on a search rather than on
     arrival. */
  for (const [route, budget, requests] of [['#/', 700, 14],
                                           ['#/read/genesis/0', 950, 18]]) {
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

  await page.close();
};
