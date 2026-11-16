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


APP_PACKAGE = "com.newtika.santosh"


def _android(request: Any) -> bool:
    return "android" in str(request.headers.get("user-agent") or "").lower()


def _done_url(request: Any, ok: bool, acc: str) -> str:
    from urllib.parse import urlencode
    from ..config import get_settings
    base = (get_settings().public_base_url or "").strip().rstrip("/") or str(request.base_url).rstrip("/")
    return f"{base}/api/devsahayak/github/done?" + urlencode({"ok": 1 if ok else 0, "acc": acc})


def github_intent(ok: bool, fallback: str = "") -> str:
    """v0.956 santosh://github?ok=1 as an Android intent link: Chrome opens an app from a redirect or a tap only this
    way (a page script jumping to santosh:// on a timer is blocked), and with no app it opens the fallback page."""
    from urllib.parse import quote
    fb = f"S.browser_fallback_url={quote(fallback, safe='')};" if fallback else ""
    return f"intent://github?ok={1 if ok else 0}#Intent;scheme=santosh;package={APP_PACKAGE};{fb}end"


def github_page(ok: bool, acc: str, why: str, android: bool) -> str:
    from ..bazar import donepage
    head = "GitHub connected" if ok else "Could not connect"
    line = (f"Hoola can now work on the repositories you chose{(' on ' + acc) if acc else ''}. Tap below to go back to "
            "Hoola.") if ok else (why or "Please try again from the app.")
    link = github_intent(ok) if android else "santosh://github?ok=" + ("1" if ok else "0")
    return donepage.render(ok, head, line, link, "GitHub")


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

    @p.get("/made/{tid}/{mid}/{v}/{name}")
    async def made_file(tid: str, mid: str, v: int, name: str, exp: int = 0, sig: str = ""):
        """v0.939 a thing Hoola Code made, on its signed link (her viewer's WebView / download). HTML is served with a
        sandbox CSP: its own opaque origin, no network but Google Fonts."""
        from . import made as MD
        got = await asyncio.to_thread(MD.open_file, tid, mid, v, name, exp, sig)
        if got is None:
            raise HTTPException(404, "This link is not active.")
        body, ctype, head = got
        return Response(content=body, media_type=ctype, headers=head)

    @p.get("/labcheck")
    async def labcheck(request: Request):
        """Phase 6: for `python -m app.devlab net` - says whether a header arrived, as a fingerprint, never the value."""
        import hashlib
        v = request.headers.get("x-hoola-lab-check") or ""
        return {"seen": hashlib.sha256(v.encode()).hexdigest()[:16] if v else ""}

    # ---- v0.941 the helper on HER server talks to Hoola here. Its only credential is its token (we keep its hash).
    def _bearer(request: Request) -> str:
        auth = request.headers.get("authorization") or ""
        return auth[7:].strip() if auth.lower().startswith("bearer ") else ""

    async def _vps(fn, *a):
        from . import vps as V
        try:
            return await asyncio.to_thread(fn, *a)
        except V.VpsError as e:
            raise HTTPException(400, str(e))

    @p.post("/vps/enroll")
    async def vps_enroll(body: dict = Body(default={})):
        from . import vps as V
        b = dict(body or {})
        return await _vps(V.enroll, str(b.get("code") or ""), b.get("facts") if isinstance(b.get("facts"), dict) else {})

    @p.post("/vps/check-in")
    async def vps_checkin(request: Request, body: dict = Body(default={})):
        from . import vps as V
        b = dict(body or {})
        return await _vps(V.check_in, _bearer(request), b.get("facts") if isinstance(b.get("facts"), dict) else {})

    @p.post("/vps/report")
    async def vps_report(request: Request, body: dict = Body(default={})):
        from . import vps as V
        b = dict(body or {})
        return await _vps(V.report, _bearer(request), str(b.get("cmd_id") or ""), int(b.get("exit_code") or 0), str(b.get("output") or ""))

    @p.get("/github/installed")
    async def github_installed(request: Request, installation_id: int = 0, setup_action: str = "", state: str = "",
                               code: str = ""):
        """v0.942 the GitHub App's Setup URL, v0.956 also its sign-in callback: binds the installation to her tenant
        (only one GitHub's sign-in shows is hers, when the App has a client id + secret), then sends her back."""
        from fastapi.responses import RedirectResponse
        from . import service as S
        out = await asyncio.to_thread(S.github_installed, int(installation_id or 0), state, setup_action, code)
        if out.get("redirect"):                 # v0.956 on to GitHub's sign-in / install page, then back here
            return RedirectResponse(str(out["redirect"]), status_code=302)
        ok = bool(out.get("ok"))
        acc = str(out.get("account") or "")
        if ok and _android(request):            # v0.956 straight back into the app: an intent link in the same redirect
            return RedirectResponse(github_intent(True, _done_url(request, True, acc)), status_code=302)
        return Response(content=github_page(ok, acc, str(out.get("why") or ""), _android(request)),
                        media_type="text/html; charset=utf-8")

    @p.get("/github/done")
    async def github_done(request: Request, ok: int = 0, acc: str = ""):
        """v0.956 the page the intent link falls back to (the app could not be opened by itself): one tap back."""
        return Response(content=github_page(bool(ok), acc[:80], "", _android(request)), media_type="text/html; charset=utf-8")
    return p


def make_install_router() -> APIRouter:
    """v0.941 the two files her server fetches at setup: GET /vps/install (the one line's script) and /vps/agent.py.
    The 6-digit code is her own bash argument, so the SAME script serves everyone and carries no secret."""
    from . import vps as V
    g = APIRouter()

    @g.get("/vps/install")
    async def vps_install():
        try:
            text = await asyncio.to_thread(V.install_script)
        except V.VpsError as e:
            raise HTTPException(404, str(e))
        return Response(content=text, media_type="text/x-shellscript; charset=utf-8")

    @g.get("/vps/agent.py")
    async def vps_agent():
        try:
            text = await asyncio.to_thread(V.agent_source)
        except V.VpsError as e:
            raise HTTPException(404, str(e))
        return Response(content=text, media_type="text/x-python; charset=utf-8")

    return g


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

    @r.get("/memory")
    async def memory_list(repo: str = "", q: str = "", tenant: str = Depends(current_tenant)):
        """Hoola Code memory: what Hoola remembers about one repo (newest first), or a search in it."""
        from . import memory as M
        if not repo:
            raise HTTPException(400, "Name the repo (owner/name).")
        rows = await run(M.search, tenant, repo, q, "", 50)
        return {"on": M.on(), "repo": repo, "observations": rows, "summaries": await run(M.summaries, tenant, repo, 10),
                "counts": await run(M.counts, tenant, repo)}

    @r.get("/memory/{oid}")
    async def memory_one(oid: int, repo: str = "", tenant: str = Depends(current_tenant)):
        from . import memory as M
        rows = await run(M.get, tenant, repo, [oid])
        if not rows:
            raise HTTPException(404, "No such memory.")
        return rows[0]

    @r.delete("/memory/{oid}")
    async def memory_forget(oid: int, kind: str = "obs", tenant: str = Depends(current_tenant)):
        from . import memory as M
        ok = await run(M.forget_summary if kind == "summary" else M.forget, tenant, oid)
        if not ok:
            raise HTTPException(404, "No such memory.")
        return {"ok": True}

    @r.delete("/memory")
    async def memory_forget_repo(repo: str = "", tenant: str = Depends(current_tenant)):
        from . import memory as M
        if not repo:
            raise HTTPException(400, "Name the repo (owner/name).")
        return {"ok": True, "removed": await run(M.forget_repo, tenant, repo)}

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
                         b.get("images"), b.get("docs"), b.get("refs"), b.get("also"), "", str(b.get("env") or ""))

    # ---- v0.878 ENVIRONMENTS (Claude Code's cloud environments): picked on the new-session screen
    async def env_run(fn, *a):
        from . import envs as EV
        try:
            return await asyncio.to_thread(fn, *a)
        except EV.EnvError as e:
            raise HTTPException(400, str(e))

    @r.get("/envs")
    async def envs_list(archived: bool = False, tenant: str = Depends(current_tenant)):
        from . import envs as EV
        return await env_run(EV.list_envs, tenant, archived)

    @r.post("/envs")
    async def envs_create(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import envs as EV
        return await env_run(EV.create_env, tenant, _b(body))

    @r.patch("/envs/{eid}")
    async def envs_update(eid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import envs as EV
        return await env_run(EV.update_env, tenant, eid, _b(body))

    @r.post("/envs/{eid}/archive")
    async def envs_archive(eid: str, tenant: str = Depends(current_tenant)):
        from . import envs as EV
        return await env_run(EV.archive_env, tenant, eid)

    @r.put("/tasks/{tid}/env")
    async def task_env(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import envs as EV
        return await env_run(EV.set_session_env, tenant, tid, str(_b(body).get("env") or ""))

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

    @r.get("/tasks/{tid}/shots/{name}")
    async def look_shot(tid: str, name: str, tenant: str = Depends(current_tenant)):
        """v0.943 a screenshot Hoola Code took of the page it changed."""
        from fastapi.responses import FileResponse
        p = await run(S.look_shot, tenant, tid, name)
        if p is None:
            raise HTTPException(404, "No such screenshot.")
        return FileResponse(str(p), media_type="image/png")

    @r.post("/tasks/{tid}/rewind")
    async def ws_rewind(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.ws_rewind, tenant, tid, int(_b(body).get("n") or 0))

    @r.get("/tasks/{tid}/made/{mid}")
    async def made_detail(tid: str, mid: str, v: int = 0, tenant: str = Depends(current_tenant)):
        """v0.939 one thing it made: versions, the document / sheet preview, a signed link to the file."""
        return await run(S.made_detail, tenant, tid, mid, v)

    @r.post("/tasks/{tid}/made/{mid}/restore")
    async def made_restore(tid: str, mid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.made_restore, tenant, tid, mid, int(_b(body).get("v") or 0))

    @r.get("/tasks/{tid}/stream")
    async def task_stream(tid: str, request: Request, tenant: str = Depends(current_tenant)):
        """v0.962 the words Hoola is writing, pushed to her phone as they come (it asked once a second, so words came in
        bursts): every 100 ms what changed - the added words (`add`, or the whole `live` when a new reply starts), the
        step working now, a new step number, a round starting or ending. Live only, nothing stored; `: ping` when quiet."""
        from fastapi.responses import StreamingResponse
        try:
            real = await asyncio.to_thread(S.task_id, tenant, tid)
        except S.DevError:
            raise HTTPException(404, "Not found")   # the phone's stream ends quietly instead of retrying for ever

        async def gen():
            last: dict[str, Any] = {}
            quiet = 0.0
            yield f"data: {json.dumps({'id': 0, 'kind': 'code_open', 'payload': S.live_state(real)}, ensure_ascii=False)}\n\n"
            last = S.live_state(real)
            while True:
                if await request.is_disconnected():
                    break
                await asyncio.sleep(0.1)
                cur = S.live_state(real)
                ev = S.live_delta(last, cur)
                last = cur
                if ev:
                    quiet = 0.0
                    yield f"data: {json.dumps({'id': 0, 'kind': 'code_live', 'payload': ev}, ensure_ascii=False)}\n\n"
                else:
                    quiet += 0.1
                    if quiet >= 15:
                        quiet = 0.0
                        yield ": ping\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @r.get("/tasks/{tid}")
    async def get_task(tid: str, since: int | None = None, tenant: str = Depends(current_tenant)):
        return await run(S.get_task, tenant, tid, since)

    @r.post("/tasks/{tid}/push")
    async def push(tid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        # v0.933 her tap is checked at once; the commit, the PR and Hoola's own review run in the background
        return await run(S.in_background, tenant, tid, "push", hash_=str(_b(body).get("hash") or ""))

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

    # ---- v0.941 HOOLA CODE ON YOUR SERVER (she pairs a VPS; her server calls out; every change is her tap)
    @r.get("/servers")
    async def servers(tenant: str = Depends(current_tenant)):
        from . import vps as V
        return await run(V.overview, tenant)

    @r.post("/servers/pair")
    async def servers_pair(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import vps as V
        return await run(V.pair_start, tenant, str(_b(body).get("name") or ""))

    @r.get("/servers/{sid}")
    async def server_detail(sid: str, tenant: str = Depends(current_tenant)):
        from . import vps as V
        return await run(V.detail, tenant, sid)

    @r.put("/servers/{sid}")
    async def server_access(sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import vps as V
        b = _b(body)
        return await run(V.set_access, tenant, sid,
                         access=b.get("access"), folders=b.get("folders"), admin_cmds=b.get("admin_cmds"),
                         auto_off_days=b.get("auto_off_days"), name=b.get("name"))

    @r.post("/servers/{sid}/disconnect")
    async def server_disconnect(sid: str, tenant: str = Depends(current_tenant)):
        from . import vps as V
        return await run(V.disconnect, tenant, sid)

    @r.post("/servers/{sid}/cmds/{cid}/decide")
    async def server_decide(sid: str, cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import vps as V
        return await run(V.decide, tenant, cid, str(_b(body).get("choice") or ""))

    # ---- v0.942 connect GitHub like Claude Code (a GitHub App install, no pasted token)
    @r.get("/github/connect")
    async def github_connect(tenant: str = Depends(current_tenant)):
        return await run(S.github_connect_url, tenant)

    @r.post("/github/disconnect")
    async def github_disconnect(tenant: str = Depends(current_tenant)):
        return await run(S.github_disconnect, tenant)

    return r
