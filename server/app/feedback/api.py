"""HTTP routes for Feedback Sahayak (Profile > Feedback sahayak).

main.py: `app.include_router(feedback_api.make_router(require_key, current_tenant))`, and in /auth/google/callback send
states starting with "fbk_" to `await feedback_api.finish_page(request)`.
Public (no key, verified by the signed token): GET / POST /api/feedback/s/{token} = her survey page.
"""
from __future__ import annotations

import asyncio
import html as _h

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse

from ..config import get_settings


def _run(fn, *a, **k):
    from . import gbp
    from . import service as S
    try:
        return fn(*a, **k)
    except (S.FeedbackError, gbp.GbpError, ValueError) as e:
        raise HTTPException(400, str(e))


def _page(address: str | None, error: str = "") -> HTMLResponse:
    scheme = get_settings().app_redirect_scheme
    deep = f"{scheme}://feedback?ok={0 if error else 1}"
    msg = (f"<h2>Google reviews Hoola se jude! ✅</h2><p>{_h.escape(address or '')}</p>" if not error else
           f"<h3>Google reviews nahi jude</h3><p>{_h.escape(error)}</p>")
    return HTMLResponse(f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:system-ui;text-align:center;padding:40px;background:#f3eefb">{msg}
<p><a href="{deep}" style="display:inline-block;background:#6d3fe0;color:#fff;padding:14px 22px;border-radius:14px;text-decoration:none;font-weight:700">App kholiye</a></p>
<script>setTimeout(function(){{location.href={deep!r}}},600);</script></body>""", status_code=400 if error else 200)


async def finish_page(request: Request) -> HTMLResponse:
    from . import gbp
    if request.query_params.get("error"):
        return _page(None, request.query_params["error"])
    try:
        v = await asyncio.to_thread(gbp.finish_link, request.query_params.get("code", ""), request.query_params.get("state", ""))
    except gbp.GbpError as e:
        return _page(None, str(e))
    return _page(v["address"])


_PUBLIC_HEADERS = {"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'",
                   "X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
                   "X-Content-Type-Options": "nosniff"}


def make_router(require_key, current_tenant) -> APIRouter:
    from . import gbp
    from . import service as S
    r = APIRouter()
    key = [Depends(require_key)]

    @r.get("/api/feedback", dependencies=key)
    async def fb_all(days: int = 0, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.summary, tenant, days or None)

    @r.get("/api/feedback/items", dependencies=key)
    async def fb_items(theme: str = "", source: str = "", label: str = "", flagged: bool = False, q: str = "", unreplied: bool = False,
                       limit: int = 50, days: int = 0, tenant: str = Depends(current_tenant)):
        return {"items": await asyncio.to_thread(_run, S.items, tenant, theme, source, label, flagged, q, unreplied, limit, days)}

    @r.post("/api/feedback/text", dependencies=key)
    async def fb_text(body: dict, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.add_text, tenant, str(body.get("text") or ""), str(body.get("source") or "text"),
                                       body.get("stars"), str(body.get("author") or ""), "", body.get("score"))

    @r.post("/api/feedback/import", dependencies=key)
    async def fb_import(file: UploadFile = File(...), source: str = Form(""), tenant: str = Depends(current_tenant)):
        data = await file.read()
        if len(data) > 25 * 1024 * 1024:
            raise HTTPException(413, "File 25 MB se badi.")
        return await asyncio.to_thread(_run, S.import_file, tenant, file.filename or "sheet.csv", data, source)

    @r.post("/api/feedback/import_file", dependencies=key)
    async def fb_import_id(body: dict, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.import_file, tenant, "", None, str(body.get("source") or ""), str(body.get("file_id") or ""))

    @r.post("/api/feedback/sync", dependencies=key)
    async def fb_sync(body: dict, tenant: str = Depends(current_tenant)):
        what = str(body.get("what") or "")
        if what == "google":
            return await asyncio.to_thread(_run, S.sync_google, tenant)
        if what == "forms":
            return await asyncio.to_thread(_run, S.sync_forms, tenant, str(body.get("form") or ""))
        if what == "inbox":
            return await asyncio.to_thread(_run, S.sync_inbox, tenant, int(body.get("days") or 30))
        if what == "calls":
            return await asyncio.to_thread(_run, S.sync_calls, tenant, int(body.get("days") or 90))
        raise HTTPException(400, "what = google | forms | inbox | calls")

    @r.get("/api/feedback/themes", dependencies=key)
    async def fb_themes(days: int = 0, source: str = "", tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.themes, tenant, days or None, source)

    @r.post("/api/feedback/themes/{tkey}", dependencies=key)
    async def fb_theme(tkey: str, body: dict, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.theme_note, tenant, tkey, body.get("label"), body.get("fixed_on"), body.get("note"),
                                       body.get("ignored"))

    @r.get("/api/feedback/fix_first", dependencies=key)
    async def fb_fix(days: int = 0, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.fix_first, tenant, days or None)

    @r.get("/api/feedback/scores", dependencies=key)
    async def fb_scores(days: int = 0, source: str = "", tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.scores, tenant, days or None, source)

    @r.get("/api/feedback/flags", dependencies=key)
    async def fb_flags(tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.flagged, tenant)

    @r.post("/api/feedback/items/{iid}/reply", dependencies=key)
    async def fb_reply(iid: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.reply_draft, tenant, iid, "", str((body or {}).get("note") or ""))

    @r.delete("/api/feedback/items/{iid}", dependencies=key)
    async def fb_forget(iid: str, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.forget_item, tenant, iid)

    @r.get("/api/feedback/replies", dependencies=key)
    async def fb_replies(status: str = "", tenant: str = Depends(current_tenant)):
        return {"replies": await asyncio.to_thread(_run, S.replies, tenant, status)}

    @r.post("/api/feedback/replies/draft_all", dependencies=key)
    async def fb_draft_all(body: dict | None = None, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.reply_drafts_all, tenant, int((body or {}).get("limit") or 10))

    @r.post("/api/feedback/replies/{rid}/decide", dependencies=key)
    async def fb_decide(rid: str, body: dict, tenant: str = Depends(current_tenant)):
        """HER tap: the only way a reply becomes public."""
        return await asyncio.to_thread(_run, S.reply_decide, tenant, rid, bool(body.get("yes")), str(body.get("hash") or ""),
                                       body.get("text"))

    @r.post("/api/feedback/replies/{rid}/done", dependencies=key)
    async def fb_done(rid: str, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.reply_done, tenant, rid)

    @r.get("/api/feedback/settings", dependencies=key)
    async def fb_settings(tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.settings, tenant)

    @r.put("/api/feedback/settings", dependencies=key)
    async def fb_settings_put(body: dict, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.save_settings, tenant, **{k: v for k, v in body.items() if isinstance(k, str)})

    @r.get("/api/feedback/surveys", dependencies=key)
    async def fb_surveys(tenant: str = Depends(current_tenant)):
        return {"surveys": await asyncio.to_thread(_run, S.surveys, tenant)}

    @r.post("/api/feedback/surveys", dependencies=key)
    async def fb_survey_new(body: dict, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.survey_new, tenant, str(body.get("kind") or "nps"), str(body.get("title") or ""),
                                       str(body.get("question") or ""), str(body.get("follow_up") or ""), str(body.get("language") or ""))

    @r.post("/api/feedback/surveys/{sid}/active", dependencies=key)
    async def fb_survey_active(sid: str, body: dict, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.survey_close, tenant, sid, bool(body.get("active")))

    @r.post("/api/feedback/report", dependencies=key)
    async def fb_report(body: dict | None = None, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, S.report_file, tenant, int((body or {}).get("days") or 0) or None)

    @r.get("/api/feedback/alerts", dependencies=key)
    async def fb_alerts(tenant: str = Depends(current_tenant)):
        return {"alerts": await asyncio.to_thread(_run, S.alerts, tenant, 50)}

    @r.get("/api/feedback/google", dependencies=key)
    async def fb_google(tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(gbp.status, tenant)

    @r.get("/api/feedback/google/link", dependencies=key)
    async def fb_google_link(tenant: str = Depends(current_tenant)):
        return {"url": await asyncio.to_thread(_run, gbp.start_link, tenant)}

    @r.get("/api/feedback/google/locations", dependencies=key)
    async def fb_google_locs(tenant: str = Depends(current_tenant)):
        return {"locations": await asyncio.to_thread(_run, gbp.locations, tenant)}

    @r.put("/api/feedback/google/location", dependencies=key)
    async def fb_google_loc(body: dict, tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(_run, gbp.pick_location, tenant, str(body.get("location") or ""))

    @r.delete("/api/feedback/google", dependencies=key)
    async def fb_google_forget(tenant: str = Depends(current_tenant)):
        return await asyncio.to_thread(gbp.forget, tenant)

    # ---- public survey page (signed token; no app key) ----
    @r.get("/api/feedback/s/{token}")
    async def fb_public(token: str):
        code, page = await asyncio.to_thread(S.public_page, token)
        return HTMLResponse(page, status_code=code, headers=_PUBLIC_HEADERS)

    @r.post("/api/feedback/s/{token}")
    async def fb_public_post(token: str, request: Request):
        try:
            form = dict(await request.form())
        except Exception:
            form = {}
        ip = (request.headers.get("cf-connecting-ip") or request.headers.get("x-real-ip") or
              (request.client.host if request.client else ""))
        code, page = await asyncio.to_thread(S.public_submit, token, {k: str(v) for k, v in form.items()}, ip)
        return HTMLResponse(page, status_code=code, headers=_PUBLIC_HEADERS)

    return r
