'use strict';

/* Browser checks for the reader.
 *
 *   node tests/run.js               everything
 *   node tests/run.js listening     one suite
 *
 * Needs Node and Playwright's Chromium. CHROME_PATH points it at a browser
 * that is already on the machine instead of fetching one.
 */

const path = require('path');
const { serve, launch, Tally } = require('./harness');

/* 'offline' builds the single-file copy and hands it to 'map', so it runs
   first of the two. run.js clears what it left behind at the end. */
const SUITES = ['routes', 'layout', 'search', 'words', 'keeping',
                'dating', 'resilience', 'listening', 'access', 'crawlable',
                'installable', 'caching', 'offline', 'map'];

async function main() {
  const wanted = process.argv.slice(2);
  const suites = wanted.length ? wanted : SUITES;
  const unknown = suites.filter(s => SUITES.indexOf(s) < 0);
  if (unknown.length) {
    console.error('No such suite: ' + unknown.join(', ') + '\nHave: ' + SUITES.join(', '));
    process.exit(2);
  }

  try {
    require.resolve('playwright');
  } catch (e) {
    console.error('Playwright is not installed. From the repository root:\n' +
                  '  npm --prefix tests install\n' +
                  '  npx playwright install chromium');
    process.exit(2);
  }

  const root = path.resolve(__dirname, '..');

  /* The worker is generated and gitignored, so a clean checkout does not have
     one -- and the page registers it from the head of index.html, so without
     this every suite that opens the site logs a 404 for a script and every
     watched page reports it as a failure. That is exactly what happened: this
     passed locally, where tools/build.sh had already made the file, and
     failed in CI, where the reader job runs these checks without building
     anything. The suite needs the file, so the suite makes it, the same way
     offline.test.js makes the single-file copy it opens. */
  try {
    require('child_process').execFileSync(
      'python3', [path.join(root, 'tools', 'build_sw.py'), path.join(root, 'docs')],
      { stdio: 'pipe' });
  } catch (e) {
    console.error('Could not build the service worker: ' +
                  String(e.message).split('\n')[0]);
    process.exit(2);
  }

  const site = await serve(path.join(root, 'docs'));
  let browser;
  try {
    browser = await launch();
  } catch (e) {
    await site.close();
    console.error('Could not start a browser: ' + String(e.message).split('\n')[0] +
                  '\nRun `npx playwright install chromium`, or set CHROME_PATH to a ' +
                  'Chromium or Chrome already on this machine.');
    process.exit(2);
  }

  const tally = new Tally();
  const ctx = { browser, base: site.url, root, tally, cleanup: [] };
  const started = Date.now();

  for (const name of suites) {
    console.log('\n' + name);
    try {
      await require('./' + name + '.test.js')(tally, ctx);
    } catch (e) {
      tally.check(name + ': suite ran to the end', false, String(e.message).split('\n')[0]);
    }
  }

  await browser.close();
  await site.close();
  ctx.cleanup.forEach(dir => {
    try { require('fs').rmSync(dir, { recursive: true, force: true }); }
    catch (e) { /* a temp directory that will not go is not a test failure */ }
  });

  const seconds = ((Date.now() - started) / 1000).toFixed(1);
  console.log(`\n${tally.passed} passed, ${tally.failed.length} failed, in ${seconds}s`);
  if (tally.failed.length) {
    console.log('\nFailures:');
    tally.failed.forEach(f => console.log('  · ' + f));
    process.exit(1);
  }
}

main().catch(e => { console.error(e); process.exit(1); });
