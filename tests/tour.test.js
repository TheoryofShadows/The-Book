'use strict';

/* The first-visit tour and the cues that make the two clicks findable.
 *
 * Any word opens its definition and any place opens on Google Maps, and
 * nothing on the page said so. This holds the things that fix that: the
 * place names are marked, the legend says what the marks mean, a new visitor
 * is offered a tour (offered, never forced), the tour walks the real page and
 * can be skipped, driven from the keyboard, and replayed, and a visitor who
 * has answered is never asked again. The suites above start every page as
 * somebody who has answered; this one is a new visitor, through ?firsttime.
 */

const AXE = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

async function axeViolations(page) {
  await page.addScriptTag({ url: new URL('__axe.js', page.url()).href });
  const r = await page.evaluate(async tags => await window.axe.run(
    document, { runOnly: { type: 'tag', values: tags } }), AXE);
  return r.violations.map(v => v.id + ' (' + v.impact + ')');
}

module.exports = async function tour(t, ctx) {
  const page = ctx.tally.watch(await ctx.browser.newPage({
    viewport: { width: 1280, height: 800 }
  }), 'tour');

  /* ---- a chapter says what is clickable ---- */
  await page.goto(ctx.base + '?firsttime#/read/jonah/0');
  await page.waitForSelector('.reader .v');
  t.check('a chapter carries a line saying what to tap',
          /Tap any word/.test(await page.textContent('.reader-legend')) &&
          /Google Maps/.test(await page.textContent('.reader-legend')));

  const marked = await page.evaluate(async () => {
    if (!window.Highlight || !CSS.highlights) return -1;
    for (let i = 0; i < 40 && !CSS.highlights.has('tbm-place'); i++) {
      await new Promise(r => setTimeout(r, 100));
    }
    const h = CSS.highlights.get('tbm-place');
    return h ? Array.from(h).map(r => r.toString()) : [];
  });
  if (marked === -1) {
    console.log('  skip  this browser has no CSS Custom Highlight API');
  } else {
    t.check('the places Jonah 1 names are marked in its text',
            ['Nineveh', 'Tarshish', 'Joppa'].every(n => marked.indexOf(n) >= 0),
            Array.from(new Set(marked)).join(', '));
    t.check('and only those: no word that is not a recorded place',
            marked.every(n => ['Nineveh', 'Tarshish', 'Joppa'].indexOf(n) >= 0));

    /* The switch for dictionary underlines does its own work, on request. */
    await page.click('.chip-terms');
    const termCount = await page.evaluate(async () => {
      for (let i = 0; i < 60 && !CSS.highlights.has('tbm-term'); i++) {
        await new Promise(r => setTimeout(r, 100));
      }
      const h = CSS.highlights.get('tbm-term');
      return h ? h.size : 0;
    });
    t.check('asking for defined words underlines them', termCount > 5, termCount + ' ranges');
    t.check('and the switch says it is on',
            await page.getAttribute('.chip-terms', 'aria-pressed') === 'true');
    await page.click('.chip-terms');
    t.check('turning it off takes them away again',
            await page.evaluate(() => !CSS.highlights.has('tbm-term')));
  }

  /* ---- the offer ---- */
  await page.goto(ctx.base + '?firsttime#/');
  await page.waitForSelector('.tour-invite', { timeout: 8000 });
  t.check('a new visitor is offered the tour, not shown it',
          (await page.$('.tour-card')) === null &&
          (await page.$('.tour-invite')) !== null);
  t.check('the offer has a button to take it and a way to say no',
          (await page.$$('.tour-invite button')).length === 2);
  const offerAxe = await axeViolations(page);
  t.check('the offer fails no WCAG A or AA check', offerAxe.length === 0, offerAxe.join(', '));

  await page.click('.tour-invite button:not(.primary)');
  t.check('"No thanks" removes it', (await page.$('.tour-invite')) === null);
  t.check('and is remembered', await page.evaluate(
    () => localStorage.getItem('thebook:tour')) === '"skipped"');
  await page.reload();
  await page.waitForTimeout(3800);
  t.check('so it does not come back on the next visit',
          (await page.$('.tour-invite')) === null);

  /* ---- the front-page line starts it too ---- */
  await page.click('.discover-strip [data-tour]');
  await page.waitForSelector('.tour-card', { timeout: 10000 });
  t.check('the front-page line starts the tour on a real chapter',
          /#\/read\/jonah\/0/.test(page.url()) &&
          (await page.$$('.reader .v')).length > 5);
  t.check('it opens as a dialog that names itself',
          await page.getAttribute('.tour-card', 'role') === 'dialog' &&
          !!(await page.getAttribute('.tour-card', 'aria-labelledby')));
  t.check('it says where you are in it', /Step 1 of 5/.test(await page.textContent('.tour-count')));
  t.check('focus is on the button that moves on',
          await page.evaluate(() => document.activeElement.classList.contains('tour-next')));
  t.check('the thing it points at is ringed and on screen', await page.evaluate(() => {
    const r = document.querySelector('.tour-ring');
    if (!r || r.hidden) return false;
    const b = r.getBoundingClientRect();
    return b.width > 10 && b.top >= 0 && b.bottom <= innerHeight;
  }));
  t.check('the page behind it is still live and scrollable',
          await page.evaluate(() => getComputedStyle(document.querySelector('.tour-ring'))
            .pointerEvents === 'none'));

  const tourAxe = await axeViolations(page);
  t.check('a step fails no WCAG A or AA check', tourAxe.length === 0, tourAxe.join(', '));

  /* ---- step through it by keyboard ---- */
  await page.keyboard.press('Enter');
  await page.waitForSelector('.lex .place-links .chip.primary', { timeout: 6000 });
  t.check('step 1 opens a real definition panel for a place',
          /Nineveh|Joppa|Tarshish/.test(await page.textContent('.lex-head')));
  await page.waitForFunction(() => /Step 2 of 5/.test(
    document.querySelector('.tour-count').textContent));
  t.check('step 2 points at Open in Google Maps', await page.evaluate(() => {
    const ring = document.querySelector('.tour-ring').getBoundingClientRect();
    const btn = document.querySelector('.lex .place-links .chip.primary').getBoundingClientRect();
    return Math.abs(ring.left + ring.width / 2 - (btn.left + btn.width / 2)) < 12 &&
           Math.abs(ring.top + ring.height / 2 - (btn.top + btn.height / 2)) < 12;
  }));
  const href = await page.getAttribute('.lex .place-links .chip.primary', 'href');
  t.check('that button really is a Google Maps link, opening a new tab safely',
          /^https:\/\/www\.google\.com\/maps\//.test(href) &&
          await page.getAttribute('.lex .place-links .chip.primary', 'target') === '_blank' &&
          /noopener/.test(await page.getAttribute('.lex .place-links .chip.primary', 'rel')));

  await page.keyboard.press('ArrowRight');
  await page.waitForFunction(() => /Step 3 of 5/.test(
    document.querySelector('.tour-count').textContent));
  t.check('moving past the place step closes the panel', (await page.$('.lex')) === null);
  await page.keyboard.press('ArrowLeft');
  await page.waitForFunction(() => /Step 2 of 5/.test(
    document.querySelector('.tour-count').textContent));
  t.check('the left arrow goes back', true);
  await page.keyboard.press('ArrowRight');
  await page.waitForFunction(() => /Step 3 of 5/.test(
    document.querySelector('.tour-count').textContent));
  await page.keyboard.press('ArrowRight');
  await page.waitForFunction(() => /Step 4 of 5/.test(
    document.querySelector('.tour-count').textContent));
  await page.keyboard.press('ArrowRight');
  await page.waitForFunction(() => /Step 5 of 5/.test(
    document.querySelector('.tour-count').textContent));
  t.check('the last step says Done',
          (await page.textContent('.tour-next')).trim() === 'Done');
  await page.click('.tour-next');
  t.check('Done closes the tour', (await page.$('.tour-card')) === null &&
                                   (await page.$('.tour-ring')) === null);
  t.check('and records that it was finished',
          await page.evaluate(() => localStorage.getItem('thebook:tour')) === '"done"');

  /* ---- skip, escape, replay ---- */
  await page.goto(ctx.base + '#/');
  await page.waitForSelector('#tour-replay');
  await page.click('#tour-replay');
  await page.waitForSelector('.tour-card', { timeout: 10000 });
  t.check('the footer link replays it for somebody who has seen it', true);
  await page.keyboard.press('Escape');
  t.check('Escape closes it', (await page.$('.tour-card')) === null);
  await page.click('#tour-replay');
  await page.waitForSelector('.tour-card', { timeout: 10000 });
  await page.click('.tour-skip');
  t.check('"Skip the tour" closes it', (await page.$('.tour-card')) === null);

  /* ---- a phone ---- */
  const phone = ctx.tally.watch(await ctx.browser.newPage({
    viewport: { width: 375, height: 667 }, hasTouch: true, isMobile: true
  }), 'tour phone');
  await phone.goto(ctx.base + '?firsttime#/');
  await phone.waitForSelector('.tour-invite', { timeout: 8000 });
  t.check('on a phone the offer fits inside the screen', await phone.evaluate(() => {
    const b = document.querySelector('.tour-invite').getBoundingClientRect();
    return b.left >= 0 && b.right <= innerWidth && b.bottom <= innerHeight;
  }));
  await phone.click('.tour-invite button.primary');
  await phone.waitForSelector('.tour-card', { timeout: 10000 });
  let fits = true;
  for (let i = 0; i < 5; i++) {
    await phone.waitForTimeout(500);
    fits = fits && await phone.evaluate(() => {
      const c = document.querySelector('.tour-card').getBoundingClientRect();
      const r = document.querySelector('.tour-ring');
      const b = r.hidden ? null : r.getBoundingClientRect();
      const inside = c.left >= 0 && c.right <= innerWidth && c.top >= 0 && c.bottom <= innerHeight;
      /* The card must not sit on top of the thing it describes. */
      const clear = !b || c.bottom <= b.top + 2 || c.top >= b.bottom - 2;
      return inside && clear;
    });
    await phone.tap('.tour-next');
  }
  t.check('on a phone every step fits and never covers what it points at', fits);
  await phone.close();

  /* ---- reduced motion ---- */
  const calm = ctx.tally.watch(await ctx.browser.newPage({
    reducedMotion: 'reduce', viewport: { width: 1280, height: 800 }
  }), 'tour calm');
  await calm.goto(ctx.base + '#/');
  await calm.click('#tour-replay');
  await calm.waitForSelector('.tour-ring', { timeout: 10000 });
  t.check('with reduced motion asked for, nothing pulses',
          await calm.evaluate(() => getComputedStyle(document.querySelector('.tour-ring'))
            .animationName === 'none'));
  await calm.close();

  /* ---- the offer and the tour never touch an account or the network ---- */
  const hits = [];
  const quiet = await ctx.browser.newPage();
  quiet.on('request', r => { if (/\/api\//.test(r.url())) hits.push(r.url()); });
  await quiet.goto(ctx.base + '?firsttime#/');
  await quiet.waitForSelector('.tour-invite', { timeout: 8000 });
  await quiet.click('.tour-invite button.primary');
  await quiet.waitForSelector('.tour-card', { timeout: 10000 });
  await quiet.close();
  t.check('taking the tour makes no request to the account API', hits.length === 0, hits.join(' '));

  await page.close();
};
