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
    def test_two_boards_and_three_leaves(self):
        """Fewer leaves stops being a fan; more is mud at sixteen pixels."""
        tones = [leaf["tone"] for leaf in logo.LEAVES]
        self.assertEqual(tones.count("navy"), 2)
        self.assertEqual(len(tones) - tones.count("navy"), 3)

    def test_every_leaf_is_drawn_on_both_sides(self):
        """A book opened flat is symmetrical, and the old mark drifted
        precisely because both halves were typed out separately.

        Rounded, because the mirror is arrived at by two different routes --
        once here and once in logo.py -- and the last bit of a float does not
        survive that. Six places is far finer than the drawing.
        """
        def key(path, rgb, flip=False):
            pts = []
            for seg in path:
                for x, y in seg[1:]:
                    pts.append((round(logo.BOX - x if flip else x, 6),
                                round(y, 6)))
            return (tuple(pts), rgb)

        drawn = {key(p, c) for p, c in logo.shapes()}
        for path, rgb in logo.shapes():
            self.assertIn(key(path, rgb, flip=True), drawn)

    def test_everything_runs_from_the_foot_of_the_spine(self):
        """The one thing that makes it a book rather than a pair of wings."""
        for path, _rgb in logo.shapes():
            self.assertEqual(path[0][0], "M")
            x, y = path[0][1]
            # The paper hairlines are the same paths blown up about that
            # point, so they start there too.
            self.assertAlmostEqual(x, logo.SPINE[0], places=6)
            self.assertAlmostEqual(y, logo.SPINE[1], places=6)

    def test_the_leaves_fan(self):
        """Each leaf stops short of the one outside it and peaks higher."""
        leaves = [f for f in logo.LEAVES if "peak" in f]
        outs = [f["out"] for f in leaves]
        peaks = [f["peak"][1] for f in leaves]
        self.assertEqual(outs, sorted(outs, reverse=True))
        self.assertEqual(peaks, sorted(peaks, reverse=True))

    def test_the_boards_sit_under_the_leaves(self):
        """The navy is the cover the pages lie on, not a swoosh beside it."""
        boards = [f for f in logo.LEAVES if "peak" not in f]
        leaves = [f for f in logo.LEAVES if "peak" in f]
        self.assertTrue(all(b["ytop"] > max(f["peak"][1] for f in leaves)
                            for b in boards))
        # And they reach further out, the way a board overhangs its text block.
        self.assertGreater(max(b["out"] for b in boards),
                           max(f["out"] for f in leaves))

    def test_everything_fits_the_box(self):
        for path, _rgb in logo.shapes():
            for x, y in logo.flatten(path):
                self.assertGreaterEqual(x, 0, (x, y))
                self.assertGreaterEqual(y, 0, (x, y))
                self.assertLessEqual(x, logo.BOX, (x, y))
                self.assertLessEqual(y, logo.BOX, (x, y))

    def test_the_colours_are_the_drawing_s_own(self):
        """Sampled from the artwork, not picked to look about right."""
        self.assertEqual(logo.NAVY, (0x0C, 0x2D, 0x5A))
        self.assertEqual(logo.GOLD, (0xD5, 0xAB, 0x6F))


class Committed(unittest.TestCase):
    """The files in docs/assets are what the builder emits, byte for byte."""

    def test_logo_svg(self):
        want = build_logo.MARK_SVG.format(paths=logo.svg_paths())
        self.assertEqual(read("logo.svg"), want)

    def test_favicon_svg(self):
        inset = 64 * build_logo.PAD
        want = build_logo.TILE_SVG.format(
            bg=build_logo.hexc(logo.PAPER),
            paths=logo.svg_paths(scale=64 * (1 - 2 * build_logo.PAD) / logo.BOX,
                                 dx=inset, dy=inset))
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

    def brand_paths(self):
        mark = self.html.split('class="brand-mark"', 1)[1].split("</svg>", 1)[0]
        return re.findall(r'<path d="([^"]*)"', mark)

    def test_inline_mark_matches_the_geometry(self):
        want = re.findall(r'<path d="([^"]*)"',
                          logo.svg_paths(mono="currentColor"))
        self.assertEqual(self.brand_paths(), want)

    def test_the_header_mark_is_a_silhouette(self):
        """It sits in a header that inverts with the theme, so it takes the
        text colour; navy on the dark ground would be invisible."""
        mark = self.html.split('class="brand-mark"', 1)[1].split("</svg>", 1)[0]
        self.assertIn('fill="currentColor"', mark)
        self.assertNotIn(build_logo.hexc(logo.NAVY), mark)

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
