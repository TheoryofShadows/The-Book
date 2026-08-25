#!/usr/bin/env python3
"""What may be claimed about a recording, and what the build refuses.

The recorded reading is the one feature of this volume whose failure mode is
silence. A wrong verse offset is audible; a recording attached to the wrong
translation is audible; a manifest promising audio that was never uploaded is
not audible at all, and that is exactly the state the site shipped in for
months.

So the manifest is not written from a list. tools/build_readings.py derives it
from the offsets on disk, and refuses to write anything at all when a claim in
those offsets does not hold. These are the refusals.

The one worth naming is the edition check. A reading of the King James
attached to the World English Bible text, or Charles Taylor's Hermas attached
to the Ante-Nicene Fathers text, is not a small error -- the words are
different words and no alignment between them exists. It is also the easiest
error to make, because the catalogue entry looks right: the LibriVox recording
titled "Apocrypha" is Plato's. build_canon.py already refuses to record an
absence without a citation; this is the same rule pointed at a recording.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import _tools  # noqa: F401

import readings

ROOT = _tools.ROOT
SCRIPT = os.path.join(_tools.TOOLS, "build_readings.py")


def run(out_dir):
    """build_readings.py against a docs tree; (exit code, output)."""
    p = subprocess.run([sys.executable, SCRIPT, out_dir],
                       capture_output=True, text=True, cwd=ROOT)
    return p.returncode, p.stdout + p.stderr


class Tree:
    """The smallest docs/ that build_readings.py will look at."""

    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="readings-")
        data = os.path.join(self.dir, "data")
        os.makedirs(os.path.join(data, "works"))
        os.makedirs(os.path.join(data, "audio"))
        self.write("data/manifest.json", {
            "sections": [{"id": "s", "works": [
                {"id": "amos"}, {"id": "jubilees"}]}]})
        self.write("data/works/amos.json", {"id": "amos", "source": "web"})
        self.write("data/works/jubilees.json",
                   {"id": "jubilees", "source": "charles"})

    def write(self, rel, obj):
        path = os.path.join(self.dir, rel)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)

    def index(self, work, **over):
        body = {"reading": "web-altman", "src": work + ".opus",
                "d": 100.0, "gap": 0.4,
                "c": [[0, 50], [50, 100]],
                "v": {"0": [[1, 0, 20]], "1": [[1, 50, 70]]}}
        body.update(over)
        self.write("data/audio/" + work + ".json", body)

    def manifest(self):
        with open(os.path.join(self.dir, "data", "audio.json"),
                  encoding="utf-8") as fh:
            return json.load(fh)

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class NothingPublished(unittest.TestCase):
    """The honest empty state, which is not a failure."""

    def setUp(self):
        self.t = Tree()
        self.addCleanup(self.t.close)

    def test_it_writes_an_empty_manifest_and_succeeds(self):
        code, out = run(self.t.dir)
        self.assertEqual(code, 0, out)
        got = self.t.manifest()
        self.assertEqual(got["base"], "")
        self.assertEqual(got["works"], {})

    def test_the_empty_manifest_says_what_it_means(self):
        run(self.t.dir)
        self.assertIn("no recorded voice", self.t.manifest()["note"])


class AGoodClaim(unittest.TestCase):

    def setUp(self):
        self.t = Tree()
        self.addCleanup(self.t.close)
        self.t.index("amos")

    def test_it_reaches_the_manifest(self):
        code, out = run(self.t.dir)
        self.assertEqual(code, 0, out)
        self.assertIn("amos", self.t.manifest()["works"])

    def test_and_carries_the_narrator_to_credit(self):
        run(self.t.dir)
        entry = self.t.manifest()["works"]["amos"]
        self.assertEqual(entry["narrator"],
                         readings.READINGS["web-altman"]["narrator"])
        self.assertTrue(entry["licence"])
        self.assertTrue(entry["url"].startswith("http"))

    def test_and_the_release_is_named_only_when_there_is_something_in_it(self):
        run(self.t.dir)
        self.assertTrue(self.t.manifest()["base"].startswith("https://"))


class ClaimsTheBuildRefuses(unittest.TestCase):
    """Every one of these must stop the build rather than warn."""

    def setUp(self):
        self.t = Tree()
        self.addCleanup(self.t.close)

    def assertRefused(self, needle):
        code, out = run(self.t.dir)
        self.assertEqual(code, 1, "the build should have refused:\n" + out)
        self.assertIn("BROKEN", out)
        self.assertIn(needle, out)
        self.assertFalse(
            os.path.exists(os.path.join(self.t.dir, "data", "audio.json")),
            "a refused build must not leave a manifest behind")

    def test_a_recording_of_the_wrong_translation(self):
        """The heart of it. web-altman reads the World English Bible;
        jubilees prints Charles. Same volume, different English."""
        self.t.index("jubilees")           # defaults to the WEB reading
        self.assertRefused("different words")

    def test_a_work_that_does_not_exist(self):
        self.t.index("nazareth-gospel")
        self.assertRefused("no such work")

    def test_a_reading_nobody_has_recorded(self):
        self.t.index("amos", reading="web-someone-imagined")
        self.assertRefused("does not list")

    def test_an_asset_name_that_could_not_be_a_release_asset(self):
        """Release asset names are flat. A src with a slash names a path that
        cannot exist, so the audio would 404 for every reader."""
        self.t.index("amos", src="amos/0.opus")
        self.assertRefused("flat")

    def test_offsets_for_a_chapter_with_no_span(self):
        self.t.index("amos", v={"0": [[1, 0, 20]], "7": [[1, 0, 5]]})
        self.assertRefused("no span")

    def test_offsets_that_are_not_keyed_by_chapter(self):
        self.t.index("amos", v={"Chapter 1": [[1, 0, 20]]})
        self.assertRefused("not a chapter index")


class TheRegistryItself(unittest.TestCase):

    def test_every_reading_states_its_edition_rights_and_source(self):
        for key, r in readings.READINGS.items():
            for field in ("narrator", "reads", "edition", "url", "licence",
                          "rights", "why"):
                self.assertTrue(str(r.get(field, "")).strip(),
                                "%s has no %s" % (key, field))
            self.assertTrue(r["url"].startswith("https://"), key)

    def test_every_rejected_recording_says_why(self):
        """A recording turned down without a reason is an opinion, and the
        next person to find it in the catalogue will add it again."""
        for key, why in readings.REJECTED.items():
            self.assertGreater(len(why), 40,
                               "%s is rejected without a real reason" % key)

    def test_the_editions_named_are_editions_this_volume_prints(self):
        """A reading of an edition no work here carries could never attach to
        anything, and is a sign the registry and the corpus have drifted."""
        with open(os.path.join(ROOT, "docs", "data", "manifest.json"),
                  encoding="utf-8") as fh:
            sources = set(json.load(fh).get("sources") or {})
        for key, r in readings.READINGS.items():
            self.assertIn(r["edition"], sources,
                          "%s reads an edition the volume does not print" % key)


if __name__ == "__main__":
    unittest.main()
