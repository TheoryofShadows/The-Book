#!/usr/bin/env python3
"""Threads: one question, traced across the whole collection in the order the
texts were written.

This is the only thing this volume can do that an ordinary Bible cannot. Read
in canonical order, the development of an idea is invisible -- Daniel sits
among the prophets, Job among the wisdom books, and the centuries between them
are flattened. Read in composition order, you can watch a question get asked,
answered, contradicted and re-answered over eight hundred years.

DISCIPLINE. A thread is an assembly of real verses. Each stop names a work, a
chapter index and a verse, and tools/build_threads.py resolves every one of
them against the published data and refuses to write the file if any does not
exist. The verse text is never copied into this file; it is pulled live from
the same JSON the reader uses, so a thread cannot drift from the text it
quotes.

The connective prose -- the 'why' on each stop -- is editorial, written for
this volume, and the interface says so. It is argument about the texts, not
text. Where a thread contains a genuine disagreement between the sources, it
says that rather than resolving it.

WHICH QUESTIONS. The first six were chosen because the arrangement makes them
answerable. The five after them were chosen the other way round -- from what
people actually ask -- and since that is an editorial claim it carries its
sources:

    what a woman may do   #1 on the top twenty GotQuestions.org publishes
                          from the questions put to it
                          https://www.gotquestions.org/top20.html
    divorce               #20 on the same list
    who wrote it          heads the lists compiled from search rather than
                          from submitted questions, together with when it
                          was written and where it came from
                          https://forallthings.bible/top-91-most-frequently-
                          asked-questions-about-the-bible/
    the end of the world  one of the named subject headings of that site's
                          hundred-question collection
    where Satan comes     no list of that kind cited for it. It is here
    from                  because it is the sharpest instance in the volume
                          of the thing these threads exist to show: one
                          scene told twice, centuries apart, with a
                          different agent in the second telling.

Where a thread shares a title with one of those questions it is not answering
it in their sense. It shows what the collection says on the subject, in the
order the collection said it, contradictions included.

That rule also decides what is left out. Much of the frequently asked list is
a request for a ruling -- tattoos, gambling, tithing, what a believer should
do. A ruling is not something a chronological arrangement can produce, and a
thread that tried would be this volume asserting an editorial position with no
citation behind it, which is the one move it says it does not make. The five
here were picked from the list because each is a question the texts themselves
answer more than once, and differently.
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
             "outOfOrder": True,
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
        "id": "what-is-god-like",
        "question": "The oldest surviving line in this collection calls God a "
                    "man of war. The latest says God is love. Everything in "
                    "between is the same collection changing its mind, or "
                    "being shown more.",
        "title": "What is God like?",
        "closing": "Two readings of this sequence are available and the volume "
                   "does not choose between them. One is that a people's idea "
                   "of God grew as they did, from a tribal war deity into "
                   "something universal. The other is that a real God revealed "
                   "himself gradually, to people who could only receive so much "
                   "at a time. The passages are identical either way. What you "
                   "make of them is not a matter the arrangement can decide.",
        "stops": [
            {"work": "the-song-of-the-sea-exodus-15", "chapter": 0, "verses": [3, 11],
             "why": "The oldest continuous text in the volume, archaic Hebrew, "
                    "perhaps the twelfth century BCE. God is a warrior who "
                    "drowns an army, and the question asked is who is like him "
                    "among the gods — not whether other gods exist."},
            {"work": "hosea", "chapter": 10, "verses": [8, 9],
             "why": "Eighth century. Something new: God torn about punishing, "
                    "and the reason given for relenting is that he is God and "
                    "not a man. Divine unlikeness becomes a reason for mercy "
                    "rather than for terror."},
            {"work": "isaiah-1-39-first-isaiah", "chapter": 5, "verses": [3, 5],
             "why": "The temple vision. Holiness is the defining attribute, and "
                    "the prophet's first reaction to seeing it is to think he "
                    "is about to die."},
            {"work": "ezekiel", "chapter": 0, "verses": [26, 28],
             "why": "In exile, far from the temple, Ezekiel sees the throne "
                    "mobile and above him in Babylon. The language piles up "
                    "hedges — likeness, appearance, as it were — because he is "
                    "describing something he says cannot be described."},
            {"work": "isaiah-40-55-second-isaiah", "chapter": 5, "verses": [5, 7],
             "why": "The decisive moment. Not merely that Israel should worship "
                    "one God, but that there is no other, and that this God "
                    "forms light and creates darkness. Monotheism stated "
                    "outright, and with it the problem of evil arrives."},
            {"work": "job", "chapter": 37, "verses": [4],
             "why": "Job demands an answer and receives a tour of creation "
                    "instead. God's reply is not a justification; it is a "
                    "question about how little Job can see."},
            {"work": "daniel", "chapter": 6, "verses": [9, 13],
             "why": "c. 165 BCE. The Ancient of Days on a throne of flame, and "
                    "beside him one like a son of man receiving dominion. A "
                    "second figure appears in the divine scene."},
            {"work": "1-enoch-the-book-of-parables-chapters-37-71",
             "chapter": 9, "verses": [1, 2],
             "why": "Enoch's Parables develop that figure further, and call God "
                    "the Lord of Spirits throughout. Not scripture in most "
                    "canons, but the vocabulary the gospels' audience already "
                    "had."},
            {"work": "john", "chapter": 0, "verses": [1, 14],
             "why": "The most radical claim in the collection: that the God of "
                    "the Song of the Sea took a body and lived in a street."},
            {"work": "1-john", "chapter": 3, "verses": [8],
             "why": "Three words, written perhaps eleven centuries after the "
                    "war hymn, in the same book."},
        ],
    },
    {
        "id": "innocent-suffering",
        "title": "Why do the innocent suffer?",
        "question": "The collection states a rule, then spends centuries "
                    "attacking it. This is the clearest case of these texts "
                    "arguing with one another rather than agreeing.",
        "closing": "No stop here cancels the others. Deuteronomy's rule is "
                   "still in the book that contains Job's refutation of it, and "
                   "Ecclesiastes' flat observation that the same fate meets "
                   "everyone was never edited out. A collection assembled to "
                   "reassure would not have kept all three. Whatever else that "
                   "means, it means the people who preserved these texts were "
                   "willing to preserve the objection.",
        "stops": [
            {"work": "deuteronomy", "chapter": 27, "verses": [1, 15],
             "why": "The rule, stated as plainly as it ever gets: obey and be "
                    "blessed, disobey and be cursed. Much of the collection "
                    "assumes this, and much of the rest exists to dispute it."},
            {"work": "habakkuk", "chapter": 0, "verses": [13],
             "why": "Late seventh century. A prophet accuses God directly of "
                    "watching treachery and doing nothing. The complaint is in "
                    "scripture, not answered from outside it."},
            {"work": "job", "chapter": 20, "verses": [7],
             "why": "Job takes the rule and inverts it with the evidence: the "
                    "wicked grow old and powerful. His friends defend the rule "
                    "for thirty chapters and God tells them at the end that "
                    "they were wrong and Job was right."},
            {"work": "psalms", "chapter": 72, "verses": [2, 3, 16, 17],
             "why": "Psalm 73 admits the writer nearly lost his footing over "
                    "this, and resolves it only by going into the sanctuary — "
                    "an answer that is honest about being a change of vantage "
                    "rather than an argument."},
            {"work": "ecclesiastes", "chapter": 7, "verses": [14],
             "why": "The bleakest verse on the subject, and it was kept: "
                    "righteous men get what the wicked deserve, and wicked men "
                    "get what the righteous deserve."},
            {"work": "the-wisdom-of-solomon", "chapter": 2, "verses": [1, 2, 4],
             "why": "A resolution arrives, and it arrives only once an "
                    "afterlife does: the righteous seemed to die, but they are "
                    "at peace. The problem is answered by moving the accounting "
                    "past death."},
            {"work": "john", "chapter": 8, "verses": [2, 3],
             "why": "Asked whose sin caused a man's blindness, Jesus rejects "
                    "the premise of the question outright. The retribution rule "
                    "is denied to its face."},
            {"work": "romans", "chapter": 7, "verses": [18, 28],
             "why": "Paul does not explain suffering away. He argues that it is "
                    "not the last word and not worth comparing to what follows "
                    "— a claim about the ending, not a solution to the problem."},
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
             "outOfOrder": True,
             "aside": "This thread deliberately alternates between a source and "
                      "the text quoting it, so it moves back and forth in time "
                      "rather than running straight forward. That is the point "
                      "of it."},
            {"work": "2-peter", "chapter": 1, "verses": [4],
             "why": "The same tradition, in the latest-written book of the New "
                    "Testament."},
        ],
    },
    {
        "id": "who-wrote-it",
        "title": "Who wrote the Bible?",
        "question": "The most asked question about this collection, and the "
                    "texts answer part of it themselves. Several of them "
                    "describe being written, edited, burned, rewritten, "
                    "abridged and read aloud, by people who give their names.",
        "closing": "None of this settles the authorship of the books that name "
                   "no author, which is most of them. What it does show is that "
                   "the collection never presented itself as arriving whole. It "
                   "contains a scroll being dictated to a secretary, burned by "
                   "a king and dictated again longer than before; a historian "
                   "apologising for the labour of abridging somebody else's "
                   "five volumes; a writer explaining that others had written "
                   "first and he thought he would do better; and a letter "
                   "complaining that Paul is hard to understand. A book that "
                   "shows its own workings is not thereby proved true or false. "
                   "It is proved to be a book.",
        "stops": [
            {"work": "deuteronomy", "chapter": 30, "verses": [24, 26],
             "why": "The collection's own account of its beginning: Moses "
                    "finishes writing the law in a book and it is laid beside "
                    "the ark. Deuteronomy is filed here, in the seventh "
                    "century, because critical scholarship reads it as the "
                    "book at the centre of Josiah's reform — the next stop."},
            {"work": "2-kings", "chapter": 21, "verses": [8, 11],
             "why": "The eighteenth year of Josiah, 622 BCE by the usual "
                    "reckoning, and a book of the law is found in the temple "
                    "by a high priest who did not know it was there. The king's "
                    "reaction — he tears his clothes — is the reaction of a "
                    "man hearing it for the first time. Whether this is a "
                    "rediscovery or a debut is the oldest live question in "
                    "the study of these texts."},
            {"work": "jeremiah", "chapter": 35, "verses": [4, 23, 32],
             "why": "A book being made, in three verses. Jeremiah dictates, "
                    "Baruch writes; the king cuts the scroll up and burns it "
                    "column by column; Jeremiah dictates it again — and the "
                    "chapter says the second edition was longer. Whatever "
                    "Jeremiah is, it is not one dictation."},
            {"work": "nehemiah", "chapter": 7, "verses": [1, 2, 8],
             "why": "The book read aloud to everyone at once, and note the "
                    "last clause: they gave the sense, so that the people "
                    "understood. Interpretation is not something that "
                    "happened to these texts later. It is in the scene where "
                    "they are first published."},
            {"work": "sirach-ecclesiasticus", "chapter": 49, "verses": [27],
             "why": "A signature, which is rare enough here to be startling. "
                    "Almost every book in the Hebrew Bible is anonymous or "
                    "attributed to a figure from its own past; this writer "
                    "gives his name, his father's name and his city."},
            {"work": "2-maccabees", "chapter": 1, "verses": [23, 26],
             "why": "And an editor, describing his method and how much he "
                    "disliked doing it. He is condensing five books by Jason "
                    "of Cyrene, which do not survive, and he says so in the "
                    "second chapter rather than hiding it."},
            {"work": "romans", "chapter": 15, "verses": [22],
             "why": "The secretary signs his own name in the middle of Paul's "
                    "greetings. Paul dictated; Tertius wrote; and for one "
                    "verse the man holding the pen says hello."},
            {"work": "luke", "chapter": 0, "verses": [1, 3],
             "why": "The only preface in the New Testament, and it is a "
                    "historian's: others have written accounts already, he "
                    "has looked into it himself, and this is his ordered "
                    "version for a named reader. It states its sources as "
                    "eyewitnesses at second hand rather than as itself."},
            {"work": "2-peter", "chapter": 2, "verses": [15, 16],
             "why": "The latest-written book in the New Testament refers to "
                    "Paul's letters as a body of writing already in "
                    "circulation, sets them beside 'the other Scriptures', "
                    "and remarks that they are hard to understand. The "
                    "collection is here quoting itself, and beginning to "
                    "close."},
        ],
    },
    {
        "id": "where-satan-comes-from",
        "title": "Where does Satan come from?",
        "question": "The adversary of the New Testament is not in the earliest "
                    "texts, and the road by which he arrives is one of the "
                    "clearest developments in the collection. Twice a later "
                    "book retells an older scene and gives to Satan what the "
                    "older one gave to God.",
        "closing": "Two readings are available and this volume does not choose "
                   "between them. One is that a figure was invented to carry "
                   "the blame that early Israel had put on God directly, and "
                   "that later writers found the older wording intolerable. "
                   "The other is that the same reality was disclosed gradually, "
                   "and that the earliest texts speak loosely of God causing "
                   "what he permits. What is not in dispute is the order: the "
                   "census is told twice, four centuries apart, and the second "
                   "telling has a different agent in it.",
        "stops": [
            {"work": "1-samuel", "chapter": 15, "verses": [14],
             "why": "In the older narrative books there is no rival power. "
                    "An evil spirit troubles Saul and the text says "
                    "plainly whose it is."},
            {"work": "2-samuel", "chapter": 23, "verses": [1],
             "why": "David's census, which the story goes on to punish with a "
                    "plague. Here it is Yahweh who moves him to it. Hold the "
                    "verse: 1 Chronicles retells it further down this thread."},
            {"work": "genesis", "chapter": 2, "verses": [1, 4, 5],
             "why": "The serpent, in the chapter everyone attaches to Satan. "
                    "It is called an animal of the field, it is never named "
                    "as anything else, and no surviving writer identifies it "
                    "with the devil until the Wisdom of Solomon, further down "
                    "this thread."},
            {"work": "job", "chapter": 0, "verses": [6, 7, 12],
             "why": "The Hebrew has ha-satan, 'the accuser' — a title with a "
                    "definite article rather than a name, and the World "
                    "English Bible's capital S is a translator's decision. He "
                    "is a member of the heavenly court, he reports to God, "
                    "and he acts only by permission."},
            {"work": "zechariah-1-8", "chapter": 2, "verses": [1, 2],
             "why": "The same office, in the same period: standing at the "
                    "right hand of the accused to accuse him, which is where "
                    "a prosecutor stood. He is rebuked here, but he is in the "
                    "court, not outside it."},
            {"work": "1-chronicles", "chapter": 20, "verses": [1],
             "why": "The census again, retold from the older book two or "
                    "three centuries later — and the sentence has been "
                    "rewritten. 'Yahweh moved David' has become 'Satan stood "
                    "up against Israel'. Everything else about the story is "
                    "the same."},
            {"work": "1-enoch-the-book-of-the-watchers-chapters-1-36",
             "chapter": 5, "verses": [1, 2],
             "why": "Evil is given an origin story of its own: angels who "
                    "chose to come down. Not scripture in most canons, and "
                    "the account the New Testament assumes when it mentions "
                    "angels who left their proper dwelling."},
            {"work": "jubilees", "chapter": 48, "verses": [2, 9],
             "why": "The same substitution as the census, in another book. "
                    "Exodus 4:24 says Yahweh met Moses on the way and wanted "
                    "to kill him; Jubilees retells the journey and gives the "
                    "attempt to Prince Mastema, and gives him the hardening "
                    "of Egypt as well."},
            {"work": "the-wisdom-of-solomon", "chapter": 1, "verses": [23, 24],
             "why": "Written in Greek, and the first surviving text to read "
                    "the serpent of Genesis 3 as the devil. The identification "
                    "the third stop does not make is made here, in a book "
                    "this volume files four centuries after Genesis reached "
                    "its written form."},
            {"work": "luke", "chapter": 9, "verses": [18],
             "why": "By the first century the figure is an enemy with a "
                    "kingdom, and a defeat to be described. Nothing in the "
                    "sentence needs explaining to its audience; the "
                    "vocabulary is already theirs."},
            {"work": "revelation", "chapter": 11, "verses": [9],
             "why": "The last stop gathers every earlier one into a single "
                    "verse: the dragon, the old serpent, the devil, Satan. "
                    "Four traditions from four centuries, stated as four "
                    "names for one thing."},
        ],
    },
    {
        "id": "can-a-marriage-end",
        "title": "Can a marriage be ended?",
        "question": "One of the most searched questions put to this "
                    "collection, and the collection does not answer it once. "
                    "In composition order you can watch the answer tighten, "
                    "and watch an exception appear.",
        "closing": "The exception clause is the thing to look at. Mark's "
                   "version has no exception in it; Matthew, writing later and "
                   "with Mark in front of him, has one. Whether that is an "
                   "explanatory addition, a saying Mark left out, or a ruling "
                   "made by a later community is argued and not settled. What "
                   "composition order does is put the two versions in the "
                   "sequence they were written in, so that the difference "
                   "between them is a thing you notice rather than a thing you "
                   "have to be told. And the earliest witness of all is not a "
                   "gospel: Paul is quoting the ruling in the 50s, and marking "
                   "off which part of his advice he has from the Lord and "
                   "which part is his own.",
        "stops": [
            {"work": "deuteronomy", "chapter": 23, "verses": [1, 4],
             "why": "The law does not institute divorce; it assumes it and "
                    "regulates one consequence of it. The certificate exists "
                    "already, and the rule is only that a man may not take "
                    "back a wife who has married again."},
            {"work": "malachi", "chapter": 1, "verses": [14, 16],
             "why": "Persian-period Jerusalem, and the tone has changed "
                    "entirely: the wife is a party to a covenant God witnessed, "
                    "and the man dismissing her is dealing treacherously. The "
                    "Hebrew of verse 16 is difficult and translations differ "
                    "sharply; the World English Bible's is printed here."},
            {"work": "ezra", "chapter": 9, "verses": [10, 11],
             "why": "The hardest passage in the thread, and it goes the other "
                    "way: here the returning community is told to dismiss "
                    "foreign wives, and does. Divorce is not merely permitted "
                    "but commanded, for the sake of a boundary the same period "
                    "was drawing everywhere else."},
            {"work": "1-corinthians", "chapter": 6, "verses": [10, 12, 15],
             "why": "The earliest written record of Jesus's ruling is not in "
                    "a gospel. Paul quotes it in the 50s, some twenty years "
                    "before Mark, and does something unusual: he marks which "
                    "of his instructions he has from the Lord and which are "
                    "his own, then gives a case the ruling does not cover."},
            {"work": "mark", "chapter": 9, "verses": [2, 5, 9],
             "why": "The earliest gospel. The ruling is absolute, and the "
                    "argument for it is that the Deuteronomy provision was a "
                    "concession to hardness of heart rather than the "
                    "intention."},
            {"work": "matthew", "chapter": 18, "verses": [3, 8, 9],
             "why": "The same scene, written later and following Mark closely "
                    "— with two changes. The question becomes whether a man "
                    "may divorce 'for any reason', which is what the rabbinic "
                    "schools were arguing about, and the ruling acquires an "
                    "exception."},
        ],
    },
    {
        "id": "what-women-may-do",
        "title": "What may a woman do?",
        "question": "The single most asked question of this collection online. "
                    "It is asked as though the answer were one sentence, and "
                    "the collection contains a woman judging the nation, a "
                    "woman authenticating scripture, and a letter forbidding "
                    "women to teach.",
        "closing": "Two of the sharpest stops are in the same letter, which is "
                   "the fact most often left out: the writer who assumes women "
                   "prophesying in chapter 11 is the writer who requires "
                   "silence in chapter 14, and both belong to the earliest "
                   "layer of the New Testament. The last stop is not from that "
                   "layer. This volume dates 1 Timothy to 90-110 CE in its "
                   "critical column and to Paul's lifetime in its traditional "
                   "one, with the reasons and citations for both on the work's "
                   "own page, and the difference between those two datings is "
                   "most of the modern argument. Read either way, the "
                   "collection did not speak with one voice about this while it "
                   "was being written.",
        "stops": [
            {"work": "judges", "chapter": 3, "verses": [4, 5],
             "why": "Deborah holds the two offices the collection takes most "
                    "seriously — prophet and judge — and the nation comes up "
                    "to her for judgement. Nothing in the chapter treats this "
                    "as needing an explanation."},
            {"work": "2-kings", "chapter": 21, "verses": [13, 14],
             "why": "A scroll is found in the temple and the king needs to "
                    "know whether it is authentic. The high priest and the "
                    "royal officials take it to Huldah, and her verdict is "
                    "what settles it. The nearest thing in the Hebrew Bible "
                    "to a canon decision is made by a woman."},
            {"work": "joel", "chapter": 1, "verses": [28, 29],
             "why": "The promise that prophecy will not be restricted by age, "
                    "status or sex. Quoted at Pentecost in Acts 2 as the "
                    "text that explains what is happening."},
            {"work": "galatians", "chapter": 2, "verses": [28],
             "why": "From the earliest layer of Paul's letters, and probably "
                    "older than the letter itself — the phrasing is widely read "
                    "as a baptismal formula Paul is quoting rather than "
                    "composing."},
            {"work": "1-corinthians", "chapter": 10, "verses": [5],
             "why": "The subject here is head covering, and the argument "
                    "assumes the practice it is regulating: women pray and "
                    "prophesy in the assembly, and the question is only what "
                    "they wear while doing it."},
            {"work": "1-corinthians", "chapter": 13, "verses": [34, 35],
             "why": "Three chapters later in the same letter, the flat "
                    "opposite. Some manuscripts print these two verses in a "
                    "different place, which is one of the reasons a number of "
                    "scholars argue they are a later insertion — an argument "
                    "about the manuscripts, not a way round the text."},
            {"work": "romans", "chapter": 15, "verses": [1, 2, 7],
             "why": "The practice, in the greetings, where nobody is arguing. "
                    "Phoebe is called a diakonos of the assembly at Cenchreae "
                    "— rendered 'servant' here and 'deacon' elsewhere, and "
                    "the same word is 'deacon' when a man holds it. Junia is "
                    "a woman, and is called notable among the apostles; her "
                    "name was printed as a man's, Junias, in a long line of "
                    "modern editions."},
            {"work": "1-timothy", "chapter": 1, "verses": [11, 12],
             "why": "The verse the question is usually really about. It is "
                    "one sentence, in the first person, in a letter about how "
                    "a settled church should be organised — which is part of "
                    "why its date and authorship are disputed."},
        ],
    },
    {
        "id": "how-it-ends",
        "title": "How does the world end?",
        "question": "The end is searched for more than almost anything else "
                    "here, usually as though the collection contained one "
                    "timetable. It contains a series of them, and the last "
                    "writers are already explaining why the earlier ones have "
                    "not happened.",
        "closing": "The thread ends with the problem rather than the picture. "
                   "Mark's generation had passed; the letter answering that is "
                   "the latest-written book in the New Testament, and its "
                   "answer is that the delay is deliberate and that God does "
                   "not keep time the way the question assumes. Whether that "
                   "is a revelation or a rescue of a prediction is precisely "
                   "what the arrangement cannot decide. What the arrangement "
                   "shows is that the objection was raised inside the "
                   "collection, by its own writers, and was not edited out.",
        "stops": [
            {"work": "amos", "chapter": 4, "verses": [18, 20],
             "why": "The earliest surviving mention of 'the day of Yahweh', "
                    "and it is already arguing with people who use the phrase "
                    "— so the idea is older than the oldest text of it. In its "
                    "first appearance the day is a warning to the faithful "
                    "rather than a promise to them."},
            {"work": "zephaniah", "chapter": 0, "verses": [14, 15],
             "why": "A century on, the day has become universal wrath. These "
                    "two verses are the source of the Dies Irae, which is why "
                    "the vocabulary sounds familiar before you have read it."},
            {"work": "ezekiel", "chapter": 37, "verses": [2, 15],
             "why": "In exile, the enemy becomes a named figure from the far "
                    "north who attacks at the end. Gog of Magog is reused by "
                    "Revelation six centuries later and has been identified "
                    "with a different contemporary power in almost every "
                    "generation since."},
            {"work": "zechariah-9-14", "chapter": 5, "verses": [1, 9],
             "why": "The chapters of Zechariah that this volume dates later "
                    "than the first eight. The end is now a specific "
                    "geography — the Mount of Olives splitting — and it ends "
                    "with God king over all the earth rather than with "
                    "Jerusalem rescued."},
            {"work": "daniel", "chapter": 6, "verses": [13, 14],
             "why": "167-164 BCE, in a persecution. One like a son of man "
                    "comes with the clouds and receives a kingdom that does "
                    "not end. Every later stop in this thread is written by "
                    "someone who knows this passage."},
            {"work": "1-thessalonians", "chapter": 4, "verses": [1, 2, 3],
             "why": "The earliest surviving Christian document, and the "
                    "expectation is imminent and unscheduled at the same "
                    "time: like a thief, so no date can be worked out, and "
                    "soon enough that the letter is answering a practical "
                    "question about it."},
            {"work": "2-thessalonians", "chapter": 1, "verses": [1, 2, 3],
             "why": "A correction, and evidence that timetables were already "
                    "circulating: someone has told this congregation the day "
                    "has come, possibly in a forged letter. The reply "
                    "inserts a sequence that has to happen first."},
            {"work": "mark", "chapter": 12, "verses": [26, 30, 32],
             "why": "The gospel apocalypse holds two things at once, two "
                    "verses apart: this generation will not pass away, and "
                    "nobody knows the day, not even the Son. Both sentences "
                    "are in the earliest gospel, and the next stop but one is "
                    "written by someone answering the first of them."},
            {"work": "revelation", "chapter": 20, "verses": [1, 4],
             "why": "The best-known ending in the collection, and it is not "
                    "an escape from the world. The city comes down, God moves "
                    "in, and the earth is the address."},
            {"work": "2-peter", "chapter": 2, "verses": [4, 8, 9],
             "why": "The last word, in the latest-written book here, and it "
                    "quotes the objection before answering it: where is the "
                    "promise of his coming, since nothing has changed? The "
                    "answer given is about God's timekeeping and God's "
                    "patience, not about a date."},
        ],
    },
]
