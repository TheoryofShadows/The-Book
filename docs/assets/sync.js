/* Optional reader accounts: the browser half.

   Nothing in here runs a network request for somebody who has not signed in.
   The site's data stays in this browser's localStorage exactly as before; this
   file only (a) draws the sign-in page and the one-time "keep my place across
   devices" note, and (b) once a reader has chosen to sign in, keeps their own
   saved verses, notes, diary, reading place and a few settings in step with the
   copy held for them on the server.

   How it stays in step, in one paragraph. Every piece of data is an item with a
   key ("saved:<id>", "diary:<id>", "last", "set:<name>"). When localStorage
   changes, the item that changed is stamped with the time and queued. A sync
   sends the queue and asks for what has changed on the server since the last
   one. For each item the newest stamp wins; a deletion is an item too (it is
   kept as a tombstone so other devices learn of it). The first time a device
   signs in, its existing items are merged in with their own old dates (a saved
   verse keeps the day it was saved), so signing in never discards the local
   copy and a copy already on the server is not overwritten by a stale one. */
(function () {
  "use strict";

  var PFX = "thebook:";
  var ACCOUNT = PFX + "account";
  var META = PFX + "sync";
  var PROMPT = PFX + "account-prompt";
  var SETTINGS = ["theme", "verse-per-line", "reader-size", "listen-rate", "listen-pace",
                  "listen-continue", "contents-mode", "timeline-mode", "mark-canon"];
  var SAVED_CAP = 500, DIARY_CAP = 1000, MAX_VALUE = 32 * 1024, BATCH = 400;

  var realSet = Storage.prototype.setItem;
  var applying = false;
  var active = false;
  var running = false, again = false;
  var timer = null;
  var state = { status: "idle", last: 0, error: "" };

  /* ---------------- small storage helpers ---------------- */

  function rawGet(k) { try { return localStorage.getItem(PFX + k); } catch (e) { return null; } }
  function get(k, d) {
    var v = rawGet(k);
    if (v === null) return d;
    try { return JSON.parse(v); } catch (e) { return d; }
  }
  function put(k, v) {
    applying = true;
    try { realSet.call(localStorage, PFX + k, JSON.stringify(v)); return true; }
    catch (e) { return false; }
    finally { applying = false; }
  }
  function drop(k) {
    applying = true;
    try { localStorage.removeItem(PFX + k); } catch (e) { /* nothing to do */ }
    applying = false;
  }

  function account() { return get("account", null); }
  function loadMeta() {
    var m = get("sync", null);
    if (!m || typeof m !== "object") m = {};
    m.items = m.items || {}; m.snap = m.snap || {}; m.pending = m.pending || {};
    m.cursor = m.cursor || 0; m.seeded = !!m.seeded;
    return m;
  }
  function saveMeta(m) { put("sync", m); }

  /* A short non-cryptographic hash (cyrb53). It only has to notice that a value
     changed; nothing is trusted on the strength of it. */
  function hash(str) {
    var h1 = 0xdeadbeef, h2 = 0x41c6ce57;
    for (var i = 0; i < str.length; i++) {
      var ch = str.charCodeAt(i);
      h1 = Math.imul(h1 ^ ch, 2654435761);
      h2 = Math.imul(h2 ^ ch, 1597334677);
    }
    h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
    h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
    return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(36) + "." + str.length;
  }

  /* ---------------- local data as items ---------------- */

  var KEY_OK = /^(?:last|saved:[^\s]{1,160}|diary:[^\s]{1,160}|set:[a-z0-9-]{1,40})$/;

  function currentItems() {
    var out = {}, skipped = 0;
    function add(k, v) {
      var s = JSON.stringify(v);
      if (!KEY_OK.test(k) || s.length > MAX_VALUE) { skipped++; return; }
      out[k] = s;
    }
    var saved = get("saved", []);
    if (Array.isArray(saved)) saved.forEach(function (s) {
      if (s && typeof s.id === "string") add("saved:" + s.id, s);
    });
    var diary = get("diary", null);
    if (!Array.isArray(diary)) diary = get("diary-copy", []);
    if (Array.isArray(diary)) diary.forEach(function (e) {
      if (e && typeof e.id === "string") add("diary:" + e.id, e);
    });
    var last = get("last", null);
    if (last && typeof last === "object") add("last", last);
    SETTINGS.forEach(function (name) {
      var v = get(name, undefined);
      if (v !== undefined) add("set:" + name, v);
    });
    out.__skipped = skipped;
    return out;
  }

  /* What date an item that has never been synced is given. */
  function seedTime(k, value) {
    try {
      var o = JSON.parse(value);
      if (k.indexOf("saved:") === 0 && o && o.at) return Math.max(1, +o.at || 1);
      if (k.indexOf("diary:") === 0 && o && o.id) return Math.max(1, Date.parse(o.id) || 1);
    } catch (e) { /* fall through */ }
    return 1;
  }

  function scan(m) {
    var cur = currentItems(), t = Date.now(), n = 0;
    state.skipped = cur.__skipped; delete cur.__skipped;
    Object.keys(cur).forEach(function (k) {
      var h = hash(cur[k]);
      if (m.snap[k] === h) return;
      m.snap[k] = h;
      m.items[k] = { t: m.seeded ? t : seedTime(k, cur[k]), d: 0 };
      m.pending[k] = 1; n++;
    });
    Object.keys(m.snap).forEach(function (k) {
      if (k in cur) return;
      if (k.indexOf("saved:") !== 0 && k.indexOf("diary:") !== 0) return; // settings and place are never deleted
      delete m.snap[k];
      m.items[k] = { t: t, d: 1 };
      m.pending[k] = 1; n++;
    });
    return n;
  }

  /* Write what arrived from the server into the same keys the reader uses. */
  function applyRemote(m, items) {
    var saved = null, diary = null, n = 0;
    function savedList() { if (!saved) saved = (get("saved", []) || []).slice(); return saved; }
    function diaryList() {
      if (!diary) {
        var d = get("diary", null);
        diary = (Array.isArray(d) ? d : (get("diary-copy", []) || [])).slice();
      }
      return diary;
    }
    var writes = {};
    items.forEach(function (r) {
      var mine = m.items[r.k];
      if (mine && r.t <= mine.t) return;
      var value = null;
      if (!r.d) { try { value = JSON.parse(r.v); } catch (e) { return; } }
      var id;
      if (r.k.indexOf("saved:") === 0) {
        id = r.k.slice(6);
        savedList(); saved = saved.filter(function (s) { return s && s.id !== id; });
        if (!r.d) saved.push(value);
      } else if (r.k.indexOf("diary:") === 0) {
        id = r.k.slice(6);
        diaryList(); diary = diary.filter(function (e) { return e && e.id !== id; });
        if (!r.d) diary.push(value);
      } else if (r.k === "last") {
        if (!r.d) writes.last = value;
      } else if (r.k.indexOf("set:") === 0) {
        if (!r.d) writes[r.k.slice(4)] = value;
      } else { return; }
      m.items[r.k] = { t: r.t, d: r.d ? 1 : 0 };
      if (r.d) delete m.snap[r.k]; else m.snap[r.k] = hash(JSON.stringify(value));
      delete m.pending[r.k];
      n++;
    });
    if (!n) return 0;
    if (saved) {
      saved.sort(function (a, b) { return (b.at || 0) - (a.at || 0); });
      writes.saved = saved.slice(0, SAVED_CAP);
    }
    if (diary) {
      diary.sort(function (a, b) { return a.id < b.id ? 1 : -1; });
      writes.diary = diary.slice(0, DIARY_CAP);
      writes["diary-copy"] = writes.diary;
    }
    var ok = true;
    Object.keys(writes).forEach(function (k) { if (!put(k, writes[k])) ok = false; });
    if (!ok) { state.error = "This browser would not store everything that arrived."; }
    return n;
  }

  /* ---------------- talking to the server ---------------- */

  function api(method, path, body) {
    var opts = { method: method, credentials: "same-origin", headers: {} };
    if (body !== undefined) {
      opts.headers["content-type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(path, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        return { status: r.status, ok: r.ok, json: j };
      });
    });
  }

  function emit(name, detail) {
    try { window.dispatchEvent(new CustomEvent(name, { detail: detail || {} })); } catch (e) { /* old browser */ }
  }

  function localSignOut() {
    active = false;
    drop("account"); drop("sync");
    state.status = "idle";
    emit("thebook:account", { signedIn: false });
  }

  function sync() {
    if (!active) return Promise.resolve();
    if (running) { again = true; return Promise.resolve(); }
    running = true; again = false;
    state.status = "syncing"; state.error = "";
    var m = loadMeta();
    scan(m); saveMeta(m);
    var keys = Object.keys(m.pending).slice(0, BATCH);
    var sentT = {}, cur = currentItems();
    var changes = keys.map(function (k) {
      var it = m.items[k] || { t: Date.now(), d: 0 };
      sentT[k] = it.t;
      var c = { k: k, t: it.t, d: it.d ? 1 : 0 };
      if (!it.d) c.v = cur[k];
      return c;
    }).filter(function (c) { return c.d || typeof c.v === "string"; });
    return api("POST", "/api/sync", { since: m.cursor, changes: changes }).then(function (res) {
      if (res.status === 401) { localSignOut(); state.error = "signed_out"; emit("thebook:synced", { signedOut: true }); return; }
      if (!res.ok) { state.status = "error"; state.error = res.json.error || ("http " + res.status); return; }
      var m2 = loadMeta();
      keys.forEach(function (k) {
        if (m2.items[k] && m2.items[k].t === sentT[k]) delete m2.pending[k];
        else if (!m2.items[k]) delete m2.pending[k];
      });
      var n = applyRemote(m2, res.json.items || []);
      m2.cursor = res.json.now || m2.cursor;
      m2.seeded = true;
      saveMeta(m2);
      state.status = state.error ? "error" : "idle";
      state.last = Date.now();
      if (n) emit("thebook:synced", { changed: n });
      else emit("thebook:synced", { changed: 0 });
      if (Object.keys(m2.pending).length) again = true;
    }).catch(function () {
      state.status = "offline"; state.error = "offline";
    }).then(function () {
      running = false;
      if (again && state.status !== "offline") return sync();
    });
  }

  function schedule(ms) {
    if (!active) return;
    clearTimeout(timer);
    timer = setTimeout(sync, ms);
  }

  /* Watch the reader's own writes. A no-op unless signed in. */
  Storage.prototype.setItem = function (k) {
    var r = realSet.apply(this, arguments);
    if (active && !applying && typeof k === "string" && k.indexOf(PFX) === 0) {
      var base = k.slice(PFX.length);
      if (base === "saved" || base === "diary" || base === "last" || SETTINGS.indexOf(base) >= 0) schedule(2500);
    }
    return r;
  };

  document.addEventListener("visibilitychange", function () {
    if (!active) return;
    if (document.visibilityState === "hidden") sync();
    else if (Date.now() - state.last > 60000) sync();
  });
  window.addEventListener("online", function () { schedule(500); });

  /* ---------------- sign-in page ---------------- */

  var helpers = null;
  function H() { return helpers; }

  function fmtTime(ms) { try { return new Date(ms).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }); } catch (e) { return ""; } }

  function say(msg) { if (helpers && helpers.announce) helpers.announce(msg); }

  function saveFile(name, text) {
    var blob = new Blob([text], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }

  var ERRORS = {
    bad_email: "That does not look like an email address.",
    rate_limited: "Too many sign-in links have been asked for that address or from this connection. Try again in an hour.",
    daily_cap: "The site has sent its limit of sign-in emails for today. Try again tomorrow.",
    email_not_configured: "Sign-in by email is not switched on for this site yet, so nothing was sent. Everything else works as it always has.",
    accounts_not_configured: "Accounts are not switched on for this site yet. Everything else works as it always has.",
    mail_failed: "The email could not be sent just now. Try again in a little while.",
    expired_or_used: "That sign-in link has already been used or has expired. Ask for a new one below."
  };

  function view(h) {
    helpers = h; var el = h.el;
    var wrap = el("div", { class: "wrap account" });
    wrap.appendChild(el("h1", { text: "Account" }));
    var body = el("div", { class: "account-body" });
    wrap.appendChild(body);

    var parts = (location.hash.replace(/^#\/?/, "")).split("/");
    var token = parts[1] === "verify" && parts[2] ? parts[2] : "";
    function show(node) { body.innerHTML = ""; body.appendChild(node); }

    function explain() {
      return el("div", {}, [
        el("p", { text: "You do not need an account. The Book works fully without one, and your saved verses, notes, diary and place are kept in this browser." }),
        el("p", { text: "If you want them on your other devices too, sign in with your email address. We email you a one-time link; there is no password. We then keep a copy of your saved verses, notes, diary entries, reading place and a few settings (theme, text size) so your devices stay in step. Nothing else, and no reading history." }),
        el("p", { class: "muted" }, ["Read exactly what is stored and how to delete it on the ",
          el("a", { href: "/privacy/#accounts", text: "privacy page" }), "."])
      ]);
    }

    function signedOutView(note) {
      var node = el("div", {});
      if (note) node.appendChild(el("p", { class: "warn", role: "status", text: note }));
      node.appendChild(explain());
      var email = el("input", { type: "email", id: "acct-email", name: "email", autocomplete: "email",
        required: "", placeholder: "you@example.com", "aria-label": "Your email address" });
      var trap = el("input", { type: "text", name: "website", tabindex: "-1", autocomplete: "off",
        "aria-hidden": "true", class: "sr-only" });
      var status = el("p", { class: "muted", role: "status", "aria-live": "polite" });
      var btn = el("button", { class: "primary", type: "submit", text: "Email me a sign-in link" });
      var form = el("form", { class: "account-form", novalidate: "" }, [
        el("label", { for: "acct-email", text: "Email address" }), email, trap, btn, status]);
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var v = email.value.trim();
        if (!v) { status.textContent = ERRORS.bad_email; email.focus(); return; }
        btn.disabled = true; status.textContent = "Sending…";
        api("POST", "/api/auth/request", { email: v, website: trap.value }).then(function (r) {
          btn.disabled = false;
          if (!r.ok) { status.textContent = ERRORS[r.json.error] || "That did not work. Try again in a little while."; return; }
          if (r.json.devLink) {
            status.textContent = "";
            status.appendChild(document.createTextNode("Development mode, no email sent: "));
            status.appendChild(el("a", { href: r.json.devLink, text: "open the sign-in link" }));
            return;
          }
          status.textContent = "If that address can receive mail, a sign-in link is on its way. It works once and expires in 15 minutes. You can close this page and open the link on any device.";
          say("Sign-in link sent");
        }).catch(function () { btn.disabled = false; status.textContent = "Could not reach the server. Check your connection."; });
      });
      node.appendChild(form);
      return node;
    }

    function confirmView() {
      var status = el("p", { class: "muted", role: "status", "aria-live": "polite" });
      var btn = el("button", { class: "primary", text: "Sign in on this device" });
      btn.addEventListener("click", function () {
        btn.disabled = true; status.textContent = "Signing in…";
        api("POST", "/api/auth/verify", { token: token }).then(function (r) {
          if (!r.ok) {
            history.replaceState(null, "", "#/account");
            show(signedOutView(ERRORS[r.json.error] || "That link did not work. Ask for a new one below."));
            return;
          }
          put("account", { email: r.json.email });
          var m = {}; put("sync", m);
          active = true;
          history.replaceState(null, "", "#/account");
          show(signedInView("Signed in. Syncing…"));
          say("Signed in");
          sync().then(function () { if (document.getElementById("acct-status")) show(signedInView()); });
        }).catch(function () { btn.disabled = false; status.textContent = "Could not reach the server. Check your connection."; });
      });
      return el("div", {}, [
        el("p", { text: "Open sign-in link detected. Press the button to finish signing in on this device." }),
        el("p", { class: "muted", text: "Your saved verses, notes and diary already on this device will be added to your account, not replaced." }),
        btn, status]);
    }

    function signedInView(note) {
      var acct = account() || {};
      var status = el("p", { id: "acct-status", class: "muted", role: "status", "aria-live": "polite" });
      function setStatus() {
        status.textContent = note ? note :
          state.status === "syncing" ? "Syncing…" :
          state.status === "offline" ? "Offline. Your changes are kept here and will sync when you are back online." :
          state.status === "error" ? "Sync problem: " + (state.error || "unknown") :
          state.last ? "In step with your account as of " + fmtTime(state.last) + "." : "Not synced yet in this visit.";
      }
      setStatus();
      var node = el("div", {}, [
        el("p", {}, ["Signed in as ", el("strong", { text: acct.email || "your account" }), "."]),
        status
      ]);
      var row = el("p", { class: "account-actions" });
      row.appendChild(el("button", { class: "primary", text: "Sync now", onclick: function () {
        note = ""; state.status = "syncing"; setStatus();
        sync().then(function () { setStatus(); say(status.textContent); });
      } }));
      row.appendChild(el("button", { text: "Download my data", onclick: function () {
        fetch("/api/export", { credentials: "same-origin" }).then(function (r) {
          if (!r.ok) throw new Error(r.status);
          return r.text();
        }).then(function (t) { saveFile("the-book-account-data.json", t); say("Downloaded"); })
          .catch(function () { status.textContent = "Could not download just now."; });
      } }));
      row.appendChild(el("button", { text: "Sign out", onclick: function () {
        api("POST", "/api/signout", {}).catch(function () {}).then(function () {
          localSignOut();
          show(signedOutView("Signed out. Your saved verses, notes and diary stay on this device."));
          say("Signed out");
        });
      } }));
      node.appendChild(row);

      var del = el("div", { class: "account-danger" });
      var ask = el("button", { class: "linkish", text: "Delete my account and data…" });
      ask.addEventListener("click", function () {
        del.innerHTML = "";
        var yes = el("button", { class: "warn-btn", text: "Yes, permanently delete everything held for me" });
        var no = el("button", { text: "Keep my account", onclick: function () { show(signedInView()); } });
        del.appendChild(el("p", { class: "warn", role: "alert", text:
          "This removes your email address and every item stored for you on the server, and signs out every device. " +
          "It cannot be undone. Copies already in your browsers stay there; they are yours." }));
        del.appendChild(yes); del.appendChild(no);
        yes.addEventListener("click", function () {
          yes.disabled = true;
          api("POST", "/api/delete", { confirm: "delete" }).then(function (r) {
            if (!r.ok && r.status !== 401) { del.appendChild(el("p", { class: "warn", text: "Could not delete just now. Nothing was changed." })); yes.disabled = false; return; }
            localSignOut();
            show(signedOutView("Your account and everything held for it on the server have been deleted. Your saved verses, notes and diary are still in this browser."));
            say("Account deleted");
          }).catch(function () { yes.disabled = false; del.appendChild(el("p", { class: "warn", text: "Could not reach the server. Nothing was changed." })); });
        });
        yes.focus();
      });
      del.appendChild(ask);
      node.appendChild(del);
      return node;
    }

    if (token) {
      history.replaceState(null, "", location.pathname + location.search + "#/account/verify/" + token);
      show(confirmView());
    } else if (account()) {
      show(signedInView());
      sync().then(function () { if (document.getElementById("acct-status") && account()) show(signedInView()); });
    } else {
      show(el("p", { class: "muted", text: "Checking…" }));
      fetch("/api/health", { credentials: "same-origin" }).then(function (r) { return r.ok ? r.json() : null; })
        .catch(function () { return null; }).then(function (j) {
          if (j && j.accounts && j.mail) return show(signedOutView());
          if (j && !j.accounts) return show(signedOutView(ERRORS.accounts_not_configured));
          if (j) return show(signedOutView(ERRORS.email_not_configured));
          show(el("div", {}, [el("p", { text: "Accounts need the online site, and the server could not be reached. Everything else works as it always has." }), explain()]));
        });
    }
    return wrap;
  }

  /* The note on the Saved and Diary pages. Shown only to somebody who has
     something saved, is not signed in, and has not said no. One line, one
     dismissal, never again after it; the Account link in the footer stays. */
  function prompt(h) {
    if (active || account() || get("account-prompt", null)) return null;
    var el = h.el;
    var holds = (get("saved", []) || []).length || (get("diary", []) || []).length;
    if (!holds) return null;
    var box = el("aside", { class: "account-prompt", "aria-label": "Keep your place across devices" });
    box.appendChild(el("p", {}, [
      "Want these on your other devices? Signing in is optional: ",
      el("a", { href: "#/account", text: "keep my place across devices" }),
      "."
    ]));
    box.appendChild(el("button", { class: "linkish", text: "No thanks", onclick: function () {
      put("account-prompt", "dismissed");
      box.remove();
      if (h.announce) h.announce("Dismissed. This will not be shown again.");
    } }));
    return box;
  }

  /* ---------------- start ---------------- */

  active = !!account();
  if (active) {
    /* Soon after the page is up, never during it. */
    var go = function () { schedule(1500); };
    if (document.readyState === "complete") go(); else window.addEventListener("load", go);
  }

  window.TheBookAccount = {
    view: view,
    prompt: prompt,
    sync: sync,
    state: function () { return { signedIn: active, status: state.status, last: state.last, error: state.error }; }
  };
})();
