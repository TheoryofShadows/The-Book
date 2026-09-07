# The Book — where things stand

Local clone: `C:\Users\KHK89\Projects\The-Book`
Live: https://thebookandme.com/ (GitHub Pages, deploys from `main`)

## Run it locally

    "C:\Program Files\Python313\python.exe" -m http.server 8347 --directory docs

Then open http://localhost:8347

**Use `C:\Program Files\Python313\python.exe`, not `py`.** The default `py` on
this machine is the experimental free-threading build (3.13t), and packages
with compiled wheels — onnxruntime among them — publish nothing for that ABI.
That is what makes `pip install kokoro-onnx` fail with a wall of dependency
conflicts. The standard build installs it fine.

## Tests

    "C:\Program Files\Python313\python.exe" -m unittest discover -s tests/python -t tests/python   # 484, passing
    node tests/run.js                                                                              # 573, passing

## The narrator — the actual state of it

The bad voice is not a file in this repo. It is the *device's* own
speechSynthesis, which is what the reader falls back to. There is nothing to
delete.

The reader already has a finished "Recorded reading" player — fetch, per-verse
seek, pace control, fallback — pointed at
`https://archive.org/download/the-book-read-aloud/`. **That item does not
exist**; the metadata API returns `{}`. The option is correctly hidden until
it does: the switch is `data-audio` on `<html>` in docs/index.html.

So the work is: render the audio, upload it, flip the switch.

### Rendering

Model is downloaded to `source/voice/` (gitignored, 338 MB):
`kokoro-fp32.onnx` + `voices-v1.0.bin`.

    "C:\Program Files\Python313\python.exe" tools/render_audio.py --only psalms --out dist/audio

Measured on this machine: **~2.7x realtime**, better than the 4.1x in the
script's own docstring. Whole library ≈ 116 h of audio, 1.79 GB, ~18–20
core-hours.

Voice is `VOICE = "bm_lewis"` at tools/render_audio.py:61 — chosen, and the
full-library render is running in it. Auditions of seven
voices on Psalm 23 are in `dist/voice-audition/`. It was picked: the deep British male reading, which is the register most
people have heard scripture read in.

**Resuming:** the render skips chapters that already have both files, so it is
safe to stop and safe to re-run. Same command as above. Full instructions,
including the upload, are in `dist/RESUME-RENDER.txt`. Do not change the voice
partway: the skip keys on the file existing, not on which voice made it, so a
change mid-run leaves the library in two voices.

### Uploading (needs your account — not automatable from here)

1.79 GB will not fit the Pages artifact (1 GB cap), which is why it goes to
archive.org as item `the-book-read-aloud`, laid out `<work>/<chapter>.opus`
with `<chapter>.json` beside it. Then set `data-audio="published"` on `<html>`
in docs/index.html, and `tools/check_audio.py` starts checking it both ways.

## Branches, none pushed

`windows-portability` — three commits, all verified:

- UTF-8 decode for the build scripts' output (was mangling an en dash on
  Windows; 484 tests now pass)
- Interpreter resolution instead of a hardcoded `python3` (the browser suite
  could not start on Windows at all). With both in, the suites run clean here:
  **484 Python tests and 573 browser checks, 0 failures.**
- This file.

`update-actions` — the six GitHub Actions brought to current majors. Separate
because three of them (configure-pages, upload-pages-artifact, deploy-pages)
sit on the deploy path, and the deploy job only ever runs on `main` — so
merging is the first time they run for real. Watch that run.

Both are pushed and open:

- **PR #40** — the two Windows fixes. https://github.com/TheoryofShadows/The-Book/pull/40
- **PR #41** — the actions bump. https://github.com/TheoryofShadows/The-Book/pull/41

A first red mark on either is probably not real: the workflow cancels its own
older run when a branch push and a pull request land on the same commit
("Canceling since a higher priority waiting request exists"), which is
checks.yml working as its comments describe. Read the newest run.

## Packages — checked, nothing to do

`npm audit` clean, 0 vulnerabilities. The site itself ships **zero**
dependencies: no framework, no CDN, hand-written JS and CSS. playwright is one
minor behind, axe-core current. The GitHub Actions are 1–3 majors behind
— done on `update-actions`, see above. CI plumbing, invisible to readers.
