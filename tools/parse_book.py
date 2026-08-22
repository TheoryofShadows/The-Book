#!/usr/bin/env python3
"""Parse THE_BOOK_COMPLETE.txt into structured JSON for the web reader.

The source file has three nesting levels marked by plain-text rules:

    ====  bar / TITLE / [ subtitle ] / ====  bar     -> section (or front/back matter)
    ----  bar / TITLE / ----  bar                    -> work
    [ CHAPTER n ] / [ 1 ENOCH n ] / [ Vision 1, 2 ]  -> chapter

Inside a chapter, verses are marked one of two ways:

    World English Bible   ->  "12  text"   (number, two spaces)
    R. H. Charles (1917)  ->  "12. text"   (number, period, one space)

Patristic prose (Apostolic Fathers, Ignatius, Hermas, NT apocrypha,
Testaments) carries no verse numbers at all and is kept as paragraphs.

Verse numbers are only accepted when they continue the running sequence,
which keeps footnote digits in the Charles texts from being mistaken for
verse markers.
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dates  # noqa: E402
from positions import POSITIONS  # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else "THE_BOOK_COMPLETE.txt"
OUT = sys.argv[2] if len(sys.argv) > 2 else "docs/data"

EQ_BAR = re.compile(r"^={10,}\s*$")
DASH_BAR = re.compile(r"^-{10,}\s*$")
CH_MARK = re.compile(r"^\[\s*(.+?)\s*\]\s*$")
SECTION_TITLE = re.compile(r"^SECTION\s+([IVXL]+)\.\s+(.*)$")
CONTINUED = re.compile(r"\(continued,\s*part\s*(\d+)\)\s*$", re.I)

# Chapter-marker flavours, most specific first.
CH_PATTERNS = [
    re.compile(r"^CHAPTER\s+(\d+)$", re.I),
    re.compile(r"^(\d+)\s+ENOCH\s+(\d+)$", re.I),
    re.compile(r"^JUBILEES\s+(\d+)$", re.I),
    re.compile(r"^PARAGRAPH\s+(\d+)$", re.I),
    re.compile(r"^(?:VISION|COMMANDMENT|SIMILITUDE)\s+(\d+),\s*(\d+)$", re.I),
    re.compile(r"^([A-Za-z]+)\s+(\d+)$"),  # Testaments: "Levi 2"
]


# Which printed edition each work comes from. Attribution has to follow the
# work, not its verse-numbering style: the Didache numbers verses the same way
# Charles's Enoch does, but it is a Roberts-Donaldson translation.
ANF_SECTIONS = (
    "the-testaments-of-the-twelve-patriarchs",
    "the-apostolic-fathers",
    "new-testament-apocrypha",
    "the-shepherd-of-hermas",
    "the-epistles-of-ignatius-of-antioch",
)

SOURCES = {
    "web": {
        "label": "World English Bible with Deuterocanon",
        "detail": "Published by eBible.org and dedicated to the public domain. "
                  "A modern revision of the American Standard Version of 1901, "
                  "rendering the divine name as Yahweh.",
    },
    "charles": {
        "label": "R. H. Charles, 1917",
        "detail": "Translated for the Society for Promoting Christian Knowledge "
                  "and public domain by age. Double brackets mark words Charles "
                  "restored by conjecture and a dagger marks a reading he judged "
                  "corrupt. Verse numbers follow the marginal numbering of that "
                  "printing and sometimes fall mid-sentence. The text was "
                  "digitised by optical character recognition, so scattered "
                  "typographic artifacts survive.",
    },
    "anf": {
        "label": "Ante-Nicene Fathers, ed. Roberts and Donaldson, 1885",
        "detail": "Public domain by age. The Ignatian letters follow the shorter "
                  "recension, the seven letters generally accepted as genuine. "
                  "These texts carry no verse numbers in the original; chapter "
                  "divisions are the editors'.",
    },
    "editorial": {
        "label": "Editorial summary",
        "detail": "Written for this volume. No primary text was available from a "
                  "public-domain source.",
    },
    # The four texts recovered from scans, which arrive from
    # tools/build_didascalia.py and tools/build_ethiopian.py rather than
    # from the source file. Their labels belong here all the same: the
    # reader's apparatus is drawn from this table, and a work whose key
    # is missing from it is shown with no statement of where its text
    # came from at all -- which for a recovered text is the one thing
    # that most needs saying.
    "platt": {
        "label": "Thomas Pell Platt, Oriental Translation Fund, 1834",
        "detail": "Public domain by age, recovered from the scan of a "
                  "facing-page printing of the Ge'ez with Platt's English "
                  "beside it. Not audited: no independent reference counts "
                  "exist for this text, so there is nothing to check it "
                  "against but the scan.",
    },
    "horner": {
        "label": "The Rev. G. Horner, The Statutes of the Apostles, 1904",
        "detail": "Public domain by age. Horner's English of the Ge'ez "
                  "Sinodos he prints in the same volume, recovered from the "
                  "scan by the word coordinates rather than by its plain "
                  "OCR. Not audited: no independent reference counts exist "
                  "for this text. His own numbering is kept, including the "
                  "two statutes he numbers 40.",
    },
    "issaverdens": {
        "label": "Jacques Issaverdens, Venice, 1901",
        "detail": "Public domain by age. The Armenian recension made from "
                  "the Greek, in Issaverdens's English, recovered from the "
                  "scan by the word coordinates. It is a witness to the "
                  "work the Ethiopian canon receives, not to the Ge'ez text "
                  "of it, and no public-domain English of the Ge'ez exists. "
                  "Not audited.",
    },
    "james": {
        "label": "Montague Rhodes James, The Apocryphal New Testament, 1924",
        "detail": "Public domain by age. James's English of the Ethiopic "
                  "published by Guerrier, recovered from the scan by the "
                  "word coordinates. His section numbers are the ones "
                  "printed. Not audited.",
    },
}


def source_for(work_id: str, section_id: str, has_text: bool) -> str:
    if not has_text:
        return "editorial"
    if work_id.startswith("1-enoch") or work_id == "jubilees":
        return "charles"
    if section_id in ANF_SECTIONS:
        return "anf"
    return "web"


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return re.sub(r"-{2,}", "-", text)


PROLOGUE = re.compile(r"^(.*?)\s*-\s*PROLOGUE$", re.I)


def chapter_label(raw: str) -> tuple[str, int | None] | None:
    """Return (display label, ordinal), or None if this is not a real marker.

    Returning None matters: the Charles texts carry OCR bracket artifacts such
    as "[[[is beautiful, and its fruit]]]]" that would otherwise be mistaken
    for chapter headings.
    """
    if PROLOGUE.match(raw):
        return raw.title().replace("Jubilees", "Jubilees"), 0
    for pat in CH_PATTERNS:
        m = pat.match(raw)
        if not m:
            continue
        groups = m.groups()
        try:
            num = int(groups[-1])
        except ValueError:
            continue
        if pat.pattern.startswith("^CHAPTER"):
            return f"Chapter {num}", num
        return raw, num
    return None


def unwrap(lines: list[str]) -> list[str]:
    """Join hard-wrapped lines into paragraphs, splitting on blank lines.

    Trailing whitespace is deliberately preserved while joining. A verse
    number that lands at the end of a wrapped line keeps its trailing space,
    so "12 " + "\\n" + "text" rejoins as "12  text" and stays recognisable as
    a verse boundary.
    """
    paras, buf = [], []
    for line in lines:
        if line.strip():
            buf.append(line.rstrip("\r").lstrip())
        elif buf:
            paras.append(" ".join(buf))
            buf = []
    if buf:
        paras.append(" ".join(buf))
    return paras


# --------------------------------------------------------------------------
# Scrape contamination.
#
# The Apostolic Fathers and Ignatius texts were harvested from web editions of
# Ante-Nicene Fathers, and site furniture came with them: ANF editorial
# introductions, Roberts-Donaldson "Elucidations", and navigation footers.
# These always land at the tail of a work's final chapter. Each removal is
# logged so the site can show exactly what was taken out and why.
CONTAMINANTS = [
    (re.compile(r"\s*(?:\b[A-Z][a-z]+\s+)?Introductory Note to\b"),
     "ANF editorial introduction to the next work"),
    (re.compile(r"\s*Go to the Chronological List\b"),
     "earlychristianwritings.com navigation footer"),
    (re.compile(r"\s*Please buy the CD\b"),
     "earlychristianwritings.com advertisement"),
    (re.compile(r"\s*Elucidations?\.\s+[IVX]+\s*\("),
     "Roberts-Donaldson editorial elucidation"),
]

REMOVALS: list[dict] = []


def decontaminate(text: str, where: str) -> str:
    """Truncate text at the first piece of scrape furniture, logging the cut."""
    for pattern, reason in CONTAMINANTS:
        m = pattern.search(text)
        if not m:
            continue
        removed = text[m.start():].strip()
        text = text[:m.start()].rstrip()
        REMOVALS.append({
            "where": where,
            "reason": reason,
            "chars": len(removed),
            "excerpt": removed[:180],
        })
        return decontaminate(text, where)
    return text


# --------------------------------------------------------------------------
# Chapter headings spliced into the running text.
#
# The Apostolic Fathers source was prepared by turning the Ante-Nicene Fathers
# chapter headings into "[ Chapter n ]" marker lines. Three headings survived
# that pass because the scan had misread their full stop as a comma --
# "CHAP, IV.--" and "CHAPTER IX,--" rather than "CHAP. IV.--" -- so they were
# left sitting mid-sentence in the prose. The chapters they open were absorbed
# into the chapter before, and the ANF heading was read out as scripture.
#
# Rewriting them into ordinary marker lines before the structural scan puts
# the boundary back. Each one is logged, so the accuracy report can show that
# the volume repaired the text rather than quietly restructuring it.
SPLICED_HEADING = re.compile(
    r"\bCHAP(?:TER)?[.,]?\s+([IVXLCDM]+)[.,]?\s*--\s*"      # CHAP, IV.--
    r"([A-Z][A-Z0-9\s,'\[\]()-]*?)\.\s+"                    # ALL-CAPS title.
    r"(?=[A-Z])"                                              # prose resumes
)

ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

SPLICES: list[dict] = []


def from_roman(numeral: str) -> int | None:
    """Read a Roman numeral, or None if it is not one."""
    total = prev = 0
    for ch in reversed(numeral.upper()):
        if ch not in ROMAN:
            return None
        val = ROMAN[ch]
        total = total - val if val < prev else total + val
        prev = max(prev, val)
    return total or None


def unsplice(raw: str) -> str:
    """Turn headings left inside the prose back into chapter marker lines.

    The heading itself is dropped rather than kept: every other chapter in
    these works had its ANF heading removed when the source was prepared, and
    keeping these three would put editorial titles in the text of three
    chapters and no others.
    """
    def repair(m: re.Match) -> str:
        num = from_roman(m.group(1))
        if num is None:
            return m.group(0)
        SPLICES.append({
            "numeral": m.group(1),
            "chapter": num,
            "heading": " ".join(m.group(2).split()),
            "reason": "ANF chapter heading left in the running text by the "
                      "source preparation; the chapter boundary is restored "
                      "here and the heading dropped, as in every other chapter",
        })
        return f"\n\n[ Chapter {num} ]\n\n"

    return SPLICED_HEADING.sub(repair, raw)


WEB_VERSE = re.compile(r"(?:(?<=\s)|^)(\d{1,3})\s\s+")
# The stray "V" is a single typo in the source -- Jubilees 6 opens "V1." where
# every other chapter opens "1." -- and without it that chapter's first verse
# is not recognised as a marker at all. "V?" cannot swallow a Roman numeral:
# a digit has to follow immediately, so "VII." is still prose.
CHARLES_VERSE = re.compile(r"(?:(?<=\s)|^)V?(\d{1,3})\.\s+")


def split_verses(paras: list[str]) -> tuple[list[dict], str]:
    """Split paragraph text into verses. Returns (verses, style)."""
    body = "\n\n".join(paras)
    for style, pattern in (("web", WEB_VERSE), ("charles", CHARLES_VERSE)):
        hits = [(m.start(), m.end(), int(m.group(1))) for m in pattern.finditer(body)]
        # Keep only markers that continue the running sequence.
        kept, expect = [], None
        for start, end, num in hits:
            if expect is None:
                if num <= 2:  # a chapter must open at verse 1 (or 2 after a gap)
                    kept.append((start, end, num))
                    expect = num + 1
                continue
            if num == expect or (expect < num <= expect + 3):
                kept.append((start, end, num))
                expect = num + 1
        if len(kept) < 2:
            continue
        verses = []

        # Text standing in front of the first marker is the opening verse,
        # printed without its number. Charles does this throughout Jubilees
        # and Enoch: the chapter numeral carries verse one and the numbering
        # visibly starts at "2.". Dropping that text, which is what slicing
        # from the first marker does, deleted 56 chapter openings from this
        # volume -- about twelve thousand characters of Jubilees and Enoch --
        # and left the chapters starting at verse two with no sign anything
        # had gone. It is emitted here under the number it must have.
        head = re.sub(r"\s+", " ", body[:kept[0][0]]).strip()
        if head and kept[0][2] > 1:
            verses.append({"v": kept[0][2] - 1, "t": head})

        for idx, (start, end, num) in enumerate(kept):
            stop = kept[idx + 1][0] if idx + 1 < len(kept) else len(body)
            text = re.sub(r"\s+", " ", body[end:stop]).strip()
            if text:
                verses.append({"v": num, "t": text})
        if verses:
            return verses, style
    return [], "prose"


def parse(path: str) -> dict:
    raw = unsplice(open(path, encoding="utf-8").read())
    lines = raw.split("\n")
    n = len(lines)

    # ---- locate every structural marker -------------------------------
    marks = []  # (index, kind, payload)
    i = 0
    while i < n:
        line = lines[i]
        if EQ_BAR.match(line):
            j = i + 1
            block = []
            while j < n and not EQ_BAR.match(lines[j]) and j - i < 8:
                block.append(lines[j])
                j += 1
            if j < n and EQ_BAR.match(lines[j]):
                title = [b.strip() for b in block if b.strip()]
                if title:
                    marks.append((j + 1, "section", title))
                i = j + 1
                continue
        if DASH_BAR.match(line):
            if i + 2 < n and DASH_BAR.match(lines[i + 2]) and lines[i + 1].strip():
                marks.append((i + 3, "work", lines[i + 1].strip()))
                i += 3
                continue
        m = CH_MARK.match(line)
        if m:
            marks.append((i + 1, "chapter", m.group(1)))
        i += 1

    marks.append((n, "eof", None))

    # ---- assemble -----------------------------------------------------
    doc = {"sections": [], "frontmatter": [], "backmatter": []}
    section = None
    work = None
    chapter = None
    seen_slugs: dict[str, int] = {}

    def flush(start: int, stop: int) -> list[str]:
        return unwrap(lines[start:stop])

    for idx, (start, kind, payload) in enumerate(marks[:-1]):
        stop = marks[idx + 1][0]
        # a marker line itself occupies start-1..; trim trailing marker lines
        stop_text = stop
        if marks[idx + 1][1] == "section":
            stop_text = stop - 4
        elif marks[idx + 1][1] == "work":
            stop_text = stop - 3
        elif marks[idx + 1][1] == "chapter":
            stop_text = stop - 1
        stop_text = max(start, stop_text)
        body = flush(start, stop_text)

        if kind == "section":
            title = payload[0]
            subtitle = payload[1] if len(payload) > 1 else ""
            cont = CONTINUED.search(title)
            base = CONTINUED.sub("", title).strip()
            sm = SECTION_TITLE.match(base)
            if cont and section and section["title"] == base:
                section["intro"] += body  # continuation of the same section
                work = None
                continue
            section = {
                "id": slugify(base),
                "title": base,
                "roman": sm.group(1) if sm else None,
                "name": sm.group(2).strip() if sm else base,
                "dates": subtitle,
                "intro": body,
                "works": [],
            }
            doc["sections"].append(section)
            work = None
            chapter = None
            continue

        if kind == "work":
            if section is None:
                continue
            slug = slugify(payload)
            if slug in seen_slugs:
                seen_slugs[slug] += 1
                slug = f"{slug}-{seen_slugs[slug]}"
            else:
                seen_slugs[slug] = 1
            work = {
                "id": slug,
                "title": payload,
                "section": section["id"],
                "note": body,
                "chapters": [],
            }
            section["works"].append(work)
            chapter = None
            continue

        if kind == "chapter":
            if work is None:
                continue
            parsed = chapter_label(payload)
            if parsed is None:
                # Not a heading at all -- an OCR bracket artifact. Fold the
                # text back into the chapter it interrupted.
                if chapter is not None and body:
                    tail = " ".join(body)
                    if chapter.get("verses"):
                        chapter["verses"][-1]["t"] += " " + tail
                    else:
                        chapter.setdefault("paras", []).extend(body)
                continue
            label, num = parsed
            where = f"{work['title']} / {label}"
            body = [decontaminate(p, where) for p in body]
            body = [p for p in body if p.strip()]
            verses, style = split_verses(body)
            chapter = {"label": label, "n": num, "raw": payload}
            if verses:
                chapter["verses"] = verses
                chapter["style"] = style
            else:
                chapter["paras"] = [re.sub(r"\s+", " ", p).strip() for p in body]
                chapter["style"] = "prose"
            work["chapters"].append(chapter)
            continue

    # Text that appeared before the first section, and the appendices.
    return doc


def main() -> None:
    doc = parse(SRC)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "works"), exist_ok=True)

    manifest = {"sections": []}
    total_ch = total_v = total_words = 0

    for section in doc["sections"]:
        entry = {
            "id": section["id"],
            "title": section["title"],
            "roman": section["roman"],
            "name": section["name"],
            "dates": section["dates"],
            # The section heading's own range, read the same way a position
            # is. It places the works that carry no position record of their
            # own, which is most of them, and the timeline says which of the
            # two a bar came from rather than blurring them together.
            "span": dates.span(section["dates"] or ""),
            "intro": section["intro"],
            "works": [],
        }
        for work in section["works"]:
            nch = len(work["chapters"])
            nv = sum(len(c.get("verses", [])) for c in work["chapters"])
            words = 0
            for c in work["chapters"]:
                for v in c.get("verses", []):
                    words += v["t"].count(" ") + 1
                for p in c.get("paras", []):
                    words += p.count(" ") + 1
            total_ch += nch
            total_v += nv
            total_words += words
            src = source_for(work["id"], section["id"], nch > 0)
            work["source"] = src
            # The prose position is what the volume asserts; the span is
            # arithmetic on it, so the reader can be shown how far apart the
            # two datings are without the page having to parse English.
            stance = dates.enrich(POSITIONS.get(work["id"]))
            if stance:
                work["positions"] = stance
            entry["works"].append({
                "id": work["id"],
                "title": work["title"],
                "note": work["note"],
                "chapters": nch,
                "verses": nv,
                "words": words,
                "versified": nv > 0,
                "source": src,
                "positions": stance,
                "chapterLabels": [c["label"] for c in work["chapters"]],
            })
            with open(os.path.join(OUT, "works", work["id"] + ".json"), "w",
                      encoding="utf-8") as fh:
                json.dump(work, fh, ensure_ascii=False, separators=(",", ":"))
        manifest["sections"].append(entry)

    manifest["sources"] = SOURCES
    manifest["totals"] = {
        "sections": len(doc["sections"]),
        "works": sum(len(s["works"]) for s in manifest["sections"]),
        "chapters": total_ch,
        "verses": total_v,
        "words": total_words,
    }
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, separators=(",", ":"))

    with open(os.path.join(OUT, "removals.json"), "w", encoding="utf-8") as fh:
        json.dump(REMOVALS, fh, ensure_ascii=False, indent=1)

    with open(os.path.join(OUT, "splices.json"), "w", encoding="utf-8") as fh:
        json.dump(SPLICES, fh, ensure_ascii=False, indent=1)

    print(json.dumps(manifest["totals"], indent=2))
    print(f"contamination removals logged: {len(REMOVALS)}")
    print(f"spliced chapter headings repaired: {len(SPLICES)}")


if __name__ == "__main__":
    main()
