#!/usr/bin/env python3
"""Works whose title names something this volume does not contain.

    python3 tools/build_cautions.py docs/data

Nearly everything absent from this collection is absent visibly: the canon
table says which books are missing and cites why, the accuracy report lists
what was patched, and a work with no text prints a page saying so. The one
kind of gap that hides is a gap standing behind a name something else is
already using.

There is exactly one of those, and it is a bad one. The famous Gospel of
Thomas -- the sayings gospel -- came out of Nag Hammadi in 1945, and every
English rendering of the Coptic is in copyright, so it is behind the same wall
as the Dead Sea Scrolls. This volume does print a Gospel of Thomas: the Infancy
Gospel, a different second-century text about Jesus's childhood, which the
Ante-Nicene Fathers prints under a title beginning "THE GOSPEL OF THOMAS". A
reader who searches for the one gets the other, at the top of the results,
under a heading that says "That is a place in the volume" -- one confident
answer, pointing at the wrong book, with nothing anywhere saying so.

The title now carries "(INFANCY)", which is a real improvement and is not
enough: it corrects a reader who already knows there are two, and those are
not the readers this costs.

So the work carries the sentence itself, in the two places a reader meets it:
the note printed above the text, and a short line the reader shows beside a
reference that resolves here. Both say what is not here, why it is not here,
and what part of it could be -- which is the same shape as every other gap
this volume admits to, rather than a special case.

Standard library only, like every other script here.
"""

from __future__ import annotations

import json
import os
import sys

# id -> what a reader has to be told before they read a word of it.
#
#   short  one line, shown wherever the work is offered as an answer
#   note   paragraphs, appended to the work's own note above the text
#
# The note repeats the short line rather than continuing from it: they are
# read in either order and neither can assume the other was seen.
CAUTIONS = {
    "the-gospel-of-thomas-infancy-first-greek-form": {
        "short": "Not the sayings gospel. This is the Infancy Gospel of "
                 "Thomas, a different second-century text.",
        "note": [
            "This is not the Gospel of Thomas most people are looking for. "
            "The famous one is the sayings gospel, a list of 114 sayings "
            "attributed to Jesus, recovered in Coptic at Nag Hammadi in 1945. "
            "This is the Infancy Gospel of Thomas: a second-century narrative "
            "of Jesus's childhood, printed by the Ante-Nicene Fathers under a "
            "title beginning “The Gospel of Thomas”, which is where "
            "the collision comes from.",

            "The sayings gospel is not in this volume, and its absence is the "
            "same wall the Dead Sea Scrolls are behind: every English "
            "translation of the Coptic is in copyright, and this collection "
            "prints nothing that is not public domain. One partial route in "
            "is open and has not been taken -- Grenfell and Hunt's English of "
            "the three Greek fragments from Oxyrhynchus, published between "
            "1897 and 1904, which carry about a fifth of the sayings. That is "
            "a gap in the work done here rather than in what is permitted, "
            "and the accuracy report counts it as one.",
        ],
    },
}


def apply_to(entry: dict, caution: dict) -> bool:
    """Add the caution to a manifest entry or a work file. Idempotent: the
    build runs this over data the last run already touched only when a rebuild
    starts from a fresh parse, but a script that doubles its own output when
    run twice is a script that will eventually be run twice."""
    changed = False
    if entry.get("caution") != caution["short"]:
        entry["caution"] = caution["short"]
        changed = True
    note = list(entry.get("note") or [])
    for paragraph in caution["note"]:
        if paragraph not in note:
            note.append(paragraph)
            changed = True
    entry["note"] = note
    return changed


def build(data_dir: str) -> int:
    path = os.path.join(data_dir, "manifest.json")
    with open(path, encoding="utf-8") as fh:
        manifest = json.load(fh)

    seen = set()
    for section in manifest["sections"]:
        for entry in section["works"]:
            caution = CAUTIONS.get(entry["id"])
            if not caution:
                continue
            seen.add(entry["id"])
            apply_to(entry, caution)

            work_path = os.path.join(data_dir, "works", entry["id"] + ".json")
            with open(work_path, encoding="utf-8") as fh:
                work = json.load(fh)
            apply_to(work, caution)
            with open(work_path, "w", encoding="utf-8") as fh:
                json.dump(work, fh, ensure_ascii=False, separators=(",", ":"))

    # A caution for a work that is no longer here is a caution nobody will
    # ever read, and the most likely reason for one is that the work was
    # renamed -- which is exactly when the warning is needed most.
    missing = sorted(set(CAUTIONS) - seen)
    if missing:
        raise SystemExit("no such work for caution: " + ", ".join(missing))

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, separators=(",", ":"))

    for wid in sorted(seen):
        print("  %s" % wid)
    print("  %d work%s carries a caution"
          % (len(seen), "" if len(seen) == 1 else "s"))
    return 0


def main(argv: list[str]) -> int:
    data_dir = argv[1] if len(argv) > 1 else "docs/data"
    if not os.path.isfile(os.path.join(data_dir, "manifest.json")):
        raise SystemExit("no %s/manifest.json -- give me the data directory"
                         % data_dir)
    return build(data_dir)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
