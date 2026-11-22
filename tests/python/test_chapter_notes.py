#!/usr/bin/env python3
"""The notes written for chapter pages (docs/data/chapter_notes.json).

These are the site's own words about a chapter -- what happens in it, why it
matters, where its places are -- printed above the text so a page is more
than one more copy of a public-domain translation. What is held here is the
shape a later hand could break while extending the file: every key names a
real chapter page, every note is short, plain prose with no links, no two
notes lean on the same stock sentence, the dates are real, and the note is in
the HTML a crawler reads rather than added by a script.
"""

import datetime
import json
import os
import re
import sys
import tempfile
import unittest
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, os.pardir, "tools"))
import build_pages                                              # noqa: E402

DATA = os.path.join(HERE, os.pardir, os.pardir, "docs", "data")

# Places whose map data is known to be wrong are left out of the notes until
# the data is mended, rather than given a line that points at the wrong spot.
WRONG_ON_THE_MAP = {"philistia", "kir"}


def sentences(text):
    return [s for s in re.split(r'(?<=[.!?"\u201d])\s+(?=[A-Z"\u201c])', text) if s]


class ChapterNotes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(DATA, build_pages.NOTES_FILE), encoding="utf-8") as fh:
            cls.doc = json.load(fh)
        cls.notes = build_pages.load_notes(DATA)
        with open(os.path.join(DATA, "manifest.json"), encoding="utf-8") as fh:
            cls.manifest = json.load(fh)
        cls.slugs = {w["id"]: (w.get("slugs") or [])
                     for s in cls.manifest["sections"] for w in s["works"]}

    def test_the_file_says_how_to_extend_it(self):
        self.assertTrue(self.doc.get("about"))
        self.assertGreater(len(self.notes), 0)

    def test_every_key_is_a_real_chapter_page(self):
        for key in self.notes:
            work, _, slug = key.partition("/")
            self.assertIn(work, self.slugs, key)
            self.assertIn(slug, self.slugs[work], key)

    def test_each_note_is_short_plain_prose(self):
        for key, n in self.notes.items():
            intro = n.get("intro") or ""
            self.assertTrue(intro.strip(), key)
            self.assertLessEqual(len(intro), 900, key)
            self.assertTrue(2 <= len(sentences(intro)) <= 6,
                            "%s: %d sentences" % (key, len(sentences(intro))))
            blob = json.dumps(n, ensure_ascii=False)
            for bad in ("http", "www.", "<", "@", "#/read/"):
                self.assertNotIn(bad, blob, key)
            if "description" in n:
                self.assertLessEqual(len(n["description"]), 160, key)

    def test_no_stock_sentences(self):
        """Written chapter by chapter, not stamped from a template."""
        seen = Counter(s.strip() for n in self.notes.values()
                       for s in sentences(n["intro"]))
        repeated = [s for s, c in seen.items() if c > 1 and len(s) > 25]
        self.assertEqual(repeated, [])
        intros = [n["intro"] for n in self.notes.values()]
        self.assertEqual(len(intros), len(set(intros)))

    def test_places_have_a_line_each_and_skip_the_misplaced(self):
        for key, n in self.notes.items():
            for p in n.get("places") or []:
                self.assertTrue(p.get("name") and p.get("note"), key)
                self.assertNotIn(p["name"].lower(), WRONG_ON_THE_MAP, key)

    def test_dates_are_real_and_not_in_the_future(self):
        today = datetime.date.today()
        for key, n in self.notes.items():
            d = datetime.date.fromisoformat(n["updated"])
            self.assertLessEqual(d, today + datetime.timedelta(days=1), key)


class OnThePage(unittest.TestCase):
    """The note is in the static HTML, above the text, and feeds the meta
    description; a chapter without one is unchanged."""

    @classmethod
    def setUpClass(cls):
        build_pages.load_context(DATA)
        with open(os.path.join(DATA, "manifest.json"), encoding="utf-8") as fh:
            cls.manifest = json.load(fh)
        cls.out = tempfile.mkdtemp()

    def page(self, work_id, i):
        for s in self.manifest["sections"]:
            for meta in s["works"]:
                if meta["id"] == work_id:
                    with open(os.path.join(DATA, "works", work_id + ".json"),
                              encoding="utf-8") as fh:
                        work = json.load(fh)
                    chapters = work["chapters"]
                    slugs = build_pages.chapter_slugs(meta, chapters)
                    build_pages.chapter_page(self.manifest, s, meta, work,
                                             chapters, slugs, i, self.out)
                    path = os.path.join(self.out, "read", work_id, slugs[i], "index.html")
                    with open(path, encoding="utf-8") as fh:
                        return slugs[i], fh.read()
        self.fail("no work %s" % work_id)

    def test_a_noted_chapter_prints_its_note_above_the_text(self):
        notes = build_pages.CONTEXT["notes"]
        key = next(iter(notes))
        work, _, slug = key.partition("/")
        meta_slugs = [w["slugs"] for s in self.manifest["sections"]
                      for w in s["works"] if w["id"] == work][0]
        got_slug, html = self.page(work, meta_slugs.index(slug))
        self.assertEqual(got_slug, slug)
        intro = build_pages.e(" ".join(notes[key]["intro"].split()))
        self.assertIn(intro, html)
        self.assertLess(html.index('class="note-block chapter-intro"'),
                        html.index('<div class="reader">'))
        desc = re.search(r'<meta name="description" content="([^"]*)"', html).group(1)
        self.assertLessEqual(len(desc), 160 + 40)      # entities count extra
        self.assertFalse(desc.startswith("Read "), desc)

    def test_a_chapter_without_a_note_is_as_it_was(self):
        notes = build_pages.CONTEXT["notes"]
        slug, html = self.page("genesis", 0)
        self.assertNotIn("genesis/%s" % slug, notes)
        self.assertNotIn("chapter-intro", html)
        self.assertNotIn("More about this chapter", html)


if __name__ == "__main__":
    unittest.main()
