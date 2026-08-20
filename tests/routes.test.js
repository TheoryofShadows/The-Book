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
  await page.close();
};
