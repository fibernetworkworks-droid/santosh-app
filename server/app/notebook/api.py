"""Hoola Notebook HTTP API (the app's Notebook screens). Everything is the owner's own (key-protected), except the
signed Studio file links (/api/notebook-files/...), which check their own HMAC + expiry."""
from __future__ import annotations

import asyncio
import mimetypes
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel


class NotebookIn(BaseModel):
    title: str = "Nayi notebook"
    emoji: str = ""


class NotebookPatch(BaseModel):
    title: str = ""
    emoji: str = ""


class SourceIn(BaseModel):
    url: str | None = None
    text: str | None = None
    title: str | None = None
    drive: str | None = None
    sheet: str | None = None
    tab: str | None = None
    file_id: str | None = None
    email_id: str | None = None
    attachment_id: str | None = None


class SelectIn(BaseModel):
    ids: list[str] | None = None
    enabled: bool = True
    only: bool = False


class TitleIn(BaseModel):
    title: str


class QueryIn(BaseModel):
    query: str


class AskIn(BaseModel):
    question: str
    save: bool = False
    sources: list[str] | None = None


class ConfigIn(BaseModel):
    goal: str = ""
    custom: str = ""
    length: str = ""
    language: str = ""


class NoteIn(BaseModel):
    title: str = ""
    content: str = ""


class MakeIn(BaseModel):
    kind: str
    language: str = ""
    focus: str = ""


class AudioIn(BaseModel):
    style: str = "deep_dive"
    length: str = "default"
    language: str = "hinglish"
    focus: str = ""
    conversation_id: str = ""


class StudioIn(BaseModel):
    kind: str
    options: dict[str, Any] = {}
    conversation_id: str = ""


class ReviseIn(BaseModel):
    edits: list[dict[str, Any]]


class JoinIn(BaseModel):
    question: str
    at: int = 0


class ShareIn(BaseModel):
    name: str
    conversation_id: str = ""


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as ns
    from . import studio

    r = APIRouter()
    dep = [Depends(require_key)]

    def sync(fn, *a, **kw):
        try:
            return fn(*a, **kw)
        except ns.NotebookError as e:
            raise HTTPException(400, str(e))

    async def thread(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except ns.NotebookError as e:
            raise HTTPException(400, str(e))

    async def aw(coro):
        try:
            return await coro
        except ns.NotebookError as e:
            raise HTTPException(400, str(e))

    def own_conv(conv: str, tenant: str) -> str:
        if not conv:
            return ""
        from ..db import Conversation, session
        with session() as s:
            c = s.get(Conversation, conv)
            return conv if c and c.tenant_id == tenant else ""

    # ---------- notebooks ----------
    @r.get("/api/notebooks", dependencies=dep)
    def nb_list(tenant: str = Depends(current_tenant)):
        return {"notebooks": ns.list_notebooks(tenant)}

    @r.post("/api/notebooks", dependencies=dep)
    def nb_create(body: NotebookIn, tenant: str = Depends(current_tenant)):
        nb = sync(ns.create, tenant, "", body.title, body.emoji)
        return ns.detail(tenant, nb["id"])

    @r.get("/api/notebooks-catalogue", dependencies=dep)
    def nb_catalogue():
        return studio.catalogue()

    @r.get("/api/notebooks/{nid}", dependencies=dep)
    def nb_detail(nid: str, tenant: str = Depends(current_tenant)):
        return sync(ns.detail, tenant, nid)

    @r.patch("/api/notebooks/{nid}", dependencies=dep)
    def nb_patch(nid: str, body: NotebookPatch, tenant: str = Depends(current_tenant)):
        return sync(ns.update, tenant, nid, body.title, body.emoji)

    @r.delete("/api/notebooks/{nid}", dependencies=dep)
    def nb_delete(nid: str, tenant: str = Depends(current_tenant)):
        """The user deletes from the app (the app asks 'sure?' first)."""
        return {"deleted": sync(ns.delete, tenant, nid)}

    @r.post("/api/notebooks/{nid}/copy", dependencies=dep)
    def nb_copy(nid: str, tenant: str = Depends(current_tenant)):
        return sync(ns.copy_notebook, tenant, nid)

    @r.get("/api/notebooks/{nid}/guide", dependencies=dep)
    async def nb_guide(nid: str, refresh: bool = False, tenant: str = Depends(current_tenant)):
        return await aw(ns.notebook_guide(tenant, nid, refresh))

    # ---------- sources ----------
    @r.post("/api/notebooks/{nid}/sources", dependencies=dep)
    async def src_add(nid: str, body: SourceIn, tenant: str = Depends(current_tenant)):
        src = {k: v for k, v in body.model_dump().items() if v}
        out = await thread(ns.add_source, tenant, nid, src)
        return {**ns.detail(tenant, nid), "added": out}

    @r.post("/api/notebooks/{nid}/upload", dependencies=dep)
    async def src_upload(nid: str, file: UploadFile = File(...), title: str = Form(""), tenant: str = Depends(current_tenant)):
        from ..pc import service as pcs
        try:
            row = await pcs.store_upload(file, tenant, "", "mail", limit_mb=200)
        except pcs.PairError as e:
            raise HTTPException(413, str(e))
        out = await thread(ns.add_source, tenant, nid, {"file_id": row.id, **({"title": title} if title else {})})
        return {**ns.detail(tenant, nid), "added": out}

    @r.post("/api/notebooks/{nid}/sources/select", dependencies=dep)
    def src_select(nid: str, body: SelectIn, tenant: str = Depends(current_tenant)):
        return sync(ns.set_enabled, tenant, nid, body.ids, body.enabled, body.only)

    @r.get("/api/notebooks/{nid}/sources/{sid}", dependencies=dep)
    def src_view(nid: str, sid: str, tenant: str = Depends(current_tenant)):
        return sync(ns.source_view, tenant, nid, sid)

    @r.get("/api/notebooks/{nid}/sources/{sid}/guide", dependencies=dep)
    async def src_guide(nid: str, sid: str, tenant: str = Depends(current_tenant)):
        return await aw(ns.source_guide(tenant, nid, sid))

    @r.patch("/api/notebooks/{nid}/sources/{sid}", dependencies=dep)
    def src_rename(nid: str, sid: str, body: TitleIn, tenant: str = Depends(current_tenant)):
        return sync(ns.rename_source, tenant, nid, sid, body.title)

    @r.post("/api/notebooks/{nid}/sources/{sid}/refresh", dependencies=dep)
    async def src_refresh(nid: str, sid: str, tenant: str = Depends(current_tenant)):
        return await thread(ns.refresh_source, tenant, nid, sid)

    @r.delete("/api/notebooks/{nid}/sources/{sid}", dependencies=dep)
    def src_remove(nid: str, sid: str, tenant: str = Depends(current_tenant)):
        sync(ns.remove_source, tenant, nid, sid)
        return ns.detail(tenant, nid)

    @r.post("/api/notebooks/{nid}/discover", dependencies=dep)
    async def src_discover(nid: str, body: QueryIn, tenant: str = Depends(current_tenant)):
        return await aw(ns.discover(tenant, nid, body.query))

    # ---------- chat ----------
    @r.get("/api/notebooks/{nid}/chat", dependencies=dep)
    def chat_get(nid: str, tenant: str = Depends(current_tenant)):
        return {"messages": sync(ns.chat_history, tenant, nid)}

    @r.delete("/api/notebooks/{nid}/chat", dependencies=dep)
    def chat_clear(nid: str, tenant: str = Depends(current_tenant)):
        return {"cleared": sync(ns.clear_chat, tenant, nid)}

    @r.put("/api/notebooks/{nid}/chat/config", dependencies=dep)
    def chat_config(nid: str, body: ConfigIn, tenant: str = Depends(current_tenant)):
        return {"chat_config": sync(ns.set_config, tenant, nid, body.goal, body.custom, body.length, body.language)}

    @r.post("/api/notebooks/{nid}/ask", dependencies=dep)
    async def chat_ask(nid: str, body: AskIn, tenant: str = Depends(current_tenant)):
        return await aw(ns.ask(tenant, nid, body.question, body.save, body.sources))

    @r.post("/api/notebooks/{nid}/chat/{mid}/save", dependencies=dep)
    def chat_save(nid: str, mid: str, tenant: str = Depends(current_tenant)):
        return sync(ns.save_message, tenant, nid, mid)

    # ---------- notes ----------
    @r.post("/api/notebooks/{nid}/notes", dependencies=dep)
    def note_new(nid: str, body: NoteIn, tenant: str = Depends(current_tenant)):
        return sync(ns.note_create, tenant, nid, body.title, body.content)

    @r.get("/api/notebooks/{nid}/notes/{note_id}", dependencies=dep)
    def note_get(nid: str, note_id: str, tenant: str = Depends(current_tenant)):
        return sync(ns.get_note, tenant, nid, note_id)

    @r.patch("/api/notebooks/{nid}/notes/{note_id}", dependencies=dep)
    def note_patch(nid: str, note_id: str, body: NoteIn, tenant: str = Depends(current_tenant)):
        return sync(ns.note_update, tenant, nid, note_id, body.title, body.content)

    @r.delete("/api/notebooks/{nid}/notes/{note_id}", dependencies=dep)
    def note_del(nid: str, note_id: str, tenant: str = Depends(current_tenant)):
        return {"deleted": sync(ns.note_delete, tenant, nid, note_id)}

    @r.post("/api/notebooks/{nid}/notes/{note_id}/source", dependencies=dep)
    def note_src(nid: str, note_id: str, tenant: str = Depends(current_tenant)):
        return sync(ns.note_to_source, tenant, nid, note_id)

    # ---------- Studio ----------
    @r.post("/api/notebooks/{nid}/studio", dependencies=dep)
    async def studio_new(nid: str, body: StudioIn, tenant: str = Depends(current_tenant)):
        conv = await asyncio.to_thread(own_conv, body.conversation_id, tenant)
        v = await thread(studio.start, tenant, conv, nid, body.kind, body.options)
        studio.launch(v["id"])          # on the server's own loop (a sync route would have none)
        return v

    @r.get("/api/notebooks/{nid}/studio-reports", dependencies=dep)
    async def studio_reports(nid: str, tenant: str = Depends(current_tenant)):
        return {"formats": await aw(studio.suggest_reports(tenant, nid))}

    @r.get("/api/notebooks/{nid}/studio/{oid}", dependencies=dep)
    def studio_get(nid: str, oid: str, tenant: str = Depends(current_tenant)):
        return sync(studio.get, tenant, nid, oid)

    @r.patch("/api/notebooks/{nid}/studio/{oid}", dependencies=dep)
    def studio_rename(nid: str, oid: str, body: TitleIn, tenant: str = Depends(current_tenant)):
        return sync(studio.rename_output, tenant, nid, oid, body.title)

    @r.delete("/api/notebooks/{nid}/studio/{oid}", dependencies=dep)
    def studio_delete(nid: str, oid: str, tenant: str = Depends(current_tenant)):
        return {"deleted": sync(studio.delete_output, tenant, nid, oid)}

    @r.post("/api/notebooks/{nid}/studio/{oid}/revise", dependencies=dep)
    async def studio_revise(nid: str, oid: str, body: ReviseIn, tenant: str = Depends(current_tenant)):
        return await aw(studio.revise_slides(tenant, nid, oid, body.edits))

    @r.post("/api/notebooks/{nid}/studio/{oid}/join", dependencies=dep)
    async def studio_join(nid: str, oid: str, body: JoinIn, tenant: str = Depends(current_tenant)):
        return await aw(studio.join_audio(tenant, nid, oid, body.question, body.at))

    @r.post("/api/notebooks/{nid}/studio/{oid}/share", dependencies=dep)
    def studio_share(nid: str, oid: str, body: ShareIn, tenant: str = Depends(current_tenant)):
        return sync(studio.share_file, tenant, nid, oid, body.name, own_conv(body.conversation_id, tenant))

    # ---------- the old routes (older app builds) ----------
    @r.post("/api/notebooks/{nid}/make", dependencies=dep)
    async def nb_make(nid: str, body: MakeIn, tenant: str = Depends(current_tenant)):
        return await aw(ns.make(tenant, nid, body.kind, body.language, body.focus))

    @r.post("/api/notebooks/{nid}/audio", dependencies=dep)
    async def nb_audio(nid: str, body: AudioIn, tenant: str = Depends(current_tenant)):
        conv = await asyncio.to_thread(own_conv, body.conversation_id, tenant)
        v = await thread(studio.start, tenant, conv, nid, "audio",
                         {"format": body.style, "length": body.length, "language": body.language, "focus": body.focus})
        studio.launch(v["id"])
        return {**v, "audio_id": v["id"]}

    @r.get("/api/notebooks/{nid}/audio/{aid}/file", dependencies=dep)
    def nb_audio_file(nid: str, aid: str, tenant: str = Depends(current_tenant)):
        """A fresh link for a finished audio overview (new Studio audio, or a pre-v0.155 one)."""
        a = ns.legacy_audio_row(tenant, nid, aid)
        if a is not None:
            from ..pc import service as pcs
            f = pcs.get_file(a.file_id) if a.file_id else None
            if f is None:
                raise HTTPException(410, "Audio file expired; make it again")
            return pcs.public_file(f)
        o = sync(studio.get, tenant, nid, aid)
        name = next((n for n in o["files"] if n.startswith("overview.")), "")
        if o["status"] != "ready" or not name:
            raise HTTPException(404, "Audio not ready")
        return {"url": o["files"][name], "name": name, "file_id": ""}

    # ---------- signed files (public: the link is the permission) ----------
    @r.get("/api/notebook-files/{oid}/{name}")
    def nb_file(oid: str, name: str, request: Request, exp: int = 0, sig: str = ""):
        p = studio.file_for(oid, name, exp, sig)
        if p is None:
            raise HTTPException(404, "Link purana ho gaya ya galat hai.")
        media = mimetypes.guess_type(name)[0] or "application/octet-stream"
        if name.endswith(".srt"):
            media = "text/plain; charset=utf-8"
        if name.endswith(".md"):
            media = "text/markdown; charset=utf-8"
        inline = name.rsplit(".", 1)[-1] in ("png", "jpg", "mp3", "wav", "mp4", "pdf", "srt", "md")
        return FileResponse(p, media_type=media, filename=name, content_disposition_type="inline" if inline else "attachment",
                            headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"})

    return r
