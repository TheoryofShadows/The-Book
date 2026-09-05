'use strict';

/* The half of the site a crawler can actually ask for.

   The reader is one page behind hash routes, and a fragment is never sent to
   a server: every work and every chapter lives at an address no crawler can
   request and no crawler can index. tools/build_pages.py writes the other
   half -- a plain page per chapter with the text really in the HTML -- and
   what is checked here is the two things that make those pages worth having.

   That the text is in the source, checked with every script aborted, because
   a crawler runs nothing and a page whose scripture arrives by JavaScript is
   a page with no scripture on it. And that the addresses are right: the
   printed chapter number rather than the reader's zero-based index, one
   address per chapter with none of them overwritten, and a chain of real
   anchors from the contents page to all 2,537 of them. */

const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

/* Every index.html under docs/read, which is one per work plus one per
   chapter. Counting the files rather than trusting what the build printed:
   a slug rule that collides writes one file where two chapters were, and
   says nothing. */
function countPages(dir) {
  let n = 0;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) n += countPages(path.join(dir, entry.name));
    else if (entry.name === 'index.html') n++;
  }
  return n;
}

module.exports = async function crawlable(t, ctx) {
  const docs = path.join(ctx.root, 'docs');

  try {
    execFileSync('python3', [path.join(ctx.root, 'tools', 'build_pages.py'), docs],
                 { stdio: 'pipe' });
  } catch (e) {
    t.check('the page build runs', false, String(e.message).split('\n')[0]);
    return;
  }
  t.check('the page build runs', true);

  const manifest = JSON.parse(
    fs.readFileSync(path.join(docs, 'data', 'manifest.json'), 'utf8'));
  const expected = manifest.totals.works + manifest.totals.chapters;
  const written = countPages(path.join(docs, 'read'));
  t.check('one page per work and one per chapter, none of them lost',
          written === expected, written + ' of ' + expected);

  /* Jubilees opens with a prologue printed as chapter 0. The obvious slug
     rule -- the number, or the position when there is no number -- files it
     at chapter 1's address, where chapter 1 then lands on top of it: a
     chapter gone, and every count still plausible. */
  t.check('the Jubilees prologue has an address of its own',
          fs.existsSync(path.join(docs, 'read', 'jubilees', 'jubilees-prologue',
                                  'index.html')));

  /* Four shapes of chapter label, which need four different answers from
     chapter_heading(). Checked as built titles rather than by calling the
     function, because the title is the thing that gets indexed.

       prefix      the label opens with the work's name  (Jubilees)
       word run    the label repeats the title's first words, but is not a
                   prefix of the whole title  (the Enoch volumes)
       borrowed    the label names the work without matching its opening
                   (the Testaments: "Judah 1" under "The Testament of Judah")
       degenerate  the label is the title and nothing else (Hermas's
                   "Similitude 1"), so dropping the repeat leaves nothing and
                   the title alone has to be the answer -- not a bare dash,
                   and not the number said twice.

     The last is the one with no margin: it is a single-chapter work, so
     there is no sibling page to notice a wrong answer by. */
  const SHAPES = [
    ['similitude-1/1', 'Similitude 1 — The Book'],
    ['jubilees/jubilees-prologue', 'Jubilees Prologue — The Book'],
    ['jubilees/1', 'Jubilees 1 — The Book'],
    ['the-testament-of-judah/1', 'The Testament of Judah 1 — The Book'],
    ['1-enoch-the-book-of-the-watchers-chapters-1-36/1',
     '1 Enoch: the Book of the Watchers (Chapters 1-36) 1 — The Book'],
    ['genesis/1', 'Genesis 1 — The Book']
  ];
  const wrongly = SHAPES.filter(([where, want]) => {
    const html = fs.readFileSync(
      path.join(docs, 'read', where, 'index.html'), 'utf8');
    const got = (/<title>([^<]*)<\/title>/.exec(html) || [])[1];
    return got !== want;
  });
  t.check('a repeated work name is dropped without eating the chapter',
          wrongly.length === 0,
          wrongly.map(w => w[0]).join(', ') || SHAPES.length + ' shapes');

  const page = ctx.tally.watch(await ctx.browser.newPage(), 'crawlable');
  /* A crawler runs nothing. Anything that only appears once a script has run
     is, to the thing being served here, not on the page at all. */
  await page.route('**/*.js', r => r.abort());

  await page.goto(ctx.base + 'read/genesis/1/');
  const body = await page.locator('body').innerText();
  t.check('the scripture is in the HTML with every script blocked',
          body.indexOf('In the beginning, God created') !== -1,
          body.slice(0, 40).replace(/\s+/g, ' '));

  t.check('the chapter has a title of its own',
          (await page.title()) === 'Genesis 1 — The Book', await page.title());

  const canonical = await page.getAttribute('link[rel=canonical]', 'href');
  t.check('and a canonical pointing at its own absolute address',
          canonical === 'https://thebookandme.com/read/genesis/1/',
          canonical);

  const ld = await page.locator('script[type="application/ld+json"]').textContent();
  let parsed = null;
  try { parsed = JSON.parse(ld); } catch (e) { /* reported by the check */ }
  t.check('the structured data parses and says what the page is',
          !!parsed && parsed['@type'] === 'Chapter' && parsed.name === 'Genesis 1',
          parsed ? parsed['@type'] : 'did not parse');

  /* The reader's hash routes count from zero, so #/read/genesis/1 is Genesis
     2. Carrying that into a public URL would put every chapter one address
     off its own name. */
  await page.goto(ctx.base + 'read/genesis/2/');
  const two = await page.locator('.reader').innerText();
  t.check('the address is the printed chapter, not the reader\'s index',
          two.indexOf('The heavens, the earth, and all their vast array') !== -1 &&
          two.indexOf('Now the serpent was more subtle') === -1,
          two.slice(0, 50).replace(/\s+/g, ' '));

  /* The threads are the argument. Eleven of them, each following one
     question across eight hundred years of writing, and until now the only
     part of the site with no address a crawler could ask for or a preview
     could unfurl -- while 2,537 chapters, which are in every Bible ever
     printed, all had one. The passages have to be here with the scripts
     blocked for the same reason the scripture does. */
  await page.goto(ctx.base + 'threads/the-dead/');
  const thread = await page.locator('body').innerText();
  t.check('a thread is a real page, with its passages in the HTML',
          thread.indexOf('You dry bones, hear Yahweh') !== -1 &&
          thread.indexOf('Where do the dead go?') !== -1,
          thread.slice(0, 40).replace(/\s+/g, ' '));

  const stopLinks = await page.locator('a[href*="../read/"], a[href*="read/"]').count();
  t.check('and every stop links the chapter it quotes',
          stopLinks >= 10, stopLinks + ' links');

  t.check('the thread page names itself rather than the site',
          (await page.title()).indexOf('Where do the dead go?') === 0,
          await page.title());

  await page.goto(ctx.base + 'threads/');
  const hub = await page.locator('body').innerText();
  t.check('the threads hub lists all eleven as real anchors',
          (await page.locator('.thread-list a').count()) === 11,
          await page.locator('.thread-list a').count() + ' of 11');

  /* The one thread that reaches furthest back reads its span off the eras it
     actually touches. Its third stop is the Isaiah apocalypse, which this
     volume files in Section II with the rest of Isaiah 1-39, so reading the
     ends of the list gave "IV to IX" for a thread that runs II to IX. */
  t.check('and says how far each one travels, from the eras it reaches',
          hub.indexOf('II to IX') !== -1, hub.slice(0, 60).replace(/\s+/g, ' '));

  /* The axis, which the reader draws as positioned bars: a crawler sees no
     canvas and neither does anybody with the stylesheet off, so the same
     reordering is written out in words. */
  await page.goto(ctx.base + 'timeline/');
  const axis = await page.locator('body').innerText();
  t.check('the timeline is a real page with the ranges in words',
          /760.760.750 BCE|760-750 BCE|760–750 BCE/.test(axis) &&
          axis.indexOf('Amos') !== -1,
          axis.slice(0, 50).replace(/\s+/g, ' '));
  t.check('and says which of its ranges are not one date',
          /are not one date/.test(axis));

  /* Two hops from here to any chapter in the library: this page links every
     work, and every work page links every one of its chapters. */
  await page.goto(ctx.base + 'contents/');
  const links = await page.locator('a[href*="read/"]').count();
  t.check('the contents page links every work as a real anchor',
          links === manifest.totals.works, links + ' of ' + manifest.totals.works);

  await page.goto(ctx.base + 'read/genesis/1/');
  await page.locator('.pager a[rel=next]').click();
  await page.waitForLoadState('load');
  t.check('and next really walks to the next chapter',
          page.url().endsWith('/read/genesis/2/'), page.url());

  await page.close();

  const BASE_URL = 'https://thebookandme.com';

  /* The sitemap is the list handed to a crawler that has not found the
     contents page. A URL in it with nothing behind it is a 404 reported by
     the site about itself. */
  const xml = fs.readFileSync(path.join(docs, 'sitemap.xml'), 'utf8');
  const locs = (xml.match(/<loc>([^<]+)<\/loc>/g) || [])
    .map(m => m.replace(/<\/?loc>/g, ''));
  /* The root, the contents hub, the timeline, the threads hub, and one page
     per thread -- on top of the work and chapter pages. The threads were the
     last part of the site with no address a crawler could ask for, which was
     the wrong way round: the chapters are in every Bible and the threads are
     the thing this arrangement exists to make possible. */
  const threads = JSON.parse(
    fs.readFileSync(path.join(docs, 'data', 'threads.json'), 'utf8'));
  const extras = 2 + 2 + threads.length;
  t.check('the sitemap lists the root, the hubs, the threads and every page',
          locs.length === expected + extras,
          locs.length + ' of ' + (expected + extras));
  t.check('the timeline and every thread are among them',
          locs.indexOf(BASE_URL + '/timeline/') !== -1 &&
          locs.indexOf(BASE_URL + '/threads/') !== -1 &&
          threads.every(x => locs.indexOf(BASE_URL + '/threads/' + x.id + '/') !== -1),
          threads.length + ' threads');
  t.check('and lists nothing twice',
          new Set(locs).size === locs.length,
          (locs.length - new Set(locs).size) + ' duplicates');

  const BASE = BASE_URL;
  const missing = locs.filter(u => {
    let rel = u.slice(BASE.length).replace(/^\//, '');
    if (rel === '') rel = 'index.html';
    const file = path.join(docs, rel);
    return !fs.existsSync(file) && !fs.existsSync(path.join(file, 'index.html'));
  });
  t.check('and every address in it has a file behind it',
          missing.length === 0, missing.slice(0, 3).join(', '));

  const robots = fs.readFileSync(path.join(docs, 'robots.txt'), 'utf8');
  t.check('robots.txt points at the sitemap and keeps crawlers off the 13 MB copy',
          robots.indexOf(BASE + '/sitemap.xml') !== -1 &&
          /* The path the site is served from, which is nothing at all on the
             custom domain and was /The-Book on the project Pages address.
             robots.txt paths are site-relative, so the rule has to follow
             whatever BASE says rather than name a prefix of its own. */
          robots.indexOf('Disallow: ' + new URL(BASE).pathname.replace(/\/$/, '') +
                         '/the-book.html') !== -1);

  t.check('there is a 404 page for the addresses that are not there',
          fs.existsSync(path.join(docs, '404.html')));
};
