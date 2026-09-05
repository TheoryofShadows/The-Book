#!/usr/bin/env python3
"""The first sentence of the site, against the coverage table it describes.

The hero said the Jewish, Protestant, Catholic, Orthodox and Ethiopian canons
were "complete". docs/data/canon.json, built by tools/build_canon.py from the
same table the canons page draws, said the Ethiopian was 90 units of 94, with
the three books of Meqabyan and Josippon absent because no English of them is
old enough to be public domain. The README's opening paragraph had it right;
the page a visitor actually reads did not.

That is worse here than it would be anywhere else. This site's argument is
that it would rather print a hole than a plausible sentence -- the accuracy
report, the NO-POSITION rows, the "not audited" line under four of the
sources. A front page that overstates the coverage and an audit that corrects
it two clicks later is the project disagreeing with itself, and a reader who
notices trusts the wrong half.

So the sentence is held to the data. A canon may be called complete only when
every one of its units is present, and a canon that is short must be named
with the exact number of books it is missing. Ingest the Meqabyan and this
test fails until the sentence is updated -- which is the direction a failure
should point, because the alternative is the claim quietly becoming true and
nobody bothering to say so.

The meta description and the JSON-LD in docs/index.html make the same claim to
machines rather than to people, and are held to the same rule.
"""

import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_JS = os.path.join(ROOT, "docs", "assets", "app.js")
INDEX = os.path.join(ROOT, "docs", "index.html")
CANON = os.path.join(ROOT, "docs", "data", "canon.json")

# What each canon is called in prose. The keys are canon.json's own.
NAMED = {
    "tanakh": "Jewish",
    "protestant": "Protestant",
    "catholic": "Catholic",
    "orthodox": "Eastern Orthodox",
    "ethiopian": "Ethiopian",
}

# Spelt out, because the sentence spells it out. Only as far as a shortfall
# could plausibly go before somebody rewrites the paragraph anyway.
WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
    7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
}

BLOCK = re.compile(r"--8<-- hero: start --8<--(.*?)--8<-- hero: end --8<--",
                   re.DOTALL)
STRING = re.compile(r'"((?:[^"\\]|\\.)*)"')


def hero_sentence():
    """The lede as a reader sees it, joined out of the source.

    The marked block is required rather than searched for: a test that
    silently found nothing to check would pass forever, which is the failure
    mode this whole file exists to prevent.
    """
    with open(APP_JS, encoding="utf-8") as fh:
        src = fh.read()
    m = BLOCK.search(src)
    if not m:
        raise AssertionError("no hero block in docs/assets/app.js")
    block = m.group(1)
    lede = block[block.index('class: "lede"'):]
    # Everything from the class name to the end of the text property: the
    # string literals in between are the sentence, in order.
    lede = lede[:lede.index("})")]
    parts = STRING.findall(lede)
    # "lede" itself, and the property name, are not part of the sentence.
    parts = [p for p in parts if p not in ("lede", "text")]
    return "".join(p.encode().decode("unicode_escape") for p in parts)


def coverage():
    with open(CANON, encoding="utf-8") as fh:
        return json.load(fh)["coverage"]


class HeroMatchesTheCoverageTable(unittest.TestCase):
    def setUp(self):
        self.sentence = hero_sentence()
        self.coverage = coverage()
        self.assertIn("canons complete", self.sentence,
                      "the hero no longer claims anything about completeness; "
                      "if that is deliberate, this test needs rewriting rather "
                      "than deleting")
        # Everything before the claim is the list of canons it applies to.
        self.claimed = self.sentence[:self.sentence.index("canons complete")]

    def test_every_canon_is_named(self):
        """A canon dropped from the sentence is a canon nobody is checking."""
        for key, name in NAMED.items():
            self.assertIn(name, self.sentence,
                          "%s is in the coverage table and not in the hero" % key)

    def test_only_complete_canons_are_called_complete(self):
        for key, name in NAMED.items():
            row = self.coverage[key]
            whole = row["presentInVolume"] == row["units"]
            if whole:
                self.assertIn(
                    name, self.claimed,
                    "%s is complete in canon.json and the hero does not say so"
                    % key)
            else:
                self.assertNotIn(
                    name, self.claimed,
                    "the hero calls the %s canon complete; canon.json has %d of "
                    "%d units, missing %s"
                    % (key, row["presentInVolume"], row["units"],
                       ", ".join(row["absent"])))

    def test_a_short_canon_is_named_with_its_shortfall(self):
        for key, name in NAMED.items():
            row = self.coverage[key]
            short = row["units"] - row["presentInVolume"]
            if not short:
                continue
            self.assertEqual(
                short, len(row["absent"]),
                "%s: the coverage count and the list of absent books disagree"
                % key)
            self.assertIn(
                short, WORDS,
                "%s is short %d books, which this test cannot spell" % (key, short))
            self.assertIn(
                "all but %s books" % WORDS[short], self.sentence,
                "the hero should say the %s canon is here all but %s books"
                % (key, WORDS[short]))

    def test_the_hero_says_why_they_are_missing(self):
        """Not merely that four are absent: absent for a reason that is not
        this project's to fix. The canon table cites it book by book."""
        self.assertIn("public-domain", self.sentence)


class TheMetadataSaysTheSameThing(unittest.TestCase):
    """The description a search engine quotes and the description a reader is
    shown are the same claim, and used to be the same overclaim."""

    def setUp(self):
        with open(INDEX, encoding="utf-8") as fh:
            self.html = fh.read()
        self.coverage = coverage()

    def descriptions(self):
        out = re.findall(r'<meta name="description" content="([^"]*)"', self.html)
        out += re.findall(r'"description": "([^"]*)"', self.html)
        self.assertTrue(out, "no description in docs/index.html")
        return out

    def test_no_description_calls_a_short_canon_complete(self):
        for key, name in NAMED.items():
            row = self.coverage[key]
            if row["presentInVolume"] == row["units"]:
                continue
            for text in self.descriptions():
                if name not in text:
                    continue
                head = text[:text.index(name)]
                self.assertNotIn(
                    "Every text of", head,
                    "a description in docs/index.html claims every text of the "
                    "%s canon; canon.json has %d of %d"
                    % (key, row["presentInVolume"], row["units"]))


if __name__ == "__main__":
    unittest.main()
