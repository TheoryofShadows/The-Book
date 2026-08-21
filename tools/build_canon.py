#!/usr/bin/env python3
"""Build the canon-membership dataset and check the volume's own claims.

Each entry maps a canonical book to the canons that receive it and to the
work id (or ids) that hold its text in this volume. Books arranged here under
more than one work -- Isaiah, Zechariah -- list every part.

Canon codes
    tanakh      Jewish Tanakh (24 books by Jewish counting)
    protestant  Protestant Old and New Testament (66)
    catholic    Roman Catholic (73, fixed at Trent, 1546)
    orthodox    Eastern Orthodox (Catholic list plus the Greek additions)
    ethiopian   Ethiopian Orthodox Tewahedo (the widest canon)

Status values
    canon       received as scripture
    appendix    printed, but outside the canon proper
    varies      included in some branches or lists only
"""

from __future__ import annotations

import json
import os
import sys

DATA = sys.argv[1] if len(sys.argv) > 1 else "docs/data"

ALL = ["tanakh", "protestant", "catholic", "orthodox", "ethiopian"]
CHRISTIAN = ["protestant", "catholic", "orthodox", "ethiopian"]
DEUTERO = ["catholic", "orthodox", "ethiopian"]

# name, division, canon status per canon, work ids in this volume
BOOKS: list[tuple[str, str, dict, list[str]]] = []


def add(name, division, canons, works, status="canon"):
    BOOKS.append((name, division, {c: status for c in canons}, works))


# ---- Torah ---------------------------------------------------------------
for n, w in [("Genesis", "genesis"), ("Exodus", "exodus"), ("Leviticus", "leviticus"),
             ("Numbers", "numbers"), ("Deuteronomy", "deuteronomy")]:
    add(n, "Torah", ALL, [w])

# ---- Historical / Former Prophets ----------------------------------------
for n, w, d in [("Joshua", "joshua", "Former Prophets"),
                ("Judges", "judges", "Former Prophets"),
                ("Ruth", "ruth", "Writings"),
                ("1 Samuel", "1-samuel", "Former Prophets"),
                ("2 Samuel", "2-samuel", "Former Prophets"),
                ("1 Kings", "1-kings", "Former Prophets"),
                ("2 Kings", "2-kings", "Former Prophets"),
                ("1 Chronicles", "1-chronicles", "Writings"),
                ("2 Chronicles", "2-chronicles", "Writings"),
                ("Ezra", "ezra", "Writings"),
                ("Nehemiah", "nehemiah", "Writings"),
                ("Esther", "esther-hebrew", "Writings")]:
    add(n, d, ALL, [w])

# ---- Wisdom / Writings ---------------------------------------------------
for n, w in [("Job", "job"), ("Psalms", "psalms"), ("Proverbs", "proverbs"),
             ("Ecclesiastes", "ecclesiastes"), ("Song of Songs", "song-of-songs")]:
    add(n, "Writings", ALL, [w])

# ---- Latter Prophets -----------------------------------------------------
add("Isaiah", "Latter Prophets", ALL,
    ["isaiah-1-39-first-isaiah", "isaiah-40-55-second-isaiah",
     "isaiah-56-66-third-isaiah"])
add("Jeremiah", "Latter Prophets", ALL, ["jeremiah"])
add("Lamentations", "Writings", ALL, ["lamentations"])
add("Ezekiel", "Latter Prophets", ALL, ["ezekiel"])
add("Daniel", "Writings", ALL, ["daniel"])
for n, w in [("Hosea", "hosea"), ("Joel", "joel"), ("Amos", "amos"),
             ("Obadiah", "obadiah"), ("Jonah", "jonah"), ("Micah", "micah"),
             ("Nahum", "nahum"), ("Habakkuk", "habakkuk"),
             ("Zephaniah", "zephaniah"), ("Haggai", "haggai"),
             ("Malachi", "malachi")]:
    add(n, "The Twelve", ALL, [w])
add("Zechariah", "The Twelve", ALL, ["zechariah-1-8", "zechariah-9-14"])

# ---- Deuterocanon --------------------------------------------------------
add("Tobit", "Deuterocanon", DEUTERO, ["tobit"])
add("Judith", "Deuterocanon", DEUTERO, ["judith"])
add("Wisdom of Solomon", "Deuterocanon", DEUTERO, ["the-wisdom-of-solomon"])
add("Sirach (Ecclesiasticus)", "Deuterocanon", DEUTERO, ["sirach-ecclesiasticus"])
add("Baruch", "Deuterocanon", DEUTERO, ["baruch"])
add("Letter of Jeremiah", "Deuterocanon", DEUTERO, ["the-letter-of-jeremiah-baruch-6"])
add("1 Maccabees", "Deuterocanon", DEUTERO, ["1-maccabees"])
add("2 Maccabees", "Deuterocanon", DEUTERO, ["2-maccabees"])
add("Greek Esther (additions)", "Deuterocanon", DEUTERO, ["esther-greek-version"])
add("Prayer of Azariah / Song of the Three", "Deuterocanon", DEUTERO,
    ["the-prayer-of-azariah-and-the-song-of-the-three-greek-daniel-3-24-90"])
add("Susanna", "Deuterocanon", DEUTERO, ["susanna-greek-daniel-13"])
add("Bel and the Dragon", "Deuterocanon", DEUTERO, ["bel-and-the-dragon-greek-daniel-14"])

# ---- Orthodox additions --------------------------------------------------
BOOKS.append(("1 Esdras", "Orthodox canon",
              {"catholic": "appendix", "orthodox": "canon", "ethiopian": "canon"},
              ["1-esdras"]))
BOOKS.append(("2 Esdras (4 Ezra)", "Orthodox canon",
              {"catholic": "appendix", "orthodox": "varies", "ethiopian": "canon"},
              ["2-esdras-4-ezra"]))
BOOKS.append(("Prayer of Manasseh", "Orthodox canon",
              {"catholic": "appendix", "orthodox": "canon", "ethiopian": "canon"},
              ["the-prayer-of-manasseh"]))
BOOKS.append(("3 Maccabees", "Orthodox canon",
              {"orthodox": "canon", "ethiopian": "canon"}, ["3-maccabees"]))
BOOKS.append(("4 Maccabees", "Orthodox canon",
              {"orthodox": "appendix"}, ["4-maccabees"]))
BOOKS.append(("Psalm 151", "Orthodox canon",
              {"orthodox": "canon", "ethiopian": "canon"}, ["psalm-151"]))

# ---- Ethiopian additions -------------------------------------------------
BOOKS.append(("1 Enoch", "Ethiopian canon", {"ethiopian": "canon"},
              ["1-enoch-the-book-of-the-watchers-chapters-1-36",
               "1-enoch-the-book-of-parables-chapters-37-71",
               "1-enoch-the-astronomical-book-chapters-72-82",
               "1-enoch-dream-visions-and-the-epistle-of-enoch-chapters-83-108"]))
BOOKS.append(("Jubilees", "Ethiopian canon", {"ethiopian": "canon"}, ["jubilees"]))
BOOKS.append(("4 Baruch (Paraleipomena Jeremiou)", "Ethiopian canon",
              {"ethiopian": "canon"}, []))
BOOKS.append(("Ethiopic Clement (Qalementos)", "Ethiopian canon",
              {"ethiopian": "canon"}, []))
BOOKS.append(("Ethiopic Didascalia", "Ethiopian canon",
              {"ethiopian": "canon"}, []))
BOOKS.append(("Sinodos", "Ethiopian canon", {"ethiopian": "canon"}, []))
BOOKS.append(("Book of the Covenant (Mets'hafe Kidan)", "Ethiopian canon",
              {"ethiopian": "canon"}, []))

# ---- New Testament -------------------------------------------------------
for n, w, d in [("Matthew", "matthew", "Gospels"), ("Mark", "mark", "Gospels"),
                ("Luke", "luke", "Gospels"), ("John", "john", "Gospels"),
                ("Acts", "acts", "Acts"),
                ("Romans", "romans", "Pauline epistles"),
                ("1 Corinthians", "1-corinthians", "Pauline epistles"),
                ("2 Corinthians", "2-corinthians", "Pauline epistles"),
                ("Galatians", "galatians", "Pauline epistles"),
                ("Ephesians", "ephesians", "Pauline epistles"),
                ("Philippians", "philippians", "Pauline epistles"),
                ("Colossians", "colossians", "Pauline epistles"),
                ("1 Thessalonians", "1-thessalonians", "Pauline epistles"),
                ("2 Thessalonians", "2-thessalonians", "Pauline epistles"),
                ("1 Timothy", "1-timothy", "Pauline epistles"),
                ("2 Timothy", "2-timothy", "Pauline epistles"),
                ("Titus", "titus", "Pauline epistles"),
                ("Philemon", "philemon", "Pauline epistles"),
                ("Hebrews", "hebrews", "Pauline epistles"),
                ("James", "james", "General epistles"),
                ("1 Peter", "1-peter", "General epistles"),
                ("2 Peter", "2-peter", "General epistles"),
                ("1 John", "1-john", "General epistles"),
                ("2 John", "2-john", "General epistles"),
                ("3 John", "3-john", "General epistles"),
                ("Jude", "jude", "General epistles"),
                ("Revelation", "revelation", "Apocalypse")]:
    add(n, d, CHRISTIAN, [w])


# Units that traditional enumeration folds into a parent book rather than
# counting separately. This is why the Catholic canon is "73 books" even
# though the deuterocanonical material arrives in more pieces than that.
FOLDED = {
    "Letter of Jeremiah": "Baruch",
    "Greek Esther (additions)": "Esther",
    "Prayer of Azariah / Song of the Three": "Daniel",
    "Susanna": "Daniel",
    "Bel and the Dragon": "Daniel",
}

# Why each absent book is absent.
#
# Five books of the Ethiopian canon are not in this volume, and until now the
# coverage table named them and stopped there. A gap with no reason beside it
# is an editorial claim without a citation, which is the one thing this volume
# says it does not do. Each entry below says what was looked for, what was
# found, and what would close it -- so that a reader can check the claim, and
# so that the next person to try does not repeat the search.
#
# The common thread is not copyright. Ge'ez texts of all five are public
# domain by age many times over. What is scarce is a *published English
# translation* old enough to be public domain: the standard modern editions
# are twentieth-century and in copyright, and the nineteenth-century work
# stopped after the Didascalia. Translating the Ge'ez here instead is not an
# option that was passed over for effort -- a translation nobody can check
# against a printed edition is exactly the kind of unverifiable claim the rest
# of this repository exists to refuse.
ABSENT_WHY = {
    "Ethiopic Didascalia": (
        "A public-domain English translation exists: Thomas Pell Platt, The "
        "Ethiopic Didascalia, Oriental Translation Fund, London, 1834, "
        "printed with the Ge'ez facing the English. The scanned text is "
        "recoverable -- about 28,000 words of continuous English survive the "
        "OCR -- but it carries the scars of a facing-page scan, and no "
        "independent chapter and verse counts exist to audit the result "
        "against the way the biblical books are audited. It is the one of the "
        "five that could be added, and it is a decision about the standard "
        "rather than a matter of finding the text.",
        "Platt 1834, archive.org/details/ethiopicdidascal00platrich"),
    "4 Baruch (Paraleipomena Jeremiou)": (
        "No public-domain English translation located. The 1889 Rendel Harris "
        "edition is the Greek text with a critical introduction, not a "
        "translation, and the standard English versions are twentieth-century "
        "and in copyright.",
        "Harris 1889, archive.org/details/restwordsbaruch01harrgoog"),
    "Ethiopic Clement (Qalementos)": (
        "Public domain in parts only. The second of its seven books circulates "
        "separately as the Ethiopic Apocalypse of Peter and has been "
        "translated; the remaining six have no public-domain English "
        "translation. Printing a seventh of a book as the book would be worse "
        "than the gap.",
        "Ethiopian Orthodox canon lists; see the coverage note above"),
    "Sinodos": (
        "No public-domain English translation. It is a large collection of "
        "canons, prayers and church order ascribed to Clement of Rome, and "
        "the scholarly editions of it are modern.",
        "Ethiopian Orthodox canon lists; see the coverage note above"),
    "Book of the Covenant (Mets'hafe Kidan)": (
        "Public domain in part only. Its second part, the discourse of the "
        "risen Lord to the disciples, corresponds to the Epistle of the "
        "Apostles and has a public-domain English translation; the first "
        "part, sections 1-60 on church order, does not.",
        "Ethiopian Orthodox canon lists; see the coverage note above"),
}

# The number each tradition actually uses for itself, with the caveat that
# makes the number meaningful.
TRADITIONAL = {
    "tanakh": (24, "24 books. Samuel, Kings, Chronicles and Ezra-Nehemiah are "
                   "one book each, and the twelve minor prophets are counted "
                   "as a single book, The Twelve."),
    "protestant": (66, "66 books: the same content as the Tanakh, divided into "
                       "39, plus the 27 of the New Testament."),
    "catholic": (73, "73 books, fixed at the Council of Trent in 1546. The "
                     "Letter of Jeremiah is counted inside Baruch, and the "
                     "Greek additions inside Esther and Daniel."),
    "orthodox": (0, "No single fixed number. Eastern Orthodoxy receives the "
                    "Catholic list plus 1 Esdras, 3 Maccabees, the Prayer of "
                    "Manasseh and Psalm 151, and speaks of anagignoskomena, "
                    "books that are read, rather than a sharp boundary."),
    "ethiopian": (81, "Usually given as 81 books, though the enumeration "
                      "differs between lists. The only canon that receives "
                      "1 Enoch and Jubilees as scripture."),
}


def main() -> int:
    manifest = json.load(open(os.path.join(DATA, "manifest.json"), encoding="utf-8"))
    have = {w["id"]: w for s in manifest["sections"] for w in s["works"]}

    books = []
    for name, division, canons, works in BOOKS:
        missing = [w for w in works if w not in have]
        present = bool(works) and not missing
        books.append({
            "name": name,
            "division": division,
            "canons": canons,
            "works": works,
            "present": present,
            "foldedInto": FOLDED.get(name),
        })
        if not present:
            why = ABSENT_WHY.get(name)
            if why is None:
                print(f"UNCITED  {name}: absent with no reason recorded")
                return 1
            books[-1]["absentWhy"], books[-1]["absentSource"] = why
        if missing:
            print(f"BAD-REF  {name}: work ids not in data: {missing}")

    counts = {}
    for canon in ALL:
        got = [b for b in books if b["canons"].get(canon) == "canon"]
        distinct = [b for b in got if not b["foldedInto"]]
        number, caveat = TRADITIONAL[canon]
        counts[canon] = {
            "units": len(got),
            "distinctBooks": len(distinct),
            "traditionalCount": number or None,
            "caveat": caveat,
            "presentInVolume": sum(1 for b in got if b["present"]),
            "absent": [b["name"] for b in got if not b["present"]],
        }

    out = {"canons": ALL, "books": books, "coverage": counts}
    with open(os.path.join(DATA, "canon.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    for canon, c in counts.items():
        print(f"{canon:11s} units={c['units']:3d} distinct={c['distinctBooks']:3d} "
              f"traditional={str(c['traditionalCount'] or '-'):>4s}  "
              f"in volume={c['presentInVolume']:3d}  absent={c['absent']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
