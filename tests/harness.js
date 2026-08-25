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
  '.svg': 'image/svg+xml',
  '.xml': 'application/xml; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8'
};

/* A static file server, so the checks need nothing installed to serve with. */
function serve(root) {
  const server = http.createServer((req, res) => {
    const rel = decodeURIComponent(req.url.split('?')[0].split('#')[0]);
    let file = path.join(root, rel);
    if (!file.startsWith(path.resolve(root))) { res.writeHead(403).end(); return; }
    /* A directory is its index.html, which is what GitHub Pages does and what
       every one of the prerendered pages depends on: they live at
       /read/genesis/1/ and nowhere else. Without this the pages built by
       tools/build_pages.py are reachable on the live site and unreachable
       here -- a gap that hides itself, because the only thing that would
       report it is the check that cannot load the page. */
    let dir = false;
    try { dir = fs.statSync(file).isDirectory(); } catch (e) { dir = false; }
    if (rel.endsWith('/') || dir) file = path.join(file, 'index.html');
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

/* Speaks: records each utterance, fires start, one word boundary, then end.
   A voice list can be supplied to stand in for a particular device's drawer
   -- the point of several of the listening checks is which voice out of a
   bad drawer the reader picks up. */
function workingEngine(msPerUtterance, voiceList) {
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
      const voices = ${JSON.stringify(voiceList || [
        { name: 'Test English', lang: 'en-US', voiceURI: 'test-en', default: true },
        { name: 'Test French', lang: 'fr-FR', voiceURI: 'test-fr', default: false }
      ])};
      let current = null, timer = null;
      const synth = new EventTarget();
      synth.getVoices = () => voices;
      synth.speak = u => {
        current = u;
        // The moment matters as well as the words: the gaps between pieces
        // are what a chapter sounds like rather than a list read out.
        log.push({ text: u.text, rate: u.rate, at: performance.now(),
                   voice: u.voice ? u.voice.voiceURI : null });
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

/* The recorded reading, without the recording.

   Two halves are stubbed, because the reader now fetches them from two
   places. The manifest and the per-work offsets are same-origin data, so
   window.fetch is patched for those paths; the audio is a release asset, so
   the <audio> element is replaced by one that reports a duration and advances
   a playhead on a timer. What is being checked is the page's arithmetic --
   which verse is marked when, what a jump seeks to, when a chapter stops,
   what a failure falls back to -- and none of that needs a decoder.

   `rows` is [[verse, start, end], ...] for the chapter under test, in
   offsets relative to the start of that chapter. Pass null to publish
   nothing at all, which is the fallback path.

   The chapter is deliberately NOT placed at the start of the work file.
   One asset holds the whole work, so every offset the reader uses is the
   chapter's own start plus the verse's offset within it, and a fixture that
   began at zero would pass whether or not that addition happened. AT is
   where the chapter sits. */
const CHAPTER_AT = 100;

function recordedEngine(rows, opts) {
  const o = opts || {};
  return { content: `
    (() => {
      const ROWS = ${JSON.stringify(rows)};
      const AT = ${o.at === undefined ? CHAPTER_AT : o.at};
      const GAP = ${o.gap === undefined ? 0.35 : o.gap};
      const WORK = ${JSON.stringify(o.work || 'amos')};
      const CH = ${o.chapter === undefined ? 2 : o.chapter};
      const CHAPTERS = ${o.chapters === undefined ? 9 : o.chapters};
      const FAIL_AUDIO = ${o.failAudio ? 'true' : 'false'};
      const BASE = 'https://releases.example.invalid/audio-v1/';
      const log = []; window.__audio = log;

      /* The work's index, built around the one chapter under test. Every
         other chapter of the work gets a span too, so that running off the
         end of this one has somewhere to go and the reader can advance. */
      function workIndex() {
        if (!ROWS) return null;
        const span = ROWS[ROWS.length - 1][2] + GAP;
        const c = [];
        for (let i = 0; i < CHAPTERS; i++) {
          c.push(i === CH ? [AT, AT + span]
                          : [i * 5 + (i > CH ? AT + span : 0),
                             i * 5 + 4 + (i > CH ? AT + span : 0)]);
        }
        const v = {};
        v[String(CH)] = ROWS.map(r => [r[0], AT + r[1], AT + r[2]]);
        return { src: WORK + '.opus', d: AT + span + 20, gap: GAP, c: c, v: v };
      }

      const MANIFEST = ROWS
        ? { base: BASE,
            works: { [WORK]: { src: WORK + '.opus',
                               narrator: 'A Test Narrator',
                               licence: 'Public domain',
                               url: 'https://example.invalid/reading' } } }
        : { base: '', works: {} };

      const realFetch = window.fetch;
      const MANIFEST_PATH = 'data/audio.json';
      const INDEX_DIR = 'data/audio/';
      window.fetch = function (url, init) {
        const u = String(url).split('?')[0];
        if (u.endsWith(MANIFEST_PATH)) {
          log.push({ fetched: 'manifest' });
          return Promise.resolve({
            ok: true, json: () => Promise.resolve(MANIFEST)
          });
        }
        const at = u.indexOf(INDEX_DIR);
        if (at !== -1 && u.endsWith('.json')) {
          const work = u.slice(at + INDEX_DIR.length, -5);
          log.push({ fetched: 'index:' + work });
          const idx = work === WORK ? workIndex() : null;
          if (!idx) return Promise.resolve({ ok: false, status: 404 });
          return Promise.resolve({ ok: true, json: () => Promise.resolve(idx) });
        }
        return realFetch.apply(this, arguments);
      };

      /* An <audio> that keeps time without decoding anything. currentTime is
         writable here, which it is on a real element too once metadata has
         arrived -- the seek in audioPlayFrom() is the thing under test. */
      class FakeAudio extends EventTarget {
        constructor() {
          super();
          this._t = 0; this._timer = null; this._src = '';
          this.playbackRate = 1; this.preload = 'none'; this.readyState = 0;
          const idx = workIndex();
          this.duration = idx ? idx.d : 0;
          window.__player = this;
        }
        get currentTime() { return this._t; }
        set currentTime(v) { this._t = v; log.push({ seek: v }); }
        getAttribute(k) { return k === 'src' ? this._src : null; }
        setAttribute(k, v) { if (k === 'src') { this._src = v; log.push({ src: v }); } }
        load() {
          this.readyState = 1;
          setTimeout(() => this.dispatchEvent(new Event('loadedmetadata')), 5);
          if (FAIL_AUDIO) setTimeout(() => this.dispatchEvent(new Event('error')), 10);
        }
        play() {
          log.push({ play: this._t });
          this.paused = false;
          clearInterval(this._timer);
          this._timer = setInterval(() => {
            this._t += 0.1 * this.playbackRate;
            if (this._t >= this.duration) {
              this._t = this.duration;
              clearInterval(this._timer);
              this.dispatchEvent(new Event('ended'));
              return;
            }
            this.dispatchEvent(new Event('timeupdate'));
          }, 20);
          return Promise.resolve();
        }
        pause() { this.paused = true; clearInterval(this._timer); log.push({ pause: this._t }); }
      }
      FakeAudio.prototype.paused = true;
      window.Audio = FakeAudio;
    })();
  ` };
}

module.exports = { serve, launch, Tally, workingEngine, failingEngine,
                   silentEngine, noEngine, recordedEngine, CHAPTER_AT };
