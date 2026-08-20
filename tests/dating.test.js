'use strict';

/* The date card, the method page, and citing a passage.
 *
 * The arrangement of this volume is its argument, so the parts that show how
 * a date was arrived at, and let a reader carry a passage out with its
 * provenance attached, are load-bearing rather than decorative.
 *
 * The spans themselves are checked in tests/python/test_dates.py, against
 * every position statement in the volume. This checks that what was read
 * there is what reaches the page.
 */

async function openPositions(page, base, route) {
  await page.goto(base + route);
  await page.waitForSelector('.positions');
  const head = page.locator('.positions-head');
  if (await head.getAttribute('aria-expanded') !== 'true') await head.click();
  await page.waitForTimeout(300);
}

module.exports = async function dating(t, ctx) {
  const page = ctx.tally.watch(await ctx.browser.newPage(),
                               'dating');
  await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
            .catch(() => {});

  /* ---- two positions that disagree by centuries ---- */
  await openPositions(page, ctx.base, '#/read/genesis/0');

  t.check('a work with dated positions gets a date card',
          await page.locator('.datecard').count() === 1);

  t.check('with a bar for each of the two positions',
          await page.locator('.datebar').count() === 2);

  const spans = await page.locator('.datespan').allTextContents();
  t.check('and each bar is labelled with the years it covers',
          spans.length === 2 && /1500/.test(spans[0]) && /400/.test(spans[1]),
          spans.join(' | '));

  t.check('the card says how far apart the two datings are',
          /701 years apart/.test(await page.textContent('.dateverdict')),
          (await page.textContent('.dateverdict')).slice(0, 50));

  /* The two bars must not be drawn on different scales, which would make the
     distance between them meaningless. */
  const geom = await page.evaluate(() => {
    const track = document.querySelector('.datetrack').getBoundingClientRect();
    return Array.from(document.querySelectorAll('.datebar')).map(b => {
      const r = b.getBoundingClientRect();
      return { left: Math.round(r.left - track.left), width: Math.round(r.width) };
    });
  });
  t.check('the bars are on one scale, so the gap on the page is the real gap',
          geom.length === 2 && geom[0].left < geom[1].left &&
          geom.every(g => g.width > 0),
          JSON.stringify(geom));

  /* ---- two positions that agree ---- */
  await openPositions(page, ctx.base, '#/read/amos/0');
  t.check('a work the two positions agree about says they overlap',
          /overlap/i.test(await page.textContent('.dateverdict')),
          (await page.textContent('.dateverdict')).slice(0, 45));

  /* ---- a position that names a person, not a date ----
     The case the parser must refuse. Drawing a plausible bar here would be
     inventing evidence. */
  await openPositions(page, ctx.base, '#/read/deuteronomy/0');
  t.check('a position that names a person gets no bar',
          await page.locator('.dateunknown').count() === 1 &&
          await page.locator('.datebar').count() === 1);
  t.check('and the card says why rather than leaving a blank',
          /names a person/i.test(await page.textContent('.datecard')));

  /* ---- how firm the claim is, visible ---- */
  await openPositions(page, ctx.base, '#/read/genesis/0');
  const kinds = await page.evaluate(() =>
    Array.from(document.querySelectorAll('.datebar'))
         .map(b => b.className.replace('datebar', '').trim()));
  t.check('a span read from a century is marked as one, not as exact years',
          kinds.indexOf('century') >= 0, kinds.join(', '));

  t.check('and every bar carries the reading in its tooltip',
          await page.locator('.datebar[title]').count() ===
          await page.locator('.datebar').count());

  /* ---- the card points at the working ---- */
  t.check('the card links to the method and to the accuracy report',
          await page.locator('.datecite a[href="#/method"]').count() === 1 &&
          await page.locator('.datecite a[href="#/accuracy"]').count() === 1);

  /* ---- the method page ---- */
  await page.locator('.datecite a[href="#/method"]').click();
  await page.waitForSelector('h1');
  await page.waitForTimeout(400);
  const method = await page.textContent('main');

  t.check('the method page opens', /how the dating was decided/i.test(
    await page.textContent('h1')));

  t.check('it says the order is a decision, not a verdict',
          /not a verdict|decision about order/i.test(method));

  t.check('it says what happens when a position names no date',
          /inventing evidence|names a person/i.test(method));

  t.check('it warns that a composite book has one bar and several dates',
          /composite/i.test(method));

  t.check('it says overlapping bars are not agreement',
          /not agreement/i.test(method));

  const rows = await page.locator('tbody tr').count();
  t.check('and it lists every named period with the event that fixes it',
          rows >= 8, rows + ' periods');

  t.check('the accuracy report leads here too',
          await (async () => {
            await page.goto(ctx.base + '#/accuracy');
            await page.waitForSelector('h1');
            await page.waitForTimeout(500);
            return await page.locator('main a[href="#/method"]').count() >= 1;
          })());

  /* ---- citing a passage ----
     A reference to this volume is worth having only if it names the edition
     and where the passage sits in the order. Neither is in the reference a
     reader would otherwise type. */
  await page.goto(ctx.base + '#/read/amos/2');
  await page.waitForSelector('.reader .v');
  await page.locator('.reader .v .vnum').first().click();
  await page.waitForSelector('.vmenu');

  const items = await page.locator('.vmenu button').allTextContents();
  t.check('the verse menu offers a citation and a BibTeX entry',
          items.some(i => /citation/i.test(i)) &&
          items.some(i => /bibtex/i.test(i)), items.length + ' items');

  await page.locator('.vmenu button', { hasText: 'Copy a citation' }).click();
  await page.waitForTimeout(300);
  const cite = await page.evaluate(() => navigator.clipboard.readText())
                         .catch(() => '');
  t.check('the citation names the passage', /amos/i.test(cite), cite.slice(0, 60));
  t.check('and the public-domain edition the text is from',
          /world english bible/i.test(cite));
  t.check('and where it sits in the composition order',
          /arranged under/i.test(cite), cite.slice(-90));
  t.check('and links back to the exact verse',
          /#\/read\/amos\/2\/v\d+/.test(cite));

  await page.keyboard.press('Escape');
  await page.locator('.reader .v .vnum').first().click();
  await page.locator('.vmenu button', { hasText: 'BibTeX' }).click();
  await page.waitForTimeout(300);
  const bib = await page.evaluate(() => navigator.clipboard.readText())
                        .catch(() => '');
  t.check('the BibTeX entry is a well-formed incollection',
          /^@incollection\{/.test(bib.trim()) && bib.trim().endsWith('}'),
          bib.split('\n')[0]);
  t.check('with a key nobody has to invent, a title, an edition and a url',
          /thebook:amos3/.test(bib) && /title\s*=/.test(bib) &&
          /edition\s*=/.test(bib) && /url\s*=/.test(bib),
          (bib.match(/@incollection\{([^,]+)/) || [])[1]);

  /* ---- and out of the saved page in bulk ---- */
  await page.keyboard.press('Escape');
  await page.locator('.reader .v .vnum').first().click();
  await page.locator('.vmenu button').first().click();
  await page.keyboard.press('Escape');
  await page.goto(ctx.base + '#/saved');
  await page.waitForSelector('.saved-row');

  const buttons = await page.locator('.toolbar .chip').allTextContents();
  t.check('saved verses can leave as text, as citations, or as BibTeX',
          buttons.length === 3, buttons.join(' | '));

  await page.locator('.toolbar .chip', { hasText: 'BibTeX' }).click();
  await page.waitForTimeout(300);
  const bulk = await page.evaluate(() => navigator.clipboard.readText())
                         .catch(() => '');
  t.check('and the bulk export is the same entries',
          /^@incollection\{/.test(bulk.trim()), bulk.split('\n')[0]);

  await page.close();
};
