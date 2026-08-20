#!/usr/bin/env bash
# Run the browser checks against docs/.
#
#   ./tools/test.sh                 everything
#   ./tools/test.sh listening       one suite
#
# Needs Node. The first run installs Playwright and its Chromium into
# tests/node_modules, which is git-ignored. Set CHROME_PATH to use a browser
# already on the machine instead.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v node >/dev/null 2>&1; then
  echo "Node is needed for the browser checks: https://nodejs.org" >&2
  exit 2
fi

if [ ! -d tests/node_modules ]; then
  echo "==> installing the test dependencies (once)"
  npm --prefix tests install --no-audit --no-fund
  if [ -z "${CHROME_PATH:-}" ]; then
    npm --prefix tests exec -- playwright install chromium
  fi
fi

# The unit tests come first when the whole suite is asked for: they take
# milliseconds, need nothing installed, and cover the half of the codebase the
# browser never sees. Finding out that split_verses is broken should not
# require waiting a minute for Chromium to finish.
if [ "$#" -eq 0 ]; then
  echo "==> the build scripts"
  python3 -m unittest discover -s tests/python -t tests/python
  echo
  echo "==> the reader"
fi

exec node tests/run.js "$@"
