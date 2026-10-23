"""Her GitHub repo, through the official REST API with HER fine-grained token (typed only in the app, sealed). Reading is all
Hoola does by itself: README, docs/*.md, OpenAPI files, releases, merged pull requests. Code is never run, never even
downloaded beyond those text files. Publishing docs = a new branch + one commit under docs/hoola/ + a pull request, ONLY on
her tap; she merges it herself (nothing on her default branch changes by itself)."""
from __future__ import annotations

import base64
import logging
import re
from typing import Any

import httpx

log = logging.getLogger("santosh.docwriter")
API = "https://api.github.com"
API_VERSION = "2026-03-10"
_TRANSPORT: httpx.BaseTransport | None = None
MAX_TEXT = 400_000
REPO_RX = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")


class GhError(Exception):
    pass


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


def parse_repo(v: str) -> str:
    s = (v or "").strip().rstrip("/")
    s = re.sub(r"^(https?://)?(www\.)?github\.com/", "", s, flags=re.I)
    s = re.sub(r"\.git$", "", s)
    s = "/".join(s.split("/")[:2])
    if not REPO_RX.match(s):
        raise GhError("Repo 'owner/naam' ya github.com link chahiye")
    return s


class Gh:
    def __init__(self, token: str):
        if not token:
            raise GhError("GitHub juda nahi: Docs Sahayak > Sources mein apna fine-grained token (read-only) app mein daaliye.")
        self.token = token

    def req(self, method: str, path: str, body: Any = None, ok404: bool = False, params: dict | None = None) -> Any:
        try:
            with httpx.Client(timeout=40, transport=_TRANSPORT) as c:
                r = c.request(method, f"{API}{path}", json=body, params=params, headers={
                    "Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": API_VERSION, "User-Agent": "Hoola-Docs"})
        except httpx.HTTPError as e:
            raise GhError(f"GitHub tak nahi pahunch paya: {e.__class__.__name__}")
        if ok404 and r.status_code == 404:
            return None
        if r.status_code >= 400:
            try:
                msg = str(r.json().get("message", ""))[:200]
            except ValueError:
                msg = r.text[:200]
            if r.status_code in (401, 403):
                msg += " (token ko is repo par 'Contents: read' / 'Pull requests: read' chahiye; publish ke liye write)"
            raise GhError(f"GitHub: {r.status_code} {msg}")
        return r.json() if r.content else {}

    def me(self) -> dict[str, Any]:
        return self.req("GET", "/user")

    def text(self, repo: str, path: str, ref: str = "") -> str | None:
        j = self.req("GET", f"/repos/{repo}/contents/{path}", ok404=True, params={"ref": ref} if ref else None)
        if not isinstance(j, dict) or j.get("type") != "file" or int(j.get("size") or 0) > MAX_TEXT:
            return None
        try:
            return base64.b64decode(j.get("content") or "").decode("utf-8", "replace")
        except Exception:
            return None


def read_repo(token: str, repo: str) -> dict[str, Any]:
    """Text only: README, docs/*.md (30), OpenAPI files, last releases, merged PRs since the last release."""
    from . import openapi as OA
    gh = Gh(token)
    meta = gh.req("GET", f"/repos/{repo}")
    branch = meta.get("default_branch") or "main"
    tree = gh.req("GET", f"/repos/{repo}/git/trees/{branch}", params={"recursive": "1"}, ok404=True) or {}
    paths = [t["path"] for t in tree.get("tree") or [] if t.get("type") == "blob"]
    readme = None
    for p in paths:
        if re.fullmatch(r"readme(\.md|\.markdown|\.txt)?", p, re.I):
            readme = gh.text(repo, p, branch)
            break
    docs = {}
    for p in [p for p in paths if re.match(r"^docs?/.+\.(md|markdown|mdx)$", p, re.I) and not p.startswith("docs/hoola/")][:30]:
        t = gh.text(repo, p, branch)
        if t:
            docs[p] = t[:60_000]
    specs = {}
    for p in OA.find_files(paths):
        t = gh.text(repo, p, branch)
        if t:
            try:
                specs[p] = OA.load(t)
            except OA.OpenApiError:
                continue
    rels = gh.req("GET", f"/repos/{repo}/releases", params={"per_page": "10"}) or []
    releases = [{"tag": r.get("tag_name") or "", "name": r.get("name") or "", "at": r.get("published_at") or "",
                 "body": (r.get("body") or "")[:8000], "draft": bool(r.get("draft")), "pre": bool(r.get("prerelease"))}
                for r in rels if isinstance(r, dict) and not r.get("draft")]
    since = releases[0]["at"] if releases else ""
    pulls = gh.req("GET", f"/repos/{repo}/pulls", params={"state": "closed", "sort": "updated", "direction": "desc",
                                                         "per_page": "50"}) or []
    merged = []
    for p in pulls:
        if not isinstance(p, dict) or not p.get("merged_at"):
            continue
        merged.append({"number": p.get("number"), "title": str(p.get("title") or "")[:200], "merged_at": p["merged_at"],
                       "labels": [str(lb.get("name") or "") for lb in p.get("labels") or [] if isinstance(lb, dict)][:6],
                       "body": str(p.get("body") or "")[:1500], "after_release": bool(not since or p["merged_at"] > since)})
    return {"repo": repo, "branch": branch, "description": str(meta.get("description") or "")[:300],
            "private": bool(meta.get("private")), "readme": (readme or "")[:80_000], "docs": docs, "openapi": specs,
            "releases": releases, "pulls": merged, "files": len(paths)}


def open_pr(token: str, repo: str, files: dict[str, bytes], title: str, body: str, branch_name: str) -> dict[str, Any]:
    """ONLY from her tap: branch from the default branch, one commit with the docs files, a pull request."""
    gh = Gh(token)
    meta = gh.req("GET", f"/repos/{repo}")
    base = meta.get("default_branch") or "main"
    ref = gh.req("GET", f"/repos/{repo}/git/ref/heads/{base}")
    head_sha = ref["object"]["sha"]
    commit = gh.req("GET", f"/repos/{repo}/git/commits/{head_sha}")
    tree = []
    for path, data in files.items():
        if not path.startswith("docs/hoola/") or ".." in path:
            raise GhError("Sirf docs/hoola/ ke andar")
        blob = gh.req("POST", f"/repos/{repo}/git/blobs", {"content": base64.b64encode(data).decode(), "encoding": "base64"})
        tree.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    t = gh.req("POST", f"/repos/{repo}/git/trees", {"base_tree": commit["tree"]["sha"], "tree": tree})
    c = gh.req("POST", f"/repos/{repo}/git/commits", {"message": title, "tree": t["sha"], "parents": [head_sha]})
    gh.req("POST", f"/repos/{repo}/git/refs", {"ref": f"refs/heads/{branch_name}", "sha": c["sha"]})
    pr = gh.req("POST", f"/repos/{repo}/pulls", {"title": title, "head": branch_name, "base": base, "body": body,
                                                 "maintainer_can_modify": True})
    return {"url": pr.get("html_url") or "", "number": pr.get("number"), "branch": branch_name, "commit": c["sha"]}
