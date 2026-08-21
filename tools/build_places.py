#!/usr/bin/env python3
"""Build the gazetteer: biblical place names to coordinates on the earth.

Source is OpenBible.info's Bible Geocoding dataset, CC BY 4.0, some of it
derived from OpenStreetMap under the ODbL. Both are credited on the site.

The reason this dataset is worth using rather than any list of coordinates is
that it marks its own uncertainty, and this project cannot drop a confident pin
on a place scholars argue about. The source encodes that in prefixes:

    >   the place SURROUNDS this point   Assyria is the region around Nineveh
    <   the place is INSIDE this city    the Gate of the Guard, within Jerusalem
    ~   the position is APPROXIMATE      known roughly, not precisely

Those become an explicit 'kind' on every record, and the interface says which
one it is rather than showing every place as a dot. A region is not a pin, and
a guess is not a location.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textnorm  # noqa: E402

RAW = sys.argv[1] if len(sys.argv) > 1 else "source/places/merged.txt"
OUT = sys.argv[2] if len(sys.argv) > 2 else "docs/data"

KIND = {
    ">": ("region", "A region or territory, not a single place. The map "
                    "centres on {root}, which sits inside it."),
    "<": ("within", "A specific spot inside {root}. The map centres on the "
                    "city rather than the spot itself."),
    "~": ("approximate", "The position is approximate. This is roughly where "
                         "it was, not a precise identification."),
}


# Places the source states as a plain point where the identification is in
# fact argued over. The prefixes above carry the source's own uncertainty and
# carry it well, but they mark uncertainty about *where a known place was*,
# not about *whether this is the place at all*, and a few famous entries fall
# in the second category with nothing to show it.
#
# It matters more once there is a map. A line of coordinates is read as a
# reference; a filled dot on a coastline is read as a finding. Drawing
# Tarshish in Spain settles, in the reader's eye, an argument that is not
# settled -- and this volume refuses that move everywhere else, in the
# positions panel, in the accuracy report, in the threads.
#
# These are demoted to "approximate" and carry their own note naming the
# candidates. The list is short, reviewed, and deliberately not mechanical:
# every entry is a case where the dispute is over the identification itself
# and is standard enough to state without taking a side. Sites argued over at
# a scale below a map pixel -- Bethsaida's two candidate mounds, Cana's two
# villages -- are left alone, because the pin is not what is wrong about them.
DISPUTED = {
    "tarshish":
        "Which place this is remains disputed. Tartessos in southern Spain, "
        "Tarsus in Cilicia, Sardinia and Carthage have all been argued for. "
        "The map shows one of the candidates, not a settled location.",
    "sinai":
        "The mountain has never been securely identified. The traditional "
        "site shown here is Byzantine; Jebel Serbal, Har Karkom and sites in "
        "north-western Arabia have all been proposed.",
    "horeb":
        "The same mountain as Sinai under another name, and as unidentified. "
        "The traditional site shown here is Byzantine, not archaeological.",
    "sodom":
        "Unlocated. Candidate sites lie both south of the Dead Sea and north "
        "of it, and many hold the city to be unrecoverable.",
    "gomorrah":
        "Unlocated, and argued over on the same grounds as Sodom.",
    "emmaus":
        "Four sites have been proposed, and the manuscripts of Luke disagree "
        "about the distance that would decide between them.",
    "ararat":
        "The text names a region -- the mountains of Ararat, Assyrian Urartu "
        "-- rather than the single peak shown here, which is a much later "
        "identification.",
}


def norm(name: str) -> str:
    """The same key the lexicon and the reader use. See tools/textnorm.py."""
    return textnorm.lookup_key(name)


def read_rows(path: str) -> list[dict]:
    """The gazetteer's rows, with the source's header comments dropped.

    tools/build_mentions.py reads the same file for its Verses column, and
    parsing it twice is how the two would quietly stop agreeing about which
    rows exist.
    """
    with open(path, encoding="utf-8", errors="replace") as fh:
        rows = [ln for ln in fh if not ln.startswith("#") or ln.startswith("#ESV")]
    return list(csv.DictReader(rows, delimiter="\t"))


def main() -> int:
    if not os.path.exists(RAW):
        print(f"missing {RAW}")
        return 1

    shards: dict[str, dict] = defaultdict(dict)
    counts = defaultdict(int)
    disputed_seen: set[str] = set()
    total = 0

    for row in read_rows(RAW):
        name = (row.get("#ESV") or "").strip()
        lat_raw = (row.get("Lat") or "").strip()
        lon_raw = (row.get("Lon") or "").strip()
        if not name or not lat_raw or not lon_raw:
            continue

        kind, note = "point", ""
        marker = lat_raw[0]
        if marker in KIND:
            kind, note = KIND[marker]
        lat_raw = lat_raw.lstrip("><~")
        lon_raw = lon_raw.lstrip("><~")

        try:
            lat, lon = round(float(lat_raw), 5), round(float(lon_raw), 5)
        except ValueError:
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue

        root = (row.get("Root") or "").strip() or name
        verses = [v.strip() for v in (row.get("Verses") or "").split(",") if v.strip()]
        comment = (row.get("Comment") or "").strip()

        key = norm(name)
        if not key:
            continue

        # A contested identification is not a precise one, whatever the source
        # says. Demoting it here rather than in the renderer means every view
        # of the place agrees -- the panel, the map and the coordinates alike.
        if key in DISPUTED:
            kind, note = "approximate", DISPUTED[key]
            disputed_seen.add(key)

        record = {
            "name": name,
            "lat": lat,
            "lon": lon,
            "kind": kind,
            "mentions": len(verses),
        }
        if note:
            record["note"] = note.format(root=root)
        # The comment column carries genuine modern identifications ("Now
        # Barada River") mixed with the source's own bookkeeping. Keep the
        # former, drop the latter rather than showing a reader "region" as
        # though it were a modern place name.
        if comment and not re.search(r"\bin KML\b|^region$|^approximate$",
                                     comment, re.I):
            record["modern"] = comment
        if root != name:
            record["root"] = root

        shard = key[0] if key[0].isalpha() else "0"
        if key not in shards[shard]:
            shards[shard][key] = record
            counts[kind] += 1
            total += 1

    out_dir = os.path.join(OUT, "places")
    os.makedirs(out_dir, exist_ok=True)
    for shard, table in shards.items():
        with open(os.path.join(out_dir, f"{shard}.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(table, fh, ensure_ascii=False, separators=(",", ":"),
                      sort_keys=True)

    # A demotion that stops matching is worse than no demotion: the map goes
    # back to asserting the disputed location and nothing says it changed.
    missing = sorted(set(DISPUTED) - disputed_seen)
    if missing:
        print(f"  ERROR: disputed entries matched no place: {', '.join(missing)}")
        return 1

    size = sum(os.path.getsize(os.path.join(out_dir, f))
               for f in os.listdir(out_dir))
    print(f"  places        : {total}")
    for k in ("point", "region", "approximate", "within"):
        print(f"    {k:12s}: {counts[k]}")
    print(f"  shards        : {len(shards)}, {size/1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
