#!/usr/bin/env python3
"""Resolving the gazetteer's references against this volume's own text.

The whole reason this file exists rather than a regex over the chapter text is
that "Dan" is a man, a tribe and a city. The tests that matter here are the
ones that check nothing is guessed: a reference either lands on a verse this
volume actually contains, or it is dropped.
"""

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_mentions as bmen  # noqa: E402

DATA = os.path.join(ROOT, "docs", "data")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


class ParsingReferences(unittest.TestCase):

    def test_an_ordinary_reference(self):
        self.assertEqual(bmen.parse_ref("2 Kgs 5:12"), ("2 Kgs", 5, 12))

    def test_leading_space_is_tolerated(self):
        self.assertEqual(bmen.parse_ref("  Num 33:47"), ("Num", 33, 47))

    def test_a_one_word_book(self):
        self.assertEqual(bmen.parse_ref("Josh 21:30"), ("Josh", 21, 30))

    def test_a_trailing_full_stop_is_not_part_of_the_name(self):
        self.assertEqual(bmen.parse_ref("Rev. 12:6")[0], "Rev")

    def test_something_that_is_not_a_reference(self):
        self.assertIsNone(bmen.parse_ref("Now Barada River"))

    def test_a_book_with_no_verse(self):
        self.assertIsNone(bmen.parse_ref("Obad 1"))


class TheBookMapping(unittest.TestCase):

    def test_every_abbreviation_in_the_source_has_a_mapping(self):
        """The check that would have caught a silently dropped book."""
        import csv
        import re
        path = os.path.join(ROOT, "source", "places", "merged.txt")
        with open(path, encoding="utf-8", errors="replace") as fh:
            rows = [ln for ln in fh
                    if not ln.startswith("#") or ln.startswith("#ESV")]
        seen = set()
        for row in csv.DictReader(rows, delimiter="\t"):
            for raw in (row.get("Verses") or "").split(","):
                ref = bmen.parse_ref(raw)
                if ref:
                    seen.add(ref[0])
        missing = sorted(seen - set(bmen.BOOKS))
        self.assertEqual(missing, [], f"no mapping for {missing}")

    def test_every_mapped_work_exists_in_the_volume(self):
        manifest = load("manifest.json")
        have = {w["id"] for s in manifest["sections"] for w in s["works"]}
        for abbrev, ids in bmen.BOOKS.items():
            for wid in ids:
                self.assertIn(wid, have, f"{abbrev} points at missing {wid}")

    def test_a_split_book_lists_all_of_its_parts(self):
        self.assertEqual(len(bmen.BOOKS["Isa"]), 3)
        self.assertEqual(len(bmen.BOOKS["Zech"]), 2)


class Resolving(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        manifest = load("manifest.json")
        cls.works = {}
        for section in manifest["sections"]:
            for w in section["works"]:
                path = os.path.join(DATA, "works", w["id"] + ".json")
                if os.path.exists(path):
                    cls.works[w["id"]] = load(os.path.join("works", w["id"] + ".json"))

    def test_an_ordinary_book_resolves_to_a_zero_based_index(self):
        self.assertEqual(bmen.resolve("Amos", 3, 1, self.works), ("amos", 2))

    def test_a_split_book_lands_in_the_right_part(self):
        """Second Isaiah opens at chapter 40, so Isa 40 is its index 0.

        Getting this wrong by arithmetic rather than lookup would put every
        reference in Isaiah 40-55 thirty-nine chapters too far along, or in
        First Isaiah entirely.
        """
        self.assertEqual(bmen.resolve("Isa", 40, 3, self.works),
                         ("isaiah-40-55-second-isaiah", 0))

    def test_the_first_part_of_a_split_book_still_works(self):
        self.assertEqual(bmen.resolve("Isa", 6, 1, self.works),
                         ("isaiah-1-39-first-isaiah", 5))

    def test_the_other_split_book(self):
        self.assertEqual(bmen.resolve("Zech", 9, 9, self.works),
                         ("zechariah-9-14", 0))

    def test_a_verse_the_volume_does_not_have_is_refused(self):
        self.assertIsNone(bmen.resolve("Amos", 3, 999, self.works))

    def test_a_chapter_the_volume_does_not_have_is_refused(self):
        self.assertIsNone(bmen.resolve("Amos", 99, 1, self.works))

    def test_an_unmapped_book_is_refused_rather_than_guessed(self):
        self.assertIsNone(bmen.resolve("Enoch", 1, 1, self.works))


class TheBuiltIndex(unittest.TestCase):
    """What actually ships, checked against the gazetteer it draws from."""

    @classmethod
    def setUpClass(cls):
        cls.mentions = load("mentions.json")
        cls.places = {}
        base = os.path.join(DATA, "places")
        for fn in sorted(os.listdir(base)):
            cls.places.update(load(os.path.join("places", fn)))
        cls.manifest = load("manifest.json")

    def test_every_place_named_has_a_record_to_draw(self):
        """A key with no record is a pin the map cannot draw and a name the
        panel cannot open."""
        used = set()
        for keys in self.mentions.values():
            used.update(keys)
        orphans = sorted(used - set(self.places))
        self.assertEqual(orphans, [], f"{len(orphans)} orphan keys")

    def test_every_chapter_key_points_at_a_real_chapter(self):
        works = {}
        for section in self.manifest["sections"]:
            for w in section["works"]:
                works[w["id"]] = w["chapters"]
        for key in self.mentions:
            wid, _, idx = key.rpartition("/")
            self.assertIn(wid, works, key)
            self.assertLess(int(idx), works[wid], key)

    def test_no_chapter_is_listed_with_nothing_in_it(self):
        empty = [k for k, v in self.mentions.items() if not v]
        self.assertEqual(empty, [])

    def test_the_places_in_a_chapter_are_unique_and_sorted(self):
        for key, keys in self.mentions.items():
            self.assertEqual(keys, sorted(set(keys)), key)

    def test_a_chapter_everyone_knows_names_the_places_it_names(self):
        # Amos 3 (index 2) opens against Samaria and names Ashdod and Egypt.
        got = set(self.mentions.get("amos/2", []))
        for want in ("samaria", "ashdod", "egypt"):
            self.assertIn(want, got, f"Amos 3 should name {want}")

    def test_the_voyage_to_rome_reaches_places_outside_the_levant(self):
        """Acts 27 is the case the world frame exists for; if it stopped
        naming western places the frame would silently stop switching."""
        got = set(self.mentions.get("acts/26", []))
        self.assertTrue(got & {"crete", "sidon", "cyprus", "syrtis"}, sorted(got))


class DisputedIdentifications(unittest.TestCase):
    """A contested identification must not be drawn as a settled dot."""

    @classmethod
    def setUpClass(cls):
        cls.places = {}
        base = os.path.join(DATA, "places")
        for fn in sorted(os.listdir(base)):
            cls.places.update(load(os.path.join("places", fn)))

    def test_every_disputed_entry_still_matches_a_place(self):
        import build_places
        missing = sorted(set(build_places.DISPUTED) - set(self.places))
        self.assertEqual(missing, [], f"demotion no longer matches: {missing}")

    def test_none_of_them_is_drawn_as_an_identified_point(self):
        import build_places
        for key in build_places.DISPUTED:
            self.assertEqual(self.places[key]["kind"], "approximate", key)

    def test_each_says_what_is_disputed_about_it(self):
        import build_places
        for key in build_places.DISPUTED:
            note = self.places[key].get("note", "")
            self.assertTrue(len(note) > 40, key)

    def test_tarshish_does_not_assert_spain(self):
        note = self.places["tarshish"]["note"]
        self.assertIn("Tarsus", note)
        self.assertIn("disputed", note.lower())


if __name__ == "__main__":
    unittest.main()
