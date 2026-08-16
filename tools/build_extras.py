#!/usr/bin/env python3
"""Add corpora that are not in the source compilation.

Runs after parse_book.py and appends to the manifest, so the search index
built afterwards covers these texts too.

Josephus is deliberately filed in its own section rather than mixed into the
chronological run. He is the primary historical source for the period and
belongs in a volume that wants a whole picture, but he is not scripture in
any canon and the site must not blur that line.

Sources are Project Gutenberg's proofread etexts of William Whiston's 1737
translation, not OCR. Public domain by age.
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/data"
RAW = sys.argv[2] if len(sys.argv) > 2 else "source/extra"

GUT_START = re.compile(r"\*\*\*\s*START OF TH[EI]S? PROJECT GUTENBERG.*?\*\*\*", re.I)
GUT_END = re.compile(r"\*\*\*\s*END OF TH[EI]S? PROJECT GUTENBERG.*?\*\*\*", re.I)

BOOK = re.compile(r"^BOOK ([IVXL]+)\.?(.*)$", re.M)
CHAPTER = re.compile(r"^CHAPTER (\d+)\.?(.*)$", re.M)
SECTION = re.compile(r"^(\d{1,3})\.\s+", re.M)
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII"]

JOSEPHUS = [
    ("2848", "antiquities-of-the-jews", "THE ANTIQUITIES OF THE JEWS",
     "Twenty books, from the creation to the eve of the revolt of 66 CE. "
     "Josephus retells the biblical narrative for a Roman audience and then "
     "carries it forward through the periods no biblical book covers. Book 18 "
     "contains the disputed passage about Jesus known as the Testimonium "
     "Flavianum, and Book 20 mentions James his brother; both are argued over "
     "and neither is settled."),
    ("2850", "the-wars-of-the-jews", "THE WARS OF THE JEWS",
     "Seven books on the revolt against Rome and the destruction of the temple "
     "in 70 CE, written by a commander who changed sides and watched the siege "
     "from the Roman camp. The single most important eyewitness account of the "
     "event that ends the world the New Testament was written in."),
    ("2849", "against-apion", "AGAINST APION",
     "A defence of the antiquity of the Jewish people against Greek critics. "
     "Its first book gives the earliest surviving list of the Jewish scriptures "
     "as a fixed count of twenty-two books, which makes it a primary witness to "
     "how the canon was understood in the first century."),
    ("2846", "the-life-of-flavius-josephus", "THE LIFE OF FLAVIUS JOSEPHUS",
     "Josephus's own account of his career, including his command in Galilee "
     "and his surrender to Vespasian. Read alongside the Wars, the two "
     "sometimes disagree, which is itself informative about him as a witness."),
]


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def strip_gutenberg(text: str) -> str:
    m = GUT_START.search(text)
    if m:
        text = text[m.end():]
    m = GUT_END.search(text)
    if m:
        text = text[:m.start()]
    return text


def unwrap(block: str) -> list[str]:
    paras, buf = [], []
    for line in block.split("\n"):
        if line.strip():
            buf.append(line.strip())
        elif buf:
            paras.append(" ".join(buf))
            buf = []
    if buf:
        paras.append(" ".join(buf))
    return paras


def split_sections(block: str, allow_restart: bool = False) -> list[dict]:
    """Whiston's numbered sections behave like verses.

    Requiring a strictly increasing run keeps stray numerals in the prose from
    being read as section marks. Against Apion restarts its numbering at book
    two inside a single span, so allow_restart lets a fresh run begin at 1
    once a substantial run has already been collected.
    """
    hits = [(m.start(), m.end(), int(m.group(1))) for m in SECTION.finditer(block)]
    kept, expect = [], 1
    for start, end, num in hits:
        if num == expect:
            kept.append((start, end, num))
            expect += 1
        elif allow_restart and num == 1 and len(kept) > 5:
            kept.append((start, end, num))
            expect = 2
    out = []
    for i, (start, end, num) in enumerate(kept):
        stop = kept[i + 1][0] if i + 1 < len(kept) else len(block)
        body = " ".join(unwrap(block[end:stop]))
        body = re.sub(r"\s+", " ", body).strip()
        if body:
            out.append({"v": num, "t": body})
    return out


def parse_flat(text: str, per_chunk: int = 12) -> list[dict]:
    """Against Apion and the Life have no chapter divisions -- just a running
    series of numbered sections. Group them so the reader gets navigable
    pages instead of one endless scroll."""
    text = strip_gutenberg(text)
    books = [(m.start(), m.group(1)) for m in BOOK.finditer(text)]
    spans = []
    if books:
        # Text before the first BOOK marker is book one, whose heading the
        # etext omits. Dropping it would silently lose a third of the work.
        head = text[:books[0][0]]
        if len(split_sections(head)) > 5:
            spans.append(("I", head))
        books.append((len(text), None))
        for i in range(len(books) - 1):
            spans.append((books[i][1], text[books[i][0]:books[i + 1][0]]))
    else:
        spans.append((None, text))

    chapters: list[dict] = []
    for roman, span in spans:
        verses = split_sections(span, allow_restart=True)
        # A restart to 1 marks a new book. Split there, so section numbers stay
        # unique inside each chapter and verse anchors keep working.
        runs: list[list[dict]] = []
        for v in verses:
            if v["v"] == 1 or not runs:
                runs.append([])
            runs[-1].append(v)

        for r, run in enumerate(runs):
            book = roman or (ROMAN[r] if r < len(ROMAN) else str(r + 1))
            for k in range(0, len(run), per_chunk):
                group = run[k:k + per_chunk]
                label = (f"Book {book}, sections {group[0]['v']}-{group[-1]['v']}"
                         if len(runs) > 1 or roman
                         else f"Sections {group[0]['v']}-{group[-1]['v']}")
                chapters.append({
                    "label": label, "n": len(chapters) + 1, "raw": label,
                    "verses": group, "style": "whiston",
                    # These pages are slices of a continuous run of sections,
                    # so they start wherever the slice starts. Tells the audit
                    # not to expect them to begin at section 1.
                    "chunked": True,
                })
    return chapters


def parse_josephus(text: str) -> list[dict]:
    """Return chapters. The table of contents is skipped by requiring that a
    chapter actually contain numbered sections."""
    text = strip_gutenberg(text)
    books = [(m.start(), m.group(1), m.group(2).strip()) for m in BOOK.finditer(text)]
    books.append((len(text), None, None))

    chapters: list[dict] = []
    for i in range(len(books) - 1):
        start, roman, _ = books[i]
        span = text[start:books[i + 1][0]]
        marks = [(m.start(), m.group(1), m.group(2).strip())
                 for m in CHAPTER.finditer(span)]
        marks.append((len(span), None, None))
        for j in range(len(marks) - 1):
            body = span[marks[j][0]:marks[j + 1][0]]
            verses = split_sections(body)
            if len(verses) < 1:
                continue                      # a contents entry, not a chapter
            title = re.sub(r"\s+", " ", marks[j][2]).strip(" .")
            chapters.append({
                "label": f"Book {roman}, Chapter {marks[j][1]}",
                "n": len(chapters) + 1,
                "raw": title[:150],
                "verses": verses,
                "style": "whiston",
            })
    return chapters


def main() -> int:
    manifest_path = os.path.join(OUT, "manifest.json")
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    if any(s["id"] == "josephus" for s in manifest["sections"]):
        print("extras already present; run parse_book.py first")
        return 1

    works, entries = [], []
    for gid, wid, title, note in JOSEPHUS:
        path = os.path.join(RAW, f"{gid}.txt")
        if not os.path.exists(path):
            print(f"missing {path}, skipping {wid}")
            continue
        text = open(path, encoding="utf-8", errors="replace").read()
        chapters = parse_josephus(text) or parse_flat(text)
        if not chapters:
            print(f"no chapters parsed for {wid}")
            continue
        nv = sum(len(c["verses"]) for c in chapters)
        words = sum(v["t"].count(" ") + 1 for c in chapters for v in c["verses"])
        work = {
            "id": wid, "title": title, "section": "josephus",
            "note": [note], "chapters": chapters, "source": "whiston",
        }
        with open(os.path.join(OUT, "works", wid + ".json"), "w",
                  encoding="utf-8") as fh:
            json.dump(work, fh, ensure_ascii=False, separators=(",", ":"))
        entries.append({
            "id": wid, "title": title, "note": [note],
            "chapters": len(chapters), "verses": nv, "words": words,
            "versified": True, "source": "whiston", "positions": None,
            "chapterLabels": [c["label"] for c in chapters],
        })
        works.append((wid, len(chapters), nv, words))

    if not entries:
        print("nothing added")
        return 1

    manifest["sections"].append({
        "id": "josephus",
        "title": "FLAVIUS JOSEPHUS",
        "roman": None,
        "name": "Flavius Josephus",
        "dates": "written 75-99 CE",
        "intro": [
            "Not scripture in any canon. Josephus was a Judean commander who "
            "surrendered to the Romans in 67 CE and wrote for a Roman audience "
            "under imperial patronage, which is worth holding in mind on every "
            "page. He is also the closest thing we have to a contemporary "
            "historian of the world the New Testament was written in, and he "
            "covers long stretches no biblical book touches.",
            "Included here because a volume that claims to give the whole "
            "picture cannot leave out the main external witness to it. Kept in "
            "its own section, rather than mixed into the chronological run, so "
            "that the line between scripture and history stays visible.",
        ],
        "works": entries,
    })

    manifest["sources"]["whiston"] = {
        "label": "William Whiston, 1737",
        "detail": "The standard English Josephus for nearly three centuries, "
                  "public domain by age. Text from Project Gutenberg's "
                  "proofread edition rather than optical character "
                  "recognition. Whiston's own section numbering is retained.",
    }

    t = manifest["totals"]
    t["works"] += len(entries)
    t["chapters"] += sum(w[1] for w in works)
    t["verses"] += sum(w[2] for w in works)
    t["words"] += sum(w[3] for w in works)
    t["sections"] = len(manifest["sections"])

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, separators=(",", ":"))

    for wid, nch, nv, words in works:
        print(f"  {wid:32s} {nch:4d} chapters {nv:6d} sections {words:8d} words")
    print(f"added {len(entries)} works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
