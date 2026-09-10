# The Book — where things stand

Local clone: `C:\Users\KHK89\Projects\The-Book`
Live: https://thebookandme.com/ (GitHub Pages, deploys from `main`)

## The audio is done. The next thing is posting.

The whole "render, upload, flip the switch" job is finished and verified:

- **Rendered** — 1,559 chapters, 3,118 files, 91.5 hours of audio, 1.34 GB,
  in the `bm_lewis` voice, at 3.6x realtime overall. `dist/render-full.log`
  ends with `[render finished]`.
- **Uploaded** — all 3,118 files are on archive.org as `the-book-read-aloud`.
  `dist/upload.log` ends with `[upload finished]`. The first pass left 50
  files behind; the retry sent them.
- **Switched on** — `data-audio="published"` on `<html>` in docs/index.html,
  deployed, and live: the served page carries it.
- **Verified both ways**, on 2026-09-08:

      "C:\Program Files\Python313\python.exe" tools/verify_audio_upload.py --item the-book-read-aloud --deep 12
      # 3118 rendered, 3118 on the item, 12 chapters read back and correct

      "C:\Program Files\Python313\python.exe" tools/check_audio_live.py --item the-book-read-aloud
      # CORS, verse offsets, HEAD, byte range, real Ogg bytes, duration vs size — all ok

Re-checked on 2026-09-10 after the reading seemed to have gone missing:
it had not. The archive.org item still holds all 3,118 files, Genesis 1
streams 1,067,139 bytes of real Ogg with its verse offsets, the live page
still carries `data-audio="published"`, and `check_audio_live.py` passes
all seven checks. Nothing was lost. What was missing was uncommitted
player work that had never been deployed — now shipped, see below.

## The iPhone could not play the reading, and that is fixed — 2026-09-10

Reported as "it still has the robot voice, where did my rendered audio go".
The audio had gone nowhere. It was never reaching an iPhone, and a bug of ours
made that permanent. Three faults on one path:

1. **The encoding.** The reading is Opus in Ogg — the one common format Apple
   was last to take. Safari either cannot decode it or says "maybe" and then
   fails. On top of that archive.org does not know the `.opus` extension and
   serves it as `application/octet-stream`; Chrome sniffs the bytes and plays
   it regardless, Safari refuses. There is now a **second copy in AAC/mp4**,
   which every iPhone plays and the archive serves as `audio/mp4`.
2. **The gate.** `AUDIO_OK` asked only whether Opus would play, so a browser
   that refused Ogg was refused the reading. It picks a format now.
3. **The one that made it stick.** A recording that failed to play wrote
   `"device"` into the saved voice *permanently*, and the code could not tell
   that from a voice the reader chose by hand. On an iPhone that happened on
   the first chapter opened, and the phone never asked for the recording
   again — however long it had been fixed. A failure now lasts one page, and a
   stamped one-time migration lets go of the value the old build wrote.

**No re-render was needed.** `tools/transcode_aac.py` makes the m4a from the
files already rendered, in 13 minutes, and the verse offsets are reused as
they are: worst duration drift over 1,559 chapters is **0.7 milliseconds**.
Safe to stop and re-run; it skips what is already converted.

    "C:\Program Files\Python313\python.exe" tools/transcode_aac.py
    "C:\Program Files\Python313\python.exe" tools/upload_audio.py

`tools/audit_audio.py` now reads both encodings and holds them against the
same sidecar, so an m4a of the wrong length cannot pass while the Opus looks
fine. 16 tests in `tests/python/test_audit_audio.py`, 635 browser checks.

**The upload of the 1,559 m4a files is the one thing still in flight.** It is
paced deliberately: archive.org queues a task per file and refuses everything
once the bucket queue is deep, so the script waits for it to drain. Re-running
it sends only what is missing.

## The reading was audited chapter by chapter, 2026-09-10

`tools/audit_audio.py` sweeps all 1,559 chapters, reading each file's real
duration out of its Ogg granule positions and checking it against the sidecar,
the verse offsets and the source text. **Nothing is wrong with any of them.**

    "C:\Program Files\Python313\python.exe" tools/audit_audio.py --csv dist/audio-audit.csv

    Swept 1559 chapters, 92.8 hours. Median pace 0.332 s/word.
    No chapter failed any check.

The figures behind that, which are the useful part:

- **Sidecar drift: 0.0000s, maximum.** Every offsets file agrees with its
  audio exactly. Nothing is truncated and nothing overruns.
- **Lead-in silence: 0.00s, maximum.** The bug fixed in `Cross the lead-in
  silence without stopping in it` is gone corpus-wide, not just where it was
  noticed.
- **Tail padding: 0.35s, maximum**, and it is the uniform inter-verse gap
  rather than dead air.
- **Verse-count mismatches: 0** across all 1,559 chapters.
- **Pace: every chapter within 0.88x-1.57x of the median.** The slow end is
  1 Chronicles' genealogies, Ezra and Nehemiah -- long proper nouns, checked
  by hand and reading correctly. The fast end is Leviticus and Deuteronomy's
  legal formulae. Both are the content, not the render.

The sweep was checked against injected faults before its clean result was
believed, and those cases are kept in `tests/python/test_audit_audio.py` (13
tests). A check that has only ever said "fine" reads the same as one that
cannot say anything else.

**What it cannot tell you is whether the voice sounds right.** That is the one
part still needing your ears, and it is a listening job, not a fixing job.

So **LAUNCH.md's precondition is met.** Its posts were written to go out only
once the audio was real, and it is. That is the open task: post them.
Nothing in the repo is waiting on you.

## Run it locally

    "C:\Program Files\Python313\python.exe" -m http.server 8347 --directory docs

Then open http://localhost:8347

**Use `C:\Program Files\Python313\python.exe`, not `py`.** The default `py` on
this machine is the free-threading build (3.13t), and packages with compiled
wheels — onnxruntime among them — publish nothing for that ABI. That is what
makes `pip install kokoro-onnx` fail with a wall of dependency conflicts.

## Tests — both green, 2026-09-08

    "C:\Program Files\Python313\python.exe" -m unittest discover -s tests/python -t tests/python   # 509, passing
    node tests/run.js                                                                              # 614, passing

## Git — clean, and the shelved work is now live

Two commits on 2026-09-10 shipped work that had been sitting uncommitted in
the working tree — built, then left, and so never deployed. That is why the
player and the filters "hadn't stuck": they only ever existed on this machine.

- **fabd602** — the page weight budgets were measured against a server that
  did not compress, while GitHub Pages does. They now weigh what the reader
  actually downloads (209 KB front page, 269 KB chapter) and the request
  counts have no slack, which is the only thing that catches a data file
  landing on the critical path.
- **278fac8** — the audio player redrawn (SVG icons instead of glyphs that
  iOS rendered as blue emoji tiles, a real seek slider, settings behind one
  toggle) and the front page's jump box + canon filter, styled and shipped.
  canon.json is fetched on first reach for the select, not on load.

Tests, 2026-09-10: **629 node, 509 python, all passing.**

## Packages — nothing to do

`npm audit` clean. The site ships **zero** dependencies: no framework, no CDN,
hand-written JS and CSS. The GitHub Actions were brought current on
`update-actions` and merged.
