#!/usr/bin/env python3
"""Recovering Platt's English out of a facing-page scan.

The Ethiopic Didascalia is the one book of the five missing from the
Ethiopian canon that had a public-domain English translation to be found.
It is also the only text in this volume that is recovered rather than
audited: no independent chapter or verse counts exist for it, so the checks
that hold the biblical books to the World English Bible have nothing to
compare it against.

That makes these tests the only thing standing between the reader and a
silently mangled text, so they check the failures that would actually
matter rather than that the file parses.
"""

import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_didascalia as bd  # noqa: E402

SCAN = os.path.join(ROOT, "source", "extra", bd.SCAN)
WORK = os.path.join(ROOT, "docs", "data", "works", bd.WORK_ID + ".json")


def scan_pages():
    with open(SCAN, encoding="utf-8", errors="replace") as fh:
        return bd.pages(fh.read())


class SeparatingEnglishFromNoise(unittest.TestCase):
    """The Ge'ez was scanned by an engine that had no Ge'ez."""

    def test_a_line_of_platts_english_is_kept(self):
        self.assertTrue(bd.english(
            "receive  again  those  who  have  transgressed,  into  the  true "
            "religion,  that  they  may"))

    def test_a_line_of_scanned_geez_is_not(self):
        self.assertFalse(bd.english(
            "gnA»4^  :  nTnoo  •-  ^KA-  :  A^fl'h  ::  (D\">kO«n  :  C?».ln"))

    def test_a_running_head_is_too_short_to_pass(self):
        self.assertFalse(bd.english("NOTES."))

    def test_hyphenation_across_the_column_is_closed_up(self):
        self.assertIn("discipline", bd.prose(["to  enforce  disci-", "pline"]))


class NoEnglishIsLost(unittest.TestCase):
    """The check the whole import rests on.

    Twenty-four page numbers did not survive the scan, which looks like two
    dozen missing pages and is not. The number is printed at the foot of its
    page, so when one fails the text above it is gathered under the next
    mark instead: nothing is dropped, the pages either side simply run
    together. Two things prove it, and both are here because reading it the
    other way round would silently lose a quarter of the book.
    """

    @classmethod
    def setUpClass(cls):
        cls.pages = scan_pages()
        cls.numbers = sorted(cls.pages)

    def test_the_page_sequence_runs_from_the_first_page_to_the_last(self):
        self.assertEqual(self.numbers[0], 2)
        self.assertGreaterEqual(self.numbers[-1], 130)

    def test_no_page_bucket_is_empty(self):
        empty = [n for n in self.numbers if not self.pages[n]]
        self.assertEqual(empty, [], "a page recovered no English at all")

    def test_a_page_after_a_missing_number_carries_two_pages_of_text(self):
        """If the text were lost rather than absorbed, these would match.

        The direction matters and is easy to get backwards. The number is
        set at the *foot* of its page, so text accumulates upward into the
        next mark: when a number fails, its page joins the one that follows
        it, not the one before. Measured on the committed scan, a page whose
        predecessor did not scan holds 432 words against a baseline of 216,
        and its neighbour on the other side holds an ordinary 232.
        """
        import statistics
        words = lambda n: len(bd.WORD.findall(bd.prose(self.pages[n])))
        missing = {n for n in range(self.numbers[0], self.numbers[-1] + 1)
                   if n not in self.pages}
        self.assertTrue(missing, "no page numbers failed; rewrite this test")
        ordinary = statistics.median(
            [words(n) for n in self.numbers
             if n - 1 not in missing and n + 1 not in missing])
        doubled = statistics.median(
            [words(n) for n in self.numbers if n - 1 in missing])
        self.assertGreater(doubled, ordinary * 1.5,
                           "a page whose predecessor did not scan should hold "
                           "roughly two pages of text; it does not, which "
                           "means the missing pages really are missing")

    def test_the_apostles_charge_that_opens_the_work_is_present(self):
        """Page one carries no number, so a forward-reading extractor drops
        it. That is how the opening of the whole book went missing once."""
        with open(WORK, encoding="utf-8") as fh:
            work = json.load(fh)
        opening = work["chapters"][0]["paras"][0]
        self.assertTrue(opening.startswith("We the Twelve Apostles"), opening[:80])


class TheBuiltWork(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(WORK, encoding="utf-8") as fh:
            cls.work = json.load(fh)
        with open(os.path.join(ROOT, "docs", "data", "manifest.json"),
                  encoding="utf-8") as fh:
            cls.manifest = json.load(fh)

    def test_it_is_marked_as_recovered_rather_than_audited(self):
        """The weaker standard is the point: it must be labelled, not hidden."""
        self.assertIs(self.work["verified"], False)
        entry = next(w for s in self.manifest["sections"] for w in s["works"]
                     if w["id"] == bd.WORK_ID)
        self.assertIs(entry["verified"], False)

    def test_it_says_in_words_that_nothing_checked_it(self):
        note = " ".join(self.work["note"])
        self.assertIn("not audited", note)
        self.assertIn("Platt", note)

    def test_it_names_the_heading_that_could_not_be_divided(self):
        """One of Platt's sections opens on a page whose number did not
        scan, so it has no division of its own. Saying so beats dropping
        a heading without a word."""
        note = " ".join(self.work["note"])
        self.assertIn("Concerning Orphans", note)

    def test_the_sections_are_platts_own(self):
        raws = [c["raw"] for c in self.work["chapters"]]
        self.assertIn("Of Bishops, Priests, and Deacons", raws)
        self.assertGreaterEqual(len(self.work["chapters"]), 18)

    def test_no_scanned_geez_reached_the_text(self):
        body = " ".join(p for c in self.work["chapters"] for p in c["paras"])
        letters = sum(c.isalpha() or c.isspace() or c in ".,;:!?'\"()[]—-"
                      for c in body)
        self.assertGreater(letters / len(body), 0.97,
                           "scanned Ge'ez has leaked into the translation")

    def test_it_carries_a_dated_position_like_every_other_work(self):
        from positions import POSITIONS
        rec = POSITIONS[bd.WORK_ID]
        for field in ("trad", "tradWhy", "tradSource",
                      "crit", "critWhy", "critSource", "gap"):
            self.assertTrue(str(rec.get(field, "")).strip(), field)

    def test_the_canon_now_counts_it_as_present(self):
        with open(os.path.join(ROOT, "docs", "data", "canon.json"),
                  encoding="utf-8") as fh:
            canon = json.load(fh)
        book = next(b for b in canon["books"] if b["name"] == "Ethiopic Didascalia")
        self.assertTrue(book["present"])
        self.assertEqual(book["works"], [bd.WORK_ID])


class TheWordsTheScanBroke(unittest.TestCase):
    """A table of words, not a table of letters.

    The scan confused the ligature fi with fii, the pair li with h, and w
    with vd, vn or vv. It would be easy to undo that with three substitution
    rules and ruin every ordinary word containing an h. Each repair is
    written out instead, and logged where a reader can count them.
    """

    @classmethod
    def setUpClass(cls):
        with open(WORK, encoding="utf-8") as fh:
            work = json.load(fh)
        cls.body = " ".join(p for c in work["chapters"] for p in c["paras"])
        with open(os.path.join(ROOT, "docs", "data",
                               "didascalia-repairs.json"), encoding="utf-8") as fh:
            cls.log = json.load(fh)

    def test_no_broken_word_is_left_in_the_text(self):
        # The caret belongs here: "I^ord Jesus Christ" was on the live page,
        # and the tokeniser that was meant to repair it did not treat ^ as
        # part of a word, so the entry in the table never fired.
        bad = re.compile(
            r"(fii|\b[Hh][kfb]|vv|vd|vm|\^|[a-z]U[a-z]|iiljbr|oiir|yoixng|eveiy|aiad)")
        found = sorted({t for t in re.findall(r"[A-Za-z']+", self.body)
                        if bad.search(t)})
        self.assertEqual(found, [], "the scan's damage is back in the text")

    def test_the_ordinary_words_were_not_repaired_along_with_them(self):
        """The check that a letter-level rule would fail.

        "his", "the", "like" and "life" all contain the sequences the
        confusions produce. If a repair ever turns into a pattern, these go
        first and nothing else would notice.
        """
        for word in ("his", "the", "with", "shall", "life", "like"):
            self.assertIn(" " + word, self.body.lower(),
                          f"ordinary word {word!r} has been mangled")

    def test_every_repair_is_written_down(self):
        self.assertGreater(len(self.log["repairs"]), 20)
        for r in self.log["repairs"]:
            self.assertTrue(r["scanned"] and r["printed"] and r["times"] >= 1)
            self.assertNotEqual(r["scanned"], r["printed"])

    def test_the_log_names_the_scan_it_repaired(self):
        self.assertIn(bd.SCAN, self.log["source"])

    def test_the_section_heading_broken_across_two_words_is_whole(self):
        """"lawful for" scanned as one ruined token in Platt's eleventh
        section heading, which is why the repairs handle phrases too."""
        self.assertIn("not lawful for Christians to enter", self.body)


class TheSectionsAreCutOnPlattsHeadings(unittest.TestCase):
    """Cut on his headings, not on the page each section opens on.

    The first version divided by page number, which is only accurate to the
    page: a section beginning halfway down one opened with the tail of the
    section before it. "Of Widows" began "runner. But if thou be not
    slothful" -- a page of sloth before the first widow -- and that went out
    to the live site.
    """

    @classmethod
    def setUpClass(cls):
        with open(WORK, encoding="utf-8") as fh:
            cls.work = json.load(fh)

    def test_every_numbered_section_opens_on_its_own_heading(self):
        """The defect this replaced, stated as a rule."""
        for c in self.work["chapters"]:
            if not c.get("numeral"):
                continue          # the unnumbered preamble
            opening = c["paras"][0][:90]
            self.assertTrue(opening.startswith(c["numeral"] + "."),
                            f"section {c['n']} opens {opening!r}")

    def test_the_preamble_opens_the_work(self):
        first = self.work["chapters"][0]
        self.assertIsNone(first.get("numeral"))
        self.assertTrue(first["paras"][0].startswith("We the Twelve Apostles"))

    def test_the_numerals_run_forward(self):
        seen = [c["numeral"] for c in self.work["chapters"] if c.get("numeral")]
        order = list(bd.TITLES)
        self.assertEqual(seen, sorted(seen, key=order.index))

    def test_each_heading_phrase_occurs_exactly_once(self):
        """An ambiguous phrase cuts in the wrong place.

        "Of Widows" was tried and dropped for this reason: the only match
        the scan left is running text about the observance of widows, and
        cutting there put a boundary mid-sentence.
        """
        body = " ".join(p for c in self.work["chapters"] for p in c["paras"])
        for numeral, phrase in bd.HEADINGS:
            found = len(re.findall(re.escape(phrase), body, re.I))
            self.assertEqual(found, 1, f"{numeral}: {phrase!r} occurs {found}x")

    def test_the_headings_that_did_not_survive_are_named(self):
        note = " ".join(self.work["note"])
        for numeral in ("XII", "XV", "XVII"):
            self.assertIn(numeral, note)


class NoGeezReachedTheEnglish(unittest.TestCase):
    """One line of scanned Ge'ez got through and shipped.

    It cleared both of the original tests by a hair -- five of its fragments
    looked like words, and it came to 0.802 letters against a threshold of
    0.80 -- and dropped a run of noise into the middle of a sentence about
    bloody assemblies. The colon is the Ge'ez separator and the tell.
    """

    def test_a_geez_line_that_once_passed_is_now_refused(self):
        self.assertFalse(bd.english(
            "fl^  :  Yian  :  Viof-I'  :  \"S^A  :  lni>  :  AiffV  :  AOA  "
            ":  I^flf  :  HHaA-T  ::  COrS^oxfi"))

    def test_english_with_one_colon_is_still_kept(self):
        self.assertTrue(bd.english(
            "For thus saith the prophet: Woe unto them that join house to house"))

    def test_no_colon_run_survives_in_the_built_text(self):
        with open(WORK, encoding="utf-8") as fh:
            work = json.load(fh)
        body = " ".join(p for c in work["chapters"] for p in c["paras"])
        self.assertEqual(re.findall(r"\S+\s*:\s*\S+\s*:\s*\S+\s*:", body), [])


class TheWholeTextSurvivesTheCut(unittest.TestCase):
    """The guard that three failed attempts at this needed and did not have.

    Cutting the body into sections is pure partition: every word recovered
    from the scan lands in exactly one section. Getting it wrong is silent
    -- one attempt lost 1,400 words to an off-by-one on the section index,
    another duplicated 19,000 by matching a title in several places -- and
    the work still built, still rendered, and still read plausibly.
    """

    def test_the_sections_hold_every_word_the_scan_gave_and_no_more(self):
        with open(WORK, encoding="utf-8") as fh:
            work = json.load(fh)
        with open(SCAN, encoding="utf-8", errors="replace") as fh:
            page = bd.pages(fh.read())
        raw = bd.WORD.findall(
            " ".join(bd.prose(page[n]) for n in sorted(page) if page[n]))
        built = bd.WORD.findall(
            " ".join(p for c in work["chapters"] for p in c["paras"]))
        self.assertEqual(len(built), len(raw),
                         "the cut lost or duplicated text")


class TheExtractionIsReproducible(unittest.TestCase):

    def test_building_it_twice_gives_the_same_text(self):
        """The scan is committed, so the build must be a function of it."""
        a = scan_pages()
        b = scan_pages()
        self.assertEqual({k: bd.prose(v) for k, v in a.items()},
                         {k: bd.prose(v) for k, v in b.items()})

    def test_the_committed_text_matches_the_committed_scan(self):
        with open(WORK, encoding="utf-8") as fh:
            work = json.load(fh)
        built = sum(len(bd.WORD.findall(" ".join(c["paras"])))
                    for c in work["chapters"])
        page = scan_pages()
        raw = sum(len(bd.WORD.findall(bd.prose(v))) for v in page.values())
        # The built text is the scan minus whatever falls outside Platt's
        # sections; it can be smaller, never larger.
        self.assertLessEqual(built, raw)
        self.assertGreater(built, raw * 0.9, "most of the scan did not reach "
                                             "the built work")


if __name__ == "__main__":
    unittest.main()
