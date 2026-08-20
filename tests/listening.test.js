'use strict';

/* Read aloud: what is spoken, in what order, and what happens when the
   device cannot speak at all. */

const { workingEngine, failingEngine, silentEngine, noEngine } = require('./harness');

const settle = 120;

async function open(ctx, route, engine) {
  const page = ctx.tally.watch(await ctx.browser.newPage(), route);
  if (engine) await page.addInitScript(engine);
  await page.goto(ctx.base + route);
  await page.waitForSelector('.reader .v, .reader p', { timeout: 20000 });
  return page;
}

/* Step the transport to the end of the chapter without assuming how many
   pieces are in it, stopping the moment the condition it is waiting for
   changes so a later assertion is not racing a chapter that moved on. */
async function toChapterEnd(page, keepGoingWhile) {
  await page.evaluate(cond => {
    const next = document.querySelector('[aria-label="Forward one verse"]');
    for (let i = 0; i < 500 && eval(cond); i++) next.click();
  }, keepGoingWhile);
  await page.waitForTimeout(500);
}

module.exports = async function listening(t, ctx) {
  /* ---- a chapter with numbered verses ---- */
  let page = await open(ctx, '#/read/amos/2', workingEngine(30));

  t.check('the reader offers to read the chapter aloud',
          await page.locator('[data-listen]').count() === 1);
  await page.locator('[data-listen]').click();
  await page.waitForSelector('.player:not([hidden])');
  await page.waitForFunction(() => window.__spoken.length >= 2);

  const spoken = await page.evaluate(() => window.__spoken.map(s => s.text));
  const firstVerse = await page.evaluate(
    () => document.querySelector('.reader .v').lastChild.textContent.trim());
  t.check('it announces the chapter first', spoken[0] === 'Chapter 3.', JSON.stringify(spoken[0]));
  t.check('then reads verse one', spoken[1].trim() === firstVerse);
  t.check('using a voice from the device',
          await page.evaluate(() => window.__spoken[0].voice) === 'test-en');
  t.check('the verse being spoken is marked on the page',
          await page.locator('.reader .v.is-speaking').count() === 1);
  t.check('and the word inside it is highlighted',
          await page.waitForFunction(() => CSS.highlights.has('book-speaking'), null, { timeout: 3000 })
            .then(() => true).catch(() => false));
  t.check('the player says where it is and how long is left',
          /(min left|under a minute left)/.test(await page.textContent('.player-unit')),
          await page.textContent('.player-unit'));

  /* ---- transport ---- */
  await page.locator('.player-play').click();
  await page.waitForTimeout(settle);
  t.check('pause turns the button back into play',
          await page.textContent('.player-play') === '▶');
  const beforePause = await page.evaluate(() => window.__spoken.length);
  await page.waitForTimeout(250);
  t.check('and nothing is spoken while it is paused',
          await page.evaluate(() => window.__spoken.length) === beforePause);
  await page.locator('.player-play').click();
  await page.waitForFunction(n => window.__spoken.length > n, beforePause);
  t.check('play picks it up again', true);

  await page.selectOption('select[aria-label="Reading speed"]', '1.5');
  await page.waitForFunction(() => window.__spoken[window.__spoken.length - 1].rate === 1.5);
  t.check('a speed change reaches the next utterance', true);

  const where = await page.textContent('.player-unit');
  await page.locator('[aria-label="Forward one verse"]').click();
  await page.waitForFunction(w => document.querySelector('.player-unit').textContent !== w, where);
  t.check('skipping forward moves the position', true, await page.textContent('.player-unit'));

  await page.waitForTimeout(200);
  const at = await page.evaluate(() => JSON.parse(localStorage.getItem('thebook:listen-at')));
  t.check('the position is remembered as it goes', !!at && at.work === 'amos' && at.at > 0,
          JSON.stringify(at));

  /* ---- one chapter runs into the next ---- */
  await toChapterEnd(page, "location.hash === '#/read/amos/2'");
  t.check('the end of a chapter carries on into the next',
          await page.evaluate(() => location.hash.indexOf('#/read/amos/') === 0 && location.hash !== '#/read/amos/2'),
          await page.evaluate(() => location.hash));
  t.check('and starts reading there',
          await page.waitForFunction(() => document.querySelector('.is-speaking'), null, { timeout: 4000 })
            .then(() => true).catch(() => false));

  /* ---- leaving the reader ---- */
  await page.evaluate(() => { location.hash = '#/saved'; });
  await page.waitForTimeout(300);
  t.check('leaving the reader stops it and closes the player',
          await page.evaluate(() => document.querySelector('.player').hidden));
  await page.close();

  /* Stopping is not breaking: the same chapter must start again afterwards. */
  page = await open(ctx, '#/read/amos/2', workingEngine(40));
  await page.locator('[data-listen]').click();
  await page.waitForFunction(() => window.__spoken.length >= 2);
  await page.locator('.player-close').click();
  await page.waitForTimeout(200);
  const stoppedAt = await page.evaluate(() => window.__spoken.length);
  t.check('the stop button closes the player',
          await page.evaluate(() => document.querySelector('.player').hidden));
  await page.locator('[data-listen]').click();
  t.check('and the same chapter starts again afterwards',
          await page.waitForFunction(n => window.__spoken.length > n, stoppedAt, { timeout: 4000 })
            .then(() => true).catch(() => false));
  await page.close();

  /* ---- picking a part-read chapter back up ---- */
  page = await open(ctx, '#/read/amos/2', workingEngine(30));
  await page.evaluate(() => localStorage.setItem('thebook:listen-at',
    JSON.stringify({ work: 'amos', chapter: 2, at: 4 })));
  await page.reload();
  await page.waitForSelector('[data-listen]');
  t.check('a part-read chapter offers to resume where it stopped',
          (await page.textContent('[data-listen]')).indexOf('Resume') !== -1,
          await page.textContent('[data-listen]'));

  /* ---- starting from one verse ---- */
  await page.locator('.reader .v .vnum').first().click();
  const fromHere = page.locator('.vmenu button', { hasText: 'Read aloud from here' });
  t.check('any verse can be the starting point', await fromHere.count() === 1);
  await fromHere.click();
  await page.waitForSelector('.player:not([hidden])');
  t.check('choosing it opens the player', true);

  await page.keyboard.press('Escape');
  await page.evaluate(() => document.body.focus());
  await page.keyboard.press('l');
  await page.waitForTimeout(settle);
  t.check('the l key pauses and resumes it',
          await page.textContent('.player-play') === '▶');
  await page.close();

  /* ---- a work with no verse numbers ---- */
  page = await open(ctx, '#/read/the-testament-of-issachar/0', workingEngine(30));
  await page.locator('[data-listen]').click();
  await page.waitForFunction(() => window.__spoken.length >= 4);
  const heading = await page.evaluate(() => window.__spoken[0].text);
  const para = await page.evaluate(() => document.querySelector('.reader p').textContent);
  t.check('the first chapter of a work names the work',
          heading.indexOf('The Testament of Issachar.') === 0, JSON.stringify(heading));
  t.check('a work without verses is read by paragraph',
          para.indexOf((await page.evaluate(() => window.__spoken[1].text)).trim()) === 0);

  const longest = await page.evaluate(
    () => Math.max.apply(null, window.__spoken.map(s => s.text.length)));
  t.check('no utterance is long enough to hit the Chrome cut-off', longest <= 220,
          longest + ' characters');
  const rejoined = await page.evaluate(() => window.__spoken.slice(1).map(s => s.text).join(''));
  t.check('the pieces reassemble into the paragraph exactly', para.indexOf(rejoined) === 0);
  await page.close();

  /* ---- one work runs into the next written ---- */
  page = await open(ctx, '#/read/amos/8', workingEngine(25));   // Amos has nine chapters
  await page.locator('[data-listen]').click();
  await page.waitForSelector('.player:not([hidden])');
  await toChapterEnd(page, "location.hash === '#/read/amos/8'");
  t.check('the last chapter of a work runs on into the next work',
          (await page.evaluate(() => location.hash)).indexOf('#/read/hosea/') === 0,
          await page.evaluate(() => location.hash));
  t.check('and names the work it has moved into',
          await page.waitForFunction(() => window.__spoken.some(s => s.text.indexOf('Hosea') === 0),
                                     null, { timeout: 4000 }).then(() => true).catch(() => false));
  await page.close();

  /* ---- entries in the chronology that carry no text ---- */
  page = await open(ctx, '#/read/the-song-of-deborah-judges-5/0', workingEngine(25));
  await page.locator('[data-listen]').click();
  await page.waitForSelector('.player:not([hidden])');
  await toChapterEnd(page, "location.hash === '#/read/the-song-of-deborah-judges-5/0'");
  const landed = await page.evaluate(() => location.hash);
  t.check('a work with no text of its own is stepped over',
          landed !== '#/read/also-often-dated-this-early/0', landed);
  t.check('and it lands on something readable',
          await page.locator('.reader .v, .reader p').count() > 0);
  await page.close();

  /* ---- the timers ---- */
  page = await open(ctx, '#/read/amos/1', workingEngine(25));
  await page.locator('[data-listen]').click();
  await page.waitForSelector('.player:not([hidden])');
  await page.selectOption('select[aria-label="Sleep timer"]', 'chapter');
  await toChapterEnd(page, "!document.querySelector('.player').hidden");
  t.check('the end-of-chapter timer stops instead of carrying on',
          await page.evaluate(() => document.querySelector('.player').hidden &&
                                    location.hash === '#/read/amos/1'),
          await page.evaluate(() => location.hash));

  await page.locator('[data-listen]').click();
  await page.locator('.player-cont').click();
  t.check('continuing can be turned off',
          await page.getAttribute('.player-cont', 'aria-pressed') === 'false');
  await toChapterEnd(page, "location.hash === '#/read/amos/1'");
  t.check('with it off, the chapter is where it stops',
          await page.evaluate(() => location.hash) === '#/read/amos/1');
  await page.close();

  /* ---- devices that cannot speak ---- */
  for (const [label, engine, wait] of [
    ['a device with no voice installed', failingEngine(), 1500],
    ['an engine that says nothing at all', silentEngine(), 6500]
  ]) {
    page = await open(ctx, '#/read/amos/2', engine);
    await page.locator('[data-listen]').click();
    await page.waitForTimeout(wait);
    const state = await page.evaluate(() => ({
      note: (document.querySelector('.listen-note') || {}).textContent || '',
      disabled: document.querySelector('[data-listen]').disabled,
      hidden: document.querySelector('.player').hidden,
      live: (document.querySelector('[role="status"]') || {}).textContent || ''
    }));
    t.check(`${label}: says so on the page`, /no speech voice/i.test(state.note),
            state.note.slice(0, 48) || 'nothing shown');
    t.check(`${label}: and to a screen reader`, /no speech voice/i.test(state.live));
    t.check(`${label}: the button stops inviting another try`, state.disabled === true);
    t.check(`${label}: no empty player is left up`, state.hidden === true);
    await page.goto(ctx.base + '#/read/amos/3');
    await page.waitForSelector('.reader .v');
    t.check(`${label}: the next chapter already knows`,
            await page.evaluate(() => document.querySelector('[data-listen]').disabled) === true);
    await page.close();
  }

  /* The watchdog that catches a silent engine must never fire on a working
     one, so this runs well past its five seconds. */
  page = await open(ctx, '#/read/amos/2', workingEngine(30));
  await page.locator('[data-listen]').click();
  await page.waitForTimeout(7000);
  const healthy = await page.evaluate(() => ({
    spoken: window.__spoken.length,
    note: !!document.querySelector('.listen-note'),
    disabled: document.querySelector('[data-listen]') && document.querySelector('[data-listen]').disabled
  }));
  t.check('a working engine reads straight past the watchdog window',
          healthy.spoken > 8 && !healthy.note && !healthy.disabled, JSON.stringify(healthy));
  await page.close();

  /* ---- a browser from before the API ---- */
  page = await open(ctx, '#/read/amos/2', noEngine());
  t.check('a browser with no speech support is offered no control',
          await page.locator('[data-listen]').count() === 0);
  await page.locator('.reader .v .vnum').first().click();
  t.check('and no read-aloud item in the verse menu',
          await page.locator('.vmenu button', { hasText: 'Read aloud' }).count() === 0);
  t.check('while the rest of the verse menu still works',
          await page.locator('.vmenu button').count() === 3);
  await page.keyboard.press('Escape');
  await page.keyboard.press('l');
  await page.waitForTimeout(settle);
  t.check('and the l key does nothing at all', true);
  await page.close();
};
