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

CHAPTERS

Platt's own table of contents divides the work into sections and gives the
page each begins on. Those page numbers are the divisions used here. One
heading -- that Christians may not enter the assemblies of the heathen --
has no legible page number in the scan, so it is not used as a division
rather than being guessed at; its text sits inside the section before it.
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

# Platt's sections, with the page each opens on, read from his table of
# contents. The titles are his; the wording is left as he set it.
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


def english(line: str) -> bool:
    """Platt's English, as against a line of OCR'd Ge'ez.

    The Ge'ez arrives as runs of colons, carets and stray capitals with
    almost no real words in them. Four words and four fifths letters is a
    wide enough gap to separate the two without guessing at either.
    """
    s = line.strip()
    if len(s) < 20 or len(WORD.findall(s)) < 4:
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
}
# One break spans two words: the heading of Platt's eleventh section, where
# "lawful for" was scanned as a single ruined token.
PHRASES = {"law/iiljbr": "lawful for"}

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

    return re.sub(r"[A-Za-z‟']+", one, text)


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
    chapters = []
    unsplit = []
    for i, (first, title) in enumerate(SECTIONS):
        last = SECTIONS[i + 1][0] - 1 if i + 1 < len(SECTIONS) else numbers[-1]
        body = [prose(page[n]) for n in numbers if first <= n <= last and page[n]]
        if not body:
            # The page this section opens on carries no legible number, so
            # its text was gathered under the next mark instead. Nothing is
            # lost -- it reads on inside the following section -- but the
            # division cannot be made, and saying so is better than dropping
            # one of Platt's headings without a word.
            unsplit.append((first, title))
            continue
        chapters.append({
            "label": f"Section {len(chapters) + 1}",
            "n": len(chapters) + 1,
            "raw": title,
            "paras": body,
            "style": "prose",
        })

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
            "there is nothing to check it against but the scan itself. The "
            "section divisions are Platt's own, taken from his table of "
            "contents. Read it as a text recovered rather than as a text "
            "verified.",
        ] + ([
            "One of Platt's headings could not be given a division of its "
            "own: " + "; ".join(f"“{t}” (his p. {p})"
                                for p, t in unsplit)
            + ". That page's number did not survive the scan, so its text "
            "was gathered under the following one and reads on inside the "
            "section after it. The words are all here; the break is not."
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
            "chapterLabels": [c["label"] for c in chapters],
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
