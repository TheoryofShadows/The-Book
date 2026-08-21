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


class WhatCountsAsAWork(unittest.TestCase):
    """The headline counts 166. Nine of them are not texts.

    Checking that the count matches manifest.totals.works proves the arithmetic
    and nothing else -- the number was never the doubtful part, the noun
    was. Two of the entries are editorial asides, four are notes on
    manuscript discoveries, and three are placeholders for material the
    volume cannot print. A reader entitled to the count is entitled to
    know what is in it.
    """

    def setUp(self):
        with open(os.path.join(ROOT, "docs", "data", "manifest.json"),
                  encoding="utf-8") as fh:
            self.manifest = json.load(fh)
        self.works = [w for s in self.manifest["sections"] for w in s["works"]]

    def test_the_split_between_text_and_apparatus(self):
        texts = [w for w in self.works if w.get("words")]
        self.assertEqual(len(self.works), 166)
        self.assertEqual(len(texts), 157)
        self.assertEqual(len(self.works) - len(texts), 9)

    def test_the_readme_says_how_many_carry_text(self):
        stated = re.search(r"Of the ([\d,]+) entries, \*\*([\d,]+) carry text\*\*",
                           readme())
        self.assertIsNotNone(
            stated, "README.md no longer states how many entries carry text")
        texts = sum(1 for w in self.works if w.get("words"))
        self.assertEqual(stated.group(1), f"{len(self.works):,}")
        self.assertEqual(stated.group(2), f"{texts:,}")

    def test_the_entries_without_text_are_the_ones_on_record(self):
        """Frozen, so a work cannot lose its text without saying so.

        A parse that silently emptied a book would otherwise just move it
        into the apparatus column and keep the totals looking reasonable.
        """
        self.assertEqual(
            sorted(w["id"] for w in self.works if not w.get("words")),
            ["also-often-dated-this-early",
             "ketef-hinnom-silver-scrolls-found-1979",
             "on-the-placement-of-the-torah",
             "philo-of-alexandria",
             "the-dead-sea-scrolls-as-biblical-manuscripts-found-1947-1956",
             "the-great-christian-codices",
             "the-major-dead-sea-scrolls-summaries",
             "the-nash-papyrus-acquired-1898-1903",
             "the-psalms-of-solomon"])


class WhatTheFrontMatterClaimsIsMissing(unittest.TestCase):
    """The volume's own list of what it does not contain.

    It said the Shepherd of Hermas Similitudes 1 and 10 were not captured
    by the parser. They were supplied from the 1870 Ante-Nicene Christian
    Library in "Close three Apostolic Fathers gaps from a second edition",
    and the sentence describing their absence outlived the absence by
    several commits -- the same way the headline counts outlived the parse
    repair that changed them.
    """

    def not_present(self):
        with open(os.path.join(ROOT, "docs", "data", "manifest.json"),
                  encoding="utf-8") as fh:
            intro = json.load(fh)["sections"][0]["intro"]
        note = [p for p in intro if p.startswith("NOT PRESENT")]
        self.assertEqual(len(note), 1, "no NOT PRESENT note in the front matter")
        return note[0]

    def test_it_does_not_claim_absent_text_the_volume_now_prints(self):
        note = self.not_present()
        self.assertNotIn("Similitudes 1 and 10", note)

    def test_and_the_similitudes_it_used_to_disclaim_really_are_there(self):
        for n, least in (("similitude-1", 400), ("similitude-10", 2500)):
            with open(os.path.join(ROOT, "docs", "data", "works", n + ".json"),
                      encoding="utf-8") as fh:
                work = json.load(fh)
            words = sum(len(" ".join(c.get("paras", [])).split())
                        for c in work["chapters"])
            self.assertGreater(words, least, f"{n} is empty again")

    def test_it_still_names_what_is_genuinely_absent(self):
        note = self.not_present()
        for missing in ("Dead Sea Scrolls", "Psalms of Solomon", "Philo",
                        "1 Clement", "Smyrnaeans"):
            self.assertIn(missing, note)


class TheAbsentBooks(unittest.TestCase):
    """Four books of the Ethiopian canon are missing, and each says why.

    There were five. The Ethiopic Didascalia was added from Platt's 1834
    printing; the other four have no English translation old enough to be
    public domain, and that is now recorded rather than left blank.

    The coverage table named them and stopped, which is a gap asserted
    without a citation -- the one move this volume says it does not make.
    A reason that cannot be checked is no better than no reason, so each
    carries a source too, and build_canon.py refuses to build without one.
    """

    def setUp(self):
        with open(os.path.join(ROOT, "docs", "data", "canon.json"),
                  encoding="utf-8") as fh:
            self.canon = json.load(fh)
        self.absent = [b for b in self.canon["books"] if not b["present"]]

    def test_the_absent_books_are_the_ones_on_record(self):
        self.assertEqual(
            sorted(b["name"] for b in self.absent),
            ["4 Baruch (Paraleipomena Jeremiou)",
             "Book of the Covenant (Mets'hafe Kidan)",
             "Ethiopic Clement (Qalementos)",
             "Sinodos"])

    def test_every_absence_carries_a_reason_and_a_source(self):
        for b in self.absent:
            self.assertTrue(b.get("absentWhy", "").strip(),
                            f"{b['name']} is absent with no reason")
            self.assertTrue(b.get("absentSource", "").strip(),
                            f"{b['name']} gives no source for its reason")


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
