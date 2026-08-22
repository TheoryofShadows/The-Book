#!/usr/bin/env python3
"""Surviving manuscripts, linked but never copied.

The Dead Sea Scrolls images and the great codices are all under copyright or
all-rights-reserved terms -- the Israel Antiquities Authority's are explicitly
so. None of that material is reproduced here and none of it can be. Linking,
however, is always permitted, and a link is worth a great deal on its own.

This matters because the site already rests arguments on these objects. The
positions panel on Isaiah cites the Great Isaiah Scroll as evidence that the
book circulated whole; the accuracy report blames a hole in Codex Alexandrinus
for the missing prayer in 1 Clement. Until now a reader had to take both on
trust. Now they can go and look.

Every URL here was checked by hand and resolved before being added. RIGHTS is
stated on each witness so nobody mistakes a link for a licence.
"""

from __future__ import annotations

WITNESSES = {
    "1qisa": {
        "name": "The Great Isaiah Scroll (1QIsaᵃ)",
        "date": "c. 125 BCE",
        "found": "Qumran Cave 1, 1947",
        "holds": "The entire book of Isaiah, all 66 chapters, complete.",
        "why": "A thousand years older than any other complete Hebrew Isaiah, "
               "and the single most important manuscript witness in the "
               "collection. The text runs continuously with no break at "
               "chapter 40, which is the evidence the traditional column cites "
               "for one author. What it proves is that the book already "
               "circulated whole by 125 BCE; whether it was composed whole is "
               "the part still argued over.",
        "url": "http://dss.collections.imj.org.il/isaiah",
        "where": "Israel Museum, Jerusalem",
        "rights": "Images © Israel Museum. Viewable online; not reproduced here.",
    },
    "1qphab": {
        "name": "The Habakkuk Commentary (1QpHab)",
        "date": "late 1st century BCE",
        "found": "Qumran Cave 1, 1947",
        "holds": "Habakkuk 1-2, quoted verse by verse with interpretation.",
        "why": "It quotes the prophet and then reads him as describing the "
               "commentators' own moment, which is the earliest surviving "
               "example of a method the New Testament writers also use.",
        "url": "http://dss.collections.imj.org.il/habakkuk",
        "where": "Israel Museum, Jerusalem",
        "rights": "Images © Israel Museum. Viewable online; not reproduced here.",
    },
    "sinaiticus": {
        "name": "Codex Sinaiticus",
        "date": "c. 330-360 CE",
        "found": "St Catherine's Monastery, Sinai, 1844-1859",
        "holds": "The oldest complete New Testament, with much of the Greek "
                 "Old Testament — and, bound in as scripture, the Epistle of "
                 "Barnabas and the Shepherd of Hermas.",
        "why": "The best single piece of evidence that the canon was still "
               "open in the fourth century. Both Barnabas and Hermas are in "
               "this volume, in the Apostolic Fathers, precisely because "
               "manuscripts like this one treated them as scripture and later "
               "councils did not.",
        "url": "https://www.codexsinaiticus.org/en/",
        "where": "British Library, Leipzig, Sinai and St Petersburg, digitally "
                 "reunited",
        "rights": "© the holding institutions. Viewable online; not reproduced "
                  "here.",
    },
    "alexandrinus": {
        "name": "Codex Alexandrinus",
        "date": "5th century CE",
        "found": "Given to Charles I in 1627",
        "holds": "Most of the Greek Bible, and 1 and 2 Clement.",
        "why": "The manuscript this volume's 1 Clement mostly depends on, and "
               "the reason six of its chapters had to come from somewhere "
               "else: the codex has a lacuna from 57.7 to 63.4, and the great "
               "intercessory prayer is inside it. Bryennios found the whole "
               "letter in a Constantinople manuscript in 1873; Lightfoot "
               "printed it in English in 1891, and chapters 58 to 63 here are "
               "recovered from a scan of that printing.",
        "url": "https://www.bl.uk/collection-items/codex-alexandrinus",
        "where": "British Library, London",
        "rights": "© British Library. Viewable online; not reproduced here.",
    },
    "vaticanus": {
        "name": "Codex Vaticanus",
        "date": "4th century CE",
        "found": "Recorded in the Vatican Library since 1475",
        "holds": "Most of the Greek Old and New Testaments.",
        "why": "With Sinaiticus, one of the two oldest near-complete Greek "
               "Bibles, and a principal witness behind the critical text the "
               "World English Bible follows — including the verses it omits.",
        "url": "https://digi.vatlib.it/view/MSS_Vat.gr.1209",
        "where": "Vatican Library",
        "rights": "© Biblioteca Apostolica Vaticana. Viewable online; not "
                  "reproduced here.",
    },
    "aleppo": {
        "name": "The Aleppo Codex",
        "date": "c. 930 CE",
        "found": "Tiberias; carried to Aleppo, partly lost in 1947",
        "holds": "The Hebrew Bible with full Masoretic vowel and accent "
                 "marking. About a third, including most of the Torah, is now "
                 "missing.",
        "why": "The most authoritative Masoretic manuscript, and the standard "
               "against which the Hebrew text is measured. Its losses are why "
               "printed Hebrew Bibles lean on the Leningrad Codex for the "
               "Torah.",
        "url": "https://www.aleppocodex.org/",
        "where": "Shrine of the Book, Jerusalem",
        "rights": "© Ben-Zvi Institute. Viewable online; not reproduced here.",
    },
    "nash": {
        "name": "The Nash Papyrus",
        "date": "2nd century BCE",
        "found": "Egypt, acquired 1898-1903",
        "holds": "The Ten Commandments and the opening of the Shema.",
        "why": "Before Qumran, the oldest known Hebrew biblical manuscript by "
               "roughly a thousand years. Its order of the commandments does "
               "not match the Masoretic text exactly, which is a small early "
               "warning that the text had a history.",
        "url": "https://cudl.lib.cam.ac.uk/view/MS-OR-00233",
        "where": "Cambridge University Library",
        "rights": "© Cambridge University Library. Viewable online; not "
                  "reproduced here.",
    },
}

# work id -> witnesses that carry it
WORKS = {
    "isaiah-1-39-first-isaiah": ["1qisa", "aleppo"],
    "isaiah-40-55-second-isaiah": ["1qisa", "aleppo"],
    "isaiah-56-66-third-isaiah": ["1qisa", "aleppo"],
    "habakkuk": ["1qphab", "aleppo"],
    "deuteronomy": ["nash", "aleppo"],
    "the-first-epistle-of-clement-to-the-corinthians": ["alexandrinus"],
    "the-second-epistle-of-clement": ["alexandrinus"],
    "the-epistle-of-barnabas": ["sinaiticus"],
}

# Sinaiticus and Vaticanus carry the New Testament entire, so rather than
# listing 27 books by hand the builder attaches them to every work in the
# New Testament section, and Sinaiticus additionally to Hermas.
NT_SECTION_WITNESSES = ["sinaiticus", "vaticanus"]
HERMAS_WITNESSES = ["sinaiticus"]

# Except that the section is arranged by date rather than by canon, and it
# holds two works these Greek codices do not contain. Attaching a witness
# to a work it does not carry is the plainest kind of false citation, and
# the shortcut was making one: 2 Esdras survives in Latin, Syriac and
# Ge'ez and is in no Greek Bible at all, and 4 Baruch is a separate work
# again, printed here from the Armenian.
NT_SECTION_EXCEPT = {
    "2-esdras-4-ezra":
        "Survives in Latin, Syriac, Ethiopic and Armenian; the Greek is "
        "lost and it stands in neither codex.",
    "the-rest-of-the-words-of-baruch":
        "A separate work from the Baruch of the canon, and in neither "
        "codex.",
}
