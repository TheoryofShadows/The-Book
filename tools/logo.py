#!/usr/bin/env python3
"""The mark, defined once, as geometry rather than as a drawing.

An open book, seen from the front: a navy board either side of the spine,
and gold leaves fanning up off it. Everything runs from one point -- the
foot of the spine -- which is what makes it read as a book opened flat
rather than as a pair of wings.

Everything downstream -- the SVG in the page head, the tile in a browser
tab, the PNG an iPhone puts on a home screen, the lockup in the README --
is generated from the numbers below, so the mark cannot drift between them.

Coordinates are in a 24 x 24 box, the size the header draws it at. The book
is wider than it is tall, so it sits in a band across the middle of that box
rather than filling it; the tile adds its own padding on top.

Only the right half is written down. The left is its mirror, because a book
opened flat is symmetrical and saying so once is the way to keep it that
way -- the old mark drifted precisely because both halves were typed out.
"""

from __future__ import annotations

# The foot of the spine. Every leaf and both boards start here, and the
# fan is what you get by sending them to different places from it.
SPINE = (12.0, 17.9)

# The band the book occupies inside the 24 x 24 box. The source drawing is
# 687 x 396, which is 1.735:1, and this keeps that.
EDGE = 22.7                                     # how far out a board reaches
TOP = 5.4                                       # the highest any leaf goes

BOX = 24.0

# Navy for the boards, gold for the leaves. Sampled from the drawing rather
# than guessed: #0c2d5a and #d5ab6f are its two modal colours.
NAVY = (0x0C, 0x2D, 0x5A)
GOLD = (0xD5, 0xAB, 0x6F)
# The lighter gold the leaves catch towards the spine. Two tones rather than
# a gradient: a gradient is one more thing the rasteriser would have to know
# about, and at sixteen pixels it is not the difference between them that
# reads, it is the hairline.
GOLD_LIT = (0xE8, 0xC8, 0x94)
PAPER = (0xFF, 0xFF, 0xFF)

# Kept for the tile's ground, which wants the site's own colour rather than
# the mark's -- a navy tile with a navy board on it is a tile with a hole.
ACCENT = NAVY

# Each leaf: how far out it reaches, where its outer edge starts and stops,
# how much its bottom edge sags on the way out, and where it lands back on
# the spine. Ordered outermost first, which is also back to front: the
# boards are under everything, and each leaf is drawn over the one outside
# it, so what you see of the outer ones is their edge -- which is what a
# fanned page block is.
#
#   out    x the leaf reaches
#   ytop   y of its outer corner, top
#   ybot   y of its outer corner, bottom
#   sag    how far below the straight line the bottom edge bows
#   rise   y it returns to on the spine
#   peak   where a leaf is tallest, if it is a leaf
#   tone   its colour
#
# A board has no peak: it is a crescent, and its top edge runs straight back
# to the spine. A leaf has one, and it sits about halfway out rather than at
# either edge -- which is the whole difference between a fanned page block
# and a row of spikes. Measured off the drawing: its highest gold is a little
# under 60% of the way from the spine to the fore-edge.
LEAVES = [
    # The two boards, under everything. Wider, lower and squarer at the
    # corner than any leaf, the way a board overhangs the text block.
    dict(out=EDGE,        ytop=12.9, ybot=15.6, sag=2.9, rise=17.5, tone="navy"),
    dict(out=EDGE - 1.1,  ytop=13.4, ybot=15.9, sag=2.7, rise=17.4, tone="navy"),
    # The leaves. Each stops short of the one outside it at the fore-edge,
    # and peaks higher and further in, which is the fan.
    # The fore-edge of a leaf is long and nearly upright -- in the drawing it
    # runs about a third of the mark's height -- and the top edge off it is a
    # shallow rise, not a climb. That pair is what makes the shoulders step;
    # short fore-edges and steep tops gave a lotus.
    dict(out=EDGE - 2.7,  ytop=7.8,  ybot=12.7, sag=2.2, rise=17.2,
         peak=(17.8, 6.8), tone="gold"),
    dict(out=EDGE - 4.4,  ytop=6.8,  ybot=11.7, sag=1.9, rise=16.9,
         peak=(15.9, 5.8), tone="gold"),
    dict(out=EDGE - 6.3,  ytop=6.2,  ybot=10.8, sag=1.6, rise=16.5,
         peak=(14.2, TOP), tone="lit"),
]

TONES = {"navy": NAVY, "gold": GOLD, "lit": GOLD_LIT}

# How much larger the paper hairline under each leaf is, measured from the
# spine. The leaves are drawn from the spine outwards, so scaling one about
# that point and laying it down first is a rule that separates every pair of
# them at once -- and it stays a hairline at every size, because it scales
# with the mark.
HAIRLINE = 0.028


def _mirror(pt: tuple[float, float]) -> tuple[float, float]:
    return (BOX - pt[0], pt[1])


def _leaf_path(leaf: dict, right: bool) -> list:
    """One leaf, as a closed path: move, curve, line, curve, close.

    Segments are ('M', p), ('Q', control, p) or ('L', p). Quadratics rather
    than cubics because every curve here is a single bow and a quadratic is
    exactly that -- and it halves what has to be flattened for the PNG.
    """
    sx, sy = SPINE
    out, ytop, ybot = leaf["out"], leaf["ytop"], leaf["ybot"]

    # The bottom edge bows below the straight line from the spine to the
    # fore-edge; without it the mark is a chevron, not a book.
    mid_x = (sx + out) / 2.0
    mid_y = (sy + ybot) / 2.0
    bottom_ctrl = (mid_x, mid_y + leaf["sag"])

    pts = [
        ("M", (sx, sy)),
        ("Q", bottom_ctrl, (out, ybot)),
        ("L", (out, ytop)),
    ]

    peak = leaf.get("peak")
    if peak is None:
        # A board: straight back to the spine along a flatter bow.
        pts.append(("Q", ((sx + out) / 2.0,
                          (leaf["rise"] + ytop) / 2.0 + leaf["sag"] * 0.55),
                    (sx, leaf["rise"])))
    else:
        # A leaf: up the cut top edge to the peak, then a long inner edge
        # falling away into the gutter. The inner edge bows towards the
        # spine, so the V between the two halves is a curve and not a
        # wedge -- pages lean, they do not hinge.
        pts.append(("L", peak))
        # Nearly straight, and only barely bowed. An inner edge with much
        # curve in it turns the gutter into the gap between two petals; the
        # thing that keeps it a book is that all ten of these edges run
        # almost dead straight into the same point.
        inner_ctrl = (sx + (peak[0] - sx) * 0.30,
                      peak[1] + (leaf["rise"] - peak[1]) * 0.62)
        pts.append(("Q", inner_ctrl, (sx, leaf["rise"])))
    if right:
        return pts
    return [(seg[0],) + tuple(_mirror(p) for p in seg[1:]) for seg in pts]


def _scaled(path: list, k: float) -> list:
    """The same path, blown up about the foot of the spine."""
    sx, sy = SPINE
    def s(p):
        return (sx + (p[0] - sx) * k, sy + (p[1] - sy) * k)
    return [(seg[0],) + tuple(s(p) for p in seg[1:]) for seg in path]


def shapes() -> list[tuple[list, tuple[int, int, int]]]:
    """Every filled path in the mark, in drawing order, back to front.

    A paper-coloured copy of each leaf goes down first, very slightly larger,
    which is what leaves the hairline between it and the leaf outside it.
    """
    out = []
    for leaf in LEAVES:
        for right in (False, True):
            path = _leaf_path(leaf, right)
            out.append((_scaled(path, 1.0 + HAIRLINE), PAPER))
            out.append((path, TONES[leaf["tone"]]))
    return out


def flatten(path: list, steps: int = 24) -> list[tuple[float, float]]:
    """The path as a polygon, for anything that has to fill it by pixel."""
    pts: list[tuple[float, float]] = []
    here = (0.0, 0.0)
    for seg in path:
        kind = seg[0]
        if kind == "M":
            here = seg[1]
            pts.append(here)
        elif kind == "L":
            here = seg[1]
            pts.append(here)
        elif kind == "Q":
            ctrl, end = seg[1], seg[2]
            x0, y0 = here
            for i in range(1, steps + 1):
                t = i / steps
                u = 1.0 - t
                pts.append((u * u * x0 + 2 * u * t * ctrl[0] + t * t * end[0],
                            u * u * y0 + 2 * u * t * ctrl[1] + t * t * end[1]))
            here = end
    return pts


def svg_paths(scale: float = 1.0, dx: float = 0.0, dy: float = 0.0,
              mono: str | None = None) -> str:
    """The mark as <path> elements, one line each.

    `mono` collapses it to a single colour, for the places that want a
    silhouette -- a header that inherits currentColor, or a tile whose
    ground is already one of the mark's own two colours.
    """
    lines = []
    for path, rgb in shapes():
        if mono is not None and rgb == PAPER:
            continue                            # no hairlines in a silhouette
        fill = mono if mono is not None else "#%02x%02x%02x" % rgb
        lines.append('<path d="%s" fill="%s"/>'
                     % (_d(path, scale, dx, dy), fill))
    return "\n  ".join(lines)


def _d(path: list, scale: float, dx: float, dy: float) -> str:
    def p(pt):
        return "%s %s" % (_n(pt[0] * scale + dx), _n(pt[1] * scale + dy))
    out = []
    for seg in path:
        if seg[0] == "M":
            out.append("M" + p(seg[1]))
        elif seg[0] == "L":
            out.append("L" + p(seg[1]))
        elif seg[0] == "Q":
            out.append("Q" + p(seg[1]) + " " + p(seg[2]))
    return " ".join(out) + "Z"


def _n(v: float) -> str:
    """Trim the float so the committed SVG is stable and readable."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s or "0"
