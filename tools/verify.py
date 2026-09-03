#!/usr/bin/env python3
"""Every chapter, verse, paragraph, definition, place and link, checked.

    python3 tools/verify.py docs/data
    python3 tools/verify.py docs/data --links     # and reach every URL

tools/audit.py already checks the shape of the library against independent
reference figures: does Genesis have fifty chapters, does Psalms have 2,461
verses. This checks the things a count cannot see -- whether the text inside
those chapters is the text and nothing else, whether every definition, pin and
link on the site points at something that exists.

It found, on the pass that produced it, seventy-nine pieces of the
transcription's own furniture being printed as scripture: thirty-nine printed
page numbers, "[p. 134]", dropped into the running text of 1 Enoch wherever a
leaf turned, and forty instances of "[paragraph continues]" -- the
transcriber's note that a paragraph ran on past a page break -- sitting in the
middle of clauses. "And regarding them I prayed to the [paragraph continues]
Lord." Every one of them was also being read aloud, because speakable() blanks
what is neither letter nor digit and "p. 134" is both.

Like audit.py this is a gate rather than a report: a finding not written down
in tools/verify-baseline.txt fails the build, and a line in that file that no
longer occurs fails it too. Nothing regenerates the baseline.

The network check is separate and off by default, for the reason
check_audio.py is a job of its own: somebody else's server being down is not
a finding about this repository.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(ROOT, "tools", "verify-baseline.txt")

# The four grades a place can carry. Kept here rather than inferred, so a
# fifth arriving in the data is a finding rather than a silent fallback to
# whatever the canvas draws by default.
PLACE_KINDS = {"point", "approximate", "region", "within"}

# What must never appear inside the text of a verse or a paragraph. Each is a
# thing a transcription leaves behind, not a thing a translator wrote.
FURNITURE = [
    (re.compile(r"\[p\.\s*\d+\]"), "printed page number"),
    (re.compile(r"\[paragraph continues\]"), "transcriber's paragraph note"),
    (re.compile(r"please buy the cd|support the site", re.I), "advertisement"),
    (re.compile(r"go to the chronological list", re.I), "navigation footer"),
    (re.compile(r"introductory note to\b", re.I), "editorial introduction"),
    (re.compile(r"https?://"), "a URL in the scripture"),
    (re.compile(r"&(?:amp|lt|gt|quot|nbsp|#\d+);"), "an unescaped HTML entity"),
    (re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"), "a control character"),
]

# Scanner noise: not a misprint of a word, but a clump of things that are not
# words at all, picked up off a smudged line and set as scripture.
#
#   "...that he Seperate ee oe ee ee, wee cone erage ee ogtoatyenenee should
#    follow a human calling..."
#
# Two shapes of it, and both need care, because the corpus is full of things
# that look like noise and are not. Transliterated Ethiopic -- Sedeqetelebab,
# Ne'elatama'uk -- fragments into single letters under a tokeniser that does
# not know its accents, and a page of 1 Esdras genealogy is fifteen rare
# proper nouns in a row. So: letters are matched with their accents on, roman
# numerals and real short English words are excluded by name, and a run has to
# be three long before it counts.
WORD = re.compile(r"[^\W\d_]+(?:['\u2019][^\W\d_]+)*", re.UNICODE)
ROMAN = re.compile(r"^[IVXLCDM]+$")
# Short words English actually uses. Everything else of three letters or
# fewer, three in a row, is a scanner talking.
SHORT_WORDS = set("""
a an and are as at be but by do for go he her him his i if in is it its me my
no nor not now of off on or our out own she so the to too up us we who why you
yea nay lo oh ye thy thee thou hath had has was were will all any can did few
how let man may men new one put run saw say see set six son ten two war way yet
god age arm bed cup dry ear eat end eye far fat fig fly get got hot ice ill joy
key kin lad law lay led leg lie lip low mad mid net oil old pay pit ram raw red
rib rod row sad sat sea sew shy sin sir sit sow sum tax tea tie top try use vex
vow wet win wit woe air ate bad bag bar bat bay big bit boy bud bug bow cat cow
cry cut dam den die dig dip ere eve ewe fed fir fit fix foe fro fry fur gap gat
ham hen hid hip hit hut ink inn ire jar jaw lap lot map mat mob nod oak oar ox
pan paw pen pig pin pod pot ran rat ray rid rim rob rot rub rug sap sip sop spy
sty sup tar tin toe ton tow tub urn van vat wag wax web wed wee wig
""".split())
# Caps that belong: an inscription, a divine name, an abbreviation.
SHOUTED_WORDS = {"LORD", "GOD", "AM", "AD", "BC", "CE", "BCE", "US", "AN", "IT",
                 "IS", "OF", "THE", "AND", "TO", "YAHWEH", "HOLY", "A", "I", "O"}


def shouted_runs(text, vocabulary):
    """Clumps of capitals the volume never uses as words anywhere else.

    The other shape the scanner leaves: "Every believer who enters the
    Christian church and NTO TE ANDY 17 BNR Hy BRIER hears the Scriptures".
    Length cannot separate that from MENE, MENE, TEKEL, UPHARSIN or HOLY TO
    YAHWEH, and neither can vowels -- NTO has an O in it. What separates them
    is that the volume knows MENE and TEKEL and HOLY and YAHWEH as words
    somewhere in its own million and a quarter, and has never once seen ANDY
    or BNR. A word used nowhere else, shouted, twice in a row, in a line that
    is not itself a heading, is a scanner rather than a scribe.
    """
    letters = [c for c in text if c.isalpha()]
    if letters and sum(1 for c in letters if c.isupper()) / len(letters) > 0.4:
        return []                       # a heading in capitals is not noise
    tokens = [m.group(0) for m in WORD.finditer(text)]

    def unknown(tok):
        return (tok.isupper() and len(tok) >= 2 and not ROMAN.match(tok)
                and vocabulary.get(tok.lower(), 0) == 0)

    runs, i = [], 0
    while i < len(tokens):
        if unknown(tokens[i]):
            j = i
            while j + 1 < len(tokens) and unknown(tokens[j + 1]):
                j += 1
            if j - i + 1 >= 2:
                runs.append(" ".join(tokens[i:j + 1]))
            i = j + 1
        else:
            i += 1
    return runs


def vocabulary_of(units):
    """Every word the volume uses in ordinary case, and how often.

    Counted in ordinary case only, so a word that appears solely as part of a
    shouted clump cannot vouch for itself.
    """
    counts = {}
    for text in units:
        for match in WORD.finditer(text):
            token = match.group(0)
            if not token.isupper():
                key = token.lower()
                counts[key] = counts.get(key, 0) + 1
    return counts


def noise_runs(text):
    """Clumps of tokens that are not words, in a line of prose that is."""
    letters = [c for c in text if c.isalpha()]
    shouting = (letters
                and sum(1 for c in letters if c.isupper()) / len(letters) > 0.6)
    tokens = [m.group(0) for m in WORD.finditer(text)]

    def gibberish(tok):
        if len(tok) > 3:
            return False
        if tok.lower() in SHORT_WORDS or tok.upper() in SHOUTED_WORDS:
            return False
        if ROMAN.match(tok):
            return False
        return tok.islower() or (tok.isupper() and not shouting)

    runs, i = [], 0
    while i < len(tokens):
        if gibberish(tokens[i]):
            j = i
            while j + 1 < len(tokens) and gibberish(tokens[j + 1]):
                j += 1
            if j - i + 1 >= 3:
                runs.append(" ".join(tokens[i:j + 1]))
            i = j + 1
        else:
            i += 1
    return runs


# A bare "p. 134" with no brackets is a citation in a footnote as often as it
# is a page marker -- "Donaldson's Hist. of Christ. Lit. vol. i. p. 291" is
# the former -- so it is reported for a human rather than matched as
# furniture, and the works where it is known to be citation are baselined.
LOOSE_PAGE = re.compile(r"(?<!\[)\bp\.\s*\d+")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def check(data_dir):
    """Every finding, as (KIND, where, detail) triples."""
    out = []
    def say(kind, where, detail=""):
        out.append((kind, where, detail))

    manifest = load(os.path.join(data_dir, "manifest.json"))
    works = {w["id"]: w for s in manifest["sections"] for w in s["works"]}
    counts = {"works": 0, "chapters": 0, "verses": 0, "paras": 0}

    # Read once for the vocabulary, because whether a shouted token is a word
    # is a question about the whole volume rather than about its own line.
    every_text = []
    for path in sorted(glob.glob(os.path.join(data_dir, "works", "*.json"))):
        for chapter in load(path).get("chapters", []):
            every_text.extend(v.get("t", "") for v in (chapter.get("verses") or []))
            every_text.extend(chapter.get("paras") or [])
    vocabulary = vocabulary_of(every_text)

    # ---- the text itself ----------------------------------------------
    chapters_in = {}
    for path in sorted(glob.glob(os.path.join(data_dir, "works", "*.json"))):
        work = load(path)
        wid = work["id"]
        counts["works"] += 1
        chapters_in[wid] = len(work.get("chapters", []))
        if wid not in works:
            say("WORK-UNLISTED", wid, "a work file the manifest does not list")

        seen_labels = {}
        for chapter in work.get("chapters", []):
            counts["chapters"] += 1
            label = chapter.get("label") or "?"
            where = f"{wid} / {label}"
            seen_labels[label] = seen_labels.get(label, 0) + 1

            verses = chapter.get("verses") or []
            paras = chapter.get("paras") or []
            if not verses and not paras:
                say("CHAPTER-EMPTY", where, "no verses and no paragraphs")

            numbers = [v.get("v") for v in verses]
            if any(not isinstance(n, int) for n in numbers):
                say("VERSE-UNNUMBERED", where, "a verse with no number")
            clean = [n for n in numbers if isinstance(n, int)]
            if len(set(clean)) != len(clean):
                dupes = sorted({n for n in clean if clean.count(n) > 1})
                say("VERSE-DUPLICATED", where, f"verse {dupes[:5]} twice")
            if clean != sorted(clean):
                say("VERSE-OUT-OF-ORDER", where, "verse numbers do not ascend")

            units = ([(str(v.get("v")), v.get("t", "")) for v in verses]
                     + [(f"para{i}", t) for i, t in enumerate(paras)])
            for ref, text in units:
                if isinstance(ref, str) and ref.startswith("para"):
                    counts["paras"] += 1
                else:
                    counts["verses"] += 1
                if not (text or "").strip():
                    say("TEXT-EMPTY", where, f"{ref} is blank")
                    continue
                for pattern, what in FURNITURE:
                    hit = pattern.search(text)
                    if hit:
                        say("TEXT-FURNITURE", where,
                            f"{ref} carries {what}: {hit.group(0)!r}")
                for run in noise_runs(text) + shouted_runs(text, vocabulary):
                    say("TEXT-NOT-WORDS", wid,
                        f"a clump the scanner invented: {run!r}")
                loose = LOOSE_PAGE.search(text)
                if loose:
                    say("TEXT-PAGE-REFERENCE", wid,
                        "a bare page reference in the running text")
                    break

        for label, n in seen_labels.items():
            if n > 1:
                say("CHAPTER-LABEL-REUSED", wid, f"{label!r} appears {n} times")

    for wid, w in works.items():
        stated = w.get("chapters") or 0
        if wid not in chapters_in:
            if stated:
                say("WORK-MISSING", wid, "the manifest lists it and it has no file")
            continue
        if chapters_in[wid] != stated:
            say("CHAPTER-COUNT-DISAGREES", wid,
                f"manifest says {stated}, the file has {chapters_in[wid]}")

    # ---- the definitions ----------------------------------------------
    lexicon = {}
    for path in sorted(glob.glob(os.path.join(data_dir, "lexicon", "*.json"))):
        lexicon.update(load(path))
    for key, entry in sorted(lexicon.items()):
        if not (entry.get("name") or "").strip():
            say("DEFINITION-UNNAMED", key, "an entry with no headword")
        if not (entry.get("text") or "").strip():
            say("DEFINITION-EMPTY", key, "an entry with no definition")
    aliases = load(os.path.join(data_dir, "lexicon-aliases.json"))
    for alias, target in sorted(aliases.items()):
        if target not in lexicon:
            say("ALIAS-DANGLING", alias, f"points at {target!r}, which is not an entry")

    # ---- the map -------------------------------------------------------
    places = {}
    for path in sorted(glob.glob(os.path.join(data_dir, "places", "*.json"))):
        places.update(load(path))
    for key, place in sorted(places.items()):
        lat, lon = place.get("lat"), place.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            say("PLACE-UNPLACED", key, "no usable coordinates")
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            say("PLACE-OFF-EARTH", key, f"{lat}, {lon}")
        if not (place.get("name") or "").strip():
            say("PLACE-UNNAMED", key, "a place with no name")
        if place.get("kind") not in PLACE_KINDS:
            say("PLACE-KIND-UNKNOWN", key, f"kind {place.get('kind')!r}")

    mentions = load(os.path.join(data_dir, "mentions.json"))
    for key in sorted(mentions):
        wid, _, idx = key.rpartition("/")
        if wid not in chapters_in:
            say("PIN-ON-NOTHING", key, "names a work that is not here")
            continue
        if not idx.isdigit() or int(idx) >= chapters_in[wid]:
            say("PIN-ON-NOTHING", key, "names a chapter that is not here")
        for place_key in mentions[key]:
            if place_key not in places:
                say("PIN-UNPLACED", key, f"names {place_key!r}, which has no record")

    # ---- the links -----------------------------------------------------
    route = re.compile(r"#/read/([a-z0-9\-]+)/(\d+)")
    for path in sorted(glob.glob(os.path.join(data_dir, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for wid, idx in route.findall(text):
            name = os.path.basename(path)
            if wid not in chapters_in:
                say("LINK-BROKEN", name, f"#/read/{wid} is not a work here")
            elif int(idx) >= chapters_in[wid]:
                say("LINK-BROKEN", name, f"#/read/{wid}/{idx} is past the end")

    threads = load(os.path.join(data_dir, "threads.json"))
    for thread in threads:
        for stop in thread.get("stops", []):
            wid, idx = stop.get("work"), stop.get("chapter")
            if wid not in chapters_in:
                say("LINK-BROKEN", thread.get("id", "?"), f"stop in {wid}, which is not here")
            elif isinstance(idx, int) and idx >= chapters_in[wid]:
                say("LINK-BROKEN", thread.get("id", "?"), f"stop at {wid}/{idx}, past the end")

    return out, counts, places


def urls_in_repo():
    """Every external address the site or its documentation offers."""
    pattern = re.compile(r"https?://[^\s\"'<>)\]}\\]+")
    found = {}
    # The prose files, and the built data -- the manuscript records carry
    # links to the Israel Museum, the Vatican Library, Cambridge and the
    # British Library, and those were never being checked because this only
    # ever read the four files below. A dead link in a citation is worse
    # than a dead link in a README.
    sources = ["README.md", "LICENSE-DATA.md", "docs/index.html",
               "docs/assets/app.js"]
    sources += sorted(os.path.relpath(f, ROOT) for f in
                      glob.glob(os.path.join(ROOT, "docs", "data", "*.json")))
    for path in sources:
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            continue
        with open(full, encoding="utf-8") as fh:
            text = fh.read()
        for url in pattern.findall(text):
            url = url.rstrip(".,;:`*")
            # Templates the page completes at runtime are not addresses,
            # and neither is the development server the README tells you to
            # start yourself.
            if url.endswith(("@", "=", "/download/the-book-read-aloud/")):
                continue
            if re.match(r"https?://(localhost|127\.0\.0\.1)", url):
                continue
            found.setdefault(url, path)
    return found


# Named honestly, with a browser string behind it. gotquestions.org answers
# 404 to an unknown agent and 200 to a browser for the same URL, which is a
# fact about bot filtering rather than about the link.
AGENT = ("Mozilla/5.0 (compatible; the-book-link-check/1.0; "
         "+https://github.com/TheoryofShadows/The-Book)")


def ask(url, method, timeout):
    request = urllib.request.Request(url, method=method, headers={
        "User-Agent": AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            return answer.status, ""
    except urllib.error.HTTPError as exc:
        return exc.code, str(exc.reason)
    except Exception as exc:                              # noqa: BLE001
        return None, str(exc)


def reach(url, timeout=20):
    """Is there something on the end of it?

    HEAD first, because it is a request for the headers alone and this asks
    about eighteen addresses. But a HEAD is the request servers treat worst:
    the Internet Archive answers 405, GitHub answers 403, and
    gotquestions.org answers 404 to a HEAD and 200 to a GET of the same URL.
    So any failed HEAD is retried as a GET and only the second answer is
    believed -- otherwise the first live page reported as dead teaches
    everybody to stop reading this.
    """
    status, why = ask(url, "HEAD", timeout)
    if status is not None and status < 400:
        return status, ""
    # Every failed HEAD is retried, 404 included: gotquestions.org answers
    # 404 to a HEAD and 200 to a GET for the same URL, so believing the first
    # answer would have had this report a live page as a dead link.
    status, why = ask(url, "GET", timeout)
    return status, why


def read_baseline():
    if not os.path.exists(BASELINE):
        return set()
    accepted = set()
    with open(BASELINE, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.split("#", 1)[0].strip()
            if line:
                accepted.add(line)
    return accepted


def line_for(finding):
    return " | ".join(x.strip() for x in finding)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    data_dir = args[0] if args else os.path.join(ROOT, "docs", "data")
    findings, counts, _places = check(data_dir)

    print(f"{counts['works']} works, {counts['chapters']} chapters, "
          f"{counts['verses']} verses and {counts['paras']} paragraphs read")

    accepted = read_baseline()
    # One line per distinct finding. Four chapters of the same work carrying
    # the same kind of page reference is one thing to write down, not four.
    lines = sorted({line_for(f) for f in findings})
    unexpected = [l for l in lines if l not in accepted]
    stale = sorted(accepted - set(lines))

    for line in unexpected:
        print(f"  {line}")

    status = 0
    if unexpected:
        print(f"\n{len(unexpected)} finding(s) not in tools/verify-baseline.txt.")
        print("Each is either a defect to repair or a property of the printed")
        print("edition to write down, with its reason, in that file.")
        status = 1
    if stale:
        print(f"\n{len(stale)} baseline entr(y/ies) no longer occur:")
        for line in stale:
            print(f"  {line}")
        print("Delete them: the file has to keep describing the volume as it is.")
        status = 1
    if not unexpected and not stale:
        print(f"{len(lines)} finding(s), all accounted for in "
              f"tools/verify-baseline.txt")

    if "--links" in sys.argv:
        print()
        urls = urls_in_repo()
        print(f"reaching {len(urls)} external addresses")
        bad, unsure = [], []
        for url, where in sorted(urls.items()):
            code, why = reach(url)
            if code is None or code in (404, 410):
                bad.append(url)
                print(f"  DEAD     {code or 'no answer'}  {url}  ({where}) {why}")
            elif code >= 400:
                # A server that will not say is not the same as a page that
                # is not there. Behind a proxy, or from a datacentre address,
                # 403 is usually a fact about who is asking.
                unsure.append(url)
                print(f"  REFUSED  {code}  {url}  ({where}) {why}")
        if unsure:
            print(f"  {len(unsure)} address(es) refused to answer this checker; "
                  f"that is not the same as a dead link, and is not a failure.")
        if bad:
            print(f"\n{len(bad)} link(s) with nothing on the end of them.")
            status = 1
        else:
            print(f"  no dead links among the {len(urls)}")

    return status


if __name__ == "__main__":
    sys.exit(main())
