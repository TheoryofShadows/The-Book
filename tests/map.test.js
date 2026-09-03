'use strict';

/* The chapter map: land, water, and the places the chapter names.
 *
 * The geometry is checked in tests/python/test_basemap.py and the references
 * in tests/python/test_mentions.py. This checks the part neither can: that
 * what was built reaches the canvas, that the frame chooses itself correctly,
 * and that everything the canvas shows is also on the page for a reader who
 * cannot see a canvas at all.
 */

async function openMap(page, base, route) {
  /* goto with a URL that differs only by its hash -- or not at all -- does
     not reload the document, so the panel would still be open from last time
     and the click below would shut it. A theme set in localStorage needs the
     fresh document too. */
  if (page.url() === base + route) await page.reload();
  else await page.goto(base + route);

  await page.waitForSelector('.chapter-map');
  const panel = page.locator('.chapter-map');
  if (!await panel.evaluate(e => e.open)) {
    await page.locator('.chapter-map > summary').click();
  }
  await page.waitForSelector('.map-canvas, .chapter-map .empty', { timeout: 15000 });
  await page.waitForTimeout(500);
}

/* The places a chapter should show, read straight off the built data rather
   than off the page. Neither the canvas nor the list is the authority here:
   the mention index is, and this is what lets a test say so. Places whose
   key is in the index but which carry no coordinates are dropped, because
   the renderer drops them too (app.js filters the shard lookup by Boolean). */
function expected(root, workId, chapterIdx) {
  const fs = require('fs');
  const path = require('path');
  const data = path.join(root, 'docs', 'data');
  const read = f => JSON.parse(fs.readFileSync(f, 'utf8'));

  const keys = read(path.join(data, 'mentions.json'))[workId + '/' + chapterIdx];
  if (!keys) throw new Error('no mention index entry for ' + workId + '/' + chapterIdx);

  const shards = {};
  for (const k of keys) {
    const s = /^[a-z]/.test(k) ? k[0] : '0';
    if (!shards[s]) shards[s] = read(path.join(data, 'places', s + '.json'));
  }
  return keys.map(k => shards[/^[a-z]/.test(k) ? k[0] : '0'][k])
             .filter(Boolean).map(p => p.name).sort();
}

/* How many distinct colours the canvas actually put down. A canvas that threw
   halfway is still a canvas; this is how you tell it drew something. */
const painted = page => page.evaluate(() => {
  const c = document.querySelector('.map-canvas');
  if (!c) return 0;
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  const seen = new Set();
  for (let i = 0; i < d.length; i += 2000) {
    seen.add(d[i] + ',' + d[i + 1] + ',' + d[i + 2]);
  }
  return seen.size;
});

module.exports = async function map(t, ctx) {
  const page = ctx.tally.watch(await ctx.browser.newPage({
    viewport: { width: 1100, height: 900 }
  }), 'map');

  /* Count the line segments a redraw puts down. Used far below to check that
     relating two places does not quietly join them: the rings are the only
     segments the map is entitled to draw, so the count is a constant, and a
     route would move it. Installed before the first navigation so it is in
     place for every document this page loads. */
  await page.addInitScript(() => {
    window.__seg = 0;
    const proto = CanvasRenderingContext2D.prototype;
    const real = proto.lineTo;
    proto.lineTo = function () { window.__seg++; return real.apply(this, arguments); };
  });

  /* ---- it is not loaded until it is wanted ---- */
  await page.goto(ctx.base + '#/read/amos/2');
  await page.waitForSelector('.reader .v');
  t.check('the map is offered on a chapter but not drawn yet',
          await page.locator('.chapter-map').count() === 1 &&
          await page.locator('.map-canvas').count() === 0);

  /* ---- the ordinary case ---- */
  await openMap(page, ctx.base, '#/read/amos/2');

  t.check('opening it draws a canvas', await page.locator('.map-canvas').count() === 1);

  const colours = await painted(page);
  t.check('with land and water actually painted on it', colours >= 4,
          colours + ' distinct colours');

  const places = await page.locator('.map-place').count();
  t.check('and the places the chapter names', places > 0, places + ' places');

  /* Amos 3 opens against Samaria. If the mention index ever stops resolving,
     this is the check that says so in words rather than in a byte count. */
  const names = (await page.locator('.map-place').allTextContents())
                  .map(s => s.toLowerCase());
  t.check('which are the right ones for this chapter',
          names.some(n => n.indexOf('samaria') === 0),
          names.slice(0, 5).join(', '));

  /* ---- the canvas is not the only copy ---- */

  /* This used to read `.map-place` on both sides. But `.map-place` is only
     ever rendered inside `.map-list`, so it counted the list, compared it to
     the list, and passed -- while the README promised a reader that the two
     copies can never disagree. The canvas now says which places it drew, so
     there are genuinely two sides to compare. */
  const drawn = await page.evaluate(() =>
    (document.querySelector('.map-canvas').dataset.drawn || '')
      .split('\n').filter(Boolean).sort());
  const listed = await page.evaluate(() =>
    [...document.querySelectorAll('.map-list .map-place')]
      .map(b => b.firstChild.textContent.trim()).sort());

  t.check('every place on the canvas is also a link on the page',
          drawn.length > 0 && drawn.join('|') === listed.join('|'),
          drawn.length + ' drawn, ' + listed.length + ' listed');

  /* Both sides can agree and both be wrong. The mention index on disk is the
     thing neither the canvas nor the list is allowed to quietly disagree
     with, so it is read here from the file rather than from the page. */
  const onRecord = expected(ctx.root, 'amos', 2);
  t.check('and both are the places the mention index actually records',
          listed.join('|') === onRecord.join('|'),
          listed.length + ' shown, ' + onRecord.length + ' on record');

  t.check('the canvas points a screen reader at that list',
          await page.evaluate(() => {
            const c = document.querySelector('.map-canvas');
            const id = c.getAttribute('aria-describedby');
            return !!id && !!document.getElementById(id);
          }));

  t.check('and says what it is rather than being an unlabelled picture',
          /places named in this chapter/i.test(
            await page.locator('.map-canvas').getAttribute('aria-label')));

  t.check('each place says how firm its location is, in words',
          await page.evaluate(() => {
            const k = document.querySelector('.map-place .map-place-kind');
            return !!k && k.textContent.length > 4;
          }));

  /* ---- a place opens the panel that already existed ---- */
  await page.locator('.map-place').first().click();
  await page.waitForTimeout(300);
  t.check('choosing a place opens the same panel the lexicon shows',
          await page.locator('.map-detail .place').count() === 1);

  t.check('with its coordinates on it',
          /\d+\.\d+°/.test(await page.textContent('.map-detail')));

  /* ---- the frame chooses itself ---- */
  await openMap(page, ctx.base, '#/read/acts/26');
  const caption = await page.textContent('.map-caption');
  t.check('a chapter that sails west is drawn on the world',
          /outside the biblical frame/i.test(caption));

  await openMap(page, ctx.base, '#/read/amos/2');
  t.check('and one that does not is drawn on the biblical frame',
          !/outside the biblical frame/i.test(
            await page.textContent('.map-caption')));

  /* ---- what the map refuses to claim ---- */
  t.check('the caption says no borders are drawn, and why',
          /no borders are drawn/i.test(await page.textContent('.map-caption')));

  t.check('and credits the land outlines',
          /natural earth/i.test(await page.textContent('.map-caption')));

  /* A contested identification must not be shown as a settled dot. Tarshish
     is the case: the gazetteer's source states Spain flat. */
  await openMap(page, ctx.base, '#/read/jonah/0');
  const tarshish = page.locator('.map-place', { hasText: 'Tarshish' }).first();
  if (await tarshish.count()) {
    t.check('a disputed identification is not drawn as an identified place',
            await tarshish.evaluate(e => e.className.indexOf('map-approximate') >= 0));
    await tarshish.click();
    await page.waitForTimeout(300);
    t.check('and says what is actually disputed about it',
            /Tarsus/.test(await page.textContent('.map-detail')));
  } else {
    t.check('Jonah 1 names Tarshish', false, 'not in the mention index');
  }

  /* ---- what a place is named beside ----

     Co-occurrence, counted over the mention index the pins already come
     from. The thing this must never become is a route: sharing a chapter is
     not travel, and the index does not even record the order a chapter names
     its places in. */
  await openMap(page, ctx.base, '#/read/amos/2');
  const chip = page.locator('.map-tools .chip', { hasText: 'First appearances' });

  t.check('the first-appearance layer is offered, and is off until asked for',
          await chip.count() === 1 &&
          await chip.getAttribute('aria-pressed') === 'false' &&
          await page.locator('.map-place.map-first').count() === 0);

  await page.locator('.map-place', { hasText: 'Samaria' }).first().click();
  await page.waitForTimeout(400);

  t.check('choosing a place says what it is named beside, and counts chapters',
          /Named in the same chapter as/i.test(await page.textContent('.map-kin')) &&
          /\d+ chapters?/.test(await page.textContent('.map-kin-list')));

  t.check('the ones already on this map can be pointed at, the rest are named only',
          await page.locator('.map-kin-here').count() > 0 &&
          await page.locator('.map-kin-here').count() <
            await page.locator('.map-kin-list li').count());

  t.check('and it resolves them to names rather than showing index keys',
          await page.evaluate(() => [...document.querySelectorAll('.map-kin-name')]
            .every(s => /^[A-Z]/.test(s.textContent.trim()))));

  /* Two different counts live in the same panel: placeBlock's "named in N
     passages" and kin's "in N chapters". Jerusalem is 719 of one and 293 of
     the other, and one wearing the other's sentence would be worse than no
     number at all. */
  t.check('and keeps chapters and passages as separate words',
          /named in \d+ passages?/i.test(await page.textContent('.map-detail')) &&
          /\d+ chapters?/.test(await page.textContent('.map-kin-list')));

  t.check('and says plainly that sharing a chapter is not a route',
          /not a route/i.test(await page.textContent('.map-kin-note')));

  /* The negative claim, and the one worth being careful about: relating two
     places must never draw a route between them.

     Counting pixels does not test this. The canvas is about 430 px across
     and Amos 3's places are a handful of pixels apart -- Samaria to Bethel
     is eight -- so a hairline between them is invisible to any colour
     metric while being exactly the thing that must not exist. So count the
     drawing instead: the basemap rings are the only line segments a redraw
     is entitled to, and they are identical whether or not a place is
     chosen. Any segment choosing adds is a stroke between two pins. */
  await page.evaluate(() => { window.__seg = 0; });
  await page.locator('.map-place', { hasText: 'Egypt' }).first().click();
  await page.waitForTimeout(400);
  const withChosen = await page.evaluate(() => window.__seg);

  await page.evaluate(() => { window.__seg = 0; });
  await page.locator('.map-tools .chip', { hasText: 'Reset' }).click();
  await page.waitForTimeout(400);
  const withNone = await page.evaluate(() => window.__seg);

  t.check('and draws no line between the places it has just related',
          withChosen > 0 && withChosen === withNone,
          withChosen + ' line segments with a place chosen, ' +
          withNone + ' with none');

  /* ---- where a place first enters the library ---- */
  await chip.click();
  await page.waitForSelector('.map-place.map-first', { timeout: 15000 });

  const marked = await page.locator('.map-place.map-first').count();
  t.check('the layer marks the places named here for the first time',
          await chip.getAttribute('aria-pressed') === 'true' && marked > 0,
          marked + ' of ' + await page.locator('.map-place').count());

  t.check('and marks the same number on the canvas as in the list',
          await page.evaluate(() => {
            const c = document.querySelector('.map-canvas');
            return (c.dataset.drawn || '').split('\n').filter(Boolean).length;
          }) === await page.locator('.map-place').count(),
          'the layer rings places, it never removes them');

  t.check('and says in words which places those are, not only in a ring',
          await page.locator('.map-place-first').count() === marked);

  t.check('and calls it the composition order rather than history',
          /composition order/i.test(await page.textContent('.map-caption')) &&
          /not when a place came to exist/i.test(
            await page.textContent('.map-caption')));

  t.check('and says an absence is a gap in the gazetteer, not a fact about the text',
          /gap in it rather than a fact about the text/i.test(
            await page.textContent('.map-caption')));

  t.check('and counts them for a screen reader too',
          /named here for the first time/i.test(
            await page.locator('.map-canvas').getAttribute('aria-label')));

  /* Amos is early enough that Samaria arrives in it; Acts 27 is late enough
     that most of what it names arrived long before, which is the case that
     proves the line is looked up rather than assumed. */
  await openMap(page, ctx.base, '#/read/acts/26');
  await page.locator('.map-place', { hasText: 'Sidon' }).first().click();
  await page.waitForSelector('.map-arrival a', { timeout: 15000 });
  t.check('a place named earlier links the chapter where it first appears',
          await page.evaluate(() => {
            const a = document.querySelector('.map-arrival a');
            return !!a && /^#\/read\/[^/]+\/\d+$/.test(a.getAttribute('href'));
          }),
          await page.textContent('.map-arrival a'));

  t.check('and does not claim to know when the place came to exist',
          /not when the place came to exist/i.test(
            await page.textContent('.map-arrival')));

  /* Turning it off must leave the two standing claims of the caption alone. */
  await openMap(page, ctx.base, '#/read/amos/2');
  await chip.click();
  await page.waitForSelector('.map-place.map-first', { timeout: 15000 });
  await chip.click();
  await page.waitForTimeout(500);
  t.check('turning the layer off clears it without disturbing the caption',
          await page.locator('.map-place.map-first').count() === 0 &&
          !/finely dotted/.test(await page.textContent('.map-caption')) &&
          /no borders are drawn/i.test(await page.textContent('.map-caption')) &&
          /natural earth/i.test(await page.textContent('.map-caption')));

  /* ---- panning and zooming stay on the map ---- */
  await openMap(page, ctx.base, '#/read/amos/2');
  const before = await painted(page);
  await page.locator('.map-canvas').hover();
  await page.mouse.wheel(0, -400);
  await page.waitForTimeout(300);
  t.check('the wheel zooms without throwing', await painted(page) >= 3);

  /* Dragging a long way must not leave the reader looking at blank ocean. */
  const box = await page.locator('.map-canvas').boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 3, box.y + box.height * 3, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(300);
  t.check('dragging hard cannot wander off into empty sea',
          await painted(page) >= 4, await painted(page) + ' colours');

  await page.locator('.map-tools .chip', { hasText: 'Reset' }).click();
  await page.waitForTimeout(300);
  t.check('reset puts it back', Math.abs(await painted(page) - before) <= 4);

  /* ---- zoomed in, the picture is a subset and never an invention ----

     The equality checked above is an unzoomed claim: pins outside the
     viewport are culled, so a zoomed map really does paint fewer places
     than the list holds. What must survive the wheel is the weaker half --
     everything painted is still on the page. Joshua 15 is the case worth
     using, because 161 places is enough that zooming genuinely leaves some
     behind; Amos 2's four stay in frame however far you go, which would
     make this a second copy of the equality check rather than a test of
     culling. */
  await openMap(page, ctx.base, '#/read/joshua/14');
  const seen = () => page.evaluate(() => {
    const drawn = (document.querySelector('.map-canvas').dataset.drawn || '')
      .split('\n').filter(Boolean);
    const listed = [...document.querySelectorAll('.map-list .map-place')]
      .map(b => b.firstChild.textContent.trim());
    return { drawn, listed, stray: drawn.filter(n => !listed.includes(n)) };
  });

  await page.locator('.map-canvas').hover();
  let zoomed = await seen();
  /* Zoom a step at a time until some place has actually been culled, rather
     than guessing a wheel count: too few and nothing is culled, too many and
     the viewport holds nothing at all, and neither proves anything. */
  for (let i = 0; i < 12 && zoomed.drawn.length === zoomed.listed.length; i++) {
    await page.mouse.wheel(0, -100);
    await page.waitForTimeout(150);
    zoomed = await seen();
  }

  t.check('zooming in really does leave some places off the canvas',
          zoomed.drawn.length > 0 &&
          zoomed.drawn.length < zoomed.listed.length,
          zoomed.drawn.length + ' of ' + zoomed.listed.length + ' still painted');

  t.check('and every place it still paints is on the page',
          zoomed.stray.length === 0,
          zoomed.stray.length ? 'not listed: ' + zoomed.stray.join(', ') : 'none stray');

  /* Back to Amos, unzoomed: the theme check below samples one pixel of sea,
     and a zoomed Joshua has land under it. */
  await openMap(page, ctx.base, '#/read/amos/2');

  /* ---- the theme ---- */
  const sea = () => page.evaluate(() => {
    const c = document.querySelector('.map-canvas');
    const d = c.getContext('2d').getImageData(2, 2, 1, 1).data;
    return d[0] + ',' + d[1] + ',' + d[2];
  });
  const light = await sea();
  await page.evaluate(() => {
    localStorage.setItem('thebook:theme', JSON.stringify('dark'));
  });
  await openMap(page, ctx.base, '#/read/amos/2');
  const dark = await sea();
  t.check('the map follows the theme instead of staying light',
          light !== dark, light + ' -> ' + dark);
  await page.evaluate(() => {
    localStorage.setItem('thebook:theme', JSON.stringify('auto'));
  });

  /* ---- a chapter with nothing to draw ---- */
  await openMap(page, ctx.base, '#/read/the-epistle-of-barnabas/0');
  t.check('a chapter the gazetteer does not cover says so rather than ' +
          'drawing an empty map',
          await page.locator('.chapter-map .empty').count() === 1 &&
          await page.locator('.map-canvas').count() === 0);

  /* ---- a tap is not a drag ----

     Every tap on a touch screen travels a few pixels. The pan used to begin
     on the first of them and the click that followed was tested against the
     positions the pan had just moved, so a finger that wobbled four pixels
     slid the map out from under itself and missed a seven-pixel target.
     Nothing was wrong with the choosing; it was being asked where a place
     had been a moment earlier. dragging.moved was already being computed for
     exactly this, and was read by nothing.

     Checked from the outside: a real drag must not select, and a tap on a
     pin must. */
  await openMap(page, ctx.base, '#/read/amos/2');
  const canvasBox = await page.locator('.map-canvas').boundingBox();
  await page.mouse.move(canvasBox.x + canvasBox.width * 0.5,
                        canvasBox.y + canvasBox.height * 0.5);
  await page.mouse.down();
  await page.mouse.move(canvasBox.x + canvasBox.width * 0.5 + 70,
                        canvasBox.y + canvasBox.height * 0.5 + 40, { steps: 12 });
  await page.mouse.up();
  await page.waitForTimeout(250);
  t.check('dragging the map does not also choose a place',
          await page.evaluate(() => document.querySelector('.map-detail').hidden));

  /* ---- zoom without a wheel ----

     The wheel was the only way to change the scale, so a phone had no way at
     all and neither did a keyboard. Both buttons call the same zoomBy the
     wheel does, centred on the canvas rather than on a pointer. */
  const inkHash = () => page.evaluate(() => {
    const c = document.querySelector('.map-canvas');
    const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
    let h = 0;
    for (let i = 0; i < d.length; i += 997) h = (h * 31 + d[i]) >>> 0;
    return h;
  });
  await openMap(page, ctx.base, '#/read/genesis/12');
  const atHome = await inkHash();
  await page.locator('.map-tools .chip', { hasText: '+' }).first().click();
  await page.waitForTimeout(300);
  const zoomedIn = await inkHash();
  await page.locator('.map-tools .chip', { hasText: '−' }).first().click();
  await page.waitForTimeout(300);
  t.check('the map can be zoomed without a wheel',
          atHome !== zoomedIn && zoomedIn !== await inkHash());

  /* ---- and with two fingers, which is the only zoom a phone has ---- */
  await openMap(page, ctx.base, '#/read/genesis/12');
  const beforePinch = await inkHash();
  const pinchBox = await page.locator('.map-canvas').boundingBox();
  await page.evaluate(({ x, y, w, h }) => {
    const c = document.querySelector('.map-canvas');
    c.setPointerCapture = () => {};
    const send = (type, id, cx, cy) => c.dispatchEvent(new PointerEvent(type, {
      pointerId: id, clientX: cx, clientY: cy, bubbles: true, pointerType: 'touch'
    }));
    send('pointerdown', 1, x + w * 0.45, y + h * 0.5);
    send('pointerdown', 2, x + w * 0.55, y + h * 0.5);
    send('pointermove', 1, x + w * 0.30, y + h * 0.5);
    send('pointermove', 2, x + w * 0.70, y + h * 0.5);
    send('pointermove', 1, x + w * 0.15, y + h * 0.5);
    send('pointermove', 2, x + w * 0.85, y + h * 0.5);
    send('pointerup', 1, x + w * 0.15, y + h * 0.5);
    send('pointerup', 2, x + w * 0.85, y + h * 0.5);
  }, { x: pinchBox.x, y: pinchBox.y, w: pinchBox.width, h: pinchBox.height });
  await page.waitForTimeout(300);
  t.check('two fingers zoom it', beforePinch !== await inkHash());

  /* ---- the names are on the map ----

     A field of unlabelled dots says how many places a chapter names and
     nothing else: to learn that the dot on the coast is Ashdod you had to
     point at it, which on a phone means guessing.

     Counted rather than read, because a canvas has no text to read. The type
     is the only thing on this canvas drawn in the text colour -- the pins are
     the accent and the coastline is the faint one, both of them lighter than
     this threshold -- so the very darkest pixels are the names and nothing
     else. Asserted as a relationship as well as a floor: a chapter naming a
     hundred and sixty places must carry more lettering than one naming four,
     which a fixed number alone would not catch if the labels stopped being
     placed and something else went dark. */
  const nameInk = () => page.evaluate(() => {
    const c = document.querySelector('.map-canvas');
    const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
    let ink = 0;
    for (let i = 0; i < d.length; i += 4) if (d[i] < 90) ink++;
    return ink;
  });

  await openMap(page, ctx.base, '#/read/amos/2');
  const fewNames = await nameInk();
  await openMap(page, ctx.base, '#/read/joshua/14');
  const manyNames = await nameInk();

  t.check('place names are painted on the canvas, not only in the list',
          fewNames > 25 && manyNames > fewNames,
          fewNames + ' ink pixels on a chapter naming four places, ' +
          manyNames + ' on one naming a hundred and sixty');

  /* ---- and the way out to a real map of the world ---- */
  await page.locator('.map-place').first().click();
  await page.waitForTimeout(300);
  const out = await page.evaluate(() => Array.from(
    document.querySelectorAll('.place-links a'),
    a => ({ text: a.textContent.trim(), href: a.href })));
  t.check('choosing a place offers Google Maps first, and says so in full',
          out.length === 3 && /Google Maps/.test(out[0].text) &&
          /google\.com\/maps/.test(out[0].href),
          out.map(o => o.text).join(' / '));
  t.check('and Google Earth and OpenStreetMap beside it, on real coordinates',
          /earth\.google\.com/.test(out[1].href) &&
          /openstreetmap\.org/.test(out[2].href) &&
          /@-?\d+\.\d+,-?\d+\.\d+/.test(out[1].href));

  /* ---- the maps you have left ----

     Every map used to wire itself to the theme button, the system
     colour-scheme query and the window resize, and take none of it off
     again. The listeners close over the canvas and the places, so a chapter
     you have navigated away from could never be collected, and one press of
     the theme button repainted every map opened in the session. Reading down
     Psalms with the map open left a hundred and fifty of them attached.

     Counted from outside rather than from a private variable: the canvases
     that actually get drawn on when the theme changes. There should be one,
     and it should be the one on the page. */
  await openMap(page, ctx.base, '#/read/amos/0');
  await openMap(page, ctx.base, '#/read/amos/1');
  await openMap(page, ctx.base, '#/read/amos/2');

  const repainted = await page.evaluate(async () => {
    const drawn = new Set();
    const real = CanvasRenderingContext2D.prototype.fillRect;
    CanvasRenderingContext2D.prototype.fillRect = function () {
      drawn.add(this.canvas);
      return real.apply(this, arguments);
    };
    document.getElementById('theme').click();
    await new Promise(r => setTimeout(r, 300));
    CanvasRenderingContext2D.prototype.fillRect = real;
    const here = document.querySelector('.map-canvas');
    return { drawn: drawn.size,
             onThePage: drawn.has(here) };
  });
  t.check('changing the theme repaints the map on the page and no other',
          repainted.drawn === 1 && repainted.onThePage,
          repainted.drawn + ' canvas(es) repainted');
  await page.evaluate(() => {
    localStorage.setItem('thebook:theme', JSON.stringify('auto'));
  });

  await page.close();

  /* ---- and all of it from a file, with no server ---- */
  const offline = ctx.tally.watch(await ctx.browser.newPage(), 'map offline');
  if (ctx.standalone) {
    await offline.goto('file://' + ctx.standalone + '#/read/amos/2');
    await offline.waitForSelector('.reader .v', { timeout: 30000 });
    await offline.locator('.chapter-map > summary').click();
    await offline.waitForSelector('.map-canvas', { timeout: 15000 });
    await offline.waitForTimeout(500);
    const off = await offline.evaluate(() => {
      const c = document.querySelector('.map-canvas');
      const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      const seen = new Set();
      for (let i = 0; i < d.length; i += 2000) {
        seen.add(d[i] + ',' + d[i + 1] + ',' + d[i + 2]);
      }
      return { colours: seen.size,
               places: document.querySelectorAll('.map-place').length };
    });
    t.check('the map draws from a file with no network at all',
            off.colours >= 4 && off.places > 0,
            off.places + ' places, ' + off.colours + ' colours');
  } else {
    t.check('the map draws from a file with no network at all', true,
            'skipped: the offline suite did not run');
  }
  await offline.close();
};
