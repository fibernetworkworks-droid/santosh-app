"""HTTP routes of the IT Admin Sahayak (/api/itadmin/*). main.py: app.include_router(make_router(require_key, current_tenant)),
and in /auth/google/callback send states starting with "ita_" to `await itadmin_api.finish_page(request)`.

The ONLY way an access / settings change is approved: POST /api/itadmin/changes/{id}/decide from her app (her tap).
Admin console secrets (Microsoft client secret) come in only through PUT /api/itadmin/microsoft and are never returned."""
from __future__ import annotations

import asyncio
import html as _h
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response

from ..config import get_settings


def _page(account: str | None, error: str = "") -> HTMLResponse:
    deep = f"{get_settings().app_redirect_scheme}://itadmin?ok={0 if error else 1}"
    msg = (f"<h2>Google Workspace admin Hoola se juda ✅</h2><p>{_h.escape(account or '')}</p><p>Hoola sirf padhega; badlaav aapki haan se.</p>"
           if not error else f"<h3>Google Workspace nahi juda</h3><p>{_h.escape(error)}</p>")
    return HTMLResponse(f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:system-ui;text-align:center;padding:40px;background:#f3eefb">{msg}
<p><a href="{deep}" style="display:inline-block;background:#6d3fe0;color:#fff;padding:14px 22px;border-radius:14px;text-decoration:none;font-weight:700">App kholiye</a></p>
<script>setTimeout(function(){{location.href={deep!r}}},600);</script></body>""", status_code=400 if error else 200)


async def finish_page(request: Request) -> HTMLResponse:
    from . import connectors as K
    if request.query_params.get("error"):
        return _page(None, request.query_params["error"])
    try:
        v = await asyncio.to_thread(K.google_finish, request.query_params.get("code", ""), request.query_params.get("state", ""))
    except K.ConnError as e:
        return _page(None, str(e))
    return _page(v.get("account"))


def make_router(require_key, current_tenant) -> APIRouter:
    from . import connectors as K
    from . import service as S

    r = APIRouter(prefix="/api/itadmin", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.ItadminError, K.ConnError, ValueError, TypeError) as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    def pick(b: dict, keys) -> dict:
        return {k: b[k] for k in keys if k in b}

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(S.overview, tenant)

    @r.get("/day")
    async def day(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @r.get("/settings")
    async def get_settings_(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.save_settings, tenant, **pick(_b(body), ("org_name", "domain", "admin_name", "standard_systems", "windows",
                                                                     "review_months", "morning_time", "rules", "practices")))

    # ---- licences
    LK = ("name", "kind", "vendor", "plan", "seats_bought", "seats_used", "cost", "cost_per", "per_seat", "renews_on", "auto_renew",
          "owner", "login_with", "notes")

    @r.get("/licences")
    async def list_lic(kind: str = "", tenant: str = Depends(current_tenant)):
        return {"licences": await run(S.licences, tenant, kind)}

    @r.post("/licences")
    async def new_lic(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.save_licence, tenant, **pick(_b(body), LK))

    @r.patch("/licences/{lid}")
    async def patch_lic(lid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.save_licence, tenant, lid, **pick(_b(body), LK))

    @r.delete("/licences/{lid}")
    async def del_lic(lid: str, tenant: str = Depends(current_tenant)):
        return await run(S.remove_licence, tenant, lid)

    @r.post("/licences/{lid}/renewed")
    async def lic_renewed(lid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.renewed, tenant, lid, str(b.get("renews_on") or ""), b.get("cost"))

    @r.get("/renewals")
    async def get_renewals(days: int = 90, tenant: str = Depends(current_tenant)):
        return await run(S.renewals, tenant, days)

    @r.get("/devices")
    async def get_devices(tenant: str = Depends(current_tenant)):
        return await run(S.devices, tenant)

    # ---- people + access
    PK = ("name", "email", "phone", "role", "department", "manager", "status", "join_date", "leave_date", "notes")

    @r.get("/people")
    async def list_people(status: str = "", tenant: str = Depends(current_tenant)):
        return {"people": await run(S.people, tenant, status)}

    @r.post("/people")
    async def new_person(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.save_person, tenant, **pick(_b(body), PK))

    @r.get("/people/{pid}")
    async def get_person(pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.person_view, tenant, pid)

    @r.patch("/people/{pid}")
    async def patch_person(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.save_person, tenant, pid, **pick(_b(body), PK))

    @r.post("/people/{pid}/forget")
    async def forget_person(pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget_person, tenant, pid)

    @r.post("/people/{pid}/{kind}")
    async def jml(pid: str, kind: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        if kind not in ("joiner", "mover", "leaver"):
            raise HTTPException(404, "not found")
        b = _b(body)
        return await run(S.start_checklist, tenant, pid, kind, str(b.get("when") or ""), str(b.get("new_role") or ""))

    @r.get("/checklists")
    async def list_cl(status: str = "open", tenant: str = Depends(current_tenant)):
        return {"checklists": await run(S.checklists, tenant, status)}

    @r.post("/checklists/{cid}/items/{item}")
    async def cl_item(cid: str, item: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.check_item, tenant, cid, item, bool(_b(body).get("done", True)))

    AK = ("person", "system", "account", "level", "shared", "mfa", "notes", "status")

    @r.get("/access")
    async def list_access(person: str = "", system: str = "", status: str = "active", tenant: str = Depends(current_tenant)):
        return {"access": await run(S.access_list, tenant, person, system, status)}

    @r.post("/access")
    async def new_access(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.save_access, tenant, **pick(_b(body), AK))

    @r.patch("/access/{aid}")
    async def patch_access(aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.save_access, tenant, aid, **pick(_b(body), AK))

    # ---- changes (her tap)
    @r.get("/changes")
    async def list_changes(status: str = "", tenant: str = Depends(current_tenant)):
        return {"changes": await run(S.changes, tenant, status)}

    @r.post("/changes")
    async def new_change(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.request_change, tenant, str(b.get("kind") or ""), str(b.get("person") or ""), str(b.get("access") or ""),
                         str(b.get("system") or ""), str(b.get("target") or ""), str(b.get("what") or ""), str(b.get("licence") or ""))

    @r.post("/changes/{cid}/decide")
    async def decide(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if "yes" not in b:
            raise HTTPException(400, "yes (true / false) chahiye")
        return await run(S.decide_change, tenant, cid, bool(b["yes"]), str(b.get("hash") or ""), str(b.get("reason") or ""), by_tap=True)

    @r.post("/changes/{cid}/done")
    async def change_done(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.change_done, tenant, cid, bool(b.get("ok", True)), str(b.get("note") or ""))

    # ---- review
    @r.get("/reviews")
    async def list_reviews(tenant: str = Depends(current_tenant)):
        return {"reviews": await run(S.reviews, tenant)}

    @r.post("/reviews")
    async def start_review(tenant: str = Depends(current_tenant)):
        return await run(S.start_review, tenant)

    @r.post("/reviews/{rid}/items/{aid}")
    async def review_item(rid: str, aid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.review_item, tenant, rid, aid, str(_b(body).get("decision") or ""))

    @r.post("/reviews/{rid}/close")
    async def close_review(rid: str, tenant: str = Depends(current_tenant)):
        return await run(S.close_review, tenant, rid)

    # ---- guides + questions
    @r.get("/guides")
    async def list_guides(status: str = "", tenant: str = Depends(current_tenant)):
        return {"guides": await run(S.guides, tenant, status)}

    @r.post("/guides")
    async def new_guide(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.write_guide, tenant, str(b.get("topic") or ""), str(b.get("words") or ""), b.get("steps"),
                         str(b.get("audience") or ""), b.get("tags"), str(b.get("guide") or ""))

    @r.get("/guides/{gid}")
    async def get_guide(gid: str, tenant: str = Depends(current_tenant)):
        return await run(S.guide_view, tenant, gid)

    @r.put("/guides/{gid}/steps/{n}")
    async def put_step(gid: str, n: int, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.edit_step, tenant, gid, n, str(b.get("text") or ""), bool(b.get("remove")))

    @r.post("/guides/{gid}/shot")
    async def guide_shot(gid: str, n: int = Form(...), file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        data = await file.read()
        return await run(S.add_shot, tenant, gid, n, data, file.filename or "shot.png")

    @r.get("/shots/{sid}")
    async def get_shot(sid: str, tenant: str = Depends(current_tenant)):
        data, mime = await run(S.shot_bytes, tenant, sid)
        return Response(data, media_type=mime, headers={"Cache-Control": "private, max-age=3600"})

    @r.post("/guides/{gid}/publish")
    async def publish(gid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.publish_guide, tenant, gid, archive=bool(_b(body).get("archive")))

    @r.post("/guides/{gid}/restore")
    async def restore(gid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.restore_version, tenant, gid, int(_b(body).get("version") or 0))

    @r.post("/guides/{gid}/file")
    async def gfile(gid: str, tenant: str = Depends(current_tenant)):
        return await run(S.guide_file, tenant, gid)

    @r.post("/guides/{gid}/feedback")
    async def gfeedback(gid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.guide_feedback, tenant, gid, bool(_b(body).get("helped")))

    @r.post("/ask")
    async def ask(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.ask, tenant, str(b.get("text") or ""), str(b.get("person") or ""))

    @r.get("/gaps")
    async def get_gaps(days: int = 30, tenant: str = Depends(current_tenant)):
        return {"gaps": await run(S.gaps, tenant, days)}

    @r.post("/register")
    async def register(tenant: str = Depends(current_tenant)):
        return await run(S.register_file, tenant)

    # ---- admin consoles
    @r.get("/connections")
    async def conns(tenant: str = Depends(current_tenant)):
        return await run(K.status, tenant)

    @r.post("/google/start")
    async def g_start(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return {"url": await run(K.google_start, tenant, str(_b(body).get("mode") or "read"))}

    @r.put("/microsoft")
    async def ms_put(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(K.ms_save, tenant, str(b.get("directory_id") or ""), str(b.get("client_id") or ""),
                         str(b.get("client_secret") or ""), str(b.get("mode") or "read"))

    @r.delete("/{provider}")
    async def conn_del(provider: str, tenant: str = Depends(current_tenant)):
        if provider not in ("google", "microsoft"):
            raise HTTPException(404, "not found")
        return await run(K.forget, tenant, provider)

    @r.post("/sync")
    async def do_sync(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.sync, tenant, str(_b(body).get("provider") or ""))

    return r
