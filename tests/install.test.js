'use strict';

/* "Install app", in the footer, only when the device can.
 *
 * Chrome-family browsers hand the page a beforeinstallprompt event; the
 * browser here never does, so the event is made up (it has prompt() and
 * userChoice, which is all the page uses). Safari on iOS has no event, so the
 * chip is for the iPhone user agent and opens a panel that names the two
 * buttons. Standalone, or after appinstalled, there is nothing to show.
 * Whether a real browser then installs the app is the browser's business.
 */

const { devices } = require('playwright');

const AXE = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

function device(name) {
  const d = Object.assign({}, devices[name]);
  delete d.defaultBrowserType;
  return d;
}

const visible = page => page.evaluate(() => {
  const b = document.getElementById('foot-install');
  return !!b && !b.hidden && b.getBoundingClientRect().height > 0;
});

/* Dispatch a stand-in for Chrome's event; report whether the page took over
   the default (it has to, or Chrome shows its own mini-bar as well). */
const fireInstallEvent = page => page.evaluate(() => {
  window.__prompted = 0;
  const e = new Event('beforeinstallprompt', { cancelable: true });
  e.prompt = () => { window.__prompted++; return Promise.resolve(); };
  e.userChoice = Promise.resolve({ outcome: 'accepted' });
  window.dispatchEvent(e);
  return e.defaultPrevented;
});

async function axe(page, selector) {
  await page.addScriptTag({ url: new URL('__axe.js', page.url()).href });
  /* Scoped: the install control is what is under test, and the rest of the
     page is held to the same rules by tests/access.test.js. */
  const r = await page.evaluate(async ([tags, sel]) => await window.axe.run(
    document.querySelector(sel), { runOnly: { type: 'tag', values: tags } }),
    [AXE, selector]);
  return r.violations.map(v => v.id + ' (' + v.impact + ')' +
    (process.env.AXE_DETAIL ? ' ' + v.nodes.map(n => n.html.slice(0, 80) + ' ' + n.any.map(a => a.message).join(';')).join(' | ') : ''));
}

module.exports = async function install(t, ctx) {
  /* ---- desktop, Chrome-style ---- */
  const page = ctx.tally.watch(await ctx.browser.newPage({
    viewport: { width: 1280, height: 800 }
  }), 'install desktop');
  await page.goto(ctx.base);
  await page.waitForSelector('#foot-install', { state: 'attached' });
  t.check('nothing is offered before the browser says it can install',
          !await visible(page));
  t.check('the page takes over the browser prompt',
          await fireInstallEvent(page));
  t.check('then the footer offers "Install app"',
          await visible(page) &&
          (await page.textContent('#install-app')).trim() === 'Install app');
  t.check('and no panel or popup opens by itself',
          await page.locator('.install-panel, .tour-invite').count() === 0);
  const violations = await axe(page, '.foot');
  t.check('the footer with the chip fails no WCAG A or AA check',
          violations.length === 0, violations.join(', '));
  await page.click('#install-app');
  t.check('pressing it shows the browser prompt, once',
          await page.evaluate(() => window.__prompted) === 1);
  t.check('and takes the chip away, since the event is spent',
          !await visible(page));

  await fireInstallEvent(page);
  t.check('a fresh event brings it back', await visible(page));
  await page.evaluate(() => window.dispatchEvent(new Event('appinstalled')));
  t.check('appinstalled takes it away', !await visible(page));
  const stored = await page.evaluate(() => Object.keys(localStorage)
    .filter(k => /install/i.test(k)));
  t.check('nothing about installing is stored', stored.length === 0, stored.join(','));
  await page.close();

  /* ---- already installed ---- */
  const app = ctx.tally.watch(await ctx.browser.newPage({
    viewport: { width: 1280, height: 800 }
  }), 'install standalone');
  await app.addInitScript(() => {
    const real = window.matchMedia.bind(window);
    window.matchMedia = q => /display-mode:\s*standalone/.test(q)
      ? { matches: true, media: q, onchange: null, addEventListener() {},
          removeEventListener() {}, addListener() {}, removeListener() {} }
      : real(q);
  });
  await app.goto(ctx.base);
  await app.waitForSelector('#foot-install', { state: 'attached' });
  await fireInstallEvent(app);
  t.check('running standalone, nothing is offered even if the event arrives',
          !await visible(app));
  await app.close();

  /* ---- Android: the same event, a phone ---- */
  const px = ctx.tally.watch(await ctx.browser.newPage(device('Pixel 7')), 'install android');
  await px.goto(ctx.base);
  await px.waitForSelector('#foot-install', { state: 'attached' });
  t.check('Android: nothing before the event', !await visible(px));
  await fireInstallEvent(px);
  t.check('Android: the chip appears after it and says "Install app"',
          await visible(px) && (await px.textContent('#install-app')).trim() === 'Install app');
  await px.close();

  /* ---- iPhone, Safari ---- */
  const ip = ctx.tally.watch(await ctx.browser.newPage(device('iPhone 14 Pro')), 'install iphone');
  await ip.goto(ctx.base);
  await ip.waitForSelector('#foot-install', { state: 'attached' });
  t.check('iPhone: an "Install" chip is there with no event at all',
          await visible(ip) && (await ip.textContent('#install-app')).trim() === 'Install');
  t.check('iPhone: and nothing is open until it is pressed',
          await ip.locator('.install-panel').count() === 0);
  await ip.tap('#install-app');
  await ip.waitForSelector('.install-panel');
  const text = await ip.textContent('.install-panel');
  t.check('iPhone: the panel says Share, then Add to Home Screen',
          /Share/.test(text) && /Add to Home Screen/.test(text), text.trim().slice(0, 80));
  t.check('iPhone: it is a named dialog and the chip knows it is open',
          await ip.getAttribute('.install-panel', 'role') === 'dialog' &&
          await ip.getAttribute('#install-app', 'aria-expanded') === 'true');
  t.check('iPhone: it fits inside the screen', await ip.evaluate(() => {
    const b = document.querySelector('.install-panel').getBoundingClientRect();
    return b.left >= 0 && b.right <= innerWidth && b.top >= 0 && b.bottom <= innerHeight;
  }));
  const pv = await axe(ip, '.install-panel');
  t.check('iPhone: the panel fails no WCAG A or AA check', pv.length === 0, pv.join(', '));
  await ip.tap('.install-panel .tour-x');
  t.check('iPhone: the close button closes it and focus returns to the chip',
          await ip.locator('.install-panel').count() === 0 &&
          await ip.evaluate(() => document.activeElement.id) === 'install-app');
  await ip.tap('#install-app');
  await ip.waitForSelector('.install-panel');
  await ip.keyboard.press('Escape');
  t.check('iPhone: Escape closes it too', await ip.locator('.install-panel').count() === 0);
  await ip.tap('#install-app');
  await ip.waitForSelector('.install-panel');
  await ip.tap('.install-panel .chip.primary');
  t.check('iPhone: and so does "Got it"', await ip.locator('.install-panel').count() === 0);
  await ip.close();

  /* ---- iPhone, already on the home screen ---- */
  const home = ctx.tally.watch(await ctx.browser.newPage(device('iPhone 14 Pro')), 'install iphone home');
  await home.addInitScript(() => {
    Object.defineProperty(navigator, 'standalone', { value: true });
  });
  await home.goto(ctx.base);
  await home.waitForSelector('#foot-install', { state: 'attached' });
  t.check('iPhone from the home screen: no chip', !await visible(home));
  await home.close();

  /* ---- iOS Chrome has its own menu; the Safari wording would be wrong ---- */
  const cr = ctx.tally.watch(await ctx.browser.newPage(Object.assign(device('iPhone 14 Pro'), {
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 ' +
               '(KHTML, like Gecko) CriOS/120.0.0.0 Mobile/15E148 Safari/604.1'
  })), 'install ios chrome');
  await cr.goto(ctx.base);
  await cr.waitForSelector('#foot-install', { state: 'attached' });
  t.check('iOS Chrome is not shown the Safari instructions', !await visible(cr));
  await cr.close();
};
