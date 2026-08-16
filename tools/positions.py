#!/usr/bin/env python3
"""Traditional and critical positions on authorship and date, side by side.

The volume is arranged by critical composition dating. Left at that, the
critical frame becomes the house voice and a reader who holds the traditional
view is reading someone else's verdict baked into the furniture. This file
supplies the other column.

Neither position is presented as the correct one. Each entry records what the
position is, who holds it, and the reasoning it rests on, so a reader can see
where the two agree, where they diverge, and why -- and decide for themselves.

Fields per work
    trad      traditional / confessional attribution and date
    tradWhy   the grounds that position rests on
    crit      critical attribution and date (matches this volume's arrangement)
    critWhy   the grounds that position rests on
    gap       "none" | "narrow" | "wide"  -- how far apart the two sit
"""

from __future__ import annotations

# gap:
#   none    the two traditions substantially agree
#   narrow  they differ over decades, or over editing rather than authorship
#   wide    they differ over centuries, or over who wrote it at all

POSITIONS: dict[str, dict] = {

    # ---- Torah -----------------------------------------------------------
    "genesis": {
        "trad": "Moses, 15th-13th century BCE",
        "tradWhy": "Jewish and Christian tradition ascribes the Torah to Moses. "
                   "Later scripture refers to 'the book of Moses' (2 Chronicles 35:12, "
                   "Mark 12:26), and Jesus speaks of Moses as its author.",
        "crit": "Composite; final form in the Persian period, c. 500-400 BCE",
        "critWhy": "Doublets, two divine names, and differences of vocabulary and "
                   "theology suggest combined sources. Genesis 14 and 36 mention "
                   "kings and customs of later eras. The final editing is placed "
                   "after the exile.",
        "gap": "wide",
    },
    "exodus": {
        "trad": "Moses, 15th-13th century BCE",
        "tradWhy": "Traditional Mosaic authorship; the book itself records Moses "
                   "writing (Exodus 24:4).",
        "crit": "Composite; final form Persian period",
        "critWhy": "The Song of the Sea in chapter 15 is archaic Hebrew and far "
                   "older than the prose around it, which is itself evidence that "
                   "the book gathers material of very different ages.",
        "gap": "wide",
    },
    "leviticus": {
        "trad": "Moses, 15th-13th century BCE",
        "tradWhy": "Traditional Mosaic authorship; framed throughout as speech of "
                   "Yahweh to Moses.",
        "crit": "Priestly source, exilic to Persian period",
        "critWhy": "Vocabulary and cultic concerns match the priestly material "
                   "elsewhere in the Torah, associated with the Second Temple.",
        "gap": "wide",
    },
    "numbers": {
        "trad": "Moses, 15th-13th century BCE",
        "tradWhy": "Traditional Mosaic authorship.",
        "crit": "Composite; final form Persian period",
        "critWhy": "Contains very old poetry, notably the Oracles of Balaam, inside "
                   "a late narrative frame.",
        "gap": "wide",
    },
    "deuteronomy": {
        "trad": "Moses, shortly before his death",
        "tradWhy": "Presented as Moses' farewell addresses; the book describes him "
                   "writing the law (Deuteronomy 31:9).",
        "crit": "7th century BCE, connected to Josiah's reform of 622",
        "critWhy": "The law book found in the temple in 2 Kings 22 matches "
                   "Deuteronomy's distinctive demand for a single sanctuary. Its "
                   "style differs sharply from the rest of the Torah.",
        "gap": "wide",
    },

    # ---- Deuteronomistic History ----------------------------------------
    "joshua": {
        "trad": "Joshua, with a later hand for his death",
        "tradWhy": "Talmudic tradition (Bava Batra 14b) assigns it to Joshua.",
        "crit": "Part of the Deuteronomistic History, 7th-6th century BCE",
        "critWhy": "Shares the language and theology of Deuteronomy; the recurring "
                   "'to this day' implies a much later vantage point.",
        "gap": "wide",
    },
    "judges": {
        "trad": "Samuel",
        "tradWhy": "Talmudic tradition assigns Judges to Samuel.",
        "crit": "Deuteronomistic History, 7th-6th century BCE, around older material",
        "critWhy": "The Song of Deborah in chapter 5 is archaic Hebrew, older than "
                   "the prose account of the same events in chapter 4.",
        "gap": "wide",
    },
    "1-samuel": {
        "trad": "Samuel, continued by Nathan and Gad",
        "tradWhy": "Talmudic tradition, drawing on 1 Chronicles 29:29, which names "
                   "records of Samuel, Nathan and Gad.",
        "crit": "Deuteronomistic History, 7th-6th century BCE",
        "critWhy": "Samuel dies partway through the book. The court narrative is "
                   "often judged very early, the framework much later.",
        "gap": "wide",
    },
    "2-samuel": {
        "trad": "Nathan and Gad",
        "tradWhy": "Talmudic tradition, since Samuel has died.",
        "crit": "Deuteronomistic History, 7th-6th century BCE",
        "critWhy": "The Succession Narrative is regarded by many as among the "
                   "oldest sustained prose in the Bible, later incorporated.",
        "gap": "narrow",
    },
    "1-kings": {
        "trad": "Jeremiah",
        "tradWhy": "Talmudic tradition assigns Kings to Jeremiah.",
        "crit": "Deuteronomistic History; first edition under Josiah, second in exile",
        "critWhy": "The book cites royal annals as sources and ends in the exile, "
                   "which sets its earliest possible completion.",
        "gap": "narrow",
    },
    "2-kings": {
        "trad": "Jeremiah",
        "tradWhy": "Talmudic tradition.",
        "crit": "Deuteronomistic History, completed in exile after 561 BCE",
        "critWhy": "Ends with Jehoiachin's release from prison, dated to 561, which "
                   "the book cannot precede.",
        "gap": "narrow",
    },

    # ---- Prophets --------------------------------------------------------
    "amos": {
        "trad": "Amos of Tekoa, c. 760-750 BCE",
        "tradWhy": "The book names its prophet and dates him by two kings.",
        "crit": "Amos, c. 760-750 BCE, with later editorial additions",
        "critWhy": "Core oracles are accepted as genuinely his; the closing promise "
                   "of restoration is often judged a later addition.",
        "gap": "none",
    },
    "hosea": {
        "trad": "Hosea, 8th century BCE",
        "tradWhy": "Named and dated in the book itself.",
        "crit": "Hosea, 8th century BCE, with Judean editing",
        "critWhy": "References to Judah are often taken as southern additions to a "
                   "northern prophet's work.",
        "gap": "none",
    },
    "isaiah-1-39-first-isaiah": {
        "trad": "Isaiah son of Amoz wrote the whole book, 8th century BCE",
        "tradWhy": "The book is a single scroll bearing one name; the New Testament "
                   "quotes from all parts of it as 'Isaiah'. The Great Isaiah Scroll "
                   "from Qumran contains all 66 chapters continuously.",
        "crit": "Isaiah of Jerusalem, c. 740-700 BCE",
        "critWhy": "Chapters 1-39 address 8th-century Assyrian crisis; chapters 40 "
                   "onward address the Babylonian exile 150 years later, naming "
                   "Cyrus, and differ in vocabulary and theology.",
        "gap": "wide",
    },
    "isaiah-40-55-second-isaiah": {
        "trad": "Isaiah son of Amoz, writing prophetically of the exile",
        "tradWhy": "Predictive prophecy: naming Cyrus in advance is understood as "
                   "evidence of genuine foreknowledge, not late composition.",
        "crit": "An anonymous prophet in Babylon, c. 550-540 BCE",
        "critWhy": "Addresses exiles as a present audience and treats Cyrus's rise "
                   "as current events.",
        "gap": "wide",
    },
    "isaiah-56-66-third-isaiah": {
        "trad": "Isaiah son of Amoz",
        "tradWhy": "Part of the single scroll attributed to Isaiah.",
        "crit": "Anonymous, after the return, c. 537-500 BCE",
        "critWhy": "Presupposes a community back in the land with the temple in view.",
        "gap": "wide",
    },
    "jeremiah": {
        "trad": "Jeremiah, dictated to Baruch",
        "tradWhy": "The book describes exactly this process in chapter 36.",
        "crit": "Jeremiah with substantial Deuteronomistic editing",
        "critWhy": "The Greek text is about an eighth shorter and ordered "
                   "differently, showing the book still circulated in more than one "
                   "form. Qumran preserves both.",
        "gap": "narrow",
    },
    "ezekiel": {
        "trad": "Ezekiel the priest, in exile, 593-571 BCE",
        "tradWhy": "The book is precisely dated throughout and written in first person.",
        "crit": "Ezekiel, 593-571 BCE, with a later editorial school",
        "critWhy": "Its dates are unusually consistent; critical and traditional "
                   "views sit closer here than almost anywhere else.",
        "gap": "none",
    },
    "daniel": {
        "trad": "Daniel, 6th century BCE, in Babylon and Persia",
        "tradWhy": "The book presents itself as Daniel's, set in the exile. Jesus "
                   "refers to 'the prophet Daniel' (Matthew 24:15).",
        "crit": "c. 165 BCE, during the Maccabean crisis",
        "critWhy": "Chapter 11 tracks Hellenistic politics in detail up to Antiochus "
                   "IV, then its predictions of his death diverge from what happened. "
                   "Its Aramaic and Persian and Greek loanwords suit a later period.",
        "gap": "wide",
    },
    "jonah": {
        "trad": "Jonah son of Amittai, 8th century BCE",
        "tradWhy": "Names the prophet known from 2 Kings 14:25. Jesus refers to the "
                   "sign of Jonah (Matthew 12:39-41).",
        "crit": "Post-exilic, c. 400-300 BCE",
        "critWhy": "Late Hebrew; speaks of Nineveh in the past tense; reads as a "
                   "didactic narrative about the reach of mercy.",
        "gap": "wide",
    },
    "joel": {
        "trad": "Joel, 9th century BCE",
        "tradWhy": "Its position among the Twelve was traditionally taken to imply "
                   "an early date.",
        "crit": "Post-exilic, c. 400-350 BCE",
        "critWhy": "Assumes a functioning temple and no monarchy; mentions Greeks.",
        "gap": "wide",
    },
    "obadiah": {
        "trad": "Obadiah, 9th century BCE",
        "tradWhy": "Traditionally tied to an earlier Edomite conflict.",
        "crit": "Shortly after 587 BCE",
        "critWhy": "Its rage at Edom fits Edomite conduct at Jerusalem's fall.",
        "gap": "wide",
    },
    "zechariah-9-14": {
        "trad": "Zechariah, late 6th century BCE",
        "tradWhy": "Part of the single book bearing his name.",
        "crit": "Anonymous, 4th-3rd century BCE",
        "critWhy": "Shifts from dated oracles about rebuilding to undated apocalyptic; "
                   "the Greek period appears in view.",
        "gap": "wide",
    },

    # ---- Writings --------------------------------------------------------
    "job": {
        "trad": "Moses, or an ancient author in the patriarchal era",
        "tradWhy": "Talmudic tradition suggests Moses; the patriarchal setting, with "
                   "wealth counted in livestock and no mention of Israel or the law, "
                   "implies great antiquity.",
        "crit": "6th-4th century BCE, with an older folk tale at its core",
        "critWhy": "The prose frame and poetic dialogue differ in style and outlook; "
                   "the Hebrew contains Aramaisms.",
        "gap": "wide",
    },
    "psalms": {
        "trad": "David wrote most; others by Asaph, Korah, Solomon, Moses",
        "tradWhy": "Seventy-three psalms carry Davidic superscriptions, and the New "
                   "Testament cites psalms as David's words (Acts 2:25).",
        "crit": "A collection spanning centuries, compiled by the Persian period",
        "critWhy": "Some psalms presuppose the exile (Psalm 137) or the second "
                   "temple. Superscriptions may indicate dedication or style rather "
                   "than authorship.",
        "gap": "narrow",
    },
    "proverbs": {
        "trad": "Solomon, 10th century BCE",
        "tradWhy": "The book names Solomon and 1 Kings 4:32 credits him with 3,000 "
                   "proverbs.",
        "crit": "A compilation; final form post-exilic",
        "critWhy": "Internally attributed to several hands, including Agur and Lemuel, "
                   "and a collection copied out under Hezekiah, centuries after Solomon.",
        "gap": "narrow",
    },
    "ecclesiastes": {
        "trad": "Solomon in old age",
        "tradWhy": "The speaker is 'son of David, king in Jerusalem'.",
        "crit": "c. 300-250 BCE",
        "critWhy": "Late Hebrew with Persian loanwords; the speaker looks back on "
                   "kingship rather than exercising it.",
        "gap": "wide",
    },
    "song-of-songs": {
        "trad": "Solomon, 10th century BCE",
        "tradWhy": "Ascribed to Solomon in its opening line.",
        "crit": "Anywhere from the 10th to the 3rd century BCE",
        "critWhy": "Genuinely unsettled. Persian loanwords suggest late; the poetry "
                   "resembles much older Egyptian love song.",
        "gap": "wide",
    },
    "ruth": {
        "trad": "Samuel",
        "tradWhy": "Talmudic tradition; the story is set in the period of the judges.",
        "crit": "Post-exilic, though a pre-exilic date is defended",
        "critWhy": "Often read as a response to the post-exilic dissolution of foreign "
                   "marriages, since its heroine is a Moabite ancestor of David. "
                   "Others note its Hebrew is classical, not late.",
        "gap": "wide",
    },
    "1-chronicles": {
        "trad": "Ezra",
        "tradWhy": "Talmudic tradition assigns Chronicles to Ezra.",
        "crit": "Anonymous Chronicler, c. 400-350 BCE",
        "critWhy": "Genealogies run generations past the exile.",
        "gap": "narrow",
    },
    "2-chronicles": {
        "trad": "Ezra",
        "tradWhy": "Talmudic tradition.",
        "crit": "Anonymous Chronicler, c. 400-350 BCE",
        "critWhy": "Ends with Cyrus's decree, the same point where Ezra begins.",
        "gap": "narrow",
    },
    "esther-hebrew": {
        "trad": "Mordecai, or the men of the Great Assembly",
        "tradWhy": "Esther 9:20 records Mordecai writing these things down.",
        "crit": "4th-3rd century BCE",
        "critWhy": "Written to explain the origin of Purim; God is never named.",
        "gap": "narrow",
    },

    # ---- New Testament ---------------------------------------------------
    "matthew": {
        "trad": "Matthew the apostle, c. 50-60 CE",
        "tradWhy": "Unanimous early attribution; Papias reports Matthew compiling "
                   "sayings in Hebrew.",
        "crit": "Anonymous, c. 80-90 CE, using Mark",
        "critWhy": "Uses about 90 percent of Mark, which an eyewitness apostle would "
                   "be unlikely to need. Chapter 22:7 is often read as knowing of "
                   "Jerusalem's fall in 70.",
        "gap": "narrow",
    },
    "mark": {
        "trad": "Mark, recording Peter's preaching, c. 50s-60s CE",
        "tradWhy": "Papias, c. 130, states Mark was Peter's interpreter and wrote "
                   "down what Peter taught.",
        "crit": "Anonymous, c. 65-75 CE; the earliest gospel",
        "critWhy": "Its priority is broadly agreed. Chapter 13 suggests the Jewish "
                   "revolt is underway or just past.",
        "gap": "none",
    },
    "luke": {
        "trad": "Luke the physician, Paul's companion, c. 60-62 CE",
        "tradWhy": "The 'we' passages in Acts imply a travelling companion; early "
                   "attribution is consistent. Acts ends with Paul alive, suggesting "
                   "it was written before his death.",
        "crit": "Anonymous, c. 80-90 CE, using Mark",
        "critWhy": "Depends on Mark; its version of the Olivet discourse is read as "
                   "describing the siege of 70 in retrospect.",
        "gap": "narrow",
    },
    "john": {
        "trad": "John the apostle, son of Zebedee, c. 90 CE",
        "tradWhy": "Irenaeus names John, the beloved disciple, writing at Ephesus. "
                   "The book claims eyewitness testimony (John 21:24).",
        "crit": "A Johannine community, c. 90-110 CE",
        "critWhy": "Chapter 21 reads as an appendix; its developed theology and its "
                   "language about expulsion from the synagogue suggest a later "
                   "setting.",
        "gap": "narrow",
    },
    "acts": {
        "trad": "Luke, c. 62 CE",
        "tradWhy": "Same author as the gospel; ends abruptly with Paul under house "
                   "arrest, before his death, which suggests it was written then.",
        "crit": "Anonymous, c. 80-90 CE",
        "critWhy": "Follows the gospel of Luke, which is dated after Mark.",
        "gap": "narrow",
    },
    "ephesians": {
        "trad": "Paul, c. 60-62 CE from prison",
        "tradWhy": "The letter names Paul twice as its author.",
        "crit": "A follower of Paul, c. 80-100 CE",
        "critWhy": "Vocabulary and long sentence style differ from the undisputed "
                   "letters; closely parallels Colossians.",
        "gap": "wide",
    },
    "colossians": {
        "trad": "Paul, c. 60-62 CE",
        "tradWhy": "Names Paul and Timothy; personal greetings match Philemon.",
        "crit": "Disputed; Paul or a close follower, c. 60-80 CE",
        "critWhy": "Style and a more cosmic Christology than the undisputed letters, "
                   "though the personal details are hard to explain as invention.",
        "gap": "narrow",
    },
    "2-thessalonians": {
        "trad": "Paul, c. 51-52 CE",
        "tradWhy": "Names Paul; follows quickly on 1 Thessalonians.",
        "crit": "Disputed",
        "critWhy": "Its end-times sequence is hard to square with 1 Thessalonians, "
                   "and it warns against forged letters in Paul's name.",
        "gap": "narrow",
    },
    "1-timothy": {
        "trad": "Paul, c. 62-64 CE, after a release from Roman imprisonment",
        "tradWhy": "Names Paul; assumes travels not recorded in Acts, which "
                   "tradition explains by a later missionary period.",
        "crit": "A follower of Paul, c. 90-110 CE",
        "critWhy": "The Pastorals share a vocabulary unlike Paul's and address a "
                   "settled church order of bishops and deacons.",
        "gap": "wide",
    },
    "2-timothy": {
        "trad": "Paul, c. 64-67 CE, shortly before execution",
        "tradWhy": "Reads as a farewell; deeply personal in tone.",
        "crit": "A follower of Paul, c. 90-110 CE",
        "critWhy": "Grouped with the other Pastorals on shared style.",
        "gap": "wide",
    },
    "titus": {
        "trad": "Paul, c. 63-65 CE",
        "tradWhy": "Names Paul; assumes work in Crete.",
        "crit": "A follower of Paul, c. 90-110 CE",
        "critWhy": "Grouped with the other Pastorals.",
        "gap": "wide",
    },
    "hebrews": {
        "trad": "Paul, or Barnabas, Apollos or Luke",
        "tradWhy": "Included among Pauline letters in the East, which helped secure "
                   "its place in the canon, though authorship was debated from the "
                   "start.",
        "crit": "Anonymous, c. 60-90 CE",
        "critWhy": "The letter never names its author. Origen already wrote that only "
                   "God knows who wrote it.",
        "gap": "narrow",
    },
    "james": {
        "trad": "James the brother of Jesus, before 62 CE",
        "tradWhy": "Attributed to James, leader of the Jerusalem church, martyred in 62.",
        "crit": "Disputed, anywhere from 45 to 120 CE",
        "critWhy": "Polished Greek is unexpected from a Galilean; its treatment of "
                   "faith and works is read by some as responding to Paul, requiring "
                   "a later date.",
        "gap": "wide",
    },
    "1-peter": {
        "trad": "Peter the apostle, c. 62-64 CE",
        "tradWhy": "Names Peter; mentions Silvanus as scribe, which accounts for the "
                   "polished Greek.",
        "crit": "Disputed; Peter or a follower, c. 70-90 CE",
        "critWhy": "Refers to persecution across Asia Minor, and 'Babylon' as a name "
                   "for Rome is characteristic of the period after 70.",
        "gap": "narrow",
    },
    "2-peter": {
        "trad": "Peter the apostle, c. 65-68 CE",
        "tradWhy": "Names Peter and refers to the transfiguration as eyewitness.",
        "crit": "Pseudonymous, c. 110-150 CE; the latest writing in the New Testament",
        "critWhy": "Uses Jude; refers to Paul's letters as an established collection "
                   "of scripture; addresses the delay of the second coming. It was "
                   "the most disputed book in the early church.",
        "gap": "wide",
    },
    "jude": {
        "trad": "Jude the brother of Jesus and James, c. 60-65 CE",
        "tradWhy": "Names itself as from Jude, brother of James.",
        "crit": "Disputed, c. 50-100 CE",
        "critWhy": "Quotes 1 Enoch as prophecy, which shows the breadth of what was "
                   "read as authoritative at the time.",
        "gap": "narrow",
    },
    "revelation": {
        "trad": "John the apostle, c. 95 CE on Patmos",
        "tradWhy": "Irenaeus places it at the end of Domitian's reign and identifies "
                   "the author as the apostle.",
        "crit": "John of Patmos, a different John, c. 95 CE",
        "critWhy": "Date is broadly agreed; the Greek differs so sharply from the "
                   "gospel of John that common authorship is doubted.",
        "gap": "none",
    },

    # ---- Second Temple and later -----------------------------------------
    "jubilees": {
        "trad": "Revelation given to Moses at Sinai",
        "tradWhy": "The book presents itself as dictated to Moses by an angel. It is "
                   "canonical scripture in the Ethiopian Orthodox Tewahedo Church.",
        "crit": "c. 160-150 BCE",
        "critWhy": "Its solar calendar and priestly concerns fit the Maccabean era; "
                   "Hebrew fragments were found at Qumran.",
        "gap": "wide",
    },
    "1-enoch-the-book-of-the-watchers-chapters-1-36": {
        "trad": "Enoch, seventh from Adam, before the flood",
        "tradWhy": "The book claims Enoch as author, and Jude 14-15 quotes it as "
                   "prophecy from 'Enoch, the seventh from Adam'. Canonical in the "
                   "Ethiopian Orthodox Tewahedo Church.",
        "crit": "3rd century BCE",
        "critWhy": "Aramaic fragments at Qumran; among the earliest Jewish "
                   "apocalyptic writing.",
        "gap": "wide",
    },
    "the-first-epistle-of-clement-to-the-corinthians": {
        "trad": "Clement of Rome, c. 95-97 CE",
        "tradWhy": "Early and consistent attribution; some early churches read it as "
                   "scripture.",
        "crit": "Clement of Rome, c. 95-97 CE",
        "critWhy": "Rarely disputed. One of the earliest Christian writings outside "
                   "the New Testament.",
        "gap": "none",
    },
    "the-teaching-of-the-twelve-apostles-didache": {
        "trad": "The teaching of the twelve apostles",
        "tradWhy": "Its title claims apostolic teaching; treated as near-scripture in "
                   "some early communities.",
        "crit": "Anonymous, c. 50-120 CE",
        "critWhy": "Possibly as old as the gospels. Lost for centuries and "
                   "rediscovered in 1873.",
        "gap": "narrow",
    },
}


def coverage(work_ids: list[str]) -> tuple[int, int]:
    """How many of the given works carry a recorded pair of positions."""
    have = sum(1 for w in work_ids if w in POSITIONS)
    return have, len(work_ids)
