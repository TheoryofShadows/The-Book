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
    node tests/run.js                                                                              # browser checks

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

Voice is `VOICE = "bm_lewis"` at tools/render_audio.py:61. Auditions of seven
voices on Psalm 23 are in `dist/voice-audition/`. **Pick one before committing
to a full render** — changing it afterwards means redoing everything.

### Uploading (needs your account — not automatable from here)

1.79 GB will not fit the Pages artifact (1 GB cap), which is why it goes to
archive.org as item `the-book-read-aloud`, laid out `<work>/<chapter>.opus`
with `<chapter>.json` beside it. Then set `data-audio="published"` on `<html>`
in docs/index.html, and `tools/check_audio.py` starts checking it both ways.

## Branch `windows-portability`

Two commits, both verified, neither pushed:

- UTF-8 decode for the build scripts' output (was mangling an en dash on
  Windows; 484 tests now pass)
- Interpreter resolution instead of a hardcoded `python3` (the browser suite
  could not start on Windows at all)

Push and open a PR when you want them in.

## Packages — checked, nothing to do

`npm audit` clean, 0 vulnerabilities. The site itself ships **zero**
dependencies: no framework, no CDN, hand-written JS and CSS. playwright is one
minor behind, axe-core current. The GitHub Actions are 1–3 majors behind
(checkout v4→v7, setup-node v4→v7, setup-python v5→v7, configure-pages v5→v6,
deploy-pages v4→v5, upload-pages-artifact v3→v5) — CI plumbing, invisible to
readers, and the Pages ones touch the deploy path so bump them on a branch.
