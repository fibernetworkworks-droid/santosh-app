"""Rentdesk Sahayak tools (property manager). `rentdesk_dekho` only reads; `rentdesk` does the work. A deposit deduction, a rent
change / notice, a repair spend and EVERY message to a tenant are only cards / drafts here: her tap in the app decides them.
Hoola never takes or pays money. Customer-safe tools for tenants on her business WhatsApp: RENTDESK_BIZ_*."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

RENTDESK_TOOLS = [
    {"name": "rentdesk", "description": (
        "Property manager's coworker (rented flats / houses / rooms / PG beds / shops / offices). action=settings (owner): business, "
        "landlord_name, landlord_address, landlord_phone, pan (goes to her Pehchaan Locker), receipt_full_pan, state (MH...), city, "
        "upi_id, upi_name, gstin, agency, remind_before, grace_days, renewal_windows, minor_repair_limit, mirror_dues, morning_time, rules. "
        "action=unit: unit (existing) or label (new: 'Flat 302'), building, kind flat|house|room|pg_bed|shop|office|godown, use, address, "
        "city, pin, area_sqft (HER number), furnished, inventory ['2 fan', ...], owner_name/owner_phone (agency), rent_ask, deposit_ask, "
        "maintenance. action=person: person (existing) or name + phone, email, kind individual|family|student|company|firm, employer, "
        "address, members, gstin, composition, aadhaar / pan (straight into the locker, only masked kept), no_messages. "
        "action=tenancy (new draft): unit, person, start, months (11), rent, deposit, maintenance, maintenance_by tenant|owner, due_day, "
        "escalation_pct, escalation_every (months), lock_in_months, notice_months, kind leave_licence|rent|mta, purpose, stamp_duty / "
        "reg_fee (HER numbers from IGR). action=update: tenancy + same fields (money fields only while draft). action=activate (owner): "
        "tenancy. action=check: tenancy, item registration|police|agreement|kyc|society|move_in|deposit_receipt|rent_authority, done, "
        "ref (doc / police ref), on. action=agreement: tenancy -> Word draft for her lawyer. action=received (owner): tenancy, amount, "
        "on, mode upi|bank|cash|cheque, ref -> receipt. action=receipt: payment -> PDF. action=charge (owner): tenancy, kind electricity|"
        "water|late_fee|other, amount (bill / agreement). action=waive (owner): charge. action=pay_link: tenancy (UPI to HER UPI ID). "
        "action=message: tenancy, kind reminder|late|custom|repair, text -> DRAFT only (her tap sends). action=rent_change: tenancy, "
        "new_rent (or agreement %), from, why -> CARD for her tap. action=notice: tenancy, kind vacate|renewal, vacate_on, reason, "
        "new_rent, from -> CARD. action=tenant_notice: tenancy, vacate_on (the tenant gave notice). action=repair: unit, text. "
        "action=assign: request, vendor, quote, who_pays -> repair CARD when quoted. action=repair_done: request, paid, note. "
        "action=vendor: name, phone, trade plumber|electrician|carpenter|painter|appliance|pest|cleaning|gas|internet|civil|other. "
        "action=inspection: tenancy, kind move_in|move_out. action=inspect: inspection, items [{room, item, condition good|fair|damaged|"
        "missing, note}], meters {electricity: n}, keys, close. action=settlement: tenancy (start). action=deduct: settlement, what, "
        "amount (HER number), reason, remove. action=settle: settlement -> deduction CARD. action=refund_done (owner): settlement, amount, "
        "ref. action=settlement_file: settlement. action=forget (owner): person (DPDP, after the tenancy ended). action=register (Excel). "
        "action=from_deal (owner): deal (Property Sahayak D-0001 rent deal), start -> a DRAFT tenancy from that deal (nothing billed / sent)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "unit", "person", "tenancy", "update", "activate", "check", "agreement",
                                               "received", "receipt", "charge", "waive", "pay_link", "message", "rent_change", "notice",
                                               "tenant_notice", "repair", "assign", "repair_done", "vendor", "inspection", "inspect",
                                               "settlement", "deduct", "settle", "refund_done", "settlement_file", "forget", "register",
                                               "from_deal"]},
         "deal": {"type": "string"},
         "business": {"type": "string"}, "landlord_name": {"type": "string"}, "landlord_address": {"type": "string"},
         "landlord_phone": {"type": "string"}, "pan": {"type": "string"}, "receipt_full_pan": {"type": "boolean"},
         "state": {"type": "string"}, "city": {"type": "string"}, "upi_id": {"type": "string"}, "upi_name": {"type": "string"},
         "gstin": {"type": "string"}, "agency": {"type": "boolean"}, "remind_before": {"type": "integer"},
         "grace_days": {"type": "integer"}, "renewal_windows": {"type": "array", "items": {"type": "integer"}},
         "minor_repair_limit": {"type": "number"}, "mirror_dues": {"type": "boolean"}, "morning_time": {"type": "string"},
         "rules": {"type": "string"}, "unit": {"type": "string"}, "label": {"type": "string"}, "building": {"type": "string"},
         "kind": {"type": "string"}, "use": {"type": "string"}, "address": {"type": "string"}, "pin": {"type": "string"},
         "area_sqft": {"type": "number"}, "furnished": {"type": "string"}, "inventory": {"type": "array", "items": {}},
         "owner_name": {"type": "string"}, "owner_phone": {"type": "string"}, "rent_ask": {"type": "number"},
         "deposit_ask": {"type": "number"}, "maintenance": {"type": "number"}, "person": {"type": "string"}, "name": {"type": "string"},
         "phone": {"type": "string"}, "email": {"type": "string"}, "employer": {"type": "string"}, "members": {"type": "array", "items": {"type": "string"}},
         "composition": {"type": "boolean"}, "aadhaar": {"type": "string"}, "no_messages": {"type": "boolean"},
         "tenancy": {"type": "string"}, "start": {"type": "string"}, "months": {"type": "integer"}, "rent": {"type": "number"},
         "deposit": {"type": "number"}, "maintenance_by": {"type": "string"}, "due_day": {"type": "integer"},
         "escalation_pct": {"type": "number"}, "escalation_every": {"type": "integer"}, "lock_in_months": {"type": "integer"},
         "notice_months": {"type": "integer"}, "purpose": {"type": "string"}, "stamp_duty": {"type": "number"}, "reg_fee": {"type": "number"},
         "item": {"type": "string"}, "done": {"type": "boolean"}, "ref": {"type": "string"}, "on": {"type": "string"},
         "amount": {"type": "number"}, "mode": {"type": "string"}, "payment": {"type": "string"}, "charge": {"type": "string"},
         "text": {"type": "string"}, "new_rent": {"type": "number"}, "from": {"type": "string"}, "why": {"type": "string"},
         "vacate_on": {"type": "string"}, "reason": {"type": "string"}, "request": {"type": "string"}, "vendor": {"type": "string"},
         "quote": {"type": "number"}, "who_pays": {"type": "string"}, "paid": {"type": "number"}, "note": {"type": "string"},
         "trade": {"type": "string"}, "inspection": {"type": "string"}, "items": {"type": "array", "items": {"type": "object"}},
         "meters": {"type": "object"}, "keys": {"type": "integer"}, "close": {"type": "boolean"}, "settlement": {"type": "string"},
         "what": {"type": "string"}, "remove": {"type": "boolean"}, "notes": {"type": "string"}},
         "required": ["action"]}},
    {"name": "rentdesk_dekho", "description": (
        "Read the rental book (nothing changes). what=day (dues overdue / today, drafts and cards waiting for her, renewals, registration "
        "/ police pending, repairs, vacating, vacant units) | units (status vacant|occupied|notice) | people (q) | tenancies (status) | "
        "tenancy (tenancy: ledger, payments, checklist, law / TDS / GST notes, files) | statement (tenancy) | approvals | messages | "
        "requests (status open|done...) | vendors | compare (tenancy: move-in vs move-out) | settings | rules (never-list + dated sources)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "units", "people", "tenancies", "tenancy", "statement", "approvals", "messages",
                                             "requests", "vendors", "compare", "settings", "rules"]},
         "tenancy": {"type": "string"}, "status": {"type": "string"}, "q": {"type": "string"}},
         "required": ["what"]}},
]
RENTDESK_LABELS = {"rentdesk": "Kiraye ka kaam kar raha hoon", "rentdesk_dekho": "Kiraye ka hisaab dekh raha hoon"}

OWNER_ONLY = ("settings", "activate", "received", "charge", "waive", "refund_done", "forget", "unit", "person", "tenancy", "update", "from_deal")
STAFF_OK = ("check", "agreement", "receipt", "pay_link", "message", "rent_change", "notice", "tenant_notice", "repair", "assign",
            "repair_done", "vendor", "inspection", "inspect", "settlement", "deduct", "settle", "settlement_file", "register")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


_SET = ("business", "landlord_name", "landlord_address", "landlord_phone", "receipt_full_pan", "state", "city", "upi_id", "upi_name",
        "gstin", "agency", "remind_before", "grace_days", "renewal_windows", "minor_repair_limit", "mirror_dues", "morning_time", "rules")
_UNIT = ("label", "building", "kind", "use", "address", "city", "pin", "area_sqft", "furnished", "inventory", "owner_name",
         "owner_phone", "rent_ask", "deposit_ask", "maintenance", "notes")
_PERSON = ("email", "kind", "employer", "address", "members", "emergency", "gstin", "composition", "no_messages", "notes")
_TEN = ("kind", "start", "months", "rent", "deposit", "maintenance", "maintenance_by", "due_day", "escalation_pct", "escalation_every",
        "lock_in_months", "notice_months", "purpose", "stamp_duty", "reg_fee", "notes")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..rentdesk import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("Kiraye ka kaam graahak ke liye nahi (unke liye biz_rent_status / biz_rent_repair).")
    if action in OWNER_ONLY and not _owner(ctx):
        raise ToolError("Yeh sirf owner kar sakti hain.")
    tn = _s(a.get("tenancy"))
    try:
        if action == "settings":
            return S.save_settings(t, _s(a.get("pan")), **{k: a[k] for k in _SET if k in a})
        if action == "unit":
            return S.save_unit(t, _s(a.get("unit")), **{k: a[k] for k in _UNIT if k in a})
        if action == "person":
            return S.save_person(t, _s(a.get("person")), _s(a.get("name")), _s(a.get("phone")), _s(a.get("aadhaar")), _s(a.get("pan")),
                                 **{k: a[k] for k in _PERSON if k in a})
        if action == "tenancy":
            return S.new_tenancy(t, _s(a.get("unit")), _s(a.get("person")), actor, conv, **{k: a[k] for k in _TEN if k in a})
        if action == "from_deal":
            return S.from_propagent_deal(t, _s(a.get("deal")), _s(a.get("start")), actor, conv)
        if action == "update":
            return S.update_tenancy(t, tn, **{k: a[k] for k in _TEN if k in a})
        if action == "activate":
            return S.activate(t, tn, conv)
        if action == "check":
            return S.check_item(t, tn, _s(a.get("item")), a.get("done", True) is not False, _s(a.get("ref")), _s(a.get("on")))
        if action == "agreement":
            return S.agreement_file(t, tn, conv)
        if action == "received":
            return S.receive(t, tn, a.get("amount"), _s(a.get("on")), _s(a.get("mode") or "upi"), _s(a.get("ref")), _s(a.get("charge")),
                             actor, conv)
        if action == "receipt":
            return S.receipt_file(t, _s(a.get("payment")), conv)
        if action == "charge":
            return S.add_charge(t, tn, _s(a.get("kind") or "other"), a.get("amount"), _s(a.get("on")), _s(a.get("note")), actor)
        if action == "waive":
            return S.waive(t, _s(a.get("charge")), actor)
        if action == "pay_link":
            return S.pay_link(t, tn)
        if action == "message":
            return S.draft_message(t, tn, _s(a.get("kind") or "custom"), _s(a.get("text")), conv=conv, summary=_s(a.get("text")))
        if action == "rent_change":
            return S.rent_change(t, tn, a.get("new_rent"), _s(a.get("from")), _s(a.get("why")), _s(a.get("ref")), actor, conv)
        if action == "notice":
            return S.notice_request(t, tn, _s(a.get("kind") or "vacate"), _s(a.get("vacate_on")), _s(a.get("reason")), a.get("new_rent"),
                                    _s(a.get("from")), actor, conv)
        if action == "tenant_notice":
            return S.tenant_notice(t, tn, _s(a.get("vacate_on")), _s(a.get("on")), actor)
        if action == "repair":
            return S.request_new(t, _s(a.get("unit")), _s(a.get("text")), actor, conv=conv)
        if action == "assign":
            return S.request_assign(t, _s(a.get("request")), _s(a.get("vendor")), a.get("quote"), _s(a.get("who_pays")), actor, conv)
        if action == "repair_done":
            return S.request_done(t, _s(a.get("request")), a.get("paid"), _s(a.get("note")), actor)
        if action == "vendor":
            return S.save_vendor(t, _s(a.get("name")), _s(a.get("phone")), _s(a.get("trade") or "other"), _s(a.get("notes")),
                                 _s(a.get("vendor")))
        if action == "inspection":
            return S.inspection_start(t, tn, _s(a.get("kind") or "move_in"), _s(a.get("on")))
        if action == "inspect":
            return S.inspection_update(t, _s(a.get("inspection")), a.get("items"), a.get("meters"), a.get("keys"), _s(a.get("name")),
                                       bool(a.get("close")))
        if action == "settlement":
            return S.settlement_start(t, tn)
        if action == "deduct":
            return S.settlement_line(t, _s(a.get("settlement")), _s(a.get("what")), a.get("amount"), _s(a.get("reason")), None,
                                     bool(a.get("remove")), actor)
        if action == "settle":
            return S.settlement_request(t, _s(a.get("settlement")), actor, conv)
        if action == "refund_done":
            return S.refund_paid(t, _s(a.get("settlement")), a.get("amount"), _s(a.get("ref")), actor)
        if action == "settlement_file":
            return S.settlement_file(t, _s(a.get("settlement")), conv)
        if action == "forget":
            return S.forget(t, _s(a.get("person")), actor)
        if action == "register":
            return S.register_file(t, conv)
    except (S.RentError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..rentdesk import rules as R
    from ..rentdesk import service as S
    t, tn = ctx.tenant_id, _s(a.get("tenancy"))
    if (getattr(ctx, "actor", "owner") or "").startswith("customer:"):
        raise ToolError("Kiraye ki jaankari graahak ke liye nahi.")
    try:
        if what == "day":
            return S.day(t)
        if what == "units":
            return {"units": S.units(t, _s(a.get("status")))}
        if what == "people":
            return {"people": S.people(t, _s(a.get("q")))}
        if what == "tenancies":
            return {"tenancies": S.tenancies(t, _s(a.get("status")))}
        if what == "tenancy":
            return S.tenancy_view(t, tn)
        if what == "statement":
            return S.statement(t, tn)
        if what == "approvals":
            return {"approvals": S.approvals(t, _s(a.get("status") or "waiting"))}
        if what == "messages":
            return {"messages": S.messages(t, _s(a.get("status") or "draft"))}
        if what == "requests":
            return {"requests": S.requests(t, _s(a.get("status")))}
        if what == "vendors":
            return {"vendors": S.vendors(t)}
        if what == "compare":
            return S.inspection_compare(t, tn)
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"never": list(R.NEVER), "sources": [{"what": w, "url": u, "date": d} for w, u, d in R.SOURCES]}
    except (S.RentError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def rentdesk(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def rentdesk_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


RENTDESK_HANDLERS = {"rentdesk": rentdesk, "rentdesk_dekho": rentdesk_dekho}


# ---------------------------------------------------------------- tenants on her business WhatsApp (customer-safe)
async def biz_rent_status(ctx: Ctx, **_: Any):
    """THIS tenant's own rent: what is due, the UPI link to the owner's UPI ID. Only by their own number."""
    from ..employee import inbox
    from ..rentdesk import service as S
    c = inbox._contact(ctx)
    return await asyncio.to_thread(S.customer_status, ctx.tenant_id, c.wa_id)


async def biz_rent_repair(ctx: Ctx, text: str = "", **_: Any):
    """THIS tenant reports a repair. Recorded for the owner; the owner decides any spend."""
    from ..employee import inbox
    from ..rentdesk import service as S
    c = inbox._contact(ctx)
    if not str(text).strip():
        raise ToolError("Kya kharab hai, likh dijiye.")
    try:
        return await asyncio.to_thread(S.customer_repair, ctx.tenant_id, c.wa_id, str(text)[:1000])
    except S.RentError as e:
        raise ToolError(str(e))


RENTDESK_BIZ_TOOLS = [
    {"name": "biz_rent_status", "description": ("THIS tenant's own rent account by their WhatsApp number: rent, what is due now, open "
                                                "lines, agreement end, UPI link to the owner's UPI ID (they pay in their own app). "
                                                "Never another tenant's details; never say money was received (only the owner says that)."),
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "biz_rent_repair", "description": ("THIS tenant reports something broken in their rented unit (tap leak, light, lock...). "
                                                "Only records it for the owner; never promise a visit time or who pays."),
     "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
]
RENTDESK_BIZ_HANDLERS = {"biz_rent_status": biz_rent_status, "biz_rent_repair": biz_rent_repair}
RENTDESK_BIZ_LABELS = {"biz_rent_status": "Kiraye ka hisaab dekh raha hoon", "biz_rent_repair": "Repair ki baat likh raha hoon"}
