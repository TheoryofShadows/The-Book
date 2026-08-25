#!/usr/bin/env python3
"""Is there actually a recording on the other end of the recorded reading?

    python3 tools/check_audio.py
    python3 tools/check_audio.py --sample jubilees

The reader offers a "Recorded reading" voice. The whole path -- the drawer
entry, the per-verse offsets, the pace control, the transport -- is covered by
the browser checks, which stand in for the host and prove the code works.
Nothing checked that the audio exists. It did not, for the entire life of the
feature: the Internet Archive item the reader fetched from had never been
uploaded, and choosing the reading produced silence and a fallback through 360
green tests.

So this asks the one question those checks cannot: is the content there.

Most of the answer is now local. docs/data/audio.json is checked into the
repository and says what has been published and where, so the schema, the
verse numbers and the ordering can all be verified without a network at all.
Only the last question -- is the asset really served -- needs to leave the
machine.

Two rules it keeps from the version that checked an Archive item.

It reads the release URL out of the manifest rather than holding a second
copy. A second copy is a second thing to remember: move the audio, forget
this file, and it goes on checking the old release -- passing, while the site
fetches from somewhere else entirely.

And somebody else's server being down is not a finding about this repository.
A check that goes red on an outage is a check people learn to ignore, and a
check people ignore has already stopped working. An outage prints a skip and
exits zero; only a definite answer exits one.
"""

import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join("docs", "data", "audio.json")
TIMEOUT = 30


class Unreachable(Exception):
    """No answer from the host. Not an answer about the host."""


def fetch(url, head=False):
    """Bytes, or None for a definite 404, or Unreachable for anything that is
    not an answer -- a refused connection, a timeout, a 5xx from their side."""
    req = urllib.request.Request(
        url, method="HEAD" if head else "GET",
        headers={"User-Agent": "the-book-check-audio/2 (+https://github.com/"
                               "TheoryofShadows/The-Book)"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return b"" if head else r.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 404, 410):
            return None
        raise Unreachable("%s -> HTTP %s" % (url, exc.code))
    except (urllib.error.URLError, socket.timeout, OSError) as exc:
        raise Unreachable("%s -> %s" % (url, exc))


def skip(why):
    print("skip: %s" % why)
    print("      the host gave no answer, so this says nothing about the "
          "recording either way.")
    return 0


def load(path, what):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError as exc:
        sys.exit("check_audio: cannot read %s: %s" % (what, exc))
    except ValueError as exc:
        sys.exit("check_audio: %s is not JSON: %s" % (what, exc))


def check_index(index, work, verses):
    """The offsets for one work, against the text the reader prints.

    Returns a list of problems, empty if it holds together.
    """
    bad = []
    if not isinstance(index.get("src"), str) or not index["src"]:
        bad.append("no src naming the audio asset")
    chapters = index.get("c")
    if not isinstance(chapters, list) or not chapters:
        bad.append("c is not a list of chapter spans")
        chapters = []
    rows = index.get("v")
    if not isinstance(rows, dict) or not rows:
        bad.append("v is not an object of chapter rows")
        rows = {}

    for i, span in enumerate(chapters):
        if not (isinstance(span, list) and len(span) == 2
                and all(isinstance(x, (int, float)) for x in span)):
            bad.append("chapter %d: span is not [start, end]" % i)
        elif span[1] <= span[0]:
            bad.append("chapter %d: ends at or before it starts" % i)

    for key, chapter_rows in sorted(rows.items()):
        if not key.isdigit():
            bad.append("chapter key %r is not a chapter index" % key)
            continue
        idx = int(key)
        if idx >= len(chapters):
            bad.append("chapter %d has offsets but no span" % idx)
        # The reader marks the verse being spoken from these, so the shape of
        # them is the difference between a reading that follows the text and a
        # reading that plays under a still page.
        last = None
        for row in chapter_rows:
            if not (isinstance(row, list) and len(row) == 3
                    and all(isinstance(x, (int, float)) for x in row)):
                bad.append("chapter %d: %r is not [verse, start, end]"
                           % (idx, row))
                continue
            if last is not None and row[1] < last:
                bad.append("chapter %d: verse %s starts before the one before "
                           "it -- the reader walks these in order"
                           % (idx, row[0]))
            last = row[1]
            known = verses.get(idx, set())
            if known and row[0] not in known:
                bad.append("chapter %d: verse %s is not in %s"
                           % (idx, row[0], work))
    return bad


def verses_of(work):
    """{chapter index: {verse numbers}} for a work the reader prints."""
    path = os.path.join("docs", "data", "works", work + ".json")
    if not os.path.exists(path):
        return {}
    data = load(path, path)
    out = {}
    for i, ch in enumerate(data.get("chapters", []) or []):
        out[i] = {v.get("v") for v in ch.get("verses", []) or []}
    return out


def check(sample, manifest_path):
    manifest = load(manifest_path, manifest_path)
    base = manifest.get("base") or ""
    works = manifest.get("works") or {}

    print("manifest: %s" % manifest_path)

    # Nothing published is a consistent state, not a failure. The reader reads
    # this same file and offers no recorded voice at all when it is empty, so
    # there is no promise outstanding for this to catch.
    if not base and not works:
        print("nothing is published yet, and the reader offers no recorded "
              "voice while that is true. Consistent.")
        return 0

    if not base or not works:
        print()
        print("FAIL: the manifest is half-filled.")
        print("  base  = %r" % base)
        print("  works = %d entries" % len(works))
        print("  Either both are set or neither is. A base with no works "
              "offers a voice with nothing behind it; works with no base "
              "gives the reader nowhere to fetch them from.")
        return 1

    print("release: %s" % base)
    print("works recorded: %d" % len(works))

    if sample not in works:
        print()
        print("FAIL: --sample names %r, which the manifest does not list. "
              "Pass one of: %s" % (sample, ", ".join(sorted(works)[:8])))
        return 1

    # ---- local: the offsets, against the text the reader prints ----
    index_path = os.path.join("docs", "data", "audio", sample + ".json")
    if not os.path.exists(index_path):
        print()
        print("FAIL: the manifest lists %r but there is no %s"
              % (sample, index_path))
        return 1
    index = load(index_path, index_path)

    problems = check_index(index, sample, verses_of(sample))
    if problems:
        print()
        print("FAIL: %s does not hold together:" % index_path)
        for p in problems[:12]:
            print("  " + p)
        if len(problems) > 12:
            print("  ... and %d more" % (len(problems) - 12))
        return 1

    covered = sum(len(r) for r in index["v"].values())
    print("offsets for %s: %d chapters, %d verses, %.1f minutes"
          % (sample, len(index["c"]), covered, (index.get("d") or 0) / 60))

    # ---- the one question that needs the network ----
    audio_url = base + index["src"]
    try:
        got = fetch(audio_url, head=True)
    except Unreachable as exc:
        return skip(str(exc))
    if got is None:
        print()
        print("FAIL: the offsets are there but the audio is not:")
        print("      %s" % audio_url)
        print()
        print("  The manifest promises this asset and the reader will offer")
        print("  the voice on the strength of it. Either upload it to the")
        print("  release, or take the work out of docs/data/audio.json.")
        return 1

    print("audio for %s is served" % sample)
    print("ok: the recorded reading has something on the end of it")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sample", default="",
                    help="work id to verify in full (default: the first the "
                         "manifest lists)")
    ap.add_argument("--manifest", default=MANIFEST,
                    help="the published-audio manifest, which names the "
                         "release the audio is fetched from")
    args = ap.parse_args(argv)

    sample = args.sample
    if not sample:
        manifest = load(args.manifest, args.manifest)
        listed = sorted(manifest.get("works") or {})
        sample = listed[0] if listed else ""
    return check(sample, args.manifest)


if __name__ == "__main__":
    sys.exit(main())
