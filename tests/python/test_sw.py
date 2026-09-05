#!/usr/bin/env python3
"""The service worker generator: the stamp, and the promise it is under.

Two things are checked here and neither is about caching working, which is a
browser question and is asked in tests/offline.test.js instead.

The first is the stamp. It exists so that a deploy which changes anything the
worker serves changes the worker's own bytes, because that is the only event
a browser treats as a new worker, and the activate step keys its cache
purging off it. A stamp that did not move when the data moved would leave a
reader on a cache from a parse that no longer exists, with nothing anywhere
reporting it -- so it is checked that it moves, and that it comes back, and
that building twice writes the same file.

The second is the refusal. The worker is network-first with no timeout and no
stale-while-revalidate, and that is not a detail of the implementation, it is
the reason this is allowed to exist at all on a volume that publishes an
accuracy audit. A later hand adding a "serve the cache if the network takes
more than two seconds" would make the site faster and would make it capable
of showing somebody yesterday's chapter while they hold a working phone.
There is no test that can read intent, so this reads the source for the
shapes that trade freshness for speed and refuses them by name.
"""

import os
import re
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_sw  # noqa: E402


def worker(root):
    """Build into a scratch copy and hand back the text, so nothing here
    depends on docs/sw.js having been built and none of it writes to docs."""
    build_sw.build(root)
    with open(os.path.join(root, "sw.js"), encoding="utf-8") as fh:
        return fh.read()


class TheStamp(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.docs = os.path.join(self.tmp, "docs")
        shutil.copytree(
            os.path.join(ROOT, "docs"), self.docs,
            ignore=shutil.ignore_patterns("read", "contents", "the-book.html"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_building_twice_writes_the_same_file(self):
        """Or every rebuild is a diff, and the diff stops being read."""
        first = worker(self.docs)
        self.assertEqual(first, worker(self.docs))

    def test_it_moves_when_the_data_moves(self):
        before = build_sw.stamp(self.docs)
        path = os.path.join(self.docs, "data", "manifest.json")
        with open(path, "ab") as fh:
            fh.write(b" ")
        self.assertNotEqual(before, build_sw.stamp(self.docs))

    def test_it_moves_when_the_reader_moves(self):
        before = build_sw.stamp(self.docs)
        path = os.path.join(self.docs, "assets", "app.js")
        with open(path, "ab") as fh:
            fh.write(b"\n")
        self.assertNotEqual(before, build_sw.stamp(self.docs))

    def test_it_comes_back(self):
        """A hash of content and not of the clock: undo the change, get the
        stamp back. Without this the check above would also pass for a
        timestamp, which would rebuild the worker on every deploy and evict
        every reader's cache for nothing."""
        path = os.path.join(self.docs, "assets", "app.css")
        with open(path, "rb") as fh:
            original = fh.read()
        before = build_sw.stamp(self.docs)
        with open(path, "ab") as fh:
            fh.write(b"\n/* touched */\n")
        self.assertNotEqual(before, build_sw.stamp(self.docs))
        with open(path, "wb") as fh:
            fh.write(original)
        self.assertEqual(before, build_sw.stamp(self.docs))

    def test_a_rename_alone_moves_it(self):
        """The path is hashed as well as the bytes. Two files swapping names
        with their content untouched is a different site."""
        before = build_sw.stamp(self.docs)
        works = os.path.join(self.docs, "data", "works")
        names = sorted(os.listdir(works))[:1]
        os.rename(os.path.join(works, names[0]),
                  os.path.join(works, "renamed-" + names[0]))
        self.assertNotEqual(before, build_sw.stamp(self.docs))

    def test_the_worker_carries_the_stamp_it_was_built_with(self):
        text = worker(self.docs)
        found = re.search(r'var VERSION = "([0-9a-f]+)"', text)
        self.assertIsNotNone(found, "the worker states no version")
        self.assertEqual(found.group(1), build_sw.stamp(self.docs))


def strip_comments(js):
    """Comments out, so the checks below read code and not prose about it.

    The generator's own docstring names the strategies it refuses, and the
    first version of this file scanned that docstring and failed on the
    sentence explaining why the thing was not there. What ships is the
    worker, so what is read is the worker.
    """
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return re.sub(r"^\s*//.*$", "", js, flags=re.M)


class ItStaysNetworkFirst(unittest.TestCase):
    """The one property the whole thing is allowed to exist for."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        docs = os.path.join(self.tmp, "docs")
        shutil.copytree(
            os.path.join(ROOT, "docs"), docs,
            ignore=shutil.ignore_patterns("read", "contents", "the-book.html"))
        self.source = strip_comments(worker(docs))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_cache_is_never_raced_against_the_network(self):
        """Named shapes, because each of them is a real and popular answer.

        Every one of these makes a site faster by being willing to hand back
        something older than what the server has. That is the trade this
        worker exists not to make, so it is refused by name rather than left
        to whoever reads the file next.
        """
        for banned in ("stale-while-revalidate", "staleWhileRevalidate",
                       "cacheFirst", "cache-first", "networkTimeout",
                       "timeoutSeconds"):
            self.assertNotIn(
                banned, self.source,
                f"{banned} trades freshness for speed; this worker does not")

    def test_the_fetch_handler_asks_the_network_before_the_cache(self):
        """caches.match appearing before fetch in the handler would be the
        same trade written by hand, and would read as an ordinary line."""
        handler = self.source.split('addEventListener("fetch"', 1)[1]
        body = handler.split("respondWith", 1)[1]
        self.assertLess(
            body.index("fetch(req)"), body.index("caches.match"),
            "the cache is consulted before the network")

    def test_only_a_real_answer_is_kept(self):
        """A 404 or a redirect put in the cache is served back offline as
        though it were the page somebody asked for."""
        self.assertIn("res.status === 200", self.source)

    def test_the_twelve_megabyte_copy_is_not_cached(self):
        """One navigation to it would cost more storage than every chapter a
        reader will open. robots.txt keeps crawlers off it; this keeps it out
        of a phone."""
        self.assertIn("/the-book.html", self.source)


class TheRegistrationIsSafeWhereItRuns(unittest.TestCase):

    def setUp(self):
        with open(os.path.join(ROOT, "docs", "assets", "sw-register.js"),
                  encoding="utf-8") as fh:
            self.source = fh.read()
        with open(os.path.join(ROOT, "docs", "index.html"),
                  encoding="utf-8") as fh:
            self.index = fh.read()

    def test_it_checks_before_it_registers(self):
        """No worker at all is ordinary -- an older browser, or plain http
        from anywhere that is not localhost -- and is not an error."""
        self.assertIn('"serviceWorker" in navigator', self.source)

    def test_it_is_loaded_from_the_head(self):
        """tools/build_standalone.py keeps only the body of index.html, so a
        tag in the head is dropped from the single-file copy. That copy opens
        from file://, where there is no worker to register: this is what
        stops it throwing on every open of the one build nobody watches.
        """
        head = self.index.split("</head>", 1)[0]
        self.assertIn("assets/sw-register.js", head)
        body = self.index.split("<body>", 1)[1]
        self.assertNotIn("sw-register.js", body)

    def test_the_offline_notice_does_not_overclaim(self):
        """navigator.onLine is coarse -- a captive portal leaves it true --
        so the wording says what is known rather than more than that."""
        self.assertIn("may not be current", self.source)


class TheBuildMakesIt(unittest.TestCase):

    def test_build_sh_builds_the_worker_after_the_data(self):
        """The stamp is a hash of the data, so building it first would ship
        the previous parse's cache key."""
        with open(os.path.join(ROOT, "tools", "build.sh"), encoding="utf-8") as fh:
            sh = fh.read()
        self.assertIn("build_sw.py", sh)
        self.assertLess(sh.index("build_canon.py") if "build_canon.py" in sh
                        else 0, sh.index("build_sw.py"))

    def test_the_deploy_builds_it_too(self):
        """It is gitignored, so if the deploy does not make it the live site
        registers a worker that is not there."""
        with open(os.path.join(ROOT, ".github", "workflows", "pages.yml"),
                  encoding="utf-8") as fh:
            self.assertIn("build_sw.py", fh.read())

    def test_it_is_not_committed(self):
        with open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as fh:
            self.assertIn("docs/sw.js", fh.read())


if __name__ == "__main__":
    unittest.main()
