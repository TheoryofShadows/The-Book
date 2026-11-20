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
import subprocess

ACCOUNT = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "575b607656db70c0664da716f53b4a18")
PROJECT = "thebookandme"


def value(name, path):
    # The file first, as tools/deploy_cloudflare.sh does: it holds the token
    # made for this project, and the environment may carry another.
    v = open(path).read().strip() if os.path.exists(path) else os.environ.get(name)
    if not v:
        raise SystemExit("%s is not set" % name)
    return v


def main():
    token = value("CLOUDFLARE_API_TOKEN", "/workspace/.cf_pages_token.txt")
    weekly = value("WEEKLY_SECRET", "/workspace/.weekly_secret.txt")
    body = {"deployment_configs": {"production": {"env_vars": {
        "WEEKLY_SECRET": {"type": "secret_text", "value": weekly}}}}}
    # curl rather than urllib: the API's edge refuses this request from
    # Python's client (403) and accepts it from curl.
    url = "https://api.cloudflare.com/client/v4/accounts/%s/pages/projects/%s" % (ACCOUNT, PROJECT)
    r = subprocess.run(["curl", "-sS", "-X", "PATCH", url, "-H", "Content-Type: application/json",
                        "-H", "Authorization: Bearer " + token, "--data-binary", "@-"],
                       input=json.dumps(body).encode(), capture_output=True, check=True)
    out = json.loads(r.stdout)
    if not out.get("success"):
        raise SystemExit("Cloudflare said: %s" % out.get("errors"))
    names = sorted(out["result"]["deployment_configs"]["production"]["env_vars"])
    print("production variables now:", ", ".join(names))


if __name__ == "__main__":
    main()
