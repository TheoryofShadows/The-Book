#!/usr/bin/env python3
"""The arithmetic that turns a reading into verse offsets.

None of this needs audio or an aligner. What it needs is the shape of the
answer one gives back -- a timing per word -- and everything after that is
bookkeeping that can be wrong in quiet ways: a verse claiming a span it does
not own, a chapter that runs backwards, an offset that forgot the chapter is a
slice of a longer file rather than a file of its own.

The last of those is the one worth naming. Every recording here holds a whole
work, so a chapter begins some way into it and every offset is the chapter's
own start plus the word's place within it. A test whose chapter began at zero
would pass whether or not that addition ever happened.
"""

import os
import unittest

import _tools  # noqa: F401

import align_audio as aa
import build_readings
import speakable as speakable_rule

EDITORIAL = speakable_rule.editorial_pattern()


def chapter(*verses):
    return {"verses": [{"v": n, "t": t} for n, t in verses]}


class WhatTheAlignerIsShown(unittest.TestCase):

    def test_each_word_carries_the_verse_it_came_from(self):
        tokens, owners = aa.chapter_tokens(
            chapter((1, "In the beginning"), (2, "The earth was")), EDITORIAL)
        self.assertEqual(tokens,
                         ["In", "the", "beginning", "The", "earth", "was"])
        self.assertEqual(owners, [1, 1, 1, 2, 2, 2])

    def test_the_apparatus_is_not_read_out(self):
        """A narrator does not say "dagger". The aligner is shown what a voice
        would have said, through the same rule the reader uses."""
        tokens, _ = aa.chapter_tokens(chapter((1, "the †corrupt† word")),
                                      EDITORIAL)
        self.assertEqual(tokens, ["the", "corrupt", "word"])

    def test_a_verse_that_is_nothing_but_apparatus_is_skipped(self):
        tokens, owners = aa.chapter_tokens(
            chapter((1, "real words"), (2, "†‡"), (3, "more words")), EDITORIAL)
        self.assertEqual(owners, [1, 1, 3, 3])
        self.assertEqual(tokens, ["real", "words", "more", "words"])


class TurningTimingsIntoVerses(unittest.TestCase):

    def test_a_verse_spans_its_first_word_to_its_last(self):
        spans = aa.verse_spans([1, 1, 2, 2],
                               [(0.0, 0.5), (0.5, 1.0), (1.4, 1.9), (1.9, 2.6)])
        self.assertEqual(spans, [[1, 0.0, 1.0], [2, 1.4, 2.6]])

    def test_the_chapter_is_a_slice_of_the_work_not_a_file_of_its_own(self):
        """Every offset is the chapter's own start plus the word's place in
        it. This is the addition the reader depends on and cannot check."""
        spans = aa.verse_spans([1, 1], [(0.0, 0.5), (0.5, 1.0)], at=100.0)
        self.assertEqual(spans, [[1, 100.0, 101.0]])

    def test_a_word_the_aligner_could_not_place_does_not_vote(self):
        spans = aa.verse_spans([1, 1, 1],
                               [(0.0, 0.5), None, (1.0, 1.5)])
        self.assertEqual(spans, [[1, 0.0, 1.5]])

    def test_a_verse_with_nothing_placed_at_all_is_dropped(self):
        """Dropped rather than guessed at. The reader treats a verse missing
        from the index as one it cannot seek to, which is true; an invented
        offset would send a listener to the wrong words."""
        spans = aa.verse_spans([1, 2, 3],
                               [(0.0, 0.5), None, (1.0, 1.5)])
        self.assertEqual([s[0] for s in spans], [1, 3])

    def test_the_rows_come_out_in_time_order(self):
        spans = aa.verse_spans([2, 1], [(5.0, 6.0), (1.0, 2.0)])
        self.assertEqual([s[0] for s in spans], [1, 2])

    def test_a_timing_for_every_token_or_it_refuses(self):
        with self.assertRaises(ValueError):
            aa.verse_spans([1, 2], [(0.0, 1.0)])


class WhatCountsAsAFailedAlignment(unittest.TestCase):
    """Every one of these is a way for an alignment to look like a result
    without being one, and every one of them means the reader hears the device
    voice for that chapter instead."""

    def test_nothing_placed_at_all(self):
        self.assertIn("nothing was placed", aa.chapter_problems([], 100))

    def test_a_chapter_that_runs_backwards(self):
        bad = aa.chapter_problems([[1, 5.0, 6.0], [2, 1.0, 2.0]], 100)
        self.assertTrue(any("before the verse before it" in b for b in bad), bad)

    def test_a_verse_that_ends_before_it_starts(self):
        bad = aa.chapter_problems([[1, 5.0, 4.0]], 60)
        self.assertTrue(any("ends at or before it starts" in b for b in bad), bad)

    def test_too_slow_to_be_a_reading_of_this_text(self):
        """Ten characters spread over a minute is a verse attached to
        silence, which is what a mismatched recording produces."""
        bad = aa.chapter_problems([[1, 0.0, 60.0]], 10)
        self.assertTrue(any("too slow" in b for b in bad), bad)

    def test_too_fast_to_be_a_reading_of_this_text(self):
        bad = aa.chapter_problems([[1, 0.0, 1.0]], 5000)
        self.assertTrue(any("too fast" in b for b in bad), bad)

    def test_a_plausible_reading_passes(self):
        # 300 characters in 20 seconds: 15 a second, an ordinary pace.
        self.assertEqual(aa.chapter_problems([[1, 0.0, 10.0], [2, 10.0, 20.0]],
                                             300), [])

    def test_coverage_is_the_fraction_actually_placed(self):
        self.assertEqual(aa.coverage([(0, 1), None, (2, 3), (3, 4)]), 0.75)
        self.assertEqual(aa.coverage([]), 0.0)


class TheIndexTheReaderFetches(unittest.TestCase):

    def setUp(self):
        self.index = aa.build_index("web-altman", "amos.opus", [
            (0, [[1, 0.0, 4.0], [2, 4.35, 9.0]]),
            (1, [[1, 20.0, 24.0]]),
        ])

    def test_it_declares_its_own_rest_rather_than_leaving_it_assumed(self):
        self.assertEqual(self.index["gap"], aa.GAP)

    def test_each_chapter_gets_a_span_covering_its_verses(self):
        self.assertEqual(self.index["c"][0][0], 0.0)
        self.assertGreaterEqual(self.index["c"][0][1], 9.0)
        self.assertEqual(self.index["c"][1][0], 20.0)

    def test_the_verses_are_keyed_by_the_readers_chapter_index(self):
        self.assertEqual(sorted(self.index["v"]), ["0", "1"])

    def test_the_asset_name_stays_flat(self):
        """Release asset names cannot contain a slash."""
        self.assertNotIn("/", self.index["src"])

    def test_the_builder_accepts_what_the_aligner_writes(self):
        """The two halves, held together. build_readings.py is what decides
        whether a claim reaches the manifest, so an index this produces and
        that refuses is a pipeline that cannot publish its own output."""
        problems = build_readings.check_index("amos", self.index, "web")
        self.assertEqual(problems, [], problems)

    def test_and_refuses_it_against_the_wrong_edition(self):
        """The same index, offered for a work printing Charles rather than
        the World English Bible, must not be accepted."""
        problems = build_readings.check_index("jubilees", self.index, "charles")
        self.assertTrue(any("different words" in p for p in problems), problems)


class TheRejectionReport(unittest.TestCase):

    def test_it_is_written_even_when_nothing_was_rejected(self):
        """A coverage figure that only appears when it is good is one nobody
        can act on."""
        import tempfile
        path = os.path.join(tempfile.mkdtemp(prefix="align-"), "rejected.txt")
        self.assertEqual(aa.report(path, []), 0)
        with open(path, encoding="utf-8") as fh:
            self.assertIn("Nothing was rejected", fh.read())

    def test_it_names_the_chapter_and_the_reason(self):
        import tempfile
        path = os.path.join(tempfile.mkdtemp(prefix="align-"), "rejected.txt")
        aa.report(path, [("hermas", 3, ["nothing was placed"])])
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
        self.assertIn("hermas chapter 3", body)
        self.assertIn("nothing was placed", body)
        self.assertIn("same edition", body)


if __name__ == "__main__":
    unittest.main()
