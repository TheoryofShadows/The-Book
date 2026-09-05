#!/usr/bin/env python3
"""The address a reader is handed for a verse.

"Copy link to this verse" used to return the reader's own route --
https://thebookandme.com/#/read/amos/4/v13 -- which is the one kind of URL in
this site that a crawler cannot ask for, that nothing unfurling a link can
preview, and that counts chapters from zero, so the link to Amos 5 said 4. All
the while tools/build_pages.py was writing a real page for that verse at
/read/amos/5/, with the text in the HTML, a canonical tag, an id on every
verse and an entry in the sitemap. The site built the citable thing and then
handed out the other one.

Two rules hold that fix together.

The addresses are written once. tools/build_slugs.py puts them in the manifest
and both halves read them from there, so the file the reader names and the
file the builder writes cannot drift apart. Recomputing them in the reader
would have been a second copy of a rule with a nasty edge in it -- Jubilees
opens with a prologue numbered 0 -- and no way to notice a disagreement.

And the published address is written once. docs/assets/app.js needs it because
the offline single-file build lives at a file:// path that means nothing to
anybody else, so a link copied from it has to point at the site instead. That
is a second copy of the site's own address, and this checks it against the
canonical the page already declares.
"""

import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_JS = os.path.join(ROOT, "docs", "assets", "app.js")
INDEX = os.path.join(ROOT, "docs", "index.html")
BUILD_PAGES = os.path.join(ROOT, "tools", "build_pages.py")
MANIFEST = os.path.join(ROOT, "docs", "data", "manifest.json")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class OneAddressForTheSite(unittest.TestCase):
    def setUp(self):
        self.app = read(APP_JS)

    def canonical(self):
        m = re.search(r'<link rel="canonical" href="([^"]+)"', read(INDEX))
        self.assertIsNotNone(m, "docs/index.html declares no canonical")
        return m.group(1)

    def test_the_reader_knows_where_it_is_published(self):
        m = re.search(r'var SITE = "([^"]+)"', self.app)
        self.assertIsNotNone(
            m, "app.js has no SITE; the offline build needs it to hand out a "
               "link somebody else can open")
        self.assertEqual(m.group(1), self.canonical())

    def test_the_page_builder_agrees(self):
        m = re.search(r'^BASE = "([^"]+)"', read(BUILD_PAGES), re.MULTILINE)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).rstrip("/") + "/", self.canonical())


class TheLinkPointsAtAPage(unittest.TestCase):
    def setUp(self):
        self.app = read(APP_JS)
        self.permalink = self.app[self.app.index("function permalink(ref)"):]
        self.permalink = self.permalink[:self.permalink.index("\n  }")]

    def test_it_names_the_built_page(self):
        self.assertIn('"read/" + ref.work + "/" + slug + "/"', self.permalink)

    def test_the_verse_is_a_fragment_on_that_page(self):
        """/read/amos/5/#v13 -- the id build_pages.py puts on every verse."""
        self.assertIn('"#v" + ref.v', self.permalink)

    def test_the_address_comes_from_the_manifest(self):
        self.assertIn("ctx.work.slugs", self.permalink)

    def test_a_route_is_still_there_as_the_fallback(self):
        """Before the manifest has loaded there is no address to look up, and
        the reader's own route is a working link, which is better than a
        broken one. It has to stay the fallback rather than become the answer
        again, so the last thing the function returns is the page."""
        self.assertIn("#/read/", self.permalink,
                      "there is no fallback for a verse whose work the "
                      "manifest does not name")
        last = self.permalink[self.permalink.rindex("return "):]
        self.assertIn('"read/" + ref.work', last)
        self.assertNotIn("#/read/", last,
                         "the route is the value that falls out of the end of "
                         "permalink(), so it is the answer rather than the "
                         "fallback")


class EveryChapterHasOne(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(MANIFEST, encoding="utf-8") as fh:
            cls.manifest = json.load(fh)
        cls.works = [w for s in cls.manifest["sections"] for w in s["works"]]

    def test_every_work_carries_its_addresses(self):
        for w in self.works:
            self.assertIn("slugs", w,
                          "%s has no chapter addresses; run "
                          "tools/build_slugs.py" % w["id"])

    def test_one_address_per_chapter(self):
        for w in self.works:
            self.assertEqual(
                len(w["slugs"]), w["chapters"],
                "%s: %d addresses for %d chapters -- the reader indexes this "
                "list by chapter, so a short list is a link to the wrong "
                "chapter" % (w["id"], len(w["slugs"]), w["chapters"]))

    def test_no_two_chapters_share_an_address(self):
        for w in self.works:
            self.assertEqual(len(set(w["slugs"])), len(w["slugs"]),
                             "%s: two chapters at one address" % w["id"])

    def test_they_are_url_safe(self):
        safe = re.compile(r"^[a-z0-9][a-z0-9-]*$")
        for w in self.works:
            for slug in w["slugs"]:
                self.assertRegex(slug, safe, "%s: %r" % (w["id"], slug))

    def test_the_printed_number_is_used_where_there_is_one(self):
        """The whole point of the second numbering: Isaiah 40 has to land in
        the second Isaiah rather than at its first chapter."""
        with open(os.path.join(ROOT, "docs", "data", "works",
                               "isaiah-40-55-second-isaiah.json"),
                  encoding="utf-8") as fh:
            work = json.load(fh)
        entry = next(w for w in self.works
                     if w["id"] == "isaiah-40-55-second-isaiah")
        self.assertEqual(entry["slugs"][0], "40")
        self.assertEqual(work["chapters"][0]["n"], 40)

    def test_a_prologue_numbered_zero_keeps_its_own_address(self):
        """Jubilees opens with one, and `n if n > 0 else i + 1` would file it
        at chapter 1's address, where chapter 1 then overwrites it."""
        entry = next((w for w in self.works if w["id"] == "jubilees"), None)
        if entry is None:
            self.skipTest("no jubilees in this build")
        self.assertEqual(len(set(entry["slugs"])), len(entry["slugs"]))


if __name__ == "__main__":
    unittest.main()
