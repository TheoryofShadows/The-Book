/* ------------------------------------------------------------------ *
   The Book — chronological reader
   Plain ES modules-free JavaScript, no build step, no dependencies.
 * ------------------------------------------------------------------ */
(function () {
  "use strict";

  var DATA = "data/";
  var main = document.getElementById("main");

  /* ---------------- tiny helpers ---------------- */

  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === "class") n.className = v;
      else if (k === "html") n.innerHTML = v;
      else if (k === "text") n.textContent = v;
      else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v === true ? "" : v);
    });
    (kids || []).forEach(function (c) {
      if (c === null || c === undefined) return;
      n.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return n;
  }

  /* A table too wide for the screen is put in a box that scrolls sideways.
     A box that scrolls and cannot be focused is a box a keyboard cannot
     scroll -- axe calls it scrollable-region-focusable and it is right: on
     the accuracy report the only way to reach the right-hand columns was a
     pointer. Focusable, named, and announced as a region it is a thing you
     can tab to and then use the arrow keys in. */
  function scroller(inner, label) {
    return el("div", {
      class: "scroller", tabindex: "0", role: "region",
      "aria-label": label || "Table, scrollable sideways"
    }, [inner]);
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function titleCase(s) {
    var small = /^(of|the|and|to|in|a|on|for|with|from|by|as|at|its)$/;
    return s.toLowerCase().replace(/[^\s\-/(]+/g, function (w, i) {
      if (i > 0 && small.test(w)) return w;
      return w.charAt(0).toUpperCase() + w.slice(1);
    }).replace(/\b(i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|bce|ce|nt|ot|web)\b/gi,
      function (m) { return m.toUpperCase(); });
  }

  /* Where you are, in the one place a browser puts it.

     A single page that never changes its title gives all 2,537 chapters the
     same name: a bookmark list where every entry reads the same, a history
     that cannot be searched, a row of tabs that cannot be told apart, and a
     screen reader that announces nothing on arrival, because the title is
     what it announces and the title did not move.

     The full title stays on the front page, where it is the description of
     the whole library rather than a label repeated 2,537 times. */
  var BASE_TITLE = document.title;

  function setTitle(what) {
    document.title = what ? what + " — The Book" : BASE_TITLE;
  }

  /* "Genesis 1", not "Genesis Chapter 1", and not "Jubilees Jubilees -
     Prologue".

     Most labels are "Chapter 7" and want the work's name in front of them.
     Some two hundred and fifty -- Jubilees, the Enoch volumes, the Testaments
     -- already carry it, and putting the name in front of those says it
     twice. So a leading run of words the work's own title already contains is
     dropped, but only when the run really is the name being repeated: a
     leading "The" is not, and the last word is never eaten, or a label that
     is nothing but the repeat would leave the chapter with no number.

     chapter_heading() in tools/build_pages.py is the same rule, because the
     prerendered page
     for a chapter is the copy a search engine indexes and this is the copy
     a reader sees in their tab. Two rules would be two titles for one
     thing. (Not chapterTitle: viewRead already has a local of that name
     for the chapter's own <h2>, and a var shadows a function.) */
  /* The lowercase word sequence of a string, punctuation dropped, so that
     "SIMILITUDE 1" and "Similitude 1" are the same thing said twice. */
  function bareWords(s) {
    return String(s).toLowerCase().split(/[^a-z0-9]+/)
      .filter(function (w) { return !!w; });
  }

  function chapterHeading(workTitle, label) {
    var rest = String(label).replace(/^Chapter\s+/i, "").trim();

    /* The label is the whole title and nothing else -- Hermas's
       "Similitude 1" inside the work "SIMILITUDE 1". There is no number to
       keep hold of, so the repeat is the entire label and the title alone is
       the answer. Only safe because such a work is a single chapter, which
       build_pages.py asserts. */
    if (bareWords(rest).join(" ") === bareWords(workTitle).join(" ")) {
      return titleCase(workTitle);
    }

    var inTitle = {};
    bareWords(workTitle).forEach(function (w) { inTitle[w] = true; });

    var words = rest.split(/\s+/);
    var run = 0, named = false;
    /* Never as far as the last word. "1 ENOCH 83" belongs to "1 ENOCH: DREAM
       VISIONS ... (chapters 83-108)", which contains 83 as well as 1 and
       ENOCH: consuming the lot would leave every chapter of that volume with
       the same title, which is the bug this whole helper exists to fix. */
    for (var i = 0; i < words.length - 1; i++) {
      var bare = words[i].toLowerCase().replace(/[^a-z0-9]/g, "");
      if (!bare || !inTitle[bare]) break;
      run = i + 1;
      if (bare.length >= 4) named = true;
    }
    if (named) {
      rest = words.slice(run).join(" ").replace(/^[^A-Za-z0-9]+/, "").trim();
    }
    return (titleCase(workTitle) + (rest ? " " + rest : "")).trim();
  }

  /* Screen readers get told about things that happen without a page change:
     saving, copying, search finishing. Without this the app is silent to
     anyone not watching the pixels. */
  /* In the document from the first line rather than created on the first
     announcement. A live region that appears and is filled in the same breath
     is a region several screen readers do not announce at all -- they watch
     for changes inside a region they already know about -- so the first thing
     the site ever had to say was the thing most likely to be missed. */
  var liveRegion = el("div", {
    class: "sr-only", role: "status",
    "aria-live": "polite", "aria-atomic": "true"
  });
  document.body.appendChild(liveRegion);

  function announce(message) {
    liveRegion.textContent = "";
    setTimeout(function () { liveRegion.textContent = message; }, 60);
  }

  var cache = {};
  function getJSON(path) {
    // The single-file build inlines every data file under this global, so
    // the same code runs served-over-HTTP and opened straight from disk.
    if (window.__BOOK__ && window.__BOOK__[path]) {
      return Promise.resolve(window.__BOOK__[path]);
    }
    if (cache[path]) return cache[path];
    cache[path] = fetch(DATA + path).then(function (r) {
      if (!r.ok) throw new Error(path + " -> " + r.status);
      return r.json();
    });
    return cache[path];
  }

  function fmt(n) { return n.toLocaleString("en-US"); }

  /* ---------------- persistent settings ---------------- */

  /* Saving can fail for reasons the reader has no way to see: Safari's
     private browsing gives every site a storage quota of zero, and a browser
     that has been reading for a long time can simply run out. Swallowing that
     silently is the worst of the options -- the verse is announced as saved,
     the reader moves on, and it is gone. set() reports whether it actually
     wrote, and the callers that promise the reader something say the true
     thing instead. */
  var storageWorks = true;

  var store = {
    get: function (k, d) {
      try { var v = localStorage.getItem("thebook:" + k); return v === null ? d : JSON.parse(v); }
      catch (e) { return d; }
    },
    set: function (k, v) {
      try {
        localStorage.setItem("thebook:" + k, JSON.stringify(v));
        storageWorks = true;
        return true;
      } catch (e) {
        storageWorks = false;
        return false;
      }
    },
    /* False once a write has been refused. Read it after set(), not before:
       a quota is only ever discovered by trying. */
    works: function () { return storageWorks; }
  };

  /* Why the write failed, in the terms that decide what the reader can do
     about it. Quota is recoverable by removing saved items; private browsing
     is not recoverable at all, and saying "try again" there would be a lie. */
  var STORAGE_FAILED = "This browser is not letting the page store anything, " +
    "so that was not kept. Private browsing usually does this, and so does a " +
    "browser that has run out of room for this site.";

  /* ---------------- theme ---------------- */

  var themeBtn = document.getElementById("theme");
  function applyTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    themeBtn.textContent = t === "dark" ? "☾" : t === "light" ? "☀" : "◐";
    themeBtn.title = "Theme: " + t + " (click to change)";
  }
  applyTheme(store.get("theme", "auto"));
  themeBtn.addEventListener("click", function () {
    var order = ["auto", "light", "dark"];
    var next = order[(order.indexOf(store.get("theme", "auto")) + 1) % 3];
    store.set("theme", next);
    applyTheme(next);
  });

  /* ---------------- resume reading ---------------- */

  var resumeBtn = document.getElementById("resume");
  function refreshResume() {
    var last = store.get("last", null);
    if (last && last.work) {
      resumeBtn.hidden = false;
      resumeBtn.textContent = "Resume " + titleCase(last.title || last.work);
      resumeBtn.onclick = function () {
        location.hash = "#/read/" + last.work + "/" + last.chapter;
      };
    } else {
      resumeBtn.hidden = true;
    }
  }

  /* ================================================================
     HOME — the chronological timeline
     ================================================================ */

  /* ---------------- the day's passage ----------------

     Asked for as "daily affirmations based off the user's recent searches".
     What is here instead is a passage: a real verse from this volume, chosen
     by what the reader has been looking for, with its reference and a link
     to the chapter it sits in.

     The difference is the whole project. tools/positions.py states the rule
     this site is built on -- "an interpretive layer that merely asserts
     things, in the same visual frame as audited text, would be the weakest
     link in the whole project" -- and a machine-written affirmation beside
     forty thousand audited verses is exactly that: the one sentence on the
     page with nothing behind it. A verse has a citation by construction.

     The searches never leave the page. They are five strings in
     localStorage under the reader's own key, they are used to pick a verse
     out of data already fetched, and they can be cleared from the card. */

  var SEARCH_MEMORY = 5;

  function rememberSearch(query) {
    var term = String(query || "").trim();
    if (term.length < 3) return;
    var recent = store.get("recent-searches", []);
    if (!Array.isArray(recent)) recent = [];
    recent = recent.filter(function (x) { return x !== term; });
    recent.unshift(term);
    store.set("recent-searches", recent.slice(0, SEARCH_MEMORY));
  }

  /* One passage a day, and the same one all day.

     Seeded on the date and the term, so the card does not reshuffle every
     time the page is opened -- a passage that changes on every reload is a
     slot machine rather than a reading. */
  function daySeed(extra) {
    var key = new Date().toISOString().slice(0, 10) + "|" + (extra || "");
    var h = 2166136261;
    for (var i = 0; i < key.length; i++) {
      h ^= key.charCodeAt(i);
      h = (h * 16777619) >>> 0;
    }
    return h;
  }

  function todaysPassage(manifest, done) {
    var recent = store.get("recent-searches", []);
    if (!Array.isArray(recent) || !recent.length) { done(null); return; }

    // The most recent search that the index actually knows a word of.
    var term = recent[0];
    var terms = tokenise(term);
    if (!terms.length) { done(null); return; }
    var word = terms[daySeed(term) % terms.length];
    var shard = /^[a-z]/.test(word) ? word[0] : "0";

    Promise.all([getJSON("chapters.json"),
                 getJSON("index/" + shard + ".json").catch(function () { return {}; })])
      .then(function (loaded) {
        var table = loaded[0], index = loaded[1];
        var ids = [];
        Object.keys(index).forEach(function (token) {
          if (token.indexOf(word) === 0) {
            ids = ids.concat(index[token] || []);
          }
        });
        if (!ids.length) { done(null); return; }

        var cid = ids[daySeed(term + word) % ids.length];
        var row = table.chapters[cid];
        if (!row) { done(null); return; }

        return getJSON("works/" + row[0] + ".json").then(function (work) {
          var chapter = work.chapters[row[1]];
          if (!chapter) { done(null); return; }
          var units = (chapter.verses || []).filter(function (v) {
            return new RegExp("\\b" + word, "i").test(fold(v.t));
          });
          if (!units.length) { done(null); return; }
          var verse = units[daySeed(term + cid) % units.length];
          done({
            work: row[0], workTitle: row[3], chapterIdx: row[1],
            label: row[2], verse: verse.v, text: verse.t, term: term
          });
        });
      }).catch(function () { done(null); });
  }

  function passageCard(manifest, found) {
    var box = el("section", { class: "today" });
    box.appendChild(el("p", { class: "today-eyebrow", text:
      "Today, because you searched \u201c" + found.term + "\u201d" }));
    box.appendChild(el("blockquote", { class: "today-text", text: found.text }));

    var foot = el("p", { class: "today-foot" });
    foot.appendChild(el("a", {
      class: "today-ref",
      href: "#/read/" + found.work + "/" + found.chapterIdx +
            (found.verse ? "/v" + found.verse : ""),
      text: titleCase(found.workTitle) + " \u00b7 " + found.label +
            (found.verse ? ":" + found.verse : "")
    }));
    foot.appendChild(el("button", {
      class: "today-forget", text: "Forget my searches",
      title: "Clears the searches this card is chosen from",
      onclick: function () {
        store.set("recent-searches", []);
        var note = el("p", { class: "today-eyebrow", text:
          "Forgotten. The card comes back the next time you search." });
        box.innerHTML = "";
        box.appendChild(note);
        announce("Recent searches cleared.");
      }
    }));
    box.appendChild(foot);
    return box;
  }

  function viewHome(manifest) {
    var t = manifest.totals;
    var wrap = el("div", { class: "wrap" });

    /* --8<-- hero: start --8<--

       The first sentence of the site, and for a long time the only claim in
       it that nothing checked. It said all five canons were "complete" while
       docs/data/canon.json -- built from the same coverage table the canons
       page draws -- recorded the Ethiopian at 90 of 94 units, four of them
       absent because no English translation of them is old enough to be
       public domain. The accuracy report said one thing and the first
       paragraph said another, on a site whose whole argument is that it
       would rather show a hole than fill it with a plausible sentence.

       tests/python/test_hero.py now reads this sentence and canon.json and
       holds them together: a canon may be called complete here only when the
       coverage table says every one of its units is present, and the one
       that is not must be named with the exact number of books it is short.
       Ingest the three Meqabyan and Josippon and this test fails until the
       sentence is updated, which is the direction the failure should point.
       --8<-- */
    wrap.appendChild(el("section", { class: "hero" }, [
      el("h1", { text: "Every text, in the order it was written." }),
      el("p", {
        class: "lede",
        text: "The Jewish, Protestant, Catholic and Eastern Orthodox canons " +
              "complete, and the Ethiopian all but four books that survive in " +
              "no public-domain English — together with the pseudepigrapha, " +
              "the New Testament apocrypha and the Apostolic Fathers, arranged " +
              "not by where tradition filed them, but by when scholars believe " +
              "they were composed. It opens with a war poem, not with Genesis."
      })
    ]));
    /* --8<-- hero: end --8<-- */

    /* Counted, not typed. Every other figure in this row comes from the
       manifest and moves when the library moves; this one was the literal
       10, which is right today and is the only number on the front page
       nothing checks. The eras are the sections that carry a numeral --
       I to X -- as against the collections after them, which are grouped by
       author or book rather than by date. */
    var eras = manifest.sections.filter(function (s) { return !!s.roman; }).length;

    var stats = el("div", { class: "stats" });
    [[t.works, "works"], [t.chapters, "chapters"], [t.verses, "numbered verses"],
     [t.words, "words"], [eras, "eras, before the collections"]]
      .forEach(function (p) {
        stats.appendChild(el("div", { class: "stat" }, [
          el("b", { text: fmt(p[0]) }), el("span", { text: p[1] })
        ]));
      });
    wrap.appendChild(stats);

    /* Under the colophon and above the threads: it is a way in rather than
       the point of the page, and a reader who has never searched sees
       nothing at all rather than an empty frame. */
    var todaySlot = el("div");
    wrap.appendChild(todaySlot);
    todaysPassage(manifest, function (found) {
      if (found && todaySlot.isConnected) {
        todaySlot.appendChild(passageCard(manifest, found));
      }
    });

    // The chronological order is the only thing here no other Bible site can
    // copy. Left as a filing decision it is invisible; this is where a
    // visitor is shown what it actually reveals.
    getJSON("threads.json").then(function (threads) {
      var box = el("section", { class: "threads-hero" });
      box.appendChild(el("h2", { text: "What the order reveals" }));
      box.appendChild(el("p", { class: "muted", text:
        "Follow one question across eight hundred years of writing. Every " +
        "passage is the text itself; every reference is checked when the site " +
        "is built." }));
      // Six is what the front page can hold before the threads push the
      // library itself off the bottom of it. The rest are one link away,
      // and the count says how many there are rather than implying six is
      // all of them.
      var SHOWN = 6;
      var grid = el("div", { class: "thread-cards" });
      threads.slice(0, SHOWN).forEach(function (t) {
        grid.appendChild(el("a", { class: "thread-card", href: "#/thread/" + t.id }, [
          el("h3", { text: t.title }),
          el("p", { text: t.question }),
          el("span", { class: "thread-meta", text: t.stops.length + " passages" })
        ]));
      });
      box.appendChild(grid);
      if (threads.length > SHOWN) {
        box.appendChild(el("p", { class: "muted" }, [
          el("a", { href: "#/threads", text:
            "All " + threads.length + " threads" })
        ]));
      }
      // Directly under the hero. The argument comes before the statistics.
      var anchor = wrap.querySelector(".stats");
      if (anchor) wrap.insertBefore(box, anchor);
    }).catch(function () {});

    wrap.appendChild(el("div", { class: "callout" }, [
      el("p", { html:
        "<strong>Read this first.</strong> The order below is a reconstruction, " +
        "not a settled fact. It dates <em>books</em>, not the events or traditions " +
        "inside them — Genesis sits in Section V because its final written form is " +
        "dated to the Persian period, which says nothing about the age of the " +
        "stories it carries. Some placements are firm; others are contested by " +
        "centuries." }),
      el("p", { html:
        'The <a href="#/accuracy">accuracy report</a> lists exactly what was ' +
        "verified against reference counts, what was corrected, and what is still " +
        "missing from the public-domain sources. " +
        '<a href="#/method">How the dating was decided</a> states the ' +
        "decisions the order rests on, and " +
        '<a href="#/timeline">the library on one axis</a> draws every work as ' +
        "the range its position actually commits to — under either column, so " +
        "you can watch the order change." })
    ]));

    var line = el("div", { class: "timeline" });
    manifest.sections.forEach(function (s) {
      if (!s.works.length) return;
      var isCollection = !s.roman;
      var openState = store.get("era:" + s.id, false);

      var body = el("div", { class: "era-body" });
      (s.intro || []).slice(0, 2).forEach(function (p) {
        body.appendChild(el("p", { class: "era-intro", text: p }));
      });

      var grid = el("div", { class: "works" });
      s.works.forEach(function (w) {
        var noteOnly = w.chapters === 0;
        var meta = noteOnly
          ? "described, no text in the sources"
          : w.chapters + (w.chapters === 1 ? " chapter" : " chapters") +
            (w.verses ? " · " + fmt(w.verses) + " verses" : "") +
            " · " + fmt(w.words) + " words";
        grid.appendChild(el("a", {
          class: "work" + (noteOnly ? " note-only" : ""),
          href: "#/read/" + w.id + "/0"
        }, [
          el("span", { class: "work-title", text: titleCase(w.title) }),
          el("span", { class: "work-meta", text: meta })
        ]));
      });
      body.appendChild(grid);

      var era = el("div", {
        class: "era" + (openState ? " open" : ""),
        "data-collection": isCollection ? "1" : "0"
      });

      var head = el("button", {
        class: "era-head",
        "aria-expanded": openState ? "true" : "false",
        onclick: function () {
          var now = !era.classList.contains("open");
          era.classList.toggle("open", now);
          head.setAttribute("aria-expanded", now ? "true" : "false");
          store.set("era:" + s.id, now);
        }
      }, [
        el("span", { class: "era-num", text: s.roman || "＋" }),
        el("span", { class: "era-name", text: titleCase(s.name || s.title) }),
        s.dates ? el("span", { class: "era-date", text: s.dates }) : null,
        el("span", { class: "era-count", text: s.works.length + " works" })
      ]);

      era.appendChild(head);
      era.appendChild(body);
      line.appendChild(era);
    });

    wrap.appendChild(line);
    return wrap;
  }

  /* ================================================================
     CONTENTS — chronological or canonical
     ================================================================ */

  function viewContents(manifest, canon) {
    var wrap = el("div", { class: "wrap" });
    wrap.appendChild(el("h1", { text: "Contents" }));
    wrap.appendChild(el("p", {
      class: "lede",
      text: "The same library, sorted two ways. Chronological is the order of " +
            "this edition. Canonical is the order a printed Bible would use, " +
            "which lets you see how far a book travels between the two."
    }));

    var mode = store.get("contents-mode", "chrono");
    var body = el("div");

    var seg = el("div", { class: "seg" });
    [["chrono", "Chronological"], ["canon", "Canonical"]].forEach(function (p) {
      seg.appendChild(el("button", {
        "aria-pressed": mode === p[0] ? "true" : "false",
        text: p[1],
        onclick: function () {
          mode = p[0];
          store.set("contents-mode", mode);
          Array.prototype.forEach.call(seg.children, function (b) {
            b.setAttribute("aria-pressed", b.textContent === p[1] ? "true" : "false");
          });
          render();
        }
      }));
    });
    wrap.appendChild(el("div", { class: "toolbar" }, [seg]));
    wrap.appendChild(body);

    var byId = {};
    manifest.sections.forEach(function (s) {
      s.works.forEach(function (w) { byId[w.id] = { w: w, s: s }; });
    });

    function render() {
      body.innerHTML = "";
      var table = el("table", { class: "grid" });

      if (mode === "chrono") {
        table.appendChild(el("thead", {}, [el("tr", {}, [
          el("th", { text: "Era" }), el("th", { text: "Work" }),
          el("th", { text: "Dated" }),
          el("th", { class: "num", text: "Chapters" }),
          el("th", { class: "num", text: "Words" })
        ])]));
        var tb = el("tbody");
        manifest.sections.forEach(function (s) {
          s.works.forEach(function (w) {
            tb.appendChild(el("tr", {}, [
              el("td", { class: "muted", text: s.roman || "—" }),
              el("td", {}, [el("a", { href: "#/read/" + w.id + "/0", text: titleCase(w.title) })]),
              el("td", { class: "muted", text: s.dates || "—" }),
              el("td", { class: "num", text: w.chapters || "—" }),
              el("td", { class: "num", text: w.words ? fmt(w.words) : "—" })
            ]));
          });
        });
        table.appendChild(tb);
      } else {
        table.appendChild(el("thead", {}, [el("tr", {}, [
          el("th", { text: "Book" }), el("th", { text: "Division" }),
          el("th", { text: "Where it sits here" }), el("th", { text: "Read" })
        ])]));
        var tb2 = el("tbody");
        canon.books.forEach(function (b) {
          var eras = b.works.map(function (id) {
            return byId[id] ? (byId[id].s.roman || "—") : null;
          }).filter(Boolean);
          var links = el("td");
          if (!b.works.length) {
            links.appendChild(el("span", { class: "muted", text: "not in this volume" }));
          } else {
            b.works.forEach(function (id, i) {
              if (i) links.appendChild(document.createTextNode(" · "));
              var m = byId[id];
              links.appendChild(el("a", {
                href: "#/read/" + id + "/0",
                text: m ? titleCase(m.w.title).replace(/\s*\(.*\)$/, "") : id
              }));
            });
          }
          tb2.appendChild(el("tr", {}, [
            el("td", {}, [el("strong", { text: b.name })]),
            el("td", { class: "muted", text: b.division }),
            el("td", { class: "muted", text: eras.length ? "Section " + eras.join(", ") : "—" }),
            links
          ]));
        });
        table.appendChild(tb2);
      }
      body.appendChild(scroller(table, "Contents, scrollable sideways"));
    }

    render();
    return wrap;
  }

  /* ================================================================
     READER
     ================================================================ */

  function viewRead(manifest, workId, chapterIdx, anchor) {
    var meta = null, section = null;
    manifest.sections.forEach(function (s) {
      s.works.forEach(function (w) { if (w.id === workId) { meta = w; section = s; } });
    });
    if (!meta) {
      setTitle("No such work");
      return el("div", { class: "wrap" }, [
        el("div", { class: "crumbs" }, [
          el("a", { href: "#/", text: "Timeline" }),
          document.createTextNode(" → "),
          el("span", { text: "Not found" })
        ]),
        el("h1", { text: "No such work" }),
        el("p", { class: "empty", text: workId
          ? "Nothing in this volume is filed under “" + workId + "”. It may " +
            "have been renamed, or the link may have been mistyped."
          : "That link does not name a work to open." }),
        el("p", {}, [
          el("a", { class: "chip", href: "#/contents", text: "Everything in the volume" }),
          document.createTextNode(" "),
          el("a", { class: "chip", href: "#/search", text: "Search the text" })
        ])
      ]);
    }

    var wrap = el("div", { class: "wrap" });
    var head = el("div", { class: "reader-head" });

    head.appendChild(el("div", { class: "crumbs" }, [
      el("a", { href: "#/", text: "Timeline" }),
      document.createTextNode(" → "),
      el("span", { text: (section.roman ? "Section " + section.roman + ". " : "") +
                          titleCase(section.name || section.title) +
                          (section.dates ? " · " + section.dates : "") })
    ]));
    head.appendChild(el("h1", { text: titleCase(meta.title) }));
    /* The chapter picker and the work's notes go in boxes of their own so
       that arranging them below is moving two nodes rather than four, and so
       that putting them back is an insertBefore against an anchor that has
       not itself moved. */
    var chapterNav = el("div", { class: "chapter-nav" });
    head.appendChild(chapterNav);
    wrap.appendChild(head);

    var body = el("div");
    wrap.appendChild(body);
    body.appendChild(el("p", { class: "loading", text: "Loading…" }));

    getJSON("works/" + workId + ".json").then(function (work) {
      body.innerHTML = "";

      var workNotes = el("div", { class: "work-notes" });
      body.appendChild(workNotes);

      if (meta.note && meta.note.length) {
        /* A work carrying a caution is being corrected, not annotated: the
           note above its text is the sentence saying this is not the book you
           came for. Marked so it reads as one. */
        var nb = el("div", { class: "note-block" +
                                    (meta.caution ? " is-caution" : "") });
        meta.note.forEach(function (p) { nb.appendChild(el("p", { text: p })); });
        workNotes.appendChild(nb);
      }

      if (meta.positions) {
        workNotes.appendChild(positionsPanel(meta.positions));
      }

      if (!work.chapters.length) {
        setTitle(titleCase(meta.title));
        body.appendChild(el("p", {
          class: "empty",
          text: "This work is described in the volume but no text was available " +
                "from a public-domain source. See the accuracy report for why."
        }));
        listeningDeadEnd();
        return;
      }

      var asked = chapterIdx | 0;
      var idx = Math.max(0, Math.min(asked, work.chapters.length - 1));
      var chapter = work.chapters[idx];

      /* Clamping is right -- #/read/amos/9999 should show Amos 9 rather than
         an error -- but leaving the address saying 9999 afterwards is not.
         That URL gets bookmarked, copied, and put in the history as though
         it were a real place, and every out-of-range number becomes another
         address serving the same chapter.

         replaceState rather than an assignment, because this is a correction
         to where you already are and not a move: assigning to the hash would
         leave the false address sitting in the history for Back to walk into,
         which is the same bug with an extra step. Changing the hash this way
         raises no hashchange, so the route does not run again. */
      if (idx !== asked) {
        history.replaceState(null, "", "#/read/" + workId + "/" + idx +
                             (anchor ? "/" + anchor : ""));
      }

      /* 2,537 chapters used to share one title. This is the one place a
         browser records where you have been, and the one thing a screen
         reader says when a page arrives. */
      setTitle(chapterHeading(meta.title, chapter.label));

      store.set("last", { work: workId, chapter: idx, title: meta.title });
      refreshResume();

      // Psalms is a 150-button grid to scroll through. Past about forty
      // chapters, hunting stops being viable and you need to just say a number.
      if (work.chapters.length > 40) {
        var jump = el("form", {
          class: "chapter-jump",
          onsubmit: function (e) {
            e.preventDefault();
            var n = parseInt(field.value, 10);
            if (!n || n < 1 || n > work.chapters.length) {
              announce("Enter a number between 1 and " + work.chapters.length);
              return;
            }
            location.hash = "#/read/" + workId + "/" + (n - 1);
          }
        });
        var field = el("input", {
          type: "number", min: "1", max: String(work.chapters.length),
          placeholder: "1–" + work.chapters.length,
          "aria-label": "Jump to a chapter of " + titleCase(meta.title) +
                        ", between 1 and " + work.chapters.length
        });
        jump.appendChild(field);
        jump.appendChild(el("button", { class: "chip", type: "submit", text: "Go" }));
        chapterNav.appendChild(jump);
      }

      if (work.chapters.length > 1) {
        var strip = el("div", { class: "chapter-strip" });
        var hereLink = null;
        work.chapters.forEach(function (c, i) {
          var a = el("a", {
            href: "#/read/" + workId + "/" + i,
            "aria-current": i === idx ? "true" : null,
            title: c.label,
            text: c.n === null || c.n === undefined
              ? c.label.replace(/^.*?(\d+).*$/, "$1") || "·"
              : String(c.n)
          });
          if (i === idx) hereLink = a;
          strip.appendChild(a);
        });
        chapterNav.appendChild(strip);

        /* The strip scrolls once it is past two rows, and it used to open at
           the top of itself whatever chapter you were in: Psalm 119 showed
           you the first sixty numbers and left you to hunt for the one you
           were reading. Put the current chapter in view instead -- after the
           strip is in the document, because until then it has no height to
           scroll. Not scrollIntoView, which would take the whole page with
           it and move the chapter you are reading off the screen. */
        if (hereLink) {
          setTimeout(function () {
            if (!strip.isConnected) return;
            var want = hereLink.offsetTop -
                       (strip.clientHeight - hereLink.offsetHeight) / 2;
            strip.scrollTop = Math.max(0, want);
          }, 0);
        }
      }

      var perLine = store.get("verse-per-line", false);
      var size = store.get("reader-size", 1.075);
      var reader = el("div", { class: "reader" + (perLine ? " verse-per-line" : "") });
      document.documentElement.style.setProperty("--reader-size", size + "rem");

      var here = workId + "/" + idx;
      var marked = isSaved(here);

      var controls = el("div", { class: "reader-controls" }, [
        el("button", {
          class: "chip", "aria-pressed": marked ? "true" : "false",
          text: marked ? "★ Chapter saved" : "☆ Save chapter",
          title: "Keep this whole chapter in your saved list",
          onclick: function (e) {
            marked = toggleSave({
              id: here, kind: "chapter", work: workId,
              workTitle: meta.title, chapter: idx, label: chapter.label
            });
            e.currentTarget.textContent = marked ? "★ Chapter saved" : "☆ Save chapter";
            e.currentTarget.setAttribute("aria-pressed", marked ? "true" : "false");
          }
        }),
        el("button", {
          class: "chip", "aria-pressed": perLine ? "true" : "false",
          text: "One verse per line",
          onclick: function (e) {
            perLine = !perLine;
            store.set("verse-per-line", perLine);
            reader.classList.toggle("verse-per-line", perLine);
            e.currentTarget.setAttribute("aria-pressed", perLine ? "true" : "false");
          }
        }),
        el("button", {
          class: "chip", text: "A−", title: "Smaller text",
          onclick: function () {
            size = Math.max(0.85, Math.round((size - 0.075) * 1000) / 1000);
            store.set("reader-size", size);
            document.documentElement.style.setProperty("--reader-size", size + "rem");
          }
        }),
        el("button", {
          class: "chip", text: "A+", title: "Larger text",
          onclick: function () {
            size = Math.min(1.6, Math.round((size + 0.075) * 1000) / 1000);
            store.set("reader-size", size);
            document.documentElement.style.setProperty("--reader-size", size + "rem");
          }
        })
      ]);
      body.appendChild(controls);
      // The chapter's rubric goes on the leaf it heads, not above it: in a
      // codex the heading is part of the page, and the leaf is where this
      // volume draws the line between the text and the apparatus round it.
      var chapterTitle = el("h2", { class: "chapter-title", text: chapter.label });
      reader.appendChild(chapterTitle);

      // What the narrator will read, in the order it appears, pointing at the
      // very nodes just rendered so the highlight lands on the visible text.
      // It opens with the heading the way a recording does — and names the
      // work as well on its first chapter, which is where one work has just
      // run on into the next.
      var passages = [{
        el: chapterTitle, node: null, unit: "heading", verse: null,
        text: (idx === 0 ? titleCase(meta.title) + ". " : "") + chapter.label + "."
      }];

      if (chapter.verses && chapter.verses.length) {
        var p = el("p");
        chapter.verses.forEach(function (v) {
          var span = el("span", {
            class: "v" + (isSaved(workId + "/" + idx + "/v" + v.v) ? " is-saved" : ""),
            id: "v" + v.v
          });
          // The verse number is the one control per verse: it opens the
          // actions rather than adding a second tab stop to every verse.
          // Psalm 119 would otherwise contribute 176 extra of them.
          span.appendChild(el("button", {
            class: "vnum",
            text: String(v.v),
            "aria-label": "Verse " + v.v + " of " + chapter.label +
                          ", open verse actions",
            "aria-expanded": "false",
            onclick: function (e) {
              e.stopPropagation();
              verseMenu(e.currentTarget, {
                work: workId, workTitle: meta.title, chapter: idx,
                label: chapter.label, v: v.v, t: v.t
              });
            }
          }));
          var textNode = document.createTextNode(v.t + " ");
          span.appendChild(textNode);
          passages.push({ el: span, node: textNode, text: v.t, verse: v.v });
          p.appendChild(span);
        });
        reader.appendChild(p);
      } else {
        (chapter.paras || []).forEach(function (t) {
          var para = el("p", { text: t });
          reader.appendChild(para);
          passages.push({ el: para, node: para.firstChild, text: t,
                          verse: null, unit: "paragraph" });
        });
      }
      body.appendChild(reader);

      attachListening({
        work: workId, workTitle: meta.title, chapter: idx, label: chapter.label,
        next: idx < work.chapters.length - 1 ? idx + 1 : null,
        nextWork: nextWorkAfter(manifest, workId)
      }, passages, controls);

      // What actually survives, and where you can look at it. Nothing is
      // reproduced -- these objects are all rights reserved -- but linking is
      // always allowed, and the site already rests arguments on them.
      getJSON("manuscripts.json").then(function (ms) {
        var ids = (ms.works || {})[workId];
        if (!ids || !ids.length) return;

        var box = el("details", { class: "witnesses" });
        box.appendChild(el("summary", {
          role: "heading", "aria-level": "2",
          text: "What survives · " + ids.length +
                (ids.length === 1 ? " manuscript" : " manuscripts") }));

        ids.forEach(function (id) {
          var w = ms.witnesses[id];
          if (!w) return;
          box.appendChild(el("div", { class: "witness" }, [
            el("h3", {}, [
              el("a", { href: w.url, target: "_blank",
                        rel: "noopener noreferrer", text: w.name })
            ]),
            el("p", { class: "witness-when", text:
              w.date + " · " + w.found + " · " + w.where }),
            el("p", { class: "witness-holds", text: w.holds }),
            el("p", { class: "witness-why", text: w.why }),
            el("p", { class: "witness-rights", text: w.rights })
          ]));
        });
        body.insertBefore(box, body.firstChild);
      }).catch(function () {});

      // After the text rather than before it: the chapter is the thing, and
      // the geography is what you turn to once you have read it.
      body.appendChild(chapterMap(workId, idx, chapter.label));

      var src = manifest.sources && manifest.sources[meta.source];
      if (src) {
        body.appendChild(el("div", { class: "apparatus", html:
          "<strong>Text.</strong> " + esc(src.label) + ". " + esc(src.detail) }));
      }

      var pager = el("div", { class: "pager" });
      if (idx > 0) {
        pager.appendChild(el("a", {
          href: "#/read/" + workId + "/" + (idx - 1),
          text: "← " + work.chapters[idx - 1].label
        }));
      } else pager.appendChild(el("span", { class: "spacer" }));
      if (idx < work.chapters.length - 1) {
        pager.appendChild(el("a", {
          href: "#/read/" + workId + "/" + (idx + 1),
          text: work.chapters[idx + 1].label + " →"
        }));
      }
      body.appendChild(pager);

      /* ---------------- the apparatus, on a phone ----------------

         Measured before it was changed: the first verse of Genesis sat 743px
         down a 568px iPhone SE, and the reason was not any one block but the
         sum of a header, a breadcrumb, a title, a chapter box, fifty chapter
         numbers, a work note, a dating panel and five buttons. Tightening the
         spacing of all of it bought 43px. This is the rest, and it is a
         reordering rather than a removal: on a narrow screen the chapter
         picker and the work's notes go after the chapter instead of before
         it, so what is on screen when the page opens is scripture.

         It reads as the better order on a phone anyway. The picker is what
         you want when you have finished a chapter, not before you have begun
         one, and it lands beside the pager that does the same job for the
         next chapter along. Nothing is hidden, collapsed or dropped: the
         wall of numbers is still a wall of numbers, which is how you see how
         long a book is, and every link that was on screen is still on screen.

         Moved in the DOM rather than with CSS order. Visual order and focus
         order have to agree -- a keyboard tabbing through a page that reads
         one way and tabs another is the accessibility fault that reordering
         in CSS quietly introduces.

         Re-run on the media query rather than once, because a phone turned on
         its side crosses this boundary: a 14 Pro is 393px upright and 852
         across. Rebuilding the route would have been simpler and would throw
         away the scroll position and stop the voice mid-verse. */
      arrangeApparatus(body, chapterNav, workNotes);

      if (anchor) {
        var target = document.getElementById(anchor);
        if (target) {
          target.classList.add("target");
          target.scrollIntoView({ block: "center" });
        }
      }
    }).catch(function (e) {
      body.innerHTML = "";
      body.appendChild(el("p", { class: "empty", text: "Could not load this work: " + e.message }));
    });

    return wrap;
  }

  /* ---------------- who wrote this, and when ----------------
     Both traditions get the same heading style, the same box, the same
     space. The volume is *arranged* by the critical dating, so this panel
     is where the other reading gets stated in full rather than implied by
     its absence. */

  var GAP_TEXT = {
    none:   "broadly agreed",
    narrow: "they differ",
    wide:   "sharply divided"
  };

  /* ---------------- the date card ----------------

     The two positions are prose, which is the right form for the claim and
     the wrong form for seeing how far apart they are. tools/dates.py reads a
     numeric span out of each where the wording commits to one, and the card
     shows the two as bars on a shared scale: on Amos they sit on top of each
     other, on Genesis they are seven centuries apart, and the difference is
     the thing this volume is actually about.

     Where a position names a person rather than a date -- "Samuel",
     "Moses, shortly before his death" -- there is no bar, and the card says
     so. Drawing a plausible one would be inventing evidence. */

  /* --8<-- span: start --8<--
     The same two functions live in tools/dates.py as label() and describe(),
     because the static timeline page has to write these ranges out in a
     language the reader is not running. Two copies of a rule is two rules
     unless something checks, so tests/python/test_span_agreement.py runs this
     block in Node against the Python over a sample built out of the awkward
     cases: an open end, a range crossing the era boundary, a single year, an
     approximate one. If this block moves, move the markers with it. */
  function yearText(y) {
    return Math.abs(y) + (y < 0 ? " BCE" : " CE");
  }

  function spanText(sp) {
    if (!sp) return "no date given";
    var head = sp.approx ? "c. " : "";
    /* One end unstated. Printing the figure alone would turn "before c. 900
       BCE" into a claim that something was written in 900 BCE. */
    if (sp.open) return sp.open + " " + head + yearText(sp.to);
    if (sp.frm === sp.to) return head + yearText(sp.frm);
    if ((sp.frm < 0) === (sp.to < 0)) {
      return head + Math.abs(sp.frm) + "–" + yearText(sp.to);
    }
    return head + yearText(sp.frm) + " – " + yearText(sp.to);
  }
  /* --8<-- span: end --8<-- */

  /* How firm the span is, in the reader's terms rather than the parser's. */
  var SPAN_KIND = {
    explicit: "as dated",
    decade: "to the decade",
    century: "to the century",
    period: "to the period"
  };

  function dateCard(p) {
    var sp = p.span;
    if (!sp || (!sp.trad && !sp.crit)) return null;

    var card = el("div", { class: "datecard" });

    /* One scale for both bars, padded so a single-year position is still
       visible as something rather than as a hairline. */
    var ends = [];
    ["trad", "crit"].forEach(function (k) {
      if (sp[k]) { ends.push(sp[k].frm, sp[k].to); }
    });
    var lo = Math.min.apply(null, ends), hi = Math.max.apply(null, ends);
    var pad = Math.max(25, Math.round((hi - lo) * 0.08));
    lo -= pad; hi += pad;
    var at = function (y) { return ((y - lo) / (hi - lo)) * 100; };

    var scale = el("div", { class: "datescale" });
    [["trad", "Traditional"], ["crit", "Critical"]].forEach(function (pair) {
      var one = sp[pair[0]];
      var row = el("div", { class: "daterow " + pair[0] });
      row.appendChild(el("span", { class: "datelabel", text: pair[1] }));

      var track = el("div", { class: "datetrack" });
      if (one) {
        var bar = el("span", { class: "datebar " + one.kind });
        bar.style.left = at(one.frm) + "%";
        bar.style.width = Math.max(1.5, at(one.to) - at(one.frm)) + "%";
        bar.title = spanText(one) + " (" + (SPAN_KIND[one.kind] || one.kind) + ")";
        track.appendChild(bar);
      } else {
        track.appendChild(el("span", { class: "dateunknown",
                                       text: "names a person, not a date" }));
      }
      row.appendChild(track);
      row.appendChild(el("span", { class: "datespan", text: spanText(one) }));
      scale.appendChild(row);
    });
    card.appendChild(scale);

    /* The one number that says what the card is for. */
    var verdict;
    if (sp.apart === null || sp.apart === undefined) {
      verdict = "The two positions cannot be compared as dates: one of them " +
                "names a person rather than a time.";
    } else if (sp.apart === 0) {
      verdict = "The two datings overlap. This is a book the traditional and " +
                "critical positions agree about, whatever else they differ on.";
    } else {
      verdict = "The two datings are " + fmt(sp.apart) + " years apart at " +
                "their closest.";
    }
    card.appendChild(el("p", { class: "dateverdict", text: verdict }));

    card.appendChild(el("p", { class: "datecite", html:
      "Read from the two positions below, which carry the citations. How the " +
      "spans are derived, and what they are not: " +
      "<a href=\"#/method\">the dating method</a>. " +
      "<a href=\"#/accuracy\">Accuracy report</a>." }));

    return card;
  }

  /* The one place the phone layout is decided, so there is one answer to
     "where does the apparatus go" rather than one per block. 620px is the
     breakpoint the stylesheet already uses for the reading page. */
  var NARROW = window.matchMedia("(max-width: 620px)");

  function arrangeApparatus(body, chapterNav, workNotes) {
    /* Where each box sits on a wide screen, recorded before anything moves.
       Both anchors are nodes that stay put -- the picker's parent is the
       head and the notes' next sibling is the controls -- so putting them
       back cannot depend on the position of something that also moved. */
    var homes = [chapterNav, workNotes].map(function (node) {
      return { node: node, parent: node.parentNode, next: node.nextSibling };
    });

    function place() {
      if (NARROW.matches) {
        homes.forEach(function (h) { body.appendChild(h.node); });
      } else {
        homes.forEach(function (h) { h.parent.insertBefore(h.node, h.next); });
      }
    }

    place();

    /* Removed when the page is replaced, or every route change leaves another
       listener behind holding on to a body that is no longer on screen. */
    NARROW.addEventListener("change", place);
    apparatusOff.push(function () { NARROW.removeEventListener("change", place); });
  }

  /* Torn down by the router before it draws the next page. */
  var apparatusOff = [];

  function forgetApparatus() {
    apparatusOff.forEach(function (off) { off(); });
    apparatusOff = [];
  }

  function positionsPanel(p) {
    var open = store.get("positions-open", false);
    var wrap = el("div", { class: "positions" + (open ? " open" : "") });

    var head = el("button", {
      class: "positions-head",
      "aria-expanded": open ? "true" : "false",
      onclick: function () {
        var now = !wrap.classList.contains("open");
        wrap.classList.toggle("open", now);
        head.setAttribute("aria-expanded", now ? "true" : "false");
        head.querySelector(".caret").textContent = now ? "▲" : "▼";
        store.set("positions-open", now);
      }
    }, [
      el("span", { text: "Who wrote this, and when?" }),
      el("span", { class: "gap-tag " + p.gap, text: GAP_TEXT[p.gap] || p.gap }),
      el("span", { class: "caret", text: open ? "▲" : "▼" })
    ]);

    var grid = el("div", { class: "positions-body" });
    var card = dateCard(p);
    if (card) grid.appendChild(card);

    var views = el("div", { class: "stances" }, [
      el("div", { class: "stance" }, [
        el("h3", { text: "Traditional view" }),
        el("p", { class: "claim", text: p.trad }),
        el("p", { class: "why", text: p.tradWhy }),
        el("p", { class: "cite", text: p.tradSource })
      ]),
      el("div", { class: "stance" }, [
        el("h3", { text: "Critical view" }),
        el("p", { class: "claim", text: p.crit }),
        el("p", { class: "why", text: p.critWhy }),
        el("p", { class: "cite", text: p.critSource })
      ])
    ]);
    grid.appendChild(views);

    grid.appendChild(el("p", { class: "positions-foot", html:
      "<strong>Written for this volume, not quoted from a source.</strong> " +
      "The two summaries above are editorial: every claim is referenced so you " +
      "can check it, but the wording is ours, unlike the texts themselves, " +
      "which are reproduced verbatim. This volume is <em>arranged</em> by the " +
      "critical dating, which is a decision about order, not a verdict on " +
      "which column is right." }));

    // Wrapped in an h2 so the document runs h1 (work) > h2 (this panel) >
    // h3 (each view) > h2 (chapter). Screen-reader users navigate by
    // heading level, and a jump from h1 straight to h4 loses them.
    wrap.appendChild(el("h2", { class: "positions-h" }, [head]));
    wrap.appendChild(grid);
    return wrap;
  }

  /* ================================================================
     SAVING -- verses, not just chapters
     ================================================================ */

  /* ---------------- asking not to be thrown away ----------------

     Everything the reader keeps is in local storage, and local storage is
     not permanent. Safari caps script-writable storage for a site at about
     seven days without a first-party visit and then deletes it -- notes,
     saved verses, reading position, all of it -- and nothing fails while it
     happens. The store above reports a write that is refused; there is no
     event at all for a write that succeeded and was collected later, so
     that failure cannot be caught, only prevented or survived.

     This is the prevention, and it is the whole of what a page is allowed to
     ask for: persist() marks the origin as one the browser should not clear
     to reclaim room. Where it is granted the seven days stop applying. It is
     feature-detected and its answer is ignored on purpose -- browsers differ
     on whether they grant it, on whether they ask the reader first, and on
     whether they answer at all, and there is nothing useful to say to
     somebody whose browser declined. What there is to say is on the saved
     page, next to the button that writes a file: surviving it is the half of
     this that does not depend on a browser agreeing to anything.

     Asked after a save rather than on load, because that is the first moment
     there is anything worth keeping, and because a browser weighing the
     request looks kindly on a page the reader has just used. */
  var askedToPersist = false;

  function keepStorage() {
    if (askedToPersist) return;
    askedToPersist = true;
    try {
      if (navigator.storage && navigator.storage.persist) navigator.storage.persist();
    } catch (e) { /* older browsers, and private modes that refuse to answer */ }
  }

  function savedItems() { return store.get("saved", []); }

  function isSaved(id) {
    return savedItems().some(function (s) { return s.id === id; });
  }

  function toggleSave(item) {
    var list = savedItems().filter(function (s) { return s.id !== item.id; });
    var wasSaved = list.length !== savedItems().length;
    if (!wasSaved) {
      item.at = Date.now();
      list.unshift(item);
    }
    if (!store.set("saved", list.slice(0, 500))) {
      announce(STORAGE_FAILED);
      return wasSaved;          // nothing changed, so neither does the button
    }
    if (!wasSaved) keepStorage();
    announce(wasSaved ? "Removed from saved" : "Saved");
    return !wasSaved;
  }

  function verseId(ref) { return ref.work + "/" + ref.chapter + "/v" + ref.v; }

  /* ---------------- citing a passage ----------------

     A reader who wants to quote this has to be able to say where it came
     from, and "a website" is not a citation. What makes a reference to this
     volume worth anything is the two things an ordinary Bible reference
     leaves out: which public-domain edition the text is from, and where the
     passage sits in the composition order, which is the whole reason for
     reading it here.

     Everything below is built from the manifest the page already has. */

  var SOURCE_CITE = {
    web: "The World English Bible with Deuterocanon (eBible.org), public domain",
    charles: "R. H. Charles, ed., The Apocrypha and Pseudepigrapha of the Old " +
             "Testament, Oxford, 1913, public domain",
    anf: "Ante-Nicene Fathers, ed. Alexander Roberts and James Donaldson, " +
         "1885, public domain",
    editorial: "Editorial summary written for this volume; no public-domain " +
               "primary text was available"
  };

  /* The verse menu and the saved page both need to name a work's edition and
     era, and neither of them is inside the view that loaded the manifest.
     route() puts it here as it goes. */
  var MANIFEST = null;

  function workContext(manifest, workId) {
    manifest = manifest || MANIFEST;
    if (!manifest) return null;
    var found = null;
    manifest.sections.forEach(function (s) {
      s.works.forEach(function (w) {
        if (w.id === workId) found = { work: w, section: s };
      });
    });
    return found;
  }

  /* The address this site is published at.

     A link is copied in order to be given to somebody else, and the offline
     single-file copy lives at a file:// path on the reader's own disk, which
     is an address that means nothing to anybody else. So that build hands out
     this instead of where it happens to be sitting. Held to the canonical in
     docs/index.html by tests/python/test_site_url.py, for the same reason
     AUDIO_BASE is read out of this file rather than copied into the checker:
     a second copy of an address is a second thing to remember. */
  var SITE = "https://thebookandme.com/";

  function siteRoot() {
    if (location.protocol === "file:") return SITE;
    /* Everything up to the last slash: "/" on the custom domain, "/The-Book/"
       on the project Pages address that still redirects here, and whatever a
       local server is serving from while this is being worked on. */
    return location.origin + location.pathname.replace(/[^/]*$/, "");
  }

  /* Where a verse lives, as a page rather than as a route.

     This used to return the reader's own hash -- .../#/read/amos/4/v13 --
     which is the one URL in the site that cannot be crawled, cannot be
     previewed by anything that unfurls a link, and counts chapters from zero,
     so the link to Amos 5 said 4. All the while tools/build_pages.py was
     writing a real page for that verse at /read/amos/5/, with the text in the
     HTML, a canonical tag, an id on every verse and an entry in the sitemap.
     The address a reader is handed is now that page.

     The chapter's printed address comes from the manifest rather than from
     arithmetic here: see tools/build_slugs.py for why the two numbers differ
     and why neither can be derived from the other. If the manifest has not
     loaded yet, or names a work this reader does not have, the reader's own
     route is still a working link and is better than a broken one. */
  function permalink(ref) {
    var ctx = workContext(null, ref.work);
    var slugs = ctx && ctx.work.slugs;
    var slug = slugs && slugs[ref.chapter];
    if (!slug) {
      return siteRoot() + "#/read/" + ref.work + "/" + ref.chapter +
             (ref.v ? "/v" + ref.v : "");
    }
    return siteRoot() + "read/" + ref.work + "/" + slug + "/" +
           (ref.v ? "#v" + ref.v : "");
  }

  /* A stable key, so two people citing the same verse produce the same one. */
  function bibKey(ctx, ref) {
    var stem = (ctx ? ctx.work.id : ref.work).replace(/[^a-z0-9]+/gi, "");
    return "thebook:" + stem + (ref.chapter + 1) + (ref.v ? "." + ref.v : "");
  }

  function citation(manifest, ref, style) {
    var ctx = workContext(manifest, ref.work);
    if (!ctx) return permalink(ref);
    var title = titleCase(ctx ? ctx.work.title : ref.work);
    var where = title + " " + ref.label + (ref.v ? ":" + ref.v : "");
    var edition = SOURCE_CITE[ctx && ctx.work.source] || "";
    var era = ctx ? (ctx.section.name || ctx.section.title) : "";
    var eraDates = ctx ? ctx.section.dates : "";
    var url = permalink(ref);
    var today = new Date().toISOString().slice(0, 10);

    if (style === "bibtex") {
      return "@incollection{" + bibKey(ctx, ref) + ",\n" +
        "  title     = {" + where + "},\n" +
        "  booktitle = {The Book in Order: Every Text in the Order It Was Written},\n" +
        "  edition   = {" + edition + "},\n" +
        (era ? "  series    = {" + titleCase(era) +
               (eraDates ? ", " + eraDates : "") + "},\n" : "") +
        "  url       = {" + url + "},\n" +
        "  urldate   = {" + today + "}\n" +
        "}";
    }

    /* Plain, for pasting into anything that is not a bibliography. */
    return where + ". " + edition + ". " +
           (era ? "Arranged under " + titleCase(era) +
                  (eraDates ? ", " + eraDates : "") + ". " : "") +
           url + " (accessed " + today + ").";
  }

  function copyText(text, button, said) {
    var done = function () {
      var was = button.textContent;
      button.textContent = "Copied";
      announce(said);
      setTimeout(function () { button.textContent = was; }, 1600);
    };
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, done);
    else done();
  }

  /* The same button feedback copyText() gives, for the things that are not a
     copy: a word in place of the label, put back after a moment. Saying it
     on the button as well as to the screen reader, because a file written to
     a downloads folder is otherwise a button that appears to do nothing. */
  function flash(button, word) {
    if (!button) return;
    var was = button.textContent;
    button.textContent = word;
    setTimeout(function () { button.textContent = was; }, 1600);
  }

  /* A file, rather than the clipboard. Everything the reader keeps lives in
     one browser's storage and can be cleared by it without warning, so this
     is the copy that survives that -- and the only way to carry saved verses
     to another browser, or between this site and the same site installed to
     a home screen, which do not share storage. */
  function saveFile(text, button, name) {
    var stamp = new Date().toISOString().slice(0, 10);
    var url;
    try {
      url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    } catch (e) {
      announce("This browser would not let the page write a file.");
      flash(button, "Could not write");
      return;
    }
    var a = el("a", { href: url, download: name || ("the-book-saved-" + stamp + ".json") });
    document.body.appendChild(a);
    a.click();
    a.remove();
    /* Revoked late: a browser that has not finished reading the blob when
       the URL goes gets an empty file. */
    setTimeout(function () { URL.revokeObjectURL(url); }, 30000);
    announce("Backup written.");
    flash(button, "Written");
  }

  var menu = null;
  function closeMenu() {
    if (menu) {
      var owner = menu.owner;
      menu.node.remove();
      menu = null;
      if (owner) owner.setAttribute("aria-expanded", "false");
    }
  }

  function verseMenu(button, ref) {
    var open = menu && menu.owner === button;
    closeMenu();
    if (open) return;

    var id = verseId(ref);
    var node = el("div", { class: "vmenu", role: "menu",
                           "aria-label": "Actions for verse " + ref.v });

    var saveBtn = el("button", {
      role: "menuitem",
      text: isSaved(id) ? "★  Saved — tap to remove" : "☆  Save this verse",
      onclick: function (e) {
        var now = toggleSave({
          id: id, kind: "verse", work: ref.work, workTitle: ref.workTitle,
          chapter: ref.chapter, label: ref.label, v: ref.v, t: ref.t
        });
        e.currentTarget.textContent = now
          ? "★  Saved — tap to remove" : "☆  Save this verse";
        span.classList.toggle("is-saved", now);
      }
    });
    var span = button.parentNode;
    node.appendChild(saveBtn);

    if (SPEECH_OK && !nar.blocked) {
      node.appendChild(el("button", {
        role: "menuitem", text: "▶  Read aloud from here",
        onclick: function () { closeMenu(); listenFromVerse(ref.v); }
      }));
    }

    node.appendChild(el("button", {
      role: "menuitem", text: "🔗  Copy link to this verse",
      onclick: function (e) {
        copyText(permalink(ref), e.currentTarget, "Link copied");
      }
    }));

    /* A reference to this volume is worth having only if it says which
       public-domain edition the text is from and where the passage sits in
       the composition order. Both are in the manifest; neither is in the
       reference a reader would otherwise type. */
    node.appendChild(el("button", {
      role: "menuitem", text: "❝  Copy a citation",
      onclick: function (e) {
        copyText(citation(MANIFEST, ref, "plain"), e.currentTarget,
                 "Citation copied");
      }
    }));

    node.appendChild(el("button", {
      role: "menuitem", text: "📚  Copy as BibTeX",
      onclick: function (e) {
        copyText(citation(MANIFEST, ref, "bibtex"), e.currentTarget,
                 "BibTeX copied");
      }
    }));

    node.appendChild(el("button", {
      role: "menuitem", text: "⧉  Copy the verse text",
      onclick: function (e) {
        var text = ref.t + " — " + titleCase(ref.workTitle) + " " +
                   ref.label + ":" + ref.v;
        var done = function () {
          e.currentTarget.textContent = "⧉  Text copied";
          announce("Verse text copied");
        };
        if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, done);
        else done();
      }
    }));

    span.appendChild(node);
    button.setAttribute("aria-expanded", "true");
    menu = { node: node, owner: button };
    node.querySelector("button").focus();
  }

  /* ================================================================
     LEXICON -- click any word
     ================================================================ */

  var aliasTable = null;

  function wordAt(x, y) {
    /* Find the word under the pointer without wrapping every word in a span.
       Psalms alone would be ~800,000 elements; this touches none. */
    var range = null;
    if (document.caretRangeFromPoint) {
      range = document.caretRangeFromPoint(x, y);
    } else if (document.caretPositionFromPoint) {
      var pos = document.caretPositionFromPoint(x, y);
      if (pos) {
        range = document.createRange();
        range.setStart(pos.offsetNode, pos.offset);
        range.collapse(true);
      }
    }
    if (!range || range.startContainer.nodeType !== 3) return null;

    var text = range.startContainer.nodeValue || "";
    var i = range.startOffset;
    var isWord = function (c) { return /[A-Za-z’']/.test(c); };
    if (!isWord(text.charAt(i)) && !isWord(text.charAt(i - 1))) return null;

    var a = i, b = i;
    while (a > 0 && isWord(text.charAt(a - 1))) a--;
    while (b < text.length && isWord(text.charAt(b))) b++;
    if (b <= a) return null;

    return { text: text, start: a, end: b, word: text.slice(a, b) };
  }

  function phrasesAround(hit) {
    /* Longest match first, so "Sea of Galilee" beats "Sea". */
    var before = hit.text.slice(Math.max(0, hit.start - 40), hit.start);
    var after = hit.text.slice(hit.end, hit.end + 40);
    var lead = (before.match(/([A-Za-z'’]+\s+){0,2}$/) || [""])[0];
    var tail = (after.match(/^(\s+[A-Za-z'’]+){0,2}/) || [""])[0];
    var leadWords = lead.trim().split(/\s+/).filter(Boolean);
    var tailWords = tail.trim().split(/\s+/).filter(Boolean);

    var out = [];
    for (var l = leadWords.length; l >= 0; l--) {
      for (var t = tailWords.length; t >= 0; t--) {
        out.push(leadWords.slice(leadWords.length - l)
          .concat([hit.word], tailWords.slice(0, t)).join(" "));
      }
    }
    out.sort(function (a, b) { return b.length - a.length; });
    return out;
  }

  function lookup(term) {
    var key = normTerm(term);
    if (!key) return Promise.resolve(null);
    return getJSON("lexicon-aliases.json").catch(function () { return {}; })
      .then(function (al) {
        aliasTable = al;
        var target = al[key] || key;
        var shard = /^[a-z]/.test(target) ? target[0] : "0";
        return Promise.all([
          getJSON("lexicon/" + shard + ".json").catch(function () { return {}; }),
          getJSON("places/" + shard + ".json").catch(function () { return {}; })
        ]).then(function (r) {
          var table = r[0], places = r[1];
          var hit = table[target];
          // Singular/plural and possessive are the common misses.
          if (!hit && /s$/.test(target)) hit = table[target.replace(/s$/, "")];
          if (!hit) hit = table[target + "s"];
          var place = places[target] ||
                      (/s$/.test(target) ? places[target.replace(/s$/, "")] : null);
          if (!hit && !place) return null;
          return { key: target, entry: hit, place: place };
        });
      });
  }

  var sheet = null;

  function closeSheet() {
    if (!sheet) return;
    sheet.remove();
    sheet = null;
    // Send focus back where it came from, or a keyboard user is dumped at
    // the top of the document every time they close a definition.
    if (lastFocus && document.contains(lastFocus)) lastFocus.focus();
    lastFocus = null;
  }

  function lookupAndShow(term) {
    if (!term) return;
    lookup(term).then(function (found) { showEntry(term, found); });
  }

  /* How far back to stand, by what kind of thing it is. A region needs the
     camera much higher than a village, and pretending otherwise would show a
     confident pin on a territory. */
  /* ================================================================
     THE MAP -- where the chapter happens
     ------------------------------------------------------------------
     The gazetteer has given every place its coordinates since the start,
     and a pair of coordinates is a number the reader has to imagine. This
     draws them.

     What it draws is land and water and nothing else. A modern border laid
     over the Iron Age Levant is an anachronism the moment it is drawn, and
     this volume has no business asserting one. Natural Earth's land
     outlines are public domain, which is why they can be carried offline
     with everything else.

     Which places belong to a chapter is not decided here by scanning the
     text for names. "Dan" is a man, a tribe and a city; a regex guessing
     between them would put pins on the map that no text supports. The
     gazetteer's source carries a curated verse list per place, and
     tools/build_mentions.py resolves those against this volume's own
     parse. Every pin on this map is a reference somebody checked.

     A canvas cannot be read by a screen reader, so everything the canvas
     shows is also on the page as a list of links. That list is not a
     fallback -- it is the same information, and it is what the keyboard
     and the screen reader actually use.
     ================================================================ */

  /* The frame the biblical material sits in: 1,209 of the 1,232 places. The
     23 outside it are Rome, Tarshish, Spain, Ophir and the rest of the
     western and eastern horizon, and they are why the world layer exists. */
  var LEVANT = { w: 20, s: 12, e: 55, n: 42 };

  /* Every map ever drawn has to follow the theme and the window, and it used
     to arrange that for itself: three listeners added when the map opened --
     the theme button, the system colour-scheme query, the window resize --
     and none ever taken off again. They close over the canvas, the places and
     the redraw, so nothing on a chapter you have left can be collected, and
     every theme toggle repaints every map you have ever opened. Reading down
     Psalms with the map open leaves a hundred and fifty of them wired up.

     So the three listeners are registered once, here, and the maps register
     with them instead. A map whose element has left the document is dropped
     the next time anything fires, which is the only moment the answer
     matters. */
  /* Asked each time rather than once: a laptop with a touchscreen answers
     differently depending on what the reader last used, and the answer only
     ever costs a media query. */
  function coarsePointer() {
    return !!(window.matchMedia &&
              window.matchMedia("(pointer: coarse)").matches);
  }

  var liveMaps = [];

  function watchMap(wrap, redraw) {
    liveMaps.push({ wrap: wrap, redraw: redraw });
  }

  function redrawLiveMaps() {
    liveMaps = liveMaps.filter(function (m) { return m.wrap.isConnected; });
    liveMaps.forEach(function (m) { if (m.wrap.open) m.redraw(); });
  }

  document.getElementById("theme").addEventListener("click", function () {
    // After the class has actually changed, not while it is being changed.
    setTimeout(redrawLiveMaps, 0);
  });
  if (window.matchMedia) {
    var schemeQuery = window.matchMedia("(prefers-color-scheme: dark)");
    if (schemeQuery.addEventListener) {
      schemeQuery.addEventListener("change", redrawLiveMaps);
    }
  }
  window.addEventListener("resize", redrawLiveMaps);

  function inFrame(p, f) {
    return p.lon >= f.w && p.lon <= f.e && p.lat >= f.s && p.lat <= f.n;
  }

  /* Equirectangular, with longitude stretched by the cosine of the middle
     latitude so the Mediterranean is not squashed into an oval. Enough for a
     frame this size, and it is four lines rather than a projection library. */
  function projector(frame, w, h) {
    var midlat = (frame.n + frame.s) / 2 * Math.PI / 180;
    var kx = Math.cos(midlat);
    var spanX = (frame.e - frame.w) * kx;
    var spanY = frame.n - frame.s;
    var scale = Math.min(w / spanX, h / spanY);
    var offX = (w - spanX * scale) / 2;
    var offY = (h - spanY * scale) / 2;
    return {
      x: function (lon) { return offX + (lon - frame.w) * kx * scale; },
      y: function (lat) { return offY + (frame.n - lat) * scale; },
      scale: scale
    };
  }

  /* Canvas colours cannot be CSS variables, so they are read from the page
     at draw time. Reading them each draw rather than once is what makes the
     map follow the theme instead of being the one element that ignores it. */
  function inkOf(el) {
    var cs = getComputedStyle(document.documentElement);
    var pick = function (n, fallback) {
      return (cs.getPropertyValue(n) || "").trim() || fallback;
    };
    return {
      sea: pick("--paper", "#f2eee5"),
      land: pick("--paper-2", "#e8e2d6"),
      /* The fill between land and sea is a few points of lightness in either
         theme, and in the dark one it is almost nothing. The coastline is
         what actually makes the shape readable, so it is drawn in the text
         colour rather than the rule colour, which is near-invisible on a
         dark ground. */
      coast: pick("--ink-faint", "#857c8a"),
      pin: pick("--accent", "#6b2d5b"),
      faint: pick("--ink-faint", "#857c8a"),
      /* Names are drawn on top of land, sea and pins, so they carry a halo
         of the ground behind them rather than relying on contrast with
         whatever they happen to land on. */
      text: pick("--ink", "#1d1822"),
      halo: pick("--paper", "#eee7d9")
    };
  }

  var VIEW = {
    point: 4000, within: 3000, approximate: 25000, region: 400000
  };

  var KIND_LABEL = {
    point: "Identified location",
    within: "Inside a larger city",
    approximate: "Approximate location",
    region: "A region, not a point"
  };

  /* One canvas, drawn from a frame, a set of rings and a set of places.
     Returns a redraw function; everything that changes -- theme, zoom, the
     frame -- goes through it, so there is one drawing path and not three. */
  function drawMap(canvas, state) {
    var ctx = canvas.getContext("2d");
    var box = canvas.getBoundingClientRect();
    var w = Math.max(1, Math.round(box.width));
    var h = Math.max(1, Math.round(box.height));

    /* Without this the map is blurry on every phone made since 2014. */
    var dpr = window.devicePixelRatio || 1;
    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr;
      canvas.height = h * dpr;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    var ink = inkOf(canvas);
    var f = state.view;
    var pr = projector(f, w, h);

    ctx.fillStyle = ink.sea;
    ctx.fillRect(0, 0, w, h);

    /* Every ring in one path, filled even-odd, so a lake enclosed by land is
       drawn as water rather than as ground. */
    ctx.beginPath();
    state.rings.forEach(function (ring) {
      for (var i = 0; i < ring.length; i += 2) {
        var x = pr.x(ring[i]), y = pr.y(ring[i + 1]);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.closePath();
    });
    ctx.fillStyle = ink.land;
    ctx.fill("evenodd");
    ctx.strokeStyle = ink.coast;
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.55;
    ctx.stroke();
    ctx.globalAlpha = 1;

    /* Neither overlay below removes a place from the canvas. Dimming and
       ringing are the whole vocabulary, deliberately: the page promises that
       the list beside the map holds the same places the map draws, and an
       overlay that filtered pins would quietly break that promise while
       still looking like a working map. */
    var kin = state.kin ? state.kin.counts : null;

    /* Jerusalem is named 719 times and Jabbok seven. Linear sizing makes one
       a blot and the other invisible, so the count is taken as a logarithm:
       the difference stays legible without the big ones swallowing the map. */
    state.hit = [];
    state.places.forEach(function (p) {
      var x = pr.x(p.lon), y = pr.y(p.lat);
      if (x < -20 || y < -20 || x > w + 20 || y > h + 20) return;
      var r = 2.2 + Math.log(1 + (p.mentions || 1)) * 1.15;
      /* The dot is small because the map is small. The target it answers to
         is not the dot: seven pixels is a comfortable mouse target and a
         quarter of a fingertip, and this map is most often read on a phone.
         Apple asks for 44 and Android for 48; a pin cannot have that without
         swallowing its neighbours, so 22 is the compromise -- four times the
         area, still smaller than the gap between two nearby places. */
      state.hit.push({ x: x, y: y, r: Math.max(r, coarsePointer() ? 22 : 9),
                       place: p });

      /* With a place chosen, the ones it shares a chapter with keep their
         weight and the rest fall back. Nothing is drawn between them: a line
         from one pin to another says the text moved from here to there, and
         being named in the same chapter does not say that. */
      var weight = !kin || p === state.chosen || kin[p.key] > 0 ? 1 : 0.25;

      ctx.beginPath();
      if (p.kind === "region") {
        /* A region is not a pin. It gets a soft halo centred on the point
           the source gives, which is a point inside it, not its middle. */
        var g = ctx.createRadialGradient(x, y, 0, x, y, r * 3.2);
        g.addColorStop(0, ink.pin);
        g.addColorStop(1, "transparent");
        /* The halo is already translucent, so emphasis multiplies rather
           than replaces -- setting it flat would make a dimmed region the
           most solid thing on the map. */
        ctx.globalAlpha = 0.28 * weight;
        ctx.fillStyle = g;
        ctx.arc(x, y, r * 3.2, 0, 6.284);
        ctx.fill();
        ctx.globalAlpha = 1;
      } else if (p.kind === "approximate") {
        /* Open, because the ring says "somewhere here" and a filled dot
           would say "here". */
        ctx.globalAlpha = weight;
        ctx.arc(x, y, r, 0, 6.284);
        ctx.strokeStyle = ink.pin;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([2, 2]);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.globalAlpha = 1;
      } else {
        ctx.globalAlpha = weight;
        ctx.arc(x, y, r, 0, 6.284);
        ctx.fillStyle = ink.pin;
        ctx.fill();
        ctx.strokeStyle = ink.sea;
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.globalAlpha = 1;
      }

      /* A place the library has not named before this chapter. The mark is a
         finely dashed ring outside the pin: clear of the chosen ring, which
         is solid and closer in, and clear of an approximate pin's own dashes,
         which sit on the pin itself rather than around it. */
      if (state.firstHere && state.firstHere[p.key]) {
        ctx.beginPath();
        ctx.arc(x, y, r + 5.5, 0, 6.284);
        ctx.strokeStyle = ink.pin;
        ctx.lineWidth = 1;
        ctx.globalAlpha = 0.6 * weight;
        ctx.setLineDash([1, 3]);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.globalAlpha = 1;
      }

      if (p === state.chosen) {
        ctx.beginPath();
        ctx.arc(x, y, r + 4, 0, 6.284);
        ctx.strokeStyle = ink.pin;
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    });

    /* Names.

       A field of unlabelled dots is a picture of how many places a chapter
       names, and nothing else: to find out that the dot on the coast is
       Ashdod you had to point at it, which on a phone means guessing. The
       names are the map.

       They are placed rather than laid out: each is offered the space to the
       right of its pin and takes it only if that box is inside the canvas and
       clear of every box already taken, so a crowded coast drops the smaller
       names instead of stacking them into a smear. The chosen place is
       written first and therefore never dropped; the rest are written in the
       order the volume names them most often, which is the order in which
       knowing the name is worth most.

       Not a substitute for the list under the canvas. That list is still
       every place, still in the DOM, and still what a screen reader reads. */
    var labels = state.places.slice().sort(function (a, b) {
      if (a === state.chosen) return -1;
      if (b === state.chosen) return 1;
      return (b.mentions || 0) - (a.mentions || 0);
    });
    var taken = [];
    ctx.font = "500 11px " + (getComputedStyle(canvas).fontFamily || "sans-serif");
    ctx.textBaseline = "middle";
    labels.forEach(function (p) {
      var hit = null;
      state.hit.forEach(function (h) { if (h.place === p) hit = h; });
      if (!hit) return;                       // off the canvas at this zoom

      // Dimmed places are context rather than subject: naming them all
      // would undo the emphasis the choosing just made.
      var kin = state.kin && state.kin.counts;
      if (kin && p !== state.chosen && !(kin[p.key] > 0)) return;

      var pad = 3;
      var wide = ctx.measureText(p.name).width;
      var bx = hit.x + hit.r * 0.5 + 5, by = hit.y;
      var box = { l: bx - pad, r: bx + wide + pad, t: by - 7, b: by + 7 };
      // Flip to the left rather than run off the edge.
      if (box.r > canvas.clientWidth - 2) {
        bx = hit.x - hit.r * 0.5 - 5 - wide;
        box = { l: bx - pad, r: bx + wide + pad, t: by - 7, b: by + 7 };
      }
      if (box.l < 2 || box.t < 2 || box.b > canvas.clientHeight - 2) return;
      var clash = taken.some(function (t) {
        return !(box.r < t.l || box.l > t.r || box.b < t.t || box.t > t.b);
      });
      if (clash) return;
      taken.push(box);

      ctx.globalAlpha = p === state.chosen ? 1 : 0.88;
      ctx.lineJoin = "round";
      ctx.lineWidth = 3;
      ctx.strokeStyle = ink.halo;
      ctx.strokeText(p.name, bx, by);
      ctx.fillStyle = p === state.chosen ? ink.pin : ink.text;
      ctx.fillText(p.name, bx, by);
      ctx.globalAlpha = 1;
    });

    /* What the canvas actually put down, in its own words. The page claims
       the list below is the same information as the picture above it, and a
       claim about a canvas is otherwise unfalsifiable: pixels do not say
       which places they are. Saying it here is what lets something check
       that the two agree, rather than checking the list against itself.

       This is what is painted *now*, so it follows the viewport: zoomed in,
       it is a subset of the list, and that is the honest answer rather than
       a promise the picture is not keeping. Unzoomed the two are equal, and
       that is the claim the README makes. */
    canvas.dataset.drawn = state.hit.map(function (h) {
      return h.place.name;
    }).join("\n");
  }

  /* ---------------- what the mention index already knows ----------------

     Two questions can be answered from the file the map already loads, with
     no second index and nothing new to build: where a place is first named
     in the order this volume is arranged in, and which places keep company
     with it. Both are arithmetic over mentions.json. Neither is a claim
     about history, and the wording downstream is careful to say so.

     What they are not is an itinerary. mentions.json records which places a
     chapter names, not the order it names them in and not that anybody
     travelled between them; Paul's journey and a list of nations under
     judgement are the same shape in this data. So nothing here draws a
     route, and nothing here counts a sequence.
     ==================================================================== */

  /* Composition order costs one more file -- chapters.json, which the index
     and the search already fetch, so it is usually in the cache and always
     in the offline build. It is fetched when a reader first asks for first
     appearances rather than on every map, because a chapter map that nobody
     interrogates should not pay for it. */
  var libraryPromise = null;
  function libraryOrder() {
    if (!libraryPromise) {
      libraryPromise = Promise.all([
        getJSON("chapters.json"), getJSON("mentions.json")
      ]).then(function (both) {
        var chapters = both[0].chapters, mentions = both[1];
        var pos = {}, firstSeen = {};
        chapters.forEach(function (c, n) {
          var k = c[0] + "/" + c[1];
          pos[k] = n;
          (mentions[k] || []).forEach(function (key) {
            if (!(key in firstSeen)) firstSeen[key] = n;
          });
        });
        return { chapters: chapters, pos: pos, firstSeen: firstSeen };
      });
    }
    return libraryPromise;
  }

  /* Which places share a chapter with this one, and in how many chapters.
     Answered for one place at a time: the full table would be 1,232 squared
     to answer a question the reader asked about one pin. */
  var kinCache = {};
  function kinOf(key, mentions) {
    if (kinCache[key]) return kinCache[key];
    var counts = {}, chapters = 0;
    Object.keys(mentions).forEach(function (k) {
      var list = mentions[k];
      if (list.indexOf(key) < 0) return;
      chapters++;
      list.forEach(function (other) {
        if (other !== key) counts[other] = (counts[other] || 0) + 1;
      });
    });
    kinCache[key] = { counts: counts, chapters: chapters };
    return kinCache[key];
  }

  function chapterMap(workId, chapterIdx, chapterLabel) {
    var wrap = el("details", { class: "chapter-map" });
    var summary = el("summary", {}, [
      el("span", { text: "Where this chapter happens" })
    ]);
    var tally = el("span", { class: "map-tally" });
    summary.appendChild(tally);
    wrap.appendChild(summary);

    /* How many places, before it is opened rather than after.

       The gazetteer covers the Hebrew Bible and the New Testament, so 1,718
       of the 2,537 chapters have nothing to draw -- and Job has seven maps
       across forty-two chapters, Psalms fifty-five across a hundred and
       fifty. Opening the panel to be told there is nothing, over and over,
       is what a removed feature feels like. The index this counts from is
       60 KB and is the same file the map itself opens with, so the answer
       costs one fetch that was going to happen anyway. */
    getJSON("mentions.json").then(function (table) {
      if (!tally.isConnected) return;
      var n = (table[workId + "/" + chapterIdx] || []).length;
      tally.textContent = n
        ? n + (n === 1 ? " place" : " places")
        : "none in the gazetteer";
      if (!n) tally.className = "map-tally none";
    }).catch(function () { /* the panel still opens and says so itself */ });

    var body = el("div", { class: "map-body" });
    wrap.appendChild(body);

    var loaded = false;
    wrap.addEventListener("toggle", function () {
      if (!wrap.open || loaded) return;
      loaded = true;
      body.appendChild(el("p", { class: "loading", text: "Loading the map…" }));

      getJSON("mentions.json").then(function (table) {
        var keys = table[workId + "/" + chapterIdx] || [];
        if (!keys.length) {
          body.innerHTML = "";
          body.appendChild(el("p", { class: "empty", text:
            "No place in the gazetteer is recorded as named in this chapter. " +
            "The gazetteer covers the books of the Hebrew Bible and the New " +
            "Testament; a chapter outside them, or one that names no place, " +
            "has nothing to draw." }));
          return;
        }

        var shards = {};
        keys.forEach(function (k) {
          shards[/^[a-z]/.test(k) ? k[0] : "0"] = true;
        });
        var names = Object.keys(shards);
        return Promise.all(names.map(function (s) {
          return getJSON("places/" + s + ".json").catch(function () { return {}; });
        })).then(function (loadedShards) {
          var all = {};
          loadedShards.forEach(function (t) {
            Object.keys(t).forEach(function (k) { all[k] = t[k]; });
          });
          /* A place record carries no key of its own -- it is the key that
             found it. Both overlays ask questions of the mention index,
             which is keyed, so the key has to come along. */
          var places = keys.map(function (k) {
            var p = all[k];
            if (p) p.key = k;
            return p;
          }).filter(Boolean);
          if (!places.length) {
            body.innerHTML = "";
            body.appendChild(el("p", { class: "empty",
              text: "The places named here have no coordinates on record." }));
            return;
          }

          /* World or Levant is not a preference, it is whether the chapter
             fits. Acts 27 sails to Rome; opening it on the Levant frame
             would show a reader an empty sea. */
          var needsWorld = places.some(function (p) {
            return !inFrame(p, LEVANT);
          });
          var frame = needsWorld
            ? { w: -25, s: -40, e: 100, n: 62 }
            : LEVANT;

          return getJSON("basemap/" + (needsWorld ? "world" : "levant") + ".json")
            .then(function (base) {
              body.innerHTML = "";
              build(body, places, base.rings, frame, needsWorld, table);
            });
        });
      }).catch(function (e) {
        body.innerHTML = "";
        body.appendChild(el("p", { class: "empty",
          text: "The map could not be loaded. " + String(e.message) }));
      });
    });

    function build(root, places, rings, frame, isWorld, table) {
      var state = {
        rings: rings, places: places, home: frame, view: frame,
        chosen: null, hit: [], kin: null, firstHere: null
      };
      var here = workId + "/" + chapterIdx;
      var onCanvas = {};
      places.forEach(function (p) { onCanvas[p.key] = p; });

      var canvas = el("canvas", {
        class: "map-canvas",
        /* The canvas itself is decoration; the list below it is the content,
           and pointing at it by id is what keeps that claim honest. */
        role: "img",
        "aria-describedby": "map-list-" + workId + "-" + chapterIdx
      });
      var stage = el("div", { class: "map-stage" }, [canvas]);

      /* Give the box the frame's own proportions. Left to fill whatever width
         it is given, a frame taller than it is wide sits in the middle of a
         letterbox with empty margins either side -- and the Levant layer is
         clipped to the frame, so those margins really are empty rather than
         showing the next country along. */
      var midlat = (frame.n + frame.s) / 2 * Math.PI / 180;
      var aspect = ((frame.e - frame.w) * Math.cos(midlat)) / (frame.n - frame.s);
      stage.style.setProperty("--map-aspect", aspect.toFixed(3));
      root.appendChild(stage);

      var redraw = function () { drawMap(canvas, state); };

      var detail = el("div", { class: "map-detail", hidden: true });

      /* Which places share a chapter with this one. The count is of
         chapters, and it is kept well away from placeBlock's "named in N
         passages", which counts something else entirely: Jerusalem is 293
         chapters and 719 passages, and one number wearing the other's
         sentence would be worse than no number at all. */
      function kinBlock(p) {
        var kin = kinOf(p.key, table);
        var ranked = Object.keys(kin.counts).sort(function (a, b) {
          return kin.counts[b] - kin.counts[a] ||
                 (onCanvas[a] ? -1 : 1) - (onCanvas[b] ? -1 : 1) ||
                 a.localeCompare(b);
        }).slice(0, 8);

        var box = el("div", { class: "map-kin" });
        box.appendChild(el("h4", { text: "Named in the same chapter as" }));

        if (!ranked.length) {
          box.appendChild(el("p", { class: "map-kin-none", text:
            "Nowhere. Every chapter that names " + p.name + " names no "
            + "other place in the gazetteer." }));
          return box;
        }

        var ol = el("ol", { class: "map-kin-list" });
        ranked.forEach(function (key) {
          var mate = onCanvas[key];
          var count = kin.counts[key];
          var tail = " · " + count + (count === 1 ? " chapter" : " chapters");
          var li = el("li", {});
          if (mate) {
            /* On this map already, so it can be pointed at. */
            var b = el("button", { class: "map-kin-here", text: mate.name,
                                   onclick: function () { choose(mate); } });
            b.appendChild(el("span", { class: "map-kin-count", text: tail }));
            li.appendChild(b);
          } else {
            /* Off this canvas, so its shard was never loaded and all we hold
               is the index key. "bethel 1" is a lookup key, not a name; the
               gazetteer's own "Bethel 1" is, so it is worth the fetch. The
               shards are small and cached, and the eight shown here are the
               most it can ever ask for. */
            var span = el("span", { class: "map-kin-name", text: key });
            li.appendChild(span);
            li.appendChild(el("span", { class: "map-kin-count", text: tail }));
            getJSON("places/" + (/^[a-z]/.test(key) ? key[0] : "0") + ".json")
              .then(function (shard) {
                if (shard[key]) span.textContent = shard[key].name;
              }).catch(function () { /* the key is a readable fallback */ });
          }
          ol.appendChild(li);
        });
        box.appendChild(ol);

        box.appendChild(el("p", { class: "map-kin-note", text:
          "Counted over every chapter in the volume, from the same curated "
          + "references the pins come from. Sharing a chapter is not travel "
          + "between two places and not a route: nothing here records the "
          + "order a chapter names things in, so nothing here draws one." }));
        return box;
      }

      /* Where the library first names this place, in the order the volume is
         arranged in. Needs chapters.json, so it arrives after the panel. */
      function arrivalLine(p) {
        var line = el("p", { class: "map-arrival" });
        libraryOrder().then(function (order) {
          if (state.chosen !== p) return;   // the reader has moved on
          var first = order.firstSeen[p.key];
          if (first === undefined) return;
          if (first === order.pos[here]) {
            line.appendChild(el("strong", { text: "First named here." }));
            line.appendChild(document.createTextNode(
              " Nothing earlier in the arrangement names " + p.name + "."));
          } else {
            var c = order.chapters[first];
            line.appendChild(document.createTextNode("First named in "));
            line.appendChild(el("a", {
              href: "#/read/" + c[0] + "/" + c[1],
              text: c[3] + ", " + c[2]
            }));
            line.appendChild(document.createTextNode("."));
          }
          line.appendChild(el("span", { class: "map-arrival-note", text:
            " That is where the text sits in this volume's composition "
            + "order, which is an argument about when things were written. "
            + "It is not when the place came to exist, and not the first "
            + "time anyone wrote it down." }));
        });
        return line;
      }

      function choose(p) {
        state.chosen = p;
        state.kin = kinOf(p.key, table);
        detail.innerHTML = "";
        detail.hidden = false;
        detail.appendChild(el("h3", { class: "map-detail-name", text: p.name }));
        detail.appendChild(placeBlock(p));
        detail.appendChild(arrivalLine(p));
        detail.appendChild(kinBlock(p));
        redraw();
        var mates = Object.keys(state.kin.counts).filter(function (k) {
          return onCanvas[k];
        }).length;
        announce(p.name + ", " + (KIND_LABEL[p.kind] || "location") + ". " +
                 (mates ? mates + (mates === 1 ? " place" : " places") +
                          " on this map " +
                          (mates === 1 ? "is" : "are") +
                          " named in a chapter with it."
                        : "No other place on this map is named in a chapter " +
                          "with it.") +
                 " The full list is in the panel.");
      }

      /* A gesture that panned or pinched is not also a choice. Set by the
         pointer handlers below and read here; it used to be set and read by
         nothing at all. */
      var gestured = false;

      canvas.addEventListener("click", function (ev) {
        if (gestured) { gestured = false; return; }
        var b = canvas.getBoundingClientRect();
        var x = ev.clientX - b.left, y = ev.clientY - b.top;
        var best = null, bestD = Infinity;
        state.hit.forEach(function (h) {
          var d = Math.pow(h.x - x, 2) + Math.pow(h.y - y, 2);
          if (d < h.r * h.r && d < bestD) { best = h.place; bestD = d; }
        });
        if (best) choose(best);
      });

      /* Wheel zoom and drag pan, clamped so the frame cannot be dragged off
         into empty ocean and lost. */
      function clamp(v) {
        var home = state.home;
        var wSpan = Math.min(v.e - v.w, home.e - home.w);
        var hSpan = Math.min(v.n - v.s, home.n - home.s);
        if (v.w < home.w) { v.w = home.w; v.e = home.w + wSpan; }
        if (v.e > home.e) { v.e = home.e; v.w = home.e - wSpan; }
        if (v.s < home.s) { v.s = home.s; v.n = home.s + hSpan; }
        if (v.n > home.n) { v.n = home.n; v.s = home.n - hSpan; }
        return v;
      }

      function zoomBy(factor, fx, fy) {
        var v = state.view;
        var cw = (v.e - v.w), ch = (v.n - v.s);
        var nw = cw * factor, nh = ch * factor;
        var maxW = state.home.e - state.home.w;
        if (nw > maxW) { nw = maxW; nh = (state.home.n - state.home.s); }
        if (nw < maxW / 25) return;
        var ax = v.w + cw * fx, ay = v.n - ch * fy;
        state.view = clamp({
          w: ax - nw * fx, e: ax + nw * (1 - fx),
          n: ay + nh * fy, s: ay - nh * (1 - fy)
        });
        redraw();
      }

      canvas.addEventListener("wheel", function (ev) {
        ev.preventDefault();
        var b = canvas.getBoundingClientRect();
        zoomBy(ev.deltaY > 0 ? 1.18 : 0.85,
               (ev.clientX - b.left) / b.width,
               (ev.clientY - b.top) / b.height);
      }, { passive: false });

      /* Pan, and pinch, and the difference between a tap and either.

         Every tap on a touch screen travels a few pixels. The pan used to
         begin on the first of them, and the click that followed was tested
         against the positions the pan had just moved -- so a finger that
         wobbled four pixels slid the map out from under itself and then
         missed a seven-pixel target. Nothing was wrong with the choosing;
         it was being asked where a place had been a moment ago.

         So the pointer has to travel past a dead zone before anything pans,
         and a gesture that crossed it does not also choose. A pinch is two
         pointers, which is the only zoom a phone has: the wheel below is a
         mouse, and until now the wheel was the only way to zoom this map at
         all. */
      var DEAD = 5;
      var pointers = {};
      var live = function () { return Object.keys(pointers); };
      var dragging = null;
      var pinching = null;

      function spread() {
        var ids = live();
        if (ids.length < 2) return null;
        var a = pointers[ids[0]], b2 = pointers[ids[1]];
        return {
          d: Math.hypot(a.x - b2.x, a.y - b2.y),
          mx: (a.x + b2.x) / 2, my: (a.y + b2.y) / 2
        };
      }

      canvas.addEventListener("pointerdown", function (ev) {
        pointers[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
        canvas.setPointerCapture(ev.pointerId);
        if (live().length === 2) {
          pinching = spread();
          dragging = null;
          gestured = true;
        } else if (live().length === 1) {
          dragging = { x: ev.clientX, y: ev.clientY,
                       fromX: ev.clientX, fromY: ev.clientY, panning: false };
        }
      });

      canvas.addEventListener("pointermove", function (ev) {
        if (!pointers[ev.pointerId]) return;
        pointers[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
        var b = canvas.getBoundingClientRect();

        if (pinching) {
          var now = spread();
          if (!now || !now.d || !pinching.d) return;
          zoomBy(pinching.d / now.d,
                 (now.mx - b.left) / b.width, (now.my - b.top) / b.height);
          pinching = now;
          return;
        }
        if (!dragging) return;

        // Nothing moves until the finger has meant it.
        if (!dragging.panning) {
          if (Math.abs(ev.clientX - dragging.fromX) < DEAD &&
              Math.abs(ev.clientY - dragging.fromY) < DEAD) return;
          dragging.panning = true;
          gestured = true;
        }
        var v = state.view;
        var dx = (ev.clientX - dragging.x) / b.width * (v.e - v.w);
        var dy = (ev.clientY - dragging.y) / b.height * (v.n - v.s);
        state.view = clamp({ w: v.w - dx, e: v.e - dx, n: v.n + dy, s: v.s + dy });
        dragging.x = ev.clientX; dragging.y = ev.clientY;
        redraw();
      });

      var endDrag = function (ev) {
        if (ev && ev.pointerId !== undefined) delete pointers[ev.pointerId];
        if (live().length < 2) pinching = null;
        if (!live().length) dragging = null;
      };
      canvas.addEventListener("pointerup", endDrag);
      canvas.addEventListener("pointercancel", endDrag);

      /* Off by default. The caption is a legend of three marks already, and
         a fourth drawn for every reader whether or not they asked is a
         busier map for no gain -- and this one needs a sentence of
         qualification that only makes sense once it has been asked for. */
      var firstOn = false;
      var firstChip = el("button", {
        class: "chip", "aria-pressed": "false", text: "First appearances",
        onclick: function () {
          firstChip.disabled = true;
          libraryOrder().then(function (order) {
            firstOn = !firstOn;
            state.firstHere = null;
            var n = 0;
            if (firstOn) {
              state.firstHere = {};
              places.forEach(function (p) {
                if (order.firstSeen[p.key] === order.pos[here]) {
                  state.firstHere[p.key] = true;
                  n++;
                }
              });
            }
            firstChip.setAttribute("aria-pressed", firstOn ? "true" : "false");
            firstChip.disabled = false;
            /* undefined, not zero: off means the caption loses the sentence
               altogether, where zero would have it announce a count of none. */
            paintFirst(firstOn ? n : undefined);
            redraw();
            announce(firstOn
              ? n + " of " + places.length + " places here are named for the "
                + "first time in the volume's composition order"
              : "First appearances hidden");
          }).catch(function () {
            firstChip.disabled = false;
            announce("The composition order could not be loaded");
          });
        }
      });

      /* Zoom without a wheel and without two hands.

         The wheel was the only way to change the scale, which means a phone
         had no way at all and a keyboard had none either. These are the same
         zoomBy the wheel and the pinch call, centred on the middle of the
         canvas rather than on a pointer, because a button has no position on
         the map. */
      function zoomChip(label, factor, said) {
        return el("button", {
          class: "chip", text: label, "aria-label": said,
          onclick: function () {
            zoomBy(factor, 0.5, 0.5);
            announce(said);
          }
        });
      }

      var tools = el("div", { class: "map-tools" }, [
        zoomChip("−", 1.35, "Zoom out"),
        zoomChip("+", 0.74, "Zoom in"),
        el("button", { class: "chip", text: "Reset", onclick: function () {
          /* The view and the chosen place, not the layer: the reader turned
             that on deliberately and did not ask for it to go away. */
          state.view = state.home; state.chosen = null; state.kin = null;
          detail.hidden = true; redraw();
          announce("Map reset");
        } }),
        firstChip
      ]);
      root.appendChild(tools);
      root.appendChild(detail);

      /* The list is the accessible copy of the canvas, and the only thing a
         keyboard can use. It carries the same places in the same order. */
      var list = el("ul", {
        class: "map-list",
        id: "map-list-" + workId + "-" + chapterIdx
      });
      places.slice().sort(function (a, b) {
        return (b.mentions || 0) - (a.mentions || 0);
      }).forEach(function (p) {
        var b = el("button", {
          class: "map-place map-" + p.kind,
          text: p.name,
          "data-place": p.key,
          onclick: function () { choose(p); }
        });
        /* Appended, never prepended: the button's first child is the name,
           and both the reader's eye and the checks that read this list start
           there. */
        b.appendChild(el("span", { class: "map-place-kind",
                                   text: KIND_LABEL[p.kind] || "Location" }));
        list.appendChild(el("li", {}, [b]));
      });

      /* The canvas is decoration; the list is the content. A mark that
         appeared on the canvas alone would be a layer a keyboard cannot
         reach, so the same fact is written here in words. */
      function paintFirst(n) {
        [].forEach.call(list.querySelectorAll(".map-place"), function (b) {
          var mark = b.querySelector(".map-place-first");
          var isFirst = state.firstHere && state.firstHere[b.dataset.place];
          b.classList.toggle("map-first", !!isFirst);
          if (isFirst && !mark) {
            b.appendChild(el("span", { class: "map-place-first",
              text: "First named here in the composition order" }));
          } else if (!isFirst && mark) {
            b.removeChild(mark);
          }
        });
        caption.innerHTML = captionHTML(n);
        canvas.setAttribute("aria-label", labelText(n));
      }

      function captionHTML(n) {
        return "<strong>" + fmt(places.length) + "</strong> " +
        (places.length === 1 ? "place is" : "places are") + " recorded as " +
        "named in " + esc(chapterLabel || "this chapter") + ". " +
        (isWorld ? "Shown on the world, because this chapter names somewhere " +
                   "outside the biblical frame. " : "") +
        "A filled dot is an identified location, a dashed ring an approximate " +
        "one, and a soft halo a region rather than a point — centred on a " +
        "spot inside it, not on its middle. " +
        /* Only while the layer is on. The qualification is the point: a
           dotted ring with no sentence attached would read as a claim about
           history, which is precisely what it is not. */
        (n === undefined ? "" :
          "A finely dotted outer ring marks the <strong>" + fmt(n) +
          "</strong> named here for the first time in the volume's " +
          "composition order — where the text sits in the argument about " +
          "when things were written, not when a place came to exist. " +
          "The gazetteer covers the Hebrew Bible and the New Testament and " +
          "only references somebody checked, so an absence here is a gap in " +
          "it rather than a fact about the text. ") +
        "Land outlines from Natural Earth, " +
        "public domain. No borders are drawn: there are none to draw.";
      }

      function labelText(n) {
        return "Map of " + places.length + " places named in this chapter. " +
          "The same places are listed below as links." +
          (n === undefined ? "" :
            " " + n + " of them are named here for the first time in the " +
            "volume's composition order.");
      }

      var caption = el("p", { class: "map-caption", html: captionHTML() });
      root.appendChild(caption);
      root.appendChild(list);

      canvas.setAttribute("aria-label", labelText());

      redraw();

      /* The theme is a button and a system setting, and the canvas has to
         follow both or it is the one element stuck in the old palette. The
         three listeners that watch for it are registered once for the whole
         page rather than once per map -- see watchMap below. */
      watchMap(wrap, redraw);
    }

    return wrap;
  }

  function placeBlock(p) {
    var dist = VIEW[p.kind] || 8000;
    // Google Earth's web URL. On a phone with the app installed this opens
    // it directly; otherwise it opens Earth in the browser.
    var earth = "https://earth.google.com/web/@" + p.lat + "," + p.lon +
                ",0a," + dist + "d,35y,0h,45t,0r";
    var maps = "https://www.google.com/maps/search/?api=1&query=" +
               p.lat + "," + p.lon;
    var osm = "https://www.openstreetmap.org/?mlat=" + p.lat +
              "&mlon=" + p.lon + "#map=" + (p.kind === "region" ? 6 : 12) +
              "/" + p.lat + "/" + p.lon;

    var box = el("div", { class: "place place-" + p.kind });

    box.appendChild(el("div", { class: "place-kind" }, [
      el("span", { class: "place-dot", "aria-hidden": "true" }),
      el("span", { text: KIND_LABEL[p.kind] || "Location" })
    ]));

    if (p.modern) {
      box.appendChild(el("p", { class: "place-modern", text: p.modern }));
    }
    if (p.note) {
      box.appendChild(el("p", { class: "place-note", text: p.note }));
    }

    box.appendChild(el("p", { class: "place-coords", text:
      p.lat.toFixed(4) + "°, " + p.lon.toFixed(4) + "°" +
      (p.mentions ? "  ·  named in " + p.mentions +
        (p.mentions === 1 ? " passage" : " passages") : "") }));

    /* Three ways out to a real map of the world. Google Maps is first and
       says so in full: it was labelled "Maps" and sat third, which is a
       label you have to already know the meaning of, in the position you
       look at last. On a phone both Google links open the app if it is
       installed. */
    var links = el("div", { class: "place-links" }, [
      el("a", { class: "chip primary", href: maps,
                target: "_blank", rel: "noopener noreferrer",
                text: "📍  Open in Google Maps" }),
      el("a", { class: "chip", href: earth,
                target: "_blank", rel: "noopener noreferrer",
                text: "🌍  Google Earth" }),
      el("a", { class: "chip", href: osm,
                target: "_blank", rel: "noopener noreferrer",
                text: "OpenStreetMap" })
    ]);
    box.appendChild(links);

    box.appendChild(el("p", { class: "place-cite", text:
      "Coordinates from OpenBible.info's Bible Geocoding data, CC BY 4.0, "
      + "parts derived from OpenStreetMap under the ODbL. Many biblical sites "
      + "are identified only tentatively; the label above says how firm this "
      + "one is." }));

    return box;
  }

  var lastFocus = null;

  function showEntry(term, found) {
    closeSheet();
    lastFocus = document.activeElement;
    sheet = el("aside", {
      class: "lex", role: "dialog", "aria-modal": "false",
      "aria-label": "Definition of " + (found ? found.entry.name : term),
      tabindex: "-1"
    });

    var title = found
      ? (found.entry ? found.entry.name : found.place.name)
      : term;

    var head = el("div", { class: "lex-head" }, [
      el("h2", { text: title }),
      el("button", {
        class: "lex-close", "aria-label": "Close definition", text: "✕",
        onclick: closeSheet
      })
    ]);
    sheet.appendChild(head);

    var body = el("div", { class: "lex-body" });
    if (!found) {
      body.appendChild(el("p", { class: "lex-none", text:
        "No entry for “" + term + "” in Easton's Bible Dictionary. " +
        "It covers the Protestant canon closely and the deuterocanon, Enoch, " +
        "Jubilees and the Apostolic Fathers barely at all." }));
    } else {
      if (found.place) body.appendChild(placeBlock(found.place));

      if (found.entry) {
        body.appendChild(el("p", { class: "lex-text", text: found.entry.text }));
        (found.entry.flags || []).forEach(function (f) {
          body.appendChild(el("p", { class: "lex-flag " + f.kind, text: f.note }));
        });
        body.appendChild(el("p", { class: "lex-cite", text:
          "Easton's Bible Dictionary, 1897. Public domain by age, and written "
          + "before modern archaeology; read it as a Victorian reference, not "
          + "as current scholarship." }));
      }

      body.appendChild(el("a", {
        class: "chip", href: "#/search/" + encodeURIComponent(title.split(",")[0]),
        text: "Find every passage mentioning this",
        onclick: closeSheet
      }));
    }
    sheet.appendChild(body);
    document.body.appendChild(sheet);
    sheet.focus();
    announce(found
      ? found.entry.name + ". " + found.entry.text.slice(0, 160)
      : "No dictionary entry for " + term);
  }

  function initLexicon() {
    document.addEventListener("click", function (e) {
      if (e.target.closest(".lex")) return;
      var reader = e.target.closest(".reader");
      if (!reader) { closeSheet(); return; }
      if (e.target.closest("a")) return;          // let verse links work
      // The verse menu is rendered inside the verse it belongs to, so every
      // click on one of its buttons landed here as well and looked up
      // whatever word was under the cursor. On a screen reader that turned
      // "Saved" into "No dictionary entry for verse": the menu's own
      // announcement was overwritten by the answer to a question nobody had
      // asked. The number that opens the menu is the same case.
      if (e.target.closest(".vmenu, .vnum")) return;
      if (window.getSelection && String(window.getSelection())) return;

      var hit = wordAt(e.clientX, e.clientY);
      if (!hit) return;

      var candidates = phrasesAround(hit);
      var i = 0;
      (function next() {
        if (i >= candidates.length) { showEntry(hit.word, null); return; }
        var term = candidates[i++];
        lookup(term).then(function (found) {
          if (found) showEntry(term, found);
          else next();
        }).catch(function () { next(); });
      })();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { closeSheet(); closeMenu(); }
    });
  }

  /* A word you can only reach with a mouse is a word a keyboard or screen
     reader user cannot look up at all. Two routes in without one:
       d   define the current text selection
       ?   ask for a word by name
     Both are listed in the shortcuts panel so they are discoverable. */
  function initLookupKeys() {
    document.addEventListener("keydown", function (e) {
      if (e.target.matches("input, textarea, select")) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      if (e.key === "d") {
        var sel = String(window.getSelection() || "").trim();
        if (sel) { e.preventDefault(); lookupAndShow(sel); }
        else announce("Select a word first, then press d to define it.");
      }
      if (e.key === "?") {
        e.preventDefault();
        var term = window.prompt("Look up a word or name:");
        if (term) lookupAndShow(term.trim());
      }
    });
  }

  /* ================================================================
     SEARCH
     ================================================================ */

  /* ---------------- folding text into keys ------------------------------

     Search tokens, lexicon headwords and place names are all keys. They are
     built here, and built again by tools/textnorm.py when the data files are
     made. The two copies have to agree exactly, or the key a reader arrives
     at is not the key the entry was filed under -- and that failure is
     silent. The search answers that no text contains a word that is on the
     page; the definition of a word the volume does have an entry for does
     not open.

     They did part company, twice. Accented letters were being deleted rather
     than folded, so "Mastêmâ" went into the index as "mast" and "m" and
     "Cæsar" as "c" and "sar" -- 163 word-forms that no spelling could reach.
     And this file derived its lexicon key by deleting anything outside
     [a-z0-9 ] while the builder decomposed first, so the same word gave
     "mastm" here and "mastema" there.

     The region between the markers below is lifted out and run against the
     Python one by tests/python/test_tokeniser_agreement.py. Keep the two in
     step; the step order is part of the rule.
     ------------------------------------------------------------------- */
  /* --8<-- fold: start --8<-- */
  var TOKEN = /[a-z0-9]+/g;

  /* NFKD leaves these alone -- they are letters in their own right, not
     accented forms of anything -- so without expanding them by hand a reader
     typing "Caesar" never meets "Cæsar". */
  var LIGATURES = {
    "æ": "ae", "œ": "oe", "ß": "ss", "ð": "d", "þ": "th",
    "ø": "o", "đ": "d", "ł": "l", "ħ": "h", "ŋ": "ng"
  };
  var LIGATURE_RE = /[æœßðþøđłħŋ]/g;
  var CURLY_RE = /[‘’ʼʻ]/g;
  var COMBINING_RE = /[\u0300-\u036f]/g;

  function fold(s) {
    return String(s)
      .toLowerCase()
      .replace(CURLY_RE, "'")
      .replace(LIGATURE_RE, function (c) { return LIGATURES[c]; })
      .normalize("NFKD")
      .replace(COMBINING_RE, "");
  }

  /* The words the index files, and the words a query is looked up as. */
  function tokenise(s) {
    return (fold(s).match(TOKEN) || []);
  }

  /* The key a lexicon entry or a place is filed under. Unlike a search token
     this keeps the spaces, because the headwords are phrases, and drops the
     apostrophe rather than splitting on it, so "Rachel's tomb" and "Rachels
     tomb" are one entry. */
  function normTerm(s) {
    return fold(s).replace(/'/g, "")
            .replace(/[^a-z0-9 ]+/g, "").replace(/\s+/g, " ").trim();
  }
  /* --8<-- fold: end --8<-- */

  /* One word that is mostly grammar is not a question about the volume's
     arrangement, and answering it as though it were fills the page with
     boxes nobody asked for: "the" is the opening word of four collection
     titles and of half the threads. A phrase is different -- somebody who
     typed several words meant them -- so this only ever silences a query
     that is a single common word. */
  var STOP_ANSWERS = {
    the: 1, and: 1, but: 1, for: 1, not: 1, all: 1, any: 1, are: 1, was: 1,
    were: 1, that: 1, this: 1, with: 1, from: 1, into: 1, unto: 1, they: 1,
    them: 1, their: 1, you: 1, your: 1, his: 1, her: 1, him: 1, she: 1,
    who: 1, what: 1, when: 1, why: 1, how: 1, shall: 1, will: 1, have: 1,
    has: 1, had: 1, out: 1, one: 1, two: 1, said: 1, say: 1, saith: 1
  };

  /* Asked of the table itself and not of everything it inherits. A plain
     object answers to "constructor" with a function, so `TABLE[key]` is
     truthy for a word nobody put in the table -- which silenced a search
     for "constructor" here, and two tables down would have handed
     `(ALIASES[key] || []).forEach` a Function and thrown. Neither is a bug
     anybody would meet on purpose, and both are one call to avoid. */
  function own(table, key) {
    return Object.prototype.hasOwnProperty.call(table, key) ? table[key] : null;
  }

  function tooCommonToAnswer(key) {
    return key.indexOf(" ") === -1 && !!own(STOP_ANSWERS, key);
  }

  /* ---------------- a reference is not a word ----------------

     Typing "Psalm 23" used to return nothing at all, and "Job 38" nothing,
     and plain "Job" returned Joshua first -- Jobab king of Madon, because
     the term test is a prefix and "Job" prefixes "Jobab". Someone who does
     not already know where a passage sits cannot get to it by searching,
     which is precisely the reader this arrangement is hardest on: the order
     is by composition, so there is no shelf to run a finger along.

     A reference is a coordinate rather than a word, so it is answered
     separately and offered above the word matches rather than instead of
     them. Both questions are real -- "Job" is a book and also a man who is
     named in several others -- and only the reader knows which was meant.

     Two properties of this edition do most of the work. Isaiah is three
     works here and 1 Enoch is four, because they were written at different
     times, and a reader asking for Isaiah 40 should not have to know that.
     And every chapter keeps its printed number in its label, so the right
     work is the one that has a "Chapter 40" in it -- asked for, rather than
     computed from an offset that the splits would break anyway. */

  /* Forms a prefix of the title cannot reach. A convenience list rather
     than a claim about anything: the resolver works without it and simply
     answers fewer of the ways people write a reference. Everything that is
     already a prefix of a title word -- gen, ex, isa, ps, rev, prov, cor,
     tim, thess -- needs no entry and has none. */
  var REF_ALIASES = {
    mt: "matthew", mk: "mark", lk: "luke", jn: "john",
    dt: "deuteronomy", jas: "james", phlm: "philemon",
    song: "song", sos: "song"
  };

  function refWords(s) {
    return fold(s).replace(/[^a-z0-9 ]+/g, " ").split(/\s+/).filter(Boolean);
  }

  /* Does this work's title answer to the words the reader typed?

     Word by word and by prefix, so "1 cor" reaches "1 CORINTHIANS" and
     "isaiah" reaches all three Isaiahs -- which is wanted, because the
     chapter number decides between them a moment later. */
  function titleAnswersTo(title, want) {
    var have = refWords(title);
    return want.every(function (w, i) {
      var probe = REF_ALIASES[w] || w;
      // A leading numeral has to be the work's own numeral, or "1 John"
      // matches "2 John" and "3 John" as happily.
      if (/^\d+$/.test(probe)) return have.indexOf(probe) !== -1;
      return have.some(function (h) { return h.indexOf(probe) === 0; });
    });
  }

  /* Parse "Job 38", "Psalm 23:4", "1 Cor 13", "Isaiah 40", or a bare book
     name, and return every place in the volume it could mean. */
  function resolveReference(manifest, query) {
    var m = String(query).trim()
      .match(/^([0-9]?\s*[A-Za-z][A-Za-z'’.\- ]*?)\s*(?:(\d+)\s*(?:[:.]\s*(\d+))?)?$/);
    if (!m) return [];

    var want = refWords(m[1]);
    if (!want.length) return [];
    /* A title match is by prefix, so a single common word matches on the
       article: "the" answered with the Song of the Sea, both Enochs, Bel
       and the Dragon and two more, under a heading saying that could be any
       of these. It could not. The same guard the other answers use, and for
       the same reason -- a phrase is somebody being specific, one very
       common word is not. */
    if (tooCommonToAnswer(normTerm(m[1]))) return [];
    var chapter = m[2] ? parseInt(m[2], 10) : null;
    var verse = m[3] ? parseInt(m[3], 10) : null;

    var hits = [];
    manifest.sections.forEach(function (section) {
      section.works.forEach(function (work) {
        if (!work.chapters) return;              // an entry with no text
        if (!titleAnswersTo(work.title, want)) return;
        hits.push({ work: work, section: section, chapter: chapter, verse: verse });
      });
    });

    // A bare book name: offer each work it names, at its first chapter.
    if (chapter === null) {
      return hits.slice(0, 6).map(function (h) {
        return { workId: h.work.id, title: h.work.title, section: h.section,
                 idx: 0, label: null, verse: null, caution: h.work.caution };
      });
    }
    return hits;
  }

  /* The chapter labels live in the work file rather than the manifest, so
     which of the matched works actually carries "Chapter 40" is a question
     that needs the file. Asked for all of them at once, and only for the
     handful a name can match. */
  function locateReference(hits) {
    if (!hits.length || hits[0].label !== undefined) {
      return Promise.resolve(hits);            // bare book name, already done
    }
    return Promise.all(hits.slice(0, 6).map(function (h) {
      return getJSON("works/" + h.work.id + ".json").catch(function () { return null; });
    })).then(function (files) {
      var out = [];
      files.forEach(function (file, i) {
        if (!file || !file.chapters) return;
        var h = hits[i];
        file.chapters.forEach(function (c, idx) {
          // The printed number, taken off the label rather than the index,
          // which is what makes Isaiah 40 land in the second Isaiah.
          var n = c.n;
          if (n === null || n === undefined) {
            var got = String(c.label || "").match(/(\d+)/);
            n = got ? parseInt(got[1], 10) : null;
          }
          if (n !== h.chapter) return;
          out.push({ workId: h.work.id, title: h.work.title, section: h.section,
                     idx: idx, label: c.label, verse: h.verse,
                     caution: h.work.caution, name: h.name || null });
        });
      });
      return out;
    });
  }

  /* ---------------- a collection is not a word either ----------------

     Searching for "new testament" answered with two verses: a line in the
     Apostolic Canons listing which books a church receives, and one in the
     Testament of Our Lord. Both contain the words. Neither is what anybody
     typing them is looking for, and from that search there was no way at all
     into the twenty-seven books -- which are all here, and were reachable
     only by knowing one of their names first.

     The same hole swallowed "torah", "the gospels", "minor prophets",
     "deuterocanon", "epistles of paul", "apostolic fathers" and "shepherd of
     hermas". A search that indexes every word of the text and nothing about
     the text's own arrangement cannot answer a question about the
     arrangement, and readers ask those constantly: a collection is the unit
     people actually hold in their heads, and this edition -- which reorders
     the whole library by date of composition -- scatters every one of them.
     That is exactly the reader this arrangement is hardest on, and it is the
     same reader the reference resolver was written for.

     So collections are resolved the way references are, and offered above
     the word matches rather than instead of them. Like references they are
     read off data the volume already keeps rather than asserted here:

       - every section of this edition, which is its own chronological
         argument: SECTION IX, the Apostolic Fathers, Hermas, the Testaments
         of the Twelve Patriarchs;
       - every division named in canon.json, which is how the printed Bibles
         divide themselves: Torah, The Twelve, Gospels, Pauline epistles,
         Deuterocanon;
       - and the two nobody would think to look up by a division's name, the
         Old and New Testaments, which are those divisions added up and are
         nothing else.

     What is asserted here is the alias table: the words people type for
     these things. That is a convenience list rather than a claim, in exactly
     the sense REF_ALIASES is one. Everything works without it and simply
     answers fewer of the ways a reader phrases the question. */

  function slugify(s) {
    return String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  /* Which divisions add up to which testament. Named rather than computed:
     canon.json's divisions are a flat list and nothing in it says that the
     Gospels are in the New Testament and the Torah is not, because for the
     table that file draws the question never comes up. */
  var OT_DIVISIONS = ["Torah", "Former Prophets", "Latter Prophets",
                      "The Twelve", "Writings"];
  var NT_DIVISIONS = ["Gospels", "Acts", "Pauline epistles",
                      "General epistles", "Apocalypse"];

  /* The whole table, built once per page from the two files that already
     know the answers. Keyed by slug, and one flat namespace: a section slug
     and a division slug have never collided, and add() refuses the second
     comer if they ever do rather than quietly redefining the first. */
  function buildCollections(manifest, canon) {
    var table = {}, order = [];

    function add(id, title, note, works, kind) {
      if (!id || own(table, id) || !works || !works.length) return;
      table[id] = { id: id, title: title, note: note || "",
                    works: works, kind: kind };
      order.push(id);
    }

    /* The volume's own arrangement. Sections with no text under them -- the
       file map, the appendices, the front matter -- are headings rather than
       collections and are not offered as somewhere to go. */
    manifest.sections.forEach(function (s) {
      var ids = s.works.filter(function (w) { return !!w.chapters; })
                       .map(function (w) { return w.id; });
      var name = s.name || s.title || "";
      add(s.id, titleCase(name),
          s.roman ? "Section " + s.roman + (s.dates ? " · " + s.dates : "")
                  : (s.dates || ""),
          ids, "section");
    });

    if (!canon || !canon.books) return { table: table, order: order };

    /* How the printed Bibles divide themselves. A division's works are the
       works this volume prints for the books in it -- Isaiah's three among
       them, which is the whole reason this is read off canon.json rather
       than off a list of titles somebody typed. */
    var byDivision = {}, divisionOrder = [], bookCount = {};
    canon.books.forEach(function (b) {
      if (!b.works || !b.works.length) return;      // not in this volume
      if (!byDivision[b.division]) {
        byDivision[b.division] = [];
        divisionOrder.push(b.division);
        bookCount[b.division] = 0;
      }
      bookCount[b.division]++;
      b.works.forEach(function (w) {
        if (byDivision[b.division].indexOf(w) === -1) {
          byDivision[b.division].push(w);
        }
      });
    });

    /* A count that does not match the name is a count that has to explain
       itself. "The Twelve" lists thirteen works here and the Latter Prophets
       five, because this edition prints Isaiah in three parts and Zechariah
       in two, each under the date its part was written. That is the whole
       argument of the volume, and a reader meeting it for the first time on
       a page headed "The Twelve" deserves the sentence rather than the
       discrepancy. */
    function splitNote(books, works) {
      if (works <= books) return "As the canons divide themselves";
      return books + " books, printed here as " + works + ": this edition " +
             "sets the parts of a book that were written at different times " +
             "under their own dates.";
    }

    divisionOrder.forEach(function (d) {
      add(slugify(d), titleCase(d),
          splitNote(bookCount[d], byDivision[d].length),
          byDivision[d], "division");
    });

    function union(divisions) {
      var seen = {}, out = [];
      divisions.forEach(function (d) {
        (byDivision[d] || []).forEach(function (w) {
          if (!seen[w]) { seen[w] = 1; out.push(w); }
        });
      });
      return out;
    }
    function books(divisions) {
      var n = 0;
      divisions.forEach(function (d) { n += bookCount[d] || 0; });
      return n;
    }

    /* The Old Testament is the one collection here whose extent is a
       question rather than a fact, so the note says so instead of the title
       quietly picking a side: these are the books every Old Testament has,
       and three of the five canons add the deuterocanon to them. */
    var otWorks = union(OT_DIVISIONS), otBooks = books(OT_DIVISIONS);
    add("old-testament", "The Old Testament",
        "The Torah, the Prophets and the Writings — the " + otBooks +
        " books every Old Testament holds, printed here as " +
        otWorks.length + ". The Catholic, Orthodox and Ethiopian canons add " +
        "the deuterocanon to these.",
        otWorks, "testament");
    add("new-testament", "The New Testament",
        "The twenty-seven books every canon receives, in the order they " +
        "were written rather than the order they are bound.",
        union(NT_DIVISIONS), "testament");

    return { table: table, order: order };
  }

  /* The words people type. Each maps to one or more collection slugs, and
     more than one is not a failure to decide: "new testament" is genuinely
     both the twenty-seven books and this edition's section of writings from
     those years, which is a slightly different set, and only the reader
     knows which they meant. The reference resolver has said "that could be
     any of these" since Isaiah was split in three; this is the same
     sentence about a different kind of thing.

     Keys are normTerm()'d on the way in, so they are lowercase, unpunctuated
     and single-spaced here for the same reason the lexicon's headwords are. */
  var COLLECTION_ALIASES = {
    "new testament": ["new-testament", "section-ix-new-testament-writings"],
    "nt": ["new-testament"],
    "the new testament": ["new-testament", "section-ix-new-testament-writings"],
    "old testament": ["old-testament"],
    "ot": ["old-testament"],
    "the old testament": ["old-testament"],
    "hebrew bible": ["old-testament"],
    "hebrew scriptures": ["old-testament"],
    "torah": ["torah"],
    "pentateuch": ["torah"],
    "the pentateuch": ["torah"],
    "five books of moses": ["torah"],
    "books of moses": ["torah"],
    "law of moses": ["torah"],
    "the law": ["torah"],
    "gospels": ["gospels"],
    "the gospels": ["gospels"],
    "four gospels": ["gospels"],
    "the four gospels": ["gospels"],
    "prophets": ["latter-prophets", "the-twelve", "former-prophets"],
    "the prophets": ["latter-prophets", "the-twelve", "former-prophets"],
    "neviim": ["former-prophets", "latter-prophets", "the-twelve"],
    "major prophets": ["latter-prophets"],
    "minor prophets": ["the-twelve"],
    "twelve prophets": ["the-twelve"],
    "the twelve": ["the-twelve"],
    "writings": ["writings"],
    "ketuvim": ["writings"],
    "epistles": ["pauline-epistles", "general-epistles"],
    "the epistles": ["pauline-epistles", "general-epistles"],
    "letters": ["pauline-epistles", "general-epistles"],
    "pauline epistles": ["pauline-epistles"],
    "epistles of paul": ["pauline-epistles"],
    "letters of paul": ["pauline-epistles"],
    "pauls letters": ["pauline-epistles"],
    "pauls epistles": ["pauline-epistles"],
    "general epistles": ["general-epistles"],
    "catholic epistles": ["general-epistles"],
    "deuterocanon": ["deuterocanon"],
    "deuterocanonical": ["deuterocanon"],
    "deuterocanonical books": ["deuterocanon"],
    "apocrypha": ["deuterocanon", "new-testament-apocrypha"],
    "the apocrypha": ["deuterocanon", "new-testament-apocrypha"],
    "nt apocrypha": ["new-testament-apocrypha"],
    "new testament apocrypha": ["new-testament-apocrypha"],
    "apostolic fathers": ["the-apostolic-fathers"],
    "church fathers": ["the-apostolic-fathers"],
    "hermas": ["the-shepherd-of-hermas"],
    "shepherd of hermas": ["the-shepherd-of-hermas"],
    "the shepherd": ["the-shepherd-of-hermas"],
    "ignatius": ["the-epistles-of-ignatius-of-antioch"],
    "epistles of ignatius": ["the-epistles-of-ignatius-of-antioch"],
    "twelve patriarchs": ["the-testaments-of-the-twelve-patriarchs"],
    "testaments of the twelve patriarchs": ["the-testaments-of-the-twelve-patriarchs"],
    "apocalypse": ["apocalypse"],
    "acts": ["acts"]
  };

  /* Answer a query with collections, by three routes: the alias table, the
     slug itself -- so a URL that names one can be typed back in -- and a
     prefix match on the title, which is what reaches "eighth-century
     prophetic books" without an alias per era. */
  function resolveCollections(collections, query) {
    var key = normTerm(query);
    if (!key || !collections || tooCommonToAnswer(key)) return [];

    var out = [], seen = {};
    function take(id) {
      var c = own(collections.table, id);
      if (!c || own(seen, id)) return;
      seen[id] = 1;
      out.push(c);
    }

    (own(COLLECTION_ALIASES, key) || []).forEach(take);
    take(key);
    take(slugify(key));

    if (!out.length) {
      collections.order.forEach(function (id) {
        var c = collections.table[id];
        var title = normTerm(c.title);
        /* From the front, and ending where a word ends: "gospel" reaches
           "Gospels" -- the plural is one word grown, not a different one --
           and "gos" reaches nothing, because a prefix of a word is not a
           name anybody typed on purpose. */
        if (key.length < 4 || title.lastIndexOf(key, 0) !== 0) return;
        var after = title.charAt(key.length);
        if (after === "" || after === " " || after === "s") take(id);
      });
    }
    return out.slice(0, 4);
  }

  /* ---------------- everything else a reader might type ----------------

     The volume is not only its verses. It carries a dictionary of 3,900
     entries, a gazetteer with coordinates, eleven threads that run an
     argument across books, seven manuscript witnesses, and eight pages of
     its own about how any of it was decided. Every one of those was
     reachable only by already being on the page that holds it: the
     dictionary by tapping a word while reading, the witnesses by opening a
     work they attest, the threads from the front page or not at all.

     A reader who types "abaddon" wants the entry. One who types "codex
     sinaiticus" wants the witness. One who types "where do the dead go" has
     typed the exact title of a thread and got fourteen verses with "dead" in
     them. None of those queries is a word search, and all of them arrive
     through the search box, because a search box is where a reader puts a
     thing they are looking for. */

  /* The pages this site has, and the words that should reach them. Titles
     are the ones the pages carry; the extra words are the ones a reader
     types instead. */
  var SITE_PAGES = [
    { href: "#/contents", title: "Contents",
      note: "Every work in the volume, chronological or canonical",
      words: "contents index table of contents all books every book list of books browse" },
    { href: "#/canons", title: "Which books belong to whom",
      note: "The five canons side by side",
      words: "canon canons which books bible comparison catholic protestant orthodox ethiopian jewish tanakh deuterocanonical" },
    { href: "#/timeline", title: "The timeline",
      note: "Every work drawn on one axis",
      words: "timeline chronology dates when written order date" },
    { href: "#/threads", title: "Threads",
      note: "Questions the library argues with itself about",
      words: "threads topics themes questions subjects" },
    { href: "#/method", title: "How the dating was decided",
      note: "What the chronological order rests on",
      words: "method dating how dated scholarship why this order sources" },
    { href: "#/accuracy", title: "The accuracy report",
      note: "What the parse got wrong, and what was removed",
      words: "accuracy errors report findings removals splices corrections mistakes" },
    { href: "#/saved", title: "Saved",
      note: "Verses you have kept",
      words: "saved bookmarks kept favourites favorites my verses highlights" }
  ];

  function resolveSitePages(query) {
    var key = normTerm(query);
    if (!key || key.length < 3 || tooCommonToAnswer(key)) return [];
    return SITE_PAGES.filter(function (p) {
      if (key.length > 3 && normTerm(p.title).lastIndexOf(key, 0) === 0) return true;
      // Any whole word of the page's own vocabulary, from the front, so
      // "canon" reaches the canons page and "can" does not.
      return (" " + p.words + " ").indexOf(" " + key + " ") !== -1;
    }).slice(0, 3);
  }

  /* Threads, matched on the question they ask as well as on their title,
     because the title is a question and a reader types questions. */
  function resolveThreads(threads, query) {
    var key = normTerm(query);
    if (!key || key.length < 3 || !threads || tooCommonToAnswer(key)) return [];
    return threads.filter(function (t) {
      var hay = " " + normTerm((t.title || "") + " " + (t.question || "")) + " ";
      // Whole words, so "dead" reaches "Where do the dead go?" and does not
      // also reach every thread with "deadly" in its question.
      return hay.indexOf(" " + key + " ") !== -1;
    }).slice(0, 3);
  }

  /* Manuscript witnesses. The name a reader types is rarely the name the
     file carries -- "dead sea scrolls" is not the name of any of them, and
     is what two of them are -- so each is matched on its name, on where it
     was found, and on the words below. */
  var WITNESS_WORDS = {
    "1qisa": "dead sea scrolls qumran isaiah scroll great isaiah scroll",
    "1qphab": "dead sea scrolls qumran habakkuk commentary pesher",
    "sinaiticus": "codex sinaiticus uncial greek",
    "alexandrinus": "codex alexandrinus uncial greek",
    "vaticanus": "codex vaticanus uncial greek",
    "aleppo": "aleppo codex masoretic keter",
    "nash": "nash papyrus decalogue shema"
  };

  function resolveWitnesses(ms, query) {
    var key = normTerm(query);
    if (!key || key.length < 3 || !ms || !ms.witnesses ||
        tooCommonToAnswer(key)) return [];
    var out = [];
    Object.keys(ms.witnesses).forEach(function (id) {
      var w = ms.witnesses[id];
      /* The name and the find-spot answer a single word -- "sinaiticus",
         "aleppo", "qumran" are each one. The alias phrases only answer a
         phrase: "dead" is a word in "dead sea scrolls" and is not a
         question about a manuscript, while "dead sea scrolls" is nothing
         else. */
      var named = " " + normTerm(w.name + " " + (w.found || "")) + " ";
      var also = " " + normTerm(WITNESS_WORDS[id] || "") + " ";
      var hit = named.indexOf(" " + key + " ") !== -1 ||
                (key.indexOf(" ") !== -1 && also.indexOf(key) !== -1);
      if (!hit) return;
      // Somewhere to go: the first work this witness attests, whose page
      // carries the witness box that describes it.
      var where = null;
      Object.keys(ms.works || {}).some(function (wid) {
        if ((ms.works[wid] || []).indexOf(id) === -1) return false;
        where = wid;
        return true;
      });
      if (where) out.push({ id: id, witness: w, workId: where });
    });
    return out.slice(0, 3);
  }

  /* Passages known by a name the text itself never uses.

     "The sermon on the mount" appears nowhere in Matthew, "the beatitudes"
     nowhere at all, and "the lord's prayer" is a title the prayer does not
     carry. Every one of them is a thing a reader types, and every one of
     them found nothing, because the only names the search knew were the
     ones printed on the page.

     A convenience list, like REF_ALIASES, and a short one on purpose: each
     entry is a passage whose common English name is not seriously disputed
     and whose location here was checked against this volume's own parse.
     Anything argued over does not belong in a list that answers with the
     confidence of a coordinate. */
  var NAMED_PASSAGES = [
    { name: "The Sermon on the Mount", work: "matthew", ch: 5, to: 7 },
    { name: "The Beatitudes", work: "matthew", ch: 5, v: 3 },
    { name: "The Lord's Prayer", work: "matthew", ch: 6, v: 9 },
    { name: "The Ten Commandments", work: "exodus", ch: 20 },
    { name: "The Shema", work: "deuteronomy", ch: 6, v: 4 },
    { name: "The Golden Rule", work: "matthew", ch: 7, v: 12 },
    { name: "The Prodigal Son", work: "luke", ch: 15, v: 11 },
    { name: "The Good Samaritan", work: "luke", ch: 10, v: 25 },
    { name: "The Creation", work: "genesis", ch: 1 },
    { name: "The Garden of Eden", work: "genesis", ch: 2 },
    { name: "The Flood", work: "genesis", ch: 6 },
    { name: "The Tower of Babel", work: "genesis", ch: 11 },
    { name: "The Binding of Isaac", work: "genesis", ch: 22 },
    { name: "The Burning Bush", work: "exodus", ch: 3 },
    { name: "The Parting of the Sea", work: "exodus", ch: 14 },
    { name: "The Valley of Dry Bones", work: "ezekiel", ch: 37 },
    { name: "The Suffering Servant", work: "isaiah-40-55-second-isaiah", ch: 53 },
    { name: "The Love Chapter", work: "1-corinthians", ch: 13 },
    { name: "The Armour of God", work: "ephesians", ch: 6, v: 10 },
    { name: "The Faith Chapter", work: "hebrews", ch: 11 },
    { name: "The Magnificat", work: "luke", ch: 1, v: 46 },
    { name: "The Nativity", work: "luke", ch: 2 },
    { name: "The Last Supper", work: "luke", ch: 22, v: 14 },
    { name: "The Road to Emmaus", work: "luke", ch: 24, v: 13 },
    { name: "Pentecost", work: "acts", ch: 2 },
    { name: "The Fruit of the Spirit", work: "galatians", ch: 5, v: 22 },
    { name: "The Four Horsemen", work: "revelation", ch: 6 },
    { name: "The New Jerusalem", work: "revelation", ch: 21 }
  ];

  /* The passage names are answered by the same machinery a reference is:
     the chapter number is printed on the chapter's own label, so which work
     file carries "Chapter 53" is a question asked of the file rather than
     computed from an offset the Isaiah split would break. */
  function resolveNamedPassages(manifest, query) {
    var key = normTerm(query);
    if (!key || key.length < 3 || tooCommonToAnswer(key)) return [];
    var works = {};
    manifest.sections.forEach(function (s) {
      s.works.forEach(function (w) { works[w.id] = { work: w, section: s }; });
    });
    return NAMED_PASSAGES.filter(function (p) {
      var name = normTerm(p.name);
      // The name, with or without its "the" -- and a part of the name only
      // when the reader typed more than one word. "God" is a word in "the
      // armour of God" and is not a request for Ephesians 6.
      if (name === key || name.replace(/^the /, "") === key) return true;
      return key.indexOf(" ") !== -1 &&
             (" " + name + " ").indexOf(" " + key + " ") !== -1;
    }).map(function (p) {
      var m = works[p.work];
      if (!m) return null;
      return { name: p.name, work: m.work, section: m.section,
               chapter: p.ch, verse: p.v || null, to: p.to || null };
    }).filter(Boolean).slice(0, 4);
  }

  function viewSearch(manifest, initialQuery, initialScope) {
    var wrap = el("div", { class: "wrap" });
    wrap.appendChild(el("h1", { text: "Search" }));
    wrap.appendChild(el("p", {
      class: "lede",
      text: "Every word of every text, including the deuterocanon, 1 Enoch, " +
            "Jubilees and the Apostolic Fathers — or only one book, only the " +
            "books one tradition receives, or only the ones left out of every " +
            "canon. Wrap a phrase in quotes to " +
            "match it exactly, or type a reference — Psalm 23, Job 38:4 — to " +
            "go straight to it."
    }));

    var input = el("input", {
      type: "search", placeholder: 'Psalm 23, "a still small voice", or: watchers heaven',
      value: initialQuery || "", autocomplete: "off", spellcheck: "false"
    });

    /* Searching less than the whole library.

       The whole library is 1.22 million words and the results are capped at
       three hundred, so a common word answers with three hundred verses from
       everywhere and the one you wanted is somewhere inside them. Narrowing
       to a book is the difference between a concordance and a search: it is
       also the only way to ask "where does Job say this", which is a
       question about a book rather than about the collection.

       One book was the only narrowing on offer, and it is the wrong size for
       the commonest way of reading here. A reader who keeps one canon is not
       asking about Job; they are asking about their Bible, and this edition
       prints five of them interleaved with books that belong to none. Asking
       that question one entry at a time is forty-two searches for the Tanakh
       and sixty-nine for the Protestant canon -- the works this select
       lists, Isaiah's three among them -- so the canons are scopes as well:
       the same five the Canons page compares, each holding exactly the books
       that page marks as theirs.

       And the sixth entry, which is the question asked the other way round.
       Reading every book is how somebody finds out what their Bible leaves
       out, and the answer was there to be read off the results a work at a
       time, if you already knew which titles those were. It is a scope
       instead: everything no canon holds. */
    var scopeSel = el("select", { "aria-label": "Which books to search" });
    scopeSel.appendChild(el("option", { value: "", text: "Every book" }));
    /* Grouped by era, because a flat list of a hundred and sixty-three is a
       list you scroll rather than one you read -- and because the grouping
       is the volume's own argument: the order here is the order of
       composition, so the heading a book sits under says when it was
       written. */
    manifest.sections.forEach(function (section) {
      var withText = section.works.filter(function (w) { return !!w.chapters; });
      if (!withText.length) return;
      var label = section.name || section.title || "";
      if (section.roman) label = section.roman + ". " + label;
      var group = el("optgroup", { label: titleCase(label) });
      withText.forEach(function (work) {
        group.appendChild(el("option", {
          value: work.id, text: titleCase(work.title)
        }));
      });
      scopeSel.appendChild(group);
    });

    /* A canon is a scope too, and it is told apart from a book by this
       prefix -- in the select and in the URL segment, which are the same
       string. No work id contains a colon: slugify() in tools/parse_book.py
       makes them out of [a-z0-9] and hyphens and can make nothing else. */
    var CANON_SCOPE = "canon:";
    /* And a collection is a scope by the same trick, under its own prefix.
       "Where do the Gospels say this" is the commonest narrowing there is
       and no canon can express it: a canon is every book a tradition
       receives, and the four Gospels are a division inside one. */
    var GROUP_SCOPE = "in:";
    var canonWorks = null;               // canon key -> { workId: 1 }
    var excerptWorks = {};               // chapters printed twice; see below
    var collections = null;              // slug -> { title, works: [ids] }

    function isCanonScope(s) {
      return String(s).lastIndexOf(CANON_SCOPE, 0) === 0;
    }
    function isGroupScope(s) {
      return String(s).lastIndexOf(GROUP_SCOPE, 0) === 0;
    }
    /* The two behave alike everywhere below -- neither is a work id, both
       arrive before canon.json does, both name a set rather than a book --
       so where the difference does not matter they are asked about together. */
    function isSetScope(s) {
      return isCanonScope(s) || isGroupScope(s);
    }

    /* Whose Bible the results are measured against.

       The mark on a result says a work is outside a canon, and until now the
       canon was all five at once: outside every one of them. That is the only
       thing the data can say about a reader it knows nothing about, and it is
       not what most readers are asking. Somebody who keeps the Protestant
       canon is not helped by 1 Enoch going unmarked because the Ethiopian
       church receives it -- for them that is exactly a book their Bible does
       not have.

       So they can say which one is theirs, and it is remembered, because a
       question about your own Bible has the same answer tomorrow. Empty is
       the honest default for a reader who has not said: mark what no canon
       holds. */
    var markCanon = store.get("mark-canon", "");

    /* The scope, held here rather than read off the select, because for a
       moment it is something the select cannot yet say: a link narrowed to a
       canon arrives before the file naming that canon's books does. */
    var scope = initialScope || "";
    scopeSel.value = scope;
    /* An id in the URL that names nothing this select offers -- a stale
       link, a mistyped slug -- is dropped rather than kept as a scope no
       verse can ever be in. A canon and a collection are the two things not
       offered yet, so they are kept until canon.json has had its chance
       below. */
    if (!scopeSel.value && !isSetScope(scope)) scope = "";

    /* Which works each tradition receives, from the file the Canons page
       draws -- so the two can never disagree about what is Catholic -- and
       asked for after the page is up, so a reader who never opens this
       select does not wait on it. */
    var canonReady = getJSON("canon.json").then(function (canon) {
      canonWorks = {};
      canon.canons.forEach(function (c) { canonWorks[c] = {}; });
      var held = {};
      canon.books.forEach(function (b) {
        Object.keys(b.canons).forEach(function (c) {
          if (!canonWorks[c]) return;
          // Present in that canon's column at all -- received, printed as an
          // appendix, or received in some branches -- which is the same rule
          // the Canons page filters by, and the same one a reader means by
          // "the books in my Bible".
          b.works.forEach(function (w) { canonWorks[c][w] = 1; held[w] = 1; });
        });
      });

      /* And the other side of the same question, which is the one somebody
         reading every book is usually asking: which of these did no canon
         take? Everything the volume prints, less everything any canon holds.

         Less one more thing. Five works here are a chapter of a canonical
         book printed a second time beside the excavated object or the early
         poem it belongs with -- the Decalogue, the Shema, the priestly
         blessing, the Song of the Sea, the Song of Deborah. No canon lists
         them because the whole book is elsewhere in the volume and that is
         where they are counted, so by subtraction alone they would arrive
         here as books left out of every Bible, which is the opposite of true
         and the exact error this scope exists to prevent. canon.json names
         them; tools/build_canon.py refuses to build if a sixth appears
         without being classed. */
      excerptWorks = canon.excerpts || {};
      canonWorks[CANON_NONE] = {};
      manifest.sections.forEach(function (section) {
        section.works.forEach(function (w) {
          if (!w.chapters || held[w.id] || excerptWorks[w.id]) return;
          canonWorks[CANON_NONE][w.id] = 1;
        });
      });

      var group = el("optgroup", { label: "By canon" });
      canon.canons.forEach(function (c) {
        group.appendChild(el("option", {
          value: CANON_SCOPE + c,
          text: "The " + (CANON_IN_FULL[c] || c) + " canon"
        }));
      });
      // Last, because it is what the five leave over.
      group.appendChild(el("option", {
        value: CANON_SCOPE + CANON_NONE,
        text: "The books left out of every canon"
      }));
      // Under every book and above the books themselves: the list runs from
      // the widest scope to the narrowest.
      scopeSel.insertBefore(group, scopeSel.children[1] || null);

      /* And the collections, between the canons and the single books,
         because that is where they sit by size. Only the divisions and the
         two testaments are offered here: this edition's own sections are
         already the optgroup headings further down the list, so listing
         them again as scopes would print every era's name twice. */
      collections = buildCollections(manifest, canon);
      var groups = el("optgroup", { label: "By collection" });
      collections.order.forEach(function (id) {
        var c = collections.table[id];
        if (c.kind === "section") return;
        groups.appendChild(el("option", {
          value: GROUP_SCOPE + id, text: c.title
        }));
      });
      if (groups.children.length) {
        scopeSel.insertBefore(groups, group.nextSibling);
      }

      /* And the sentence that says what the marking means, which is a
         sentence rather than a labelled control because the rule is short
         enough to read: "Mark verses not in the Protestant canon". */
      markSel.appendChild(el("option", { value: "", text: "any canon" }));
      canon.canons.forEach(function (c) {
        markSel.appendChild(el("option", {
          value: c, text: "the " + (CANON_IN_FULL[c] || c) + " canon"
        }));
      });
      // A key from an older build, or from another tab's future one, is not
      // a canon this file knows: fall back rather than measure against a set
      // that does not exist.
      markSel.value = markCanon;
      if (!markSel.value) markCanon = "";
      markRow.hidden = false;

      if (isSetScope(scope)) {
        scopeSel.value = scope;              // now that the option exists
        if (!scopeSel.value) scope = "";     // a key nothing here knows
      }
    }).catch(function () {
      /* No list, no canon entries. An option that would quietly search the
         whole library under a tradition's name is worse than not offering
         the tradition at all. The collections built off the same file go
         with it, for the same reason: "the Gospels" over results from
         outside them is the same lie in a smaller hat. */
      canonWorks = {};
      collections = null;
    });

    /* What the scope means, and what the results have to say for themselves
       under it. Both come out of canon.json, so both are answered together
       and after it has landed.

       keep: a test on a work id. A book is itself, a canon is every work it
       receives, null is no narrowing -- including when the canon list failed
       to arrive, which run() notices and stops claiming a scope for.

       mark: whether a work is outside the canon the reader measures by. With
       no canon of their own that is all five at once, and the answer is the
       set built above. With one, it is that canon's own books, and every
       work it does not receive is outside it -- Enoch and Jubilees included,
       which is the whole reason for asking.

       Either way the five chapters printed twice are never marked. They are
       Deuteronomy and Numbers and Exodus, in every canon there is, and no
       canon's book list names the second printing because the whole book is
       elsewhere in the volume. A mark on the Decalogue would be this feature
       telling a reader the Ten Commandments are not in their Bible. */
    function scopeReady(want) {
      return canonReady.then(function () {
        var keep = null;
        if (want && !isSetScope(want)) {
          keep = function (w) { return w === want; };
        } else if (isCanonScope(want)) {
          var set = canonWorks && canonWorks[want.slice(CANON_SCOPE.length)];
          if (set) keep = function (w) { return !!set[w]; };
        } else if (isGroupScope(want)) {
          var c = collections &&
                  own(collections.table, want.slice(GROUP_SCOPE.length));
          if (c) {
            var member = {};
            c.works.forEach(function (w) { member[w] = 1; });
            keep = function (w) { return !!member[w]; };
          }
        }
        var mine = canonWorks && canonWorks[markCanon || CANON_NONE];
        return {
          keep: keep,
          mark: function (w) {
            if (!mine || excerptWorks[w]) return false;
            return markCanon ? !mine[w] : !!mine[w];
          }
        };
      });
    }

    /* What the mark says: the same canon the control names, said about one
       verse instead of about the search. */
    function markLabel() {
      return markCanon
        ? "outside the " + (CANON_IN_FULL[markCanon] || markCanon) + " canon"
        : "outside every canon";
    }

    /* How a scope is named back to the reader: a book by its title, a canon
       by the tradition's name. Read from the data rather than from the
       select, which is a moment behind it. */
    function scopeTitle(want) {
      if (isCanonScope(want)) {
        var key = want.slice(CANON_SCOPE.length);
        if (key === CANON_NONE) return CANON_NONE_TITLE;
        return "the " + (CANON_IN_FULL[key] || key) + " canon";
      }
      if (isGroupScope(want)) {
        var c = collections &&
                own(collections.table, want.slice(GROUP_SCOPE.length));
        return c ? c.title : want.slice(GROUP_SCOPE.length);
      }
      var title = want;
      manifest.sections.forEach(function (s) {
        s.works.forEach(function (w) {
          if (w.id === want) title = titleCase(w.title);
        });
      });
      return title;
    }

    /* Nothing found, said as a fact about what was searched. A reader who
       narrowed to Psalms has not learnt that the word is absent from the
       volume, and must not be told that it is. */
    function nothingMatched(want) {
      if (!want) return "No verse matched.";
      return "No verse in " +
             (isSetScope(want) ? scopeTitle(want) : "that book") + " matched.";
    }

    wrap.appendChild(el("div", { class: "toolbar search-bar" }, [input, scopeSel]));

    /* Hidden until canon.json fills it: a select with nothing in it is a
       control that cannot answer the question it asks. */
    var markSel = el("select", { "aria-label": "Mark verses not in this canon" });
    markSel.addEventListener("change", function () {
      markCanon = markSel.value;
      store.set("mark-canon", markCanon);
      go();
    });
    var markRow = el("p", { class: "marking", hidden: true },
                     ["Mark verses not in ", markSel]);
    wrap.appendChild(markRow);

    var chips = el("div", { class: "chips" });
    ["\"living creatures\"", "watchers", "\"son of man\"", "jubilee", "resurrection", "wisdom"]
      .forEach(function (q) {
        chips.appendChild(el("a", {
          class: "chip", href: "#/search/" + encodeURIComponent(q), text: q.replace(/"/g, "")
        }));
      });
    wrap.appendChild(chips);

    var jump = el("div", { class: "jump" });
    var status = el("div", { class: "muted" });
    var bar = el("div", { class: "progress" }, [el("i")]);
    var results = el("div", { class: "results" });
    wrap.appendChild(jump);
    wrap.appendChild(status);
    wrap.appendChild(bar);
    wrap.appendChild(results);

    var runId = 0;

    function run(query, scope) {
      var mine = ++runId;
      /* Remembered here rather than in the input handler, because a search
         reached by its URL -- a shared link, a bookmark, the back button --
         never touches the input handler and is just as much a search. */
      rememberSearch(query);
      results.innerHTML = "";
      jump.innerHTML = "";
      bar.firstChild.style.width = "0%";

      /* Everything above the word matches, and never instead of them. "Job"
         is a book and also a man named in several others; "Enoch" is three
         works, a person with a dictionary entry, and a word in ninety
         verses. Only the reader knows which was meant, so all of it is
         offered and none of it is chosen for them.

         The answers arrive from files that land in whatever order the
         network gives them, so the boxes are made now, in the order they
         should read, and filled as each resolves. Appending on arrival
         would shuffle the page under a reader already looking at it. */
      var slots = {};
      ["reference", "passage", "collection", "thread", "entry",
       "witness", "page"].forEach(function (k) {
        slots[k] = el("div");
        jump.appendChild(slots[k]);
      });

      /* Each box says which question it is answering, in a class as well as
         in its heading: a page can carry five of them at once, and "the
         first jump link" stops meaning anything the moment it can be a
         dictionary entry as easily as a reference. */
      function answerBox(slot, head, rows) {
        if (mine !== runId || !rows.length) return;
        var box = el("div", { class: "jump-box is-" + slot });
        box.appendChild(el("p", { class: "jump-head", text: head }));
        rows.forEach(function (r) { box.appendChild(r); });
        slots[slot].appendChild(box);
      }

      /* A reference is a coordinate: the oldest of these answers and still
         the first, because somebody who typed one has told you exactly what
         they want. */
      locateReference(resolveReference(manifest, query)).then(function (places) {
        if (mine !== runId || !places.length) return;
        var box = el("div", { class: "jump-box is-reference" });
        box.appendChild(el("p", { class: "jump-head", text: places.length === 1
          ? "That is a place in the volume:" : "That could be any of these:" }));
        places.slice(0, 6).forEach(function (r) {
          var where = titleCase(r.title) + (r.label ? " · " + r.label : "");
          box.appendChild(el("a", {
            class: "jump-link",
            href: "#/read/" + r.workId + "/" + r.idx + (r.verse ? "/v" + r.verse : "")
          }, [
            el("span", { class: "jump-where", text: where +
              (r.verse ? ":" + r.verse : "") }),
            el("span", { class: "jump-era", text: r.section.name || r.section.title || "" })
          ]));
          /* One work here is printed under a title that names a different and
             much more famous text, so "gospel of thomas" resolved to a single
             confident answer -- the Infancy Gospel -- under a heading saying
             that is a place in the volume, with nothing correcting it. The
             correction travels with the work: see tools/build_cautions.py. */
          if (r.caution) {
            box.appendChild(el("p", { class: "jump-caution", text: r.caution }));
          }
        });
        slots.reference.appendChild(box);
      });

      /* A passage by the name it is known under rather than by its
         coordinate, which is how almost everybody holds one. */
      locateReference(resolveNamedPassages(manifest, query)).then(function (found) {
        answerBox("passage", found.length === 1
          ? "That passage is here:" : "Those passages are here:",
          found.slice(0, 4).map(function (r) {
            return el("a", {
              class: "jump-link",
              href: "#/read/" + r.workId + "/" + r.idx +
                    (r.verse ? "/v" + r.verse : "")
            }, [
              el("span", { class: "jump-where", text: r.name }),
              el("span", { class: "jump-era", text: titleCase(r.title) +
                (r.label ? " · " + r.label : "") })
            ]);
          }));
      });

      /* A collection: the answer to "new testament", which is the query
         this whole layer was built for. Waits on canon.json, because half
         of these are read off it. */
      canonReady.then(function () {
        var found = resolveCollections(collections, query);
        answerBox("collection", found.length === 1
          ? "That is a collection in the volume:"
          : "Those are collections in the volume:",
          found.map(function (c) {
            return el("a", { class: "jump-link", href: "#/collection/" + c.id }, [
              el("span", { class: "jump-where", text: c.title }),
              el("span", { class: "jump-era", text: c.works.length +
                (c.works.length === 1 ? " work" : " works") })
            ]);
          }));
      }).catch(function () {});

      /* A thread. "Where do the dead go" is the exact title of one and
         answered with fourteen verses containing the word "dead". */
      getJSON("threads.json").then(function (threads) {
        answerBox("thread", "The library argues about that:",
          resolveThreads(threads, query).map(function (t) {
            return el("a", { class: "jump-link", href: "#/thread/" + t.id }, [
              el("span", { class: "jump-where", text: t.title }),
              el("span", { class: "jump-era", text: (t.stops || []).length +
                " passages" })
            ]);
          }));
      }).catch(function () {});

      /* The dictionary and the gazetteer, which between them know who
         Abaddon was and where Bethlehem is, and could be asked only by
         tapping the word on a page you had already found. */
      lookup(query).then(function (found) {
        if (!found) return;
        var name = found.entry ? found.entry.name
                 : (found.place ? found.place.name : query);
        var what = found.entry && found.place ? "A person, and a place"
                 : (found.place ? "A place" : "In the dictionary");
        var row = el("a", {
          class: "jump-link", href: "#/search/" + encodeURIComponent(query),
          onclick: function (e) {
            // Not a navigation: the definition is a sheet over this page,
            // and the href is there so the row is a real link for a
            // keyboard and a screen reader.
            e.preventDefault();
            showEntry(name, found);
          }
        }, [
          el("span", { class: "jump-where", text: name }),
          el("span", { class: "jump-era", text: what })
        ]);
        answerBox("entry", "There is an entry for that:", [row]);
      }).catch(function () {});

      /* The manuscripts. "Dead sea scrolls" is not the name of any of them
         and is what two of them are. */
      getJSON("manuscripts.json").then(function (ms) {
        answerBox("witness", "A manuscript witness:",
          resolveWitnesses(ms, query).map(function (w) {
            return el("a", {
              class: "jump-link", href: "#/read/" + w.workId + "/0"
            }, [
              el("span", { class: "jump-where", text: w.witness.name }),
              el("span", { class: "jump-era", text: w.witness.date || "" })
            ]);
          }));
      }).catch(function () {});

      /* And the site's own pages, which a reader looks for in the search
         box because that is where you look for things. */
      answerBox("page", "A page here:",
        resolveSitePages(query).map(function (p) {
          return el("a", { class: "jump-link", href: p.href }, [
            el("span", { class: "jump-where", text: p.title }),
            el("span", { class: "jump-era", text: p.note })
          ]);
        }));

      var phrase = null;
      var m = query.match(/^\s*"(.+)"\s*$/);
      // Folded, because the verses it will be compared against are folded:
      // a phrase typed as "Caesar's household" has to meet "Cæsar's" on the
      // page, and the index has already filed that chapter under "caesar".
      if (m) phrase = fold(m[1]).replace(/\s+/g, " ").trim();

      var terms = tokenise(phrase || query);
      if (!terms.length) { status.textContent = ""; return; }

      status.textContent = "Looking up terms…";

      var index = getJSON("chapters.json").then(function (tbl) {
        var shards = {};
        terms.forEach(function (t) {
          var k = /^[a-z]/.test(t) ? t[0] : "0";
          shards[k] = true;
        });
        return Promise.all(Object.keys(shards).map(function (k) {
          return getJSON("index/" + k + ".json").catch(function () { return {}; });
        })).then(function (loaded) {
          var lookup = {};
          Object.keys(shards).forEach(function (k, i) { lookup[k] = loaded[i]; });
          return { tbl: tbl, lookup: lookup };
        });
      });

      Promise.all([scopeReady(scope), index]).then(function (both) {
        if (mine !== runId) return;
        var keep = both[0].keep, mark = both[0].mark, ctx = both[1];
        /* The canon list never arrived, so the scope cannot be honoured.
           Searching everything and saying so is better than printing a
           tradition's name over results from outside it. */
        if (isSetScope(scope) && !keep) scope = "";
        var tbl = ctx.tbl, lookup = ctx.lookup;

        // Narrow to candidate chapters using the selective terms only.
        //
        // The narrowing has to use the same rule the verse test below uses,
        // and that rule is a prefix: "jubilee" is meant to find "jubilees",
        // and does, once the chapter is being read. The index files whole
        // words, so asking it for the exact token and then prefix-matching
        // inside whatever came back returns only the verses that happen to
        // sit beside the exact spelling. Searching for "caesar" found 44 of
        // the 59 verses that mention him: the other 15 say "Caesarea", which
        // is a token of its own and so never made it into the candidates.
        //
        // Every token in the shard that starts with the term contributes its
        // chapters instead. The largest shard holds about two thousand
        // tokens, so this is a scan of a few thousand strings once per term.
        var candidate = null;
        var unknown = [];
        terms.forEach(function (t) {
          var k = /^[a-z]/.test(t) ? t[0] : "0";
          var table = lookup[k];
          if (!table) { unknown.push(t); return; }

          var set = null, matched = false, common = false;
          for (var token in table) {
            if (token.lastIndexOf(t, 0) !== 0) continue;      // startsWith
            matched = true;
            if (table[token] === 0) { common = true; break; } // no narrowing
            if (set === null) set = {};
            var post = table[token];
            for (var i = 0; i < post.length; i++) set[post[i]] = 1;
          }

          if (!matched) { unknown.push(t); return; }
          if (common || set === null) return;   // too common to narrow with

          if (candidate === null) candidate = set;
          else {
            var next = {};
            Object.keys(candidate).forEach(function (c) { if (set[c]) next[c] = 1; });
            candidate = next;
          }
        });

        if (unknown.length) {
          status.textContent = "No text contains " +
            unknown.map(function (u) { return '"' + u + '"'; }).join(" or ") + ".";
          bar.firstChild.style.width = "100%";
          return;
        }

        var ids = candidate === null
          ? tbl.chapters.map(function (_, i) { return i; })
          : Object.keys(candidate).map(Number);

        if (!ids.length) {
          status.textContent = "No chapter contains all of those words.";
          bar.firstChild.style.width = "100%";
          return;
        }

        // Group candidate chapters by work so each work is fetched once.
        var byWork = {};
        ids.forEach(function (cid) {
          var row = tbl.chapters[cid];
          (byWork[row[0]] = byWork[row[0]] || []).push([cid, row[1]]);
        });

        var workIds = Object.keys(byWork);
        if (keep) workIds = workIds.filter(keep);
        if (!workIds.length) {
          bar.firstChild.style.width = "100%";
          status.textContent = nothingMatched(scope);
          return;
        }
        /* Counted over the works about to be read rather than over every
           candidate the index returned. The index knows nothing about the
           scope, so under one its count is the size of a search nobody
           asked for: "shepherd" in the Jewish canon said it was scanning
           124 chapters when 53 of them were in a book it would open. */
        var scanning = 0;
        workIds.forEach(function (w) { scanning += byWork[w].length; });
        status.textContent = "Scanning " + fmt(scanning) + " chapters in " +
                             fmt(workIds.length) +
                             (workIds.length === 1 ? " work…" : " works…");

        /* The mark earns its place only where it divides the results. Under
           every book it does. Inside one book, inside the reader's own
           canon, or under the books left out, it would land on all of the
           rows or on none of them -- which is the scope's own sentence,
           printed again on every line. Asked of the works this run will
           actually read rather than of the scope, because that is the same
           question with fewer special cases: a canon scope wider than the
           reader's own canon does divide, and does get marked. */
        var flags = {}, flagged = 0;
        workIds.forEach(function (w) { if (mark(w)) { flags[w] = 1; flagged++; } });
        if (!flagged || flagged === workIds.length) flags = {};

        var found = 0, done = 0, LIMIT = 300;
        var order = {};
        manifest.sections.forEach(function (s, si) {
          s.works.forEach(function (w, wi) { order[w.id] = si * 1000 + wi; });
        });
        workIds.sort(function (a, b) { return (order[a] || 0) - (order[b] || 0); });

        function step(i) {
          if (mine !== runId) return;
          if (i >= workIds.length || found >= LIMIT) {
            bar.firstChild.style.width = "100%";
            var where = scope ? " in " + scopeTitle(scope) : "";
            status.textContent = found
              ? fmt(found) + (found >= LIMIT ? "+ matches (showing the first " + LIMIT + ")" : " matches") + where
              : nothingMatched(scope);
            return;
          }
          var wid = workIds[i];
          // One question per work rather than per verse: which canon holds a
          // book is a fact about the book.
          var uncanonical = !!flags[wid];
          getJSON("works/" + wid + ".json").then(function (work) {
            if (mine !== runId) return;
            byWork[wid].forEach(function (pair) {
              if (found >= LIMIT) return;
              var chapter = work.chapters[pair[1]];
              if (!chapter) return;
              var units = chapter.verses
                ? chapter.verses.map(function (v) { return { ref: v.v, t: v.t }; })
                : (chapter.paras || []).map(function (t, k) { return { ref: null, t: t, k: k }; });

              units.forEach(function (u) {
                if (found >= LIMIT) return;
                // The same fold the index was built with. Comparing the
                // raw text here would undo it: the index narrows to the
                // chapter that has "Cæsar" in it and this test then throws
                // every one of those verses away, so the search reports no
                // match for a word it just located.
                var low = fold(u.t).replace(/\s+/g, " ");
                var ok = phrase
                  ? low.indexOf(phrase) !== -1
                  : terms.every(function (t) { return new RegExp("\\b" + t, "i").test(low); });
                if (!ok) return;
                found++;
                results.appendChild(resultRow(tbl, pair[0], wid, pair[1], u,
                                             phrase, terms, uncanonical));
              });
            });
            done++;
            bar.firstChild.style.width = Math.round(done / workIds.length * 100) + "%";
            step(i + 1);
          }).catch(function () { step(i + 1); });
        }
        step(0);
      });
    }

    function resultRow(tbl, cid, wid, chIdx, unit, phrase, terms, uncanonical) {
      var row = tbl.chapters[cid];
      var href = "#/read/" + wid + "/" + chIdx + (unit.ref ? "/v" + unit.ref : "");
      var label = titleCase(row[3]) + " · " + row[2] + (unit.ref ? ":" + unit.ref : "");

      /* Cut the verse down before it is marked up, never after.

         This used to escape, mark, and then slice 420 characters off the
         finished HTML, which counts "&amp;" as five characters and "<mark>"
         as six and will cut through the middle of either. Nothing in the
         library is currently long enough to make it happen, so this is
         hardening rather than a repair -- but the window is a fact about the
         verse, not about its markup, and taken on the verse it also stops
         cutting words in half at both edges and stops promising a "..." when
         the window has in fact reached the end of the verse. */
      var quote = function (t) { return t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); };
      var finder = phrase
        ? new RegExp(quote(phrase), "i")
        : (terms.length ? new RegExp("\\b" + quote(terms[0]) + "\\w*", "i") : null);

      var text = unit.t;
      var WINDOW = 420;
      if (text.length > WINDOW) {
        var at = finder ? text.search(finder) : -1;
        var from = at > 160 ? at - 160 : 0;
        // Never leave a word cut in half at either edge.
        if (from) {
          var space = text.indexOf(" ", from);
          from = space === -1 ? from : space + 1;
        }
        var to = from + WINDOW;
        if (to < text.length) {
          var back = text.lastIndexOf(" ", to);
          to = back > from ? back : to;
        }
        text = (from ? "… " : "") + text.slice(from, to) +
               (to < unit.t.length ? " …" : "");
      }

      var html = esc(text);
      if (phrase) {
        html = html.replace(new RegExp("(" + quote(esc(phrase)) + ")", "gi"),
                            "<mark>$1</mark>");
      } else {
        terms.forEach(function (t) {
          html = html.replace(new RegExp("(\\b" + quote(esc(t)) + "\\w*)", "gi"),
                              "<mark>$1</mark>");
        });
      }

      var ref = el("div", { class: "result-ref" }, [
        el("a", { href: href, text: label })
      ]);
      /* Which of these is in my Bible is the question somebody searching the
         whole library is usually holding in their head, and until now it was
         answered by recognising the title -- which works for Psalms and not
         for Barnabas, and so works least well for the reader who most needs
         it. The mark is on the verses outside the canon being measured by,
         and on nothing else: a page where every row carries a badge says
         nothing at all. */
      if (uncanonical) {
        ref.appendChild(el("span", { class: "result-outside", text: markLabel() }));
      }

      return el("div", { class: "result" }, [
        ref,
        el("div", { class: "result-text", html: html })
      ]);
    }

    /* The scope is in the URL beside the query -- a work id, or "canon:" and
       a canon's key -- so a narrowed search can be kept, shared and come
       back to, which is most of what it is for. */
    function go() {
      var q = input.value;
      /* A scope with no query keeps its place with an empty segment, so
         that narrowing to the Gospels and then typing a word does not
         silently lose the narrowing on the way through the URL. */
      var target = "#/search";
      if (q.trim() || scope) target += "/" + encodeURIComponent(q.trim() ? q : "");
      if (scope) target += "/" + scope;
      if (location.hash !== target) history.replaceState(null, "", target);
      run(q, scope);
    }

    var timer;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(go, 220);
    });
    scopeSel.addEventListener("change", function () {
      scope = scopeSel.value;
      clearTimeout(timer);
      go();
    });

    setTimeout(function () { input.focus(); }, 30);
    if (initialQuery) run(initialQuery, scope);

    return wrap;
  }

  /* ================================================================
     CANONS
     ================================================================ */

  var CANON_LABEL = {
    tanakh: "Jewish", protestant: "Protestant", catholic: "Catholic",
    orthodox: "E. Orthodox", ethiopian: "Ethiopian"
  };

  /* The same five, unabbreviated. The labels above head a table whose
     columns have to fit a phone; these are read in sentences -- the search
     scope, and what the search says it searched -- where "E. Orthodox" is
     an abbreviation nobody asked for. */
  var CANON_IN_FULL = {
    tanakh: "Jewish", protestant: "Protestant", catholic: "Catholic",
    orthodox: "Eastern Orthodox", ethiopian: "Ethiopian"
  };

  /* The sixth entry in the search's list of canons, which is not a canon: the
     works this volume prints that none of the five receive -- the Apostolic
     Fathers, the New Testament apocrypha, the Testaments of the Twelve
     Patriarchs, Hermas, Ignatius. Keyed like a canon so that one prefix, one
     set of work ids and one URL segment carry both, and named "none" because
     canon.json's own keys are the five traditions and cannot collide with
     it. */
  var CANON_NONE = "none";
  var CANON_NONE_TITLE = "the books left out of every canon";

  function viewCanons(manifest, canon) {
    var wrap = el("div", { class: "wrap-wide" });
    wrap.appendChild(el("h1", { text: "Which books belong to whom" }));
    wrap.appendChild(el("p", {
      class: "lede",
      text: "There has never been one Bible. Five traditions draw the boundary in " +
            "five places, and the disagreements are older than any of the printed " +
            "editions. Every book below that this volume carries is linked to its text."
    }));

    var cards = el("div", { class: "stats" });
    canon.canons.forEach(function (c) {
      var cov = canon.coverage[c];
      cards.appendChild(el("div", { class: "stat" }, [
        el("b", { text: cov.traditionalCount ? String(cov.traditionalCount) : "varies",
                  style: cov.traditionalCount ? null : "font-size:1.15rem;color:var(--ink-soft)" }),
        el("span", { text: CANON_LABEL[c] + " · " + cov.presentInVolume + " of " +
                           cov.units + " units here" })
      ]));
    });
    wrap.appendChild(cards);

    var notes = el("div", { class: "callout" });
    canon.canons.forEach(function (c) {
      notes.appendChild(el("p", { html: "<strong>" + CANON_LABEL[c] + ".</strong> " +
                                        esc(canon.coverage[c].caveat) }));
    });
    wrap.appendChild(notes);

    var filter = "all";
    var tableBox = el("div");

    var chips = el("div", { class: "chips" });
    [["all", "All books"]].concat(canon.canons.map(function (c) {
      return [c, "In the " + CANON_LABEL[c] + " canon"];
    })).forEach(function (p) {
      chips.appendChild(el("button", {
        class: "chip", "aria-pressed": filter === p[0] ? "true" : "false", text: p[1],
        onclick: function () {
          filter = p[0];
          Array.prototype.forEach.call(chips.children, function (b) {
            b.setAttribute("aria-pressed", b.textContent === p[1] ? "true" : "false");
          });
          render();
        }
      }));
    });
    wrap.appendChild(chips);
    wrap.appendChild(tableBox);

    var byId = {};
    manifest.sections.forEach(function (s) {
      s.works.forEach(function (w) { byId[w.id] = { w: w, s: s }; });
    });

    function cell(status) {
      if (status === "canon") return el("td", { class: "yes", text: "●", title: "Received as scripture" });
      if (status === "appendix") return el("td", { class: "part", text: "◐", title: "Printed, outside the canon" });
      if (status === "varies") return el("td", { class: "part", text: "◐", title: "In some branches only" });
      return el("td", { class: "no", text: "·" });
    }

    function render() {
      tableBox.innerHTML = "";
      var table = el("table", { class: "grid" });
      table.appendChild(el("thead", {}, [el("tr", {}, [
        el("th", { text: "Book" })
      ].concat(canon.canons.map(function (c) {
        return el("th", { text: CANON_LABEL[c] });
      })).concat([
        el("th", { text: "Era here" }), el("th", { text: "Text" })
      ]))]));

      var tb = el("tbody");
      canon.books.forEach(function (b) {
        if (filter !== "all" && !b.canons[filter]) return;
        var eras = b.works.map(function (id) {
          return byId[id] ? (byId[id].s.roman || "＋") : null;
        }).filter(Boolean);

        var link = el("td");
        if (!b.present) {
          link.appendChild(el("span", { class: "muted", text: "not here" }));
        } else if (b.partialWhy) {
          b.works.forEach(function (id, i) {
            if (i) link.appendChild(document.createTextNode(" · "));
            link.appendChild(el("a", { href: "#/read/" + id + "/0", text: i === 0 && b.works.length === 1 ? "read the part here" : String(i + 1) }));
          });
        } else {
          b.works.forEach(function (id, i) {
            if (i) link.appendChild(document.createTextNode(" · "));
            link.appendChild(el("a", { href: "#/read/" + id + "/0", text: i === 0 && b.works.length === 1 ? "read" : String(i + 1) }));
          });
        }

        // Why a book is missing, or which part of it is here, has been in
        // canon.json since it was first written down and has never been on
        // the page. A table that says "not here" and nothing else is the
        // kind of unsourced editorial claim this volume refuses everywhere
        // else, and one that says "read" over half a book is worse.
        var why = b.present ? b.partialWhy : b.absentWhy;
        var whySource = b.present ? b.partialSource : b.absentSource;

        tb.appendChild(el("tr", {}, [
          el("td", {}, [
            el("strong", { text: b.name }),
            b.foldedInto ? el("div", { class: "tiny", text: "counted inside " + b.foldedInto }) : null,
            why ? el("details", { class: "tiny why" }, [
              el("summary", { text: b.present ? "here in part — what is and is not" : "why it is not here" }),
              el("p", { text: why }),
              whySource ? el("p", { class: "muted", text: whySource }) : null
            ]) : null
          ])
        ].concat(canon.canons.map(function (c) {
          return cell(b.canons[c]);
        })).concat([
          el("td", { class: "muted", text: eras.length ? eras.join(", ") : "—" }),
          link
        ])));
      });
      table.appendChild(tb);
      tableBox.appendChild(scroller(table, "Canon comparison, scrollable sideways"));
      tableBox.appendChild(el("p", { class: "tiny", text:
        "● received as scripture   ◐ printed but outside the canon, or received in some branches only   · absent" }));
    }

    render();
    return wrap;
  }

  /* ================================================================
     ACCURACY
     ================================================================ */

  /* ================================================================
     A COLLECTION
     ------------------------------------------------------------------
     Somewhere for a collection answer to go. The Contents page lists all
     163 works and marks each with the era it belongs to, which answers
     "where does Amos sit" and cannot answer "what is in the New Testament"
     -- for that you read the whole table and keep score.

     This is that table with one question already asked. It is also the only
     page in the volume where the deuterocanon, or the Twelve, or the
     Pauline epistles exist as a thing rather than as a property of
     scattered rows.
     ================================================================ */

  function viewCollection(manifest, canon, id) {
    var wrap = el("div", { class: "wrap" });
    var built = buildCollections(manifest, canon);
    var c = own(built.table, id);

    if (!c) {
      wrap.appendChild(el("h1", { text: "No such collection" }));
      wrap.appendChild(el("p", { class: "lede", text:
        "Nothing here is filed under “" + id + "”. The contents list every " +
        "work in the volume, and the canons page lists the collections." }));
      wrap.appendChild(el("div", { class: "chips" }, [
        el("a", { class: "chip", href: "#/contents", text: "Contents" }),
        el("a", { class: "chip", href: "#/canons", text: "Which books belong to whom" }),
        el("a", { class: "chip", href: "#/search", text: "Search" })
      ]));
      return wrap;
    }

    wrap.appendChild(el("h1", { text: c.title }));
    if (c.note) wrap.appendChild(el("p", { class: "lede", text: c.note }));

    var byId = {};
    manifest.sections.forEach(function (s) {
      s.works.forEach(function (w) { byId[w.id] = { w: w, s: s }; });
    });

    /* What the collection costs to read, which is the question anybody
       standing in front of one is actually asking. */
    var chapters = 0, words = 0;
    c.works.forEach(function (id) {
      var m = byId[id];
      if (!m) return;
      chapters += m.w.chapters || 0;
      words += m.w.words || 0;
    });
    wrap.appendChild(el("p", { class: "muted", text:
      fmt(c.works.length) + (c.works.length === 1 ? " work · " : " works · ") +
      fmt(chapters) + " chapters · " + fmt(words) + " words" }));

    wrap.appendChild(el("div", { class: "chips" }, [
      el("a", { class: "chip primary",
                href: "#/search//in:" + c.id,
                text: "Search only these" }),
      el("a", { class: "chip", href: "#/contents", text: "Everything in the volume" }),
      el("a", { class: "chip", href: "#/canons", text: "Which books belong to whom" })
    ]));

    /* In the volume's order, not the collection's. A reader who has come
       here from "the gospels" is being shown, without being told, that Mark
       was written first: that is this edition's whole argument and the one
       thing a page like this must not quietly undo by printing Matthew at
       the top because a printed Bible does. */
    var order = {};
    manifest.sections.forEach(function (s, si) {
      s.works.forEach(function (w, wi) { order[w.id] = si * 1000 + wi; });
    });
    var works = c.works.filter(function (id) { return !!byId[id]; })
                       .sort(function (a, b) { return order[a] - order[b]; });

    var table = el("table", { class: "grid" });
    table.appendChild(el("thead", {}, [el("tr", {}, [
      el("th", { text: "Work" }),
      el("th", { text: "Written" }),
      el("th", { class: "num", text: "Chapters" }),
      el("th", { class: "num", text: "Words" })
    ])]));
    var tb = el("tbody");
    var byOwn = 0;
    works.forEach(function (id) {
      var m = byId[id];
      /* The work's own critical position where it has one, and the era's
         range only where it does not. Four Gospels all reading
         "c. 50-110 CE" is the section talking; Mark at c. 65-75 and Matthew
         at c. 80-90 is why Mark is the row above, and is the argument this
         page exists to show. Same field, same formatter and same fallback
         as the timeline -- and marked the same way, fainter and named in a
         title, because placing a book by the era it is filed under is a
         looser claim than placing it by its own record and the page should
         not print the two in the same voice. */
      var own = m.w.positions && m.w.positions.span && m.w.positions.span.crit;
      var when;
      if (own) {
        when = el("td", { class: "muted", text: spanText(own) });
        byOwn++;
      } else {
        when = el("td", { class: "muted is-era", title: PLACED.section,
                          text: m.s.dates || "—" });
      }
      tb.appendChild(el("tr", {}, [
        el("td", {}, [el("a", { href: "#/read/" + id + "/0",
                                text: titleCase(m.w.title) })]),
        when,
        el("td", { class: "num", text: m.w.chapters || "—" }),
        el("td", { class: "num", text: m.w.words ? fmt(m.w.words) : "—" })
      ]));
    });
    table.appendChild(tb);
    wrap.appendChild(scroller(table, c.title + ", scrollable sideways"));

    /* Counted rather than left to be noticed, which is what the timeline
       does with the same two kinds of date and for the same reason. */
    if (works.length) {
      /* Three sentences rather than one with holes in it. "4 of these 4 ...
         the rest carry the era" describes a remainder that is not there, and
         "0 of these 27" opens on a number that says nothing. Hermas is the
         second case for all twenty-seven of its parts, and the Gospels the
         first for all four. */
      var cited = "each with its citation on the work itself";
      var looser = ", which is a looser claim";
      var said;
      if (!byOwn) {
        said = "None of these " + fmt(works.length) + " has a dated position " +
               "of its own. Each carries the era it is filed under" +
               looser + ". ";
      } else if (byOwn === works.length) {
        said = (works.length === 1 ? "This one is" : "All " +
                fmt(works.length) + " are") +
               " dated by the work's own position record, " + cited + ". ";
      } else {
        said = "<strong>" + fmt(byOwn) + "</strong> of these " +
               fmt(works.length) + " are dated by the work's own position " +
               "record, " + cited + ". The rest carry the era they are " +
               "filed under" + looser + ". ";
      }
      wrap.appendChild(el("p", { class: "muted dating-note", html: said +
        "<a href=\"#/method\">How the dating was decided</a>." }));
    }

    return wrap;
  }

  function viewAccuracy(findings, removals, splices) {
    var wrap = el("div", { class: "wrap" });
    wrap.appendChild(el("h1", { text: "Accuracy report" }));
    wrap.appendChild(el("p", { class: "lede", text: findings.summary }));
    wrap.appendChild(el("p", { class: "muted", text:
      "Every chapter and verse count below was checked against independent " +
      "reference figures rather than against the source file's own claims. " +
      "Where the source and the reference disagreed, the disagreement is listed." }));

    findings.groups.forEach(function (g) {
      wrap.appendChild(el("hr", { class: "rule" }));
      wrap.appendChild(el("div", { class: "group-head" }, [el("h2", { text: g.title })]));
      wrap.appendChild(el("p", { class: "muted", text: g.blurb }));
      g.items.forEach(function (it) {
        wrap.appendChild(el("div", { class: "finding" }, [
          el("h3", {}, [
            el("span", { class: "badge " + it.status, text: it.status }),
            document.createTextNode(it.claim)
          ]),
          el("p", { text: it.detail })
        ]));
      });
    });

    wrap.appendChild(el("hr", { class: "rule" }));
    wrap.appendChild(el("h2", { text: "Removal log" }));
    wrap.appendChild(el("p", { class: "muted", text:
      "Material deleted from the text as it was published, itemised. Nothing " +
      "was removed without being recorded here." }));

    var table = el("table", { class: "grid" });
    table.appendChild(el("thead", {}, [el("tr", {}, [
      el("th", { text: "Where" }), el("th", { text: "What" }),
      el("th", { text: "Chars" }), el("th", { text: "Opening words" })
    ])]));
    var tb = el("tbody");
    removals.forEach(function (r) {
      tb.appendChild(el("tr", {}, [
        el("td", { text: titleCase(r.where) }),
        el("td", { class: "muted", text: r.reason }),
        el("td", { text: fmt(r.chars) }),
        el("td", { class: "tiny", text: r.excerpt.slice(0, 90) + "…" })
      ]));
    });
    table.appendChild(tb);
    wrap.appendChild(scroller(table, "Findings, scrollable sideways"));

    if (splices && splices.length) {
      wrap.appendChild(el("hr", { class: "rule" }));
      wrap.appendChild(el("h2", { text: "Chapter boundaries repaired" }));
      wrap.appendChild(el("p", { class: "muted", text:
        "The Ante-Nicene Fathers print a heading above each chapter. Preparing " +
        "the source turned those headings into chapter markers, except where " +
        "the scan had misread the full stop as a comma — “CHAP, IV.—” rather " +
        "than “CHAP. IV.—”. Those headings stayed in the running text, the " +
        "chapters they opened were folded into the chapter before, and the " +
        "heading itself was read out as though it were scripture. The " +
        "boundaries below are put back by the parser, and the heading dropped, " +
        "as it is in every other chapter of these works." }));

      var stable = el("table", { class: "grid" });
      stable.appendChild(el("thead", {}, [el("tr", {}, [
        el("th", { text: "As printed" }), el("th", { text: "Chapter restored" }),
        el("th", { text: "Heading removed" })
      ])]));
      var sb = el("tbody");
      splices.forEach(function (sp) {
        sb.appendChild(el("tr", {}, [
          el("td", { class: "tiny", text: "CHAP. " + sp.numeral + ".—" }),
          el("td", { text: String(sp.chapter) }),
          el("td", { class: "muted", text: sp.heading })
        ]));
      });
      stable.appendChild(sb);
      wrap.appendChild(scroller(stable, "Table, scrollable sideways"));
    }

    wrap.appendChild(el("hr", { class: "rule" }));
    wrap.appendChild(el("h2", { text: "How the order was decided" }));
    wrap.appendChild(el("p", { html:
      "This page is about the text. The arrangement is a separate set of " +
      "decisions, and they are written down too: " +
      "<a href=\"#/method\">how the dating was decided</a> — what the two " +
      "columns on every work are, where each date comes from, how the bars " +
      "on a date card are derived, and the two things they cannot tell you." }));

    wrap.appendChild(el("hr", { class: "rule" }));
    wrap.appendChild(el("h2", { text: "How to check this yourself" }));
    wrap.appendChild(el("p", { html:
      "The parser, the audit and the index builder are in <code>tools/</code> " +
      "in the repository, and the original text is in <code>source/</code>. " +
      "Running <code>python3 tools/audit.py</code> reproduces every count on " +
      "this page. Findings are stated so they can be falsified: if a count here " +
      "is wrong, the script will say so." }));

    return wrap;
  }

  /* ================================================================
     THREADS -- one question, traced across the collection
     ================================================================ */

  /* ================================================================
     TIMELINE -- the whole library on one axis, under either dating
     ------------------------------------------------------------------
     The home page is the arrangement as a reader walks it: era by era, in
     order. This is the same library seen side-on, every work a bar on a
     shared scale, and it exists to make two things visible that a list
     cannot.

     The first is how much of the library is a guess about a range rather
     than a date. A bar that runs three centuries is not a book we know less
     about than its neighbour; it is a book whose position says three
     centuries, and reading that as a point is the mistake this view is meant
     to stop.

     The second is what happens when you switch the dating. Under the
     traditional column the Torah moves eight hundred years and lands on top
     of everything else. That is the disagreement this volume is about, and
     it is worth being able to see rather than read.
     ================================================================ */

  /* Where a bar comes from, in the reader's terms. A work with a position
     record of its own is placed by it; the rest are placed by the era they
     are filed under, which is a looser claim and is drawn as one. */
  var PLACED = {
    own: "from this work's own dated position",
    section: "from the era it is filed under, no dated position of its own"
  };

  function timelineRows(manifest, mode) {
    var rows = [];
    manifest.sections.forEach(function (s) {
      s.works.forEach(function (w) {
        var own = w.positions && w.positions.span && w.positions.span[mode];
        var sp = own || s.span || null;
        rows.push({
          id: w.id, title: w.title, section: s, span: sp,
          placed: own ? "own" : (s.span ? "section" : null),
          /* What this work's own critical position says is not one date:
             "Composite" for the Torah books, "perhaps two letters joined"
             for Polycarp, "chapters 24-27" for the Isaiah apocalypse sitting
             inside the eighth-century oracles. A solid bar across a book like
             that is a lie of resolution -- it draws the confidence of a single
             range over an object the volume itself says is layered. The phrase
             is a quotation from the position record rather than a new claim,
             so the citation under the work covers it: see tools/positions.py
             and tests/python/test_composite.py, which holds every one of them
             to being a verbatim piece of the sentence it comes from. */
          composite: (w.positions && w.positions.composite) || null,
          words: w.words
        });
      });
    });
    return rows;
  }

  function viewTimeline(manifest) {
    var wrap = el("div", { class: "wrap-wide" });
    wrap.appendChild(el("h1", { text: "The library on one axis" }));
    wrap.appendChild(el("p", { class: "lede", text:
      "Every work in the volume, drawn against time. A bar is a range, not a " +
      "date: its length is how much the position it comes from actually " +
      "commits to." }));

    var mode = store.get("timeline-mode", "crit");
    var body = el("div");

    var seg = el("div", { class: "seg" });
    [["crit", "Critical dating"], ["trad", "Traditional dating"]].forEach(function (p) {
      seg.appendChild(el("button", {
        "aria-pressed": mode === p[0] ? "true" : "false",
        text: p[1],
        onclick: function () {
          mode = p[0];
          store.set("timeline-mode", mode);
          Array.prototype.forEach.call(seg.children, function (b) {
            b.setAttribute("aria-pressed",
                           b.textContent === p[1] ? "true" : "false");
          });
          announce(p[1] + ": the order is redrawn");
          render();
        }
      }));
    });
    wrap.appendChild(el("div", { class: "toolbar" }, [seg]));
    wrap.appendChild(body);

    function render() {
      body.innerHTML = "";
      var rows = timelineRows(manifest, mode);
      var dated = rows.filter(function (r) { return r.span; });
      var undated = rows.filter(function (r) { return !r.span; });

      if (!dated.length) {
        body.appendChild(el("p", { class: "empty", text:
          "No work in the volume carries a date under this column." }));
        return;
      }

      /* Sorted by where the bar starts, so switching the column really does
         reorder the library rather than recolouring it. */
      dated.sort(function (a, b) {
        return a.span.frm - b.span.frm || a.span.to - b.span.to;
      });

      var lo = Math.min.apply(null, dated.map(function (r) { return r.span.frm; }));
      var hi = Math.max.apply(null, dated.map(function (r) { return r.span.to; }));
      var pad = Math.round((hi - lo) * 0.03) || 25;
      lo -= pad; hi += pad;
      var at = function (y) { return ((y - lo) / (hi - lo)) * 100; };

      /* A ruler the eye can hold: round centuries, thinned so the labels
         never collide on a phone. */
      var axis = el("div", { class: "tl-axis" });
      var step = (hi - lo) > 1600 ? 400 : (hi - lo) > 700 ? 200 : 100;
      var first = Math.ceil(lo / step) * step;
      for (var y = first; y <= hi; y += step) {
        /* There is no year zero: the tick that lands there is the boundary
           between the eras, not a date, and saying "0 CE" would be wrong. */
        var tick = el("span", { class: "tl-tick",
                                text: y === 0 ? "BCE | CE" : yearText(y) });
        tick.style.left = at(y) + "%";
        axis.appendChild(tick);
      }
      body.appendChild(axis);

      var list = el("div", { class: "tl-rows" });
      dated.forEach(function (r) {
        var row = el("a", {
          class: "tl-row placed-" + r.placed,
          href: "#/read/" + r.id + "/0"
        });
        row.appendChild(el("span", { class: "tl-name", text: titleCase(r.title) }));

        var track = el("span", { class: "tl-track" });
        var bar = el("span", {
          class: "tl-bar " + r.span.kind + (r.span.open ? " open-" + r.span.open : "") +
                 (r.composite ? " composite" : "")
        });
        var left = r.span.open === "before" ? 0 : at(r.span.frm);
        var right = r.span.open === "after" ? 100 : at(r.span.to);
        bar.style.left = left + "%";
        bar.style.width = Math.max(0.8, right - left) + "%";
        track.appendChild(bar);
        row.appendChild(track);

        row.appendChild(el("span", { class: "tl-when",
          text: spanText(r.span) + (r.composite ? " · not one date" : "") }));
        row.title = titleCase(r.title) + " — " + spanText(r.span) + "\n" +
                    PLACED[r.placed] +
                    (r.composite
                      ? "\nNot one date: the position for this work says " +
                        r.composite + "."
                      : "");
        list.appendChild(row);
      });
      body.appendChild(list);

      var byOwn = dated.filter(function (r) { return r.placed === "own"; }).length;
      body.appendChild(el("p", { class: "tl-note", html:
        "<strong>" + fmt(byOwn) + "</strong> of these " + fmt(dated.length) +
        " are placed by the work's own dated position, each with its citation " +
        "on the work itself. The rest are placed by the era they are filed " +
        "under, which is a looser claim, and are drawn fainter. " +
        "<a href=\"#/method\">How the dating was decided</a>." }));

      /* A composite book drawn as one solid bar is the most confident thing
         on this page and the least true. The volume does not split Genesis
         into its sources or Isaiah 1-39 into its apocalypse, and says so on
         the method page -- but the drawing said nothing, so the reader saw
         the same shape for Amos, whose bar is ten years, and for the Psalms,
         which the same records call a collection spanning centuries. These
         are hatched instead, and counted here rather than left to be noticed. */
      var layered = dated.filter(function (r) { return r.composite; });
      if (layered.length) {
        var note = el("details", { class: "tl-layered" });
        note.appendChild(el("summary", { text:
          fmt(layered.length) + " of these bars are not one date" }));
        note.appendChild(el("p", { class: "muted", text:
          "A bar is drawn from one position, and some of these books are not " +
          "one composition. Where a work's own critical position says so, the " +
          "bar is hatched rather than solid and the phrase is quoted below. " +
          "This volume keeps such books whole rather than splitting them, so " +
          "the hatching is the only warning the drawing can give." }));
        var list = el("ul", { class: "tl-layered-list" });
        layered.forEach(function (r) {
          list.appendChild(el("li", {}, [
            el("a", { href: "#/read/" + r.id + "/0", text: titleCase(r.title) }),
            el("span", { class: "muted", text: " — " + r.composite })
          ]));
        });
        note.appendChild(list);
        body.appendChild(note);
      }

      if (undated.length) {
        body.appendChild(el("details", { class: "tl-undated" }, [
          el("summary", { text: fmt(undated.length) +
            " works carry no date under this column" }),
          el("p", { class: "muted", text:
            "Nothing here is a gap in the data. Under the traditional column " +
            "many positions name a person rather than a time, and the later " +
            "collections — the Testaments, the Apostolic Fathers, the " +
            "Shepherd — are filed after the numbered eras and have no era " +
            "range to fall back on." }),
          el("div", { class: "tl-undated-list" }, undated.map(function (r) {
            return el("a", { class: "chip", href: "#/read/" + r.id + "/0",
                             text: titleCase(r.title) });
          }))
        ]));
      }
    }

    render();
    return wrap;
  }

  /* ================================================================
     METHOD -- how the order was decided, stated so it can be argued with
     ================================================================ */

  function viewMethod(manifest) {
    var wrap = el("div", { class: "wrap" });
    wrap.appendChild(el("h1", { text: "How the dating was decided" }));
    wrap.appendChild(el("p", { class: "lede", text:
      "This volume puts the texts in the order they were written. That order " +
      "is a series of decisions, and a reader who cannot see the decisions " +
      "has been handed a verdict. Here they are." }));

    function part(title, paras) {
      wrap.appendChild(el("hr", { class: "rule" }));
      wrap.appendChild(el("h2", { text: title }));
      paras.forEach(function (p) {
        wrap.appendChild(el("p", typeof p === "string" ? { text: p } : p));
      });
    }

    part("What the arrangement is, and is not", [
      "The arrangement follows the critical dating: the date a book reached " +
      "something like its present form, as argued from its language, the " +
      "events it knows about, and its relation to the books around it.",
      { html: "<strong>That is a decision about order, not a verdict about " +
        "truth.</strong> Every work carries the traditional position beside " +
        "the critical one, in the same size type, each with its citation. " +
        "Where they disagree the volume shows the disagreement rather than " +
        "resolving it. The order had to be <em>some</em> order; this one is " +
        "the one that makes the development of an idea visible, which is the " +
        "one thing this arrangement can do that a canonical Bible cannot." },
      "Nothing here is a claim to have settled a question scholars have not."
    ]);

    part("Where each date comes from", [
      "Neither column is quoted from a single authority, because no single " +
      "authority covers this range of texts. Each is a summary of the " +
      "majority position as it stands, written for this volume and " +
      "referenced so it can be checked: the traditional column cites the " +
      "text or the received attribution it rests on, and the critical column " +
      "cites the argument or the scholar the position is associated with.",
      { html: "A position with no citation is a build failure, not a warning. " +
        "<code>tools/audit.py</code> refuses to finish if any of the seven " +
        "fields on any of the " + fmt(52) + " position records is empty. " +
        "That rule exists because an editorial claim sitting beside verse " +
        "counts that were audited against independent references borrows " +
        "their authority without having earned it." }
    ]);

    part("How the bars are drawn", [
      "The positions are prose. The bars on each work's date card are read " +
      "out of that prose by a parser, and are arithmetic on what the position " +
      "already says — nothing is added.",
      { html: "Four forms are recognised. <strong>A year or a span of " +
        "years</strong> is taken as written. <strong>A century</strong> is " +
        "taken as its hundred years, so the 8th century BCE is 800–701 BCE. " +
        "<strong>A decade</strong> likewise. <strong>A named period</strong> " +
        "is the one case where boundaries are imposed that the position did " +
        "not state, so each is fixed by the event that fixes it, and a bar " +
        "drawn from one is hatched to mark it as the looser kind." },
      { html: "<strong>Where a position names a person rather than a time, " +
        "there is no bar and the card says so.</strong> “Samuel”, “Moses, " +
        "shortly before his death” — these are not dates, and drawing a " +
        "plausible-looking bar for them would be inventing evidence. About " +
        "two in five traditional positions have no bar for this reason. That " +
        "is a fact about the tradition, not a gap in the data." }
    ]);

    var table = el("table", { class: "grid" });
    table.appendChild(el("thead", {}, [el("tr", {}, [
      el("th", { text: "Period" }), el("th", { text: "Taken as" }),
      el("th", { text: "Fixed by" })
    ])]));
    var tb = el("tbody");
    (PERIOD_TABLE).forEach(function (row) {
      tb.appendChild(el("tr", {}, [
        el("td", { text: titleCase(row[0]) }), el("td", { text: row[1] }),
        el("td", { class: "muted", text: row[2] })
      ]));
    });
    table.appendChild(tb);
    wrap.appendChild(scroller(table, "Sources, scrollable sideways"));
    wrap.appendChild(el("p", { class: "muted", text:
      "Where a boundary is itself argued, the span is drawn wide rather than " +
      "picking a side." }));

    part("The two things the bars cannot tell you", [
      { html: "<strong>A composite book has one bar and several dates.</strong> " +
        "Genesis is not a book written between 500 and 400 BCE; it is a book " +
        "assembled then out of material centuries older. The bar shows when " +
        "the critical position puts the form we have, and the prose beside " +
        "it says the rest. Any single date for a composite work is a " +
        "simplification, and this one is no exception." },
      { html: "<strong>Overlapping bars are not agreement.</strong> They mean " +
        "the two positions admit a common date. Amos is dated the same way " +
        "by both columns and they still differ about whether the last five " +
        "verses are his." }
    ]);

    part("Seeing it", [
      { html: "<a href=\"#/timeline\">The library on one axis</a> draws every " +
        "work as a bar, under either column. Switching the column reorders " +
        "the whole library: under the traditional dating the Torah moves " +
        "eight hundred years and lands on top of everything else. A bar " +
        "placed by a work's own dated position is drawn solid; one placed by " +
        "the era it is filed under is drawn fainter, because it is a looser " +
        "claim." }
    ]);

    part("Arguing with it", [
      { html: "The source text is in <code>source/</code>, the positions in " +
        "<code>tools/positions.py</code>, the parser that reads the spans in " +
        "<code>tools/dates.py</code>, and the audit in " +
        "<code>tools/audit.py</code>. Every figure on this site can be " +
        "reproduced by running <code>./tools/build.sh</code>." },
      { html: "If a date here is wrong, the fix is a citation. Open an issue " +
        "with one and the position changes. That is the whole standard: " +
        "<a href=\"#/accuracy\">the accuracy report</a> lists what is known " +
        "to be imperfect, and this page lists how the rest was decided." }
    ]);

    return wrap;
  }

  /* Kept beside the method page it documents, and mirrored from PERIODS in
     tools/dates.py -- if one changes the other has to. */
  var PERIOD_TABLE = [
    ["monarchic", "1020–586 BCE", "Saul to the fall of Jerusalem"],
    ["exilic", "597–538 BCE", "the first deportation to the edict of Cyrus"],
    ["post-exilic", "538–332 BCE", "the return under Cyrus to Alexander"],
    ["persian period", "539–332 BCE", "the fall of Babylon to Alexander"],
    ["hellenistic", "332–63 BCE", "Alexander to Pompey's capture of Jerusalem"],
    ["maccabean", "167–63 BCE", "the revolt to Pompey"],
    ["hasmonean", "140–63 BCE", "Simon's rule to Pompey"],
    ["second temple", "516 BCE – 70 CE", "the rebuilt temple to its destruction"],
    ["roman period", "63 BCE – 324 CE", "Pompey to Constantine"]
  ];

  /* "II to IX", or just "IX" for a thread that stays inside one era. */
  function threadSpan(t) {
    var sp = t.sections || {};
    if (!sp.earliest) return t.stops.length ? "one era" : "";
    return sp.earliest === sp.latest
      ? sp.earliest
      : sp.earliest + " to " + sp.latest;
  }

  function viewThreads(threads) {
    var wrap = el("div", { class: "wrap" });
    wrap.appendChild(el("h1", { text: "Threads" }));
    wrap.appendChild(el("p", { class: "lede", text:
      "One question, followed across the whole collection in the order the " +
      "texts were written. This is the thing a chronological arrangement can " +
      "show and a normal Bible cannot: an idea being asked, answered, " +
      "contradicted and answered again over eight hundred years." }));

    var grid = el("div", { class: "thread-cards" });
    threads.forEach(function (t) {
      grid.appendChild(el("a", { class: "thread-card", href: "#/thread/" + t.id }, [
        el("h2", { text: t.title }),
        el("p", { text: t.question }),
        /* The eras the thread reaches, not the eras its first and last stop
           happen to sit in. "Where do the dead go?" takes its third stop in
           the Isaiah apocalypse, which this volume files back in Section II
           with the rest of Isaiah 1-39, so reading the ends of the list gave
           "IV to IX" for a thread that runs II to IX -- understating the one
           thread that travels furthest, on the card whose only job is to say
           how far it travels. tools/build_threads.py works it out where the
           section order is actually known. */
        el("span", { class: "thread-meta", text:
          t.stops.length + " passages · " + threadSpan(t) })
      ]));
    });
    wrap.appendChild(grid);
    return wrap;
  }

  function viewThread(threads, id) {
    var t = threads.filter(function (x) { return x.id === id; })[0];
    if (!t) {
      return el("div", { class: "wrap" }, [
        el("div", { class: "crumbs" }, [
          el("a", { href: "#/threads", text: "Threads" })
        ]),
        el("h1", { text: "No such thread" }),
        el("p", { class: "empty", text:
          "There is no thread by that name. The ones there are are listed " +
          "on the threads page." }),
        el("p", {}, [
          el("a", { class: "chip", href: "#/threads", text: "Every thread" })
        ])
      ]);
    }

    var wrap = el("div", { class: "wrap" });
    wrap.appendChild(el("div", { class: "crumbs" }, [
      el("a", { href: "#/threads", text: "Threads" })
    ]));
    wrap.appendChild(el("h1", { text: t.title }));
    wrap.appendChild(el("p", { class: "lede", text: t.question }));

    var line = el("ol", { class: "thread" });
    t.stops.forEach(function (s, i) {
      var li = el("li", { class: "stop" });

      li.appendChild(el("div", { class: "stop-when" }, [
        el("span", { class: "stop-era", text: s.section || "＋" }),
        el("span", { class: "stop-date", text: s.dates })
      ]));

      var card = el("div", { class: "stop-card" });
      card.appendChild(el("a", {
        class: "stop-ref",
        href: "#/read/" + s.work + "/" + s.chapter + "/v" + s.verses[0].v,
        text: titleCase(s.workTitle) + " · " + s.label
      }));

      s.verses.forEach(function (v) {
        card.appendChild(el("blockquote", { class: "stop-text" }, [
          el("span", { class: "stop-vnum", text: String(v.v) }),
          document.createTextNode(v.t)
        ]));
      });

      card.appendChild(el("p", { class: "stop-why", text: s.why }));
      if (s.aside) {
        card.appendChild(el("p", { class: "stop-aside", text: s.aside }));
      }
      li.appendChild(card);
      line.appendChild(li);
    });
    wrap.appendChild(line);

    wrap.appendChild(el("div", { class: "callout" }, [
      el("p", { text: t.closing })
    ]));

    wrap.appendChild(el("p", { class: "tiny", text:
      "The passages above are the text, reproduced exactly and checked against " +
      "the same files the reader uses; every reference is verified when the " +
      "site is built. The commentary between them is editorial, written for " +
      "this volume." }));

    return wrap;
  }

  /* ================================================================
     SAVED
     ================================================================ */

  function viewSaved() {
    var wrap = el("div", { class: "wrap" });
    wrap.appendChild(el("h1", { text: "Saved" }));

    // Older builds saved whole chapters under a different key. Carry them
    // over rather than appearing to lose someone's work.
    var legacy = store.get("bookmarks", []);
    if (legacy.length) {
      var merged = savedItems();
      legacy.forEach(function (m) {
        var id = m.at;
        if (!merged.some(function (s) { return s.id === id; })) {
          merged.push({
            id: id, kind: "chapter", work: (m.at || "").split("/")[0],
            workTitle: m.work, chapter: parseInt((m.at || "0/0").split("/")[1], 10) || 0,
            label: m.label, at: 0
          });
        }
      });
      // Order matters, and it used to be wrong: clearing the old key after a
      // failed write threw the reader's bookmarks away to save nothing. The
      // old copy is only released once the new one is known to be on disk.
      if (store.set("saved", merged)) store.set("bookmarks", []);
    }

    if (!store.works()) {
      wrap.appendChild(el("p", { class: "empty", text: STORAGE_FAILED }));
    }

    /* ---------------- a copy that can be read back ----------------

       The three below are for putting a passage somewhere else: a document,
       a bibliography, a citation. All three are prose, all three go to the
       clipboard, and none of them can be turned back into saved verses --
       which is fine for what they are for and no use at all for the thing
       this pair is for.

       A browser can drop everything here without warning. Safari's seven-day
       cap is the common way, a cleared site, a new phone or a reinstall are
       the others, and the reader is not told by any of them. keepStorage()
       asks the browser not to; this is what to do when it does anyway, and
       it is the half that works whatever the browser decides.

       The file is the stored array as it stands, so a restore is exact
       rather than a reconstruction: every note, every reference, in the
       shape the reader wrote them. It is also the only way to carry saved
       verses between Safari and the same site installed to the home screen,
       which do not share storage with each other. */
    var BACKUP_FORMAT = "thebook.saved";

    var backup = function () {
      return JSON.stringify({
        format: BACKUP_FORMAT,
        version: 1,
        exported: new Date().toISOString(),
        items: savedItems()
      }, null, 2);
    };

    /* Merged rather than replaced, and by id, so restoring onto a browser
       that already has notes adds what is missing instead of choosing one of
       the two sets to lose. */
    var restore = function (text, button) {
      var parsed;
      try { parsed = JSON.parse(text); }
      catch (e) {
        announce("That file is not a backup this page can read.");
        flash(button, "Not a backup");
        return;
      }
      var incoming = parsed && parsed.items;
      if (!parsed || parsed.format !== BACKUP_FORMAT || !Array.isArray(incoming)) {
        announce("That file is not a backup of saved verses.");
        flash(button, "Not a backup");
        return;
      }
      var usable = incoming.filter(function (i) {
        return i && typeof i.id === "string";
      });
      var have = savedItems();
      var known = {};
      have.forEach(function (i) { known[i.id] = true; });
      var added = usable.filter(function (i) { return !known[i.id]; });
      var merged = have.concat(added);
      merged.sort(function (a, b) { return (b.at || 0) - (a.at || 0); });

      if (!added.length) {
        announce(usable.length
          ? "Everything in that file was already here."
          : "That backup has nothing in it.");
        flash(button, usable.length ? "Already here" : "Nothing to add");
        return;
      }
      if (!store.set("saved", merged.slice(0, 500))) {
        announce(STORAGE_FAILED);
        flash(button, "Could not save");
        return;
      }
      keepStorage();
      announce("Restored " + added.length + " saved item" +
               (added.length === 1 ? "" : "s") + ".");
      route();
    };

    /* Hidden from the accessibility tree rather than merely off-screen. It
       is not a control: the button beside it is, and this is the thing that
       button reaches for. Left visible to a screen reader it is an unlabelled
       file input in the tab order -- which is what axe called critical, and
       it was right. */
    var picker = el("input", {
      type: "file", accept: ".json,application/json", class: "sr-only",
      tabindex: "-1", "aria-hidden": "true"
    });
    picker.addEventListener("change", function () {
      var file = picker.files && picker.files[0];
      if (!file) return;
      var button = picker.__button;
      var reader = new FileReader();
      reader.onload = function () { restore(String(reader.result), button); };
      reader.onerror = function () {
        announce("That file could not be read.");
        flash(button, "Could not read");
      };
      reader.readAsText(file);
      /* Cleared so choosing the same file twice in a row still fires. */
      picker.value = "";
    });

    var items = savedItems();
    if (!items.length) {
      wrap.appendChild(el("p", { class: "empty", text:
        "Nothing saved yet. Tap any verse number to save that verse, or use " +
        "Save at the top of a chapter to keep the whole thing. Everything is " +
        "stored in this browser only — nothing is sent anywhere, and nobody " +
        "else can see it." }));
      /* Restoring has to be offered here above all. An empty list is not
         only the state before anybody has saved anything -- it is also
         exactly what a reader sees after a browser has cleared its storage,
         which is the one moment a backup is for. Returning before this was
         built put the file picker on every screen except the one where it
         was needed, and nothing said so: the button was simply not there,
         on a page whose emptiness was the reason to look for it. */
      wrap.appendChild(el("div", { class: "toolbar" }, [
        el("button", {
          class: "chip", text: "Restore from a file",
          title: "Bring back saved verses from a backup file",
          onclick: function (e) { picker.__button = e.currentTarget; picker.click(); }
        })
      ]));
      wrap.appendChild(picker);
      return wrap;
    }

    var verses = items.filter(function (i) { return i.kind === "verse"; });
    wrap.appendChild(el("p", { class: "muted", text:
      items.length + (items.length === 1 ? " item" : " items") + ", " +
      verses.length + " of them individual verses. Most recent first, stored " +
      "in this browser only." }));

    /* Three ways out, because saved verses are working notes and the next
       place they go is different every time: a document, a bibliography, or
       a file that outlives this browser. Everything here lives in local
       storage only, so being able to get it out is not a convenience. */
    var asText = function () {
      return items.map(function (i) {
        var ref = titleCase(i.workTitle || i.work) + " " + i.label +
                  (i.v ? ":" + i.v : "");
        return i.t ? "“" + i.t + "”\n— " + ref +
                     (i.note ? "\nNote: " + i.note : "") : ref;
      }).join("\n\n");
    };

    var asCitations = function (style) {
      return items.map(function (i) {
        var one = citation(MANIFEST, i, style);
        return i.note && style !== "bibtex" ? one + "\nNote: " + i.note : one;
      }).join(style === "bibtex" ? "\n\n" : "\n\n");
    };

    var tools = el("div", { class: "toolbar" }, [
      el("button", {
        class: "chip", text: "Back up to a file",
        title: "Write everything saved here to a file you keep",
        onclick: function (e) { saveFile(backup(), e.currentTarget); }
      }),
      el("button", {
        class: "chip", text: "Restore from a file",
        title: "Add the saved verses in a backup file to the ones here",
        onclick: function (e) { picker.__button = e.currentTarget; picker.click(); }
      }),
      el("button", {
        class: "chip", text: "Copy all as text",
        onclick: function (e) { copyText(asText(), e.currentTarget,
                                         "All saved items copied"); }
      }),
      el("button", {
        class: "chip", text: "Copy as citations",
        onclick: function (e) { copyText(asCitations("plain"), e.currentTarget,
                                         "Citations copied"); }
      }),
      el("button", {
        class: "chip", text: "Copy as BibTeX",
        onclick: function (e) { copyText(asCitations("bibtex"), e.currentTarget,
                                         "BibTeX copied"); }
      })
    ]);
    wrap.appendChild(tools);
    wrap.appendChild(picker);

    /* Said once, here, where the button that answers it is. Not on the verse
       menu and not after every save: a reader saving a verse is told the true
       thing already, which is that it was saved. This is the standing fact
       about where it was saved to, and it belongs beside the way out. */
    wrap.appendChild(el("p", { class: "muted tiny", text:
      "Saved verses live in this browser and nowhere else. A browser can "
      + "clear them without warning — Safari removes a site's storage after "
      + "about a week without a visit — and they do not follow you to another "
      + "device, or to this site installed to a home screen. Backing up to a "
      + "file is what survives that." }));

    var list = el("div", { class: "results" });
    items.forEach(function (item) {
      var href = "#/read/" + item.work + "/" + item.chapter +
                 (item.v ? "/v" + item.v : "");
      var row = el("article", { class: "saved-row" });

      row.appendChild(el("div", { class: "result-ref" }, [
        el("a", { href: href, text: titleCase(item.workTitle || item.work) +
                   " · " + item.label + (item.v ? ":" + item.v : "") })
      ]));

      if (item.t) {
        row.appendChild(el("blockquote", { class: "saved-text", text: item.t }));
      }

      var note = el("textarea", {
        class: "saved-note", rows: "2",
        placeholder: "Add a note to yourself…",
        "aria-label": "Your note on " + (item.workTitle || item.work) +
                      " " + item.label
      });
      note.value = item.note || "";
      note.addEventListener("change", function () {
        var all = savedItems();
        all.forEach(function (s) { if (s.id === item.id) s.note = note.value; });
        announce(store.set("saved", all) ? "Note saved" : STORAGE_FAILED);
      });
      row.appendChild(note);

      row.appendChild(el("button", {
        class: "chip", text: "Remove",
        "aria-label": "Remove " + (item.workTitle || item.work) + " " + item.label,
        onclick: function () {
          var kept = savedItems().filter(function (s) { return s.id !== item.id; });
          if (!store.set("saved", kept)) { announce(STORAGE_FAILED); return; }
          row.remove();
          announce("Removed from saved");
        }
      }));

      list.appendChild(row);
    });
    wrap.appendChild(list);
    return wrap;
  }

  /* ================================================================
     LISTEN — the text read aloud
     ------------------------------------------------------------------
     Every modern browser ships a speech engine, so the chapter is narrated
     by the voices already installed on the machine. Nothing is downloaded,
     nothing is sent anywhere, and it works offline.

     This comment used to justify that by saying an audiobook of a library
     this size cannot be recorded and that no recording of these translations
     exists in the public domain. Neither is true: LibriVox has read the
     World English Bible through -- 99 hours, Public Domain Mark -- and has
     done Charles's Enoch and Jubilees as well. The device voice is still the
     right default, because it is the one that needs no network and works in
     the single-file copy. It is not the only thing there is.

     The narration is verse-granular on purpose: it is the unit the reader
     already navigates by, it is what gets highlighted as the voice moves,
     and it is what the position is remembered as, so listening picks up
     mid-chapter the way reading does.
     ================================================================ */

  var speech = window.speechSynthesis;
  var SPEECH_OK = !!(speech && typeof window.SpeechSynthesisUtterance === "function");

  /* Chrome cuts off a single utterance at around fifteen seconds and simply
     stops. The usual workaround is a pause/resume heartbeat, which clips
     words; instead every passage is cut into pieces short enough that no
     one utterance ever reaches the limit. Verses are already about this
     length, so only the long paragraph works are really affected.

     Fifteen seconds is a duration, not a length, so the limit has to be read
     in characters through the reading speed. Engines land near fifteen
     characters a second at rate 1, and the budget below is thirteen seconds
     of that with the rest left as margin — 195 characters at rate 1, 136 at
     0.7, 390 at 2. A fixed 220 was over the cut-off at both of the slow
     speeds this player offers, which is the one place the truncation it
     exists to prevent was still happening, and the place a reader is most
     likely to be when a passage stops mid-sentence: liturgical pace and a
     slow voice is how you read the Psalms. Capped, because a very long
     utterance also coarsens the transport and delays the first word
     highlight. */
  var SECONDS = 13, PER_SECOND = 15, CAP = 400, FLOOR = 110;

  function maxChars(rate) {
    var n = Math.round(SECONDS * PER_SECOND * (rate || 1));
    return Math.max(FLOOR, Math.min(CAP, n));
  }

  /* The Charles editions print their apparatus in the running text: daggers
     round a corrupt reading, angle brackets round a restoration, plus signs
     round an emendation, square brackets round a later hand. The eye steps
     over them without noticing. An engine does not — it reads them out,
     "dagger", "less than", "plus" — and a paragraph of that is half of why
     a voice sounds deranged. They are blanked before speaking and left
     standing on the page, where they belong.

     Blanked rather than deleted: each mark becomes a space, so the text
     handed to the engine is the same length as the text on the page, and the
     word highlight — which is drawn from character offsets into it — still
     lands on the right word. Everything below obeys that rule, which is why
     none of it is a rewrite of the text: it is the page's own characters
     with the ones that are not words taken out of the voice's way.

     The nineteenth-century printings recovered from scans bring a second set
     of marks, and a larger one: their footnote references. Cooper and
     Maclean, Horner and Issaverdens all set them as superscript symbols, and
     the scanning engine read those as whatever glyph they most resembled —
     ® 270 times, then », °, §, •, ¢, £, ¥, ™, © and the rest. On the page
     they are what the printing has and they stay. Spoken, they were
     "registered trademark" and "degrees" and "section" scattered through the
     Testament of our Lord about once every other sentence.

     The set is not a guess at what a scan might contain: it is every
     character in this volume that is neither a letter, a digit, nor ordinary
     punctuation, and tests/python/test_narration.py fails if the volume ever
     grows one that is not listed here. */
  /* --8<-- speakable: start --8<-- */
  var EDITORIAL = /[†‡+<>[\]{}®©™°§¶•¢£¥€$#%*«»^¬■|\\_&]/g;

  /* Charles numbers his chapters in the running text, so Enoch, Jubilees,
     the Apostolic Canons and the Didascalia carry two hundred roman numerals
     inside the prose. An engine does not read those as numbers. It reads
     LXXXIX as five or six letters, and the reader hears the alphabet in the
     middle of a sentence about Noah.

     Converted rather than blanked, because the number is not apparatus — it
     is what the sentence says. The full stop after it is required, which is
     what keeps an ordinary capitalised word made only of numeral letters out
     of this, and the arabic form is padded back out to the length of the
     roman one so the character offsets the highlight runs on do not move. A
     numeral that would grow — CD is 400 — is left alone rather than padded
     negatively. */
  var ROMAN = /\b(?=[MDCLXVI]{2,}\b)M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})\b\./g;
  var ROMAN_VALUE = { I: 1, V: 5, X: 10, L: 50, C: 100, D: 500, M: 1000 };
  var PAD = "          ";

  function fromRoman(text) {
    var total = 0, highest = 0;
    for (var i = text.length - 1; i >= 0; i--) {
      var v = ROMAN_VALUE[text.charAt(i)];
      total = v < highest ? total - v : total + v;
      if (v > highest) highest = v;
    }
    return total;
  }

  /* The Ante-Nicene Fathers set their dashes as a pair of hyphens, and the
     source kept them: 162 of them, most in Hermas. Engines disagree about
     what to do with "--" and several read it as nothing at all, so the
     sentence runs through the break without one. A comma and a space is two
     characters, the same as the pair it replaces, and it is what the dash
     was there to ask for. */
  var DOUBLE_DASH = /--/g;

  function speakable(text) {
    return text.replace(EDITORIAL, " ")
               .replace(DOUBLE_DASH, ", ")
               .replace(ROMAN, function (m) {
                 var said = String(fromRoman(m.slice(0, -1))) + ".";
                 if (said.length > m.length) return m;
                 return said + PAD.slice(0, m.length - said.length);
               });
  }
  /* --8<-- speakable: end --8<-- */

  var NO_VOICE =
    "This device has no speech voice for the page to read with. Voices are " +
    "installed by the operating system rather than by a website — adding one " +
    "in your system's speech or accessibility settings will turn this on.";

  function sentenceSpans(text) {
    var out = [], start = 0, i = 0, n = text.length;
    while (i < n) {
      var c = text.charAt(i);
      if (c === "." || c === "!" || c === "?") {
        var j = i + 1;
        while (j < n && /["'’”)\]]/.test(text.charAt(j))) j++;
        if (j >= n || /\s/.test(text.charAt(j))) {
          while (j < n && /\s/.test(text.charAt(j))) j++;
          out.push({ start: start, text: text.slice(start, j) });
          start = j; i = j;
          continue;
        }
      }
      i++;
    }
    if (start < n) out.push({ start: start, text: text.slice(start) });
    return out;
  }

  /* A sentence longer than the limit on its own — Hebrews and 4 Maccabees
     both manage it — has to be broken somewhere, and where matters more than
     it looks. An engine drops its pitch and takes a breath at the end of
     every utterance, so a break in the middle of a clause is heard as a full
     stop that is not there: the commonest way a long verse comes out sounding
     chopped up by a machine. The break is taken at the last comma, semicolon,
     colon or dash that still leaves a piece worth speaking, and only falls
     back to the nearest word boundary when a clause runs past the limit by
     itself. */
  var CLAUSE_END = /[,;:—–)]["'’”]?\s*$/;

  /* A piece has to be worth the pause it ends on. Kept proportional to the
     budget rather than fixed, so that at a slow speed -- where the budget is
     small -- the rule does not demand a piece longer than the budget allows
     and give up on clause breaks altogether. */
  function minPiece(limit) { return Math.round(limit * 0.45); }

  function splitLong(span, limit) {
    var re = /\S+\s*/g, m, toks = [];
    while ((m = re.exec(span.text))) toks.push({ text: m[0], at: m.index });
    if (!toks.length) return [span];

    var out = [], i = 0;
    while (i < toks.length) {
      var len = 0, j = i, clause = -1, least = minPiece(limit);
      while (j < toks.length && (len === 0 || len + toks[j].text.length <= limit)) {
        len += toks[j].text.length;
        j++;
        if (len >= least && CLAUSE_END.test(toks[j - 1].text)) clause = j;
      }
      // The tail of a sentence already ends where the sentence does; only a
      // piece with more coming after it is worth pulling back to a pause.
      var end = (j < toks.length && clause > i) ? clause : j;
      var text = "";
      for (var k = i; k < end; k++) text += toks[k].text;
      out.push({ start: span.start + toks[i].at, text: text });
      i = end;
    }
    return out;
  }

  function chunk(text, limit) {
    var out = [], cur = null;
    limit = limit || maxChars(1);

    function flush() { if (cur) { out.push(cur); cur = null; } }

    sentenceSpans(text).forEach(function (s) {
      if (s.text.length > limit) {
        flush();
        splitLong(s, limit).forEach(function (p) { out.push(p); });
        return;
      }
      if (cur && cur.text.length + s.text.length <= limit) cur.text += s.text;
      else { flush(); cur = { start: s.start, text: s.text }; }
    });
    flush();
    return out.length ? out : [{ start: 0, text: text }];
  }

  /* ---------------- voices ----------------

     A device does not offer a voice, it offers a drawer of them, and the
     drawer is not sorted by how they sound. macOS files two dozen novelties
     — Zarvox, Bubbles, Deranged, Trinoids — beside its good ones, and the
     MacinTalk voices of the early nineties beside those. Linux answers with
     eSpeak. Windows still ships the old SAPI "Desktop" voices alongside its
     neural ones. Taking the first voice in the list, or the one the system
     happens to flag as default, is how a library of scripture ends up read
     by a joke robot — which is exactly what it used to do here.

     So the drawer is scored. What is known to be good — Apple's enhanced and
     premium downloads, Microsoft's natural voices, Google's, anything the
     browser synthesises on a server rather than on the device — is preferred
     and offered first. What is known to be a toy or a relic is put at the
     bottom and labelled, rather than hidden: a device may have nothing else,
     and the choice stays the reader's.

     The scoring goes on names, which is unlovely, but names are all there is:
     the API has no field for quality, and no way to ask. So this is a list of
     what the platforms are known to ship, and it will age. It is only ever a
     default — one selection in the player overrides the lot of it. */

  var GOOD    = /(natural|neural|premium|enhanced|siri|wavenet|studio|journey|online)/i;
  var GOOGLE  = /^google\b/i;
  /* The engines that sound synthetic however they are driven, and the SAPI5
     "Desktop" voices Windows keeps for compatibility. */
  var POOR    = /(espeak|festival|flite|pico|klatt|robosoft|mbrola|compact|\bdesktop\b)/i;
  /* The novelties and the MacinTalk set, by name, because that is how they
     arrive. Any of them can still be chosen; none is ever chosen for you. */
  var NOVELTY = /^(albert|bad news|bahh|bells|boing|bubbles|cellos|deranged|good news|hysterical|jester|junior|kathy|organ|pipe organ|princess|ralph|superstar|trinoids|whisper|wobble|zarvox|agnes|bruce|fred|vicki|victoria)\b/i;
  /* Apple's standard English voices, which carry no marker in their names. */
  var MODERN  = /^(alex|allison|ava|aaron|daniel|evan|fiona|joelle|karen|moira|nathan|nicky|noelle|rishi|samantha|serena|susan|tessa|tom|zoe)\b/i;

  /* Everything above reads the name, because on Windows, Android and Linux
     the name is where the quality is written. Apple does the opposite: the
     name is bare and the quality is in the identifier. The same Samantha is

       com.apple.voice.compact.en-US.Samantha     nothing downloaded
       com.apple.voice.enhanced.en-US.Samantha    the free download
       com.apple.voice.premium.en-US.Samantha     the larger free download

     and an iPhone out of the box has only the compact set — the thin,
     clipped reading this whole change is about. Reading only the name filed
     that under "best on this device" and said nothing, which was worse than
     useless: it is the one case where the reader has to be told, because the
     fix is a download in Settings and no web page can do it for them. */
  var APPLE_BETTER  = /\b(premium|enhanced)\b/i;
  var APPLE_COMPACT = /\bcompact\b/i;

  function isEnglish(v) { return /^en(-|_|$)/i.test(v.lang || ""); }

  /* Three drawers rather than a ranking the reader cannot see: what to use,
     what else is here, and what not to be surprised by. */
  function voiceTier(v) {
    var name = v.name || "", uri = v.voiceURI || "";
    if (NOVELTY.test(name) || !isEnglish(v)) return 2;
    // Apple's own tiering, where it keeps it, and ahead of the name so a
    // compact Samantha is not promoted on the strength of being a Samantha.
    if (APPLE_BETTER.test(uri)) return 0;
    if (APPLE_COMPACT.test(uri)) return 1;
    if (POOR.test(name)) return 1;
    if (GOOD.test(name) || GOOGLE.test(name) || MODERN.test(name) ||
        v.localService === false) return 0;
    return 1;
  }

  function voiceScore(v) {
    var name = v.name || "";
    var lang = (v.lang || "").replace("_", "-");
    var here = (navigator.language || "en-US").replace("_", "-");
    var s = 0;

    // The library is English. A Polish voice reading Amos is not a matter of
    // taste, so language outranks everything else in the sort.
    if (isEnglish(v)) {
      s += 1000;
      if (lang.toLowerCase() === here.toLowerCase()) s += 20;
      else if (/^en-(us|gb)$/i.test(lang)) s += 12;
    }

    if (NOVELTY.test(name)) s -= 500;
    else if (POOR.test(name)) s -= 200;

    if (GOOD.test(name)) s += 60;
    if (GOOGLE.test(name)) s += 45;
    if (MODERN.test(name)) s += 30;
    // Where Apple writes the quality, so a downloaded voice outranks the
    // stock one of the same name rather than tying with it.
    var uri = v.voiceURI || "";
    if (APPLE_BETTER.test(uri)) s += 70;
    else if (APPLE_COMPACT.test(uri)) s -= 40;
    // Chrome and Android synthesise their good voices on a server and their
    // stopgaps on the device, so this is a quality signal as much as a
    // network one. Safari runs everything locally and simply scores flat.
    if (v.localService === false) s += 15;
    if (v.default) s += 2;
    return s;
  }

  var voices = [];
  function loadVoices() {
    if (!SPEECH_OK) return;
    voices = (speech.getVoices() || []).slice();
    var order = [];
    voices.forEach(function (v, i) { order.push({ v: v, i: i, s: voiceScore(v) }); });
    // Sorted best first, and by the drawer's own order where the score ties,
    // so the list does not reshuffle itself between visits.
    order.sort(function (a, b) { return b.s - a.s || a.i - b.i; });
    voices = order.map(function (o) { return o.v; });
  }
  if (SPEECH_OK) {
    loadVoices();
    speech.addEventListener("voiceschanged", function () {
      loadVoices();
      if (player) fillVoices();
    });
  }

  function chosenVoice() {
    var want = store.get("listen-voice", null);
    var found = null;
    // Some engines renumber their voice URIs between releases; the name is
    // the more durable half of a saved choice, so it is the fallback.
    voices.forEach(function (v) { if (!found && v.voiceURI === want) found = v; });
    voices.forEach(function (v) { if (!found && v.name === want) found = v; });
    return found || voices[0] || null;
  }

  /* ---------------- the recorded voice ----------------

     Everything above is the device's own engine, and the ceiling of it is
     that the audio belongs to the operating system: on a phone out of the
     box that is the compact set, and no amount of work on this page changes
     how it sounds.

     A neural voice good enough to read these texts cannot run here. Kokoro
     measures 0.43x realtime in Chromium on one thread — thirty-one seconds
     of arithmetic for thirteen seconds of speech — because WebAssembly gets
     no threads on a site that cannot send COOP/COEP headers, and the model
     is transformer-heavy. So the arithmetic is done once by
     tools/render_audio.py and the result is served: one Opus file per
     chapter, with a JSON of per-verse offsets beside it.

     What that buys, beyond the voice: speed is playbackRate, which browsers
     time-stretch without shifting pitch; seeking to a verse is one
     assignment to currentTime; and the verse marks are exact rather than
     estimated, because each verse was synthesised on its own and its offset
     recorded as it accumulated.

     What it costs: it needs a network, and there are no word boundaries in
     an audio file, so the word highlight is off here and the verse mark
     carries the reading. The device engine stays the default and the
     offline path, and everything falls back to it. */

  /* The one line to change when the audio moves. It is an Internet Archive
     item because the texts are public domain and so is their reading, and
     because 1.79 GB cannot live in the Pages artifact — that caps at 1 GB. */
  var AUDIO_BASE = "https://archive.org/download/the-book-read-aloud/";

  /* Whether that item exists at all, which is a different question from
     whether a given chapter has a reading, and needs a different answer.

     The metadata endpoint returns {} for an item that is not there -- the
     Internet Archive's way of saying no such thing -- and sends
     Access-Control-Allow-Origin: *, so the page can ask. Without asking, a
     missing collection is indistinguishable from a chapter that was never
     rendered: the drawer goes on offering a reading nobody can hear, and
     every chapter opened fires another doomed cross-origin request at it.
     Reading through Psalms did that a hundred and fifty times. */
  var AUDIO_META = "https://archive.org/metadata/the-book-read-aloud";

  /* Not in the single-file copy. That build's whole claim is that it opens
     from a file:// URL with the network off and everything in it works, and
     a voice that has to be fetched from an archive is the one thing it
     cannot honour. The footer link is cut from that build for the same
     reason -- see strip_online_only() in tools/build_standalone.py -- and
     this is the same rule applied to the one feature the markers in
     index.html cannot reach, because the drawer is built here rather than
     written in the page. */
  /* Whether the reading has actually been rendered and uploaded.
     ------------------------------------------------------------------
     Everything below this line is finished and under test: the fetch, the
     per-verse index, the seek, the pace control, the fall back to the
     device engine. What does not exist is the audio. The item at
     AUDIO_BASE has never been created, and until it is, offering a voice
     in the drawer is offering something that is not there -- the probe
     only fires once a reader has already chosen it, so on every ordinary
     device the drawer went on advertising it for the whole session.

     The switch is data-audio on <html> rather than a constant here: it is
     a fact about a deploy rather than about the code, it is visible in the
     served page without reading a bundle, and the browser checks can set it
     to exercise the player's recorded path -- which is finished, and would
     otherwise lose its tests the moment the voice stopped being offered.
     tools/check_audio.py reads it out of docs/index.html and checks it both
     ways: absent while the item exists is a switch somebody forgot to flip;
     "published" while the item is missing is a broken promise to every
     reader. Add the attribute in the same commit that uploads the item.

     A note on what "uploaded" would mean, so the next hand does not repeat
     the search: LibriVox has read the World English Bible through and
     dedicated it to the public domain, and Charles's Enoch and Jubilees
     besides. That is a person rather than a model and costs no rendering
     at all -- but an audiobook is continuous speech with no verse
     boundaries in it, so the per-verse marks this player is built on have
     to be recovered by forced alignment rather than recorded. That is the
     work between here and true. */
  var AUDIO_PUBLISHED =
        document.documentElement.getAttribute("data-audio") === "published";

  var AUDIO_OK = AUDIO_PUBLISHED &&
                 typeof window.Audio === "function" && !window.__BOOK__;

  var aud = {
    el: null,       // one <audio>, reused across chapters
    index: null,    // [[verse, start, end], ...] for the chapter loaded
    key: null,      // which chapter that is
    want: false,    // the reader has asked for the recorded voice
    tried: {},      // chapters already looked for, so a miss is asked once
    waiting: 0      // a pace pause is running; ignore the transport meanwhile
  };

  /* Asked once a session rather than once a chapter, and asked once even if
     six things ask at the same moment: everything that wants to know waits on
     the one request in flight. */
  var audioItem = {
    state: "unknown",   // "unknown" | "checking" | "present" | "absent"
    waiting: []         // callbacks held while the one request is in flight
  };

  function audioItemReady(done) {
    if (audioItem.state === "present") { done(true); return; }
    if (audioItem.state === "absent") { done(false); return; }

    audioItem.waiting.push(done);
    if (audioItem.state === "checking") return;
    audioItem.state = "checking";

    fetchJSON(AUDIO_META, function (meta) {
      // A network failure is not an answer. Treating an unreachable
      // archive.org as a missing collection would take the reading away from
      // everyone on a flaky connection and not give it back until they
      // reloaded, which is the worse of the two mistakes: the reading is
      // most wanted by the people least able to fetch it reliably.
      if (meta === null) {
        audioItem.state = "unknown";
      } else {
        audioItem.state = (meta.files || meta.metadata) ? "present" : "absent";
      }
      var present = audioItem.state === "present";
      var waiting = audioItem.waiting;
      audioItem.waiting = [];
      if (audioItem.state === "absent") {
        // Stop offering it, and stop the reader's saved choice pointing at
        // it -- otherwise every chapter starts by asking for a voice that
        // does not exist and falling back from it.
        if (store.get("listen-voice", null) === "recorded") {
          store.set("listen-voice", null);
        }
        if (player) fillVoices();
      }
      waiting.forEach(function (fn) { fn(present); });
    });
  }

  function audioWanted() {
    if (!AUDIO_OK) return false;
    var want = store.get("listen-voice", null);
    if (want === "recorded") return true;
    /* A device with no speech engine of its own has only this one, and the
       drawer that would let it be chosen lives inside a player that does not
       open until something is being read. Without this, such a device gets a
       Listen button that does nothing and no way to find out why. */
    return !SPEECH_OK && want === null;
  }

  function chapterKey(ctx) {
    return ctx ? ctx.work + "/" + ctx.chapter : null;
  }

  /* The offsets for a chapter, or null if there is no reading of it.

     Not every chapter has one: render_audio.py works from the verse
     structure, so the paragraph works — Hermas, the Didascalia — have no
     index and fall back to the device engine. A miss is remembered so that
     paging through a work does not ask for the same missing file twice. */
  function loadAudioIndex(ctx, done) {
    var key = chapterKey(ctx);
    if (!key) { done(null); return; }
    if (aud.key === key && aud.index) { done(aud.index); return; }
    if (aud.tried[key] === false) { done(null); return; }

    // Is there a collection at all, before asking it for one chapter.
    audioItemReady(function (present) {
      if (!present) { done(null); return; }

      fetchJSON(AUDIO_BASE + ctx.work + "/" + ctx.chapter + ".json",
        function (data) {
          if (!data || !data.v || !data.v.length) {
            aud.tried[key] = false;
            done(null);
            return;
          }
          aud.tried[key] = true;
          aud.key = key;
          aud.index = data;
          done(data);
        });
    });
  }

  function fetchJSON(url, done) {
    try {
      fetch(url, { mode: "cors" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(done)
        .catch(function () { done(null); });
    } catch (e) { done(null); }
  }

  /* One item per verse, in the order the offsets give, pointing at the same
     nodes the device engine would have marked.

     Built to the same shape buildItems() produces, so mark(), itemLabel(),
     jump(), updatePlayer() and the saved position all work on it unchanged.
     The only additions are the two numbers that say where in the file this
     verse is. A verse in the index with nothing matching it on the page is
     dropped rather than guessed at. */
  function buildAudioItems(passages, index) {
    var byVerse = {};
    passages.forEach(function (p) {
      if (p.verse && !byVerse[p.verse]) byVerse[p.verse] = p;
    });

    var items = [];
    index.v.forEach(function (row, i) {
      var p = byVerse[row[0]];
      if (!p) return;
      items.push({
        el: p.el, node: p.node, start: 0, text: p.text,
        verse: p.verse, unit: p.unit, ordinal: i + 1,
        a: row[1], b: row[2]
      });
    });
    return items;
  }

  function audioElement() {
    if (aud.el) return aud.el;
    var a = new Audio();
    a.preload = "none";

    a.addEventListener("timeupdate", function () { audioTick(); });
    a.addEventListener("ended", function () {
      if (!nar.playing || !usingAudio()) return;
      chapterFinished();
    });
    a.addEventListener("error", function () {
      if (!usingAudio()) return;
      fallBackToDevice("The recording could not be played — using this " +
                       "device's own voice instead.");
    });
    aud.el = a;
    return a;
  }

  function usingAudio() {
    return nar.engine === "recorded";
  }

  /* The pace controls are the reader's, not the recording's.

     render_audio.py bakes a 350 ms rest between verses, which is the natural
     pace and the one that has to sound continuous. The slower paces ask for
     more than that, so the difference is taken here by holding the transport
     — which is also why a psalm can still be read the way a psalm is read.
     Nothing is added at natural pace, so the common case never pauses. */
  var BAKED_REST = 350;

  function audioTick() {
    if (!usingAudio() || !nar.playing || aud.waiting) return;
    var a = aud.el, items = nar.items;
    if (!a || !items.length) return;

    // The sleep timer is checked between pieces on the device side; here the
    // transport is what ticks, so it is checked here.
    if (nar.sleepAt && Date.now() > nar.sleepAt) {
      stopListening("Listening stopped — sleep timer.");
      return;
    }

    var t = a.currentTime;
    var at = nar.at;

    // Which verse the playhead is in. Normally the next one along, so this
    // walks rather than searches.
    while (at + 1 < items.length && t >= items[at + 1].a) at++;
    while (at > 0 && t < items[at].a) at--;

    if (at !== nar.at) {
      nar.at = at;
      mark(items[at]);
      updatePlayer();
    }

    // Past the end of this verse, with more to come: take the extra rest the
    // pace asks for beyond what the file already carries.
    var item = items[nar.at];
    if (item && nar.at + 1 < items.length && t >= item.b) {
      var extra = restAfter(item, items[nar.at + 1]) - BAKED_REST;
      if (extra > 200) {
        var gen = nar.gen;
        aud.waiting = 1;
        a.pause();
        setTimeout(function () {
          aud.waiting = 0;
          if (gen === nar.gen && nar.playing && usingAudio()) a.play();
        }, extra);
      }
    }
  }

  function audioPlayFrom(i) {
    var a = audioElement(), items = nar.items;
    if (!items.length) return;

    nar.at = Math.max(0, Math.min(i, items.length - 1));
    nar.playing = true;
    aud.waiting = 0;

    var src = AUDIO_BASE + nar.ctx.work + "/" + nar.ctx.chapter + ".opus";
    if (a.getAttribute("src") !== src) {
      a.setAttribute("src", src);
      a.load();
    }
    a.playbackRate = store.get("listen-rate", 1);

    // A seek before the file has any duration is discarded, so it waits for
    // as much metadata as a seek needs rather than for the whole file.
    var target = items[nar.at].a;
    function go() {
      try { a.currentTime = target; } catch (e) { /* seek when it can */ }
      var playing = a.play();
      if (playing && playing.catch) {
        playing.catch(function () {
          fallBackToDevice("The recording could not be played — using this " +
                           "device's own voice instead.");
        });
      }
    }
    if (a.readyState >= 1) go();
    else a.addEventListener("loadedmetadata", go, { once: true });

    mark(items[nar.at]);
    updatePlayer();
  }

  /* Any failure on the recorded side is answered by the engine that needs
     nothing: rebuild the queue the device engine expects and carry on from
     the verse being read, rather than stopping on an error the reader can do
     nothing about. */
  function fallBackToDevice(message) {
    var verse = nar.items[nar.at] ? nar.items[nar.at].verse : null;
    if (aud.el) aud.el.pause();
    aud.waiting = 0;
    nar.engine = "device";
    store.set("listen-voice", null);

    if (!SPEECH_OK) { stopListening(message); return; }

    nar.items = buildItems(nar.passages, maxChars(store.get("listen-rate", 1)));
    var at = 0;
    for (var i = 0; i < nar.items.length; i++) {
      if (nar.items[i].verse === verse) { at = i; break; }
    }
    if (player) fillVoices();
    announce(message);
    if (nar.playing) speakFrom(at);
    else { nar.at = at; updatePlayer(); }
  }

  /* Changing voice mid-chapter changes which engine is reading, and the two
     count their position differently — the device engine in utterance-sized
     pieces, the recording in verses. So the place is carried across as the
     verse it is, the way rebuildQueue() carries it across a change of speed,
     and not as an index into a list that is about to be replaced. */
  function switchEngine(toRecorded) {
    var was = nar.items[nar.at];
    var verse = was ? was.verse : null;
    var playing = nar.playing;

    function settle(items, engine) {
      nar.engine = engine;
      nar.items = items;
      var at = 0;
      for (var i = 0; i < items.length; i++) {
        if (items[i].verse === verse) { at = i; break; }
      }
      nar.at = at;
      if (playing) speakFrom(at);
      else { if (items[at]) mark(items[at]); updatePlayer(); }
    }

    if (!toRecorded) {
      if (aud.el) { aud.el.pause(); aud.waiting = 0; }
      if (!SPEECH_OK) { stopListening(null); return; }
      settle(buildItems(nar.passages, maxChars(store.get("listen-rate", 1))),
             "device");
      if (!playing) previewVoice();   // picked while stopped: let it be heard
      return;
    }

    if (!nar.ctx) return;
    loadAudioIndex(nar.ctx, function (index) {
      if (!index) {
        // Asked for by a reader who cannot have it here: say so once, and
        // leave them on the engine that works.
        store.set("listen-voice", null);
        if (player) fillVoices();
        announce("There is no recording of this chapter — it is read by " +
                 "this device's own voice.");
        return;
      }
      var items = buildAudioItems(nar.passages, index);
      if (!items.length) { store.set("listen-voice", null); return; }
      if (playing && SPEECH_OK) speech.cancel();
      settle(items, "recorded");
    });
  }

  /* ---------------- the narrator ---------------- */

  var HIGHLIGHT_OK = !!(window.CSS && CSS.highlights &&
                        typeof window.Highlight === "function");

  var nar = {
    items: [],      // one utterance-sized piece each
    passages: [],   // what they were cut from, for when the speed changes
    at: 0,
    ctx: null,      // which chapter these belong to
    on: false,      // the player is open
    playing: false,
    utter: null,
    gen: 0,         // cancels stale onend/onerror from a discarded utterance
    resumeChapter: null,  // set when auto-advancing into the next chapter
    sleepAt: 0,
    stopAtEnd: false,
    pendingResumeAt: 0,
    blocked: null,  // the engine has already told us it cannot speak
    engine: "device"  // "device" is speechSynthesis, "recorded" is the files

  };

  function reducedMotion() {
    return window.matchMedia &&
           window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function clearWordHighlight() {
    if (HIGHLIGHT_OK) CSS.highlights.delete("book-speaking");
  }

  function clearMarks() {
    var prev = document.querySelector(".is-speaking");
    if (prev) prev.classList.remove("is-speaking");
    clearWordHighlight();
  }

  /* Build the speakable queue from what was actually rendered, so the thing
     being highlighted is the thing on the page rather than a second copy of
     the text held somewhere else. */
  function buildItems(passages, limit) {
    var items = [];
    passages.forEach(function (p, pi) {
      chunk(p.text, limit).forEach(function (c) {
        items.push({
          el: p.el, node: p.node, start: c.start, text: c.text,
          verse: p.verse, unit: p.unit, ordinal: pi + 1
        });
      });
    });
    return items;
  }

  /* Changing the speed changes how many characters fit in an utterance, so
     the queue has to be cut again. Where the reader had got to is a place in
     the chapter, not an index into a list that no longer exists, so it is
     carried across as the passage and the character offset inside it and
     looked up again in the new queue. Without that, slowing down in the
     middle of Jeremiah would put you somewhere else in Jeremiah. */
  function rebuildQueue() {
    if (!nar.passages || !nar.passages.length) return;
    var here = nar.items[nar.at];
    nar.items = buildItems(nar.passages, maxChars(store.get("listen-rate", 1)));
    if (!here) { nar.at = Math.min(nar.at, nar.items.length - 1); return; }
    var best = 0;
    for (var i = 0; i < nar.items.length; i++) {
      var it = nar.items[i];
      if (it.el !== here.el) continue;
      if (it.start <= here.start) best = i;
      else break;
    }
    nar.at = best;
  }

  /* Engines land near 165 words a minute at rate 1 — about fifteen characters
     a second. This is not a duration, it is the difference between a psalm
     you can hear now and a chapter of Jeremiah you cannot.

     The silences count too, and at the slow paces they are most of the
     difference. Psalm 119 is 176 verses; at liturgical pace the pause after
     each of them is just over a second, so a reading the arithmetic below
     used to call ten minutes is thirteen. A time left that is wrong by three
     minutes on the longest chapter in the volume is worse than no time left
     at all, because it is believed. */
  function minutesLeft() {
    // The recording knows exactly how long it is, so there is nothing to
    // estimate: the arithmetic below exists only because an engine speaking
    // live cannot be asked.
    if (usingAudio() && aud.index) {
      var played = aud.el ? aud.el.currentTime : 0;
      var rate = store.get("listen-rate", 1) || 1;
      return Math.max(0, (aud.index.d - played) / rate) / 60;
    }

    var chars = 0, rest = 0;
    for (var i = nar.at; i < nar.items.length; i++) {
      chars += nar.items[i].text.length;
      rest += restAfter(nar.items[i], nar.items[i + 1]);
    }
    var speaking = chars / (15 * (store.get("listen-rate", 1) || 1));
    return (speaking + rest / 1000) / 60;
  }

  function timeLabel(min) {
    if (min < 1) return "under a minute left";
    if (min < 60) return Math.round(min) + " min left";
    var h = Math.floor(min / 60);
    return h + " h " + Math.round(min - h * 60) + " min left";
  }

  function itemLabel(item) {
    if (!item) return "";
    if (item.unit === "heading") return "Heading";
    if (item.verse) return "Verse " + item.verse;
    return titleCase(item.unit || "paragraph") + " " + item.ordinal;
  }

  /* Engines run one utterance straight into the next, so a chapter arrives
     as an unbroken wall of words — on its own the thing that most makes a
     reading sound mechanical, whatever voice is doing it. A verse gets the
     beat a person reading aloud would take, the chapter heading a longer
     one, and a sentence that was cut only because it was too long gets none
     at all: that seam is the one place a pause would be a lie. */
  /* How long the silences are.

     The default is speech: the pauses a reader would leave, and no more. That
     is wrong for the half of this library that is verse. A psalm read at
     conversational pacing is a list of sentences; the line is the unit, and
     the silence after it is part of the line.

     This is a control rather than something the volume decides, because the
     volume does not classify its books by genre and has no business
     pretending to. Job is verse inside a prose frame, the prophets move
     between the two mid-chapter, and Ecclesiastes is argued about. A reader
     can hear which one they are in; a hand-written list of "the poetry books"
     would be an editorial claim with no citation behind it, which is the one
     thing the rest of this volume refuses to do. */
  var PACE = {
    natural:    { rest: 1,   line: 1,   label: "Pace: natural" },
    measured:   { rest: 1.8, line: 2.2, label: "Measured" },
    liturgical: { rest: 3,   line: 4,   label: "Liturgical" }
  };

  function pace() {
    return PACE[store.get("listen-pace", "natural")] || PACE.natural;
  }

  function restAfter(item, next) {
    if (!next) return 0;
    var p = pace();
    if (item.unit === "heading") return Math.round(550 * p.rest);
    var ends = /[.!?]["'’”)\]]?\s*$/.test(item.text);
    var moved = next.verse !== item.verse || next.el !== item.el;

    /* At a slower pace the break between verses is the break between lines
       and takes the longer silence. A sentence broken only for the engine's
       length limit still takes none, at any pace, or the words come apart. */
    if (!ends && !moved) return 0;
    if (moved) return Math.round(260 * p.line);
    return Math.round(170 * p.rest);
  }

  function speakFrom(i) {
    // The recorded voice is a file with a playhead rather than a queue of
    // utterances, so it takes the whole transport rather than one piece.
    if (usingAudio()) { nar.gen++; audioPlayFrom(i); return; }
    if (!SPEECH_OK) return;
    nar.gen++;
    var gen = nar.gen;
    speech.cancel();
    nar.at = Math.max(0, Math.min(i, nar.items.length - 1));
    nar.playing = true;
    // Chrome can swallow a speak() issued in the same tick as the cancel()
    // before it; a beat of daylight between the two is the usual remedy.
    setTimeout(function () { step(gen); }, 60);
  }

  function step(gen) {
    if (gen !== nar.gen) return;

    if (nar.sleepAt && Date.now() > nar.sleepAt) {
      stopListening("Listening stopped — sleep timer.");
      return;
    }

    var item = nar.items[nar.at];
    if (!item) { chapterFinished(); return; }

    // A piece that is nothing but editorial marks has nothing to say, and
    // an empty utterance makes several engines report a failure.
    var said = speakable(item.text);
    if (!/\S/.test(said)) { nar.at++; step(gen); return; }

    mark(item);

    var u = new SpeechSynthesisUtterance(said);
    var v = chosenVoice();
    if (v) { u.voice = v; u.lang = v.lang; }
    u.rate = store.get("listen-rate", 1);
    u.pitch = 1;

    // Some engines neither speak nor report a failure. Nothing having
    // happened several seconds after asking is itself the answer.
    var watchdog = setTimeout(function () {
      if (gen === nar.gen && nar.playing) listenUnavailable(NO_VOICE);
    }, 5000);

    u.onstart = function () { clearTimeout(watchdog); };
    u.onboundary = function (e) {
      clearTimeout(watchdog);
      if (gen !== nar.gen || !HIGHLIGHT_OK) return;
      if (e.name && e.name !== "word") return;
      highlightWord(item, e.charIndex, e.charLength);
    };
    u.onend = function () {
      clearTimeout(watchdog);
      if (gen !== nar.gen) return;
      nar.at++;
      var rest = restAfter(item, nar.items[nar.at]);
      if (!rest) { step(gen); return; }
      setTimeout(function () { if (gen === nar.gen) step(gen); }, rest);
    };
    u.onerror = function (e) {
      if (gen !== nar.gen) return;
      clearTimeout(watchdog);
      // "interrupted" and "canceled" are what a deliberate stop looks like.
      if (e.error === "interrupted" || e.error === "canceled") return;
      if (e.error === "synthesis-failed" || e.error === "synthesis-unavailable" ||
          e.error === "language-unavailable" || e.error === "voice-unavailable" ||
          !voices.length) {
        listenUnavailable(NO_VOICE);
        return;
      }
      stopListening("Listening stopped — the voice reported an error.");
    };

    nar.utter = u;
    speech.speak(u);
    updatePlayer();
  }

  function highlightWord(item, charIndex, charLength) {
    if (typeof charIndex !== "number" || !item.node) return;
    var len = charLength;
    if (!len) {
      var m = /^\S+/.exec(item.text.slice(charIndex));
      len = m ? m[0].length : 0;
    }
    if (!len) return;
    var a = item.start + charIndex;
    var b = a + len;
    var max = item.node.length;
    if (a >= max) return;
    if (b > max) b = max;
    try {
      var r = document.createRange();
      r.setStart(item.node, a);
      r.setEnd(item.node, b);
      CSS.highlights.set("book-speaking", new Highlight(r));
    } catch (e) { /* the chapter was re-rendered underneath us */ }
  }

  function mark(item) {
    clearMarks();
    if (!item.el || !item.el.isConnected) return;
    item.el.classList.add("is-speaking");

    var box = item.el.getBoundingClientRect();
    var margin = Math.min(160, window.innerHeight * 0.2);
    if (box.top < margin || box.bottom > window.innerHeight - margin) {
      item.el.scrollIntoView({
        block: "center",
        behavior: reducedMotion() ? "auto" : "smooth"
      });
    }

    if (nar.ctx) {
      store.set("listen-at", {
        work: nar.ctx.work, chapter: nar.ctx.chapter, at: nar.at
      });
    }
  }

  function chapterFinished() {
    clearMarks();
    var ctx = nar.ctx;
    store.set("listen-at", null);

    if (nar.stopAtEnd) {
      nar.stopAtEnd = false;
      stopListening("Listening stopped — end of chapter.");
      return;
    }
    if (store.get("listen-continue", true) && ctx) {
      var intoWork = ctx.next === null;
      var target = intoWork
        ? (ctx.nextWork ? ctx.nextWork.id + "/0" : null)
        : ctx.work + "/" + ctx.next;
      if (target) {
        // Carry the intent across the route change; viewRead picks it up once
        // the next chapter has rendered and starts it from the top.
        nar.resumeChapter = target;
        nar.playing = false;
        updatePlayer();
        if (intoWork) announce("Continuing into " + titleCase(ctx.nextWork.title));
        location.hash = "#/read/" + target;
        return;
      }
    }
    nar.playing = false;
    updatePlayer();
    announce("Finished reading " + (ctx ? ctx.label : "the chapter"));
  }

  /* Having the API is not having a voice. Plenty of desktops -- any Linux
     without speech-dispatcher, some locked-down Windows builds -- expose
     speechSynthesis and then fail the moment you ask it to say something.
     The engine's report of that has to reach the person who pressed the
     button, not just the live region. */
  function listenUnavailable(message) {
    nar.blocked = message;
    stopListening(null);
    document.querySelectorAll("[data-listen]").forEach(function (b) {
      markUnavailable(b);
    });
    announce(message);
  }

  function markUnavailable(button) {
    button.disabled = true;
    button.textContent = "▶ Listen";
    button.title = nar.blocked;
    button.setAttribute("aria-disabled", "true");
    button.setAttribute("aria-pressed", "false");

    var controls = button.parentNode;
    if (!controls || controls.parentNode.querySelector(".listen-note")) return;
    controls.parentNode.insertBefore(
      el("p", { class: "listen-note", role: "note", text: nar.blocked }),
      controls.nextSibling
    );
  }

  function stopListening(message) {
    nar.gen++;
    nar.playing = false;
    nar.on = false;
    nar.resumeChapter = null;
    nar.sleepAt = 0;
    nar.stopAtEnd = false;
    if (SPEECH_OK) speech.cancel();
    if (aud.el) { aud.el.pause(); aud.waiting = 0; }
    clearMarks();
    // The position is deliberately left behind: stopping is not finishing,
    // and reopening the chapter should offer the spot back.
    if (player) player.hidden = true;
    document.body.classList.remove("listening");
    syncListenButtons();
    if (message) announce(message);
  }

  function pauseListening() {
    if (!nar.playing) return;
    nar.gen++;
    nar.playing = false;
    if (usingAudio()) {
      // A file pauses where it is and resumes there, which is what an
      // audio element is for; nothing has to be restarted.
      aud.waiting = 0;
      if (aud.el) aud.el.pause();
    } else {
      // Pause is unreliable on some Android engines, so the position is kept
      // and the piece restarted on resume rather than trusted to the queue.
      speech.cancel();
    }
    clearWordHighlight();
    updatePlayer();
    syncListenButtons();
  }

  function resumeListening() {
    if (!nar.on || !nar.items.length) return;
    if (usingAudio() && aud.el && aud.el.getAttribute("src")) {
      // Carry on from where the playhead stopped, rather than from the top
      // of the verse it stopped inside: seeking back would make pause and
      // play repeat a line every time.
      nar.gen++;
      nar.playing = true;
      aud.el.playbackRate = store.get("listen-rate", 1);
      aud.el.play();
      updatePlayer();
      syncListenButtons();
      return;
    }
    speakFrom(nar.at);
    syncListenButtons();
  }

  function jump(delta) {
    if (!nar.on || !nar.items.length) return;
    var target = nar.at + delta;
    // Back-arrow within a long passage restarts it, as a player would.
    if (delta < 0 && nar.items[nar.at] && nar.items[nar.at].verse) {
      var here = nar.items[nar.at].verse;
      while (target > 0 && nar.items[target] && nar.items[target].verse === here) target--;
    }
    if (target < 0) target = 0;
    if (target >= nar.items.length) { chapterFinished(); return; }
    if (nar.playing) speakFrom(target);
    else { nar.at = target; mark(nar.items[target]); updatePlayer(); }
  }

  /* ---------------- the player ---------------- */

  var player = null, playBtn = null, whereEl = null, unitEl = null,
      barEl = null, voiceSel = null, hintEl = null;

  function option(value, label, selected) {
    return el("option", { value: value, selected: selected ? true : null, text: label });
  }

  var displayNames = null;
  function langLabel(tag) {
    var t = (tag || "").replace("_", "-");
    try {
      if (displayNames === null && window.Intl && Intl.DisplayNames) {
        displayNames = new Intl.DisplayNames([navigator.language || "en"],
                                             { type: "language" });
      }
      if (displayNames) return displayNames.of(t) || t;
    } catch (e) { displayNames = false; }
    return t;
  }

  /* "Microsoft Aria Online (Natural) - English (United States)" names the
     language twice and the second half is the browser's doing, not the
     voice's; it comes off, and the language goes back on cleanly. */
  function voiceLabel(v) {
    var name = String(v.name || "Voice").replace(/\s+[-–]\s+[^-–]*\(.*\)\s*$/, "").trim();
    var label = (name || "Voice") + " · " + langLabel(v.lang);
    // Apple ships several voices under one name and tells them apart only in
    // the identifier, so the drawer would otherwise show the same word twice
    // with no way to know which is the one worth having.
    var grade = APPLE_BETTER.exec(v.voiceURI || "") ||
                APPLE_COMPACT.exec(v.voiceURI || "");
    if (grade) label += " · " + titleCase(grade[0].toLowerCase());
    return label;
  }

  var TIERS = ["Best on this device", "Other voices",
               "Novelty, legacy and other languages"];

  function fillVoices() {
    if (!voiceSel) return;
    var want = chosenVoice();
    var recorded = store.get("listen-voice", null) === "recorded";
    voiceSel.innerHTML = "";

    /* First, and offered to everyone rather than only to the devices with
       nothing good on them. The scoring below can put the best voice on this
       machine at the top of the list and it is still the operating system's
       voice; this one is the same reading everywhere, and on the phones the
       drawer has least to offer it is the only good answer there is. */
    /* Offered while the answer is still "unknown" -- hiding a working voice
       because a request is in flight is the worse of the two mistakes, and
       the drawer refills itself the moment the probe comes back. */
    if (AUDIO_OK && audioItem.state !== "absent") {
      var read = el("optgroup", { label: "Read aloud" });
      read.appendChild(option("recorded", "Recorded reading", recorded));
      voiceSel.appendChild(read);
    }

    if (!voices.length) {
      voiceSel.appendChild(option("", "Default voice", !recorded));
      updateHint();
      return;
    }
    var groups = [null, null, null];
    voices.forEach(function (v) {
      var t = voiceTier(v);
      if (!groups[t]) groups[t] = el("optgroup", { label: TIERS[t] });
      groups[t].appendChild(option(v.voiceURI, voiceLabel(v),
                                   !recorded && !!want &&
                                   v.voiceURI === want.voiceURI));
    });
    groups.forEach(function (g) { if (g) voiceSel.appendChild(g); });
    // chosenVoice() always names a device voice, because that is what it is
    // for; letting it set the value here would undo the recorded choice
    // every time the drawer was refilled.
    if (recorded) voiceSel.value = "recorded";
    else if (want) voiceSel.value = want.voiceURI;
    updateHint();
  }

  /* Nothing a web page can do will make eSpeak sound like a person: the audio
     belongs to the operating system, not to the site. When the drawer holds
     nothing better than a relic, saying where better voices come from is more
     use to the reader than letting them conclude the site is broken. */
  var VOICE_HELP = [
    ["iPhone and iPad", "Settings › Accessibility › Spoken Content › Voices › " +
     "English — pick a voice and download the Enhanced or Premium one. The " +
     "stock voices are the compact set, and they are the thin ones."],
    ["macOS", "System Settings › Accessibility › Spoken Content › System voice › " +
     "Manage Voices, where the Enhanced and Premium downloads are."],
    ["Windows", "Settings › Time & language › Speech › Manage voices, and the " +
     "Natural voices in Narrator's settings."],
    ["Android", "Settings › Accessibility › Text-to-speech output › " +
     "install voice data."],
    ["Linux", "install a neural engine such as Piper, or speech-dispatcher " +
     "with a better module than eSpeak."]
  ];

  function bestIsPoor() {
    if (!voices.length) return false;
    for (var i = 0; i < voices.length; i++) {
      if (voiceTier(voices[i]) === 0) return false;
    }
    return true;
  }

  /* A title attribute is a tooltip, and a tooltip on a phone is nothing at
     all — which is where this matters most. So it opens instead. */
  function buildHint() {
    var box = el("details", { class: "player-hint", hidden: true }, [
      el("summary", { text:
        "No high-quality voice is installed on this device — better ones are " +
        "a free download. How ›" })
    ]);
    VOICE_HELP.forEach(function (row) {
      box.appendChild(el("p", {}, [
        el("strong", { text: row[0] + ": " }), row[1]
      ]));
    });
    return box;
  }

  function updateHint() {
    if (!hintEl) return;
    hintEl.hidden = !bestIsPoor();
  }

  /* Only the person listening can say whether a voice is bearable, and a
     chapter is a long way to find out, so the drawer comes with a sentence
     to try one on. */
  var SAMPLE = "In the beginning, God created the heavens and the earth.";

  function previewVoice() {
    // The recorded reading has no sample to try: it is one voice, and the
    // way to hear it is to press play.
    if (audioWanted()) { announce("The recorded reading starts on play."); return; }
    if (!SPEECH_OK) return;
    if (nar.playing) pauseListening();
    nar.gen++;
    speech.cancel();
    var u = new SpeechSynthesisUtterance(SAMPLE);
    var v = chosenVoice();
    if (v) { u.voice = v; u.lang = v.lang; }
    u.rate = store.get("listen-rate", 1);
    u.pitch = 1;
    // The same beat of daylight after a cancel() that the narration needs.
    setTimeout(function () { speech.speak(u); }, 60);
  }

  function buildPlayer() {
    playBtn = el("button", {
      class: "player-btn player-play", "aria-label": "Pause reading",
      text: "⏸", onclick: function () {
        if (nar.playing) pauseListening(); else resumeListening();
      }
    });

    whereEl = el("strong", { class: "player-where" });
    unitEl = el("span", { class: "player-unit" });
    barEl = el("i");

    var rate = el("select", {
      "aria-label": "Reading speed",
      onchange: function (e) {
        store.set("listen-rate", parseFloat(e.target.value));
        if (usingAudio()) {
          // A recording changes speed where it stands. Browsers time-stretch
          // playbackRate without shifting pitch, so there is no queue to cut
          // and nothing to restart -- the sentence being read keeps going,
          // faster.
          if (aud.el) aud.el.playbackRate = store.get("listen-rate", 1);
          updatePlayer();
          return;
        }
        // The speed decides how long a piece may be as well as how fast it
        // is read, so the queue is cut again before anything is spoken.
        rebuildQueue();
        if (nar.playing) speakFrom(nar.at);   // rate only applies to a new utterance
        else updatePlayer();
      }
    });
    var current = store.get("listen-rate", 1);
    [0.7, 0.85, 1, 1.15, 1.3, 1.5, 1.75, 2].forEach(function (r) {
      rate.appendChild(option(String(r), r + "×", Math.abs(r - current) < 0.001));
    });

    voiceSel = el("select", {
      "aria-label": "Voice",
      onchange: function (e) {
        store.set("listen-voice", e.target.value || null);
        switchEngine(e.target.value === "recorded");
      }
    });
    hintEl = buildHint();
    fillVoices();

    var tryIt = el("button", {
      class: "player-btn player-try", text: "♪",
      "aria-label": "Hear this voice", title: "Hear this voice",
      onclick: function () { previewVoice(); }
    });

    var paceSel = el("select", {
      "aria-label": "Pace",
      title: "How long the silences are. Slower suits verse, where the line " +
             "is the unit and the pause after it is part of it.",
      onchange: function (e) {
        store.set("listen-pace", e.target.value);
        announce(e.target.value === "natural"
          ? "Natural pace" : PACE[e.target.value].label + " pace");
      }
    });
    var nowPace = store.get("listen-pace", "natural");
    ["natural", "measured", "liturgical"].forEach(function (k) {
      paceSel.appendChild(option(k, PACE[k].label, k === nowPace));
    });

    var sleep = el("select", {
      "aria-label": "Sleep timer",
      onchange: function (e) {
        var v = e.target.value;
        nar.stopAtEnd = v === "chapter";
        nar.sleepAt = /^\d+$/.test(v) && +v > 0 ? Date.now() + (+v) * 60000 : 0;
        announce(v === "off" ? "Sleep timer off"
               : v === "chapter" ? "Stopping at the end of this chapter"
               : "Stopping in " + v + " minutes");
      }
    });
    [["off", "Sleep: off"], ["10", "10 min"], ["20", "20 min"], ["30", "30 min"],
     ["45", "45 min"], ["60", "60 min"], ["chapter", "End of chapter"]
    ].forEach(function (o) { sleep.appendChild(option(o[0], o[1], o[0] === "off")); });

    var cont = el("button", {
      class: "player-btn player-cont",
      "aria-pressed": store.get("listen-continue", true) ? "true" : "false",
      title: "Keep going into the next chapter",
      text: "↻",
      "aria-label": "Continue into the next chapter",
      onclick: function (e) {
        var now = !store.get("listen-continue", true);
        store.set("listen-continue", now);
        e.currentTarget.setAttribute("aria-pressed", now ? "true" : "false");
        announce(now ? "Will continue into the next chapter"
                     : "Will stop at the end of this chapter");
      }
    });

    player = el("div", {
      class: "player", role: "region", "aria-label": "Read aloud", hidden: true
    }, [
      el("div", { class: "player-bar" }, [barEl]),
      el("div", { class: "player-line" }, [
        el("button", {
          class: "player-btn", "aria-label": "Back one verse", title: "Back one verse",
          text: "⏮", onclick: function () { jump(-1); }
        }),
        playBtn,
        el("button", {
          class: "player-btn", "aria-label": "Forward one verse", title: "Forward one verse",
          text: "⏭", onclick: function () { jump(1); }
        }),
        el("div", { class: "player-pos" }, [whereEl, unitEl]),
        cont,
        el("button", {
          class: "player-btn player-close", "aria-label": "Stop reading aloud",
          title: "Stop reading aloud", text: "✕",
          onclick: function () { stopListening("Stopped reading aloud"); }
        })
      ]),
      el("div", { class: "player-line player-opts" }, [rate, paceSel, voiceSel, tryIt, sleep]),
      hintEl
    ]);
    document.body.appendChild(player);
  }

  /* The page gives back the inch the player covers, and the player is not
     always the same height: the hint doubles it, and on a narrow phone the
     options wrap. So it is measured rather than guessed at. */
  function sizePlayer() {
    if (!player || player.hidden) return;
    document.documentElement.style.setProperty(
      "--player-h", player.offsetHeight + "px");
  }

  function updatePlayer() {
    if (!player) return;
    player.hidden = !nar.on;
    if (!nar.on) return;
    sizePlayer();

    playBtn.textContent = nar.playing ? "⏸" : "▶";
    playBtn.setAttribute("aria-label", nar.playing ? "Pause reading" : "Continue reading");

    var item = nar.items[nar.at];
    whereEl.textContent = nar.ctx
      ? titleCase(nar.ctx.workTitle) + " · " + nar.ctx.label : "";
    unitEl.textContent = item
      ? itemLabel(item) + " · " + timeLabel(minutesLeft()) : "";
    barEl.style.width = nar.items.length
      ? Math.round((nar.at / nar.items.length) * 100) + "%" : "0";
  }

  function syncListenButtons() {
    document.querySelectorAll("[data-listen]").forEach(function (b) {
      if (b.disabled) return;
      var live = nar.on && nar.playing;
      b.setAttribute("aria-pressed", live ? "true" : "false");
      b.textContent = live ? "⏸ Listening" : "▶ Listen";
    });
  }

  /* The volume's whole argument is that these works are a sequence, so the
     narration follows it: the end of a work runs on into the one that was
     written next, skipping the entries that carry no text of their own. */
  function nextWorkAfter(manifest, workId) {
    var flat = [];
    manifest.sections.forEach(function (sec) {
      sec.works.forEach(function (w) { flat.push(w); });
    });
    var i = -1;
    flat.forEach(function (w, n) { if (i < 0 && w.id === workId) i = n; });
    if (i < 0) return null;
    for (var j = i + 1; j < flat.length; j++) {
      if (flat[j].chapters) return { id: flat[j].id, title: flat[j].title };
    }
    return null;
  }

  /* Called by the reader once a chapter is on the page.

     A device with no speech engine at all used to get no player. It can now
     get the recorded one, which is the case the whole feature is for -- so
     the gate is "some voice is possible", not "this browser can speak". */
  function attachListening(ctx, passages, controls) {
    if ((!SPEECH_OK && !AUDIO_OK) || !passages.length) return;

    nar.passages = passages;
    nar.engine = "device";
    nar.items = SPEECH_OK
      ? buildItems(passages, maxChars(store.get("listen-rate", 1)))
      : [];
    nar.ctx = ctx;
    if (!player) buildPlayer();

    /* Whether this chapter has a reading is a question for the network, so
       the answer arrives after the button does. It only ever swaps the queue
       out from under a chapter that has not started, and a chapter already
       playing on the device engine is left alone. */
    if (audioWanted()) {
      loadAudioIndex(ctx, function (index) {
        if (nar.ctx !== ctx) return;
        var items = index ? buildAudioItems(passages, index) : [];
        if (!items.length) {
          /* Nothing to read with. A device that has no engine of its own was
             relying on this, so it has to be told rather than left with a
             button that does nothing when pressed. */
          if (!SPEECH_OK) {
            listenUnavailable(
              "There is no recording of this chapter, and this device has no " +
              "speech voice of its own to read it with.");
          }
          return;
        }
        if (nar.on && nar.playing) return;
        nar.engine = "recorded";
        nar.items = items;
        if (player) fillVoices();
        updatePlayer();
      });
    }

    var btn = el("button", {
      class: "chip", "data-listen": "1", "aria-pressed": "false",
      text: "▶ Listen",
      title: "Read this chapter aloud with a voice from your device",
      onclick: function () {
        if (nar.on && nar.playing) { pauseListening(); return; }
        if (nar.on && !nar.playing) { resumeListening(); return; }
        startHere(0, true);
      }
    });
    controls.insertBefore(btn, controls.firstChild);
    if (nar.blocked) { markUnavailable(btn); return; }

    var pending = nar.resumeChapter === ctx.work + "/" + ctx.chapter;
    nar.resumeChapter = null;
    if (pending) { startHere(0, false); return; }

    // Opening the chapter you stopped listening in offers that spot back,
    // the same way Resume does for reading.
    var last = store.get("listen-at", null);
    if (last && last.work === ctx.work && last.chapter === ctx.chapter &&
        last.at > 0 && last.at < nar.items.length) {
      nar.pendingResumeAt = last.at;
      btn.textContent = "▶ Resume listening";
      btn.title = "Pick up at " + itemLabel(nar.items[last.at]).toLowerCase();
    }
  }

  function startHere(index, announceIt) {
    if ((!SPEECH_OK && !usingAudio()) || !nar.items.length) return;
    if (index === 0 && nar.pendingResumeAt) {
      index = nar.pendingResumeAt;
      nar.pendingResumeAt = 0;
    }
    nar.on = true;
    if (player) { player.hidden = false; sizePlayer(); }
    document.body.classList.add("listening");
    speakFrom(index);
    syncListenButtons();
    if (announceIt) {
      announce("Reading aloud from " + itemLabel(nar.items[nar.at]).toLowerCase());
    }
  }

  /* Start at a particular verse — used by the verse menu. */
  function listenFromVerse(v) {
    var found = -1;
    nar.items.forEach(function (it, i) {
      if (found < 0 && it.verse === v) found = i;
    });
    if (found < 0) return;
    nar.pendingResumeAt = 0;
    startHere(found, true);
  }

  /* The reader reached a work it has no text for while the narration was on
     its way into it. Say so rather than going quiet with the player up. */
  function listeningDeadEnd() {
    if (!nar.on || !nar.resumeChapter) return;
    stopListening("Listening stopped — there is no text here to read.");
  }

  /* A route change that is not the auto-advance ends the narration: the
     queue points at elements that are about to be thrown away. */
  function listeningPageChange() {
    // Mid auto-advance the queue is about to be replaced by the next
    // chapter's, so leave it in place until that arrives.
    if (nar.on && nar.resumeChapter) {
      nar.gen++;
      if (SPEECH_OK) speech.cancel();
      clearMarks();
      return;
    }
    if (nar.on) stopListening(null);
    // Every item holds a node from a chapter this route change is discarding.
    nar.items = [];
    nar.ctx = null;
  }

  window.addEventListener("resize", function () { sizePlayer(); });

  window.addEventListener("pagehide", function () {
    // Speech outlives the document in several browsers if left running.
    if (SPEECH_OK) speech.cancel();
  });

  /* ================================================================
     ROUTER
     ================================================================ */

  function setNav(route) {
    document.querySelectorAll(".nav a").forEach(function (a) {
      a.removeAttribute("aria-current");
      if (a.getAttribute("data-route") === route) a.setAttribute("aria-current", "page");
    });
  }

  /* ---------------- the bar gets out of the way ----------------
     On a phone the bar carries the wordmark, the tools and two rows of
     links: a sixth of the screen, held there permanently by position:
     sticky, in front of a page whose entire purpose is the text below it.
     So it leaves as you read down and returns as soon as you turn back up
     -- one gesture, no button, and it is always there at the top of a page.
     Wide screens have the room and keep it in place. */

  var topbar = document.querySelector(".topbar");
  var lastY = window.pageYOffset, tucked = false;

  function phone() {
    return window.matchMedia && window.matchMedia("(max-width: 620px)").matches;
  }

  function tuck(on) {
    if (on === tucked) return;
    tucked = on;
    topbar.classList.toggle("tucked", on);
  }

  function onScroll() {
    var y = Math.max(0, window.pageYOffset);
    if (!phone()) { tuck(false); lastY = y; return; }
    // Ignore the small jitter of a finger resting on a scrolling page, and
    // never hide the bar while the top of the page is still in view.
    if (Math.abs(y - lastY) < 8) return;
    tuck(y > lastY && y > 120);
    lastY = y;
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", function () { if (!phone()) tuck(false); });
  // Tabbing into a hidden bar would move focus to something off-screen.
  topbar.addEventListener("focusin", function () { tuck(false); });

  function route() {
    var hash = location.hash.replace(/^#\/?/, "");
    var parts = hash.split("/").filter(function (p) { return p !== ""; });
    var view = parts[0] || "home";

    // Overlays hang off document.body, so they outlive a route change unless
    // closed here. Otherwise a definition opened in Amos follows you to the
    // saved page and sits there.
    closeSheet();
    closeMenu();
    listeningPageChange();
    /* Same reason as the two above: the reading page registers a media-query
       listener to keep the apparatus on the right side of the chapter, and a
       route change replaces the nodes it was holding. Left attached, every
       chapter read in a session would add one more listener rearranging a
       page that is no longer there. */
    forgetApparatus();

    tuck(false);
    lastY = 0;

    main.innerHTML = "";
    main.appendChild(el("p", { class: "loading", text: "Loading…" }));

    getJSON("manifest.json").then(function (manifest) {
      MANIFEST = manifest;
      var node;
      if (view === "read") {
        // Set by viewRead once the chapter is loaded: the title is the
        // chapter, and until the work file arrives nothing here knows it.
        setNav("");
        node = viewRead(manifest, parts[1], parseInt(parts[2] || "0", 10), parts[3]);
        main.innerHTML = "";
        main.appendChild(node);
        window.scrollTo(0, 0);
        return;
      }
      if (view === "search") {
        setNav("search");
        /* Split again without dropping the empty segments, because a scope
           with no query is a real address -- "every verse in the Gospels,
           tell me which word" is what the collection page's own search link
           means -- and it is written "#/search//in:gospels". The filter
           above would hand that back as the query "in:gospels", which is a
           word search for a string that is in no text. */
        var raw = hash.split("/");
        var q = raw[1] ? decodeURIComponent(raw[1]) : "";
        var scope = raw[2] ? decodeURIComponent(raw[2]) : "";
        setTitle(q ? "Search: " + q : "Search");
        node = viewSearch(manifest, q, scope);
        main.innerHTML = "";
        main.appendChild(node);
        return;
      }
      /* Needs canon.json for the same reason the contents do: half the
         collections it can show are divisions read off that file. */
      if (view === "collection") {
        setNav("contents");
        return getJSON("canon.json").catch(function () { return null; })
          .then(function (canon) {
            var node = viewCollection(manifest, canon, parts[1] || "");
            var h1 = node.querySelector("h1");
            setTitle(h1 ? h1.textContent : "Collection");
            main.innerHTML = "";
            main.appendChild(node);
            window.scrollTo(0, 0);
          });
      }
      if (view === "canons" || view === "contents") {
        setNav(view);
        setTitle(view === "canons" ? "Canons" : "Contents");
        return getJSON("canon.json").then(function (canon) {
          main.innerHTML = "";
          main.appendChild(view === "canons"
            ? viewCanons(manifest, canon)
            : viewContents(manifest, canon));
          window.scrollTo(0, 0);
        });
      }
      if (view === "threads" || view === "thread") {
        setNav("threads");
        setTitle("Threads");
        return getJSON("threads.json").then(function (threads) {
          if (view === "thread") {
            var one = threads.filter(function (x) { return x.id === parts[1]; })[0];
            setTitle(one ? one.title : "No such thread");
          }
          main.innerHTML = "";
          main.appendChild(view === "thread"
            ? viewThread(threads, parts[1])
            : viewThreads(threads));
          window.scrollTo(0, 0);
        });
      }
      if (view === "timeline") {
        setNav("timeline");
        setTitle("The timeline");
        main.innerHTML = "";
        main.appendChild(viewTimeline(manifest));
        window.scrollTo(0, 0);
        return;
      }
      if (view === "method") {
        setNav("accuracy");
        setTitle("How the dating was decided");
        main.innerHTML = "";
        main.appendChild(viewMethod(manifest));
        window.scrollTo(0, 0);
        return;
      }
      if (view === "saved") {
        setNav("saved");
        setTitle("Saved");
        main.innerHTML = "";
        main.appendChild(viewSaved());
        window.scrollTo(0, 0);
        return;
      }
      if (view === "accuracy") {
        setNav("accuracy");
        setTitle("Accuracy report");
        return Promise.all([getJSON("findings.json"), getJSON("removals.json"),
                            getJSON("splices.json").catch(function () { return []; })])
          .then(function (r) {
            main.innerHTML = "";
            main.appendChild(viewAccuracy(r[0], r[1], r[2]));
            window.scrollTo(0, 0);
          });
      }
      /* Nothing in the bar to mark: the front page's link in it is the
         wordmark on the left, which is where a reader looks for home and is
         the one link present on all 2,710 static pages too. The nav's
         "Timeline" now goes to the axis, which is what it says. */
      setNav("");
      // The front page, and anything that named no route at all: the full
      // title, which is the description of the whole library.
      setTitle("");
      main.innerHTML = "";
      main.appendChild(viewHome(manifest));
      window.scrollTo(0, 0);
    }).catch(function (e) {
      setTitle("Could not load the library");
      main.innerHTML = "";
      main.appendChild(el("div", { class: "wrap" }, [
        el("h1", { text: "Could not load the library" }),
        el("p", { class: "muted", text: String(e.message) })
      ]));
    });
  }

  window.addEventListener("hashchange", route);

  document.addEventListener("keydown", function (e) {
    if (e.target.matches("input, textarea, select")) return;
    if (e.key === "/") { e.preventDefault(); location.hash = "#/search"; return; }
    if (e.key === "l" || e.key === "L") {
      var listen = document.querySelector("[data-listen]");
      if (listen) { e.preventDefault(); listen.click(); }
      return;
    }
    var pager = document.querySelectorAll(".pager a");
    if (e.key === "ArrowLeft" && pager.length) {
      var prev = Array.prototype.find.call(pager, function (a) { return a.textContent.indexOf("←") === 0; });
      if (prev) location.hash = prev.getAttribute("href");
    }
    if (e.key === "ArrowRight" && pager.length) {
      var next = Array.prototype.find.call(pager, function (a) { return a.textContent.indexOf("→") !== -1; });
      if (next) location.hash = next.getAttribute("href");
    }
  });

  refreshResume();
  initLexicon();
  initLookupKeys();
  route();
})();
