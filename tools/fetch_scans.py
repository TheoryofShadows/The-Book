#!/usr/bin/env python3
"""Fetch the scans this volume recovers texts from. Run by hand.

    python3 tools/fetch_scans.py            everything not already here
    python3 tools/fetch_scans.py sinodos    one of them
    python3 tools/fetch_scans.py --force    fetch again over what is here

Nothing in the ordinary build touches the network. This is the only
script that does, in the same way tools/build_basemap.py --fetch is: it
is run once, its output is committed under source/extra/, and every
build afterwards reads the committed file.

What is committed is not the archive's plain OCR text. It is the printed
lines recovered from the scan's word coordinates by tools/scans.py --
running heads, marginal line-numbers and footnotes taken off by where
they sit on the leaf rather than by what the scanner made of them -- and
it is written with the scan's own page numbers beside it, so any line of
it can be checked against the page image it came from.

The four sources are the four Ethiopian canon books this volume was
missing, and one of them is missing still; see tools/build_ethiopian.py
for what each one is and what it is not.
"""

from __future__ import annotations

import gzip
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scans                                            # noqa: E402

OUT = "source/extra"

# item      the archive.org identifier
# frm, to   the scan's own image indices, half open. Not printed page
#           numbers: the front matter of these volumes is unnumbered and
#           differs between copies, and an image index is what the
#           archive's reader and its page images agree on
# margin    the longest word that may be a marginal line-number, or 0
#           for a printing that sets none
# head      what the running head must look like for the leaf to belong
#           to this work, where the volume runs another work on from it
SOURCES = {
    "sinodos": {
        "item": "statutesapostle00unkngoog",
        "frm": 173, "to": 279, "margin": 3, "head": None,
        "file": "sinodos-horner-1904.txt",
        "cite": "The Rev. G. Horner, The Statutes of the Apostles, or "
                "Canones Ecclesiastici, edited with translation and "
                "collation from Ethiopic and Arabic MSS. London: Williams "
                "& Norgate, 1904, pages 127-232: the translation of the "
                "Ethiopic text.",
        "note": "Horner's English of the Ge'ez Sinodos whose text he prints "
                "on pages 1-88 of the same volume. The work names itself in "
                "its first sentence: \u201cThis is the Sinodos of the "
                "fathers, the Apostles.\u201d Horner set a line-number in "
                "the margin every five lines, in the outer margin, so it "
                "changes side with the leaf.",
    },
    "baruch": {
        "item": "uncanonicalwrit00isavgoog",
        "frm": 307, "to": 330, "margin": 0, "head": r"BOOK\s+OF",
        "file": "4-baruch-issaverdens-1901.txt",
        "cite": "Jacques (James) Issaverdens, The Uncanonical Writings of "
                "the Old Testament found in the Armenian MSS. of the "
                "Library of St. Lazarus. Venice: Armenian Monastery of St. "
                "Lazarus, 1901, pages 282-304: \u201cFrom the Book of "
                "Paralipomena, which I found in the Books of the "
                "Greeks\u201d.",
        "note": "The fullest of the three Armenian recensions Issaverdens "
                "prints of the work the Ethiopian canon receives as The "
                "Rest of the Words of Baruch, and the one he says was made "
                "from the Greek. The two shorter ones stand on the leaves "
                "before it, printed against each other; the running head "
                "is what separates them, and what selects this one.",
    },
    "covenant": {
        "item": "JAMESApocryphalNewTestament1924",
        "frm": 510, "to": 529, "margin": 0,
        "head": r"EPISTLE\s+OF\s+THE\s+APOSTLES",
        "file": "book-of-the-covenant-james-1924.txt",
        "cite": "Montague Rhodes James, The Apocryphal New Testament. "
                "Oxford: Clarendon Press, 1924, pages 485-503: "
                "\u201cEpistle of the Apostles\u201d.",
        "note": "James's English of the Ethiopic that Guerrier published as "
                "the Testament of our Lord in Galilee, which is the second "
                "book of the Mets'hafe Kidan, the Book of the Covenant. "
                "James's own introduction stands at the head of these "
                "leaves and is not part of the text; tools/build_ethiopian.py "
                "cuts it off at the opening of section 1.",
    },
}

META = "https://archive.org/metadata/{item}"
FILE = "https://archive.org/download/{item}/{name}"


def get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=300) as fh:
        raw = fh.read()
    return gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw


def fetch(item: str) -> str:
    """The item's word-coordinate OCR.

    Found through the item's file list rather than assembled from the
    identifier: most archive items name the derivative after the
    identifier and some do not, and guessing gives a 404 that looks like
    a missing scan.
    """
    listing = json.loads(get(META.format(item=item)))
    names = [f["name"] for f in listing.get("files", [])
             if f["name"].endswith("_djvu.xml")]
    if not names:
        raise SystemExit(f"  {item} has no word-coordinate OCR (_djvu.xml)")
    url = FILE.format(item=item, name=names[0])
    print(f"  fetching {url}")
    return get(url).decode("utf-8", "replace")


def write(key: str, spec: dict, xml: str) -> int:
    got = scans.read(xml, spec["frm"], spec["to"],
                     margin_len=spec["margin"],
                     head=re.compile(spec["head"]) if spec["head"] else None)
    lines = sum(len(p.lines) for p in got)
    if lines < 200:
        print(f"  ERROR: {key} recovered only {lines} lines")
        return 1

    out = [
        "Source: " + spec["cite"],
        "Public domain by age. Scanned by the Internet Archive; "
        "archive.org/details/" + spec["item"],
        "",
        spec["note"],
        "",
        "Recovered from the scan's word coordinates by tools/scans.py, run "
        "from tools/fetch_scans.py: the running heads, the marginal "
        "line-numbers and the footnotes are taken off by where they sit on "
        "the leaf. Each [page n] below is the scan's own image number, so "
        "any line here can be put beside the leaf it came from. Lines are "
        "the printed lines. A blank line means a paragraph opens on the "
        "line after it; the page markers carry no blank line of their "
        "own, so that a paragraph broken by a page turn stays one "
        "paragraph.",
        "-" * 78,
        "",
    ]
    for page in got:
        out.append(f"[page {page.number}]")
        for line in page.lines:
            if line.starts_para:
                out.append("")
            out.append(line.text)

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, spec["file"])
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out).rstrip() + "\n")
    print(f"  {path}: {len(got)} pages, {lines} lines, "
          f"{sum(len(p.margins) for p in got)} marginal numbers dropped, "
          f"{sum(len(p.notes) for p in got)} footnote lines dropped")
    return 0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    force = "--force" in sys.argv[1:]
    want = args or list(SOURCES)

    cache = {}
    bad = 0
    for key in want:
        spec = SOURCES.get(key)
        if spec is None:
            print(f"  unknown source {key}; have {', '.join(SOURCES)}")
            return 2
        path = os.path.join(OUT, spec["file"])
        if os.path.exists(path) and not force:
            print(f"  {path} is already here; --force to fetch again")
            continue
        if spec["item"] not in cache:
            cache[spec["item"]] = fetch(spec["item"])
        bad |= write(key, spec, cache[spec["item"]])
    return bad


if __name__ == "__main__":
    raise SystemExit(main())
