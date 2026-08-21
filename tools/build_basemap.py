#!/usr/bin/env python3
"""Land and water, simplified enough to ship, for drawing places on.

The gazetteer gives 1,232 places their coordinates. Coordinates on their own
are a number a reader has to imagine; the point of a basemap is that they stop
having to. What it takes to draw them is the outline of the land, and nothing
else -- no borders, no relief, no modern countries. A political boundary drawn
across the Iron Age Levant is an anachronism the moment it is drawn, and this
volume has no business asserting one.

Source is Natural Earth, which places its data in the public domain with no
permission required and no attribution demanded. That matters here: every
other body of material in this repository was chosen because it could be
carried without asking, and a basemap under a share-alike tile licence would
have been the one piece a reader could not take offline with the rest.

    ne_110m_land   the whole world, for Tarshish and Rome and Ophir
    ne_50m_land    clipped to the biblical frame, where the detail is wanted

Two things this does that a mapping library would do for us, and which are
here so that no mapping library is needed:

CLIPPING cuts the 50m world down to the frame, using Sutherland-Hodgman
against the four edges. Land that runs off the edge is closed along the edge,
so it fills as land rather than showing as a coastline where the frame stops.

SIMPLIFYING drops the points that do not change the shape, by Visvalingam-
Whyatt: each point is scored by the area of the triangle it makes with its
neighbours, and the flattest go first. It beats Douglas-Peucker on coastlines,
which is the only kind of line here, because it removes detail evenly instead
of chasing the furthest outlier. Small islands are protected by a floor on
points per ring, so Cyprus and Crete survive a threshold that would otherwise
swallow them.

    ./tools/build_basemap.py --fetch     download the source, then build
    ./tools/build_basemap.py             build from source/basemap/

The download is deliberately not part of tools/build.sh. That script runs in
CI, must be deterministic, and must not depend on a third-party host being up;
the output of this one is committed instead, and rebuilt only when the frame
or the budget changes.
"""

from __future__ import annotations

import heapq
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source", "basemap")
OUT = os.path.join(ROOT, "docs", "data", "basemap")

NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"

# west, south, east, north. Nile to Mesopotamia, Anatolia to the top of the
# Red Sea. 1,209 of the 1,232 places in the gazetteer fall inside it; the 23
# that do not are Rome, Tarshish, Spain and the rest of the western horizon,
# which is what the world layer is for.
FRAME = (20.0, 12.0, 55.0, 42.0)

# Uncompressed JSON, before gzip. The whole map feature is meant to cost less
# than a single photograph.
BUDGET = {"world": 80 * 1024, "levant": 120 * 1024}

# No ring may be simplified below this. Without it a threshold chosen for the
# mainland deletes every island, and the Mediterranean loses Cyprus, Crete and
# Rhodes -- three places the texts actually name.
KEEP_MIN = 6

# ~110 m at the equator, which is far below one pixel at any zoom this map
# offers. Storing more is storing noise.
PLACES = 3


# --------------------------------------------------------------------------
# geometry


def ring_points(ring: list) -> list[tuple[float, float]]:
    """GeoJSON positions to (lon, lat) pairs, with any third value dropped."""
    return [(float(p[0]), float(p[1])) for p in ring]


def triangle_area(a, b, c) -> float:
    """Twice the area of the triangle abc. Twice, because halving it changes
    no ordering and the comparison is all this is for."""
    return abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))


def visvalingam(points: list, threshold: float, keep_min: int = KEEP_MIN) -> list:
    """Drop points whose triangle with their neighbours is flatter than
    `threshold`, smallest first, never going below `keep_min`.

    The first and last points are kept, which on a closed ring are the same
    point, so a ring stays closed. Removing a point changes the area of its
    two neighbours, so those are rescored as it goes: the heap carries stale
    entries rather than being reordered, and they are recognised and skipped
    when they surface.
    """
    n = len(points)
    if n <= keep_min:
        return list(points)

    prev = list(range(-1, n - 1))
    nxt = list(range(1, n + 1))
    alive = [True] * n
    area = [0.0] * n

    heap = []
    for i in range(1, n - 1):
        area[i] = triangle_area(points[i - 1], points[i], points[i + 1])
        heapq.heappush(heap, (area[i], i))

    left = n
    while heap and left > keep_min:
        a, i = heapq.heappop(heap)
        # Stale: this point has already gone, or has been rescored since.
        if not alive[i] or a != area[i]:
            continue
        if a >= threshold:
            break
        alive[i] = False
        left -= 1
        p, q = prev[i], nxt[i]
        nxt[p] = q
        prev[q] = p
        for j in (p, q):
            if 0 < j < n - 1 and alive[j]:
                area[j] = triangle_area(points[prev[j]], points[j], points[nxt[j]])
                heapq.heappush(heap, (area[j], j))

    return [points[i] for i in range(n) if alive[i]]


def clip_ring(points: list, frame: tuple) -> list:
    """Sutherland-Hodgman against the frame, one edge at a time.

    The result follows the frame's edge where the land crossed it, which is
    what makes the fill correct: Egypt runs off the bottom of the biblical
    frame and should be drawn as land all the way down to it, not as a
    coastline along latitude twelve.
    """
    west, south, east, north = frame

    def cut(pts, inside, intersect):
        if not pts:
            return []
        out = []
        prev = pts[-1]
        prev_in = inside(prev)
        for cur in pts:
            cur_in = inside(cur)
            if cur_in:
                if not prev_in:
                    out.append(intersect(prev, cur))
                out.append(cur)
            elif prev_in:
                out.append(intersect(prev, cur))
            prev, prev_in = cur, cur_in
        return out

    def at_x(a, b, x):
        t = (x - a[0]) / (b[0] - a[0])
        return (x, a[1] + t * (b[1] - a[1]))

    def at_y(a, b, y):
        t = (y - a[1]) / (b[1] - a[1])
        return (a[0] + t * (b[0] - a[0]), y)

    pts = points[:-1] if len(points) > 1 and points[0] == points[-1] else list(points)
    pts = cut(pts, lambda p: p[0] >= west, lambda a, b: at_x(a, b, west))
    pts = cut(pts, lambda p: p[0] <= east, lambda a, b: at_x(a, b, east))
    pts = cut(pts, lambda p: p[1] >= south, lambda a, b: at_y(a, b, south))
    pts = cut(pts, lambda p: p[1] <= north, lambda a, b: at_y(a, b, north))
    if len(pts) < 3:
        return []
    return pts + [pts[0]]


def rings_of(geojson: dict) -> list:
    """Every ring in the file, outer and inner alike.

    Holes are kept rather than discarded: the Caspian is a hole in the land,
    and filling it would put a sea on the map as ground. The renderer fills
    the whole set with the even-odd rule, which draws them as holes without
    anything here having to record which is which.
    """
    out = []
    for feature in geojson.get("features", []):
        geom = feature.get("geometry") or {}
        kind = geom.get("type")
        coords = geom.get("coordinates") or []
        if kind == "Polygon":
            polys = [coords]
        elif kind == "MultiPolygon":
            polys = coords
        else:
            continue
        for poly in polys:
            for ring in poly:
                if len(ring) >= 4:
                    out.append(ring_points(ring))
    return out


# --------------------------------------------------------------------------
# packing


def pack(rings: list) -> dict:
    """Flat [lon, lat, lon, lat, ...] per ring.

    A pair per point costs two brackets and a comma that carry no information;
    at this many points that punctuation is a fifth of the file.
    """
    flat = []
    for ring in rings:
        arr = []
        for lon, lat in ring:
            arr.append(round(lon, PLACES))
            arr.append(round(lat, PLACES))
        flat.append(arr)
    return {"rings": flat}


def encode(rings: list) -> str:
    return json.dumps(pack(rings), separators=(",", ":"))


def fit(rings: list, budget: int) -> tuple[list, float]:
    """Simplify as little as the budget allows.

    A threshold is a number nobody can pick by looking at it, so it is
    searched for instead: the loosest one whose output still fits. Bisection
    over a wide range, because the useful values span several orders of
    magnitude between the two scales.
    """
    lo, hi = 0.0, 10.0
    best, best_t = None, hi

    for _ in range(28):
        mid = (lo + hi) / 2
        got = [r for r in (visvalingam(r, mid) for r in rings) if len(r) >= 4]
        if len(encode(got)) <= budget:
            best, best_t = got, mid
            hi = mid          # fits: try keeping more detail
        else:
            lo = mid          # too big: simplify harder

    if best is None:
        # Even the hardest threshold in range did not fit. Say so rather than
        # shipping something over budget or silently mangling it further.
        raise SystemExit(
            f"cannot reach {budget} bytes; loosen the budget or the frame")
    return best, best_t


# --------------------------------------------------------------------------


def fetch(name: str) -> str:
    os.makedirs(SRC, exist_ok=True)
    path = os.path.join(SRC, name + ".geojson")
    print(f"  fetching {name}")
    with urllib.request.urlopen(NE + name + ".geojson", timeout=120) as r:
        body = r.read()
    with open(path, "wb") as fh:
        fh.write(body)
    return path


def load(name: str, want_fetch: bool) -> dict:
    path = os.path.join(SRC, name + ".geojson")
    if want_fetch or not os.path.exists(path):
        if not want_fetch:
            raise SystemExit(
                f"missing {path}\nRun ./tools/build_basemap.py --fetch once to "
                "download it. The build does not fetch on its own.")
        path = fetch(name)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    want_fetch = "--fetch" in sys.argv[1:]
    os.makedirs(OUT, exist_ok=True)

    layers = [
        ("world", "ne_110m_land", None),
        ("levant", "ne_50m_land", FRAME),
    ]

    for label, source, frame in layers:
        data = load(source, want_fetch)
        rings = rings_of(data)
        before = sum(len(r) for r in rings)

        if frame:
            rings = [c for c in (clip_ring(r, frame) for r in rings) if c]

        kept, threshold = fit(rings, BUDGET[label])
        body = encode(kept)
        after = sum(len(r) for r in kept)

        path = os.path.join(OUT, label + ".json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)

        print(f"  {label:8s}: {len(kept)} rings, {after} points "
              f"(from {before}), {len(body)/1024:.0f} KB "
              f"of {BUDGET[label]/1024:.0f} KB, threshold {threshold:.5f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
