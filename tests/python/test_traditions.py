#!/usr/bin/env python3
"""The tradition table, which makes claims about somebody's religion.

Everything else this volume builds is derived from the texts. This one file
is editorial: thirty-odd sentences saying which books a church reads. That is
a claim about a living tradition, and the failure mode is not a broken build
but a page telling a Baptist their Bible is something it is not.

So the gates are here rather than in the reader, and they are the ones that
can actually be checked mechanically:

  - a canon key that canon.json does not have would send the reader to a
    scope that silently searches the whole library under a church's name;
  - a note without a source is an unfalsifiable claim about a religion;
  - two traditions answering to one word makes one of them unreachable, and
    which one is an accident of list order;
  - a tradition marked as an approximation must say so in its note, because
    the row's own lead sentence is the thing being qualified.

What cannot be checked here is whether a sentence is true. That is what the
source field is for, and why the builder refuses a note without one.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "tools"))

import _tools                                              # noqa: F401,E402

import build_traditions                                    # noqa: E402
import traditions                                          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "docs", "data")


def build(table, canons=("tanakh", "protestant", "catholic", "orthodox",
                         "ethiopian")):
    """Run the builder over a table, and give back its status and output."""
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "canon.json"), "w", encoding="utf-8") as fh:
            json.dump({"canons": list(canons)}, fh)
        was_out = build_traditions.OUT
        was_table = build_traditions.TRADITIONS
        build_traditions.OUT = tmp
        build_traditions.TRADITIONS = table
        said, cried = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(said), \
                 contextlib.redirect_stderr(cried):
                code = build_traditions.main()
        finally:
            build_traditions.OUT = was_out
            build_traditions.TRADITIONS = was_table
        out = os.path.join(tmp, "traditions.json")
        got = None
        if os.path.exists(out):
            with open(out, encoding="utf-8") as fh:
                got = json.load(fh)
        return code, got, cried.getvalue()


def one(**kw):
    """A minimal valid entry, with whatever the test is about overridden."""
    entry = {"id": "x", "name": "X", "family": "Judaism",
             "canon": "tanakh", "also": [], "note": "", "source": ""}
    entry.update(kw)
    return entry


class TheShippedTable(unittest.TestCase):
    """The real file, as it will go out."""

    def setUp(self):
        with open(os.path.join(DATA, "traditions.json"), encoding="utf-8") as fh:
            self.built = json.load(fh)
        with open(os.path.join(DATA, "canon.json"), encoding="utf-8") as fh:
            self.canons = set(json.load(fh)["canons"])

    def test_every_canon_named_exists(self):
        """The one that would silently mislead rather than break."""
        for t in self.built["traditions"]:
            if t["canon"] is not None:
                self.assertIn(t["canon"], self.canons,
                              f"{t['id']} names a canon canon.json lacks")

    def test_every_note_carries_a_source(self):
        for t in self.built["traditions"]:
            if t["note"]:
                self.assertTrue(t["source"],
                                f"{t['id']} claims something with no source")

    def test_no_two_traditions_answer_to_one_word(self):
        seen = {}
        for t in self.built["traditions"]:
            for word in [t["name"].lower()] + list(t["also"]):
                key = " ".join(word.lower().split())
                self.assertNotIn(key, seen,
                                 f"{t['id']} and {seen.get(key)} both answer "
                                 f"to {key!r}")
                seen[key] = t["id"]

    def test_an_approximation_says_so(self):
        for t in self.built["traditions"]:
            if t["approx"]:
                self.assertTrue(t["canon"], f"{t['id']} approximates nothing")
                self.assertTrue(t["note"],
                                f"{t['id']} approximates in silence")

    def test_the_ones_with_no_canon_explain_themselves(self):
        """A blank canon is a position, not a gap, and has to read as one."""
        unplaced = [t for t in self.built["traditions"] if not t["canon"]]
        self.assertTrue(unplaced, "the table has stopped saying no to anything")
        for t in unplaced:
            self.assertTrue(t["note"],
                            f"{t['id']} has no canon and no explanation")
            self.assertTrue(t["source"], f"{t['id']} explains with no source")

    def test_every_family_is_one_the_file_declares(self):
        for t in self.built["traditions"]:
            self.assertIn(t["family"], self.built["families"])

    def test_the_shared_canon_is_the_common_case(self):
        """The premise of the design: most of these names share a canon.

        If this ever stopped being true the answer panel's sentence -- "as do
        15 other traditions listed here" -- would be describing a table that
        no longer looks like that, and a filter would have become the better
        design after all.
        """
        counts = {}
        for t in self.built["traditions"]:
            if t["canon"] and not t["approx"]:
                counts[t["canon"]] = counts.get(t["canon"], 0) + 1
        biggest = max(counts.values())
        self.assertGreater(biggest, 5,
                           "no canon is shared by many traditions any more")


class TheGates(unittest.TestCase):
    """That the builder refuses what it says it refuses."""

    def test_a_good_table_builds(self):
        code, got, _ = build([one()])
        self.assertEqual(code, 0)
        self.assertEqual(len(got["traditions"]), 1)

    def test_an_unknown_canon_is_refused(self):
        code, got, cried = build([one(canon="wycliffe")])
        self.assertEqual(code, 1)
        self.assertIsNone(got)
        self.assertIn("wycliffe", cried)

    def test_no_canon_at_all_is_allowed(self):
        """Islam, the Samaritans and the Church of the East are not gaps."""
        code, got, _ = build([one(canon=None, note="n", source="s")])
        self.assertEqual(code, 0)
        self.assertIsNone(got["traditions"][0]["canon"])

    def test_a_note_without_a_source_is_refused(self):
        code, _, cried = build([one(note="They read only Mark.")])
        self.assertEqual(code, 1)
        self.assertIn("source", cried)

    def test_a_shared_word_is_refused(self):
        code, _, cried = build([one(id="a", name="A", also=["same"]),
                                one(id="b", name="B", also=["same"])])
        self.assertEqual(code, 1)
        self.assertIn("same", cried)

    def test_an_unknown_family_is_refused(self):
        code, _, cried = build([one(family="Zoroastrianism")])
        self.assertEqual(code, 1)
        self.assertIn("FAMILIES", cried)

    def test_an_approximation_of_nothing_is_refused(self):
        code, _, cried = build([one(canon=None, approx=True,
                                    note="n", source="s")])
        self.assertEqual(code, 1)
        self.assertIn("approximate", cried)

    def test_a_silent_approximation_is_refused(self):
        code, _, cried = build([one(approx=True)])
        self.assertEqual(code, 1)
        self.assertIn("approximate", cried)

    def test_a_duplicate_id_is_refused(self):
        code, _, cried = build([one(id="a", name="A"), one(id="a", name="B")])
        self.assertEqual(code, 1)
        self.assertIn("duplicate", cried)


class TheSourceModule(unittest.TestCase):
    """The editorial file itself, before it is built."""

    def test_the_families_are_used(self):
        used = {t["family"] for t in traditions.TRADITIONS}
        for family in traditions.FAMILIES:
            self.assertIn(family, used,
                          f"{family!r} is declared and never used")


if __name__ == "__main__":
    unittest.main()
