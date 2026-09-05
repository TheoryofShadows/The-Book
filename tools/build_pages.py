#!/usr/bin/env python3
"""One real HTML page per work and per chapter, so the library can be found.

    python3 tools/build_pages.py docs

The reader is a hash-routed single page. A fragment is never sent to a
server, so every one of the 172 works and 2,537 chapters lives at a URL that
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


def describe(text, limit=155):
    """The opening of the chapter, cut at a word rather than mid-syllable."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    space = cut.rfind(" ")
    if space > 40:
        cut = cut[:space]
    return cut.rstrip(" ,;:.—-") + "…"


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
        # The light accent, spelt out because a browser reads it before any
        # stylesheet. docs/index.html carries the same value and is held to
        # it by tests/python/test_palette.py; this copy said #6b2d5b for as
        # long as that one did, was not corrected with it, and so shipped a
        # different colour on all 2,709 of these pages than on the page they
        # link to. Both are gated now.
        '<meta name="theme-color" content="#632a55">',
        '<meta property="og:type" content="%s">' % e(og_type),
        '<meta property="og:site_name" content="%s">' % e(SITE),
        '<meta property="og:title" content="%s">' % e(title),
        '<meta property="og:description" content="%s">' % e(description),
        '<meta property="og:url" content="%s">' % e(canonical),
        '<meta property="og:image" content="%s/assets/icon-512.png">' % BASE,
        '<meta name="twitter:card" content="summary">',
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
  <p>
    <strong>The texts are public domain</strong> — the World English Bible with
    Deuterocanon, R. H. Charles's 1917 Enoch and Jubilees, and the Ante-Nicene
    Fathers of 1870 and 1885. The <a href="{up}#/accuracy">accuracy report</a>
    sets out what was verified, what was corrected, and what is still missing.
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


def pager(prev, nxt):
    """Real anchors, because a crawler follows anchors and nothing else.

    The arrows are the reader's, so a keyboard reader arriving from there
    finds the same two shapes in the same two corners.
    """
    parts = ['<div class="pager">']
    if prev:
        parts.append('<a rel="prev" href="%s">← %s</a>' % (e(prev[0]), e(prev[1])))
    else:
        parts.append('<span class="spacer"></span>')
    if nxt:
        parts.append('<a rel="next" href="%s">%s →</a>' % (e(nxt[0]), e(nxt[1])))
    parts.append("</div>")
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
    page worth crawling: 2,537 addresses reachable in two hops from the root."""
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


def chapter_page(manifest, section, meta, work, chapters, slugs, i, out_dir):
    c = chapters[i]
    slug = slugs[i]
    work_url = "%s/read/%s/" % (BASE, meta["id"])
    url = "%s/read/%s/%s/" % (BASE, meta["id"], slug)
    heading = chapter_heading(meta["title"], c.get("label") or "")
    title = heading + " — " + SITE

    verses = c.get("verses") or []
    paras = c.get("paras") or []
    opening = (verses[0]["t"] if verses else (paras[0] if paras else meta["title"]))
    description = describe(opening)

    prev = (("../%s/" % slugs[i - 1]), chapters[i - 1].get("label")) if i > 0 else None
    nxt = (("../%s/" % slugs[i + 1]), chapters[i + 1].get("label")) \
        if i < len(chapters) - 1 else None

    body = [
        '<div class="wrap">',
        crumbs(3, section, ("../", title_case(meta["title"]))),
        '<div class="reader-head">',
        "<h1>%s</h1>" % e(title_case(meta["title"])),
        strip_html(meta["id"], chapters, slugs, slug, 3),
        "</div>",
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

    # The reader's hash routes count chapters from zero, so chapter 1 is
    # #/read/genesis/0. That is a fine internal index and a poor public URL,
    # which is why these pages use the printed number instead -- but the link
    # back into the reader has to speak the reader's own arithmetic.
    body.append('<p><a class="chip" href="../../../#/read/%s/%d">Open in the reader</a> '
                '<a class="chip" href="../">All of %s</a></p>'
                % (e(meta["id"]), i, e(title_case(meta["title"]))))

    src = (manifest.get("sources") or {}).get(meta.get("source"))
    if src:
        body.append('<div class="apparatus"><strong>Text.</strong> %s. %s</div>'
                    % (e(src.get("label")), e(src.get("detail"))))

    body.append(pager(prev, nxt))
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
        head(title, description, url, 3, rel_links(prev, nxt) + "\n" + ld(schema)),
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
    description = describe(note[0]) if note else describe(
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
        head(title, description, url, 2, rel_links(prev, nxt) + "\n" + ld(schema),
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
# reader has 2,537 chapters at real URLs and eleven threads at fragments --
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
<link rel="stylesheet" href="{base}/assets/app.css">
<link rel="icon" href="{base}/assets/favicon.svg" type="image/svg+xml">
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


def sitemap(out_dir, urls):
    if len(set(urls)) != len(urls):
        raise SystemExit("sitemap: %d URLs, %d of them distinct"
                         % (len(urls), len(set(urls))))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        lines.append("  <url><loc>%s</loc></url>" % e(u))
    lines.append("</urlset>")
    write(os.path.join(out_dir, "sitemap.xml"), "\n".join(lines) + "\n")


def robots(out_dir):
    """The single-file build is 13 MB of the entire library in one document.
    It is for a reader taking the thing on a plane, not for a crawler, and
    letting one fetch it is both a waste of everybody's bandwidth and a second
    copy of every chapter competing with the pages written here."""
    write(os.path.join(out_dir, "robots.txt"),
          "User-agent: *\n"
          "Allow: /\n"
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
    slugs_by_work = {w["id"]: (w.get("slugs") or [])
                     for sec in manifest["sections"] for w in sec["works"]}

    urls = [BASE + "/", contents_page(manifest, out_dir),
            timeline_page(manifest, out_dir),
            thread_hub_page(threads, out_dir)]
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
    print("  the timeline, and %d thread pages under a hub" % len(threads))
    print("  %d URLs in sitemap.xml, plus robots.txt and 404.html" % len(urls))
    print("  %d pages" % (works + chapters_written + len(threads) + 4))


def main(argv):
    out_dir = argv[1] if len(argv) > 1 else "docs"
    if not os.path.isdir(os.path.join(out_dir, "data")):
        raise SystemExit("no %s/data -- give me the docs directory" % out_dir)
    build(out_dir)


if __name__ == "__main__":
    main(sys.argv)
