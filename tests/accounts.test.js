'use strict';

/* Optional accounts, end to end: two browsers ("devices") against the real
 * worker handler on an in-memory store (see tests/run.js).
 *
 * What is being held here, in order of how much it matters:
 *   1. a reader who never signs in makes no account request at all
 *   2. signing in never loses what was already on the device
 *   3. two devices converge, newest edit wins, deletions travel
 *   4. signing out keeps the local data; deleting the account removes the server's copy
 */

const VERSE = (page, base, route) => (async () => {
  await page.goto(base + route);
  await page.waitForSelector('.reader .v');
  await page.locator('.reader .v .vnum').first().click();
  await page.waitForSelector('.vmenu button');
  await page.locator('.vmenu button').first().click();
  await page.keyboard.press('Escape');
})();

const savedIds = page => page.evaluate(() =>
  (JSON.parse(localStorage.getItem('thebook:saved') || '[]')).map(s => s.id).sort());

async function signIn(page, base, email) {
  await page.goto(base + '#/account');
  await page.waitForSelector('#acct-email');
  await page.fill('#acct-email', email);
  await page.click('button[type=submit]');
  await page.waitForSelector('.account-form a');                 // the development-mode link
  await page.click('.account-form a');
  await page.waitForSelector('text=Sign in on this device');
  await page.click('text=Sign in on this device');
  await page.waitForSelector('text=Signed in as');
  await page.waitForFunction(() => window.TheBookAccount.state().last > 0, null, { timeout: 8000 });
}
const sync = page => page.evaluate(() => window.TheBookAccount.sync());

module.exports = async function accounts(t, ctx) {
  const requestsTo = [];

  /* ---- 1. nothing happens for a reader who does not sign in ---- */
  {
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'no-account');
    page.on('request', r => { if (r.url().startsWith(ctx.base + 'api/')) requestsTo.push(r.url()); });
    await VERSE(page, ctx.base, '#/read/amos/2');
    await page.goto(ctx.base + '#/saved');
    await page.waitForSelector('.saved-row');
    await page.waitForTimeout(3500);   // longer than the sync debounce
    t.check('reading, saving and visiting Saved makes no account request', requestsTo.length === 0, requestsTo.join());
    t.check('the "keep my place across devices" note is shown once something is saved',
            await page.locator('.account-prompt').count() === 1);
    t.check('the note offers a way out that is one click',
            await page.locator('.account-prompt button', { hasText: 'No thanks' }).count() === 1);
    await page.locator('.account-prompt button', { hasText: 'No thanks' }).click();
    await page.reload();
    await page.waitForSelector('.saved-row');
    t.check('after "No thanks" it never comes back', await page.locator('.account-prompt').count() === 0);
    await page.goto(ctx.base + '#/diary');
    await page.waitForSelector('h1');
    t.check('not on the Diary page either', await page.locator('.account-prompt').count() === 0);
    t.check('there is no cookie and no account state for a reader who never signed in',
            (await page.context().cookies()).length === 0 &&
            await page.evaluate(() => localStorage.getItem('thebook:account') === null));
    await page.goto(ctx.base);
    t.check('the footer has an Account link', await page.locator('a[href="#/account"]').count() >= 1);
    await page.close();
  }

  /* ---- the Account page when sign-in is not switched on ---- */
  {
    const saved = ctx.accountEnv.AUTH_DEV_MODE;
    delete ctx.accountEnv.AUTH_DEV_MODE;       // no mail path at all
    const page = ctx.tally.watch(await ctx.browser.newPage(), 'not-configured');
    await page.goto(ctx.base + '#/account');
    await page.waitForSelector('.account-body');
    await page.waitForTimeout(500);
    const text = await page.textContent('.account-body');
    t.check('with no mail configured the page says so and offers no form that would pretend',
            /not switched on/i.test(text));
    ctx.accountEnv.AUTH_DEV_MODE = saved;
    await page.close();
  }

  /* ---- 2. device A signs in; device B has data of its own ---- */
  const A = ctx.tally.watch(await ctx.browser.newPage(), 'device A');
  const B = ctx.tally.watch(await ctx.browser.newPage(), 'device B');
  const EMAIL = 'reader@example.com';

  await VERSE(A, ctx.base, '#/read/amos/2');                  // A already has one verse
  const aOwn = await savedIds(A);
  await VERSE(B, ctx.base, '#/read/hosea/1');                 // B has a different one
  const bOwn = await savedIds(B);
  t.check('each device starts with its own, different verse', aOwn.length === 1 && bOwn.length === 1 && aOwn[0] !== bOwn[0]);

  await signIn(A, ctx.base, EMAIL);
  const cookies = await A.context().cookies();
  const sess = cookies.find(c => c.name === 'tbm_session');
  t.check('signing in sets one session cookie, HttpOnly, scoped to /api',
          !!sess && sess.httpOnly && sess.path === '/api' && sess.sameSite === 'Lax');
  t.check('script cannot read it', await A.evaluate(() => document.cookie.indexOf('tbm_session') === -1));
  t.check('the link token is gone from the address bar after signing in', !/verify/.test(A.url()));
  t.check('what was already on device A is still there and now on the server',
          (await savedIds(A)).join() === aOwn.join() &&
          [...ctx.accountStore.items.values()].some(i => i.k.indexOf('saved:') === 0 && !i.d));

  await signIn(B, ctx.base, EMAIL);
  await sync(B);
  const merged = [...aOwn, ...bOwn].sort();
  t.check("device B now has both devices' verses", (await savedIds(B)).join() === merged.join(), (await savedIds(B)).join());
  await sync(A);
  t.check("and device A got B's: signing in merged, nothing was overwritten", (await savedIds(A)).join() === merged.join());

  /* ---- 3. convergence ---- */
  await A.goto(ctx.base + '#/saved');
  await A.waitForSelector('.saved-row');
  await A.locator('.saved-row').first().locator('.saved-note').fill('note written on A');
  await A.locator('.saved-row').first().locator('.saved-note').blur();
  const firstId = await A.evaluate(() => JSON.parse(localStorage.getItem('thebook:saved'))[0].id);
  await A.waitForTimeout(2900);                               // the debounce, no explicit sync
  const onServer = [...ctx.accountStore.items.values()].find(i => i.k === 'saved:' + firstId);
  t.check('a note is sent to the server by itself a few seconds after it is written',
          onServer && JSON.parse(onServer.v).note === 'note written on A');

  await sync(B);
  const noteOnB = await B.evaluate(id => (JSON.parse(localStorage.getItem('thebook:saved')).find(s => s.id === id) || {}).note, firstId);
  t.check('device B receives it', noteOnB === 'note written on A', String(noteOnB));

  await B.waitForTimeout(30);
  await B.evaluate(id => {
    const list = JSON.parse(localStorage.getItem('thebook:saved'));
    list.forEach(s => { if (s.id === id) s.note = 'newer edit on B'; });
    localStorage.setItem('thebook:saved', JSON.stringify(list));
  }, firstId);
  await sync(B); await sync(A);
  const noteOnA = await A.evaluate(id => JSON.parse(localStorage.getItem('thebook:saved')).find(s => s.id === id).note, firstId);
  t.check('the newest edit wins on the other device', noteOnA === 'newer edit on B', noteOnA);

  await B.evaluate(id => {
    localStorage.setItem('thebook:saved', JSON.stringify(JSON.parse(localStorage.getItem('thebook:saved')).filter(s => s.id !== id)));
  }, firstId);
  await sync(B); await sync(A);
  t.check('a removal travels: gone from device A as well', !(await savedIds(A)).includes(firstId));

  await B.evaluate(() => localStorage.setItem('thebook:theme', JSON.stringify('dark')));
  await B.evaluate(() => localStorage.setItem('thebook:last', JSON.stringify({ work: 'amos', chapter: 3, title: 'Amos' })));
  await sync(B); await sync(A);
  t.check('settings and the reading place follow too',
          await A.evaluate(() => localStorage.getItem('thebook:theme') === '"dark"' &&
                                 JSON.parse(localStorage.getItem('thebook:last')).chapter === 3));
  t.check('and the open page shows it (theme applied without a reload)',
          await A.evaluate(() => document.documentElement.getAttribute('data-theme')) === 'dark');

  t.check('searches and audio position are not sent anywhere',
          ![...ctx.accountStore.items.values()].some(i => /recent-searches|listen-at|listen-voice/.test(i.k)));

  /* ---- Download my data ---- */
  await A.goto(ctx.base + '#/account');
  await A.waitForSelector('text=Signed in as');
  const [dl] = await Promise.all([A.waitForEvent('download'), A.click('text=Download my data')]);
  const body = JSON.parse(require('fs').readFileSync(await dl.path(), 'utf8'));
  t.check('"Download my data" returns the reader\'s own items and email',
          body.email === EMAIL && body.items.some(i => i.key.indexOf('saved:') === 0));

  /* ---- 4. sign out keeps the local copy ---- */
  const before = await savedIds(A);
  await A.click('text=Sign out');
  await A.waitForSelector('#acct-email');
  t.check('signing out keeps everything on the device', (await savedIds(A)).join() === before.join() && before.length > 0);
  t.check('and clears the account state and cookie',
          await A.evaluate(() => localStorage.getItem('thebook:account') === null && localStorage.getItem('thebook:sync') === null) &&
          !(await A.context().cookies()).some(c => c.name === 'tbm_session'));
  const after = [];
  A.on('request', r => { if (r.url().startsWith(ctx.base + 'api/')) after.push(r.url()); });
  await VERSE(A, ctx.base, '#/read/micah/1');
  await A.waitForTimeout(3300);
  t.check('after signing out, saving makes no more account requests', after.length === 0, after.join());

  /* ---- delete ---- */
  await B.goto(ctx.base + '#/account');
  await B.waitForSelector('text=Signed in as');
  await B.click('text=Delete my account and data');
  await B.waitForSelector('text=Yes, permanently delete');
  t.check('deleting asks first and says what stays on the device',
          /Copies already in your browsers stay/.test(await B.textContent('.account-danger')));
  const bBefore = await savedIds(B);
  await B.click('text=Yes, permanently delete');
  await B.waitForSelector('#acct-email');
  t.check('after deletion the server holds no user, items or sessions for them',
          ctx.accountStore.users.size === 0 && [...ctx.accountStore.items.keys()].length === 0 && ctx.accountStore.sessions.size === 0);
  t.check('and the browser still has its own copy', (await savedIds(B)).join() === bBefore.join() && bBefore.length > 0);

  await A.close(); await B.close();
};
