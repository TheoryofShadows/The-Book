#!/usr/bin/env python3
"""Is there actually a recording on the other end of the recorded reading?

    python3 tools/check_audio.py
    python3 tools/check_audio.py --sample psalms/22

The reader offers a "Recorded reading" voice, ahead of the device's own and
to everybody, and fetches it from an Internet Archive item. The whole path --
the drawer entry, the per-verse offsets, the pace control, the Opus transport
-- is covered by the browser checks, which stand in for archive.org and prove
the code works. Nothing checked that the item exists. It did not, and choosing
the reading produced silence and a fallback for every reader who tried it,
through 360 green tests.

So this asks the one question those checks cannot: is the content there.

Two rules it follows, both of them about staying worth running.

It reads AUDIO_BASE out of docs/assets/app.js rather than holding a second
copy of the URL. A second copy is a second thing to remember: move the audio,
forget this file, and it goes on checking the old item -- passing, while the
site fetches from somewhere else entirely.

And archive.org being down is not a finding about this repository. A check
that goes red on somebody else's outage is a check people learn to ignore,
and a check people ignore has already stopped working. An outage prints a
skip and exits zero; only a definite answer -- the item is not there, or it
is there and does not serve what the reader asks it for -- exits one.
"""

import argparse
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request

APP_JS = os.path.join("docs", "assets", "app.js")
TIMEOUT = 30


class Unreachable(Exception):
    """No answer from archive.org. Not an answer about the archive."""


def audio_base(path):
    """The one line the reader fetches audio from, read from the reader."""
    try:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
    except OSError as exc:
        sys.exit("check_audio: cannot read %s: %s" % (path, exc))

    m = re.search(r'\bAUDIO_BASE\s*=\s*["\']([^"\']+)["\']', src)
    if not m:
        sys.exit("check_audio: no AUDIO_BASE in %s. If the reader stopped "
                 "naming it that, this check has been reading a variable that "
                 "is not there and passing on the strength of it." % path)
    return m.group(1)


def metadata_url(base):
    """The metadata endpoint for whatever AUDIO_BASE names -- host and item
    both taken from it, so there is still only one URL in the repository. A
    second copy written out here would go on describing the old item after
    the audio moved, and pass while the site fetched from somewhere else."""
    m = re.match(r"(https?://[^/]+)/download/([^/]+)/?$", base)
    if not m:
        sys.exit("check_audio: AUDIO_BASE is %r, which is not an Internet "
                 "Archive download URL. Point this check at whatever it is "
                 "now, or it is checking nothing." % base)
    return m.group(1) + "/metadata/" + m.group(2), m.group(2)


def fetch(url, head=False):
    """Bytes, or None for a 404, or Unreachable for anything that is not an
    answer -- a refused connection, a timeout, a 5xx from their side."""
    req = urllib.request.Request(
        url, method="HEAD" if head else "GET",
        headers={"User-Agent": "the-book-check-audio/1 (+https://github.com/"
                               "TheoryofShadows/The-Book)"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read() if not head else b""
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 404, 410):
            return None
        raise Unreachable("%s -> HTTP %s" % (url, exc.code))
    except (urllib.error.URLError, socket.timeout, OSError) as exc:
        raise Unreachable("%s -> %s" % (url, exc))


def skip(why):
    print("skip: %s" % why)
    print("      archive.org gave no answer, so this says nothing about the "
          "recording either way.")
    return 0


INDEX_HTML = os.path.join("docs", "index.html")


def declared_published(path=INDEX_HTML):
    """Does the served page say a recording exists?

    The reader gates the recorded voice on data-audio="published" on <html>.
    That is a fact about a deploy rather than about the code, so it lives in
    the page, and this check reads it from the same place the browser does.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            html = fh.read()
    except OSError as exc:
        sys.exit("check_audio: cannot read %s: %s" % (path, exc))
    return re.search(r'<html[^>]*\bdata-audio\s*=\s*"published"', html) is not None


def check(sample, app_js):
    base = audio_base(app_js)
    meta_url, item = metadata_url(base)
    published = declared_published()
    print("AUDIO_BASE in %s -> %s" % (app_js, base))
    print("item: %s" % item)
    print("docs/index.html declares the reading %s"
          % ("published" if published else "not published"))

    try:
        raw = fetch(meta_url)
    except Unreachable as exc:
        return skip(str(exc))

    if raw is None:
        return skip("%s answered 404" % meta_url)

    try:
        meta = json.loads(raw.decode("utf-8"))
    except ValueError as exc:
        return skip("the metadata for %s did not parse: %s" % (item, exc))

    # {} is the Internet Archive's answer for an item that does not exist.
    # That is a definite answer, and it is the finding.
    if not (meta.get("files") or meta.get("metadata")):
        if not published:
            print()
            print("ok: there is no item at %r, and the page does not claim"
                  % item)
            print("    there is. The recorded voice is not offered, so nobody")
            print("    is shown a reading that would fall back the moment they")
            print("    chose it.")
            print()
            print("    To publish: render the audio, upload it to that item,")
            print("    and add data-audio=\"published\" to <html> in")
            print("    docs/index.html in the same commit. This check then")
            print("    holds the item to its promise instead.")
            return 0
        print()
        print("FAIL: docs/index.html declares the reading published and there")
        print("      is no Internet Archive item called %r." % item)
        print()
        print("  Every reader is being offered a voice that is not there, and")
        print("  choosing it plays nothing and falls back to the device.")
        print("  Either upload the audio or take the attribute back off.")
        return 1

    if not published:
        print()
        print("FAIL: the item %r exists and the page does not offer it." % item)
        print()
        print("  data-audio=\"published\" is missing from <html> in")
        print("  docs/index.html, so the reader hides a reading that is")
        print("  sitting there ready. Add the attribute.")
        return 1

    print("the item exists: %d files"
          % len(meta.get("files") or []))

    work, chapter = sample.split("/", 1)
    offsets_url = "%s%s/%s.json" % (base, work, chapter)
    audio_url = "%s%s/%s.opus" % (base, work, chapter)

    try:
        raw = fetch(offsets_url)
    except Unreachable as exc:
        return skip(str(exc))
    if raw is None:
        print("FAIL: the item is there but has no offsets for the sample "
              "chapter:\n      %s" % offsets_url)
        return 1

    try:
        index = json.loads(raw.decode("utf-8"))
    except ValueError as exc:
        print("FAIL: %s is not JSON: %s" % (offsets_url, exc))
        return 1

    # The reader marks the verse being spoken from these, so the shape of them
    # is the difference between a reading that follows the text and a reading
    # that plays under a still page.
    rows = index.get("v")
    if not isinstance(rows, list) or not rows:
        print("FAIL: %s has no verse offsets (index.v is %r)."
              % (offsets_url, rows))
        return 1
    bad = [r for r in rows
           if not (isinstance(r, list) and len(r) == 3
                   and all(isinstance(x, (int, float)) for x in r))]
    if bad:
        print("FAIL: %d of %d offsets in %s are not [verse, start, end] "
              "triples, e.g. %r" % (len(bad), len(rows), offsets_url, bad[0]))
        return 1
    print("offsets for %s: %d verses, %.1f seconds"
          % (sample, len(rows), rows[-1][2]))

    try:
        got = fetch(audio_url, head=True)
    except Unreachable as exc:
        return skip(str(exc))
    if got is None:
        print("FAIL: the offsets are there but the audio is not:\n      %s"
              % audio_url)
        return 1
    print("audio for %s is served" % sample)

    print("ok: the recorded reading has something on the end of it")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sample", default="genesis/0",
                    help="work/chapter to fetch, in the reader's own "
                         "zero-based chapter numbering (default genesis/0)")
    ap.add_argument("--app", default=APP_JS,
                    help="the reader, which AUDIO_BASE is read out of")
    args = ap.parse_args(argv)

    if "/" not in args.sample:
        ap.error("--sample takes work/chapter, e.g. genesis/0")
    return check(args.sample, args.app)


if __name__ == "__main__":
    sys.exit(main())
