'use strict';

/* Read aloud: what is spoken, in what order, and what happens when the
   device cannot speak at all. */

const { workingEngine, failingEngine, silentEngine,
        noEngine } = require('./harness');

const settle = 120;

/* More than one init script, because the speech engine and the recorded one
   are separate stubs and several cases need both -- a device with no voice
   of its own is precisely the case the recording exists for. */
async function open(ctx, route, ...engines) {
  const page = ctx.tally.watch(await ctx.browser.newPage(), route);
  for (const engine of engines) if (engine) await page.addInitScript(engine);
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

  /* ---- which voice comes out of the drawer ----
     A device does not offer a voice, it offers a drawer of them: novelties
     and thirty-year-old relics filed beside the good ones, and often enough
     the worst thing in it flagged as the system default. Picking the first
     one, which is what this used to do, is how scripture ends up read by a
     joke robot. */
  const DRAWER = [
    { name: 'Zarvox', lang: 'en-US', voiceURI: 'zarvox', default: true, localService: true },
    { name: 'eSpeak English', lang: 'en-GB', voiceURI: 'espeak', localService: true },
    { name: 'Microsoft David Desktop - English (United States)', lang: 'en-US',
      voiceURI: 'david', localService: true },
    { name: 'Google US English', lang: 'en-US', voiceURI: 'google', localService: false },
    { name: 'Google Deutsch', lang: 'de-DE', voiceURI: 'google-de', localService: false }
  ];
  page = await open(ctx, '#/read/amos/2', workingEngine(30, DRAWER));
  await page.locator('[data-listen]').click();
  await page.waitForFunction(() => window.__spoken.length >= 1);
  t.check('the best voice is used, not the one the device calls default',
          await page.evaluate(() => window.__spoken[0].voice) === 'google',
          await page.evaluate(() => window.__spoken[0].voice));

  /* The drawer that used to be here is gone -- five controls of clutter for
     a decision almost nobody made -- but the scoring behind it is not, and
     the check above is the whole of what it now shows: given a device whose
     own default is a joke robot, the reader is read to by the best voice on
     the machine instead. That is the entire point of keeping 129 lines with
     no interface attached to them.

     The other half of the same rule is further down: a drawer holding
     nothing but relics gets told where better voices come from. Between them
     the ranking is checked from both ends. */
  t.check('and nothing is said about voices when there is a good one',
          await page.evaluate(() => document.querySelector('.player-hint').hidden));
  await page.close();

  /* Nothing a page can do makes eSpeak sound like a person; saying where
     better voices come from is the only honest help there is. */
  page = await open(ctx, '#/read/amos/2', workingEngine(30, [
    { name: 'eSpeak English', lang: 'en-GB', voiceURI: 'espeak', default: true }
  ]));
  await page.locator('[data-listen]').click();
  await page.waitForSelector('.player:not([hidden])');
  t.check('a device with nothing but a relic is told where better voices come from',
          await page.evaluate(() => {
            const h = document.querySelector('.player-hint');
            return !h.hidden && /free download/.test(h.textContent);
          }));
  await page.close();

  /* ---- an iPhone, where the quality is not in the name ----
     Apple ships the same voice at three grades and tells them apart only in
     the identifier. A phone out of the box has the compact set, which is the
     thin one, and every one of them just says "Samantha". */
  const IPHONE = [
    { name: 'Samantha', lang: 'en-US', localService: true, default: true,
      voiceURI: 'com.apple.voice.compact.en-US.Samantha' },
    { name: 'Daniel', lang: 'en-GB', localService: true,
      voiceURI: 'com.apple.voice.compact.en-GB.Daniel' },
    { name: 'Aaron', lang: 'en-US', localService: true,
      voiceURI: 'com.apple.voice.compact.en-US.Aaron' }
  ];
  page = await open(ctx, '#/read/amos/2', workingEngine(30, IPHONE));
  await page.locator('[data-listen]').click();
  await page.waitForSelector('.player:not([hidden])');
  t.check('it is told the download is what fixes it, and where',
          await page.evaluate(() => {
            const h = document.querySelector('.player-hint');
            return !h.hidden && /free download/.test(h.textContent) &&
                   /Spoken Content/.test(h.textContent);
          }));
  t.check('and the help opens rather than hovering, there being no hover',
          await page.evaluate(
            () => document.querySelector('.player-hint > summary') !== null));
  await page.close();

  /* Download the better one and it has to win, over the same name. */
  page = await open(ctx, '#/read/amos/2', workingEngine(30, IPHONE.concat([
    { name: 'Samantha', lang: 'en-US', localService: true,
      voiceURI: 'com.apple.voice.enhanced.en-US.Samantha' }
  ])));
  await page.locator('[data-listen]').click();
  await page.waitForFunction(() => window.__spoken.length >= 1);
  t.check('a downloaded voice outranks the stock one of the same name',
          await page.evaluate(() => window.__spoken[0].voice) ===
            'com.apple.voice.enhanced.en-US.Samantha',
          await page.evaluate(() => window.__spoken[0].voice));
  t.check('and nothing is said about downloads once there is a good one',
          await page.evaluate(() => document.querySelector('.player-hint').hidden));
  await page.close();

  /* ---- the editorial apparatus is not read out ----
     Charles prints his apparatus in the running text. The eye steps over a
     dagger; an engine says "dagger". */
  page = await open(ctx, '#/read/1-enoch-the-astronomical-book-chapters-72-82/0',
                    workingEngine(15));
  await page.locator('[data-listen]').click();
  await page.waitForFunction(() => window.__spoken.length >= 14);
  t.check('the marks are still on the page',
          await page.evaluate(
            () => /[+†<>[\]]/.test(document.querySelector('.reader').textContent)));
  t.check('and the voice is never handed one to read',
          await page.evaluate(
            () => !window.__spoken.some(s => /[+†<>[\]]/.test(s.text))),
          JSON.stringify((await page.evaluate(
            () => window.__spoken.map(s => s.text).filter(x => /[+†<>[\]]/.test(x)))).slice(0, 2)));

  const kept = await page.evaluate(() => {
    const said = window.__spoken.filter(s => s.text.indexOf('In this way he rises') === 0)[0];
    const v = Array.from(document.querySelectorAll('.reader .v')).filter(
      x => x.lastChild.textContent.trim().indexOf('In this way he rises') === 0)[0];
    return said && v ? [said.text.length, v.lastChild.textContent.trim().length] : null;
  });
  t.check('blanked rather than cut out, so the word highlight still lands',
          !!kept && kept[0] === kept[1], JSON.stringify(kept));

  /* ---- the gaps between the pieces ----
     Engines run one utterance straight into the next, which is what makes a
     chapter arrive as a wall of words whatever voice is reading it. */
  /* Every verse of this chapter ends in a full stop, so a piece that does not
     is a sentence that was cut for length — the one seam a pause would lie
     about. The two are told apart that way. */
  const gaps = await page.evaluate(() => {
    const s = window.__spoken, beats = [], seams = [];
    for (let i = 1; i < s.length; i++) {
      const g = Math.round(s[i].at - s[i - 1].at);
      (/[.!?]["'’”)\]]?\s*$/.test(s[i - 1].text) ? beats : seams).push(g);
    }
    return { first: Math.round(s[1].at - s[0].at), beats: beats, seams: seams };
  });
  t.check('the chapter heading is given a longer beat than a verse',
          gaps.first > 400 && gaps.first > Math.max.apply(null, gaps.beats.slice(1)),
          gaps.first + ' vs ' + JSON.stringify(gaps.beats.slice(1, 4)));
  t.check('and every finished sentence a beat of its own',
          gaps.beats.length > 4 && gaps.beats.slice(1).every(g => g > 150),
          JSON.stringify(gaps.beats.slice(0, 8)));
  t.check('while a sentence broken for length is put back without a gap',
          gaps.seams.length > 0 && gaps.seams.every(g => g < 150),
          JSON.stringify(gaps.seams));
  await page.close();

  /* ---- the other printings' apparatus ----
     The scans this volume recovers texts from bring an apparatus of their
     own, and a bigger one: Cooper and Maclean, Horner and Issaverdens all
     set their footnote references as superscript symbols, and the scanning
     engine read those as whatever glyph they resembled. There are 373 of
     them in the Testament of our Lord alone, and every one of them used to
     be spoken -- "registered trademark", "degrees", "section" -- about once
     every other sentence. */
  page = await open(ctx, '#/read/the-testament-of-our-lord/0', workingEngine(12));
  await page.locator('[data-listen]').click();
  await page.waitForFunction(() => window.__spoken.length >= 10);
  const MARKS = /[®©™°§•¢£¥$#%*«»^¬■|\\_&]/;
  t.check("the scan's footnote marks are still on the page",
          await page.evaluate(
            () => /[®»°¢]/.test(document.querySelector('.reader').textContent)));
  t.check('and none of them is handed to the voice',
          await page.evaluate(
            re => !window.__spoken.some(s => new RegExp(re).test(s.text)),
            MARKS.source),
          JSON.stringify((await page.evaluate(
            re => window.__spoken.map(s => s.text)
                    .filter(x => new RegExp(re).test(x)),
            MARKS.source)).slice(0, 2)));
  await page.close();

  /* ---- Charles's chapter numbers are numbers ----
     He prints them in the running text, so two hundred roman numerals stand
     inside the prose of Enoch, Jubilees and the Didascalia. An engine reads
     LXXVI as letters, and the reader hears the alphabet in the middle of a
     sentence about the winds. */
  page = await open(ctx, '#/read/jubilees/7', workingEngine(12));
  await page.locator('[data-listen]').click();
  await page.waitForFunction(() => window.__spoken.length >= 3);
  t.check('the roman numeral is still printed on the page',
          await page.evaluate(
            () => /\bVII\./.test(document.querySelector('.reader .v').textContent)));
  const numeral = await page.evaluate(
    () => window.__spoken.map(s => s.text)
            .filter(x => x.indexOf('A.M.') !== -1)[0] || '');
  t.check('but the voice is given the number',
          /A\.M\. 7\./.test(numeral) && numeral.indexOf('VII') === -1,
          JSON.stringify(numeral));
  t.check('padded back to its printed length, so the highlight still lands',
          await page.evaluate(said => {
            const printed = document.querySelector('.reader .v')
                              .lastChild.textContent;
            return printed.indexOf('VII.') === said.indexOf('7.') &&
                   printed.slice(0, said.length).length === said.length;
          }, numeral),
          JSON.stringify(numeral));
  await page.close();

  /* ---- the reading speed decides how long a piece may be ----
     Chrome's cut-off is fifteen seconds, which is a duration. A fixed
     character limit is only the same thing at one speed, and at the two slow
     speeds this player offers a 220-character piece runs well past it -- so
     the passage stops mid-sentence, which is the exact failure the cutting
     exists to prevent, at the setting a reader of the Psalms is most likely
     to be using. */
  const piecesAt = async (rate) => {
    const p = ctx.tally.watch(await ctx.browser.newPage(), 'rate:' + rate);
    await p.addInitScript(workingEngine(8));
    await p.addInitScript({ content:
      `try { localStorage.setItem('thebook:listen-rate', '${rate}'); } catch (e) {}` });
    await p.goto(ctx.base + '#/read/the-testament-of-issachar/0');
    await p.waitForSelector('.reader p');
    await p.locator('[data-listen]').click();
    await p.waitForFunction(() => window.__spoken.length >= 4);
    const out = await p.evaluate(() => ({
      longest: Math.max.apply(null, window.__spoken.map(s => s.text.length)),
      rate: window.__spoken[0].rate,
      whole: window.__spoken.slice(1).map(s => s.text).join('')
    }));
    const para = await p.evaluate(
      () => document.querySelector('.reader p').textContent);
    await p.close();
    return Object.assign(out, { para });
  };

  const slow = await piecesAt(0.7);
  const fast = await piecesAt(2);
  t.check('at 0.7x no piece is more than thirteen seconds of speech',
          slow.longest <= Math.round(13 * 15 * 0.7), slow.longest + ' characters');
  t.check('at 2x the pieces are allowed to be longer',
          fast.longest > slow.longest, slow.longest + ' -> ' + fast.longest);
  t.check('and at either speed the pieces still reassemble into the paragraph',
          slow.para.indexOf(slow.whole) === 0 && fast.para.indexOf(fast.whole) === 0);

  /* Changing the speed re-cuts the queue, so the index the reader is on
     stops meaning what it meant. The place has to survive that.

     The engine is deliberately slow here. What is under test is a pause that
     lands INSIDE an utterance -- that is when the index still points at a
     piece which is about to stop existing. At 40ms a piece finished before
     the pause arrived about half the time, nar.at had already advanced, and
     the check then compared two different verses and failed for a reason
     that had nothing to do with re-cutting. 600ms is longer than anything
     this test waits, so the pause is always mid-piece. */
  page = await open(ctx, '#/read/the-testament-of-issachar/0', workingEngine(600));
  await page.locator('[data-listen]').click();
  await page.waitForFunction(() => window.__spoken.length >= 2);
  await page.locator('.player-play').click();
  await page.waitForTimeout(settle);
  const wasAt = await page.evaluate(() => window.__spoken[window.__spoken.length - 1].text);
  await page.selectOption('select[aria-label="Reading speed"]', '0.7');
  await page.waitForTimeout(settle);
  await page.locator('.player-play').click();
  await page.waitForFunction(n => window.__spoken.length > n,
                             await page.evaluate(() => window.__spoken.length));
  const nowAt = await page.evaluate(() => window.__spoken[window.__spoken.length - 1].text);
  t.check('slowing down picks up where it was, not somewhere else in the chapter',
          wasAt.indexOf(nowAt.slice(0, 25)) === 0 || nowAt.indexOf(wasAt.slice(0, 25)) === 0,
          JSON.stringify([wasAt.slice(0, 40), nowAt.slice(0, 40)]));
  await page.close();

  /* ---- the silence between pieces ----
     The pace control is gone -- three settings for a preference almost nobody
     touched -- but restAfter() is not, and what it has to do is unchanged: a
     real break between lines, and none at all inside a sentence that was only
     broken because the engine cannot say it in one breath. The second is the
     one that matters. An engine drops its pitch at the end of every
     utterance, so a pause at the wrong seam is heard as a full stop that is
     not there, and a psalm comes apart. */
  {
    const p = ctx.tally.watch(await ctx.browser.newPage(), 'rests');
    await p.addInitScript(workingEngine(30));
    await p.goto(ctx.base + '#/read/psalms/22');
    await p.waitForSelector('.reader .v');
    await p.locator('[data-listen]').click();
    await p.waitForFunction(() => window.__spoken.length >= 6);
    const out = await p.evaluate(() => {
      const s = window.__spoken, beats = [], seams = [];
      for (let i = 1; i < s.length; i++) {
        const g = Math.round(s[i].at - s[i - 1].at);
        (/[.!?]["'\u2019\u201d)\]]?\s*$/.test(s[i - 1].text) ? beats : seams).push(g);
      }
      return { first: Math.round(s[1].at - s[0].at), beats, seams };
    });
    await p.close();

    t.check('a finished line is given a real silence after it',
            out.beats.length > 0 && out.beats.slice(1).every(g => g >= 150),
            JSON.stringify(out.beats.slice(0, 5)));
    t.check('and the chapter heading a longer one still',
            out.first > 400, out.first + 'ms');
    t.check('but a sentence broken only for length is put back without a gap',
            out.seams.length === 0 || out.seams.every(g => g < 150),
            JSON.stringify(out.seams.slice(0, 5)));
  }

  /* And broken where the sentence itself pauses, not in the middle of a
     clause: an engine drops its pitch at the end of every utterance, so the
     wrong break is heard as a full stop that is not there. */
  page = await open(ctx, '#/read/the-testament-of-issachar/0', workingEngine(15));
  await page.locator('[data-listen]').click();
  await page.waitForFunction(() => window.__spoken.length >= 6);
  t.check('a long passage is cut at its pauses, never mid-clause',
          await page.evaluate(() => window.__spoken.slice(1, -1).every(
            s => /[,;:—–)."!?’”]["'’”]?\s*$/.test(s.text))),
          JSON.stringify(await page.evaluate(
            () => window.__spoken.slice(1, -1).map(s => s.text.slice(-24)).slice(0, 3))));
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

  /* ---- stopping at the end of a chapter ----
     The sleep timer offered this too, among five other durations. It is gone;
     the continue toggle does the same job with one control instead of seven
     options, and it is the one people actually reached for. */
  page = await open(ctx, '#/read/amos/1', workingEngine(25));
  await page.locator('[data-listen]').click();
  await page.waitForSelector('.player:not([hidden])');
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
  /* No speechSynthesis at all, which is different from having one that
     cannot speak. An engine that exists and then fails is worth a sentence
     explaining itself -- that is the case above, and it still says so. A
     browser that never had the API has nothing to explain and nothing to
     offer, so it is offered nothing: no button, rather than a button that
     apologises. The distinction is the point, so both are checked. */
  page = await open(ctx, '#/read/amos/2', noEngine());
  await page.waitForTimeout(settle);
  t.check('a browser with no speech support is offered no control at all',
          await page.locator('[data-listen]').count() === 0,
          await page.locator('[data-listen]').count() + ' listen controls');
  t.check('and no player is left sitting there empty',
          await page.evaluate(
            () => !document.querySelector('.player') ||
                  document.querySelector('.player').hidden));
  await page.locator('.reader .v .vnum').first().click();
  t.check('and no read-aloud item in the verse menu',
          await page.locator('.vmenu button', { hasText: 'Read aloud' }).count() === 0);
  /* Named rather than counted: the menu grows, and a count here would fail
     for the wrong reason every time it does. What matters is that losing the
     speech engine costs the reader the read-aloud item and nothing else. */
  const stillThere = await page.locator('.vmenu button').allTextContents();
  t.check('while the rest of the verse menu still works',
          ['Save', 'link', 'citation', 'BibTeX', 'verse text']
            .every(want => stillThere.some(
              got => got.toLowerCase().indexOf(want.toLowerCase()) >= 0)),
          stillThere.length + ' items: ' + stillThere.join(' | '));
  await page.keyboard.press('Escape');
  await page.keyboard.press('l');
  await page.waitForTimeout(settle);
  t.check('and the l key does nothing at all', true);
  await page.close();
};
