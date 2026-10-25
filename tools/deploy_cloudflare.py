#!/usr/bin/env python3
"""Deploy the built site (docs/) to Cloudflare Pages by direct upload -- no GitHub involved.

  python3 tools/deploy_cloudflare.py [--build] [--dir docs] [--project thebookandme]
  python3 tools/deploy_cloudflare.py --stage-only        # just build the staging dir + manifest

Needs CLOUDFLARE_API_TOKEN (Pages:Edit on the account) and CLOUDFLARE_ACCOUNT_ID in the
environment.  --build runs the same steps as .github/workflows/pages.yml on a COPY of the
repo, so docs/ in the working tree is never polluted with generated files.
Needs `pip install blake3`.  Never prints the token.
"""
import argparse, base64, json, mimetypes, os, shutil, subprocess, sys, urllib.request, uuid
from pathlib import Path

API = "https://api.cloudflare.com/client/v4"
SKIP = {".nojekyll", "CNAME", "_headers", "_redirects", "_routes.json", "_worker.js", ".DS_Store"}
# The policy is the home page's own <meta> policy (the widest one the site uses: it
# adds the live-status hosts the Watch box asks), so the header never blocks anything
# a page's own policy allows, and adds frame-ancestors, which a <meta> cannot carry.
# Both are enforced together, so each page is held to the stricter of the two.
CSP = ("default-src 'self'; base-uri 'self'; form-action 'self'; object-src 'none'; "
       "frame-ancestors 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
       "script-src 'self' https://static.cloudflareinsights.com; worker-src 'self'; manifest-src 'self'; "
       "connect-src 'self' https://cloudflareinsights.com https://archive.org https://*.archive.org "
       "https://kick.com https://decapi.me; media-src 'self' blob: https://archive.org https://*.archive.org")
# HSTS: six months, and deliberately NOT includeSubDomains or preload -- send.thebookandme.com
# and the mail records live on subdomains this file knows nothing about, and preload is not
# something to turn on by accident. /api/* responses come from the Worker, which sets its own
# headers (Pages does not apply this file to them).
HEADERS = f"""/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Strict-Transport-Security: max-age=15552000
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), accelerometer=(), gyroscope=(), magnetometer=()
  Content-Security-Policy: {CSP}
/the-book
  ! Content-Security-Policy
/the-book.html
  ! Content-Security-Policy
/sw.js
  Cache-Control: no-cache
"""

ROUTES = json.dumps({"version": 1, "include": ["/api/*"], "exclude": []})

def call(method, url, token, body=None, ctype="application/json"):
    data = body if isinstance(body, (bytes, type(None))) else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": "Bearer " + token, "Content-Type": ctype})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())

def stage(repo, out):
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(repo, out, ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__"))
    # The scratch copy has no git history, so the sitemap dates are asked of the real
    # repo here and handed down (see build_pages.source_date / site_date).
    sys.path.insert(0, str(repo / "tools"))
    import build_pages
    os.environ["BOOK_SOURCE_DATE"] = build_pages.source_date()
    os.environ["BOOK_SITE_DATE"] = build_pages.site_date()
    for cmd in (["tools/build_pages.py", "docs"],
                ["tools/build_standalone.py", "docs", "docs/the-book.html"],
                ["tools/build_sw.py", "docs"]):
        subprocess.run([sys.executable] + cmd, cwd=out, check=True, stdout=subprocess.DEVNULL)
    (out / "docs" / "_headers").write_text(HEADERS)
    # The account API (worker/worker.js) rides along as the Pages "advanced mode"
    # worker. _routes.json limits it to /api/*, so every page and asset is still
    # served as plain static files, never through a Worker invocation.
    src = repo / "worker" / "worker.js"
    if src.exists():
        shutil.copyfile(src, out / "docs" / "_worker.js")
        (out / "docs" / "_routes.json").write_text(ROUTES)
    return out / "docs"

def manifest(site):
    from blake3 import blake3
    files = {}
    for p in sorted(site.rglob("*")):
        if p.is_file() and p.name not in SKIP:
            rel = "/" + p.relative_to(site).as_posix()
            b64 = base64.b64encode(p.read_bytes()).decode()
            ext = p.suffix.lstrip(".")
            h = blake3((b64 + ext).encode()).hexdigest()[:32]
            files[rel] = (h, p, b64, mimetypes.guess_type(p.name)[0] or "application/octet-stream")
    return files

def upload(files, jwt):
    hashes = sorted({v[0] for v in files.values()})
    missing = set(call("POST", API + "/pages/assets/check-missing", jwt, {"hashes": hashes})["result"])
    todo = {}
    for h, p, b64, ct in files.values():
        if h in missing:
            todo[h] = {"key": h, "value": b64, "metadata": {"contentType": ct}, "base64": True}
    batch, size = [], 0
    def flush():
        nonlocal batch, size
        if batch:
            call("POST", API + "/pages/assets/upload", jwt, batch)
            batch, size = [], 0
    for item in todo.values():
        if batch and (size + len(item["value"]) > 30_000_000 or len(batch) >= 1000):
            flush()
        batch.append(item); size += len(item["value"])
    flush()
    call("POST", API + "/pages/assets/upsert-hashes", jwt, {"hashes": hashes})
    return len(todo), len(hashes)

def deploy(site, project, token, account, branch="main"):
    files = manifest(site)
    jwt = call("GET", f"{API}/accounts/{account}/pages/projects/{project}/upload-token", token)["result"]["jwt"]
    n_up, n_all = upload(files, jwt)
    man = {k: v[0] for k, v in files.items()}
    b = uuid.uuid4().hex
    parts = [("manifest", json.dumps(man)), ("branch", branch)]
    body = b"".join(f'--{b}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n'.encode() for n, v in parts)
    # _headers and _routes.json must be sent as FILE parts (with a filename), the way wrangler
    # does. As plain form fields the API accepts them and silently ignores them, which is how
    # the header rules went unapplied until now (sw.js was not no-cache, no HSTS).
    for name, ctype in (("_headers", "text/plain"), ("_routes.json", "application/json")):
        if (site / name).exists():
            body += (f'--{b}\r\nContent-Disposition: form-data; name="{name}"; filename="{name}"\r\n'
                     f'Content-Type: {ctype}\r\n\r\n').encode() + (site / name).read_bytes() + b"\r\n"
    if (site / "_worker.js").exists():
        body += (f'--{b}\r\nContent-Disposition: form-data; name="_worker.js"; filename="_worker.js"\r\n'
                 f'Content-Type: application/javascript+module\r\n\r\n').encode() + (site / "_worker.js").read_bytes() + b"\r\n"
    body += f"--{b}--\r\n".encode()
    r = call("POST", f"{API}/accounts/{account}/pages/projects/{project}/deployments", token, body, f"multipart/form-data; boundary={b}")
    return n_up, n_all, r["result"]["url"], r["result"].get("environment")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true", help="build in a scratch copy first (default)")
    ap.add_argument("--dir", help="deploy an already-built dir instead of building")
    ap.add_argument("--project", default="thebookandme")
    ap.add_argument("--stage-only", action="store_true")
    ap.add_argument("--branch", default="main",
                    help="'main' is PRODUCTION. Any other branch name makes a preview deployment "
                         "at <branch>.<project>.pages.dev that does not touch production.")
    ap.add_argument("--scratch", default="/tmp/thebook-site-build")
    a = ap.parse_args()
    repo = Path(__file__).resolve().parent.parent
    site = Path(a.dir) if a.dir else stage(repo, Path(a.scratch))
    if a.stage_only:
        print(site); sys.exit(0)
    token, account = os.environ["CLOUDFLARE_API_TOKEN"], os.environ["CLOUDFLARE_ACCOUNT_ID"]
    up, total, url, env = deploy(site, a.project, token, account, a.branch)
    print(f"uploaded {up} new of {total} unique files -> {url} ({env or 'unknown'} environment, branch {a.branch})")
