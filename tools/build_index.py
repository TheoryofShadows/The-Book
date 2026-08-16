#!/usr/bin/env python3
"""Build the client-side search index.

The index maps each token to the chapters that contain it, not to individual
verses. Chapter granularity keeps the shipped index around a tenth of the size
of a verse-level one; the client narrows candidate chapters from the index,
then fetches only those works and finds the exact verses itself.

Tokens are sharded by first character so a query downloads a few small files
instead of the whole index. Tokens that occur in more than COMMON_RATIO of all
chapters carry no posting list: they are useless for narrowing, and the client
still enforces them when it checks the candidate text.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict

DATA = sys.argv[1] if len(sys.argv) > 1 else "docs/data"
COMMON_RATIO = 0.35
TOKEN = re.compile(r"[a-z0-9]+")


def normalise(text: str) -> list[str]:
    text = text.lower()
    text = text.replace("’", "'").replace("‘", "'")
    return TOKEN.findall(text)


def main() -> int:
    manifest = json.load(open(os.path.join(DATA, "manifest.json"), encoding="utf-8"))

    chapters: list[list] = []      # [workId, chapterIndex, label, workTitle]
    postings: dict[str, set[int]] = defaultdict(set)

    for section in manifest["sections"]:
        for meta in section["works"]:
            path = os.path.join(DATA, "works", meta["id"] + ".json")
            if not os.path.exists(path):
                continue
            work = json.load(open(path, encoding="utf-8"))
            for idx, chapter in enumerate(work["chapters"]):
                cid = len(chapters)
                chapters.append([meta["id"], idx, chapter["label"], meta["title"]])
                blob = " ".join(
                    [v["t"] for v in chapter.get("verses", [])] +
                    chapter.get("paras", [])
                )
                for token in set(normalise(blob)):
                    postings[token].add(cid)

    total = len(chapters)
    limit = int(total * COMMON_RATIO)

    shards: dict[str, dict] = defaultdict(dict)
    common: list[str] = []
    for token, cids in postings.items():
        key = token[0] if token[0].isalpha() else "0"
        if len(cids) > limit:
            common.append(token)
            shards[key][token] = 0          # present, but not selective
        else:
            shards[key][token] = sorted(cids)

    out = os.path.join(DATA, "index")
    os.makedirs(out, exist_ok=True)
    # sort_keys keeps the output byte-identical between runs: token order
    # otherwise follows set iteration, which Python's hash randomisation
    # varies from process to process, and CI checks these files for drift.
    for key, table in shards.items():
        with open(os.path.join(out, f"{key}.json"), "w", encoding="utf-8") as fh:
            json.dump(table, fh, ensure_ascii=False, separators=(",", ":"),
                      sort_keys=True)

    with open(os.path.join(DATA, "chapters.json"), "w", encoding="utf-8") as fh:
        json.dump({"chapters": chapters, "common": sorted(common)}, fh,
                  ensure_ascii=False, separators=(",", ":"))

    size = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out))
    print(f"chapters indexed : {total}")
    print(f"distinct tokens  : {len(postings)}")
    print(f"non-selective    : {len(common)} ({', '.join(sorted(common)[:12])}...)")
    print(f"index shards     : {len(shards)}, {size/1024/1024:.2f} MB total")
    print(f"largest shard    : "
          f"{max((os.path.getsize(os.path.join(out, f)), f) for f in os.listdir(out))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
