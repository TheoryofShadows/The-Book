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
import re
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
              {"ethiopian": "canon"}, ["the-rest-of-the-words-of-baruch"]))
BOOKS.append(("Ethiopic Clement (Qalementos)", "Ethiopian canon",
              {"ethiopian": "canon"}, ["the-apocalypse-of-peter"]))
BOOKS.append(("Ethiopic Didascalia", "Ethiopian canon",
              {"ethiopian": "canon"}, ["the-ethiopic-didascalia"]))
BOOKS.append(("Sinodos", "Ethiopian canon", {"ethiopian": "canon"},
              ["the-sinodos", "the-apostolic-canons"]))
BOOKS.append(("Book of the Covenant (Mets'hafe Kidan)", "Ethiopian canon",
              {"ethiopian": "canon"},
              ["the-testament-of-our-lord", "the-book-of-the-covenant"]))

# Books of the Ethiopian canon this table did not name at all. A coverage
# table that leaves a canon's own books off it is not reporting a gap, it
# is hiding one: the count came out flattering because the books nobody
# could supply were never counted. The three Meqabyan are not the Greek
# Maccabees under another spelling -- they are three separate works,
# composed in Ge'ez, that exist in no other canon -- and Josippon stands
# in the Ethiopian Old Testament as its forty-sixth book.
BOOKS.append(("1 Meqabyan", "Ethiopian canon", {"ethiopian": "canon"}, []))
BOOKS.append(("2 Meqabyan", "Ethiopian canon", {"ethiopian": "canon"}, []))
BOOKS.append(("3 Meqabyan", "Ethiopian canon", {"ethiopian": "canon"}, []))
BOOKS.append(("Josippon (Zena Ayhud)", "Ethiopian canon",
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

# Chapters of canonical books that this volume also prints on their own,
# beside the early poem or the excavated object they belong with. They are
# not books, and the table above rightly does not list them as anybody's
# text: the whole book is elsewhere in the volume and that is where a canon's
# coverage is counted.
#
# They have to be named all the same, because a work in none of the lists
# above looks exactly like a work no canon receives, and these five are the
# opposite of that. The Decalogue is in every Bible there is. Anything that
# reads the gap between the manifest and this table as "the books left out" --
# the search does -- would otherwise hand a reader Deuteronomy 5 as a book
# their Bible does not have, which is a worse error than the one it fixes.
#
# The book each reproduces is named so the claim can be checked against the
# work's own note, and main() refuses to build if a sixth appears without
# being classed either way.
EXCERPTS = {
    "the-song-of-the-sea-exodus-15": "Exodus",
    "the-song-of-deborah-judges-5": "Judges",
    "numbers-6-the-priestly-blessing-is-verses-24-26": "Numbers",
    "deuteronomy-5-the-decalogue": "Deuteronomy",
    "deuteronomy-6-the-shema-is-verses-4-9": "Deuteronomy",
}

# Why each absent book is absent, and what is missing from each book that is
# here in part.
#
# Five books of the Ethiopian canon were absent from this volume, and the
# coverage table used to name them and stop there. A gap with no reason
# beside it is an editorial claim without a citation, which is the one thing
# this volume says it does not do, so each entry says what was looked for and
# what was found. Four of the five are now here, and the same rule applies to
# them in reverse: a book printed in part must say which part, in the place a
# reader is being told it is present.
#
# The common thread was never copyright. Ge'ez texts of all five have been
# public domain for centuries. What is scarce is a *published English
# translation* old enough to be public domain: the standard modern editions
# are twentieth-century and in copyright. What was wrong was the belief that
# the nineteenth-century work stopped after Platt's Didascalia. It did not --
# Horner in 1904, Issaverdens in 1901 and James in 1924 between them cover
# three more -- and tools/fetch_scans.py and tools/build_ethiopian.py print
# what they found. Translating the Ge'ez here instead remains not an option:
# a translation nobody can check against a printed edition is exactly the
# kind of unverifiable claim the rest of this repository exists to refuse.
# All three Meqabyan share one reason, so it is written once.
_MEQABYAN = (
    "No public-domain English translation. These are three works composed "
    "in Ge'ez and found in no other canon, and the first English of them "
    "is twenty-first century: D. P. Curtin released the first chapter of "
    "1 Meqabyan to the public domain and no more, and the complete "
    "translations that exist are under copyright or under a share-alike "
    "licence, which is not the same thing as public domain and is not the "
    "rule this volume prints under.",
    "D. P. Curtin, First Book of Ethiopian Maccabees, 2018, chapter 1, "
    "released to the public domain; en.wikisource.org/wiki/"
    "First_Book_of_Ethiopian_Maccabees")

ABSENT_WHY = {
    "1 Meqabyan": _MEQABYAN,
    "2 Meqabyan": _MEQABYAN,
    "3 Meqabyan": _MEQABYAN,
    "Josippon (Zena Ayhud)": (
        "No public-domain English of the Ge'ez. The Ethiopic Zena Ayhud is "
        "a recension of the Hebrew Josippon, which reached English in 1558 "
        "in Peter Morwyng's translation and was reprinted into the "
        "eighteenth century \u2014 but that is the Hebrew, and the Ethiopic "
        "is an abridgement made through Arabic and differs from it "
        "substantially. Printing one as the other would be a bigger claim "
        "than this volume makes anywhere else.",
        "Peter Morwyng, The Wonderful and Most Deplorable History of the "
        "Latter Times of the Jews, London, 1558 and later editions"),
}

# A book that is here, but not all of it. Each says what is printed, what is
# not, and where the boundary comes from.
PARTIAL = {
    "Sinodos": (
        "Two of its parts, both from the Ge'ez: Horner's Statutes of the "
        "Apostles \u2014 seventy-two statutes and thirteen prayers \u2014 "
        "and Schodde's fifty-seven Apostolic Canons. The Sinodos is a body "
        "of canon law that Ethiopian lists divide into four books, and the "
        "remaining material has no public-domain English translation.",
        "G. Horner, The Statutes of the Apostles, London, 1904, pp. 127-232; "
        "G. H. Schodde, Journal of the Society of Biblical Literature and "
        "Exegesis 5 (1885), pp. 61-72"),
    "Ethiopic Clement (Qalementos)": (
        "One piece of one of its seven books. The Apocalypse of Peter "
        "survives embedded in the Ethiopic Books of Clement and M. R. James "
        "translated that Ethiopic in 1924 \u2014 but only as far as the "
        "point where he judged the rest of it late, saying so and stopping. "
        "The other six books have no public-domain English translation at "
        "all. What is here is worth reading and is not the book.",
        "M. R. James, The Apocryphal New Testament, Oxford, 1924, "
        "pp. 505-521"),
    "Book of the Covenant (Mets'hafe Kidan)": (
        "Both of its books, and neither of them from the Ge'ez in full. The "
        "second, the discourse of the risen Lord, is James's English of the "
        "Ethiopic Guerrier published. The first, the church order, is here "
        "as the Syriac Testamentum Domini in Cooper and Maclean's English: "
        "the same work in another version, because the Ethiopic of it was "
        "unpublished when they wrote and has no public-domain English now.",
        "M. R. James, The Apocryphal New Testament, Oxford, 1924, "
        "pp. 485-503; J. Cooper and A. J. Maclean, The Testament of Our "
        "Lord, Edinburgh, 1902, pp. 47-138"),
    "4 Baruch (Paraleipomena Jeremiou)": (
        "Whole, but not from the Ge'ez. No public-domain English translation "
        "of the Ge'ez exists; what is printed is the Armenian recension made "
        "from the Greek that the Ge'ez also descends from, in Issaverdens's "
        "English. A witness to the work in another version.",
        "J. Issaverdens, The Uncanonical Writings of the Old Testament found "
        "in the Armenian MSS. of the Library of St. Lazarus, Venice, 1901, "
        "pp. 282-304"),
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
        elif name in PARTIAL:
            books[-1]["partialWhy"], books[-1]["partialSource"] = PARTIAL[name]
        if missing:
            print(f"BAD-REF  {name}: work ids not in data: {missing}")

    # ---- the excerpts, and the gate that keeps their list complete --------
    in_canon = {w for b in books for w in b["works"]}
    named = {b["name"] for b in books}

    stray_ids = sorted(w for w in EXCERPTS if w not in have)
    if stray_ids:
        print(f"BAD-REF  excerpts: work ids not in data: {stray_ids}")
        return 1
    stray_books = sorted({b for b in EXCERPTS.values() if b not in named})
    if stray_books:
        print(f"BAD-REF  excerpts: not books in this table: {stray_books}")
        return 1
    both = sorted(set(EXCERPTS) & in_canon)
    if both:
        print(f"BAD-REF  excerpts also listed as a book's own text: {both}")
        return 1

    # A work that is in no canon and in no line above is a book no canon
    # receives -- the Apostolic Fathers, the apocrypha, Hermas. A work whose
    # title names a canonical book and a chapter of it is not, and the cost of
    # the two being confused falls entirely on the reader. So the confusable
    # case is a build failure rather than a silent one: "ISAIAH 53" added to
    # the discoveries section stops the build until somebody says which it is.
    chapter_of = re.compile(
        r"\b(" + "|".join(re.escape(n) for n in sorted(named, key=len, reverse=True))
        + r")\s+\d+\b", re.I)
    unclassed = []
    for wid, work in have.items():
        if not work.get("chapters") or wid in in_canon or wid in EXCERPTS:
            continue
        hit = chapter_of.search(work["title"])
        if hit:
            unclassed.append((wid, hit.group(0)))
    if unclassed:
        for wid, hit in sorted(unclassed):
            print(f"UNCLASSED  {wid}: the title names {hit!r}, so this is "
                  "either a book's own text or an excerpt of one. Add it to "
                  "BOOKS or to EXCERPTS.")
        return 1

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

    out = {"canons": ALL, "books": books, "coverage": counts,
           "excerpts": EXCERPTS}
    with open(os.path.join(DATA, "canon.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    for canon, c in counts.items():
        print(f"{canon:11s} units={c['units']:3d} distinct={c['distinctBooks']:3d} "
              f"traditional={str(c['traditionalCount'] or '-'):>4s}  "
              f"in volume={c['presentInVolume']:3d}  absent={c['absent']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
