"""Reading a date out of a position statement.

Every form below is one that actually occurs in tools/positions.py. The last
class in the file runs the parser over all 104 statements in the volume and
holds it to a coverage figure, so a change that quietly stops recognising a
form shows up as a number rather than as a date card that went blank.
"""

import re
import unittest

import _tools  # noqa: F401

import dates
from positions import POSITIONS


class ExplicitYears(unittest.TestCase):
    def test_a_span_of_years_bce(self):
        s = dates.span("Amos of Tekoa, c. 760-750 BCE")
        self.assertEqual((s["frm"], s["to"]), (-760, -750))
        self.assertEqual(s["kind"], "explicit")
        self.assertTrue(s["approx"])

    def test_a_span_of_years_ce(self):
        s = dates.span("c. 90-110 CE")
        self.assertEqual((s["frm"], s["to"]), (90, 110))

    def test_a_single_year(self):
        s = dates.span("Ezekiel, 561 BCE")
        self.assertEqual((s["frm"], s["to"]), (-561, -561))

    def test_a_single_year_ce(self):
        s = dates.span("written at Rome, 62 CE")
        self.assertEqual((s["frm"], s["to"]), (62, 62))

    def test_an_en_dash_reads_the_same_as_a_hyphen(self):
        # Only the matched substring differs, and only in the dash itself.
        en, hy = dates.span("c. 593–571 BCE"), dates.span("c. 593-571 BCE")
        self.assertEqual((en["frm"], en["to"], en["kind"]),
                         (hy["frm"], hy["to"], hy["kind"]))

    def test_the_earlier_end_comes_first_whichever_way_it_is_written(self):
        s = dates.span("750-760 BCE")
        self.assertEqual((s["frm"], s["to"]), (-760, -750))

    def test_a_statement_with_no_hedge_is_not_marked_approximate(self):
        self.assertFalse(dates.span("Ezekiel, 561 BCE")["approx"])

    def test_every_hedge_is_recognised(self):
        for hedge in ("c.", "ca.", "about", "around", "roughly",
                      "perhaps", "probably"):
            self.assertTrue(dates.span(hedge + " 500 BCE")["approx"], hedge)


class Centuries(unittest.TestCase):
    def test_a_century_bce_runs_from_its_hundred_to_its_one(self):
        s = dates.span("Hosea, 8th century BCE")
        self.assertEqual((s["frm"], s["to"]), (-800, -701))
        self.assertEqual(s["kind"], "century")

    def test_the_first_century_ce_starts_at_year_one(self):
        s = dates.span("1st century CE")
        self.assertEqual((s["frm"], s["to"]), (1, 100))

    def test_a_later_century_ce(self):
        s = dates.span("2nd century CE")
        self.assertEqual((s["frm"], s["to"]), (101, 200))

    def test_a_span_of_centuries_covers_both_ends(self):
        s = dates.span("Moses, 15th-13th century BCE")
        self.assertEqual((s["frm"], s["to"]), (-1500, -1201))

    def test_the_common_two_century_span(self):
        s = dates.span("Deuteronomistic History, 7th-6th century BCE")
        self.assertEqual((s["frm"], s["to"]), (-700, -501))

    def test_a_century_span_is_not_misread_as_a_single_century(self):
        # "15th-13th century BCE" must not be read as the 13th century, and
        # must not be read as the year 15 either. Both are what happens if the
        # patterns are tried in the wrong order.
        s = dates.span("15th-13th century BCE")
        self.assertEqual(s["frm"], -1500)
        self.assertNotEqual(s["frm"], -15)

    def test_a_century_is_marked_as_a_century_not_an_exact_year(self):
        self.assertEqual(dates.span("6th century BCE")["kind"], "century")


class NamedPeriods(unittest.TestCase):
    def test_the_persian_period(self):
        s = dates.span("Composite; final form in the Persian period")
        self.assertEqual((s["frm"], s["to"]), (-539, -332))
        self.assertEqual(s["kind"], "period")

    def test_a_period_is_always_approximate(self):
        self.assertTrue(dates.span("Priestly source, exilic")["approx"])

    def test_a_period_carries_the_event_that_fixes_it(self):
        # The file's own rule: a claim the reader cannot check does not belong
        # beside one that was checked. A period imposes boundaries the position
        # did not state, so it has to say where they come from.
        s = dates.span("final form in the Persian period")
        self.assertIn("Babylon", s["basis"])

    def test_every_period_in_the_table_has_its_reason(self):
        for name, (frm, to, why) in dates.PERIODS.items():
            self.assertLess(frm, to, name)
            self.assertTrue(why.strip(), name)

    def test_an_explicit_year_beats_the_period_it_falls_in(self):
        # The tighter claim is the one the position's author made.
        s = dates.span("Persian period, c. 500-400 BCE")
        self.assertEqual((s["frm"], s["to"]), (-500, -400))
        self.assertEqual(s["kind"], "explicit")

    def test_the_longest_matching_name_wins(self):
        s = dates.span("a post-exilic composition")
        self.assertEqual((s["frm"], s["to"]), (-538, -332))


class Decades(unittest.TestCase):
    def test_a_span_of_decades(self):
        s = dates.span("Mark, recording Peter's preaching, c. 50s-60s CE")
        self.assertEqual((s["frm"], s["to"]), (50, 69))
        self.assertEqual(s["kind"], "decade")

    def test_a_single_decade(self):
        s = dates.span("the 60s CE")
        self.assertEqual((s["frm"], s["to"]), (60, 69))

    def test_a_decade_is_always_approximate(self):
        self.assertTrue(dates.span("the 60s CE")["approx"])

    def test_a_decade_bce_runs_backwards(self):
        s = dates.span("the 50s BCE")
        self.assertEqual((s["frm"], s["to"]), (-59, -50))

    def test_a_plain_year_is_not_read_as_a_decade(self):
        self.assertEqual(dates.span("60 CE")["kind"], "explicit")


class NoDate(unittest.TestCase):
    """Refusing to guess is the whole point."""

    def test_a_position_with_no_date_gets_no_span(self):
        self.assertIsNone(dates.span("Moses, shortly before his death"))

    def test_a_bare_name_gets_no_span(self):
        self.assertIsNone(dates.span("Samuel"))
        self.assertIsNone(dates.span("Jeremiah"))

    def test_empty_text(self):
        self.assertIsNone(dates.span(""))
        self.assertIsNone(dates.span(None))

    def test_a_year_with_no_era_is_not_a_date(self):
        # "Josiah's reform of 622" names an event, not the date of the book.
        self.assertIsNone(dates.span("connected to Josiah's reform of 622"))

    def test_a_chapter_and_verse_is_not_a_date(self):
        self.assertIsNone(dates.span("Amos 9:11-15"))


class Distance(unittest.TestCase):
    def test_overlapping_positions_are_no_distance_apart(self):
        a = dates.span("c. 760-750 BCE")
        b = dates.span("c. 755-740 BCE")
        self.assertEqual(dates.distance(a, b), 0)

    def test_one_inside_the_other_is_no_distance_apart(self):
        a = dates.span("8th century BCE")
        b = dates.span("c. 760-750 BCE")
        self.assertEqual(dates.distance(a, b), 0)

    def test_positions_that_do_not_meet_are_measured(self):
        a = dates.span("15th-13th century BCE")     # ends 1201 BCE
        b = dates.span("c. 500-400 BCE")            # starts 500 BCE
        self.assertEqual(dates.distance(a, b), 701)

    def test_the_measure_does_not_depend_on_the_order(self):
        a, b = dates.span("10th century BCE"), dates.span("c. 200 BCE")
        self.assertEqual(dates.distance(a, b), dates.distance(b, a))

    def test_an_unknown_date_makes_the_distance_unknown(self):
        self.assertIsNone(dates.distance(dates.span("Samuel"),
                                         dates.span("c. 500 BCE")))


class Labels(unittest.TestCase):
    def test_a_negative_year_is_bce(self):
        self.assertEqual(dates.label(-760), "760 BCE")

    def test_a_positive_year_is_ce(self):
        self.assertEqual(dates.label(95), "95 CE")

    def test_a_span_within_one_era_names_the_era_once(self):
        self.assertEqual(dates.describe(dates.span("c. 760-750 BCE")),
                         "c. 760–750 BCE")

    def test_a_span_across_the_eras_names_both(self):
        self.assertEqual(dates.describe(dates.span("Second Temple")),
                         "c. 516 BCE – 70 CE")

    def test_a_single_year(self):
        self.assertEqual(dates.describe(dates.span("561 BCE")), "561 BCE")

    def test_no_date_says_so(self):
        self.assertEqual(dates.describe(None), "no numeric date")


class Enrich(unittest.TestCase):
    def test_the_record_is_returned_unchanged_apart_from_the_span(self):
        record = POSITIONS["amos"]
        out = dates.enrich(record)
        for key, value in record.items():
            self.assertEqual(out[key], value, key)
        self.assertIn("span", out)

    def test_the_original_record_is_not_modified(self):
        record = POSITIONS["amos"]
        dates.enrich(record)
        self.assertNotIn("span", record)

    def test_both_positions_are_read(self):
        out = dates.enrich(POSITIONS["amos"])
        self.assertEqual(out["span"]["trad"]["frm"], -760)
        self.assertEqual(out["span"]["crit"]["frm"], -760)
        self.assertEqual(out["span"]["apart"], 0)

    def test_the_hand_written_gap_is_carried_through(self):
        out = dates.enrich(POSITIONS["genesis"])
        self.assertIn(out["span"]["gap"], ("none", "narrow", "wide"))

    def test_none_in_none_out(self):
        self.assertIsNone(dates.enrich(None))


class AgainstTheWholeVolume(unittest.TestCase):
    """Over every position statement the volume actually contains."""

    @classmethod
    def setUpClass(cls):
        cls.statements = [(wid, field, rec[field])
                          for wid, rec in POSITIONS.items()
                          for field in ("trad", "crit")]
        cls.parsed = [(w, f, t, dates.span(t)) for w, f, t in cls.statements]

    def _ratio(self, field):
        rows = [p for p in self.parsed if p[1] == field]
        return len([p for p in rows if p[3]]) / len(rows), len(rows)

    def test_nearly_every_critical_position_yields_a_span(self):
        # The critical position is a dating claim, so it almost always carries
        # one. The three that do not name a source rather than a date.
        ratio, total = self._ratio("crit")
        self.assertGreaterEqual(
            ratio, 0.90,
            "only %.0f%% of %d critical positions parsed; a form has probably "
            "stopped being recognised" % (ratio * 100, total))

    def test_the_traditional_positions_parse_less_often_and_that_is_correct(self):
        # Tradition mostly answers "who", not "when" -- "Samuel", "Jeremiah",
        # "Moses, shortly before his death". Those have no numeric date and
        # must not be given one. The floor guards against a regression; the
        # ceiling guards against the parser starting to invent dates out of
        # names and stray numbers.
        ratio, total = self._ratio("trad")
        self.assertGreaterEqual(ratio, 0.50, "%.0f%% of %d" % (ratio * 100, total))
        self.assertLessEqual(ratio, 0.85, "%.0f%% of %d -- suspiciously high"
                             % (ratio * 100, total))

    def test_no_span_is_inside_out(self):
        for wid, field, text, sp in self.parsed:
            if sp:
                self.assertLessEqual(sp["frm"], sp["to"], f"{wid}.{field}: {text}")

    def test_no_span_lands_somewhere_impossible(self):
        # The volume runs from the earliest identifiable material to the
        # Apostolic Fathers, and one book past them: the Ethiopic Sinodos
        # is a compilation rather than a composition, and the critical
        # position dates the compiling rather than the canons in it. The
        # ceiling is set to hold that and nothing looser. Anything outside
        # these bounds is a misparse, not a date.
        for wid, field, text, sp in self.parsed:
            if sp:
                self.assertGreater(sp["frm"], -2000, f"{wid}.{field}: {text}")
                self.assertLess(sp["to"], 650, f"{wid}.{field}: {text}")

    def test_every_statement_that_names_an_era_is_read(self):
        # If the text says BCE or CE, a date is being asserted and the parser
        # has no excuse for missing it.
        for wid, field, text, sp in self.parsed:
            if "BCE" in text or "CE" in text:
                self.assertIsNotNone(sp, f"{wid}.{field} names an era but did "
                                          f"not parse: {text}")


if __name__ == "__main__":
    unittest.main()


class TheMethodPageMatchesTheParser(unittest.TestCase):
    """The reader's period table is a second copy of dates.PERIODS.

    It is prose for a human rather than data for a program, so it is written
    out by hand in docs/assets/app.js -- which means it can drift, and a
    methodology page that describes boundaries the parser does not use is
    worse than no methodology page at all.
    """

    @classmethod
    def setUpClass(cls):
        import os
        import re
        path = os.path.join(_tools.ROOT, "docs", "assets", "app.js")
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        block = re.search(r"var PERIOD_TABLE = \[(.*?)\n  \];", src, re.S)
        assert block, "PERIOD_TABLE is not in app.js"
        cls.rows = re.findall(r'\["([^"]+)", "([^"]+)", "([^"]*)"\]',
                              block.group(1))

    def test_the_table_was_found_and_is_not_empty(self):
        self.assertGreaterEqual(len(self.rows), 8)

    def test_every_row_names_a_period_the_parser_knows(self):
        # The table stores the parser's own key, and the page title-cases it
        # for display, so there is no second spelling to keep in step.
        for name, _span, _why in self.rows:
            self.assertIn(name, dates.PERIODS, name)

    def test_every_row_states_the_span_the_parser_uses(self):
        for name, shown, _why in self.rows:
            frm, to, _ = dates.PERIODS[name]
            self.assertEqual(shown.replace("\u2013", "-").replace(" - ", "-"),
                             dates.describe({"frm": frm, "to": to,
                                             "approx": False, "kind": "period"})
                             .replace("\u2013", "-").replace(" - ", "-"),
                             name)

    def test_every_row_states_the_reason_the_parser_carries(self):
        for name, _span, why in self.rows:
            self.assertEqual(why, dates.PERIODS[name][2], name)


class SectionDates(unittest.TestCase):
    """The forms the volume's own section headings use.

    These were found by trying to draw a timeline from them, at which point
    three of the ten sections turned out to be losing half their range: the
    span patterns could not see a hedge inside a span, could not see a span
    whose two ends carry different eras, and read "before c. 900 BCE" as the
    year 900 rather than as everything up to it.
    """

    def test_a_hedge_inside_the_span_does_not_eat_the_start(self):
        s = dates.span("539 - c. 400 BCE")
        self.assertEqual((s["frm"], s["to"]), (-539, -400))

    def test_a_span_across_the_eras(self):
        s = dates.span("c. 100 BCE - 50 CE")
        self.assertEqual((s["frm"], s["to"]), (-100, 50))

    def test_a_span_across_the_eras_is_not_read_as_its_second_half(self):
        self.assertNotEqual(dates.span("c. 100 BCE - 50 CE")["frm"], 50)

    def test_before_leaves_the_early_end_open(self):
        s = dates.span("before c. 900 BCE")
        self.assertEqual(s["open"], "before")
        self.assertEqual(s["to"], -900)

    def test_after_leaves_the_late_end_open(self):
        self.assertEqual(dates.span("after 200 BCE")["open"], "after")

    def test_an_ordinary_span_is_not_marked_open(self):
        self.assertNotIn("open", dates.span("c. 760-700 BCE"))

    def test_a_span_whose_end_is_hedged_is_not_marked_open(self):
        # "539 - c. 400 BCE" has no "before" in it, but neither may a phrase
        # like "from 539 to c. 400 BCE" be turned into an open span once the
        # two ends have already been read.
        self.assertNotIn("open", dates.span("from 539 to c. 400 BCE"))

    def test_an_open_span_cannot_be_measured_against_anything(self):
        self.assertIsNone(dates.distance(dates.span("before c. 900 BCE"),
                                         dates.span("c. 500 BCE")))

    def test_an_open_span_says_so_when_written_out(self):
        self.assertEqual(dates.describe(dates.span("before c. 900 BCE")),
                         "before c. 900 BCE")

    def test_years_with_no_era_are_still_not_dates(self):
        # Section X is dated 1896-1979 -- when the manuscripts were found, not
        # when anything was written. Leaving it out of a composition timeline
        # is the right answer, and falls out of the rule already in force.
        self.assertIsNone(dates.span("1896-1979"))

    def test_every_dated_section_of_the_volume_is_read(self):
        import json
        import os
        path = os.path.join(_tools.ROOT, "docs", "data", "manifest.json")
        with open(path, encoding="utf-8") as fh:
            manifest = json.load(fh)
        missed = []
        for section in manifest["sections"]:
            text = section.get("dates") or ""
            if not section["works"] or not re.search(r"\b(BCE|CE)\b", text):
                continue
            sp = dates.span(text)
            if not sp:
                missed.append((section["name"], text))
            else:
                # A span that swallowed only half its range is the failure
                # this class exists for, and it looks like success otherwise.
                stated = [int(n) for n in re.findall(r"\b(\d{3,4})\b", text)]
                if len(stated) > 1 and sp["frm"] == sp["to"]:
                    missed.append((section["name"], text + " -> single point"))
        self.assertEqual(missed, [], "sections whose dates were not fully read")
