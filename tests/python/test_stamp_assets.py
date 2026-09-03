#!/usr/bin/env python3
"""The asset URLs carry their own content hash, and the pages agree.

Every deploy of this site shipped app.css and app.js under the same two
names. GitHub Pages serves them with Cache-Control max-age=600 and an
Expires ten hours out, so a reader who had been here before got the copy
their browser already held. The site was deployed, correct, and identical
to the repository -- and the person looking at it saw the version they saw
last time. Nothing errors, nothing logs, and the only symptom is somebody
saying they see no changes.

So the URL carries eight characters of the file's own SHA-256, and these
hold the three places that have to agree about it: the hand-written page,
the 2,709 generated ones, and the stamper itself.
"""

import hashlib
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import stamp_assets  # noqa: E402

DOCS = os.path.join(ROOT, "docs")


def sha8(name):
    with open(os.path.join(DOCS, "assets", name), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:8]


class TheAssetsAreStamped(unittest.TestCase):

    def setUp(self):
        with open(os.path.join(DOCS, "index.html"), encoding="utf-8") as fh:
            self.index = fh.read()

    def test_the_page_asks_for_the_stylesheet_it_actually_has(self):
        want = sha8("app.css")
        found = re.search(r'href="assets/app\.css\?v=([0-9a-f]+)"', self.index)
        self.assertIsNotNone(
            found, "docs/index.html no longer fetches a versioned stylesheet, "
                   "so every returning reader gets whichever one their browser "
                   "kept")
        self.assertEqual(found.group(1), want)

    def test_the_page_asks_for_the_script_it_actually_has(self):
        want = sha8("app.js")
        found = re.search(r'src="assets/app\.js\?v=([0-9a-f]+)"', self.index)
        self.assertIsNotNone(found, "docs/index.html no longer fetches a "
                                    "versioned script")
        self.assertEqual(found.group(1), want)

    def test_stamping_twice_does_not_double_the_query(self):
        """It runs on every build, over a file it has already stamped."""
        once = stamp_assets.stamp_html(
            '<link href="assets/app.css">', {"app.css": "aaaaaaaa"})
        twice = stamp_assets.stamp_html(once, {"app.css": "bbbbbbbb"})
        self.assertEqual(twice, '<link href="assets/app.css?v=bbbbbbbb">')
        self.assertEqual(twice.count("?v="), 1)

    def test_a_changed_asset_changes_the_url(self):
        """The whole point: same bytes, same URL; one byte different, new URL."""
        first = stamp_assets.stamp_html("assets/app.js", {"app.js": "11111111"})
        again = stamp_assets.stamp_html("assets/app.js", {"app.js": "11111111"})
        moved = stamp_assets.stamp_html("assets/app.js", {"app.js": "22222222"})
        self.assertEqual(first, again)
        self.assertNotEqual(first, moved)

    def test_the_generated_pages_agree_with_the_hand_written_one(self):
        """Skipped when the pages have not been built -- they are gitignored
        and rebuilt by the deploy -- but checked whenever they are there."""
        page = os.path.join(DOCS, "read", "genesis", "1", "index.html")
        if not os.path.exists(page):
            self.skipTest("docs/read is not built; run tools/build.sh")
        with open(page, encoding="utf-8") as fh:
            generated = fh.read()
        want = sha8("app.css")
        found = re.search(r'assets/app\.css\?v=([0-9a-f]+)', generated)
        self.assertIsNotNone(found, "a generated page fetches an unversioned "
                                    "stylesheet")
        self.assertEqual(found.group(1), want)

    def test_the_offline_copy_carries_no_reference_to_a_file_beside_it(self):
        """It inlines both assets, so a surviving <script src> would point at
        something that is not there. The tag now carries a query string, and
        the strip that removes it used to match a literal."""
        copy = os.path.join(DOCS, "the-book.html")
        if not os.path.exists(copy):
            self.skipTest("the offline copy is not built; run tools/build.sh")
        with open(copy, encoding="utf-8") as fh:
            head = fh.read(400000)
        self.assertNotIn('src="assets/app.js', head)
        self.assertNotIn('href="assets/app.css', head)


if __name__ == "__main__":
    unittest.main()
