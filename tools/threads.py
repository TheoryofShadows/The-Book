#!/usr/bin/env python3
"""Threads: one question, traced across the whole collection in the order the
texts were written.

This is the only thing this volume can do that an ordinary Bible cannot. Read
in canonical order, the development of an idea is invisible -- Daniel sits
among the prophets, Job among the wisdom books, and the centuries between them
are flattened. Read in composition order, you can watch a question get asked,
answered, contradicted and re-answered over eight hundred years.

DISCIPLINE. A thread is an assembly of real verses. Each stop names a work, a
chapter index and a verse, and tools/audit.py resolves every one of them
against the published data and fails the build if any does not exist. The
verse text is never copied into this file; it is pulled live from the same
JSON the reader uses, so a thread cannot drift from the text it quotes.

The connective prose -- the 'why' on each stop -- is editorial, written for
this volume, and the interface says so. It is argument about the texts, not
text. Where a thread contains a genuine disagreement between the sources, it
says that rather than resolving it.
"""

from __future__ import annotations

THREADS = [
    {
        "id": "the-dead",
        "title": "Where do the dead go?",
        "question": "The Hebrew Bible begins with almost no afterlife at all. "
                    "Watching one arrive, and when, is the clearest example of "
                    "an idea developing inside these texts.",
        "closing": "Eight hundred years separate the first stop from the last. "
                   "The hope does not appear all at once and it does not appear "
                   "in calm conditions: it sharpens under persecution, in "
                   "Daniel and in 2 Maccabees, where people are dying for "
                   "refusing to give up the covenant. Whether that makes it a "
                   "human consolation or a revelation arriving when it was "
                   "needed is exactly the question this volume cannot settle "
                   "for you.",
        "stops": [
            {"work": "ezekiel", "chapter": 36, "verses": [4, 11],
             "why": "Exile, c. 590 BCE. The valley of dry bones is the most "
                    "famous resurrection image in the Hebrew Bible, and the "
                    "chapter interprets it itself: the bones are the nation, "
                    "not individuals. This is about Israel coming home."},
            {"work": "job", "chapter": 18, "verses": [25, 26],
             "why": "Job reaches for something past death and the Hebrew is "
                    "notoriously difficult. Read plainly it is a hope of "
                    "vindication; read later it became a resurrection text. "
                    "Both readings are old."},
            {"work": "isaiah-1-39-first-isaiah", "chapter": 25, "verses": [19],
             "why": "The Isaiah apocalypse. Here the dead themselves rise, "
                    "stated without hedging, though still tied to the fate of "
                    "the nation.",
             "aside": "Filed in Section II with the rest of Isaiah 1-39, but "
                      "chapters 24-27 are widely dated centuries later than "
                      "the eighth-century oracles around them. This volume "
                      "keeps the book whole rather than splitting it further, "
                      "so the stop sits earlier in the sections than its likely "
                      "date. Flagged rather than hidden."},
            {"work": "1-enoch-the-book-of-the-watchers-chapters-1-36",
             "chapter": 21, "verses": [3],
             "why": "Enoch is shown the dead held in separate places awaiting "
                    "judgement. Not in most Bibles, and one of the earliest "
                    "detailed geographies of the afterlife in Jewish writing."},
            {"work": "daniel", "chapter": 11, "verses": [2, 3],
             "why": "c. 165 BCE, written during Antiochus IV's persecution. "
                    "The first unambiguous statement in the Hebrew Bible that "
                    "individuals rise, and that they rise to different "
                    "outcomes. Judgement enters the picture."},
            {"work": "2-maccabees", "chapter": 6, "verses": [9, 14],
             "why": "A mother watches seven sons tortured to death and they "
                    "die stating the hope explicitly. This is what the belief "
                    "cost, in the same period it became firm."},
            {"work": "the-wisdom-of-solomon", "chapter": 2, "verses": [1, 4],
             "why": "Written in Greek in Alexandria, and the vocabulary shifts "
                    "with the language: souls in the hand of God, immortality "
                    "rather than bodies rising. Two different pictures now sit "
                    "in the same collection."},
            {"work": "1-thessalonians", "chapter": 3, "verses": [13, 14, 16, 17],
             "why": "c. 50 CE, the earliest surviving Christian document. Its "
                    "subject is grief: members of the congregation have died "
                    "and were not expected to. The answer given is bodily and "
                    "imminent."},
            {"work": "1-corinthians", "chapter": 14, "verses": [20, 42, 44],
             "why": "Paul argues it out at length, and insists the risen body "
                    "is transformed rather than resuscitated. The whole "
                    "Christian claim is staked on one event being real."},
            {"work": "revelation", "chapter": 20, "verses": [3, 4],
             "why": "The end of the arc: not souls escaping the world but "
                    "death itself abolished and the world remade."},
        ],
    },
    {
        "id": "sacrifice-or-justice",
        "title": "Does God want sacrifice, or justice?",
        "question": "Every one of the earliest prophets attacks the sacrificial "
                    "system. In composition order something surprising follows: "
                    "the law prescribing those sacrifices reaches its final "
                    "written form after they wrote.",
        "closing": "This is a real argument inside the collection, not a "
                   "misreading. The prophets are not abolishing the cult; they "
                   "are denying it can substitute for justice. But a reader who "
                   "meets Leviticus first, as canonical order arranges it, will "
                   "hear the prophets as commentary on settled law. In "
                   "composition order the protest comes first.",
        "stops": [
            {"work": "amos", "chapter": 4, "verses": [21, 22, 23, 24],
             "why": "c. 760 BCE, the oldest prophetic book in the collection. "
                    "The first sustained prophetic voice we have opens by "
                    "telling worshippers their worship is hateful."},
            {"work": "hosea", "chapter": 5, "verses": [6],
             "why": "The same generation, the northern kingdom: mercy rather "
                    "than sacrifice. Jesus quotes this line twice."},
            {"work": "isaiah-1-39-first-isaiah", "chapter": 0, "verses": [11, 13, 16, 17],
             "why": "Jerusalem, same century. The offerings are called futile "
                    "and the remedy given is to seek justice and defend the "
                    "orphan and the widow."},
            {"work": "micah", "chapter": 5, "verses": [6, 7, 8],
             "why": "The demand distilled to a single line that has outlived "
                    "every other verse in the book."},
            {"work": "jeremiah", "chapter": 6, "verses": [21, 22, 23],
             "why": "c. 600 BCE, and the sharpest version: Jeremiah says that "
                    "at the exodus God commanded obedience, not offerings."},
            {"work": "leviticus", "chapter": 0, "verses": [1, 2, 3],
             "why": "The priestly legislation, whose final written form is "
                    "dated after all of the above. Traditional dating places it "
                    "with Moses, centuries earlier; the positions panel on "
                    "Leviticus sets out both cases. Either way, the collection "
                    "holds the protest and the system together without "
                    "resolving them."},
            {"work": "psalms", "chapter": 50, "verses": [16, 17],
             "why": "The same tension inside the worship book itself: a broken "
                    "spirit is the sacrifice God will not despise."},
            {"work": "mark", "chapter": 11, "verses": [32, 33],
             "why": "A scribe agrees with Jesus that loving God and neighbour "
                    "outweighs all burnt offerings, and is told he is not far "
                    "from the kingdom. The prophetic line, still running eight "
                    "centuries later."},
        ],
    },
    {
        "id": "who-is-in",
        "title": "Who counts as one of us?",
        "question": "The collection does not speak with one voice about "
                    "outsiders. It argues with itself, and in composition order "
                    "you can see the argument happening.",
        "closing": "These texts are not reconcilable by clever reading, and "
                   "this volume does not try. Deuteronomy excludes; Ruth makes "
                   "an excluded people the ancestor of the king; Third Isaiah "
                   "throws the doors open; Ezra shuts them again in the same "
                   "period. A reader is entitled to notice that and to decide "
                   "what to make of it.",
        "stops": [
            {"work": "deuteronomy", "chapter": 22, "verses": [3],
             "why": "The rule as stated: Moabites excluded from the assembly, "
                    "to the tenth generation."},
            {"work": "isaiah-56-66-third-isaiah", "chapter": 0, "verses": [3, 6, 7],
             "why": "After the return: foreigners and eunuchs, both explicitly "
                    "barred elsewhere in the law, are promised a name better "
                    "than sons and daughters."},
            {"work": "ruth", "chapter": 3, "verses": [13, 17],
             "why": "A Moabite woman, from the excluded people, is named "
                    "great-grandmother of David. The genealogy is the argument."},
            {"work": "jonah", "chapter": 3, "verses": [10, 11],
             "why": "The book ends with God defending his pity for a foreign "
                    "city, against his own prophet, who is furious about it."},
            {"work": "ezra", "chapter": 9, "verses": [10, 11],
             "why": "The same period, the opposite conclusion: foreign wives "
                    "are dissolved and the children sent away. This is in the "
                    "collection too, and is not softened here."},
            {"work": "galatians", "chapter": 2, "verses": [28],
             "why": "Paul's formulation, written around 50 CE — earlier than "
                    "any gospel, and the earliest stop in this thread's "
                    "Christian material."},
            {"work": "acts", "chapter": 9, "verses": [34, 35],
             "why": "Peter, a Jew, in a Roman officer's house, concluding that "
                    "God shows no partiality. The argument does not end; it "
                    "changes venue."},
        ],
    },
    {
        "id": "quoting-enoch",
        "title": "The New Testament quotes a book most Bibles leave out",
        "question": "Jude cites Enoch by name, as prophecy. Because this "
                    "collection carries both, you can read the quotation and "
                    "its source together and check it yourself.",
        "closing": "1 Enoch is scripture in the Ethiopian Orthodox Tewahedo "
                   "Church and in no other major canon. Jude's use of it is not "
                   "a curiosity; it shows that the boundary of authoritative "
                   "writing was still open when the New Testament was being "
                   "written, and that the canon was decided later, by people, "
                   "through a process that took centuries.",
        "stops": [
            {"work": "1-enoch-the-book-of-the-watchers-chapters-1-36",
             "chapter": 0, "verses": [9],
             "why": "1 Enoch, third century BCE. Note the wording, then read "
                    "the next stop."},
            {"work": "jude", "chapter": 0, "verses": [14, 15],
             "why": "Jude, three centuries later, quoting it almost word for "
                    "word and attributing it to 'Enoch, the seventh from "
                    "Adam'. Double brackets in the Enoch text mark words the "
                    "1917 translator restored by conjecture."},
            {"work": "1-enoch-the-book-of-the-watchers-chapters-1-36",
             "chapter": 5, "verses": [1, 2],
             "why": "The Watchers narrative that Jude and 2 Peter both allude "
                    "to when they mention angels who left their proper "
                    "dwelling. Without Enoch, those verses have no referent.",
             "aside": "This thread deliberately alternates between a source and "
                      "the text quoting it, so it moves back and forth in time "
                      "rather than running straight forward. That is the point "
                      "of it."},
            {"work": "2-peter", "chapter": 1, "verses": [4],
             "why": "The same tradition, in the latest-written book of the New "
                    "Testament."},
        ],
    },
]
