#!/usr/bin/env python3
"""The web manifest, against the files and the colours it names.

A manifest is a set of promises made to two operating systems about files
none of them fetch until somebody taps Install, which is the worst possible
time to discover the icon is not there or is not the size it said. Every
claim in it is checkable here, so it is checked here: the icons exist, they
really are the pixel dimensions declared, and the two colours agree with the
palette the rest of the site is held to.

The split between the manifest and the apple- tags is the thing most likely
to be undone by somebody tidying. Android installs from the manifest. iOS
reads almost none of it and installs from the meta tags instead -- the name
under the icon comes from apple-mobile-web-app-title, not from short_name,
and standalone comes from apple-mobile-web-app-capable, not from display.
Deleting either half loses a platform silently: nothing renders differently,
no test that only reads the manifest notices, and the site simply stops
being installable on one of the two phones anybody owns.
"""

import json
import os
import re
import struct
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(ROOT, "docs")

# The tags iOS needs, and the standardised spelling of the one Chrome reads.
INSTALL_TAGS = (
    "mobile-web-app-capable",
    "apple-mobile-web-app-capable",
    "apple-mobile-web-app-status-bar-style",
    "apple-mobile-web-app-title",
)


def manifest():
    with open(os.path.join(DOCS, "site.webmanifest"), encoding="utf-8") as fh:
        return json.load(fh)


def index():
    with open(os.path.join(DOCS, "index.html"), encoding="utf-8") as fh:
        return fh.read()


def png_size(path):
    """Width and height out of the PNG header, rather than off the filename.

    The filename is what a person typed and the header is what the file is.
    Those disagreeing is exactly the bug this file exists to catch, so it
    cannot be the filename that answers.
    """
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"{path} is not a PNG")
    return struct.unpack(">II", head[16:24])


class TheManifestIsValid(unittest.TestCase):

    def test_it_is_json(self):
        manifest()

    def test_it_names_the_site(self):
        m = manifest()
        self.assertTrue(m.get("name"))
        self.assertTrue(m.get("short_name"))
        # short_name is what fits under an icon. Long ones are truncated by
        # the launcher with no say from here.
        self.assertLessEqual(len(m["short_name"]), 12, m["short_name"])

    def test_it_opens_the_reader_rather_than_a_chapter(self):
        """start_url is resolved against the manifest, not the installing page.

        The manifest sits at the root and every generated chapter page links
        it, so a relative start_url means installing from Genesis 1 still
        opens the reader where it opens for everybody else.
        """
        m = manifest()
        self.assertEqual(m.get("start_url"), "./")
        self.assertEqual(m.get("scope"), "./")

    def test_it_asks_for_standalone(self):
        self.assertEqual(manifest().get("display"), "standalone")


class TheIconsAreReallyThere(unittest.TestCase):

    def test_every_icon_exists_and_is_the_size_it_claims(self):
        for icon in manifest()["icons"]:
            path = os.path.join(DOCS, icon["src"])
            self.assertTrue(os.path.exists(path),
                            f"{icon['src']} is in the manifest and not on disk")
            want = icon["sizes"]
            w, h = png_size(path)
            self.assertEqual(f"{w}x{h}", want,
                             f"{icon['src']} is {w}x{h}, manifest says {want}")

    def test_there_is_an_icon_android_will_install_from(self):
        """Chrome's install criteria name 192; without one there is no prompt.

        512 alone is not a substitute -- the criteria are written as sizes
        rather than as a minimum, which is why icon-192.png exists at all.
        """
        sizes = {i["sizes"] for i in manifest()["icons"]}
        self.assertIn("192x192", sizes, sorted(sizes))
        self.assertIn("512x512", sizes, sorted(sizes))

    def test_only_the_icon_drawn_for_it_claims_to_be_maskable(self):
        """The plain tiles are drawn with Apple's padding, not Android's
        safe zone.

        A maskable icon must keep its content inside a circle 80% of the
        icon wide. The plain tiles are inset by an eighth, so the corners of
        the mark sit near the edge of that circle and a launcher applying a
        round mask could crop them. Claiming maskable for those would look
        fine here and be visibly wrong on a phone. The one icon that does
        claim it is icon-maskable-512.png, drawn smaller for the purpose;
        test_logo.py checks its mark against the safe zone.
        """
        for icon in manifest()["icons"]:
            purpose = icon.get("purpose", "any")
            if "maskable" in purpose:
                self.assertIn("maskable", icon["src"])
                self.assertEqual(purpose, "maskable")
            else:
                self.assertNotIn("maskable", icon["src"])


def png_pixel(path, x, y):
    """One pixel of an 8-bit RGB or RGBA PNG, decoded by hand so the test
    needs nothing installed. Not a general decoder: no palette, no
    interlacing, which is all the icons are."""
    import zlib
    with open(path, "rb") as fh:
        data = fh.read()
    pos, idat, w, h, ctype = 8, b"", 0, 0, 0
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h, depth, ctype, _c, _f, inter = struct.unpack(">IIBBBBB", body)
            assert depth == 8 and ctype in (2, 6) and inter == 0, "unsupported PNG"
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    bpp = 3 if ctype == 2 else 4
    raw = zlib.decompress(idat)
    stride = w * bpp
    prev = bytearray(stride)
    for row in range(y + 1):
        base = row * (stride + 1)
        ft, line = raw[base], bytearray(raw[base + 1:base + 1 + stride])
        for i in range(stride):
            a_ = line[i - bpp] if i >= bpp else 0
            b_ = prev[i]
            c_ = prev[i - bpp] if i >= bpp else 0
            if ft == 1:
                line[i] = (line[i] + a_) & 255
            elif ft == 2:
                line[i] = (line[i] + b_) & 255
            elif ft == 3:
                line[i] = (line[i] + (a_ + b_) // 2) & 255
            elif ft == 4:
                pa, pb, pc = abs(b_ - c_), abs(a_ - c_), abs(a_ + b_ - 2 * c_)
                pr = a_ if pa <= pb and pa <= pc else (b_ if pb <= pc else c_)
                line[i] = (line[i] + pr) & 255
        prev = line
    return tuple(prev[x * bpp:x * bpp + 3])


def icon_edge():
    """The ground colour the icon tiles are drawn on, read off a corner."""
    return "#%02x%02x%02x" % png_pixel(
        os.path.join(DOCS, "assets", "icon-512.png"), 2, 2)


class TheColoursAgreeWithTheLogo(unittest.TestCase):
    """The installed app wears the brand navy, not the reading page's plum.

    theme_color paints the status bar of the installed app and the address
    bar; background_color is the splash behind the icon. The splash is the
    icon's own ground, so the square tile does not show as a tile.
    """

    def test_theme_color_is_the_logo_navy(self):
        import sys
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import logo
        want = "#%02x%02x%02x" % logo.NAVY
        self.assertEqual(manifest()["theme_color"].lower(), want)

    def test_the_page_light_theme_colour_matches_the_manifest(self):
        stated = re.search(
            r'name="theme-color"\s+content="(#[0-9a-fA-F]{6})"\s+'
            r'media="\(prefers-color-scheme: light\)"', index())
        self.assertIsNotNone(stated, "docs/index.html states no light theme-color")
        self.assertEqual(manifest()["theme_color"].lower(),
                         stated.group(1).lower())

    def test_the_page_has_a_dark_theme_colour_too(self):
        self.assertRegex(
            index(), r'name="theme-color"\s+content="#[0-9a-fA-F]{6}"\s+'
                     r'media="\(prefers-color-scheme: dark\)"')

    def test_the_generated_pages_say_the_same(self):
        with open(os.path.join(ROOT, "tools", "build_pages.py"), encoding="utf-8") as fh:
            source = fh.read()
        for scheme in ("light", "dark"):
            m = re.search(r'theme-color" content="(#[0-9a-fA-F]{6})" '
                          r'media="\(prefers-color-scheme: %s\)"' % scheme, source)
            self.assertIsNotNone(m, "build_pages.py has no %s theme-color" % scheme)
            h = re.search(r'name="theme-color"\s+content="(#[0-9a-fA-F]{6})"\s+'
                          r'media="\(prefers-color-scheme: %s\)"' % scheme, index())
            self.assertEqual(m.group(1).lower(), h.group(1).lower())

    def test_background_color_is_the_ground_the_icons_are_drawn_on(self):
        self.assertEqual(manifest()["background_color"].lower(), icon_edge())


class TheManifestIsAnApp(unittest.TestCase):

    def test_it_has_a_stable_identity_and_categories(self):
        m = manifest()
        self.assertEqual(m["id"], "./")
        self.assertEqual(m["categories"], ["books", "education"])

    def test_shortcuts_point_at_routes_inside_the_scope(self):
        shortcuts = manifest()["shortcuts"]
        self.assertEqual([s["url"] for s in shortcuts], ["./#/", "./#/timeline"])
        with open(os.path.join(DOCS, "assets", "app.js"), encoding="utf-8") as fh:
            js = fh.read()
        self.assertIn('href="#/timeline"', index())
        self.assertIn('"#/timeline"', js)
        for s in shortcuts:
            self.assertTrue(s["url"].startswith(manifest()["scope"]))


class BothPlatformsCanInstallIt(unittest.TestCase):

    def test_the_front_page_links_the_manifest(self):
        self.assertRegex(index(), r'<link rel="manifest" href="site\.webmanifest">')

    def test_the_front_page_carries_the_tags_ios_needs(self):
        html = index()
        for tag in INSTALL_TAGS:
            self.assertIn(f'name="{tag}"', html,
                          f"{tag} is gone, and with it one of the two platforms")

    def test_the_status_bar_is_not_translucent(self):
        """black-translucent draws the page under the clock.

        On this layout that puts the header behind the status bar. It is a
        one-word change with no visible warning, so it is written down.
        """
        style = re.search(
            r'name="apple-mobile-web-app-status-bar-style"\s+content="([^"]+)"',
            index())
        self.assertIsNotNone(style)
        self.assertNotEqual(style.group(1), "black-translucent")

    def test_the_generated_pages_link_it_too(self):
        """A phone from a search result lands on a chapter, not the front page.

        build_pages.py writes the link at each page's own depth, so this
        checks the generator rather than any one built file -- the built
        ones are gitignored and are not here to read on a clean checkout.
        """
        with open(os.path.join(ROOT, "tools", "build_pages.py"),
                  encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn('<link rel="manifest" href="%ssite.webmanifest">', source)
        for tag in INSTALL_TAGS:
            self.assertIn(f'name="{tag}"', source,
                          f"{tag} is on the front page and not on the "
                          f"2,709 pages most phones actually arrive at")


if __name__ == "__main__":
    unittest.main()
