#!/usr/bin/env python3
"""Add the Ethiopian canon books recovered from the scans under source/extra.

    python3 tools/build_ethiopian.py [docs/data] [source/extra]

WHAT THIS CLOSES, AND WHAT IT DOES NOT

The Ethiopian Orthodox Tewahedo canon is the widest of the five this
volume prints, and five of its books were absent from it. The coverage
table named them and the accuracy report gave the reason: not copyright,
which expired on the Ge'ez many times over, but the want of a *published
English translation* old enough to be public domain. The standard modern
editions are twentieth-century and in copyright, and the nineteenth-
century work was thought to have stopped after the Didascalia, which
tools/build_didascalia.py recovered from Platt's 1834 printing.

It had not stopped. Three more of the five have public-domain English,
and this adds them:

    The Sinodos            Horner printed the Ge'ez in 1904 with his own
                           English facing it. The text opens by naming
                           itself: "This is the Sinodos of the fathers,
                           the Apostles." Complete as Horner has it,
                           which is the Statutes -- the largest part of
                           the Sinodos and not the whole collection.

    The Rest of the        No public-domain English of the Ge'ez exists.
    Words of Baruch        Issaverdens printed one of the Armenian
                           recension in 1901, made from the Greek that
                           the Ge'ez also descends from. A witness to
                           the work, in another version: said so on the
                           work's own page, not buried here.

    The Book of the        Its second book, the discourse of the risen
    Covenant               Lord, is the Ethiopic that Guerrier published
                           and M. R. James rendered into English in
                           1924, from that Ethiopic. Its first book, the
                           church order, still has no public-domain
                           English of any version and is still absent.

The fifth, Ethiopic Clement, stays out. Its second book circulates
separately as the Ethiopic Apocalypse of Peter and James translated
that; the other six have no public-domain English, and James took his
Ethiopic only as far as the point where he judged the rest late and
stopped. A seventh of a book, itself cut short, printed as the book
would be worse than the gap. tools/build_canon.py says so where a reader
will see it.

NONE OF THESE THREE IS AUDITED. Every biblical book in this volume is
checked verse for verse against independent reference counts. No such
counts exist for any of these, so there is nothing to check them against
but the scans, and each is marked verified: false and says so on its own
page. What *is* checked is below, and in tests/python/test_ethiopian.py:
that the divisions found are the divisions printed, in the order printed
and with the numbers printed -- including the two statutes Horner
numbers 40, which is his numbering and not a fault in this reading of
it.
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dates                                            # noqa: E402
import scans                                            # noqa: E402
from positions import POSITIONS                         # noqa: E402

# Defaults, overridden from the command line in main(). Read there rather
# than here so that importing this module -- which the tests do -- cannot
# pick up whatever arguments the importing program was given.
OUT = "docs/data"
RAW = "source/extra"
SRC = "source/THE_BOOK_COMPLETE.txt"

WORD = re.compile(r"\b[A-Za-z][a-z]{2,}\b")
LETTER = re.compile(r"[A-Za-z]")

# A numeral the scanner mangled. Nothing here is a guess: each is a
# letter shaped like the digit it was read as, and the reading is only
# ever accepted when the division it opens is the one the sequence
# expects anyway.
LOOKALIKE = str.maketrans({
    "I": "1", "l": "1", "i": "1", "|": "1",
    "O": "0", "o": "0", "D": "0", "a": "0",
    "S": "5", "s": "5", "b": "6", "g": "9", "B": "8", "Z": "2",
})


def numeral(text: str) -> int | None:
    """What the scanner's reading of a printed numeral comes to."""
    cleaned = arabic_clean(text)
    return int(cleaned) if cleaned.isdigit() else None


def arabic_clean(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z|]", "", text).translate(LOOKALIKE)


# Schodde numbers his canons in roman, so the same machinery has to read
# roman. The lookalikes differ: what a scanner makes of an I is not what
# it makes of a 1.
ROMAN_LOOKALIKE = str.maketrans({
    "1": "I", "|": "I", "!": "I", "J": "I", "T": "I",
    "0": "O", "U": "V", "Y": "V",
})
ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman_clean(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z|!]", "", text).upper().translate(ROMAN_LOOKALIKE)


def roman(text: str) -> int | None:
    """The value of a roman numeral, or None if it is not one."""
    cleaned = roman_clean(text)
    if not cleaned or any(c not in ROMAN_VALUES for c in cleaned):
        return None
    total = 0
    for i, c in enumerate(cleaned):
        value = ROMAN_VALUES[c]
        after = [ROMAN_VALUES[d] for d in cleaned[i + 1:]]
        total += -value if after and max(after) > value else value
    return total or None


def to_roman(value: int) -> str:
    out = []
    for figure, letters in ((100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
                            (10, "X"), (9, "IX"), (5, "V"), (4, "IV"),
                            (1, "I")):
        while value >= figure:
            out.append(letters)
            value -= figure
    return "".join(out)


# How a printing numbers its divisions: how to read one, how to write the
# one that is expected, and how to strip a reading down to the characters
# the two can be compared on.
ARABIC = (numeral, str, arabic_clean)
ROMAN = (roman, to_roman, roman_clean)


def resembles(printed: str, expected: int, style=ARABIC) -> bool:
    """Is this the expected numeral, allowing for one bad character?

    The order of the divisions is the authority -- they were printed in
    order and the scan cannot reorder them -- so the printed numeral is a
    check on the reading rather than the source of it. Accepting a
    one-character difference is what lets "88" be read as the 38 it is
    without pretending the scan said 38.
    """
    read, write, clean = style
    if read(printed) == expected:
        return True
    seen, want = clean(printed), write(expected)
    # One character out of one is not a misreading, it is a different
    # number: "4" would otherwise be accepted as the 3 that went missing
    # before it, and every division after would be labelled wrong.
    if len(want) < 2 or len(seen) != len(want):
        return False
    return sum(a != b for a, b in zip(seen, want)) <= 1


def divisions(paragraphs, pattern, expect, report, style=ARABIC, gaps=0):
    """Find the printed divisions in order, and cut the prose on them.

    `expect` yields the numeral each division should carry. A candidate
    that carries a different one is not a division: in James the same
    shape is a footnote mark standing in the running text, and in Horner
    it is a chapter reference. Reading the sequence rather than the shape
    is what tells them apart.

    `gaps` is how many expected divisions may be passed over at once. The
    scanner lost two of Schodde's headings outright -- there is no
    "Canon XXX" anywhere in the leaf -- and their text runs on inside the
    canon before them, exactly as three of Platt's do in the Didascalia.
    Passing over one is only allowed when the *next* heading is found, so
    a lost heading costs a division and never a word; which ones were
    lost comes back so the work can say so.
    """
    flat = "\n\n".join(paragraphs)
    wanted = list(expect)
    found, missing, i = [], [], 0
    for m in pattern.finditer(flat):
        if i >= len(wanted):
            break
        exact = style[0](m.group(1))
        # A reading that is itself a number still to come is taken at its
        # word and never mended. "12" differs from "11" by one character
        # and is the twelfth chapter, not a misprint of the eleventh; the
        # mending is for "88", which is no chapter at all.
        ahead = exact is not None and exact in wanted[i:]
        for j in range(i, min(i + 1 + gaps, len(wanted))):
            if exact == wanted[j] or (not ahead
                                      and resembles(m.group(1), wanted[j],
                                                    style)):
                if exact != wanted[j]:
                    report.append((m.group(1), wanted[j]))
                missing.extend(wanted[i:j])
                found.append((m.start(), wanted[j], m.end() - m.start()))
                i = j + 1
                break
    if i < len(wanted):
        missing.extend(wanted[i:])
    if len(found) < len(wanted) - 3 * (gaps + 1):
        raise SystemExit(f"  ERROR: found {len(found)} of {len(wanted)} "
                         f"divisions; the first missing is "
                         f"{missing[0] if missing else '?'}")
    return flat, found, missing


SMALL_WORDS = {"of", "for", "the", "a", "an", "and"}


def titled(heading: str) -> str:
    """Horner's headings are set in capitals; a label is not shouted."""
    words = " ".join(heading.split()).lower().split()
    return " ".join(w if i and w in SMALL_WORDS else w.capitalize()
                    for i, w in enumerate(words))


def paragraphs_of(chunk: str) -> list:
    """Back to paragraphs, dropping anything with no letters in it.

    What that drops is the printer's signature marks -- a bare "9" or
    "13" at the foot of a gathering -- which sit low enough on the leaf
    to look like text and carry nothing.
    """
    out = []
    for para in chunk.split("\n\n"):
        para = para.strip()
        if para and LETTER.search(para):
            out.append(para)
    return out


# ---- the Sinodos ------------------------------------------------------

# Horner sets the number and the subject of each statute in the running
# text rather than over it, so the division and its title arrive as one
# sentence: "Statute 14. Concerning the ordination of a Bishop. If it
# should be a deacon..." The number is what cuts, and the sentence after
# it is the title where there is one -- statutes 1 to 13 have none,
# opening straight into "Said Yuhanes".
STATUTE = re.compile(r"\bStatute\s+(\S+(?:\s+\d[.,*]?)?)")
# A one-letter word inside a heading -- "PRAYER FOR THOSE WHO MAKE A
# JOURNEY" -- but never at the end of one, which is what keeps the run
# from swallowing the "And" that opens the prayer itself.
PRAYER = re.compile(
    r"\bPRAYER\s+(?:OF|FOR)\s+(?:[A-Z][A-Z']*\s+)*[A-Z][A-Z']+")
TITLED = re.compile(r"^(Concerning\b|That\b|Of\b)[^.]*\.")

# Horner numbers two consecutive statutes 40. It is his numbering -- the
# second is headed "Concerning the fruit which it is seemly to offer" --
# and it is kept, because renumbering it would silently disagree with
# every citation of his edition.
STATUTES = list(range(1, 40)) + [40, 40] + list(range(41, 73))


def sinodos(report):
    paragraphs, pages = scans.read_recovered(
        os.path.join(RAW, "sinodos-horner-1904.txt"))
    prose = scans.prose(paragraphs, report["hyphens"])
    flat, found, _missing = divisions(prose, STATUTE, STATUTES,
                                      report["numerals"])

    chapters = []

    def add(raw, numeral_, chunk):
        paras = paragraphs_of(chunk)
        if not paras:
            return
        chapters.append({
            "label": f"Section {len(chapters) + 1}",
            "n": len(chapters) + 1,
            "raw": raw,
            "numeral": numeral_,
            "paras": paras,
            "style": "prose",
        })

    add("The Sinodos of the fathers, the Apostles", None, flat[:found[0][0]])

    seen = {}
    for i, (at, number, head_len) in enumerate(found):
        end = found[i + 1][0] if i + 1 < len(found) else len(flat)
        chunk = flat[at:end]
        seen[number] = seen.get(number, 0) + 1
        printed = f"Statute {number}"
        if seen[number] > 1:
            printed += " (the second so numbered)"
        rest = chunk[head_len:].lstrip(" .,*\n")
        raw = printed
        head = TITLED.match(rest)
        if head:
            # Horner runs the speaker straight on from the heading, and
            # where the scan lost the stop between them the "title" runs
            # into the statute. "Said" is his own marker for the one and
            # never opens the other.
            title = re.split(r"\s+Said\s", head.group(0))[0].rstrip(" .,;")
            if len(title) <= 170:
                raw = f"{printed}. {title}"

        # The prayers are printed on from the last statute with headings
        # of their own, and are divisions of the same kind.
        prayers = list(PRAYER.finditer(chunk))
        add(raw, number, chunk[:prayers[0].start()] if prayers else chunk)
        for j, m in enumerate(prayers):
            stop = prayers[j + 1].start() if j + 1 < len(prayers) else len(chunk)
            add(titled(m.group(0)), None, chunk[m.start():stop])

    report["pages"] = pages
    return chapters


# ---- The Rest of the Words of Baruch ----------------------------------

# Issaverdens prints no divisions at all, so this volume adds none. The
# nine chapters the work is cited by are a modern editor's and belong to
# the Greek text; imposing them on a different recension, by matching
# what looks like the right sentence, would be an editorial claim
# dressed as a transcription.
BARUCH_OPENS = "And it came to pass when the children"


def baruch(report):
    paragraphs, pages = scans.read_recovered(
        os.path.join(RAW, "4-baruch-issaverdens-1901.txt"))
    prose = scans.prose(paragraphs, report["hyphens"])
    flat = "\n\n".join(prose)
    at = flat.index(BARUCH_OPENS)
    report["pages"] = pages
    return [{
        "label": "The whole",
        "n": 1,
        "raw": "From the Book of Paralipomena, which I found in the Books "
               "of the Greeks",
        "numeral": None,
        "paras": paragraphs_of(flat[at:]),
        "style": "prose",
    }]


# ---- The Book of the Covenant -----------------------------------------

# James numbers the sections 1 to 51 in the running text. The same shape
# appears in it as a footnote mark, so the number alone will not do; the
# sequence is what tells them apart.
COVENANT = re.compile(r"(?<![\w.])(\d{1,2})\s+(?=[A-Z(])")
COVENANT_OPENS = "1 The book which Jesus Christ revealed"


def covenant(report):
    paragraphs, pages = scans.read_recovered(
        os.path.join(RAW, "book-of-the-covenant-james-1924.txt"))
    prose = scans.prose(paragraphs, report["hyphens"])
    flat = "\n\n".join(prose)
    # James's own introduction stands above the text on the same leaf.
    flat = flat[flat.index(COVENANT_OPENS):]

    _, found, _missing = divisions([flat], COVENANT, range(1, 52),
                                   report["numerals"])
    chapters = []
    for i, (at, number, head_len) in enumerate(found):
        end = found[i + 1][0] if i + 1 < len(found) else len(flat)
        chapters.append({
            "label": f"Section {number}",
            "n": number,
            "raw": None,
            "numeral": str(number),
            "paras": paragraphs_of(flat[at + head_len:end]),
            "style": "prose",
        })
    report["pages"] = pages
    return chapters


# ---- repairing what the scanner misread -------------------------------
#
# These three scans are the two thousands and the nineteen hundreds
# respectively, and it shows. Issaverdens's is the worst: his printing
# has a thin y and the scanner reads it as a v, so "they" comes through
# as "thev" and "Babylon" as "Babvlon", a hundred and forty times over.
#
# The repairs below are derived rather than tabulated. A token is
# considered only when this volume's own million and a half words have
# never seen it; a repair is only ever a substitution the scanner is
# known to make; and it is only accepted when exactly one such
# substitution turns the token into a word the volume does know. Two
# candidate words and it is left alone, because a coin toss inside
# scripture is worse than a visible misprint.
#
# What that fixes is the systematic failures. What it leaves is the long
# tail -- "tchick" for "which", "iifrieved" for "grieved" -- which is
# left standing and counted on the work's own page, because a reader who
# can see the scanner failed can allow for it, and a reader shown a
# confident guess cannot.

CONFUSIONS = [
    ("v", "y"), ("y", "v"),         # a thin y, and the reverse
    ("li", "h"), ("h", "li"),       # a broken h
    ("ii", "n"), ("rn", "m"),       # letters run together
    ("t", "f"), ("f", "t"),         # a worn crossbar
    ("c", "e"), ("e", "c"),
    ("i", "l"), ("l", "i"),
    ("u", "n"), ("n", "u"),
    ("1", "l"), ("0", "o"), ("j", "y"),
]

TOKEN = re.compile(r"[A-Za-z][A-Za-z'-]*")


def vocabulary(path: str) -> set:
    """Every word this volume already prints, as the test of a repair.

    A million and a half words of the same register as these texts, which
    is a better authority for them than a modern dictionary would be: it
    knows "thou shalt" and "Yahweh" and does not know "email".
    """
    words = set()
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            for word in TOKEN.findall(line):
                words.add(word.lower())
    return words


def mend(token: str, words: set, confusions) -> str | None:
    """The one repair that makes this token a word, if there is one.

    Hyphens are left exactly as the scan has them. Closing one up would
    mend "eag-le" into "eagle", and would also turn James's "oft-times"
    into "ofttimes", which is not a repair but a change to what he
    printed. A word genuinely broken across a line break was already put
    back together when the printed lines were joined into prose; a
    hyphen surviving into the middle of a line is either the
    translator's or the scanner's, and this cannot tell which.
    """
    if token.lower() in words or len(token) < 2:
        return None
    found = set()
    for bad, good in confusions:
        start = 0
        while True:
            at = token.find(bad, start)
            if at < 0:
                break
            candidate = token[:at] + good + token[at + len(bad):]
            if candidate.lower() in words:
                found.add(candidate)
            start = at + 1
    return found.pop() if len(found) == 1 else None


def repair(text: str, words: set, confusions, report) -> str:
    """Mend what can be mended, and count what cannot."""
    def one(match):
        token = match.group(0)
        fixed = mend(token, words, confusions)
        if fixed:
            report["repairs"][(token, fixed)] = \
                report["repairs"].get((token, fixed), 0) + 1
            return fixed
        if token.lower() not in words:
            report["unmended"][token] = report["unmended"].get(token, 0) + 1
        return token
    return TOKEN.sub(one, text)


# ---- the Apostolic Canons, the second part of the Sinodos -------------

CANON = re.compile(r"\bCanon\s+([IVXLC][IVXLC0-9.,]*)")
CANONS_OPEN = "In the name of the Father and the Son"
CANONS = list(range(1, 58))


def canons(report):
    paragraphs, pages = scans.read_recovered(
        os.path.join(RAW, "apostolic-canons-schodde-1885.txt"))
    prose = scans.prose(paragraphs, report["hyphens"])
    flat = "\n\n".join(prose)
    # Schodde's own introduction stands above his translation.
    flat = flat[flat.index(CANONS_OPEN):]

    _, found, missing = divisions([flat], CANON, CANONS, report["numerals"],
                                  style=ROMAN, gaps=3)
    report["missing"] = [to_roman(n) for n in missing]
    report["pages"] = pages

    chapters = []

    def add(raw, numeral_, chunk):
        paras = paragraphs_of(chunk)
        if not paras:
            return
        chapters.append({
            "label": f"Section {len(chapters) + 1}",
            "n": len(chapters) + 1,
            "raw": raw,
            "numeral": numeral_,
            "paras": paras,
            "style": "prose",
        })

    add("The Synod of the Christian Church, which the Apostles gave "
        "through the hand of Clemens", None, flat[:found[0][0]])
    for i, (at, number, head_len) in enumerate(found):
        end = found[i + 1][0] if i + 1 < len(found) else len(flat)
        chunk = flat[at:end]
        rest = chunk[head_len:].lstrip(" .,*\n")
        head = TITLED.match(rest)
        raw = f"Canon {to_roman(number)}"
        if head:
            title = head.group(0).rstrip(" .,;")
            if len(title) <= 170:
                raw = f"{raw}. {title}"
        add(raw, number, chunk)
    return chapters


# ---- the church order of the Book of the Covenant ---------------------

CHAPTER = re.compile(r"\bCHAPTER\s+(\S+)")
TESTAMENT_OPEN = "Ir came to pass, after our Lord rose from the dead"
TESTAMENT_SECOND = "THE SECOND BOOK OF CLEMENT"


def testament(report):
    paragraphs, pages = scans.read_recovered(
        os.path.join(RAW, "testament-of-our-lord-cooper-maclean-1902.txt"))
    prose = scans.prose(paragraphs, report["hyphens"])
    flat = "\n\n".join(prose)
    flat = flat[flat.index(TESTAMENT_OPEN):]
    at = flat.index(TESTAMENT_SECOND)
    books = [("I", flat[:at], 47), ("II", flat[at:], 27)]

    chapters, missing = [], []
    for book, text, last in books:
        _, found, gone = divisions([text], CHAPTER, range(1, last + 1),
                                   report["numerals"], gaps=3)
        missing += [f"{book}. {n}" for n in gone]
        head = text[:found[0][0]] if found else text
        if paragraphs_of(head):
            chapters.append({
                "label": f"{book}. opening",
                "n": len(chapters) + 1,
                "raw": f"Book {book}, and what stands before its first chapter",
                "numeral": None,
                "paras": paragraphs_of(head),
                "style": "prose",
            })
        for i, (start, number, head_len) in enumerate(found):
            end = found[i + 1][0] if i + 1 < len(found) else len(text)
            chapters.append({
                "label": f"{book}. {number}",
                "n": len(chapters) + 1,
                "raw": None,
                "numeral": number,
                "paras": paragraphs_of(text[start + head_len:end]),
                "style": "prose",
            })
    report["missing"] = missing
    report["pages"] = pages
    return chapters


# ---- the Apocalypse of Peter, out of the Books of Clement -------------

CLEMENT_OPEN = "The Second Coming of Christ and Resurrection of the Dead"
CLEMENT_END = "There is a great deal more of the Ethiopic text"


def clement(report):
    paragraphs, pages = scans.read_recovered(
        os.path.join(RAW, "ethiopic-clement-james-1924.txt"))
    prose = scans.prose(paragraphs, report["hyphens"])
    flat = "\n\n".join(prose)
    # James prints his study of the book, then the Greek fragment, then
    # this. Only the last of the three is the Ethiopic.
    flat = flat[flat.index(CLEMENT_OPEN):flat.index(CLEMENT_END)]
    report["pages"] = pages
    return [{
        "label": "The whole",
        "n": 1,
        "raw": "The Second Coming of Christ and Resurrection of the Dead, "
               "which Christ revealed unto Peter",
        "numeral": None,
        "paras": paragraphs_of(flat),
        "style": "prose",
    }]


# ---- the three works --------------------------------------------------

RECOVERED = (
    "Every biblical book in this volume is checked verse for verse "
    "against independent reference counts. None exist for this text, so "
    "there is nothing to check it against but the scan itself, and it is "
    "marked unverified for that reason. Read it as a text recovered "
    "rather than as a text verified."
)

WORKS = [
    {
        "id": "the-sinodos",
        "title": "THE SINODOS",
        "section": "the-apostolic-fathers",
        "source": "horner",
        "build": sinodos,
        "confusions": [("li", "h")],
        "note": [
            "One of the five books of the Ethiopian canon this volume listed "
            "as absent. The Ge'ez has been public domain for centuries; what "
            "was scarce was an English translation old enough to be public "
            "domain too. Horner printed one in 1904, with the Ge'ez and his "
            "English in the same volume, to argue about where the eighth book "
            "of the Apostolic Constitutions came from.",
            "What is here is the Statutes of the Apostles, which is the "
            "largest part of the Ethiopic Sinodos and not the whole "
            "collection: the Sinodos is a body of canon law, and Horner "
            "printed and translated this part of it. The text opens by naming "
            "itself — “This is the Sinodos of the fathers, the "
            "Apostles” — and the divisions, the numbers and the "
            "titles below are his.",
            "Horner numbers two consecutive statutes 40. That is his edition, "
            "not a fault in this reading of it, and it is kept so that a "
            "citation of him still lands where he put it.",
            RECOVERED,
        ],
    },
    {
        "id": "the-apostolic-canons",
        "title": "THE APOSTOLIC CANONS",
        "section": "the-apostolic-fathers",
        "source": "schodde",
        "build": canons,
        "confusions": [],
        "note": [
            "The second part of the Sinodos this volume has. Schodde "
            "translated the Ge'ez of the fifty-seven Apostolic Canons for "
            "the Society of Biblical Literature in 1885 and said in his "
            "introduction what they are: “The Canons constitute a "
            "part of the so-called Synodus of this church, which is for "
            "them virtually a Corpus Juris Ecclesiastici.”",
            "Canon LV is the Ethiopian church's own list of its "
            "scriptures, and it names the three books of Kufalé — "
            "Jubilees — among them. A canon list inside a canon book, "
            "in a volume arranged around the question of who counts what.",
            RECOVERED,
        ],
    },
    {
        "id": "the-testament-of-our-lord",
        "title": "THE TESTAMENT OF OUR LORD",
        "section": "the-apostolic-fathers",
        "source": "cooper",
        "build": testament,
        "confusions": [],
        "note": [
            "The church order that in Ge'ez is the first book of the "
            "Mets'hafe Kidan, the Book of the Covenant of the Ethiopian "
            "canon: the risen Lord, before his ascension, laying down how "
            "the church is to be built, who may be ordained, how the "
            "eucharist and baptism are to be done, and what a bishop owes "
            "the poor. It opens with an apocalypse and closes with the "
            "apostles sending copies out of Jerusalem.",
            "This is not the Ge'ez. Cooper and Maclean translated the "
            "Syriac, and say in the same book that the Ethiopic version was "
            "then unpublished; it has no public-domain English now either. "
            "What is printed here is a witness to the same work in another "
            "version, which is a different thing from the version the "
            "Ethiopian church reads, and this paragraph exists to say so.",
            "The chapters are theirs, in the two books they print.",
            RECOVERED,
        ],
    },
    {
        "id": "the-apocalypse-of-peter",
        "title": "THE APOCALYPSE OF PETER",
        "section": "new-testament-apocrypha",
        "before": "the-gospel-of-pseudo-matthew",
        "source": "james",
        "build": clement,
        "confusions": [],
        "note": [
            "The Ethiopic Apocalypse of Peter, which survives inside "
            "Qalementos — the Ethiopic Books of Clement, one of the "
            "five books of the Ethiopian canon this volume listed as "
            "absent. Peter asks the Lord on the Mount of Olives for the "
            "signs of his coming and is shown the end of the world, the "
            "punishments of hell and the garden of the righteous. It was "
            "read as scripture in Rome in the second century, and the "
            "Muratorian Canon lists it beside the Apocalypse of John.",
            "It is a part of Qalementos and not the book. Six of the seven "
            "books of the Ethiopic Clement have no public-domain English "
            "translation at all, and James took even this one only as far "
            "as the point where he judged the rest of the Ethiopic late, "
            "saying so and stopping. The canon table counts the book as "
            "here in part for that reason, and says which part.",
            "Where the text carries a section number from the Greek "
            "fragment rather than from the Ethiopic, James set it as a "
            "label in the margin — “Gr. 22.” and so on — and "
            "those are his and are left where he put them.",
            RECOVERED,
        ],
    },
    {
        "id": "the-rest-of-the-words-of-baruch",
        "title": "THE REST OF THE WORDS OF BARUCH",
        "section": "section-ix-new-testament-writings",
        "source": "issaverdens",
        "build": baruch,
        "confusions": [("v", "y"), ("li", "h"), ("t", "f"), ("nn", "u")],
        "note": [
            "4 Baruch, the Paraleipomena Jeremiou, which the Ethiopian canon "
            "receives as The Rest of the Words of Baruch. Jerusalem falls, "
            "Jeremiah goes into exile with the people, and Abimelech the "
            "Ethiopian sleeps sixty-six years under a tree with a basket of "
            "figs that do not spoil.",
            "This is not the Ge'ez. No public-domain English translation of "
            "the Ge'ez exists — the standard modern one is in copyright, "
            "and Rendel Harris's 1889 edition, the earliest in English, "
            "prints the Greek text with a study of it and translates "
            "nothing. What is printed here is the Armenian recension, in the "
            "English Issaverdens published at Venice in 1901, and it is the "
            "one he says was made from the Greek that the Ge'ez also "
            "descends from. It is a witness to this work in another version, "
            "which is a different thing from the version the Ethiopian church "
            "reads, and saying so is the point of this paragraph.",
            "Issaverdens prints no chapter divisions, so this volume adds "
            "none. The nine chapters the work is usually cited by belong to "
            "the Greek text; ruling them onto a different recension by "
            "matching what looked like the right sentence would be an "
            "editorial claim wearing the clothes of a transcription.",
            RECOVERED,
        ],
    },
    {
        "id": "the-book-of-the-covenant",
        "title": "THE BOOK OF THE COVENANT",
        "section": "new-testament-apocrypha",
        "before": "the-acts-of-paul-and-thecla",
        "source": "james",
        "build": covenant,
        "confusions": [("v", "y")],
        "note": [
            "The second book of the Mets'hafe Kidan, the Book of the Covenant "
            "of the Ethiopian canon: the discourse of the risen Lord to the "
            "eleven, which circulates elsewhere as the Epistle of the "
            "Apostles. Guerrier published the Ethiopic as the Testament of "
            "our Lord in Galilee, and M. R. James rendered it into English in "
            "1924 from that Ethiopic and from Schmidt's Coptic beside it.",
            "The Book of the Covenant is in two parts and this is the second "
            "of them. The first, sixty sections of church order, has no "
            "public-domain English translation of any version, so the book is "
            "here in part and the coverage table says so rather than "
            "counting it complete.",
            "The section numbers are James's. Where his text carries a "
            "reading from the Coptic or the Latin rather than the Ethiopic he "
            "says so in the running text, and those remarks are his and are "
            "left where he put them.",
            RECOVERED,
        ],
    },
]


def build(spec, words):
    report = {"hyphens": [], "numerals": [], "repairs": {}, "unmended": {},
              "pages": [], "missing": []}
    chapters = spec["build"](report)
    for chapter in chapters:
        chapter["paras"] = [repair(p, words, spec["confusions"], report)
                            for p in chapter["paras"]]

    note = list(spec["note"])
    left = sum(report["unmended"].values())
    mended = sum(report["repairs"].values())
    if mended:
        note.append(
            f"The scanner's reading was mended in {mended} "
            f"{'place' if mended == 1 else 'places'}. A word "
            "is only mended when this volume's own million and a half words "
            "have never seen it, when the change is a substitution this "
            "scanner is known to make, and when exactly one such change "
            "turns it into a word the volume does know. Two candidates and "
            "it is left as it is, because a visible misprint is better than "
            "a confident guess.")
    if left:
        note.append(
            f"{left} words here appear nowhere else in this volume and were "
            "left exactly as the scan has them"
            + (", mended or not." if mended else ", and nothing was mended.")
            + " Most of them are not mistakes at all — they are words "
            "this library simply never uses elsewhere, and the Ge'ez forms "
            "of names — and the rest are the scanner's worst pages, left "
            "visible rather than smoothed over.")
    if report.get("missing"):
        note.append(
            "The scan lost " + str(len(report["missing"]))
            + " of the printed headings outright, so "
            + ", ".join(str(m) for m in report["missing"])
            + " get no division of their own and their text reads on inside "
              "the one before. The words are all here; the breaks are not.")
    if report["numerals"]:
        note.append(
            "The scan misread " + ", ".join(
                f"{printed} for {wanted}" for printed, wanted in
                report["numerals"])
            + ". Each was accepted because the divisions run in the printed "
              "order and the sequence says which one this is, not because "
              "the shape was read twice.")

    work = {
        "id": spec["id"],
        "title": spec["title"],
        "section": spec["section"],
        "note": note,
        "chapters": chapters,
        "source": spec["source"],
        "verified": False,
    }
    stance = dates.enrich(POSITIONS.get(spec["id"]))
    if stance:
        work["positions"] = stance
    return work, report


def place(section, entry, before):
    """Put the work where its date puts it, not always at the end."""
    if before:
        for i, w in enumerate(section["works"]):
            if w["id"] == before:
                section["works"].insert(i, entry)
                return
    section["works"].append(entry)


def main() -> int:
    global OUT, RAW
    if len(sys.argv) > 1:
        OUT = sys.argv[1]
    if len(sys.argv) > 2:
        RAW = sys.argv[2]
    words = vocabulary(sys.argv[3] if len(sys.argv) > 3 else SRC)

    manifest_path = os.path.join(OUT, "manifest.json")
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)

    os.makedirs(os.path.join(OUT, "works"), exist_ok=True)
    for spec in WORKS:
        work, report = build(spec, words)

        section = next((s for s in manifest["sections"]
                        if s["id"] == spec["section"]), None)
        if section is None:
            print(f"  ERROR: no section {spec['section']} in the manifest")
            return 1

        with open(os.path.join(OUT, "works", spec["id"] + ".json"), "w",
                  encoding="utf-8") as fh:
            json.dump(work, fh, ensure_ascii=False, separators=(",", ":"))

        count = sum(len(WORD.findall(" ".join(c["paras"])))
                    for c in work["chapters"])
        if not any(w["id"] == spec["id"] for w in section["works"]):
            place(section, {
                "id": spec["id"],
                "title": work["title"],
                "note": work["note"],
                "chapters": len(work["chapters"]),
                "verses": 0,
                "words": count,
                "versified": False,
                "source": spec["source"],
                "positions": work.get("positions"),
                "chapterLabels": [c["label"] for c in work["chapters"]],
                "verified": False,
            }, spec.get("before"))

        print(f"  {spec['id']}: {len(work['chapters'])} sections, "
              f"{count:,} words, from {len(report['pages'])} leaves, "
              f"{sum(report['repairs'].values())} scan repairs, "
              f"recovered not audited")

    totals = {"works": 0, "chapters": 0, "verses": 0, "words": 0}
    for s in manifest["sections"]:
        for w in s["works"]:
            totals["works"] += 1
            totals["chapters"] += w["chapters"]
            totals["verses"] += w["verses"]
            totals["words"] += w["words"]
    totals["sections"] = len(manifest["sections"])
    manifest["totals"] = totals

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, separators=(",", ":"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
