"""v0.531.0 const_tender tools (C10: #52 tender watch + #54 bid price pack + #55 pre-qual dossier +
#58 vendor developer). The bid / no-bid decision is HERS with her factor rows; every pack row
carries its source; portal submission is the bid manager's act (tier A record, no auto-bid)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

TENDER_TOOLS = [
    {"name": "const_tender", "description": (
        "Tendering desk: watch list, bid/no-bid sheet, pre-qual dossier, bid price pack, vendor register. "
        "action=tender: name, authority, due_on, emd, scope -> watch. action=bid_sheet: tender, decision bid|no_bid, "
        "reasons [{factor, note}] (call aapki, reasons aapke). action=pack: tender, kind prequal|price, rows "
        "[{item, value, source}] (har row apna source leke). action=tender_mark: tender, status watch|bid|no_bid|"
        "submitted|won|lost, ref. action=vendor_add: vendor, scope, rating preferred|ok|watch|blocked, last_work. "
        "action=vendor_rate: vendor (id), rating, note."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["tender", "bid_sheet", "pack", "tender_mark", "vendor_add",
                                               "vendor_rate", "vendors"]},
         "name": {"type": "string"}, "authority": {"type": "string"}, "due_on": {"type": "string"},
         "emd": {"type": "number"}, "scope": {"type": "string"}, "tender": {"type": "string"},
         "decision": {"type": "string"}, "reasons": {"type": "array", "items": {"type": "object"}},
         "kind": {"type": "string"}, "rows": {"type": "array", "items": {"type": "object"}},
         "status": {"type": "string"}, "ref": {"type": "string"}, "vendor": {"type": "string"},
         "rating": {"type": "string"}, "last_work": {"type": "string"}, "note": {"type": "string"},
         "vendor_id": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_tender_dekho", "description": (
        "Read tender desk (nothing changes). what=day | tenders (status filter optional) | packs (tender optional) | "
        "vendors (rating optional)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "tenders", "packs", "vendors"]},
         "status": {"type": "string"}, "tender": {"type": "string"}, "rating": {"type": "string"}},
         "required": ["what"]}},
]
TENDER_LABELS = {"const_tender": "Tender ka record jod raha hoon", "const_tender_dekho": "Tender desk dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import tender as T
    from ..construction.common import guard
    guard(f"{action} tender")     # tier-C refusal rides every construction action
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "tender":
            return T.tender_add(t, _s(a.get("name")), _s(a.get("authority")), _s(a.get("due_on")), a.get("emd"),
                                _s(a.get("scope")), conv)
        if action == "bid_sheet":
            return T.bid_sheet(t, _s(a.get("tender")), _s(a.get("decision")), a.get("reasons"), conv)
        if action == "pack":
            return T.pack(t, _s(a.get("tender")), _s(a.get("kind")), a.get("rows"), _s(a.get("note")))
        if action == "tender_mark":
            return T.tender_mark(t, _s(a.get("tender")), _s(a.get("status")), _s(a.get("ref")))
        if action == "vendor_add":
            return T.vendor_add(t, _s(a.get("vendor")), _s(a.get("scope")), _s(a.get("rating")) or "watch",
                                _s(a.get("last_work")), _s(a.get("note")))
        if action == "vendor_rate":
            return T.vendor_rate(t, _s(a.get("vendor_id")), _s(a.get("rating")), _s(a.get("note")))
        if action == "vendors":
            return T.vendors(t, _s(a.get("rating")))
    except (T.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import tender as T
    from ..construction.common import guard
    from ..db import session
    from sqlalchemy import select
    from ..construction.models import CTendPack, CTender
    t = ctx.tenant_id
    guard(f"read tender {what}")
    try:
        if what == "day":
            return T.due(t, 14)
        if what == "tenders":
            with session() as s:
                rows = s.scalars(select(CTender).where(CTender.tenant_id == t)).all()
            st = _s(a.get("status"))
            if st:
                rows = [r for r in rows if r.status == st]
            return {"tenders": [{"id": r.id, "name": r.name, "authority": r.authority, "due_on": r.due_on,
                                 "emd": r.emd, "status": r.status} for r in rows]}
        if what == "packs":
            with session() as s:
                rows = s.scalars(select(CTendPack).where(CTendPack.tenant_id == t)).all()
            tid = _s(a.get("tender"))
            if tid:
                rows = [r for r in rows if r.tender_id == tid]
            return {"packs": [{"id": r.id, "tender_id": r.tender_id, "kind": r.kind, "rows": len(_j(r.rows, [])),
                               "status": r.status} for r in rows]}
        if what == "vendors":
            return T.vendors(t, _s(a.get("rating")))
    except (T.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


def _j(s_: str, default):
    import json
    try:
        v = json.loads(s_)
        return v if isinstance(v, type(default)) else default
    except (json.JSONDecodeError, TypeError):
        return default


async def const_tender(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_tender_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


TENDER_HANDLERS = {"const_tender": const_tender, "const_tender_dekho": const_tender_dekho}
