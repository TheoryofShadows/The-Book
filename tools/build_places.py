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


def norm(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9 ]+", "", name).strip()


def main() -> int:
    if not os.path.exists(RAW):
        print(f"missing {RAW}")
        return 1

    shards: dict[str, dict] = defaultdict(dict)
    counts = defaultdict(int)
    total = 0

    with open(RAW, encoding="utf-8", errors="replace") as fh:
        rows = [ln for ln in fh if not ln.startswith("#") or ln.startswith("#ESV")]
    reader = csv.DictReader(rows, delimiter="\t")

    for row in reader:
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

    size = sum(os.path.getsize(os.path.join(out_dir, f))
               for f in os.listdir(out_dir))
    print(f"  places        : {total}")
    for k in ("point", "region", "approximate", "within"):
        print(f"    {k:12s}: {counts[k]}")
    print(f"  shards        : {len(shards)}, {size/1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
