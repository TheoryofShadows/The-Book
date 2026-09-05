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

    def test_no_icon_claims_to_be_maskable(self):
        """The tile is drawn with Apple's padding, not Android's safe zone.

        A maskable icon must keep its content inside a circle 80% of the
        icon wide. These are inset by an eighth, so the corners of the mark
        sit outside that circle and a launcher applying a round mask would
        crop them. Claiming maskable would look fine here and be visibly
        wrong on a phone, which is the reason to state it rather than to
        leave the absence to chance.
        """
        for icon in manifest()["icons"]:
            self.assertNotIn("maskable", icon.get("purpose", "any"))


class TheColoursAgreeWithTheSite(unittest.TestCase):

    def test_theme_color_matches_the_page(self):
        stated = re.search(
            r'name="theme-color"\s+content="(#[0-9a-fA-F]{6})"', index())
        self.assertIsNotNone(stated, "docs/index.html states no theme-color")
        self.assertEqual(manifest()["theme_color"].lower(),
                         stated.group(1).lower())

    def test_background_color_is_the_paper_the_page_opens_on(self):
        """The splash screen is painted before any stylesheet runs.

        If it is not the page's own ground the app opens on a flash of the
        wrong colour. There is only one background_color and the site has a
        dark theme, so this is the light paper by choice: it matches the
        default a device reports when it has no preference.
        """
        with open(os.path.join(DOCS, "assets", "app.css"), encoding="utf-8") as fh:
            css = fh.read()
        paper = re.search(r"--paper:\s*(#[0-9a-fA-F]{6})", css)
        self.assertIsNotNone(paper, "app.css no longer defines --paper")
        self.assertEqual(manifest()["background_color"].lower(),
                         paper.group(1).lower())


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
