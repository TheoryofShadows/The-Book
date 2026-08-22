"""The four Ethiopian canon books recovered from scans, and how.

Three of these texts came out of nineteenth- and early twentieth-century
scans, and none of them can be audited the way the biblical books are:
there are no independent chapter and verse counts for the Ethiopic
Sinodos to check a reading against. So what is checkable is checked
here instead, and it is not nothing.

The load-bearing claim is that no English was lost. A recovery that
drops the furniture off a page can as easily drop a line of the text
with it, and the failure is invisible -- the prose still reads, it is
just missing a sentence. Every word the scan gives up is therefore
accounted for: it is in the work, or it is a repair this build made and
recorded, or it is part of a head the build says in its own source that
it cuts. Nothing else is allowed.
"""

import collections
import json
import os
import re
import unittest

import _tools                                            # noqa: F401
import build_ethiopian as ethiopian
import scans

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "docs", "data")
RAW = os.path.join(ROOT, "source", "extra")

TOKEN = re.compile(r"[A-Za-z][A-Za-z'-]*")

# Which vendored scan each work is built from, and the head the build
# cuts off the front of it -- Issaverdens's printed title, which becomes
# the work's title, and James's own introduction, which is not text.
SCANS = {
    "the-sinodos": ("sinodos-horner-1904.txt", None),
    "the-apostolic-canons": ("apostolic-canons-schodde-1885.txt",
                             ethiopian.CANONS_OPEN),
    "the-testament-of-our-lord": (
        "testament-of-our-lord-cooper-maclean-1902.txt",
        ethiopian.TESTAMENT_OPEN),
    "the-apocalypse-of-peter": ("ethiopic-clement-james-1924.txt",
                                ethiopian.CLEMENT_OPEN),
    "the-rest-of-the-words-of-baruch": ("4-baruch-issaverdens-1901.txt",
                                        ethiopian.BARUCH_OPENS),
    "the-book-of-the-covenant": ("book-of-the-covenant-james-1924.txt",
                                 ethiopian.COVENANT_OPENS),
}

# The Apocalypse of Peter is the one work cut at both ends: James prints
# his own study of the book after it as well as before it.
TAILS = {"the-apocalypse-of-peter": ethiopian.CLEMENT_END}

# Words a build drops because they are the division marker itself. Cooper
# heads each chapter "CHAPTER 27"; the number becomes the label and the
# word goes with it. Nothing else may go.
MARKERS = {"the-testament-of-our-lord": {"CHAPTER"}}


def tokens(text):
    return collections.Counter(TOKEN.findall(text))


class TheVendoredScans(unittest.TestCase):
    """The files under source/extra, before anything is built from them."""

    def test_each_one_says_where_it_came_from(self):
        for name, _ in SCANS.values():
            with open(os.path.join(RAW, name), encoding="utf-8") as fh:
                head = fh.read().split("-" * 78, 1)[0]
            self.assertIn("Source:", head, name)
            self.assertIn("archive.org/details/", head, name)
            self.assertIn("Public domain", head, name)

    def test_the_page_markers_are_the_scan_s_own(self):
        """A line here can be put beside the leaf it came from, or the
        claim that it can is worthless."""
        for name, _ in SCANS.values():
            paragraphs, pages = scans.read_recovered(os.path.join(RAW, name))
            self.assertGreater(len(pages), 10, name)
            self.assertEqual(pages, sorted(pages), name)
            self.assertEqual(len(pages), len(set(pages)), name)
            self.assertGreater(len(paragraphs), 20, name)


class JoiningLines(unittest.TestCase):
    """A word broken by a line break, put back together."""

    def test_a_break_the_compositor_made_closes_up(self):
        got = scans.prose([["he com-", "manded us to go"], ["commanded"]])
        self.assertEqual(got[0], "he commanded us to go")

    def test_a_hyphen_the_translator_meant_is_kept(self):
        got = scans.prose([["thou shalt not be a star-", "gazer, nor"],
                           ["a star-gazer"]])
        self.assertEqual(got[0], "thou shalt not be a star-gazer, nor")

    def test_a_break_it_has_never_seen_either_way_closes_up(self):
        got = scans.prose([["the ordina-", "tion of a Bishop"]])
        self.assertEqual(got[0], "the ordination of a Bishop")

    def test_it_says_what_it_decided(self):
        log = []
        scans.prose([["he com-", "manded us"], ["a star-", "gazer"],
                     ["star-gazer commanded"]], log)
        self.assertIn(("commanded", "closed"), log)
        self.assertIn(("star-gazer", "kept"), log)


class ReadingAMangledNumeral(unittest.TestCase):
    """The scanner's readings of the numbers that cut these texts."""

    def test_the_shapes_the_scanner_makes_of_digits(self):
        for printed, want in (("I.", 1), ("9*", 9), ("ID.", 10), ("II.", 11),
                              ("1 2.", 12), ("34,", 34), ("6a", 60),
                              ("6i.", 61), ("40.", 40)):
            self.assertEqual(ethiopian.numeral(printed), want, printed)

    def test_one_bad_character_is_allowed_and_two_are_not(self):
        self.assertTrue(ethiopian.resembles("88", 38))
        self.assertFalse(ethiopian.resembles("88", 33))
        self.assertFalse(ethiopian.resembles("8", 38))

    def test_a_footnote_mark_is_not_a_division(self):
        """The thing the sequence exists to refuse."""
        self.assertFalse(ethiopian.resembles("1", 12))
        self.assertFalse(ethiopian.resembles("2", 18))


class MendingAToken(unittest.TestCase):
    """What may be repaired, and what must be left standing."""

    WORDS = {"they", "city", "figs", "tight", "fight", "verity", "eagle"}
    THIN_Y = [("v", "y")]
    CROSSBAR = [("t", "f")]

    def test_a_word_the_volume_knows_is_never_touched(self):
        self.assertIsNone(ethiopian.mend("verity", self.WORDS, self.CROSSBAR))

    def test_a_thin_y_read_as_a_v_is_mended(self):
        self.assertEqual(ethiopian.mend("thev", self.WORDS, self.THIN_Y),
                         "they")
        self.assertEqual(ethiopian.mend("citv", self.WORDS, self.THIN_Y),
                         "city")

    def test_two_candidates_are_left_alone(self):
        """"tight" and "fight" are both words; the printed one is
        "fight", and a machine that guesses gets it wrong half the
        time."""
        self.assertIsNone(ethiopian.mend("tight", self.WORDS, self.CROSSBAR))

    def test_a_repair_outside_the_scanner_s_habits_is_not_made(self):
        self.assertIsNone(ethiopian.mend("thev", self.WORDS, self.CROSSBAR))


class NothingIsLost(unittest.TestCase):
    """Every word the scan gives up is in the work, repaired, or cut."""

    @classmethod
    def setUpClass(cls):
        ethiopian.RAW = RAW
        cls.words = ethiopian.vocabulary(
            os.path.join(ROOT, "source", "THE_BOOK_COMPLETE.txt"))

    def test_every_word_is_accounted_for(self):
        for spec in ethiopian.WORKS:
            name, opens = SCANS[spec["id"]]
            paragraphs, _pages = scans.read_recovered(os.path.join(RAW, name))
            source = "\n\n".join(scans.prose(paragraphs))

            work, report = ethiopian.build(spec, self.words)
            built = tokens(" ".join(p for c in work["chapters"]
                                    for p in c["paras"]))

            cut = tokens(source[:source.index(opens)] if opens else "")
            tail = TAILS.get(spec["id"])
            if tail:
                cut += tokens(source[source.index(tail):])
            mended = collections.Counter()
            for (was, _now), n in report["repairs"].items():
                mended[was] += n

            unexplained = tokens(source) - built - cut - mended
            for marker in MARKERS.get(spec["id"], ()):
                unexplained.pop(marker, None)
            self.assertEqual(sum(unexplained.values()), 0,
                             f"{spec['id']} dropped {dict(unexplained)}")


class TheDivisionsAreThePrintedOnes(unittest.TestCase):

    def work(self, work_id):
        with open(os.path.join(DATA, "works", work_id + ".json"),
                  encoding="utf-8") as fh:
            return json.load(fh)

    def test_the_canons_run_in_schodde_s_roman_numbering(self):
        got = self.work("the-apostolic-canons")
        numerals = [c["numeral"] for c in got["chapters"] if c["numeral"]]
        self.assertEqual(numerals, sorted(numerals))
        self.assertEqual(numerals[0], 1)
        self.assertEqual(numerals[-1], 57)
        # The two the scan lost outright, which the work says it lost.
        self.assertEqual(set(range(1, 58)) - set(numerals), {30, 42})
        self.assertTrue(any("XXX, XLII" in n for n in got["note"]))

    def test_the_testament_keeps_cooper_s_two_books(self):
        got = self.work("the-testament-of-our-lord")
        labels = [c["label"] for c in got["chapters"]]
        self.assertTrue(any(l.startswith("I. ") for l in labels))
        self.assertTrue(any(l.startswith("II. ") for l in labels))
        firsts = [i for i, l in enumerate(labels) if l.endswith("opening")]
        self.assertEqual(len(firsts), 2, "each book keeps its own opening")

    def test_the_apocalypse_stops_where_james_stopped(self):
        got = self.work("the-apocalypse-of-peter")
        self.assertEqual(len(got["chapters"]), 1)
        text = " ".join(got["chapters"][0]["paras"])
        self.assertIn("book of life", text[-400:])
        self.assertNotIn("great deal more of the Ethiopic", text)

    def test_the_sinodos_has_horner_s_statutes_and_his_prayers(self):
        got = self.work("the-sinodos")
        numerals = [c["numeral"] for c in got["chapters"] if c["numeral"]]
        self.assertEqual(numerals, ethiopian.STATUTES)
        # The opening, the statutes, and the thirteen prayers he prints on
        # from the last of them.
        self.assertEqual(len(got["chapters"]), 1 + len(ethiopian.STATUTES) + 13)

    def test_horner_numbers_two_statutes_forty_and_both_are_kept(self):
        got = self.work("the-sinodos")
        forties = [c for c in got["chapters"] if c["numeral"] == 40]
        self.assertEqual(len(forties), 2)
        self.assertIn("second so numbered", forties[1]["raw"])
        self.assertNotEqual(forties[0]["paras"], forties[1]["paras"])

    def test_the_covenant_carries_james_s_fifty_one_sections_in_order(self):
        got = self.work("the-book-of-the-covenant")
        self.assertEqual([c["n"] for c in got["chapters"]],
                         list(range(1, 52)))

    def test_baruch_is_undivided_because_its_printing_is(self):
        got = self.work("the-rest-of-the-words-of-baruch")
        self.assertEqual(len(got["chapters"]), 1)

    def test_no_division_is_empty(self):
        for work_id in SCANS:
            for chapter in self.work(work_id)["chapters"]:
                self.assertTrue(chapter["paras"], f"{work_id} {chapter['n']}")
                self.assertTrue(" ".join(chapter["paras"]).strip())


class NoWitnessIsClaimedThatDoesNotCarryTheWork(unittest.TestCase):
    """Sinaiticus and Vaticanus are attached by section, not by book.

    Section IX is arranged by date rather than by canon, so it holds two
    works that are in neither Greek codex: 2 Esdras, whose Greek is lost,
    and this volume's 4 Baruch, which is printed from the Armenian. The
    shortcut that saves listing twenty-seven books by hand was quietly
    claiming both, which is the plainest kind of false citation there is.
    """

    def test_the_codices_are_not_claimed_for_books_they_lack(self):
        with open(os.path.join(DATA, "manuscripts.json"), encoding="utf-8") as fh:
            works = json.load(fh)["works"]
        import manuscripts
        for work_id in manuscripts.NT_SECTION_EXCEPT:
            self.assertNotIn(work_id, works, f"{work_id} is credited to a "
                                             f"manuscript that does not hold it")

    def test_the_rest_of_the_section_still_has_them(self):
        with open(os.path.join(DATA, "manuscripts.json"), encoding="utf-8") as fh:
            works = json.load(fh)["works"]
        for work_id in ("mark", "romans", "revelation"):
            self.assertEqual(works[work_id], ["sinaiticus", "vaticanus"])


class WhatTheseWorksSayAboutThemselves(unittest.TestCase):

    def test_none_of_them_claims_to_be_audited(self):
        for work_id in SCANS:
            with open(os.path.join(DATA, "works", work_id + ".json"),
                      encoding="utf-8") as fh:
                got = json.load(fh)
            self.assertFalse(got["verified"], work_id)
            self.assertTrue(any("recovered rather than" in n
                                for n in got["note"]), work_id)

    def test_each_one_names_the_edition_it_came_from(self):
        with open(os.path.join(DATA, "manifest.json"), encoding="utf-8") as fh:
            manifest = json.load(fh)
        for work_id in list(SCANS) + ["the-ethiopic-didascalia"]:
            with open(os.path.join(DATA, "works", work_id + ".json"),
                      encoding="utf-8") as fh:
                got = json.load(fh)
            self.assertIn(got["source"], manifest["sources"],
                          f"{work_id} names a source the reader's apparatus "
                          f"cannot resolve, so its page says nothing about "
                          f"where its text came from")

    def test_the_ones_that_are_not_here_say_why(self):
        with open(os.path.join(DATA, "canon.json"), encoding="utf-8") as fh:
            canon = json.load(fh)
        absent = [b for b in canon["books"] if not b["present"]]
        self.assertEqual(sorted(b["name"] for b in absent),
                         ["1 Meqabyan", "2 Meqabyan", "3 Meqabyan",
                          "Josippon (Zena Ayhud)"])

    def test_the_canon_names_the_books_it_used_to_leave_off(self):
        """A count is only as honest as the list it counts.

        The table reported 89 of 90 Ethiopian units while four books of
        that canon were not on it at all. Naming them makes the number
        worse and makes it true.
        """
        with open(os.path.join(DATA, "canon.json"), encoding="utf-8") as fh:
            canon = json.load(fh)
        names = {b["name"] for b in canon["books"]}
        for missed in ("1 Meqabyan", "2 Meqabyan", "3 Meqabyan",
                       "Josippon (Zena Ayhud)"):
            self.assertIn(missed, names)


if __name__ == "__main__":
    unittest.main()
