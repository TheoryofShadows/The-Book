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
    return chapter.get("verses") or chapter.get("v") or []


class WhereTheFilesAre(unittest.TestCase):
    """Skipped where there is no render: this describes dist/, which is not
    committed and is not present in a fresh checkout or in CI."""

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(AUDIO):
            raise unittest.SkipTest("no rendered audio here")
        cls.any = any(f.endswith(".opus")
                      for _, _, fs in os.walk(AUDIO) for f in fs)
        if not cls.any:
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
                if not name.endswith(".opus"):
                    continue
                stem = name[:-5]
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
        for wid, work in works():
            for idx, chapter in enumerate(work.get("chapters", [])):
                meta = os.path.join(AUDIO, wid, "%d.json" % idx)
                if not os.path.exists(meta):
                    continue
                with open(meta, encoding="utf-8") as fh:
                    index = json.load(fh)
                want = len(verses(chapter))
                got = len(index.get("v", []))
                if want != got:
                    wrong.append("%s/%d: text has %d verses, audio has %d"
                                 % (wid, idx, want, got))
        self.assertEqual(wrong, [], wrong[:8])

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
        be reached, and the sign of an index built against different audio."""
        bad = []
        for dirpath, _, names in os.walk(AUDIO):
            for name in sorted(names):
                if not name.endswith(".json"):
                    continue
                with open(os.path.join(dirpath, name), encoding="utf-8") as fh:
                    index = json.load(fh)
                d = index.get("d", 0)
                for v in index.get("v", []):
                    if v[2] > d + 1:
                        bad.append("%s/%s verse %s ends %.1fs into a %.1fs file"
                                   % (os.path.basename(dirpath), name, v[0],
                                      v[2], d))
                        break
        self.assertEqual(bad, [], bad[:6])


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
