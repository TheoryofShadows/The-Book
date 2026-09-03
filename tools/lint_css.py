#!/usr/bin/env python3
"""Two mistakes a stylesheet makes without looking like it has.

A selector declared twice is legal CSS. The second block quietly overrides
part of the first and the first goes on describing something that never
renders, so the file reads as though it says one thing and behaves as though
it says another. Six of those had gathered in app.css, and one --
".player-bar i { background: var(--rubric) }" -- sat twenty-six lines above
the real rule and had therefore never painted a single pixel, which did not
stop it being read, believed, and written up as a fix.

A custom property defined and never used is the same mistake in the palette.
--gilt sat in all three themes for a year with nothing referencing it, and
--rubric-bg went the same way. A colour nothing uses is a colour nobody
maintains, and it will be wrong by the time somebody wants it.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(ROOT, "docs", "assets", "app.css")
JS = os.path.join(ROOT, "docs", "assets", "app.js")


def top_level_selectors(css):
    """Every selector declared at the top level, and how often.

    Only the top level: a rule inside @media is a different rule, and
    repeating the selector it narrows is the whole point of one.
    """
    bare = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    seen, depth, buf, sel = {}, 0, "", ""
    for ch in bare:
        if ch == "{":
            depth += 1
            if depth == 1:
                sel, buf = " ".join(buf.split()), ""
                continue
        elif ch == "}":
            depth -= 1
            if depth == 0:
                if sel and not sel.startswith("@"):
                    seen[sel] = seen.get(sel, 0) + 1
                buf = ""
                continue
        if depth == 0:
            buf += ch
    return seen


def main():
    with open(CSS, encoding="utf-8") as fh:
        css = fh.read()
    with open(JS, encoding="utf-8") as fh:
        js = fh.read()

    bad = 0
    selectors = top_level_selectors(css)
    for name, times in sorted(selectors.items()):
        if times > 1:
            print(f"  FAIL  {name} is declared {times} times", file=sys.stderr)
            bad += 1

    defined = set(re.findall(r"^\s*(--[a-z0-9-]+)\s*:", css, re.M))
    # The reader asks the stylesheet for palette values by name when it
    # paints the map, so a property used only there is still used.
    used = (set(re.findall(r"var\((--[a-z0-9-]+)", css))
            | set(re.findall(r"""["'](--[a-z0-9-]+)["']""", js)))
    for name in sorted(defined - used):
        print(f"  FAIL  {name} is defined and never used", file=sys.stderr)
        bad += 1

    print(f"  ok    {len(selectors)} selectors, {len(defined)} custom properties")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
