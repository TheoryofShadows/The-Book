#!/usr/bin/env python3
"""The counts the README states, against the data it is describing.

The audit is a gate and docs/data cannot drift from source/, so the numbers
in the built files are checked. The sentences *about* those numbers are not,
and that is a real gap rather than a pedantic one: the six parse defects
repaired in "Make the audit a real gate" grew the library by three chapters
and fifty-four verses, and the front page of this repository went on
advertising the old figures. The data was right, the gate was working, and
the first line a reader saw was wrong.

A number in prose is an editorial claim, and this volume's argument is that
editorial claims carry citations. These are the citations.

The map's own README claim -- 1,209 of 1,232 places inside the frame -- is
checked in test_basemap.py instead, where the frame constant it depends on
lives.
"""

import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def readme():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        return fh.read()


def totals():
    with open(os.path.join(ROOT, "docs", "data", "manifest.json"),
              encoding="utf-8") as fh:
        return json.load(fh)["totals"]


class TheHeadline(unittest.TestCase):
    """The one line every reader sees before anything else."""

    def setUp(self):
        self.claim = re.search(
            r"\*\*([\d,]+) works · ([\d,]+) chapters · ([\d,]+) numbered "
            r"verses · ([\d.]+) million words\*\*", readme())
        self.assertIsNotNone(
            self.claim,
            "the headline this test exists to check is no longer in README.md "
            "in the form it can read; rewrite the test or restore the line")
        self.totals = totals()

    def test_the_number_of_works(self):
        self.assertEqual(self.claim.group(1), f"{self.totals['works']:,}")

    def test_the_number_of_chapters(self):
        """+3 when three folded Ignatius chapters were unfolded."""
        self.assertEqual(self.claim.group(2), f"{self.totals['chapters']:,}")

    def test_the_number_of_verses(self):
        """+54 when the dropped chapter-opening verses came back."""
        self.assertEqual(self.claim.group(3), f"{self.totals['verses']:,}")

    def test_the_number_of_words(self):
        """Stated to two decimal places, so it is checked to two.

        This is the one figure in the line that is rounded, and rounding is
        the reason it survived the last corpus change while its neighbours
        did not -- 1,128,001 and 1,130,336 are both "1.13 million". Checking
        it to the precision it is written at is the most the sentence can be
        held to.
        """
        stated = float(self.claim.group(4))
        self.assertEqual(stated, round(self.totals["words"] / 1_000_000, 2))


class TheGazetteer(unittest.TestCase):

    def test_the_number_of_curated_references(self):
        """"7,394 references" -- the count the map's honesty rests on.

        The point of the sentence is that the pins come from a list somebody
        checked rather than from a pattern run over the text, so the size of
        that list is load-bearing. It is read from the source column rather
        than from anything built, because the source is what the claim is
        about.
        """
        import sys
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import build_places

        rows = build_places.read_rows(
            os.path.join(ROOT, "source", "places", "merged.txt"))
        counted = sum(
            len([v for v in (r.get("Verses") or "").split(",") if v.strip()])
            for r in rows)

        stated = re.search(r"([\d,]+) references", readme())
        self.assertIsNotNone(
            stated, "the reference count is no longer stated in README.md")
        self.assertEqual(stated.group(1), f"{counted:,}")


if __name__ == "__main__":
    unittest.main()
