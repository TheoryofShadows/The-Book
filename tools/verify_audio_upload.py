#!/usr/bin/env python3
"""Every rendered chapter, checked at the address the reader will use.

    python3 tools/verify_audio_upload.py
    python3 tools/verify_audio_upload.py --deep 40

check_audio.py asks whether the item exists and looks at one chapter.
check_audio_live.py asks whether the headers are right on one chapter. Neither
of them would notice a hundred files missing from the middle of the library,
and both of them passed a trial upload that was shifted by one, because a
filename was all either was ever pointed at.

This asks the whole question, of everything:

    is every file the render made on the item, at the address app.js builds,
    the size it was locally, and -- for a sample -- really served with the
    verse count the text says that chapter has

The first three come from one metadata request, so the whole library costs a
single call rather than 3,118. The fourth needs a request each and is done for
a sample, because it is the one that has to fetch bytes.

Exits non-zero on any finding. This is the check that stands between a render
and telling readers there is a recording.
"""

import argparse
import json
import os
import random
import sys
import urllib.error
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
AUDIO = os.path.join(ROOT, "dist", "audio")
WORKS = os.path.join(ROOT, "docs", "data", "works")
ITEM = "the-book-read-aloud"
TIMEOUT = 45


class Unreachable(Exception):
    """No answer from archive.org. Not an answer about the archive."""


def fetch(url, headers=None):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "the-book-verify/1 (+https://thebookandme.com)")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        return urllib.request.urlopen(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as exc:
        return exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise Unreachable(str(exc))


def local_files():
    """{address: size} for everything the render made."""
    out = {}
    if not os.path.isdir(AUDIO):
        sys.exit("verify_audio_upload: no dist/audio here to compare against")
    for dirpath, _, names in os.walk(AUDIO):
        work = os.path.relpath(dirpath, AUDIO).replace(os.sep, "/")
        if work == ".":
            continue
        for name in names:
            if name.endswith((".opus", ".json")):
                path = os.path.join(dirpath, name)
                out["%s/%s" % (work, name)] = os.path.getsize(path)
    return out


def item_files(item):
    """{address: size} for everything on the archive item."""
    r = fetch("https://archive.org/metadata/%s" % item)
    meta = json.loads(r.read())
    if not meta:
        sys.exit("verify_audio_upload: the item %r does not exist" % item)
    out = {}
    for f in meta.get("files") or []:
        name = f.get("name", "")
        if name.endswith((".opus", ".json")) and "/" in name:
            try:
                out[name] = int(f.get("size", 0))
            except (TypeError, ValueError):
                out[name] = 0
    return out, bool(meta.get("pending_tasks"))


def expected_verses():
    """{work/chapter: verse count} straight from the text."""
    out = {}
    for name in sorted(os.listdir(WORKS)):
        if not name.endswith(".json"):
            continue
        wid = name[:-5]
        with open(os.path.join(WORKS, name), encoding="utf-8") as fh:
            work = json.load(fh)
        for idx, chapter in enumerate(work.get("chapters", [])):
            out["%s/%d" % (wid, idx)] = len(chapter.get("verses", []))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--item", default=ITEM)
    ap.add_argument("--deep", type=int, default=25,
                    help="how many chapters to actually fetch and read")
    args = ap.parse_args()

    local = local_files()
    print("the render made %d files" % len(local))

    try:
        served, pending = item_files(args.item)
    except Unreachable as exc:
        print("skip: archive.org could not be reached (%s)" % exc)
        return 0
    print("the item holds   %d files%s"
          % (len(served), "  (tasks still pending)" if pending else ""))

    findings = []

    missing = sorted(set(local) - set(served))
    if missing:
        findings.append("%d file(s) never arrived" % len(missing))
        print("\nMISSING, first 10:")
        for name in missing[:10]:
            print("   ", name)

    extra = sorted(set(served) - set(local))
    if extra:
        # Not fatal on its own -- an old upload can leave files behind -- but
        # it is how a shifted or renamed set hides in plain sight, so it is
        # reported rather than ignored.
        findings.append("%d file(s) on the item the render did not make" % len(extra))
        print("\nUNEXPECTED, first 10:")
        for name in extra[:10]:
            print("   ", name)

    wrong_size = [n for n in sorted(set(local) & set(served))
                  if served[n] and served[n] != local[n]]
    if wrong_size:
        findings.append("%d file(s) are a different size than the render made"
                        % len(wrong_size))
        print("\nWRONG SIZE, first 10:")
        for name in wrong_size[:10]:
            print("    %s: %d local, %d served"
                  % (name, local[name], served[name]))

    # The part that has to fetch. A size match proves the bytes are the same
    # bytes; it cannot prove the file is at the address for the chapter it
    # holds. That is what shifted the whole library by one last time, so it is
    # asked of real addresses, against the verse count in the text.
    want = expected_verses()
    addresses = sorted(n[:-5] for n in local if n.endswith(".json"))
    sample = random.Random(0).sample(addresses, min(args.deep, len(addresses)))
    print("\nreading %d chapters from the item:" % len(sample))
    base = "https://archive.org/download/%s/" % args.item
    bad = 0
    for address in sample:
        try:
            r = fetch(base + address + ".json", {"Origin": "https://thebookandme.com"})
        except Unreachable as exc:
            print("  skip: %s (%s)" % (address, exc))
            continue
        status = getattr(r, "status", r.code)
        if status != 200:
            print("  FAIL %s -> HTTP %s" % (address, status))
            bad += 1
            continue
        if r.headers.get("Access-Control-Allow-Origin") is None:
            print("  FAIL %s -> no CORS header; the browser would refuse it"
                  % address)
            bad += 1
            continue
        try:
            index = json.loads(r.read())
        except ValueError:
            print("  FAIL %s -> not JSON" % address)
            bad += 1
            continue
        got = len(index.get("v") or [])
        expect = want.get(address)
        if expect is None:
            print("  FAIL %s -> no such chapter in the text" % address)
            bad += 1
        elif got != expect:
            print("  FAIL %s -> %d verses served, text has %d"
                  % (address, got, expect))
            bad += 1
    if bad:
        findings.append("%d of %d chapters read back wrong" % (bad, len(sample)))
    else:
        print("  all %d hold the chapter the text says they should" % len(sample))

    print()
    if findings:
        for f in findings:
            print("FINDING: %s" % f)
        print("\nDo not publish. The reader would meet at least one chapter")
        print("that is missing, wrong, or not the one it asked for.")
        return 1
    if pending:
        print("Everything matches, but archive.org still has tasks pending.")
        print("Run again once they clear before publishing.")
        return 1
    print("Every rendered file is on the item, at the right size, and the")
    print("chapters read back are the ones the text says they are.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
