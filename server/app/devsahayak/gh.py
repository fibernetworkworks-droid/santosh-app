"""GitHub REST API client for the Developer Sahayak (official API only, her own token).

Fine-grained personal access token, repository permissions (Oct 2026 docs):
  Metadata: read (always), Contents: read & write (read files, blobs / trees / commits / refs, MERGE a PR),
  Pull requests: read & write (open PRs, read diffs, post reviews), Issues: read (bug reports),
  Checks: read + Commit statuses: read (CI), Actions: read & write (start her deploy workflow, read its run),
  Workflows: write ONLY if she lets Hoola edit .github/workflows (off by default).
Nothing here runs repo code: it reads text and writes git objects through the API.
"""
from __future__ import annotations

import base64
import time
from typing import Any
from urllib.parse import quote

import httpx

API = "https://api.github.com"
_TRANSPORT: httpx.BaseTransport | None = None

PERMS = ("Metadata: read", "Contents: read & write", "Pull requests: read & write", "Issues: read", "Checks: read",
         "Commit statuses: read", "Actions: read & write")


class GhError(Exception):
    def __init__(self, msg: str, status: int = 0):
        super().__init__(msg)
        self.status = status


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


def _why(status: int, msg: str) -> str:
    if status == 401:
        return "GitHub token galat ya expire ho gaya: Developer > Niyam mein naya token daaliye."
    if status == 403 and "rate limit" in msg.lower():
        return "GitHub ki rate limit: thodi der baad."
    if status in (403, 404):
        return (f"GitHub ne mana kiya ({status}: {msg[:120]}). Token ko is repo ki ijazat chahiye: " + ", ".join(PERMS) + ".")
    return f"GitHub: {status} {msg[:200]}"


class Gh:
    def __init__(self, token: str):
        if not token:
            raise GhError("GitHub juda nahi: Developer Sahayak > Niyam mein apna fine-grained token daaliye (sirf app mein).")
        self.token = token
        self.calls = 0

    def req(self, method: str, path: str, body: Any = None, params: dict | None = None, ok: tuple[int, ...] = (),
            raw: bool = False) -> Any:
        url = path if path.startswith("http") else f"{API}{path}"
        if not url.startswith(API + "/"):
            raise GhError("Sirf api.github.com")
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Hoola-Developer-Sahayak"}
        if raw:
            headers["Accept"] = "application/vnd.github.raw+json"
        for attempt in range(3):
            self.calls += 1
            if self.calls > 400:
                raise GhError("Ek kaam mein bahut zyada GitHub calls; rok diya.")
            try:
                with httpx.Client(timeout=60, transport=_TRANSPORT, follow_redirects=False) as c:
                    r = c.request(method, url, json=body, params=params, headers=headers)
            except httpx.HTTPError as e:
                if attempt < 2:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise GhError(f"GitHub tak nahi pahunch paya: {e.__class__.__name__}")
            if r.status_code in (502, 503, 504) and attempt < 2:
                time.sleep(0.5 * (attempt + 1))
                continue
            break
        if r.status_code in ok:
            return {"_status": r.status_code, **(_json(r) if r.content else {})}
        if r.status_code >= 400:
            j = _json(r)
            raise GhError(_why(r.status_code, str(j.get("message") or r.text[:200])), r.status_code)
        if raw:
            return r.text
        if not r.content:
            return {"_status": r.status_code}
        j = _json(r)
        if isinstance(j, dict):
            j.setdefault("_status", r.status_code)
        return j

    # ---- account / repo
    def me(self) -> dict[str, Any]:
        return self.req("GET", "/user")

    def repo(self, full: str) -> dict[str, Any]:
        return self.req("GET", f"/repos/{full}")

    def my_repos(self) -> list[dict[str, Any]]:
        out = self.req("GET", "/user/repos", params={"per_page": 100, "sort": "updated"})
        return out if isinstance(out, list) else []

    def branch_sha(self, full: str, branch: str) -> str:
        r = self.req("GET", f"/repos/{full}/git/ref/heads/{quote(branch, safe='/')}", ok=(404,))
        return "" if r.get("_status") == 404 else str((r.get("object") or {}).get("sha") or "")

    def branch_rules(self, full: str, branch: str) -> list[dict[str, Any]]:
        try:
            out = self.req("GET", f"/repos/{full}/rules/branches/{quote(branch, safe='')}")
        except GhError:
            return []
        return out if isinstance(out, list) else []

    def tree(self, full: str, sha: str) -> list[dict[str, Any]]:
        r = self.req("GET", f"/repos/{full}/git/trees/{sha}", params={"recursive": "1"})
        return [t for t in (r.get("tree") or []) if t.get("type") == "blob"]

    def file(self, full: str, path: str, ref: str) -> tuple[str, str]:
        """(text, blob sha); ('', '') when missing."""
        r = self.req("GET", f"/repos/{full}/contents/{quote(path)}", params={"ref": ref}, ok=(404,))
        if r.get("_status") == 404 or r.get("type") != "file":
            return "", ""
        content = r.get("content") or ""
        try:
            text = base64.b64decode(content).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            text = ""
        return text, str(r.get("sha") or "")

    def search_code(self, full: str, words: list[str]) -> list[str]:
        if not words:
            return []
        q = " ".join(w for w in words[:3]) + f" repo:{full}"
        try:
            r = self.req("GET", "/search/code", params={"q": q, "per_page": 10})
        except GhError:
            return []
        return [str(i.get("path")) for i in (r.get("items") or []) if i.get("path")]

    def issue(self, full: str, n: int) -> dict[str, Any]:
        return self.req("GET", f"/repos/{full}/issues/{int(n)}")

    # ---- write (only on hoola/* branches)
    def commit_files(self, full: str, branch: str, parent: str, files: list[tuple[str, str]], message: str) -> str:
        if not branch.startswith("hoola/"):
            raise GhError("Hoola sirf hoola/* branch par commit karta hai.")
        tree = []
        for path, text in files:
            b = self.req("POST", f"/repos/{full}/git/blobs", {"content": text, "encoding": "utf-8"})
            tree.append({"path": path, "mode": "100644", "type": "blob", "sha": b["sha"]})
        base_tree = self.req("GET", f"/repos/{full}/git/commits/{parent}").get("tree", {}).get("sha")
        t = self.req("POST", f"/repos/{full}/git/trees", {"base_tree": base_tree, "tree": tree})
        c = self.req("POST", f"/repos/{full}/git/commits", {"message": message, "tree": t["sha"], "parents": [parent]})
        if self.branch_sha(full, branch):
            self.req("PATCH", f"/repos/{full}/git/refs/heads/{quote(branch, safe='/')}", {"sha": c["sha"], "force": False})
        else:
            self.req("POST", f"/repos/{full}/git/refs", {"ref": f"refs/heads/{branch}", "sha": c["sha"]})
        return str(c["sha"])

    def open_pr(self, full: str, head: str, base: str, title: str, body: str, draft: bool = False) -> dict[str, Any]:
        return self.req("POST", f"/repos/{full}/pulls", {"title": title, "head": head, "base": base, "body": body, "draft": draft,
                                                          "maintainer_can_modify": True})

    def pr(self, full: str, n: int) -> dict[str, Any]:
        return self.req("GET", f"/repos/{full}/pulls/{int(n)}")

    def pr_files(self, full: str, n: int) -> list[dict[str, Any]]:
        out = self.req("GET", f"/repos/{full}/pulls/{int(n)}/files", params={"per_page": 100})
        return out if isinstance(out, list) else []

    def open_prs(self, full: str) -> list[dict[str, Any]]:
        out = self.req("GET", f"/repos/{full}/pulls", params={"state": "open", "per_page": 30})
        return out if isinstance(out, list) else []

    def checks(self, full: str, sha: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        runs = self.req("GET", f"/repos/{full}/commits/{sha}/check-runs", params={"per_page": 100}).get("check_runs") or []
        try:
            st = self.req("GET", f"/repos/{full}/commits/{sha}/status").get("statuses") or []
        except GhError:
            st = []
        return runs, st

    def annotations(self, full: str, check_id: Any) -> list[dict[str, Any]]:
        try:
            out = self.req("GET", f"/repos/{full}/check-runs/{check_id}/annotations", params={"per_page": 30})
        except GhError:
            return []
        return out if isinstance(out, list) else []

    def check_run(self, full: str, check_id: Any) -> dict[str, Any]:
        try:
            return self.req("GET", f"/repos/{full}/check-runs/{check_id}")
        except GhError:
            return {}

    def review(self, full: str, n: int, commit: str, body: str, event: str, comments: list[dict[str, Any]]) -> dict[str, Any]:
        return self.req("POST", f"/repos/{full}/pulls/{int(n)}/reviews",
                        {"commit_id": commit, "body": body, "event": event, "comments": comments})

    def merge(self, full: str, n: int, sha: str, method: str, title: str) -> dict[str, Any]:
        return self.req("PUT", f"/repos/{full}/pulls/{int(n)}/merge", {"sha": sha, "merge_method": method, "commit_title": title},
                        ok=(405, 409, 422))

    def workflows(self, full: str) -> list[dict[str, Any]]:
        return self.req("GET", f"/repos/{full}/actions/workflows", params={"per_page": 100}).get("workflows") or []

    def dispatch(self, full: str, workflow: str, ref: str, inputs: dict[str, Any]) -> dict[str, Any]:
        body: dict[str, Any] = {"ref": ref}
        if inputs:
            body["inputs"] = inputs
        return self.req("POST", f"/repos/{full}/actions/workflows/{quote(workflow, safe='')}/dispatches", body)

    def runs(self, full: str, workflow: str, branch: str) -> list[dict[str, Any]]:
        r = self.req("GET", f"/repos/{full}/actions/workflows/{quote(workflow, safe='')}/runs",
                     params={"branch": branch, "event": "workflow_dispatch", "per_page": 5})
        return r.get("workflow_runs") or []

    def run(self, full: str, run_id: Any) -> dict[str, Any]:
        return self.req("GET", f"/repos/{full}/actions/runs/{run_id}")


def _json(r: httpx.Response) -> Any:
    try:
        return r.json()
    except ValueError:
        return {}
