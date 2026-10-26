#!/usr/bin/env python3
"""The mark, defined once, as geometry rather than as a drawing.

An open book, seen from the front: two navy boards either side of the spine
and three gold leaves fanning up off them, each leaf a little shorter and
further in than the one outside it. Everything runs into one point -- the
foot of the spine -- which is what makes it read as a book opened flat
rather than as a pair of wings.

Everything downstream -- the SVG in the page head, the tile in a browser
tab, the PNG an iPhone puts on a home screen, the lockup, the social card --
is generated from the numbers below, so the mark cannot drift between them.

Only the left half is written down. The right is its mirror, because a book
opened flat is symmetrical and saying so once is the way to keep it that way.

Coordinates are in "mark units": x runs either side of the spine, so the
spine is x = 0; y is negative upwards from the foot of the spine, which is
y = 0. The mark is 410 wide and 220 tall, and VIEW is the box that holds it
with room for the shadow under the book.

Two levels of detail, because one drawing cannot be right at 22 pixels and
at 2000:

  full    the whole richer mark: cast shadows between the leaves, a rim of
          light along each page edge, the gutter shading, a soft glow and a
          shadow under the book. Uses a blur filter, so it is for files and
          large sizes only.
  small   the same shapes and the same gradients with no filters and no
          clip paths -- ten gradient fills and the gutter shading -- which
          stays crisp and cheap at the header's 32 pixels and in a tab.

Two themes: LIGHT is navy and gold for cream or white grounds; DARK lifts the
navy to a blue that holds up on a navy or near-black ground and brightens the
gold, because navy on navy is a mark with a hole in it.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Colour. Two themes, each a set of stops.
#   gold   centre-of-sheen -> edge, four stops: light, mid, dark, deepest
#   navy   tip -> spine, three stops
#   word   top -> bottom of the wordmark, three stops
# --------------------------------------------------------------------------
LIGHT = dict(
    gold=("#F6DC9C", "#D9A94F", "#A87626", "#7A4F14"),
    navy=("#1B3A82", "#12295F", "#0B1F4B"),
    word=("#1A3A80", "#0F2A66", "#0A1D4A"),
    tag="#12295F", tag2="#0F2559",
    rim="#FFF3CF", rim_op=0.85, rim_navy="#4B6FC0",
    gutter=0.38, glow=0.0, shadow=0.30,
)
DARK = dict(
    gold=("#FBE8B4", "#E5BB62", "#BC8A33", "#8F6420"),
    navy=("#5A82CF", "#3C62B3", "#233F82"),
    word=("#FFFFFF", "#F6EFDC", "#E3D5AE"),
    tag="#E8CF98", tag2="#D9B96E",
    rim="#FFF6DA", rim_op=0.9, rim_navy="#9DB8F0",
    gutter=0.50, glow=0.30, shadow=0.55,
)
THEMES = {"light": LIGHT, "dark": DARK}

# The two grounds the mark is set on elsewhere in the repository.
CREAM = "#F4EEDF"
NAVY_GROUND = ("#112A63", "#0A1D49", "#050F2B")     # centre, middle, edge

# The colours the site's own header and tile name, kept as constants because
# other files and tests quote them.
NAVY = (0x12, 0x29, 0x5F)
GOLD = (0xD9, 0xA9, 0x4F)

# --------------------------------------------------------------------------
# Geometry. The left half, in a drawing grid of 4 units to a mark unit,
# origin at the foot of the spine in the drawing (854, 930). Each leaf is two
# edges: the top edge, from the spine out to the outer corner, and the
# bottom edge, from the other outer corner back in to the spine. They are
# smoothed through their points (Catmull-Rom, written out as cubics), which
# is why a leaf is a list of points and not a pair of curves.
# --------------------------------------------------------------------------
SCALE = 0.25
ORIGIN = (854, 930)

LEAVES = [
    ("g1", "gold",
     [(858, 918), (852, 780), (830, 580), (760, 400), (650, 250), (500, 125), (378, 60)],
     [(310, 262), (430, 335), (560, 425), (700, 560), (790, 700), (838, 830), (852, 915)]),
    ("g2", "gold",
     [(846, 916), (830, 790), (790, 690), (700, 590), (560, 455), (420, 355),
      (300, 278), (288, 262), (313, 190), (265, 172)],
     [(165, 358), (300, 392), (470, 462), (640, 585), (760, 725), (828, 860), (842, 915)]),
    ("g3", "gold",
     [(838, 916), (822, 830), (780, 745), (680, 625), (520, 508), (330, 423), (180, 380)],
     [(100, 482), (300, 502), (500, 572), (660, 682), (770, 802), (826, 885), (834, 915)]),
    ("n1", "navy",
     [(826, 915), (790, 835), (700, 722), (520, 602), (300, 527), (150, 508)],
     [(82, 612), (250, 612), (450, 664), (640, 774), (758, 866), (814, 915)]),
    ("n2", "navy",
     [(808, 918), (770, 890), (680, 818), (500, 722), (300, 656), (75, 637)],
     [(35, 690), (250, 692), (450, 742), (640, 832), (745, 892), (800, 926)]),
]
# The little block the spine sits on, drawn over the boards.
BASE = [(782, 892), (854, 892), (854, 940), (812, 938), (795, 925)]

# The box that holds the mark and the shadow under it: x0, y0, width, height.
VIEW = (-216.0, -224.0, 432.0, 256.0)
# The mark's own extent, without the shadow, for centring on a tile.
BOUNDS = (-206.0, -218.0, 412.0, 224.0)


def _pt(p):
    return ((p[0] - ORIGIN[0]) * SCALE, (p[1] - ORIGIN[1]) * SCALE)


def _n(v: float) -> str:
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _cr(pts):
    """Catmull-Rom through pts, as cubic segments with no leading move."""
    out = []
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        out.append(("C", c1, c2, p2))
    return out


def leaf_path(leaf) -> list:
    """One leaf of the left half as segments: ('M', p), ('C', c1, c2, p),
    ('L', p). Top edge out from the spine, across the outer edge, bottom
    edge back to the spine."""
    _name, _kind, top, bottom = leaf
    t = [_pt(p) for p in top]
    b = [_pt(p) for p in bottom]
    return [("M", t[0])] + _cr(t) + [("L", b[0])] + _cr(b)


def top_edge(leaf) -> list:
    t = [_pt(p) for p in leaf[2]]
    return [("M", t[0])] + _cr(t)


def base_path() -> list:
    pts = [_pt(p) for p in BASE]
    return [("M", pts[0])] + [("L", p) for p in pts[1:]]


def mirror(path: list) -> list:
    return [(seg[0],) + tuple((-p[0], p[1]) for p in seg[1:]) for seg in path]


def d(path: list) -> str:
    """Path data, closed."""
    out = []
    for seg in path:
        pts = " ".join(f"{_n(x)} {_n(y)}" for x, y in seg[1:])
        out.append(seg[0] + pts)
    return "".join(out) + "Z"


def d_open(path: list) -> str:
    out = []
    for seg in path:
        pts = " ".join(f"{_n(x)} {_n(y)}" for x, y in seg[1:])
        out.append(seg[0] + pts)
    return "".join(out)


def flatten(path: list, steps: int = 20) -> list:
    """The path as a polygon, for anything that has to fill it by pixel."""
    pts, here = [], (0.0, 0.0)
    for seg in path:
        if seg[0] in ("M", "L"):
            here = seg[1]
            pts.append(here)
        else:
            c1, c2, end = seg[1], seg[2], seg[3]
            for i in range(1, steps + 1):
                t = i / steps
                u = 1 - t
                pts.append((u**3 * here[0] + 3 * u * u * t * c1[0]
                            + 3 * u * t * t * c2[0] + t**3 * end[0],
                            u**3 * here[1] + 3 * u * u * t * c1[1]
                            + 3 * u * t * t * c2[1] + t**3 * end[1]))
            here = end
    return pts


def shapes() -> list:
    """Every filled shape of the mark, back to front, both halves, as
    (kind, path): kind is 'gold', 'navy' or 'base'."""
    out = []
    for leaf in LEAVES:
        p = leaf_path(leaf)
        out.append((leaf[1], p))
        out.append((leaf[1], mirror(p)))
    b = base_path()
    out.append(("base", b))
    out.append(("base", mirror(b)))
    return out


# --------------------------------------------------------------------------
# SVG
# --------------------------------------------------------------------------
def _stops(cols, offs=None, css=None, pfx=""):
    offs = offs or [i / (len(cols) - 1) for i in range(len(cols))]
    out = []
    for i, (o, c) in enumerate(zip(offs, cols)):
        if css:
            out.append(f'<stop offset="{o:.2f}" class="{css}{i}"/>')
        else:
            out.append(f'<stop offset="{o:.2f}" stop-color="{c}"/>')
    return "".join(out)


def defs(pfx: str, t: dict, css: bool = False, full: bool = True) -> str:
    """Gradients (and, for the full mark, the glow, shadow and blur).

    css=True leaves the stop colours to the stylesheet, as classes
    <pfx>g0..g3 (gold) and <pfx>n0..n2 (navy), so one inline mark can follow
    the page's theme.
    """
    g, n = t["gold"], t["navy"]
    gc = f"{pfx}g" if css else None
    nc = f"{pfx}n" if css else None
    s = (f'<radialGradient id="{pfx}gold" cx="-95" cy="-125" r="215" '
         f'gradientUnits="userSpaceOnUse">'
         + _stops([g[0], g[0], g[1], g[2], g[3]], [0, .18, .5, .82, 1], css=None)
         + '</radialGradient>')
    if css:
        # Five stops, drawn from four classes: the light end repeats.
        cls = [0, 0, 1, 2, 3]
        s = (f'<radialGradient id="{pfx}gold" cx="-95" cy="-125" r="215" '
             f'gradientUnits="userSpaceOnUse">'
             + "".join(f'<stop offset="{o}" class="{gc}{c}"/>'
                       for o, c in zip(("0", ".18", ".5", ".82", "1"), cls))
             + '</radialGradient>')
    s += (f'<linearGradient id="{pfx}navy" gradientUnits="userSpaceOnUse" '
          f'x1="-215" y1="-40" x2="-5" y2="-5">'
          + _stops(n, css=nc) + '</linearGradient>')
    s += (f'<linearGradient id="{pfx}gut" gradientUnits="userSpaceOnUse" '
          f'x1="0" y1="0" x2="-75" y2="0">'
          f'<stop offset="0" stop-color="#000" stop-opacity="{t["gutter"]}"/>'
          f'<stop offset="1" stop-color="#000" stop-opacity="0"/></linearGradient>')
    if full:
        s += (f'<radialGradient id="{pfx}glow" cx="0" cy="0" r="1" '
              f'gradientUnits="userSpaceOnUse" '
              f'gradientTransform="translate(0 -95) scale(190 150)">'
              f'<stop offset="0" stop-color="{g[0]}" stop-opacity="{t["glow"]}"/>'
              f'<stop offset="1" stop-color="{g[0]}" stop-opacity="0"/></radialGradient>'
              f'<radialGradient id="{pfx}shad" cx=".5" cy=".5" r=".5">'
              f'<stop offset="0" stop-color="#000" stop-opacity="{t["shadow"]}"/>'
              f'<stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>'
              f'<filter id="{pfx}blur" x="-30%" y="-30%" width="160%" height="160%">'
              f'<feGaussianBlur stdDeviation="4"/></filter>')
    return s


def mark_body(pfx: str, t: dict, detail: str = "full") -> str:
    """The mark's drawing (no <svg>, no <defs>): the left half, then its
    mirror through <use>."""
    full = detail == "full"
    paths = {l[0]: d(leaf_path(l)) for l in LEAVES}
    ids = [l[0] for l in LEAVES]
    half = ""
    for i, l in enumerate(LEAVES):
        name, kind = l[0], l[1]
        fill = f"url(#{pfx}{'gold' if kind == 'gold' else 'navy'})"
        half += f'<path d="{paths[name]}" fill="{fill}"/>'
        if full and i > 0:
            op = 0.34 if kind == "gold" else 0.5
            half += (f'<g clip-path="url(#{pfx}c{name})"><path d="{paths[ids[i-1]]}" '
                     f'fill="#000" opacity="{op}" filter="url(#{pfx}blur)" '
                     f'transform="translate(-2 9)"/></g>')
        half += f'<path d="{paths[name]}" fill="url(#{pfx}gut)"/>'
        if full:
            rim = t["rim"] if kind == "gold" else t["rim_navy"]
            op = t["rim_op"] if kind == "gold" else 0.55
            half += (f'<path d="{d_open(top_edge(l))}" fill="none" stroke="{rim}" '
                     f'stroke-width="1.3" stroke-linecap="round" opacity="{op}"/>')
    half += f'<path d="{d(base_path())}" fill="url(#{pfx}navy)"/>'
    out = ""
    if full:
        out += (f'<ellipse cx="0" cy="12" rx="215" ry="16" fill="url(#{pfx}shad)"/>'
                f'<rect x="-200" y="-250" width="400" height="300" fill="url(#{pfx}glow)"/>')
    out += f'<g id="{pfx}half">{half}</g>'
    out += f'<use href="#{pfx}half" transform="scale(-1 1)"/>'
    return out


def clip_defs(pfx: str) -> str:
    return "".join(f'<clipPath id="{pfx}c{l[0]}"><path d="{d(leaf_path(l))}"/></clipPath>'
                   for l in LEAVES)


def mark_inner(pfx: str, theme: str = "light", detail: str = "full") -> str:
    t = THEMES[theme]
    full = detail == "full"
    return (f"<defs>{defs(pfx, t, full=full)}{clip_defs(pfx) if full else ''}</defs>"
            + mark_body(pfx, t, detail))


def header_svg(width: int = 38) -> str:
    """The mark for the page header: small detail, colours from CSS.

    The stops carry classes (hmg0..hmg3, hmn0..hmn2) that app.css fills from
    the theme, so this one drawing is navy and gold on the cream ground and
    the lifted blue and brighter gold on the dark one.
    """
    x, y, w, h = BOUNDS
    height = round(width * h / w)
    t = LIGHT
    body = mark_body("hm", t, "small")
    inner = f'<defs>{defs("hm", t, css=True, full=False)}</defs>{body}'
    return (f'<svg viewBox="{_n(x)} {_n(y)} {_n(w)} {_n(h)}" width="{width}" '
            f'height="{height}" aria-hidden="true">{inner}</svg>')


# --------------------------------------------------------------------------
# Whole files
# --------------------------------------------------------------------------
def mark_svg(theme: str = "light", detail: str = "full", ground: str | None = None) -> str:
    """The mark alone, as a standalone file. VIEW is the viewBox; a ground
    ("cream", "white" or "navy") adds a background rectangle."""
    x, y, w, h = VIEW
    bg = _ground(ground, x, y, w, h)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{_n(x)} {_n(y)} {_n(w)} {_n(h)}" '
            f'width="{_n(w)}" height="{_n(h)}" role="img" aria-label="The Book">'
            f'<title>The Book</title>{bg[0]}{mark_inner("k", theme, detail)}{bg[1]}</svg>\n')


def _ground(ground, x, y, w, h):
    if ground is None:
        return "", ""
    if ground == "navy":
        a, b, c = NAVY_GROUND
        defs_ = (f'<defs><radialGradient id="kbg" gradientUnits="userSpaceOnUse" '
                 f'cx="{x + w/2}" cy="{y + h*0.42}" r="{max(w, h)*0.75}">'
                 f'<stop offset="0" stop-color="{a}"/><stop offset=".6" stop-color="{b}"/>'
                 f'<stop offset="1" stop-color="{c}"/></radialGradient></defs>')
        return defs_ + f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#kbg)"/>', ""
    col = {"cream": CREAM, "white": "#FFFFFF"}[ground]
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{col}"/>', ""


def tile_svg(size: int = 64, rx: int = 14) -> str:
    """The mark on a navy tile, for the browser tab: small detail, dark
    theme, no filters, so it stays under a few kilobytes (the offline copy
    inlines it as a data: URL)."""
    pad = 1.0 / 8.0
    x, y, w, h = BOUNDS
    k = size * (1 - 2 * pad) / w
    cx = size / 2
    cy = size / 2
    mx = x + w / 2
    my = y + h / 2
    a, b, c = NAVY_GROUND
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
            f'width="{size}" height="{size}" role="img" aria-label="The Book">'
            f'<title>The Book</title>'
            f'<defs><linearGradient id="tg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{c}"/>'
            f'</linearGradient></defs>'
            f'<rect width="{size}" height="{size}" rx="{rx}" fill="url(#tg)"/>'
            f'<g transform="translate({_n(cx - mx*k)} {_n(cy - my*k)}) scale({k:.4f})">'
            f'{mark_inner("t", "dark", "small")}</g></svg>\n')
