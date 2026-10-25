/* Sends a short chapter address to the real one.
 *
 * Loaded only by 404.html. Chapter pages live at /read/<work>/<chapter>/,
 * but people type and share the short form -- /exodus/31 -- and that used to
 * end on "No page at that address". If the missed address has that shape it
 * is sent on to /read/exodus/31/. If that is not a real chapter either, Pages
 * answers with this same page and, because the path now starts with read/,
 * nothing redirects again. The 404 is noindex, so no crawler is shown one
 * text and a reader another.
 */
(function () {
  "use strict";
  var KEEP = { read: 1, contents: 1, timeline: 1, threads: 1, assets: 1, data: 1,
    about: 1, contact: 1, privacy: 1, press: 1 };
  var SEG = /^[a-z0-9][a-z0-9-]*$/;
  var parts = location.pathname.toLowerCase().split("/").filter(function (p) { return p !== ""; });
  if (parts.length < 1 || parts.length > 2 || KEEP[parts[0]]) return;
  for (var i = 0; i < parts.length; i++) if (!SEG.test(parts[i])) return;
  location.replace("/read/" + parts.join("/") + "/" + location.search + location.hash);
})();
