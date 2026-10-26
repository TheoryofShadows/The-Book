#!/usr/bin/env python3
"""Draw the mark into every form the site needs, from tools/logo.py.

    python3 tools/build_logo.py [docs/assets]

Emits:

    logo.svg        the mark alone, navy and gold, for a light ground
    logo-dark.svg   the same with the blue lifted and the gold brightened,
                    for a navy or near-black ground
    favicon.svg     the mark on a navy tile, for the browser tab (no
                    filters, a few kilobytes: the offline copy inlines it)
    lockup.svg      the mark over the wordmark and the two lines under it,
                    letters as outlines so it draws the same everywhere
    lockup-dark.svg the same for a dark ground
    icon-180.png    the tile, full bleed, for an iOS home screen
    icon-192.png    the tile, the size Chrome's install criteria name
    icon-512.png    the tile, full bleed, for link previews and elsewhere
    icon-maskable-512.png
                    the same mark drawn inside Android's safe zone, so a
                    launcher can crop it to a circle or a squircle
    og-card.jpg     1200 x 630, the social card
    logo.build.json what the PNG and JPG were drawn from

The SVGs are plain strings from tools/logo.py and need nothing. The raster
files are drawn by the headless Chromium that tests/ already installs
(tools/render_logo.js), because the mark now has gradients, a blur and a
shadow, and a hand-written rasteriser that did all of that would be a worse
renderer than the one already in the repository. A browser does not promise
the same bytes across versions, so the raster files are not compared byte
for byte: logo.build.json records the hash of the SVG each one was drawn
from, and tests/python/test_logo.py holds that to the SVGs this file emits
now. Change the mark and the build file no longer matches, which is the
failure that matters: the PNGs are stale.

The second tagline reads SCRIPTURE · HISTORY. The artwork this was drawn
from has a third term, TRUTH, and it is left off the site's lockup and card
on purpose -- see the note above LOCKUP_TERMS.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import logo                                          # noqa: E402
from logo import THEMES, _n                          # noqa: E402
from logo_type import TYPE                           # noqa: E402

# Read in main() rather than here, so importing this module cannot pick
# up the arguments of whatever imported it.
OUT = "docs/assets"

# The sizes emitted, named once because two places count on them: main()
# below writes them and test_logo.py asserts each one exists and was drawn
# from the current source. 180 is Apple's home-screen tile. 512 is the link
# preview and the manifest's large icon. 192 is the size Chrome's install
# criteria name, and a manifest without one is a site Android will not offer
# to install -- which is the whole point of having a manifest.
ICON_SIZES = (180, 192, 512)

# The mark inset in a square tile. 1/8 on every side is the padding Apple's
# own icons use, and it survives the corner rounding iOS applies on top.
PAD = 1.0 / 8.0

# The maskable icon: a launcher crops it to whatever shape it likes, and
# promises only that a circle 80% of the icon wide survives. The mark is
# sized so that its farthest corner sits inside that circle with room to
# spare, which tests/python/test_webmanifest.py checks from these numbers.
MASKABLE_MARK = 0.62                            # mark width / icon width

# A decision about the signature, not an accident. The volume says, in bold,
# on its own accuracy page: "That is a decision about order, not a verdict
# about truth", and closes the section "Nothing here is a claim to have
# settled a question scholars have not." Claiming TRUTH on the signature while
# the text underneath declines to is the one contradiction a reader would
# actually catch, so the site's lockup and card carry two terms. The
# owner's own artwork has all three; the platform banners made from it
# (outside this repository) keep them.
LOCKUP_TERMS = ("SCRIPTURE", "HISTORY")

CARD = (1200, 630)


# --------------------------------------------------------------------------
# Lockup
# --------------------------------------------------------------------------
def _hrule(pfx, y, half, gap, diamond=True, w=1.6):
    s = ""
    if diamond:
        r = 7
        s += (f'<path d="M0 {y-r}L{r} {y}L0 {y+r}L{-r} {y}Z" fill="url(#{pfx}dia)"/>')
    else:
        s += f'<circle cx="0" cy="{y}" r="3.6" fill="url(#{pfx}dia)"/>'
    s += (f'<rect x="{gap}" y="{_n(y-w/2)}" width="{half-gap}" height="{w}" fill="url(#{pfx}rule)"/>'
          f'<rect x="{-half}" y="{_n(y-w/2)}" width="{half-gap}" height="{w}" fill="url(#{pfx}rule)"/>')
    return s


def _type_defs(pfx, t):
    g, w = t["gold"], t["word"]
    return (f'<linearGradient id="{pfx}word" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{w[0]}"/><stop offset=".5" stop-color="{w[1]}"/>'
            f'<stop offset="1" stop-color="{w[2]}"/></linearGradient>'
            f'<linearGradient id="{pfx}rule" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{g[2]}" stop-opacity="0"/>'
            f'<stop offset=".25" stop-color="{g[1]}"/><stop offset=".5" stop-color="{g[0]}"/>'
            f'<stop offset=".75" stop-color="{g[1]}"/>'
            f'<stop offset="1" stop-color="{g[2]}" stop-opacity="0"/></linearGradient>'
            f'<linearGradient id="{pfx}dia" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{g[0]}"/><stop offset=".5" stop-color="{g[1]}"/>'
            f'<stop offset="1" stop-color="{g[3]}"/></linearGradient>')


def _terms(pfx, t, words, y, size_k=1.0):
    """The tagline of dot-separated terms, centred on x = 0, baseline y."""
    gap = 26 * size_k
    widths = [TYPE[w][1] * size_k for w in words]
    total = sum(widths) + gap * (len(words) - 1)
    x = -total / 2
    out = ""
    for i, wd in enumerate(words):
        out += (f'<path transform="translate({_n(x)} {_n(y)}) scale({size_k})" '
                f'd="{TYPE[wd][0]}" fill="{t["tag2"]}"/>')
        x += widths[i]
        if i < len(words) - 1:
            out += (f'<circle cx="{_n(x + gap/2)}" cy="{_n(y - 7*size_k)}" '
                    f'r="{_n(2.6*size_k)}" fill="url(#{pfx}dia)"/>')
            x += gap
    return out


def lockup_inner(pfx, theme, terms=LOCKUP_TERMS):
    """The stacked lockup: mark at the origin (foot of its spine = 0,0),
    everything else below it. Returns (svg fragment, (x0, y0, w, h))."""
    t = THEMES[theme]
    out = (f'<defs>{logo.defs(pfx, t)}{logo.clip_defs(pfx)}{_type_defs(pfx, t)}</defs>'
           + logo.mark_body(pfx, t, "full"))
    out += _hrule(pfx, 34, 140, 14)
    the_w, book_w = TYPE["THE"][1], TYPE["BOOK"][1]
    tb, bb = 118, 256
    out += (f'<path transform="translate({_n(-the_w/2)} {tb})" d="{TYPE["THE"][0]}" '
            f'fill="url(#{pfx}word)"/>')
    out += (f'<path transform="translate({_n(-book_w/2)} {bb})" d="{TYPE["BOOK"][0]}" '
            f'fill="url(#{pfx}word)"/>')
    y2 = bb + 38
    out += _hrule(pfx, y2, 205, 18)
    y3 = y2 + 46
    out += (f'<path transform="translate({_n(-TYPE["TAG1"][1]/2)} {y3})" '
            f'd="{TYPE["TAG1"][0]}" fill="{t["tag"]}"/>')
    y4 = y3 + 26
    out += _hrule(pfx, y4, 140, 10, diamond=False, w=1.3)
    y5 = y4 + 36
    out += _terms(pfx, t, terms, y5)
    return out, (-245.0, -266.0, 490.0, y5 + 30 + 266.0)


def lockup_svg(theme="light", ground=None, terms=LOCKUP_TERMS) -> str:
    body, (x, y, w, h) = lockup_inner("k", theme, terms)
    bg = logo._ground(ground, x, y, w, h)[0]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{_n(x)} {_n(y)} {_n(w)} {_n(h)}" '
            f'width="{_n(w)}" height="{_n(h)}" role="img" '
            f'aria-label="The Book — Chronological Biblical Library">'
            f'<title>The Book — Chronological Biblical Library</title>{bg}{body}</svg>\n')


# --------------------------------------------------------------------------
# Tile and card
# --------------------------------------------------------------------------
def icon_svg(size: int, mark: float = 1 - 2 * PAD) -> str:
    """The full-bleed tile for a PNG: navy ground, the full mark, centred,
    `mark` of the tile wide."""
    a, b, c = logo.NAVY_GROUND
    x, y, w, h = logo.BOUNDS
    k = size * mark / w
    tx = size / 2 - (x + w / 2) * k
    ty = size / 2 - (y + h / 2) * k
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
            f'width="{size}" height="{size}">'
            f'<defs><radialGradient id="ib" gradientUnits="userSpaceOnUse" cx="{size/2}" '
            f'cy="{size*0.42}" r="{size*0.75}"><stop offset="0" stop-color="{a}"/>'
            f'<stop offset=".6" stop-color="{b}"/><stop offset="1" stop-color="{c}"/>'
            f'</radialGradient></defs>'
            f'<rect width="{size}" height="{size}" fill="url(#ib)"/>'
            f'<g transform="translate({_n(tx)} {_n(ty)}) scale({k:.4f})">'
            f'{logo.mark_inner("i", "dark", "full")}</g></svg>\n')


def card_svg() -> str:
    """1200 x 630 social card on navy: the mark on the left, the name large
    on the right with the tagline and the address under it. Everything is
    sized to read at the 300 px wide a feed shows it at."""
    W, H = CARD
    t = THEMES["dark"]
    a, b, c = logo.NAVY_GROUND
    mk = 1.12                                   # mark scale
    mx, my = 300, 360                           # foot of the spine
    bx = 860                                    # centre of the text block
    ks = 560 / TYPE["THEBOOK"][1]               # name scaled to 560 wide
    name_y = 270
    out = (f'<defs><radialGradient id="cb" gradientUnits="userSpaceOnUse" cx="{W/2}" '
           f'cy="{H*0.42}" r="{W*0.7}"><stop offset="0" stop-color="{a}"/>'
           f'<stop offset=".6" stop-color="{b}"/><stop offset="1" stop-color="{c}"/>'
           f'</radialGradient>{_type_defs("c", t)}</defs>'
           f'<rect width="{W}" height="{H}" fill="url(#cb)"/>'
           f'<rect x="24" y="24" width="{W-48}" height="{H-48}" fill="none" '
           f'stroke="{t["gold"][1]}" stroke-opacity=".55" stroke-width="1.5"/>'
           f'<rect x="32" y="32" width="{W-64}" height="{H-64}" fill="none" '
           f'stroke="{t["gold"][1]}" stroke-opacity=".22" stroke-width="1"/>'
           f'<g transform="translate({mx} {my}) scale({mk})">'
           f'{logo.mark_inner("m", "dark", "full")}</g>')
    out += (f'<g transform="translate({bx} 0)">'
            f'<path transform="translate({_n(-TYPE["THEBOOK"][1]*ks/2)} {name_y}) scale({_n(ks)})" '
            f'd="{TYPE["THEBOOK"][0]}" fill="url(#cword)"/>')
    out += _hrule("c", name_y + 40, 280, 18)
    tk = 560 / TYPE["TAG1"][1] * 0.98
    out += (f'<path transform="translate({_n(-TYPE["TAG1"][1]*tk/2)} {name_y+112}) scale({_n(tk)})" '
            f'd="{TYPE["TAG1"][0]}" fill="{t["tag"]}"/>')
    out += _terms("c", t, LOCKUP_TERMS, name_y + 170, 1.55)
    dk = 1.25
    out += (f'<path transform="translate({_n(-TYPE["DOMAIN"][1]*dk/2)} {name_y+232}) scale({dk})" '
            f'd="{TYPE["DOMAIN"][0]}" fill="{t["tag"]}" opacity=".85"/></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
            f'height="{H}">{out}</svg>\n')


# --------------------------------------------------------------------------
# Files
# --------------------------------------------------------------------------
def sources() -> dict:
    """name -> SVG text for everything written."""
    return {
        "logo.svg": logo.mark_svg("light", "full"),
        "logo-dark.svg": logo.mark_svg("dark", "full"),
        "favicon.svg": logo.tile_svg(),
        "lockup.svg": lockup_svg("light"),
        "lockup-dark.svg": lockup_svg("dark"),
    }


def raster_sources() -> dict:
    """name -> (SVG text, width, height) for the raster files."""
    out = {f"icon-{s}.png": (icon_svg(s), s, s) for s in ICON_SIZES}
    out["icon-maskable-512.png"] = (icon_svg(512, MASKABLE_MARK), 512, 512)
    out["og-card.jpg"] = (card_svg(), CARD[0], CARD[1])
    return out


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_record() -> dict:
    return {name: sha(svg) for name, (svg, _w, _h) in raster_sources().items()}


def render(items: dict, outdir: str) -> bool:
    """Hand the raster sources to tools/render_logo.js. False if there is no
    node or no Chromium to do it with; the SVGs are still written."""
    node = shutil.which("node")
    if not node:
        print("  (node not found: raster files left as they are)")
        return False
    jobs = []
    tmp = os.path.join(outdir, ".logo-src")
    os.makedirs(tmp, exist_ok=True)
    for name, (svg, w, h) in items.items():
        src = os.path.join(tmp, name.rsplit(".", 1)[0] + ".svg")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(svg)
        jobs.append({"svg": src, "out": os.path.join(outdir, name), "w": w, "h": h})
    try:
        subprocess.run([node, os.path.join(HERE, "render_logo.js")],
                       input=json.dumps(jobs).encode(), check=True)
    except (subprocess.CalledProcessError, OSError) as e:
        print(f"  (render failed: {e}; raster files left as they are)")
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return True


def main() -> int:
    global OUT
    if len(sys.argv) > 1:
        OUT = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    written = []
    for name, svg in sources().items():
        _write(os.path.join(OUT, name), svg.encode("utf-8"), written)
    rs = raster_sources()
    if render(rs, OUT):
        record = build_record()
        _write(os.path.join(OUT, "logo.build.json"),
               (json.dumps({"drawn_from_sha256": record}, indent=2) + "\n").encode(),
               written)
        for name in rs:
            written.append((os.path.relpath(os.path.join(OUT, name)),
                            os.path.getsize(os.path.join(OUT, name))))
    for name, n in written:
        print(f"  {name}  {n:,} bytes")
    return 0


def _write(path: str, data: bytes, written: list) -> None:
    with open(path, "wb") as fh:
        fh.write(data)
    written.append((os.path.relpath(path), len(data)))


if __name__ == "__main__":
    raise SystemExit(main())
