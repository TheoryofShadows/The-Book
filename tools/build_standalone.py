#!/usr/bin/env python3
"""Emit the whole library as one self-contained HTML file.

Every data file is inlined under window.__BOOK__, keyed by the same path the
served site fetches, so docs/assets/app.js runs unchanged in both. The result
opens from a file:// URL or any host with no network access at all.
"""

from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The live site's address, read from the script that already owns it rather
# than written out a second time here. Two copies is one to forget: move the
# site and this file goes on telling every offline reader to visit the old
# address, which is the one thing the stamp exists to get right.
from build_pages import BASE                                    # noqa: E402

DOCS = sys.argv[1] if len(sys.argv) > 1 else "docs"
OUT = sys.argv[2] if len(sys.argv) > 2 else "dist/the-book.html"

DATA = os.path.join(DOCS, "data")


def collect() -> dict:
    """Every JSON file under docs/data, keyed by the path the site fetches.

    Naming the files individually meant that anything added later -- threads,
    the lexicon, the places, the manuscripts -- was left out, and the page
    lost those features with nothing but a failed fetch in the console to say
    so. Walking the tree keeps the offline copy honest by construction.
    """
    bundle = {}
    for folder, _dirs, files in os.walk(DATA):
        for fn in sorted(files):
            if not fn.endswith(".json"):
                continue
            full = os.path.join(folder, fn)
            key = os.path.relpath(full, DATA).replace(os.sep, "/")
            if skip_offline(key):
                continue
            with open(full, encoding="utf-8") as fh:
                bundle[key] = json.load(fh)
    return bundle


def commit() -> str:
    """The revision this copy was cut from, or "" if that cannot be known.

    GITHUB_SHA in the deploy, git otherwise, and nothing at all when the
    build is run from an unpacked tarball with no repository around it. The
    date below is the part that matters to a reader; this is for the person
    they report a problem to.
    """
    sha = os.environ.get("GITHUB_SHA", "")
    if sha:
        return sha[:7]
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             cwd=os.path.dirname(os.path.abspath(__file__)),
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def stamp() -> dict:
    """What this copy is, when it was taken, and where the living one is.

    A single-file build is a photograph of the site, and a photograph does not
    know that it is one. Opened from a disk some months later it is the reader
    down to the wordmark, so a library that has grown since, a text that has
    been corrected and a feature that has shipped all present as a site that
    has stopped being maintained -- and the reader has no way to tell that
    from the inside. The only difference is the one they cannot see, so the
    build writes it down and docs/assets/app.js prints it.

    UTC, because the machine that renders this is in no particular place and a
    date that shifts with the builder's timezone is a date that says less than
    it appears to.
    """
    return {
        "date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "commit": commit(),
        "home": BASE.rstrip("/") + "/",
    }


# The recorded reading is the one feature this build cannot honour: the audio
# is a release asset and there is no network here. docs/assets/app.js already
# knows that -- AUDIO_OK is false whenever window.__BOOK__ is set -- so these
# files would be inlined, never read, and paid for in megabytes. Roughly three
# quarters of a megabyte of verse offsets for a voice that cannot play.
#
# The same rule as the online-only markers in index.html, applied to the data
# rather than to the page.
def skip_offline(key):
    return key == "audio.json" or key.startswith("audio/")


ONLINE_ONLY = ("<!-- online-only:start -->", "<!-- online-only:end -->")


def strip_online_only(body: str) -> str:
    """Drop anything the served site has that this copy cannot honour.

    The one case so far is the link offering this file. In the served page it
    is a download; inlined here it would be a link from the offline copy to
    the offline copy, resolving against a file:// path that does not exist --
    a dead link in the one build whose whole claim is that nothing it needs
    is elsewhere. Marking the region in index.html rather than matching on
    the link keeps the rule general, and keeps the decision beside the thing
    being decided about.
    """
    start, end = ONLINE_ONLY
    while start in body:
        head, rest = body.split(start, 1)
        if end not in rest:
            raise SystemExit(f"unclosed {start} in docs/index.html")
        body = head + rest.split(end, 1)[1]
    if end in body:
        raise SystemExit(f"{end} with no {start} in docs/index.html")
    return body


def main() -> int:
    css = open(os.path.join(DOCS, "assets", "app.css"), encoding="utf-8").read()
    js = open(os.path.join(DOCS, "assets", "app.js"), encoding="utf-8").read()
    html = open(os.path.join(DOCS, "index.html"), encoding="utf-8").read()
    icon = open(os.path.join(DOCS, "assets", "favicon.svg"),
                encoding="utf-8").read()

    bundle = collect()
    # </script> inside the payload would close the tag early.
    payload = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")

    body = html.split("<body>", 1)[1].split("</body>", 1)[0]
    body = body.replace('<script src="assets/app.js"></script>', "")
    body = strip_online_only(body)

    # Only the body survives the split above, so the tab icon has to be put
    # back by hand or the offline copy is the one place the mark is missing.
    # There is nowhere to fetch it from at file://, so it is inlined.
    href = "data:image/svg+xml," + quote(icon, safe="")

    page = (
        "<title>The Book in Order</title>\n"
        f'<link rel="icon" href="{href}" type="image/svg+xml">\n'
        f"<style>\n{css}\n</style>\n"
        f"{body}\n"
        f'<script id="book-data">window.__BOOK__={payload};\n'
        f"window.__BOOK_BUILT__={json.dumps(stamp())};</script>\n"
        f"<script>\n{js}\n</script>\n"
    )

    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(page)

    mb = os.path.getsize(OUT) / 1024 / 1024
    print(f"{OUT}  {mb:.2f} MB  ({len(bundle)} data files inlined)")
    if mb > 15:
        print("WARNING: over 15 MB, close to the artifact ceiling")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
