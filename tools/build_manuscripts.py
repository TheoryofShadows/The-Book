#!/usr/bin/env python3
"""Attach manuscript witnesses to works, and check the references hold.

Fails if a work id does not exist or a witness id is unknown, so the links
cannot rot against a renamed work the way a hand-maintained list would.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manuscripts import (  # noqa: E402
    WITNESSES, WORKS, NT_SECTION_WITNESSES, HERMAS_WITNESSES)

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/data"

NT_SECTION = "section-ix-new-testament-writings"
HERMAS_SECTION = "the-shepherd-of-hermas"


def main() -> int:
    manifest = json.load(open(os.path.join(OUT, "manifest.json"), encoding="utf-8"))
    known = set()
    section_of = {}
    for section in manifest["sections"]:
        for work in section["works"]:
            known.add(work["id"])
            section_of[work["id"]] = section["id"]

    problems = []
    mapping: dict[str, list[str]] = {}

    for wid, ids in WORKS.items():
        if wid not in known:
            problems.append(f"no such work: {wid}")
            continue
        for i in ids:
            if i not in WITNESSES:
                problems.append(f"{wid}: unknown witness '{i}'")
        mapping.setdefault(wid, []).extend(ids)

    # Whole-collection witnesses, applied by section.
    for wid, sid in section_of.items():
        if sid == NT_SECTION:
            mapping.setdefault(wid, []).extend(NT_SECTION_WITNESSES)
        elif sid == HERMAS_SECTION:
            mapping.setdefault(wid, []).extend(HERMAS_WITNESSES)

    for i in WITNESSES:
        if not WITNESSES[i].get("url", "").startswith(("http://", "https://")):
            problems.append(f"witness {i}: bad url")

    if problems:
        for p in problems:
            print("  BROKEN  " + p)
        return 1

    # de-duplicate, keep order
    for wid, ids in mapping.items():
        seen, out = set(), []
        for i in ids:
            if i not in seen:
                seen.add(i)
                out.append(i)
        mapping[wid] = out

    with open(os.path.join(OUT, "manuscripts.json"), "w", encoding="utf-8") as fh:
        json.dump({"witnesses": WITNESSES, "works": mapping}, fh,
                  ensure_ascii=False, separators=(",", ":"))

    print(f"  witnesses     : {len(WITNESSES)}")
    print(f"  works linked  : {len(mapping)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
