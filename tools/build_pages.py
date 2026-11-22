#!/usr/bin/env python3
"""One real HTML page per work and per chapter, so the library can be found.

    python3 tools/build_pages.py docs

The reader is a hash-routed single page. A fragment is never sent to a
server, so every one of the 174 works and 2,655 chapters lives at a URL that
no crawler can ask for and no crawler can index: Google sees the shell, once,
with no scripture on it at all. This writes the other half -- a plain page per
chapter, with the text really in the HTML -- and a contents page that links to
all of them, which is the hub a crawler starts from.

Nothing here is a second site. The pages load docs/assets/app.css and use the
reader's own class names, so they are the same object seen without JavaScript,
and each one carries a link into the reader for anyone who wants the search,
the map and the definitions.

There is deliberately no script that redirects into the reader. A page whose
text is replaced the moment JavaScript runs is what a search engine calls
cloaking, and the penalty for it is the whole site.

Output, all of it gitignored and rebuilt by the deploy:

    <out>/read/<work>/index.html            the work
    <out>/read/<work>/<slug>/index.html     the chapter
    <out>/contents/index.html               the crawl hub
    <out>/sitemap.xml  robots.txt  404.html

Standard library only, like every other script here.
"""

import html
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dates                                                # noqa: E402

BASE = "https://thebookandme.com"

# Everything after the host in BASE: empty on the custom domain, "/The-Book"
# on the project Pages address it used to be served from. robots.txt takes
# site-relative paths rather than absolute ones, so the rule below has to be
# built from this rather than spelt out beside it and left to rot.
PREFIX = urllib.parse.urlsplit(BASE).path.rstrip("/")
SITE = "The Book"

# The name the site goes by in a search result: the domain says "The Book and
# Me", and a chapter title that names it is the one a reader can match to the
# address they were given.
BRAND = "The Book and Me"

# The address of the Enoch reading plan, relative to the site root.
ENOCH_PLAN = "enoch-reading-plan"

# The last day the generated text pages changed in substance (not merely
# rebuilt). Bump it only when what a chapter page says changes.
PAGES_DATE = "2026-11-21"

# The reader's own title, for the pages that are not a single chapter.
FULL_TITLE = "The Book — Biblical and Related Ancient Texts in Order of Composition"


# ---------------------------------------------------------------- text

_SMALL = re.compile(r"^(of|the|and|to|in|a|on|for|with|from|by|as|at|its)$")
_WORD = re.compile(r"[^\s\-/(]+")
_SHOUT = re.compile(r"\b(i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|bce|ce|nt|ot|web)\b",
                    re.IGNORECASE)


def title_case(s):
    """The reader's titleCase(), ported from docs/assets/app.js.

    Kept identical on purpose: a work whose heading here reads differently
    from its heading in the reader is two titles for one thing, which is
    exactly what these pages exist to stop.
    """
    def word(m):
        w = m.group(0)
        if m.start() > 0 and _SMALL.match(w):
            return w
        return w[:1].upper() + w[1:]

    return _SHOUT.sub(lambda m: m.group(0).upper(), _WORD.sub(word, s.lower()))


def _words(s):
    """The lowercase word sequence of a string, punctuation dropped, so that
    "SIMILITUDE 1" and "Similitude 1" are the same thing said twice."""
    return [w for w in re.split(r"[^a-z0-9]+", s.lower()) if w]


def chapter_heading(work_title, label):
    """"Genesis 1", not "Genesis Chapter 1" and not "Jubilees JUBILEES 1".

    Most labels are "Chapter 7" and want the work's name in front of them.
    Some two hundred and fifty -- Jubilees, the Enoch volumes, the Testaments
    -- already carry it, and putting the name in front of those says it twice.
    So a leading run of words the work's title already contains is dropped,
    but only when the run really is the name being repeated: a leading "The"
    is not, and the last word is never eaten, or a label that is nothing but
    the repeat would leave the chapter with no number.

    chapterTitle() in docs/assets/app.js is the same rule. It has to be: this
    is the title a search engine indexes and that one is the title the reader
    sees in their tab, and they are the same chapter.
    """
    rest = re.sub(r"^Chapter\s+", "", label, flags=re.IGNORECASE).strip()

    # The label is the whole title and nothing else -- Hermas's "Similitude 1"
    # inside the work "SIMILITUDE 1". There is no number to keep hold of, so
    # the repeat is the entire label and the title alone is the answer. Only
    # safe because such a work is a single chapter; the assertion in build()
    # is what keeps that true.
    if _words(rest) == _words(work_title):
        return title_case(work_title)

    in_title = set(_words(work_title))

    words = rest.split()
    run = 0
    named = False
    # Never as far as the last word. "1 ENOCH 83" belongs to "1 ENOCH: DREAM
    # VISIONS ... (chapters 83-108)", which contains 83 as well as 1 and
    # ENOCH: consuming the lot would leave every chapter of that volume with
    # the same title, which is the bug this whole helper exists to fix.
    for i in range(max(0, len(words) - 1)):
        bare = re.sub(r"[^a-z0-9]", "", words[i].lower())
        if not bare or bare not in in_title:
            break
        run = i + 1
        if len(bare) >= 4:
            named = True
    if named:
        rest = re.sub(r"^[^A-Za-z0-9]+", "", " ".join(words[run:])).strip()

    return (title_case(work_title) + (" " + rest if rest else "")).strip()


_ENOCH_WORK = re.compile(r"^([123])-enoch-")


def enoch_book(work_id):
    """"1", "2" or "3" for a work that is part of a book of Enoch, else None."""
    m = _ENOCH_WORK.match(work_id or "")
    return m.group(1) if m else None


def short_heading(meta, c, heading):
    """The chapter as a person searching for it would type it.

    "1 Enoch Chapter 84", not "1 Enoch: Dream Visions and the Epistle of
    Enoch (Chapters 83-108) 84": the volume's sections are how the library
    files the book, and nobody searches for them. Every other work keeps the
    heading chapter_heading() gives, which is already what people type.
    """
    book = enoch_book(meta.get("id"))
    n = c.get("n")
    if book and isinstance(n, int) and n > 0:
        return "%s Enoch Chapter %d" % (book, n)
    return heading


def page_title(short):
    """The <title> of a chapter page. One rule for every chapter."""
    return "%s – Read Along | %s" % (short, BRAND)


_SENTENCE_END = re.compile(r"[.!?][\u201d\u2019\"')\]]*(?=\s|$)")


_ABBREV = {"c", "ca", "cf", "ch", "chs", "v", "vv", "vol", "vols", "e.g", "i.e",
           "st", "mr", "dr", "no", "ed", "eds", "trans", "lit", "viz", "etc"}


def whole_sentences(text, limit):
    """The longest run of whole sentences from the start of text that fits in
    limit, or "" if not even the first one does."""
    text = " ".join(str(text).split())
    if len(text) <= limit and _SENTENCE_END.search(text[-3:] + " "):
        return text
    best = ""
    for m in _SENTENCE_END.finditer(text):
        if m.end() > limit:
            break
        word = text[:m.start()].rsplit(" ", 1)[-1].lower().lstrip("(")
        if word in _ABBREV or (len(word) == 1 and word.isalpha()):
            continue            # "c. 590 BCE", "cf. Isaiah", "v. 21": not an end
        best = text[:m.end()]
    return best


def describe(text, limit=160):
    """A description that reads as finished: whole sentences where they fit
    (a snippet that trails off in an ellipsis looks broken in a search result
    and a link preview), cut at a word only when one sentence is too long."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    whole = whole_sentences(text, limit)
    if len(whole) >= 20:
        return whole
    cut = text[:limit]
    space = cut.rfind(" ")
    if space > 40:
        cut = cut[:space]
    return cut.rstrip(" ,;:.—-") + "…"


def chapter_description(short, by, opening, places, limit=160):
    """A chapter's meta description, always complete. The opening sentence(s)
    when they fit; otherwise a plain account of what is on the page, naming as
    many of the chapter's places as fit."""
    lead = "Read %s%s free online: " % (short, by)
    whole = whole_sentences(opening, limit - len(lead))
    if len(whole) >= 25:
        return lead + whole
    base = "Read %s%s free online, with a note on when it was written" % (short, by)
    for n in range(min(len(places), 6), 0, -1):
        names = places[:n]
        lst = names[0] if n == 1 else ", ".join(names[:-1]) + " and " + names[-1]
        cand = "%s and the places it names: %s." % (base, lst)
        if len(cand) <= limit:
            return cand
    return base + "."


def e(s):
    return html.escape("" if s is None else str(s), quote=True)


# ---------------------------------------------------------------- slugs

def chapter_slugs(meta, chapters):
    """The addresses of this work's chapters, read rather than worked out.

    They used to be computed here, on the way to naming a file, and thrown
    away -- so the reader, which is where a person actually presses "copy
    link to this verse", had no way to name the page this script had just
    built for that purpose and handed out its own array index in a fragment
    instead. tools/build_slugs.py now writes the list into the manifest, both
    halves read it from there, and there is one list rather than two rules.
    """
    slugs = meta.get("slugs")
    if slugs is None:
        raise SystemExit(
            "%s has no chapter addresses in the manifest -- run "
            "tools/build_slugs.py (./tools/build.sh does)" % meta["id"])
    if len(slugs) != len(chapters):
        raise SystemExit("%s: %d addresses for %d chapters"
                         % (meta["id"], len(slugs), len(chapters)))
    if len(set(slugs)) != len(slugs):
        raise SystemExit("%s: two chapters share an address" % meta["id"])
    return slugs


# ---------------------------------------------------------------- the shell

def head(title, description, canonical, depth, extra_head="", og_type="article"):
    """Everything above <body>, with the asset paths written for this depth."""
    up = "../" * depth
    return "\n".join([
        "<!DOCTYPE html>",
        '<html lang="en" data-theme="auto">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>%s</title>" % e(title),
        '<meta name="description" content="%s">' % e(description),
        '<link rel="canonical" href="%s">' % e(canonical),
        '<link rel="stylesheet" href="%sassets/app.css">' % up,
        '<link rel="icon" href="%sassets/favicon.svg" type="image/svg+xml">' % up,
        '<link rel="apple-touch-icon" href="%sassets/icon-180.png">' % up,
        # Most phones reach the library through one of these pages rather
        # than through the front page, so the manifest has to be reachable
        # from here too or there is nothing for Android to offer to install.
        # start_url in it is relative to the manifest, not to this page, so
        # installing from a chapter still opens the reader at its root.
        '<link rel="manifest" href="%ssite.webmanifest">' % up,
        '<meta name="mobile-web-app-capable" content="yes">',
        '<meta name="apple-mobile-web-app-capable" content="yes">',
        '<meta name="apple-mobile-web-app-status-bar-style" content="default">',
        '<meta name="apple-mobile-web-app-title" content="The Book">',
        # The brand navy, spelt out because a browser reads it before any
        # stylesheet. docs/index.html carries the same two values and
        # tests/python/test_webmanifest.py holds both copies to the manifest.
        '<meta name="theme-color" content="#12295f" media="(prefers-color-scheme: light)">',
        '<meta name="theme-color" content="#0a1d49" media="(prefers-color-scheme: dark)">',
        '<meta name="referrer" content="strict-origin-when-cross-origin">',
        # The download URL redirects onto ia*.us.archive.org and
        # dn*.ca.archive.org. A policy that names only archive.org itself
        # blocks that hop, so the chapter index and the recording never
        # arrive. *.archive.org is the CDN. blob: is the retyped file
        # Firefox will decode; the archive serves .opus as
        # application/octet-stream.
        '<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; base-uri \'self\'; form-action \'self\'; object-src \'none\'; img-src \'self\' data:; style-src \'self\' \'unsafe-inline\'; script-src \'self\' https://static.cloudflareinsights.com; worker-src \'self\'; manifest-src \'self\'; connect-src \'self\' https://cloudflareinsights.com https://archive.org https://*.archive.org; media-src \'self\' blob: https://archive.org https://*.archive.org">',
        # Cloudflare Web Analytics, cookieless; allowed by the policy above.
        '<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon=\'{"token": "8f4f21d9a22040fbb72ceb3302ecb4ea"}\'></script>',
        '<meta property="og:type" content="%s">' % e(og_type),
        '<meta property="og:site_name" content="%s">' % e(SITE),
        '<meta property="og:title" content="%s">' % e(title),
        '<meta property="og:description" content="%s">' % e(description),
        '<meta property="og:url" content="%s">' % e(canonical),
        '<meta property="og:image" content="%s/assets/og-card.jpg">' % BASE,
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="The Book and Me: an open book by candlelight under a night sky">',
        '<meta property="og:locale" content="en_US">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:title" content="%s">' % e(title),
        '<meta name="twitter:description" content="%s">' % e(description),
        '<meta name="twitter:image" content="%s/assets/og-card.jpg">' % BASE,
        extra_head,
        "</head>",
    ])


def topbar(depth):
    """The reader's header, with the links that have a real page pointing at
    one and the rest going to the reader's own routes."""
    up = "../" * depth
    # Timeline and Threads have real pages of their own now, so they point at
    # them rather than at a fragment, the way Contents always has. A link to
    # #/threads from a static page is a link a crawler cannot follow and a
    # preview cannot unfurl, which for the eleven threads -- the one thing
    # here a canonical Bible cannot do -- meant the argument of the site was
    # the only part of it with no indexable address.
    nav = [
        ("%stimeline/" % up, "Timeline"),
        ("%sthreads/" % up, "Threads"),
        ("%scontents/" % up, "Contents"),
        ("%s#/search" % up, "Search"),
        ("%s#/canons" % up, "Canons"),
        ("%s#/accuracy" % up, "Accuracy"),
    ]
    links = "\n    ".join('<a href="%s">%s</a>' % (e(h), e(t)) for h, t in nav)
    return """<a class="skip" href="#main">Skip to content</a>

<header class="topbar">
  <a class="brand" href="{up}" aria-label="The Book, home">
    <span class="brand-text">
      <span class="brand-name">The Book</span>
      <span class="brand-sub">in the order it was written</span>
    </span>
  </a>
  <nav class="nav" aria-label="Main">
    {links}
  </nav>
</header>
""".format(up=e(up or "./"), links=links)


def footer(depth, what="a plain page of one chapter"):
    up = "../" * depth
    return """<footer class="foot">
  <p class="sleep-yt"><a href="https://www.youtube.com/@thebookandme/live" rel="noopener noreferrer" target="_blank">🌙 Listen live on YouTube</a> — the Bible read aloud, live around the clock.</p>
  <p>
    <strong>The texts are public domain</strong> — the World English Bible with
    Deuterocanon, R. H. Charles's 1917 Enoch and Jubilees, Morfill's 2 Enoch
    (1896) and Odeberg's 3 Enoch (1928), and the Ante-Nicene Fathers of 1870
    and 1885. The <a href="{up}#/accuracy">accuracy report</a>
    sets out what was verified, what was corrected, and what is still missing.
  </p>
  <p class="muted foot-links">
    <a href="{up}about/">About</a> · <a href="{up}contact/">Contact</a> ·
    <a href="{up}privacy/">Privacy</a> · <a href="{up}press/">Press and credits</a> ·
    <a href="{up}#/account">Account (optional)</a>
    — read aloud by an AI voice.
  </p>
  <p class="muted">
    This is {what}. The
    <a href="{up}">reader</a> has the search, the map, the word definitions,
    the saved verses and the reading aloud.
  </p>
</footer>
</body>
</html>
""".format(up=e(up or "./"), what=e(what))


def ld(obj):
    return ('<script type="application/ld+json">%s</script>'
            % json.dumps(obj, ensure_ascii=False, separators=(",", ":")))


def pager(prev, nxt, big=False, top=False):
    """Real anchors, because a crawler follows anchors and nothing else.

    The arrows are the reader's, so a keyboard reader arriving from there
    finds the same two shapes in the same two corners.

    big is the chapter pages' version: three of every four readers arrive on
    a phone, so the two buttons are a thumb's width tall and say which way
    they go. top is a second copy above the text, which carries no rel --
    one rel="next" per page is what a crawler and the tests both expect.
    """
    cls = "pager" + (" pager-big" if big else "") + (" pager-top" if top else "")
    parts = ['<nav class="%s" aria-label="%s">'
             % (cls, "Chapters, top" if top else "Chapters")] if big else ['<div class="pager">']
    rel_p = "" if top else ' rel="prev"'
    rel_n = "" if top else ' rel="next"'
    if prev:
        inner = ('<span class="dir">← Previous</span><span class="to">%s</span>' % e(prev[1])
                 if big else "← %s" % e(prev[1]))
        parts.append('<a%s href="%s">%s</a>' % (rel_p, e(prev[0]), inner))
    else:
        parts.append('<span class="spacer"></span>')
    if nxt:
        inner = ('<span class="dir">Next →</span><span class="to">%s</span>' % e(nxt[1])
                 if big else "%s →" % e(nxt[1]))
        parts.append('<a%s href="%s">%s</a>' % (rel_n, e(nxt[0]), inner))
    parts.append("</nav>" if big else "</div>")
    return "\n".join(parts)


def rel_links(prev, nxt):
    out = []
    if prev:
        out.append('<link rel="prev" href="%s">' % e(prev[0]))
    if nxt:
        out.append('<link rel="next" href="%s">' % e(nxt[0]))
    return "\n".join(out)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# ---------------------------------------------------------------- pages

def crumbs(depth, section, work=None):
    up = "../" * depth
    bits = ['<div class="crumbs">',
            # Not "Timeline": that name belongs to /timeline/, which draws the
            # library against a scale. This is the front page.
            '<a href="%s">The Book</a> → ' % e(up or "./"),
            '<a href="%scontents/">Contents</a>' % e(up)]
    if section:
        name = ((("Section " + section["roman"] + ". ") if section.get("roman") else "")
                + title_case(section.get("name") or section.get("title") or "")
                + ((" · " + section["dates"]) if section.get("dates") else ""))
        bits.append(" → <span>%s</span>" % e(name))
    if work:
        bits.append(' → <a href="%s">%s</a>' % (e(work[0]), e(work[1])))
    bits.append("</div>")
    return "".join(bits)


def strip_html(work_id, chapters, slugs, current, depth):
    """The chapter strip, every entry a real link. This is what makes a work
    page worth crawling: 2,655 addresses reachable in two hops from the root."""
    if len(chapters) < 2:
        return ""
    up = "../" * (depth - 2)          # back up to /read/<work>/
    out = ['<nav class="chapter-strip" aria-label="Chapters">']
    for c, slug in zip(chapters, slugs):
        n = c.get("n")
        label = str(n) if isinstance(n, int) and n > 0 else (
            re.sub(r"^.*?(\d+).*$", r"\1", c.get("label") or "") or "·")
        current_attr = ' aria-current="true"' if slug == current else ""
        out.append('<a href="%s%s/" title="%s"%s>%s</a>'
                   % (e(up), e(slug), e(c.get("label") or ""), current_attr, e(label)))
    out.append("</nav>")
    return "\n".join(out)


# ---------------------------------------------------------------- chapter context
#
# Google crawled the chapter pages and declined to index them ("Crawled -
# currently not indexed"): a page that is nothing but public-domain text is the
# same page as on a thousand other sites. What this volume has that they do not
# is its own apparatus -- when each work was written, the places each chapter
# names, and the threads that pass through it. build() fills this in from the
# data files the reader already ships, and chapter_page() prints it under the
# text, so each page carries something only this site says.
CONTEXT = {"mentions": {}, "places": {}, "threads": {}}


def load_context(data):
    import glob
    ctx = {"mentions": {}, "places": {}, "threads": {}}
    try:
        with open(os.path.join(data, "mentions.json"), encoding="utf-8") as fh:
            ctx["mentions"] = json.load(fh)
    except (OSError, ValueError):
        pass
    for f in sorted(glob.glob(os.path.join(data, "places", "*.json"))):
        try:
            with open(f, encoding="utf-8") as fh:
                ctx["places"].update(json.load(fh))
        except (OSError, ValueError):
            pass
    try:
        with open(os.path.join(data, "threads.json"), encoding="utf-8") as fh:
            for t in json.load(fh):
                for stop in t.get("stops") or []:
                    key = "%s/%s" % (stop.get("work"), stop.get("chapter"))
                    ctx["threads"].setdefault(key, []).append((t, stop))
    except (OSError, ValueError):
        pass
    CONTEXT.update(ctx)


def place_label(key):
    p = CONTEXT["places"].get(key) or {}
    name = re.sub(r"\s+\d+$", "", p.get("name") or title_case(key))
    modern = (p.get("modern") or "").strip()
    return name, modern


def breadcrumb_ld(items):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": n + 1, "name": name, "item": url}
            for n, (name, url) in enumerate(items)],
    }


def chapter_context(meta, section, i, slug, depth):
    """The block under a chapter's text: when the work was written, the places
    the chapter names, and the threads that stop here. Empty if there is
    nothing true to say."""
    up = "../" * depth
    name = title_case(meta["title"])
    out = []
    note = meta.get("note") or []
    sec = ""
    if section:
        sec = ((("Section " + section["roman"] + ", ") if section.get("roman") else "")
               + title_case(section.get("name") or section.get("title") or "")
               + ((" (" + section["dates"] + ")") if section.get("dates") else ""))
    when = []
    if sec:
        when.append("In this volume %s sits in %s." % (name, sec))
    if note:
        when.append(describe(note[0], 360))
    if when:
        out.append('<p><strong>When it was written.</strong> %s '
                   '<a href="../">More on %s</a> · '
                   '<a href="%stimeline/">See it on the timeline</a></p>'
                   % (e(" ".join(when)), e(name), e(up)))

    keys = CONTEXT["mentions"].get("%s/%d" % (meta["id"], i)) or []
    seen, names = set(), []
    for k in keys:
        nm, modern = place_label(k)
        if nm.lower() in seen:
            continue
        seen.add(nm.lower())
        names.append(e(nm) + ((" <span class=\"muted\">(%s)</span>" % e(modern))
                              if modern else ""))
    if names:
        out.append('<p><strong>Places named in this chapter.</strong> %s. '
                   '<a href="%s#/read/%s/%d">See them on the map in the reader</a></p>'
                   % (", ".join(names), e(up), e(meta["id"]), i))

    for t, stop in CONTEXT["threads"].get("%s/%d" % (meta["id"], i)) or []:
        why = stop.get("why") or ""
        out.append('<p><strong>A stop on the thread '
                   '<a href="%sthreads/%s/">%s</a></strong>%s</p>'
                   % (e(up), e(t["id"]), e(t.get("title") or t["id"]),
                      (" — " + e(why)) if why else ""))
    if not out:
        return ""
    return ('<section class="note-block chapter-context" aria-label="About this chapter">\n'
            '<h2>About this chapter</h2>\n' + "\n".join(out) + "\n</section>")


def chapter_page(manifest, section, meta, work, chapters, slugs, i, out_dir):
    c = chapters[i]
    slug = slugs[i]
    work_url = "%s/read/%s/" % (BASE, meta["id"])
    url = "%s/read/%s/%s/" % (BASE, meta["id"], slug)
    heading = chapter_heading(meta["title"], c.get("label") or "")
    short = short_heading(meta, c, heading)
    title = page_title(short)

    verses = c.get("verses") or []
    paras = c.get("paras") or []
    opening = (verses[0]["t"] if verses else (paras[0] if paras else meta["title"]))
    src = (manifest.get("sources") or {}).get(meta.get("source"))
    by = (" (%s)" % src["label"]) if src and meta.get("source") != "web" else ""
    place_names = []
    for k in CONTEXT["mentions"].get("%s/%d" % (meta["id"], i)) or []:
        nm = place_label(k)[0]
        if nm not in place_names:
            place_names.append(nm)
    description = chapter_description(short, by, opening, place_names)

    def near(k):
        return chapter_heading(meta["title"], chapters[k].get("label") or "")
    book = enoch_book(meta["id"])
    prev = (("../%s/" % slugs[i - 1]), short_heading(meta, chapters[i - 1], near(i - 1))) \
        if i > 0 else None
    nxt = (("../%s/" % slugs[i + 1]), short_heading(meta, chapters[i + 1], near(i + 1))) \
        if i < len(chapters) - 1 else None
    # The last chapter of a section of Enoch goes on to the reading plan,
    # which says where the next part is, rather than stopping dead.
    if book and nxt is None:
        nxt = ("../../../%s/" % ENOCH_PLAN, "Enoch reading plan")

    body = [
        '<div class="wrap">',
        crumbs(3, section, ("../", title_case(meta["title"]))),
        '<div class="reader-head">',
        "<h1>%s</h1>" % e(title_case(meta["title"])),
        strip_html(meta["id"], chapters, slugs, slug, 3),
        "</div>",
        pager(prev, nxt, big=True, top=True),
        # Most visitors to a chapter page arrive from a YouTube "read along"
        # link expecting to hear it. The recorded reading lives in the reader,
        # so say so above the text instead of only at the foot of the page.
        '<p class="listen-cta"><a class="chip primary" href="../../../#/read/%s/%d">'
        '\u25b6 Listen to this chapter</a></p>' % (e(meta["id"]), i),
        '<div class="reader">',
        '<h2 class="chapter-title">%s</h2>' % e(c.get("label") or heading),
    ]

    if verses:
        body.append("<p>")
        for v in verses:
            body.append('<span class="v" id="v%s"><span class="vnum">%s</span> %s </span>'
                        % (e(v["v"]), e(v["v"]), e(v["t"])))
        body.append("</p>")
    else:
        for t in paras:
            body.append("<p>%s</p>" % e(t))
        if not paras:
            body.append('<p class="empty">This chapter has no text in the '
                        'public-domain sources this volume is built from.</p>')

    body.append("</div>")
    ctx = chapter_context(meta, section, i, slug, 3)
    if ctx:
        body.append(ctx)

    # The reader's hash routes count chapters from zero, so chapter 1 is
    # #/read/genesis/0. That is a fine internal index and a poor public URL,
    # which is why these pages use the printed number instead -- but the link
    # back into the reader has to speak the reader's own arithmetic.
    body.append('<p><a class="chip" href="../../../#/read/%s/%d">Open in the reader</a> '
                '<a class="chip" href="../">All of %s</a>%s</p>'
                % (e(meta["id"]), i, e(title_case(meta["title"])),
                   (' <a class="chip" href="../../../%s/">Enoch reading plan</a>' % ENOCH_PLAN)
                   if book else ""))

    if src:
        body.append('<div class="apparatus"><strong>Text.</strong> %s. %s</div>'
                    % (e(src.get("label")), e(src.get("detail"))))

    body.append(pager(prev, nxt, big=True))
    if book:
        body.append(signup_form("/read/%s/%s/" % (meta["id"], slug)))
    body.append("</div>")

    schema = {
        "@context": "https://schema.org",
        "@type": "Chapter",
        "name": heading,
        "url": url,
        "description": description,
        "inLanguage": "en",
        "isPartOf": {"@type": "Book", "name": title_case(meta["title"]), "url": work_url},
    }
    if isinstance(c.get("n"), int) and c["n"] > 0:
        schema["position"] = c["n"]

    page = "\n".join([
        head(title, description, url, 3, rel_links(prev, nxt) + "\n" + ld(schema) + "\n"
             + ld(breadcrumb_ld([(SITE, BASE + "/"), ("Contents", BASE + "/contents/"),
                                 (title_case(meta["title"]), work_url), (short, url)]))),
        "<body>",
        topbar(3),
        '<main id="main">',
        "\n".join(body),
        "</main>",
        footer(3),
    ])
    write(os.path.join(out_dir, "read", meta["id"], slug, "index.html"), page)
    return url


def work_page(manifest, section, meta, chapters, slugs, prev_work, next_work, out_dir):
    url = "%s/read/%s/" % (BASE, meta["id"])
    name = title_case(meta["title"])
    title = name + " — " + SITE
    note = meta.get("note") or []
    description = describe(note[0]) if note else ""
    if not description or description.endswith("…"):
        description = describe(
            "%s, in The Book: the library arranged in the order it was written." % name)

    if meta.get("chapters"):
        stats = ("%d %s" % (meta["chapters"],
                            "chapter" if meta["chapters"] == 1 else "chapters")
                 + (" · %s verses" % format(meta["verses"], ",") if meta.get("verses") else "")
                 + " · %s words" % format(meta.get("words") or 0, ","))
    else:
        stats = "described in the volume, no text in the public-domain sources"

    prev = (("../%s/" % prev_work["id"]), title_case(prev_work["title"])) if prev_work else None
    nxt = (("../%s/" % next_work["id"]), title_case(next_work["title"])) if next_work else None

    body = [
        '<div class="wrap">',
        crumbs(2, section),
        '<div class="reader-head">',
        "<h1>%s</h1>" % e(name),
        '<p class="muted">%s</p>' % e(stats),
        "</div>",
    ]
    if note:
        body.append('<div class="note-block">')
        for p in note:
            body.append("<p>%s</p>" % e(p))
        body.append("</div>")

    if chapters:
        body.append("<h2>Chapters</h2>")
        body.append('<nav class="chapter-strip" aria-label="Chapters">')
        for c, slug in zip(chapters, slugs):
            n = c.get("n")
            label = str(n) if isinstance(n, int) and n > 0 else (
                re.sub(r"^.*?(\d+).*$", r"\1", c.get("label") or "") or "·")
            body.append('<a href="%s/" title="%s">%s</a>'
                        % (e(slug), e(c.get("label") or ""), e(label)))
        body.append("</nav>")
        body.append('<p><a class="chip" href="%s/">Start reading: %s</a> '
                    '<a class="chip" href="../../#/read/%s/0">Open in the reader</a></p>'
                    % (e(slugs[0]), e(chapters[0].get("label") or "the first chapter"),
                       e(meta["id"])))
    else:
        body.append('<p class="empty">No text was available from a public-domain '
                    'source, so this work is described rather than printed. The '
                    'accuracy report says why.</p>')

    body.append(pager(prev, nxt))
    body.append("</div>")

    schema = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": name,
        "url": url,
        "description": description,
        "inLanguage": "en",
        "numberOfPages": meta.get("chapters") or 0,
        "isPartOf": {"@type": "CollectionPage", "name": SITE,
                     "url": "%s/contents/" % BASE},
    }

    page = "\n".join([
        head(title, description, url, 2, rel_links(prev, nxt) + "\n" + ld(schema) + "\n"
             + ld(breadcrumb_ld([(SITE, BASE + "/"), ("Contents", BASE + "/contents/"),
                                 (name, url)])),
             og_type="book"),
        "<body>",
        topbar(2),
        '<main id="main">',
        "\n".join(body),
        "</main>",
        footer(2),
    ])
    write(os.path.join(out_dir, "read", meta["id"], "index.html"), page)
    return url


def contents_page(manifest, out_dir):
    """The hub. Every work is a real anchor here, and every work page carries
    a real anchor per chapter, so the whole library is two clicks from this."""
    url = "%s/contents/" % BASE
    totals = manifest.get("totals") or {}
    description = describe(
        "Every work in The Book, in the order it was written: %s works, %s "
        "chapters of the Jewish, Protestant, Catholic, Orthodox and Ethiopian "
        "canons with the apocrypha and the Apostolic Fathers."
        % (format(totals.get("works", 0), ","), format(totals.get("chapters", 0), ",")))

    body = ['<div class="wrap">',
            "<h1>Contents</h1>",
            '<p class="lede">%s</p>' % e(description)]

    for s in manifest["sections"]:
        if not s["works"]:
            continue
        name = ((("%s. " % s["roman"]) if s.get("roman") else "")
                + title_case(s.get("name") or s.get("title") or ""))
        body.append('<div class="era open">')
        body.append("<h2>%s%s</h2>" % (e(name),
                                       e(" · " + s["dates"]) if s.get("dates") else ""))
        if s.get("intro"):
            body.append('<p class="muted">%s</p>' % e(s["intro"]))
        body.append("<ul>")
        for w in s["works"]:
            meta = ("%d %s" % (w["chapters"], "chapter" if w["chapters"] == 1 else "chapters")
                    if w.get("chapters") else "described, no text in the sources")
            body.append('<li><a href="../read/%s/">%s</a> <span class="muted">%s</span></li>'
                        % (e(w["id"]), e(title_case(w["title"])), e(meta)))
        body.append("</ul>")
        body.append("</div>")

    body.append('<p><a class="chip" href="../#/contents">Open in the reader</a></p>')
    body.append("</div>")

    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Contents — " + SITE,
        "url": url,
        "description": description,
        "inLanguage": "en",
        "isPartOf": {"@type": "WebSite", "name": SITE, "url": BASE + "/"},
    }

    page = "\n".join([
        head("Contents — " + SITE, description, url, 1, ld(schema),
             og_type="website"),
        "<body>",
        topbar(1),
        '<main id="main">',
        "\n".join(body),
        "</main>",
        footer(1),
    ])
    write(os.path.join(out_dir, "contents", "index.html"), page)
    return url


# ------------------------------------------------- threads and the timeline
#
# These two are the site's argument, and until now they were the two parts of
# it with no address a crawler, a preview card or a footnote could use. The
# reader has 2,655 chapters at real URLs and eleven threads at fragments --
# which is the wrong way round, because the chapters are in every Bible and
# the threads are the thing this arrangement exists to make possible.


def thread_hub_page(threads, out_dir):
    url = "%s/threads/" % BASE
    description = describe(
        "%d questions followed across the whole collection in the order the "
        "texts were written: where the dead go, whether God wants sacrifice "
        "or justice, where Satan comes from." % len(threads))

    body = ['<div class="wrap">',
            crumbs(1, None),
            "<h1>Threads</h1>",
            '<p class="lede">One question, followed across the whole collection '
            'in the order the texts were written. This is the thing a '
            'chronological arrangement can show and a normal Bible cannot: an '
            'idea being asked, answered, contradicted and answered again over '
            'eight hundred years.</p>',
            '<ul class="thread-list">']
    for t in threads:
        span = t.get("sections") or {}
        meta = "%d passages" % len(t["stops"])
        if span.get("earliest"):
            meta += " · " + (span["earliest"] if span["earliest"] == span["latest"]
                             else "%s to %s" % (span["earliest"], span["latest"]))
        body.append('<li><a href="%s/">%s</a> <span class="muted">%s</span>'
                    '<p class="muted">%s</p></li>'
                    % (e(t["id"]), e(t["title"]), e(meta), e(t["question"])))
    body.append("</ul>")
    body.append('<p><a class="chip" href="../#/threads">Open in the reader</a></p>')
    body.append("</div>")

    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Threads — " + SITE,
        "url": url,
        "description": description,
        "inLanguage": "en",
        "isPartOf": {"@type": "WebSite", "name": SITE, "url": BASE + "/"},
    }
    page = "\n".join([
        head("Threads — " + SITE, description, url, 1, ld(schema),
             og_type="website"),
        "<body>",
        topbar(1),
        '<main id="main">',
        "\n".join(body),
        "</main>",
        footer(1, "the list of threads"),
    ])
    write(os.path.join(out_dir, "threads", "index.html"), page)
    return url


def thread_page(manifest, slugs_by_work, t, out_dir):
    """One thread, with the passages really in the HTML.

    Every stop links to the chapter page for the passage it quotes, which is
    what makes this worth crawling rather than a wall of text: the thread is
    a path through the library and the path is made of anchors.
    """
    url = "%s/threads/%s/" % (BASE, t["id"])
    title = t["title"] + " — " + SITE
    description = describe(t["question"])

    body = ['<div class="wrap">',
            '<div class="crumbs"><a href="../../">The Book</a> → '
            '<a href="../">Threads</a></div>',
            "<h1>%s</h1>" % e(t["title"]),
            '<p class="lede">%s</p>' % e(t["question"]),
            '<ol class="thread">']

    for stop in t["stops"]:
        slug = slugs_by_work.get(stop["work"], [])
        where = ("../../read/%s/%s/" % (stop["work"], slug[stop["chapter"]])
                 if stop["chapter"] < len(slug) else "../../read/%s/" % stop["work"])
        body.append('<li class="stop">')
        body.append('<div class="stop-when"><span class="stop-era">%s</span>'
                    '<span class="stop-date">%s</span></div>'
                    % (e(stop["section"] or "＋"), e(stop["dates"])))
        body.append('<div class="stop-card">')
        body.append('<a class="stop-ref" href="%s#v%s">%s · %s</a>'
                    % (e(where), e(stop["verses"][0]["v"]),
                       e(title_case(stop["workTitle"])), e(stop["label"])))
        for v in stop["verses"]:
            body.append('<blockquote class="stop-text">'
                        '<span class="stop-vnum">%s</span> %s</blockquote>'
                        % (e(v["v"]), e(v["t"])))
        body.append('<p class="stop-why">%s</p>' % e(stop["why"]))
        if stop.get("aside"):
            body.append('<p class="stop-aside">%s</p>' % e(stop["aside"]))
        body.append("</div></li>")

    body.append("</ol>")
    body.append('<div class="callout"><p>%s</p></div>' % e(t["closing"]))
    body.append('<p class="tiny">The passages above are the text, reproduced '
                'exactly and checked against the same files the reader uses; '
                'every reference is verified when the site is built. The '
                'commentary between them is editorial, written for this '
                'volume.</p>')
    body.append('<p><a class="chip" href="../../#/thread/%s">Open in the '
                'reader</a> <a class="chip" href="../">All the threads</a></p>'
                % e(t["id"]))
    body.append("</div>")

    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": t["title"],
        "url": url,
        "description": description,
        "inLanguage": "en",
        "isPartOf": {"@type": "CollectionPage", "name": "Threads — " + SITE,
                     "url": "%s/threads/" % BASE},
    }
    page = "\n".join([
        head(title, description, url, 2, ld(schema)),
        "<body>",
        topbar(2),
        '<main id="main">',
        "\n".join(body),
        "</main>",
        footer(2, "one thread, as a plain page"),
    ])
    write(os.path.join(out_dir, "threads", t["id"], "index.html"), page)
    return url


def timeline_page(manifest, out_dir):
    """Every work against the critical column, in the order the bars start.

    The reader draws this; a crawler cannot see a canvas of positioned spans
    and neither can a person with the stylesheet off, so the same reordering
    is written out here as a table with the ranges in words. The dates are
    read from the manifest -- the same spans the reader positions its bars
    from -- and formatted by tools/dates.py, which is the function the
    reader's own spanText() is held against by
    tests/python/test_span_agreement.py.
    """
    url = "%s/timeline/" % BASE
    title = "The library on one axis — " + SITE
    description = describe(
        "Every work in The Book against time, in the order the critical "
        "positions start rather than the order tradition files them.")

    rows = []
    undated = []
    for section in manifest["sections"]:
        for w in section["works"]:
            positions = w.get("positions") or {}
            own = (positions.get("span") or {}).get("crit")
            span = own or section.get("span")
            row = {"w": w, "section": section, "span": span,
                   "own": bool(own), "composite": positions.get("composite")}
            (rows if span else undated).append(row)

    rows.sort(key=lambda r: (r["span"]["frm"], r["span"]["to"]))

    body = ['<div class="wrap-wide">',
            crumbs(1, None),
            "<h1>The library on one axis</h1>",
            '<p class="lede">Every work in the volume, against time. A range '
            'is a range and not a date: its width is how much the position it '
            'comes from actually commits to. This page is the critical column, '
            'which is the one that reorders the library; the reader draws both '
            'and lets you switch between them.</p>',
            '<table class="grid"><thead><tr>'
            "<th>Work</th><th>When</th><th>Era it is filed under</th>"
            "<th>How it is placed</th></tr></thead><tbody>"]

    for r in rows:
        placed = ("its own dated position" if r["own"]
                  else "the era it is filed under")
        when = e(dates.describe(r["span"]))
        if r["composite"]:
            when += (' <span class="muted">— not one date: %s</span>'
                     % e(r["composite"]))
        body.append("<tr><td><a href=\"../read/%s/\">%s</a></td>"
                    "<td>%s</td><td>%s</td><td>%s</td></tr>"
                    % (e(r["w"]["id"]), e(title_case(r["w"]["title"])), when,
                       e(((r["section"]["roman"] + ". ") if r["section"].get("roman") else "")
                         + title_case(r["section"].get("name")
                                      or r["section"].get("title") or "")),
                       e(placed)))
    body.append("</tbody></table>")

    layered = [r for r in rows if r["composite"]]
    if layered:
        body.append("<h2>%d of these are not one date</h2>" % len(layered))
        body.append('<p class="muted">A range is drawn from one position, and '
                    'some of these books are not one composition. Where a '
                    "work's own critical position says so, it is quoted here. "
                    'This volume keeps such books whole rather than splitting '
                    'them, so saying it is the only warning the arrangement '
                    'can give.</p>')
        body.append("<ul>")
        for r in layered:
            body.append('<li><a href="../read/%s/">%s</a> '
                        '<span class="muted">— %s</span></li>'
                        % (e(r["w"]["id"]), e(title_case(r["w"]["title"])),
                           e(r["composite"])))
        body.append("</ul>")

    if undated:
        body.append("<h2>%d works carry no date under this column</h2>"
                    % len(undated))
        body.append('<p class="muted">Nothing here is a gap in the data. The '
                    'later collections — the Testaments, the Apostolic '
                    'Fathers, the Shepherd — are filed after the numbered eras '
                    'and have no era range to fall back on.</p>')
        body.append("<ul>")
        for r in undated:
            body.append('<li><a href="../read/%s/">%s</a></li>'
                        % (e(r["w"]["id"]), e(title_case(r["w"]["title"]))))
        body.append("</ul>")

    body.append('<p><a class="chip" href="../#/timeline">Open in the reader</a> '
                '<a class="chip" href="../#/method">How the dating was '
                'decided</a></p>')
    body.append("</div>")

    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "The library on one axis — " + SITE,
        "url": url,
        "description": description,
        "inLanguage": "en",
        "isPartOf": {"@type": "WebSite", "name": SITE, "url": BASE + "/"},
    }
    page = "\n".join([
        head(title, description, url, 1, ld(schema), og_type="website"),
        "<body>",
        topbar(1),
        '<main id="main">',
        "\n".join(body),
        "</main>",
        footer(1, "the timeline as a plain page"),
    ])
    write(os.path.join(out_dir, "timeline", "index.html"), page)
    return url


def not_found_page(out_dir):
    """Served by Pages from any depth, so its links and its stylesheet are
    absolute -- a relative path here resolves against whatever address was
    mistyped, which is the one place relative paths cannot work."""
    page = """<!DOCTYPE html>
<html lang="en" data-theme="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Not found — {site}</title>
<meta name="robots" content="noindex">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; base-uri 'self'; form-action 'self'; object-src 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; worker-src 'self'; manifest-src 'self'; connect-src 'self' https://archive.org https://*.archive.org; media-src 'self' blob: https://archive.org https://*.archive.org">
<link rel="stylesheet" href="{base}/assets/app.css">
<link rel="icon" href="{base}/assets/favicon.svg" type="image/svg+xml">
<script src="/assets/short-link.js"></script>
</head>
<body>
<main id="main">
<div class="wrap">
  <h1>No page at that address</h1>
  <p class="empty">
    Nothing here answers to that. A chapter may have been renumbered, or the
    link may have been cut short somewhere between here and you.
  </p>
  <p>
    <a class="chip" href="{base}/contents/">Everything in the volume</a>
    <a class="chip" href="{base}/#/search">Search the text</a>
    <a class="chip" href="{base}/timeline/">The timeline</a>
  </p>
</div>
</main>
</body>
</html>
""".format(base=BASE, site=SITE)
    write(os.path.join(out_dir, "404.html"), page)


# ---------------------------------------------------------------- about, contact, privacy, press
#
# Four plain pages that say who is behind the site, how the audio is made,
# what is counted and where to reach it. Everything on them is a fact that can
# be checked in this repository or on the pages linked from them; nothing is
# claimed about a company, an address, staff or awards, because none is
# documented anywhere. The voice is synthetic and the pages say so first.

ORG = "The Book and Me"
# The publisher, by the owner's say-so. A name and nothing else: no address, staff or claims.
PUBLISHER = "OpenPrints"
ORG_ID = BASE + "/#organization"
CHANNELS = [
    ("YouTube", "https://www.youtube.com/@thebookandme"),
    ("Kick", "https://kick.com/jonesproject"),
]
YOUTUBE = CHANNELS[0][1]
REPO = "https://github.com/TheoryofShadows/The-Book"
AUDIO_ITEM = "https://archive.org/details/the-book-read-aloud"
POLICY_DATE = "21 November 2026"

# Who sends the sign-in email. The privacy page names it, so it must be the
# service the deployed worker actually uses (see ACCOUNTS.md).
MAIL_PROVIDER = "Resend"

# The public contact address: Cloudflare Email Routing forwards it to the
# maintainer. Set to None to fall back to the YouTube/GitHub contact text.
CONTACT_EMAIL = "hello@thebookandme.com"

INFO_PAGES = ["about", "contact", "privacy", "press"]


def org_schema():
    node = {
        "@type": "Organization",
        "@id": ORG_ID,
        "name": PUBLISHER,
        "url": BASE + "/",
        "logo": BASE + "/assets/icon-512.png",
        "brand": {"@type": "Brand", "name": ORG, "alternateName": SITE},
        "description": ("A free, searchable library of biblical and related "
                        "ancient texts in the order they were written, read "
                        "aloud by a synthetic voice."),
        "sameAs": [u for _, u in CHANNELS],
    }
    if CONTACT_EMAIL:
        node["email"] = CONTACT_EMAIL
    return node


def website_schema():
    return {
        "@type": "WebSite",
        "@id": BASE + "/#website",
        "name": ORG,
        "alternateName": SITE,
        "url": BASE + "/",
        "inLanguage": "en",
        "isAccessibleForFree": True,
        "publisher": {"@id": ORG_ID},
    }


def _ext(url, text):
    return '<a href="%s" rel="noopener noreferrer">%s</a>' % (e(url), e(text))


def _channel_links():
    return " · ".join(_ext(u, n) for n, u in CHANNELS)


def _info_page(slug, title, description, body, page_type, manifest):
    """Write /<slug>/index.html and return its URL."""
    url = "%s/%s/" % (BASE, slug)
    nodes = [{
        "@type": page_type,
        "@id": url + "#page",
        "name": title,
        "url": url,
        "description": description,
        "inLanguage": "en",
        "isPartOf": {"@id": BASE + "/#website"},
        "about": {"@id": ORG_ID},
    }]
    if slug == "about":
        nodes += [org_schema(), website_schema()]
    schema = {"@context": "https://schema.org", "@graph": nodes}
    page = "\n".join([
        head(title, description, url, 1, ld(schema), og_type="website"),
        "<body>",
        topbar(1),
        '<main id="main">',
        '<div class="wrap">',
        '<div class="crumbs"><a href="../">The Book</a> → <span>%s</span></div>'
        % e(title.split(" — ")[0]),
        body,
        "</div>",
        "</main>",
        footer(1, "an information page about the project"),
    ])
    write(os.path.join(slug_dir(slug), "index.html"), page)
    return url


_OUT = [None]


def slug_dir(slug):
    return os.path.join(_OUT[0], slug)


def about_page(manifest):
    t = manifest.get("totals") or {}
    works, chapters = t.get("works", 0), t.get("chapters", 0)
    body = """
<h1>About {org}</h1>
<p class="lede">{org} is a free, independent project. It publishes biblical
and related ancient texts in the order scholars believe they were written,
lets you search and read them, and reads them aloud — in a synthetic voice,
not a human one.</p>

<h2>The voice is AI-generated</h2>
<p>Every recorded reading on this site, and on our 24/7 streams, is produced by
a text-to-speech model (<strong>Kokoro</strong>, voice “bm_lewis”). There is no
human narrator. The audio files are published at the
{ia} as one audio file per chapter ({chapters:,} chapters) with verse timings;
the Internet Archive hosts them, it did not record them. When you press
Listen, the page plays that synthetic reading, or your own device’s built-in
speech voice if the recording is not available.</p>

<h2>What the library is</h2>
<p>{works:,} works and {chapters:,} chapters of the Jewish, Protestant,
Catholic, Orthodox and Ethiopian canons, with the apocrypha, pseudepigrapha
and Apostolic Fathers, arranged by when each is dated — not by traditional
Bible order. That order is a scholarly reconstruction, not a fact, and the
site says so. The texts are public domain: the World English Bible
(eBible.org) for the canonical books, R. H. Charles’s 1917 Enoch and Jubilees,
and the Ante-Nicene Fathers, among others. Nothing is taken from a modern
copyrighted translation. See the <a href="../press/">credits</a> for the
full list, and the <a href="../#/accuracy">accuracy report</a> for what has
been checked and what has not.</p>

<h2>The livestreams</h2>
<p>The same reading plays around the clock on {channels}. These are
pre-rendered playback streams in the order the texts were written, not live
performances. Where a platform has a rerun label we use it. Some replies in
stream chat are written by an AI assistant working for the project.</p>

<h2>What this is not</h2>
<ul>
<li>It is not medical, mental-health or pastoral advice. Many people listen at
bedtime; we make no claim that it helps with sleep, anxiety or any condition.</li>
<li>It takes no side between the canons: it prints them all and says which is
which.</li>
<li>It has no ads and needs no account. Reading and listening are free; an account is an optional way to keep your place across devices.</li>
</ul>

<h2>Who runs it</h2>
<p>{org} is published by {publisher}, an independent publisher. The code is open source (MIT licence) and
public at {repo}; the texts are public domain and the reference data carries
its own credits on the <a href="../press/">credits page</a>. See
<a href="../contact/">Contact</a> to get in touch and
<a href="../privacy/">Privacy</a> for what is and is not collected.</p>
""".format(org=e(ORG), publisher=e(PUBLISHER), works=works, chapters=chapters,
           ia=_ext(AUDIO_ITEM, "Internet Archive"),
           channels=_channel_links(), repo=_ext(REPO, "GitHub"))
    return _info_page(
        "about", "About — " + ORG,
        "The Book and Me is a free, independent library of biblical and related "
        "ancient texts in the order they were written, read aloud by a "
        "synthetic (AI) voice.", body, "AboutPage", manifest)


def contact_page(manifest):
    if CONTACT_EMAIL:
        # email_off: Cloudflare's Email Obfuscation would otherwise rewrite this
        # into /cdn-cgi/l/email-protection, a link that 404s without JavaScript.
        mail = ('<li><strong>Email:</strong> <!--email_off--><a href="mailto:{m}">{m}</a><!--/email_off--></li>'
                .format(m=e(CONTACT_EMAIL)))
    else:
        mail = ""
    body = """
<h1>Contact</h1>
<p class="lede">How to reach {org}. It is a small independent project, so
replies can take a few days.</p>
<ul>
{mail}
<li><strong>YouTube:</strong> {yt}. Comment on a video or in the live chat.</li>
<li><strong>Kick:</strong> {kick} — stream chat.</li>
<li><strong>Corrections to a text or a date:</strong> open an issue on
{repo}. Say the work, the chapter and what is wrong; the accuracy report
explains how checks are done.</li>
</ul>
<p class="muted">We will never ask for a password, payment or personal
details by message. See <a href="../privacy/">Privacy</a>.</p>
""".format(org=e(ORG), mail=mail, yt=_ext(YOUTUBE, "The Book and Me on YouTube"),
           kick=_ext(CHANNELS[1][1], "kick.com/jonesproject"),
           repo=_ext(REPO + "/issues", "the project’s GitHub issues"))
    return _info_page(
        "contact", "Contact — " + ORG,
        "How to reach The Book and Me: the YouTube channel, stream chat, "
        "and GitHub issues for corrections.", body, "ContactPage", manifest)


def privacy_page(manifest):
    reach = ("through the contact address on the <a href=\"../contact/\">Contact</a> page"
             if CONTACT_EMAIL else
             "through the channels on the <a href=\"../contact/\">Contact</a> page")
    mail_note = (
        "<li><strong>Email.</strong> If you write to us, we keep your message "
        "and address only to reply and to fix what you reported. They are not "
        "shared or sold.</li>" if CONTACT_EMAIL else
        "<li><strong>Messages.</strong> If you contact us through YouTube, "
        "Kick or GitHub, that platform’s own privacy policy applies to "
        "the message.</li>")
    body = """
<h1>Privacy</h1>
<p class="lede">Short version: accounts are optional and off by default, so
nothing you save leaves your device unless you choose to sign in. No ads, no
sale of personal data, and no cookies unless you sign in. Last updated
{date}.</p>

<h2>What this site counts</h2>
<p>We use <strong>Cloudflare Web Analytics</strong> to count visits: which pages
are read and roughly where visitors come from. Cloudflare describes it as
cookie-less and says it does not use client-side storage or fingerprinting to
build a profile of a person. We use the totals to see which texts are read; we
do not look at individuals and we do not sell or share the data. Cloudflare
also serves the site and, like any host, handles the technical details of a
request (such as the IP address) to deliver pages and block abuse, under its
<a href="https://www.cloudflare.com/privacypolicy/" rel="noopener noreferrer">own
privacy policy</a>.</p>

<h2>What stays on your device</h2>
<p>The reader remembers your theme, reading position, saved verses and any
diary notes in your browser’s local storage, and keeps an offline copy of
pages through a service worker. Unless you sign in (next section), this data
is on your device only; the site has no server that receives it, and clearing
your browser’s site data removes it.</p>

<h2 id="accounts">Optional accounts</h2>
<p>You never need an account. If you want your saved verses and notes on more
than one device you can sign in with your email address. There is no password:
we email you a one-time link that works once and expires in 15 minutes.</p>
<p><strong>What is stored on our server if you sign in:</strong></p>
<ul>
<li>your email address;</li>
<li>the things you chose to keep: saved verses (with the verse text and
reference), your notes on them, your diary entries, your reading position, and
a few settings (theme, text size, listening speed and pace and similar);</li>
<li>a hash of your current sign-in session on each device, and, for a short
time, a hash of an unused sign-in link;</li>
<li>abuse-limit counters keyed by a hash of your address and connection, not
the address itself, kept for at most two days.</li>
</ul>
<p><strong>What is not stored:</strong> any password (none exists), your search
history, which chapters you read or listen to, or any profile of you. Signing
in does not change how the Cloudflare visit counter above works.</p>
<p><strong>Cookie.</strong> Signing in sets one cookie, <code>tbm_session</code>. It
is HttpOnly, sent only to this site’s sign-in and sync addresses, and lasts 30
days (renewed when you use it). Signing out removes it. Nobody who has not
signed in is given a cookie.</p>
<p><strong>Who handles it.</strong> The data is held in a Cloudflare D1 database in
our Cloudflare account. The sign-in email is sent through {mail_provider}, which
therefore sees your address and the message. We do not sell or share the data,
and we do not use it for advertising.</p>
<p><strong>Keeping it, taking it, deleting it.</strong> Your data is kept until you
delete it. On the <a href="../#/account">Account page</a> you can download
everything held for you, sign out, or choose <em>Delete my account and data</em>,
which immediately and permanently removes your email address, your items and
all your sessions from our database. Items you delete yourself are kept as
small deletion markers, without their content, for up to 90 days so your other
devices learn of the deletion, and then removed. Copies already in your own
browsers are not touched and remain yours. Cloudflare’s database platform keeps
point-in-time recovery history for a short period (up to 30 days), so deleted
data can persist there until it ages out. If you cannot use the page, write to
us and we will delete it by hand. We do not currently delete inactive accounts
automatically.</p>

<h2 id="weekly">A new chapter every week</h2>
<p>The Enoch pages have a small form, <em>A new chapter every week</em>. If you
fill it in, we keep your email address, the date you signed up and the page you
signed up from, in the same Cloudflare D1 database as the accounts, and use the
address only to send that weekly chapter: one email each Sunday morning (US
Eastern time), with the next chapter of the Enoch reading plan, starting at
1 Enoch 1. We also keep which chapter you are up to and when the last one was
sent. The emails go out through Resend, which therefore handles your address.
Nothing else is asked for and no cookie is set. Every email has a one-click
unsubscribe link; using it deletes your address and your place in the plan
straight away. You can also write to us and we will remove it by hand.</p>

<h2>Other services your browser contacts</h2>
<ul>
<li><strong>Internet Archive</strong> (archive.org) — when you play the recorded
reading, your browser fetches the audio from there, so it sees your IP address
and the file requested, under <a href="https://archive.org/about/terms.php"
rel="noopener noreferrer">its terms</a>.</li>
<li><strong>Kick</strong> — the front page checks whether our Kick stream is
live by asking kick.com. That request carries no cookies from us, but Kick sees
your IP address.</li>
<li><strong>Links out</strong> — YouTube, Kick and GitHub. Once you follow a
link, that site’s policy applies.</li>
</ul>

<h2>What we do not do</h2>
<ul>
<li>No required accounts and no advertising; no email from us unless you sign up for the weekly chapter; no sign-up wall.</li>
<li>No selling or renting of personal data, and no data brokers.</li>
<li>No health, location or other sensitive data is asked for or collected.</li>
</ul>
{mail}
<p>Questions about any of this? Ask {reach}. If this page ever stops matching
how the site works, that is a bug we want to hear about.</p>
""".format(date=POLICY_DATE, mail="<ul>%s</ul>" % mail_note, reach=reach,
           mail_provider=e(MAIL_PROVIDER))
    return _info_page(
        "privacy", "Privacy — " + ORG,
        "Optional accounts, no ads, no sale of personal data. The Book and Me "
        "counts visits with cookie-less Cloudflare Web Analytics; reader data "
        "stays on your device unless you choose to sign in.", body, "WebPage", manifest)


def press_page(manifest):
    t = manifest.get("totals") or {}
    works, chapters = t.get("works", 0), t.get("chapters", 0)
    assets = [
        ("Mark (SVG)", "../assets/logo.svg"),
        ("Wordmark lockup (SVG)", "../assets/lockup.svg"),
        ("Icon, 512 px (PNG)", "../assets/icon-512.png"),
        ("Channel avatar, 800 px (PNG)", "../assets/press/the-book-and-me-avatar.png"),
        ("Channel banner, 2560 × 1440 (JPG)", "../assets/press/the-book-and-me-banner.jpg"),
    ]
    asset_li = "\n".join('<li><a href="%s">%s</a></li>' % (e(h), e(n)) for n, h in assets)
    short = ("%s is a free, independent library of %d biblical and related "
             "ancient texts, arranged in the order scholars believe they were "
             "written and read aloud by a synthetic (AI) voice. The texts are "
             "public domain. thebookandme.com" % (ORG, works))
    contact = ("Email <!--email_off-->%s<!--/email_off-->, or " % CONTACT_EMAIL) if CONTACT_EMAIL else ""
    body = """
<h1>Press and credits</h1>
<p class="lede">Facts, a short description and logo files for anyone writing
about {org}. Everything here can be checked on the site.</p>

<h2>Quick facts</h2>
<ul>
<li><strong>Name:</strong> {org} (the reader is titled “The Book”)</li>
<li><strong>Publisher:</strong> {publisher}</li>
<li><strong>What it is:</strong> A free, searchable reader and 24/7 read-aloud stream of
{works:,} biblical and related ancient texts ({chapters:,} chapters), ordered by
date of composition rather than by traditional Bible order.</li>
<li><strong>Voice:</strong> <strong>AI-generated.</strong> Kokoro text-to-speech, voice
“bm_lewis”. No human narrator. Audio is hosted by the {ia}.</li>
<li><strong>Streams:</strong> Pre-rendered playback on {channels}.</li>
<li><strong>Cost:</strong> Free to read and listen. No account needed, no ads.</li>
<li><strong>Website:</strong> <a href="{base}/">thebookandme.com</a></li>
<li><strong>Source:</strong> Code under the MIT licence at {repo}.</li>
</ul>

<h2>Short description</h2>
<p>{short}</p>

<h2>Logos and images</h2>
<p>Provided for press and review use. Please do not imply endorsement.</p>
<p><img src="../assets/press/the-book-and-me-avatar.png" alt="The Book and Me logo: an open book with a flame, cream on plum" width="160" height="160"></p>
<ul>
{assets}
</ul>

<h2>Texts, data and audio credits</h2>
<ul>
<li><strong>World English Bible with Deuterocanon</strong> (eBible.org), dedicated
to the public domain: the canonical Old and New Testaments and the deuterocanon.</li>
<li><strong>R. H. Charles</strong> (1917, Enoch and Jubilees), the
<strong>Ante-Nicene Fathers</strong> (1870 and 1885), and the other editions named
on each work’s page: public domain by age. The full list of editions is in the
<a href="{repo_url}#sources">project README</a>.</li>
<li><strong>Word definitions:</strong> Easton’s Bible Dictionary (1897, public
domain) in a parse by NEUU, CC BY 4.0.</li>
<li><strong>Place coordinates:</strong> OpenBible.info Bible Geocoding, CC BY 4.0,
with parts derived from OpenStreetMap contributors (ODbL). Land outlines: Natural
Earth, public domain.</li>
<li><strong>Voice:</strong> Kokoro text-to-speech model, rendered by this project;
the resulting audio is published at the {ia} with a CC0 dedication.</li>
</ul>
<p>The <a href="../#/accuracy">accuracy report</a> sets out what was checked
against the sources, what was corrected and what is still missing.</p>

<h2>Press contact</h2>
<p>{contact}see <a href="../contact/">Contact</a>. For how the site handles
data, see <a href="../privacy/">Privacy</a>.</p>
""".format(org=e(ORG), publisher=e(PUBLISHER), works=works, chapters=chapters, base=BASE,
           ia=_ext(AUDIO_ITEM, "Internet Archive"), channels=_channel_links(),
           repo=_ext(REPO, "GitHub"), repo_url=e(REPO), short=e(short),
           assets=asset_li, contact=contact)
    return _info_page(
        "press", "Press and credits — " + ORG,
        "Facts, a short description, logo files and source credits for The "
        "Book and Me, a free library of ancient texts read aloud by a "
        "synthetic (AI) voice.", body, "WebPage", manifest)


def info_pages(manifest, out_dir):
    _OUT[0] = out_dir
    return [about_page(manifest), contact_page(manifest),
            privacy_page(manifest), press_page(manifest)]


# ---------------------------------------------------------------- Enoch plan

# The sections of the three books of Enoch, in the order the books number
# their chapters -- which is not the order the library files them in: the
# library goes by date, and puts the Astronomical Book before the Parables.
# Each intro says only what the volume's own notes on these works say.
ENOCH_GROUPS = [
    ("1 Enoch", "The Book of the Watchers", "1-enoch-the-book-of-the-watchers-chapters-1-36", 1, 36,
     "Third century BCE, one of the earliest Jewish apocalypses. The Watchers, "
     "angels who take human wives, are bound; Enoch is taken on journeys through "
     "the cosmos. Quoted in Jude 14-15."),
    ("1 Enoch", "The Book of Parables", "1-enoch-the-book-of-parables-chapters-37-71", 37, 71,
     "Three parables of the coming judgment, probably late first century BCE or "
     "first century CE, and the latest part of 1 Enoch. The figure called the Son "
     "of Man, the Elect One, sits on a throne of glory."),
    ("1 Enoch", "The Astronomical Book", "1-enoch-the-astronomical-book-chapters-72-82", 72, 82,
     "Possibly the oldest part of 1 Enoch. The angel Uriel shows Enoch the laws of "
     "the sun, moon and stars, and a calendar of 364 days."),
    ("1 Enoch", "The Dream Visions", "1-enoch-dream-visions-and-the-epistle-of-enoch-chapters-83-108", 83, 90,
     "Second century BCE. Two dream visions; the second, the Animal Apocalypse, "
     "retells Israel's history with the people as animals."),
    ("1 Enoch", "The Epistle of Enoch", "1-enoch-dream-visions-and-the-epistle-of-enoch-chapters-83-108", 91, 108,
     "Enoch's instruction to his children: the Apocalypse of Weeks, woes against the "
     "rich and the oppressor, and the birth of Noah."),
    ("2 Enoch", "The Book of the Secrets of Enoch", "2-enoch-the-book-of-the-secrets-of-enoch", 1, None,
     "Slavonic Enoch, probably late first century CE. Enoch passes through the "
     "heavens, is shown the week of creation, and returns to teach his sons."),
    ("3 Enoch", "The Hebrew Book of Enoch", "3-enoch-the-hebrew-book-of-enoch", 1, None,
     "A much later Hebrew work, in its final form fifth or sixth century CE. Rabbi "
     "Ishmael ascends to heaven and meets the angel Metatron, who was Enoch."),
]


def signup_form(from_path):
    """"A new chapter every week": a plain form, so it needs no script.

    It posts to /api/subscribe, which keeps the address in the site's own
    Cloudflare D1 database (worker/worker.js, migrations/0002_subscribers.sql)
    and answers with a page of its own. The hidden "website" field is the
    same honeypot the sign-in form uses.
    """
    return "\n".join([
        '<form class="signup" method="post" action="/api/subscribe">',
        '<h2>A new chapter every week</h2>',
        '<p class="muted">Leave your email and get one chapter of the Enoch reading plan '
        'each Sunday morning, in order from 1 Enoch 1: a link to the chapter and its '
        'opening lines. Your address is used for nothing else, and every email has a '
        'one-click unsubscribe link.</p>',
        '<input type="hidden" name="from" value="%s">' % e(from_path),
        '<label class="hp" aria-hidden="true">Leave this empty '
        '<input type="text" name="website" tabindex="-1" autocomplete="off"></label>',
        '<div class="signup-row">',
        '<label for="signup-email" class="sr">Email address</label>',
        '<input id="signup-email" type="email" name="email" required maxlength="254" '
        'autocomplete="email" inputmode="email" placeholder="you@example.com">',
        '<button type="submit">Sign up</button>',
        "</div>",
        "</form>",
    ])


def enoch_plan_page(manifest, out_dir):
    """/enoch-reading-plan/: every chapter of the three books of Enoch, in order."""
    works = {w["id"]: w for sec in manifest["sections"] for w in sec["works"]}
    data = os.path.join(out_dir, "data", "works")
    url = "%s/%s/" % (BASE, ENOCH_PLAN)
    title = "Enoch Reading Plan: 1, 2 and 3 Enoch, Chapter by Chapter | " + BRAND
    total = 0
    blocks = []
    current = None
    weekly = []
    for book, name, wid, lo, hi, intro in ENOCH_GROUPS:
        meta = works.get(wid)
        if not meta:
            raise SystemExit("enoch plan: no work %s in the manifest" % wid)
        with open(os.path.join(data, wid + ".json"), encoding="utf-8") as fh:
            chapters = json.load(fh).get("chapters") or []
        slugs = chapter_slugs(meta, chapters)
        links = []
        for c, slug in zip(chapters, slugs):
            n = c.get("n")
            if not isinstance(n, int) or n < lo or (hi is not None and n > hi):
                continue
            weekly.append({"title": "%s %d" % (book, n), "part": name,
                           "url": "/read/%s/%s/" % (wid, slug), "excerpt": weekly_excerpt(c)})
            links.append('<a href="../read/%s/%s/" title="%s Enoch Chapter %d">%d</a>'
                         % (e(wid), e(slug), book[0], n, n))
        if not links:
            raise SystemExit("enoch plan: %s has no chapters %s-%s" % (wid, lo, hi))
        total += len(links)
        last = hi if hi is not None else max(c.get("n") or 0 for c in chapters)
        if book != current:
            blocks.append("<h2>%s</h2>" % e(book))
            current = book
        blocks.append('<h3>%s <span class="muted">· chapters %d–%d</span></h3>' % (e(name), lo, last))
        blocks.append("<p>%s</p>" % e(intro))
        blocks.append('<nav class="chapter-strip" aria-label="%s, %s">%s</nav>'
                      % (e(book), e(name), "".join(links)))
    description = ("All %d chapters of 1, 2 and 3 Enoch in order, grouped by section, "
                   "free to read and listen to." % total)
    sources = manifest.get("sources") or {}
    credit = "; ".join(sources[k]["label"] for k in ("charles", "morfill", "odeberg") if k in sources)
    body = "\n".join([
        "<h1>Enoch reading plan</h1>",
        '<p class="lede">Every chapter of the three books of Enoch, in the order '
        "the books number them: %d chapters, one link each. Read them in order, "
        "a chapter at a time, at whatever pace suits you.</p>" % total,
        "\n".join(blocks),
        signup_form("/%s/" % ENOCH_PLAN),
        '<p class="muted">Translations: %s. The library itself files these works '
        'by the date scholars give them, which is why the <a href="../contents/">contents</a> '
        "list them in a different order.</p>" % e(credit),
    ])
    schema = {"@context": "https://schema.org", "@type": "CollectionPage",
              "name": "Enoch reading plan", "url": url, "description": description,
              "inLanguage": "en", "isPartOf": {"@id": BASE + "/#website"}}
    page = "\n".join([
        head(title, description, url, 1, ld(schema), og_type="website"),
        "<body>",
        topbar(1),
        '<main id="main">',
        '<div class="wrap">',
        '<div class="crumbs"><a href="../">The Book</a> → <span>Enoch reading plan</span></div>',
        body,
        "</div>",
        "</main>",
        footer(1, "a reading plan for the books of Enoch"),
    ])
    write(os.path.join(out_dir, ENOCH_PLAN, "index.html"), page)
    # The weekly email's running order, read by worker/worker.js: one entry
    # per chapter, in the plan's order, each with its opening words exactly as
    # the chapter page prints them.
    if len(weekly) != total:
        raise SystemExit("enoch plan: %d weekly entries for %d chapters" % (len(weekly), total))
    write(os.path.join(out_dir, "data", "weekly.json"),
          json.dumps({"order": "enoch-reading-plan", "chapters": weekly},
                     ensure_ascii=False, separators=(",", ":")))
    return url, total


def weekly_excerpt(c, most=320):
    """The opening of a chapter, whole verses or paragraphs only, as printed."""
    parts = [v["t"] for v in (c.get("verses") or [])] or list(c.get("paras") or [])
    out = ""
    for t in parts:
        t = " ".join(str(t).split())
        if not t:
            continue
        if out and len(out) + 1 + len(t) > most:
            break
        out = (out + " " + t) if out else t
        if len(out) >= most // 2:
            break
    if len(out) > most:
        cut = out[:most].rsplit(" ", 1)[0]
        out = cut.rstrip(",;:") + "…"
    return out


NL = chr(10)


def sitemap(out_dir, urls, changed=None):
    """Every page, and when it last changed.

    The date is as much the point of this file as the list is. Without a
    lastmod a crawler cannot tell a page it read last week from one rewritten
    since, so it either re-reads everything or -- on 2,724 pages with no
    particular standing -- re-reads very little. Google uses the date while
    the dates are consistent and verifiable, and discounts the whole file
    once it catches a site stamping every page with today.

    So this is the date the text last moved, not the build time. A rebuild
    that changes nothing must not move it: that is the lie that gets the file
    discounted.
    """
    if len(set(urls)) != len(urls):
        raise SystemExit("sitemap: %d URLs, %d of them distinct"
                         % (len(urls), len(set(urls))))
    if changed is None:
        # The chapter and work pages changed on their own on PAGES_DATE, when
        # each gained the "About this chapter" block: a real change to what a
        # crawler reads, so it moves their date once. A rebuild that changes
        # nothing still moves nothing.
        changed = max(source_date(), PAGES_DATE)
    # The text pages carry the date the text moved. The home page and the
    # about, contact, privacy and press pages are the site's own writing, which
    # moves on a different clock (privacy says "last updated" on its face), so
    # they carry the date of the last commit that touched that writing. Never
    # earlier than the text date: a page cannot be older than the library it
    # describes.
    own = max(changed, site_date())
    own_urls = {BASE + "/"} | {"%s/%s/" % (BASE, p) for p in INFO_PAGES}
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        out.append("  <url><loc>%s</loc><lastmod>%s</lastmod></url>"
                   % (e(u), own if u in own_urls else changed))
    out.append("</urlset>")
    write(os.path.join(out_dir, "sitemap.xml"), NL.join(out) + NL)


def _env_date(name):
    """A date handed in by the deploy, which builds in a copy of the repo with
    no git history and so cannot ask git itself. Only a real YYYY-MM-DD is
    believed."""
    got = os.environ.get(name, "").strip()
    if len(got) == 10 and got[4] == "-":
        try:
            import datetime
            datetime.date.fromisoformat(got)
            return got
        except ValueError:
            pass
    return None


def site_date():
    """When the site's own writing last changed, as YYYY-MM-DD: the last commit
    that touched the generator, the home page or the stylesheet and script.
    Falls back to the newest mtime of those files, like source_date()."""
    import subprocess, datetime
    got = _env_date("BOOK_SITE_DATE")
    if got:
        return got
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
    paths = ["tools/build_pages.py", "docs/index.html"]
    try:
        run = subprocess.run(
            ["git", "-C", root, "log", "-1", "--format=%cs", "--"] + paths,
            capture_output=True, text=True, encoding="utf-8", timeout=20)
        stamp = (run.stdout or "").strip()
        if len(stamp) == 10 and stamp[4] == "-":
            return stamp
    except Exception:
        pass
    newest = 0
    for rel in paths:
        try:
            newest = max(newest, os.path.getmtime(os.path.join(root, rel)))
        except OSError:
            pass
    return (datetime.date.fromtimestamp(newest) if newest
            else datetime.date.today()).isoformat()


def source_date():
    """When the text last changed, as YYYY-MM-DD.

    Asked of git, which is the only record of when the library moved rather
    than when somebody happened to run the build. Falls back to the mtime of
    the source text where there is no history to ask -- a tarball, a shallow
    checkout -- which answers the same question less precisely rather than a
    different one.
    """
    import subprocess, datetime
    forced = _env_date("BOOK_SOURCE_DATE")
    if forced:
        return forced
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
    try:
        got = subprocess.run(
            ["git", "-C", root, "log", "-1", "--format=%cs",
             "--", "source", "docs/data"],
            capture_output=True, text=True, encoding="utf-8", timeout=20)
        stamp = (got.stdout or "").strip()
        if len(stamp) == 10 and stamp[4] == "-":
            return stamp
    except Exception:
        pass
    src = os.path.join(root, "source", "THE_BOOK_COMPLETE.txt")
    try:
        return datetime.date.fromtimestamp(os.path.getmtime(src)).isoformat()
    except OSError:
        return datetime.date.today().isoformat()


def robots(out_dir):
    """The single-file build is 13 MB of the entire library in one document.
    It is for a reader taking the thing on a plane, not for a crawler, and
    letting one fetch it is both a waste of everybody's bandwidth and a second
    copy of every chapter competing with the pages written here.

    Cloudflare Pages serves docs/the-book.html at /the-book (and 308s
    /the-book.html there), so both paths have to be disallowed. Disallowing
    only the .html address left the pretty URL open to crawlers.
    """
    write(os.path.join(out_dir, "robots.txt"),
          "User-agent: *\n"
          "Allow: /\n"
          "Disallow: {prefix}/the-book\n"
          "Disallow: {prefix}/the-book.html\n"
          "\n"
          "Sitemap: {base}/sitemap.xml\n".format(prefix=PREFIX, base=BASE))


# ---------------------------------------------------------------- main

def build(out_dir):
    data = os.path.join(out_dir, "data")
    with open(os.path.join(data, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)

    ordered = []
    for s in manifest["sections"]:
        for w in s["works"]:
            ordered.append((s, w))

    with open(os.path.join(data, "threads.json"), encoding="utf-8") as fh:
        threads = json.load(fh)
    load_context(data)
    slugs_by_work = {w["id"]: (w.get("slugs") or [])
                     for sec in manifest["sections"] for w in sec["works"]}

    urls = [BASE + "/", contents_page(manifest, out_dir),
            timeline_page(manifest, out_dir),
            thread_hub_page(threads, out_dir)]
    urls.extend(info_pages(manifest, out_dir))
    plan_url, plan_total = enoch_plan_page(manifest, out_dir)
    urls.append(plan_url)
    for t in threads:
        urls.append(thread_page(manifest, slugs_by_work, t, out_dir))
    works = 0
    chapters_written = 0
    chapters_expected = 0

    for i, (section, meta) in enumerate(ordered):
        path = os.path.join(data, "works", meta["id"] + ".json")
        with open(path, encoding="utf-8") as fh:
            work = json.load(fh)
        chapters = work.get("chapters") or []
        chapters_expected += len(chapters)
        slugs = chapter_slugs(meta, chapters)

        # Two chapters of one work must never end up with the same title.
        # The rule that drops a repeated work name is what could cause it --
        # eat one word too many and every chapter of a volume is left calling
        # itself the volume -- and the titles are indexed, so a collision is
        # duplicate pages competing with each other rather than a cosmetic
        # slip. Cheap to check, and the check is what lets chapter_heading()
        # return the bare title for a label that is nothing but the title.
        headings = [chapter_heading(meta["title"], c.get("label") or "")
                    for c in chapters]
        if len(set(headings)) != len(headings):
            dupes = sorted(h for h in set(headings) if headings.count(h) > 1)
            raise SystemExit("%s: %d chapters share a title, e.g. %r"
                             % (meta["id"], len(headings) - len(set(headings)),
                                dupes[0]))

        urls.append(work_page(
            manifest, section, meta, chapters, slugs,
            ordered[i - 1][1] if i > 0 else None,
            ordered[i + 1][1] if i < len(ordered) - 1 else None,
            out_dir))
        works += 1

        for j in range(len(chapters)):
            urls.append(chapter_page(manifest, section, meta, work,
                                     chapters, slugs, j, out_dir))
            chapters_written += 1

    # The count is the check. A slug rule that collides writes one file where
    # two chapters were, and every other number on the page still looks right.
    if chapters_written != chapters_expected:
        raise SystemExit("wrote %d chapter pages for %d chapters"
                         % (chapters_written, chapters_expected))
    totals = manifest.get("totals") or {}
    if totals.get("chapters") and chapters_written != totals["chapters"]:
        raise SystemExit("wrote %d chapter pages, the manifest counts %d chapters"
                         % (chapters_written, totals["chapters"]))
    if totals.get("works") and works != totals["works"]:
        raise SystemExit("wrote %d work pages, the manifest counts %d works"
                         % (works, totals["works"]))

    sitemap(out_dir, urls)
    robots(out_dir)
    not_found_page(out_dir)

    print("  %d work pages" % works)
    print("  %d chapter pages" % chapters_written)
    print("  the timeline, %d thread pages under a hub, and the about, contact, privacy and press pages" % len(threads))
    print("  the Enoch reading plan, %d chapters" % plan_total)
    print("  %d URLs in sitemap.xml, plus robots.txt and 404.html" % len(urls))
    print("  %d pages" % (works + chapters_written + len(threads) + 4 + len(INFO_PAGES)))


def main(argv):
    out_dir = argv[1] if len(argv) > 1 else "docs"
    if not os.path.isdir(os.path.join(out_dir, "data")):
        raise SystemExit("no %s/data -- give me the docs directory" % out_dir)
    build(out_dir)


if __name__ == "__main__":
    main(sys.argv)
