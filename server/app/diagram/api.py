"""HOOLA DIAGRAM routes (D3): the live draw.io editor and her console's way to open it.

  GET  /diagram-edit/{token}            the page around the editor (host) - token = one diagram, one person, expires
  GET  /diagram-edit/e/{path}           the pinned draw.io editor's files (public, unmodified; index.html gets Hoola's
                                        bridge script tag at serve time - the file on disk is never edited)
  GET  /diagram-edit/hoola/{name}       host.js / bridge.js
  GET  /api/diagram/live/{token}/state  the diagram + its revision
  POST /api/diagram/live/{token}/save   her edit (xml + the editor's own SVG export)
  POST /api/diagram/live/{token}/select her selection
  GET  /api/diagram/live/{token}/poll   Hoola's changes since a revision
  GET  /api/diagram/live/{token}/file   the .drawio file
  GET  /api/diagram/open/{artifact_id}  (signed-in) how to open a diagram page by hand: the editor link (draw.io) or
                                        "convertible" (archify / diagram-design: Hoola redraws it as draw.io first)

Every editor response is sandboxed (its own origin, no access to her sign-in, cookies or storage); the live API takes
only the token (credentials are never sent - the editor's origin is opaque) and answers any origin, because the token
IS the permission and it names one diagram."""
from __future__ import annotations

import html
import json
import mimetypes
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from . import drawio as DR
from . import live as L
from . import service as S

HERE = Path(__file__).resolve().parent
EDITOR_CSP = ("sandbox allow-scripts allow-popups allow-modals allow-downloads; default-src 'self' data: blob:; "
              "script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: "
              "blob:; font-src 'self' data:; connect-src 'self'; frame-src 'self'; form-action 'none'; base-uri 'self'")
HEADERS = {"Content-Security-Policy": EDITOR_CSP, "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
           "X-Robots-Tag": "noindex, nofollow", "Access-Control-Allow-Origin": "*",
           "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()"}
WORDS = {"loading": "Opening the editor…", "ready": "Ready - your changes save by themselves",
         "saving": "Saving…", "saved": "Saved", "uptodate": "Saved", "syncing": "Bringing in Hoola's change…",
         "notsaved": "Not saved - check the diagram", "offline": "Offline - not saved yet",
         "hoola": "Hoola changed {n} shapes (Ctrl+Z takes it back)", "notapplied": "Hoola's change could not be applied",
         "gone": "This diagram is no longer here", "download": "Download .drawio"}
HOST = """<!doctype html><html lang="{lang}" dir="{dir}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
:root{{color-scheme:light dark;--bg:#fff;--ink:#1f1d24;--mut:#6b6875;--line:#e7e5ec}}
@media (prefers-color-scheme:dark){{:root{{--bg:#17161b;--ink:#ecebf0;--mut:#a3a0ad;--line:#2c2a33}}}}
html,body{{margin:0;height:100%;background:var(--bg);color:var(--ink);font:14px/1.4 system-ui,sans-serif}}
.bar{{display:flex;align-items:center;gap:12px;height:44px;padding:0 12px;border-bottom:1px solid var(--line)}}
.t{{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:45%}}
#st{{color:var(--mut);flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
button{{font:inherit;border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:8px;padding:6px 10px;cursor:pointer}}
iframe{{display:block;border:0;width:100%;height:calc(100% - 45px)}}
</style></head><body><div class="bar"><span class="t">{title}</span><span id="st" role="status" aria-live="polite"></span>
<button type="button" id="dl">{dl}</button></div>
<iframe id="ed" title="draw.io" src="/diagram-edit/e/index.html?embed=1&amp;proto=json&amp;spin=0&amp;ui=simple&amp;offline=1&amp;noSaveBtn=1&amp;noExitBtn=1&amp;saveAndExit=0&amp;lang={dlang}"></iframe>
<script>window.HOOLA_DIAGRAM={conf};window.HOOLA_WORDS={words};</script><script src="/diagram-edit/hoola/host.js"></script>
</body></html>"""
RTL = ("ar", "he", "fa", "ur", "ps", "sd", "yi", "dv", "ku")
DRAWIO_LANGS = {"zh": "zh", "zh-tw": "zh-tw", "pt-br": "pt-br"}


def _who(token: str) -> tuple[str, str]:
    w = L.verify(token)
    if not w:
        raise HTTPException(403, "This editor link has expired - open the diagram again from Hoola.")
    return w


def _j(data: dict, status: int = 200) -> JSONResponse:
    return JSONResponse(data, status_code=status, headers={"Access-Control-Allow-Origin": "*",
                                                         "Cache-Control": "no-store"})


def make_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter()

    @r.get("/diagram-edit/hoola/{name}")
    async def hoola_js(name: str):
        if name not in ("host.js", "bridge.js"):
            raise HTTPException(404)
        return Response((HERE / "web" / name).read_text("utf-8"), media_type="application/javascript", headers=HEADERS)

    @r.get("/diagram-edit/e/{path:path}")
    async def editor_file(path: str):
        if not DR.ready():
            raise HTTPException(503, "The draw.io editor is not set up on this server (vps-ops diagram_setup).")
        root = DR.editor_dir().resolve()
        f = (root / path).resolve()
        if root not in f.parents or not f.is_file() or f.name.startswith("__"):
            raise HTTPException(404)
        if f.name == "index.html" and f.parent == root:
            t = f.read_text("utf-8")
            t = t.replace("<head>", '<head><script src="/diagram-edit/hoola/bridge.js"></script>', 1)
            return HTMLResponse(t, headers=HEADERS)
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        return Response(f.read_bytes(), media_type=ctype, headers={**HEADERS, "Cache-Control": "public, max-age=86400"})

    @r.get("/diagram-edit/{token}")
    async def host(token: str, lang: str = "en"):
        tenant, did = _who(token)
        s = L.state(tenant, did)
        if not s.get("ok"):
            raise HTTPException(404, "This diagram is no longer here.")
        lg = (lang or "en").lower()[:8]
        page = HOST.format(lang=html.escape(lg), dir="rtl" if lg.split("-")[0] in RTL else "ltr",
                           title=html.escape(s.get("title") or "Diagram"), dl=html.escape(WORDS["download"]),
                           dlang=html.escape(DRAWIO_LANGS.get(lg, lg.split("-")[0])),
                           conf=json.dumps({"token": token, "title": s.get("title") or "diagram"}).replace("</", "<\\/"),
                           words=json.dumps(WORDS).replace("</", "<\\/"))
        return HTMLResponse(page, headers=HEADERS)

    @r.options("/api/diagram/live/{token}/{what}")
    async def live_preflight(token: str, what: str):
        # the editor's origin is opaque ("null"), so a JSON POST asks first; the token in the address is the permission
        return Response(status_code=204, headers={"Access-Control-Allow-Origin": "*",
                                                  "Access-Control-Allow-Methods": "GET, POST",
                                                  "Access-Control-Allow-Headers": "Content-Type",
                                                  "Access-Control-Max-Age": "600"})

    @r.get("/api/diagram/live/{token}/state")
    async def live_state(token: str):
        tenant, did = _who(token)
        return _j(L.state(tenant, did))

    @r.post("/api/diagram/live/{token}/save")
    async def live_save(token: str, body: dict = Body(default={})):
        tenant, did = _who(token)
        xml, svg = str(body.get("xml") or ""), str(body.get("svg") or "")
        if len(xml) > 2_000_000 or len(svg) > 4_000_000:
            return _j({"ok": False, "error": "too large"}, 413)
        import asyncio
        return _j(await asyncio.to_thread(L.save, tenant, did, xml, svg, int(body.get("applied_rev") or 0)))

    @r.post("/api/diagram/live/{token}/select")
    async def live_select(token: str, body: dict = Body(default={})):
        tenant, did = _who(token)
        ids = body.get("ids") if isinstance(body.get("ids"), list) else []
        return _j(L.select(tenant, did, ids))

    @r.get("/api/diagram/live/{token}/poll")
    async def live_poll(token: str, rev: int = 0):
        tenant, did = _who(token)
        return _j(L.poll(tenant, did, rev))

    @r.get("/api/diagram/live/{token}/file")
    async def live_file(token: str):
        tenant, did = _who(token)
        s = L.state(tenant, did)
        if not s.get("ok"):
            raise HTTPException(404)
        name = "".join(ch for ch in (s.get("title") or "diagram") if ch.isalnum() or ch in " -_")[:60].strip() or "diagram"
        return Response(s["xml"], media_type="application/vnd.jgraph.mxfile",
                        headers={"Content-Disposition": f'attachment; filename="{name}.drawio"',
                                 "Access-Control-Allow-Origin": "*", "X-Content-Type-Options": "nosniff"})

    @r.get("/api/diagram/open/{artifact_id}", dependencies=[Depends(require_key)])
    async def open_by_hand(artifact_id: str, tenant: str = Depends(current_tenant)):
        m = S.by_artifact(tenant, artifact_id)
        if m is None:
            return {"ok": False, "diagram": False}
        if m.get("engine") == "drawio":
            return {"ok": True, "diagram": True, "editable": True, "url": L.link(tenant, m["id"]),
                    "diagram_id": m["id"], "engine": "drawio"}
        return {"ok": True, "diagram": True, "editable": False, "diagram_id": m["id"], "engine": m.get("engine"),
                "title": m.get("title", "")}

    return r
