'use strict';

/* The intro: the wordmark opens like a book, once, for a person.
 *
 * Every other suite runs as an automated browser, which the intro leaves
 * alone (navigator.webdriver), so they see the page exactly as before. This
 * one says it is not automated, with an ordinary user agent, and checks the
 * promises: the page is already there underneath, it is gone in about two
 * seconds, it plays once, Skip and a tap end it, the tour's offer waits for
 * it, the wordmark replays it, and reduced motion never sees it.
 */

const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36';
const human = () => { Object.defineProperty(navigator, 'webdriver', { get: () => false }); };

module.exports = async function intro(t, ctx) {
  for (const [label, viewport] of [['phone', { width: 390, height: 844 }], ['desktop', { width: 1280, height: 800 }]]) {
    const page = ctx.tally.watch(await ctx.browser.newPage({ viewport, userAgent: UA }), 'intro ' + label);
    await page.addInitScript(human);
    await page.goto(ctx.base + '?firsttime#/');
    await page.waitForSelector('.intro', { timeout: 3000 });
    t.check(label + ': a first visit opens on the book',
            await page.isVisible('.intro-cover') && await page.isVisible('.intro-skip'));
    t.check(label + ': the front page is already rendered underneath it',
            await page.evaluate(() => !!document.querySelector('main .hero h1')));
    t.check(label + ': the tour offer does not share the screen with it',
            !(await page.$('.tour-invite')));
    await page.waitForSelector('.intro', { state: 'detached', timeout: 2600 });
    t.check(label + ': it is gone within about two seconds and remembered',
            await page.evaluate(() => localStorage.getItem('thebook:intro')) === '"seen"');
    await page.waitForSelector('.tour-invite', { timeout: 5000 }).catch(() => null);
    t.check(label + ': the tour offer comes after it', !!(await page.$('.tour-invite')));
    await page.click('.tour-invite .tour-x');

    await page.reload();
    await page.waitForSelector('main .hero');
    await page.waitForTimeout(300);
    t.check(label + ': a second visit does not play it again', !(await page.$('.intro')));

    await page.click('.brand');
    await page.waitForSelector('.intro', { timeout: 1000 });
    t.check(label + ': pressing the wordmark on the front page plays it again', true);
    await page.click('.intro-skip');
    await page.waitForSelector('.intro', { state: 'detached', timeout: 1000 });
    t.check(label + ': Skip ends it at once', true);

    await page.click('.brand');
    await page.waitForSelector('.intro');
    await page.mouse.click(viewport.width / 2, viewport.height / 2);
    await page.waitForSelector('.intro', { state: 'detached', timeout: 1000 });
    t.check(label + ': a tap opens it straight away', true);
    await page.close();
  }

  const still = ctx.tally.watch(await ctx.browser.newPage({ userAgent: UA, reducedMotion: 'reduce' }), 'intro reduced');
  await still.addInitScript(human);
  await still.goto(ctx.base + '?firsttime#/');
  await still.waitForSelector('main .hero');
  await still.waitForTimeout(400);
  t.check('reduced motion: no intro at all', !(await still.$('.intro')));
  await still.close();

  const bot = ctx.tally.watch(await ctx.browser.newPage({ userAgent: 'Mozilla/5.0 (compatible; Googlebot/2.1)' }), 'intro bot');
  await bot.addInitScript(human);
  await bot.goto(ctx.base + '?firsttime#/');
  await bot.waitForSelector('main .hero');
  await bot.waitForTimeout(400);
  t.check('a crawler: no intro at all', !(await bot.$('.intro')));
  await bot.close();
};
