"""v0.751 HOOLA FLOW: the Kaan pack (W0-W6) as a console page (owner: "check the code" -> "first show me
the design here" -> the 8-screen canvas -> "GO").

Everything that hears, writes, styles, exports or names already lives in kaan/service.py and its
/api/kaan/* door; the page rides those routes as they are. This router only adds the few things a
PAGE needs that a tool never did:

  GET    /api/flow/overview          one read for the page: engine / switches / limits / doors in plain
                                     English + her recent transcripts with a kind (dictated / live / file)
  GET    /api/flow/t/{tid}           one transcript WITH its segments and speaker turns (the tool's get
                                     returns the row only)
  POST   /api/flow/t/{tid}/rename    a name she gives it ("Monday stand-up"); a dictation is named
                                     "Dictation ..." by the page so it shows as dictated
  POST   /api/flow/t/{tid}/pin       keep for ever (the W6 retention sweep skips pinned rows)
  DELETE /api/flow/t/{tid}           her tap deletes it (the live session record keeps no text of its own)

Behind `flow_page` (off = every route 404s). Tenant from current_tenant like every other door.
"""
from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..db import now, session
from . import service as KS
from .models import KaanTranscript

KIND_DICTATED = "Dictation"


class RenameIn(BaseModel):
    name: str


class PinIn(BaseModel):
    pinned: bool = True


def _on() -> None:
    from ..config import get_settings
    if not bool(getattr(get_settings(), "flow_page", False)):
        raise HTTPException(404, "Hoola Flow is switched off on this server (FLOW_PAGE).")


def kind_of(row: dict[str, Any], source: str = "") -> str:
    name = str(row.get("file_name") or "")
    if name.startswith(KIND_DICTATED):
        return "dictated"
    if source == "live" or name.startswith("live:"):
        return "live"
    return "file"


def title_of(row: dict[str, Any]) -> str:
    name = str(row.get("file_name") or "").strip()
    if name.startswith("live:") or not name:
        day = str(row.get("created_at") or "")[:16].replace("T", " ")
        return f"Live captions {day}".strip()
    return name


def _item(r: KaanTranscript) -> dict[str, Any]:
    d = KS._row(r)
    d["text"] = (d.get("text") or "")[:220]
    d["kind"] = kind_of(d, r.source or "")
    d["title"] = title_of(d)
    sp = r.speakers if isinstance(r.speakers, dict) else {}
    d["n_turns"] = int(sp.get("n_turns") or 0)
    return d


def _get(s, tenant: str, tid: str) -> KaanTranscript:
    r = s.scalars(select(KaanTranscript).where(KaanTranscript.tenant_id == tenant, KaanTranscript.id == tid)).first()
    if not r:
        raise HTTPException(404, "That transcript is not here (deleted, or never made).")
    return r


def overview(tenant: str, limit: int = 40) -> dict[str, Any]:
    st = KS.status(tenant)
    with session() as s:
        rows = s.scalars(select(KaanTranscript).where(KaanTranscript.tenant_id == tenant)
                         .order_by(KaanTranscript.created_at.desc()).limit(max(1, min(int(limit or 40), 100)))).all()
        items = [_item(r) for r in rows]
    usage = st.get("usage") or {}
    ret = st.get("retention") or {}
    vp = st.get("voiceprint") or {}
    engine_ok = st.get("engine") == "ready"
    return {
        "ready": engine_ok and st.get("gate") == "ON",
        "engine": {"ok": engine_ok, "why": "" if engine_ok else (st.get("engine_note") or "The Whisper engine is not installed on this server."),
                   "default_model": st.get("default_model") or "",
                   "live_model": (st.get("live") or {}).get("default_model") or "",
                   "ladder": st.get("ladder") or []},
        "recording": {"on": st.get("gate") == "ON",
                      "how": "" if st.get("gate") == "ON" else "Recording is off on this server. The owner turns it on with KAAN_AUDIO=1 in the server settings."},
        "speakers": {"on": bool((st.get("diarize") or {}).get("on"))},
        "voiceprint": {"on": bool(vp.get("on")), "why": vp.get("note") or ""},
        "usage": {"minutes": usage.get("audio_min_used", 0), "cap": int(usage.get("quota_min") or 0),
                  "remaining": usage.get("remaining_min"), "month": usage.get("month", "")},
        "retention": {"days": int(ret.get("days") or 0)},
        "words": (st.get("vocab") or {}).get("n_terms", 0),
        "live_active": (st.get("live") or {}).get("active", 0),
        "styles": [["verbatim", "As said"], ["clean", "Clean"], ["minutes", "Notes"], ["social", "Social"], ["subtitles", "Subtitles"]],
        "exports": ["srt", "vtt", "txt", "json"],
        "doors": {"api": "/api/kaan", "mcp": "python -m app.kaan.mcp_server", "extension": "Hoola Chrome extension > Live captions"},
        "items": items,
    }


def detail(tenant: str, tid: str) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, tid)
        d = KS._row(r)
        d["segments"] = (r.segments or {}).get("items", []) if isinstance(r.segments, dict) else (r.segments or [])
        d["kind"] = kind_of(d, r.source or "")
        d["title"] = title_of(d)
        d["source"] = r.source or ""
    return d


def rename(tenant: str, tid: str, name: str) -> dict[str, Any]:
    name = " ".join((name or "").split())[:200]
    if not name:
        raise HTTPException(400, "Give it a name.")
    with session() as s:
        r = _get(s, tenant, tid)
        r.file_name = name
        r.updated_at = now()
        s.commit()
    return {"id": tid, "file_name": name}


def pin(tenant: str, tid: str, pinned: bool) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, tid)
        r.pinned = bool(pinned)
        r.updated_at = now()
        s.commit()
    return {"id": tid, "pinned": bool(pinned)}


def delete(tenant: str, tid: str) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, tid)
        s.delete(r)
        s.commit()
    return {"id": tid, "deleted": True}


def _flow_router(require_key: Callable, current_tenant: Callable) -> APIRouter:
    r = APIRouter(prefix="/api/flow", tags=["flow"], dependencies=[Depends(require_key), Depends(_on)])

    @r.get("/overview")
    def flow_overview(limit: int = 40, tenant: str = Depends(current_tenant)):
        return overview(tenant, limit)

    @r.get("/t/{tid}")
    def flow_detail(tid: str, tenant: str = Depends(current_tenant)):
        return detail(tenant, tid)

    @r.post("/t/{tid}/rename")
    def flow_rename(tid: str, body: RenameIn, tenant: str = Depends(current_tenant)):
        return rename(tenant, tid, body.name)

    @r.post("/t/{tid}/pin")
    def flow_pin(tid: str, body: PinIn, tenant: str = Depends(current_tenant)):
        return pin(tenant, tid, body.pinned)

    @r.delete("/t/{tid}")
    def flow_delete(tid: str, tenant: str = Depends(current_tenant)):
        return delete(tenant, tid)

    return r
