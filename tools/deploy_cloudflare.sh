#!/usr/bin/env bash
# One-command deploy of the site to Cloudflare Pages (no GitHub involved).
# Needs: CLOUDFLARE_API_TOKEN (permission: Account > Cloudflare Pages > Edit) and
#        CLOUDFLARE_ACCOUNT_ID=575b607656db70c0664da716f53b4a18  in the environment,
#        and `pip install blake3` (or use the venv at /workspace/venv).
set -euo pipefail
cd "$(dirname "$0")/.."
export CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-575b607656db70c0664da716f53b4a18}"
[ -f /workspace/.cf_pages_token.txt ] && export CLOUDFLARE_API_TOKEN="$(cat /workspace/.cf_pages_token.txt)" || export CLOUDFLARE_API_TOKEN="${CLOUDFLARE_PAGES_TOKEN:-${CLOUDFLARE_API_TOKEN:-}}"
PY=python3; [ -x /workspace/venv/bin/python ] && PY=/workspace/venv/bin/python
exec "$PY" tools/deploy_cloudflare.py "$@"
