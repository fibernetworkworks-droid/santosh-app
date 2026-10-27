"""HTTP routes for Gyaan (Profile > "<name> ka gyaan" in the app). All under /api/gyaan, owner's key required.

GET    /api/gyaan                 status + settings + recent docs
GET    /api/gyaan/docs?source=&q= list
POST   /api/gyaan/search          {query, queries?, sources?, days?}  (what Hoola would find; for her to test)
POST   /api/gyaan/files           {file_id}                            add one of her stored files
POST   /api/gyaan/upload          multipart file                       add a file from the phone
POST   /api/gyaan/notes           {title, text}
POST   /api/gyaan/drive           {folder}                             keep a Google Drive folder in Gyaan (daily sync)
DELETE /api/gyaan/drive/{id}      stop + forget its files
POST   /api/gyaan/web             {url, follow}                        v0.135 a public web page (+ same-site links), weekly
DELETE /api/gyaan/watch/{id}      stop a Drive folder / web page + forget its pages
GET    /api/gyaan/names?q=        v0.135 people / firms in her Gyaan (documents per name)
GET    /api/gyaan/names/who?name= which documents name them + who appears with them
POST   /api/gyaan/sync            Drive + web pages + mail + her records now
PUT    /api/gyaan/settings        {auto_files, mail_on, records_on}    off = that part forgotten too
DELETE /api/gyaan/docs/{id}       forget one item (chunks, vectors, IDs: all of it)
DELETE /api/gyaan                 forget everything (the owner's file is deleted)
GET    /api/gyaan/eval            run the built-in test set (recall / abstention)"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile


def make_router(require_key, current_tenant) -> APIRouter:
    from . import evaluate, ingest, search
    r = APIRouter(prefix="/api/gyaan", dependencies=[Depends(require_key)])

    async def run(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except ingest.GyaanError as e:
            raise HTTPException(400, str(e))

    def _b(body: Any) -> dict:
        return body if isinstance(body, dict) else {}

    @r.get("")
    async def gyaan_all(tenant: str = Depends(current_tenant)):
        st = await run(ingest.status, tenant)
        st["recent"] = await run(ingest.docs, tenant, "", "", 30)
        return st

    @r.get("/docs")
    async def gyaan_docs(source: str = "", q: str = "", limit: int = 100, tenant: str = Depends(current_tenant)):
        return {"docs": await run(ingest.docs, tenant, source, q, max(1, min(limit, 500)))}

    @r.post("/search")
    async def gyaan_search(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        q = str(b.get("query") or "").strip()
        if not q:
            raise HTTPException(400, "query chahiye")
        out = await run(search.search, tenant, q, [str(x) for x in (b.get("queries") or [])][:4],
                        [str(x) for x in (b.get("sources") or [])] or None, int(b["days"]) if b.get("days") else None,
                        int(b.get("top") or 8), bool(b.get("fast")))
        for h in out.get("hits", []):
            h["text"] = h["text"][:700]
        return out

    @r.post("/files")
    async def gyaan_add_file(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        fid = str(_b(body).get("file_id") or "")
        if not fid:
            raise HTTPException(400, "file_id chahiye")
        return await run(ingest.add_owner_file, tenant, fid)

    @r.post("/upload")
    async def gyaan_upload(file: UploadFile = File(...), tenant: str = Depends(current_tenant)):
        data = await file.read()
        return await run(ingest.add_bytes, tenant, file.filename or "file", data, "file", "", file.content_type or "")

    @r.post("/notes")
    async def gyaan_note(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if not str(b.get("text") or "").strip():
            raise HTTPException(400, "text chahiye")
        return await run(ingest.add_note, tenant, str(b.get("title") or ""), str(b.get("text")))

    @r.post("/drive")
    async def gyaan_drive(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        folder = str(_b(body).get("folder") or "").strip()
        if not folder:
            raise HTTPException(400, "folder chahiye")
        return await run(ingest.add_drive_folder, tenant, folder)

    @r.delete("/drive/{watch_id}")
    async def gyaan_drive_off(watch_id: str, tenant: str = Depends(current_tenant)):
        return await run(ingest.remove_watch, tenant, watch_id)

    @r.post("/web")
    async def gyaan_web(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        url = str(b.get("url") or "").strip()
        if not url:
            raise HTTPException(400, "url chahiye")
        return await run(ingest.add_web, tenant, url, int(b.get("follow") or 0))

    @r.delete("/watch/{watch_id}")
    async def gyaan_watch_off(watch_id: str, tenant: str = Depends(current_tenant)):
        return await run(ingest.remove_watch, tenant, watch_id)

    @r.get("/names")
    async def gyaan_names(q: str = "", limit: int = 40, tenant: str = Depends(current_tenant)):
        return {"names": await run(ingest.names, tenant, q, max(1, min(limit, 200)))}

    @r.get("/names/who")
    async def gyaan_who(name: str = "", tenant: str = Depends(current_tenant)):
        if not name.strip():
            raise HTTPException(400, "name chahiye")
        return await run(ingest.who, tenant, name.strip())

    @r.post("/sync")
    async def gyaan_sync(tenant: str = Depends(current_tenant)):
        return {"drive": await run(ingest.sync_drive, tenant), "web": await run(ingest.sync_web, tenant),
                "mail": await run(ingest.sync_mail, tenant), "records": await run(ingest.sync_records, tenant)}

    @r.put("/settings")
    async def gyaan_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(ingest.save_settings, tenant, **{k: b[k] for k in ("auto_files", "mail_on", "records_on") if k in b})

    @r.delete("/docs/{doc_id}")
    async def gyaan_forget(doc_id: str, tenant: str = Depends(current_tenant)):
        return await run(ingest.forget, tenant, doc_id)

    @r.delete("")
    async def gyaan_forget_all(tenant: str = Depends(current_tenant)):
        return await run(ingest.forget_all, tenant)

    @r.get("/eval")
    async def gyaan_eval(k: int = 8, tenant: str = Depends(current_tenant)):
        out = await run(evaluate.evaluate, None, None, max(1, min(k, 20)))
        return {x: out[x] for x in ("embedder", "recall", "abstain", "slices", "missed", "false_found", "k")}

    return r
