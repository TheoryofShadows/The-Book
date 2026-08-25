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


def chapter_stem(work_id: str, idx: int) -> str:
    """Where the reader will look for this chapter, minus the extension.

    The index, not chapter["n"]. These are two different numbers and they
    disagree for 2,486 of the 2,537 chapters here: "n" is the number printed
    at the head of the chapter, while the reader addresses a chapter by its
    position in work["chapters"] -- what the route #/read/<work>/<i> carries,
    and what ctx.chapter hands to the fetch in docs/assets/app.js.

    This named files by "n" until it was found. A rendered Genesis 1 landed
    at genesis/1 while the reader asked for genesis/0, and so for 98% of the
    library. Nothing caught it because nothing was ever uploaded for it to
    404 against -- and check_audio.py's own default sample, genesis/0, is
    written in the reader's numbering, so the check would have failed on a
    correct render and passed on none.

    It is a function so that there is one rule rather than two, and so
    tests/python/test_render_audio.py can hold it against the reader's own
    URL rather than against a second copy of it.
    """
    return os.path.join(work_id, str(idx))


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
            base = os.path.join(args.out, chapter_stem(work_id, idx))
            opus, meta = base + ".opus", base + ".json"

            # Twenty-eight core-hours will be interrupted. Anything already
            # rendered is left alone, so the run resumes rather than restarts.
            if not args.force and os.path.exists(opus) and os.path.exists(meta):
                skipped += 1
                continue

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
            print(f"{work['title']} {chapter['n']} -> {work_id}/{idx}: "
                  f"{len(index)} verses, "
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
