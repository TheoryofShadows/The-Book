#!/usr/bin/env python3
"""The rendered audio, at the addresses the reader actually asks for.

This exists because of a bug that every other check passed.

tools/render_audio.py named each file after chapter["n"], the printed chapter
number. docs/assets/app.js builds its address from the chapter's position in
the array: #/read/psalms/22 is the twenty-third chapter and fetches
psalms/22.opus. Those two agree only when a work's first chapter is numbered
zero, and none of them are.

So every file sat one place off. Tapping Psalm 23 played Psalm 22 -- in a
good voice, with the verse marks landing exactly where they should, because
the file was internally perfect. The last chapter of every book fetched a
file that was not there and fell back to the device voice. Nothing looked
broken from any angle: the renderer's own log was right, the file count was
plausible, and the live checker passed because it was pointed at a filename
rather than at an address.

A wrong chapter that plays confidently is worse than silence. These are the
checks that would have caught it, and they are all the same question asked
of the layout rather than of the audio: does the file at the address the
reader will use hold the chapter the reader asked for.
"""

import json
import os
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    os.pardir, os.pardir)
WORKS = os.path.join(ROOT, "docs", "data", "works")
AUDIO = os.path.join(ROOT, "dist", "audio")


def works():
    for name in sorted(os.listdir(WORKS)):
        if name.endswith(".json"):
            with open(os.path.join(WORKS, name), encoding="utf-8") as fh:
                yield name[:-5], json.load(fh)


def verses(chapter):
    """What the renderer counts as verses, spelt the way it spells it.

    render_chapter reads chapter["verses"] and nothing else, so a test that
    also accepted a "v" key would demand audio for chapters the renderer
    deliberately skips, and fail against correct output.
    """
    return chapter.get("verses", [])


class WhereTheFilesAre(unittest.TestCase):
    """Skipped where there is no render: this describes dist/, which is not
    committed and is not present in a fresh checkout or in CI."""

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(AUDIO):
            raise unittest.SkipTest("no rendered audio here")
        if not any(f.endswith(".opus")
                   for _, _, fs in os.walk(AUDIO) for f in fs):
            raise unittest.SkipTest("no rendered audio here")

    def test_a_chapter_with_audio_has_it_at_its_index(self):
        """The bug, stated as a rule.

        Every .opus in a work's folder must be named for a position in that
        work's chapter array. A file named for a chapter number is the
        failure this file is about, and on any real work the two differ.
        """
        stray = []
        for wid, work in works():
            folder = os.path.join(AUDIO, wid)
            if not os.path.isdir(folder):
                continue
            count = len(work.get("chapters", []))
            for name in os.listdir(folder):
                # Both halves, not just the audio: a misnamed pair is
                # internally consistent, so the pairing test cannot see it and
                # only this can -- and it could only see half of it while it
                # filtered on .opus.
                if name.endswith(".opus"):
                    stem = name[:-5]
                elif name.endswith(".json"):
                    stem = name[:-5]
                else:
                    continue
                if not stem.isdigit() or int(stem) >= count:
                    stray.append("%s/%s" % (wid, name))
        self.assertEqual(stray, [],
                         "audio at an address no chapter has: %s"
                         % stray[:8])

    def test_the_index_beside_it_matches_that_chapter(self):
        """The check that would have caught it on its own.

        The verse count in the rendered index has to equal the verse count of
        the chapter at that address. Off-by-one survives every other test --
        the audio is fine, the offsets are fine, the file is fine -- and dies
        here, because chapter 23 does not have chapter 22's number of verses.
        """
        wrong = []
        checked = 0
        for wid, work in works():
            for idx, chapter in enumerate(work.get("chapters", [])):
                meta = os.path.join(AUDIO, wid, "%d.json" % idx)
                if not os.path.exists(meta):
                    continue
                checked += 1
                with open(meta, encoding="utf-8") as fh:
                    index = json.load(fh)
                want = len(verses(chapter))
                got = len(index.get("v", []))
                if want != got:
                    wrong.append("%s/%d: text has %d verses, audio has %d"
                                 % (wid, idx, want, got))
        self.assertEqual(wrong, [], wrong[:8])
        # Without this the test passes by checking nothing: a render named
        # wholly by chapter number leaves no <idx>.json at any expected
        # address, every chapter is skipped, and the cross-check the test
        # exists for never runs.
        self.assertGreater(checked, 1000,
                           "only %d indexes were at an address to check; a "
                           "render named some other way would pass this test "
                           "by being absent from it" % checked)

    def test_every_chapter_with_verses_has_audio(self):
        """A chapter the reader can open and cannot hear.

        Chapters with no verses are prose held as paragraphs and are skipped
        by the renderer on purpose, so they are not counted here.
        """
        silent = []
        for wid, work in works():
            for idx, chapter in enumerate(work.get("chapters", [])):
                if not verses(chapter):
                    continue
                if not os.path.exists(os.path.join(AUDIO, wid,
                                                   "%d.opus" % idx)):
                    silent.append("%s/%d" % (wid, idx))
        self.assertEqual(silent, [],
                         "%d chapter(s) have verses and no audio: %s"
                         % (len(silent), silent[:8]))

    def test_audio_and_index_come_in_pairs(self):
        """Audio with no index has no verse marks; an index with no audio is
        a promise of a file that is not there."""
        odd = []
        for dirpath, _, names in os.walk(AUDIO):
            for name in names:
                if name.endswith(".opus"):
                    if not os.path.exists(os.path.join(dirpath,
                                                       name[:-5] + ".json")):
                        odd.append(os.path.join(dirpath, name))
                elif name.endswith(".json"):
                    if not os.path.exists(os.path.join(dirpath,
                                                       name[:-5] + ".opus")):
                        odd.append(os.path.join(dirpath, name))
        self.assertEqual(odd, [], odd[:8])

    def test_no_verse_ends_after_the_file_does(self):
        """An offset past the end of the audio is a verse mark that can never
        be reached, and the sign of an index built against different audio.

        The tolerance was a full second, which is slack this has no use for:
        the renderer appends GAP after the last verse, so the real margin is
        -0.35 on every one of the 1,559 indexes and the largest measured
        overrun is negative. A second of grace meant a verse could end 1.35s
        past the end of its file and still pass, which is most of the failure
        this is here to catch.
        """
        bad = []
        for dirpath, _, names in os.walk(AUDIO):
            for name in sorted(names):
                if not name.endswith(".json"):
                    continue
                with open(os.path.join(dirpath, name), encoding="utf-8") as fh:
                    index = json.load(fh)
                d = index.get("d", 0)
                for v in index.get("v", []):
                    if v[2] > d + 0.05:   # float slop only
                        bad.append("%s/%s verse %s ends %.1fs into a %.1fs file"
                                   % (os.path.basename(dirpath), name, v[0],
                                      v[2], d))
                        break
        self.assertEqual(bad, [], bad[:6])


class TheNumberingItReplaced(unittest.TestCase):
    """Why the fix could not be "subtract one".

    Nineteen works do not number their chapters 1..len. The split prophets
    keep the numbering of the book they came from, so Second Isaiah starts at
    40 and the Astronomical Book at 72; a work extracted as a single chapter
    carries that chapter's number, so Bel and the Dragon is 14; and Jubilees
    starts at 0, where n and the index already agreed.

    An off-by-one fix that shifted every file by one would have been right for
    most of the library and badly wrong for those -- Second Isaiah 40 becoming
    chapter 39 of a work that has sixteen. The mapping has to be from n to the
    position n actually sits at, which is what this asserts is still true of
    the data the renderer reads.
    """

    def test_chapter_numbers_are_not_always_their_index_plus_one(self):
        odd = []
        for wid, work in works():
            ns = [ch["n"] for ch in work.get("chapters", [])]
            if ns and ns != list(range(1, len(ns) + 1)):
                odd.append(wid)
        self.assertGreater(len(odd), 0,
                           "if every work were numbered 1..len this test is "
                           "pointless, but the split works are not")

    def test_no_work_numbers_two_chapters_the_same(self):
        """A duplicate n would make any n-keyed mapping lossy, which is how a
        rename silently overwrites a chapter."""
        for wid, work in works():
            ns = [ch["n"] for ch in work.get("chapters", [])]
            self.assertEqual(len(ns), len(set(ns)),
                             "%s numbers a chapter twice" % wid)


class WhatTheRendererWillDo(unittest.TestCase):
    """The rule, checked in the script rather than only in its output, so a
    fresh render cannot reintroduce it."""

    def test_the_renderer_names_files_by_index(self):
        path = os.path.join(ROOT, "tools", "render_audio.py")
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn('str(chapter["n"])', src,
                         "render_audio.py is naming files by chapter number "
                         "again, which puts every file one place off from the "
                         "address the reader uses")
        self.assertIn("str(idx)", src)


if __name__ == "__main__":
    unittest.main()
