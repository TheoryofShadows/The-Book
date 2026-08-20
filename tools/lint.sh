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

fail=0

echo "==> python"
for f in tools/*.py tests/python/*.py; do
  if ! python3 -m py_compile "$f" 2>&1; then
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

echo "==> data"
python3 - <<'PY'
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
