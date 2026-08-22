#!/usr/bin/env python3
"""What the voice is handed, checked against what the volume contains.

The reader blanks the marks that are apparatus rather than words before
speaking a passage — Charles's daggers and brackets, and the footnote
references the nineteenth-century printings recovered from scans are full
of. That list lives in docs/assets/app.js, where the browser checks can
exercise it, and it is a list of characters somebody wrote down once.

The failure it invites is silent and one-directional. Add a text recovered
from another scan, and it arrives with another engine's idea of a
superscript dagger; nothing breaks, no test goes red, and a voice somewhere
starts saying "pilcrow" in the middle of a psalm. Nobody is listening to all
1.22 million words to find out.

So this reads the class out of the reader and holds it against every
character the volume actually contains. A character that is neither a letter,
a digit, nor punctuation an English sentence uses has to be either in the
class or in the short list below of the ones deliberately left for the voice
to read.
"""

import json
import os
import re
import unittest

import _tools  # noqa: F401

ROOT = _tools.ROOT
APP = os.path.join(ROOT, "docs", "assets", "app.js")
WORKS = os.path.join(ROOT, "docs", "data", "works")

# Punctuation an English sentence is made of. A speech engine reads these as
# phrasing, which is what they are for, and none of them belongs in the
# blanked class.
SENTENCE = set(" ,.;:!?'’\"“”‘()-–—")

# Characters that are not sentence punctuation and are still left alone,
# with the reason. Both are read correctly by every engine, and both mean
# something where they stand.
SPOKEN = {
    "=": "Charles glosses his abbreviations with it — “A.M. = Anno "
         "Mundi” — and an engine says “equals”, which is right",
    "/": "three occurrences, all inside Horner's editorial “(lit. …)”",
}


def marks_from_reader():
    """The blanked class as the reader defines it, as a set of characters."""
    with open(APP, encoding="utf-8") as fh:
        source = fh.read()
    m = re.search(r"var EDITORIAL = /\[(.*?)\]/g;", source)
    assert m, "docs/assets/app.js no longer declares EDITORIAL as expected"
    body, out, i = m.group(1), set(), 0
    while i < len(body):
        ch = body[i]
        if ch == "\\":
            i += 1
            ch = body[i]
        out.add(ch)
        i += 1
    return out


def volume_characters():
    """Every character in the text the reader would speak, with an example."""
    seen = {}
    for name in sorted(os.listdir(WORKS)):
        with open(os.path.join(WORKS, name), encoding="utf-8") as fh:
            work = json.load(fh)
        for chapter in work.get("chapters", []):
            texts = list(chapter.get("paras", []))
            texts += [v["t"] for v in chapter.get("verses", [])]
            for text in texts:
                for i, ch in enumerate(text):
                    if ch not in seen:
                        seen[ch] = (name, text[max(0, i - 40):i + 40])
    return seen


class EveryMarkTheVolumeHasIsAccountedFor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.marks = marks_from_reader()
        cls.chars = volume_characters()

    def test_the_class_can_be_read_out_of_the_reader(self):
        # If this fails the rest of the file is checking nothing, so it is
        # asserted rather than assumed.
        self.assertGreater(len(self.marks), 10)
        for ch in "†+<>[]":
            self.assertIn(ch, self.marks, "Charles's apparatus")

    def test_the_scan_footnote_marks_are_in_it(self):
        # The ones the recovered printings actually contain, in order of how
        # often. Named rather than derived, so that a change to the class
        # that dropped them would fail here as well as in the sweep below.
        for ch in "®»«°§•¢£¥™©":
            self.assertIn(ch, self.marks)

    def test_nothing_unaccounted_for_is_left_for_the_voice(self):
        loose = []
        for ch, (where, excerpt) in sorted(self.chars.items()):
            if ch.isalnum() or ch in SENTENCE or ch in self.marks or ch in SPOKEN:
                continue
            loose.append(f"{ch!r} in {where}: …{excerpt.strip()}…")
        self.assertEqual(loose, [], "\n".join(
            ["characters the voice would read out that nothing accounts for.",
             "Add each to EDITORIAL in docs/assets/app.js, or to SPOKEN here "
             "with a reason:"] + loose))

    def test_no_blanked_mark_is_ordinary_punctuation(self):
        # The class is blanked wholesale, so a comma finding its way in would
        # silently take the phrasing out of the whole library.
        for ch in self.marks:
            self.assertNotIn(ch, SENTENCE, f"{ch!r} is sentence punctuation")

    def test_every_reason_given_for_leaving_a_mark_alone_still_applies(self):
        # A reason for a character the volume no longer contains is a claim
        # about nothing, and the next person to read it will believe it.
        for ch in SPOKEN:
            self.assertIn(ch, self.chars, f"{ch!r} is no longer in the volume")


class TheMarksAreWorthBlanking(unittest.TestCase):
    """Not a rule looking for a problem: the problem is measurable."""

    @classmethod
    def setUpClass(cls):
        cls.marks = marks_from_reader()

    def test_the_recovered_works_are_thick_with_them(self):
        with open(os.path.join(WORKS, "the-testament-of-our-lord.json"),
                  encoding="utf-8") as fh:
            work = json.load(fh)
        text = " ".join(p for c in work["chapters"] for p in c["paras"])
        found = sum(1 for ch in text if ch in self.marks)
        # About one every other sentence, which is what it sounded like.
        self.assertGreater(found, 200)
        self.assertLess(found / max(1, text.count(". ")), 3)


if __name__ == "__main__":
    unittest.main()
