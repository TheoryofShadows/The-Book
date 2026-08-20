#!/usr/bin/env python3
"""Emit the whole library as one self-contained HTML file.

Every data file is inlined under window.__BOOK__, keyed by the same path the
served site fetches, so docs/assets/app.js runs unchanged in both. The result
opens from a file:// URL or any host with no network access at all.
"""

from __future__ import annotations

import json
import os
import sys

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
            with open(full, encoding="utf-8") as fh:
                bundle[key] = json.load(fh)
    return bundle


def main() -> int:
    css = open(os.path.join(DOCS, "assets", "app.css"), encoding="utf-8").read()
    js = open(os.path.join(DOCS, "assets", "app.js"), encoding="utf-8").read()
    html = open(os.path.join(DOCS, "index.html"), encoding="utf-8").read()

    bundle = collect()
    # </script> inside the payload would close the tag early.
    payload = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")

    body = html.split("<body>", 1)[1].split("</body>", 1)[0]
    body = body.replace('<script src="assets/app.js"></script>', "")

    page = (
        "<title>The Book in Order</title>\n"
        f"<style>\n{css}\n</style>\n"
        f"{body}\n"
        f'<script id="book-data">window.__BOOK__={payload};</script>\n'
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
