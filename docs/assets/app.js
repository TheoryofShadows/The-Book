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

  var store = {
    get: function (k, d) {
      try { var v = localStorage.getItem("thebook:" + k); return v === null ? d : JSON.parse(v); }
      catch (e) { return d; }
    },
    set: function (k, v) {
      try { localStorage.setItem("thebook:" + k, JSON.stringify(v)); } catch (e) {}
    }
  };

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

  function viewHome(manifest) {
    var t = manifest.totals;
    var wrap = el("div", { class: "wrap" });

    wrap.appendChild(el("section", { class: "hero" }, [
      el("h1", { text: "Every text, in the order it was written." }),
      el("p", {
        class: "lede",
        text: "The Jewish, Protestant, Catholic, Eastern Orthodox and Ethiopian " +
              "canons complete, together with the pseudepigrapha, the New Testament " +
              "apocrypha and the Apostolic Fathers — arranged not by where tradition " +
              "filed them, but by when scholars believe they were composed. " +
              "It opens with a war poem, not with Genesis."
      })
    ]));

    var stats = el("div", { class: "stats" });
    [[t.works, "works"], [t.chapters, "chapters"], [t.verses, "numbered verses"],
     [t.words, "words"], [10, "eras, before the collections"]]
      .forEach(function (p) {
        stats.appendChild(el("div", { class: "stat" }, [
          el("b", { text: fmt(p[0]) }), el("span", { text: p[1] })
        ]));
      });
    wrap.appendChild(stats);

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
        "missing from the public-domain sources." })
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
          el("th", { text: "Dated" }), el("th", { text: "Chapters" }),
          el("th", { text: "Words" })
        ])]));
        var tb = el("tbody");
        manifest.sections.forEach(function (s) {
          s.works.forEach(function (w) {
            tb.appendChild(el("tr", {}, [
              el("td", { class: "muted", text: s.roman || "—" }),
              el("td", {}, [el("a", { href: "#/read/" + w.id + "/0", text: titleCase(w.title) })]),
              el("td", { class: "muted", text: s.dates || "—" }),
              el("td", { text: w.chapters || "—" }),
              el("td", { text: w.words ? fmt(w.words) : "—" })
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
      body.appendChild(el("div", { class: "scroller" }, [table]));
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
    if (!meta) return el("div", { class: "wrap" }, [el("p", { class: "empty", text: "No such work." })]);

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
    wrap.appendChild(head);

    var body = el("div");
    wrap.appendChild(body);
    body.appendChild(el("p", { class: "loading", text: "Loading…" }));

    getJSON("works/" + workId + ".json").then(function (work) {
      body.innerHTML = "";

      if (meta.note && meta.note.length) {
        var nb = el("div", { class: "note-block" });
        meta.note.forEach(function (p) { nb.appendChild(el("p", { text: p })); });
        body.appendChild(nb);
      }

      if (meta.positions) {
        body.appendChild(positionsPanel(meta.positions));
      }

      if (!work.chapters.length) {
        body.appendChild(el("p", {
          class: "empty",
          text: "This work is described in the volume but no text was available " +
                "from a public-domain source. See the accuracy report for why."
        }));
        return;
      }

      var idx = Math.max(0, Math.min(chapterIdx | 0, work.chapters.length - 1));
      var chapter = work.chapters[idx];

      store.set("last", { work: workId, chapter: idx, title: meta.title });
      refreshResume();

      if (work.chapters.length > 1) {
        var strip = el("div", { class: "chapter-strip" });
        work.chapters.forEach(function (c, i) {
          strip.appendChild(el("a", {
            href: "#/read/" + workId + "/" + i,
            "aria-current": i === idx ? "true" : null,
            title: c.label,
            text: c.n === null || c.n === undefined
              ? c.label.replace(/^.*?(\d+).*$/, "$1") || "·"
              : String(c.n)
          }));
        });
        head.appendChild(strip);
      }

      var perLine = store.get("verse-per-line", false);
      var size = store.get("reader-size", 1.075);
      var reader = el("div", { class: "reader" + (perLine ? " verse-per-line" : "") });
      document.documentElement.style.setProperty("--reader-size", size + "rem");

      var marks = store.get("bookmarks", []);
      var here = workId + "/" + idx;
      var marked = marks.some(function (m) { return m.at === here; });

      var controls = el("div", { class: "reader-controls" }, [
        el("button", {
          class: "chip", "aria-pressed": marked ? "true" : "false",
          text: marked ? "★ Saved" : "☆ Save",
          title: "Keep this chapter in your saved list",
          onclick: function (e) {
            marks = store.get("bookmarks", []).filter(function (m) { return m.at !== here; });
            if (!marked) {
              marks.unshift({ at: here, work: meta.title, label: chapter.label });
              marks = marks.slice(0, 200);
            }
            marked = !marked;
            store.set("bookmarks", marks);
            e.currentTarget.textContent = marked ? "★ Saved" : "☆ Save";
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
      body.appendChild(el("h2", { class: "chapter-title", text: chapter.label }));

      if (chapter.verses && chapter.verses.length) {
        var p = el("p");
        chapter.verses.forEach(function (v) {
          var span = el("span", { class: "v", id: "v" + v.v });
          span.appendChild(el("a", {
            class: "vnum",
            href: "#/read/" + workId + "/" + idx + "/v" + v.v,
            text: String(v.v),
            title: "Link to verse " + v.v
          }));
          span.appendChild(document.createTextNode(v.t + " "));
          p.appendChild(span);
        });
        reader.appendChild(p);
      } else {
        (chapter.paras || []).forEach(function (t) {
          reader.appendChild(el("p", { text: t }));
        });
      }
      body.appendChild(reader);

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

    var grid = el("div", { class: "positions-body" }, [
      el("div", { class: "stance" }, [
        el("h4", { text: "Traditional view" }),
        el("p", { class: "claim", text: p.trad }),
        el("p", { class: "why", text: p.tradWhy })
      ]),
      el("div", { class: "stance" }, [
        el("h4", { text: "Critical view" }),
        el("p", { class: "claim", text: p.crit }),
        el("p", { class: "why", text: p.critWhy })
      ])
    ]);

    grid.appendChild(el("p", { class: "positions-foot", html:
      "This volume is <em>arranged</em> by the critical dating, which is an " +
      "editorial decision about order, not a verdict on which column is right. " +
      "Both positions are held by serious people for the reasons given." }));

    wrap.appendChild(head);
    wrap.appendChild(grid);
    return wrap;
  }

  /* ================================================================
     SEARCH
     ================================================================ */

  var TOKEN = /[a-z0-9]+/g;
  function tokenise(s) {
    return (s.toLowerCase().replace(/[’‘]/g, "'").match(TOKEN) || []);
  }

  function viewSearch(manifest, initialQuery) {
    var wrap = el("div", { class: "wrap" });
    wrap.appendChild(el("h1", { text: "Search" }));
    wrap.appendChild(el("p", {
      class: "lede",
      text: "Every word of every text, including the deuterocanon, 1 Enoch, " +
            "Jubilees and the Apostolic Fathers. Wrap a phrase in quotes to " +
            "match it exactly."
    }));

    var input = el("input", {
      type: "search", placeholder: '"a still small voice", or: watchers heaven',
      value: initialQuery || "", autocomplete: "off", spellcheck: "false"
    });
    wrap.appendChild(el("div", { class: "toolbar" }, [input]));

    var chips = el("div", { class: "chips" });
    ["\"living creatures\"", "watchers", "\"son of man\"", "jubilee", "resurrection", "wisdom"]
      .forEach(function (q) {
        chips.appendChild(el("a", {
          class: "chip", href: "#/search/" + encodeURIComponent(q), text: q.replace(/"/g, "")
        }));
      });
    wrap.appendChild(chips);

    var status = el("div", { class: "muted" });
    var bar = el("div", { class: "progress" }, [el("i")]);
    var results = el("div", { class: "results" });
    wrap.appendChild(status);
    wrap.appendChild(bar);
    wrap.appendChild(results);

    var runId = 0;

    function run(query) {
      var mine = ++runId;
      results.innerHTML = "";
      bar.firstChild.style.width = "0%";

      var phrase = null;
      var m = query.match(/^\s*"(.+)"\s*$/);
      if (m) phrase = m[1].toLowerCase().replace(/\s+/g, " ").trim();

      var terms = tokenise(phrase || query);
      if (!terms.length) { status.textContent = ""; return; }

      status.textContent = "Looking up terms…";

      getJSON("chapters.json").then(function (tbl) {
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
      }).then(function (ctx) {
        if (mine !== runId) return;
        var tbl = ctx.tbl, lookup = ctx.lookup;

        // Narrow to candidate chapters using the selective terms only.
        var candidate = null;
        var unknown = [];
        terms.forEach(function (t) {
          var k = /^[a-z]/.test(t) ? t[0] : "0";
          var post = lookup[k] ? lookup[k][t] : undefined;
          if (post === undefined) { unknown.push(t); return; }
          if (post === 0) return;                 // too common to narrow with
          var set = {};
          post.forEach(function (c) { set[c] = 1; });
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
        status.textContent = "Scanning " + fmt(ids.length) + " chapters in " +
                             workIds.length + " works…";

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
            status.textContent = found
              ? fmt(found) + (found >= LIMIT ? "+ matches (showing the first " + LIMIT + ")" : " matches")
              : "No verse matched.";
            return;
          }
          var wid = workIds[i];
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
                var low = u.t.toLowerCase();
                var ok = phrase
                  ? low.replace(/\s+/g, " ").indexOf(phrase) !== -1
                  : terms.every(function (t) { return new RegExp("\\b" + t, "i").test(low); });
                if (!ok) return;
                found++;
                results.appendChild(resultRow(tbl, pair[0], wid, pair[1], u, phrase, terms));
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

    function resultRow(tbl, cid, wid, chIdx, unit, phrase, terms) {
      var row = tbl.chapters[cid];
      var href = "#/read/" + wid + "/" + chIdx + (unit.ref ? "/v" + unit.ref : "");
      var label = titleCase(row[3]) + " · " + row[2] + (unit.ref ? ":" + unit.ref : "");

      var html = esc(unit.t);
      if (phrase) {
        html = html.replace(new RegExp("(" + phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi"),
                            "<mark>$1</mark>");
      } else {
        terms.forEach(function (t) {
          html = html.replace(new RegExp("(\\b" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\w*)", "gi"),
                              "<mark>$1</mark>");
        });
      }
      if (html.length > 420) {
        var at = html.indexOf("<mark>");
        var from = Math.max(0, at - 160);
        html = (from ? "… " : "") + html.slice(from, from + 420) + " …";
      }

      return el("div", { class: "result" }, [
        el("div", { class: "result-ref" }, [
          el("a", { href: href, text: label })
        ]),
        el("div", { class: "result-text", html: html })
      ]);
    }

    var timer;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      var q = input.value;
      timer = setTimeout(function () {
        var target = "#/search" + (q.trim() ? "/" + encodeURIComponent(q) : "");
        if (location.hash !== target) history.replaceState(null, "", target);
        run(q);
      }, 220);
    });

    setTimeout(function () { input.focus(); }, 30);
    if (initialQuery) run(initialQuery);

    return wrap;
  }

  /* ================================================================
     CANONS
     ================================================================ */

  var CANON_LABEL = {
    tanakh: "Jewish", protestant: "Protestant", catholic: "Catholic",
    orthodox: "E. Orthodox", ethiopian: "Ethiopian"
  };

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
        } else {
          b.works.forEach(function (id, i) {
            if (i) link.appendChild(document.createTextNode(" · "));
            link.appendChild(el("a", { href: "#/read/" + id + "/0", text: i === 0 && b.works.length === 1 ? "read" : String(i + 1) }));
          });
        }

        tb.appendChild(el("tr", {}, [
          el("td", {}, [
            el("strong", { text: b.name }),
            b.foldedInto ? el("div", { class: "tiny", text: "counted inside " + b.foldedInto }) : null
          ])
        ].concat(canon.canons.map(function (c) {
          return cell(b.canons[c]);
        })).concat([
          el("td", { class: "muted", text: eras.length ? eras.join(", ") : "—" }),
          link
        ])));
      });
      table.appendChild(tb);
      tableBox.appendChild(el("div", { class: "scroller" }, [table]));
      tableBox.appendChild(el("p", { class: "tiny", text:
        "● received as scripture   ◐ printed but outside the canon, or received in some branches only   · absent" }));
    }

    render();
    return wrap;
  }

  /* ================================================================
     ACCURACY
     ================================================================ */

  function viewAccuracy(findings, removals) {
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
          el("h4", {}, [
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
    wrap.appendChild(el("div", { class: "scroller" }, [table]));

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
     SAVED
     ================================================================ */

  function viewSaved() {
    var wrap = el("div", { class: "wrap" });
    wrap.appendChild(el("h1", { text: "Saved" }));

    var marks = store.get("bookmarks", []);
    if (!marks.length) {
      wrap.appendChild(el("p", { class: "empty", text:
        "Nothing saved yet. The ☆ Save button at the top of any chapter keeps " +
        "it here. Saved chapters live in this browser only — nothing is sent " +
        "anywhere." }));
      return wrap;
    }

    wrap.appendChild(el("p", { class: "muted", text:
      marks.length + (marks.length === 1 ? " chapter" : " chapters") +
      ", most recent first. Stored in this browser only." }));

    var list = el("div", { class: "results" });
    marks.forEach(function (m) {
      var row = el("div", { class: "result" }, [
        el("div", { class: "result-ref" }, [
          el("a", { href: "#/read/" + m.at, text: titleCase(m.work) + " · " + m.label })
        ])
      ]);
      row.appendChild(el("button", {
        class: "chip", text: "Remove",
        onclick: function () {
          store.set("bookmarks", store.get("bookmarks", []).filter(function (x) {
            return x.at !== m.at;
          }));
          row.remove();
        }
      }));
      list.appendChild(row);
    });
    wrap.appendChild(list);
    return wrap;
  }

  /* ================================================================
     ROUTER
     ================================================================ */

  function setNav(route) {
    document.querySelectorAll(".nav a").forEach(function (a) {
      a.removeAttribute("aria-current");
      if (a.getAttribute("data-route") === route) a.setAttribute("aria-current", "page");
    });
  }

  function route() {
    var hash = location.hash.replace(/^#\/?/, "");
    var parts = hash.split("/").filter(function (p) { return p !== ""; });
    var view = parts[0] || "home";

    main.innerHTML = "";
    main.appendChild(el("p", { class: "loading", text: "Loading…" }));

    getJSON("manifest.json").then(function (manifest) {
      var node;
      if (view === "read") {
        setNav("");
        node = viewRead(manifest, parts[1], parseInt(parts[2] || "0", 10), parts[3]);
        main.innerHTML = "";
        main.appendChild(node);
        window.scrollTo(0, 0);
        return;
      }
      if (view === "search") {
        setNav("search");
        node = viewSearch(manifest, parts[1] ? decodeURIComponent(parts[1]) : "");
        main.innerHTML = "";
        main.appendChild(node);
        return;
      }
      if (view === "canons" || view === "contents") {
        setNav(view);
        return getJSON("canon.json").then(function (canon) {
          main.innerHTML = "";
          main.appendChild(view === "canons"
            ? viewCanons(manifest, canon)
            : viewContents(manifest, canon));
          window.scrollTo(0, 0);
        });
      }
      if (view === "saved") {
        setNav("saved");
        main.innerHTML = "";
        main.appendChild(viewSaved());
        window.scrollTo(0, 0);
        return;
      }
      if (view === "accuracy") {
        setNav("accuracy");
        return Promise.all([getJSON("findings.json"), getJSON("removals.json")])
          .then(function (r) {
            main.innerHTML = "";
            main.appendChild(viewAccuracy(r[0], r[1]));
            window.scrollTo(0, 0);
          });
      }
      setNav("home");
      main.innerHTML = "";
      main.appendChild(viewHome(manifest));
      window.scrollTo(0, 0);
    }).catch(function (e) {
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
  route();
})();
