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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stamp_assets  # noqa: E402

BASE = "https://theoryofshadows.github.io/The-Book"
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


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "chapter"


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

def chapter_slugs(chapters):
    """One URL segment per chapter, in the order they are printed.

    The printed number when there is one, the label otherwise. Do not be
    tempted by `n if n > 0 else i + 1`: Jubilees opens with a prologue
    numbered 0, and that formula quietly files it at chapter 1's address,
    where the real chapter 1 then overwrites it. The count of pages written
    still looks right, and a chapter is simply gone.
    """
    slugs = []
    for c in chapters:
        n = c.get("n")
        if isinstance(n, int) and not isinstance(n, bool) and n > 0:
            slugs.append(str(n))
        else:
            slugs.append(slugify(c.get("label") or ""))

    # Whatever the two rules above collide on gets -2, -3, and so on, so that
    # the number of addresses is always the number of chapters.
    seen = {}
    out = []
    for s in slugs:
        if s not in seen:
            seen[s] = 1
            out.append(s)
            continue
        while True:
            seen[s] += 1
            candidate = "%s-%d" % (s, seen[s])
            if candidate not in seen:
                break
        seen[candidate] = 1
        out.append(candidate)

    if len(set(out)) != len(chapters):
        raise SystemExit("chapter_slugs: %d chapters, %d addresses"
                         % (len(chapters), len(set(out))))
    return out


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
        '<link rel="stylesheet" href="%sassets/app.css?v=%s">' % (up, ASSET_V["app.css"]),
        '<link rel="icon" href="%sassets/favicon.svg" type="image/svg+xml">' % up,
        '<link rel="apple-touch-icon" href="%sassets/icon-180.png">' % up,
        '<meta name="theme-color" content="#6b2d5b">',
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
    nav = [
        ("%s#/" % up, "Timeline"),
        ("%s#/threads" % up, "Threads"),
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


def footer(depth):
    up = "../" * depth
    return """<footer class="foot">
  <p>
    <strong>The texts are public domain</strong> — the World English Bible with
    Deuterocanon, R. H. Charles's 1917 Enoch and Jubilees, and the Ante-Nicene
    Fathers of 1870 and 1885. The <a href="{up}#/accuracy">accuracy report</a>
    sets out what was verified, what was corrected, and what is still missing.
  </p>
  <p class="muted">
    This is a plain page of one chapter. The
    <a href="{up}">reader</a> has the search, the map, the word definitions,
    the saved verses and the reading aloud.
  </p>
</footer>
</body>
</html>
""".format(up=e(up or "./"))


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
            '<a href="%s">Timeline</a> → ' % e(up or "./"),
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
<link rel="stylesheet" href="{base}/assets/app.css?v={css_v}">
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
    <a class="chip" href="{base}/">The timeline</a>
  </p>
</div>
</main>
</body>
</html>
""".format(base=BASE, site=SITE, css_v=ASSET_V["app.css"])
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
          "Disallow: /The-Book/the-book.html\n"
          "\n"
          "Sitemap: %s/sitemap.xml\n" % BASE)


# ---------------------------------------------------------------- main

def build(out_dir):
    data = os.path.join(out_dir, "data")
    with open(os.path.join(data, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)

    ordered = []
    for s in manifest["sections"]:
        for w in s["works"]:
            ordered.append((s, w))

    urls = [BASE + "/", contents_page(manifest, out_dir)]
    works = 0
    chapters_written = 0
    chapters_expected = 0

    for i, (section, meta) in enumerate(ordered):
        path = os.path.join(data, "works", meta["id"] + ".json")
        with open(path, encoding="utf-8") as fh:
            work = json.load(fh)
        chapters = work.get("chapters") or []
        chapters_expected += len(chapters)
        slugs = chapter_slugs(chapters)

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
    print("  %d URLs in sitemap.xml, plus robots.txt and 404.html" % len(urls))
    print("  %d pages" % (works + chapters_written + 1))


# The content hashes the generated pages fetch the stylesheet by. Read at
# import time from the same helper docs/index.html is stamped with, so the
# 2,709 pages and the one hand-written page cannot disagree about which
# stylesheet they want.
ASSET_V = {"app.css": "0", "app.js": "0"}


def main(argv):
    out_dir = argv[1] if len(argv) > 1 else "docs"
    if not os.path.isdir(os.path.join(out_dir, "data")):
        raise SystemExit("no %s/data -- give me the docs directory" % out_dir)
    ASSET_V.update(stamp_assets.stamps(out_dir))
    build(out_dir)


if __name__ == "__main__":
    main(sys.argv)
