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
  behemothLeviathan: 2,
  /* "shepherd" across everything, and across the books the Tanakh receives.
     Thirty of the ninety-nine verses between those two figures are in works
     no canon holds at all, twenty-five of them in the Shepherd of Hermas --
     which is the reason a canon is worth being able to search on its own. */
  shepherd: 175,
  shepherdJewish: 76,
  /* And in the works no canon holds at all, which is the same question asked
     from the other side. */
  shepherdLeftOut: 30,
  /* Horeb is named in Deuteronomy 5, which this volume prints twice: once in
     Deuteronomy and once on its own beside the Nash Papyrus. The second
     printing belongs to no canon's book list, and must still never be
     offered as a book left out of every canon. */
  horeb: 20
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

  /* The one place a confident answer is the wrong answer. The famous Gospel
     of Thomas is the sayings gospel from Nag Hammadi, every English of which
     is in copyright; what this volume prints is the Infancy Gospel, which the
     Ante-Nicene Fathers gives a title beginning "THE GOSPEL OF THOMAS". So
     the reference resolved to exactly one place, under a heading reading
     "That is a place in the volume", and nothing on the page said it was a
     different second-century text. */
  await page.goto(ctx.base + '#/search/' + encodeURIComponent('gospel of thomas'));
  await settled(page);
  await page.waitForTimeout(400);
  const caution = await page.evaluate(() => ({
    jumps: document.querySelectorAll('.jump-link').length,
    said: (document.querySelector('.jump-caution') || {}).textContent || ''
  }));
  t.check('a title that names a more famous book says so at the search',
          caution.jumps === 1 && /Infancy/.test(caution.said),
          caution.said || '(nothing said)');

  /* And on the work itself, where a reader who arrived by any other route
     meets it -- marked as a correction rather than as one more remark. */
  await page.goto(ctx.base +
    '#/read/the-gospel-of-thomas-infancy-first-greek-form/0');
  await page.waitForSelector('.note-block');
  const onWork = await page.evaluate(() => ({
    marked: !!document.querySelector('.note-block.is-caution'),
    text: (document.querySelector('.note-block') || {}).innerText || ''
  }));
  t.check('and on the work, with what is missing and why',
          onWork.marked && /Nag Hammadi/.test(onWork.text) &&
          /copyright/.test(onWork.text),
          onWork.text.slice(0, 60).replace(/\s+/g, ' '));

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
    picked: document.querySelector('select[aria-label="Which books to search"]').value,
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
  await page.selectOption('select[aria-label="Which books to search"]', 'job');
  await settled(page);
  await page.waitForTimeout(300);
  t.check('the chosen book is in the URL, so a narrowed search can be kept',
          await page.evaluate(() => location.hash) === '#/search/shepherd/job',
          await page.evaluate(() => location.hash));

  t.check('a book with no match says so as a fact about that book',
          /No verse in that book matched/.test(
            await page.evaluate(() => document.querySelector('.muted').textContent)),
          await page.evaluate(() => document.querySelector('.muted').textContent));

  /* ---- one canon at a time ----

     A book was the only narrowing there was, and it is the wrong size for
     the way most people read: somebody who keeps one canon is not asking
     about Job, they are asking about their Bible, and this edition prints
     five of them interleaved with books that belong to none of them. Asked
     one entry at a time that is forty-two searches for the Tanakh.

     Which works belong to which canon is read here out of canon.json rather
     than listed, because that is where the site reads it too: a check with
     its own copy of the answer would pass while the two disagreed. */
  const { canonWorks, excerpts } = await page.evaluate(async () => {
    const canon = await (await fetch('data/canon.json')).json();
    const out = {};
    canon.canons.forEach(c => { out[c] = []; });
    canon.books.forEach(b => Object.keys(b.canons).forEach(
      c => out[c] && b.works.forEach(w => out[c].push(w))));
    return { canonWorks: out, excerpts: Object.keys(canon.excerpts) };
  });
  const inSomeCanon = (w) => Object.keys(canonWorks).some(
    c => canonWorks[c].indexOf(w) >= 0);

  // The work id is the third segment of "#/read/<work>/<chapter>".
  const worksIn = () => page.evaluate(() => Array.from(
    document.querySelectorAll('.result-ref a'),
    a => a.getAttribute('href').split('/')[2]));

  await page.goto(ctx.base + '#/search/shepherd');
  await settled(page);
  const everywhere = await worksIn();
  const uncanonical = everywhere.filter(w => !inSomeCanon(w));

  t.check('the whole library answers with books no canon holds',
          everywhere.length === EXPECT.shepherd && uncanonical.length > 0,
          everywhere.length + ' hits, ' + uncanonical.length + ' outside every canon');

  await page.goto(ctx.base + '#/search/shepherd/canon:tanakh');
  await settled(page);
  const jewish = await worksIn();

  t.check('searching a canon returns that canon and nothing else',
          jewish.length === EXPECT.shepherdJewish &&
          jewish.every(w => canonWorks.tanakh.indexOf(w) >= 0),
          jewish.length + ' of ' + EXPECT.shepherdJewish + ', ' +
          jewish.filter(w => canonWorks.tanakh.indexOf(w) < 0).length + ' from outside it');

  t.check('and the canon it names, not one of the wider ones',
          await page.evaluate(() =>
            document.querySelector('select[aria-label="Which books to search"]').value) ===
          'canon:tanakh' &&
          /in the Jewish canon/.test(
            await page.evaluate(() => document.querySelector('.muted').textContent)),
          await page.evaluate(() => document.querySelector('.muted').textContent));

  /* The canons nest, in canon.json and in history: every book of the Tanakh
     is in the Protestant canon, that inside the Catholic, that inside the
     Orthodox, that inside the Ethiopian. So a wider canon can never answer
     with less than a narrower one, and for a word this common it answers
     with more at every step. */
  const scopedCount = async (scope) => {
    await page.goto(ctx.base + '#/search/shepherd/canon:' + scope);
    await settled(page);
    return page.locator('.result').count();
  };
  const protestant = await scopedCount('protestant');
  const ethiopian = await scopedCount('ethiopian');
  t.check('a wider canon answers with at least as much as a narrower one',
          jewish.length < protestant && protestant < ethiopian &&
          ethiopian < EXPECT.shepherd,
          [EXPECT.shepherdJewish, protestant, ethiopian, EXPECT.shepherd].join(' < '));

  /* Absent from your canon and absent from the volume are different facts,
     and a reader told the second when the first is true goes away believing
     the library does not have the book. Mastema is all through Jubilees,
     which the Ethiopian canon receives and the Tanakh does not. */
  await page.goto(ctx.base + '#/search/mastema/canon:tanakh');
  await settled(page);
  t.check('a canon with no match says so about the canon, not the library',
          await page.locator('.result').count() === 0 &&
          /No verse in the Jewish canon matched/.test(
            await page.evaluate(() => document.querySelector('.muted').textContent)),
          await page.evaluate(() => document.querySelector('.muted').textContent));

  // Kept in the URL, like the book, so it can be shared and come back to.
  await page.goto(ctx.base + '#/search/shepherd');
  await settled(page);
  await page.selectOption('select[aria-label="Which books to search"]', 'canon:ethiopian');
  await settled(page);
  await page.waitForTimeout(300);
  t.check('the chosen canon is in the URL, so a narrowed search can be kept',
          await page.evaluate(() => location.hash) === '#/search/shepherd/canon:ethiopian',
          await page.evaluate(() => location.hash));

  /* And every book is still every book -- the thing the narrowing is there
     to be an alternative to, not a replacement for. */
  await page.selectOption('select[aria-label="Which books to search"]', '');
  await settled(page);
  await page.waitForTimeout(300);
  t.check('and every book is still one of the choices',
          await page.locator('.result').count() === EXPECT.shepherd &&
          await page.evaluate(() => location.hash) === '#/search/shepherd',
          await page.locator('.result').count() + ' hits at ' +
          await page.evaluate(() => location.hash));

  /* ---- and the books no canon holds ----

     The same question from the other side, and the one somebody reading
     every book is usually asking: which of these did my Bible leave out?
     The answer was readable off the results a work at a time, if you already
     knew which of the titles were which -- which is precisely what a reader
     who recognises some of the books does not know. */
  await page.goto(ctx.base + '#/search/shepherd/canon:none');
  await settled(page);
  const leftOut = await worksIn();

  t.check('searching the books left out returns only books no canon holds',
          leftOut.length === EXPECT.shepherdLeftOut &&
          leftOut.every(w => !inSomeCanon(w)),
          leftOut.length + ' of ' + EXPECT.shepherdLeftOut + ', ' +
          leftOut.filter(inSomeCanon).length + ' from inside a canon');

  t.check('and says which side of the question it answered',
          /in the books left out of every canon/.test(
            await page.evaluate(() => document.querySelector('.muted').textContent)),
          await page.evaluate(() => document.querySelector('.muted').textContent));

  /* Every work the library answered with is in a canon, or is one of the
     five reprinted chapters, or is left out -- and the three do not overlap.
     A work that fell between them would be invisible to both scopes while
     still turning up under every book. */
  const strays = everywhere.filter(w => !inSomeCanon(w) &&
                                        excerpts.indexOf(w) < 0 &&
                                        leftOut.indexOf(w) < 0);
  t.check('the two scopes divide the library between them, with no remainder',
          strays.length === 0, strays.join(' ') || 'nothing unaccounted for');

  /* The trap this scope walks into if it is only subtraction. Deuteronomy 5
     is printed twice here: in Deuteronomy, and again on its own beside the
     Nash Papyrus. The second printing is in no canon's book list, because
     the canons are counted on the whole book -- so a search for the books no
     canon holds would offer the Decalogue as one of them, and tell a reader
     that the Ten Commandments are not in their Bible. */
  await page.goto(ctx.base + '#/search/horeb');
  await settled(page);
  const horeb = await worksIn();
  t.check('a chapter printed twice is in the results under every book',
          horeb.length === EXPECT.horeb &&
          horeb.indexOf('deuteronomy-5-the-decalogue') >= 0,
          horeb.length + ' hits, ' +
          (horeb.indexOf('deuteronomy-5-the-decalogue') >= 0 ? 'the Decalogue among them'
                                                             : 'and the Decalogue is not'));

  await page.goto(ctx.base + '#/search/horeb/canon:none');
  await settled(page);
  const horebLeftOut = await worksIn();
  t.check('and is never one of the books left out, because it is scripture',
          horebLeftOut.length === 0 &&
          /No verse in the books left out of every canon matched/.test(
            await page.evaluate(() => document.querySelector('.muted').textContent)),
          horebLeftOut.join(' ') ||
          await page.evaluate(() => document.querySelector('.muted').textContent));

  // Chosen from the select, kept in the URL, like every other scope.
  await page.goto(ctx.base + '#/search/shepherd');
  await settled(page);
  await page.selectOption('select[aria-label="Which books to search"]', 'canon:none');
  await settled(page);
  await page.waitForTimeout(300);
  t.check('the books left out are a choice in the list, and stay in the URL',
          await page.evaluate(() => location.hash) === '#/search/shepherd/canon:none' &&
          await page.locator('.result').count() === EXPECT.shepherdLeftOut,
          await page.locator('.result').count() + ' hits at ' +
          await page.evaluate(() => location.hash));

  await page.close();
};
