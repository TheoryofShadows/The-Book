#!/usr/bin/env python3
"""Write the published-audio manifest from the offsets that actually exist.

    python3 tools/build_readings.py docs

The manifest, docs/data/audio.json, is what the reader consults to decide
whether to offer a recorded voice at all. Everything about how that went wrong
before is in one sentence: the reader offered the voice on the strength of a
line of code, and there was nothing on the other end of it for months.

So this does not take a list of what has been recorded. It derives one, from
docs/data/audio/<work>.json -- the offsets tools/align_audio.py writes, and
writes only for a work whose audio it managed to align to the text this volume
prints. A work reaches the manifest because there is evidence for it on disk,
or it does not reach the manifest.

Four things are checked, and any of them failing is a build failure rather
than a warning, in the manner of build_manuscripts.py and build_canon.py:

  - the work exists in manifest.json, so a renamed work cannot rot the link
  - the reading named exists in tools/readings.py, so the credit resolves
  - the reading's edition matches the work's own "source", so a recording of
    one translation cannot be attached to the text of another
  - the offsets are shaped the way the reader reads them

Standard library only, like every other script here.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from readings import READINGS                                   # noqa: E402

# The release the audio is served from. Bump the tag when the audio is
# republished; the reader reads this out of the manifest rather than holding
# its own copy, and tools/check_audio.py reads it from the same place.
RELEASE = ("https://github.com/TheoryofShadows/The-Book/"
           "releases/download/audio-v1/")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def check_index(work, index, source):
    """Whatever is wrong with one work's offsets, as a list of sentences."""
    bad = []
    reading = index.get("reading")
    if reading not in READINGS:
        bad.append("names reading %r, which tools/readings.py does not list"
                   % reading)
        return bad

    want = READINGS[reading]["edition"]
    if source and want != source:
        bad.append(
            "is read from the %r edition but the work prints %r. A recording "
            "of one translation cannot be attached to the text of another; "
            "the words are different words." % (want, source))

    if not isinstance(index.get("src"), str) or not index["src"]:
        bad.append("has no src naming its audio asset")
    if "/" in (index.get("src") or ""):
        bad.append("has a src containing a slash: release asset names are "
                   "flat, so the audio cannot live at that path")

    spans = index.get("c")
    if not isinstance(spans, list) or not spans:
        bad.append("has no chapter spans")
        spans = []
    rows = index.get("v")
    if not isinstance(rows, dict) or not rows:
        bad.append("has no verse offsets")
        rows = {}

    for key in sorted(rows):
        if not key.isdigit():
            bad.append("has a chapter key %r that is not a chapter index" % key)
        elif int(key) >= len(spans):
            bad.append("has offsets for chapter %s but no span for it" % key)
    return bad


def build(out_dir):
    works_dir = os.path.join(out_dir, "data", "works")
    audio_dir = os.path.join(out_dir, "data", "audio")
    manifest_path = os.path.join(out_dir, "data", "manifest.json")

    manifest = load(manifest_path)
    known = {}
    for section in manifest["sections"]:
        for work in section["works"]:
            known[work["id"]] = work

    names = []
    if os.path.isdir(audio_dir):
        names = sorted(n for n in os.listdir(audio_dir) if n.endswith(".json"))

    problems = []
    published = {}

    for name in names:
        work_id = name[:-5]
        index = load(os.path.join(audio_dir, name))

        if work_id not in known:
            problems.append("no such work: %s" % work_id)
            continue

        source = ""
        work_path = os.path.join(works_dir, work_id + ".json")
        if os.path.exists(work_path):
            source = load(work_path).get("source", "")

        bad = check_index(work_id, index, source)
        if bad:
            problems.extend("%s: %s" % (work_id, b) for b in bad)
            continue

        r = READINGS[index["reading"]]
        published[work_id] = {
            "src": index["src"],
            "reading": index["reading"],
            "narrator": r["narrator"],
            "licence": r["licence"],
            "url": r["url"],
        }

    if problems:
        print("  the manifest was not written:")
        for p in problems:
            print("  BROKEN  " + p)
        return 1

    payload = {
        "base": RELEASE if published else "",
        "works": published,
    }
    if not published:
        payload["note"] = (
            "Nothing has been published yet. Both fields empty is the "
            "reader's cue to offer no recorded voice at all, which is the "
            "state this file exists to make checkable. Written by "
            "tools/build_readings.py.")

    with open(os.path.join(out_dir, "data", "audio.json"), "w",
              encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    if published:
        chapters = 0
        for name in names:
            index = load(os.path.join(audio_dir, name))
            chapters += len(index.get("v") or {})
        print("  %d works, %d chapters, read by %d narrator(s)"
              % (len(published), chapters,
                 len({p["reading"] for p in published.values()})))
    else:
        print("  nothing published yet; the reader will offer no recorded voice")
    return 0


def main(argv):
    out_dir = argv[1] if len(argv) > 1 else "docs"
    if not os.path.isdir(os.path.join(out_dir, "data")):
        raise SystemExit("no %s/data -- give me the docs directory" % out_dir)
    return build(out_dir)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
