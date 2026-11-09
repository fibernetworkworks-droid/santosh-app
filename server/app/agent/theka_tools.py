"""v0.117 Theka Sahayak tools (contractor). `theka_dekho` only reads; `theka` does the work. An RA bill is marked submitted and
a letter goes to the department only on HER Haan. Hoola never submits a bid (her DSC), never pays, never inflates a measurement."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

THEKA_TOOLS = [
    {"name": "theka", "description": (
        "Contractor's coworker (civil / electrical / road / building, govt or private works), end to end. action=settings: firm, "
        "gstin, individual (proprietor -> 1% TDS), udyam, registration (class), registration_valid_to, address. action=tender: name or "
        "tender (id / ref to update), dept, portal, ref, value, emd, emd_mode dd|bg|online|declaration|exempt, prebid, last_date (date + "
        "time), opening, status watching|preparing|submitted|won|lost|dropped, have [documents ready], our_quote, l1, emd_back. "
        "action=project: name or project, client, govt, agreement_no, value, start, end, dlp_months, gst_rate, retention_pct, sd_pct, "
        "it_tds_pct, gst_tds, cess_pct, mob_advance, mob_pct, deviation_pct, bg_no, bg_amount, bg_valid_to, insurance_valid_to, "
        "completed_on, status. action=boq: project, items [{code, description, unit, qty, rate}] or file_id (BOQ Excel / CSV), extra "
        "(true for extra items). action=measure: project, item (BOQ item no or words), qty (as measured), detail (L x B x D / "
        "chainage), day, by. action=ra_bill: project, upto, final. action=bill_status: bill_id, status submitted (ONLY on her haan)|"
        "passed|paid, amount, on. action=sub: name, phone, individual, pan_ok, work, retention_pct, rate_basis (naap kaisa - sqm / cum / "
        "running ft / lump). action=sub_advance: sub, amount (advance), project, day, note. action=sub_bill: sub, amount, "
        "project, day, advance_recover (kitna advance isi bill se kaatna hai, oldest pehle), note. action=wage_calc: workers, days, "
        "rate, basis day|hour|piece, gang, ot_hours, advance_recover, note -> wage working paper trail ke saath (payment aapke tap se). "
        "action=material: project, item, qty, rate, used (true when consumed). action=diary: project, labour, work, "
        "hindrance, lost_hours, by_client (department-side), day. action=eot: project (extension letter draft). action=register (Excel)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "tender", "project", "boq", "measure", "ra_bill", "bill_status", "sub", "sub_advance",
                                               "sub_bill", "wage_calc", "material", "diary", "eot", "register"]},
         "firm": {"type": "string"}, "gstin": {"type": "string"}, "individual": {"type": "boolean"}, "udyam": {"type": "string"},
         "registration": {"type": "string"}, "registration_valid_to": {"type": "string"}, "address": {"type": "string"},
         "name": {"type": "string"}, "tender": {"type": "string"}, "dept": {"type": "string"}, "portal": {"type": "string"},
         "ref": {"type": "string"}, "value": {"type": "number"}, "emd": {"type": "number"}, "emd_mode": {"type": "string"},
         "prebid": {"type": "string"}, "last_date": {"type": "string"}, "opening": {"type": "string"}, "status": {"type": "string"},
         "have": {"type": "array", "items": {"type": "string"}}, "our_quote": {"type": "number"}, "l1": {"type": "number"},
         "emd_back": {"type": "boolean"}, "project": {"type": "string"}, "client": {"type": "string"}, "govt": {"type": "boolean"},
         "agreement_no": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"}, "dlp_months": {"type": "integer"},
         "gst_rate": {"type": "number"}, "retention_pct": {"type": "number"}, "sd_pct": {"type": "number"}, "it_tds_pct": {"type": "number"},
         "gst_tds": {"type": "boolean"}, "cess_pct": {"type": "number"}, "mob_advance": {"type": "number"}, "mob_pct": {"type": "number"},
         "deviation_pct": {"type": "number"}, "bg_no": {"type": "string"}, "bg_amount": {"type": "number"}, "bg_valid_to": {"type": "string"},
         "insurance_valid_to": {"type": "string"}, "completed_on": {"type": "string"}, "items": {"type": "array", "items": {"type": "object"}},
         "file_id": {"type": "string"}, "extra": {"type": "boolean"}, "item": {"type": "string"}, "qty": {"type": "number"},
         "detail": {"type": "string"}, "day": {"type": "string"}, "by": {"type": "string"}, "upto": {"type": "string"}, "final": {"type": "boolean"},
         "bill_id": {"type": "string"}, "amount": {"type": "number"}, "on": {"type": "string"}, "phone": {"type": "string"},
         "pan_ok": {"type": "boolean"}, "work": {"type": "string"}, "sub": {"type": "string"}, "rate": {"type": "number"},
         "used": {"type": "boolean"}, "labour": {"type": "integer"}, "hindrance": {"type": "string"}, "lost_hours": {"type": "number"},
         "by_client": {"type": "boolean"}, "note": {"type": "string"}, "rate_basis": {"type": "string"}, "advance_recover": {"type": "number"},
         "workers": {"type": "integer"}, "days": {"type": "integer"}, "basis": {"type": "string"}, "ot_hours": {"type": "number"},
         "gang": {"type": "string"}, "advance": {"type": "number"}},
         "required": ["action"]}},
    {"name": "theka_dekho", "description": (
        "Read contractor work (nothing changes). what=day (tender deadlines, EMD to recover, BG / insurance / registration expiry, "
        "delays, retention due, old bills) | tenders (status) | projects (status) | project (project: progress vs time, bills, "
        "retention) | boq (project: done vs BOQ with deviation flags) | receivables | stock (project) | settings | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "tenders", "projects", "project", "boq", "receivables", "stock", "settings", "rules"]},
         "status": {"type": "string"}, "project": {"type": "string"}},
         "required": ["what"]}},
]
THEKA_LABELS = {"theka": "Theke ka kaam kar raha hoon", "theka_dekho": "Site aur bill dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


_TENDER_KEYS = ("dept", "portal", "ref", "value", "emd", "emd_mode", "prebid", "last_date", "opening", "status", "have", "our_quote", "l1", "emd_back", "notes")
_PROJECT_KEYS = ("client", "govt", "agreement_no", "value", "start", "end", "dlp_months", "gst_rate", "retention_pct", "sd_pct", "it_tds_pct", "gst_tds",
                 "cess_pct", "mob_advance", "mob_pct", "deviation_pct", "bg_no", "bg_amount", "bg_valid_to", "insurance_valid_to", "completed_on", "status")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..theka import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    pr = _s(a.get("project"))
    try:
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Owner only.")
            keys = ("firm", "gstin", "individual", "udyam", "registration", "registration_valid_to", "address", "morning_time")
            return S.save_settings(t, **{k: a[k] for k in keys if k in a})
        if action == "tender":
            return S.save_tender(t, _s(a.get("name")), _s(a.get("tender")), **{k: a[k] for k in _TENDER_KEYS if k in a})
        if action == "project":
            return S.save_project(t, _s(a.get("name")), pr, **{k: a[k] for k in _PROJECT_KEYS if k in a})
        if action == "boq":
            return S.boq(t, pr, a.get("items"), file_id=_s(a.get("file_id")), extra=bool(a.get("extra")))
        if action == "measure":
            return S.measure(t, pr, _s(a.get("item")), a.get("qty"), _s(a.get("detail")), _s(a.get("day")), _s(a.get("by")))
        if action == "ra_bill":
            return S.ra_bill(t, pr, _s(a.get("upto")), bool(a.get("final")), conv)
        if action == "bill_status":
            if _s(a.get("status")) == "submitted" and not _owner(ctx):
                raise ToolError("Only the owner can say yes to submitting the bill to the department.")
            return S.bill_status(t, _s(a.get("bill_id")), _s(a.get("status")), a.get("amount"), _s(a.get("on")))
        if action == "sub":
            return S.save_sub(t, _s(a.get("name")), _s(a.get("phone")), a.get("individual"), a.get("pan_ok"), _s(a.get("work")), a.get("retention_pct"),
                              _s(a.get("rate_basis")))
        if action == "sub_advance":
            return S.sub_advance(t, _s(a.get("sub")), a.get("advance"), pr, _s(a.get("day")), _s(a.get("note")))
        if action == "sub_bill":
            return S.sub_bill(t, _s(a.get("sub")), a.get("amount"), pr, _s(a.get("day")), _s(a.get("note")), a.get("advance_recover"))
        if action == "wage_calc":
            return S.wage_calc(t, pr, _s(a.get("gang")), a.get("workers"), a.get("days"), a.get("rate"), _s(a.get("basis")) or "day",
                               a.get("ot_hours"), a.get("advance_recover"), _s(a.get("note")))
        if action == "material":
            return S.material(t, pr, _s(a.get("item")), a.get("qty"), a.get("rate"), bool(a.get("used")), _s(a.get("day")), _s(a.get("note")))
        if action == "diary":
            return S.diary(t, pr, a.get("labour") or 0, _s(a.get("work")), _s(a.get("hindrance")), a.get("lost_hours"), bool(a.get("by_client")),
                           _s(a.get("day")))
        if action == "eot":
            return S.eot_letter(t, pr, conv)
        if action == "register":
            return S.register_file(t, conv)
    except (S.ThekaError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("invalid action")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..theka import rules as R
    from ..theka import service as S
    t, pr = ctx.tenant_id, _s(a.get("project"))
    try:
        if what == "day":
            return S.day(t)
        if what == "tenders":
            return {"tenders": S.tenders(t, _s(a.get("status")))}
        if what == "projects":
            return {"projects": S.projects(t, _s(a.get("status")))}
        if what == "project":
            return S.project_view(t, pr)
        if what == "boq":
            return {"items": S.boq_items(t, pr)}
        if what == "receivables":
            return S.receivables(t)
        if what == "stock":
            return {"stock": S.stock(t, pr)}
        if what == "sub":
            from ..db import session as _sess
            from sqlalchemy import select as _sel
            from ..theka.service import ThekaSub, ThekaSubAdvance, ThekaSubBill
            with _sess() as _s2:
                subs = _s2.scalars(_sel(ThekaSub).where(ThekaSub.tenant_id == t)).all()
                x = next((r for r in subs if _s(a.get("sub")).lower() in r.name.lower()), None) if subs else None
                if not x:
                    raise ToolError("Petty contractor not found.")
                advs = _s2.scalars(_sel(ThekaSubAdvance).where(ThekaSubAdvance.tenant_id == t, ThekaSubAdvance.sub_id == x.id)).all()
                bills = _s2.scalars(_sel(ThekaSubBill).where(ThekaSubBill.tenant_id == t, ThekaSubBill.sub_id == x.id)).all()
            return {"sub": {"name": x.name, "work": x.work, "rate_basis": x.rate_basis, "retention_pct": x.retention_pct,
                            "individual": x.individual, "pan_ok": x.pan_ok,
                            "open_advances": round(sum(a.amount for a in advs if not a.recovered), 2),
                            "advances": [{"day": a.day, "amount": a.amount, "recovered": a.recovered} for a in advs],
                            "bills": [{"day": b.day, "amount": b.amount, "net": b.net, "paid": b.paid} for b in bills]}}
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"never": list(R.NEVER), "gst_works": R.GST_WORKS, "gst_tds": R.GST_TDS, "it_tds": R.IT_TDS, "labour_cess": R.LABOUR_CESS, "docs": R.DOCS}
    except (S.ThekaError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("invalid what")


async def theka(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def theka_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


THEKA_HANDLERS = {"theka": theka, "theka_dekho": theka_dekho}
