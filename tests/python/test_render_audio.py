#!/usr/bin/env python3
"""The name the renderer writes, against the name the reader asks for.

These are two halves of one contract and they were written in different
numbers. A chapter has a printed number -- chapter["n"], the numeral at its
head -- and it has a position in work["chapters"]. The reader addresses
chapters by position: that is what the route #/read/<work>/<i> carries and
what ctx.chapter hands to the fetch. render_audio.py named its output files
by the printed number.

For 2,486 of the 2,537 chapters in this volume those are different numbers,
so a rendered Genesis 1 would have been written to genesis/1 and asked for at
genesis/0, and 98% of the library would have answered 404. The defect was
invisible for as long as it was, because nothing had ever been uploaded for a
request to miss against -- and because check_audio.py's own sample chapter is
written in the reader's numbering, the one check that would have caught it
would have failed on a correct render and passed on no render at all.

So this holds the two halves together. Not by keeping a second copy of the
rule, which is the thing that went wrong: it reads the reader's numbering out
of docs/assets/app.js and the renderer's out of render_audio.py, and asserts
they are the same number.
"""

import json
import os
import re
import unittest

import _tools  # noqa: F401

import render_audio

ROOT = _tools.ROOT
APP = os.path.join(ROOT, "docs", "assets", "app.js")
WORKS = os.path.join(ROOT, "docs", "data", "works")


def app_js():
    with open(APP, encoding="utf-8") as fh:
        return fh.read()


def works():
    """Every work file, as (id, parsed) pairs."""
    for name in sorted(os.listdir(WORKS)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(WORKS, name), encoding="utf-8") as fh:
            yield name[:-5], json.load(fh)


class TheStemIsTheReadersIndex(unittest.TestCase):
    """What render_audio.py writes."""

    def test_it_is_the_position_not_the_printed_number(self):
        self.assertEqual(render_audio.chapter_stem("genesis", 0), "genesis/0")
        self.assertEqual(render_audio.chapter_stem("amos", 2), "amos/2")

    def test_it_counts_from_zero(self):
        """The reader's first chapter is 0. A renderer that counted from one
        would be off by one everywhere, which is the subtler half of the bug
        this file exists for."""
        self.assertEqual(render_audio.chapter_stem("jubilees", 0), "jubilees/0")

    def test_the_loop_does_not_reach_for_the_printed_number(self):
        """The rule is a function so there is one of it. If the chapter loop
        starts naming files from chapter["n"] again, this is what says so."""
        with open(os.path.join(_tools.TOOLS, "render_audio.py"),
                  encoding="utf-8") as fh:
            src = fh.read()
        loop = src.split("for idx, chapter in enumerate(", 1)
        self.assertEqual(len(loop), 2,
                         "render_audio.py no longer enumerates its chapters; "
                         "if the loop moved, point this at it rather than "
                         "deleting the check")
        body = loop[1][:400]
        self.assertIn("chapter_stem(work_id, idx)", body)
        self.assertNotIn('chapter["n"]', body)


class TheReaderAsksByIndex(unittest.TestCase):
    """The other half, read out of the reader rather than assumed."""

    def setUp(self):
        self.src = app_js()

    def test_a_chapter_is_identified_to_the_narrator_by_its_index(self):
        """attachListening is handed the chapter's position, and that is what
        every audio URL is then built from. If this becomes chapter["n"] or a
        label, the renderer's naming has to move with it."""
        self.assertRegex(
            self.src, r"attachListening\(\{[^}]*\bchapter:\s*idx\b",
            "the reader no longer identifies a chapter to the narrator by "
            "its index; render_audio.chapter_stem() must follow it")

    def test_the_audio_url_is_built_from_that_index(self):
        """Loosely, because the URL's shape is allowed to change -- what is
        not allowed is for it to stop being keyed on ctx.chapter."""
        self.assertRegex(
            self.src, r"\bctx\.chapter\b",
            "nothing in the reader builds an audio path from ctx.chapter any "
            "more; if the audio moved to a different addressing scheme, this "
            "test and chapter_stem() both need to move with it")


class TheTwoNumbersReallyDoDiffer(unittest.TestCase):
    """Proof that the tests above are not vacuous.

    If chapter["n"] happened to equal the index everywhere, every assertion
    here would pass against the broken code too. It does not: it differs
    almost everywhere, which is why the bug was worth a file of its own.
    """

    def setUp(self):
        self.rows = [(wid, i, ch.get("n"))
                     for wid, work in works()
                     for i, ch in enumerate(work.get("chapters", []) or [])]

    def test_the_volume_still_has_the_chapters_this_is_about(self):
        self.assertEqual(len(self.rows), 2537)

    def test_the_printed_number_disagrees_with_the_index_almost_everywhere(self):
        differ = [r for r in self.rows if r[1] != r[2]]
        self.assertGreater(
            len(differ), 2400,
            "the printed chapter number and the reader's index have come into "
            "agreement across the volume, which would make the naming bug "
            "this file guards unreproducible -- check why before relaxing it")

    def test_genesis_is_the_worked_example(self):
        """check_audio.py samples genesis/0 by default. Under the printed
        numbering there is no such chapter, which is the whole story in one
        line."""
        gen = [r for r in self.rows if r[0] == "genesis"]
        self.assertTrue(gen, "genesis has no chapters")
        self.assertEqual(gen[0][1], 0)
        self.assertEqual(gen[0][2], 1)
        self.assertEqual(render_audio.chapter_stem("genesis", gen[0][1]),
                         "genesis/0")


if __name__ == "__main__":
    unittest.main()
