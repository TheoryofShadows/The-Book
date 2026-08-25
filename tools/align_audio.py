#!/usr/bin/env python3
"""Find the verses inside a public-domain reading, and index them.

    pip install ctc-forced-aligner soundfile numpy
    ./tools/align_audio.py --reading enoch-plogue --only 1-enoch-the-book-of-the-watchers
    ./tools/align_audio.py --reading web-altman --out dist/audio

People have already read these texts aloud and put the recordings in the
public domain. What they have not done is say where each verse begins, and
that is the one thing the reader needs: it marks the verse being spoken, it
seeks to a verse, and it remembers a place as a verse. A chapter of audio
with no offsets is a file that plays under a still page.

So the offsets are computed here, once, by forced alignment: the audio and
the text we already have, matched against each other to find where in the
recording each word falls. Verse granularity is a forgiving target -- a fifth
of a second either way at a boundary is inaudible -- which is why this works
at all on recordings made by volunteers in domestic rooms.

WHY THE ALIGNMENT IS ALSO THE AUDIT

A recording has to be of the same EDITION as the text on the page. This
volume prints the World English Bible, Charles's Enoch and Jubilees, the
Ante-Nicene Fathers; a reading of the King James, or of Charles Taylor's
Hermas, shares the subject and not the words. Catalogues do not reliably say
which: the LibriVox recording titled "Apocrypha" is Plato's.

Alignment answers that question as a side effect of doing its job. Audio that
is not this text will not align to it -- the score collapses, and no amount of
tolerance rescues it. So a chapter below the threshold is rejected outright,
written to the rejection report instead of the index, and the reader falls
back to the device voice for it, which is what that fallback is for. Nothing
reaches a listener on the strength of a catalogue entry.

WHAT THIS WRITES

    <out>/<work>.opus                   one file per work, for the release
    docs/data/audio/<work>.json         the offsets the reader fetches
    <out>/rejected.txt                  what did not align, and how badly

One file per work because release asset names are flat and cannot contain a
slash, and because the sources arrive as long multi-chapter files anyway.

The heavy parts -- the aligner, the decoder, the transcode -- are imported
where they are used rather than at module scope, so tools/lint.sh can compile
this without half a gigabyte of wheels, exactly as render_audio.py defers
Kokoro.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import speakable as speakable_rule                              # noqa: E402
from readings import READINGS                                   # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)

# Silence inserted between verses when the pieces are laid end to end. Written
# into the index as "gap" so the reader does not have to assume it -- which is
# the mistake the synthesised path made, keeping the number in two files and
# hoping they stayed level.
GAP = 0.35

# A reading has to move at a plausible speed. Below the floor the aligner has
# almost certainly attached a verse to silence; above the ceiling it has
# collapsed several verses onto one instant. Both are alignment failures
# wearing the costume of a result. English narration sits near 15 characters a
# second; these are wide enough not to argue with an unhurried reader or a
# brisk one.
MIN_CPS = 5.0
MAX_CPS = 40.0

# How much of a chapter's text has to have been placed for the result to be
# believed. Below this the audio is not this edition.
MIN_COVERAGE = 0.80

_WORD = re.compile(r"\S+")


def chapter_tokens(chapter, editorial):
    """The words to align, and which verse each of them belongs to.

    Returns (tokens, owners): two lists of the same length, tokens being the
    words in reading order and owners the verse number each came from.

    The text goes through the same speakable rule the reader and
    render_audio.py use, so the aligner is shown what a voice would have said
    rather than what the page prints -- Charles's daggers and brackets are
    apparatus, and a narrator does not read them out.
    """
    tokens, owners = [], []
    for verse in chapter.get("verses", []) or []:
        said = speakable_rule.speakable(verse.get("t", ""), editorial)
        words = _WORD.findall(said)
        if not words:
            # A verse that is nothing but apparatus has nothing to align to.
            continue
        tokens.extend(words)
        owners.extend([verse["v"]] * len(words))
    return tokens, owners


def verse_spans(owners, timings, at=0.0):
    """[[verse, start, end], ...] from per-token timings.

    `timings` is [(start, end), ...] in seconds, one per token, in the same
    order as `owners`. `at` shifts everything, because a chapter is a slice of
    the work's file rather than a file of its own.

    A token the aligner could not place is passed as None and simply does not
    vote on its verse's boundaries. A verse with no placed token at all is
    dropped: the reader treats a verse missing from the index as one it cannot
    seek to, which is honest, where a guessed offset is not.
    """
    if len(owners) != len(timings):
        raise ValueError("%d tokens but %d timings" % (len(owners), len(timings)))

    spans, order = {}, []
    for verse, t in zip(owners, timings):
        if t is None:
            continue
        start, end = t
        if verse not in spans:
            spans[verse] = [start, end]
            order.append(verse)
        else:
            spans[verse][0] = min(spans[verse][0], start)
            spans[verse][1] = max(spans[verse][1], end)

    out = []
    for verse in order:
        a, b = spans[verse]
        out.append([verse, round(a + at, 3), round(b + at, 3)])
    out.sort(key=lambda r: r[1])
    return out


def coverage(timings):
    """The fraction of tokens the aligner actually placed."""
    if not timings:
        return 0.0
    return sum(1 for t in timings if t is not None) / float(len(timings))


def chapter_problems(spans, chars):
    """Whatever is wrong with one chapter's spans, as a list of sentences.

    Everything here is a way for an alignment to look like a result and not be
    one, so a chapter that trips any of it is rejected rather than published.
    """
    bad = []
    if not spans:
        bad.append("nothing was placed")
        return bad

    last = None
    for verse, a, b in spans:
        if b <= a:
            bad.append("verse %s ends at or before it starts" % verse)
        if last is not None and a < last:
            bad.append("verse %s starts before the verse before it; the "
                       "reader walks these in order" % verse)
        last = a

    length = spans[-1][2] - spans[0][1]
    if length <= 0:
        bad.append("the chapter occupies no time at all")
    elif chars:
        cps = chars / length
        if cps < MIN_CPS:
            bad.append("%.1f characters a second is too slow to be a reading "
                       "of this text -- the audio is probably not it" % cps)
        elif cps > MAX_CPS:
            bad.append("%.1f characters a second is too fast to be a reading "
                       "of this text -- verses have collapsed together" % cps)
    return bad


def chapter_chars(chapter, editorial):
    """How many characters a narrator actually has to say."""
    n = 0
    for verse in chapter.get("verses", []) or []:
        n += len(speakable_rule.speakable(verse.get("t", ""), editorial).strip())
    return n


def build_index(reading_id, src, chapters):
    """The file the reader fetches, from the per-chapter results.

    `chapters` is a list of (chapter_index, spans) in file order, already
    shifted to their place in the work's audio.
    """
    spans = []
    rows = {}
    end = 0.0
    for idx, verses in chapters:
        if not verses:
            continue
        a = min(v[1] for v in verses)
        b = max(v[2] for v in verses)
        while len(spans) <= idx:
            spans.append([0.0, 0.0])
        spans[idx] = [round(a, 3), round(b + GAP, 3)]
        rows[str(idx)] = verses
        end = max(end, b + GAP)

    return {
        "reading": reading_id,
        "src": src,
        "d": round(end, 3),
        "gap": GAP,
        "c": spans,
        "v": rows,
    }


def load_aligner():
    """Import and construct the aligner, with a useful failure if it is absent.

    Deferred for the same reason render_audio.py defers Kokoro: tools/lint.sh
    byte-compiles every script in this directory and must not need the wheels.

    Deliberately not torchaudio.functional.forced_align, which was deprecated
    in 2.8 and removed in 2.9.
    """
    try:
        from ctc_forced_aligner import (load_alignment_model,     # noqa: F401
                                        generate_emissions,
                                        get_alignments)
    except ImportError:
        raise SystemExit(
            "align_audio.py needs a forced aligner:\n"
            "  pip install ctc-forced-aligner soundfile numpy\n"
            "It aligns the recording against the text this volume already "
            "has, so no transcription model and no network are involved once "
            "the audio is on disk.")
    return load_alignment_model


def report(path, rejected):
    """What did not align, and why. Written whether or not anything did.

    A coverage figure that only ever appears when it is good is a coverage
    figure nobody can act on. This is the other half of the index: the works
    and chapters a listener will hear the device voice on, and the reason.
    """
    lines = ["Chapters that did not align, and were therefore not published.",
             "",
             "A recording has to be of the same edition as the text printed",
             "here. Alignment is what establishes that, so a chapter in this",
             "list is either a recording of a different translation, or a",
             "passage the reader skipped, or audio too poor to place.",
             ""]
    for work, idx, why in rejected:
        lines.append("%s chapter %s" % (work, idx))
        for w in why:
            lines.append("    " + w)
    if not rejected:
        lines.append("Nothing was rejected.")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return len(rejected)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reading", required=True,
                    help="which recording, by its id in tools/readings.py")
    ap.add_argument("--data", default=os.path.join(ROOT, "docs", "data"))
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", "audio"))
    ap.add_argument("--only", default="",
                    help="comma-separated work ids, for a partial run")
    ap.add_argument("--list-readings", action="store_true",
                    help="print the readings on record and stop")
    args = ap.parse_args(argv)

    if args.list_readings:
        for key, r in READINGS.items():
            print("%-24s %-22s %s" % (key, r["edition"], r["narrator"]))
            print("%-24s %s" % ("", r["reads"]))
        return 0

    if args.reading not in READINGS:
        raise SystemExit(
            "no such reading: %s\nOn record: %s"
            % (args.reading, ", ".join(sorted(READINGS))))

    # Everything past this point needs the audio and the aligner, neither of
    # which this repository carries. The pieces above are the arithmetic, and
    # tests/python/test_align_audio.py exercises them without either.
    load_aligner()
    raise SystemExit(
        "align_audio.py: the fetch-and-align run is not wired up yet.\n"
        "The offsets arithmetic, the validation and the index format are "
        "implemented and under test; what is missing is the per-item file "
        "mapping for each reading, which differs by recording and has to be "
        "read from the item rather than guessed.")


if __name__ == "__main__":
    sys.exit(main())
