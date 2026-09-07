'use strict';

/* Studying it: progress, recall, and the streak.
 *
 * All three live in localStorage beside the saved verses, which means a bug
 * in any of them is not a rendering fault the reader can reload past -- it
 * is a month of their work, wrong or gone.
 *
 * The first check here exists because of a real one. The progress key was
 * built by a function called chapterKey(workId, idx), and the audio player
 * already had a chapterKey(ctx) further down the same file. Function
 * declarations hoist, so the later one won, every call got a string where it
 * wanted a context object, and every chapter anybody marked was filed under
 * "undefined/undefined". The count read 1 no matter how much you read. It
 * looked completely fine until two different chapters were marked and the
 * keys compared, which is what 'two chapters make two records' does.
 */

/* Wipe between blocks, so one block's streak is not another's fixture. */
async function fresh(page, base) {
  await page.goto(base);
  await page.evaluate(() => {
    ['read', 'days', 'review', 'saved', 'last', 'bookmarks']
      .forEach(k => localStorage.removeItem('thebook:' + k));
  });
}

const readRecord = page =>
  page.evaluate(() => JSON.parse(localStorage.getItem('thebook:read') || '{}'));

/* Going to a hash the page is already rendering does not re-render it, so
   waiting for the button alone can hand back the previous chapter's. Wait
   for the URL and the button together. */
async function openChapter(page, base, work, idx) {
  await page.goto(base + '#/read/' + work + '/' + idx);
  await page.waitForFunction(
    want => !!document.querySelector('.done-btn') && location.hash === want,
    '#/read/' + work + '/' + idx);
}

async function markChapter(page, base, work, idx) {
  await openChapter(page, base, work, idx);
  await page.click('.done-btn');
  await page.waitForTimeout(120);
}

/* A run of consecutive days ending today, which is what a streak is. */
function daysBack(n) {
  const out = [];
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    out.push(d.getFullYear() + '-' +
             ('0' + (d.getMonth() + 1)).slice(-2) + '-' +
             ('0' + d.getDate()).slice(-2));
  }
  return out;
}

module.exports = async function study(t, ctx) {

  /* ---- marking a chapter off ---- */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'study-progress');
    await fresh(page, ctx.base);

    await openChapter(page, ctx.base, 'mark', 0);
    t.check('a chapter offers to be marked read',
            /Mark as read/.test(await page.textContent('.done-btn')),
            await page.textContent('.done-btn'));

    await page.click('.done-btn');
    await page.waitForTimeout(150);
    t.check('and says so once it is',
            /Read/.test(await page.textContent('.done-btn')) &&
            await page.getAttribute('.done-btn', 'aria-pressed') === 'true',
            await page.textContent('.done-btn'));

    /* The regression this suite was written for. */
    await markChapter(page, ctx.base, 'mark', 1);
    let rec = await readRecord(page);
    t.check('two chapters make two records, under their own names',
            Object.keys(rec).sort().join() === 'mark/0,mark/1',
            Object.keys(rec).join(' '));

    t.check('and none of them is filed under undefined',
            !Object.keys(rec).some(k => /undefined/.test(k)),
            Object.keys(rec).join(' '));

    await markChapter(page, ctx.base, 'amos', 0);
    rec = await readRecord(page);
    t.check('a chapter in another work is its own record too',
            Object.keys(rec).length === 3 && !!rec['amos/0'],
            Object.keys(rec).join(' '));

    /* Unmarking has to actually remove it, not write a falsy value that
       still counts as a key. */
    await openChapter(page, ctx.base, 'mark', 0);
    t.check('coming back to a marked chapter shows it marked',
            /tap to unmark/.test(await page.textContent('.done-btn')),
            await page.textContent('.done-btn'));
    await page.click('.done-btn');
    await page.waitForTimeout(150);
    rec = await readRecord(page);
    t.check('unmarking removes the record rather than emptying it',
            Object.keys(rec).sort().join() === 'amos/0,mark/1',
            Object.keys(rec).join(' '));

    /* The strip of chapter numbers is the one place progress is visible
       while reading, and it has to survive a reload. */
    await markChapter(page, ctx.base, 'mark', 2);
    await openChapter(page, ctx.base, 'mark', 5);
    t.check('the chapter strip marks what has been read',
            await page.locator('.chapter-strip a.is-done').count() === 2,
            await page.locator('.chapter-strip a.is-done').count() + ' marked');

    t.check('and says so in words, not only in a colour',
            (await page.$$eval('.chapter-strip a.is-done',
                               as => as.map(a => a.getAttribute('title'))))
              .every(s => / — read$/.test(s)),
            (await page.$$eval('.chapter-strip a.is-done',
                               as => as.map(a => a.getAttribute('title')))).join(' | '));

    await page.close();
  }

  /* ---- the study page ---- */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'study-page');
    await fresh(page, ctx.base);

    /* A first visit is not a report card: three empty measures would tell
       somebody who has just arrived that they are already behind. */
    await page.goto(ctx.base + '#/study');
    await page.waitForSelector('h1');
    t.check('a first visit offers a way in rather than a row of noughts',
            /Nothing here yet/.test(await page.textContent('.lede')) &&
            await page.locator('.stat').count() === 0,
            await page.locator('.stat').count() + ' stats shown');

    await markChapter(page, ctx.base, 'mark', 0);
    await markChapter(page, ctx.base, 'mark', 1);
    await markChapter(page, ctx.base, 'mark', 2);

    await page.goto(ctx.base + '#/study');
    await page.waitForSelector('.stat');
    const stats = await page.$$eval('.stat', ds => ds.map(d => d.textContent.trim()));
    t.check('the study page counts what has been read',
            /^3chapters read/.test(stats[0]), stats.join(' | '));

    /* Per-work progress is the number a reader actually holds: nobody is
       tracking 2,537 chapters, they are tracking Mark. */
    const rows = await page.$$eval('.progress-row',
                                   rs => rs.map(r => r.textContent.replace(/\s+/g, ' ').trim()));
    t.check('and how far through the work they are part-way into',
            rows.length === 1 && /Mark/.test(rows[0]) && /3 of 16/.test(rows[0]),
            rows.join(' | ') || '(no rows)');

    t.check('the bar is labelled, because a bar is a picture of a number',
            /3 of 16/.test(await page.getAttribute('.progress-row .meter', 'aria-label')),
            await page.getAttribute('.progress-row .meter', 'aria-label'));

    /* A finished work is counted, not listed: forty rows of trophies is
       forty rows between the reader and the next thing. */
    for (let i = 3; i < 16; i++) await markChapter(page, ctx.base, 'mark', i);
    await page.goto(ctx.base + '#/study');
    await page.waitForSelector('.stat');
    t.check('a work read all the way through leaves the part-way list',
            await page.locator('.progress-row').count() === 0 &&
            /1 work read all the way through/.test(await page.textContent('.wrap')),
            await page.locator('.progress-row').count() + ' rows left');

    await page.close();
  }

  /* ---- the streak ---- */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'study-streak');
    await fresh(page, ctx.base);

    await markChapter(page, ctx.base, 'amos', 0);
    await page.goto(ctx.base + '#/study');
    await page.waitForSelector('.stat');
    let stats = await page.$$eval('.stat', ds => ds.map(d => d.textContent.trim()));
    t.check('finishing something today starts a streak of one',
            /^1day in a row/.test(stats[2]), stats[2]);

    /* Counted back from yesterday when nothing has been done yet today --
       otherwise forty days reads as nothing at the moment it is most worth
       showing. */
    await page.evaluate(d => {
      localStorage.setItem('thebook:days', JSON.stringify(d));
    }, daysBack(6).slice(0, 5));
    await page.goto(ctx.base + '#/');
    await page.goto(ctx.base + '#/study');
    await page.waitForSelector('.stat');
    stats = await page.$$eval('.stat', ds => ds.map(d => d.textContent.trim()));
    t.check('a streak counts back from yesterday before today is worked',
            /^5days in a row/.test(stats[2]), stats[2]);

    /* And a gap ends it rather than being counted through. */
    await page.evaluate(d => {
      localStorage.setItem('thebook:days', JSON.stringify(d));
    }, daysBack(10).filter((_, i) => i !== 7));
    await page.goto(ctx.base + '#/');
    await page.goto(ctx.base + '#/study');
    await page.waitForSelector('.stat');
    stats = await page.$$eval('.stat', ds => ds.map(d => d.textContent.trim()));
    t.check('and a missed day ends it rather than being counted through',
            /^2days in a row/.test(stats[2]), stats[2]);

    t.check('a lapsed streak is reported without scolding',
            !/failed|lost|broke your/i.test(await page.textContent('.wrap')));

    await page.close();
  }

  /* ---- recall ---- */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'study-recall');
    await fresh(page, ctx.base);

    await page.goto(ctx.base + '#/review');
    await page.waitForSelector('.lede');
    t.check('recall with nothing saved says how to start, not that it is empty',
            /Nothing saved yet/.test(await page.textContent('.lede')),
            (await page.textContent('.lede')).slice(0, 50));

    await page.evaluate(() => {
      localStorage.setItem('thebook:saved', JSON.stringify([
        { id: 'amos/4/v24', kind: 'verse', work: 'amos', workTitle: 'AMOS',
          chapter: 4, label: 'Chapter 5', v: 24, at: Date.now(),
          t: 'But let justice roll on like rivers.' },
        { id: 'mark/0/v1', kind: 'verse', work: 'mark', workTitle: 'MARK',
          chapter: 0, label: 'Chapter 1', v: 1, at: Date.now(),
          t: 'The beginning of the Good News.' },
        /* A saved chapter has nothing to recall about it except that it was
           saved, and must not turn up as a card with no text on it. */
        { id: 'hosea/0', kind: 'chapter', work: 'hosea', workTitle: 'HOSEA',
          chapter: 0, label: 'Chapter 1', at: Date.now() }
      ]));
    });

    await page.goto(ctx.base + '#/');
    await page.goto(ctx.base + '#/review');
    await page.waitForSelector('.recall-ref');
    t.check('a saved verse comes round, and a saved chapter does not',
            /Verse 1 of 2/.test(await page.textContent('.wrap > .muted')),
            await page.textContent('.wrap > .muted'));

    t.check('the reference comes first and the words are turned over',
            await page.locator('.recall-text').isHidden() &&
            (await page.textContent('.recall-ref')).length > 5,
            await page.textContent('.recall-ref'));

    await page.locator('.card button', { hasText: 'Turn it over' }).click();
    await page.waitForTimeout(200);
    t.check('turning it over shows the verse',
            await page.locator('.recall-text').isVisible());

    await page.locator('.card button', { hasText: 'I had it' }).click();
    await page.waitForTimeout(250);

    /* Leitner: recalled goes a box out, failed comes straight back. The
       intervals are the whole schedule, so they are what is checked. */
    await page.locator('.card button', { hasText: 'Turn it over' }).click();
    await page.waitForTimeout(150);
    await page.locator('.card button', { hasText: 'Not quite' }).click();
    await page.waitForTimeout(250);

    const state = await page.evaluate(() =>
      JSON.parse(localStorage.getItem('thebook:review') || '{}'));
    const boxes = Object.keys(state).map(k => state[k].box).sort();
    t.check('recalling moves a verse out a box and failing sends it back',
            boxes.join() === '0,1', JSON.stringify(boxes));

    const ahead = Object.keys(state)
      .map(k => state[k].due - Date.now()).sort((a, b) => a - b);
    t.check('a failed verse comes back in minutes, a recalled one in a day',
            ahead[0] > 60000 && ahead[0] < 3600000 &&
            ahead[1] > 20 * 3600000 && ahead[1] < 26 * 3600000,
            Math.round(ahead[0] / 60000) + ' min and ' +
            Math.round(ahead[1] / 3600000) + ' hours');

    t.check('and the round ends by saying how it went',
            /came back to you/.test(await page.textContent('.card')),
            (await page.textContent('.card')).replace(/\s+/g, ' ').slice(0, 60));

    /* Nothing is due now, and saying "nothing due" is a different sentence
       from "nothing saved" -- the reader is in a different position. */
    await page.goto(ctx.base + '#/');
    await page.goto(ctx.base + '#/review');
    await page.waitForSelector('.lede');
    t.check('with everything freshly seen it says so, not that nothing is saved',
            /Nothing is due/.test(await page.textContent('.lede')),
            (await page.textContent('.lede')).slice(0, 50));

    /* Sitting down to recall is doing the work, so it counts for the day. */
    const days = await page.evaluate(() =>
      JSON.parse(localStorage.getItem('thebook:days') || '[]'));
    t.check('a recall session counts towards the day, like a chapter does',
            days.length === 1, JSON.stringify(days));

    await page.close();
  }

  /* ---- the backup carries the study, not only the verses ---- */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'study-backup');
    await fresh(page, ctx.base);
    await markChapter(page, ctx.base, 'amos', 0);
    await markChapter(page, ctx.base, 'amos', 1);

    await page.goto(ctx.base + '#/saved');
    await page.waitForSelector('h1');
    const dump = await page.evaluate(() => {
      /* The page builds the file when the button is pressed; this asks the
         same question of the same storage, which is what goes into it. */
      return {
        read: JSON.parse(localStorage.getItem('thebook:read') || '{}'),
        days: JSON.parse(localStorage.getItem('thebook:days') || '[]')
      };
    });
    t.check('there is a study record to lose in the first place',
            Object.keys(dump.read).length === 2 && dump.days.length === 1);

    /* Restoring a version-2 file onto a browser that has its own progress
       must add rather than choose one of the two to throw away. */
    await page.evaluate(() => {
      localStorage.setItem('thebook:read', JSON.stringify({ 'hosea/0': 1 }));
      localStorage.setItem('thebook:days', JSON.stringify(['2001-01-01']));
    });
    const file = JSON.stringify({
      format: 'thebook.saved', version: 2, exported: new Date().toISOString(),
      items: [{ id: 'amos/4/v24', kind: 'verse', work: 'amos', workTitle: 'AMOS',
                chapter: 4, label: 'Chapter 5', v: 24, at: 1, t: 'Justice.' }],
      read: { 'amos/0': 1, 'amos/1': 1 },
      days: ['2002-02-02'],
      review: { 'amos/4/v24': { box: 3, seen: 4, last: 9, due: 9 } }
    });
    await page.setInputFiles('input[type=file]', {
      name: 'backup.json', mimeType: 'application/json', buffer: Buffer.from(file)
    });
    await page.waitForTimeout(500);

    const after = await page.evaluate(() => ({
      read: Object.keys(JSON.parse(localStorage.getItem('thebook:read') || '{}')).sort(),
      days: JSON.parse(localStorage.getItem('thebook:days') || '[]').sort(),
      review: JSON.parse(localStorage.getItem('thebook:review') || '{}')
    }));
    t.check('restoring merges the chapters read rather than replacing them',
            after.read.join() === 'amos/0,amos/1,hosea/0', after.read.join(' '));
    t.check('and the days studied',
            after.days.join() === '2001-01-01,2002-02-02', after.days.join(' '));
    t.check('and the recall schedule',
            (after.review['amos/4/v24'] || {}).box === 3,
            JSON.stringify(after.review));

    await page.close();
  }

  /* ---- a browser that will not store anything ---- */
  {
    /* Private browsing refuses every write. The reader must be told rather
       than left tapping a button that silently does nothing. */
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'study-nostore');
    await page.addInitScript(() => {
      const real = window.localStorage;
      const dead = {
        getItem: k => real.getItem(k),
        removeItem: k => real.removeItem(k),
        key: i => real.key(i),
        clear: () => real.clear(),
        setItem: () => { const e = new Error('QuotaExceededError');
                         e.name = 'QuotaExceededError'; throw e; }
      };
      Object.defineProperty(dead, 'length', { get: () => real.length });
      Object.defineProperty(window, 'localStorage', { value: dead, configurable: true });
    });
    await openChapter(page, ctx.base, 'amos', 0);
    await page.click('.done-btn');
    await page.waitForTimeout(200);
    t.check('a refused write leaves the button honest rather than pretending',
            /Mark as read/.test(await page.textContent('.done-btn')),
            await page.textContent('.done-btn'));
    /* The live region is where a screen reader is told, and it is the only
       place this can be said: the button has gone back to how it was, which
       is honest and is not an explanation. */
    await page.waitForFunction(
      () => /not letting the page store/i.test(
        (document.querySelector('[role=status]') || {}).textContent || ''),
      null, { timeout: 5000 }).catch(() => {});
    const spoken = await page.textContent('[role=status]') || '';
    t.check('and the page says so out loud',
            /not letting the page store/i.test(spoken), spoken.slice(0, 60));
    await page.close();
  }
};
