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
  '.txt': 'text/plain; charset=utf-8',
  /* The manifest and the icons it names. Without these two the server hands
     back application/octet-stream and the install checks are testing
     something no real host does: GitHub Pages serves both with their proper
     types, so serving them wrongly here would let a check pass that the
     live site would fail, or fail one it would pass. */
  '.webmanifest': 'application/manifest+json',
  '.png': 'image/png'
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

   The real files are 1.79 GB on an Internet Archive item, so the suite stands
   in for them: fetch answers the offsets with a synthetic index, and the
   <audio> element is replaced by one that reports a duration and advances a
   playhead on a timer. What is being checked is the page's arithmetic --
   which verse is marked when, what a jump seeks to, what a failure falls back
   to -- and none of that needs a decoder.

   `verses` is [[verse, start, end], ...]; pass null for `index` to make the
   chapter one that has no reading, which is the fallback path. */
function recordedEngine(verses, opts) {
  const o = opts || {};
  return { content: `
    (() => {
      const INDEX = ${JSON.stringify(verses)};
      const FAIL_AUDIO = ${o.failAudio ? 'true' : 'false'};
      const log = []; window.__audio = log;

      /* This stub stands in for a published recording, so the page has to
         be told there is one. The reader gates the recorded voice on
         data-audio="published" on <html> -- a deploy-time switch, because
         nothing has been rendered or uploaded yet and a drawer that offers
         a voice nobody can hear is a drawer that lies. Setting it here is
         how the finished recorded path keeps its tests while the audio
         does not exist. */
      const publish = () => {
        if (!document.documentElement) return false;
        document.documentElement.setAttribute('data-audio', 'published');
        return true;
      };
      // An init script runs before the document element exists, and app.js
      // reads the attribute while it evaluates -- before DOMContentLoaded --
      // so the stamp has to land the moment <html> appears.
      if (!publish()) {
        new MutationObserver((_records, obs) => { if (publish()) obs.disconnect(); })
          .observe(document, { childList: true, subtree: true });
      }

      const realFetch = window.fetch;
      window.fetch = function (url, init) {
        const u = String(url);
        if (u.indexOf('archive.org') !== -1) {
          log.push({ fetched: u });
          /* The page asks once whether the collection exists at all before
             asking it for any chapter. The Internet Archive answers {} for an
             item that is not there, which is exactly what a suite standing in
             for a chapter with no reading should answer too -- a stand-in
             that reported the collection present while refusing every file
             would be testing a state the real service cannot be in. */
          if (u.indexOf('/metadata/') !== -1) {
            return Promise.resolve({
              ok: true,
              json: () => Promise.resolve(
                INDEX ? { metadata: { identifier: 'the-book-read-aloud' } } : {})
            });
          }
          if (!INDEX) return Promise.resolve({ ok: false, status: 404 });
          if (/\\.json$/.test(u)) {
            const d = INDEX[INDEX.length - 1][2] + 0.35;
            return Promise.resolve({
              ok: true, json: () => Promise.resolve({ d: d, v: INDEX })
            });
          }
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
          this.duration = INDEX ? INDEX[INDEX.length - 1][2] + 0.35 : 0;
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


/* Which command runs Python.
 *
 * The checks shell out to the build scripts, and every call site said
 * "python3" -- which is the name on the CI runners and on macOS, and is not
 * a name Windows has. A Windows install provides "py", and ships a
 * python3.exe stub that opens the Microsoft Store rather than running
 * anything, so looking the name up and trusting what answers is not enough:
 * the stub answers, then does the wrong thing.
 *
 * So the interpreter is chosen by asking each candidate for its version and
 * keeping the first that really replies with one. Resolved once and reused;
 * the checks make several of these calls and the probe is a process each.
 */
let PYTHON = null;
function python() {
  if (PYTHON) return PYTHON;
  const candidates = process.platform === 'win32'
    ? [['py', ['-3']], ['python', []], ['python3', []]]
    : [['python3', []], ['python', []]];
  for (const [cmd, prefix] of candidates) {
    try {
      const out = require('child_process').execFileSync(
        cmd, prefix.concat(['--version']),
        { stdio: 'pipe', encoding: 'utf-8' });
      if (/^Python 3\./.test(out.trim())) {
        PYTHON = { cmd, prefix };
        return PYTHON;
      }
    } catch (e) { /* not this one; try the next */ }
  }
  throw new Error('no Python 3 interpreter found (tried ' +
                  candidates.map(c => c[0]).join(', ') + ')');
}

/* execFileSync against whichever interpreter python() found. */
function runPython(args, opts) {
  const { cmd, prefix } = python();
  return require('child_process').execFileSync(
    cmd, prefix.concat(args), opts || { stdio: 'pipe' });
}
module.exports = { serve, launch, Tally, runPython, workingEngine, failingEngine,
                   silentEngine, noEngine, recordedEngine };
