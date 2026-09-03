#!/usr/bin/env python3
"""Close 1 Clement's hole, and give Smyrnaeans back the chapter it had.

Two of the Apostolic Fathers in this volume are short of a chapter or six.
tools/build_repairs.py closed what the 1870 printing could close and wrote
down what it could not:

    1 Clement 59:2-61, the great intercessory prayer ... Lightfoot's
    edition of 1890-91 would close it.
    Ignatius to the Smyrnaeans 13.

This closes both, and they turn out to be two different kinds of hole.

1 CLEMENT: A HOLE IN THE MANUSCRIPT, FILLED BY A LATER FIND

The Ante-Nicene Fathers translate Codex Alexandrinus, and the last leaf of
Alexandrinus is damaged. Everything between 57.7 and 63.4 went with it,
which is why the volume's 1 Clement runs 1-59 and every modern edition runs
1-65: the ANF's 58 and 59 are the world's 64 and 65, and six chapters in
between are simply not there. Inside those six is the great intercessory
prayer -- the oldest Christian liturgical prayer that survives outside the
New Testament, and the reason anyone reads this letter twice.

The gap is not a gap in the public domain. Bryennios found the whole letter
in a Constantinople manuscript in 1873 and published it in 1875, and
Lightfoot printed an English translation of the complete text in 1891. That
edition is public domain by age, and its translation section is set in a
single column with the chapter numbers in the text -- so tools/scans.py
recovers it from the scan's word coordinates with nothing to separate but
the running heads.

So chapters 58 to 63 are Lightfoot's English and the rest of the letter is
Roberts and Donaldson's. Two translators in one work is not ideal and is not
hidden: the work says so at its head, and the six chapters are the six the
other translator could not have printed.

What is checked, and it is the thing that would matter most: the join. If
the chapters were cut one out of step -- if Lightfoot's 58 were really the
ANF's 58 -- the letter would gain six chapters and lose its sense. Ten
leaves are recovered rather than the four the missing chapters occupy, so
Lightfoot's 57, 64 and 65 come with them, and tests/python/test_lightfoot.py
holds them against the volume's own 57, 58 and 59. They are different
translations of the same Greek and will not match word for word; they name
the same people and quote the same scripture, and that is enough to prove
the seam is in the right place.

SMYRNAEANS: NOT A HOLE AT ALL

The audit baseline said Ignatius to the Smyrnaeans had lost its thirteenth
chapter to the scrape. It had not. The chapter is in the volume, printed as
the second half of chapter 12, with the ANF heading that opens it -- the
single word CONCLUSION -- left standing mid-sentence in the prose. It is the
same defect tools/parse_book.py repairs three times over as a spliced
heading, in a shape that pattern cannot match: no CHAP., no roman numeral,
no dash. So it is named here instead.

Two more things had gone wrong in the same chapter and are put right with
it: the scrape doubled the opening clause, so Ignatius greets Troas twice,
and it doubled the word "and" in the sentence about the virgins.

Runs after tools/build_repairs.py.
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scans                                            # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/data"
RAW = sys.argv[2] if len(sys.argv) > 2 else "source/extra"
SCAN = "1-clement-lightfoot-1891.txt"

CLEMENT = "the-first-epistle-of-clement-to-the-corinthians"
SMYRNAEANS = "the-epistle-of-ignatius-to-the-smyrnaeans"

# The chapters Lightfoot's leaves carry, in order. Cutting against a known
# ascending run rather than against "any number followed by a full stop" is
# what keeps a scripture reference -- and this letter is nothing but
# scripture references -- from being read as a chapter opening.
PRINTED = list(range(44, 66))

# The six the volume is missing. Everything else recovered here is context:
# it is what proves the cut is in the right place, and it is not used.
WANTED = list(range(58, 64))

# What the scan made of Lightfoot's italics, and what he printed. Every one
# of these is a word he set in italic to mark a quotation of scripture --
# the engine reads an italic b as a d, an italic l as a J, an italic t as a
# cedilla -- so they cluster in the prayer, which is quotation almost
# throughout. Found by reading every token in these six chapters that is not
# an English word, not by spell-checking, and applied as a table so that
# each change is countable and can be put beside the page image.
REPAIRS = [
    ("who alone adidest Highest", "who alone abidest Highest"),
    ("whoralone art the Benefactor", "who alone art the Benefactor"),
    ("who Jlookest into the abysses", "who lookest into the abysses"),
    ("comfort the faint-hearted. ef all the Gentiles",
     "comfort the faint-hearted. Let all the Gentiles"),
    ("and we ave Thy people", "and we are Thy people"),
    ("and guzde our steps", "and guide our steps"),
    ("of heart and ¢o do such things", "of heart and to do such things"),
    ("sheltered 4y Zhy mighty hand", "sheltered by Thy mighty hand"),
    ("every sin dy Thine uplifted arm", "every sin by Thine uplifted arm"),
    # A printer's signature mark -- the sheet number, set at the foot of the
    # first leaf of a gathering -- which sits below the text and is caught by
    # neither the running-head rule nor the footnote rule, because it is
    # neither. It falls inside a sentence of chapter 61.
    ("they may obtain Thy 6—2 favour", "they may obtain Thy favour"),
    # Two brackets the compositor closed up against the next word, or the
    # engine did. Lightfoot's square brackets mark what he supplied from the
    # versions where the Greek is defective, and they are his, so they stay;
    # the space after them is put back.
    ("[Grant unto us, Lord,]that", "[Grant unto us, Lord,] that"),
    ("[their steps]in holiness", "[their steps] in holiness"),
    # A word broken across a line break which tools/scans.py closed up,
    # because neither the closed nor the hyphenated form occurs anywhere
    # else in the ten leaves it had to judge by. Lightfoot prints the hyphen.
    ("being lowlyminded towards", "being lowly-minded towards"),
    ("65. Nowsend ye back", "65. Now send ye back"),
]

# A thin space before a semicolon or a colon is the compositor's, and the
# engine reads it as a word space. Closed up rather than tabulated: it is
# one rule about spacing and it applies wherever it fires, so a table of
# instances would say less than the rule does.
THIN = re.compile(r"\s+([;:,.])")

CHAPTER_OPENS = "Let us therefore be obedient"


def repair(text: str, log: list[dict]) -> str:
    """Apply the table, recording what fired and how often."""
    for scanned, printed in REPAIRS:
        times = text.count(scanned)
        if times:
            text = text.replace(scanned, printed)
        log.append({"scanned": scanned, "printed": printed, "times": times})
    return text


def cut(paragraphs: list[str], numbers: list[int]) -> dict:
    """Split paragraphs of prose at the printed chapter numbers.

    A chapter can open in the middle of a paragraph -- Lightfoot runs 59
    straight on from the Amen of 58 -- and a paragraph can open in the
    middle of a chapter, which is how the prayer is set off inside 59. Both
    have to survive, so this walks the paragraphs and the expected numbers
    together rather than splitting the text and losing where the paragraphs
    were.
    """
    want = list(numbers)
    at = 0
    chapters: dict[int, list[str]] = {}
    current: int | None = None

    for para in paragraphs:
        pos = 0
        while at < len(want):
            mark = re.compile(r"(?:(?<=\s)|^)%d\.\s+" % want[at])
            found = mark.search(para, pos)
            if not found:
                break
            head = para[pos:found.start()].strip()
            if head and current is not None:
                chapters[current].append(head)
            current = want[at]
            chapters[current] = []
            pos = found.end()
            at += 1
        tail = para[pos:].strip()
        if tail and current is not None:
            chapters[current].append(tail)

    if at < len(want):
        raise SystemExit(
            f"  ERROR: {SCAN} stops at chapter {want[at]}; the range in "
            f"tools/fetch_scans.py is wrong")
    return chapters


def save(work: dict) -> None:
    path = os.path.join(OUT, "works", work["id"] + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(work, fh, ensure_ascii=False, separators=(",", ":"))


def load(wid: str):
    path = os.path.join(OUT, "works", wid + ".json")
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) \
        else None


def restat(work: dict, entry: dict) -> None:
    entry["chapters"] = len(work["chapters"])
    entry["verses"] = sum(len(c.get("verses", [])) for c in work["chapters"])
    entry["words"] = sum(
        p.count(" ") + 1
        for c in work["chapters"]
        for p in (c.get("paras", []) + [v["t"] for v in c.get("verses", [])]))


def chapter(n: int, paras: list[str]) -> dict:
    return {"label": f"Chapter {n}", "n": n, "raw": f"Chapter {n}",
            "paras": paras, "style": "prose"}


def do_clement(manifest, report, log) -> None:
    path = os.path.join(RAW, SCAN)
    if not os.path.exists(path):
        print(f"  missing {path}; skipping 1 Clement")
        return
    work = load(CLEMENT)
    if work is None:
        return
    if len(work["chapters"]) >= 65:
        return

    paragraphs, pages = scans.read_recovered(path)
    flat = scans.prose(paragraphs, report["hyphens"])
    text = repair("\n\n".join(flat), report["repairs"])
    text = THIN.sub(r"\1", text)
    chapters = cut(text.split("\n\n"), PRINTED)

    # The two chapters the volume already has, as Lightfoot numbers them.
    # Kept in the report rather than in the text: they are what the join is
    # checked against, and the volume keeps its own translation of them.
    report["overlap"] = {n: " ".join(chapters[n]) for n in (57, 64, 65)
                         if n in chapters}

    opens = " ".join(chapters[58])[:len(CHAPTER_OPENS)]
    if opens != CHAPTER_OPENS:
        raise SystemExit(f"  ERROR: Lightfoot 58 opens {opens!r}, not "
                         f"{CHAPTER_OPENS!r}; the cut is out of step")

    # The volume's 58 and 59 are the letter's 64 and 65. Renumber them
    # before the six go in, or the six have nowhere to sit.
    tail = work["chapters"][-2:]
    if [c["n"] for c in tail] != [58, 59]:
        raise SystemExit("  ERROR: 1 Clement does not end at 58, 59")
    for c, n in zip(tail, (64, 65)):
        c["n"] = n
        c["label"] = c["raw"] = f"Chapter {n}"

    work["chapters"] = (work["chapters"][:-2]
                        + [chapter(n, chapters[n]) for n in WANTED]
                        + tail)

    # The printing marks the lacuna with an ellipsis at the end of 57. It
    # said something true and now says something false, because what was
    # missing is the next six chapters, so it comes off with them.
    fifty_seven = work["chapters"][56]
    assert fifty_seven["n"] == 57
    ellipsis = fifty_seven["paras"][-1].rstrip()
    if ellipsis.endswith("..."):
        fifty_seven["paras"][-1] = ellipsis[:-3].rstrip()
        report["ellipsis"] = ("the ellipsis the printing set at the end of "
                              "chapter 57 to mark the lacuna, removed "
                              "because the lacuna is filled")

    work["note"] = [
        "Chapters 58 to 63 are J. B. Lightfoot's translation of 1891; the "
        "rest of the letter is Roberts and Donaldson's of 1885. The 1885 "
        "printing follows Codex Alexandrinus, whose last leaf is damaged, "
        "and everything from 57.7 to 63.4 is lost with it — including "
        "the great intercessory prayer, the oldest Christian liturgical "
        "prayer surviving outside the New Testament. Bryennios found the "
        "whole letter in a Constantinople manuscript in 1873; Lightfoot "
        "printed it in English in 1891, and those six chapters are "
        "recovered here from the scan of that printing. The letter's last "
        "two chapters were numbered 58 and 59 in this volume because the "
        "six before them were absent; they are numbered 64 and 65 here, as "
        "they are in every edition of the complete text.",
        "J. B. Lightfoot and J. R. Harmer, The Apostolic Fathers: revised "
        "texts with short introductions and English translations. London: "
        "Macmillan, 1891, pages 82–85.",
    ]

    save(work)
    for section in manifest["sections"]:
        for entry in section["works"]:
            if entry["id"] == CLEMENT:
                entry["note"] = work["note"]
                restat(work, entry)
    log.append(f"1 Clement: 59 -> {len(work['chapters'])} chapters, "
               f"the six of the Alexandrinus lacuna from Lightfoot 1891 "
               f"({len(pages)} leaves read)")


# The heading the scrape left standing where chapter 13 begins, and the two
# doublings in the same chapter. Each is a defect in the source compilation
# rather than in any printed edition, so each is stated with what it should
# have been.
SMYRNAEAN_FIXES = [
    {"was": "The love of the brethren at Troas salutes you; whence also I "
            "write to The love of your brethren at Troas salutes you; "
            "whence also I write to you by Burrhus",
     "now": "The love of the brethren at Troas salutes you; whence also I "
            "write to you by Burrhus",
     "why": "the scrape repeated the opening clause, so Ignatius greeted "
            "Troas twice"},
    {"was": "with their wives and children, and and the virgins",
     "now": "with their wives and children, and the virgins",
     "why": "the scrape doubled a word"},
]

CONCLUSION = "! CONCLUSION. "


def do_smyrnaeans(manifest, report, log) -> None:
    work = load(SMYRNAEANS)
    if work is None or len(work["chapters"]) >= 13:
        return
    last = work["chapters"][-1]
    if last["n"] != 12 or len(last["paras"]) != 1:
        return
    body = last["paras"][0]

    for fix in SMYRNAEAN_FIXES:
        times = body.count(fix["was"])
        if times:
            body = body.replace(fix["was"], fix["now"])
        report["smyrnaeans"].append(dict(fix, times=times))

    if CONCLUSION not in body:
        return
    head, _, rest = body.partition(CONCLUSION)
    last["paras"] = [head + "!"]
    work["chapters"].append(chapter(13, [rest.strip()]))
    report["smyrnaeans"].append({
        "was": CONCLUSION.strip(),
        "now": "a chapter boundary",
        "why": "the ANF heading that opens chapter 13 was left in the "
               "running text by the source preparation, and the chapter "
               "was read as the second half of chapter 12. The boundary is "
               "restored and the heading dropped, as in every other "
               "chapter of these works",
        "times": 1,
    })

    save(work)
    for section in manifest["sections"]:
        for entry in section["works"]:
            if entry["id"] == SMYRNAEANS:
                restat(work, entry)
    log.append("Ignatius to the Smyrnaeans: 12 -> 13 chapters, the "
               "boundary restored at the heading the scrape left standing")


def main() -> int:
    manifest_path = os.path.join(OUT, "manifest.json")
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    report = {"hyphens": [], "repairs": [], "smyrnaeans": [], "overlap": {}}
    log: list[str] = []

    do_clement(manifest, report, log)
    do_smyrnaeans(manifest, report, log)

    if not log:
        print("  nothing to do")
        return 0

    totals = {"works": 0, "chapters": 0, "verses": 0, "words": 0}
    for section in manifest["sections"]:
        for entry in section["works"]:
            totals["works"] += 1
            for key in ("chapters", "verses", "words"):
                totals[key] += entry[key]
    totals["sections"] = len(manifest["sections"])
    manifest["totals"] = totals
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, separators=(",", ":"))

    report["note"] = (
        "What the 1891 scan made of Lightfoot's italics, and what he "
        "printed; and the three defects the source compilation left in "
        "Ignatius to the Smyrnaeans 12-13. Every change is listed with the "
        "number of times it fired, so a change that stops being needed "
        "shows up as a zero rather than disappearing.")
    report["source"] = "source/extra/" + SCAN
    with open(os.path.join(OUT, "lightfoot-repairs.json"), "w",
              encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    for line in log:
        print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
