#!/usr/bin/env bash
# Regenerate every data file the site reads, from the source text.
set -euo pipefail
cd "$(dirname "$0")/.."

SRC=${1:-source/THE_BOOK_COMPLETE.txt}
OUT=${2:-docs/data}

echo "==> parsing $SRC"
python3 tools/parse_book.py "$SRC" "$OUT"

echo "==> repairs"
python3 tools/build_repairs.py "$OUT" source/extra

echo "==> canon membership"
python3 tools/build_canon.py "$OUT"

echo "==> search index"
python3 tools/build_index.py "$OUT"

echo "==> audit"
python3 tools/audit.py "$OUT" | tail -1

echo "==> done"
