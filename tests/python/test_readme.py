#!/usr/bin/env python3
"""The counts the README states, against the data it is describing.

The audit is a gate and docs/data cannot drift from source/, so the numbers
in the built files are checked. The sentences *about* those numbers are not,
and that is a real gap rather than a pedantic one: the six parse defects
repaired in "Make the audit a real gate" grew the library by three chapters
and fifty-four verses, and the front page of this repository went on
advertising the old figures. The data was right, the gate was working, and
the first line a reader saw was wrong.

A number in prose is an editorial claim, and this volume's argument is that
editorial claims carry citations. These are the citations.

The map's own README claim -- 1,209 of 1,232 places inside the frame -- is
checked in test_basemap.py instead, where the frame constant it depends on
lives.

The share card in docs/index.html is here too. It is prose about the counts
in exactly the way the README headline is, it is read by more people than
either -- it is what a link to this site looks like when somebody posts it --
and it was the one that rotted: it went on advertising 166 works, 2,269
chapters and 1.16 million words for as long as the headline beside it was
being kept right by the tests below.
"""

import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def readme():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        return fh.read()


def totals():
    with open(os.path.join(ROOT, "docs", "data", "manifest.json"),
              encoding="utf-8") as fh:
        return json.load(fh)["totals"]


class TheHeadline(unittest.TestCase):
    """The one line every reader sees before anything else."""

    def setUp(self):
        self.claim = re.search(
            r"\*\*([\d,]+) works · ([\d,]+) chapters · ([\d,]+) numbered "
            r"verses · ([\d.]+) million words\*\*", readme())
        self.assertIsNotNone(
            self.claim,
            "the headline this test exists to check is no longer in README.md "
            "in the form it can read; rewrite the test or restore the line")
        self.totals = totals()

    def test_the_number_of_works(self):
        self.assertEqual(self.claim.group(1), f"{self.totals['works']:,}")

    def test_the_number_of_chapters(self):
        """+3 when three folded Ignatius chapters were unfolded."""
        self.assertEqual(self.claim.group(2), f"{self.totals['chapters']:,}")

    def test_the_number_of_verses(self):
        """+54 when the dropped chapter-opening verses came back."""
        self.assertEqual(self.claim.group(3), f"{self.totals['verses']:,}")

    def test_the_number_of_words(self):
        """Stated to two decimal places, so it is checked to two.

        This is the one figure in the line that is rounded, and rounding is
        the reason it survived the last corpus change while its neighbours
        did not -- 1,128,001 and 1,130,336 are both "1.13 million". Checking
        it to the precision it is written at is the most the sentence can be
        held to.
        """
        stated = float(self.claim.group(4))
        self.assertEqual(stated, round(self.totals["words"] / 1_000_000, 2))


class TheThreadCount(unittest.TestCase):
    """The README says how many threads there are, so it is checked.

    A count in prose beside a file that is regenerated on every build is the
    same kind of claim as the headline, and rots the same way.
    """

    def test_the_readme_states_the_number_of_threads(self):
        stated = re.search(r"\*\*([\d,]+) threads\*\*", readme())
        self.assertIsNotNone(
            stated, "README.md no longer states how many threads there are")
        with open(os.path.join(ROOT, "docs", "data", "threads.json"),
                  encoding="utf-8") as fh:
            threads = json.load(fh)
        self.assertEqual(stated.group(1), f"{len(threads):,}")

    def test_every_thread_has_stops_with_text(self):
        """A thread with an empty stop would still build; it would say nothing."""
        with open(os.path.join(ROOT, "docs", "data", "threads.json"),
                  encoding="utf-8") as fh:
            threads = json.load(fh)
        for thread in threads:
            self.assertGreaterEqual(len(thread["stops"]), 4, thread["id"])
            for stop in thread["stops"]:
                self.assertTrue(stop["verses"], f"{thread['id']}: empty stop")
                self.assertTrue(stop["why"].strip(),
                                f"{thread['id']}: a stop with no reason")
                for verse in stop["verses"]:
                    self.assertTrue(verse["t"].strip(),
                                    f"{thread['id']}: a verse with no text")


class TheLinks(unittest.TestCase):
    """A link with nothing behind it.

    "How the dating was decided" pointed at (#) for as long as the page it
    names has existed. It is the one link in the file a sceptical reader is
    most likely to follow -- the arrangement is the claim, and that page is
    where the claim is defended -- and it went nowhere.
    """

    LINK = re.compile(r"\[(?P<text>[^\]]+)\]\((?P<href>[^)]*)\)")

    def test_no_link_points_at_nothing(self):
        dead = [m.group("text") for m in self.LINK.finditer(readme())
                if m.group("href").strip() in ("", "#")]
        self.assertEqual(dead, [],
                         "links in README.md with no destination: " +
                         ", ".join(dead))

    def test_every_repository_path_a_link_names_exists(self):
        missing = []
        for m in self.LINK.finditer(readme()):
            href = m.group("href").split("#")[0].strip()
            if not href or "://" in href or href.startswith("mailto:"):
                continue
            if not os.path.exists(os.path.join(ROOT, href)):
                missing.append(href)
        self.assertEqual(missing, [],
                         "links in README.md to paths that are not here: " +
                         ", ".join(missing))


class TheShareCard(unittest.TestCase):
    """What a link to this site says before anyone has opened it."""

    def setUp(self):
        with open(os.path.join(ROOT, "docs", "index.html"), encoding="utf-8") as fh:
            page = fh.read()
        card = re.search(r'<meta property="og:description" content="([^"]+)"', page)
        self.assertIsNotNone(card, "docs/index.html has no og:description")
        self.claim = re.match(
            r"([\d,]+) works, ([\d,]+) chapters, ([\d.]+) million words",
            card.group(1))
        self.assertIsNotNone(
            self.claim,
            "the og:description no longer opens with the counts this test "
            "reads; rewrite the test or restore the form")
        self.totals = totals()

    def test_the_number_of_works(self):
        self.assertEqual(self.claim.group(1), f"{self.totals['works']:,}")

    def test_the_number_of_chapters(self):
        self.assertEqual(self.claim.group(2), f"{self.totals['chapters']:,}")

    def test_the_number_of_words(self):
        """Rounded to two places, and held to the precision it is written at."""
        self.assertEqual(float(self.claim.group(3)),
                         round(self.totals["words"] / 1_000_000, 2))


class WhatCountsAsAWork(unittest.TestCase):
    """The headline counts 172. Nine of them are not texts.

    Checking that the count matches manifest.totals.works proves the arithmetic
    and nothing else -- the number was never the doubtful part, the noun
    was. Two of the entries are editorial asides, four are notes on
    manuscript discoveries, and three are placeholders for material the
    volume cannot print. A reader entitled to the count is entitled to
    know what is in it.
    """

    def setUp(self):
        with open(os.path.join(ROOT, "docs", "data", "manifest.json"),
                  encoding="utf-8") as fh:
            self.manifest = json.load(fh)
        self.works = [w for s in self.manifest["sections"] for w in s["works"]]

    def test_the_split_between_text_and_apparatus(self):
        texts = [w for w in self.works if w.get("words")]
        self.assertEqual(len(self.works), 172)
        self.assertEqual(len(texts), 163)
        self.assertEqual(len(self.works) - len(texts), 9)

    def test_the_readme_says_how_many_carry_text(self):
        stated = re.search(r"Of the ([\d,]+) entries, \*\*([\d,]+) carry text\*\*",
                           readme())
        self.assertIsNotNone(
            stated, "README.md no longer states how many entries carry text")
        texts = sum(1 for w in self.works if w.get("words"))
        self.assertEqual(stated.group(1), f"{len(self.works):,}")
        self.assertEqual(stated.group(2), f"{texts:,}")

    def test_the_entries_without_text_are_the_ones_on_record(self):
        """Frozen, so a work cannot lose its text without saying so.

        A parse that silently emptied a book would otherwise just move it
        into the apparatus column and keep the totals looking reasonable.
        """
        self.assertEqual(
            sorted(w["id"] for w in self.works if not w.get("words")),
            ["also-often-dated-this-early",
             "ketef-hinnom-silver-scrolls-found-1979",
             "on-the-placement-of-the-torah",
             "philo-of-alexandria",
             "the-dead-sea-scrolls-as-biblical-manuscripts-found-1947-1956",
             "the-great-christian-codices",
             "the-major-dead-sea-scrolls-summaries",
             "the-nash-papyrus-acquired-1898-1903",
             "the-psalms-of-solomon"])


class WhatTheFrontMatterClaimsIsMissing(unittest.TestCase):
    """The volume's own list of what it does not contain.

    It said the Shepherd of Hermas Similitudes 1 and 10 were not captured
    by the parser. They were supplied from the 1870 Ante-Nicene Christian
    Library in "Close three Apostolic Fathers gaps from a second edition",
    and the sentence describing their absence outlived the absence by
    several commits -- the same way the headline counts outlived the parse
    repair that changed them.
    """

    def not_present(self):
        with open(os.path.join(ROOT, "docs", "data", "manifest.json"),
                  encoding="utf-8") as fh:
            intro = json.load(fh)["sections"][0]["intro"]
        note = [p for p in intro if p.startswith("NOT PRESENT")]
        self.assertEqual(len(note), 1, "no NOT PRESENT note in the front matter")
        return note[0]

    def test_it_does_not_claim_absent_text_the_volume_now_prints(self):
        note = self.not_present()
        self.assertNotIn("Similitudes 1 and 10", note)

    def test_and_the_similitudes_it_used_to_disclaim_really_are_there(self):
        for n, least in (("similitude-1", 400), ("similitude-10", 2500)):
            with open(os.path.join(ROOT, "docs", "data", "works", n + ".json"),
                      encoding="utf-8") as fh:
                work = json.load(fh)
            words = sum(len(" ".join(c.get("paras", [])).split())
                        for c in work["chapters"])
            self.assertGreater(words, least, f"{n} is empty again")

    def test_it_still_names_what_is_genuinely_absent(self):
        note = self.not_present()
        for missing in ("Dead Sea Scrolls", "Psalms of Solomon", "Philo",
                        "1 Clement", "Smyrnaeans"):
            self.assertIn(missing, note)


class TheAbsentBooks(unittest.TestCase):
    """Four books of the Ethiopian canon are missing, and each says why.

    Not the four anyone expected. Five books were listed as missing and
    all five are now here in whole or in part -- the Didascalia from
    Platt's 1834 printing, the Sinodos from Horner's of 1904 and
    Schodde's of 1885, the Book of the Covenant from Cooper and Maclean's
    Syriac and James's Ethiopic, the Rest of the Words of Baruch from
    Issaverdens's Armenian, and the one piece of Ethiopic Clement James
    translated. The four now absent are the ones the table never listed:
    three Meqabyan and Josippon.

    The coverage table used to name the absences and stop, which is a gap
    asserted without a citation -- the one move this volume says it does
    not make. A reason that cannot be checked is no better than no reason,
    so each carries a source too, and build_canon.py refuses to build
    without one.

    The same rule now runs the other way. Three of the four recovered
    books are here in part or in another version, and a table that says
    "read" over half a book is making the same unsourced claim in the
    opposite direction, so each of those carries its own reason and
    source as well.
    """

    RECOVERED = ("4 Baruch (Paraleipomena Jeremiou)",
                 "Book of the Covenant (Mets'hafe Kidan)",
                 "Ethiopic Clement (Qalementos)",
                 "Sinodos")

    def setUp(self):
        with open(os.path.join(ROOT, "docs", "data", "canon.json"),
                  encoding="utf-8") as fh:
            self.canon = json.load(fh)
        self.absent = [b for b in self.canon["books"] if not b["present"]]

    def test_the_absent_books_are_the_ones_on_record(self):
        self.assertEqual(
            sorted(b["name"] for b in self.absent),
            ["1 Meqabyan", "2 Meqabyan", "3 Meqabyan",
             "Josippon (Zena Ayhud)"])

    def test_every_absence_carries_a_reason_and_a_source(self):
        for b in self.absent:
            self.assertTrue(b.get("absentWhy", "").strip(),
                            f"{b['name']} is absent with no reason")
            self.assertTrue(b.get("absentSource", "").strip(),
                            f"{b['name']} gives no source for its reason")

    def test_the_recovered_books_really_carry_text(self):
        by_name = {b["name"]: b for b in self.canon["books"]}
        for name in self.RECOVERED:
            book = by_name[name]
            self.assertTrue(book["present"], f"{name} lost its text")
            for work in book["works"]:
                path = os.path.join(ROOT, "docs", "data", "works",
                                    work + ".json")
                with open(path, encoding="utf-8") as fh:
                    got = json.load(fh)
                words = sum(len(" ".join(c.get("paras", [])).split())
                            for c in got["chapters"])
                self.assertGreater(words, 3000, f"{work} is nearly empty")
                self.assertFalse(got["verified"],
                                 f"{work} is not audited and must not say it is")

    def test_a_book_here_in_part_says_which_part(self):
        by_name = {b["name"]: b for b in self.canon["books"]}
        for name in self.RECOVERED:
            book = by_name[name]
            self.assertTrue(book.get("partialWhy", "").strip(),
                            f"{name} is here in part and does not say so")
            self.assertTrue(book.get("partialSource", "").strip(),
                            f"{name} gives no source for what is here")


class TheGazetteer(unittest.TestCase):

    def test_the_number_of_curated_references(self):
        """"7,394 references" -- the count the map's honesty rests on.

        The point of the sentence is that the pins come from a list somebody
        checked rather than from a pattern run over the text, so the size of
        that list is load-bearing. It is read from the source column rather
        than from anything built, because the source is what the claim is
        about.
        """
        import sys
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import build_places

        rows = build_places.read_rows(
            os.path.join(ROOT, "source", "places", "merged.txt"))
        counted = sum(
            len([v for v in (r.get("Verses") or "").split(",") if v.strip()])
            for r in rows)

        stated = re.search(r"([\d,]+) references", readme())
        self.assertIsNotNone(
            stated, "the reference count is no longer stated in README.md")
        self.assertEqual(stated.group(1), f"{counted:,}")


class TheSizesInMegabytes(unittest.TestCase):
    """The figures nothing rebuilds the sentence for.

    A count of works moves when the parse moves, and somebody notices. A size
    in megabytes moves every time a word is added to the library and nobody
    does: the search index was advertised at 1.45 MB for as long as it took to
    grow to 1.64, and that sentence is the one a reader on a phone uses to
    decide whether to open the thing at all.

    Measured the way tools/build_standalone.py measures, because that is the
    figure the build prints and the one the README was written from: bytes,
    over 1024, over 1024.
    """

    @staticmethod
    def mib(path):
        if os.path.isdir(path):
            total = 0
            for folder, _dirs, files in os.walk(path):
                total += sum(os.path.getsize(os.path.join(folder, f))
                             for f in files)
        else:
            total = os.path.getsize(path)
        return total / 1024 / 1024

    def test_the_search_index_is_the_size_the_readme_says(self):
        claim = re.search(
            r"inverted index \(([\d.]+) MB\s+across ([\d,]+) shards\)",
            readme())
        self.assertIsNotNone(
            claim,
            "the search index's size and shard count are no longer stated in "
            "README.md in the form this test can read")

        index = os.path.join(ROOT, "docs", "data", "index")
        self.assertEqual(float(claim.group(1)), round(self.mib(index), 2))

        shards = [f for f in os.listdir(index) if f.endswith(".json")]
        self.assertEqual(claim.group(2), f"{len(shards):,}")

    def test_the_offline_copy_refuses_at_the_size_the_readme_says(self):
        """The sentence claims a gate. This is whether there is one.

        build_standalone.py prints the word WARNING and then returns 1, and
        build.sh runs under set -e, so it really is a refusal rather than a
        note -- but the two halves of that are in different files, and a
        later hand tidying the wording of a warning into a warning is all it
        would take to turn the README's claim into a false one.
        """
        claim = re.search(r"refuses to finish above (\d+) MB", readme())
        self.assertIsNotNone(
            claim, "the offline copy's size ceiling is no longer stated in "
                   "README.md")

        with open(os.path.join(ROOT, "tools", "build_standalone.py"),
                  encoding="utf-8") as fh:
            source = fh.read()

        gate = re.search(r"if mb > (\d+):\n(.*\n)*?\s+return 1\n", source)
        self.assertIsNotNone(
            gate,
            "build_standalone.py no longer refuses above a size, so the "
            "README's claim that it does is now false")
        self.assertEqual(claim.group(1), gate.group(1))


if __name__ == "__main__":
    unittest.main()
