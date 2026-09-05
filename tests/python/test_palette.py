#!/usr/bin/env python3
"""The palette, against the contrast it has to clear.

Colour is the one part of a design that can be checked rather than argued
about, and it is the part that rots quietly: a token nudged half a step
lighter to look better on the designer's screen is a paragraph a reader with
low vision can no longer read, and nothing goes red.

--ink-faint was #837a89 for the life of this stylesheet. It measures 3.34:1
on the page and 2.99:1 on the ground a table row takes under the pointer --
below WCAG AA for body text at every size it is used at, and below the 3:1
floor that applies to anything visible at all on that last ground. It
carries .muted, .tiny, the crumbs, the era dates, the work meta, the thread
counts and every table head, which is most of the small type on the site.

So the rule is written down here rather than left as an intention. Every ink
in the palette must clear 4.5:1 on every ground in the same palette, in both
the light and the dark; light and dark are checked separately because they
are separate palettes and neither may be the poor relation of the other.
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSS = os.path.join(ROOT, "docs", "assets", "app.css")

# The floor for ordinary body text. The site sets .tiny at .78rem and .muted
# at .9rem, so nothing here qualifies for the large-text exemption.
AA_TEXT = 4.5
# Anything that is a border or a mark rather than a letter.
AA_NONTEXT = 3.0

INKS = ["ink", "ink-soft", "ink-faint", "accent", "rubric"]
GROUNDS = ["paper", "paper-2", "raised"]
# Ruled, not written: the gilt border down a callout, which sits on paper-2.
BORDERS = [("gilt", "paper-2")]
# A badge is its own ground and its own ink.
BADGES = [("good", "good-bg"), ("warn", "warn-bg"), ("fix", "fix-bg")]


def channel(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b))


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def palettes():
    """The light palette and the dark one, read out of the stylesheet.

    Light is the bare :root block. Dark is written twice on purpose -- once
    under the media query and once under [data-theme="dark"], because the
    theme can be inherited or chosen -- and the two are checked against each
    other here as well, since a palette maintained in two places is a palette
    that will eventually disagree with itself.
    """
    with open(CSS, encoding="utf-8") as fh:
        css = fh.read()

    def block(pattern):
        m = re.search(pattern, css, re.S | re.M)
        if not m:
            return None
        return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;",
                               m.group(1)))

    light = block(r"^:root\s*\{(.*?)\n\}")
    media = block(r'@media \(prefers-color-scheme: dark\).*?'
                  r':root:not\(\[data-theme="light"\]\)\s*\{(.*?)\n  \}')
    chosen = block(r'^:root\[data-theme="dark"\]\s*\{(.*?)\n\}')
    return light, media, chosen


class ThePaletteIsReadable(unittest.TestCase):

    def setUp(self):
        self.light, self.media, self.chosen = palettes()
        for name, pal in (("light", self.light), ("dark (media)", self.media),
                          ("dark (chosen)", self.chosen)):
            self.assertIsNotNone(
                pal, f"the {name} palette is no longer a block this test can "
                     f"read out of app.css; rewrite the test or restore it")
            # A regex that matched but found no tokens would pass every check
            # below by having nothing to check, which is the failure mode of
            # a test that reads its subject out of a file.
            self.assertGreater(
                len(pal), 15,
                f"only {len(pal)} colours were read out of the {name} "
                f"palette, so the checks below are running on almost nothing")

    def each(self):
        """Light, and dark as it is actually written under the media query.

        The dark block inherits everything it does not restate, so it is read
        as the light palette with the dark one laid over it -- which is what
        the browser does.
        """
        yield "light", self.light
        merged = dict(self.light)
        merged.update(self.media)
        yield "dark", merged

    def test_the_two_dark_blocks_say_the_same_thing(self):
        self.assertEqual(
            self.media, self.chosen,
            "the inherited dark palette and the chosen one have drifted "
            "apart; a reader who picks dark and a reader whose system is "
            "dark would now see different colours")

    def test_every_ink_clears_aa_on_every_ground(self):
        failures = []
        for theme, pal in self.each():
            for ink in INKS:
                for ground in GROUNDS:
                    got = contrast(pal[ink], pal[ground])
                    if got < AA_TEXT:
                        failures.append(
                            f"{theme}: --{ink} on --{ground} is {got:.2f}:1, "
                            f"under {AA_TEXT}")
        self.assertEqual(failures, [], "\n" + "\n".join(failures))

    def test_every_badge_is_legible_on_its_own_ground(self):
        failures = []
        for theme, pal in self.each():
            for ink, ground in BADGES:
                got = contrast(pal[ink], pal[ground])
                if got < AA_TEXT:
                    failures.append(
                        f"{theme}: --{ink} on --{ground} is {got:.2f}:1, "
                        f"under {AA_TEXT}")
        self.assertEqual(failures, [], "\n" + "\n".join(failures))

    def test_every_rule_drawn_in_colour_can_be_seen(self):
        failures = []
        for theme, pal in self.each():
            for ink, ground in BORDERS:
                got = contrast(pal[ink], pal[ground])
                if got < AA_NONTEXT:
                    failures.append(
                        f"{theme}: --{ink} on --{ground} is {got:.2f}:1, "
                        f"under {AA_NONTEXT}")
        self.assertEqual(failures, [], "\n" + "\n".join(failures))


class NoRuleSetsALiteralOnATokenGround(unittest.TestCase):
    """The hole the class above left open.

    Checking every ink token against every ground token proves the palette is
    internally sound and proves nothing about a rule that ignores the palette.
    Six rules did: "background: var(--accent); color: #fff". White on the
    accent measures 10.5:1 in the light theme and 2.30:1 in the dark one,
    where the accent is a pale pink -- and 1.72:1 on the hover accent, which
    is a button whose label has effectively gone. Among them were the skip
    link, which is the first thing a keyboard user reaches, and the chip
    carrying "Open in Google Maps".

    So the literals are read out of the stylesheet and measured against the
    token behind them, in both themes.
    """

    LITERALS = {"#fff": "#ffffff", "#ffffff": "#ffffff",
                "#000": "#000000", "#000000": "#000000",
                "white": "#ffffff", "black": "#000000"}

    def setUp(self):
        with open(CSS, encoding="utf-8") as fh:
            self.css = fh.read()
        self.light, self.media, _chosen = palettes()

    def rules(self):
        """Every rule body, with @media print left out: a printed page is
        white paper and a literal is the right answer there."""
        text = re.sub(r"/\*.*?\*/", "", self.css, flags=re.S)
        text = re.sub(r"@media print\s*\{.*?\n\}", "", text, flags=re.S)
        return re.findall(r"\{([^{}]*)\}", text)

    def test_a_literal_colour_is_legible_on_the_token_behind_it(self):
        failures = []
        for body in self.rules():
            ground = re.search(r"background(?:-color)?:\s*var\((--[a-z0-9-]+)\)", body)
            ink = re.search(r"(?<!-)color:\s*(#[0-9a-fA-F]{3,6}|white|black)\s*[;}]", body)
            if not ground or not ink:
                continue
            literal = self.LITERALS.get(ink.group(1).lower())
            if not literal:
                continue
            token = ground.group(1)[2:]
            dark = dict(self.light)
            dark.update(self.media)
            for theme, palette in (("light", self.light), ("dark", dark)):
                if token not in palette:
                    continue
                got = contrast(literal, palette[token])
                if got < AA_TEXT:
                    failures.append(
                        f"{theme}: {ink.group(1)} on --{token} is {got:.2f}:1, "
                        f"under {AA_TEXT} -- use var(--paper) instead")
        self.assertEqual(failures, [], "\n" + "\n".join(failures))


class TheBrowserIsToldTheRightColour(unittest.TestCase):
    """theme-color paints the phone's address bar, and a browser reads it
    before any stylesheet, so it cannot be var(--accent) and has to be spelt
    out. Spelt-out values drift: this one said #6b2d5b while the accent it
    is meant to be had been #632a55 for as long as the file had existed."""

    def test_theme_color_is_the_light_accent(self):
        with open(os.path.join(ROOT, "docs", "index.html"), encoding="utf-8") as fh:
            html = fh.read()
        stated = re.search(r'name="theme-color"\s+content="(#[0-9a-fA-F]{6})"', html)
        self.assertIsNotNone(
            stated, "docs/index.html no longer states a theme-color")
        light, _media, _chosen = palettes()
        self.assertEqual(stated.group(1).lower(), light["accent"].lower())

    def test_the_generated_pages_are_told_the_same_colour(self):
        """The front page is one page; tools/build_pages.py writes 2,709 more.

        Its copy of this value was spelt out beside the other one and was not
        corrected when the other one was, so every generated page painted the
        address bar #6b2d5b while the page they all link to painted it
        #632a55. Nothing compared them, because the test above reads only
        docs/index.html. This reads the generator.
        """
        with open(os.path.join(ROOT, "tools", "build_pages.py"),
                  encoding="utf-8") as fh:
            source = fh.read()
        stated = re.search(
            r'theme-color" content="(#[0-9a-fA-F]{6})"', source)
        self.assertIsNotNone(
            stated, "tools/build_pages.py no longer writes a theme-color")
        light, _media, _chosen = palettes()
        self.assertEqual(stated.group(1).lower(), light["accent"].lower())


if __name__ == "__main__":
    unittest.main()
