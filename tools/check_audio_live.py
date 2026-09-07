#!/usr/bin/env python3
"""Does a real archive.org item serve what the reader actually asks it for?

    python3 tools/check_audio_live.py --item the-book-read-aloud-test
    python3 tools/check_audio_live.py --item the-book-read-aloud --sample psalms/22

tools/check_audio.py asks whether the item exists. This asks the harder
question, and the one nothing has ever asked: whether what it serves is
usable by the page.

The player does two different things to two different files, and they fail
in different ways:

    the .json  is read with fetch(), from a page on thebookandme.com. That is
               a cross-origin request, so without an
               Access-Control-Allow-Origin header the browser refuses it and
               the reader sees a silent fallback to the device voice. curl
               will not notice: it has no origin and no same-origin policy.

    the .opus  is handed to an <audio> element, which seeks by asking for a
               byte range. A server that ignores Range and returns the whole
               file makes every verse tap download the chapter from the
               start -- which works, slowly, and looks like the site being
               bad on a phone.

Neither is visible from a normal GET, which is why this exists. It checks
the headers the browser will act on, and it checks that the offsets in the
JSON actually describe the audio beside it: a chapter whose index says 39.6
seconds against a file that is 12 is a chapter whose verse marks are wrong
everywhere, and that is the failure a listener notices first.

Exits non-zero on a definite finding. An archive.org outage is not a finding
about this repository and prints a skip.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

TIMEOUT = 45
APP_JS = os.path.join("docs", "assets", "app.js")
ORIGIN = "https://thebookandme.com"


class Unreachable(Exception):
    """No answer from archive.org. Not an answer about the archive."""


class KeepMethod(urllib.request.HTTPRedirectHandler):
    """Follow archive.org's redirect without turning a HEAD into a GET.

    /download/<item>/<file> is a 302 to the node actually holding the file,
    and it is the node that sets the headers that matter -- the CORS header
    and the range support both live there, not on the redirect. Checking the
    302 and stopping, which is what a plain HEAD does, reads the wrong reply
    and would call a working item broken.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = urllib.request.Request(newurl, method=req.get_method())
        for k, v in req.header_items():
            if k.lower() != "host":
                new.add_header(k, v)
        return new


OPENER = urllib.request.build_opener(KeepMethod)


def get(url, headers=None, method="GET"):
    req = urllib.request.Request(url, method=method)
    req.add_header("User-Agent", "the-book-check/1 (+%s)" % ORIGIN)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        return OPENER.open(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as exc:
        return exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise Unreachable(str(exc))


def audio_base(path=APP_JS):
    """The address the reader really uses, read from the reader."""
    try:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
    except OSError as exc:
        sys.exit("check_audio_live: cannot read %s: %s" % (path, exc))
    m = re.search(r'\bAUDIO_BASE\s*=\s*["\']([^"\']+)["\']', src)
    if not m:
        sys.exit("check_audio_live: no AUDIO_BASE in %s" % path)
    return m.group(1)


def report(ok, label, detail=""):
    print("  %-4s %s%s" % ("ok" if ok else "FAIL", label,
                           ("  (%s)" % detail) if detail else ""))
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--item", help="archive.org identifier to test against; "
                                   "defaults to the one the reader names")
    ap.add_argument("--sample", default="psalms/0",
                    help="work/chapter to fetch, as the reader addresses it")
    args = ap.parse_args()

    base = audio_base()
    if args.item:
        base = re.sub(r"/download/[^/]+/", "/download/%s/" % args.item, base)
    print("Checking %s" % base)
    print("Sample:  %s" % args.sample)
    print()

    json_url = base + args.sample + ".json"
    opus_url = base + args.sample + ".opus"
    bad = []

    try:
        # ---- the index, as fetch() will ask for it --------------------
        r = get(json_url, {"Origin": ORIGIN})
        if getattr(r, "status", r.code) == 404:
            sys.exit("check_audio_live: %s is not there. Upload first, or "
                     "pass --sample for a chapter that exists." % json_url)
        body = r.read()
        allow = r.headers.get("Access-Control-Allow-Origin")

        if not report(allow is not None,
                      "the index is sent with an Access-Control-Allow-Origin",
                      allow or "no header -- the browser will refuse this"):
            bad.append("cors")
        if allow and allow not in ("*", ORIGIN):
            if not report(False, "and that header allows this site", allow):
                bad.append("cors-origin")

        try:
            index = json.loads(body)
        except ValueError:
            report(False, "the index parses as JSON", body[:60])
            bad.append("json")
            index = None

        if index is not None:
            shaped = isinstance(index.get("v"), list) and index["v"]
            if not report(bool(shaped), "and has the verse offsets in it",
                          "%d verses" % len(index.get("v", []))):
                bad.append("shape")

        # ---- the audio, as <audio> will ask for it --------------------
        h = get(opus_url, method="HEAD")
        status = getattr(h, "status", h.code)
        length = h.headers.get("Content-Length")
        ctype = h.headers.get("Content-Type", "")
        if not report(status == 200, "the audio answers a HEAD", str(status)):
            bad.append("head")
        if not report("opus" in ctype or "ogg" in ctype or "octet" in ctype,
                      "and is served as audio", ctype or "no type"):
            bad.append("type")

        rng = get(opus_url, {"Range": "bytes=0-99"})
        rstat = getattr(rng, "status", rng.code)
        got = rng.read()
        if not report(rstat == 206 and len(got) == 100,
                      "and serves a byte range, so seeking is a seek",
                      "%s, %d bytes" % (rstat, len(got))):
            bad.append("range")
        if not report(got[:4] == b"OggS",
                      "and the bytes really are an Ogg stream",
                      repr(got[:4])):
            bad.append("magic")

        # ---- do the two agree? ---------------------------------------
        if index is not None and length and index.get("d"):
            secs = float(index["d"])
            kbps = (int(length) * 8) / secs / 1000
            # The render targets 34 kbps. A file whose implied bitrate is far
            # from that is not the file this index describes -- most likely a
            # chapter uploaded against the wrong index, which would put every
            # verse mark in it somewhere else.
            sane = 10 < kbps < 120
            if not report(sane,
                          "the index's duration matches the file's size",
                          "%.1fs, %s bytes -> %.0f kbps" % (secs, length, kbps)):
                bad.append("mismatch")

    except Unreachable as exc:
        print("skip: archive.org could not be reached (%s)" % exc)
        print("An outage is not a finding about this repository.")
        return 0

    print()
    if bad:
        print("%d finding(s): %s" % (len(bad), ", ".join(bad)))
        print("The reader would fall back to the device voice, or seek badly,")
        print("and nothing on the page would say why.")
        return 1
    print("The item serves what the reader asks it for.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
