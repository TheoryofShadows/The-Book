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
  /* And the verses outside one reader's own canon rather than outside all
     five: 175 less the 99 the Protestant canon holds. Sirach, Judith,
     Jubilees and Enoch are in it and not in the thirty above, which is the
     difference the setting exists to make. */
  shepherdOutsideProtestant: 76,
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
  /* References only. A search now answers several different questions at
     once -- a reference, a collection, a dictionary entry -- and each is in
     its own box, so "the jump links on the page" stopped being a question
     about the reference resolver the moment "Job" also matched a headword. */
  const jumpsFor = async (q) => {
    await page.goto(ctx.base + '#/search/' + encodeURIComponent(q));
    await settled(page);
    await page.waitForTimeout(400);
    return page.evaluate(() => Array.from(
      document.querySelectorAll('.jump-box.is-reference .jump-link'),
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
    jumps: document.querySelectorAll('.jump-box.is-reference .jump-link').length,
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
          await page.locator('.jump-box.is-reference .jump-link').count() === 1 &&
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

  /* ---- and the same fact on the row, under every book ----

     Narrowing is one answer to "which of these is in my Bible" and it is not
     the answer for somebody who wants to read the whole library and know
     what they are reading. On that page the question was answered by
     recognising the title, which works for Psalms and not for Barnabas --
     so it worked least well for the reader who most needed it. */
  const rows = () => page.evaluate(() => Array.from(
    document.querySelectorAll('.result'), r => ({
      work: r.querySelector('.result-ref a').getAttribute('href').split('/')[2],
      marked: !!r.querySelector('.result-outside'),
      said: (r.querySelector('.result-outside') || {}).textContent || ''
    })));

  await page.goto(ctx.base + '#/search/shepherd');
  await settled(page);
  const everyBook = await rows();

  t.check('every book marks the verses no canon holds, and only those',
          everyBook.filter(r => r.marked).length === EXPECT.shepherdLeftOut &&
          everyBook.every(r => r.marked === !inSomeCanon(r.work)),
          everyBook.filter(r => r.marked).length + ' marked of ' +
          EXPECT.shepherdLeftOut + ', ' +
          everyBook.filter(r => r.marked && inSomeCanon(r.work)).length + ' wrongly');

  t.check('and says what the mark means rather than drawing a symbol',
          /outside every canon/.test((everyBook.find(r => r.marked) || {}).said || ''),
          (everyBook.find(r => r.marked) || {}).said || '(nothing said)');

  /* The same trap as the scope, on the row this time: a chapter of
     Deuteronomy printed twice is scripture in both places, and a mark on the
     second printing would tell a reader the Decalogue is in no Bible. */
  await page.goto(ctx.base + '#/search/horeb');
  await settled(page);
  const horebRows = await rows();
  t.check('a chapter printed twice is never marked as outside every canon',
          horebRows.length === EXPECT.horeb &&
          horebRows.every(r => !r.marked),
          horebRows.filter(r => r.marked).map(r => r.work).join(' ') ||
          horebRows.length + ' rows, none marked');

  /* Under a scope the marking would be a fact the page has already stated,
     on every row or on none of them. */
  for (const [scope, what] of [['canon:tanakh', 'a canon'],
                               ['canon:none', 'the books left out'],
                               ['psalms', 'one book']]) {
    await page.goto(ctx.base + '#/search/shepherd/' + scope);
    await settled(page);
    const scopedRows = await rows();
    t.check('no verse is marked when the scope has already said it: ' + what,
            scopedRows.length > 0 && scopedRows.every(r => !r.marked),
            scopedRows.length + ' rows, ' +
            scopedRows.filter(r => r.marked).length + ' marked');
  }

  /* ---- measured against the reader's own canon ----

     "Outside every canon" is the only thing the page can say to a reader it
     knows nothing about, and it is not the question most people are asking.
     Somebody who keeps the Protestant canon is not helped by 1 Enoch going
     unmarked because the Ethiopian church receives it: for them that is
     precisely a book their Bible does not have. So they can say which canon
     is theirs, and the mark is measured against that instead. */
  const mine = 'select[aria-label="Mark verses not in this canon"]';

  await page.goto(ctx.base + '#/search/shepherd');
  await settled(page);
  t.check('the page asks whose canon to measure by, and assumes none',
          await page.locator(mine).count() === 1 &&
          await page.inputValue(mine) === '' &&
          /Mark verses not in/.test(await page.textContent('.marking')),
          (await page.textContent('.marking') || '').slice(0, 30));

  await page.selectOption(mine, 'protestant');
  await settled(page);
  await page.waitForTimeout(300);
  const byProtestant = await rows();
  const inProtestant = (w) => canonWorks.protestant.indexOf(w) >= 0;

  t.check('choosing a canon marks what that canon does not hold',
          byProtestant.filter(r => r.marked).length === EXPECT.shepherdOutsideProtestant &&
          byProtestant.every(r => r.marked ===
            (!inProtestant(r.work) && excerpts.indexOf(r.work) < 0)),
          byProtestant.filter(r => r.marked).length + ' of ' +
          EXPECT.shepherdOutsideProtestant);

  t.check('and the mark names the canon it was measured against',
          /outside the Protestant canon/.test(
            (byProtestant.find(r => r.marked) || {}).said || ''),
          (byProtestant.find(r => r.marked) || {}).said || '(nothing said)');

  /* The books the five canons disagree about are the point of the setting:
     under "every canon" Sirach and Enoch go unmarked, because somebody
     receives them. Under a Protestant reader's canon they do not. */
  t.check('a book another tradition receives is outside this reader\'s canon',
          ['sirach-ecclesiasticus', 'jubilees', 'judith'].every(w =>
            byProtestant.some(r => r.work === w && r.marked)),
          ['sirach-ecclesiasticus', 'jubilees', 'judith']
            .filter(w => byProtestant.some(r => r.work === w && r.marked)).join(' '));

  /* A question about your own Bible has the same answer tomorrow. */
  await page.goto(ctx.base + '#/search/horeb');
  await settled(page);
  const horebMine = await rows();
  t.check('the answer is remembered, and applies to the next search',
          await page.inputValue(mine) === 'protestant' &&
          horebMine.some(r => r.marked),
          await page.inputValue(mine) + ', ' +
          horebMine.filter(r => r.marked).length + ' marked');

  t.check('and the chapter printed twice is still never marked',
          horebMine.every(r => r.work !== 'deuteronomy-5-the-decalogue' || !r.marked),
          horebMine.filter(r => r.marked).map(r => r.work).join(' '));

  /* Inside the reader's own canon there is nothing to mark; inside a wider
     one there is, and that is the case the scope cannot answer on its own. */
  await page.goto(ctx.base + '#/search/shepherd/canon:protestant');
  await settled(page);
  const insideMine = await rows();
  await page.goto(ctx.base + '#/search/shepherd/canon:ethiopian');
  await settled(page);
  const widerThanMine = await rows();

  t.check('a scope inside the reader\'s canon marks nothing',
          insideMine.length > 0 && insideMine.every(r => !r.marked),
          insideMine.filter(r => r.marked).length + ' marked of ' + insideMine.length);

  t.check('and a canon wider than theirs marks what it adds',
          widerThanMine.some(r => r.marked) &&
          widerThanMine.every(r => r.marked ===
            (!inProtestant(r.work) && excerpts.indexOf(r.work) < 0)),
          widerThanMine.filter(r => r.marked).length + ' marked of ' +
          widerThanMine.length);

  // And back to no canon of one's own, which is where every reader starts.
  await page.goto(ctx.base + '#/search/shepherd');
  await settled(page);
  await page.selectOption(mine, '');
  await settled(page);
  await page.waitForTimeout(300);
  const backToAny = await rows();
  t.check('and it can be given back, leaving the honest default',
          backToAny.filter(r => r.marked).length === EXPECT.shepherdLeftOut &&
          /outside every canon/.test((backToAny.find(r => r.marked) || {}).said || ''),
          backToAny.filter(r => r.marked).length + ' marked, ' +
          ((backToAny.find(r => r.marked) || {}).said || '(nothing said)'));

  /* ---------------- what a search is asked, besides words ----------------

     "New testament" used to answer with two verses -- a line in the
     Apostolic Canons listing which books are received, and one in the
     Testament of Our Lord -- and nothing else at all. Both contain the
     words; neither is what anybody typing them wants, and there was no way
     from that search into the twenty-seven books. Every check below is a
     query a reader plainly means as a question about the volume's own
     arrangement rather than about its wording. */

  async function answers(query) {
    await page.goto(ctx.base + '#/search/' + encodeURIComponent(query));
    // The answer boxes come from files that land independently of the word
    // search, so waiting on the status line is not enough for these.
    await settled(page);
    await page.waitForTimeout(600);
    return page.$$eval('.jump-box', boxes => boxes.map(b => ({
      head: b.querySelector('.jump-head').textContent,
      rows: [...b.querySelectorAll('.jump-where')].map(e => e.textContent),
      hrefs: [...b.querySelectorAll('a.jump-link')].map(a => a.getAttribute('href'))
    })));
  }
  const rowsOf = a => a.reduce((all, b) => all.concat(b.rows), []);
  const hrefsOf = a => a.reduce((all, b) => all.concat(b.hrefs), []);

  let a = await answers('new testament');
  t.check('"new testament" offers the New Testament',
          rowsOf(a).indexOf('The New Testament') >= 0,
          rowsOf(a).join(' | ') || '(nothing offered)');

  t.check('and this edition\'s section of the same name beside it, ' +
          'because they are not the same set',
          rowsOf(a).indexOf('New Testament Writings') >= 0,
          rowsOf(a).join(' | '));

  t.check('and links somewhere that exists',
          hrefsOf(a).indexOf('#/collection/new-testament') >= 0,
          hrefsOf(a).join(' '));

  /* The word matches are still there. An answer that replaced them would
     have taken something away to add something. */
  t.check('without taking the word matches away',
          await page.locator('.result').count() > 0,
          await page.locator('.result').count() + ' verses');

  for (const [query, want] of [
    ['old testament', 'The Old Testament'],
    ['torah', 'Torah'],
    ['pentateuch', 'Torah'],
    ['the gospels', 'Gospels'],
    ['minor prophets', 'The Twelve'],
    ['deuterocanon', 'Deuterocanon'],
    ['letters of paul', 'Pauline Epistles'],
    ['apostolic fathers', 'The Apostolic Fathers'],
    ['shepherd of hermas', 'The Shepherd of Hermas']
  ]) {
    const got = rowsOf(await answers(query));
    t.check('"' + query + '" reaches ' + want,
            got.indexOf(want) >= 0, got.join(' | ') || '(nothing offered)');
  }

  /* Things the text cannot be asked for, because the text never says them. */
  a = await answers('sermon on the mount');
  t.check('a passage known by a name the text never uses is still findable',
          rowsOf(a).indexOf('The Sermon on the Mount') >= 0,
          rowsOf(a).join(' | '));
  t.check('and it lands in Matthew rather than on a guess',
          hrefsOf(a).some(h => /#\/read\/matthew\//.test(h)),
          hrefsOf(a).join(' '));

  a = await answers('dead sea scrolls');
  t.check('a manuscript nobody calls by its catalogue number is findable',
          rowsOf(a).some(r => /Isaiah Scroll/.test(r)),
          rowsOf(a).join(' | '));

  a = await answers('where do the dead go');
  t.check('a thread\'s own title reaches the thread',
          hrefsOf(a).some(h => /#\/thread\//.test(h)),
          rowsOf(a).join(' | '));

  a = await answers('abaddon');
  t.check('a dictionary headword offers its entry',
          rowsOf(a).indexOf('Abaddon') >= 0, rowsOf(a).join(' | '));

  a = await answers('timeline');
  t.check('a page of this site is reachable from the search box',
          hrefsOf(a).indexOf('#/timeline') >= 0, hrefsOf(a).join(' '));

  /* A word search must not sprout answers it has no business offering. */
  a = await answers('zzzznotaword');
  t.check('a query that means nothing offers nothing',
          a.length === 0, a.length + ' boxes');

  /* ---------------- a collection as a place, and as a scope ---------------- */

  await page.goto(ctx.base + '#/collection/gospels');
  await page.waitForSelector('tbody tr');
  const gospels = await page.$$eval('tbody tr td:first-child a',
                                    as => as.map(a => a.textContent));
  t.check('a collection page lists exactly its works',
          gospels.length === 4 && gospels.indexOf('Matthew') >= 0,
          gospels.join(', '));

  t.check('in the order this edition argues for, not the bound order',
          gospels[0] === 'Mark', gospels.join(', '));

  /* And says why that order, rather than leaving it to be taken on trust.
     All four Gospels sit in one era, so the era's range is the same sentence
     four times; each one's own dated position is what puts Mark above
     Matthew, and it is the only thing on the page that can. */
  const when = await page.$$eval('tbody tr td:nth-child(2)',
                                 tds => tds.map(td => td.textContent.trim()));
  t.check('and dates each work by its own position, not by its era',
          when[0] !== when[1] && /65/.test(when[0]) && /80/.test(when[1]),
          when.join(' | '));

  t.check('with none of them falling back to the era',
          await page.locator('td.is-era').count() === 0 &&
          /All 4 are dated by the work/.test(await page.textContent('.dating-note')),
          await page.textContent('.dating-note'));

  /* Hermas is the other end of it: twenty-seven parts, not one of which has
     a dated position of its own. A page that printed the era in the same
     ink as a cited date would be claiming twenty-seven dates it does not
     have -- so they are marked, and counted, and the sentence is not the
     one with a remainder in it. */
  await page.goto(ctx.base + '#/collection/the-shepherd-of-hermas');
  await page.waitForSelector('.dating-note');
  t.check('a collection with no dated positions marks every row as its era',
          await page.locator('td.is-era').count() ===
          await page.locator('tbody tr').count(),
          await page.locator('td.is-era').count() + ' of ' +
          await page.locator('tbody tr').count());

  t.check('and says so without opening on a nought or a missing remainder',
          /^None of these 27/.test(await page.textContent('.dating-note')) &&
          !/The rest/.test(await page.textContent('.dating-note')),
          await page.textContent('.dating-note'));

  /* The Twelve are twelve books and thirteen works here, because Zechariah
     is split. A count that contradicts the name has to explain itself. */
  await page.goto(ctx.base + '#/collection/the-twelve');
  await page.waitForSelector('tbody tr');
  t.check('and says so where its count contradicts its name',
          /12 books, printed here as 13/
            .test(await page.textContent('.lede') || ''),
          (await page.textContent('.lede') || '').slice(0, 60));

  await page.goto(ctx.base + '#/collection/not-a-collection');
  await page.waitForSelector('h1');
  t.check('a collection that does not exist says so rather than emptying',
          /No such collection/.test(await page.textContent('h1')),
          await page.textContent('h1'));

  await page.goto(ctx.base + '#/search/shepherd/in:gospels');
  await settled(page);
  const inGospels = await rows();
  t.check('a collection narrows a search the way a canon does',
          inGospels.length > 0 &&
          inGospels.every(r => ['matthew', 'mark', 'luke', 'john']
                                 .indexOf(r.work) >= 0),
          inGospels.length + ' hits in ' +
          [...new Set(inGospels.map(r => r.work))].join(' '));

  t.check('and the search says which collection it searched',
          /in Gospels/.test(await page.textContent('.wrap .muted') || ''),
          await page.textContent('.wrap .muted'));

  /* A scope with no query is a real address: it is what the collection
     page's own search link means, and the empty segment carrying it must
     survive the round trip through the URL. */
  await page.goto(ctx.base + '#/search//in:gospels');
  await page.waitForTimeout(900);
  t.check('a collection can be narrowed to before a word is typed',
          await page.inputValue('.search-bar select') === 'in:gospels',
          await page.inputValue('.search-bar select'));

  await page.fill('.search-bar input', 'shepherd');
  await settled(page);
  t.check('and typing one then keeps the narrowing',
          /in Gospels/.test(await page.textContent('.wrap .muted') || '') &&
          page.url().indexOf('in:gospels') > 0,
          await page.textContent('.wrap .muted'));

  /* A stale or mistyped collection is dropped rather than kept as a scope
     no verse can be in -- the same rule a stale work id already followed. */
  await page.goto(ctx.base + '#/search/shepherd/in:notacollection');
  await settled(page);
  t.check('a collection nothing knows is dropped, not searched under',
          await page.inputValue('.search-bar select') === '' &&
          await page.locator('.result').count() === EXPECT.shepherd,
          await page.locator('.result').count() + ' of ' + EXPECT.shepherd);

  /* ---------------- and what a search must not answer ----------------

     Every one of these boxes is a guess at what somebody meant, and a guess
     made from one very common word is noise sitting above the results they
     actually asked for. "The" is the first word of four collection titles,
     of half the threads, and -- by the title prefix the reference resolver
     matches on -- of six works. */

  a = await answers('the');
  t.check('one word that is mostly grammar answers nothing at all',
          a.length === 0,
          a.map(b => b.rows.join('/')).join(' | ') || '(nothing, as it should)');

  /* A word of a phrase is not the phrase. "Dead sea scrolls" is the only
     name two of the manuscripts answer to; "dead" is a question about what
     the texts say. */
  a = await answers('dead');
  t.check('a word inside a manuscript\'s nickname does not summon it',
          !a.some(b => /is-witness/.test(b.head) ) &&
          rowsOf(a).every(r => !/Isaiah Scroll/.test(r)),
          rowsOf(a).join(' | '));

  t.check('though the thread it is the title of still answers',
          rowsOf(a).indexOf('Where do the dead go?') >= 0,
          rowsOf(a).join(' | '));

  t.check('and the phrase itself still reaches the manuscripts',
          rowsOf(await answers('dead sea scrolls'))
            .some(r => /Isaiah Scroll/.test(r)));

  t.check('a word inside a passage\'s name does not summon it either',
          rowsOf(await answers('god')).indexOf('The Armour of God') < 0,
          rowsOf(await answers('god')).join(' | '));

  t.check('though the full name still reaches it',
          rowsOf(await answers('armour of god')).indexOf('The Armour of God') >= 0,
          rowsOf(await answers('armour of god')).join(' | '));

  /* The dictionary and the gazetteer are sharded by first letter and now
     ship every shard, empty ones included: no entry starts "x", no place
     starts "q", and asking for a file that is not there answered an
     ordinary lookup with a 404 in the console of every reader who tried. */
  const noise = [];
  page.on('console', m => { if (m.type() === 'error') noise.push(m.text()); });
  for (const q of ['xerxes', 'quartus', 'xystus']) await answers(q);
  t.check('a letter with no entries is answered, not 404ed',
          noise.length === 0, noise.join(' | ') || 'no console errors');

  /* ---------------- the name a reader has for their own Bible ----------

     The Canons page compares five canons and nobody has one: they have a
     church, and the word for it is "Baptist" or "Pentecostal" or "Reform",
     none of which is one of the five and none of which found anything.

     The fix is deliberately not a filter. Thirty of these names read one of
     five canons, so a dropdown of them would return identical results for
     most entries and would tell the reader their tradition has a canon of
     its own, which for most of them is false. */

  a = await answers('baptist');
  t.check('the name of a church reaches the canon it reads',
          rowsOf(a).indexOf('Baptist churches') >= 0,
          rowsOf(a).join(' | ') || '(nothing offered)');

  const saidsFor = async (q) => {
    await page.goto(ctx.base + '#/search/' + encodeURIComponent(q));
    await settled(page);
    await page.waitForTimeout(600);
    return page.$$eval('.jump-box.is-tradition .jump-said',
                       ps => ps.map(p => p.textContent));
  };

  /* The sentence the whole design rests on: your canon is shared, and that
     is why this is an answer and not a filter. */
  let s1 = await saidsFor('baptist');
  t.check('and says the canon is shared rather than implying it is theirs',
          /Reads the Protestant canon, as do \d+ other traditions/.test(s1[0] || ''),
          s1[0] || '(said nothing)');

  const s2 = await saidsFor('pentecostal');
  t.check('two churches that share a canon are told the same thing',
          (s1[0] || '') === (s2[0] || ''), s2[0] || '(said nothing)');

  t.check('and the answer links to that canon, ready to search',
          hrefsOf(await answers('pentecostal'))
            .indexOf('#/search//canon:protestant') >= 0,
          hrefsOf(await answers('pentecostal')).join(' '));

  /* Where a tradition really does differ, it says how. */
  s1 = await saidsFor('anglican');
  t.check('a tradition whose Bible is not simply the sixty-six says so',
          /example of life/.test(s1[0] || ''), (s1[0] || '').slice(0, 80));

  s1 = await saidsFor('messianic judaism');
  t.check('and a tradition that reads across two of them is placed, not refused',
          /Tanakh and the New Testament/.test(s1[0] || ''),
          (s1[0] || '').slice(0, 80));

  /* Three land nowhere, on purpose. Offering the nearest column would hand
     a reader books their tradition does not receive. */
  s1 = await saidsFor('church of the east');
  t.check('it says which books its New Testament does not have',
          /twenty-two books/.test(s1[0] || '') && /Revelation/.test(s1[0] || ''),
          (s1[0] || '').slice(0, 80));

  t.check('and offers no link, because there is nowhere honest to send it',
          await page.locator('.jump-box.is-tradition a.jump-link').count() === 0 &&
          await page.locator('.jump-box.is-tradition .is-unplaced').count() === 1,
          await page.locator('.jump-box.is-tradition a.jump-link').count() +
          ' links');

  s1 = await saidsFor('islam');
  t.check('a religion whose scripture is not in this volume is told plainly',
          /Qur/.test(s1[0] || '') && /not in this volume/.test(s1[0] || ''),
          (s1[0] || '').slice(0, 80));

  /* An approximation is never announced as the tradition's own canon. */
  s1 = await saidsFor('coptic');
  t.check('a nearest-column answer leads with being a nearest column',
          /^Nearest column here/.test(s1[0] || ''), (s1[0] || '').slice(0, 60));

  /* Singular for plural is how these are actually typed. */
  t.check('"quaker" reaches Quakers, and "orthodox jew" Orthodox Judaism',
          rowsOf(await answers('quaker')).some(r => /Quakers/.test(r)) &&
          rowsOf(await answers('orthodox jew'))
            .indexOf('Orthodox Judaism') >= 0);

  /* And a religion nobody is asking this page about stays quiet rather than
     matching on a word inside a note. */
  t.check('a word that is only inside a note does not summon a tradition',
          !rowsOf(await answers('liturgy')).some(r => /Catholic/.test(r)),
          rowsOf(await answers('liturgy')).join(' | ') || '(quiet)');

  await page.close();
};
