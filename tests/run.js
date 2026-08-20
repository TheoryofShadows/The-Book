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

const SUITES = ['routes', 'layout', 'search', 'words', 'keeping',
                'resilience', 'listening', 'offline'];

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
  const ctx = { browser, base: site.url, root, tally };
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

  const seconds = ((Date.now() - started) / 1000).toFixed(1);
  console.log(`\n${tally.passed} passed, ${tally.failed.length} failed, in ${seconds}s`);
  if (tally.failed.length) {
    console.log('\nFailures:');
    tally.failed.forEach(f => console.log('  · ' + f));
    process.exit(1);
  }
}

main().catch(e => { console.error(e); process.exit(1); });
