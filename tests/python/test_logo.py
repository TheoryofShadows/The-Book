"""The mark, and the files drawn from it.

A logo has a way of drifting: the SVG in the page head gets nudged, the
tab icon does not, and a year later they are two different marks. These
hold the committed assets to what tools/build_logo.py produces from
tools/logo.py, and hold the copy inlined in docs/index.html to the same
geometry, so a nudge in one place fails here rather than shipping.

The SVGs are compared byte for byte. The PNG and JPEG are drawn from them by
a browser, which does not promise the same bytes across versions, so those
are held to what can be held: the file really is the size it claims, and
docs/assets/logo.build.json -- the hash of the SVG each was drawn from --
still matches the SVG this code emits now. Change the mark without
re-running tools/build_logo.py and that is the test that fails.
"""

import json
import math
import os
import re
import struct
import unittest

import _tools                                            # noqa: F401
import build_logo
import logo
import logo_type

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "..")
ASSETS = os.path.join(ROOT, "docs", "assets")


def read(name, mode="r"):
    kw = {"encoding": "utf-8"} if mode == "r" else {}
    with open(os.path.join(ASSETS, name), mode, **kw) as fh:
        return fh.read()


def png_size(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    return struct.unpack(">II", data[16:24])


def jpeg_size(data):
    assert data[:2] == b"\xff\xd8", "not a JPEG"
    i = 2
    while i < len(data):
        assert data[i] == 0xFF
        marker = data[i + 1]
        (length,) = struct.unpack(">H", data[i + 2:i + 4])
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + length
    raise AssertionError("no frame header")


class Geometry(unittest.TestCase):
    def test_two_boards_and_three_leaves(self):
        """Fewer leaves stops being a fan; more is mud at thirty pixels."""
        kinds = [leaf[1] for leaf in logo.LEAVES]
        self.assertEqual(kinds.count("navy"), 2)
        self.assertEqual(kinds.count("gold"), 3)

    def test_the_right_half_is_the_left_mirrored(self):
        """A book opened flat is symmetrical, and the geometry says so once:
        only the left half is written down."""
        for kind, path in logo.shapes():
            pass
        shapes = logo.shapes()
        self.assertEqual(len(shapes) % 2, 0)
        for (k1, left), (k2, right) in zip(shapes[0::2], shapes[1::2]):
            self.assertEqual(k1, k2)
            for a, b in zip(left, right):
                self.assertEqual(a[0], b[0])
                for pa, pb in zip(a[1:], b[1:]):
                    self.assertAlmostEqual(pa[0], -pb[0], places=9)
                    self.assertAlmostEqual(pa[1], pb[1], places=9)
        # And the drawing uses the same half twice rather than a second copy.
        self.assertIn('transform="scale(-1 1)"', logo.mark_body("k", logo.LIGHT))

    def test_everything_runs_into_the_foot_of_the_spine(self):
        """The one thing that makes it a book rather than a pair of wings."""
        for leaf in logo.LEAVES:
            path = logo.leaf_path(leaf)
            for end in (path[0][1], path[-1][-1]):
                self.assertLess(abs(end[0]), 16, (leaf[0], end))
                self.assertLess(abs(end[1] - 0), 8, (leaf[0], end))

    def test_the_leaves_fan(self):
        """Each gold leaf reaches further out than the one before it, and
        the first, innermost, is the tallest."""
        gold = [l for l in logo.LEAVES if l[1] == "gold"]
        reach = [abs(logo.leaf_path(l)[len(l[2])][1][0]) for l in gold]
        self.assertEqual(reach, sorted(reach))
        tops = [min(y for _x, y in logo.flatten(logo.leaf_path(l))) for l in gold]
        self.assertEqual(tops[0], min(tops))

    def test_the_boards_sit_under_the_leaves(self):
        """The navy is the cover the pages lie on, not a swoosh beside it."""
        def box(kind):
            pts = [p for l in logo.LEAVES if l[1] == kind
                   for p in logo.flatten(logo.leaf_path(l))]
            return (min(p[0] for p in pts), max(p[1] for p in pts),
                    min(p[1] for p in pts))
        nx, nbottom, ntop = box("navy")
        gx, gbottom, gtop = box("gold")
        self.assertLess(ntop, gbottom)              # they overlap in height
        self.assertGreater(ntop, gtop)              # but start below the leaves
        self.assertLess(nx, gx)                     # and overhang them

    def test_everything_fits_the_view(self):
        x0, y0, w, h = logo.VIEW
        for _kind, path in logo.shapes():
            for x, y in logo.flatten(path):
                self.assertTrue(x0 <= x <= x0 + w and y0 <= y <= y0 + h, (x, y))
        bx, by, bw, bh = logo.BOUNDS
        for _kind, path in logo.shapes():
            for x, y in logo.flatten(path):
                self.assertTrue(bx - 1 <= x <= bx + bw + 1, (x, y))
                self.assertTrue(by - 1 <= y <= by + bh + 1, (x, y))

    def test_the_colours_are_navy_and_gold(self):
        def rgb(h):
            return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
        for theme in logo.THEMES.values():
            for h in theme["gold"]:
                r, g, b = rgb(h)
                self.assertTrue(r > g > b, h)       # warm, going to brown
            for h in theme["navy"]:
                r, g, b = rgb(h)
                self.assertTrue(b > g > r, h)       # blue
        # The dark theme is lighter than the light one, which is its point.
        lum = lambda h: sum(rgb(h))
        self.assertGreater(lum(logo.DARK["navy"][2]), lum(logo.LIGHT["navy"][2]))
        self.assertEqual(logo.NAVY, rgb(logo.LIGHT["navy"][1]))
        self.assertEqual(logo.GOLD, rgb(logo.LIGHT["gold"][1]))

    def test_the_type_is_all_there(self):
        for key in ("THE", "BOOK", "THEBOOK", "TAG1", "SCRIPTURE", "HISTORY",
                    "TRUTH", "DOMAIN"):
            d, w = logo_type.TYPE[key]
            self.assertTrue(d.startswith("M"), key)
            self.assertGreater(w, 20, key)
        # The tagline is fitted to the width the rules above it are drawn to.
        self.assertAlmostEqual(logo_type.TYPE["TAG1"][1], 410.0, delta=1)


class Committed(unittest.TestCase):
    """The SVGs in docs/assets are what the builder emits, byte for byte."""

    def test_svgs(self):
        for name, want in build_logo.sources().items():
            self.assertEqual(read(name), want, name)

    def test_no_svg_reaches_outside_itself(self):
        """The CSP's img-src is 'self' and data:, and a file that fetched
        something would be one more thing to go missing."""
        for name in build_logo.sources():
            svg = read(name)
            stripped = svg.replace('xmlns="http://www.w3.org/2000/svg"', "")
            self.assertNotIn("http", stripped, name)
            self.assertNotIn("<image", svg, name)
            self.assertNotIn("@import", svg, name)

    def test_the_lockup_is_outlines_not_a_font_request(self):
        for name in ("lockup.svg", "lockup-dark.svg"):
            self.assertNotIn("<text", read(name), name)
            self.assertNotIn("font-family", read(name), name)

    def test_the_lockup_carries_two_terms_not_three(self):
        """See LOCKUP_TERMS in tools/build_logo.py. The site declines to
        claim truth and its signature does not claim it either."""
        self.assertEqual(build_logo.LOCKUP_TERMS, ("SCRIPTURE", "HISTORY"))
        self.assertNotIn(logo_type.TYPE["TRUTH"][0], read("lockup.svg"))
        self.assertNotIn(logo_type.TYPE["TRUTH"][0], read("lockup-dark.svg"))

    def test_the_tab_icon_is_small(self):
        """The offline copy inlines it as a data: URL in the page."""
        self.assertLess(len(read("favicon.svg")), 8000)
        self.assertNotIn("<filter", read("favicon.svg"))

    def test_raster_files_are_the_size_they_say(self):
        for size in build_logo.ICON_SIZES:
            self.assertEqual(png_size(read(f"icon-{size}.png", "rb")),
                             (size, size), size)
        self.assertEqual(png_size(read("icon-maskable-512.png", "rb")), (512, 512))
        card = read("og-card.jpg", "rb")
        self.assertEqual(jpeg_size(card), build_logo.CARD)
        self.assertLess(len(card), 300_000)         # a feed fetches it cold

    def test_raster_files_were_drawn_from_the_current_svgs(self):
        """The failure that matters: the mark changed and the PNGs did not."""
        recorded = json.loads(read("logo.build.json"))["drawn_from_sha256"]
        self.assertEqual(recorded, build_logo.build_record())
        for name in recorded:
            self.assertTrue(os.path.exists(os.path.join(ASSETS, name)), name)


class Maskable(unittest.TestCase):
    def test_the_mark_stays_inside_the_safe_zone(self):
        """A launcher promises only a circle 80% of the icon wide. The
        farthest corner of the mark, at the size it is drawn, has to be
        inside it."""
        x, y, w, h = logo.BOUNDS
        k = build_logo.MASKABLE_MARK / w            # icon widths per unit
        far = 0.0
        for _kind, path in logo.shapes():
            for px, py in logo.flatten(path):
                dx = (px - (x + w / 2)) * k
                dy = (py - (y + h / 2)) * k
                far = max(far, math.hypot(dx, dy))
        self.assertLess(far, 0.40, far)


class InThePage(unittest.TestCase):
    """docs/index.html carries the mark inline; it must be the same mark."""

    def setUp(self):
        with open(os.path.join(ROOT, "docs", "index.html"),
                  encoding="utf-8") as fh:
            self.html = fh.read()
        with open(os.path.join(ASSETS, "app.css"), encoding="utf-8") as fh:
            self.css = fh.read()

    def mark(self):
        return self.html.split('class="brand-mark"', 1)[1].split("</span>", 1)[0]

    def test_inline_mark_is_the_generated_one(self):
        self.assertIn(logo.header_svg(), self.mark())

    def test_the_header_mark_is_cheap_and_crisp(self):
        """No filters or clip paths: it is drawn at thirty-odd pixels on
        every page load."""
        m = self.mark()
        self.assertNotIn("<filter", m)
        self.assertNotIn("clip-path", m)
        self.assertLess(len(logo.header_svg()), 8000)

    def test_it_follows_the_theme(self):
        """Its stops are coloured from the stylesheet, in the light default
        and in both routes to dark, or navy would vanish on a dark ground."""
        stops = ["hmg0", "hmg1", "hmg2", "hmg3", "hmn0", "hmn1", "hmn2"]
        for cls in stops:
            self.assertIn(f'class="{cls}"', self.mark(), cls)
            self.assertIn(f".{cls}", self.css, cls)
            self.assertRegex(
                self.css, r'prefers-color-scheme: dark\)[^@]*?:root:not\(\[data-theme="light"\]\) \.'
                + cls + r' \{ stop-color', cls)
            self.assertIn(f':root[data-theme="dark"] .{cls} {{ stop-color', self.css, cls)

    def test_head_points_at_the_generated_files(self):
        head = self.html.split("</head>", 1)[0]
        self.assertIn('href="assets/favicon.svg"', head)
        self.assertIn('href="assets/icon-180.png"', head)
        self.assertIn("assets/icon-512.png", head)
        self.assertIn("assets/og-card.jpg", head)

    def test_no_emoji_favicon_left(self):
        """The placeholder it replaced, so it cannot quietly come back."""
        self.assertNotIn("\U0001F4D6", self.html)


if __name__ == "__main__":
    unittest.main()
