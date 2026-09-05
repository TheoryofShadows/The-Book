#!/usr/bin/env python3
"""The public address of every chapter, written into the manifest.

    python3 tools/build_slugs.py docs/data

A chapter has two names in this site. The reader counts from zero, because
that is the index of an array -- Genesis 1 is #/read/genesis/0. The crawlable
pages built by tools/build_pages.py count the way the book counts, because a
URL somebody pastes into a footnote should say 5 when the page says 5, and
because Isaiah 40 has to land in the second Isaiah rather than at that work's
first chapter.

Both are right for their job, and for a long time only one of them existed
anywhere a program could read it: build_pages.py worked the printed form out
for itself, on its way to writing a file, and threw it away. So the reader --
which is where a person actually clicks "copy link to this verse" -- had no
way to name the page that had been built for exactly that purpose, and handed
out its own internal index in a fragment instead.

This writes that address down once, into manifest.json, where both halves can
read it: build_pages.py to name the file it writes, and the reader to name
the file that was written. One list, so the two cannot drift.
"""

from __future__ import annotations

import json
import os
import re
import sys


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "chapter"


def chapter_slugs(chapters: list[dict]) -> list[str]:
    """One URL segment per chapter, in the order they are printed.

    The printed number when there is one, the label otherwise. Do not be
    tempted by `n if n > 0 else i + 1`: Jubilees opens with a prologue
    numbered 0, and that formula quietly files it at chapter 1's address,
    where the real chapter 1 then overwrites it. The count of pages written
    still looks right, and a chapter is simply gone.
    """
    slugs = []
    for c in chapters:
        n = c.get("n")
        if isinstance(n, int) and not isinstance(n, bool) and n > 0:
            slugs.append(str(n))
        else:
            slugs.append(slugify(c.get("label") or ""))

    # Whatever the two rules above collide on gets -2, -3, and so on, so that
    # the number of addresses is always the number of chapters.
    seen: dict[str, int] = {}
    out: list[str] = []
    for s in slugs:
        if s not in seen:
            seen[s] = 1
            out.append(s)
            continue
        while True:
            seen[s] += 1
            candidate = "%s-%d" % (s, seen[s])
            if candidate not in seen:
                break
        seen[candidate] = 1
        out.append(candidate)

    if len(set(out)) != len(chapters):
        raise SystemExit("chapter_slugs: %d chapters, %d addresses"
                         % (len(chapters), len(set(out))))
    return out


def build(data_dir: str) -> int:
    path = os.path.join(data_dir, "manifest.json")
    with open(path, encoding="utf-8") as fh:
        manifest = json.load(fh)

    total = 0
    for section in manifest["sections"]:
        for entry in section["works"]:
            work_path = os.path.join(data_dir, "works", entry["id"] + ".json")
            with open(work_path, encoding="utf-8") as fh:
                work = json.load(fh)
            chapters = work.get("chapters") or []
            slugs = chapter_slugs(chapters)
            # The manifest's own chapter count is written by the parse and
            # then edited by every repair script. If it has fallen out of step
            # with the file it counts, the addresses written here would be a
            # list of a different length than the reader indexes into, and the
            # copy-link button would hand out a neighbouring chapter.
            if entry.get("chapters", 0) != len(chapters):
                raise SystemExit(
                    "%s: the manifest counts %d chapters, the work file has %d"
                    % (entry["id"], entry.get("chapters", 0), len(chapters)))
            entry["slugs"] = slugs
            total += len(slugs)

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, separators=(",", ":"))

    print("  %d chapter addresses over %d works"
          % (total, sum(len(s["works"]) for s in manifest["sections"])))
    return 0


def main(argv: list[str]) -> int:
    data_dir = argv[1] if len(argv) > 1 else "docs/data"
    if not os.path.isfile(os.path.join(data_dir, "manifest.json")):
        raise SystemExit("no %s/manifest.json -- give me the data directory"
                         % data_dir)
    return build(data_dir)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
