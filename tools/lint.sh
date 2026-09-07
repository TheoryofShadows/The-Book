#!/usr/bin/env bash
# Everything parses, and every data file is the JSON it claims to be.
#
#   ./tools/lint.sh
#
# Not a style checker. It uses only what Python and Node already ship, for the
# same reason the site ships no dependencies: a check nobody can run without
# installing something first is a check that stops being run. What it catches
# is the class of mistake that turns into a blank page -- a stray bracket in
# app.js, a script that cannot be imported, a data file truncated by a failed
# write -- and it catches it in a couple of seconds rather than after a
# five-minute browser run.
set -euo pipefail
cd "$(dirname "$0")/.."

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

fail=0

echo "==> python"
for f in tools/*.py tests/python/*.py; do
  if ! "$PY" -m py_compile "$f" 2>&1; then
    echo "  FAIL  $f" >&2
    fail=1
  fi
done
find . -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
echo "  ok    $(ls tools/*.py tests/python/*.py | wc -l | tr -d ' ') files"

if command -v node >/dev/null 2>&1; then
  echo "==> javascript"
  for f in docs/assets/*.js tests/*.js; do
    if ! node --check "$f"; then
      echo "  FAIL  $f" >&2
      fail=1
    fi
  done
  echo "  ok    $(ls docs/assets/*.js tests/*.js | wc -l | tr -d ' ') files"
else
  echo "==> javascript  (skipped, no node)"
fi

# The stylesheet, for the two mistakes it can make silently.
#
# A selector declared twice is not an error and does not look like one: the
# second block quietly overrides part of the first, and the first goes on
# describing something that never renders. Six had accumulated here, and one
# of them -- ".player-bar i { background: var(--rubric) }" -- sat twenty-six
# lines above the real rule and so had never painted anything at all, which
# did not stop it being read, believed, and written up as a fix.
#
# A custom property defined and never used is the same mistake in the
# palette: --gilt sat in all three themes for a year unused, and --rubric-bg
# went the same way. A colour nothing uses is a colour nobody maintains.
echo "==> stylesheet"
"$PY" tools/lint_css.py
style=$?
[ "$style" -eq 0 ] || fail=1

echo "==> data"
"$PY" - <<'PY'
import json
import os
import sys

bad = 0
count = 0
for folder, _dirs, files in os.walk("docs/data"):
    for name in sorted(files):
        if not name.endswith(".json"):
            continue
        path = os.path.join(folder, name)
        count += 1
        try:
            with open(path, encoding="utf-8") as fh:
                json.load(fh)
        except Exception as exc:                    # noqa: BLE001
            print(f"  FAIL  {path}: {exc}", file=sys.stderr)
            bad += 1
print(f"  ok    {count - bad} of {count} files")
sys.exit(1 if bad else 0)
PY
data=$?
[ "$data" -eq 0 ] || fail=1

if [ "$fail" -ne 0 ]; then
  echo
  echo "Something above does not parse." >&2
  exit 1
fi
