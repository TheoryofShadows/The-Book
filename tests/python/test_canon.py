#!/usr/bin/env python3
"""The canon table, and the five works that are neither in it nor left out.

canon.json says which canon receives which book. The search reads it twice:
once forwards, to search one tradition's books, and once backwards, to search
the books no tradition holds. The second reading is subtraction -- everything
the volume prints, less everything any canon lists -- and subtraction is
where this can go quietly wrong.

Five works here are a chapter of a canonical book printed a second time
beside the excavated object or the early poem it belongs with: the Decalogue,
the Shema, the priestly blessing, the Song of the Sea, the Song of Deborah.
No canon lists them, because the whole book is elsewhere in the volume and
that is where its coverage is counted. Left to the subtraction they would
come out as books left out of every Bible, which is the opposite of true.

So build_canon.py names them, and refuses to build when a sixth appears that
is classed neither way. That refusal is the thing worth testing: the table
above it is a list somebody wrote down, and a list is only as good as the
gate that notices when the volume has moved past it.
"""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

import _tools                                              # noqa: F401

import build_canon

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "docs", "data")


def build(manifest):
    """Run the builder over a manifest, and give back its output and status."""
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh)
        was, build_canon.DATA = build_canon.DATA, tmp
        said = io.StringIO()
        try:
            with contextlib.redirect_stdout(said):
                code = build_canon.main()
        finally:
            build_canon.DATA = was
        out = os.path.join(tmp, "canon.json")
        got = None
        if os.path.exists(out):
            with open(out, encoding="utf-8") as fh:
                got = json.load(fh)
        return code, got, said.getvalue()


class Excerpts(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(DATA, "canon.json"), encoding="utf-8") as fh:
            self.canon = json.load(fh)
        with open(os.path.join(DATA, "manifest.json"), encoding="utf-8") as fh:
            self.manifest = json.load(fh)
        self.works = {w["id"]: w for s in self.manifest["sections"]
                      for w in s["works"]}

    def test_every_excerpt_is_a_work_that_exists(self):
        for wid in self.canon["excerpts"]:
            self.assertIn(wid, self.works, f"{wid} is not in the manifest")

    def test_an_excerpt_is_not_also_a_book_s_own_text(self):
        # Both at once would mean a canon's coverage counted the chapter and
        # the book it came out of as two separate things.
        listed = {w for b in self.canon["books"] for w in b["works"]}
        for wid in self.canon["excerpts"]:
            self.assertNotIn(wid, listed)

    def test_each_names_a_book_the_volume_really_carries(self):
        by_name = {b["name"]: b for b in self.canon["books"]}
        for wid, book in self.canon["excerpts"].items():
            self.assertIn(book, by_name, f"{wid} names {book}, which is not a book here")
            self.assertTrue(by_name[book]["present"],
                            f"{wid} reproduces {book}, which the volume does not carry")

    def test_the_titles_say_which_chapter_they_are(self):
        # The claim in the table is checkable against the work itself, and
        # this is what makes it checkable: each title names its book and the
        # chapter number, which is also what the gate below looks for.
        for wid, book in self.canon["excerpts"].items():
            self.assertIn(book.lower(), self.works[wid]["title"].lower(),
                          f"{wid} does not say it is part of {book}")


class TheGate(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(DATA, "manifest.json"), encoding="utf-8") as fh:
            self.manifest = json.load(fh)

    def test_the_volume_as_it_stands_builds(self):
        code, got, said = build(self.manifest)
        self.assertEqual(code, 0, said)
        self.assertTrue(got["excerpts"])

    def test_the_committed_file_is_what_the_builder_makes(self):
        # Nothing here is hand-edited. A canon.json that has drifted from the
        # script is a table nobody rebuilt and nobody can check.
        code, got, said = build(self.manifest)
        self.assertEqual(code, 0, said)
        with open(os.path.join(DATA, "canon.json"), encoding="utf-8") as fh:
            self.assertEqual(got, json.load(fh))

    def test_a_new_chapter_of_a_canonical_book_stops_the_build(self):
        # The failure this exists for: somebody adds Isaiah 53 to the
        # discoveries section, nobody classes it, and the search starts
        # offering the suffering servant as a book left out of every Bible.
        manifest = json.loads(json.dumps(self.manifest))
        manifest["sections"][-1]["works"].append({
            "id": "isaiah-53-the-suffering-servant",
            "title": "ISAIAH 53 (the suffering servant)",
            "note": [], "chapters": 1, "verses": 12, "words": 400,
            "versified": True, "source": "web", "positions": None,
        })
        code, _got, said = build(manifest)
        self.assertEqual(code, 1, said or "the build did not fail")
        self.assertIn("UNCLASSED", said)
        self.assertIn("isaiah-53-the-suffering-servant", said)

    def test_a_book_no_canon_holds_is_not_mistaken_for_one(self):
        # The other half of the gate: it must not fire on the works that
        # really are outside every canon, which is most of the library's
        # second half. The Epistle to the Romans is Ignatius's here, and
        # naming Romans is not naming a chapter of it.
        manifest = json.loads(json.dumps(self.manifest))
        manifest["sections"][-1]["works"].append({
            "id": "the-epistle-of-ignatius-to-the-corinthians",
            "title": "THE EPISTLE OF IGNATIUS TO THE CORINTHIANS",
            "note": [], "chapters": 2, "verses": 0, "words": 400,
            "versified": False, "source": "anf", "positions": None,
        })
        code, _got, said = build(manifest)
        self.assertEqual(code, 0, said)


if __name__ == "__main__":
    unittest.main()
