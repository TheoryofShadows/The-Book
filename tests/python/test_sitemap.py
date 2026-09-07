#!/usr/bin/env python3
"""The sitemap, and the date on it.

The list of URLs is checked by build_pages itself, which refuses to write a
file with a duplicate in it. What is checked here is the lastmod, because it
is the half that can be wrong while looking right.

A crawler cannot tell a page it read last week from one rewritten since
unless the file says so. On 2,724 pages belonging to a site with no
particular standing, that is the difference between being re-read and being
left alone -- and 2,240 of these pages are known to Google and not indexed.

But a date is only worth having while it is true. Google discounts the whole
file once it catches a site stamping every page with today, and the easy way
to arrive at that is a build that uses its own clock. So the rule these hold
is not "there is a date" but "the date is the day the text last moved, and a
rebuild that changes nothing does not move it".
"""

import datetime
import os
import re
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                os.pardir, os.pardir, "tools"))

import build_pages                                            # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    os.pardir, os.pardir)
SITEMAP = os.path.join(ROOT, "docs", "sitemap.xml")


def read():
    with open(SITEMAP, encoding="utf-8") as fh:
        return fh.read()


class TheDate(unittest.TestCase):
    """What the lastmod says, and whether it is entitled to say it."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(SITEMAP):
            raise unittest.SkipTest("no sitemap built yet")
        cls.xml = read()

    def test_every_url_carries_one(self):
        """A date on some pages and not others is worse than none: it invites
        the crawler to read the undated ones as unchanged."""
        locs = len(re.findall(r"<loc>", self.xml))
        mods = len(re.findall(r"<lastmod>", self.xml))
        self.assertEqual(locs, mods,
                         "%d URLs but %d dates" % (locs, mods))
        self.assertGreater(locs, 2000, "suspiciously few URLs")

    def test_it_is_a_date_a_crawler_will_accept(self):
        """W3C date, which is what the sitemap protocol asks for."""
        for stamp in set(re.findall(r"<lastmod>([^<]+)</lastmod>", self.xml)):
            self.assertRegex(stamp, r"^\d{4}-\d{2}-\d{2}$")
            datetime.date.fromisoformat(stamp)          # raises if not real

    def test_it_is_not_today_unless_today_is_true(self):
        """The failure this file exists to prevent.

        A build that stamps its own clock produces a sitemap that says every
        one of 2,724 pages changed this morning, every morning. That is not a
        small inaccuracy -- it is the thing that gets the dates ignored, so
        the honest pages lose the benefit along with the dishonest ones.

        Asserted against what git says about the text rather than against
        "not today", so that it still holds on the day the text really does
        change.
        """
        stamps = set(re.findall(r"<lastmod>([^<]+)</lastmod>", self.xml))
        self.assertEqual(len(stamps), 1,
                         "one build, one date: got %r" % (sorted(stamps),))
        self.assertEqual(stamps.pop(), build_pages.source_date())

    def test_the_date_comes_from_the_text_not_the_clock(self):
        """source_date() answers with the last commit that touched the text.

        Checked against git directly rather than trusting the function to
        agree with itself.
        """
        got = subprocess.run(
            ["git", "-C", ROOT, "log", "-1", "--format=%cs",
             "--", "source", "docs/data"],
            capture_output=True, text=True, encoding="utf-8", timeout=20)
        stamp = (got.stdout or "").strip()
        if not stamp:
            self.skipTest("no git history here to check against")
        self.assertEqual(build_pages.source_date(), stamp)

    def test_building_twice_writes_the_same_date(self):
        """Because a date that moves on a build that changed nothing is the
        same lie told slowly."""
        first = build_pages.source_date()
        second = build_pages.source_date()
        self.assertEqual(first, second)


class TheFile(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(SITEMAP):
            raise unittest.SkipTest("no sitemap built yet")
        cls.xml = read()

    def test_it_names_the_live_site(self):
        """A sitemap listing another host is one a crawler discards whole."""
        hosts = set(re.findall(r"<loc>https://([^/]+)/", self.xml))
        self.assertEqual(hosts, {"thebookandme.com"}, sorted(hosts))

    def test_the_offline_copy_is_not_in_it(self):
        """robots.txt disallows the 13 MB single-file build. Listing it in the
        sitemap while disallowing it in robots is the site contradicting
        itself, which is the one thing this project holds itself to."""
        self.assertNotIn("/the-book.html", self.xml)


if __name__ == "__main__":
    unittest.main()
