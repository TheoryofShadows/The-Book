#!/usr/bin/env python3
"""What the voice is handed, in Python, for the side that renders audio.

docs/assets/app.js decides what a speech engine is given: the editorial marks
blanked, the roman numerals said as numbers, the doubled hyphen turned into
the pause it was printed for. That rule ran in one place while the only
narrator was the browser's own.

Pre-rendering puts a second narrator on the other side of the build, and it
has to be handed exactly the same string. If the two drift, the audio says
"dagger" where the page is silent, or reads LXXXIX as letters -- and nothing
fails, because both sides are individually well-formed. The audio is simply
wrong, in a hundred and sixteen hours of it that nobody is going to listen to
in full.

tests/python/test_speakable_agreement.py runs the reader's own copy of the
rule against this one and fails if they part company, the way
test_tokeniser_agreement.py already does for the search tokeniser.

Deliberately stdlib-only. The renderer that used to share it needed a
neural engine and
half a gigabyte of wheels; the rule it shares with the reader must not, or
the test that holds the two together could not run in CI.
"""

from __future__ import annotations

import os
import re

APP_JS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      os.pardir, "docs", "assets", "app.js")

# The numerals Charles prints in his running text, matched only when a full
# stop follows -- which is what keeps an ordinary capitalised word made of
# numeral letters ("DID", "MIX") out of it.
ROMAN = re.compile(
    r"\b(?=[MDCLXVI]{2,}\b)M{0,3}(?:CM|CD|D?C{0,3})"
    r"(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})\b\.")

ROMAN_VALUE = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

PAD = " " * 10


def editorial_pattern(app_js: str = APP_JS) -> re.Pattern:
    """The blanked class, read out of the reader rather than copied.

    tests/python/test_narration.py already reads EDITORIAL this way to hold it
    against the characters the volume contains. Reading it again here means a
    mark added for the page is blanked in the audio by the same edit, and
    there is no second list to forget.

    Not finding it is a hard failure. A renderer that quietly fell back to a
    class of its own would agree with nothing and say so never.
    """
    with open(app_js, encoding="utf-8") as fh:
        m = re.search(r"var EDITORIAL = /\[(.*?)\]/g;", fh.read())
    if not m:
        raise AssertionError(
            "docs/assets/app.js no longer declares EDITORIAL as expected; "
            "if the declaration moved, point this at it -- do not guess the "
            "character class")

    body, chars, i = m.group(1), [], 0
    while i < len(body):
        ch = body[i]
        if ch == "\\":                      # \\ and \] arrive escaped
            i += 1
            ch = body[i]
        chars.append(ch)
        i += 1
    return re.compile("[" + re.escape("".join(chars)) + "]")


def from_roman(text: str) -> int:
    """MDCCCXCIV -> 1894, reading right to left the way the reader does."""
    total = highest = 0
    for ch in reversed(text):
        value = ROMAN_VALUE[ch]
        total = total - value if value < highest else total + value
        highest = max(highest, value)
    return total


def speakable(text: str, editorial: re.Pattern | None = None) -> str:
    """The string the reader would hand a speech engine, for this text.

    The padding looks pointless on this side -- nothing here highlights a
    word by character offset -- and it is kept anyway, because the value of
    this function is being character-for-character what app.js produces. A
    difference that "does not matter" is a difference the agreement test has
    to be taught to ignore, and then it is not holding the two together any
    more.
    """
    if editorial is None:
        editorial = editorial_pattern()

    text = editorial.sub(" ", text)
    text = text.replace("--", ", ")

    def say(match: re.Match) -> str:
        whole = match.group(0)
        said = str(from_roman(whole[:-1])) + "."
        if len(said) > len(whole):          # CD is 400 and would grow
            return whole
        return said + PAD[:len(whole) - len(said)]

    return ROMAN.sub(say, text)
