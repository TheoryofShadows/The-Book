#!/usr/bin/env python3
"""The sweep that reads the recordings can actually tell a bad one.

tools/audit_audio.py swept 1,559 chapters and flagged nothing. That is the
right answer -- it was checked against injected faults before it was believed
-- but a check which has only ever said "fine" is indistinguishable from one
that cannot say anything else, and it stays that way until somebody proves
otherwise. This is that proof, kept.

Each case builds a small fixture with one thing wrong with it and asks
whether that one thing is found. The Opus payload is real audio taken from
the corpus, because the duration is read out of the Ogg framing and a
made-up file would not have any.

What is deliberately not here: whether the reading sounds right. The sweep
does not claim to know, and neither does this.
"""

import io
import json
import os
import shutil
import struct
import tempfile
import unittest

from _tools import ROOT  # noqa: F401  (puts tools/ on the path)
import audit_audio

CORPUS = os.path.join(ROOT, "dist", "audio")


def a_real_chapter():
    """One rendered chapter to build fixtures out of, or None."""
    if not os.path.isdir(CORPUS):
        return None
    for work in sorted(os.listdir(CORPUS)):
        wdir = os.path.join(CORPUS, work)
        if not os.path.isdir(wdir):
            continue
        for f in sorted(os.listdir(wdir)):
            if f.endswith(".opus"):
                side = os.path.join(wdir, f[:-5] + ".json")
                if os.path.exists(side):
                    return os.path.join(wdir, f), side
    return None


class AuditFindsFaults(unittest.TestCase):
    """Every fault the sweep claims to find, injected and found."""

    @classmethod
    def setUpClass(cls):
        cls.sample = a_real_chapter()

    def setUp(self):
        if not self.sample:
            self.skipTest("no rendered audio here to build a fixture from")
        self.dir = tempfile.mkdtemp(prefix="audit-")
        self.audio = os.path.join(self.dir, "dist", "audio", "w")
        self.works = os.path.join(self.dir, "docs", "data", "works")
        os.makedirs(self.audio)
        os.makedirs(self.works)
        self.opus, self.side = self.sample
        with io.open(self.side, encoding="utf-8") as fh:
            self.meta = json.load(fh)

        # A source work whose verse count matches the sidecar, so a mismatch
        # is something a case introduces rather than the fixture's own noise.
        verses = [{"t": "word " * 40} for _ in self.meta["v"]]
        with io.open(os.path.join(self.works, "w.json"), "w",
                     encoding="utf-8") as fh:
            json.dump({"id": "w", "chapters": [{"verses": verses}]}, fh)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def chapter(self, idx, meta=None, payload=None):
        """Write chapter idx into the fixture, optionally damaged."""
        dst = os.path.join(self.audio, "%d.opus" % idx)
        if payload is None:
            shutil.copyfile(self.opus, dst)
        else:
            with io.open(dst, "wb") as fh:
                fh.write(payload)
        if meta is not None:
            with io.open(os.path.join(self.audio, "%d.json" % idx), "w",
                         encoding="utf-8") as fh:
                json.dump(meta, fh)

    def sweep(self):
        """Run the audit over the fixture and return (rows, broken)."""
        here = os.getcwd()
        os.chdir(self.dir)
        try:
            return audit_audio.audit()
        finally:
            os.chdir(here)

    def faults_on(self, idx):
        rows, _ = self.sweep()
        for r in rows:
            if r["key"] == "w/%d" % idx:
                return "; ".join(r["faults"])
        return None

    # ---- the duration is read out of the file, not off the sidecar ----

    def test_duration_comes_from_the_audio(self):
        """The granule reading agrees with what the renderer recorded."""
        secs, err = audit_audio.ogg_duration(self.opus)
        self.assertIsNone(err, err)
        self.assertAlmostEqual(secs, self.meta["d"], places=2,
                               msg="the duration read out of the Ogg framing "
                                   "should match the sidecar on a good file")

    # ---- files that are not playable at all ----

    def test_a_file_that_is_not_ogg_is_unreadable(self):
        self.chapter(0, self.meta, payload=b"this is not audio")
        _, broken = self.sweep()
        self.assertEqual([b[0] for b in broken], ["w/0"])
        self.assertIn("not an Ogg", broken[0][1])

    def test_an_empty_file_is_unreadable(self):
        self.chapter(0, self.meta, payload=b"")
        _, broken = self.sweep()
        self.assertEqual(len(broken), 1)

    def test_a_truncated_file_is_caught(self):
        """Half a file still starts with OggS, which is the trap."""
        with io.open(self.opus, "rb") as fh:
            half = fh.read(4000)
        self.chapter(0, self.meta, payload=half)
        rows, broken = self.sweep()
        # Either it has no final page, or it decodes far shorter than the
        # sidecar claims. Both are findings; silence is not.
        self.assertTrue(broken or "audio is" in (self.faults_on(0) or ""),
                        "a truncated file must not pass as fine")

    # ---- the sidecar disagreeing with the audio ----

    def test_a_duration_that_lies_is_caught(self):
        meta = json.loads(json.dumps(self.meta))
        meta["d"] = self.meta["d"] + 45.0
        self.chapter(0, meta)
        self.assertIn("offsets claim", self.faults_on(0) or "")

    def test_verses_starting_after_the_end_are_caught(self):
        meta = json.loads(json.dumps(self.meta))
        meta["v"][-1][1] = self.meta["d"] + 30.0
        meta["v"][-1][2] = self.meta["d"] + 40.0
        self.chapter(0, meta)
        self.assertIn("after the audio ends", self.faults_on(0) or "")

    def test_overlapping_verses_are_caught(self):
        meta = json.loads(json.dumps(self.meta))
        if len(meta["v"]) < 3:
            self.skipTest("needs a chapter with a few verses")
        meta["v"][2][1] = float(meta["v"][1][1])  # starts inside the one before
        self.chapter(0, meta)
        self.assertIn("overlap", self.faults_on(0) or "")

    def test_a_verse_ending_before_it_starts_is_caught(self):
        meta = json.loads(json.dumps(self.meta))
        meta["v"][0][1], meta["v"][0][2] = 10.0, 2.0
        self.chapter(0, meta)
        self.assertIn("ends before it starts", self.faults_on(0) or "")

    # ---- the two faults this repository has already had once ----

    def test_lead_in_silence_is_caught(self):
        """Fixed once already, so the check for it is kept."""
        meta = json.loads(json.dumps(self.meta))
        meta["v"][0][1] = 9.0
        self.chapter(0, meta)
        self.assertIn("before the first verse", self.faults_on(0) or "")

    def test_a_long_tail_of_nothing_is_caught(self):
        meta = json.loads(json.dumps(self.meta))
        for row in meta["v"]:
            row[1], row[2] = 0.0, 0.5
        self.chapter(0, meta)
        self.assertIn("after the last verse", self.faults_on(0) or "")

    # ---- the text and the recording disagreeing ----

    def test_a_missing_offsets_file_is_caught(self):
        self.chapter(0, None)
        self.assertIn("no offsets", self.faults_on(0) or "")

    def test_offsets_that_do_not_match_the_text_are_caught(self):
        meta = json.loads(json.dumps(self.meta))
        meta["v"] = meta["v"][:1]
        if len(self.meta["v"]) < 2:
            self.skipTest("needs a chapter with more than one verse")
        self.chapter(0, meta)
        self.assertIn("in the text", self.faults_on(0) or "")

    # ---- the second encoding, which is what the iPhone actually plays ----

    def test_an_m4a_of_the_wrong_length_is_caught(self):
        """Both encodings share one sidecar, so both must match it.

        An m4a that came out a different length would put every verse mark
        wrong on every iPhone while a desktop, playing the Opus, showed
        nothing amiss at all.
        """
        self.chapter(0, self.meta)
        # Stand in a longer piece of audio for this chapter's m4a. Any real
        # mp4 will do; what is under test is the length disagreeing.
        other = None
        for work in sorted(os.listdir(CORPUS)):
            wdir = os.path.join(CORPUS, work)
            if not os.path.isdir(wdir):
                continue
            for f in sorted(os.listdir(wdir)):
                if f.endswith(".m4a"):
                    d, err = audit_audio.m4a_duration(os.path.join(wdir, f))
                    if not err and abs(d - self.meta["d"]) > 5:
                        other = os.path.join(wdir, f)
                        break
            if other:
                break
        if not other:
            self.skipTest("no m4a of a clearly different length to stand in")
        shutil.copyfile(other, os.path.join(self.audio, "0.m4a"))
        self.assertIn("m4a is", self.faults_on(0) or "")

    def test_a_matching_m4a_raises_nothing(self):
        """And the pair as rendered is accepted."""
        src_m4a = self.opus[:-5] + ".m4a"
        if not os.path.exists(src_m4a):
            self.skipTest("this chapter has not been transcoded")
        self.chapter(0, self.meta)
        shutil.copyfile(src_m4a, os.path.join(self.audio, "0.m4a"))
        self.assertEqual(self.faults_on(0), "",
                         "an m4a the same length as its opus is not a fault")

    def test_an_m4a_that_is_not_an_mp4_is_caught(self):
        self.chapter(0, self.meta)
        with io.open(os.path.join(self.audio, "0.m4a"), "wb") as fh:
            fh.write(b"not an mp4 at all")
        self.assertIn("m4a is unreadable", self.faults_on(0) or "")

    # ---- a good chapter is left alone ----

    def test_an_undamaged_chapter_raises_nothing(self):
        """The other half of the bargain: no crying wolf."""
        self.chapter(0, self.meta)
        rows, broken = self.sweep()
        self.assertEqual(broken, [])
        self.assertEqual(rows[0]["faults"], [],
                         "an untouched chapter should pass every check")


if __name__ == "__main__":
    unittest.main()
