"""HTTP routes for Docs Sahayak (Profile > "<name> · Technical writer").

main.py: `app.include_router(docwriter_api.make_router(require_key, current_tenant))`.
Public (no key): GET /api/docwriter/page/{token} = a docs page she published with her tap (random token; CSP: no scripts,
images only from data: URIs inside the page)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

PAGE_HEADERS = {"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:; frame-ancestors *",
                "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Cache-Control": "public, max-age=300"}


def _run(fn, *a, **k):
    from . import service as S
    try:
        return fn(*a, **k)
    except (S.DocError, ValueError) as e:
        raise HTTPException(400, str(e))


async def _bg(fn, *a, **k):
    return await asyncio.to_thread(_run, fn, *a, **k)


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S
    r = APIRouter()
    key = [Depends(require_key)]

    @r.get("/api/docwriter", dependencies=key)
    def everything(tenant: str = Depends(current_tenant)):
        return _run(S.everything, tenant)

    @r.get("/api/docwriter/settings", dependencies=key)
    def get_settings(tenant: str = Depends(current_tenant)):
        return S.settings(tenant)

    @r.put("/api/docwriter/settings", dependencies=key)
    def put_settings(body: dict = Body(...), tenant: str = Depends(current_tenant)):
        keys = ("product_name", "audience", "tone", "contact", "langs", "keep", "rules", "glossary")
        return _run(S.save_settings, tenant, **{k: body[k] for k in keys if k in body})

    @r.put("/api/docwriter/github", dependencies=key)
    async def put_github(body: dict = Body(...), tenant: str = Depends(current_tenant)):
        """Her fine-grained token, typed ONLY here (never in chat)."""
        return await _bg(S.set_github, tenant, str(body.get("token") or ""))

    @r.delete("/api/docwriter/github", dependencies=key)
    def del_github(tenant: str = Depends(current_tenant)):
        return S.forget_github(tenant)

    @r.get("/api/docwriter/products", dependencies=key)
    def products(tenant: str = Depends(current_tenant)):
        return {"products": S.products(tenant)}

    @r.post("/api/docwriter/products", dependencies=key)
    async def add_product(body: dict = Body(...), tenant: str = Depends(current_tenant)):
        return await _bg(S.add_product, tenant, str(body.get("kind") or ""), str(body.get("ref") or ""), str(body.get("name") or ""),
                         body.get("file_ids"))

    @r.get("/api/docwriter/products/{pid}", dependencies=key)
    def product(pid: str, tenant: str = Depends(current_tenant)):
        return _run(S.get_product, tenant, pid)

    @r.delete("/api/docwriter/products/{pid}", dependencies=key)
    def del_product(pid: str, tenant: str = Depends(current_tenant)):
        return _run(S.remove_product, tenant, pid)

    @r.post("/api/docwriter/products/{pid}/verify", dependencies=key)
    async def verify(pid: str, tenant: str = Depends(current_tenant)):
        return await _bg(S.verify_product, tenant, pid)

    @r.post("/api/docwriter/products/{pid}/sync", dependencies=key)
    async def sync(pid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await _bg(S.sync, tenant, pid, bool(body.get("redraft", True)))

    @r.post("/api/docwriter/products/{pid}/flows", dependencies=key)
    async def flow(pid: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        return await _bg(S.record_flow, tenant, pid, str(body.get("name") or ""), body.get("steps"), str(body.get("device") or "phone"),
                         body.get("hide"), "", str(body.get("flow") or ""))

    @r.get("/api/docwriter/flows/{fid}/img/{name}", dependencies=key)
    def flow_img(fid: str, name: str, tenant: str = Depends(current_tenant)):
        try:
            return FileResponse(S.flow_image(tenant, fid, name), media_type="image/png")
        except (S.DocError, ValueError):
            raise HTTPException(404, "not found")

    @r.get("/api/docwriter/docs", dependencies=key)
    def docs(product: str = "", status: str = "", tenant: str = Depends(current_tenant)):
        return {"docs": _run(S.docs, tenant, product, status)}

    @r.post("/api/docwriter/docs", dependencies=key)
    async def write(body: dict = Body(...), tenant: str = Depends(current_tenant)):
        return await _bg(S.write, tenant, str(body.get("product") or ""), str(body.get("kind") or ""), str(body.get("lang") or ""),
                         str(body.get("title") or ""), str(body.get("words") or ""), body.get("focus"))

    @r.post("/api/docwriter/release_notes", dependencies=key)
    async def release_notes(body: dict = Body(...), tenant: str = Depends(current_tenant)):
        return await _bg(S.release_notes, tenant, str(body.get("product") or ""), str(body.get("lang") or ""), str(body.get("words") or ""),
                         str(body.get("version") or ""))

    @r.get("/api/docwriter/docs/{did}", dependencies=key)
    def doc(did: str, tenant: str = Depends(current_tenant)):
        return _run(S.get, tenant, did)

    @r.delete("/api/docwriter/docs/{did}", dependencies=key)
    def del_doc(did: str, tenant: str = Depends(current_tenant)):
        return _run(S.delete, tenant, did)

    @r.get("/api/docwriter/docs/{did}/img/{name}", dependencies=key)
    def doc_img(did: str, name: str, tenant: str = Depends(current_tenant)):
        try:
            return FileResponse(S.doc_image(tenant, did, name), media_type="image/jpeg")
        except (S.DocError, ValueError):
            raise HTTPException(404, "not found")

    @r.put("/api/docwriter/docs/{did}/sections/{sid}", dependencies=key)
    def edit(did: str, sid: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        return _run(S.edit, tenant, did, sid, body.get("body"), body.get("title"))

    @r.post("/api/docwriter/docs/{did}/revise", dependencies=key)
    async def revise(did: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        return await _bg(S.revise, tenant, did, str(body.get("instruction") or ""), str(body.get("section") or ""))

    @r.post("/api/docwriter/docs/{did}/check", dependencies=key)
    def check(did: str, tenant: str = Depends(current_tenant)):
        return _run(S.check, tenant, did)

    @r.post("/api/docwriter/docs/{did}/translate", dependencies=key)
    async def translate(did: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        return await _bg(S.translate, tenant, did, str(body.get("to") or ""))

    @r.post("/api/docwriter/docs/{did}/files", dependencies=key)
    async def files(did: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await _bg(S.make_files, tenant, did, body.get("formats"))

    @r.post("/api/docwriter/docs/{did}/publish", dependencies=key)
    async def publish(did: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        return await _bg(S.publish_request, tenant, did, str(body.get("dest") or "page"), str(body.get("repo") or ""))

    @r.post("/api/docwriter/docs/{did}/decide", dependencies=key)
    async def decide(did: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        """Her tap on the publish card: the ONLY way a doc goes public."""
        return await _bg(S.decide_publish, tenant, did, bool(body.get("yes")), str(body.get("hash") or ""), True)

    @r.post("/api/docwriter/docs/{did}/unpage", dependencies=key)
    def unpage(did: str, tenant: str = Depends(current_tenant)):
        return _run(S.unpublish_page, tenant, did)

    @r.get("/api/docwriter/page/{token}")
    def page(token: str):
        html_text = S.page_by_token(token)
        if not html_text:
            raise HTTPException(404, "Page nahi mila")
        return HTMLResponse(html_text, headers=PAGE_HEADERS)

    return r
