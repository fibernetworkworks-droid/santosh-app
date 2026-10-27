"""HTTP routes of the Developer Sahayak (/api/devsahayak/*). main.py: app.include_router(make_router(require_key, current_tenant)).

The ONLY ways something happens in her GitHub that she has to agree to:
  POST /api/devsahayak/tasks/{id}/push          (open the PR of a prepared change: public repos / ask_before_pr)
  POST /api/devsahayak/reviews/{id}/post        (post Hoola's draft review, her chosen event)
  POST /api/devsahayak/actions/{id}/decide      (MERGE / DEPLOY)
The GitHub token is accepted only here (PUT /token), never through the chat tool."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


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

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("review_post", "ask_before_pr", "draft_pr", "allow_workflows", "merge_method", "max_files", "max_lines", "rules", "default_repo")
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

    @r.delete("/repos/{owner}/{name}")
    async def del_repo(owner: str, name: str, tenant: str = Depends(current_tenant)):
        return await run(S.remove_repo, tenant, f"{owner}/{name}")

    @r.get("/prs")
    async def prs(repo: str = "", tenant: str = Depends(current_tenant)):
        return {"prs": await run(S.open_prs, tenant, repo)}

    # ---- tasks
    @r.get("/tasks")
    async def list_tasks(status: str = "", limit: int = 40, tenant: str = Depends(current_tenant)):
        return {"tasks": await run(S.tasks, tenant, status, limit)}

    @r.post("/tasks")
    async def new_task(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        files = b.get("files") or []
        return await run(S.start, tenant, str(b.get("kind") or "write"), str(b.get("text") or ""), str(b.get("repo") or ""),
                         int(b.get("issue") or 0), [str(x) for x in files if x][:10], str(b.get("conv") or ""), "owner")

    @r.get("/tasks/{tid}")
    async def get_task(tid: str, tenant: str = Depends(current_tenant)):
        return await run(S.get_task, tenant, tid)

    @r.post("/tasks/{tid}/push")
    async def push(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.push, tenant, tid, str(_b(body).get("hash") or ""), by_tap=True)

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
