#!/usr/bin/env python3
"""Which tradition reads which canon, and where two names read the same one.

The Canons page compares five canons. A reader does not have one. They have a
church, or a synagogue, or neither, and the word they would use for it is
"Baptist" or "Pentecostal" or "Reform" -- none of which is one of the five,
and none of which found anything at all in the search box.

The obvious fix is the wrong one. Adding Baptist, Pentecostal, Methodist,
Presbyterian and the rest as filters would put forty entries in a list where
thirty-five of them return byte-identical results, because those churches
disagree about a great deal and not about which books are in the Bible. A
control that offers a distinction the data cannot make is worse than no
control: it tells the reader their tradition has its own canon, which for
most of these is false, and it is exactly the kind of false precision this
volume exists to argue against.

So this is not a filter. It is a way in by the name somebody already uses,
and it says plainly where that name lands -- including, and especially, when
it lands in the same place as a dozen others. "Baptist churches read the
sixty-six books of the Protestant canon, as do most Protestant churches" is
the true answer and also the useful one.

What each entry may say:

  canon   one of canon.json's five keys, or None where this volume does not
          model the tradition's canon as a column. None is not a gap to be
          filled in later by guessing: the Church of the East reads a New
          Testament of twenty-two books and the Samaritan Torah is a
          different recension of the text, and neither is answerable by
          pointing at one of the five.
  note    what is true of this tradition's canon that the canon key alone
          does not say. Left empty where there is nothing to add, which is
          the common case and is itself the point.
  source  where the note's claim comes from. Required whenever there is a
          note, because a sentence about what a church holds is a claim
          about somebody's religion and must be checkable.

Nothing here is a statement about what any tradition believes beyond which
books it prints in its Bible. That is the only question this volume can
answer and the only one that is asked.
"""

from __future__ import annotations

# The families the answers are grouped under. Order is the order they are
# offered in, which runs oldest canon first.
FAMILIES = ["Judaism", "Protestant Christianity", "Catholic Christianity",
            "Orthodox Christianity", "Other"]

TRADITIONS = [
    # ---- Judaism -------------------------------------------------------
    # The movements divide over authority, law and practice, and not over
    # the contents of the Tanakh, which is why they share a line here.
    {"id": "judaism", "name": "Judaism", "family": "Judaism",
     "canon": "tanakh", "also": ["jewish", "jew", "jews"],
     "note": "", "source": ""},
    {"id": "orthodox-judaism", "name": "Orthodox Judaism", "family": "Judaism",
     "canon": "tanakh", "also": ["orthodox jew", "orthodox jews", "haredi", "hasidic",
              "modern orthodox"],
     "note": "", "source": ""},
    {"id": "conservative-judaism", "name": "Conservative Judaism",
     "family": "Judaism", "canon": "tanakh", "also": ["masorti", "conservative jew",
                                 "conservative jews"],
     "note": "", "source": ""},
    {"id": "reform-judaism", "name": "Reform Judaism", "family": "Judaism",
     "canon": "tanakh", "also": ["reform jew", "reform jews", "liberal judaism",
              "progressive judaism"],
     "note": "", "source": ""},
    {"id": "reconstructionist-judaism", "name": "Reconstructionist Judaism",
     "family": "Judaism", "canon": "tanakh", "also": [], "note": "",
     "source": ""},
    {"id": "karaite", "name": "Karaite Judaism", "family": "Judaism",
     "canon": "tanakh", "also": ["karaism", "karaites"],
     "note": "The dispute with rabbinic Judaism is over the oral law and "
             "the Talmud, not over the written books, which is why it "
             "leaves no mark on this volume.",
     "source": "The dispute is over the Talmud and the oral Torah, not over "
               "the contents of the written canon."},
    {"id": "messianic-judaism", "name": "Messianic Judaism",
     "family": "Judaism", "canon": "protestant",
     "also": ["messianic jew", "messianic jews", "messianic",
              "jews for jesus", "hebrew roots"],
     "note": "The Tanakh and the New Testament together, with the first "
             "part usually kept in the Jewish order and under its Hebrew "
             "names.",
     "source": "The canon is the Protestant one; the ordering and the names "
               "used for its divisions are not."},
    {"id": "samaritan", "name": "Samaritanism", "family": "Judaism",
     "canon": None, "also": ["samaritans", "samaritan pentateuch"],
     "note": "Holds the Torah alone, in the Samaritan recension — a text "
             "that differs from the Masoretic Torah in some six thousand "
             "places. This volume prints the Masoretic text, so it cannot "
             "show you a Samaritan Bible, and pointing you at the Torah "
             "here would be showing you a different book under their name.",
     "source": "The Samaritan Pentateuch is a distinct textual recension, "
               "not a subset of the text printed here."},

    # ---- Protestant Christianity ---------------------------------------
    # Thirty-odd names, one canon. Saying so is the whole job of this block.
    {"id": "protestant", "name": "Protestant Christianity",
     "family": "Protestant Christianity", "canon": "protestant",
     "also": ["protestants", "protestant"], "note": "", "source": ""},
    {"id": "baptist", "name": "Baptist churches",
     "family": "Protestant Christianity", "canon": "protestant",
     "also": ["baptists", "southern baptist", "southern baptists",
              "american baptist", "reformed baptist"],
     "note": "", "source": ""},
    {"id": "pentecostal", "name": "Pentecostal churches",
     "family": "Protestant Christianity", "canon": "protestant",
     "also": ["pentecostals", "pentecostalism", "assemblies of god",
              "church of god", "foursquare", "charismatic"],
     "note": "", "source": ""},
    {"id": "methodist", "name": "Methodist churches",
     "family": "Protestant Christianity", "canon": "protestant",
     "also": ["methodists", "wesleyan", "united methodist", "nazarene",
              "church of the nazarene"],
     "note": "", "source": ""},
    {"id": "presbyterian", "name": "Presbyterian and Reformed churches",
     "family": "Protestant Christianity", "canon": "protestant",
     "also": ["presbyterians", "reformed", "calvinist", "calvinism",
              "congregational", "united church of christ"],
     "note": "The Westminster Confession names the sixty-six and says the "
             "apocrypha are “of no authority in the Church of God” "
             "and not to be approved or made use of otherwise than other "
             "human writings — the firmest of the Protestant statements on "
             "the question.",
     "source": "Westminster Confession of Faith (1646), I.3."},
    {"id": "evangelical", "name": "Evangelical and non-denominational churches",
     "family": "Protestant Christianity", "canon": "protestant",
     "also": ["evangelical", "evangelicals", "non denominational",
              "nondenominational", "bible church", "born again"],
     "note": "", "source": ""},
    {"id": "adventist", "name": "Seventh-day Adventist Church",
     "family": "Protestant Christianity", "canon": "protestant",
     "also": ["adventist", "adventists", "seventh day adventist", "sda"],
     "note": "", "source": ""},
    {"id": "anabaptist", "name": "Anabaptist churches",
     "family": "Protestant Christianity", "canon": "protestant",
     "also": ["mennonite", "mennonites", "amish", "hutterite", "brethren"],
     "note": "", "source": ""},
    {"id": "quaker", "name": "Quakers (Religious Society of Friends)",
     "family": "Protestant Christianity", "canon": "protestant",
     "also": ["quaker", "quakers", "friends", "society of friends"],
     "note": "", "source": ""},
    {"id": "salvation-army", "name": "The Salvation Army",
     "family": "Protestant Christianity", "canon": "protestant",
     "also": ["salvationist"], "note": "", "source": ""},
    {"id": "restorationist", "name": "Churches of Christ and Disciples",
     "family": "Protestant Christianity", "canon": "protestant",
     "also": ["church of christ", "churches of christ", "disciples of christ",
              "restorationist", "stone campbell"],
     "note": "", "source": ""},

    # The two Protestant traditions whose Bibles are not simply the
    # sixty-six. Both print the deuterocanon and both deny it doctrinal
    # authority, which is a third category the five-column table has no
    # room for -- so the note carries it and the scope does not pretend to.
    {"id": "anglican", "name": "Anglican and Episcopal churches",
     "family": "Protestant Christianity", "canon": "protestant",
     "also": ["anglican", "anglicanism", "episcopal", "episcopalian",
              "church of england"],
     "note": "Anglican Bibles also print the apocrypha, which the Church "
             "“doth read for example of life and instruction of "
             "manners; but yet doth it not apply them to establish any "
             "doctrine” — read, and not doctrinal. That third category "
             "has no column here: this scope gives the sixty-six, and the "
             "Catholic one gives the books printed beside them.",
     "source": "Articles of Religion (1571), Article VI."},
    {"id": "lutheran", "name": "Lutheran churches",
     "family": "Protestant Christianity", "canon": "protestant",
     "also": ["lutheran", "lutherans", "lutheranism", "elca", "missouri synod"],
     "note": "Luther printed the apocrypha between the Testaments under a "
             "heading calling them “not held equal to the Scriptures, "
             "but useful and good to read” — the same third category the "
             "Anglican article names, and the reason Lutheran Bibles have "
             "varied in whether they print them at all.",
     "source": "Luther's German Bible (1534), the heading to the Apocrypha."},

    # ---- Catholic Christianity -----------------------------------------
    {"id": "catholic", "name": "The Catholic Church",
     "family": "Catholic Christianity", "canon": "catholic",
     "also": ["catholic", "catholics", "roman catholic", "catholicism"],
     "note": "", "source": ""},
    {"id": "eastern-catholic", "name": "Eastern Catholic churches",
     "family": "Catholic Christianity", "canon": "catholic",
     "also": ["eastern catholic", "maronite", "melkite", "byzantine catholic",
              "ukrainian catholic", "chaldean catholic"],
     "note": "In communion with Rome while keeping an Eastern liturgy — the "
             "difference from the Latin Church is of rite, not of which "
             "books.",
     "source": "The canon is that fixed at Trent, shared with the Latin "
               "Church."},
    {"id": "old-catholic", "name": "Old Catholic churches",
     "family": "Catholic Christianity", "canon": "catholic",
     "also": ["old catholic", "utrecht"], "note": "", "source": ""},

    # ---- Orthodox Christianity -----------------------------------------
    {"id": "eastern-orthodox", "name": "The Eastern Orthodox Church",
     "family": "Orthodox Christianity", "canon": "orthodox",
     "also": ["orthodox", "eastern orthodox", "greek orthodox",
              "russian orthodox", "serbian orthodox", "romanian orthodox",
              "bulgarian orthodox", "antiochian orthodox", "oca",
              "orthodox church"],
     "note": "", "source": ""},
    {"id": "ethiopian-orthodox",
     "name": "The Ethiopian and Eritrean Orthodox Tewahedo Churches",
     "family": "Orthodox Christianity", "canon": "ethiopian",
     "also": ["ethiopian orthodox", "ethiopian", "eritrean orthodox",
              "tewahedo", "ethiopia"],
     "note": "The widest canon there is, and the only one that receives "
             "1 Enoch and Jubilees as scripture — which is much of why this "
             "volume prints them.",
     "source": "canon.json records the Ethiopian column; the coverage note "
               "on the Canons page states the enumeration."},
    {"id": "coptic-orthodox", "name": "The Coptic Orthodox Church",
     "family": "Orthodox Christianity", "canon": "orthodox", "approx": True,
     "also": ["coptic", "copt", "copts", "coptic orthodox"],
     "note": "Oriental Orthodox rather than Eastern. The two canons are "
             "close and are not identical, and this volume does not draw "
             "the difference — so the scope below is an approximation, "
             "offered as one rather than as this church's own list.",
     "source": "This volume compares five canons; the Coptic canon is not "
               "one of its columns."},
    {"id": "armenian-orthodox", "name": "The Armenian Apostolic Church",
     "family": "Orthodox Christianity", "canon": "orthodox", "approx": True,
     "also": ["armenian", "armenian apostolic", "armenian orthodox"],
     "note": "Oriental Orthodox rather than Eastern, with a canon close "
             "to that column and not identical to it — so the scope below "
             "is an approximation. Some Armenian Bibles have also carried "
             "a third letter to the Corinthians, which this volume does "
             "not print.",
     "source": "This volume compares five canons; the Armenian canon is not "
               "one of its columns."},
    {"id": "church-of-the-east", "name": "The Assyrian Church of the East",
     "family": "Orthodox Christianity", "canon": None,
     "also": ["assyrian church", "church of the east", "nestorian",
              "peshitta", "syriac"],
     "note": "Reads the Peshitta, whose New Testament has twenty-two books: "
             "2 Peter, 2 John, 3 John, Jude and Revelation are not in it. "
             "All five are printed in this volume, so none of the five "
             "columns can stand in for this canon — a scope built from any "
             "of them would hand you books this church does not receive.",
     "source": "The Peshitta New Testament omits the four shorter Catholic "
               "epistles and the Apocalypse."},

    # ---- Other ----------------------------------------------------------
    {"id": "rastafari", "name": "Rastafari", "family": "Other",
     "canon": "ethiopian", "also": ["rasta", "rastafarian", "rastafarianism"],
     "note": "Holds the Ethiopic Enoch and the Kebra Nagast in particular "
             "regard. This volume prints Enoch; it does not print the "
             "Kebra Nagast.",
     "source": "The scriptural canon is the Ethiopian Orthodox one."},
    {"id": "latter-day-saints",
     "name": "The Church of Jesus Christ of Latter-day Saints",
     "family": "Other", "canon": "protestant",
     "also": ["mormon", "mormons", "lds", "latter day saints"],
     "note": "Holds the sixty-six as one part of a larger scripture that "
             "also includes the Book of Mormon, the Doctrine and Covenants "
             "and the Pearl of Great Price. Those three are nineteenth-"
             "century texts and are not in this volume, which stops in the "
             "second century.",
     "source": "The biblical canon is the Protestant sixty-six, in the King "
               "James translation."},
    {"id": "jehovahs-witnesses", "name": "Jehovah's Witnesses",
     "family": "Other", "canon": "protestant",
     "also": ["jehovahs witness", "jehovah witness", "watchtower"],
     "note": "Holds the same sixty-six books, in its own translation.",
     "source": "The canon is the Protestant sixty-six; the New World "
               "Translation is a translation, not a different canon."},
    {"id": "islam", "name": "Islam", "family": "Other", "canon": None,
     "also": ["muslim", "muslims", "islamic", "quran", "koran"],
     "note": "Honours the Tawrat, Zabur and Injil given to Moses, David and "
             "Jesus, and holds that the texts in circulation are not those "
             "revelations intact. Its own scripture is the Qur'an, which is "
             "not in this volume: this is a library of Jewish and Christian "
             "scripture and does not pretend to be more.",
     "source": "The Qur'an is not among the texts this volume carries."},
]
