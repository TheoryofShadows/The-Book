#!/usr/bin/env python3
"""Resolve every thread stop against the published text.

A thread names references only. This resolves each one against the same JSON
the reader loads, pulls the actual verse text, and refuses to emit anything if
a reference does not exist. The threads therefore cannot quote a verse the
volume does not contain, or drift if the parse changes.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from threads import THREADS  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/data"


def main() -> int:
    manifest = json.load(open(os.path.join(OUT, "manifest.json"), encoding="utf-8"))
    meta = {}
    order = {}
    for i, section in enumerate(manifest["sections"]):
        for work in section["works"]:
            meta[work["id"]] = (work, section)
            order[work["id"]] = i

    out, problems = [], []

    for thread in THREADS:
        stops = []
        for stop in thread["stops"]:
            wid = stop["work"]
            if wid not in meta:
                problems.append(f"{thread['id']}: no work '{wid}'")
                continue
            work_meta, section = meta[wid]
            path = os.path.join(OUT, "works", wid + ".json")
            work = json.load(open(path, encoding="utf-8"))

            idx = stop["chapter"]
            if idx >= len(work["chapters"]):
                problems.append(f"{thread['id']}: {wid} has no chapter index {idx}")
                continue
            chapter = work["chapters"][idx]

            found = []
            for want in stop["verses"]:
                hit = next((v for v in chapter.get("verses", []) if v["v"] == want), None)
                if hit is None:
                    problems.append(
                        f"{thread['id']}: {wid} {chapter['label']} has no verse {want}")
                    continue
                found.append({"v": want, "t": hit["t"]})

            if not found:
                continue

            stops.append({
                "work": wid,
                "workTitle": work_meta["title"],
                "chapter": idx,
                "label": chapter["label"],
                "section": section["roman"] or "",
                "dates": section["dates"],
                "verses": found,
                "why": stop["why"],
                "aside": stop.get("aside"),
                "_order": order[wid],
                "_deliberate": bool(stop.get("outOfOrder")),
            })

        # The premise of a thread is that it runs forward in time. A stop that
        # goes backwards has to say why, or the thread is quietly lying about
        # the one thing it exists to show.
        #
        # The permission is a flag of its own rather than the presence of an
        # aside. It used to be the aside: any non-empty one let a stop past,
        # and an aside is a general-purpose note -- the next one written about
        # a translation or a variant reading would have waved a genuinely
        # misordered stop through without anybody meaning it to. So the author
        # has to say "this one goes back, and here is why" in two fields, and
        # a flag on a stop that does not in fact go back is a finding too:
        # a stale permission is how a gate stops being a gate.
        prev = -1
        for s in stops:
            backwards = s["_order"] < prev
            if backwards and not s.pop("_deliberate", False):
                problems.append(
                    f"{thread['id']}: {s['work']} goes backwards in the "
                    f"sequence without 'outOfOrder': True saying it is meant to")
            elif backwards and not s.get("aside"):
                problems.append(
                    f"{thread['id']}: {s['work']} is marked 'outOfOrder' but "
                    f"carries no 'aside' telling the reader why")
            elif not backwards and s.pop("_deliberate", False):
                problems.append(
                    f"{thread['id']}: {s['work']} is marked 'outOfOrder' and "
                    f"runs forward; the flag is stale")
            prev = max(prev, s["_order"])
        for s in stops:
            s.pop("_deliberate", None)
            del s["_order"]

        # The earliest and latest era the thread actually reaches, rather than
        # the era of its first and last stop. The reader's own thread card
        # printed the latter, so "Where do the dead go?" -- whose third stop
        # is the Isaiah apocalypse, filed back in Section II -- advertised
        # itself as running from IV to IX when it runs from II to IX. The
        # card's whole job is to say how far across the library the question
        # travels, and it was understating it on the one thread that goes
        # furthest. Worked out here, where the section order is known, rather
        # than in a view that only has the stops.
        eras = [s["section"] for s in stops if s["section"]]
        by_order = sorted(
            (s for s in stops if s["section"]),
            key=lambda s: order[s["work"]])
        out.append({
            "id": thread["id"],
            "title": thread["title"],
            "question": thread["question"],
            "closing": thread["closing"],
            "sections": {
                "earliest": by_order[0]["section"] if by_order else "",
                "latest": by_order[-1]["section"] if by_order else "",
                "count": len(set(eras)),
            },
            "stops": stops,
        })

    if problems:
        for p in problems:
            print("  BROKEN  " + p)
        print(f"{len(problems)} broken references; threads not written")
        return 1

    with open(os.path.join(OUT, "threads.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))

    for t in out:
        print(f"  {t['id']:22s} {len(t['stops'])} stops")
    print(f"{len(out)} threads, all references resolved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
