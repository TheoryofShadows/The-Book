#!/usr/bin/env python3
"""The date range, written twice, in two languages.

A position record says "c. 760-750 BCE" in prose and tools/dates.py reads a
{frm, to, kind, approx, open} out of it. Turning that back into words is done
in two places: describe() in tools/dates.py, which writes the static timeline
page, and spanText() in docs/assets/app.js, which writes the one the reader
draws. They are the same rule, and the rule has edges -- an open end that must
not print its one figure as though it were the date, a range that crosses the
era boundary and needs BCE on both halves, a single year, an approximation.

Nothing else in the build would notice them drifting. Both pages would render,
both would look right, and the only symptom would be the same work dated one
way to a crawler and another way to a reader.

So the JS is executed here rather than translated. A Python translation would
be a third copy of the rule and would agree with the other two by
construction, which is the failure this file exists to prevent.
"""

import json
import os
import shutil
import subprocess
import unittest

import _tools                                              # noqa: F401

import dates

APP_JS = os.path.join(_tools.ROOT, "docs", "assets", "app.js")

# The awkward cases, not the ordinary ones. An ordinary range agrees whatever
# either side does with it.
SAMPLE = [
    {"frm": -760, "to": -750, "kind": "explicit", "approx": True},
    {"frm": -760, "to": -750, "kind": "explicit", "approx": False},
    {"frm": -165, "to": -165, "kind": "explicit", "approx": False},
    {"frm": -165, "to": -165, "kind": "explicit", "approx": True},
    # Crossing the boundary: both ends need their era, and there is no year 0.
    {"frm": -100, "to": 50, "kind": "period", "approx": True},
    {"frm": -1, "to": 1, "kind": "explicit", "approx": False},
    # Wholly in the common era.
    {"frm": 95, "to": 95, "kind": "explicit", "approx": True},
    {"frm": 110, "to": 150, "kind": "century", "approx": True},
    # One end unstated. Printing the figure alone would turn "before c. 900
    # BCE" into a claim that something was written in 900 BCE.
    {"frm": -900, "to": -900, "kind": "period", "approx": True, "open": "before"},
    {"frm": 150, "to": 150, "kind": "period", "approx": False, "open": "after"},
    {"frm": -1200, "to": -1200, "kind": "century", "approx": True,
     "open": "before"},
]


def js_span(spans):
    script = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8');

const START = '/* --8<-- span: start --8<--';
const END = '/* --8<-- span: end --8<-- */';
const a = src.indexOf(START), b = src.indexOf(END);
if (a < 0 || b < 0) {
  throw new Error('the span markers are not in app.js; if the block moved, ' +
                  'move these markers with it -- do not delete them');
}
const block = src.slice(src.indexOf('*/', a) + 2, b);

const make = new Function(block + '; return spanText;');
const spanText = make();
process.stdout.write(JSON.stringify(JSON.parse(process.argv[2]).map(spanText)));
"""
    out = subprocess.run(["node", "-e", script, APP_JS, json.dumps(spans)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError("could not run the reader's spanText:\n"
                             + out.stderr.strip())
    return json.loads(out.stdout)


@unittest.skipIf(shutil.which("node") is None,
                 "node is needed to run the reader's own copy of the rule")
class SpanAgreement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.js = js_span(SAMPLE)

    def test_every_span_reads_the_same_in_both(self):
        for span, js in zip(SAMPLE, self.js):
            self.assertEqual(dates.describe(span), js,
                             "the two copies disagree about %r" % (span,))

    def test_an_open_end_never_prints_its_figure_alone(self):
        """The one that matters most: a bare year here is a date the position
        never gave."""
        for span, js in zip(SAMPLE, self.js):
            if not span.get("open"):
                continue
            self.assertTrue(js.startswith(span["open"]), js)
            self.assertTrue(dates.describe(span).startswith(span["open"]))


if __name__ == "__main__":
    unittest.main()
