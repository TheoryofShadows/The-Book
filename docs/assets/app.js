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

  /* Screen readers get told about things that happen without a page change:
     saving, copying, search finishing. Without this the app is silent to
     anyone not watching the pixels. */
  var liveRegion = null;
  function announce(message) {
    if (!liveRegion) {
      liveRegion = el("div", {
        class: "sr-only", role: "status",
        "aria-live": "polite", "aria-atomic": "true"
      });
      document.body.appendChild(liveRegion);
    }
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
      var grid = el("div", { class: "thread-cards" });
      threads.forEach(function (t) {
        grid.appendChild(el("a", { class: "thread-card", href: "#/thread/" + t.id }, [
          el("h3", { text: t.title }),
          el("p", { text: t.question }),
          el("span", { class: "thread-meta", text: t.stops.length + " passages" })
        ]));
      });
      box.appendChild(grid);
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
        head.appendChild(jump);
      }

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
      body.appendChild(el("h2", { class: "chapter-title", text: chapter.label }));

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

      // What actually survives, and where you can look at it. Nothing is
      // reproduced -- these objects are all rights reserved -- but linking is
      // always allowed, and the site already rests arguments on them.
      getJSON("manuscripts.json").then(function (ms) {
        var ids = (ms.works || {})[workId];
        if (!ids || !ids.length) return;

        var box = el("details", { class: "witnesses" });
        box.appendChild(el("summary", { text:
          "What survives · " + ids.length +
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
    store.set("saved", list.slice(0, 500));
    announce(wasSaved ? "Removed from saved" : "Saved");
    return !wasSaved;
  }

  function verseId(ref) { return ref.work + "/" + ref.chapter + "/v" + ref.v; }

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

    node.appendChild(el("button", {
      role: "menuitem", text: "🔗  Copy link to this verse",
      onclick: function (e) {
        var url = location.href.split("#")[0] +
                  "#/read/" + ref.work + "/" + ref.chapter + "/v" + ref.v;
        var done = function () {
          e.currentTarget.textContent = "🔗  Link copied";
          announce("Link copied");
        };
        if (navigator.clipboard) navigator.clipboard.writeText(url).then(done, done);
        else done();
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

  function normTerm(s) {
    return s.toLowerCase().replace(/[’']/g, "")
            .replace(/[^a-z0-9 ]+/g, "").trim();
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
  var VIEW = {
    point: 4000, within: 3000, approximate: 25000, region: 400000
  };

  var KIND_LABEL = {
    point: "Identified location",
    within: "Inside a larger city",
    approximate: "Approximate location",
    region: "A region, not a point"
  };

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

    var links = el("div", { class: "place-links" }, [
      el("a", { class: "chip primary", href: earth,
                target: "_blank", rel: "noopener noreferrer",
                text: "🌍  Open in Google Earth" }),
      el("a", { class: "chip", href: maps,
                target: "_blank", rel: "noopener noreferrer", text: "Maps" }),
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
     THREADS -- one question, traced across the collection
     ================================================================ */

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
        el("span", { class: "thread-meta", text:
          t.stops.length + " passages · " +
          t.stops[0].section + " to " + t.stops[t.stops.length - 1].section })
      ]));
    });
    wrap.appendChild(grid);
    return wrap;
  }

  function viewThread(threads, id) {
    var t = threads.filter(function (x) { return x.id === id; })[0];
    if (!t) return el("div", { class: "wrap" },
                      [el("p", { class: "empty", text: "No such thread." })]);

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
      store.set("saved", merged);
      store.set("bookmarks", []);
    }

    var items = savedItems();
    if (!items.length) {
      wrap.appendChild(el("p", { class: "empty", text:
        "Nothing saved yet. Tap any verse number to save that verse, or use " +
        "Save at the top of a chapter to keep the whole thing. Everything is " +
        "stored in this browser only — nothing is sent anywhere, and nobody " +
        "else can see it." }));
      return wrap;
    }

    var verses = items.filter(function (i) { return i.kind === "verse"; });
    wrap.appendChild(el("p", { class: "muted", text:
      items.length + (items.length === 1 ? " item" : " items") + ", " +
      verses.length + " of them individual verses. Most recent first, stored " +
      "in this browser only." }));

    var tools = el("div", { class: "toolbar" }, [
      el("button", {
        class: "chip", text: "Copy all as text",
        onclick: function (e) {
          var text = items.map(function (i) {
            var ref = titleCase(i.workTitle || i.work) + " " + i.label +
                      (i.v ? ":" + i.v : "");
            return i.t ? "“" + i.t + "”\n— " + ref +
                         (i.note ? "\nNote: " + i.note : "") : ref;
          }).join("\n\n");
          var done = function () {
            e.currentTarget.textContent = "Copied";
            announce("All saved items copied");
          };
          if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, done);
          else done();
        }
      })
    ]);
    wrap.appendChild(tools);

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
        store.set("saved", all);
        announce("Note saved");
      });
      row.appendChild(note);

      row.appendChild(el("button", {
        class: "chip", text: "Remove",
        "aria-label": "Remove " + (item.workTitle || item.work) + " " + item.label,
        onclick: function () {
          store.set("saved", savedItems().filter(function (s) {
            return s.id !== item.id;
          }));
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

    // Overlays hang off document.body, so they outlive a route change unless
    // closed here. Otherwise a definition opened in Amos follows you to the
    // saved page and sits there.
    closeSheet();
    closeMenu();

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
      if (view === "threads" || view === "thread") {
        setNav("threads");
        return getJSON("threads.json").then(function (threads) {
          main.innerHTML = "";
          main.appendChild(view === "thread"
            ? viewThread(threads, parts[1])
            : viewThreads(threads));
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
  initLexicon();
  initLookupKeys();
  route();
})();
