#!/usr/bin/env python3
"""A bar drawn across a book that is not one composition.

The timeline gives every work one bar, and a bar is a claim: this object was
written between these two years. For most of the volume that is what the
position record says. For the Torah, the Psalms, Proverbs, Polycarp and the
rest of the works marked here, the same records say the opposite in so many
words -- "Composite", "A collection spanning centuries", "perhaps two letters
joined" -- and the drawing said nothing about it. One solid bar over Genesis
and one over Amos, whose bar is ten years, are the same shape.

The method page has always admitted this. The picture did not, and the picture
is what a visitor reads.

So the works are marked, and the mark is a quotation rather than a new claim:
the value of "composite" in a position record must appear verbatim inside that
record's own critical position, which already carries a citation. That is the
whole rule this file enforces, in both directions --

  * nothing may be marked composite on a sentence that does not say so, which
    is what would let a marking drift into an editorial opinion with no source
    behind it;
  * and a record whose own words are unambiguous about being layered may not
    go unmarked, which is how the next book added would quietly get a solid
    bar it has not earned.
"""

import os
import re
import unittest

import _tools                                              # noqa: F401

from positions import POSITIONS

ROOT = _tools.ROOT
APP_JS = os.path.join(ROOT, "docs", "assets", "app.js")

# Words that cannot mean anything but "this book is not one composition".
# Deliberately narrow: "later editing" and "around older material" say it too,
# and are marked, but they are phrases a record could use loosely, and a test
# that guesses is a test that has to be argued with. These cannot be read any
# other way, so a record containing one and carrying no mark is a mistake.
UNAMBIGUOUS = re.compile(
    r"\bComposite\b|\bA compilation of several\b|\bcollection spanning\b",
    re.IGNORECASE)


def sourced_sentence(record):
    """The critical position and its reasoning: the part of the record that
    carries a citation in critSource."""
    return (record.get("crit") or "") + " " + (record.get("critWhy") or "")


class EveryMarkQuotesItsOwnRecord(unittest.TestCase):
    def test_marked_works_exist_and_are_strings(self):
        for wid, record in POSITIONS.items():
            if "composite" not in record:
                continue
            self.assertIsInstance(record["composite"], str, wid)
            self.assertTrue(record["composite"].strip(),
                            "%s: an empty composite mark says nothing" % wid)

    def test_the_mark_is_a_quotation_not_a_new_claim(self):
        for wid, record in POSITIONS.items():
            phrase = record.get("composite")
            if not phrase:
                continue
            self.assertIn(
                phrase, sourced_sentence(record),
                "%s is marked composite on words that are not in its own "
                "critical position. The mark has to be a quotation from a "
                "sentence critSource already stands behind, or it is an "
                "unsourced claim wearing the same clothes as a sourced one."
                % wid)

    def test_an_unambiguous_record_is_not_left_unmarked(self):
        for wid, record in POSITIONS.items():
            if record.get("composite"):
                continue
            found = UNAMBIGUOUS.search(sourced_sentence(record))
            self.assertIsNone(
                found,
                "%s: the position says %r and the work is not marked "
                "composite, so the timeline will draw it as one solid bar"
                % (wid, found.group(0) if found else ""))

    def test_something_is_actually_marked(self):
        """A rule that matches nothing is a rule nobody will notice breaking."""
        marked = [w for w, r in POSITIONS.items() if r.get("composite")]
        self.assertGreaterEqual(len(marked), 10, marked)

    def test_first_isaiah_carries_the_apocalypse(self):
        """The volume asserted this in a thread aside long before it asserted
        it where a work's dates live, which is why the timeline could draw
        Isaiah 1-39 as eighth-century and the thread could send a reader back
        two eras to a chapter inside it."""
        record = POSITIONS["isaiah-1-39-first-isaiah"]
        self.assertTrue(record.get("composite"))
        self.assertIn("24-27", sourced_sentence(record))


class TheReaderDrawsTheMark(unittest.TestCase):
    """The data is only half of it: a mark nothing renders is a mark nobody
    sees. These are the three places the reader has to use it."""

    def setUp(self):
        with open(APP_JS, encoding="utf-8") as fh:
            self.src = fh.read()

    def test_the_row_carries_the_field(self):
        self.assertIn("w.positions && w.positions.composite", self.src)

    def test_the_bar_is_hatched(self):
        self.assertIn('" composite"', self.src)
        with open(os.path.join(ROOT, "docs", "assets", "app.css"),
                  encoding="utf-8") as fh:
            self.assertIn(".tl-bar.composite", fh.read())

    def test_the_count_is_stated_in_words(self):
        self.assertIn("bars are not one date", self.src)


if __name__ == "__main__":
    unittest.main()
