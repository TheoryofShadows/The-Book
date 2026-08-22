#!/usr/bin/env python3
"""Recover printed English from an Internet Archive scan, by geometry.

The plain OCR text these scans ship with -- the _djvu.txt everyone uses --
has thrown away the one thing that makes a nineteenth-century critical
edition separable: where on the page each word sat. A running head, a
marginal line-number, a footnote and a line of the text all arrive as
lines of prose, and telling them apart afterwards means guessing at
shapes. That guessing is how "ao" and "i{" and "y)" end up inside
scripture, because they are what the scanner made of a 20, a 15 and a 30
printed in the margin.

The _djvu.xml keeps the coordinates. So this reads that instead, and
decides by position and type size what every other approach has to
decide by luck:

    the text block   the median left and right edge of the page's own
                     full lines, computed per page because the scans
                     wander by a hundred pixels or more

    marginal numbers a first or last word that starts left of the block
                     or ends right of it. Which margin they sit in
                     alternates with the leaf, and nothing here has to
                     know that

    running heads    the first line of a leaf, when the same first line
                     stands at the top of other leaves too. Type size
                     alone will not do it: Horner's heads are set
                     smaller than his text and James's are set larger.
                     Repetition is what a running head is

    footnotes        trailing lines set smaller than the body and
                     opening after a gap wider than the page's own line
                     pitch. Both signals, and only at the foot: a line
                     of short letters measures small anywhere -- some of
                     Issaverdens's do -- and a rule that could reach the
                     middle of a page would eventually eat some text.
                     Both distances are measured between baselines,
                     because the top of a line moves with whether its
                     first word happens to have an ascender and the
                     baseline does not

    paragraphs       a line indented past the block, following a line
                     that ended short. Either signal alone misfires --
                     the scans put spurious indents on continuation
                     lines -- and together they do not

What comes out is the printed lines, in order, page by page, with
nothing added. Joining them into prose is the caller's business, because
where a work's divisions fall is an editorial question and this is not.
"""

from __future__ import annotations

import difflib
import html
import re
import statistics

OBJECT = re.compile(r"<OBJECT\b")
LINE = re.compile(r"<LINE>(.*?)</LINE>", re.S)
# Two derivers are in play across these scans: the older one writes four
# coordinates, the newer one adds the baseline as a fifth. Both mean
# left, bottom, right, top.
WORD = re.compile(
    r'<WORD coords="(\d+),(\d+),(\d+),(\d+)(?:,-?\d+)?"[^>]*>(.*?)</WORD>',
    re.S)

# How far outside the text block a word must sit to be a margin number,
# how far past it a line must start to be an indent, and how short the
# line before an indent must end. All three are in multiples of the
# page's own body type, because these scans are at whatever resolution
# somebody chose: Horner's leaves carry type 75 pixels tall and
# Issaverdens's 36, and a threshold in pixels that suits one silently
# stops firing on the other. All three are loose, because the signals
# they read are worth whole ems and the jitter is worth fractions.
OUTSIDE = 0.5
INDENT = 0.7
SHORT = 2.0

# A trailing line set below this fraction of the page's body type, and
# opening after a gap this much wider than the page's line pitch, is a
# footnote. Horner's notes measure 0.81 of his text and James's 0.92 to
# 0.95, so the size cut has to sit high -- above some perfectly ordinary
# lines -- and the gap is what keeps it off them. Measured between
# baselines, a body line opens between 0.97 and 1.03 of the pitch on
# every leaf of all three of these books, and a footnote at 1.13 or
# more.
SMALL = 0.96
GAP = 1.08

# How many leaves must open with the same line before it is a running
# head rather than a coincidence, and how alike two readings of one head
# must be to count as the same head.
REPEATS = 3
CLOSE = 0.75


class Line:
    """One printed line: its words, its box, and how it starts."""

    def __init__(self, words):
        self.words = words
        self.x0 = min(w[0] for w in words)
        self.x1 = max(w[2] for w in words)
        self.height = statistics.median(w[1] - w[3] for w in words)
        self.base = statistics.median(w[1] for w in words)
        self.starts_para = False

    @property
    def text(self) -> str:
        return " ".join(w[4] for w in self.words)

    def __repr__(self) -> str:                          # pragma: no cover
        return f"<Line {self.text[:40]!r}>"


class Page:
    """One leaf of the scan, after the furniture has been taken off."""

    def __init__(self, number: int, lines, heads, notes, margins):
        self.number = number
        self.lines = lines
        self.heads = heads
        self.notes = notes
        self.margins = margins


def words(chunk: str):
    """Every word in a chunk of the XML, as (x0, y1, x1, y0, text)."""
    out = []
    for x0, y1, x1, y0, text in WORD.findall(chunk):
        text = html.unescape(text).strip()
        if text:
            out.append((int(x0), int(y1), int(x1), int(y0), text))
    return out


def pages(xml: str):
    """Split the document into per-page chunks, in printed order."""
    parts = OBJECT.split(xml)[1:]
    return parts


def read(xml: str, frm: int, to: int, margin_len: int = 3, head=None):
    """Pages `frm` up to but not including `to`, cleaned.

    `frm` and `to` index the scan's own images, which is what the
    archive's page-number map speaks in and what a reader checking this
    against the scan will be looking at.

    `margin_len` is the longest word that may be taken for a marginal
    line-number; 0 for a printing that has none, because then any word
    the scanner boxed a little wide is at risk and there is nothing to
    gain by the risk.

    `head` is a pattern the page's running head must match to be kept. A
    page with no running head at all is always kept: that is what the
    opening leaf of a work looks like. It is how a work is cut out of a
    volume that runs another one on from it.
    """
    parts = pages(xml)
    leaves = []
    for index in range(frm, to):
        raw = []
        for line in LINE.findall(parts[index]):
            got = words(line)
            if got:
                raw.append(Line(got))
        if raw:
            leaves.append((index, raw))

    running = _running_heads(leaves)

    out = []
    previous = None
    for index, raw in leaves:
        page = _page(index, raw, previous, margin_len, running)
        if page is None:
            continue
        if head is not None and page.heads and not any(
                head.search(h) for h in page.heads):
            continue
        if page.lines:
            previous = page.lines[-1]
        out.append(page)
    return out


def _key(text: str) -> str:
    """A page's first line, with everything a page number changes taken off."""
    return re.sub(r"[^A-Z]", "", text.upper())


def _running_heads(leaves) -> list:
    """The first lines that repeat across leaves, and so are furniture.

    Matched loosely afterwards, because the scanner does not read a
    running head the same way twice: Horner's "STATUTES OF THE APOSTLES"
    comes back as "STATUTBS" on one leaf and his "TRANSLATION" as
    "TRANSLATIOH" on another, and an exact table would leave those two
    heads standing in the text.
    """
    seen = {}
    for _index, raw in leaves:
        key = _key(raw[0].text)
        if len(key) >= 8:
            seen[key] = seen.get(key, 0) + 1
    return sorted(k for k, n in seen.items() if n >= REPEATS)


def _is_head(text: str, running) -> bool:
    key = _key(text)
    if len(key) < 8:
        return False
    return bool(difflib.get_close_matches(key, running, n=1, cutoff=CLOSE))


def _page(number: int, raw, previous, margin_len: int, running: set):
    if not raw:
        return None

    median = statistics.median(line.height for line in raw)
    bases = [line.base for line in raw]
    pitch = statistics.median(
        [b - a for a, b in zip(bases, bases[1:])]) if len(bases) > 1 else 0

    lo, hi = 0, len(raw)
    heads, notes = [], []
    while lo < hi:
        if _is_head(raw[lo].text, running):
            heads.append(raw[lo].text)
            lo += 1
            continue
        # A page number the scanner read as a line of its own, sitting
        # above the head it was printed beside. Only ever taken with the
        # head, never on its own.
        if (lo + 1 < hi and len(_key(raw[lo].text)) < 8
                and _is_head(raw[lo + 1].text, running)):
            heads.append(raw[lo].text)
            lo += 1
            continue
        break

    # A footnote is set smaller than the text and opens after a gap
    # wider than the page's line pitch. Its continuation lines are only
    # set smaller, so the run is found by type size and then the gap is
    # asked about the line that opens it -- asking it of the last line
    # on the leaf would only ever find a one-line note.
    foot = hi
    while foot - 1 > lo and raw[foot - 1].height < SMALL * median:
        foot -= 1
    if foot < hi and pitch:
        gap = raw[foot].base - raw[foot - 1].base
        if gap > GAP * pitch:
            notes = [l.text for l in raw[foot:hi]]
            hi = foot

    body = [l for l in raw[lo:hi] if len(l.words) >= 6]
    if not body:
        return Page(number, [], heads, notes, [])
    left = statistics.median(l.x0 for l in body)
    right = statistics.median(l.x1 for l in body)
    outside, indent, short = OUTSIDE * median, INDENT * median, SHORT * median

    kept, margins = [], []
    for line in raw[lo:hi]:
        ws = list(line.words)
        # A margin number is short and outside the block. Both, because
        # a long word starting left of the block is the scanner boxing
        # the block itself wide, and dropping it would lose text.
        if margin_len and len(ws) > 1 and ws[0][0] < left - outside \
                and len(ws[0][4]) <= margin_len:
            margins.append(ws[0][4])
            ws = ws[1:]
        if margin_len and len(ws) > 1 and ws[-1][2] > right + outside \
                and len(ws[-1][4]) <= margin_len:
            margins.append(ws[-1][4])
            ws = ws[:-1]
        if not ws:
            continue
        made = Line(ws)
        made.starts_para = (made.x0 > left + indent
                            and (previous is None or previous.x1 < right - short))
        kept.append(made)
        previous = made

    return Page(number, kept, heads, notes, margins)


# ---- turning printed lines back into prose ---------------------------
#
# This half runs offline, from the text committed under source/extra, and
# knows nothing about scans. Joining printed lines into prose is a
# question about words, and the answer has to be checkable from the file
# in the repository rather than from a page image nobody has.

HYPHEN = re.compile(r"[A-Za-z]-$")
EDGE = ".,;:!?()[]'\"\u00ab\u00bb"


def prose(paragraphs, hyphens=None):
    """Paragraphs of printed lines, joined into paragraphs of prose.

    A word broken across a line break is put back together. Whether the
    join keeps the hyphen is decided by the rest of the work rather than
    by a rule: if the closed-up form occurs elsewhere in it the break was
    the compositor's and the hyphen goes; if only the hyphenated form
    occurs, the hyphen is the translator's and it stays; if neither does,
    it closes up, which is the commoner case by far. `hyphens` collects
    every decision, so the caller can print or test them.
    """
    if hyphens is None:
        hyphens = []
    vocabulary = set()
    for para in paragraphs:
        for line in para:
            for word in line.split():
                vocabulary.add(word.strip(EDGE).lower())

    out = []
    for para in paragraphs:
        joined = _dehyphenate(list(para), vocabulary, hyphens)
        text = re.sub(r"\s+", " ", " ".join(joined)).strip()
        if text:
            out.append(text)
    return out


def _dehyphenate(lines, vocabulary, hyphens):
    """Close every hyphenated line break, returning the lines."""
    for i in range(len(lines) - 1):
        line = lines[i].rstrip()
        if not HYPHEN.search(line):
            continue
        nxt = lines[i + 1].lstrip()
        if not nxt:
            continue
        head, _, rest = nxt.partition(" ")
        stem = line[:-1]
        started = stem.split()[-1] if stem.split() else ""
        tail = head.strip(EDGE)
        if not started or not tail:
            continue
        closed = (started + tail).lower()
        kept = (started + "-" + tail).lower()
        if kept in vocabulary and closed not in vocabulary:
            lines[i] = line + head
            hyphens.append((started + "-" + tail, "kept"))
        else:
            lines[i] = stem + head
            hyphens.append((started + tail, "closed"))
        lines[i + 1] = rest
    return [l.strip() for l in lines if l.strip()]


def read_recovered(path):
    """A file written by tools/fetch_scans.py, as paragraphs of lines.

    The page markers are transparent -- a paragraph runs across a leaf
    the way it does in the book -- and a blank line is what says a
    paragraph opens. That is why the markers carry no blank line of
    their own: the two would be indistinguishable, and every paragraph
    broken by a page turn would come apart.
    """
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    body = text.split("-" * 78, 1)[1]

    paragraphs, current, pages = [], [], []
    for line in body.split("\n"):
        if line.startswith("[page "):
            pages.append(int(line[6:-1]))
            continue
        if not line.strip():
            if current:
                paragraphs.append(current)
                current = []
            continue
        current.append(line.strip())
    if current:
        paragraphs.append(current)
    return paragraphs, pages
