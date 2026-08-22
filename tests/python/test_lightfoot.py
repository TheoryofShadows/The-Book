#!/usr/bin/env python3
"""Six chapters of 1 Clement from one printing, fifty-nine from another.

The volume's 1 Clement is now two translations. Chapters 58 to 63 are
Lightfoot's of 1891, recovered from a scan; everything else is Roberts and
Donaldson's of 1885. The whole thing rests on one claim -- that the six
chapters go in at the right place -- and one failure would be invisible:
if the cut were one chapter out of step, the letter would still run 1 to 65
and still read as English, and it would say something Clement did not.

So the seam is what is checked here, from both sides. tools/fetch_scans.py
takes ten leaves rather than the four the missing chapters need, precisely
so that Lightfoot's 57, 64 and 65 come with them and can be held against the
volume's own. They are different translations of the same Greek: they will
not agree word for word, and they must agree about who is named, what is
quoted, and where each chapter ends.
"""

import json
import os
import re
import unittest

import _tools  # noqa: F401
import build_lightfoot as bl
import scans

ROOT = _tools.ROOT
SCAN = os.path.join(ROOT, "source", "extra", bl.SCAN)
WORKS = os.path.join(ROOT, "docs", "data", "works")


def work(wid):
    with open(os.path.join(WORKS, wid + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def recovered():
    paragraphs, pages = scans.read_recovered(SCAN)
    text = bl.repair("\n\n".join(scans.prose(paragraphs, [])), [])
    text = bl.THIN.sub(r"\1", text)
    return bl.cut(text.split("\n\n"), bl.PRINTED), pages


def words(text):
    return set(re.findall(r"[A-Za-z']+", text.lower()))


class TheScanIsCutWhereItShouldBe(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.chapters, cls.pages = recovered()

    def test_every_chapter_the_leaves_carry_is_found(self):
        self.assertEqual(sorted(self.chapters), sorted(bl.PRINTED))

    def test_no_chapter_comes_out_empty(self):
        for n, paras in self.chapters.items():
            self.assertTrue(" ".join(paras).strip(), f"chapter {n} is empty")

    def test_the_leaves_are_the_ten_that_were_asked_for(self):
        self.assertEqual(len(self.pages), 10)

    def test_the_prayer_is_a_paragraph_of_its_own_inside_59(self):
        # Lightfoot sets the intercessory prayer off from the sentence that
        # introduces it. Losing that break would not lose a word and would
        # lose the shape of the thing.
        self.assertEqual(len(self.chapters[59]), 2)
        self.assertTrue(self.chapters[59][1].startswith("[Grant unto us, Lord,]"))


class TheSeamIsInTheRightPlace(unittest.TestCase):
    """Lightfoot's 57, 64 and 65 against the volume's own 57, 64 and 65."""

    @classmethod
    def setUpClass(cls):
        cls.lightfoot, _ = recovered()
        cls.volume = {c["n"]: " ".join(c["paras"])
                      for c in work(bl.CLEMENT)["chapters"]}

    def test_the_letter_runs_one_to_sixty_five(self):
        self.assertEqual([c["n"] for c in work(bl.CLEMENT)["chapters"]],
                         list(range(1, 66)))

    def test_both_translations_of_57_reach_the_edge_of_the_lacuna(self):
        # Proverbs 1.31, which is where Codex Alexandrinus gives out: the
        # volume's 57 stops on it and Lightfoot's runs two verses past it.
        # Both have to contain it, and the volume's has to end there, or the
        # six chapters are being joined on at the wrong seam.
        edge = "filled with their own ungodliness"
        self.assertIn(edge, " ".join(self.lightfoot[57]))
        self.assertIn(edge, self.volume[57])
        self.assertTrue(self.volume[57].rstrip().endswith(edge + '."'))

    def test_both_translations_of_65_name_the_three_messengers(self):
        named = {"claudius", "ephebus", "valerius", "bito", "fortunatus"}
        self.assertTrue(named <= words(" ".join(self.lightfoot[65])))
        self.assertTrue(named <= words(self.volume[65]))

    def test_both_translations_of_64_are_the_same_benediction(self):
        # The list of graces Clement asks for. Two translators, one list.
        # Not the whole list: the two translators part company over the
        # last three words of it, where Lightfoot has temperance, chastity
        # and soberness and the ANF has self-control, purity and sobriety.
        for wanted in ("faith", "fear", "peace", "patience"):
            self.assertIn(wanted, words(" ".join(self.lightfoot[64])))
            self.assertIn(wanted, words(self.volume[64]))

    def test_the_volume_keeps_its_own_translation_either_side(self):
        # The six chapters are Lightfoot's; 64 is not. If the splice had
        # overwritten it, the volume's 64 would read "Finally may the
        # All-seeing God", which is Lightfoot's opening, not the ANF's.
        self.assertTrue(self.volume[64].startswith("May God, who seeth"))
        self.assertTrue(" ".join(self.lightfoot[64]).startswith(
            "Finally may the All-seeing God"))


class TheChaptersThatWereMissing(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.volume = {c["n"]: " ".join(c["paras"])
                      for c in work(bl.CLEMENT)["chapters"]}

    def test_the_great_prayer_is_here(self):
        prayer = self.volume[59] + " " + self.volume[60] + self.volume[61]
        for line in ("Succour of them that are in peril",
                     "feed the hungry; release our prisoners",
                     "Give concord and peace to us",
                     "the sheep of Thy pasture"):
            self.assertIn(line, prayer)

    def test_the_prayer_for_the_rulers_is_here(self):
        # 61: a Christian congregation praying for the Roman authorities,
        # twenty years or so after Domitian. It is the reason this chapter
        # is quoted in every argument about church and state in the period.
        self.assertIn("hast given them the power of sovereignty",
                      self.volume[61])

    def test_the_scan_repairs_all_fired(self):
        with open(os.path.join(ROOT, "docs", "data",
                               "lightfoot-repairs.json"), encoding="utf-8") as fh:
            report = json.load(fh)
        never = [r["scanned"] for r in report["repairs"] if not r["times"]]
        self.assertEqual(never, [], "repairs that no longer fire")

    def test_no_repaired_reading_survives_in_the_text(self):
        whole = " ".join(self.volume.values())
        for scanned, _printed in bl.REPAIRS:
            self.assertNotIn(scanned, whole)

    def test_the_work_says_which_chapters_are_lightfoots(self):
        note = " ".join(work(bl.CLEMENT)["note"])
        self.assertIn("58 to 63", note)
        self.assertIn("Lightfoot", note)


class SmyrnaeansThirteen(unittest.TestCase):
    """Not a hole: a chapter read as the second half of the one before."""

    @classmethod
    def setUpClass(cls):
        cls.work = work(bl.SMYRNAEANS)

    def test_the_letter_runs_one_to_thirteen(self):
        self.assertEqual([c["n"] for c in self.work["chapters"]],
                         list(range(1, 14)))

    def test_thirteen_opens_at_the_salutations(self):
        self.assertTrue(self.work["chapters"][-1]["paras"][0].startswith(
            "I salute the families of my brethren"))

    def test_the_heading_is_gone_from_the_text(self):
        whole = " ".join(p for c in self.work["chapters"]
                         for p in c["paras"])
        self.assertNotIn("CONCLUSION", whole)

    def test_ignatius_greets_troas_once(self):
        twelve = self.work["chapters"][11]["paras"][0]
        self.assertEqual(twelve.count("The love of the brethren at Troas"), 1)
        self.assertNotIn("The love of your brethren at Troas", twelve)

    def test_the_doubled_word_is_gone(self):
        thirteen = self.work["chapters"][-1]["paras"][0]
        self.assertNotIn("and and", thirteen)
        self.assertIn("with their wives and children, and the virgins",
                      thirteen)


class HeadingsLeftAtTheHeadOfTheirOwnChapter(unittest.TestCase):
    """The other kind of contamination, and the rule that finds it."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "docs", "data",
                               "heading-residue.json"), encoding="utf-8") as fh:
            cls.report = json.load(fh)

    def test_they_were_found_across_more_than_one_work(self):
        works = {r["work"] for r in self.report["removed"]}
        self.assertGreater(len(works), 2)

    def test_no_chapter_now_opens_in_the_middle_of_a_sentence(self):
        # A chapter opening in lower case is what this defect looks like
        # from the outside, and after the repair there should be none left
        # in the works it touched.
        for wid in {r["work"] for r in self.report["removed"]}:
            for chapter in work(wid)["chapters"]:
                first = (chapter.get("paras") or [""])[0]
                self.assertFalse(re.match(r"^[a-z]", first),
                                 f"{wid} {chapter['label']}: {first[:60]}")

    def test_a_chapter_that_opens_by_naming_itself_is_left_alone(self):
        # Barnabas 19 is headed "The way of light" and opens "The way of
        # light, then, is as follows". A rule that matched headings without
        # asking whether a sentence resumed after them would eat it.
        barnabas = work("the-epistle-of-barnabas")
        nineteen = next(c for c in barnabas["chapters"] if c["n"] == 19)
        self.assertTrue(nineteen["paras"][0].startswith("The way of light"))

    def test_a_chapter_that_opens_with_its_headings_words_is_left_alone(self):
        # The Martyrdom of Polycarp 7 is headed "Polycarp is discovered by
        # his pursuers" and opens "His pursuers then, along with horsemen".
        martyrdom = work("the-martyrdom-of-polycarp")
        seven = next(c for c in martyrdom["chapters"] if c["n"] == 7)
        self.assertTrue(seven["paras"][0].startswith("His pursuers then"))


if __name__ == "__main__":
    unittest.main()
