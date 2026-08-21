'use strict';

/* Looking a word up.
 *
 * Roughly three hundred lines of the reader are about turning a word on the
 * page into an entry: finding the word under a tap, widening it to the
 * phrases it might belong to, folding it to a key, and showing what came
 * back. One check covered any of it, and only inside the offline suite.
 */

/* Select a range of characters inside the first verse, the way a reader
   dragging across a word does, and press d. */
async function selectAndDefine(page, word) {
  await page.evaluate(w => {
    const node = document.querySelector('.reader .v').lastChild;
    const text = node.textContent;
    const at = text.toLowerCase().indexOf(w.toLowerCase());
    if (at < 0) throw new Error('"' + w + '" is not in the first verse: ' +
                                text.slice(0, 80));
    const r = document.createRange();
    r.setStart(node, at);
    r.setEnd(node, at + w.length);
    const sel = getSelection();
    sel.removeAllRanges();
    sel.addRange(r);
  }, word);
  await page.keyboard.press('d');
}

const sheetText = page =>
  page.textContent('.lex').catch(() => '');

module.exports = async function words(t, ctx) {
  const page = ctx.tally.watch(await ctx.browser.newPage(), 'words');

  /* ---- a word that has an entry ---- */
  await page.goto(ctx.base + '#/read/amos/2');
  await page.waitForSelector('.reader .v');
  const firstVerse = await page.textContent('.reader .v');

  /* Pick a word from the verse actually on screen rather than assuming one:
     the text moves when the parse improves, and a test that hard-codes a word
     starts failing for the wrong reason. */
  const word = (firstVerse.match(/\b[A-Z][a-z]{4,}\b/) || [])[0] ||
               (firstVerse.match(/\b[a-z]{5,}\b/) || ['israel'])[0];

  await selectAndDefine(page, word);
  t.check('a selected word opens the definition panel',
          await page.waitForSelector('.lex', { timeout: 4000 })
                    .then(() => true).catch(() => false), word);

  t.check('the panel names the word it is defining',
          (await page.textContent('.lex-head') || '').toLowerCase()
            .indexOf(word.toLowerCase().slice(0, 4)) >= 0,
          (await page.textContent('.lex-head') || '').slice(0, 40));

  t.check('it is a dialog, so a screen reader announces it as one',
          await page.getAttribute('.lex', 'role') === 'dialog');

  t.check('and it says which dictionary this is and when it is from',
          /1897|easton/i.test(await sheetText(page)));

  /* ---- closing ---- */
  await page.keyboard.press('Escape');
  await page.waitForTimeout(200);
  t.check('escape closes it', await page.locator('.lex').count() === 0);

  await selectAndDefine(page, word);
  await page.waitForSelector('.lex');
  await page.locator('.lex-close').click();
  await page.waitForTimeout(200);
  t.check('and so does the close button', await page.locator('.lex').count() === 0);

  /* An open panel must not follow the reader to another page. */
  await selectAndDefine(page, word);
  await page.waitForSelector('.lex');
  await page.evaluate(() => { location.hash = '#/saved'; });
  await page.waitForTimeout(400);
  t.check('changing page closes it rather than carrying it along',
          await page.locator('.lex').count() === 0);

  /* ---- a word with no entry ---- */
  await page.goto(ctx.base + '#/read/amos/2');
  await page.waitForSelector('.reader .v');
  await page.evaluate(() => {
    const node = document.querySelector('.reader .v').lastChild;
    const r = document.createRange();
    r.setStart(node, 0); r.setEnd(node, Math.min(3, node.textContent.length));
    const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
  });
  await page.keyboard.press('d');
  await page.waitForTimeout(600);
  const none = await sheetText(page);
  t.check('a word with no entry says so rather than showing an empty panel',
          await page.locator('.lex').count() === 1 &&
          /no entry for/i.test(none) &&
          await page.locator('.lex-none').count() === 1, none.slice(0, 60));

  /* ---- with nothing selected ---- */
  await page.keyboard.press('Escape');
  await page.evaluate(() => getSelection().removeAllRanges());
  await page.keyboard.press('d');
  await page.waitForTimeout(250);
  const live = await page.textContent('[role=status]').catch(() => '');
  t.check('pressing d with nothing selected says what to do instead',
          /select a word/i.test(live || ''), (live || '').slice(0, 50));

  /* ---- the keyboard route in ----
     A word only reachable with a mouse cannot be looked up by a keyboard or
     screen reader user at all. */
  await page.evaluate(() => {
    window.prompt = () => 'Jerusalem';
  });
  await page.keyboard.press('?');
  t.check('a word can be asked for by name without touching the page',
          await page.waitForSelector('.lex', { timeout: 4000 })
                    .then(() => true).catch(() => false));

  t.check('and that word is a place, so the panel offers the map links',
          await page.locator('.lex .place-links a').count() >= 1,
          await page.locator('.lex .place').count() + ' place blocks');

  const kinds = await page.locator('.lex .place-kind').count();
  t.check('the place says what kind of identification it is',
          kinds >= 1);

  t.check('and credits the gazetteer it came from',
          /openbible|cc by/i.test(await sheetText(page)));

  /* ---- the fold, from the reader's side ----
     Entries are filed under a folded key -- "Jaare-oregim" under
     "jaareoregim", "Jacob's Well" under "jacobs well" -- and the reader has
     to arrive at that same key from the word as it is printed. The two
     implementations of the rule are held together by
     tests/python/test_tokeniser_agreement.py; this checks that the rule is
     actually the one the reader reaches an entry through.

     There is no accented headword in Easton to ask for, so the accented case
     is covered there rather than here. */
  const askFor = async term => {
    await page.keyboard.press('Escape');
    await page.evaluate(w => { window.prompt = () => w; }, term);
    await page.keyboard.press('?');
    await page.waitForTimeout(600);
    return (await page.textContent('.lex-body').catch(() => '')) || '';
  };

  const hyphenated = await askFor('Jaare-oregim');
  t.check('a hyphenated name is found with its hyphen',
          /forests of the weavers/i.test(hyphenated), hyphenated.slice(0, 45));

  t.check('a hyphen is removed rather than turned into a space',
          await askFor('Jaareoregim') === hyphenated);

  /* A space is not the same as no separator, on purpose: the headwords
     include real phrases -- "Jacob's Well", "judgment hall" -- and folding
     a space away would merge them into whatever single word they abut. */
  t.check('and a space is kept, so a phrase stays a phrase',
          await askFor('Jaare oregim') !== hyphenated);

  t.check('case makes no difference', await askFor('JAARE-OREGIM') === hyphenated);

  const possessive = await askFor("Jacob's Well");
  t.check("an apostrophe is dropped rather than splitting the name",
          possessive.length > 30 && await askFor('Jacobs Well') === possessive,
          possessive.slice(0, 45));

  /* Singular and plural are the common misses, and are handled deliberately. */
  t.check('a plural finds the singular entry',
          (await askFor('cherubims')).length > 30 ||
          (await askFor('cherubim')).length > 30);

  /* ---- aliases ----
     114 of them, mapping a name a reader might select to the entry that
     actually holds it. None of them was exercised. */
  await page.keyboard.press('Escape');
  const aliases = await page.evaluate(async base => {
    const r = await fetch(base + 'data/lexicon-aliases.json');
    return Object.entries(await r.json()).slice(0, 3);
  }, ctx.base);

  let aliasWorked = 0;
  for (const [from, to] of aliases) {
    const body = await askFor(from);
    if (body.length > 20) aliasWorked++;
  }
  t.check('an aliased name reaches the entry that holds it',
          aliasWorked === aliases.length,
          aliasWorked + ' of ' + aliases.length + ': ' +
          aliases.map(a => a[0] + '→' + a[1]).join(', '));

  /* ---- from the panel back into the volume ---- */
  await page.keyboard.press('Escape');
  await page.evaluate(() => { window.prompt = () => 'Jerusalem'; });
  await page.keyboard.press('?');
  await page.waitForSelector('.lex');
  const search = page.locator('.lex a', { hasText: 'Find every passage' });
  t.check('the panel offers to search for the word', await search.count() === 1);
  await search.click();
  await page.waitForSelector('.result', { timeout: 20000 });
  t.check('and that search finds passages',
          await page.locator('.result').count() > 0);

  await page.close();
};
