#!/usr/bin/env python3
"""Render the library to audio, one file per chapter, with verse offsets.

    pip install kokoro-onnx soundfile numpy
    ./tools/render_audio.py --models source/voice --out dist/audio
    ./tools/render_audio.py --out dist/audio --only genesis,psalms,daniel

An audiobook of a 1.13-million-word library cannot be recorded, and no
recording of these translations exists in the public domain. The browser's own
speechSynthesis was the answer to that for as long as the only voice available
was the operating system's, and the ceiling of that approach is the reason
this file exists: the audio belongs to the device, and on a phone out of the
box it is the thin compact set.

A neural voice good enough to read scripture cannot run in the browser. Kokoro
was measured at 0.43x realtime in Chromium on one thread -- thirty-one seconds
of arithmetic for thirteen seconds of speech -- because WebAssembly has no
threads here (GitHub Pages cannot send the COOP/COEP headers that would allow
them) and the model is transformer-heavy. So the arithmetic is done once,
here, and the result is served.

WHY ONE FILE PER CHAPTER, AND WHY PER-VERSE SYNTHESIS

The chapter is the unit the reader fetches and the unit a listener sits
through, so it is one request and one <audio> element: seeking is then
currentTime, and speed is playbackRate, which browsers time-stretch without
shifting pitch. Neither has to be built.

But each verse is synthesised on its own and the offsets recorded as they
accumulate. That is what makes the verse marks exact. The alternative --
render the chapter as one utterance and recover verse boundaries afterwards --
means forced alignment, which is a second model, an approximation, and a new
way for the highlight to drift halfway through Jeremiah. Synthesising the
piece you want the boundary of is cheaper and exact.

The cost is that prosody does not run across a verse boundary. That is the
right trade here, and not really a cost: the reader already speaks
verse-granularly with a pause between, because that is how these texts are
read.

WHAT IT COSTS, measured on Genesis 1, Daniel 3 and Psalm 23

    4.1x realtime, one core          116 hours of audio for the whole library
    1.79 GB as Opus at 34 kbps       28 core-hours to render
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import speakable as speakable_rule                              # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)

VOICE = "bm_lewis"
RATE = 24000

# Silence between verses. The reader's own transport rests between pieces --
# restAfter() in docs/assets/app.js -- and this is the same beat, baked in so
# a chapter plays as one continuous file rather than needing the page to sit
# on a timer between verses.
GAP = 0.35

# Kokoro's style vectors are indexed by token count and there are 510 of them,
# so a verse longer than that has to be broken. Broken at a clause, for the
# reason splitLong() gives in app.js: an engine drops its pitch and takes a
# breath at the end of every utterance, so a break mid-clause is heard as a
# full stop that is not there.
MAX_TOKENS = 500
CLAUSE = (";", ":", ",", "—", "–")


def load_engine(models: str):
    """Import and construct the engine, with a useful failure if it is absent.

    Imported here rather than at module scope so that tools/lint.sh, which
    byte-compiles every script in this directory, does not need half a
    gigabyte of wheels installed to check that this one parses.
    """
    try:
        from kokoro_onnx import Kokoro
    except ImportError:
        raise SystemExit(
            "render_audio.py needs the Kokoro runtime:\n"
            "  pip install kokoro-onnx soundfile numpy\n"
            "and the model files under --models (see the README).")

    model = os.path.join(models, "kokoro-fp32.onnx")
    voices = os.path.join(models, "voices-v1.0.bin")
    for path in (model, voices):
        if not os.path.exists(path):
            raise SystemExit(
                f"missing {path}\n"
                "Download them once:\n"
                "  curl -L -o kokoro-fp32.onnx https://huggingface.co/"
                "onnx-community/Kokoro-82M-v1.0-ONNX/resolve/main/onnx/model.onnx\n"
                "  curl -L -o voices-v1.0.bin https://github.com/thewh1teagle/"
                "kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin\n"
                "Full precision on purpose: the quantised builds are both worse "
                "and slower -- q8f16 measured 0.73x against fp32's 4.0x.")
    return Kokoro(model, voices)


def chapter_paths(folder, idx):
    """Where a chapter's two files go, given its position in the work.

    A function rather than two lines inline because it is the one rule in
    this script that another program depends on: docs/assets/app.js builds
    its address from the same index, so #/read/psalms/22 is the
    twenty-third chapter and fetches psalms/22.opus.

    Naming these by chapter["n"], the printed chapter number, agrees with
    that only where a work's first chapter is numbered zero -- and of 172
    works exactly one is. It put every file one place off: tapping Psalm 23
    played Psalm 22, in a good voice, with the verse marks landing where
    they should, and the last chapter of every book fetched a file that was
    not there. Nothing about it looked broken.

    tests/python/test_audio_layout.py calls this directly, so the rule is
    held by what it does rather than by how it is spelt.
    """
    base = os.path.join(folder, str(idx))
    return base + ".opus", base + ".json"


def _holds(meta_path, chapter):
    """Does the index at this address describe this chapter?

    Compares the verse count, which is what distinguishes a chapter from its
    neighbour and is the same check tests/python/test_audio_layout.py makes of
    the finished render. An unreadable index counts as not holding it: better
    to spend a minute re-rendering than to keep a file nothing can vouch for.
    """
    try:
        with open(meta_path, encoding="utf-8") as fh:
            index = json.load(fh)
        verses = index.get("v")
    except (OSError, ValueError, AttributeError):
        return False
    # A half-written index can hold anything, including a null where the list
    # should be. Asking len() of that raised inside the resume check, which
    # would have ended a twenty-five hour render on a file it was supposed to
    # be defending against.
    if not isinstance(verses, list):
        return False
    return len(verses) == len(chapter.get("verses", []))


def split_long(text: str) -> list[str]:
    """Break a verse too long for the model, at a clause where one exists."""
    if len(text) <= MAX_TOKENS:
        return [text]

    out, rest = [], text
    while len(rest) > MAX_TOKENS:
        window = rest[:MAX_TOKENS]
        cut = max(window.rfind(c) for c in CLAUSE)
        if cut < MAX_TOKENS // 2:               # no clause worth the pause
            cut = window.rfind(" ")
        if cut <= 0:
            cut = MAX_TOKENS
        out.append(rest[:cut + 1].strip())
        rest = rest[cut + 1:].lstrip()
    if rest:
        out.append(rest)
    return out


def render_chapter(engine, chapter, editorial, np):
    """One chapter's audio and its verse index, or None if it has no text."""
    gap = np.zeros(int(GAP * RATE), dtype=np.float32)
    pieces, index = [], []
    at = 0.0
    chars = 0

    for verse in chapter.get("verses", []):
        said = speakable_rule.speakable(verse["t"], editorial)
        if not said.strip():
            # A verse that is nothing but apparatus has nothing to say, and an
            # empty utterance makes several engines report a failure.
            continue
        chars += len(said)

        start = at
        for part in split_long(said):
            samples, rate = engine.create(part, voice=VOICE, speed=1.0,
                                          lang="en-us")
            audio = np.asarray(samples, dtype=np.float32)
            pieces.append(audio)
            at += len(audio) / rate
        index.append([verse["v"], round(start, 3), round(at, 3)])

        pieces.append(gap)
        at += GAP

    if not index:
        return None
    return np.concatenate(pieces), index, chars


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--models", default=os.path.join(ROOT, "source", "voice"),
                    help="where kokoro-fp32.onnx and voices-v1.0.bin live")
    ap.add_argument("--data", default=os.path.join(ROOT, "docs", "data"))
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", "audio"))
    ap.add_argument("--only", default="",
                    help="comma-separated work ids, for a partial render")
    ap.add_argument("--force", action="store_true",
                    help="re-render chapters that are already done")
    args = ap.parse_args()

    try:
        import numpy as np
        import soundfile as sf
    except ImportError:
        raise SystemExit("render_audio.py needs numpy and soundfile:\n"
                         "  pip install kokoro-onnx soundfile numpy")

    works_dir = os.path.join(args.data, "works")
    wanted = {w.strip() for w in args.only.split(",") if w.strip()}

    engine = load_engine(args.models)
    editorial = speakable_rule.editorial_pattern()

    names = sorted(n for n in os.listdir(works_dir) if n.endswith(".json"))
    if wanted:
        names = [n for n in names if n[:-5] in wanted]
        missing = wanted - {n[:-5] for n in names}
        if missing:
            raise SystemExit("no such work: " + ", ".join(sorted(missing)))

    started = time.time()
    done = skipped = 0
    total_audio = total_chars = 0.0
    total_bytes = 0

    for name in names:
        work_id = name[:-5]
        with open(os.path.join(works_dir, name), encoding="utf-8") as fh:
            work = json.load(fh)

        folder = os.path.join(args.out, work_id)
        os.makedirs(folder, exist_ok=True)

        for idx, chapter in enumerate(work.get("chapters", [])):
            opus, meta = chapter_paths(folder, idx)

            # Twenty-eight core-hours will be interrupted. Anything already
            # rendered is left alone, so the run resumes rather than restarts.
            #
            # But "already rendered" has to mean the right chapter, not just a
            # file with the right name. A dist/ from before the naming was
            # fixed holds n-named files, and those overlap the index names
            # almost everywhere: for Psalms, 1..150 against 0..149 collide at
            # 1..149. Resuming such a render with existence as the only test
            # would skip 149 chapters as done while each held the previous
            # chapter's audio, render only index 0, and report a clean resume.
            # That is this exact bug, recreated by the thing meant to be safe.
            #
            # So the index is opened and its verse count compared with the
            # chapter's. It is cheap next to synthesis, it is the same
            # property test_audio_layout.py asserts, and it is wrong exactly
            # when the file belongs to a different chapter.
            if not args.force and os.path.exists(opus) and os.path.exists(meta):
                if _holds(meta, chapter):
                    skipped += 1
                    continue
                print("  re-rendering %s/%s: the file there is not this "
                      "chapter" % (work_id, idx))

            t0 = time.time()
            rendered = render_chapter(engine, chapter, editorial, np)
            if rendered is None:
                continue
            audio, index, chars = rendered
            duration = len(audio) / RATE

            sf.write(opus, audio, RATE, format="OGG", subtype="OPUS")
            with open(meta, "w", encoding="utf-8") as fh:
                json.dump({"d": round(duration, 3), "v": index}, fh,
                          separators=(",", ":"))

            done += 1
            total_audio += duration
            total_chars += chars
            total_bytes += os.path.getsize(opus)
            print(f"{work['title']} {chapter['n']}: {len(index)} verses, "
                  f"{duration/60:.1f} min, {os.path.getsize(opus)/1024:.0f} KB, "
                  f"{duration/(time.time()-t0):.1f}x realtime", flush=True)

    wall = time.time() - started
    print(f"\n{done} chapters rendered, {skipped} already done, "
          f"in {wall/60:.1f} min")
    if total_audio:
        print(f"  {total_audio/3600:.2f} hours of audio, "
              f"{total_bytes/1e6:.1f} MB, "
              f"{total_audio/wall:.1f}x realtime overall")


if __name__ == "__main__":
    main()
