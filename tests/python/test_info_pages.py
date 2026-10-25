#!/usr/bin/env python3
"""The about, contact, privacy and press pages say what is true.

They are built by tools/build_pages.py. What is held here is the part a
reader would be misled by: the voice is called synthetic, every page names its
own canonical address, the organisation points at the three channels, and no
address is published before mail to it works.
"""

import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, os.pardir, "tools"))
import build_pages                                              # noqa: E402

DOCS = os.path.join(HERE, os.pardir, os.pardir, "docs")


class InfoPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(DOCS, "data", "manifest.json"), encoding="utf-8") as fh:
            manifest = json.load(fh)
        cls.out = tempfile.mkdtemp()
        cls.urls = build_pages.info_pages(manifest, cls.out)
        cls.html = {}
        for slug in build_pages.INFO_PAGES:
            with open(os.path.join(cls.out, slug, "index.html"), encoding="utf-8") as fh:
                cls.html[slug] = fh.read()

    def test_four_pages_each_with_its_own_canonical(self):
        self.assertEqual(len(self.urls), 4)
        for slug, url in zip(build_pages.INFO_PAGES, self.urls):
            self.assertEqual(url, "https://thebookandme.com/%s/" % slug)
            self.assertIn('<link rel="canonical" href="%s">' % url, self.html[slug])

    def test_the_voice_is_called_synthetic_where_it_is_described(self):
        for slug in ("about", "press"):
            self.assertRegex(self.html[slug], r"AI-generated|synthetic")
            flat = " ".join(self.html[slug].split()).lower()
            self.assertIn("no human narrator", flat)
        self.assertNotRegex(self.html["about"].lower(), r"real recorded audio|human voice")

    def test_organisation_points_at_the_three_channels(self):
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>',
                      self.html["about"], re.S)
        graph = json.loads(m.group(1))["@graph"]
        org = [n for n in graph if n["@type"] == "Organization"][0]
        self.assertEqual(org["name"], "OpenPrints")
        self.assertEqual(org["brand"]["name"], "The Book and Me")
        # a name and nothing else: no invented address, staff or claims
        for banned in ("address", "founder", "employee", "telephone", "foundingDate", "award"):
            self.assertNotIn(banned, org)
        for slug in ("about", "press"):
            self.assertIn("OpenPrints", self.html[slug])
        self.assertEqual(sorted(org["sameAs"]), sorted([
            "https://www.youtube.com/@thebookandme",
            "https://www.twitch.tv/xtheorx",
            "https://kick.com/jonesproject"]))

    def test_no_address_is_published_until_it_is_set(self):
        if build_pages.CONTACT_EMAIL is None:
            for slug, text in self.html.items():
                self.assertNotIn("mailto:", text)
                self.assertNotIn("@thebookandme.com", text)

    def test_privacy_matches_what_is_live(self):
        text = self.html["privacy"]
        self.assertIn("cookie-less", text)
        self.assertIn("Cloudflare Web Analytics", text)
        # Accounts are optional; the page must say what is stored, for how
        # long, and how to delete it.
        self.assertIn("Optional accounts", text)
        self.assertIn("tbm_session", text)
        self.assertIn("Delete my account and data", text)
        self.assertIn("90 days", text)
        self.assertIn("Resend", text)
        self.assertNotIn("no accounts", text.lower())

    def test_no_health_claims(self):
        for text in self.html.values():
            self.assertNotRegex(text.lower(), r"\b(cures?|heals?|treats?)\b")


if __name__ == "__main__":
    unittest.main()
