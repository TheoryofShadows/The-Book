'use strict';

/* The diary.
 *
 * Every other thing this site keeps can be made again: a saved verse is one
 * tap, a theme is a click. An entry is a paragraph somebody wrote about their
 * own life, and if it goes it does not come back -- and they will not find
 * out until the day they come back for it.
 *
 * So the checks here are not really about the feature working. They are about
 * the two ways this page could betray somebody: losing what they wrote, and
 * saying it kept something it did not.
 */

const fullDisk = () => ({ content: `
  (() => {
    const real = window.localStorage;
    const dead = {
      getItem: k => real.getItem(k),
      removeItem: k => real.removeItem(k),
      key: i => real.key(i),
      clear: () => real.clear(),
      setItem: () => { const e = new Error('QuotaExceededError'); e.name = 'QuotaExceededError'; throw e; }
    };
    Object.defineProperty(dead, 'length', { get: () => real.length });
    Object.defineProperty(window, 'localStorage', { value: dead, configurable: true });
  })();
` });

const seed = (page, key, value) => page.addInitScript({ content:
  `try { localStorage.setItem(${JSON.stringify('thebook:' + key)}, ` +
  `${JSON.stringify(JSON.stringify(value))}); } catch (e) {}` });

const read = (page, key) => page.evaluate(
  k => JSON.parse(localStorage.getItem('thebook:' + k) || 'null'), key);

/* Fill the form on whatever page it is open on and submit it. */
async function write(page, { why = '', took = 'Something worth keeping.', mark } = {}) {
  await page.waitForSelector('.diary-form textarea#diary-took');
  if (why) await page.fill('.diary-form textarea#diary-why', why);
  await page.fill('.diary-form textarea#diary-took', took);
  if (mark) await page.check('#mark-' + mark);
  await page.click('.diary-form button[type=submit]');
  await page.waitForTimeout(200);
}

module.exports = async function diary(t, ctx) {

  /* The ordinary path, and the only one that is about the feature rather
     than about not losing it. */
  {
    const page = await ctx.browser.newPage();
    await page.goto(ctx.base + '#/diary');
    await write(page, { why: 'A hard week.', took: 'The valley is walked through, not sat in.', mark: 'stayed' });

    const stored = await read(page, 'diary');
    t.check('an entry is written to storage',
            Array.isArray(stored) && stored.length === 1,
            JSON.stringify(stored));
    t.check('and keeps what was typed in it',
            stored[0].took === 'The valley is walked through, not sat in.' &&
            stored[0].why === 'A hard week.' && stored[0].mark === 'stayed');

    await page.reload();
    await page.waitForSelector('.diary-entry');
    t.check('and survives a reload',
            (await page.locator('.diary-entry').count()) === 1);
    await page.close();
  }

  /* The one that matters most. A refused write must not be announced as a
     save, and the words must still be on screen -- because at that moment
     the textarea is the only copy in existence. */
  {
    const page = await ctx.browser.newPage();
    await page.addInitScript(fullDisk());
    await page.goto(ctx.base + '#/diary');
    const words = 'Written while the disk was full.';
    await write(page, { took: words });

    t.check('a refused write leaves the words in the box',
            (await page.inputValue('.diary-form textarea#diary-took')) === words,
            'the only copy there was');
    t.check('and says so rather than claiming it was kept',
            (await page.locator('.warn').count()) > 0);
    t.check('and does not show the entry as saved',
            (await page.locator('.diary-entry').count()) === 0);
    await page.close();
  }

  /* An entry is the reader's words. Anything in it that looks like markup is
     theirs too, and is shown, not run. */
  {
    const page = await ctx.browser.newPage();
    await page.goto(ctx.base + '#/diary');
    await write(page, { took: 'I wondered <b>why</b> <script>alert(1)</script>' });
    await page.reload();
    await page.waitForSelector('.diary-took');
    t.check('an entry containing markup is shown as text, not rendered',
            (await page.locator('.diary-took b').count()) === 0 &&
            (await page.locator('.diary-took').first().textContent()).includes('<b>why</b>'));
    await page.close();
  }

  /* The day an entry belongs to is the day it was evening for the person
     writing it, not the day it was in UTC. */
  {
    const page = await ctx.browser.newPage({ timezoneId: 'Pacific/Auckland' });
    await page.goto(ctx.base + '#/diary');
    await write(page, { took: 'Late here, yesterday in London.' });
    const stored = await read(page, 'diary');
    const local = await page.evaluate(() => {
      const d = new Date();
      const p = n => (n < 10 ? '0' : '') + n;
      return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
    });
    t.check('the day is the local one, not UTC',
            stored[0].day === local, stored[0].day + ' vs ' + local);
    await page.close();
  }

  /* A second copy, so that a main key lost or half-written is not the end of
     somebody's diary. */
  {
    const page = await ctx.browser.newPage();
    await page.goto(ctx.base + '#/diary');
    await write(page, { took: 'The copy that saves this.' });

    const shadow = await read(page, 'diary-copy');
    t.check('a second copy is kept beside the first',
            Array.isArray(shadow) && shadow.length === 1);

    /* Lose the main key the way a browser would, and reload. */
    await page.evaluate(() => localStorage.removeItem('thebook:diary'));
    await page.reload();
    await page.waitForSelector('.diary-entry');
    t.check('and the diary is read back from it when the first is gone',
            (await page.locator('.diary-took').first().textContent())
              .includes('The copy that saves this.'));
    await page.close();
  }

  /* An entry not about one chapter has to be allowed: some sittings are
     about the whole thing. */
  {
    const page = await ctx.browser.newPage();
    await page.goto(ctx.base + '#/diary');
    await write(page, { took: 'Not about any one chapter.' });
    const stored = await read(page, 'diary');
    t.check('an entry with no reference is allowed',
            stored.length === 1 && stored[0].ref === null);
    await page.close();
  }

  /* Written from the chapter, which is where somebody actually wants to
     write, with the reference already in it. */
  {
    const page = await ctx.browser.newPage();
    // Route indices are zero-based: this is the chapter the site
    // labels "Chapter 24". Which chapter it is does not matter here;
    // that the reference is carried does.
    await page.goto(ctx.base + '#/read/psalms/23');
    await page.waitForSelector('.reader-controls');
    await page.click('.reader-controls button:has-text("Write about this")');
    await write(page, { took: 'Read at the graveside.' });

    const stored = await read(page, 'diary');
    t.check('an entry written from a chapter carries that reference',
            stored.length === 1 && stored[0].ref &&
            stored[0].ref.work === 'psalms' && stored[0].ref.chapter === 23,
            JSON.stringify(stored[0] && stored[0].ref));

    await page.goto(ctx.base + '#/diary');
    await page.waitForSelector('.diary-entry');
    t.check('and the diary links back to the chapter',
            (await page.locator('.diary-ref a').first().getAttribute('href'))
              === '#/read/psalms/23');
    await page.close();
  }

  /* The way out. Both files, because they are for two different futures --
     one comes back into this site, one outlives it. */
  {
    const page = await ctx.browser.newPage();
    await seed(page, 'diary', [{
      id: '2026-01-02T10:00:00.000Z', day: '2026-01-02', ref: null,
      why: 'why it was read', took: 'what it gave', mark: 'settled'
    }]);
    await page.goto(ctx.base + '#/diary');
    await page.waitForSelector('.diary-keep');

    const [file] = await Promise.all([
      page.waitForEvent('download'),
      page.click('.diary-keep button:has-text("As plain text")')
    ]);
    const stream = await file.createReadStream();
    let text = '';
    for await (const chunk of stream) text += chunk;

    t.check('the plain-text copy contains the entry as written',
            text.includes('what it gave') && text.includes('why it was read'),
            text.slice(0, 120));
    t.check('and is named as a diary rather than a data file',
            /diary/.test(file.suggestedFilename()), file.suggestedFilename());
    await page.close();
  }

  /* The file the saved page writes carries the diary too. One file rather
     than two, so a reader who keeps a copy keeps all of it -- the diary
     being the half that cannot be written again. */
  {
    const page = await ctx.browser.newPage();
    await seed(page, 'diary', [{
      id: '2026-02-02T10:00:00.000Z', day: '2026-02-02', ref: null,
      why: '', took: 'in the backup', mark: null
    }]);
    await seed(page, 'saved', [{
      id: 'genesis/1/v1', kind: 'verse', work: 'genesis', workTitle: 'Genesis',
      chapter: 0, v: 1, t: 'In the beginning', label: 'Chapter 1', at: 1
    }]);
    await page.goto(ctx.base + '#/saved');
    await page.waitForSelector('button:has-text("Back up to a file")');

    const [file] = await Promise.all([
      page.waitForEvent('download'),
      page.click('button:has-text("Back up to a file")')
    ]);
    const stream = await file.createReadStream();
    let text = '';
    for await (const chunk of stream) text += chunk;
    const parsed = JSON.parse(text);

    t.check('the saved page writes a file carrying the diary as well',
            Array.isArray(parsed.diary) && parsed.diary.length === 1 &&
            parsed.diary[0].took === 'in the backup',
            JSON.stringify(parsed.diary));
    t.check('and says which version of the format it is',
            parsed.version === 2, String(parsed.version));
    await page.close();
  }

  /* Restoring a file whose only new content is diary entries must not be
     reported as nothing to add -- the case that would silently drop them. */
  {
    const page = await ctx.browser.newPage();
    const dir = require('fs').mkdtempSync(require('path').join(require('os').tmpdir(), 'bk-diary-'));
    ctx.cleanup.push(dir);
    const file = require('path').join(dir, 'diary-only.json');
    require('fs').writeFileSync(file, JSON.stringify({
      format: 'thebook.saved', version: 2, exported: new Date().toISOString(),
      items: [],
      diary: [{ id: '2026-03-03T10:00:00.000Z', day: '2026-03-03', ref: null,
                why: '', took: 'restored from a file', mark: null }]
    }));

    await page.goto(ctx.base + '#/saved');
    await page.waitForSelector('input[type=file]');
    await page.locator('input[type=file]').setInputFiles(file);
    await page.waitForTimeout(400);

    const stored = await read(page, 'diary');
    t.check('a backup with only diary entries still restores them',
            Array.isArray(stored) && stored.length === 1 &&
            stored[0].took === 'restored from a file',
            JSON.stringify(stored));
    await page.close();
  }

  /* Restoring twice adds each entry once, and never replaces what is already
     written. */
  {
    const page = await ctx.browser.newPage();
    const dir = require('fs').mkdtempSync(require('path').join(require('os').tmpdir(), 'bk-diary2-'));
    ctx.cleanup.push(dir);
    const file = require('path').join(dir, 'twice.json');
    require('fs').writeFileSync(file, JSON.stringify({
      format: 'thebook.saved', version: 2, exported: new Date().toISOString(),
      items: [],
      diary: [{ id: '2026-04-04T10:00:00.000Z', day: '2026-04-04', ref: null,
                why: '', took: 'from the file', mark: null }]
    }));
    await seed(page, 'diary', [{
      id: '2026-05-05T10:00:00.000Z', day: '2026-05-05', ref: null,
      why: '', took: 'already here', mark: null
    }]);

    await page.goto(ctx.base + '#/saved');
    await page.waitForSelector('input[type=file]');
    await page.locator('input[type=file]').setInputFiles(file);
    await page.waitForTimeout(400);
    await page.locator('input[type=file]').setInputFiles(file);
    await page.waitForTimeout(400);

    const stored = await read(page, 'diary');
    const texts = (stored || []).map(e => e.took).sort();
    t.check('restoring twice adds each entry once and keeps what was there',
            stored.length === 2 &&
            texts[0] === 'already here' && texts[1] === 'from the file',
            JSON.stringify(texts));
    await page.close();
  }

  /* A version 1 file predates the diary. It must restore its verses and
     leave the diary alone rather than emptying it. */
  {
    const page = await ctx.browser.newPage();
    const dir = require('fs').mkdtempSync(require('path').join(require('os').tmpdir(), 'bk-v1-'));
    ctx.cleanup.push(dir);
    const file = require('path').join(dir, 'v1.json');
    require('fs').writeFileSync(file, JSON.stringify({
      format: 'thebook.saved', version: 1, exported: new Date().toISOString(),
      items: [{ id: 'genesis/1/v1', kind: 'verse', work: 'genesis',
                workTitle: 'Genesis', chapter: 1, v: 1, at: 1 }]
    }));
    await seed(page, 'diary', [{
      id: '2026-06-06T10:00:00.000Z', day: '2026-06-06', ref: null,
      why: '', took: 'must survive a v1 restore', mark: null
    }]);

    await page.goto(ctx.base + '#/saved');
    await page.waitForSelector('input[type=file]');
    await page.locator('input[type=file]').setInputFiles(file);
    await page.waitForTimeout(400);

    const stored = await read(page, 'diary');
    t.check('a version 1 backup restores without touching the diary',
            Array.isArray(stored) && stored.length === 1 &&
            stored[0].took === 'must survive a v1 restore',
            JSON.stringify(stored));
    await page.close();
  }

  /* The page says where the entries live. A reader deciding whether to write
     something real here is owed that before they write it, not after they
     lose it. */
  {
    const page = await ctx.browser.newPage();
    await page.goto(ctx.base + '#/diary');
    await page.waitForSelector('.diary-where');
    const said = (await page.locator('.diary-where').textContent()) || '';
    t.check('the page says the entries are kept in this browser',
            /this browser/i.test(said), said.slice(0, 90));
    t.check('and does not promise they cannot be lost',
            !/never|forever|permanent|always safe/i.test(said), said.slice(0, 90));
    await page.close();
  }

  /* No streak, no score, no verdict on the reading. */
  {
    const page = await ctx.browser.newPage();
    await seed(page, 'diary', [
      { id: '2026-07-01T10:00:00.000Z', day: '2026-07-01', ref: null, why: '', took: 'one', mark: null },
      { id: '2026-07-09T10:00:00.000Z', day: '2026-07-09', ref: null, why: '', took: 'two', mark: null }
    ]);
    await page.goto(ctx.base + '#/diary');
    await page.waitForSelector('.diary-shape');
    const shape = (await page.locator('.diary-shape').textContent()) || '';
    t.check('what it says about the reading is a count and a span',
            /2 sittings/.test(shape) && /2 days/.test(shape), shape);
    t.check('and it is not a streak',
            !/streak|in a row|day streak|keep it up|goal/i.test(shape), shape);
    await page.close();
  }

};
