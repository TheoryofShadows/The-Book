#!/usr/bin/env node
// Draw SVG files to PNG or JPEG with the Chromium the test suite installs.
//
//   echo '[{"svg":"a.svg","out":"a.png","w":512,"h":512}]' | node tools/render_logo.js
//
// Used only by tools/build_logo.py. Nothing here ships to the site.
const fs = require('fs');
const path = require('path');
const { chromium } = require(path.join(__dirname, '..', 'tests', 'node_modules', 'playwright'));

(async () => {
  const jobs = JSON.parse(fs.readFileSync(0, 'utf8'));
  const browser = await chromium.launch();
  try {
    for (const j of jobs) {
      const page = await browser.newPage({ viewport: { width: j.w, height: j.h }, deviceScaleFactor: 1 });
      const svg = fs.readFileSync(j.svg, 'utf8')
        .replace('<svg ', `<svg style="display:block;width:${j.w}px;height:${j.h}px" `);
      await page.setContent(`<!doctype html><html><body style="margin:0;background:transparent">${svg}</body></html>`);
      const jpeg = /\.jpe?g$/i.test(j.out);
      await page.screenshot(Object.assign(
        { path: j.out, clip: { x: 0, y: 0, width: j.w, height: j.h } },
        jpeg ? { type: 'jpeg', quality: 88 } : { type: 'png' }));
      await page.close();
    }
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exit(1); });
