#!/usr/bin/env python3
"""Public-domain readings of the editions this volume prints.

An audiobook of a 1.22-million-word library cannot be recorded here, and for
a long time the answer to that was to synthesise one. It does not have to be.
People have already read these texts aloud and put the recordings in the
public domain, and a person reading beats any voice this repository could run.

What makes it possible at all is that the recordings have to be of the SAME
EDITION as the text on the page. That is a much narrower requirement than "a
reading of the Bible", and it is the whole difficulty. This volume prints the
World English Bible, R. H. Charles's 1917 Enoch and Jubilees, the Ante-Nicene
Fathers, and six texts recovered from nineteenth-century scans. A reading of
the King James, or of Charles Taylor's Hermas, cannot be aligned to any of
them -- the words are different words.

So every entry states the edition it reads, and nothing is attached to a work
on the strength of a title. Two things found while assembling this list are
the reason for that caution:

  - The LibriVox recording catalogued as "Apocrypha" is Plato's apocrypha.
    It is a perfectly good recording of the wrong thing entirely.

  - The LibriVox Shepherd of Hermas is Charles Taylor's translation. This
    volume prints the Ante-Nicene Fathers text. Same work, different English,
    and no alignment between them is possible.

Neither of those is caught by reading a catalogue. Both are caught by trying
to align the audio to the text and failing, which is what tools/align_audio.py
does and why nothing here reaches the reader until it has.

Every URL was checked by hand and resolved before being added. RIGHTS is
stated on each reading so nobody mistakes a public-domain recording for a
public-domain performance right in something else.
"""

from __future__ import annotations

# Edition keys are manifest.sources keys -- the same value a work carries in
# its "source" field -- so a reading and a work can be compared without a
# translation table in between.
READINGS = {
    "web-altman": {
        "narrator": "Ron Altman",
        "reads": "The World English Bible, complete",
        "edition": "web",
        "solo": True,
        "runtime": "98h 05m",
        "recorded": "2025",
        "item": "biblewebcomplete_2510_librivox",
        "url": "https://archive.org/details/biblewebcomplete_2510_librivox",
        "files": "https://archive.org/download/biblewebcomplete_2510_librivox/",
        "licence": "Public Domain Mark 1.0",
        "rights": "Public domain, dedicated by the reader through LibriVox. "
                  "Mirrored rather than hot-linked, and credited where it plays.",
        "why": "The edition this volume prints, read straight through by one "
               "voice. A single reader matters more here than it would in a "
               "novel: the library is read in the order it was written, so a "
               "listener crosses eight centuries in a sitting, and a change "
               "of narrator at every book would be the loudest thing in it.",
    },
    "web-henson": {
        "narrator": "Winfred Wardell Henson",
        "reads": "The World English Bible, complete",
        "edition": "web",
        "solo": True,
        "runtime": "99h 37m",
        "recorded": "2017",
        "item": "worldenglishbible_1707_librivox",
        "url": "https://archive.org/details/worldenglishbible_1707_librivox",
        "files": "https://archive.org/download/worldenglishbible_1707_librivox/",
        "licence": "Public Domain Mark 1.0",
        "rights": "Public domain, dedicated by the reader through LibriVox. "
                  "Mirrored rather than hot-linked, and credited where it plays.",
        "why": "The longer-established of the two complete solo readings of "
               "this edition, and the alternative if the other does not suit "
               "the ear.",
    },
    "web-williams": {
        "narrator": "David Williams",
        "reads": "The World English Bible, complete",
        "edition": "web",
        "solo": True,
        "runtime": "about 75 hours",
        "recorded": "2000-2001",
        "item": None,
        "url": "https://www.audiotreasure.com/webindex.htm",
        "files": "https://www.audiotreasure.com/content/WEBD_AT/zipfiles/",
        "licence": "Released without restriction",
        "rights": "Public domain, released without restriction by the reader. "
                  "Mirrored rather than hot-linked, and credited where it plays.",
        "why": "Already cut one file per chapter, which is the only source "
               "here that needs no slicing at all -- the alignment still has "
               "to run, but only to find the verses inside a chapter that is "
               "already its own file.",
    },
    "enoch-plogue": {
        "narrator": "CJ Plogue",
        "reads": "1 Enoch, in R. H. Charles's translation",
        "edition": "charles",
        "solo": True,
        "runtime": "4h 29m",
        "recorded": "2018",
        "item": "bookofenoch_1812_librivox",
        "url": "https://archive.org/details/bookofenoch_1812_librivox",
        "files": "https://archive.org/download/bookofenoch_1812_librivox/",
        "licence": "Public Domain Mark 1.0",
        "rights": "Public domain, dedicated by the reader through LibriVox. "
                  "Mirrored rather than hot-linked, and credited where it plays.",
        "why": "Charles's translation, which is the one printed here. That it "
               "is the same translation is not a small coincidence: Charles is "
               "the only English Enoch old enough to be public domain, so the "
               "recording and the text arrive at the same edition for the same "
               "reason.",
    },
    "jubilees-librivox": {
        "narrator": "LibriVox volunteers",
        "reads": "Jubilees, in R. H. Charles's translation",
        "edition": "charles",
        "solo": False,
        "runtime": "5h 38m",
        "recorded": "2021",
        "item": "book_jubilees_2108_librivox",
        "url": "https://archive.org/details/book_jubilees_2108_librivox",
        "files": "https://archive.org/download/book_jubilees_2108_librivox/",
        "licence": "Public Domain Mark 1.0",
        "rights": "Public domain, dedicated by the readers through LibriVox. "
                  "Mirrored rather than hot-linked, and credited where it plays.",
        "why": "Charles again, and already one file per chapter. Not a solo "
               "reading -- the voice changes between chapters, and a listener "
               "will hear that. It is offered because a reading in the right "
               "translation is worth more than an even one in the wrong "
               "translation, and there is no other.",
    },
    "tobit-ancientchristian": {
        "narrator": "ancientchristian",
        "reads": "Tobit, from the World English Bible with Deuterocanon",
        "edition": "web",
        "solo": True,
        "runtime": "42m",
        "recorded": "2020",
        "item": "tobit_2005_librivox",
        "url": "https://archive.org/details/tobit_2005_librivox",
        "files": "https://archive.org/download/tobit_2005_librivox/",
        "licence": "Public Domain Mark 1.0",
        "rights": "Public domain, dedicated by the reader through LibriVox. "
                  "Mirrored rather than hot-linked, and credited where it plays.",
        "why": "The only book of the deuterocanon for which a reading of this "
               "edition exists. The others have been recorded from the King "
               "James and the Douay-Rheims, which are different translations "
               "and cannot be used.",
    },
}


# Readings that exist, are public domain, are of a work in this volume, and
# still cannot be used -- each with the reason, so that nobody adds them again
# in six months having found them the same way.
#
# The rule this table serves is the one build_canon.py and build_manuscripts.py
# already keep: a claim a reader cannot check does not belong beside claims
# that were checked. Attaching a recording of one translation to the text of
# another is that kind of claim, and it is the easiest one to make by accident,
# because the catalogue entry looks right.
REJECTED = {
    "shepherdofhermas_2102_librivox":
        "The Shepherd of Hermas in Charles Taylor's translation. This volume "
        "prints the Ante-Nicene Fathers text, which is different English for "
        "the same work. Nothing can be aligned between them.",
    "apocrypha_1605_librivox":
        "Catalogued as 'Apocrypha' and read by a LibriVox volunteer, but it is "
        "Plato's apocrypha -- Hippias Major, Second Alcibiades, Theages -- in "
        "George Burges's translation. It has no connection to this volume at "
        "all beyond the word.",
    "1maccabees_2005_librivox":
        "1 Maccabees from the King James Apocrypha. This volume prints the "
        "World English Bible's deuterocanon.",
    "sirach_2005_librivox":
        "Sirach from the Douay-Rheims. Same objection as the King James "
        "Maccabees: a different translation of the same book.",
    "bible_drv_tobit_version_2_2005_librivox":
        "Tobit from the Douay-Rheims. The World English Bible Tobit is "
        "recorded separately and is the one used.",
}


def by_edition(edition):
    """Every reading of a given edition, newest-sounding first is not a thing
    this can know -- so, in declaration order, which is the order a human put
    them in."""
    return {k: v for k, v in READINGS.items() if v["edition"] == edition}


def credit(reading_id):
    """What the player says while this reading is playing."""
    r = READINGS[reading_id]
    return {
        "narrator": r["narrator"],
        "licence": r["licence"],
        "url": r["url"],
        "rights": r["rights"],
    }
