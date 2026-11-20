#!/usr/bin/env python3
"""Put WEEKLY_SECRET on the Cloudflare Pages project.

    WEEKLY_SECRET=... python3 tools/set_weekly_secret.py

worker/worker.js uses it to sign the unsubscribe links in the weekly chapter
email and to check the scheduler's calls to /api/weekly/run. The scheduler is
.github/workflows/weekly-email.yml, which holds the same value as the GitHub
Actions secret WEEKLY_SECRET (gh secret set WEEKLY_SECRET). Changing it breaks
the unsubscribe links in emails already sent, so set it once.

Needs CLOUDFLARE_API_TOKEN (Account > Cloudflare Pages > Edit), or the file
/workspace/.cf_pages_token.txt. The Pages PATCH merges variables, so the
others (RESEND_API_KEY, MAIL_FROM) are kept. It takes effect on the next deploy.
"""
import json
import os
import urllib.request

ACCOUNT = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "575b607656db70c0664da716f53b4a18")
PROJECT = "thebookandme"


def value(name, path):
    v = os.environ.get(name)
    if not v and os.path.exists(path):
        v = open(path).read().strip()
    if not v:
        raise SystemExit("%s is not set" % name)
    return v


def main():
    token = value("CLOUDFLARE_API_TOKEN", "/workspace/.cf_pages_token.txt")
    weekly = value("WEEKLY_SECRET", "/workspace/.weekly_secret.txt")
    body = {"deployment_configs": {"production": {"env_vars": {
        "WEEKLY_SECRET": {"type": "secret_text", "value": weekly}}}}}
    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/accounts/%s/pages/projects/%s" % (ACCOUNT, PROJECT),
        data=json.dumps(body).encode(), method="PATCH",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        out = json.load(r)
    names = sorted(out["result"]["deployment_configs"]["production"]["env_vars"])
    print("production variables now:", ", ".join(names))


if __name__ == "__main__":
    main()
