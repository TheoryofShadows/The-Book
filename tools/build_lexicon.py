#!/usr/bin/env python3
"""Build the click-a-word lexicon from Easton's Bible Dictionary, 1897.

Why a Victorian dictionary: it is the only comprehensive Bible dictionary in
the public domain. That is a real limitation, not a detail, so every entry
carries its date and the reader is told plainly what they are reading. Easton
is confessional and pre-archaeological, and states some identifications that
excavation has since abandoned.

Two flags are generated mechanically rather than by reviewing 3,962 entries:

  dated      the entry rests on assumptions this volume documents as contested
             -- Mosaic authorship of the Torah, Ussher-style chronology, or a
             traditional attribution the site's own positions layer disputes
  measure    weights, measures and money, where a bare ancient figure means
             nothing without a modern equivalent

Output mirrors the search index: sharded by first letter so a lookup fetches
one small file instead of the whole dictionary.

Sources
  Easton's Bible Dictionary, M. G. Easton, 1897 -- public domain by age
  Machine-readable parse from CCEL ThML by NEUU, CC BY 4.0, which the site
  credits in its licensing note.
"""

from __future__ import annotations

import json
import os
import re
import string
import sys
import unicodedata
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textnorm  # noqa: E402

RAW = sys.argv[1] if len(sys.argv) > 1 else "source/lexicon"
OUT = sys.argv[2] if len(sys.argv) > 2 else "docs/data"

# Assumptions Easton writes from that this volume records as contested.
DATED_PATTERNS = [
    (re.compile(r"\bMoses\b.{0,60}\b(wrote|author|penned)\b", re.I | re.S),
     "Assumes Mosaic authorship of the Torah, which this volume records as "
     "contested; see the positions panel on any book of the Torah."),
    (re.compile(r"\bB\.?C\.?\s*400[0-9]\b|\bcreation\b.{0,40}\b400[0-4]\b", re.I | re.S),
     "Uses the Ussher chronology dating creation to about 4004 BC, which no "
     "current scholarship follows."),
    (re.compile(r"\bthe\s+author\s+of\s+this\s+book\s+was\b", re.I),
     "States an authorship attribution as settled; this volume shows the "
     "traditional and critical positions side by side."),
]

# The plural is the common form -- Easton writes "five hundred cubits" far
# more often than "a cubit" -- and matching only the singular left 31 entries
# quoting ancient measures with no note saying whose figures they are.
MEASURE = re.compile(
    r"\b(cubit|homer|ephah|omer|shekel|talent|denarius|mina|log|hin|bath|"
    r"seah|kab|firkin|stadia|furlong|farthing|mite|drachm)s?\b", re.I)

# Words so common that offering a Bible-dictionary gloss is noise, not help.
STOP = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "had", "has", "have", "he", "her", "him", "his", "i", "in", "is", "it",
    "me", "my", "no", "not", "of", "on", "or", "our", "out", "shall", "she",
    "so", "that", "the", "their", "them", "then", "there", "they", "this",
    "to", "unto", "up", "was", "we", "were", "which", "who", "will", "with",
    "you", "your", "all", "when", "if", "into", "upon", "one", "also", "now",
}


def norm(term: str) -> str:
    """Lookup key: lowercase, unaccented, no punctuation.

    Shared with the gazetteer and with the reader, which has to derive the
    same key from a word the reader selected on the page.
    """
    return textnorm.lookup_key(term)


def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def flags_for(text: str) -> list[dict]:
    out = []
    for pattern, note in DATED_PATTERNS:
        if pattern.search(text):
            out.append({"kind": "dated", "note": note})
            break
    if MEASURE.search(text):
        out.append({
            "kind": "measure",
            "note": "Ancient weights, measures and coin values are given as "
                    "Easton understood them in 1897; modern estimates differ "
                    "and are themselves uncertain.",
        })
    return out


def main() -> int:
    if not os.path.isdir(RAW):
        print(f"missing {RAW}")
        return 1

    shards: dict[str, dict] = defaultdict(dict)
    aliases: dict[str, str] = {}
    total = flagged = 0

    for fn in sorted(os.listdir(RAW)):
        if not fn.endswith(".json"):
            continue
        try:
            data = json.load(open(os.path.join(RAW, fn), encoding="utf-8"))
        except Exception:
            continue

        for key, entry in data.items():
            text = " ".join(clean(d.get("text", "")) for d in
                            entry.get("definitions", []) if d.get("text"))
            if not text:
                continue

            name = entry.get("name") or key.title()
            # "TEKOA, TEKOAH" is one entry serving two spellings; both should
            # resolve to it, which is most of what an alias table is for here.
            surfaces = [s.strip() for s in re.split(r"[,;]", key) if s.strip()]
            primary = norm(surfaces[0])
            if not primary or primary in STOP:
                continue

            flags = flags_for(text)
            # The upstream dataset gives each reference twice: the
            # abbreviation Easton printed ("Ex. 6:20") and the expansion
            # ("Exodus 6:20"). Only the expansion can be resolved against
            # this volume's own book names, and the abbreviation was
            # 0.47 MiB shipped to every reader, and inlined into the
            # offline copy, for nothing at all -- the definition sheet
            # renders a name, a text and its flags, and has never rendered
            # a reference. Kept as a flat list of the expansions, so the
            # data is a third of the size and still says the same thing.
            record = {
                "name": name,
                "text": text,
                "refs": [r["reference"] for r
                         in entry.get("scripture_refs", [])[:12]
                         if isinstance(r, dict) and r.get("reference")],
            }
            if flags:
                record["flags"] = flags
                flagged += 1

            shard = primary[0] if primary[0].isalpha() else "0"
            if primary not in shards[shard]:
                shards[shard][primary] = record
                total += 1

            for s in surfaces:
                n = norm(s)
                if n and n not in STOP and n != primary:
                    aliases[n] = primary

    out_dir = os.path.join(OUT, "lexicon")
    os.makedirs(out_dir, exist_ok=True)
    # Every shard a lookup key can name, including the empty ones. A key is
    # filed under its first letter or under "0", so there are twenty-seven
    # possible files and the corpus fills only some -- no entry starts "x",
    # no place starts "q". The reader has to ask for the shard before it can
    # know that, so a missing file turned an ordinary lookup into a 404:
    # caught, but logged in the console of every reader who tapped such a
    # word, and in the single-file offline build a failed fetch rather than
    # an answer. An empty table is the answer. "Nothing is filed here" is a
    # fact about the corpus and belongs in the data, not in a network error.
    for shard in ["0"] + list(string.ascii_lowercase):
        shards.setdefault(shard, {})

    for shard, table in shards.items():
        with open(os.path.join(out_dir, f"{shard}.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(table, fh, ensure_ascii=False, separators=(",", ":"),
                      sort_keys=True)

    with open(os.path.join(OUT, "lexicon-aliases.json"), "w",
              encoding="utf-8") as fh:
        json.dump(aliases, fh, ensure_ascii=False, separators=(",", ":"),
                  sort_keys=True)

    size = sum(os.path.getsize(os.path.join(out_dir, f))
               for f in os.listdir(out_dir))
    print(f"  entries      : {total}")
    print(f"  aliases      : {len(aliases)}")
    print(f"  flagged      : {flagged}")
    print(f"  shards       : {len(shards)}, {size/1024/1024:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
