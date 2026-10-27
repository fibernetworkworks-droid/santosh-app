"""Interior Sahayak tools (interior designer's coworker). `interior_dekho` only reads; `interior` does the work.

The quotation going to the client, any vendor order, a change order that changes the price and any payment request become
CARDS here; only HER tap in the app (API) decides them. Hoola never invents a rate, size or brand price (blanks instead), never
sends a message by itself, never collects or pays money."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["settings", "rate", "rate_import", "vendor", "project", "brief", "measure", "measure_sheet", "concept", "render3d", "boq",
            "boq_remove", "boq_file", "quote", "quote_send", "quote_mark", "stage_due", "pay_request", "paid", "order", "order_done",
            "change", "task", "task_update", "snag", "snag_photo", "snag_status", "handover", "forget"]

INTERIOR_TOOLS = [
    {"name": "interior", "description": (
        "Interior designer's coworker (homes, offices, shops), end to end. NEVER invent a rate, size, quantity or brand price: "
        "missing ones stay blank and you ask her. action=settings*: firm, title (never 'architect' unless coa_reg), coa_reg, gstin, "
        "address, phone, email, upi_id, fee_mode none|percent|sqft|flat + fee_value, gst_works, gst_design, stages [{label, pct}] "
        "(must total 100), terms, validity_days, warranty {kind: her words}, measure_unit ft|m|mm, morning_time. action=rate*: her "
        "rate card line: name, rate (her selling rate per unit before GST), unit sqft|rft|nos|point|sqm|set|lumpsum, kind, code, "
        "spec (material / brand / finish SHE said), gst_pct. action=rate_import*: file_id (Excel / CSV). action=vendor: name, trade, "
        "phone. action=project: name / project (to update), client, phone, site, city, pin, client_state (2-digit code), home "
        "(2BHK / office ...), carpet_sqft, budget (client's), style, target_handover. action=brief: project, room (optional), "
        "room_type, style, budget, must [], avoid [], notes (client's words are data). action=measure: project, room, l, w, h "
        "(12, 12.5, 12'6\", 3.6 m), unit, openings [{kind door|window, w, h, count}], by. action=measure_sheet (Excel). "
        "action=concept: project, room, style, words, pictures 0-3 (AI pictures, labelled 'AI se bana'), file_ids (her photos), "
        "brand_colors. action=render3d: project, room (3D Studio). action=boq: project, lines [{room, name or code, qty or "
        "qty_from floor|ceiling|wall|wall_ceiling|skirting|perimeter, unit, rate only if she said it for this line, spec, gst_pct, "
        "id to replace}], replace. action=boq_remove: project, line. action=boq_file. action=quote: project (draft revision). "
        "action=quote_send: quote (number / id) -> only a CARD for her tap. action=quote_mark: quote, what sent|accepted*|rejected. "
        "action=stage_due: stage, due_on. action=pay_request: stage -> CARD. action=paid*: stage, amount, ref. action=order: project, "
        "vendor, lines [{line (BOQ id) or name, qty, unit, rate = the VENDOR's rate she said}], amount, start, finish, notes -> CARD. "
        "action=order_done: order. action=change: project, what, add [lines], remove [BOQ line ids] -> card when the price changes. "
        "action=task: project, what, kind, room, vendor, start, end. action=task_update: task, status planned|started|done|delayed|"
        "cancelled, start, end, note. action=snag: project, what, room, vendor, file_id (photo). action=snag_photo: snag, file_id, "
        "stage before|fixed. action=snag_status: snag, status open|fixed|closed*. action=handover*: project, force, reason. "
        "action=forget*: project (DPDP, after done). * = owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS},
         "project": {"type": "string"}, "name": {"type": "string"}, "client": {"type": "string"}, "phone": {"type": "string"},
         "email": {"type": "string"}, "site": {"type": "string"}, "city": {"type": "string"}, "pin": {"type": "string"},
         "client_state": {"type": "string"}, "client_gstin": {"type": "string"}, "home": {"type": "string"},
         "carpet_sqft": {"type": "number"}, "budget": {"type": "number"}, "style": {"type": "string"},
         "target_handover": {"type": "string"}, "status": {"type": "string"}, "room": {"type": "string"},
         "room_type": {"type": "string"}, "must": {"type": "array", "items": {"type": "string"}},
         "avoid": {"type": "array", "items": {"type": "string"}}, "notes": {"type": "string"}, "l": {"type": "string"},
         "w": {"type": "string"}, "h": {"type": "string"}, "unit": {"type": "string"},
         "openings": {"type": "array", "items": {"type": "object"}}, "by": {"type": "string"}, "words": {"type": "string"},
         "pictures": {"type": "integer"}, "file_ids": {"type": "array", "items": {"type": "string"}}, "file_id": {"type": "string"},
         "brand_colors": {"type": "boolean"}, "lines": {"type": "array", "items": {"type": "object"}}, "replace": {"type": "boolean"},
         "line": {"type": "string"}, "quote": {"type": "string"}, "what": {"type": "string"}, "stage": {"type": "string"},
         "due_on": {"type": "string"}, "amount": {"type": "number"}, "ref": {"type": "string"}, "vendor": {"type": "string"},
         "trade": {"type": "string"}, "order": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"},
         "finish": {"type": "string"}, "add": {"type": "array", "items": {"type": "object"}},
         "remove": {"type": "array", "items": {"type": "string"}}, "kind": {"type": "string"}, "task": {"type": "string"},
         "note": {"type": "string"}, "snag": {"type": "string"}, "force": {"type": "boolean"}, "reason": {"type": "string"},
         "rate": {"type": "number"}, "code": {"type": "string"}, "spec": {"type": "string"}, "gst_pct": {"type": "number"},
         "hsn_sac": {"type": "string"}, "firm": {"type": "string"}, "title": {"type": "string"}, "coa_reg": {"type": "string"},
         "gstin": {"type": "string"}, "address": {"type": "string"}, "upi_id": {"type": "string"}, "fee_mode": {"type": "string"},
         "fee_value": {"type": "number"}, "gst_works": {"type": "number"}, "gst_design": {"type": "number"},
         "stages": {"type": "array", "items": {"type": "object"}}, "terms": {"type": "string"}, "validity_days": {"type": "integer"},
         "warranty": {"type": "object"}, "measure_unit": {"type": "string"}, "morning_time": {"type": "string"},
         "rules": {"type": "string"}},
         "required": ["action"]}},
    {"name": "interior_dekho", "description": (
        "Read interior work (nothing changes). what=day (today's installation, late work, payment stages due, open snags, quotes "
        "expiring, cards waiting for her) | projects | project (project: brief, rooms with measurements, BOQ, quotes, stages, "
        "orders, changes, schedule, snags) | boq (project) | rates (q) | vendors | stages (project) | schedule (project) | snags "
        "(project) | quote (quote) | waiting | warranty (project) | settings | styles."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "projects", "project", "boq", "rates", "vendors", "stages", "schedule", "snags",
                                             "quote", "waiting", "warranty", "settings", "styles"]},
         "project": {"type": "string"}, "quote": {"type": "string"}, "q": {"type": "string"}, "status": {"type": "string"}},
         "required": ["what"]}},
]
INTERIOR_LABELS = {"interior": "Interior ka kaam kar raha hoon", "interior_dekho": "Interior project dekh raha hoon"}

_OWNER_ONLY = {"settings", "rate", "rate_import", "paid", "handover", "forget"}
_SET_KEYS = ("firm", "title", "coa_reg", "gstin", "state_code", "address", "phone", "email", "upi_id", "fee_mode", "fee_value",
             "gst_works", "gst_design", "stages", "terms", "validity_days", "warranty", "measure_unit", "morning_time", "rules")
_PROJ_KEYS = ("client", "phone", "email", "site", "city", "pin", "client_state", "client_gstin", "home", "carpet_sqft", "budget",
              "style", "target_handover", "status")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..interior import service as S
    t, conv, actor = ctx.tenant_id, ctx.conversation_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner.")
    pr = _s(a.get("project"))
    try:
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in _SET_KEYS if k in a})
        if action == "rate":
            return S.rate_save(t, _s(a.get("name")), a.get("rate"), _s(a.get("unit")), _s(a.get("kind")), _s(a.get("code")),
                               _s(a.get("spec")), _s(a.get("hsn_sac")), a.get("gst_pct"))
        if action == "rate_import":
            return S.import_rates(t, _s(a.get("file_id")))
        if action == "vendor":
            return S.vendor_save(t, _s(a.get("vendor") or a.get("name")), _s(a.get("trade")), _s(a.get("phone")), "", _s(a.get("notes")))
        if action == "project":
            kw = {k: a[k] for k in _PROJ_KEYS if k in a}
            return S.project_save(t, _s(a.get("name")), pr, actor, conv, **kw)
        if action == "brief":
            return S.brief(t, pr, _s(a.get("room")), _s(a.get("style")), a.get("budget"), a.get("must"), a.get("avoid"),
                           _s(a.get("notes")), _s(a.get("room_type")), actor)
        if action == "measure":
            return S.measure(t, pr, _s(a.get("room")), a.get("l"), a.get("w"), a.get("h"), _s(a.get("unit")), a.get("openings"),
                             _s(a.get("notes")), _s(a.get("by")), actor)
        if action == "measure_sheet":
            return S.measure_sheet(t, pr, conv)
        if action == "concept":
            return S.concept(t, pr, _s(a.get("room")), _s(a.get("style")), _s(a.get("words")), int(a.get("pictures") or 0),
                             a.get("file_ids"), bool(a.get("brand_colors")), conv, actor)
        if action == "render3d":
            return S.render3d(t, pr, _s(a.get("room")), _s(a.get("words")), conv, actor)
        if action == "boq":
            return S.boq_set(t, pr, a.get("lines"), bool(a.get("replace")), actor)
        if action == "boq_remove":
            return S.boq_remove(t, pr, _s(a.get("line")))
        if action == "boq_file":
            return S.boq_file(t, pr, conv)
        if action == "quote":
            return S.quote_make(t, pr, conv, actor)
        if action == "quote_send":
            return S.quote_request(t, _s(a.get("quote")), conv, actor)
        if action == "quote_mark":
            return S.quote_mark(t, _s(a.get("quote")), _s(a.get("what")), actor)
        if action == "stage_due":
            return S.stage_due(t, _s(a.get("stage")), _s(a.get("due_on")))
        if action == "pay_request":
            return S.pay_request(t, _s(a.get("stage")), conv, actor)
        if action == "paid":
            return S.stage_paid(t, _s(a.get("stage")), a.get("amount"), _s(a.get("ref")), "", actor)
        if action == "order":
            return S.order_request(t, pr, _s(a.get("vendor")), a.get("lines"), a.get("amount"), _s(a.get("start")),
                                   _s(a.get("finish") or a.get("end")), _s(a.get("notes")), actor, conv)
        if action == "order_done":
            return S.order_done(t, _s(a.get("order")), actor)
        if action == "change":
            return S.change_request(t, pr, _s(a.get("what")), a.get("add"), a.get("remove"), actor, conv)
        if action == "task":
            return S.task_add(t, pr, _s(a.get("what")), _s(a.get("kind")), _s(a.get("room")), _s(a.get("vendor")), _s(a.get("start")),
                              _s(a.get("end")), _s(a.get("note")), actor)
        if action == "task_update":
            return S.task_update(t, _s(a.get("task")), _s(a.get("status")), _s(a.get("start")), _s(a.get("end")), _s(a.get("note")), actor)
        if action == "snag":
            return S.snag_add(t, pr, _s(a.get("what")), _s(a.get("room")), _s(a.get("vendor")), _s(a.get("file_id")), None, actor)
        if action == "snag_photo":
            return S.snag_photo(t, _s(a.get("snag")), None, _s(a.get("file_id")), _s(a.get("stage")) or "fixed")
        if action == "snag_status":
            return S.snag_status(t, _s(a.get("snag")), _s(a.get("status")), actor)
        if action == "handover":
            return S.handover(t, pr, bool(a.get("force")), _s(a.get("reason")), actor, conv)
        if action == "forget":
            return S.forget(t, pr, actor)
    except S.InteriorError as e:
        raise ToolError(str(e))
    raise ToolError(f"action '{action}' nahi pehchana.")


def _see(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..interior import rules as R
    from ..interior import service as S
    t, pr = ctx.tenant_id, _s(a.get("project"))
    try:
        if what == "day":
            return S.day(t)
        if what == "projects":
            return {"projects": S.projects(t, _s(a.get("status")))}
        if what == "project":
            return S.project_view(t, pr)
        if what == "boq":
            return S.boq(t, pr)
        if what == "rates":
            return {"rates": S.rates(t, _s(a.get("q")))}
        if what == "vendors":
            return {"vendors": S.vendors(t)}
        if what == "stages":
            return S.stages(t, pr)
        if what == "schedule":
            return S.schedule(t, pr)
        if what == "snags":
            return {"snags": S.snags(t, pr, _s(a.get("status")))}
        if what == "quote":
            return S.quote_view(t, _s(a.get("quote")))
        if what == "waiting":
            return S.waiting(t)
        if what == "warranty":
            return {"warranty": S.warranty_rows(t, pr)}
        if what == "settings":
            return S.settings(t)
        if what == "styles":
            return {"styles": {k: {"label": v["label"], "palette": v["palette"], "materials": v["materials"]} for k, v in R.STYLES.items()},
                    "kinds": {k: {"label": v["label"], "unit": v["unit"]} for k, v in R.KINDS.items()}}
    except S.InteriorError as e:
        raise ToolError(str(e))
    raise ToolError(f"what '{what}' nahi pehchana.")


async def _interior(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_act, ctx, action, a)


async def _interior_dekho(ctx: Ctx, what: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_see, ctx, what, a)


INTERIOR_HANDLERS = {"interior": _interior, "interior_dekho": _interior_dekho}
