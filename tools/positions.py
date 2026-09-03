#!/usr/bin/env python3
"""Traditional and critical positions on authorship and date, side by side.

The volume is arranged by critical composition dating. Left at that, the
critical frame becomes the house voice and a reader who holds the traditional
view is reading someone else's verdict baked into the furniture. This file
supplies the other column.

Neither position is presented as the correct one.

EVERY CLAIM CARRIES A CITATION. That is the rule this file exists to enforce.
Elsewhere on the site a reader can check the work: verse counts are audited
against independent reference figures and every deleted byte is logged. An
interpretive layer that merely asserts things, in the same visual frame as
audited text, would be the weakest link in the whole project. So a position is
either attributable to a named ancient source, a named scholar and work, a
manuscript, or a specific feature of the text itself -- or it does not appear
here at all. tools/audit.py fails the build if any record is missing either
source field.

Fields per work
    trad        traditional / confessional attribution and date
    tradWhy     the grounds that position rests on
    tradSource  where that position is actually attested
    crit        critical attribution and date (matches this volume's arrangement)
    critWhy     the grounds that position rests on
    critSource  who argued it, or the evidence it rests on
    gap         "none" | "narrow" | "wide"  -- how far apart the two sit

Recurring citations
    Bava Batra 14b-15a   the Talmud's list of who wrote what, c. 3rd-5th century
    Papias               via Eusebius, Ecclesiastical History 3.39; the fragments
                         are in this volume under the Apostolic Fathers
    Irenaeus             Against Heresies, c. 180
    Wellhausen 1878      Prolegomena to the History of Israel, the classic
                         statement of the documentary analysis
"""

from __future__ import annotations

TALMUD = "Talmud, Bava Batra 14b-15a"

POSITIONS: dict[str, dict] = {
    "the-ethiopic-didascalia": {
        "trad": "c. 50 CE",
        "tradWhy": "The work opens by naming its own authors and occasion: "
                   "\u201cWe the Twelve Apostles, Messengers of the only-begotten "
                   "Son Jesus Christ, being assembled together in Jerusalem\u201d, "
                   "with Paul and with James the brother of the Lord presiding as "
                   "bishop of the city. That is the council of Acts 15, and the "
                   "Ethiopian church receives the book on those terms.",
        "tradSource": "The text's own opening charge, Platt 1834, p. 1",
        "crit": "3rd century CE",
        "critWhy": "The Didascalia Apostolorum is a Greek church order composed "
                   "in northern Syria, generally placed in the third century; the "
                   "Apostles' names are the convention of the genre rather than a "
                   "claim of authorship. What is printed here is later still: the "
                   "Ethiopic is a translation of a translation, reaching Ge'ez "
                   "through Arabic, and its own date is medieval.",
        "critSource": "R. H. Connolly, Didascalia Apostolorum: The Syriac Version "
                      "Translated and Accompanied by the Verona Latin Fragments, "
                      "Oxford, 1929, introduction",
        "gap": "About two centuries between the apostolic setting the book claims "
               "for itself and the century that produced it, and a further gulf "
               "again to the Ge'ez version this volume prints.",
    },

    "the-sinodos": {
        "trad": "c. 50 CE",
        "tradWhy": "The book opens by naming the assembly it claims to be: the "
                   "apostles gathered \u201cwith the knowledge of our Lord Jesus "
                   "Christ, our Saviour\u201d, and told to divide the earth "
                   "between them and to set the orders of the Church. Statute 1 "
                   "lists them by name, and the Ethiopian church receives the "
                   "collection on those terms, through Clement.",
        "tradSource": "The text's own first statute, Horner 1904, p. 127",
        "crit": "4th-6th century CE",
        "critWhy": "The Statutes are a compilation rather than a composition. "
                   "Their first part is the Apostolic Church Order, their second "
                   "the church order that also stands behind the eighth book of "
                   "the Apostolic Constitutions, and Horner published the "
                   "Ethiopic, Arabic and Saidic together precisely to argue about "
                   "which came first. The Ge'ez itself is later again, reaching "
                   "Ethiopia through Arabic, and its manuscripts are medieval.",
        "critSource": "G. Horner, The Statutes of the Apostles, or Canones "
                      "Ecclesiastici, London, 1904, introduction, pp. vii-xxxix",
        "gap": "Three centuries at least between the apostolic council the book "
               "claims and the compilation that produced it, and a thousand years "
               "more to the Ge'ez manuscripts it survives in.",
    },

    "the-apostolic-canons": {
        "trad": "c. 50 CE",
        "tradWhy": "The collection opens and closes by naming itself the "
                   "Synod of the Apostles, sent out \u201cwith Clemens\u201d, "
                   "and every canon in it is framed as their own ruling. The "
                   "Ethiopian church receives it on those terms, as part of "
                   "the Sinodos.",
        "tradSource": "The text's own opening and closing sentences, Schodde "
                      "1885, pp. 63 and 72",
        "crit": "4th century CE",
        "critWhy": "These are the canons appended to the eighth book of the "
                   "Apostolic Constitutions, which is Syrian work of the "
                   "later fourth century; Schodde says so in the "
                   "introduction to the translation printed here, and "
                   "distinguishes them from the older Apostolic Church "
                   "Order. The Ge'ez is later again, reaching Ethiopia "
                   "through the Coptic.",
        "critSource": "G. H. Schodde, \u201cThe Apostolic Canons, translated "
                      "from the Ethiopic\u201d, Journal of the Society of "
                      "Biblical Literature and Exegesis 5 (1885), "
                      "pp. 61-62",
        "gap": "Three centuries between the apostolic council the canons "
               "claim and the compilation that produced them.",
    },

    "the-testament-of-our-lord": {
        "trad": "c. 30-40 CE",
        "tradWhy": "The book is the risen Lord speaking to the apostles, and "
                   "its closing sentence names the men who wrote it down and "
                   "sent it out: \u201cJohn and Peter and Matthew wrote this "
                   "Testament, and sent it in copies from Jerusalem\u201d.",
        "tradSource": "The text's own last chapter, Cooper and Maclean 1902, "
                      "p. 138",
        "crit": "4th-5th century CE",
        "critWhy": "Cooper and Maclean weigh the evidence at length and "
                   "settle on the middle of the fourth century or a little "
                   "later: the church order it describes is too developed "
                   "for the second century and its apocalyptic prelude "
                   "answers a persecution rather than a Roman peace. The "
                   "Syriac they translate says of itself that it was turned "
                   "out of Greek in the year 998 of the Greeks, which is "
                   "687 CE, so even the version is centuries younger than "
                   "the book.",
        "critSource": "J. Cooper and A. J. Maclean, The Testament of Our "
                      "Lord, Edinburgh, 1902, introduction \u00a7vi",
        "gap": "Three centuries or more between the Jerusalem the book "
               "writes from and the church it actually describes.",
    },

    "the-apocalypse-of-peter": {
        "trad": "c. 30-40 CE",
        "tradWhy": "Peter receives the vision from the Lord on the Mount of "
                   "Olives, in answer to the disciples' question about the "
                   "signs of his coming, and writes it for the church. It "
                   "was read as Peter's in Rome: the Muratorian Canon lists "
                   "it beside the Apocalypse of John.",
        "tradSource": "The text's own opening, James 1924, p. 510; the "
                      "Muratorian Canon",
        "crit": "c. 125-150 CE",
        "critWhy": "Clement of Alexandria quotes it as scripture, which puts "
                   "it well before 200; its parable of the fig-tree, read as "
                   "the house of Israel with a false messiah among its "
                   "shoots, is generally taken for the Bar Kokhba revolt of "
                   "132-135. That places it in the second quarter of the "
                   "second century, a generation after the apostle.",
        "critSource": "M. R. James, The Apocryphal New Testament, Oxford, "
                      "1924, pp. 505-506",
        "gap": "About a century between the Mount of Olives the vision is "
               "set on and the revolt it appears to answer.",
    },

    "the-rest-of-the-words-of-baruch": {
        "trad": "c. 586 BCE",
        "tradWhy": "The book sets itself at the fall of Jerusalem and tells its "
                   "story through Jeremiah, Baruch his scribe and Abimelech the "
                   "Ethiopian; it presents itself as the rest of what Baruch "
                   "wrote, and is received under his name.",
        "tradSource": "The text's own opening, and its closing sentence: "
                      "\u201cAnd the rest of the sayings of Jeremiah ... are not "
                      "written in the letter of Baruch\u201d",
        "crit": "c. 100-150 CE",
        "critWhy": "Abimelech sleeps sixty-six years, which is the interval from "
                   "the fall of Jerusalem in 70 CE to the crushing of the Bar "
                   "Kokhba revolt in 136 rather than any interval of the Babylonian "
                   "exile; Harris read the number as the book's own date. The "
                   "closing chapter, in which Jeremiah is stoned for preaching "
                   "Christ, is Christian work over a Jewish story.",
        "critSource": "J. Rendel Harris, The Rest of the Words of Baruch: A "
                      "Christian Apocalypse of the Year 136 A.D., London, 1889, "
                      "introduction",
        "gap": "About seven centuries: the book is set in the exile and was "
               "written after the second Jewish revolt.",
    },

    "the-book-of-the-covenant": {
        "trad": "c. 30-40 CE",
        "tradWhy": "The eleven write in their own names \u2014 \u201cWe, John, "
                   "Thomas, Peter, Andrew, James, Philip, Bartholomew, Matthew, "
                   "Nathanael, Judas Zelotes, and Cephas\u201d \u2014 and say "
                   "they set down what the risen Lord revealed to them, having "
                   "seen and heard and touched him. That places it in the years "
                   "after the resurrection.",
        "tradSource": "The text's own sections 1 and 2, James 1924, pp. 485-486",
        "crit": "c. 140-160 CE",
        "critWhy": "The letter argues against Simon and Cerinthus by name and "
                   "answers a docetic reading of the resurrection, which is a "
                   "second-century quarrel; its calculation of the Lord's return "
                   "and its Easter discipline belong there too. Schmidt, who "
                   "edited the Coptic, Ethiopic and Latin together, placed it in "
                   "Asia Minor about 160.",
        "critSource": "C. Schmidt, 1919, as reported by M. R. James, The "
                      "Apocryphal New Testament, Oxford, 1924, p. 485",
        "gap": "About a century and a quarter between the apostolic voice the "
               "letter writes in and the controversy it was written for.",
    },


    # ---- Torah -----------------------------------------------------------
    "genesis": {
        "trad": "Moses, 15th-13th century BCE",
        "tradWhy": "Jewish and Christian tradition ascribes the Torah to Moses. "
                   "Later scripture speaks of 'the book of Moses', and Jesus "
                   "refers to what Moses wrote.",
        "tradSource": f"{TALMUD}; 2 Chronicles 35:12; Mark 12:26; John 5:46-47",
        "crit": "Composite; final form in the Persian period, c. 500-400 BCE",
        "critWhy": "Doublets, two divine names, and differences of vocabulary and "
                   "theology are read as evidence of combined sources. Genesis 14 "
                   "and 36 mention kings and customs of later eras.",
        "critSource": "Julius Wellhausen, Prolegomena to the History of Israel, "
                      "1878, building on Astruc 1753 and Graf 1866",
        "gap": "wide",
    },
    "exodus": {
        "trad": "Moses, 15th-13th century BCE",
        "tradWhy": "The book records Moses writing down what he was given.",
        "tradSource": f"Exodus 24:4; {TALMUD}",
        "crit": "Composite; final form Persian period",
        "critWhy": "The Song of the Sea in chapter 15 is archaic Hebrew, "
                   "linguistically older than the prose around it, which is "
                   "itself evidence the book gathers material of different ages.",
        "critSource": "Frank Moore Cross and David Noel Freedman, Studies in "
                      "Ancient Yahwistic Poetry, 1950",
        "gap": "wide",
    },
    "leviticus": {
        "trad": "Moses, 15th-13th century BCE",
        "tradWhy": "Framed throughout as speech of Yahweh to Moses.",
        "tradSource": f"Leviticus 1:1; {TALMUD}",
        "crit": "Priestly source, exilic to Persian period",
        "critWhy": "Its vocabulary and cultic concerns match the priestly material "
                   "elsewhere in the Torah, associated with the Second Temple.",
        "critSource": "Wellhausen, Prolegomena, 1878",
        "gap": "wide",
    },
    "numbers": {
        "trad": "Moses, 15th-13th century BCE",
        "tradWhy": "Traditional Mosaic authorship of the Torah as a whole.",
        "tradSource": TALMUD,
        "crit": "Composite; final form Persian period",
        "critWhy": "Contains very old poetry, notably the Oracles of Balaam, "
                   "inside a later narrative frame.",
        "critSource": "William F. Albright, 'The Oracles of Balaam', Journal of "
                      "Biblical Literature, 1944",
        "gap": "wide",
    },
    "deuteronomy": {
        "trad": "Moses, shortly before his death",
        "tradWhy": "Presented as Moses' farewell addresses; the book describes him "
                   "writing the law and entrusting it to the Levites.",
        "tradSource": f"Deuteronomy 31:9, 24-26; {TALMUD}",
        "crit": "7th century BCE, connected to Josiah's reform of 622",
        "critWhy": "The law book found in the temple matches Deuteronomy's "
                   "distinctive demand for a single sanctuary, and its style "
                   "differs sharply from the rest of the Torah.",
        "critSource": "W. M. L. de Wette, 1805; the correspondence is with "
                      "2 Kings 22:8-23:25",
        "gap": "wide",
    },

    # ---- Deuteronomistic History ----------------------------------------
    "joshua": {
        "trad": "Joshua, with a later hand for the account of his death",
        "tradWhy": "The Talmud assigns the book to Joshua himself.",
        "tradSource": TALMUD,
        "crit": "Part of the Deuteronomistic History, 7th-6th century BCE",
        "critWhy": "Shares the language and theology of Deuteronomy, and the "
                   "recurring phrase 'to this day' implies a much later vantage.",
        "critSource": "Martin Noth, Uberlieferungsgeschichtliche Studien, 1943",
        "gap": "wide",
    },
    "judges": {
        "trad": "Samuel",
        "tradWhy": "The Talmud assigns Judges to Samuel.",
        "tradSource": TALMUD,
        "crit": "Deuteronomistic History, 7th-6th century BCE, around older material",
        "critWhy": "The Song of Deborah in chapter 5 is archaic Hebrew, older than "
                   "the prose account of the same events in chapter 4.",
        "critSource": "Noth, 1943; on the antiquity of chapter 5, Albright, 1936",
        "gap": "wide",
    },
    "1-samuel": {
        "trad": "Samuel, continued by the prophets Nathan and Gad",
        "tradWhy": "Chronicles names records kept by Samuel, Nathan and Gad, and "
                   "the Talmud builds its attribution on that.",
        "tradSource": f"1 Chronicles 29:29; {TALMUD}",
        "crit": "Deuteronomistic History, 7th-6th century BCE",
        "critWhy": "Samuel dies partway through the book that bears his name.",
        "critSource": "Noth, 1943; 1 Samuel 25:1",
        "gap": "wide",
    },
    "2-samuel": {
        "trad": "Nathan and Gad, Samuel having died",
        "tradWhy": "The Talmud continues the attribution to the surviving prophets.",
        "tradSource": f"{TALMUD}; 1 Chronicles 29:29",
        "crit": "Deuteronomistic History, 7th-6th century BCE",
        "critWhy": "The Succession Narrative in chapters 9-20 is regarded by many "
                   "as among the oldest sustained prose in the Bible, later "
                   "incorporated into the larger work.",
        "critSource": "Leonhard Rost, Die Uberlieferung von der Thronnachfolge "
                      "Davids, 1926",
        "gap": "narrow",
    },
    "1-kings": {
        "trad": "Jeremiah",
        "tradWhy": "The Talmud assigns Kings to Jeremiah.",
        "tradSource": TALMUD,
        "crit": "Deuteronomistic History; a first edition under Josiah, a second "
                "in exile",
        "critWhy": "The book cites royal annals as its sources and carries the "
                   "story into the exile.",
        "critSource": "Frank Moore Cross, Canaanite Myth and Hebrew Epic, 1973, "
                      "revising Noth's single-exilic model",
        "gap": "narrow",
    },
    "2-kings": {
        "trad": "Jeremiah",
        "tradWhy": "The Talmud assigns Kings to Jeremiah.",
        "tradSource": TALMUD,
        "crit": "Deuteronomistic History, completed in exile after 561 BCE",
        "critWhy": "It ends with Jehoiachin's release from prison, an event dated "
                   "to 561, which the book cannot precede.",
        "critSource": "2 Kings 25:27-30; Noth, 1943",
        "gap": "narrow",
    },

    # ---- Prophets --------------------------------------------------------
    "amos": {
        "trad": "Amos of Tekoa, c. 760-750 BCE",
        "tradWhy": "The book names its prophet and dates him by two reigns.",
        "tradSource": "Amos 1:1",
        "crit": "Amos, c. 760-750 BCE, with later editorial additions",
        "critWhy": "The core oracles are accepted as genuinely his; the closing "
                   "promise of restoration is often judged a later addition.",
        "critSource": "Amos 9:11-15; Wellhausen, Die kleinen Propheten, 1892",
        "gap": "none",
    },
    "hosea": {
        "trad": "Hosea, 8th century BCE",
        "tradWhy": "Named and dated in the book's opening verse.",
        "tradSource": "Hosea 1:1",
        "crit": "Hosea, 8th century BCE, with later Judean editing",
        "critWhy": "References to Judah in a northern prophet's book are widely "
                   "taken as southern additions.",
        "critSource": "Hosea 1:1, 1:7; Wellhausen, Die kleinen Propheten, 1892",
        "gap": "none",
    },
    "isaiah-1-39-first-isaiah": {
        "trad": "Isaiah son of Amoz wrote the whole book, 8th century BCE",
        "tradWhy": "The book is one scroll under one name. Ben Sira, writing "
                   "c. 180 BCE, already credits the single prophet Isaiah with "
                   "comforting the mourners of Zion, which is the language of "
                   "chapter 40 onward. The Great Isaiah Scroll from Qumran "
                   "carries all 66 chapters continuously.",
        "tradSource": "Sirach 48:22-25, in this volume; 1QIsa-a (Qumran, "
                      "2nd century BCE); Isaiah 1:1",
        "crit": "Isaiah of Jerusalem, c. 740-700 BCE",
        "critWhy": "Chapters 1-39 address the 8th-century Assyrian crisis; from "
                   "chapter 40 the audience is in Babylonian exile 150 years "
                   "later, with different vocabulary and theology.",
        "critSource": "J. C. Doderlein, 1775; Bernhard Duhm, Das Buch Jesaia, 1892",
        "gap": "wide",
    },
    "isaiah-40-55-second-isaiah": {
        "trad": "Isaiah son of Amoz, writing prophetically of the exile",
        "tradWhy": "Naming Cyrus before his birth is understood as genuine "
                   "foreknowledge rather than evidence of a late writer.",
        "tradSource": "Isaiah 44:28, 45:1; Isaiah 46:9-10 on declaring the end "
                      "from the beginning",
        "crit": "An anonymous prophet in Babylon, c. 550-540 BCE",
        "critWhy": "It addresses exiles as a present audience and treats the rise "
                   "of Cyrus as current events.",
        "critSource": "Doderlein, 1775; Duhm, 1892",
        "gap": "wide",
    },
    "isaiah-56-66-third-isaiah": {
        "trad": "Isaiah son of Amoz",
        "tradWhy": "Part of the single scroll bearing his name.",
        "tradSource": "Isaiah 1:1; 1QIsa-a",
        "crit": "Anonymous, after the return, c. 537-500 BCE",
        "critWhy": "It presupposes a community back in the land with the temple "
                   "in view.",
        "critSource": "Duhm, 1892, who first separated these chapters",
        "gap": "wide",
    },
    "jeremiah": {
        "trad": "Jeremiah, dictated to his scribe Baruch",
        "tradWhy": "The book describes exactly that process, twice.",
        "tradSource": "Jeremiah 36:4, 36:32",
        "crit": "Jeremiah, with substantial later editing",
        "critWhy": "The Greek text is about an eighth shorter and differently "
                   "ordered, showing the book still circulated in more than one "
                   "form. Qumran preserves fragments of both.",
        "critSource": "4QJer-b (short form) and 4QJer-a (long form); Emanuel Tov, "
                      "Textual Criticism of the Hebrew Bible, 1992",
        "gap": "narrow",
    },
    "ezekiel": {
        "trad": "Ezekiel the priest, in exile, 593-571 BCE",
        "tradWhy": "The book is precisely dated throughout and written in the "
                   "first person.",
        "tradSource": "Ezekiel 1:1-3, and the fourteen dated oracles thereafter",
        "crit": "Ezekiel, 593-571 BCE, with a later editorial school",
        "critWhy": "Its internal dates are unusually consistent, and the critical "
                   "and traditional positions sit closer here than almost anywhere "
                   "else in the prophets.",
        "critSource": "Walther Zimmerli, Ezechiel, 1969",
        "gap": "none",
    },
    "daniel": {
        "trad": "Daniel, 6th century BCE, in Babylon and Persia",
        "tradWhy": "The book presents itself as Daniel's, set in the exile, and "
                   "Jesus refers to it as the work of 'the prophet Daniel'.",
        "tradSource": "Daniel 7:1, 8:1; Matthew 24:15",
        "crit": "c. 165 BCE, during the Maccabean crisis",
        "critWhy": "Chapter 11 tracks Hellenistic dynastic politics in detail up "
                   "to Antiochus IV, then its account of his death diverges from "
                   "what happened, which places the writer at that moment.",
        "critSource": "Porphyry, 3rd century, preserved in Jerome's Commentary on "
                      "Daniel; the divergence is at Daniel 11:40-45",
        "gap": "wide",
    },
    "jonah": {
        "trad": "Jonah son of Amittai, 8th century BCE",
        "tradWhy": "It names the prophet known from the reign of Jeroboam II, and "
                   "Jesus refers to the sign of Jonah.",
        "tradSource": "Jonah 1:1; 2 Kings 14:25; Matthew 12:39-41",
        "crit": "Post-exilic, c. 400-300 BCE",
        "critWhy": "Late Hebrew, Aramaic loanwords, and Nineveh described in the "
                   "past tense as a city that was great.",
        "critSource": "Jonah 3:3; Otto Eissfeldt, The Old Testament: An "
                      "Introduction, 1934",
        "gap": "wide",
    },
    "joel": {
        "trad": "Joel, 9th century BCE",
        "tradWhy": "Its placement among the earlier of the Twelve was traditionally "
                   "taken to imply an early date.",
        "tradSource": "Position in the Masoretic order of the Twelve; Joel 1:1, "
                      "which gives no king and so no fixed date",
        "crit": "Post-exilic, c. 400-350 BCE",
        "critWhy": "It assumes a functioning temple and no monarchy, and mentions "
                   "Greeks as distant slave-traders.",
        "critSource": "Joel 3:6; Hans Walter Wolff, Joel and Amos, 1969",
        "gap": "wide",
    },
    "zechariah-9-14": {
        "trad": "Zechariah, late 6th century BCE",
        "tradWhy": "Part of the single book bearing his name.",
        "tradSource": "Zechariah 1:1",
        "crit": "Anonymous, 4th-3rd century BCE",
        "critWhy": "The book shifts from precisely dated oracles about rebuilding "
                   "to undated apocalyptic, and Greece appears as a power.",
        "critSource": "Zechariah 9:13; Joseph Mede, 1653, who first argued the "
                      "division",
        "gap": "wide",
    },

    # ---- Writings --------------------------------------------------------
    "job": {
        "trad": "Moses, or an ancient author of the patriarchal era",
        "tradWhy": "The Talmud suggests Moses. The setting has wealth counted in "
                   "livestock, sacrifice offered by the head of the family, and no "
                   "mention of Israel, the law or the temple.",
        "tradSource": f"{TALMUD}; Job 1:3, 1:5, 42:11",
        "crit": "6th-4th century BCE, around an older folk tale",
        "critWhy": "The prose frame and the poetic dialogue differ in style and "
                   "outlook, and the Hebrew carries Aramaisms.",
        "critSource": "Job 1-2 and 42:7-17 against 3:1-42:6; Marvin Pope, Job, "
                      "Anchor Bible, 1965",
        "gap": "wide",
    },
    "psalms": {
        "trad": "David wrote most, with Asaph, the sons of Korah, Solomon and Moses",
        "tradWhy": "Seventy-three psalms carry Davidic superscriptions, and the "
                   "apostles cite psalms as David's own words.",
        "tradSource": "Superscriptions throughout; Acts 2:25, 4:25; Mark 12:36",
        "crit": "A collection spanning centuries, compiled by the Persian period",
        "critWhy": "Some psalms presuppose the exile. The Hebrew preposition in "
                   "the superscriptions can mean 'belonging to' or 'in the manner "
                   "of' as readily as 'by'.",
        "critSource": "Psalm 137:1; Hermann Gunkel, Einleitung in die Psalmen, 1933",
        "gap": "narrow",
    },
    "proverbs": {
        "trad": "Solomon, 10th century BCE",
        "tradWhy": "The book opens in his name and Kings credits him with three "
                   "thousand proverbs.",
        "tradSource": "Proverbs 1:1; 1 Kings 4:32",
        "crit": "A compilation of several collections; final form post-exilic",
        "critWhy": "The book names other authors within itself, and one collection "
                   "is explicitly said to have been copied out by Hezekiah's men, "
                   "some two and a half centuries after Solomon.",
        "critSource": "Proverbs 25:1, 30:1, 31:1",
        "gap": "narrow",
    },
    "ecclesiastes": {
        "trad": "Solomon in old age",
        "tradWhy": "The speaker calls himself son of David, king in Jerusalem.",
        "tradSource": "Ecclesiastes 1:1, 1:12",
        "crit": "c. 300-250 BCE",
        "critWhy": "Late Hebrew with Persian loanwords, and a speaker who looks "
                   "back on kingship rather than exercising it.",
        "critSource": "Persian 'pardes' at Ecclesiastes 2:5; Franz Delitzsch, 1875, "
                      "who judged the language decisive against Solomonic authorship",
        "gap": "wide",
    },
    "song-of-songs": {
        "trad": "Solomon, 10th century BCE",
        "tradWhy": "Ascribed to Solomon in its opening line.",
        "tradSource": "Song of Songs 1:1",
        "crit": "Genuinely unsettled, from the 10th to the 3rd century BCE",
        "critWhy": "Persian loanwords point late; the poetry closely resembles much "
                   "older Egyptian love song. Neither argument has carried the day.",
        "critSource": "Persian 'pardes' at Song 4:13; Michael V. Fox, The Song of "
                      "Songs and the Ancient Egyptian Love Songs, 1985",
        "gap": "wide",
    },
    "ruth": {
        "trad": "Samuel",
        "tradWhy": "The Talmud assigns Ruth to Samuel; the story is set in the "
                   "period of the judges.",
        "tradSource": f"{TALMUD}; Ruth 1:1",
        "crit": "Disputed; post-exilic on one reading, pre-exilic on another",
        "critWhy": "Often read as a response to the post-exilic dissolution of "
                   "foreign marriages, since its heroine is a Moabite ancestor of "
                   "David. Against that, its Hebrew is classical rather than late.",
        "critSource": "Ezra 10:10-11 for the setting proposed; on the classical "
                      "Hebrew, Edward F. Campbell, Ruth, Anchor Bible, 1975",
        "gap": "wide",
    },
    "1-chronicles": {
        "trad": "Ezra",
        "tradWhy": "The Talmud assigns Chronicles to Ezra.",
        "tradSource": TALMUD,
        "crit": "An anonymous Chronicler, c. 400-350 BCE",
        "critWhy": "The genealogy of David's line runs several generations past "
                   "the exile.",
        "critSource": "1 Chronicles 3:19-24; Sara Japhet, I and II Chronicles, 1993",
        "gap": "narrow",
    },
    "2-chronicles": {
        "trad": "Ezra",
        "tradWhy": "The Talmud assigns Chronicles to Ezra.",
        "tradSource": TALMUD,
        "crit": "An anonymous Chronicler, c. 400-350 BCE",
        "critWhy": "It ends mid-sentence with the decree of Cyrus, at precisely "
                   "the point where Ezra begins.",
        "critSource": "2 Chronicles 36:22-23 against Ezra 1:1-3",
        "gap": "narrow",
    },
    "esther-hebrew": {
        "trad": "Mordecai",
        "tradWhy": "The book records Mordecai writing these things down and "
                   "sending letters.",
        "tradSource": "Esther 9:20",
        "crit": "4th-3rd century BCE",
        "critWhy": "Written to account for the origin of Purim, a festival with no "
                   "basis in the Torah. God is never named in the book.",
        "critSource": "Esther 9:26-28; Carey Moore, Esther, Anchor Bible, 1971",
        "gap": "narrow",
    },

    # ---- New Testament ---------------------------------------------------
    "matthew": {
        "trad": "Matthew the apostle, c. 50-60 CE",
        "tradWhy": "Papias, writing within living memory, reports that Matthew "
                   "compiled the sayings in the Hebrew tongue.",
        "tradSource": "Papias, in this volume, Fragment VI; via Eusebius, "
                      "Ecclesiastical History 3.39.16",
        "crit": "Anonymous, c. 80-90 CE, using Mark",
        "critWhy": "It reproduces about ninety per cent of Mark, which an "
                   "eyewitness apostle would have little need to do, and its "
                   "parable of the burned city is widely read as knowing of "
                   "Jerusalem's fall in 70.",
        "critSource": "Matthew 22:7; on Markan priority, Karl Lachmann, 1835",
        "gap": "narrow",
    },
    "mark": {
        "trad": "Mark, recording Peter's preaching, c. 50s-60s CE",
        "tradWhy": "Papias states that Mark was Peter's interpreter and wrote down "
                   "accurately, though not in order, what Peter taught.",
        "tradSource": "Papias, in this volume, Fragment VI; via Eusebius, "
                      "Ecclesiastical History 3.39.15",
        "crit": "Anonymous, c. 65-75 CE; the earliest of the gospels",
        "critWhy": "Its priority is broadly agreed, and chapter 13 suggests the "
                   "Jewish revolt is under way or just past.",
        "critSource": "Mark 13:1-2, 13:14; Lachmann, 1835; H. J. Holtzmann, 1863",
        "gap": "none",
    },
    "luke": {
        "trad": "Luke the physician, Paul's companion, c. 60-62 CE",
        "tradWhy": "Irenaeus names Luke as the author. The narrative of Acts "
                   "switches to the first person during the voyages, implying a "
                   "travelling companion, and it ends with Paul still alive.",
        "tradSource": "Irenaeus, Against Heresies 3.1.1; Acts 16:10, 27:1; "
                      "Colossians 4:14",
        "crit": "Anonymous, c. 80-90 CE, using Mark",
        "critWhy": "It depends on Mark, and its version of the Olivet discourse "
                   "describes an army encircling Jerusalem, read as the siege of "
                   "70 in retrospect.",
        "critSource": "Luke 21:20 against Mark 13:14; Lachmann, 1835",
        "gap": "narrow",
    },
    "john": {
        "trad": "John the apostle, son of Zebedee, c. 90 CE",
        "tradWhy": "Irenaeus names John, the disciple who leaned on the Lord's "
                   "breast, publishing the gospel at Ephesus, and the book itself "
                   "claims eyewitness testimony.",
        "tradSource": "Irenaeus, Against Heresies 3.1.1; John 21:24",
        "crit": "A Johannine community, c. 90-110 CE",
        "critWhy": "Chapter 21 reads as an appendix after a formal ending, and the "
                   "language about being put out of the synagogue suits a later "
                   "setting than the ministry it narrates.",
        "critSource": "John 20:30-31 followed by chapter 21; John 9:22, 16:2; "
                      "J. Louis Martyn, History and Theology in the Fourth Gospel, "
                      "1968",
        "gap": "narrow",
    },
    "acts": {
        "trad": "Luke, c. 62 CE",
        "tradWhy": "Same author as the gospel, addressed to the same patron, and "
                   "it breaks off with Paul under house arrest rather than "
                   "recording his death.",
        "tradSource": "Acts 1:1 with Luke 1:3; Acts 28:30-31",
        "crit": "Anonymous, c. 80-90 CE",
        "critWhy": "It follows the gospel of Luke, which is itself dated after Mark.",
        "critSource": "Acts 1:1; Henry Cadbury, The Making of Luke-Acts, 1927",
        "gap": "narrow",
    },
    "ephesians": {
        "trad": "Paul, c. 60-62 CE, from prison",
        "tradWhy": "The letter names Paul as its author twice.",
        "tradSource": "Ephesians 1:1, 3:1",
        "crit": "A follower of Paul, c. 80-100 CE",
        "critWhy": "Its vocabulary and very long sentences differ from the "
                   "undisputed letters, and it runs closely parallel to Colossians "
                   "throughout.",
        "critSource": "Ephesians 6:21-22 against Colossians 4:7-8; "
                      "Edgar Goodspeed, The Meaning of Ephesians, 1933",
        "gap": "wide",
    },
    "colossians": {
        "trad": "Paul, c. 60-62 CE",
        "tradWhy": "Names Paul and Timothy, and its personal greetings match those "
                   "of Philemon, a letter nobody disputes.",
        "tradSource": "Colossians 1:1, 4:10-14 against Philemon 23-24",
        "crit": "Disputed; Paul or a close follower, c. 60-80 CE",
        "critWhy": "Style and a more cosmic Christology than the undisputed "
                   "letters, though the personal detail is hard to explain as "
                   "invention.",
        "critSource": "Colossians 1:15-20; Eduard Lohse, Colossians and Philemon, "
                      "1971",
        "gap": "narrow",
    },
    "2-thessalonians": {
        "trad": "Paul, c. 51-52 CE",
        "tradWhy": "Names Paul, Silvanus and Timothy, as does the first letter.",
        "tradSource": "2 Thessalonians 1:1",
        "crit": "Disputed",
        "critWhy": "Its sequence of end-time events is hard to square with the "
                   "first letter's thief in the night, and it warns readers against "
                   "letters forged in Paul's name.",
        "critSource": "2 Thessalonians 2:1-4 against 1 Thessalonians 5:2; "
                      "2 Thessalonians 2:2, 3:17",
        "gap": "narrow",
    },
    "1-timothy": {
        "trad": "Paul, c. 62-64 CE, after release from a first Roman imprisonment",
        "tradWhy": "Names Paul, and assumes travels not recorded in Acts, which "
                   "tradition explains by a later missionary period.",
        "tradSource": "1 Timothy 1:1, 1:3; Eusebius, Ecclesiastical History 2.22, "
                      "on a release and second imprisonment",
        "crit": "A follower of Paul, c. 90-110 CE",
        "critWhy": "The three Pastorals share a vocabulary unlike Paul's and "
                   "address a settled church order of overseers and deacons.",
        "critSource": "1 Timothy 3:1-13; Friedrich Schleiermacher, 1807; "
                      "P. N. Harrison, The Problem of the Pastoral Epistles, 1921",
        "gap": "wide",
    },
    "2-timothy": {
        "trad": "Paul, c. 64-67 CE, shortly before his execution",
        "tradWhy": "Reads as a farewell, and is the most personal of the three.",
        "tradSource": "2 Timothy 4:6-8",
        "crit": "A follower of Paul, c. 90-110 CE",
        "critWhy": "Grouped with the other Pastorals on shared vocabulary and "
                   "style.",
        "critSource": "Harrison, 1921",
        "gap": "wide",
    },
    "titus": {
        "trad": "Paul, c. 63-65 CE",
        "tradWhy": "Names Paul, and assumes a mission in Crete.",
        "tradSource": "Titus 1:1, 1:5",
        "crit": "A follower of Paul, c. 90-110 CE",
        "critWhy": "Grouped with the other Pastorals on shared vocabulary and "
                   "church order.",
        "critSource": "Titus 1:5-9; Harrison, 1921",
        "gap": "wide",
    },
    "hebrews": {
        "trad": "Paul, or Barnabas, Apollos or Luke",
        "tradWhy": "It circulated among the Pauline letters in the East, which "
                   "helped secure its place in the canon, though its authorship "
                   "was argued over from the start.",
        "tradSource": "P46, c. 200, which places Hebrews among Paul's letters; "
                      "Tertullian, On Modesty 20, proposing Barnabas",
        "crit": "Anonymous, c. 60-90 CE",
        "critWhy": "The letter never names its author, and Origen said outright "
                   "that only God knows who wrote it.",
        "critSource": "Origen, quoted in Eusebius, Ecclesiastical History 6.25.14",
        "gap": "narrow",
    },
    "james": {
        "trad": "James the brother of Jesus, before 62 CE",
        "tradWhy": "Attributed to James, leader of the Jerusalem church, whose "
                   "death Eusebius places in the early 60s.",
        "tradSource": "James 1:1; Galatians 1:19; Eusebius, Ecclesiastical History "
                      "2.23",
        "crit": "Disputed, anywhere from 45 to 120 CE",
        "critWhy": "Its polished Greek is unexpected from a Galilean, and its "
                   "treatment of faith and works is read by some as answering "
                   "Paul, which would require a later date.",
        "critSource": "James 2:14-26 against Romans 3:28; Martin Dibelius, Der "
                      "Brief des Jakobus, 1921",
        "gap": "wide",
    },
    "1-peter": {
        "trad": "Peter the apostle, c. 62-64 CE",
        "tradWhy": "Names Peter, and names Silvanus as the hand that wrote it, "
                   "which accounts for the polished Greek.",
        "tradSource": "1 Peter 1:1, 5:12",
        "crit": "Disputed; Peter or a follower, c. 70-90 CE",
        "critWhy": "It addresses persecution across Asia Minor, and its use of "
                   "'Babylon' for Rome is characteristic of the period after "
                   "70 CE.",
        "critSource": "1 Peter 5:13; compare Revelation 17:5 and 2 Esdras 3:1-2, "
                      "both in this volume",
        "gap": "narrow",
    },
    "2-peter": {
        "trad": "Peter the apostle, c. 65-68 CE",
        "tradWhy": "Names Peter and claims eyewitness presence at the "
                   "transfiguration.",
        "tradSource": "2 Peter 1:1, 1:16-18",
        "crit": "Pseudonymous, c. 110-150 CE; the latest writing in the New "
                "Testament",
        "critWhy": "It reuses Jude, refers to Paul's letters as an established "
                   "collection of scripture, and answers the problem of a second "
                   "coming that has not arrived. It was the most disputed book in "
                   "the early church.",
        "critSource": "2 Peter 2 against Jude 4-16; 2 Peter 3:15-16; 2 Peter 3:4; "
                      "Eusebius, Ecclesiastical History 3.25, listing it as disputed",
        "gap": "wide",
    },
    "jude": {
        "trad": "Jude the brother of James, c. 60-65 CE",
        "tradWhy": "Names itself as from Jude, a servant of Jesus Christ and "
                   "brother of James.",
        "tradSource": "Jude 1; Mark 6:3",
        "crit": "Disputed, c. 50-100 CE",
        "critWhy": "It quotes 1 Enoch as prophecy, which shows how wide the range "
                   "of authoritative writing still was.",
        "critSource": "Jude 14-15 quoting 1 Enoch 1:9, both in this volume",
        "gap": "narrow",
    },
    "revelation": {
        "trad": "John the apostle, c. 95 CE, on Patmos",
        "tradWhy": "Irenaeus places the vision at the end of Domitian's reign and "
                   "identifies its author with the apostle.",
        "tradSource": "Irenaeus, Against Heresies 5.30.3; Revelation 1:9",
        "crit": "John of Patmos, a different John, c. 95 CE",
        "critWhy": "The date is broadly agreed. The Greek differs so sharply from "
                   "the gospel of John that common authorship is doubted, an "
                   "objection raised as early as the third century.",
        "critSource": "Dionysius of Alexandria, quoted in Eusebius, Ecclesiastical "
                      "History 7.25",
        "gap": "none",
    },

    # ---- Second Temple and later -----------------------------------------
    "jubilees": {
        "trad": "Revelation given to Moses at Sinai",
        "tradWhy": "The book presents itself as dictated to Moses by an angel of "
                   "the presence. It is canonical scripture in the Ethiopian "
                   "Orthodox Tewahedo Church.",
        "tradSource": "Jubilees, Prologue and 1:27, in this volume",
        "crit": "c. 160-150 BCE",
        "critWhy": "Its 364-day solar calendar and priestly preoccupations fit the "
                   "Maccabean era, and Hebrew fragments were found at Qumran.",
        "critSource": "Jubilees 6:32-38, in this volume; 4Q216-4Q228 (Qumran); "
                      "James VanderKam, The Book of Jubilees, 2001",
        "gap": "wide",
    },
    "1-enoch-the-book-of-the-watchers-chapters-1-36": {
        "trad": "Enoch, seventh from Adam, before the flood",
        "tradWhy": "The book claims Enoch as its author, and Jude quotes it as "
                   "prophecy from Enoch, the seventh from Adam. It is canonical in "
                   "the Ethiopian Orthodox Tewahedo Church.",
        "tradSource": "1 Enoch 1:1-2 and Jude 14-15, both in this volume",
        "crit": "3rd century BCE",
        "critWhy": "Aramaic fragments at Qumran place it among the earliest Jewish "
                   "apocalyptic writing.",
        "critSource": "4QEn-a (Qumran); J. T. Milik, The Books of Enoch, 1976",
        "gap": "wide",
    },
    "the-first-epistle-of-clement-to-the-corinthians": {
        "trad": "Clement of Rome, c. 95-97 CE",
        "tradWhy": "Early and consistent attribution, and some churches read it "
                   "publicly alongside scripture.",
        "tradSource": "Irenaeus, Against Heresies 3.3.3; Eusebius, Ecclesiastical "
                      "History 3.16 and 4.23 on its public reading at Corinth",
        "crit": "Clement of Rome, c. 95-97 CE",
        "critWhy": "Rarely disputed, and among the earliest Christian writings "
                   "outside the New Testament.",
        "critSource": "Eusebius, Ecclesiastical History 3.16",
        "gap": "none",
    },
    "the-teaching-of-the-twelve-apostles-didache": {
        "trad": "The teaching of the twelve apostles",
        "tradWhy": "Its title claims apostolic teaching, and it stood near "
                   "scripture in some early lists.",
        "tradSource": "The title itself; Eusebius, Ecclesiastical History 3.25, "
                      "which lists it among disputed writings",
        "crit": "Anonymous, c. 50-120 CE",
        "critWhy": "Possibly as old as the gospels. It was lost for centuries and "
                   "rediscovered in a Constantinople manuscript in 1873.",
        "critSource": "Codex Hierosolymitanus 54, found by Philotheos Bryennios, "
                      "1873",
        "gap": "narrow",
    },
    # ------------------------------------------------------------------
    # Added later, and only where the evidence is checkable.
    #
    # 104 works carried text and no position. Most of that number is
    # sub-units -- the Shepherd of Hermas is one book in twenty-seven
    # entries, Ignatius one corpus in seven letters, the Twelve Patriarchs
    # one work in twelve -- so the real count of editorial units wanting a
    # position was about forty-seven.
    #
    # These are the ones whose dating rests on something a reader can go
    # and check: a book that dates itself (Haggai to the day, Sirach's
    # prologue to the thirty-eighth year of Euergetes, 2 Maccabees to the
    # Seleucid year 188), a book that fixes itself between two events
    # anyone can date (Nahum, after Thebes and before Nineveh), or an
    # ancient witness naming the author (Irenaeus on Polycarp, Eusebius on
    # Papias, the Talmud on Lamentations).
    #
    # Where the honest answer needed a monograph this file could not
    # verify, no position was written. A record invented to fill a gap
    # would be exactly the assertion this file exists to refuse, and the
    # empty ones are visible: the audit prints NO-POSITION for each.

    # ---- prophets whose superscription dates them and whose text fixes it ----
    "micah": {
        "trad": "Micah of Moresheth, c. 750-686 BCE",
        "tradWhy": "The book's own superscription places him in the reigns of "
                   "Jotham, Ahaz and Hezekiah of Judah. Jeremiah's hearers cite "
                   "Micah by name as a prophet of Hezekiah's day and quote "
                   "Micah 3:12 back verbatim, which is the earliest external "
                   "attestation any writing prophet has.",
        "tradSource": "Micah 1:1; Jeremiah 26:18-19, quoting Micah 3:12",
        "crit": "An eighth-century core, c. 740-700 BCE, enlarged in the exile "
                "and after",
        "critWhy": "Chapters 1-3 are read as the prophet's own and match the "
                   "Assyrian crisis they describe. Chapters 4-7 look later: "
                   "4:10 tells Zion she will go to Babylon and be rescued "
                   "there, which is the sixth-century exile rather than the "
                   "eighth-century Assyrian threat the opening chapters face.",
        "critSource": "Micah 4:10, naming Babylon; the seam between chapters 3 "
                      "and 4 in the book itself",
        "gap": "narrow",
    },
    "zephaniah": {
        "trad": "Zephaniah, in the reign of Josiah, 640-609 BCE",
        "tradWhy": "The superscription names four generations of his ancestry "
                   "and sets him under Josiah king of Judah.",
        "tradSource": "Zephaniah 1:1",
        "crit": "Josiah's reign, c. 640-609 BCE",
        "critWhy": "The critical reading takes the superscription at its word "
                   "here. The book attacks foreign cult practice in Jerusalem "
                   "of exactly the kind Josiah's reform is said to have swept "
                   "out, so the setting the book claims and the setting its "
                   "contents fit are the same one.",
        "critSource": "Zephaniah 1:4-6 against the reform of 2 Kings 23",
        "gap": "none",
    },
    "nahum": {
        "trad": "Nahum the Elkoshite, before the fall of Nineveh in 612 BCE",
        "tradWhy": "The book heads itself as his vision, and its subject is the "
                   "destruction of Nineveh as a thing still to come.",
        "tradSource": "Nahum 1:1",
        "crit": "663-612 BCE",
        "critWhy": "The book dates itself at both ends. It speaks of the fall "
                   "of No-Amon -- Thebes -- as an event already past, and "
                   "Thebes fell to Ashurbanipal in 663 BCE; and it speaks of "
                   "the fall of Nineveh as still to come, and Nineveh fell in "
                   "612. Between those two the poem must sit.",
        "critSource": "Nahum 3:8-10 on Thebes, against the fall of Nineveh in "
                      "612 BCE",
        "gap": "none",
    },
    "habakkuk": {
        "trad": "Habakkuk the prophet, late 7th century BCE",
        "tradWhy": "The book heads itself as his oracle, and the Greek addition "
                   "Bel and the Dragon -- printed in this volume -- names him "
                   "as a prophet in Judaea.",
        "tradSource": "Habakkuk 1:1; Bel and the Dragon 33-39",
        "crit": "c. 605 BCE, as the Chaldeans rise",
        "critWhy": "The answer the prophet is given names the instrument: God "
                   "is raising up the Chaldeans, 'that bitter and hasty "
                   "nation'. Babylon became the power to fear at Carchemish in "
                   "605 BCE, and the book reads as written while that was new "
                   "and not yet the exile.",
        "critSource": "Habakkuk 1:6, naming the Chaldeans as a rising power",
        "gap": "none",
    },
    "obadiah": {
        "trad": "Obadiah the prophet",
        "tradWhy": "The book heads itself with his name alone and gives no "
                   "reign, which is why tradition has placed him anywhere from "
                   "the ninth century to the sixth.",
        "tradSource": "Obadiah 1",
        "crit": "Shortly after 587 BCE",
        "critWhy": "The charge against Edom is not general: it is that they "
                   "stood by on the day strangers carried off Jerusalem's "
                   "wealth, entered the gate of God's people in the day of "
                   "their calamity, and cut off those who escaped. That is the "
                   "fall of Jerusalem, described by someone who watched it.",
        "critSource": "Obadiah 11-14",
        "gap": "wide",
    },
    "lamentations": {
        "trad": "Jeremiah, shortly after 587 BCE",
        "tradWhy": "The Talmud's list of who wrote what assigns Lamentations to "
                   "Jeremiah, and the Greek translation prefaces the book with "
                   "a line saying Jeremiah sat weeping over Jerusalem and spoke "
                   "this lament. The Hebrew text carries no such heading.",
        "tradSource": "Talmud, Bava Batra 15a; the Septuagint superscription to "
                      "Lamentations",
        "crit": "Anonymous, shortly after 587 BCE",
        "critWhy": "The date is not in dispute -- the poems are eyewitness to "
                   "the siege and its aftermath -- but the authorship is. The "
                   "book is five acrostics of high formal control rather than "
                   "prophetic oracle, the Hebrew carries no attribution, and "
                   "its view of the last kings differs from Jeremiah's.",
        "critSource": "The absence of any attribution in the Hebrew text; the "
                      "acrostic form of chapters 1-4",
        "gap": "none",
    },
    "haggai": {
        "trad": "Haggai the prophet, 520 BCE",
        "tradWhy": "Every oracle in the book is dated to the day, by regnal "
                   "year of Darius, and Ezra names Haggai and Zechariah as the "
                   "prophets who got the temple rebuilt.",
        "tradSource": "Haggai 1:1, 2:1, 2:10, 2:20; Ezra 5:1, 6:14",
        "crit": "520 BCE",
        "critWhy": "One of the few books whose date is not an inference. It "
                   "dates itself five times to the second year of Darius, and "
                   "the second year of Darius I is 520 BCE by the Babylonian "
                   "king lists; the building it urges is the temple finished in "
                   "516.",
        "critSource": "The book's own regnal dating against the Babylonian "
                      "chronology of Darius I",
        "gap": "none",
    },
    "zechariah-1-8": {
        "trad": "Zechariah son of Berechiah, 520-518 BCE",
        "tradWhy": "The visions are dated by regnal year of Darius, and Ezra "
                   "pairs him with Haggai as the prophets of the rebuilding.",
        "tradSource": "Zechariah 1:1, 1:7, 7:1; Ezra 5:1, 6:14",
        "crit": "520-518 BCE",
        "critWhy": "Dated by the book itself, in the same manner as Haggai and "
                   "to the same years. Chapters 9-14 are a separate matter and "
                   "are printed separately in this volume: they carry no dates, "
                   "no Darius and no temple building, and name Greece as the "
                   "power in view.",
        "critSource": "The book's own regnal dating; the break in subject at "
                      "chapter 9, and Zechariah 9:13 naming Greece",
        "gap": "none",
    },
    "malachi": {
        "trad": "Malachi the prophet, 5th century BCE",
        "tradWhy": "The book heads itself with the name, and Jewish and "
                   "Christian tradition reads it as the last of the prophets "
                   "before the silence.",
        "tradSource": "Malachi 1:1",
        "crit": "c. 500-450 BCE, and 'Malachi' may be a title rather than a name",
        "critWhy": "The temple is standing and its sacrifices have gone stale, "
                   "so this is after 516; and the governor is called by the "
                   "Persian title pechah, so this is under Persian rule. The "
                   "name itself is the difficulty: mal'akhi is Hebrew for 'my "
                   "messenger', which is what 3:1 calls the figure God will "
                   "send, so the heading may have been taken from the text "
                   "rather than the text from an author.",
        "critSource": "Malachi 1:8 (the Persian title pechah), 1:10 (the temple "
                      "in use), and 3:1 against the heading at 1:1",
        "gap": "narrow",
    },

    # ---- books that date themselves in their own prologues and colophons ----
    "sirach-ecclesiasticus": {
        "trad": "Jesus ben Sira of Jerusalem, c. 180 BCE",
        "tradWhy": "The book names its own author, which almost nothing else in "
                   "this part of the library does: 'Jesus the son of Sirach, "
                   "the son of Eleazar, of Jerusalem.'",
        "tradSource": "Sirach 50:27",
        "crit": "Hebrew original c. 190-175 BCE; Greek translation after 132 BCE",
        "critWhy": "The translator's prologue is the clearest self-dating "
                   "document in the deuterocanon. He says he is the author's "
                   "grandson, that he came into Egypt in the thirty-eighth year "
                   "of Euergetes, and that he then translated his grandfather's "
                   "book. The thirty-eighth year of Ptolemy VIII Euergetes II "
                   "is 132 BCE, which puts the grandfather two generations "
                   "earlier -- and the praise of the high priest Simon in "
                   "chapter 50 reads as a living memory.",
        "critSource": "The translator's prologue to Sirach; Sirach 50:1-21 on "
                      "Simon son of Onias",
        "gap": "none",
    },
    "1-maccabees": {
        "trad": "A Jewish historian of the Hasmonean court, 2nd-1st century BCE",
        "tradWhy": "The book is anonymous and tradition has not assigned it an "
                   "author; it is received as a record of the revolt written "
                   "close to it.",
        "tradSource": "The book's own anonymity; Josephus uses it as a source "
                      "in Antiquities 12-13",
        "crit": "c. 100 BCE, after 134 BCE",
        "critWhy": "The narrative runs to the death of Simon and the accession "
                   "of John Hyrcanus, and then refers the reader to the "
                   "chronicle of Hyrcanus's own high priesthood as a finished "
                   "record -- so the author is writing after Hyrcanus's reign "
                   "was under way, which began in 134 BCE.",
        "critSource": "1 Maccabees 16:23-24",
        "gap": "none",
    },
    "2-maccabees": {
        "trad": "An epitome of Jason of Cyrene, 2nd-1st century BCE",
        "tradWhy": "The book says outright what it is: an abridgement into one "
                   "volume of the five books of Jason of Cyrene, made by an "
                   "epitomist who describes the labour of doing it.",
        "tradSource": "2 Maccabees 2:23-31",
        "crit": "c. 124 BCE or later",
        "critWhy": "The book opens with two letters to the Jews of Egypt, and "
                   "the second is dated to the hundred and eighty-eighth year "
                   "of the Seleucid era, which is 124 BCE. The epitome is "
                   "prefaced by them, so it is no earlier.",
        "critSource": "2 Maccabees 1:10, dating the letter to the Seleucid year "
                      "188",
        "gap": "none",
    },
    "judith": {
        "trad": "A record of the deliverance of Bethulia",
        "tradWhy": "The book is received as history in the traditions that "
                   "carry it, and Clement of Rome -- printed in this volume -- "
                   "holds Judith up beside Esther as a woman who saved her "
                   "people.",
        "tradSource": "1 Clement 55:4-5",
        "crit": "Hasmonean period, c. 150-100 BCE, and not history",
        "critWhy": "The opening sentence is impossible on purpose: "
                   "Nebuchadnezzar is called king of the Assyrians reigning in "
                   "Nineveh, when he was king of Babylon and Nineveh had fallen "
                   "before he took the throne. A book that begins by placing "
                   "the wrong king in a destroyed capital is not attempting a "
                   "chronicle, and the piety it teaches -- fasting, dietary "
                   "scruple, holy war -- is Hasmonean.",
        "critSource": "Judith 1:1, against the Babylonian chronicle of "
                      "Nebuchadnezzar II and the fall of Nineveh in 612 BCE",
        "gap": "wide",
    },
    "tobit": {
        "trad": "Tobit and Tobias, in the Assyrian exile, 8th-7th century BCE",
        "tradWhy": "The book presents itself as Tobit's own account, opening in "
                   "the first person and setting itself in the deportation "
                   "under Shalmaneser.",
        "tradSource": "Tobit 1:1-2",
        "crit": "c. 225-175 BCE",
        "critWhy": "Fragments of Tobit were found at Qumran in four Aramaic "
                   "copies and one Hebrew, which puts the book well before the "
                   "first century BCE and shows a Semitic original behind the "
                   "Greek. Its geography and its knowledge of Assyria are those "
                   "of a much later writer than its setting.",
        "critSource": "4Q196-200, the Tobit fragments from Qumran Cave 4",
        "gap": "wide",
    },
    "the-wisdom-of-solomon": {
        "trad": "Solomon",
        "tradWhy": "The book speaks throughout in the voice of a king chosen to "
                   "build a temple and given wisdom by prayer, which is "
                   "Solomon's part in 1 Kings, and the tradition that carries "
                   "the book names it for him.",
        "tradSource": "Wisdom of Solomon 9:7-8, echoing 1 Kings 3:6-9",
        "crit": "Alexandria, 1st century BCE",
        "critWhy": "The book was composed in Greek rather than translated into "
                   "it: it works in Greek philosophical vocabulary, argues with "
                   "Greek terms for the soul and immortality, and quotes the "
                   "Septuagint rather than the Hebrew. Solomon died some eight "
                   "centuries before any of that existed.",
        "critSource": "The book's Greek composition and its use of the "
                      "Septuagint; its Alexandrian polemic against Egyptian "
                      "animal cult at 11:15 and 15:18-19",
        "gap": "wide",
    },
    "2-esdras-4-ezra": {
        "trad": "Ezra the scribe",
        "tradWhy": "The apocalypse is spoken by Ezra ('I, Salathiel, who am "
                   "also called Ezra') and dated by its own opening to the "
                   "thirtieth year after the fall of the city.",
        "tradSource": "2 Esdras 3:1",
        "crit": "c. 100 CE, after the fall of Jerusalem in 70",
        "critWhy": "The eagle of the fifth vision is interpreted in the book "
                   "itself as the fourth kingdom of Daniel, and its three heads "
                   "are read as the Flavian emperors -- Vespasian, Titus and "
                   "Domitian. The city whose fall the seer mourns is not "
                   "Nebuchadnezzar's Jerusalem but Titus's, and 'the thirtieth "
                   "year' after 70 CE lands about 100.",
        "critSource": "2 Esdras 11-12, the eagle vision, read against Daniel 7",
        "gap": "wide",
    },

    # ---- the Apostolic Fathers, where the ancient testimony is explicit ----
    "the-epistle-of-polycarp-to-the-philippians": {
        "trad": "Polycarp of Smyrna, c. 110-140 CE",
        "tradWhy": "Irenaeus knew Polycarp personally as a boy and says he "
                   "wrote letters to the churches; this is the one that "
                   "survives. The letter accompanies a collection of Ignatius's "
                   "letters, which Polycarp says he is sending on, and speaks "
                   "of Ignatius as recently passed.",
        "tradSource": "Irenaeus, Against Heresies 3.3.4; Eusebius, "
                      "Ecclesiastical History 4.14; Polycarp, Philippians 13",
        "crit": "Polycarp, though perhaps two letters joined",
        "critWhy": "The authorship is not doubted. What is argued is unity: "
                   "chapter 13 treats Ignatius as newly martyred and asks for "
                   "news of him, while chapter 9 speaks of him as long since "
                   "gone to his reward, so the letter is read by some as two "
                   "notes of different dates joined in transmission.",
        "critSource": "Polycarp, Philippians 9 against 13",
        "gap": "none",
    },
    "the-martyrdom-of-polycarp": {
        "trad": "The church of Smyrna, shortly after Polycarp's death",
        "tradWhy": "The work is a circular letter from one congregation to "
                   "another, names its own scribes at the end, and says it was "
                   "written down so the account would not be lost.",
        "tradSource": "The Martyrdom of Polycarp, opening address and closing "
                      "chapters 20-22",
        "crit": "c. 155-177 CE, with the closing chapters added later",
        "critWhy": "The date of the martyrdom itself is contested within a "
                   "generation, and the appendices that trace the manuscript's "
                   "descent through several copyists are plainly later "
                   "additions to the letter they follow.",
        "critSource": "The chain of transmission described in chapters 22, "
                      "naming successive copyists",
        "gap": "none",
    },
    "fragments-of-papias": {
        "trad": "Papias of Hierapolis, c. 110-130 CE",
        "tradWhy": "Irenaeus calls him a hearer of John and a companion of "
                   "Polycarp, and Eusebius preserves the fragments while "
                   "disputing his judgement. What survives is quotation: the "
                   "five books of the Exposition of the Oracles of the Lord are "
                   "lost.",
        "tradSource": "Irenaeus, Against Heresies 5.33.4; Eusebius, "
                      "Ecclesiastical History 3.39",
        "crit": "c. 110-140 CE, surviving only as quotation",
        "critWhy": "The date is inferred from the people Papias says he "
                   "questioned -- those who had heard the apostles -- and from "
                   "Eusebius's placing of him. Nothing here is a text of "
                   "Papias: every fragment is somebody else quoting him, and "
                   "the quoters had their own arguments to make.",
        "critSource": "Eusebius, Ecclesiastical History 3.39, which is the "
                      "source of most of what survives",
        "gap": "none",
    },
    "the-epistle-of-barnabas": {
        "trad": "Barnabas the companion of Paul",
        "tradWhy": "The letter circulated under his name from early on: "
                   "Clement of Alexandria quotes it as Barnabas, and Codex "
                   "Sinaiticus binds it into the New Testament.",
        "tradSource": "Clement of Alexandria, Stromata 2.6-7; Codex Sinaiticus",
        "crit": "c. 130-132 CE, and not by Barnabas",
        "critWhy": "The letter is anonymous; the name is attached by later "
                   "readers. It speaks of the temple as destroyed and of its "
                   "being rebuilt by the enemies who pulled it down, which fits "
                   "the years before the Bar Kokhba revolt rather than the "
                   "lifetime of Paul's companion.",
        "critSource": "Barnabas 16:3-4 on the destroyed temple; the letter's "
                      "own anonymity",
        "gap": "wide",
    },
}


def coverage(work_ids: list[str]) -> tuple[int, int]:
    """How many of the given works carry a recorded pair of positions."""
    return sum(1 for w in work_ids if w in POSITIONS), len(work_ids)
