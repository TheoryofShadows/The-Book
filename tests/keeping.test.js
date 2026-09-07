'use strict';

/* What the reader keeps.
 *
 * Everything here is stored in the browser and nowhere else, so a bug in it
 * is not a rendering fault the reader can reload past -- it is their notes,
 * gone, with no copy anywhere. The single check this grew out of saved one
 * verse and looked for it afterwards.
 */

/* Storage that refuses to write, which is what Safari private browsing does
   and what any browser does once the site's quota is spent. Installed before
   the page's own scripts, so the site sees it from the first line it runs. */
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

/* The first item in a verse menu is the save toggle. Its label says which
   way it will go -- "Save this verse" or "Saved - tap to remove" -- so the
   toggle is reached by position and the label is what gets asserted. */
async function verseToggle(page, base, route) {
  await page.goto(base + route);
  await page.waitForSelector('.reader .v');
  await page.locator('.reader .v .vnum').first().click();
  await page.waitForSelector('.vmenu button');
  const button = page.locator('.vmenu button').first();
  const label = (await button.textContent()) || '';
  await button.click();
  await page.keyboard.press('Escape');
  return label;
}

const saveFirstVerse = verseToggle;

module.exports = async function keeping(t, ctx) {

  /* ---- saving, unsaving, and the note ---- */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'saved');
    await saveFirstVerse(page, ctx.base, '#/read/amos/2');
    await saveFirstVerse(page, ctx.base, '#/read/hosea/1');

    await page.goto(ctx.base + '#/saved');
    await page.waitForSelector('.saved-row');
    t.check('two saved verses are both there',
            await page.locator('.saved-row').count() === 2);

    t.check('the newest is first',
            /hosea/i.test(await page.locator('.saved-row a').first().textContent()));

    t.check('the verse text is kept, not just the reference',
            (await page.locator('.saved-row blockquote').first().textContent() || '')
              .trim().length > 20);

    /* A note is the reader's own writing and the only thing here they cannot
       reconstruct from the volume. */
    await page.locator('.saved-note').first().fill('my note about this verse');
    await page.locator('.saved-note').first().blur();
    await page.waitForTimeout(200);
    await page.reload();
    await page.waitForSelector('.saved-row');
    t.check('a note survives a reload',
            await page.locator('.saved-note').first().inputValue() ===
            'my note about this verse');

    await page.locator('.saved-row', { hasText: 'Hosea' })
              .locator('button', { hasText: 'Remove' }).click();
    await page.waitForTimeout(150);
    t.check('removing one takes it off the page at once',
            await page.locator('.saved-row').count() === 1);

    await page.reload();
    await page.waitForSelector('.saved-row');
    t.check('and it stays removed',
            await page.locator('.saved-row').count() === 1 &&
            /amos/i.test(await page.locator('.saved-row a').first().textContent()));

    t.check('the other one kept its note',
            await page.locator('.saved-note').first().inputValue() === '');

    /* Saving the same verse twice is unsaving it, not a second copy -- and
       the menu has to say which of the two it is about to do. */
    const label = await verseToggle(page, ctx.base, '#/read/amos/2');
    t.check('the menu offers to remove a verse that is already saved',
            /tap to remove/i.test(label), label.trim());

    await page.goto(ctx.base + '#/saved');
    await page.waitForTimeout(300);
    t.check('and it is removed rather than saved a second time',
            await page.locator('.saved-row').count() === 0);

    await page.close();
  }

  /* ---- the empty state says where things are kept ---- */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'saved-empty');
    await page.goto(ctx.base + '#/saved');
    await page.waitForSelector('.empty');
    const text = await page.textContent('.empty');
    t.check('with nothing saved, the page says so and says where it would be kept',
            /nothing sent anywhere|browser only|nobody else/i.test(text),
            text.slice(0, 50));
    await page.close();
  }

  /* ---- the migration from the old key ----
     Older builds saved under "bookmarks". This runs once, silently, over
     data the reader cannot see and has no copy of. */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'migration');
    await seed(page, 'bookmarks', [
      { at: 'amos/2', work: 'Amos', label: 'Chapter 3' },
      { at: 'hosea/1', work: 'Hosea', label: 'Chapter 2' }
    ]);
    await page.goto(ctx.base + '#/saved');
    await page.waitForSelector('.saved-row');
    t.check('bookmarks from an older build are carried over, not lost',
            await page.locator('.saved-row').count() === 2);

    const first = await page.locator('.saved-row a').first().textContent();
    t.check('and they still point at the chapter they were made on',
            /amos/i.test(first) && /chapter 3/i.test(first), first);

    const href = await page.locator('.saved-row a').first().getAttribute('href');
    t.check('the link resolves to a real chapter',
            href === '#/read/amos/2', href);

    await page.reload();
    await page.waitForSelector('.saved-row');
    t.check('the migration does not run twice and double everything',
            await page.locator('.saved-row').count() === 2);
    await page.close();
  }

  /* ---- storage that refuses to write ----
     The reader was told "Saved", and it was not saved. */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'quota');
    await page.addInitScript(fullDisk());
    await page.goto(ctx.base + '#/read/amos/2');
    await page.waitForSelector('.reader .v');
    t.check('the reader still opens when nothing can be stored', true);

    await page.locator('.reader .v .vnum').first().click();
    await page.locator('.vmenu button', { hasText: 'Save this verse' }).click();
    await page.waitForTimeout(250);

    const live = (await page.locator('[role=status]').textContent().catch(() => '')) || '';
    t.check('a save that could not be written says so rather than saying "Saved"',
            /not letting the page store|not kept/i.test(live) && !/^Saved$/.test(live.trim()),
            live.slice(0, 60));

    await page.keyboard.press('Escape');
    await page.goto(ctx.base + '#/saved');
    await page.waitForTimeout(300);
    t.check('and the saved page warns instead of looking merely empty',
            /not letting the page store/i.test(await page.textContent('.wrap')));
    await page.close();
  }

  /* ---- a failed migration must not destroy the old copy ----
     Clearing the old key after a failed write threw the reader's bookmarks
     away to save nothing at all. */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'migration-quota');
    await page.addInitScript({ content:
      `try { localStorage.setItem('thebook:bookmarks', ` +
      `'[{"at":"amos/2","work":"Amos","label":"Chapter 3"}]'); } catch (e) {}` });
    await page.addInitScript(fullDisk());
    await page.goto(ctx.base + '#/saved');
    await page.waitForTimeout(400);
    const stillThere = await page.evaluate(
      () => JSON.parse(localStorage.getItem('thebook:bookmarks') || '[]').length);
    t.check('bookmarks are not cleared when the migration could not write',
            stillThere === 1, stillThere + ' left');
    await page.close();
  }

  /* ---- reading position ---- */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'resume');
    await page.goto(ctx.base + '#/read/amos/2');
    await page.waitForSelector('.reader .v');
    await page.goto(ctx.base + '#/');
    await page.waitForSelector('h1');
    const resume = page.locator('#resume');
    t.check('the last chapter read is offered again on the way back in',
            await resume.isVisible() &&
            /amos/i.test(await resume.textContent()),
            (await resume.textContent() || '').trim());

    await resume.click();
    await page.waitForSelector('.reader .v');
    t.check('and it goes to that chapter',
            page.url().indexOf('#/read/amos/2') > 0, page.url().slice(-24));
    await page.close();
  }

  /* ---- settings the reader chose ---- */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'theme');
    await page.goto(ctx.base + '#/');
    await page.waitForSelector('#theme');
    const before = await page.getAttribute('html', 'data-theme');
    await page.locator('#theme').click();
    const after = await page.getAttribute('html', 'data-theme');
    t.check('the theme button changes the theme', before !== after,
            before + ' -> ' + after);

    await page.reload();
    await page.waitForSelector('#theme');
    t.check('and the choice survives a reload',
            await page.getAttribute('html', 'data-theme') === after);

    /* Three states, and back to where it started. */
    await page.locator('#theme').click();
    await page.locator('#theme').click();
    t.check('the three themes cycle back round',
            await page.getAttribute('html', 'data-theme') === before);
    await page.close();
  }

  /* ---- the backup, and surviving a browser that clears itself ----

     Saved verses are in local storage and nowhere else, and local storage is
     not permanent: Safari drops a site's after about a week without a visit,
     and a cleared site, a new phone or a reinstall do the same thing on any
     browser. None of them warn anybody. The three copy buttons beside these
     are prose for a document and cannot be read back, so the file is the
     only thing between an eviction and somebody's notes.

     Which makes the round trip the check that matters. Writing a file that
     cannot be restored would look exactly like this working. */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'backup');
    await saveFirstVerse(page, ctx.base, '#/read/amos/2');
    await saveFirstVerse(page, ctx.base, '#/read/hosea/1');
    await page.goto(ctx.base + '#/saved');
    await page.waitForSelector('.saved-row');

    /* A note, so the check is that the reader's own words come back and not
       merely that two rows do. */
    const note = page.locator('.saved-note').first();
    await note.fill('the thing I was thinking');
    await note.blur();

    const before = await page.evaluate(() =>
      JSON.parse(localStorage.getItem('thebook:saved')).length);

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.locator('button:has-text("Back up to a file")').click()
    ]);
    t.check('the backup is offered as a file, named for the day',
            /^the-book-saved-\d{4}-\d{2}-\d{2}\.json$/.test(download.suggestedFilename()),
            download.suggestedFilename());

    const file = await download.path();
    const text = require('fs').readFileSync(file, 'utf8');
    let parsed = null;
    try { parsed = JSON.parse(text); } catch (e) { /* reported next */ }
    /* Version 2 since the file started carrying the study record as well as
       the verses. A reader who has marked off two hundred chapters and kept
       a streak for a month has more to lose than their bookmarks, and all of
       it sits in the same storage the same browser can drop. */
    t.check('and it is JSON that says what it is',
            !!parsed && parsed.format === 'thebook.saved' && parsed.version === 2,
            parsed ? parsed.format + ' v' + parsed.version : 'did not parse');

    t.check('and carries the study record, not only the verses',
            !!parsed && !!parsed.read && Array.isArray(parsed.days) &&
            !!parsed.review,
            parsed ? Object.keys(parsed).join(' ') : 'did not parse');
    t.check('and holds everything that was saved',
            !!parsed && parsed.items.length === before,
            parsed ? parsed.items.length + ' of ' + before : 'none');
    t.check('including the note, which is the part nothing else can rebuild',
            /the thing I was thinking/.test(text));

    /* The eviction, done to the browser rather than waited for. Reloaded
       rather than navigated: the page is already at #/saved, and going to
       the hash it is on is not a navigation, so nothing would re-render and
       the check would be reading the rows from before the clear. */
    await page.evaluate(() => localStorage.removeItem('thebook:saved'));
    await page.reload();
    await page.waitForSelector('.empty');
    t.check('with the storage cleared, the saved page is empty',
            (await page.locator('.saved-row').count()) === 0);

    await page.locator('input[type=file]').setInputFiles(file);
    await page.waitForSelector('.saved-row');
    t.check('restoring the file brings the verses back',
            (await page.locator('.saved-row').count()) === before,
            (await page.locator('.saved-row').count()) + ' of ' + before);
    t.check('and brings the note back with them',
            (await page.locator('.saved-note').first().inputValue() || '')
              .indexOf('the thing I was thinking') !== -1);

    /* Restoring the same file again must not double everything: somebody
       who is not sure whether it worked will press it twice. */
    await page.locator('input[type=file]').setInputFiles(file);
    await page.waitForTimeout(300);
    t.check('restoring the same file twice adds nothing the second time',
            (await page.locator('.saved-row').count()) === before,
            (await page.locator('.saved-row').count()) + ' of ' + before);

    await page.close();
  }

  /* A file that is not a backup has to be refused rather than obeyed: this
     is a file picker pointed at a reader's own disk, and the shapes it will
     be handed include every other JSON file they have. */
  {
    const page = await ctx.browser.newPage();
    const dir = require('fs').mkdtempSync(require('path').join(require('os').tmpdir(), 'bk-'));
    ctx.cleanup.push(dir);
    const junk = require('path').join(dir, 'not-a-backup.json');
    const broken = require('path').join(dir, 'broken.json');
    require('fs').writeFileSync(junk, JSON.stringify({ hello: 'world' }));
    require('fs').writeFileSync(broken, '{ this is not json');

    await saveFirstVerse(page, ctx.base, '#/read/amos/2');
    await page.goto(ctx.base + '#/saved');
    await page.waitForSelector('.saved-row');

    for (const [what, file] of [['a JSON file that is not a backup', junk],
                                ['a file that is not JSON at all', broken]]) {
      await page.locator('input[type=file]').setInputFiles(file);
      await page.waitForTimeout(250);
      t.check(what + ' is refused rather than obeyed',
              (await page.locator('.saved-row').count()) === 1,
              (await page.locator('.saved-row').count()) + ' row(s) left');
    }
    t.check('and the saved verse is still there afterwards',
            (await page.locator('.saved-row').count()) === 1);
    await page.close();
  }

};
