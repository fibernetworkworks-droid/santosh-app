"""After-sales Sahayak tools. `service_desk_dekho` only reads; `service_desk` does the work. A charge to a customer is approved
and a business WhatsApp message is sent ONLY by her tap in the app (no tool action can do either); reminders and reports are
drafts. Hoola never collects money and never messages a customer by itself."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

AFTERSALES_TOOLS = [
    {"name": "service_desk", "description": (
        "After-sales service coworker for a dealer / service business (RO, AC, inverter / battery, CCTV, two-wheeler, car, solar, "
        "genset, lift, appliances, geyser, chimney, broadband). action=settings: business, phone, address, gstin, gst_on, prices "
        "{visit, <ptype>, parts {name: price}}, day_start, day_end, work_days [0=Mon..6], travel_minutes, remind_days, terms, rule, "
        "morning_time. action=schedule: ptype, months, usage (km / hours) - her own service interval. action=customer: name, phone, "
        "area, pincode, address, no_messages, marketing_ok (customer agreed to offers / renewal notices). action=unit (add / update a "
        "machine): unit (to update), ptype or product words, brand, model, serial, installed_on, purchased_on, warranty_months or "
        "warranty_until, last_service, reading, name, phone, area, pincode, address, status removed. action=import: file_id (her "
        "installed-base Excel / CSV). action=amc: unit, plan comprehensive|non_comprehensive, start, months, visits, price (her "
        "record). action=tech: name or tech, phone, skills [ptypes], areas [names / pincode prefixes], per_day, off_days, active. "
        "action=slots: unit, days, tech, day (free visit times grouped by area). action=book: unit, start ('kal 11 baje' or "
        "'2026-10-25 11:00'; empty = best free slot), tech, kind service|repair|install|amc|warranty|inspection, problem, force. "
        "action=reschedule: visit, start, tech. action=status: visit, status on_way|cancelled|no_show. action=job_card: visit. "
        "action=done: visit, checklist [items done ok], not_ok [items found faulty], readings {name: value}, parts [{name, qty, price, "
        "warranty_days}], labour, notes, signed_by, done_at. action=photo: visit, file_id, kind before|after|work|part|signature. "
        "action=report: visit (PDF + customer message draft). action=paid: visit, amount, how (owner; she says customer paid). "
        "action=remind: kind due|amc, within (days), unit (drafts only). action=message_sent: message_id (she sent it herself). "
        "action=claim: unit or visit, part, fault, brand_ref, amount. action=claim_update: claim, status raised|approved|"
        "part_received|rejected|settled, brand_ref, settled. Charging the customer and business WhatsApp sends happen only by "
        "her tap on the card in the app."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "schedule", "customer", "unit", "import", "amc", "tech", "slots", "book", "reschedule",
                                               "status", "job_card", "done", "photo", "report", "paid", "remind", "message_sent", "claim",
                                               "claim_update"]},
         "business": {"type": "string"}, "phone": {"type": "string"}, "address": {"type": "string"}, "gstin": {"type": "string"},
         "gst_on": {"type": "boolean"}, "prices": {"type": "object"}, "day_start": {"type": "string"}, "day_end": {"type": "string"},
         "work_days": {"type": "array", "items": {"type": "integer"}}, "travel_minutes": {"type": "integer"}, "remind_days": {"type": "integer"},
         "terms": {"type": "string"}, "rule": {"type": "string"}, "morning_time": {"type": "string"},
         "ptype": {"type": "string"}, "months": {"type": "number"}, "usage": {"type": "number"},
         "name": {"type": "string"}, "area": {"type": "string"}, "pincode": {"type": "string"}, "customer": {"type": "string"},
         "no_messages": {"type": "boolean"}, "marketing_ok": {"type": "boolean"}, "notes": {"type": "string"},
         "unit": {"type": "string"}, "brand": {"type": "string"}, "model": {"type": "string"}, "serial": {"type": "string"},
         "installed_on": {"type": "string"}, "purchased_on": {"type": "string"}, "warranty_months": {"type": "number"},
         "warranty_until": {"type": "string"}, "last_service": {"type": "string"}, "reading": {"type": "number"}, "status": {"type": "string"},
         "file_id": {"type": "string"}, "plan": {"type": "string"}, "start": {"type": "string"}, "visits": {"type": "integer"},
         "price": {"type": "number"}, "tech": {"type": "string"}, "skills": {"type": "array", "items": {"type": "string"}},
         "areas": {"type": "array", "items": {"type": "string"}}, "per_day": {"type": "integer"},
         "off_days": {"type": "array", "items": {"type": "integer"}}, "active": {"type": "boolean"}, "days": {"type": "integer"},
         "day": {"type": "string"}, "kind": {"type": "string"}, "problem": {"type": "string"}, "force": {"type": "boolean"},
         "minutes": {"type": "integer"}, "visit": {"type": "string"}, "checklist": {"type": "array", "items": {"type": "string"}}, "not_ok": {"type": "array", "items": {"type": "string"}}, "readings": {"type": "object"},
         "parts": {"type": "array", "items": {"type": "object"}}, "labour": {"type": "number"}, "signed_by": {"type": "string"},
         "done_at": {"type": "string"}, "amount": {"type": "number"}, "how": {"type": "string"}, "within": {"type": "integer"},
         "message_id": {"type": "string"}, "part": {"type": "string"}, "fault": {"type": "string"}, "brand_ref": {"type": "string"},
         "claim": {"type": "string"}, "settled": {"type": "number"}, "note": {"type": "string"}},
         "required": ["action"]}},
    {"name": "service_desk_dekho", "description": (
        "Read after-sales work (nothing changes). what=day (today's visits per technician, service due, AMC ending, charges waiting "
        "for her, reports not sent, stuck claims) | due (within days: machines due / late, AMC + warranty ending) | visits (day, "
        "status open|done, tech) | visit (visit) | units (q) | unit (unit: history, claims) | techs | slots (unit) | amc (revenue, "
        "renewals, expiring) | claims | messages (drafts) | templates (WhatsApp templates + Meta status) | schedules | settings | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "due", "visits", "visit", "units", "unit", "techs", "slots", "amc", "claims", "messages",
                                             "templates", "schedules", "settings", "rules"]},
         "within": {"type": "integer"}, "day": {"type": "string"}, "status": {"type": "string"}, "tech": {"type": "string"},
         "visit": {"type": "string"}, "q": {"type": "string"}, "unit": {"type": "string"}, "days": {"type": "integer"}},
         "required": ["what"]}},
]
AFTERSALES_LABELS = {"service_desk": "Service ka kaam kar raha hoon", "service_desk_dekho": "Service register dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _pick(a: dict, keys: tuple) -> dict:
    return {k: a[k] for k in keys if k in a}


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..aftersales import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    by = getattr(ctx, "actor", "owner") or "owner"
    try:
        if action in ("settings", "schedule", "amc", "paid") and not _owner(ctx):
            raise ToolError("Yeh sirf owner kar sakti hain.")
        if action == "settings":
            return S.save_settings(t, **_pick(a, ("business", "phone", "address", "gstin", "gst_on", "gst_pct", "sac", "prices", "day_start",
                                                  "day_end", "work_days", "travel_minutes", "lead_minutes", "remind_days", "terms", "rule",
                                                  "morning_time")))
        if action == "schedule":
            return S.set_schedule(t, _s(a.get("ptype")), a.get("months"), a.get("usage"))
        if action == "customer":
            return S.save_customer(t, **_pick(a, ("name", "phone", "area", "pincode", "address", "customer", "no_messages", "marketing_ok", "notes")))
        if action == "unit":
            return S.save_unit(t, **_pick(a, ("unit", "ptype", "brand", "model", "serial", "installed_on", "purchased_on", "warranty_months",
                                              "warranty_until", "last_service", "reading", "notes", "name", "phone", "area", "pincode", "address",
                                              "customer", "status")))
        if action == "import":
            if not a.get("file_id"):
                raise ToolError("file_id chahiye (sheet chat mein bhejiye).")
            return S.import_units(t, file_id=_s(a.get("file_id")))
        if action == "amc":
            return S.set_amc(t, _s(a.get("unit")), _s(a.get("plan")) or "non_comprehensive", _s(a.get("start")), a.get("months") or 12,
                             a.get("visits"), a.get("price"))
        if action == "tech":
            return S.save_tech(t, **_pick(a, ("name", "tech", "phone", "skills", "areas", "per_day", "off_days", "active")))
        if action == "slots":
            return S.slots(t, _s(a.get("unit")), int(a.get("days") or 5), _s(a.get("tech")), _s(a.get("day")), a.get("minutes"))
        if action == "book":
            return S.book(t, _s(a.get("unit")), _s(a.get("start")), _s(a.get("tech")), _s(a.get("kind")) or "service", _s(a.get("problem")),
                          a.get("minutes"), bool(a.get("force")), conv, by)
        if action == "reschedule":
            return S.reschedule(t, _s(a.get("visit")), _s(a.get("start")), _s(a.get("tech")), bool(a.get("force")), conv)
        if action == "status":
            st = {"cancel": "cancelled"}.get(_s(a.get("status")), _s(a.get("status")))
            return S.set_status(t, _s(a.get("visit")), st, _s(a.get("note")), by)
        if action == "job_card":
            return S.job_card(t, _s(a.get("visit")))
        if action == "done":
            cl = a.get("checklist")
            if isinstance(cl, list) and a.get("not_ok"):
                cl = {**{str(x): "ok" for x in cl}, **{str(x): "not_ok" for x in a["not_ok"]}}
            return S.complete(t, _s(a.get("visit")), cl, a.get("readings"), a.get("parts"), a.get("labour"), _s(a.get("notes")),
                              _s(a.get("signed_by")), _s(a.get("done_at")), conv, by)
        if action == "photo":
            return S.attach_file(t, _s(a.get("visit")), _s(a.get("file_id")), _s(a.get("kind")) or "work")
        if action == "report":
            return S.report(t, _s(a.get("visit")), conv)
        if action == "paid":
            return S.mark_paid(t, _s(a.get("visit")), a.get("amount"), _s(a.get("how")))
        if action == "remind":
            return S.remind(t, a.get("within"), _s(a.get("kind")) or "due", _s(a.get("unit")), conv)
        if action == "message_sent":
            return S.message_mark(t, _s(a.get("message_id")), "sent")
        if action == "claim":
            return S.claim(t, _s(a.get("unit")), _s(a.get("visit")), _s(a.get("part")), _s(a.get("fault")), _s(a.get("brand_ref")), a.get("amount"))
        if action == "claim_update":
            return S.claim_update(t, _s(a.get("claim")), _s(a.get("status")), _s(a.get("brand_ref")), a.get("settled"), _s(a.get("note")))
    except (S.AsError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..aftersales import rules as R
    from ..aftersales import service as S
    t = ctx.tenant_id
    try:
        if what == "day":
            return S.day(t)
        if what == "due":
            return S.due(t, int(a.get("within") or 15))
        if what == "visits":
            return {"visits": S.visits(t, _s(a.get("day")), _s(a.get("status")), _s(a.get("tech")))}
        if what == "visit":
            return S.get_visit(t, _s(a.get("visit")))
        if what == "units":
            return {"units": S.units(t, _s(a.get("q")))}
        if what == "unit":
            return S.get_unit(t, _s(a.get("unit")))
        if what == "techs":
            return {"techs": S.techs(t)}
        if what == "slots":
            return S.slots(t, _s(a.get("unit")), int(a.get("days") or 5), _s(a.get("tech")), _s(a.get("day")))
        if what == "amc":
            return S.amc_view(t)
        if what == "claims":
            return S.claims(t, _s(a.get("status")))
        if what == "messages":
            return {"messages": S.messages(t, _s(a.get("status")) or "draft")}
        if what == "templates":
            return {"templates": S.templates(t)}
        if what == "schedules":
            return {"schedules": S.schedules(t)}
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"never": list(R.NEVER), "products": {k: {"label": p["label"], "months": p["months"], "usage": p.get("usage"),
                                                            "checklist": p["checklist"]} for k, p in R.PRODUCTS.items()},
                    "templates": {k: v["category"] for k, v in R.TEMPLATES.items()}}
    except (S.AsError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def service_desk(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def service_desk_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


AFTERSALES_HANDLERS = {"service_desk": service_desk, "service_desk_dekho": service_desk_dekho}
