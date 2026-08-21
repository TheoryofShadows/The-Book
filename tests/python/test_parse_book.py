"""The parser, function by function.

This is the layer that decides what the text of the volume actually is. A
regression here does not raise anything and does not fail a page: it quietly
publishes a book with a verse missing, and the only sign is a number on the
accuracy report that nobody is watching. Every case below is either a rule the
parser is supposed to follow or a defect that reached the published data once
already.
"""

import unittest

import _tools  # noqa: F401  (import for the side effect: tools/ on sys.path)

import parse_book as pb


class Slugify(unittest.TestCase):
    """Work ids are permalinks. Everything a reader saved is keyed by one."""

    def test_lowercases_and_hyphenates(self):
        self.assertEqual(pb.slugify("The Book of Amos"), "the-book-of-amos")

    def test_strips_accents_to_ascii(self):
        self.assertEqual(pb.slugify("Lûbâr"), "lubar")

    def test_collapses_runs_of_punctuation_to_one_hyphen(self):
        self.assertEqual(pb.slugify("1 Enoch -- Dream Visions"),
                         "1-enoch-dream-visions")

    def test_trims_leading_and_trailing_hyphens(self):
        self.assertEqual(pb.slugify("...Jubilees!"), "jubilees")

    def test_keeps_digits(self):
        self.assertEqual(pb.slugify("2 Maccabees"), "2-maccabees")

    def test_never_returns_a_double_hyphen(self):
        for raw in ("A -- B", "A, B", "A  B", "A...B", "A / B"):
            self.assertNotIn("--", pb.slugify(raw), raw)


class ChapterLabel(unittest.TestCase):
    """Deciding what is a heading and what is not."""

    def test_plain_chapter(self):
        self.assertEqual(pb.chapter_label("CHAPTER 12"), ("Chapter 12", 12))

    def test_chapter_is_case_insensitive(self):
        self.assertEqual(pb.chapter_label("Chapter 3"), ("Chapter 3", 3))

    def test_enoch_keeps_its_own_label(self):
        self.assertEqual(pb.chapter_label("1 ENOCH 72"), ("1 ENOCH 72", 72))

    def test_jubilees_keeps_its_own_label(self):
        self.assertEqual(pb.chapter_label("JUBILEES 6"), ("JUBILEES 6", 6))

    def test_hermas_two_part_marker_takes_the_second_number(self):
        self.assertEqual(pb.chapter_label("SIMILITUDE 1, 4"),
                         ("SIMILITUDE 1, 4", 4))

    def test_prologue_sorts_before_chapter_one(self):
        label, num = pb.chapter_label("JUBILEES - PROLOGUE")
        self.assertEqual(num, 0)
        self.assertIn("Prologue", label)

    def test_ocr_bracket_artifact_is_not_a_heading(self):
        # The reason this function returns None at all. Charles's text carries
        # runs like this, and treating one as a heading starts a chapter in
        # the middle of a sentence.
        self.assertIsNone(pb.chapter_label("[[is beautiful, and its fruit]]]"))

    def test_prose_is_not_a_heading(self):
        self.assertIsNone(pb.chapter_label("And he said unto them"))

    def test_a_word_with_no_number_is_not_a_heading(self):
        self.assertIsNone(pb.chapter_label("CHAPTER"))


class FromRoman(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(pb.from_roman("IV"), 4)
        self.assertEqual(pb.from_roman("VIII"), 8)
        self.assertEqual(pb.from_roman("IX"), 9)
        self.assertEqual(pb.from_roman("XIII"), 13)

    def test_not_a_numeral(self):
        self.assertIsNone(pb.from_roman("SOME"))
        self.assertIsNone(pb.from_roman(""))


class Unsplice(unittest.TestCase):
    """Chapter headings the source preparation left inside the prose.

    Three of these reached the published volume. Each one silently merged a
    chapter into the one before it and left an ANF editorial title standing in
    the text, where the read-aloud voice duly announced it as scripture.
    """

    def setUp(self):
        pb.SPLICES.clear()

    def tearDown(self):
        pb.SPLICES.clear()

    def test_comma_for_full_stop_after_chap(self):
        out = pb.unsplice("...knows all secrets. CHAP, IV.--SOME WICKEDLY ACT "
                          "INDEPENDENTLY OF THE BISHOP. It is fitting, then,")
        self.assertIn("[ Chapter 4 ]", out)
        self.assertIn("knows all secrets.", out)
        self.assertIn("It is fitting, then,", out)
        self.assertNotIn("WICKEDLY", out)

    def test_comma_after_the_numeral(self):
        out = pb.unsplice('blasphemed among any." CHAPTER IX,--REFERENCE TO '
                          'THE HISTORY OF CHRIST. Stop your ears, therefore,')
        self.assertIn("[ Chapter 9 ]", out)
        self.assertIn("Stop your ears, therefore,", out)

    def test_heading_wrapped_across_lines(self):
        out = pb.unsplice("secrets. CHAP, IV.--SOME WICKEDLY ACT INDEPENDENTLY OF\n"
                          "THE BISHOP. It is fitting")
        self.assertIn("[ Chapter 4 ]", out)
        self.assertNotIn("BISHOP", out)

    def test_each_repair_is_logged_with_what_was_dropped(self):
        pb.unsplice("x. CHAP, VIII.--CAUTION AGAINST FALSE DOCTRINES. Be not")
        self.assertEqual(len(pb.SPLICES), 1)
        self.assertEqual(pb.SPLICES[0]["chapter"], 8)
        self.assertEqual(pb.SPLICES[0]["heading"],
                         "CAUTION AGAINST FALSE DOCTRINES")
        self.assertTrue(pb.SPLICES[0]["reason"])

    def test_ordinary_prose_is_left_alone(self):
        text = "And in the seventh week Noah planted vines. Chapter and verse."
        self.assertEqual(pb.unsplice(text), text)
        self.assertEqual(pb.SPLICES, [])

    def test_a_proper_marker_line_is_left_alone(self):
        text = "\n[ Chapter 4 ]\n\nIt is fitting"
        self.assertEqual(pb.unsplice(text), text)

    def test_an_unreadable_numeral_is_left_where_it_is(self):
        text = "x. CHAP, QQ.--SOMETHING OR OTHER. And then"
        self.assertEqual(pb.unsplice(text), text)
        self.assertEqual(pb.SPLICES, [])


class Unwrap(unittest.TestCase):
    def test_hard_wrapped_lines_become_one_paragraph(self):
        self.assertEqual(pb.unwrap(["And he", "said unto", "them"]),
                         ["And he said unto them"])

    def test_blank_lines_separate_paragraphs(self):
        self.assertEqual(pb.unwrap(["one", "", "two"]), ["one", "two"])

    def test_runs_of_blank_lines_do_not_make_empty_paragraphs(self):
        self.assertEqual(pb.unwrap(["one", "", "", "", "two"]), ["one", "two"])

    def test_trailing_blank_lines_are_dropped(self):
        self.assertEqual(pb.unwrap(["one", "", ""]), ["one"])

    def test_a_verse_number_at_the_end_of_a_line_keeps_its_gap(self):
        # The whole reason unwrap preserves trailing whitespace. "12 " at the
        # end of a wrapped line has to rejoin as "12  text", because two
        # spaces is what marks a WEB verse. Join it as "12 text" and the verse
        # boundary is gone and the verse merges into the one before.
        joined = pb.unwrap(["and it came to pass 12 ", "In the days of"])[0]
        self.assertIn("12  In the days of", joined)
        self.assertTrue(pb.WEB_VERSE.search(joined))

    def test_leading_indentation_is_dropped(self):
        self.assertEqual(pb.unwrap(["    indented poetry"]), ["indented poetry"])


class Decontaminate(unittest.TestCase):
    """Scrape furniture that came along with the Apostolic Fathers."""

    def setUp(self):
        pb.REMOVALS.clear()

    def tearDown(self):
        pb.REMOVALS.clear()

    def test_clean_text_is_untouched_and_logs_nothing(self):
        text = "Fare ye well in the grace of God."
        self.assertEqual(pb.decontaminate(text, "somewhere"), text)
        self.assertEqual(pb.REMOVALS, [])

    def test_navigation_footer_is_cut(self):
        out = pb.decontaminate(
            "grace of God. Go to the Chronological List of all Early "
            "Christian Writings", "Smyrnaeans / Chapter 12")
        self.assertEqual(out, "grace of God.")

    def test_advertisement_is_cut(self):
        out = pb.decontaminate("of God. Please buy the CD to support the site",
                               "w / c")
        self.assertEqual(out, "of God.")

    def test_editorial_introduction_is_cut(self):
        out = pb.decontaminate("of God. Introductory Note to the Epistle", "w / c")
        self.assertEqual(out, "of God.")

    def test_elucidation_is_cut(self):
        out = pb.decontaminate("of God. Elucidations. II (See page 20)", "w / c")
        self.assertEqual(out, "of God.")

    def test_every_cut_is_logged_with_where_why_and_what(self):
        pb.decontaminate("of God. Please buy the CD now", "Polycarp / Chapter 3")
        self.assertEqual(len(pb.REMOVALS), 1)
        entry = pb.REMOVALS[0]
        self.assertEqual(entry["where"], "Polycarp / Chapter 3")
        self.assertTrue(entry["reason"])
        self.assertEqual(entry["chars"], len("Please buy the CD now"))
        self.assertTrue(entry["excerpt"].startswith("Please buy the CD"))

    def test_several_contaminants_in_one_passage_are_all_removed(self):
        out = pb.decontaminate(
            "of God. Elucidations. I (x) more junk Please buy the CD", "w / c")
        self.assertEqual(out, "of God.")
        self.assertEqual(len(pb.REMOVALS), 2)

    def test_the_word_elucidation_in_running_prose_survives(self):
        # The pattern wants "Elucidations. II (", not the bare word: cutting on
        # the word alone would truncate any chapter that discusses one.
        text = "he offers no elucidation of the matter"
        self.assertEqual(pb.decontaminate(text, "w / c"), text)


class SplitVerses(unittest.TestCase):
    """Where one verse stops and the next begins."""

    def test_web_style_two_spaces_after_the_number(self):
        verses, style = pb.split_verses(["1  In the beginning. 2  And the earth."])
        self.assertEqual(style, "web")
        self.assertEqual([v["v"] for v in verses], [1, 2])
        self.assertEqual(verses[0]["t"], "In the beginning.")
        self.assertEqual(verses[1]["t"], "And the earth.")

    def test_charles_style_number_then_full_stop(self):
        verses, style = pb.split_verses(["1. And Enoch said. 2. And he spoke."])
        self.assertEqual(style, "charles")
        self.assertEqual([v["v"] for v in verses], [1, 2])

    def test_prose_with_no_numbers_at_all(self):
        verses, style = pb.split_verses(["Having been informed of your godly love."])
        self.assertEqual(verses, [])
        self.assertEqual(style, "prose")

    def test_a_single_marker_is_not_enough_to_call_it_versified(self):
        verses, style = pb.split_verses(["1  Only one marker here."])
        self.assertEqual(style, "prose")

    def test_a_year_inside_a_sentence_is_not_a_verse_marker(self):
        # One space, so WEB does not match; and out of sequence, so it cannot
        # join the run either.
        verses, _ = pb.split_verses(
            ["1  In the year 586 the city fell. 2  And the people wept."])
        self.assertEqual([v["v"] for v in verses], [1, 2])
        self.assertIn("586", verses[0]["t"])

    def test_a_small_gap_in_the_numbering_is_tolerated(self):
        # The WEB leaves gaps where the critical text omits a verse; the run
        # has to survive them or the whole chapter falls back to prose.
        verses, _ = pb.split_verses(["1  a. 2  b. 4  d. 5  e."])
        self.assertEqual([v["v"] for v in verses], [1, 2, 4, 5])

    def test_a_number_far_out_of_sequence_is_ignored(self):
        verses, _ = pb.split_verses(["1  a. 2  b. 90  not a verse. 3  c."])
        self.assertEqual([v["v"] for v in verses], [1, 2, 3])
        self.assertIn("90", verses[1]["t"])

    def test_a_chapter_may_open_at_verse_two(self):
        verses, _ = pb.split_verses(["2  b. 3  c. 4  d."])
        self.assertEqual([v["v"] for v in verses], [2, 3, 4])

    def test_a_chapter_may_not_open_at_verse_nine(self):
        verses, style = pb.split_verses(["9  i. 10  j. 11  k."])
        self.assertEqual(style, "prose")

    def test_whitespace_inside_a_verse_is_collapsed(self):
        verses, _ = pb.split_verses(["1  In   the\n\nbeginning. 2  And."])
        self.assertEqual(verses[0]["t"], "In the beginning.")

    def test_paragraphs_are_joined_before_splitting(self):
        verses, _ = pb.split_verses(["1  first part", "carries on. 2  second."])
        self.assertEqual(len(verses), 2)
        self.assertIn("carries on.", verses[0]["t"])

    def test_web_wins_over_charles_when_both_could_match(self):
        verses, style = pb.split_verses(["1  a. 2  b. 3  c."])
        self.assertEqual(style, "web")

    # ---- the opening verse ------------------------------------------------
    #
    # Charles prints verse one without its number: the chapter numeral carries
    # it and the visible numbering starts at "2.". Slicing from the first
    # marker threw that text away. It removed 56 chapter openings -- some
    # twelve thousand characters of Jubilees and Enoch -- from the published
    # volume, and the only trace was an audit line saying the chapter started
    # at verse two.

    def test_text_before_the_first_marker_is_the_opening_verse(self):
        verses, _ = pb.split_verses(
            ["And Noah planted vines. 2. one of the mountains, 3. and he guarded"])
        self.assertEqual([v["v"] for v in verses], [1, 2, 3])
        self.assertEqual(verses[0]["t"], "And Noah planted vines.")

    def test_the_opening_verse_takes_the_number_below_the_first_marker(self):
        verses, _ = pb.split_verses(["opening words. 2. second. 3. third."])
        self.assertEqual([v["v"] for v in verses], [1, 2, 3])
        self.assertEqual(verses[0]["t"], "opening words.")

    def test_a_run_starting_at_three_is_not_a_chapter_opening(self):
        # The opening-verse rule rides on the run-detection rule and must not
        # widen it: a chapter opens at verse 1 or, after an omission, at 2.
        # A first marker of 3 means these are not verse numbers, and inventing
        # a verse 2 in front of them would be worse than reading it as prose.
        verses, style = pb.split_verses(["opening words. 3. third. 4. fourth."])
        self.assertEqual(verses, [])
        self.assertEqual(style, "prose")

    def test_no_phantom_verse_when_the_chapter_opens_at_one(self):
        verses, _ = pb.split_verses(["1  In the beginning. 2  And the earth."])
        self.assertEqual([v["v"] for v in verses], [1, 2])

    def test_no_phantom_verse_when_there_is_no_opening_text(self):
        verses, _ = pb.split_verses(["2  b. 3  c."])
        self.assertEqual([v["v"] for v in verses], [2, 3])

    def test_the_v_prefix_typo_is_read_as_a_verse_number(self):
        # Jubilees 6 opens "V1." where every other chapter opens "1.". Without
        # this the chapter began at verse 2 and verse 1 was deleted.
        verses, style = pb.split_verses(
            ["V1. And on the new moon he went forth. 2. And he made atonement."])
        self.assertEqual(style, "charles")
        self.assertEqual([v["v"] for v in verses], [1, 2])
        self.assertTrue(verses[0]["t"].startswith("And on the new moon"))

    def test_a_roman_numeral_is_not_swallowed_by_the_v_prefix(self):
        # "V?" must need a digit straight after it, or "VII." becomes a marker.
        verses, _ = pb.split_verses(["1. a. VII. And in the seventh week. 2. b."])
        self.assertEqual([v["v"] for v in verses], [1, 2])
        self.assertIn("VII.", verses[0]["t"])


class SourceFor(unittest.TestCase):
    """Which printed edition a work is attributed to."""

    def test_no_text_means_the_note_was_written_here(self):
        self.assertEqual(pb.source_for("philo-of-alexandria", "s", False),
                         "editorial")

    def test_enoch_and_jubilees_are_charles(self):
        self.assertEqual(pb.source_for("1-enoch-the-watchers", "s", True), "charles")
        self.assertEqual(pb.source_for("jubilees", "s", True), "charles")

    def test_apostolic_fathers_are_ante_nicene(self):
        self.assertEqual(
            pb.source_for("the-epistle-of-barnabas", "the-apostolic-fathers", True),
            "anf")

    def test_everything_else_is_the_world_english_bible(self):
        self.assertEqual(pb.source_for("amos", "the-latter-prophets", True), "web")

    def test_attribution_follows_the_work_not_the_numbering_style(self):
        # The Didache numbers its verses the way Charles's Enoch does, and is
        # still a Roberts-Donaldson translation.
        self.assertEqual(
            pb.source_for("the-teaching-of-the-twelve-apostles-didache",
                          "the-apostolic-fathers", True),
            "anf")


if __name__ == "__main__":
    unittest.main()
