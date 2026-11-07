"""KAAN W5 HTTP API: the REST door beside the agent tool and the MCP server.

The SAME service functions the `kaan` tool calls (KS.*), the SAME gates (audio ingest
rides `kaan_audio`), the SAME honesty - one brain, three doors. Every route is
tenant-scoped by `current_tenant` (the API key, a product session, or a paired device
token - the browser extension pairs through /api/pc/pair and rides the same law).
Reads (list/get/search/export/style/minutes/status/live_get) are gate-free by the W1
law; anything that ingests audio or writes tenant data keeps its W0-W4 gate/actor rules.

New W5 strings are English (owner instruction).
"""
from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from . import service as KS


class StyleIn(BaseModel):
    style: str


class DiarizeIn(BaseModel):
    names: dict[str, str] | None = None
    pause_s: float | None = None


class VocabIn(BaseModel):
    term: str
    fix_to: str = ""
    note: str = ""


class LiveStartIn(BaseModel):
    model: str = ""
    language: str = ""
    conversation_id: str = ""
    vocab: bool = True


class LiveStopIn(BaseModel):
    finalize_model: str = ""


_MEDIA = {"srt": "text/plain; charset=utf-8", "vtt": "text/plain; charset=utf-8",
          "txt": "text/plain; charset=utf-8", "json": "application/json; charset=utf-8"}


def _err(e: Exception) -> HTTPException:
    """One honest line, the service's own words (the tool layer maps the same families)."""
    return HTTPException(400, str(e))


def _kaan_router(require_key: Callable, current_tenant: Callable) -> APIRouter:
    r = APIRouter(prefix="/api/kaan", tags=["kaan"], dependencies=[Depends(require_key)])

    # ---------------------------------------------------------------- reads (gate-free)
    @r.get("/status")
    def kaan_status(tenant: str = Depends(current_tenant)):
        return KS.status(tenant)

    @r.get("/list")
    def kaan_list(limit: int = 20, tenant: str = Depends(current_tenant)):
        return {"items": KS.list_transcripts(tenant, limit)}

    @r.get("/search")
    def kaan_search(q: str = "", limit: int = 10, tenant: str = Depends(current_tenant)):
        return {"q": (q or "").strip(), "items": KS.search_transcripts(tenant, q, limit)}

    @r.get("/vocab")
    def kaan_vocab_list(tenant: str = Depends(current_tenant)):
        return KS.vocab_list(tenant)

    @r.post("/vocab")
    def kaan_vocab_add(body: VocabIn, tenant: str = Depends(current_tenant)):
        try:
            return KS.vocab_add(tenant, body.term, fix_to=body.fix_to, note=body.note)
        except ValueError as e:
            raise _err(e) from e

    @r.delete("/vocab/{term}")
    def kaan_vocab_remove(term: str, tenant: str = Depends(current_tenant)):
        try:
            return KS.vocab_remove(tenant, term)
        except ValueError as e:
            raise _err(e) from e

    # ---------------------------------------------------------------- live (audio gate rides KS)
    @r.post("/live/start")
    def kaan_live_start(body: LiveStartIn, tenant: str = Depends(current_tenant)):
        try:
            return KS.live_start(tenant, model=body.model, language=body.language,
                                 conversation_id=body.conversation_id, vocab=body.vocab)
        except Exception as e:                                  # noqa: BLE001 - KaanError/LiveError -> 400
            raise _err(e) from e

    @r.post("/live/{sid}/chunk")
    async def kaan_live_chunk(sid: str, request: Request, tenant: str = Depends(current_tenant)):
        data = await request.body()
        try:
            return KS.live_chunk(tenant, sid, data)
        except Exception as e:                                  # noqa: BLE001
            raise _err(e) from e

    @r.post("/live/{sid}/stop")
    def kaan_live_stop(sid: str, body: LiveStopIn | None = None, tenant: str = Depends(current_tenant)):
        try:
            fm = (body.finalize_model if body else "") or ""
            return KS.live_stop(tenant, sid, finalize_model=fm)
        except Exception as e:                                  # noqa: BLE001
            raise _err(e) from e

    @r.get("/live/{sid}")
    def kaan_live_get(sid: str, tenant: str = Depends(current_tenant)):
        try:
            return KS.live_get(tenant, sid)
        except Exception as e:                                  # noqa: BLE001
            raise _err(e) from e

    @r.get("/live")
    def kaan_live_list(limit: int = 20, tenant: str = Depends(current_tenant)):
        return {"items": KS.live_list(tenant, limit)}

    # ---------------------------------------------------------------- transcribe (audio gate rides KS)
    @r.post("/transcribe")
    async def kaan_transcribe(file: UploadFile, model: str = Form(""), language: str = Form(""),
                              task: str = Form("transcribe"), word_timestamps: bool = Form(True),
                              vocab: bool = Form(True), diarize: str = Form(""),
                              tenant: str = Depends(current_tenant)):
        try:
            return KS.transcribe_file(tenant, name=file.filename or "upload",
                                      data=await file.read(), model=model, language=language,
                                      task=task, word_timestamps=word_timestamps, vocab=vocab,
                                      diarize=diarize)
        except Exception as e:                                  # noqa: BLE001
            raise _err(e) from e

    # ---------------------------------------------------------------- per-transcript (tid routes LAST)
    @r.get("/{tid}")
    def kaan_get(tid: str, tenant: str = Depends(current_tenant)):
        try:
            return KS.get_transcript(tenant, tid)
        except ValueError as e:
            raise _err(e) from e

    @r.get("/{tid}/export")
    def kaan_export(tid: str, fmt: str, download: int = 0, tenant: str = Depends(current_tenant)):
        try:
            out = KS.export_transcript(tenant, tid, fmt)
        except ValueError as e:
            raise _err(e) from e
        if download:
            return Response(content=out["text"], media_type=_MEDIA.get(out["fmt"], "text/plain"),
                            headers={"Content-Disposition": f'attachment; filename="{out["filename"]}"'})
        return out

    @r.post("/{tid}/style")
    def kaan_style(tid: str, body: StyleIn, tenant: str = Depends(current_tenant)):
        try:
            return KS.style_render(tenant, tid, body.style)
        except ValueError as e:
            raise _err(e) from e

    @r.get("/{tid}/minutes")
    def kaan_minutes(tid: str, tenant: str = Depends(current_tenant)):
        try:
            return KS.minutes(tenant, tid)
        except ValueError as e:
            raise _err(e) from e

    @r.post("/{tid}/diarize")
    def kaan_diarize(tid: str, body: DiarizeIn | None = None, tenant: str = Depends(current_tenant)):
        try:
            b = body or DiarizeIn()
            return KS.diarize_transcript(tenant, tid, names=b.names, pause_s=b.pause_s)
        except Exception as e:                                  # noqa: BLE001 - KaanError (kill switch) too
            raise _err(e) from e

    @r.post("/{tid}/to_gyaan")
    def kaan_to_gyaan(tid: str, tenant: str = Depends(current_tenant)):
        try:
            return KS.to_gyaan(tenant, tid)
        except ValueError as e:
            raise _err(e) from e

    return r
