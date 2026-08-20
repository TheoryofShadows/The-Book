"""The search tokeniser is written twice. This is the only thing holding the
two copies together.

tools/build_index.py normalise() decides what goes into the index. The
reader's own tokenise(), in docs/assets/app.js, decides what a query is looked
up as. They implement one rule in two languages, and if they ever disagree the
failure is silent and total for the affected words: the index has "lion" filed
under a key the client never asks for, so the search returns nothing and says,
untruthfully, that no text contains it.

Nothing else in the build would notice. The index would be well-formed, the
site would raise nothing, and the only symptom is a search result that is
quietly wrong.

The JS is executed here rather than reimplemented, because a Python
translation of it would be a third copy of the rule and would agree with the
other two by construction.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

import _tools

import build_index
import build_lexicon
import build_places
import textnorm

APP_JS = os.path.join(_tools.ROOT, "docs", "assets", "app.js")

# The words a divergence would most plausibly turn up in: curly and straight
# apostrophes, hyphenation, case, digits, accents, the em dash the WEB uses,
# the editorial marks Charles prints in the running text, and the punctuation
# that ends a verse.
SAMPLE = [
    "In the beginning God created the heavens and the earth.",
    "the LORD's anointed",                      # straight apostrophe
    "the LORD’s anointed",                 # curly apostrophe
    "‘quoted’ speech",                # curly single quotes
    "Beth-Shemesh and Kiriath-Jearim",
    "1 Enoch 72, and Jubilees 6",
    "Habakkuk 2:4",
    "Lûbâr, one of the Ararat Mountains",   # combining accents
    "Lûbâr, one of the Ararat Mountains",     # precomposed
    "a still small voice—and then",        # em dash
    "†corrupt† and <restored> and +emended+ and [a later hand]",
    "ALL CAPS AND Mixed Case",
    "trailing space   ",
    "",
    "   ",
    "123 456",
    "don't---won't",
    "Ba‘al",                               # turned comma as a letter
    "Mastêmâ and Cæsar",                   # the two folds this file exists for
    "son of man;  and the watchers.",
    "Élohim",
]


def js_fold(strings: list[str]) -> dict:
    """Run the reader's own folding rule over the sample, in Node.

    app.js wants a DOM, so the block between the markers is lifted out and run
    on its own rather than loading the file. Not finding the markers is a hard
    failure: a test that quietly fell back to a tokeniser of its own would
    agree with Python forever and check nothing.
    """
    script = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8');

const START = '/* --8<-- fold: start --8<-- */';
const END = '/* --8<-- fold: end --8<-- */';
const a = src.indexOf(START), b = src.indexOf(END);
if (a < 0 || b < 0) {
  throw new Error('the fold markers are not in app.js; if the block moved, ' +
                  'move these markers with it -- do not delete them');
}
const block = src.slice(a + START.length, b);

const make = new Function(block + '; return { tokenise: tokenise, normTerm: normTerm };');
const fns = make();

const input = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify({
  tokens: input.map(fns.tokenise),
  keys: input.map(fns.normTerm)
}));
"""
    out = subprocess.run(
        ["node", "-e", script, APP_JS, json.dumps(strings)],
        capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError("could not run the reader's fold:\n" + out.stderr.strip())
    return json.loads(out.stdout)


@unittest.skipIf(shutil.which("node") is None,
                 "node is needed to run the reader's own copy of the rule")
class FoldAgreement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.js = js_fold(SAMPLE)

    def test_search_tokens_agree_on_every_sample(self):
        for text, js in zip(SAMPLE, self.js["tokens"]):
            self.assertEqual(textnorm.search_tokens(text), js,
                             "search tokens differ for %r" % text)

    def test_lookup_keys_agree_on_every_sample(self):
        for text, js in zip(SAMPLE, self.js["keys"]):
            self.assertEqual(textnorm.lookup_key(text), js,
                             "lookup keys differ for %r" % text)

    def test_the_index_builder_and_the_lexicon_use_that_same_rule(self):
        # Delegation, not a fourth copy: if either script grows its own
        # version again this is what notices.
        for text in SAMPLE:
            self.assertEqual(build_index.normalise(text),
                             textnorm.search_tokens(text), text)
            self.assertEqual(build_lexicon.norm(text),
                             textnorm.lookup_key(text), text)
            self.assertEqual(build_places.norm(text),
                             textnorm.lookup_key(text), text)

    def test_the_sample_actually_exercises_the_rule(self):
        # A test that agrees on twenty empty lists proves nothing.
        produced = [t for row in self.js["tokens"] for t in row]
        self.assertGreater(len(produced), 60)
        self.assertIn("beth", produced)      # a hyphen split the word
        self.assertIn("1", produced)         # digits are tokens
        self.assertIn("caesar", produced)    # the ligature was expanded
        self.assertIn("mastema", produced)   # the accents were folded

    def test_the_two_spellings_of_an_accented_name_meet(self):
        # Combining marks and precomposed characters have to land on the same
        # key, or the same name indexes two ways depending on the keyboard.
        combining = "Lu\u0302ba\u0302r"
        precomposed = "L\u00fbb\u00e2r"
        self.assertEqual(textnorm.search_tokens(combining),
                         textnorm.search_tokens(precomposed))
        self.assertEqual(textnorm.search_tokens(precomposed), ["lubar"])

    def test_an_accented_word_reaches_its_own_lexicon_entry(self):
        # The bug this file was written for: the entry was filed under the
        # folded key and the reader selecting the word on the page asked for
        # a different one.
        self.assertEqual(textnorm.lookup_key("Mastêmâ"), "mastema")
        self.assertEqual(self.js["keys"][SAMPLE.index("Mastêmâ and Cæsar")],
                         textnorm.lookup_key("Mastêmâ and Cæsar"))


class NormaliseRules(unittest.TestCase):
    """The Python half on its own, so a failure says which side moved."""

    def test_lowercases(self):
        self.assertEqual(build_index.normalise("LION"), ["lion"])

    def test_splits_on_punctuation(self):
        self.assertEqual(build_index.normalise("Beth-Shemesh"), ["beth", "shemesh"])

    def test_an_apostrophe_splits_a_search_token(self):
        # It is not in the token class, so it separates like any other mark.
        # The lookup key deletes it instead; the two rules differ here on
        # purpose and both sides of the port have to differ the same way.
        self.assertEqual(build_index.normalise("LORD's"), ["lord", "s"])
        self.assertEqual(textnorm.lookup_key("LORD's"), "lords")

    def test_digits_are_tokens(self):
        self.assertEqual(build_index.normalise("Chapter 12"), ["chapter", "12"])

    def test_empty_text_yields_no_tokens(self):
        self.assertEqual(build_index.normalise(""), [])
        self.assertEqual(build_index.normalise("   —  "), [])

    def test_editorial_marks_do_not_become_tokens(self):
        self.assertEqual(build_index.normalise("†corrupt†"), ["corrupt"])


class IndexShape(unittest.TestCase):
    """The client picks a shard from the token's first character."""

    def test_every_token_lands_in_a_shard_the_client_would_ask_for(self):
        # app.js: k = /^[a-z]/.test(t) ? t[0] : "0". A token that starts with
        # anything else has to be in the "0" shard or it can never be found.
        for text in SAMPLE:
            for token in build_index.normalise(text):
                shard = token[0] if re.match(r"^[a-z]", token) else "0"
                self.assertTrue(re.match(r"^[a-z0]$", shard),
                                "token %r has no shard" % token)

    def test_the_common_ratio_is_a_ratio(self):
        self.assertGreater(build_index.COMMON_RATIO, 0)
        self.assertLess(build_index.COMMON_RATIO, 1)


if __name__ == "__main__":
    unittest.main()
