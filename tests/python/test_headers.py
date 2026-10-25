"""The response headers the deploy sends, and whether they agree with the policy in the pages.

tools/deploy_cloudflare.py writes the _headers file. The home page carries a
Content-Security-Policy <meta>; the header must allow at least everything that one allows
(both are enforced together, so a header narrower than the page would break the page), and it
adds frame-ancestors, which a <meta> cannot carry.
"""
import os
import re
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import deploy_cloudflare  # noqa: E402


def directives(policy):
    out = {}
    for part in policy.split(";"):
        bits = part.split()
        if bits:
            out[bits[0]] = set(bits[1:])
    return out


class TheHeaders(unittest.TestCase):
    def setUp(self):
        self.h = deploy_cloudflare.HEADERS

    def test_hsts_is_six_months_without_subdomains_or_preload(self):
        m = re.search(r"Strict-Transport-Security: (.+)", self.h)
        self.assertTrue(m)
        self.assertEqual(m.group(1).strip(), "max-age=15552000")

    def test_framing_is_refused_twice(self):
        self.assertIn("X-Frame-Options: DENY", self.h)
        self.assertIn("frame-ancestors 'none'", self.h)

    def test_permissions_policy_present(self):
        self.assertRegex(self.h, r"Permissions-Policy: .*camera=\(\)")

    def test_header_policy_covers_the_pages_policies(self):
        header = directives(deploy_cloudflare.CSP)
        for rel in ("docs/index.html",):
            with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
                html = fh.read()
            meta = re.search(r'http-equiv="Content-Security-Policy" content="([^"]*)"', html)
            self.assertTrue(meta, rel)
            for name, vals in directives(meta.group(1)).items():
                self.assertIn(name, header, "%s: header lacks %s" % (rel, name))
                self.assertTrue(vals <= header[name],
                                "%s: header narrower than page for %s: %r"
                                % (rel, name, sorted(vals - header[name])))

    def test_the_offline_copy_is_not_given_the_policy(self):
        """It has an inline script, so the header policy would blank it."""
        self.assertRegex(self.h, r"/the-book\.html\n  ! Content-Security-Policy")


if __name__ == "__main__":
    unittest.main()
