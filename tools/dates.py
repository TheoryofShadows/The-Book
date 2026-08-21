#!/usr/bin/env python3
"""Read a numeric span out of a position statement.

The volume is arranged by date, and every work carries two dated positions in
prose -- "Amos of Tekoa, c. 760-750 BCE" against "Amos, c. 760-750 BCE, with
later editorial additions". Prose is the right form for the claim and the wrong
form for showing a reader how far apart two positions are, which on some books
is eight hundred years and on others is nothing at all.

This turns the prose into a span where it can, and says so plainly where it
cannot. It never invents one: a work whose position is "Moses, shortly before
his death" has no numeric date and is shown as having none, rather than being
given a plausible-looking bar that nothing supports.

Years are integers, BCE negative, CE positive, and there is no year zero to
worry about because nothing here is dated to it. `frm` is always the earlier
end.

WHAT IS AND IS NOT A CLAIM HERE. The spans read out of explicit years and
centuries are arithmetic on what the position already says, and add nothing.
The named periods below are different -- they impose boundaries the position
did not state -- so each one carries the event that defines it, and a span
derived from one is marked "period" so the reader can see it is the looser
kind. tests/python/test_dates.py holds every form in the data.
"""

from __future__ import annotations

import re

# Conventional boundaries, each fixed by the event that fixes it. These are the
# standard divisions of the period; where a boundary is genuinely argued the
# span is drawn wide rather than picking a side.
PERIODS = {
    "monarchic": (-1020, -586,
                  "Saul to the fall of Jerusalem"),
    "exilic": (-597, -538,
               "the first deportation to the edict of Cyrus"),
    "the exile": (-597, -538,
                  "the first deportation to the edict of Cyrus"),
    "post-exilic": (-538, -332,
                    "the return under Cyrus to Alexander"),
    "persian period": (-539, -332,
                       "the fall of Babylon to Alexander"),
    "persian": (-539, -332,
                "the fall of Babylon to Alexander"),
    "hellenistic": (-332, -63,
                    "Alexander to Pompey's capture of Jerusalem"),
    "maccabean": (-167, -63,
                  "the revolt to Pompey"),
    "hasmonean": (-140, -63,
                  "Simon's rule to Pompey"),
    "roman period": (-63, 324,
                     "Pompey to Constantine"),
    "second temple": (-516, 70,
                      "the rebuilt temple to its destruction"),
}

CENTURY_SPAN = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s*[-–]\s*(\d{1,2})(?:st|nd|rd|th)\s+centur(?:y|ies)\s+(BCE|CE)\b",
    re.I)
CENTURY = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)\s+century\s+(BCE|CE)\b", re.I)
# "the 50s-60s CE", which is a decade the way "8th century" is a century.
DECADE_SPAN = re.compile(
    r"\b(\d{1,3})0s\s*[-–]\s*(\d{1,3})0s\s*(BCE|CE)\b", re.I)
DECADE = re.compile(r"\b(\d{1,3})0s\s*(BCE|CE)\b", re.I)

# "c. 100 BCE - 50 CE": each end carries its own era, so the two-number
# pattern below cannot see it and would read only the second half.
# The separator is a dash or the word "to"; both are used in the volume.
SEP = r"(?:\s*[-–]\s*|\s+to\s+)"

CROSS_ERA = re.compile(
    r"\b(\d{1,4})\s*(BCE|CE)" + SEP + r"(?:c\.|ca\.)?\s*(\d{1,4})\s*(BCE|CE)\b",
    re.I)
# The hedge is allowed to sit inside the span -- "539 - c. 400 BCE" -- which
# is how the section dates in this volume are written. Without it the start
# of the span is dropped and the section begins where it ends.
YEAR_SPAN = re.compile(
    r"\b(\d{1,4})" + SEP + r"(?:c\.|ca\.)?\s*(\d{1,4})\s*(BCE|CE)\b", re.I)
YEAR = re.compile(r"\b(\d{1,4})\s*(BCE|CE)\b", re.I)

# "before c. 900 BCE" states one end and leaves the other open. Giving it a
# start would be inventing one, so the stated figure is recorded as both ends
# and the openness is recorded beside it; a caller that draws a bar runs it
# off the edge, and a caller measuring a distance refuses.
OPEN_BEFORE = re.compile(r"\bbefore\b", re.I)
# "from" is deliberately not here. "from 539 to c. 400 BCE" is a closed span
# and reading it as an open one would throw away the end that is stated.
OPEN_AFTER = re.compile(r"\b(after|no earlier than|onwards?)\b", re.I)

APPROX = re.compile(r"\b(c\.|ca\.|about|around|roughly|perhaps|probably)", re.I)


def _century_bounds(n: int, era: str) -> tuple[int, int]:
    """The 8th century BCE is 800-701 BCE; the 1st century CE is 1-100."""
    if era.upper() == "BCE":
        return -(n * 100), -(n * 100 - 99)
    return (n - 1) * 100 + 1, n * 100


def _decade_bounds(tens: int, era: str) -> tuple[int, int]:
    """The 50s CE is 50-59 CE; the 50s BCE is 59-50 BCE."""
    if era.upper() == "BCE":
        return -(tens * 10 + 9), -(tens * 10)
    return tens * 10, tens * 10 + 9


def _signed(year: int, era: str) -> int:
    return -year if era.upper() == "BCE" else year


def span(text: str) -> dict | None:
    """The span a position statement commits to, or None if it commits to none.

    The forms are tried most specific first. "15th-13th century BCE" has to be
    read as a span of centuries before the century pattern gets to it and
    calls it the 13th, and before the bare-year pattern gets to it and calls
    it the year 15.
    """
    if not text:
        return None

    approx = bool(APPROX.search(text))

    m = CENTURY_SPAN.search(text)
    if m:
        first, _ = _century_bounds(int(m.group(1)), m.group(3))
        _, last = _century_bounds(int(m.group(2)), m.group(3))
        frm, to = min(first, last), max(first, last)
        return _span(frm, to, "century", approx, m.group(0))

    m = CENTURY.search(text)
    if m:
        frm, to = _century_bounds(int(m.group(1)), m.group(2))
        return _span(frm, to, "century", approx, m.group(0))

    m = DECADE_SPAN.search(text)
    if m:
        first = _decade_bounds(int(m.group(1)), m.group(3))
        last = _decade_bounds(int(m.group(2)), m.group(3))
        ends = first + last
        return _span(min(ends), max(ends), "decade", True, m.group(0))

    m = DECADE.search(text)
    if m:
        frm, to = _decade_bounds(int(m.group(1)), m.group(2))
        return _span(min(frm, to), max(frm, to), "decade", True, m.group(0))

    m = CROSS_ERA.search(text)
    if m:
        a = _signed(int(m.group(1)), m.group(2))
        b = _signed(int(m.group(3)), m.group(4))
        return _span(min(a, b), max(a, b), "explicit", approx, m.group(0))

    m = YEAR_SPAN.search(text)
    if m:
        a = _signed(int(m.group(1)), m.group(3))
        b = _signed(int(m.group(2)), m.group(3))
        return _span(min(a, b), max(a, b), "explicit", approx, m.group(0))

    m = YEAR.search(text)
    if m:
        year = _signed(int(m.group(1)), m.group(2))
        out = _span(year, year, "explicit", approx, m.group(0))
        # Only when the hedge governs the whole statement, not when it is one
        # end of something already read as a span above.
        if OPEN_BEFORE.search(text):
            out["open"] = "before"
        elif OPEN_AFTER.search(text):
            out["open"] = "after"
        return out

    # Named periods last: a position that gives a year and also mentions the
    # period it falls in should be read by its year, which is the tighter
    # claim and the one its author made.
    low = text.lower()
    for name in sorted(PERIODS, key=len, reverse=True):
        if name in low:
            frm, to, why = PERIODS[name]
            out = _span(frm, to, "period", True, name)
            out["basis"] = why
            return out

    return None


def _span(frm: int, to: int, kind: str, approx: bool, matched: str) -> dict:
    return {"frm": frm, "to": to, "kind": kind, "approx": approx,
            "matched": matched.strip()}


def label(year: int) -> str:
    """A year as it is written, not as it is stored."""
    return f"{abs(year)} {'BCE' if year < 0 else 'CE'}"


def describe(sp: dict | None) -> str:
    if not sp:
        return "no numeric date"
    if sp.get("open"):
        return sp["open"] + " " + ("c. " if sp["approx"] else "") + label(sp["to"])
    if sp["frm"] == sp["to"]:
        return ("c. " if sp["approx"] else "") + label(sp["frm"])
    same_era = (sp["frm"] < 0) == (sp["to"] < 0)
    head = ("c. " if sp["approx"] else "")
    if same_era:
        return f"{head}{abs(sp['frm'])}–{label(sp['to'])}"
    return f"{head}{label(sp['frm'])} – {label(sp['to'])}"


def distance(a: dict | None, b: dict | None) -> int | None:
    """How far apart two positions are, in years, or None if unknowable.

    Zero when the spans overlap at all: two positions that admit a common date
    are not in disagreement about the date, whatever else they disagree about.
    """
    if not a or not b:
        return None
    # One end unstated means the distance is unstated. Measuring from the
    # figure that is given would report a confidence the position never had.
    if a.get("open") or b.get("open"):
        return None
    if a["frm"] <= b["to"] and b["frm"] <= a["to"]:
        return 0
    return b["frm"] - a["to"] if b["frm"] > a["to"] else a["frm"] - b["to"]


def enrich(record: dict | None) -> dict | None:
    """A position record with the spans read out of it, leaving it otherwise
    exactly as written."""
    if not record:
        return record
    out = dict(record)
    trad = span(record.get("trad", ""))
    crit = span(record.get("crit", ""))
    out["span"] = {
        "trad": trad,
        "crit": crit,
        "apart": distance(trad, crit),
        # The volume's own word for how far apart the two positions are, which
        # is written by hand and is about more than the dates.
        "gap": record.get("gap", ""),
    }
    return out
