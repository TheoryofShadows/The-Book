#!/usr/bin/env python3
"""Close gaps in the Apostolic Fathers using a second public-domain edition.

The source compilation drew its Apostolic Fathers from the 1885 Ante-Nicene
Fathers, and inherited that printing's holes. Some of those holes are not
inherent to the public domain at all -- they are artifacts of which edition
was scraped. The 1870 T. & T. Clark Ante-Nicene Christian Library, the same
Roberts-Donaldson translation in an earlier printing, carries material the
1885 scrape lost.

Closed here
    Shepherd of Hermas, Similitude 1 and Similitude 10  -- absent entirely
    Polycarp to the Philippians 14  -- truncated mid-sentence
    Fragments of Papias  -- absent entirely, a work in its own right

    Twenty chapter openings across three works, which were not gaps at all
    but the opposite: the tail of the printing's own chapter heading, left
    standing at the head of the chapter and read as scripture. 1 Clement 24
    began "resurrection." and Ignatius to the Philadelphians 10 began
    "PERSECUTION." The source preparation turned each ANF heading into a
    chapter marker by cutting it at a line break, and whatever stood on the
    second line of a two-line heading stayed in the text. Which chapters
    those are is not guessed: this edition prints the headings in full, so a
    chapter opening that is the end of its own heading can be recognised as
    one and taken off.

Still open, and not closable from this edition
    1 Clement 59:2-61, the great intercessory prayer. This 1870 printing
    predates the 1873 discovery of the Jerusalem manuscript that fills the
    Codex Alexandrinus lacuna, so it has the same gap. Lightfoot's edition of
    1890-91 closes it, and tools/build_lightfoot.py does that from the scan.

Runs after build_extras.py.
"""

from __future__ import annotations

import json
import os
import re
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/data"
RAW = sys.argv[2] if len(sys.argv) > 2 else "source/extra"
EDITION = "77576.txt"

FOOTNOTE = re.compile(r"\[\d+\]")
# [ \t]* rather than \s*: \s crosses newlines, so the trailing (.*) would
# swallow the first line of the chapter's body along with its title.
CHAP = re.compile(r"^[ \t]*CHAP\.[ \t]+([IVXLC]+)\.?[ \t]*(.*)$", re.M)

# The 1870 printing carries the editors' own front matter for each work.
# Same class of contamination the main parser strips, same treatment.
NOTICE = re.compile(r"^[ \t]*INTRODUCTORY NOTICE.*$", re.M)
# Fragment headings are centred roman numerals, and all but the first carry a
# footnote marker: "II.[1790]". Allowing it is what makes fragments 2-10 visible.
FRAGMENT_NUM = re.compile(r"^[ \t]*([IVXL]{1,6})\.(?:\[\d+\])?[ \t]*$", re.M)


def clean(text: str) -> str:
    """Strip the printing's footnote markers and normalise whitespace."""
    text = FOOTNOTE.sub("", text)
    text = text.replace("_", "")
    return re.sub(r"\s+", " ", text).strip()


def body_of(path: str) -> str:
    raw = open(path, encoding="utf-8", errors="replace").read()
    i = raw.find("*** START")
    if i >= 0:
        raw = raw[raw.find("\n", i):]
    j = raw.find("*** END")
    if j >= 0:
        raw = raw[:j]
    return raw


def slice_between(text: str, start_pat: str, end_pat: str) -> str:
    a = re.search(start_pat, text, re.M)
    if not a:
        return ""
    rest = text[a.end():]
    b = re.search(end_pat, rest, re.M)
    return rest[:b.start()] if b else rest


def paragraphs(block: str) -> list[str]:
    out, buf = [], []
    for line in block.split("\n"):
        if line.strip():
            buf.append(line.strip())
        elif buf:
            out.append(clean(" ".join(buf)))
            buf = []
    if buf:
        out.append(clean(" ".join(buf)))
    return [p for p in out if len(p) > 1]


def as_chapters(block: str, label_fmt: str) -> list[dict]:
    """Split on CHAP. markers if present, else one chapter."""
    marks = [(m.start(), m.end(), m.group(1)) for m in CHAP.finditer(block)]
    if not marks:
        paras = paragraphs(block)
        return [{"label": label_fmt.format(""), "n": 1, "raw": label_fmt,
                 "paras": paras, "style": "prose"}] if paras else []
    marks.append((len(block), len(block), None))
    out = []
    for i in range(len(marks) - 1):
        paras = paragraphs(block[marks[i][1]:marks[i + 1][0]])
        if paras:
            out.append({
                "label": label_fmt.format(" " + marks[i][2]),
                "n": len(out) + 1,
                "raw": label_fmt.format(" " + marks[i][2]),
                "paras": paras, "style": "prose",
            })
    return out


# The printing sets each chapter heading as "CHAP. N.--_Title._", and wraps
# it over two lines when it is long. The italic underscores are the Project
# Gutenberg transcription's, not the printer's.
HEADING = re.compile(
    r"CHAP(?:TER)?[.,]?\s+([IVXLC]+)[.,]?\s*[\u2014\u2013-]+\s*_?(.*?)_?"
    r"(?=\n\s*\n)", re.S)

ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}

# Two readings are the same heading when their letters and digits are, which
# is what lets a heading printed in italic capitals in 1885 be matched
# against the same heading printed in lower case in 1870.
def fold(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def numeral(text: str) -> int:
    total = prev = 0
    for ch in reversed(text.upper()):
        value = ROMAN.get(ch, 0)
        total = total - value if value < prev else total + value
        prev = max(prev, value)
    return total


def anf_headings(text: str) -> list[tuple[int, str]]:
    out = []
    for m in HEADING.finditer(text):
        heading = " ".join(m.group(2).split()).rstrip("_")
        if heading:
            out.append((numeral(m.group(1)), heading))
    return out


# How many folded characters of a heading's tail are enough to be sure of it
# on its own. Ten is about two words; below that the coincidences start.
# A shorter tail is taken only when the heading is numbered as the chapter
# it stands at the head of -- Barnabas 14 opens with the single word
# "broke." and Magnesians 15 with "you)," -- because then it is not a
# coincidence between a chapter and some heading somewhere in the volume but
# a chapter and its own.
ENOUGH = 10
LEAST = 3


def leading_heading(para: str, headings: list[tuple[int, str]],
                    number: int) -> int | None:
    """How much of this paragraph is the end of its own chapter heading.

    None when it is not one. The tail has to be a *proper* tail -- a whole
    heading standing at the head of its chapter is a chapter that opens by
    saying what it is about, which several of these do -- and the text has
    to resume at a sentence after it.
    """
    folded = fold(para[:400])
    best = None
    for its_number, heading in headings:
        enough = ENOUGH if its_number != number else LEAST
        for i in range(1, len(heading)):
            if heading[i - 1] != " ":
                continue
            tail = fold(heading[i:])
            if len(tail) < enough or not folded.startswith(tail):
                continue
            end = span(para, len(tail))
            if end is None or not resumes(para, end):
                continue
            # Past the heading's own full stop as well, so what is left is
            # the sentence the chapter really opens with.
            if best is None or end > best:
                best = end + 1
    return best


def span(para: str, folded_length: int) -> int | None:
    """Where the first `folded_length` letters and digits of `para` end."""
    seen = 0
    for i, ch in enumerate(para):
        if fold(ch):
            seen += 1
            if seen == folded_length:
                return i + 1
    return None


RESUMES = re.compile(r"[.!?][\s\u201c\"']*[A-Z\u201c\"(\[]")


def resumes(para: str, end: int) -> bool:
    """True when the heading's own full stop stands where the tail ends."""
    return bool(RESUMES.match(para[end:end + 5]))


def main() -> int:
    path = os.path.join(RAW, EDITION)
    if not os.path.exists(path):
        print(f"missing {path}; skipping repairs")
        return 0
    text = body_of(path)

    manifest_path = os.path.join(OUT, "manifest.json")
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    log: list[str] = []

    def find_section(sid):
        return next((s for s in manifest["sections"] if s["id"] == sid), None)

    def save(work):
        with open(os.path.join(OUT, "works", work["id"] + ".json"), "w",
                  encoding="utf-8") as fh:
            json.dump(work, fh, ensure_ascii=False, separators=(",", ":"))

    def load(wid):
        p = os.path.join(OUT, "works", wid + ".json")
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

    def meta_for(sid, wid):
        s = find_section(sid)
        if not s:
            return None
        return next((w for w in s["works"] if w["id"] == wid), None)

    def restat(work, entry):
        entry["chapters"] = len(work["chapters"])
        entry["verses"] = sum(len(c.get("verses", [])) for c in work["chapters"])
        entry["words"] = sum(
            p.count(" ") + 1
            for c in work["chapters"]
            for p in (c.get("paras", []) + [v["t"] for v in c.get("verses", [])])
        )

    # ---- 1. Hermas Similitudes 1 and 10 ------------------------------
    hermas = find_section("the-shepherd-of-hermas")
    if hermas:
        for name, start, end, where in [
            ("SIMILITUDE 1", r"^\s*SIMILITUDE FIRST\.", r"^\s*SIMILITUDE SECOND\.", 17),
            ("SIMILITUDE 10", r"^\s*SIMILITUDE TENTH\.", r"^\s*FRAGMENTS OF PAPIAS", None),
        ]:
            wid = name.lower().replace(" ", "-")
            if any(w["id"] == wid for w in hermas["works"]):
                continue
            block = slice_between(text, start, end)
            chapters = as_chapters(block, "Similitude " + name.split()[-1] + "{}")
            if not chapters:
                continue
            work = {"id": wid, "title": name, "section": "the-shepherd-of-hermas",
                    "note": ["Absent from the 1885 printing this volume otherwise "
                             "follows; supplied here from the 1870 edition of the "
                             "same Roberts-Donaldson translation."],
                    "chapters": chapters, "source": "anf"}
            save(work)
            entry = {"id": wid, "title": name, "note": work["note"],
                     "versified": False, "source": "anf", "positions": None}
            restat(work, entry)
            if where is None:
                hermas["works"].append(entry)
            else:
                hermas["works"].insert(min(where, len(hermas["works"])), entry)
            log.append(f"added Hermas {name} ({entry['chapters']} ch, "
                       f"{entry['words']} words)")

    # ---- 2. Polycarp to the Philippians, chapter 14 -------------------
    poly = load("the-epistle-of-polycarp-to-the-philippians")
    if poly:
        # "CHAP. XIV." occurs in several works in this volume, so scope the
        # search to Polycarp's epistle before looking for its final chapter.
        anchor = [m.start() for m in
                  re.finditer(r"POLYCARP TO THE PHILIPPIANS", text)]
        region = text[anchor[-1]:] if anchor else text
        block = slice_between(region, r"CHAP\. XIV\.", r"Footnote 316:")
        paras = paragraphs(block)
        # The first paragraph is the printing's chapter title ("-Conclusion."),
        # not text. Drop it, then compare whole bodies rather than first
        # paragraphs, which is what made this silently no-op before.
        if paras and len(paras[0]) < 40 and paras[0].rstrip(".").endswith(
                ("Conclusion", "conclusion")):
            paras = paras[1:]
        if paras:
            last = poly["chapters"][-1]
            old = " ".join(last.get("paras", []))
            if len(" ".join(paras)) > len(old):
                last["paras"] = paras
                save(poly)
                entry = meta_for("the-apostolic-fathers",
                                 "the-epistle-of-polycarp-to-the-philippians")
                if entry:
                    restat(poly, entry)
                log.append("repaired Polycarp to the Philippians 14 "
                           f"({len(old)} -> {len(paras[0])} chars)")

    # ---- 3. Fragments of Papias ---------------------------------------
    fathers = find_section("the-apostolic-fathers")
    if fathers and not any(w["id"] == "fragments-of-papias" for w in fathers["works"]):
        marks = [m.start() for m in re.finditer(r"FRAGMENTS OF PAPIAS", text)]
        if len(marks) > 1:
            block = text[marks[-1]:]
            end = re.search(r"^\s*THE SPURIOUS EPISTLES OF IGNATIUS", block, re.M)
            if end:
                block = block[:end.start()]
            # Drop the editors' 1870 introductory notice. The fragments
            # themselves begin at the first centred roman numeral.
            notice = NOTICE.search(block)
            if notice:
                first = FRAGMENT_NUM.search(block, notice.end())
                if first:
                    block = block[first.start():]

            # Each fragment is its own chapter rather than one long blob.
            marks = [(m.start(), m.end(), m.group(1))
                     for m in FRAGMENT_NUM.finditer(block)]
            chapters = []
            if marks:
                marks.append((len(block), len(block), None))
                for i in range(len(marks) - 1):
                    paras = paragraphs(block[marks[i][1]:marks[i + 1][0]])
                    if paras:
                        chapters.append({
                            "label": f"Fragment {marks[i][2]}",
                            "n": len(chapters) + 1,
                            "raw": f"Fragment {marks[i][2]}",
                            "paras": paras, "style": "prose",
                        })
            if len(chapters) > 1:
                work = {"id": "fragments-of-papias",
                        "title": "THE FRAGMENTS OF PAPIAS",
                        "section": "the-apostolic-fathers",
                        "note": ["Papias, bishop of Hierapolis, wrote five books "
                                 "around 110-140 CE. They are lost; what survives "
                                 "is quotations in later writers, chiefly Eusebius "
                                 "and Irenaeus. He is the earliest witness to who "
                                 "wrote Mark and Matthew, which makes these few "
                                 "paragraphs disproportionately important to how "
                                 "the gospels are dated and attributed.",
                                 "Absent from the source compilation; supplied "
                                 "from the 1870 edition."],
                        "chapters": chapters, "source": "anf"}
                save(work)
                entry = {"id": work["id"], "title": work["title"],
                         "note": work["note"], "versified": False,
                         "source": "anf", "positions": None}
                restat(work, entry)
                fathers["works"].append(entry)
                log.append(f"added Fragments of Papias ({entry['words']} words)")

    # ---- 3b. Ignatius to the Magnesians, chapter 15 --------------------
    #
    # The opposite defect to the one below, and the only one of its kind:
    # here the cut that was meant to take the heading off took the first
    # nine words of the chapter with it, and Magnesians 15 opened "you),
    # who are here for the glory of God". The shorter recension in this
    # edition has the sentence whole.
    mag = load("the-epistle-of-ignatius-to-the-magnesians")
    if mag and mag["chapters"][-1]["n"] == 15:
        last = mag["chapters"][-1]
        opening = "The Ephesians from Smyrna (whence I also write to "
        if last["paras"] and not last["paras"][0].startswith(opening):
            where = text.find(opening)
            if where >= 0:
                whole = paragraphs(text[where:where + 700])[0]
                # Both recensions open with this sentence; the shorter one
                # comes first in the printing, and it is the one this volume
                # follows throughout Ignatius.
                if whole.endswith(last["paras"][0][-40:]):
                    was = last["paras"][0]
                    last["paras"][0] = whole
                    save(mag)
                    entry = meta_for("the-epistles-of-ignatius-of-antioch",
                                     "the-epistle-of-ignatius-to-the-magnesians")
                    if entry:
                        restat(mag, entry)
                    log.append("restored the opening of Ignatius to the "
                               f"Magnesians 15 ({len(was)} -> "
                               f"{len(whole)} chars)")

    # ---- 4. Chapter headings left at the head of their own chapter ----
    #
    # Twenty of them, and every one is the second line of a two-line heading
    # in the printing the source was prepared from. Nothing about the
    # sentence itself says it is a heading -- "resurrection." is a word of
    # English -- so the headings are read out of this edition, which prints
    # them, and a chapter opening is taken off only when it is the end of
    # its own printed heading and the text resumes at a full stop after it.
    #
    # Both halves of that test matter. Without the first, "His pursuers" at
    # the head of Martyrdom of Polycarp 7 looks like the tail of "POLYCARP
    # IS DISCOVERED BY HIS PURSUERS", which it is, except that it is also
    # the first two words Polycarp's story needs. Without the second,
    # Barnabas 19 loses "The way of light", which is its heading and also
    # its opening clause.
    headings = anf_headings(text)
    stripped = []
    for section in manifest["sections"]:
        for entry in section["works"]:
            if entry.get("source") != "anf":
                continue
            work = load(entry["id"])
            if not work:
                continue
            hit = False
            for ch in work["chapters"]:
                paras = ch.get("paras") or []
                if not paras:
                    continue
                cut = leading_heading(paras[0], headings, ch["n"])
                if cut is None:
                    continue
                head, rest = paras[0][:cut], paras[0][cut:].lstrip()
                if not rest:
                    continue
                paras[0] = rest
                hit = True
                stripped.append({
                    "work": entry["id"], "chapter": ch["label"],
                    "removed": head.strip(),
                    "opens": rest[:60].rstrip() + "\u2026",
                })
            if hit:
                save(work)
                restat(work, entry)
    if stripped:
        with open(os.path.join(OUT, "heading-residue.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({
                "note": "Chapter headings from the 1885 printing left "
                        "standing at the head of the chapter they name, "
                        "and read as scripture. Each was the second line "
                        "of a two-line heading; the source preparation cut "
                        "the heading at the line break and kept what "
                        "followed. Recognised against the same headings as "
                        "printed in the 1870 edition, and removed.",
                "source": "source/extra/" + EDITION,
                "removed": stripped,
            }, fh, ensure_ascii=False, indent=1)
        log.append(f"removed {len(stripped)} chapter headings left standing "
                   "at the head of their own chapter")

    # ---- totals --------------------------------------------------------
    t = {"works": 0, "chapters": 0, "verses": 0, "words": 0}
    for s in manifest["sections"]:
        for w in s["works"]:
            t["works"] += 1
            t["chapters"] += w["chapters"]
            t["verses"] += w["verses"]
            t["words"] += w["words"]
    t["sections"] = len(manifest["sections"])
    manifest["totals"] = t

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, separators=(",", ":"))

    for line in log:
        print("  " + line)
    print(f"{len(log)} repairs applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
