'use strict';

/* How "Open in Google Maps" leaves the page on each kind of device.
 *
 *   Android  a geo: URI, which the system hands straight to the Maps app
 *   iPhone   the https universal link, same tab, so the app takes it over
 *   desktop  the https link in a new tab, exactly as before, and one
 *            preconnect to Google once the chip is first approached
 *
 * The OpenStreetMap and Google Earth chips are web links on every device.
 * Whether the Maps app then opens quickly is the phone's business and cannot
 * be measured here; what this holds is the markup that lets it.
 */

const { devices } = require('playwright');

function device(name) {
  const d = Object.assign({}, devices[name]);
  delete d.defaultBrowserType;
  return d;
}

async function openNineveh(page, base) {
  await page.goto(base + '#/read/jonah/0');
  await page.waitForSelector('.reader .v');
  await page.evaluate(() => { window.prompt = () => 'Nineveh'; });
  await page.keyboard.press('?');
  await page.waitForSelector('.lex .place-links .chip.primary', { timeout: 6000 });
}

const chip = (page, i) => page.evaluate(i => {
  const a = document.querySelectorAll('.lex .place-links a')[i];
  return { href: a.getAttribute('href'), target: a.getAttribute('target'),
           rel: a.getAttribute('rel'), text: a.textContent.trim() };
}, i);

module.exports = async function maphandoff(t, ctx) {
  /* ---- desktop: unchanged, plus one preconnect ---- */
  const desk = ctx.tally.watch(await ctx.browser.newPage({
    viewport: { width: 1280, height: 800 }
  }), 'maphandoff desktop');
  const cspErrors = [];
  desk.on('console', m => { if (/Content Security Policy/i.test(m.text())) cspErrors.push(m.text()); });
  await openNineveh(desk, ctx.base);
  const d = await chip(desk, 0);
  t.check('desktop: Google Maps is the https link, in a new tab, noopener',
          /^https:\/\/www\.google\.com\/maps\/search\/\?api=1&query=-?[\d.]+,-?[\d.]+$/.test(d.href) &&
          d.target === '_blank' && /noopener/.test(d.rel), JSON.stringify(d));
  t.check('desktop: there is no preconnect before the chip is approached',
          await desk.locator('link[rel=preconnect][href="https://www.google.com"]').count() === 0);
  await desk.hover('.lex .place-links .chip.primary');
  await desk.focus('.lex .place-links .chip.primary');
  await desk.mouse.down(); await desk.mouse.up().catch(() => {});
  t.check('desktop: approaching the chip adds exactly one preconnect to Google',
          await desk.locator('link[rel=preconnect][href="https://www.google.com"]').count() === 1);
  t.check('desktop: the preconnect hint is not blocked by the page policy',
          cspErrors.length === 0, cspErrors.join(' | ').slice(0, 200));
  await desk.close();

  /* ---- Android ---- */
  const px = ctx.tally.watch(await ctx.browser.newPage(device('Pixel 7')), 'maphandoff android');
  await openNineveh(px, ctx.base);
  const a = await chip(px, 0);
  t.check('Android: Google Maps is a geo: URI with the place name as its label',
          /^geo:-?[\d.]+,-?[\d.]+\?q=-?[\d.]+,-?[\d.]+\(Nineveh\)$/.test(a.href), a.href);
  t.check('Android: it does not ask for a new tab', a.target === null && /noopener/.test(a.rel));
  const aEarth = await chip(px, 1), aOsm = await chip(px, 2);
  t.check('Android: Google Earth and OpenStreetMap stay https links in a new tab',
          /^https:\/\/earth\.google\.com\//.test(aEarth.href) && aEarth.target === '_blank' &&
          /^https:\/\/www\.openstreetmap\.org\//.test(aOsm.href) && aOsm.target === '_blank');
  await px.evaluate(() => document.querySelector('.lex .place-links .chip.primary').dispatchEvent(
    new Event('mouseenter')));
  t.check('Android: no preconnect to Google is added',
          await px.locator('link[rel=preconnect]').count() === 0);
  await px.close();

  /* ---- iPhone ---- */
  const ip = ctx.tally.watch(await ctx.browser.newPage(device('iPhone 14 Pro')), 'maphandoff iphone');
  await openNineveh(ip, ctx.base);
  const i = await chip(ip, 0);
  t.check('iPhone: Google Maps is the https link, same tab, noopener kept',
          /^https:\/\/www\.google\.com\/maps\/search\/\?api=1&query=/.test(i.href) &&
          i.target === null && /noopener/.test(i.rel), JSON.stringify(i));
  const iEarth = await chip(ip, 1);
  t.check('iPhone: Google Earth is unchanged', iEarth.target === '_blank');
  t.check('iPhone: no preconnect to Google is added',
          await ip.locator('link[rel=preconnect]').count() === 0);
  await ip.close();
};
