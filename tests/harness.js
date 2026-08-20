'use strict';

/* Shared machinery for the browser checks: a static server, a browser, a
   tally, and stand-in speech engines.

   Headless browsers have no speech engine of their own -- the one these
   checks run in reports zero voices and fails every utterance -- so the
   engine is replaced with one that records what it was asked to say and
   fires the events a real one fires. Everything above that line is the
   site's own code, unmodified. What cannot be checked here, and is not
   claimed anywhere, is whether a real voice sounds right. */

const http = require('http');
const fs = require('fs');
const path = require('path');

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml'
};

/* A static file server, so the checks need nothing installed to serve with. */
function serve(root) {
  const server = http.createServer((req, res) => {
    const rel = decodeURIComponent(req.url.split('?')[0].split('#')[0]);
    let file = path.join(root, rel === '/' ? 'index.html' : rel);
    if (!file.startsWith(path.resolve(root))) { res.writeHead(403).end(); return; }
    fs.readFile(file, (err, body) => {
      if (err) { res.writeHead(404).end('not found'); return; }
      res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream' });
      res.end(body);
    });
  });
  return new Promise(resolve => {
    server.listen(0, '127.0.0.1', () => {
      resolve({
        url: `http://127.0.0.1:${server.address().port}/`,
        close: () => new Promise(done => server.close(done))
      });
    });
  });
}

/* Playwright ships its own Chromium. CHROME_PATH overrides it, which is how
   this runs on a machine that already has one and should not fetch another. */
async function launch() {
  const { chromium } = require('playwright');
  const opts = process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {};
  return chromium.launch(opts);
}

class Tally {
  constructor() { this.passed = 0; this.failed = []; }

  check(name, ok, detail) {
    if (ok) this.passed++;
    else this.failed.push(name + (detail ? ' — ' + detail : ''));
    console.log(`  ${ok ? 'ok  ' : 'FAIL'}  ${name}${detail ? '  (' + detail + ')' : ''}`);
    return ok;
  }

  /* Page errors are failures wherever they happen, so every page gets this. */
  watch(page, label) {
    page.on('pageerror', e => this.check(`${label}: no uncaught error`, false, e.message));
    page.on('console', m => {
      if (m.type() === 'error') this.check(`${label}: no console error`, false, m.text());
    });
    return page;
  }
}

/* ---- stand-in speech engines ----------------------------------------

   These are source strings rather than functions: Playwright serialises an
   init script with toString(), and a bound or generated function stringifies
   to "[native code]", which the page then fails to parse. A string says what
   it means and survives the trip. */

/* Speaks: records each utterance, fires start, one word boundary, then end. */
function workingEngine(msPerUtterance) {
  return { content: `
    (() => {
      const MS = ${Number(msPerUtterance) || 30};
      const log = []; window.__spoken = log;
      class U extends EventTarget {
        constructor(t) { super(); this.text = t; this.rate = 1; this.pitch = 1; }
        set onstart(f) { this._s = f; } get onstart() { return this._s; }
        set onend(f) { this._e = f; } get onend() { return this._e; }
        set onboundary(f) { this._b = f; } get onboundary() { return this._b; }
        set onerror(f) { this._r = f; } get onerror() { return this._r; }
      }
      const voices = [
        { name: 'Test English', lang: 'en-US', voiceURI: 'test-en', default: true },
        { name: 'Test French', lang: 'fr-FR', voiceURI: 'test-fr', default: false }
      ];
      let current = null, timer = null;
      const synth = new EventTarget();
      synth.getVoices = () => voices;
      synth.speak = u => {
        current = u;
        log.push({ text: u.text, rate: u.rate, voice: u.voice ? u.voice.voiceURI : null });
        if (u._s) u._s({});
        timer = setTimeout(() => {
          if (current !== u) return;
          if (u._b) u._b({ name: 'word', charIndex: 0,
                           charLength: (/^\\S+/.exec(u.text) || [''])[0].length });
          timer = setTimeout(() => { if (current === u && u._e) u._e({}); }, Math.max(10, MS / 3));
        }, Math.max(10, MS));
      };
      synth.cancel = () => { current = null; clearTimeout(timer); };
      synth.pause = () => {}; synth.resume = () => {};
      Object.defineProperty(window, 'speechSynthesis', { value: synth, configurable: true });
      window.SpeechSynthesisUtterance = U;
    })();
  ` };
}

const UTTERANCE_CLASS = `
  class U extends EventTarget {
    constructor(t) { super(); this.text = t; this.rate = 1; }
    set onstart(f) { this._s = f; } get onstart() { return this._s; }
    set onend(f) { this._e = f; } get onend() { return this._e; }
    set onboundary(f) { this._b = f; } get onboundary() { return this._b; }
    set onerror(f) { this._r = f; } get onerror() { return this._r; }
  }`;

/* Has the API, has no voice: what a Linux desktop without speech-dispatcher
   does, and what the browser these checks run in does for real. */
function failingEngine() {
  return { content: `
    (() => {
      ${UTTERANCE_CLASS}
      const synth = new EventTarget();
      synth.getVoices = () => [];
      synth.speak = u => setTimeout(() => u._r && u._r({ error: 'synthesis-failed' }), 20);
      synth.cancel = () => {}; synth.pause = () => {}; synth.resume = () => {};
      Object.defineProperty(window, 'speechSynthesis', { value: synth, configurable: true });
      window.SpeechSynthesisUtterance = U;
    })();
  ` };
}

/* Takes the utterance and then never says anything, never reports anything. */
function silentEngine() {
  return { content: `
    (() => {
      ${UTTERANCE_CLASS}
      const synth = new EventTarget();
      synth.getVoices = () => [{ name: 'Ghost', lang: 'en-US', voiceURI: 'ghost', default: true }];
      synth.speak = () => {};
      synth.cancel = () => {}; synth.pause = () => {}; synth.resume = () => {};
      Object.defineProperty(window, 'speechSynthesis', { value: synth, configurable: true });
      window.SpeechSynthesisUtterance = U;
    })();
  ` };
}

/* A browser from before the API existed at all. */
function noEngine() {
  return { content: `
    Object.defineProperty(window, 'speechSynthesis', { value: undefined, configurable: true });
    window.SpeechSynthesisUtterance = undefined;
  ` };
}

module.exports = { serve, launch, Tally, workingEngine, failingEngine, silentEngine, noEngine };
