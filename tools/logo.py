#!/usr/bin/env python3
"""The mark, defined once, as geometry rather than as a drawing.

The logo says the two things the site is: a book, and an argument about
when its parts were written. So it is a bound spine with four leaves
running off it, and the leaves are the date bars the rest of the volume
draws -- unequal, and each starting at its own point on the scale. At a
glance it is a codex seen from its fore-edge; at a second glance it is
the library on one axis, which is the same thing this arrangement claims.

Everything downstream -- the SVG in the page head, the tile in a browser
tab, the PNG an iPhone puts on a home screen -- is generated from the
numbers below, so the mark cannot drift between them.

Coordinates are in a 24 x 24 box, the size the header draws it at.
"""

from __future__ import annotations

# The bound edge. It overhangs the leaves at head and tail, the way a
# board overhangs a text block, which is what keeps the mark reading as a
# book rather than as a bar chart.
SPINE = (3.4, 3.2, 2.8, 17.6)

# The leaves, as (x, y, width, height). The heights are equal and nothing
# else is: each one starts later than the one above it and runs for its
# own length, which is what a date bar does and what a stack of flush,
# equal lines -- an align-left icon -- would not say. Read down, the four
# are a library in composition order.
LEAVES = [
    (8.0, 4.3, 8.2, 2.7),
    (9.8, 8.2, 10.6, 2.7),
    (11.6, 12.1, 5.8, 2.7),
    (13.2, 16.0, 7.2, 2.7),
]

BOX = 24.0

# Iron-gall ink oxidises violet-black and Tyrian purple is the dye of the
# coast these texts come from; both are already the site's palette, and
# the mark takes the accent and the paper from it rather than inventing a
# third colour.
ACCENT = (0x6B, 0x2D, 0x5B)
PAPER = (0xF2, 0xEE, 0xE5)


def rects() -> list[tuple[float, float, float, float]]:
    """Spine first, then the leaves, in drawing order."""
    return [SPINE] + LEAVES


def radius(h: float) -> float:
    """Every bar is a stadium: fully rounded on its short axis."""
    return h / 2.0


def svg_paths(scale: float = 1.0, dx: float = 0.0, dy: float = 0.0,
              fill: str = "currentColor") -> str:
    """The mark as <rect> elements, one line each."""
    out = []
    for x, y, w, h in rects():
        out.append(
            '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"/>'
            % (_n(x * scale + dx), _n(y * scale + dy), _n(w * scale),
               _n(h * scale), _n(radius(min(w, h)) * scale), fill))
    return "\n  ".join(out)


def _n(v: float) -> str:
    """Trim the float so the committed SVG is stable and readable."""
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s or "0"
