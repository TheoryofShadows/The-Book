#!/usr/bin/env python3
"""Put the assets' own content hash into the URLs that fetch them.

    python3 tools/stamp_assets.py docs

Every deploy of this site since the first one has shipped app.css and app.js
under the same two names. GitHub Pages serves them with Cache-Control
max-age=600 and an Expires ten hours out, so a reader who has been here
before gets the browser's copy, and a browser's copy of a file that never
changes its name can be a year old. The site is deployed, correct and
identical to what the repository says -- and the person looking at it sees
the version they saw last time. There is no error to notice, which is what
makes it the worst kind of bug.

So the URL carries eight characters of the file's own SHA-256. Change a byte
of the stylesheet and the URL changes with it, and no cache anywhere can
serve the old one; change nothing and the URL is byte-identical, so a deploy
that touches no assets costs returning readers nothing.

Run after the assets are final and before the pages that reference them are
built. It is idempotent: an already-stamped reference is restamped, not
doubled.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys

ASSETS = ("app.css", "app.js")


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:8]


def stamps(docs):
    """The version string for each asset, keyed by file name."""
    out = {}
    for name in ASSETS:
        path = os.path.join(docs, "assets", name)
        if not os.path.exists(path):
            sys.exit("stamp_assets: %s is missing; nothing to stamp." % path)
        out[name] = digest(path)
    return out


def stamp_html(html, versions):
    """Rewrite every assets/<name> reference to carry its current hash."""
    for name, version in versions.items():
        # Matches assets/app.js and assets/app.js?v=deadbeef alike, so
        # running this twice leaves one query string rather than two.
        html = re.sub(
            r'((?:\.\./)*|(?:\{base\}/))?assets/' + re.escape(name)
            + r'(?:\?v=[0-9a-f]+)?',
            lambda m: (m.group(1) or "") + "assets/" + name + "?v=" + version,
            html)
    return html


def main():
    docs = sys.argv[1] if len(sys.argv) > 1 else "docs"
    versions = stamps(docs)

    index = os.path.join(docs, "index.html")
    with open(index, encoding="utf-8") as fh:
        before = fh.read()
    after = stamp_html(before, versions)
    if after != before:
        with open(index, "w", encoding="utf-8") as fh:
            fh.write(after)

    print("  stamped       " + ", ".join(
        "%s?v=%s" % (n, v) for n, v in sorted(versions.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
