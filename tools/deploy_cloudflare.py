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
SKIP = {".nojekyll", "CNAME", "_headers", "_redirects", "_worker.js", ".DS_Store"}
HEADERS = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
/sw.js
  Cache-Control: no-cache
"""

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
    for cmd in (["tools/build_pages.py", "docs"],
                ["tools/build_standalone.py", "docs", "docs/the-book.html"],
                ["tools/build_sw.py", "docs"]):
        subprocess.run([sys.executable] + cmd, cwd=out, check=True, stdout=subprocess.DEVNULL)
    (out / "docs" / "_headers").write_text(HEADERS)
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

def deploy(site, project, token, account):
    files = manifest(site)
    jwt = call("GET", f"{API}/accounts/{account}/pages/projects/{project}/upload-token", token)["result"]["jwt"]
    n_up, n_all = upload(files, jwt)
    man = {k: v[0] for k, v in files.items()}
    b = uuid.uuid4().hex
    parts = [("manifest", json.dumps(man)), ("branch", "main"), ("_headers", (site / "_headers").read_text())]
    body = b"".join(f'--{b}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n'.encode() for n, v in parts) + f"--{b}--\r\n".encode()
    r = call("POST", f"{API}/accounts/{account}/pages/projects/{project}/deployments", token, body, f"multipart/form-data; boundary={b}")
    return n_up, n_all, r["result"]["url"]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true", help="build in a scratch copy first (default)")
    ap.add_argument("--dir", help="deploy an already-built dir instead of building")
    ap.add_argument("--project", default="thebookandme")
    ap.add_argument("--stage-only", action="store_true")
    ap.add_argument("--scratch", default="/tmp/thebook-site-build")
    a = ap.parse_args()
    repo = Path(__file__).resolve().parent.parent
    site = Path(a.dir) if a.dir else stage(repo, Path(a.scratch))
    if a.stage_only:
        print(site); sys.exit(0)
    token, account = os.environ["CLOUDFLARE_API_TOKEN"], os.environ["CLOUDFLARE_ACCOUNT_ID"]
    up, total, url = deploy(site, a.project, token, account)
    print(f"uploaded {up} new of {total} unique files -> {url}")
