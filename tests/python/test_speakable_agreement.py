"""What the voice is handed is decided twice. This holds the two together.

docs/assets/app.js speakable() decides what the browser's engine is given.
tools/speakable.py decides what the pre-rendered audio is made from. They are
one rule in two languages, and a divergence is silent on both sides: the page
renders, the render finishes, and the audio simply says something the page
does not.

It is worse than the search tokeniser it is modelled on. A wrong search key
is discovered the first time somebody searches for that word. A wrong reading
is discovered only by somebody listening to that verse, in a hundred and
sixteen hours of audio, and by then it is a re-render.

The JS is executed rather than reimplemented, for the reason given in
test_tokeniser_agreement.py: a Python translation would be a third copy that
agrees with the other two by construction.
"""

import json
import os
import shutil
import subprocess
import unittest

import _tools

import speakable

APP_JS = os.path.join(_tools.ROOT, "docs", "assets", "app.js")

# Where a divergence would plausibly turn up: every mark in the blanked class,
# the roman numerals at the lengths Charles actually prints, the doubled
# hyphen, and the cases the padding rule exists for.
SAMPLE = [
    "In the beginning, God created the heavens and the earth.",

    # The apparatus, one mark at a time and then together.
    "†corrupt† reading",
    "<restored> text",
    "+emended+ words",
    "[a later hand]",
    "{a brace}",
    "the ® and the » and the ° and the § and the •",
    "¢ £ ¥ € $ # % * ^ ¬ ■ | \\ _ & ™ © ¶",
    "†‡+<>[]{}®©™°§¶•¢£¥€$#%*«»^¬■|\\_&",

    # Roman numerals: the ordinary ones, the subtractive forms, the long ones
    # Enoch and Jubilees carry, and the ones that must be left alone.
    "Chapter II. begins",
    "Chapter IV. and chapter IX.",
    "Chapter XIV. of the book",
    "Chapter LXXXIX. of Enoch",
    "Chapter MDCCCXCIV. is not a chapter",
    "CD. would grow, so it stays",
    "CM. likewise",
    "I. is one letter and the rule wants two",
    "DID and MIX are words, not numerals",
    "MIX. however ends in a stop",

    # The doubled hyphen, alone and beside everything else.
    "a still small voice--and then",
    "don't--won't",
    "†X.--Y†",

    # Nothing, and nothing but marks.
    "",
    "   ",
    "†®©",

    # A real verse with a real footnote reference in it.
    "Then Nebuchadnezzar® came near to the mouth of the burning fiery "
    "furnace. He spoke and said, “Shadrach, Meshach, and Abednego, you "
    "servants of the Most High God, come out, and come here!”",
]


def js_speakable(strings):
    """Run the reader's own speakable() over the sample, in Node.

    app.js wants a DOM, so the block between the markers is lifted out and run
    on its own. Not finding the markers is a hard failure: a test that fell
    back to a rule of its own would agree with Python forever and check
    nothing.
    """
    script = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8');

const START = '/* --8<-- speakable: start --8<-- */';
const END = '/* --8<-- speakable: end --8<-- */';
const a = src.indexOf(START), b = src.indexOf(END);
if (a < 0 || b < 0) {
  throw new Error('the speakable markers are not in app.js; if the block ' +
                  'moved, move these markers with it -- do not delete them');
}
const block = src.slice(a + START.length, b);

const make = new Function(block + '; return speakable;');
const speakable = make();

const input = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(input.map(speakable)));
"""
    out = subprocess.run(
        ["node", "-e", script, APP_JS, json.dumps(strings)],
        capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError(
            "could not run the reader's speakable():\n" + out.stderr.strip())
    return json.loads(out.stdout)


@unittest.skipIf(shutil.which("node") is None,
                 "node is needed to run the reader's own copy of the rule")
class SpeakableAgreement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.js = js_speakable(SAMPLE)
        cls.editorial = speakable.editorial_pattern()

    def test_every_sample_is_spoken_the_same_way(self):
        for text, js in zip(SAMPLE, self.js):
            self.assertEqual(speakable.speakable(text, self.editorial), js,
                             "speakable() differs for %r" % text)

    def test_the_sample_actually_exercises_the_rule(self):
        # A test that agrees on twenty unchanged strings proves nothing.
        changed = [t for t, js in zip(SAMPLE, self.js) if t != js]
        self.assertGreater(len(changed), 15)

    def test_the_blanked_class_is_read_from_the_reader(self):
        # Not a copy: the pattern has to come from app.js, so a mark added
        # there is blanked here by the same edit.
        for mark in "†‡®©™°§¶•":
            self.assertTrue(self.editorial.search(mark), mark)
        for kept in "abc123 ,.;:!?'\"()-":
            self.assertIsNone(self.editorial.search(kept), kept)

    def test_offsets_do_not_move(self):
        # The reader highlights a word by character offset into this string,
        # so it must be the same length as the text on the page. The roman
        # rule pads for exactly this reason.
        for text, js in zip(SAMPLE, self.js):
            if "--" in text:
                continue        # the one rule that is a substitution, 2 for 2
            self.assertEqual(len(text), len(js),
                             "length changed for %r" % text)


class SpeakableRules(unittest.TestCase):
    """The Python half alone, so a failure says which side moved."""

    @classmethod
    def setUpClass(cls):
        cls.editorial = speakable.editorial_pattern()

    def say(self, text):
        return speakable.speakable(text, self.editorial)

    def test_roman_numerals_become_arabic(self):
        # Padded back out to the length of the numeral it replaced, so the
        # character offsets the word highlight runs on do not move.
        self.assertEqual(self.say("Chapter II."), "Chapter 2. ")
        self.assertEqual(self.say("Chapter LXXXIX."), "Chapter 89.    ")

    def test_a_numeral_that_would_grow_is_left_alone(self):
        self.assertEqual(self.say("CD."), "CD.")
        self.assertEqual(self.say("CM."), "CM.")

    def test_a_single_letter_is_not_a_numeral(self):
        self.assertEqual(self.say("I. am"), "I. am")

    def test_a_numeral_needs_its_full_stop(self):
        self.assertEqual(self.say("MIX and match"), "MIX and match")

    def test_marks_are_blanked_not_deleted(self):
        self.assertEqual(self.say("†corrupt†"), " corrupt ")

    def test_the_doubled_hyphen_becomes_a_pause(self):
        self.assertEqual(self.say("voice--and"), "voice, and")

    def test_from_roman_reads_subtractive_forms(self):
        self.assertEqual(speakable.from_roman("IV"), 4)
        self.assertEqual(speakable.from_roman("IX"), 9)
        self.assertEqual(speakable.from_roman("XIV"), 14)
        self.assertEqual(speakable.from_roman("LXXXIX"), 89)
        self.assertEqual(speakable.from_roman("MDCCCXCIV"), 1894)


if __name__ == "__main__":
    unittest.main()
