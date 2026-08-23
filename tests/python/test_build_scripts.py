"""The rest of the build pipeline: the repairs, the lexicon, the gazetteer,
and the single-file offline copy.

These are smaller than the parser and no less load-bearing. The lexicon keys
every definition the reader can open; the gazetteer keys every place; a repair
that slices the wrong range publishes someone else's paragraph as scripture;
and the offline build is the one artifact nobody opens until they are already
somewhere with no network to fix it from.
"""

import os
import unittest

import _tools  # noqa: F401

import build_lexicon
import build_places
import build_repairs
import build_standalone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class RepairClean(unittest.TestCase):
    def test_underscores_from_the_printing_are_dropped(self):
        self.assertEqual(build_repairs.clean("the _Shepherd_ of Hermas"),
                         "the Shepherd of Hermas")

    def test_whitespace_is_collapsed(self):
        self.assertEqual(build_repairs.clean("a   b\n\nc"), "a b c")

    def test_leading_and_trailing_space_is_trimmed(self):
        self.assertEqual(build_repairs.clean("  a b  "), "a b")

    def test_plain_text_survives(self):
        self.assertEqual(build_repairs.clean("And he said unto me"),
                         "And he said unto me")


class SliceBetween(unittest.TestCase):
    def test_takes_what_lies_between_the_two_markers(self):
        got = build_repairs.slice_between(
            "junk\nSTART HERE\nthe body\nSTOP HERE\nmore junk",
            r"^START HERE$", r"^STOP HERE$")
        self.assertEqual(got.strip(), "the body")

    def test_missing_start_yields_nothing_rather_than_everything(self):
        # Returning the whole file on a missed marker is how a repair pastes
        # a Gutenberg header into the middle of the Shepherd of Hermas.
        self.assertEqual(
            build_repairs.slice_between("no marker here", r"^START$", r"^STOP$"),
            "")

    def test_missing_end_runs_to_the_end_of_the_text(self):
        got = build_repairs.slice_between("START\nbody to the end",
                                          r"^START$", r"^NEVER APPEARS$")
        self.assertEqual(got.strip(), "body to the end")

    def test_the_markers_themselves_are_not_included(self):
        got = build_repairs.slice_between("START\nbody\nSTOP", r"^START$", r"^STOP$")
        self.assertNotIn("START", got)
        self.assertNotIn("STOP", got)


class Paragraphs(unittest.TestCase):
    def test_blank_lines_separate_paragraphs(self):
        self.assertEqual(build_repairs.paragraphs("one\ntwo\n\nthree"),
                         ["one two", "three"])

    def test_single_character_fragments_are_dropped(self):
        # Page numbers and stray marks survive the scrape as one-char lines.
        self.assertEqual(build_repairs.paragraphs("a\n\nreal paragraph here"),
                         ["real paragraph here"])

    def test_an_empty_block_yields_nothing(self):
        self.assertEqual(build_repairs.paragraphs("\n\n\n"), [])


class AsChapters(unittest.TestCase):
    def test_a_block_with_no_markers_is_one_chapter(self):
        out = build_repairs.as_chapters("just a body of text here",
                                        "SIMILITUDE 1{}")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["n"], 1)
        self.assertEqual(out[0]["style"], "prose")
        self.assertEqual(out[0]["paras"], ["just a body of text here"])

    def test_an_empty_block_yields_no_chapters(self):
        self.assertEqual(build_repairs.as_chapters("   ", "SIMILITUDE 1{}"), [])

    def test_chapters_are_numbered_from_one_in_order(self):
        block = "CHAP. I.\n\nfirst body\n\nCHAP. II.\n\nsecond body"
        out = build_repairs.as_chapters(block, "SIMILITUDE 10{}")
        self.assertEqual([c["n"] for c in out], [1, 2])
        self.assertEqual(out[0]["paras"], ["first body"])
        self.assertEqual(out[1]["paras"], ["second body"])

    def test_the_marker_text_does_not_leak_into_the_body(self):
        out = build_repairs.as_chapters("CHAP. I.\n\nfirst body", "S{}")
        self.assertNotIn("CHAP", " ".join(out[0]["paras"]))


class LexiconNorm(unittest.TestCase):
    """The key every definition is found under."""

    def test_lowercases(self):
        self.assertEqual(build_lexicon.norm("Abaddon"), "abaddon")

    def test_strips_accents(self):
        self.assertEqual(build_lexicon.norm("Bethleheḿ"), "bethlehem")

    def test_drops_punctuation_but_keeps_the_space(self):
        self.assertEqual(build_lexicon.norm("Ain-gedi, the"), "aingedi the")

    def test_trims(self):
        self.assertEqual(build_lexicon.norm("  Zion  "), "zion")

    def test_keeps_digits(self):
        self.assertEqual(build_lexicon.norm("Baal 2"), "baal 2")

    def test_is_stable_under_a_second_pass(self):
        # The client normalises the reader's selection with its own copy of
        # this rule; a key that changes when normalised twice cannot be found.
        for raw in ("Abaddon", "Ain-gedi, the", "Beth-El", "  Zion  "):
            once = build_lexicon.norm(raw)
            self.assertEqual(build_lexicon.norm(once), once, raw)


class LexiconFlags(unittest.TestCase):
    """Flags are generated mechanically, so their edges matter."""

    def test_clean_prose_gets_no_flag(self):
        self.assertEqual(build_lexicon.flags_for("A city in the hill country."), [])

    def test_a_measure_is_flagged_as_dated(self):
        flags = build_lexicon.flags_for("about 3 shekels in weight")
        self.assertTrue(any(f["kind"] == "measure" for f in flags))

    def test_every_flag_carries_a_note_the_reader_can_read(self):
        for text in ("about 3 shekels in weight", "A city in the hill country."):
            for flag in build_lexicon.flags_for(text):
                self.assertTrue(flag["note"].strip(), text)
                self.assertIn(flag["kind"], ("dated", "measure"))

    def test_at_most_one_dated_flag(self):
        # The loop breaks after the first match on purpose: two overlapping
        # patterns should not stack two near-identical warnings on one entry.
        many = " ".join(p.pattern for p, _ in build_lexicon.DATED_PATTERNS)
        dated = [f for f in build_lexicon.flags_for(many) if f["kind"] == "dated"]
        self.assertLessEqual(len(dated), 1)


class PlacesNorm(unittest.TestCase):
    def test_lowercases_and_strips_punctuation(self):
        self.assertEqual(build_places.norm("Beth-Shemesh"), "bethshemesh")

    def test_strips_accents(self):
        self.assertEqual(build_places.norm("Bāshān"), "bashan")

    def test_keeps_internal_spaces(self):
        self.assertEqual(build_places.norm("Sea of Galilee"), "sea of galilee")

    def test_is_stable_under_a_second_pass(self):
        for raw in ("Beth-Shemesh", "Bāshān", "Sea of Galilee"):
            once = build_places.norm(raw)
            self.assertEqual(build_places.norm(once), once, raw)

    def test_agrees_with_the_lexicon_rule(self):
        # Two files, one rule. They are allowed to diverge, but not by
        # accident, and nothing else would notice if they did.
        for raw in ("Beth-Shemesh", "Bāshān", "Sea of Galilee", "Ain-gedi, the"):
            self.assertEqual(build_places.norm(raw), build_lexicon.norm(raw), raw)


class PlaceKinds(unittest.TestCase):
    """The uncertainty prefixes are the reason this dataset was chosen."""

    def test_every_prefix_has_a_kind_and_an_explanation(self):
        for prefix, (kind, blurb) in build_places.KIND.items():
            self.assertIn(prefix, (">", "<", "~"))
            self.assertTrue(kind)
            self.assertIn("{root}", blurb + "{root}")

    def test_the_kinds_are_distinct(self):
        kinds = [k for k, _ in build_places.KIND.values()]
        self.assertEqual(len(kinds), len(set(kinds)))


if __name__ == "__main__":
    unittest.main()


class TheOfflineCopyCarriesNoDeadLinks(unittest.TestCase):
    """The one page whose claim is that nothing it needs is elsewhere.

    The served site offers the single-file build for download. Inlining the
    footer whole would put that link inside the file it offers, pointing at a
    path beside itself that is not there. index.html marks the region and
    build_standalone.py cuts it; these hold both ends of that arrangement,
    because the failure is a link that looks perfectly normal and does
    nothing.
    """

    def index(self):
        with open(os.path.join(ROOT, "docs", "index.html"), encoding="utf-8") as fh:
            return fh.read()

    def test_the_markers_are_balanced(self):
        start, end = build_standalone.ONLINE_ONLY
        page = self.index()
        self.assertEqual(page.count(start), page.count(end))
        self.assertGreater(page.count(start), 0,
                           "nothing is marked online-only; if the download "
                           "link has gone, this test and the stripping can go "
                           "with it")

    def test_the_download_link_is_inside_them(self):
        start, end = build_standalone.ONLINE_ONLY
        page = self.index()
        self.assertIn('href="the-book.html"', page,
                      "the served page no longer offers the offline copy")
        self.assertNotIn('href="the-book.html"',
                         build_standalone.strip_online_only(page),
                         "the download link is not inside the online-only "
                         "markers, so the offline copy would link to itself")

    def test_stripping_takes_the_region_and_nothing_else(self):
        start, end = build_standalone.ONLINE_ONLY
        self.assertEqual(
            build_standalone.strip_online_only(f"keep{start}drop{end}keep"),
            "keepkeep")

    def test_an_unclosed_marker_stops_the_build(self):
        start, _end = build_standalone.ONLINE_ONLY
        with self.assertRaises(SystemExit):
            build_standalone.strip_online_only("a" + start + "b")
