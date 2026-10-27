"""Her GitHub, official REST API only, with HER fine-grained token (typed only in the app, sealed with the bazar vault, never
shown to the model). Read-only calls are free to use; the three write calls (workflow_dispatch, re-run failed jobs, review
pending deployments) are only ever reached from an app tap (service.decide_deploy / rerun / env review, by_tap=True).

Token permissions she needs (fine-grained PAT, chosen repos): Actions read (runs / jobs / logs), Contents read (compare,
workflow files), Metadata read, Commit statuses + Checks read; for deploys: Actions write (dispatch / re-run) and
Deployments write (approve a waiting environment)."""
from __future__ import annotations

import base64
from typing import Any
from urllib.parse import quote

import httpx

API = "https://api.github.com"
_TRANSPORT: httpx.BaseTransport | None = None
MAX_LOG = 2_000_000


class GhError(Exception):
    def __init__(self, msg: str, status: int = 0):
        super().__init__(msg)
        self.status = status


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


def _client() -> httpx.Client:
    return httpx.Client(timeout=30, transport=_TRANSPORT, follow_redirects=False)


class Gh:
    def __init__(self, token: str):
        if not token:
            raise GhError("GitHub juda nahi hai: DevOps > Niyam mein apna GitHub token jodiye (sirf app mein, chat mein kabhi nahi).")
        self.token = token

    def _h(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Hoola-DevOps"}

    def req(self, method: str, path: str, body: Any = None, ok404: bool = False, params: dict | None = None) -> Any:
        try:
            with _client() as c:
                r = c.request(method, f"{API}{path}", json=body, params=params, headers=self._h())
        except httpx.HTTPError as e:
            raise GhError(f"GitHub tak nahi pahunch paya ({e.__class__.__name__}).")
        if ok404 and r.status_code == 404:
            return None
        if r.status_code >= 400:
            try:
                msg = r.json().get("message", "")
            except ValueError:
                msg = r.text[:200]
            if r.status_code in (401, 403):
                msg += " (token expire / ijazat kam: Actions, Contents, Deployments ki permission dekhiye)"
            raise GhError(f"GitHub {r.status_code}: {msg}", r.status_code)
        if r.status_code == 204 or not r.content:
            return {}
        return r.json()

    # ---- read
    def me(self) -> dict[str, Any]:
        return self.req("GET", "/user")

    def repo(self, full: str) -> dict[str, Any] | None:
        return self.req("GET", f"/repos/{full}", ok404=True)

    def workflows(self, full: str) -> list[dict[str, Any]]:
        return (self.req("GET", f"/repos/{full}/actions/workflows", params={"per_page": 100}) or {}).get("workflows", [])

    def workflow_file(self, full: str, path: str, ref: str = "") -> str:
        d = self.req("GET", f"/repos/{full}/contents/{quote(path)}", ok404=True, params={"ref": ref} if ref else None)
        if not d or d.get("encoding") != "base64":
            return ""
        try:
            return base64.b64decode(d.get("content", "")).decode("utf-8", "replace")
        except ValueError:
            return ""

    def runs(self, full: str, per_page: int = 30, branch: str = "", workflow: str = "") -> list[dict[str, Any]]:
        p: dict[str, Any] = {"per_page": per_page}
        if branch:
            p["branch"] = branch
        path = f"/repos/{full}/actions/workflows/{quote(workflow)}/runs" if workflow else f"/repos/{full}/actions/runs"
        return (self.req("GET", path, params=p) or {}).get("workflow_runs", [])

    def run(self, full: str, run_id: int) -> dict[str, Any] | None:
        return self.req("GET", f"/repos/{full}/actions/runs/{run_id}", ok404=True)

    def attempt(self, full: str, run_id: int, n: int) -> dict[str, Any] | None:
        return self.req("GET", f"/repos/{full}/actions/runs/{run_id}/attempts/{n}", ok404=True)

    def jobs(self, full: str, run_id: int, attempt: int = 0) -> list[dict[str, Any]]:
        path = f"/repos/{full}/actions/runs/{run_id}/attempts/{attempt}/jobs" if attempt else f"/repos/{full}/actions/runs/{run_id}/jobs"
        return (self.req("GET", path, params={"per_page": 100}) or {}).get("jobs", [])

    def job_log(self, full: str, job_id: int) -> str:
        """302 to a short-lived download link; followed WITHOUT our token (the link carries its own signature)."""
        try:
            with _client() as c:
                r = c.get(f"{API}/repos/{full}/actions/jobs/{job_id}/logs", headers=self._h())
                if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                    loc = r.headers["location"]
                    if not loc.startswith("https://"):
                        raise GhError("GitHub log ka link https nahi.")
                    r = c.get(loc, headers={"User-Agent": "Hoola-DevOps"})
        except httpx.HTTPError as e:
            raise GhError(f"Log nahi mila ({e.__class__.__name__}).")
        if r.status_code == 410 or r.status_code == 404:
            return ""
        if r.status_code >= 400:
            raise GhError(f"Log nahi mila: GitHub {r.status_code}", r.status_code)
        return r.content[-MAX_LOG:].decode("utf-8", "replace")

    def commit(self, full: str, ref: str) -> dict[str, Any] | None:
        return self.req("GET", f"/repos/{full}/commits/{quote(ref, safe='')}", ok404=True)

    def compare(self, full: str, base: str, head: str) -> dict[str, Any] | None:
        return self.req("GET", f"/repos/{full}/compare/{base}...{head}", ok404=True)

    def checks(self, full: str, sha: str) -> dict[str, Any]:
        """Check runs + commit statuses of one commit -> {state success|failure|pending|none, total, failed[], pending[]}."""
        cr = (self.req("GET", f"/repos/{full}/commits/{sha}/check-runs", params={"per_page": 100}, ok404=True) or {}).get("check_runs", [])
        st = (self.req("GET", f"/repos/{full}/commits/{sha}/status", ok404=True) or {}).get("statuses", [])
        failed, pending, ok = [], [], []
        for c in cr:
            nm = c.get("name", "")
            if c.get("status") != "completed":
                pending.append(nm)
            elif c.get("conclusion") in ("success", "neutral", "skipped"):
                ok.append(nm)
            else:
                failed.append(nm)
        for s in st:
            nm = s.get("context", "")
            {"success": ok, "pending": pending}.get(s.get("state", ""), failed).append(nm)
        total = len(ok) + len(failed) + len(pending)
        state = "none" if not total else "failure" if failed else "pending" if pending else "success"
        return {"state": state, "total": total, "failed": failed[:20], "pending": pending[:20], "ok": len(ok)}

    def pending_deployments(self, full: str, run_id: int) -> list[dict[str, Any]]:
        return self.req("GET", f"/repos/{full}/actions/runs/{run_id}/pending_deployments", ok404=True) or []

    # ---- write (only from her tap)
    def dispatch(self, full: str, workflow: str, ref: str, inputs: dict[str, Any]) -> dict[str, Any]:
        body: dict[str, Any] = {"ref": ref, "return_run_details": True}
        if inputs:
            body["inputs"] = inputs
        out = self.req("POST", f"/repos/{full}/actions/workflows/{quote(workflow)}/dispatches", body)
        return out or {}

    def rerun_failed(self, full: str, run_id: int) -> None:
        self.req("POST", f"/repos/{full}/actions/runs/{run_id}/rerun-failed-jobs", {})

    def review_pending(self, full: str, run_id: int, env_ids: list[int], approve: bool, comment: str) -> Any:
        return self.req("POST", f"/repos/{full}/actions/runs/{run_id}/pending_deployments",
                        {"environment_ids": env_ids, "state": "approved" if approve else "rejected", "comment": comment[:500]})
