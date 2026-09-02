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
  /* 59 until the Ethiopic Didascalia was added, which quotes "Give unto
     Caesar the things that are Caesar's" and makes 60. A count like this
     moving is the corpus changing, and the right response is to find the
     verse that changed it before touching the number. */
  caesar: 60,
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
    // "No verse matched." and "No verse matched in that book." are both
    // ends of a run; matching the shared opening keeps this helper from
    // having to be edited every time the sentence gains a clause.
    return /matches|No verse|No text contains|No chapter contains/
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

  /* ---- a long verse is cut down without being cut through ----

     The snippet is windowed on the verse and marked up afterwards, rather
     than marked up and then sliced: "&amp;" is five characters of HTML and
     "<mark>" is six, and a cut taken on the HTML goes through the middle of
     either. Nothing in the library is quite long enough to make that happen
     today, so this holds the invariant rather than reproducing a break --
     every snippet closes every mark it opens, ends on a whole entity, and
     still carries the highlight it was shown for. Greek Esther 8 carries a
     four-thousand-character verse, which is where it would show first. */
  await page.goto(ctx.base + '#/search/' + encodeURIComponent('Hammedatha'));
  await settled(page);
  const snippets = await page.evaluate(() => Array.from(
    document.querySelectorAll('.result-text'),
    e => ({ html: e.innerHTML, text: e.textContent })));

  const balanced = snippets.every(s =>
    (s.html.match(/<mark>/g) || []).length ===
    (s.html.match(/<\/mark>/g) || []).length);
  const marked = snippets.every(s => s.html.indexOf('<mark>') !== -1);
  const whole = snippets.every(s => !/&[a-z]{1,6}$|<[a-z]*$/i.test(s.html));

  t.check('a long result is windowed on the verse, not on its markup',
          snippets.length > 0 && balanced && marked && whole,
          snippets.length + ' snippet(s), longest ' +
          Math.max.apply(null, snippets.map(s => s.text.length)) + ' chars');

  /* ---- a reference is a coordinate, not a word ----

     "Psalm 23" returned nothing at all, "Job 38" returned nothing, and a
     bare "Job" put Joshua first -- Jobab king of Madon, because the term
     test is a prefix. A reader who does not already know where a passage
     sits could not reach it by searching, which in an edition ordered by
     composition is the reader least able to find it any other way. */
  const jumpsFor = async (q) => {
    await page.goto(ctx.base + '#/search/' + encodeURIComponent(q));
    await settled(page);
    await page.waitForTimeout(400);
    return page.evaluate(() => Array.from(
      document.querySelectorAll('.jump-link'),
      a => a.getAttribute('href')));
  };

  t.check('a chapter reference goes to the chapter',
          (await jumpsFor('Psalm 23')).join() === '#/read/psalms/22',
          (await jumpsFor('Psalm 23')).join() || '(nothing offered)');

  t.check('and a verse reference to the verse',
          (await jumpsFor('Job 38:4')).join() === '#/read/job/37/v4',
          (await jumpsFor('Job 38:4')).join() || '(nothing offered)');

  /* The one this edition makes hard, and the one it most needs. Isaiah is
     three works here because it was written across three periods, and the
     chapter numbers carry on across them: Isaiah 40 is the first chapter of
     the second work, not the fortieth of the first. Resolved off the
     chapter's printed label rather than its index, so the splits -- Isaiah's
     three and 1 Enoch's four -- need no special case. */
  t.check('a chapter in a split work lands in the right part of it',
          (await jumpsFor('Isaiah 40')).join() === '#/read/isaiah-40-55-second-isaiah/0',
          (await jumpsFor('Isaiah 40')).join() || '(nothing offered)');

  t.check('an abbreviation and a numbered book both resolve',
          (await jumpsFor('1 Cor 13')).join() === '#/read/1-corinthians/12' &&
          (await jumpsFor('Mt 5'))[0] === '#/read/matthew/4',
          (await jumpsFor('1 Cor 13')).join() + ' / ' + (await jumpsFor('Mt 5'))[0]);

  /* Two real answers stay two answers. The volume has both a book of Psalms
     and a Psalm 151, so "Psalm 1" is genuinely ambiguous and guessing would
     be worse than offering. */
  t.check('a genuinely ambiguous reference offers both',
          (await jumpsFor('Psalm 1')).join() === '#/read/psalms/0,#/read/psalm-151/0',
          (await jumpsFor('Psalm 1')).join());

  t.check('a book that does not exist is not invented',
          (await jumpsFor('Nonesuch 3')).length === 0 &&
          (await jumpsFor('Psalm 999')).length === 0);

  /* The word search still runs underneath: "Job" is a book and also a man
     named in books that are not his, and only the reader knows which. */
  await page.goto(ctx.base + '#/search/' + encodeURIComponent('Job'));
  await settled(page);
  await page.waitForTimeout(400);
  t.check('a bare book name offers the book and still searches the word',
          await page.locator('.jump-link').count() === 1 &&
          await page.locator('.result').count() > 1,
          await page.locator('.result').count() + ' verses as well');

  /* ---- one book at a time ---- */
  await page.goto(ctx.base + '#/search/shepherd/psalms');
  await settled(page);
  const scoped = await page.evaluate(() => ({
    picked: document.querySelector('select[aria-label="Which book to search"]').value,
    refs: Array.from(document.querySelectorAll('.result-ref'), e => e.textContent)
  }));
  t.check('searching one book returns that book and nothing else',
          scoped.picked === 'psalms' && scoped.refs.length > 0 &&
          scoped.refs.every(r => /^Psalms/.test(r.trim())),
          scoped.refs.length + ' results, first ' + (scoped.refs[0] || '').trim());

  t.check('and the same search across everything returns more',
          await (async () => {
            await page.goto(ctx.base + '#/search/shepherd');
            await settled(page);
            return await page.locator('.result').count() > scoped.refs.length;
          })());

  // Choosing a book keeps the search shareable rather than losing it.
  await page.goto(ctx.base + '#/search/shepherd');
  await settled(page);
  await page.selectOption('select[aria-label="Which book to search"]', 'job');
  await settled(page);
  await page.waitForTimeout(300);
  t.check('the chosen book is in the URL, so a narrowed search can be kept',
          await page.evaluate(() => location.hash) === '#/search/shepherd/job',
          await page.evaluate(() => location.hash));

  t.check('a book with no match says so as a fact about that book',
          /No verse in that book matched/.test(
            await page.evaluate(() => document.querySelector('.muted').textContent)),
          await page.evaluate(() => document.querySelector('.muted').textContent));

  await page.close();
};
