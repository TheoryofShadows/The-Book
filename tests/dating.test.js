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

  /* ---- the whole library on one axis ---- */

  /* Reachable from the bar, which is the fix this needed most. The axis was
     built, tested and linked from one sentence in the second paragraph of a
     callout half way down the front page, while the bar's own "Timeline"
     pointed at that front page -- a manifesto, a row of statistics and an
     accordion of eras. A visitor who came to see eight hundred years read a
     pitch instead. */
  await page.goto(ctx.base + '#/');
  await page.waitForSelector('.nav');
  await page.locator('.nav a', { hasText: 'Timeline' }).click();
  await page.waitForSelector('.tl-row');
  t.check('the bar\'s Timeline link goes to the axis',
          /#\/timeline$/.test(page.url()), page.url());
  t.check('and the bar marks it as the page you are on',
          await page.locator('.nav a[aria-current="page"]').count() === 1);

  await page.goto(ctx.base + '#/timeline');
  await page.waitForSelector('.tl-row');
  await page.waitForTimeout(400);

  const shot = () => page.evaluate(() => ({
    rows: document.querySelectorAll('.tl-row').length,
    bySection: document.querySelectorAll('.tl-row.placed-section').length,
    ticks: Array.from(document.querySelectorAll('.tl-tick')).map(t => t.textContent),
    order: Array.from(document.querySelectorAll('.tl-row .tl-name'))
                .slice(0, 6).map(n => n.textContent),
    undated: (document.querySelector('.tl-undated summary') || {}).textContent || '',
    bars: Array.from(document.querySelectorAll('.tl-bar')).map(b => ({
      left: parseFloat(b.style.left), width: parseFloat(b.style.width)
    }))
  }));

  const crit = await shot();
  t.check('the timeline draws most of the library',
          crit.rows > 90, crit.rows + ' works placed');

  t.check('every bar has a position and a width on the axis',
          crit.bars.length === crit.rows &&
          crit.bars.every(b => b.left >= 0 && b.left <= 100 && b.width > 0),
          crit.bars.length + ' bars');

  /* A book the volume's own position calls composite -- the Torah, the
     Psalms, Isaiah 1-39 with the apocalypse inside it -- is not one
     composition, and a solid bar across it is the most confident mark on the
     page and the least true. The method page always admitted that; the
     drawing said nothing, so Amos, whose bar is ten years, and the Psalms,
     which the same records call a collection spanning centuries, were drawn
     as the same kind of object. */
  const layered = await page.evaluate(() => ({
    bars: document.querySelectorAll('.tl-bar.composite').length,
    summary: (document.querySelector('.tl-layered summary') || {}).textContent || '',
    named: Array.from(document.querySelectorAll('.tl-layered-list li'))
                .map(li => li.textContent)
  }));
  t.check('a composite book is not drawn as one solid bar',
          layered.bars >= 10, layered.bars + ' hatched');
  t.check('and the page counts them rather than leaving it to be noticed',
          /are not one date/.test(layered.summary), layered.summary);
  t.check('and quotes what the work\'s own position says is layered',
          layered.named.length === layered.bars &&
          layered.named.some(n => /Isaiah/.test(n) && /24-27/.test(n)),
          layered.named.find(n => /Isaiah/.test(n)) || '');

  t.check('the works come out in date order',
          await page.evaluate(() => {
            const at = Array.from(document.querySelectorAll('.tl-bar'))
                            .map(b => parseFloat(b.style.left));
            return at.every((v, i) => i === 0 || v >= at[i - 1] - 0.001);
          }));

  t.check('the axis is ruled in round years',
          crit.ticks.length >= 3 && crit.ticks.every(x => /BCE|CE/.test(x)),
          crit.ticks.join(', '));

  /* There is no year zero, and a tick that says so is simply wrong. */
  t.check('and never labels a year zero',
          !crit.ticks.some(x => /^0\s*(BCE|CE)/.test(x)), crit.ticks.join(', '));

  t.check('works placed by their era are marked as the looser claim',
          crit.bySection > 0 && crit.bySection < crit.rows,
          crit.bySection + ' of ' + crit.rows + ' placed by era');

  t.check('the count of each is stated on the page',
          /placed by the work's own dated position/i.test(
            await page.textContent('.tl-note')));

  t.check('works with no date under this column are listed, not dropped',
          /carry no date under this column/.test(crit.undated) &&
          await page.locator('.tl-undated .chip').count() > 0,
          crit.undated);

  t.check('and the page says why that is not a gap in the data',
          /nothing here is a gap in the data/i.test(
            await page.textContent('.tl-undated')));

  /* ---- switching the column reorders the library ---- */
  await page.locator('.seg button', { hasText: 'Traditional' }).click();
  await page.waitForTimeout(400);
  const trad = await shot();

  t.check('switching to the traditional dating redraws the order',
          trad.order[0] !== crit.order[0],
          crit.order[0] + ' -> ' + trad.order[0]);

  t.check('and the Torah moves to the front, which is the disagreement',
          /genesis|exodus|leviticus|numbers|deuteronomy/i.test(trad.order[0]),
          trad.order.slice(0, 3).join(' | '));

  t.check('the axis is redrawn to fit, not left on the old scale',
          trad.ticks[0] !== crit.ticks[0],
          crit.ticks[0] + ' -> ' + trad.ticks[0]);

  t.check('more works fall back to their era under the traditional column',
          trad.bySection > crit.bySection,
          crit.bySection + ' -> ' + trad.bySection);

  await page.reload();
  await page.waitForSelector('.tl-row');
  await page.waitForTimeout(400);
  t.check('the chosen column is remembered',
          await page.locator('.seg button[aria-pressed=true]').textContent() ===
          'Traditional dating');

  /* An open-ended range must not be printed as the year it stops at. */
  const whens = await page.locator('.tl-when').allTextContents();
  t.check('a range with one end unstated says so rather than naming a date',
          whens.some(w => /^before |^after /.test(w)),
          whens.filter(w => /^before |^after /.test(w))[0] || 'none found');

  t.check('every row links to the work it stands for',
          await page.locator('.tl-row[href^="#/read/"]').count() === trad.rows);

  await page.locator('.seg button', { hasText: 'Critical' }).click();
  await page.waitForTimeout(300);

  /* ---- and it is reachable ---- */
  await page.goto(ctx.base + '#/');
  await page.waitForSelector('h1');
  await page.waitForTimeout(400);
  t.check('the timeline is linked from the front page',
          await page.locator('main a[href="#/timeline"]').count() >= 1);

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
  /* The reader is at #/read/amos/2 -- the third chapter, counted from zero --
     and the address in the citation is the page built for it, which counts
     the way the book counts. A citation that named the reader's route was a
     citation nothing could crawl, nothing could preview, and that said 2 for
     a chapter printed as 3. */
  t.check('and links back to the exact verse, as a page rather than a route',
          /\/read\/amos\/3\/#v\d+$/.test(cite.trim().replace(/ \(accessed.*$/, '')),
          cite.slice(-70));
  t.check('and not to a fragment no crawler can ask for',
          !/#\/read\//.test(cite));

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
  /* By name rather than by counting. The count was standing in for "the
     three ways out are offered", and it broke the moment a fourth button
     arrived that was not one of them -- reporting a new feature as a lost
     one. What matters is that these three are here, not that nothing else
     is. */
  t.check('saved verses can leave as text, as citations, or as BibTeX',
          ['Copy all as text', 'Copy as citations', 'Copy as BibTeX']
            .every(name => buttons.indexOf(name) !== -1),
          buttons.join(' | '));

  await page.locator('.toolbar .chip', { hasText: 'BibTeX' }).click();
  await page.waitForTimeout(300);
  const bulk = await page.evaluate(() => navigator.clipboard.readText())
                         .catch(() => '');
  t.check('and the bulk export is the same entries',
          /^@incollection\{/.test(bulk.trim()), bulk.split('\n')[0]);

  await page.close();
};
