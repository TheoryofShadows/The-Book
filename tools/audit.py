#!/usr/bin/env python3
"""Check the parsed library against standard chapter/verse counts.

Chapter counts are the settled figures for the Masoretic/Greek books.
Verse counts follow the World English Bible, which is the source text here;
where WEB versification legitimately differs from KJV (Malachi, Joel, the
Greek additions, 3 John, Revelation 12) the WEB figure is used.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(HERE, "audit-baseline.txt")

DATA = sys.argv[1] if len(sys.argv) > 1 else "docs/data"

# work-id -> (expected chapters, expected verses or None)
EXPECT = {
    # Torah
    "genesis": (50, 1533), "exodus": (40, 1213), "leviticus": (27, 859),
    "numbers": (36, 1288), "deuteronomy": (34, 959),
    # Former prophets / history
    "joshua": (24, 658), "judges": (21, 618), "ruth": (4, 85),
    "1-samuel": (31, 810), "2-samuel": (24, 695),
    "1-kings": (22, 816), "2-kings": (25, 719),
    "1-chronicles": (29, 942), "2-chronicles": (36, 822),
    "ezra": (10, 280), "nehemiah": (13, 406), "esther-hebrew": (10, 167),
    # Wisdom / poetry
    "job": (42, 1070), "psalms": (150, 2461), "proverbs": (31, 915),
    "ecclesiastes": (12, 222), "song-of-songs": (8, 117),
    # Latter prophets
    "jeremiah": (52, 1364), "lamentations": (5, 154), "ezekiel": (48, 1273),
    "daniel": (12, 357), "hosea": (14, 197), "joel": (3, 73),
    "amos": (9, 146), "obadiah": (1, 21), "jonah": (4, 48),
    "micah": (7, 105), "nahum": (3, 47), "habakkuk": (3, 56),
    "zephaniah": (3, 53), "haggai": (2, 38), "malachi": (4, 55),
    # New Testament
    "matthew": (28, 1071), "mark": (16, 678), "luke": (24, 1151),
    "john": (21, 879), "acts": (28, 1007), "romans": (16, 433),
    "1-corinthians": (16, 437), "2-corinthians": (13, 257),
    "galatians": (6, 149), "ephesians": (6, 155), "philippians": (4, 104),
    "colossians": (4, 95), "1-thessalonians": (5, 89),
    "2-thessalonians": (3, 47), "1-timothy": (6, 113), "2-timothy": (4, 83),
    "titus": (3, 46), "philemon": (1, 25), "hebrews": (13, 303),
    "james": (5, 108), "1-peter": (5, 105), "2-peter": (3, 61),
    "1-john": (5, 105), "2-john": (1, 13), "3-john": (1, 14),
    "jude": (1, 25), "revelation": (22, 405),
    # Deuterocanon / wider canon
    "tobit": (14, None), "judith": (16, None), "baruch": (5, None),
    "sirach-ecclesiasticus": (51, None), "the-wisdom-of-solomon": (19, None),
    "1-maccabees": (16, None), "2-maccabees": (15, None),
    "3-maccabees": (7, None), "4-maccabees": (18, None),
    "1-esdras": (9, None), "2-esdras-4-ezra": (16, None),
    "the-prayer-of-manasseh": (1, None), "psalm-151": (1, None),
    # The Vulgate prints the Greek additions as chapters 11-16, giving 16.
    # The World English Bible, which is the edition here, keeps the Greek
    # book's own arrangement: ten chapters with the additions folded in where
    # they belong rather than appended. The text is complete either way.
    "esther-greek-version": (10, None),
    # Split prophets, as arranged in this volume
    "isaiah-1-39-first-isaiah": (39, None),
    "isaiah-40-55-second-isaiah": (16, None),
    "isaiah-56-66-third-isaiah": (11, None),
    "zechariah-1-8": (8, None), "zechariah-9-14": (6, None),
    # Pseudepigrapha
    # Fifty chapters plus the prologue, which is parsed as a chapter of its
    # own because it carries text a reader can open.
    "jubilees": (51, None),
    "1-enoch-the-book-of-the-watchers-chapters-1-36": (36, None),
    "1-enoch-the-astronomical-book-chapters-72-82": (11, None),
    "1-enoch-the-book-of-parables-chapters-37-71": (35, None),
    "1-enoch-dream-visions-and-the-epistle-of-enoch-chapters-83-108": (26, None),
    # Apostolic Fathers
    "the-first-epistle-of-clement-to-the-corinthians": (65, None),
    "the-second-epistle-of-clement": (20, None),
    "the-epistle-of-polycarp-to-the-philippians": (14, None),
    "the-epistle-of-barnabas": (21, None),
    "the-teaching-of-the-twelve-apostles-didache": (16, None),
    "the-epistle-of-mathetes-to-diognetus": (12, None),
    "the-martyrdom-of-polycarp": (22, None),
    # Ignatius, shorter recension
    "the-epistle-of-ignatius-to-the-ephesians": (21, None),
    "the-epistle-of-ignatius-to-the-magnesians": (15, None),
    "the-epistle-of-ignatius-to-the-trallians": (13, None),
    "the-epistle-of-ignatius-to-the-romans": (10, None),
    "the-epistle-of-ignatius-to-the-philadelphians": (11, None),
    "the-epistle-of-ignatius-to-the-smyrnaeans": (13, None),
    "the-epistle-of-ignatius-to-polycarp": (8, None),
}


def main() -> int:
    manifest = json.load(open(os.path.join(DATA, "manifest.json"), encoding="utf-8"))
    works = {w["id"]: w for s in manifest["sections"] for w in s["works"]}

    problems = []
    checked = 0
    for wid, (exp_ch, exp_v) in sorted(EXPECT.items()):
        w = works.get(wid)
        if w is None:
            problems.append(("MISSING", wid, "not found in parsed output", ""))
            continue
        checked += 1
        if w["chapters"] != exp_ch:
            problems.append(("CHAPTERS", wid, f"expected {exp_ch}", f"got {w['chapters']}"))
        if exp_v is not None and w["verses"] != exp_v:
            problems.append(("VERSES", wid, f"expected {exp_v}", f"got {w['verses']}"))

    # Structural sanity: gaps and duplicates in chapter numbering.
    for wid, w in sorted(works.items()):
        path = os.path.join(DATA, "works", wid + ".json")
        if not os.path.exists(path):
            continue
        work = json.load(open(path, encoding="utf-8"))
        nums = [c["n"] for c in work["chapters"] if c.get("n") is not None]
        if len(nums) != len(set(nums)):
            dupes = sorted({n for n in nums if nums.count(n) > 1})
            problems.append(("DUP-CH", wid, "duplicate chapter numbers", str(dupes)))
        for chap in work["chapters"]:
            vs = [v["v"] for v in chap.get("verses", [])]
            if not vs:
                continue
            if chap.get("chunked"):
                # A deliberate slice of a continuous section run; it starts
                # where the slice starts, by design.
                continue
            if vs[0] != 1:
                problems.append(("V-START", wid, chap["label"], f"starts at verse {vs[0]}"))
            missing = sorted(set(range(1, vs[-1] + 1)) - set(vs))
            if missing:
                problems.append(("V-GAP", wid, chap["label"],
                                 f"missing {missing[:8]}{'...' if len(missing) > 8 else ''}"))
        empty = [c["label"] for c in work["chapters"]
                 if not c.get("verses") and not c.get("paras")]
        if empty:
            problems.append(("EMPTY", wid, "chapters with no text", str(empty[:6])))

    # The interpretive layer is held to the same standard as the text. A
    # position a reader cannot check does not belong beside verse counts that
    # were audited against independent references, so a missing citation is a
    # build failure, not a warning.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from positions import POSITIONS
    except ImportError:
        POSITIONS = {}

    for wid, rec in sorted(POSITIONS.items()):
        for field in ("trad", "tradWhy", "tradSource",
                      "crit", "critWhy", "critSource", "gap"):
            if not str(rec.get(field, "")).strip():
                problems.append(("UNCITED", wid, "missing " + field, ""))
        if wid not in works:
            problems.append(("ORPHAN", wid, "position for a work not in the volume", ""))

    # And the other direction, which is the one that was missing. The loop
    # above walks the positions and asks whether each is cited. It never
    # asked whether a work *has* a position, so a work carrying text and no
    # dated argument at all was invisible here -- and the arrangement by
    # composition date is the one claim this whole volume is built on. A work
    # with no record is not undated on the page: it inherits the span of the
    # section it is filed under, and the timeline draws it fainter to say so.
    # That is a looser claim than a cited date, and until now nothing counted
    # how many of them there were.
    for wid, w in sorted(works.items()):
        if not w.get("words"):
            continue          # apparatus and placeholders carry no date
        if wid not in POSITIONS:
            problems.append(("NO-POSITION", wid, "placed by its section's era",
                             "no dated position record"))

    for kind, wid, a, b in problems:
        print(f"{kind:11s} {wid:62s} {a}  {b}")
    positioned = sum(1 for wid, w in works.items()
                     if w.get("words") and wid in POSITIONS)
    texts = sum(1 for w in works.values() if w.get("words"))
    print(f"\n{checked} works checked against reference counts; "
          f"{len(POSITIONS)} position records checked for citations; "
          f"{positioned} of {texts} works carrying text have one")

    return gate(problems)


def line_for(problem: tuple[str, str, str, str]) -> str:
    """One finding as the single line the baseline stores it under."""
    kind, wid, a, b = problem
    return " | ".join(x.strip() for x in (kind, wid, a, b))


def read_baseline() -> set[str]:
    """The accepted findings. Blank lines and anything after # are ignored."""
    if not os.path.exists(BASELINE):
        return set()
    accepted = set()
    with open(BASELINE, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.split("#", 1)[0].strip()
            if line:
                accepted.add(line)
    return accepted


def gate(problems: list[tuple[str, str, str, str]]) -> int:
    """Compare the findings against the baseline; fail on any difference.

    The point of the baseline is that this script can be a gate at all. Every
    finding here is either a known property of the printed edition -- the WEB
    really does omit Luke 17:36 -- or a defect. Without a baseline the two are
    indistinguishable and 150-odd lines of known-good output drown the one
    line that means the parse has broken, which is why this check ran for as
    long as it did while reporting real chapter losses to nobody.

    The file is deliberately not regenerated by this script. Every accepted
    entry carries a written reason, which is the same standard the volume
    holds its positions and its verse counts to; a baseline that rewrote
    itself would let a regression in under cover of a passing build.
    """
    current = {line_for(p) for p in problems}
    accepted = read_baseline()

    appeared = sorted(current - accepted)
    resolved = sorted(accepted - current)

    if not appeared and not resolved:
        print(f"{len(current)} findings, all accounted for in "
              f"{os.path.relpath(BASELINE)}")
        return 0

    if appeared:
        print(f"\n{len(appeared)} finding(s) not in the baseline:\n")
        for line in appeared:
            print("  + " + line)
        print("\nEach one is either a defect to fix or a property of the "
              "printed edition.\nIf it is the latter, add it to "
              f"{os.path.relpath(BASELINE)} under a heading\nthat says why, "
              "in the same terms the accuracy report uses.")

    if resolved:
        print(f"\n{len(resolved)} baseline entry(ies) no longer occur:\n")
        for line in resolved:
            print("  - " + line)
        print("\nThe text or the parse improved, or a reference figure moved. "
              "Delete these\nfrom the baseline so it keeps describing the "
              "volume as it actually is.")

    return 1


if __name__ == "__main__":
    sys.exit(main())
