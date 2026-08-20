#!/usr/bin/env python3
"""One folding rule, for everything that turns text into a key.

Three build scripts and the reader all reduce text to a comparable form: the
search index files a token, the lexicon files a headword, the gazetteer files a
place name, and the reader has to arrive at exactly the same string for any of
them to be found again. That rule lived in four places and agreed by luck.

Where it stopped agreeing:

  Search dropped accented letters instead of folding them, so Charles's
  transliterations went into the index as fragments -- "Mastêmâ" filed under
  "mast" and "m", "Cæsar" under "c" and "sar" -- and no spelling a reader could
  type would find them. 163 word-forms, 304 occurrences.

  The lexicon built its keys with NFKD and an ASCII fold, and the reader built
  its lookup key by deleting anything outside [a-z0-9 ]. For "Mastêmâ" that is
  "mastema" against "mastm": the entry existed and the reader asking for it by
  double-clicking the word could not reach it.

Both failures are silent. Nothing raises, the page renders, the search simply
answers that no text contains a word that appears twenty times.

tests/python/test_tokeniser_agreement.py runs the reader's copy of this rule
against this one and fails if they part company.
"""

from __future__ import annotations

import re
import unicodedata

TOKEN = re.compile(r"[a-z0-9]+")

# NFKD leaves these alone -- they are letters in their own right, not accented
# forms of anything -- so a reader typing "Caesar" would still miss "Cæsar".
# Expanding them by hand is what makes the two spellings meet.
LIGATURES = {
    "æ": "ae", "œ": "oe", "ß": "ss", "ð": "d", "þ": "th", "ø": "o",
    "đ": "d", "ł": "l", "ħ": "h", "ŋ": "ng",
}

CURLY = re.compile(r"[‘’ʼʻ]")
COMBINING = re.compile(r"[\u0300-\u036f]")


def fold(text: str) -> str:
    """Lowercase, expand the ligatures, and separate letters from their accents.

    Order matters and is mirrored exactly in docs/assets/app.js: case first,
    so the ligature table only needs its lowercase entries; then the quotes,
    so the two apostrophes cannot end up on different sides of a comparison;
    then the ligatures, which have to happen before the decomposition or they
    survive it unchanged; then the decomposition, which splits a letter from
    its accent so that the accent alone can be dropped.

    What is deliberately *not* done here is discarding everything outside
    ASCII. Doing that deletes a separator instead of respecting it: an em dash
    vanishes and "voice-and" becomes one word "voiceand", which is then filed
    under a key nothing will ever ask for. Characters that are not letters are
    left standing, and the two callers below decide what to do with them --
    which is what the JavaScript does, and the only way the two stay equal.
    """
    text = text.lower()
    text = CURLY.sub("'", text)
    for src, dst in LIGATURES.items():
        text = text.replace(src, dst)
    text = unicodedata.normalize("NFKD", text)
    return COMBINING.sub("", text)


def search_tokens(text: str) -> list[str]:
    """The words the search index files, and the words a query is looked up as."""
    return TOKEN.findall(fold(text))


def lookup_key(text: str) -> str:
    """The key a lexicon entry or a place name is filed under.

    Unlike a search token this keeps the spaces, because the headwords are
    phrases -- "sea of galilee", "ain gedi the" -- and drops the apostrophe
    rather than splitting on it, so "Rachel's tomb" and "Rachels tomb" are one
    entry.
    """
    text = fold(text).replace("'", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", "", text)).strip()
