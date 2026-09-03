#!/usr/bin/env python3
"""The verifier, against text it is supposed to catch.

A checker that has stopped checking passes every build in exactly the way a
working one does, and this is the second time that has happened here: the
audit returned zero whatever it found for long enough to hide three missing
chapters of Ignatius. So verify.py is given a small library with each of the
defects planted in it, and has to find them.

The planted text is the real thing. "[p. 134]" and "[paragraph continues]"
are quoted from 1 Enoch as the transcription actually left them, mid-clause,
which is what made them worth removing and what makes a regression here
worth catching.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import verify  # noqa: E402


def write(folder, name, payload):
    path = os.path.join(folder, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)


class Library:
    """A whole data directory, small enough to reason about."""

    def __init__(self):
        self.dir = tempfile.mkdtemp()
        self.work = {
            "id": "amos", "title": "AMOS", "section": "s", "source": "web",
            "chapters": [{
                "label": "Chapter 1", "n": 1, "style": "verse",
                "verses": [{"v": 1, "t": "The words of Amos."},
                           {"v": 2, "t": "He said: Yahweh will roar from Zion."}],
            }],
        }
        self.manifest = {
            "sections": [{"id": "s", "name": "Section I", "roman": "I",
                          "works": [{"id": "amos", "title": "AMOS", "chapters": 1}]}],
            "sources": {}, "totals": {},
        }
        self.lexicon = {"zion": {"name": "Zion", "text": "The hill.", "refs": []}}
        self.aliases = {"sion": "zion"}
        self.places = {"zion": {"name": "Zion", "kind": "point",
                                "lat": 31.77, "lon": 35.23, "mentions": 1}}
        self.mentions = {"amos/0": ["zion"]}
        self.threads = [{"id": "t", "title": "T",
                         "stops": [{"work": "amos", "chapter": 0}]}]

    def build(self):
        write(self.dir, "manifest.json", self.manifest)
        write(self.dir, os.path.join("works", "amos.json"), self.work)
        write(self.dir, os.path.join("lexicon", "z.json"), self.lexicon)
        write(self.dir, "lexicon-aliases.json", self.aliases)
        write(self.dir, os.path.join("places", "z.json"), self.places)
        write(self.dir, "mentions.json", self.mentions)
        write(self.dir, "threads.json", self.threads)
        return self.dir

    def kinds(self):
        findings, _counts, _places = verify.check(self.build())
        return sorted({f[0] for f in findings})

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TheVerifierFindsWhatIsPlanted(unittest.TestCase):

    def setUp(self):
        self.lib = Library()
        self.addCleanup(self.lib.close)

    def verse(self, text, number=1):
        self.lib.work["chapters"][0]["verses"][number - 1]["t"] = text

    def test_a_clean_library_has_nothing_wrong_with_it(self):
        """The control. Without it every check below could pass by accident."""
        self.assertEqual(self.lib.kinds(), [])

    def test_the_printed_page_number(self):
        """1 Enoch 93:7, as the transcription actually left it."""
        self.verse("The house of glory shall be built for ever. [p. 133]")
        self.assertIn("TEXT-FURNITURE", self.lib.kinds())

    def test_the_transcribers_paragraph_note(self):
        """1 Enoch 83:2. It lands in the middle of the clause."""
        self.verse("And regarding them I prayed to the [paragraph continues] Lord.")
        self.assertIn("TEXT-FURNITURE", self.lib.kinds())

    def test_charles_own_brackets_are_not_furniture(self):
        """The one that must NOT fire.

        Charles supplies words the Ethiopic does not have and marks them with
        square brackets. A rule that took those out would be rewriting the
        translator rather than cleaning up after his scanner.
        """
        self.verse("And they shall bless [and] praise [Him] for ever.")
        self.assertEqual(self.lib.kinds(), [])

    def test_a_clump_the_scanner_invented(self):
        """Apostolic Canons LIV, as Horner's page came out of the scanner."""
        self.verse("that he Seperate ee oe ee ee, wee cone erage ee "
                   "ogtoatyenenee should follow a human calling")
        self.assertIn("TEXT-NOT-WORDS", self.lib.kinds())

    def test_a_shouted_clump_the_scanner_invented(self):
        """Apostolic Canons VII. Length cannot separate this from MENE,
        MENE, TEKEL, UPHARSIN and neither can vowels -- NTO has an O."""
        self.verse("Every believer who enters the church and NTO TE ANDY "
                   "17 BNR Hy BRIER hears the Scriptures")
        self.assertIn("TEXT-NOT-WORDS", self.lib.kinds())

    def test_an_inscription_in_capitals_is_not_noise(self):
        """The one that must NOT fire. Daniel 5:25 is four shouted words in
        a row, and the volume knows every one of them elsewhere."""
        self.verse("This is the writing that was inscribed: MENE, MENE, "
                   "TEKEL, UPHARSIN.")
        self.lib.work["chapters"][0]["verses"][1]["t"] = (
            "This is the interpretation: mene, God has numbered thy kingdom; "
            "tekel, thou art weighed; upharsin, thy kingdom is divided.")
        self.assertEqual(self.lib.kinds(), [])

    def test_a_list_of_foreign_names_is_not_noise(self):
        """Also must not fire. 1 Esdras 9:34 is fifteen rare proper nouns in
        a row, and Jubilees transliterates Ge'ez with its accents on."""
        self.verse("Of the sons of Baani: Jeremias, Momdis, Ismaerus, Juel, "
                   "Mamdai, Pedias, Anos, Carabasion, Enasibus.")
        self.lib.work["chapters"][0]["verses"][1]["t"] = (
            "and its name after his wife S\u00ead\u00ead\u0119q\u00eat\u00ebl\u0115b\u00e2b "
            "and Na\u2019\u00eal\u00e2tam\u00e2\u2019\u00fbk.")
        self.assertEqual(self.lib.kinds(), [])

    def test_an_advertisement(self):
        self.verse("The words of Amos. Please buy the CD to support the site.")
        self.assertIn("TEXT-FURNITURE", self.lib.kinds())

    def test_a_url_in_the_scripture(self):
        self.verse("The words of Amos. See http://example.org for more.")
        self.assertIn("TEXT-FURNITURE", self.lib.kinds())

    def test_an_empty_verse(self):
        self.verse("   ")
        self.assertIn("TEXT-EMPTY", self.lib.kinds())

    def test_a_chapter_with_nothing_in_it(self):
        self.lib.work["chapters"][0].pop("verses")
        self.assertIn("CHAPTER-EMPTY", self.lib.kinds())

    def test_a_verse_number_used_twice(self):
        self.lib.work["chapters"][0]["verses"][1]["v"] = 1
        self.assertIn("VERSE-DUPLICATED", self.lib.kinds())

    def test_verse_numbers_that_go_backwards(self):
        self.lib.work["chapters"][0]["verses"][0]["v"] = 9
        self.assertIn("VERSE-OUT-OF-ORDER", self.lib.kinds())

    def test_the_manifest_disagreeing_with_the_file(self):
        self.lib.manifest["sections"][0]["works"][0]["chapters"] = 9
        self.assertIn("CHAPTER-COUNT-DISAGREES", self.lib.kinds())

    def test_a_definition_with_no_text(self):
        self.lib.lexicon["zion"]["text"] = ""
        self.assertIn("DEFINITION-EMPTY", self.lib.kinds())

    def test_an_alias_pointing_at_nothing(self):
        self.lib.aliases["sion"] = "nowhere"
        self.assertIn("ALIAS-DANGLING", self.lib.kinds())

    def test_a_place_off_the_earth(self):
        self.lib.places["zion"]["lat"] = 999
        self.assertIn("PLACE-OFF-EARTH", self.lib.kinds())

    def test_a_place_whose_grade_the_map_cannot_draw(self):
        """Four kinds are drawn. A fifth would fall through to a plain dot,
        which would state an identified location the data does not claim."""
        self.lib.places["zion"]["kind"] = "somewhere-ish"
        self.assertIn("PLACE-KIND-UNKNOWN", self.lib.kinds())

    def test_a_pin_on_a_chapter_that_is_not_here(self):
        self.lib.mentions["amos/40"] = ["zion"]
        self.assertIn("PIN-ON-NOTHING", self.lib.kinds())

    def test_a_pin_on_a_place_with_no_record(self):
        self.lib.mentions["amos/0"] = ["atlantis"]
        self.assertIn("PIN-UNPLACED", self.lib.kinds())

    def test_a_thread_pointing_past_the_end_of_a_work(self):
        self.lib.threads[0]["stops"][0]["chapter"] = 40
        self.assertIn("LINK-BROKEN", self.lib.kinds())


class TheLinkCheckerBelievesTheSecondAnswer(unittest.TestCase):
    """HEAD is the request servers treat worst.

    gotquestions.org answers 404 to a HEAD and 200 to a GET of the same URL,
    and the first version of this reported that live page as a dead link.
    One link checker crying wolf is how everybody learns to stop reading it,
    so the retry is held here rather than left as a comment.
    """

    def test_a_failed_head_is_retried_as_a_get(self):
        asked = []

        def fake(url, method, timeout):
            asked.append(method)
            return (404, "Not Found") if method == "HEAD" else (200, "")

        original = verify.ask
        verify.ask = fake
        try:
            status, _why = verify.reach("https://example.org/page")
        finally:
            verify.ask = original

        self.assertEqual(asked, ["HEAD", "GET"])
        self.assertEqual(status, 200)

    def test_the_development_server_is_not_an_external_link(self):
        """The README tells you to start it yourself; it is not an address
        anything on the internet is expected to answer."""
        self.assertNotIn(
            "http://localhost:8000",
            verify.urls_in_repo(),
            "the link check would report the reader's own dev server as dead")


if __name__ == "__main__":
    unittest.main()
