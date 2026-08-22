"""The mark, and the four files drawn from it.

A logo has a way of drifting: the SVG in the page head gets nudged, the
tab icon does not, and a year later they are two different marks. These
hold the committed assets to what tools/build_logo.py produces from
tools/logo.py, and hold the copy inlined in docs/index.html to the same
geometry, so a nudge in one place fails here rather than shipping.
"""

import os
import re
import unittest

import _tools                                            # noqa: F401
import build_logo
import logo

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "..")
ASSETS = os.path.join(ROOT, "docs", "assets")


def read(name, mode="r"):
    kw = {"encoding": "utf-8"} if mode == "r" else {}
    with open(os.path.join(ASSETS, name), mode, **kw) as fh:
        return fh.read()


class Geometry(unittest.TestCase):
    def test_five_bars(self):
        """A spine and four leaves. Fewer stops being a book."""
        self.assertEqual(len(logo.rects()), 5)

    def test_leaves_start_later_going_down(self):
        """The one thing the mark asserts: later texts start later."""
        starts = [x for x, _y, _w, _h in logo.LEAVES]
        self.assertEqual(starts, sorted(starts))
        self.assertEqual(len(set(starts)), len(starts))

    def test_leaves_are_unequal(self):
        """Equal lengths would be an align-left icon and mean nothing."""
        widths = [w for _x, _y, w, _h in logo.LEAVES]
        self.assertEqual(len(set(widths)), len(widths))

    def test_everything_fits_the_box(self):
        for x, y, w, h in logo.rects():
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + w, logo.BOX)
            self.assertLessEqual(y + h, logo.BOX)


class Committed(unittest.TestCase):
    """The files in docs/assets are what the builder emits, byte for byte."""

    def test_logo_svg(self):
        want = build_logo.MARK_SVG.format(paths=logo.svg_paths())
        self.assertEqual(read("logo.svg"), want)

    def test_favicon_svg(self):
        inset = 64 * build_logo.PAD
        want = build_logo.TILE_SVG.format(
            bg=build_logo.hexc(logo.ACCENT),
            paths=logo.svg_paths(scale=64 * (1 - 2 * build_logo.PAD) / logo.BOX,
                                 dx=inset, dy=inset,
                                 fill=build_logo.hexc(logo.PAPER)))
        self.assertEqual(read("favicon.svg"), want)

    def test_pngs_are_reproducible(self):
        """Deterministic output, or a rebuild shows up as a diff every time."""
        for size in (180, 512):
            self.assertEqual(read(f"icon-{size}.png", "rb"),
                             build_logo.png(size), size)


class InThePage(unittest.TestCase):
    """docs/index.html carries the mark inline; it must be the same mark."""

    def setUp(self):
        with open(os.path.join(ROOT, "docs", "index.html"),
                  encoding="utf-8") as fh:
            self.html = fh.read()

    def brand_rects(self):
        mark = self.html.split('class="brand-mark"', 1)[1].split("</svg>", 1)[0]
        out = []
        for tag in re.findall(r"<rect[^>]*>", mark):
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', tag))
            out.append((float(attrs["x"]), float(attrs["y"]),
                        float(attrs["width"]), float(attrs["height"])))
        return out

    def test_inline_mark_matches_the_geometry(self):
        self.assertEqual(self.brand_rects(), [tuple(r) for r in logo.rects()])

    def test_head_points_at_the_generated_files(self):
        head = self.html.split("</head>", 1)[0]
        self.assertIn('href="assets/favicon.svg"', head)
        self.assertIn('href="assets/icon-180.png"', head)
        self.assertIn("assets/icon-512.png", head)

    def test_no_emoji_favicon_left(self):
        """The placeholder it replaced, so it cannot quietly come back."""
        self.assertNotIn("\U0001F4D6", self.html)


if __name__ == "__main__":
    unittest.main()
