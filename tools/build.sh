#!/usr/bin/env bash
# Regenerate every data file the site reads, from the source text.
set -euo pipefail
cd "$(dirname "$0")/.."

SRC=${1:-source/THE_BOOK_COMPLETE.txt}
OUT=${2:-docs/data}

# Which command runs Python. "python3" is the name on the CI runners and on
# macOS; Windows has "py" instead, and the python3.exe on its PATH is a
# Microsoft Store stub that opens the Store rather than running anything -- so
# the name is asked for its version and only believed if it answers with one.
PY=""
for c in "$PY" python py; do
  if command -v "$c" >/dev/null 2>&1 && "$c" --version 2>&1 | grep -q "^Python 3\."; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "no Python 3 interpreter found (tried python3, python, py)" >&2
  exit 1
fi

echo "==> parsing $SRC"
"$PY" tools/parse_book.py "$SRC" "$OUT"

echo "==> repairs"
"$PY" tools/build_repairs.py "$OUT" source/extra

echo "==> 1 Clement's lacuna, from Lightfoot's edition of 1891"
"$PY" tools/build_lightfoot.py "$OUT" source/extra

echo "==> the Ethiopic Didascalia"
"$PY" tools/build_didascalia.py "$OUT" source/extra

echo "==> the Ethiopian canon books recovered from scans"
"$PY" tools/build_ethiopian.py "$OUT" source/extra "$SRC"

echo "==> lexicon"
"$PY" tools/build_lexicon.py source/lexicon "$OUT"

echo "==> manuscripts"
"$PY" tools/build_manuscripts.py "$OUT"

echo "==> places"
"$PY" tools/build_places.py source/places/merged.txt "$OUT"

echo "==> place mentions"
"$PY" tools/build_mentions.py source/places/merged.txt "$OUT"

# The land outlines. Deterministic and offline: the Natural Earth source is
# vendored under source/basemap/, and only ./tools/build_basemap.py --fetch,
# run by hand, ever downloads anything.
echo "==> basemap"
"$PY" tools/build_basemap.py

echo "==> threads"
"$PY" tools/build_threads.py "$OUT"

echo "==> canon membership"
"$PY" tools/build_canon.py "$OUT"

# After the canons, because it checks every tradition against the canon keys
# that file has just written and fails on one it does not.
echo "==> traditions"
"$PY" tools/build_traditions.py "$OUT"

echo "==> search index"
"$PY" tools/build_index.py "$OUT"

# One work in this volume is printed under a title that names a different and
# far more famous text. The reader cannot be expected to know that, so the work
# says it itself. Before the addresses below, because it edits the manifest.
echo "==> cautions"
"$PY" tools/build_cautions.py "$OUT"

# The public address of every chapter, written into the manifest so that the
# reader and the page builder name the same file. Must run after every script
# that can add, remove or renumber a chapter -- which is all of the repairs
# above -- because it is a list indexed by chapter position.
echo "==> chapter addresses"
"$PY" tools/build_slugs.py "$OUT"

# The audit is a gate, not a report: it exits non-zero when a finding is not
# in tools/audit-baseline.txt. Piping it through tail used to hide both the
# findings and, because the exit status came from tail, the failure itself.
echo "==> audit"
"$PY" tools/audit.py "$OUT"

# The audit asks whether the shape of the library matches the reference
# counts. This asks whether the text inside that shape is the text and
# nothing else, and whether every definition, pin and link points at
# something that exists. It is a gate on the same terms: a finding not in
# tools/verify-baseline.txt stops the build. The --links pass is not run
# here, because whether somebody else's server answered today is not a fact
# about this repository.
echo "==> verify"
"$PY" tools/verify.py "$OUT"

# The whole library as one file, after the audit rather than before it: a copy
# nobody can check is a copy of whatever the data happened to be. It is not
# committed -- 13 MB regenerated on every data change would be most of this
# repository's history within a year -- so it is gitignored here and rebuilt
# from the committed data by the deploy, which is the only place it is served
# from. Building it locally too means the link in the footer works while you
# are developing, and means this script fails here rather than in CI if the
# page ever stops being self-contained.
echo "==> the single-file offline build"
"$PY" tools/build_standalone.py docs docs/the-book.html

# One plain page per work and per chapter, so the library is reachable by a
# crawler at all: the reader is hash-routed, and a fragment is never sent to
# a server, so without these there is exactly one indexable URL for 172 works
# and 2,537 chapters. Not committed either, for the same reason as above and
# with more force -- 2,709 files rebuilt on every text change -- so it is
# gitignored and made here and by the deploy. After the audit, like the
# offline copy: pages nobody has checked are pages of whatever the data
# happened to be.
echo "==> the crawlable static pages"
"$PY" tools/build_pages.py docs

# The worker is stamped with a hash of the files it serves, so it has to be
# built after them: run before the data is rebuilt it would carry the stamp
# of the previous parse and a deploy would ship a cache key for a site that
# no longer exists. Gitignored and made here and by the deploy, like the two
# above.
echo "==> the service worker"
"$PY" tools/build_sw.py docs

echo "==> done"
