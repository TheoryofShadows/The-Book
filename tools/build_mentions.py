#!/usr/bin/env python3
"""Which places each chapter names, from the gazetteer's own references.

The obvious way to build this is to scan the text for place names. It is also
the wrong way, and the reason is the whole point of the file.

"Dan" is a man, a tribe and a city. "Judah" is a man, a tribe, a kingdom and a
region. "Israel" is a man, a people, a kingdom and a land. A regex cannot tell
which is meant, and every time it guesses wrong the map grows a pin that no
text supports -- in a volume whose build fails over an uncited sentence, and
whose gazetteer refuses to show a guess as a location.

It does not have to guess. OpenBible's dataset already carries a Verses column:
7,394 references, curated, one list per place, and the judgement about which
Dan is which has already been made by someone who could make it. This resolves
those references against the volume's own parsed text and writes out the
inverse -- chapter to places -- which is the direction the reader asks in.

Nothing is invented and nothing is approximated. A reference that does not
resolve is dropped and counted, exactly as tools/build_threads.py drops a
thread stop that does not exist, and the count is held against a committed
figure so a parse change that starts losing references cannot pass quietly.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_places import norm, read_rows  # noqa: E402

RAW = sys.argv[1] if len(sys.argv) > 1 else "source/places/merged.txt"
OUT = sys.argv[2] if len(sys.argv) > 2 else "docs/data"

# The source's abbreviations to this volume's work ids. All 59 of them, all
# Protestant canon -- the dataset covers nothing else -- so the mapping is a
# closed list that can be read and checked rather than a matching rule that
# has to be trusted.
#
# Where this volume splits a book across works, every part is listed and the
# right one is chosen by chapter number: the split works keep the book's own
# numbering, so Second Isaiah's chapters really are 40 to 55.
BOOKS = {
    "Gen": ["genesis"], "Ex": ["exodus"], "Lev": ["leviticus"],
    "Num": ["numbers"], "Deut": ["deuteronomy"], "Josh": ["joshua"],
    "Judg": ["judges"], "Ruth": ["ruth"],
    "1 Sam": ["1-samuel"], "2 Sam": ["2-samuel"],
    "1 Kgs": ["1-kings"], "2 Kgs": ["2-kings"],
    "1 Chr": ["1-chronicles"], "2 Chr": ["2-chronicles"],
    "Ezra": ["ezra"], "Neh": ["nehemiah"], "Est": ["esther-hebrew"],
    "Job": ["job"], "Ps": ["psalms"], "Eccl": ["ecclesiastes"],
    "Sng": ["song-of-songs"],
    "Isa": ["isaiah-1-39-first-isaiah", "isaiah-40-55-second-isaiah",
            "isaiah-56-66-third-isaiah"],
    "Jer": ["jeremiah"], "Lam": ["lamentations"], "Ezek": ["ezekiel"],
    "Dan": ["daniel"], "Hos": ["hosea"], "Joel": ["joel"], "Amos": ["amos"],
    "Obad": ["obadiah"], "Jonah": ["jonah"], "Mic": ["micah"],
    "Nahum": ["nahum"], "Hab": ["habakkuk"], "Zeph": ["zephaniah"],
    "Hag": ["haggai"], "Zech": ["zechariah-1-8", "zechariah-9-14"],
    "Mal": ["malachi"],
    "Matt": ["matthew"], "Mark": ["mark"], "Luke": ["luke"], "John": ["john"],
    "Acts": ["acts"], "Rom": ["romans"],
    "1 Cor": ["1-corinthians"], "2 Cor": ["2-corinthians"],
    "Gal": ["galatians"], "Eph": ["ephesians"], "Phil": ["philippians"],
    "Col": ["colossians"], "1 Thes": ["1-thessalonians"],
    "1 Tim": ["1-timothy"], "2 Tim": ["2-timothy"], "Titus": ["titus"],
    "Heb": ["hebrews"], "1 Pet": ["1-peter"], "2 Pet": ["2-peter"],
    "Jude": ["jude"], "Rev": ["revelation"],
}

REF = re.compile(r"^\s*((?:[1-4]\s+)?[A-Za-z][A-Za-z.]*)\s+(\d+):(\d+)")

# Every reference belonging to a place the gazetteer can draw resolves today,
# so the allowance is nought: anything that stops resolving is a regression in
# the parse or a gap in the mapping, not background noise. Raise it only with
# a reason written next to it.
ALLOWED_UNRESOLVED = 0


def parse_ref(text: str) -> tuple[str, int, int] | None:
    """"2 Kgs 5:12" -> ("2 Kgs", 5, 12). None if it is not a verse reference."""
    m = REF.match(text)
    if not m:
        return None
    book = re.sub(r"\s+", " ", m.group(1)).strip().rstrip(".")
    return book, int(m.group(2)), int(m.group(3))


def resolve(book: str, chapter: int, verse: int, works: dict) -> tuple[str, int] | None:
    """A reference to (work id, chapter index), or None if the volume has no
    such verse.

    The chapter index is not the chapter number: a work may open with a
    prologue, and a split work opens partway through its book. Both are
    handled by looking the number up in the chapters the parse produced rather
    than by arithmetic on it.
    """
    for wid in BOOKS.get(book, []):
        work = works.get(wid)
        if not work:
            continue
        for idx, chap in enumerate(work["chapters"]):
            if chap.get("n") != chapter:
                continue
            if any(v["v"] == verse for v in chap.get("verses", [])):
                return wid, idx
            return None
    return None


def main() -> int:
    if not os.path.exists(RAW):
        print(f"missing {RAW}")
        return 1

    manifest = json.load(open(os.path.join(OUT, "manifest.json"), encoding="utf-8"))
    wanted = {w["id"] for s in manifest["sections"] for w in s["works"]}

    works = {}
    for wid in wanted:
        path = os.path.join(OUT, "works", wid + ".json")
        if os.path.exists(path):
            works[wid] = json.load(open(path, encoding="utf-8"))

    unknown_books: set[str] = set()
    for abbrev in BOOKS:
        for wid in BOOKS[abbrev]:
            if wid not in wanted:
                unknown_books.add(f"{abbrev} -> {wid}")
    if unknown_books:
        print("  ERROR: mapping points at works not in the volume: " +
              ", ".join(sorted(unknown_books)))
        return 1

    # chapter key -> set of place keys
    chapters: dict[str, set[str]] = defaultdict(set)
    resolved = unresolved = undrawable = 0
    missing_books: set[str] = set()

    for row in read_rows(RAW):
        name = (row.get("#ESV") or "").strip()
        key = norm(name)
        if not key:
            continue
        # Only places that made it into the gazetteer: a row with no usable
        # coordinates has nothing to draw and must not reach the map.
        lat = (row.get("Lat") or "").strip().lstrip("><~")
        try:
            float(lat)
        except ValueError:
            # The source marks a place it could not locate with "?". Those
            # references are real; there is simply nowhere to put them, and
            # counting them as failures would hide the ones that are.
            undrawable += len([v for v in (row.get("Verses") or "").split(",")
                               if v.strip()])
            continue

        for raw in (row.get("Verses") or "").split(","):
            ref = parse_ref(raw)
            if ref is None:
                if raw.strip():
                    unresolved += 1
                continue
            book, chapter, verse = ref
            if book not in BOOKS:
                missing_books.add(book)
                unresolved += 1
                continue
            hit = resolve(book, chapter, verse, works)
            if hit is None:
                unresolved += 1
                continue
            chapters[f"{hit[0]}/{hit[1]}"].add(key)
            resolved += 1

    if missing_books:
        print("  ERROR: no mapping for " + ", ".join(sorted(missing_books)))
        return 1

    out = {k: sorted(v) for k, v in sorted(chapters.items())}
    path = os.path.join(OUT, "mentions.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"),
                  sort_keys=True)

    size = os.path.getsize(path) / 1024
    print(f"  mentions      : {resolved} references in {len(out)} chapters, "
          f"{size:.0f} KB")

    if unresolved > ALLOWED_UNRESOLVED:
        print(f"  ERROR: {unresolved} references did not resolve, "
              f"more than the {ALLOWED_UNRESOLVED} accounted for. "
              f"Either the parse changed or the mapping needs an entry.")
        return 1
    print(f"    unresolved  : {unresolved} (allowed {ALLOWED_UNRESOLVED})")
    print(f"    unlocatable : {undrawable} references to places the source "
          f"could not locate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
