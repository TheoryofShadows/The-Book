#!/usr/bin/env python3
"""Add the Ethiopic Didascalia from Platt's 1834 edition.

One of the five books of the Ethiopian canon this volume was missing. The
other four have no public-domain English translation; this one does -- Thomas
Pell Platt printed the Ge'ez with his English facing it for the Oriental
Translation Fund in 1834, and the scan is public domain by age.

What makes it awkward is the facing pages. The scanning engine had no Ge'ez,
so those pages come through as dense noise, interleaved block by block with
clean English. The English is separable: it is mostly letters and spaces and
carries real words, and the noise is neither. Everything below follows from
that one distinction.

WHAT IS AND IS NOT VERIFIED HERE

The text is recovered, not audited. The biblical books in this volume are
checked verse for verse against independent reference counts; no such counts
exist for the Ethiopic Didascalia, so there is nothing to check this against
except the scan itself. The work is marked verified: false for that reason,
and the reader is told so on the page. That is a weaker standard than the
rest of the library and it is labelled rather than hidden.

What *was* checked, because it is the failure that would matter most:

    No English is lost. Twenty-four page numbers failed to scan, which at
    first looks like two dozen missing pages. It is not. A page followed by
    a missing number carries twice the words of an ordinary page (432
    against 216), and the prose runs straight across the join -- page 4 ends
    "And if thou" and page 6 begins "hast committed adultery". The numbers
    failed; the pages did not. tests/python/test_didascalia.py holds that
    check so it cannot quietly stop being true.

SECTIONS

Platt set each section's heading in the running text, as a roman numeral and
a title, and those headings are the divisions used here. Cutting on them is
exact.

The first attempt cut on the page each section opens on, taken from his table
of contents, and that is only accurate to the page: a section beginning
halfway down one opened with the tail of the section before it. "Of Widows"
began "runner. But if thou be not slothful" -- a page of sloth before the
first widow -- and it went out to the live site that way.

Three of his headings did not survive the scan and get no division: XII "Of
Widows", XV, and XVII "Concerning Orphans". Their text reads on inside the
section before. The numerals themselves needed repair before the cut could
be made -- he set "VII." and the scan read "VIL" -- which is why the repairs
below run first.
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dates                                            # noqa: E402
from positions import POSITIONS                         # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/data"
RAW = sys.argv[2] if len(sys.argv) > 2 else "source/extra"
SCAN = "didascalia-platt-1834.txt"

WORK_ID = "the-ethiopic-didascalia"
SECTION = "the-apostolic-fathers"

WORD = re.compile(r"\b[A-Za-z][a-z]{2,}\b")
# A page number sits alone on its line, sometimes behind a signature mark.
PAGE = re.compile(r"^\s*(?:[a-z0-9]{1,3}\s+)?(\d{1,3})\s*$")

PREAMBLE = "Of the Apostles' ordinance, and the degrees of the Church"

# A distinctive phrase out of each of Platt's section headings, as the scan
# left it. Each is checked to occur exactly once in the recovered text.
HEADINGS = [
    ("I", "the duty of the Rich to search"),
    ("II", "the duty of Women to obey"),
    ("III", "Concerning the Bishop, the Priest, and the Deacon"),
    ("IV", "Concerning the duty of Bishops to receive the repentance"),
    ("V", "not lawful for us to enforce discipline"),
    ("VI", "the duty of the people to bring offerings"),
    ("VII", "not lawful for the Deacon to do any thing"),
    ("VIII", "the duty of the Bishop to try and inquire"),
    ("IX", "Christians ought to forgive the trespasses"),
    ("X", "Bishops to be peace-makers"),
    ("XI", "not lawful for Christians to enter into the assemblies"),
    # XII, "Of Widows", is absent too: the only "Of Widows" the scan left is
    # running text about the observance of widows, and cutting there put a
    # section boundary in the middle of a sentence.
    # "not lawful for Women to baptize" alone appears twice -- the heading
    # and a restatement a page later. The capital W pins the heading.
    ("XIII", "not lawful for Women to baptize. Behold"),
    ("XIV", "not lawful for the Layman to do any work"),
    ("XVI", "do evil against your neighbours"),
    # XVI, "Concerning Orphans", is absent: its heading did not survive the
    # scan, so its text reads on inside the section before it.
    ("XVIII", "provide for Widows and Orphans"),
    ("XIX", "Unmarried Women, and Widows"),
    ("XX", "discreet in receiving offerings"),
    ("XXI", "Fathers to keep their Children"),
    ("XXII", "Servants that they be subject"),
]

TITLES = {
    "I": "That it is the duty of the Rich to search into the profit of the Scriptures at all times",
    "II": "That it is the duty of Women to obey their Husbands, and to walk in wisdom and virtue",
    "III": "Of Bishops, Priests, and Deacons",
    "IV": "Concerning the duty of Bishops to receive the repentance of those who turn, in love and meekness",
    "V": "That it is not lawful for us to enforce discipline against any man, unless testimony be established against him",
    "VI": "Concerning the duty of the people to bring offerings to the Church, according to their ability",
    "VII": "That it is not lawful for the Deacon to do any thing but by authority of the Bishop",
    "VIII": "That it is the duty of the Bishop to try and inquire into every matter in justice and uprightness",
    "IX": "That Christians ought to forgive the trespasses of their neighbours",
    "X": "It is the duty of Bishops to be peace-makers, merciful, pardoning him who hath transgressed against them",
    "XI": "That it is not lawful for Christians to enter into the assemblies of the Heathen",
    "XII": "Of Widows",
    "XIII": "That it is not lawful for Women to baptize",
    "XIV": "That it is not lawful for the Layman to do any work belonging to the Priesthood",
    "XVI": "That it is not lawful that ye should do evil against your neighbours",
    "XVII": "Concerning Orphans",
    "XV": "a title the scan did not preserve either",
    "XII": "Of Widows",
    "XVIII": "That it is required of Bishops to provide for Widows and Orphans",
    "XIX": "That it is required of the Unmarried Women, and Widows, that they receive that which is bestowed upon them thankfully",
    "XX": "That it is required of Bishops to be discreet in receiving offerings from those only who are worthy",
    "XXI": "That it is required of Fathers to keep their Children under discipline",
    "XXII": "That it is required of Servants that they be subject unto their Masters in all purity",
}

# Platt's table of contents, by his own numbering. Used only to report which
# of his headings the scan failed to preserve -- the divisions themselves are
# cut from the headings in the text, not from this.
TOC = [
    ("I", "the duty of the Rich"), ("II", "the duty of Women"),
    ("III", "Bishops, Priests, and Deacons"),
    ("IV", "Bishops to receive the repentance"),
    ("V", "not lawful to enforce discipline"),
    ("VI", "the people to bring offerings"), ("VII", "not lawful for the Deacon"),
    ("VIII", "the Bishop to try and inquire"),
    ("IX", "Christians ought to forgive"), ("X", "Bishops to be peace-makers"),
    ("XI", "not lawful to enter the assemblies of the Heathen"),
    ("XII", "Of Widows"), # "not lawful for Women to baptize" alone appears twice -- the heading
    # and a restatement a page later. The capital W pins the heading.
    ("XIII", "not lawful for Women to baptize. Behold"),
    ("XIV", "not lawful for the Layman"), ("XV", "not to do evil against your neighbours"),
    ("XVI", "Concerning Orphans"), ("XVII", "provide for Widows and Orphans"),
    ("XVIII", "the Unmarried Women and Widows"),
    ("XIX", "Bishops to be discreet in receiving offerings"),
    ("XX", "Fathers to keep their Children under discipline"),
    ("XXI", "Servants subject unto their Masters"),
    ("XXII", "Servants subject unto their Masters"),
]

# Kept for the page fallback and for the record of where each section opens.
SECTIONS = [
    (1, "Of the Apostles' ordinance, and the degrees of the Church"),
    (8, "That it is the duty of the Rich to search into the profit of the "
        "Scriptures at all times"),
    (12, "That it is the duty of Women to obey their Husbands, and to walk "
         "in wisdom and virtue"),
    (16, "Of Bishops, Priests, and Deacons"),
    (34, "Concerning the duty of Bishops to receive the repentance of those "
         "who turn, in love and meekness"),
    (47, "That it is not lawful for us to enforce discipline against any "
         "man, unless testimony be established against him"),
    (60, "Concerning the duty of the people to bring offerings to the "
         "Church, according to their ability"),
    (66, "That it is not lawful for the Deacon to do any thing but by "
         "authority of the Bishop"),
    (73, "That it is the duty of the Bishop to try and inquire into every "
         "matter in justice and uprightness"),
    (88, "That Christians ought to forgive the trespasses of their "
         "neighbours, and not let revenge dwell in their hearts"),
    (90, "It is the duty of Bishops to be peace-makers, merciful, pardoning "
         "him who hath transgressed against them"),
    (105, "Of Widows"),
    (114, "That it is not lawful for Women to baptize"),
    (115, "That it is not lawful for the Layman to do any work belonging to "
          "the Priesthood"),
    (118, "That it is not lawful that ye should do evil against your "
          "neighbours"),
    (121, "Concerning Orphans"),
    (122, "That it is required of Bishops to provide for Widows and Orphans"),
    (124, "That it is required of the Unmarried Women, and Widows, that they "
          "receive that which is bestowed upon them thankfully"),
    (125, "That it is required of Bishops to be discreet in receiving "
          "offerings from those only who are worthy"),
    (129, "That it is required of Fathers to keep their Children under "
          "discipline"),
    (130, "That it is required of Servants that they be subject unto their "
          "Masters in all purity, whether they be faithful or unbelievers"),
]


ROMAN = {"I": 1, "V": 5, "X": 10}


def roman(text: str) -> int:
    """Platt numbers his sections I to XXII. Zero-based, to index SECTIONS."""
    total = prev = 0
    for ch in reversed(text.upper()):
        v = ROMAN.get(ch, 0)
        total += -v if v < prev else v
        prev = max(prev, v)
    return total - 1


def english(line: str) -> bool:
    """Platt's English, as against a line of OCR'd Ge'ez.

    The Ge'ez arrives as runs of colons, carets and stray capitals with
    almost no real words in them. Four words and four fifths letters is a
    wide enough gap to separate the two without guessing at either.
    """
    s = line.strip()
    if len(s) < 20 or len(WORD.findall(s)) < 4:
        return False
    # The colon is the Ge'ez separator, and the scan keeps it even where it
    # loses everything else. One line of Ge'ez cleared both tests above --
    # five of its fragments looked like words and it came to 0.802 letters
    # against a threshold of 0.80 -- and landed a run of noise in the middle
    # of a sentence about bloody assemblies. English prose uses at most one
    # colon in a line; that Ge'ez line carried eleven. Of the 2,323 English
    # lines in the translation, 134 use a colon and exactly one uses two.
    if s.count(":") > 1:
        return False
    return sum(c.isalpha() or c.isspace() for c in s) / len(s) > 0.80


def pages(text: str) -> dict[int, list[str]]:
    """{printed page number: its English lines}.

    The number is set at the foot of the page it belongs to, so the lines
    that *precede* a mark are that page's, not the next one's. Reading it
    the other way round shifts every page by one and silently drops the
    first: page 1 carries no number in this scan, and its text -- the
    Apostles' charge that opens the whole work -- sits before the first
    mark, where a forward-looking reader never reaches it.
    """
    lines = text.split("\n")
    # Platt's table of contents lists every section in English, which reads
    # exactly like body text and would otherwise be captured as page one.
    # The work itself opens with the Apostles naming themselves, so that is
    # the anchor -- a line of the text rather than a feature of the layout.
    start = next(i for i, l in enumerate(lines)
                 if "We  the  Twelve  Apostles" in l or "We the Twelve Apostles" in l)
    stop = next(i for i, l in enumerate(lines)
                if l.strip() == "NOTES." and i > 6000)

    out: dict[int, list[str]] = {}
    held: list[str] = []
    for line in lines[start:stop]:
        m = PAGE.match(line)
        if m:
            out.setdefault(int(m.group(1)), []).extend(held)
            held = []
        elif english(line):
            held.append(line.strip())
    if held:                       # the last page carries no closing mark
        out.setdefault(max(out) + 1 if out else 1, []).extend(held)
    return out


# Words the scan broke, and what Platt printed.
#
# Every one was found by listing the tokens that occur once or twice and
# reading each in context, not by running a spell-checker over the text: a
# corrector with a dictionary and no Greek would have "improved" half the
# proper nouns in the book. Three confusions account for nearly all of it --
# the ligature fi read as fii, the pair li read as h, and w read as vd, vn or
# vv -- and the handful left over are one-offs.
#
# The list is deliberately explicit rather than a set of patterns. A pattern
# that turns every "h" back into "li" would ruin "his" and "the"; a table
# only ever changes the words written in it, and every change is countable.
REPAIRS = {
    "afiiict": "afflict", "afiiicted": "afflicted",
    "deceitfiilness": "deceitfulness", "slothfiilness": "slothfulness",
    "Hfe": "Life", "hfe": "life",
    "Hke": "Like", "hke": "like",
    "Hkeness": "Likeness", "hkeness": "likeness",
    "accomphsh": "accomplish", "fooHshly": "foolishly",
    "suppHcation": "supplication", "supphcation": "supplication",
    "firsthng": "firstling", "trembhng": "trembling",
    "vdcked": "wicked", "vdlt": "wilt", "vdth": "with",
    "vdthout": "without", "vnth": "with", "vvdth": "with",
    "vmtten": "written",
    "finiit": "fruit", "fljdng": "flying", "murnmring": "murmuring",
    "oiir": "our", "yoixng": "young", "eveiy": "every",
    "sm‟ely": "surely", "Ufe": "life", "Uke": "like", "Uved": "lived",
    # The same w/u family, caught on a second pass over the repaired text.
    # Note that vm stands for un here and for w elsewhere, which is why this
    # is a table of words and not a table of letter substitutions.
    "vmderstand": "understand", "vmto": "unto", "likevdse": "likewise",
    "vnse": "wise", "vdse": "wise", "vdzards": "wizards", "vddow": "widow",
    # ll set as U, found on the live page rather than in the build.
    "aU": "all", "aUke": "alike", "coUyrium": "collyrium", "dweUing": "dwelling",
    "enUghtened": "enlightened", "foUoweth": "followeth", "fooUsh": "foolish",
    "hireUng": "hireling", "humiUty": "humility", "unbeUever": "unbeliever",
    "unbeUevers": "unbelievers", "wiU": "will",
    "Uvest": "livest", "Ups": "lips",
    # L set as I^, w as vp or vs^, and the ff ligature as fF or lFF.
    "I^ord": "Lord", "vporks": "works", "vpritten": "written",
    "ofFering": "offering", "oflFer": "offer",
    # Single-word wrecks, each read in context before being written down.
    "maiTiage": "marriage", "meiTy": "merry", "waJketh": "walketh",
    # Platt's roman numerals, scanned with a trailing L where he set "I."
    # These are repaired before the sections are cut, because the cut looks
    # for the numeral.
    "VIL": "VII.", "XVL": "XVI.", "XXL": "XXI.", "Thai": "That",
    "tnist": "trust", "Widotos": "Widows", "LaAV": "Law",
    "I^ord": "Lord", "aiad": "and",
    # Both wrecks at once: w read as vm, and the comma after it read as a
    # caret. Listed whole because the tokeniser sees it as one word.
    "vmtten^": "written,",
}
# One break spans two words: the heading of Platt's eleventh section, where
# "lawful for" was scanned as a single ruined token.
PHRASES = {
    "law/iiljbr": "lawful for",
    "th«?ir": "their",
    "any thing hut by authority": "any thing but by authority",
    "written^ saying": "written, saying",
    # Platt's own note that his manuscript is defective here. It is his
    # editorial voice, not the text, and it is worth keeping legible.
    "L' ^ Leaf is here lost from the MS. ]": "[ Leaf is here lost from the MS. ]",
    "^'the Lord": "the Lord",
    "vs^hich": "which",
    "repe?itance": "repentance",
    # Platt's own section heads, printed in the running text and scanned
    # badly. They are repaired before the sections are cut, because the cut
    # is made on them.
    "XXn. That it is required of' Servants that they he sulked":
        "XXII. That it is required of Servants that they be subject",
    "bejaitliful": "be faithful",
    "XIII, That it is not lawful": "XIII. That it is not lawful",
    # A run of scanned Ge'ez that reached the English before the colon test
    # above existed. Kept here as well so the repaired text is correct even
    # if the line is ever admitted again.
    "fl^: Yian: Viof-I': \"S^A: lni>: AiffV: AOA: I^flf: HHaA-T:: COrS^oxfi ": "",
}

repaired: dict[str, int] = {}


def repair(text: str) -> str:
    """Put back the words the scan broke, and count each one."""
    for bad, good in PHRASES.items():
        if bad in text:
            repaired[bad] = repaired.get(bad, 0) + text.count(bad)
            text = text.replace(bad, good)

    def one(m):
        bad = m.group(0)
        good = REPAIRS.get(bad)
        if good is None:
            return bad
        repaired[bad] = repaired.get(bad, 0) + 1
        return good

    # The caret has to be inside the token class: the scan reads Platt's L
    # as I^, and a tokeniser that stops at the caret splits "I^ord" into two
    # pieces that match nothing and leaves "I^ord Jesus Christ" on the page.
    return re.sub(r"[A-Za-z‟'^]+", one, text)


def prose(lines: list[str]) -> str:
    """A page's lines rejoined.

    The column hyphenates across line ends and the scan doubles every space.
    Both are the printing, not Platt.
    """
    t = " ".join(lines)
    t = re.sub(r"([a-z])-\s+([a-z])", r"\1\2", t)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    return repair(t.strip())


def main() -> int:
    path = os.path.join(RAW, SCAN)
    if not os.path.exists(path):
        print(f"  ERROR: {path} not found")
        return 1

    with open(path, encoding="utf-8", errors="replace") as fh:
        page = pages(fh.read())
    if not page:
        print("  ERROR: no pages recovered from the scan")
        return 1

    numbers = sorted(page)

    # Lay the whole translation out as one repaired string, remembering
    # where each printed page begins in it. The page offsets are the
    # fallback; Platt's own headings are the first choice.
    body = ""
    at_page = {}
    for n in numbers:
        if not page[n]:
            continue
        at_page[n] = len(body)
        body += ("" if not body else " ") + prose(page[n])

    # Platt set each section's heading in the running text, as a roman
    # numeral and the title. Cutting there is exact. Cutting on the page a
    # section opens on is only accurate to the page, and a section that
    # begins halfway down one opens with the tail of the section before it:
    # "Of Widows" began "runner. But if thou be not slothful", a page of
    # sloth before the first widow. The headings are repaired above, because
    # some of them are damaged and the cut is made on them.
    # Cut on Platt's headings, located by an explicit phrase each.
    #
    # Three attempts at deriving these with a pattern went wrong in three
    # different ways -- a numeral mapped onto the wrong list index, a fuzzy
    # title match that fired in several places, and a regex whose matches
    # swallowed the heading after them -- costing thousands of words each
    # time, once by loss and once by duplication. The phrases below are
    # checked to occur exactly once, in ascending order, by
    # tests/python/test_didascalia.py. An explicit table cannot drift.
    starts = []
    for num, phrase in HEADINGS:
        m = re.search(re.escape(phrase), body, re.I)
        if m is None:
            continue
        # Back up to the roman numeral that introduces the heading, so a
        # section opens on its own title rather than partway through it.
        window = body[max(0, m.start() - 130):m.start()]
        lead = None
        for r in re.finditer(r"(?<![A-Za-z])[IVX]{1,6}\.\s", window):
            lead = max(0, m.start() - 130) + r.start()
        starts.append((lead if lead is not None else m.start(), num, phrase))
    starts.sort()

    chapters = []
    spans = [(0, starts[0][0] if starts else len(body), None, PREAMBLE)]
    for i, (pos, num, phrase) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(body)
        spans.append((pos, end, num, TITLES[num]))

    for start, end, num, title in spans:
        text = body[start:end].strip()
        if not text:
            continue
        chapters.append({
            "label": f"Section {len(chapters) + 1}",
            "n": len(chapters) + 1,
            "raw": title,
            "numeral": num,
            "paras": [text],
            "style": "prose",
        })

    # What Platt numbered, against what the scan preserved. Derived from the
    # full table of titles rather than from the headings actually located,
    # or the ones that went missing would go unmentioned as well as unused.
    found = {n for _, n, _ in starts}
    unsplit = [(n, TITLES[n]) for n in TITLES if n not in found]
    unsplit.sort(key=lambda e: roman(e[0]))

    if len(chapters) < 15:
        print(f"  ERROR: only {len(chapters)} sections recovered")
        return 1

    words = sum(len(WORD.findall(" ".join(c["paras"]))) for c in chapters)
    work = {
        "id": WORK_ID,
        "title": "THE ETHIOPIC DIDASCALIA",
        "section": SECTION,
        "note": [
            "One of the five books of the Ethiopian canon this volume long "
            "listed as absent. The Ge'ez is public domain many times over; "
            "what was scarce was an English translation old enough to be "
            "public domain too. Thomas Pell Platt printed one in 1834, with "
            "the Ge'ez and the English on facing pages.",
            "Recovered from the scan of that printing, and not audited. "
            "Every biblical book here is checked verse for verse against "
            "independent reference counts; none exist for this text, so "
            "there is nothing to check it against but the scan itself. "
            "The sections are Platt's own, cut at the headings he set in "
            "the running text and carrying the numerals he printed. Read it "
            "as a text recovered rather than as a text verified.",
        ] + ([
            "Three of Platt's headings did not survive the scan, so they "
            "get no division of their own and their text reads on inside "
            "the section before: " + "; ".join(f"{n}, “{t}”"
                                               for n, t in unsplit)
            + ". The words are all here; the breaks are not."
        ] if unsplit else []),
        "chapters": chapters,
        "source": "platt",
        "verified": False,
    }

    os.makedirs(os.path.join(OUT, "works"), exist_ok=True)
    with open(os.path.join(OUT, "works", WORK_ID + ".json"), "w",
              encoding="utf-8") as fh:
        json.dump(work, fh, ensure_ascii=False, separators=(",", ":"))

    manifest_path = os.path.join(OUT, "manifest.json")
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)

    # The date card is drawn from the enriched position, the same way every
    # other work gets one. Without this the record exists in positions.py and
    # never reaches the page, and the reader is shown a text with no dating
    # beside it -- which for this one is the most interesting thing about it.
    stance = dates.enrich(POSITIONS.get(WORK_ID))
    if stance:
        work["positions"] = stance
        with open(os.path.join(OUT, "works", WORK_ID + ".json"), "w",
                  encoding="utf-8") as fh:
            json.dump(work, fh, ensure_ascii=False, separators=(",", ":"))

    section = next((s for s in manifest["sections"] if s["id"] == SECTION), None)
    if section is None:
        print(f"  ERROR: no section {SECTION} in the manifest")
        return 1

    if not any(w["id"] == WORK_ID for w in section["works"]):
        section["works"].append({
            "id": WORK_ID,
            "title": work["title"],
            "note": work["note"],
            "chapters": len(chapters),
            "verses": 0,
            "words": words,
            "versified": False,
            "source": "platt",
            "positions": stance,
            "verified": False,
        })

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

    with open(os.path.join(OUT, "didascalia-repairs.json"), "w",
              encoding="utf-8") as fh:
        json.dump({
            "note": "Words the 1834 scan broke, and what Platt printed. Found "
                    "by reading every token that occurs once or twice in "
                    "context, not by spell-checking, and applied as an "
                    "explicit table so each change is countable.",
            "source": "source/extra/" + SCAN,
            "repairs": [{"scanned": k, "printed": (REPAIRS | PHRASES)[k],
                         "times": n}
                        for k, n in sorted(repaired.items())],
        }, fh, ensure_ascii=False, indent=1)

    print(f"  added the Ethiopic Didascalia: {len(chapters)} sections, "
          f"{words:,} words, {sum(repaired.values())} scan repairs, "
          f"recovered not audited")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
