"""HTTP routes of the Developer Sahayak (/api/devsahayak/*). main.py: app.include_router(make_router(require_key, current_tenant)).

The ONLY ways something happens in her GitHub that she has to agree to:
  POST /api/devsahayak/tasks/{id}/plan-ok       (v0.451 her Haan on a LARGE job's plan, before any file is touched)
  POST /api/devsahayak/tasks/{id}/push          (open the PR of a prepared change: public repos / ask_before_pr)
  POST /api/devsahayak/reviews/{id}/post        (post Hoola's draft review, her chosen event)
  POST /api/devsahayak/actions/{id}/decide      (MERGE / DEPLOY)
The GitHub token is accepted only here (PUT /token), never through the chat tool."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import Response


def make_public_router() -> APIRouter:
    """Phase 5: the two doors that are NOT behind her sign-in, each with its own secret in the address or the header.
    - GET  /api/devsahayak/shared/{token}: the read-only view of ONE session she shared (random token, 7 days).
    - POST /api/devsahayak/hooks/{id}: her own program starts a run of ONE scheduled task (Bearer token, 10 an hour)."""
    from . import around as AR
    p = APIRouter(prefix="/api/devsahayak")

    @p.get("/shared/{token}")
    async def shared(token: str):
        v = await asyncio.to_thread(AR.shared, token)
        if v is None:
            raise HTTPException(404, "This link is not active.")
        return v

    @p.post("/hooks/{sid}")
    async def hook(sid: str, request: Request):
        auth = request.headers.get("authorization") or ""
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        payload = ""
        try:
            size = int(request.headers.get("content-length") or 0)
        except ValueError:
            size = 0
        if 0 < size <= 16000:                   # a bigger body is not read at all (this door has no sign-in in front of it)
            try:
                body = json.loads(await request.body())
                payload = str(body.get("text") or "") if isinstance(body, dict) else ""
            except (ValueError, UnicodeDecodeError):
                payload = ""
        out = await asyncio.to_thread(AR.fire, sid, token, payload)
        if out["status"] != 200:
            raise HTTPException(out["status"], out.get("error") or "Refused.")
        return {"ok": True, "session": out["session"]}

    @p.post("/github/{hook_id}")
    async def github(hook_id: str, request: Request):
        """Phase 6: GitHub's webhook deliveries for one repo. Believed only with a matching X-Hub-Signature-256."""
        from . import events as EV
        try:
            size = int(request.headers.get("content-length") or 0)
        except ValueError:
            size = 0
        if not 0 < size <= EV.MAX_BODY:
            raise HTTPException(401, "Refused.")
        out = await asyncio.to_thread(EV.receive, hook_id, request.headers.get("x-github-event") or "",
                                      request.headers.get("x-github-delivery") or "", request.headers.get("x-hub-signature-256") or "",
                                      await request.body())
        if out["status"] != 200:
            raise HTTPException(401, "Refused.")
        return {"ok": True, "started": int(out.get("started") or 0)}

    @p.get("/labcheck")
    async def labcheck(request: Request):
        """Phase 6: for `python -m app.devlab net` - says whether a header arrived, as a fingerprint, never the value."""
        import hashlib
        v = request.headers.get("x-hoola-lab-check") or ""
        return {"seen": hashlib.sha256(v.encode()).hexdigest()[:16] if v else ""}
    return p


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/devsahayak", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.DevError, ValueError) as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(S.overview, tenant)

    @r.get("/agents")
    async def agents(tenant: str = Depends(current_tenant)):
        """v0.794 the ECC agents Hoola Code can hand work to (and the ECC agents left out, with why)."""
        from . import ecc
        from . import subagent as SA
        rows = [{k: a[k] for k in ("name", "title", "group", "tools", "when")} for a in ecc.catalog().values()]
        return {"on": SA.on(), "agents": sorted(rows, key=lambda a: (a["group"], a["name"])),
                "not_added": [{"name": k, "why": v} for k, v in sorted(ecc.NOT_ADDED.items())], "credit": ecc.CREDIT}

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("review_post", "ask_before_pr", "draft_pr", "allow_workflows", "merge_method", "max_files", "max_lines", "rules", "default_repo",
                "archive_after_merge")
        return await run(S.save_settings, tenant, **{k: b[k] for k in keys if k in b})

    @r.put("/token")
    async def put_token(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.set_token, tenant, str(_b(body).get("token") or ""))

    @r.delete("/token")
    async def del_token(tenant: str = Depends(current_tenant)):
        return await run(S.forget_token, tenant)

    # ---- repos
    @r.get("/repos")
    async def list_repos(tenant: str = Depends(current_tenant)):
        return {"repos": await run(S.repos, tenant)}

    @r.get("/github_repos")
    async def gh_repos(tenant: str = Depends(current_tenant)):
        return {"repos": await run(S.github_repos, tenant)}

    @r.post("/repos")
    async def add_repo(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_repo, tenant, str(b.get("repo") or ""), str(b.get("deploy_workflow") or ""), str(b.get("deploy_ref") or ""),
                         str(b.get("notes") or ""))

    # ---- Phase 5: around the session (schedules + trigger, share link, reviewers' comments)
    @r.get("/schedules")
    async def list_schedules(tenant: str = Depends(current_tenant)):
        from . import around as AR
        return {"schedules": await run(AR.schedules, tenant)}

    @r.post("/schedules")
    async def new_schedule(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import around as AR
        b = _b(body)
        return await run(AR.save_schedule, tenant, "", **{k: b[k] for k in ("title", "repo", "base", "kind", "text", "mode", "days", "at", "enabled", "event", "filter") if k in b})

    @r.patch("/schedules/{sid}")
    async def patch_schedule(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import around as AR
        b = _b(body)
        return await run(AR.save_schedule, tenant, sid, **{k: b[k] for k in ("title", "repo", "base", "kind", "text", "mode", "days", "at", "enabled", "event", "filter") if k in b})

    @r.delete("/schedules/{sid}")
    async def del_schedule(sid: str, tenant: str = Depends(current_tenant)):
        from . import around as AR
        return await run(AR.delete_schedule, tenant, sid)

    @r.post("/schedules/{sid}/run")
    async def run_schedule(sid: str, tenant: str = Depends(current_tenant)):
        from . import around as AR
        return await run(AR.run_schedule, tenant, sid, "now")

    @r.post("/schedules/{sid}/trigger")
    async def make_trigger(sid: str, tenant: str = Depends(current_tenant)):
        from . import around as AR
        return await run(AR.make_trigger, tenant, sid)         # the token is in THIS answer only

    @r.delete("/schedules/{sid}/trigger")
    async def drop_trigger(sid: str, tenant: str = Depends(current_tenant)):
        from . import around as AR
        return await run(AR.drop_trigger, tenant, sid)

    @r.post("/tasks/{tid}/share")
    async def share(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import around as AR
        return await run(AR.share, tenant, tid, bool(_b(body).get("on", True)))

    @r.get("/tasks/{tid}/comments")
    async def pr_comments(tid: str, tenant: str = Depends(current_tenant)):
        from . import around as AR
        return await run(AR.read_comments, tenant, tid)

    @r.patch("/repos/{owner}/{name}")
    async def patch_repo(owner: str, name: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)             # how this repo runs in the box: her setup command, her test command, plain variables
        return await run(S.save_repo, tenant, f"{owner}/{name}", b.get("setup_cmd"), b.get("test_cmd"), b.get("env_vars"),
                         b.get("net_level"), b.get("net_hosts"))

    # ---- Phase 6: a key for one outside host, added by the proxy OUTSIDE the box. Typed only here; never returned.
    @r.put("/repos/{owner}/{name}/secrets")
    async def put_secret(owner: str, name: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_repo_secret, tenant, f"{owner}/{name}", str(b.get("host") or ""), str(b.get("header") or "Authorization"),
                         str(b.get("value") or ""), str(b.get("prefix") or ""))

    @r.delete("/repos/{owner}/{name}/secrets/{host}")
    async def del_secret(owner: str, name: str, host: str, tenant: str = Depends(current_tenant)):
        return await run(S.remove_repo_secret, tenant, f"{owner}/{name}", host)

    # ---- Phase 6: GitHub events for one repo (her tap). The secret is in the answer only when SHE must add the webhook.
    @r.post("/repos/{owner}/{name}/events")
    async def events_on(owner: str, name: str, tenant: str = Depends(current_tenant)):
        from . import events as EV
        return await run(EV.connect, tenant, f"{owner}/{name}")

    @r.delete("/repos/{owner}/{name}/events")
    async def events_off(owner: str, name: str, tenant: str = Depends(current_tenant)):
        from . import events as EV
        return await run(EV.disconnect, tenant, f"{owner}/{name}")

    @r.get("/net")
    async def net_status(tenant: str = Depends(current_tenant)):
        from ..devlab import net as NET
        return await run(NET.status)

    @r.delete("/repos/{owner}/{name}")
    async def del_repo(owner: str, name: str, tenant: str = Depends(current_tenant)):
        return await run(S.remove_repo, tenant, f"{owner}/{name}")

    @r.get("/prs")
    async def prs(repo: str = "", tenant: str = Depends(current_tenant)):
        return {"prs": await run(S.open_prs, tenant, repo)}

    # ---- tasks
    @r.get("/tasks")
    async def list_tasks(status: str = "", limit: int = 40, archived: int = 0, q: str = "", tenant: str = Depends(current_tenant)):
        return {"tasks": await run(S.tasks, tenant, status, limit, bool(archived), q)}

    @r.post("/tasks")
    async def new_task(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        files = b.get("files") or []
        return await run(S.start, tenant, str(b.get("kind") or "write"), str(b.get("text") or ""), str(b.get("repo") or ""),
                         int(b.get("issue") or 0), [str(x) for x in files if x][:10], str(b.get("conv") or ""), "owner")

    # ---- v0.748 HOOLA CODE: the console runs the work in the background and watches it
    @r.post("/tasks/start")
    async def start_bg(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        files = b.get("files") or []
        return await run(S.start_bg, tenant, str(b.get("kind") or "write"), str(b.get("text") or ""), str(b.get("repo") or ""),
                         int(b.get("issue") or 0), [str(x) for x in files if x][:10], str(b.get("conv") or ""),
                         str(b.get("base") or ""), str(b.get("mode") or ""), str(b.get("model") or ""), str(b.get("effort") or ""),
                         b.get("images"), b.get("docs"), b.get("refs"), b.get("also"))

    @r.get("/tasks/{tid}/attach/{index}")
    async def attachment(tid: str, index: int, tenant: str = Depends(current_tenant)):
        raw, kind = await run(S.attachment, tenant, tid, index)       # Phase 3: a picture she attached, for her own bubble
        return Response(content=raw, media_type=kind, headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"})

    @r.post("/tasks/{tid}/note")
    async def note(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.add_note, tenant, tid, str(b.get("text") or ""), b.get("comments"))

    @r.post("/tasks/{tid}/stop")
    async def stop(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.stop, tenant, tid)

    @r.post("/tasks/{tid}/bg/{what}")
    async def bg(tid: str, what: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if what == "plan_ok":
            kw = {"hash_": str(b.get("hash") or ""), "by_tap": True, "note": str(b.get("note") or "")}
        elif what == "revise":
            kw = {"words": str(b.get("text") or ""), "comments": b.get("comments")}
        elif what == "begin":
            kw = {"repo": str(b.get("repo") or "")}
        elif what in ("fix_ci", "fix_comments"):
            kw = {}
        else:
            raise HTTPException(404, "plan_ok | revise | fix_ci | fix_comments | begin")
        return await run(S.in_background, tenant, tid, what, **kw)

    # ---- v0.768 the session list: her own name for a session, archive / unarchive, delete, take a queued note back
    @r.patch("/tasks/{tid}")
    async def patch_task(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b, out = _b(body), None
        if "title" in b:
            out = await run(S.rename, tenant, tid, str(b.get("title") or ""))
        if "archived" in b:
            out = await run(S.archive, tenant, tid, bool(b.get("archived")))
        if "auto_fix" in b:
            out = await run(S.set_auto_fix, tenant, tid, bool(b.get("auto_fix")))
        if out is None:
            raise HTTPException(400, "title | archived | auto_fix")
        return out

    @r.delete("/tasks/{tid}")
    async def delete_task(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.delete_task, tenant, tid)

    # ---- Phase 2: her answer to Hoola's one question, and the Changes pane's "Compare against"
    @r.post("/tasks/{tid}/answer")
    async def answer(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.answer, tenant, tid, str(_b(body).get("text") or ""))

    @r.get("/tasks/{tid}/compare")
    async def compare(tid: str, base: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.compare, tenant, tid, base)

    @r.get("/branches")
    async def branches(repo: str = "", tenant: str = Depends(current_tenant)):
        return {"branches": await run(S.branches, tenant, repo)}

    @r.delete("/tasks/{tid}/note/{index}")
    async def drop_note(tid: str, index: int, tenant: str = Depends(current_tenant)):
        return await run(S.drop_note, tenant, tid, index)

    @r.get("/tasks/{tid}/ws")
    async def ws_view(tid: str, tenant: str = Depends(current_tenant)):
        """v0.784 the session's working copy: checkpoints, to-do list, live / slots."""
        return await run(S.ws_task_view, tenant, tid)

    @r.get("/tasks/{tid}/files")
    async def ws_files(tid: str, path: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.ws_files, tenant, tid, path)

    @r.post("/tasks/{tid}/rewind")
    async def ws_rewind(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.ws_rewind, tenant, tid, int(_b(body).get("n") or 0))

    @r.get("/tasks/{tid}")
    async def get_task(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.get_task, tenant, tid)

    @r.post("/tasks/{tid}/push")
    async def push(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.push, tenant, tid, str(_b(body).get("hash") or ""), by_tap=True)

    @r.post("/tasks/{tid}/plan-ok")
    async def plan_ok(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.plan_ok, tenant, tid, str(b.get("hash") or ""), by_tap=True, note=str(b.get("note") or ""))

    @r.post("/tasks/{tid}/begin")
    async def begin(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.begin, tenant, tid, str(_b(body).get("repo") or ""))

    @r.post("/tasks/{tid}/revise")
    async def revise(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.revise, tenant, tid, str(_b(body).get("text") or ""))

    @r.post("/tasks/{tid}/refresh")
    async def refresh(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.refresh, tenant, tid)

    @r.post("/tasks/{tid}/fix_ci")
    async def fix_ci(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.fix_ci, tenant, tid)

    @r.post("/tasks/{tid}/cancel")
    async def cancel(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.cancel, tenant, tid)

    @r.post("/tasks/{tid}/merge_request")
    async def task_merge(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.merge_request, tenant, method=str(_b(body).get("method") or ""), task=tid)

    # ---- reviews
    @r.get("/reviews")
    async def list_reviews(status: str = "", tenant: str = Depends(current_tenant)):
        return {"reviews": await run(S.reviews, tenant, status)}

    @r.post("/reviews")
    async def new_review(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.review, tenant, str(b.get("repo") or ""), int(b.get("pr") or 0), str(b.get("conv") or ""))

    @r.post("/reviews/{rid}/post")
    async def post_review(rid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.post_review, tenant, rid, str(b.get("hash") or ""), str(b.get("event") or "COMMENT"), by_tap=True,
                         edited_summary=str(b.get("summary") or ""))

    @r.post("/reviews/{rid}/discard")
    async def discard_review(rid: str, tenant: str = Depends(current_tenant)):
        return await run(S.discard_review, tenant, rid)

    # ---- merge / deploy (her tap)
    @r.get("/actions")
    async def list_actions(kind: str = "", status: str = "", tenant: str = Depends(current_tenant)):
        return {"actions": await run(S.actions, tenant, kind, status)}

    @r.post("/merge_request")
    async def merge_request(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.merge_request, tenant, str(b.get("repo") or ""), int(b.get("pr") or 0), str(b.get("method") or ""))

    @r.post("/deploy_request")
    async def deploy_request(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.deploy_request, tenant, str(b.get("repo") or ""), str(b.get("workflow") or ""), str(b.get("ref") or ""),
                         b.get("inputs") if isinstance(b.get("inputs"), dict) else {})

    @r.post("/actions/{aid}/decide")
    async def decide(aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes = true | false")
        return await run(S.decide, tenant, aid, bool(b.get("yes")), str(b.get("hash") or ""), str(b.get("force_reason") or ""), by_tap=True)

    @r.get("/rules")
    async def rules():
        from . import rules as R
        return {"never": list(R.NEVER), "owasp": R.OWASP, "limits": R.LIMITS}

    return r
