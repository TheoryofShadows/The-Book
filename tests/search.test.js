'use strict';

/* Search, against known answers.
 *
 * The one check this replaces asked whether searching for "lion" produced
 * more than zero rows. That passes whether the search is right or wrong; it
 * would have passed while accented words were unfindable, which they were.
 *
 * Every count below was computed from docs/data by tools, applying the same
 * fold the site applies, and is re-derivable:
 *
 *     python3 -m unittest discover -s tests/python -t tests/python
 *
 * They will move when the text does. That is the point -- a search whose
 * result count changed without the text changing is a search that broke.
 */

const EXPECT = {
  stillSmallVoice: 1,     // 1 Kings 19:12, and nowhere else in the volume
  livingCreatures: 27,
  caesar: 59,
  mastema: 11,
  behemothLeviathan: 2
};

/* Search does work rather than just drawing, so every assertion waits for it
   to have finished rather than for a fixed number of milliseconds. The status
   line is the site's own signal that a run is over. */
function settled(page) {
  return page.waitForFunction(() => {
    const s = document.querySelector('.results');
    const status = document.querySelector('.wrap .muted');
    if (!s || !status) return false;
    return /matches|No verse matched|No text contains|No chapter contains/
      .test(status.textContent);
  }, null, { timeout: 30000 });
}

async function run(page, base, query) {
  await page.goto(base + '#/search/' + encodeURIComponent(query));
  await settled(page);
  return {
    hits: await page.locator('.result').count(),
    status: (await page.textContent('.wrap .muted')) || ''
  };
}

module.exports = async function search(t, ctx) {
  const page = ctx.tally.watch(await ctx.browser.newPage(), 'search');

  /* ---- phrases ---- */

  let r = await run(page, ctx.base, '"a still small voice"');
  t.check('a quoted phrase finds exactly its occurrences',
          r.hits === EXPECT.stillSmallVoice, r.hits + ' of ' + EXPECT.stillSmallVoice);

  const ref = (await page.locator('.result .result-ref').first().textContent() || '');
  t.check('and names the passage it is in', /kings/i.test(ref), ref.trim().slice(0, 40));

  t.check('the phrase itself is marked in the result',
          (await page.locator('.result mark').first().textContent() || '')
            .toLowerCase().indexOf('still') >= 0);

  r = await run(page, ctx.base, '"living creatures"');
  t.check('a phrase in many books finds all of them',
          r.hits === EXPECT.livingCreatures, r.hits + ' of ' + EXPECT.livingCreatures);

  /* A phrase is not the same query as its words: the words match verses
     where they are scattered, the phrase only where they are adjacent. */
  const loose = await run(page, ctx.base, 'living creatures');
  t.check('the same words unquoted match more widely than the phrase',
          loose.hits > r.hits, loose.hits + ' unquoted vs ' + r.hits + ' quoted');

  /* ---- the fold ----
     Accented and ligatured spellings were unreachable: the index filed
     "Cæsar" under "c" and "sar" and no query could ask for it. */

  r = await run(page, ctx.base, 'caesar');
  t.check('an ASCII spelling finds the ligatured one on the page',
          r.hits === EXPECT.caesar, r.hits + ' of ' + EXPECT.caesar);

  r = await run(page, ctx.base, 'mastema');
  t.check('and an unaccented spelling finds the accented one',
          r.hits === EXPECT.mastema, r.hits + ' of ' + EXPECT.mastema);

  const accented = await run(page, ctx.base, 'Mastêmâ');
  t.check('typing the accents gives the same answer as leaving them out',
          accented.hits === EXPECT.mastema, accented.hits + ' hits');

  /* ---- several terms ---- */

  r = await run(page, ctx.base, 'behemoth leviathan');
  t.check('two words mean both, not either',
          r.hits === EXPECT.behemothLeviathan,
          r.hits + ' of ' + EXPECT.behemothLeviathan);

  /* ---- the ways a search ends with nothing ----
     Three different messages, because they mean three different things, and
     a reader who is told the wrong one goes looking in the wrong place. */

  r = await run(page, ctx.base, 'zzzznotaword');
  t.check('a word in no text says so, and names the word',
          r.hits === 0 && /no text contains/i.test(r.status) &&
          r.status.indexOf('zzzznotaword') >= 0, r.status.slice(0, 60));

  r = await run(page, ctx.base, 'behemoth zzzznotaword');
  t.check('one unknown word in a pair is reported rather than ignored',
          r.hits === 0 && /no text contains/i.test(r.status), r.status.slice(0, 60));

  r = await run(page, ctx.base, 'behemoth jubilee tabernacle synagogue');
  t.check('real words that never share a chapter say that instead',
          r.hits === 0 && /no chapter contains|no verse matched/i.test(r.status),
          r.status.slice(0, 60));

  r = await run(page, ctx.base, '"zzzz not a phrase anywhere"');
  t.check('a phrase whose words exist but never adjoin says nothing matched',
          r.hits === 0, r.status.slice(0, 60));

  /* ---- the index shards ----
     Tokens that do not start with a letter go in the "0" shard, and the
     client has to ask for that shard rather than one named after a digit. */

  r = await run(page, ctx.base, '1000');
  t.check('a number is searchable and lands in the digit shard',
          r.hits === 1, r.hits + ' results');

  /* ---- a term is a prefix, at both stages ----
     The index files whole words. Narrowing by the exact token and then
     prefix-matching inside the result returned only the verses that happened
     to sit beside the exact spelling. */

  r = await run(page, ctx.base, 'caesarea');
  t.check('a longer word is not confused with the shorter one it contains',
          r.hits > 0 && r.hits < EXPECT.caesar, r.hits + ' results');

  /* ---- a stale run must not overwrite a newer one ----
     Each keystroke starts a search; they finish out of order, and the guard
     that stops an old one painting over a new one has never been exercised. */

  await page.goto(ctx.base + '#/search/');
  await page.waitForSelector('input[type=search]');
  await page.fill('input[type=search]', 'behemoth');
  await page.waitForTimeout(80);
  await page.fill('input[type=search]', '"living creatures"');
  await settled(page);
  await page.waitForTimeout(600);
  const after = await page.locator('.result').count();
  t.check('a slower earlier search does not overwrite the latest one',
          after === EXPECT.livingCreatures, after + ' of ' + EXPECT.livingCreatures);

  /* ---- an empty query does nothing rather than everything ---- */
  await page.goto(ctx.base + '#/search/');
  await page.waitForSelector('input[type=search]');
  await page.waitForTimeout(500);
  t.check('an empty search does not list the whole library',
          await page.locator('.result').count() === 0);

  /* ---- the suggested searches are real searches ---- */
  await page.goto(ctx.base + '#/search');
  await page.waitForSelector('.chip');
  const chips = await page.locator('.chips .chip').count();
  await page.locator('.chips .chip').first().click();
  await settled(page);
  t.check('the offered searches lead somewhere',
          chips > 0 && await page.locator('.result').count() > 0,
          chips + ' offered');

  await page.close();
};
