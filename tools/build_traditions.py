#!/usr/bin/env python3
"""Emit the tradition table, and refuse to build a claim that cannot hold.

    python3 tools/build_traditions.py docs/data

Fails when a tradition names a canon that canon.json does not have, when two
traditions answer to the same word, when a note is made without a source, or
when a family is used that FAMILIES does not list. Every one of those is a
statement about somebody's religion going onto a page, and the cheapest place
to catch a wrong one is here.

Deliberately does not fail on a tradition whose canon is None. That is not a
missing value to be filled in later: the Assyrian Church of the East reads a
New Testament of twenty-two books and the Samaritan Torah is a different
recension of the text, and answering either by pointing at one of the five
columns would be worse than saying so.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from traditions import FAMILIES, TRADITIONS  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/data"


def main() -> int:
    with open(os.path.join(OUT, "canon.json"), encoding="utf-8") as fh:
        canons = set(json.load(fh)["canons"])

    problems: list[str] = []
    seen_ids: set[str] = set()
    seen_words: dict[str, str] = {}

    for t in TRADITIONS:
        where = t.get("id", "(no id)")
        if not t.get("id") or not t.get("name"):
            problems.append(f"{where}: needs an id and a name")
        if t["id"] in seen_ids:
            problems.append(f"{where}: duplicate id")
        seen_ids.add(t["id"])

        if t["family"] not in FAMILIES:
            problems.append(f"{where}: family {t['family']!r} is not in FAMILIES")

        # The one that matters: a canon key nothing can honour would send a
        # reader to a scope that silently searches everything.
        if t["canon"] is not None and t["canon"] not in canons:
            problems.append(
                f"{where}: canon {t['canon']!r} is not in canon.json "
                f"({', '.join(sorted(canons))})")

        if t.get("approx") and not t["canon"]:
            problems.append(f"{where}: approximate to no canon at all")
        if t.get("approx") and not t["note"]:
            problems.append(
                f"{where}: names an approximate canon and does not say so")

        # A sentence about what a church holds has to be checkable.
        if t["note"] and not t["source"]:
            problems.append(f"{where}: has a note and no source for it")

        # Two traditions answering to one word means one of them is
        # unreachable, and which one is an accident of list order.
        for word in [t["name"].lower()] + list(t["also"]):
            key = " ".join(word.lower().split())
            if key in seen_words and seen_words[key] != t["id"]:
                problems.append(
                    f"{where}: the word {key!r} already reaches "
                    f"{seen_words[key]}")
            seen_words[key] = t["id"]

    if problems:
        for p in problems:
            print(f"traditions: {p}", file=sys.stderr)
        return 1

    out = {
        "families": FAMILIES,
        "traditions": [
            {"id": t["id"], "name": t["name"], "family": t["family"],
             "canon": t["canon"], "also": t["also"],
             # True where the canon named is the nearest column rather than
             # this tradition's own list. The reader is told so instead of
             # the lead sentence claiming a canon the note takes back.
             "approx": bool(t.get("approx")),
             "note": t["note"], "source": t["source"]}
            for t in TRADITIONS
        ],
    }
    path = os.path.join(OUT, "traditions.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"),
                  sort_keys=True)

    mapped = sum(1 for t in TRADITIONS if t["canon"])
    print(f"traditions       : {len(TRADITIONS)}, {mapped} mapped to a canon, "
          f"{len(TRADITIONS) - mapped} answered without one")
    print(f"  words they answer to : {len(seen_words)}")
    print(f"  {os.path.getsize(path) / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
