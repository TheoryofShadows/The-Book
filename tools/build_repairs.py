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

Still open, and not closable from this edition
    1 Clement 59:2-61, the great intercessory prayer. This 1870 printing
    predates the 1873 discovery of the Jerusalem manuscript that fills the
    Codex Alexandrinus lacuna, so it has the same gap. Lightfoot's edition of
    1890-91 would close it.
    Ignatius to the Smyrnaeans 13.

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
        entry["chapterLabels"] = [c["label"] for c in work["chapters"]]

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
