"""Society Sahayak tools (housing society manager). `society_dekho` only reads; `society` does the work. Bills going to
members, notices / circulars, messages to members, spends and penalties are only CARDS here: her tap in the app decides them.
Hoola never takes or pays money."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

SOCIETY_TOOLS = [
    {"name": "society", "description": (
        "Housing society manager / secretary's coworker. action=settings (owner): name, reg_no, address, state (MH = Maharashtra "
        "caps: non-occupancy max 10% of service charges, interest max 12% simple, sinking >= 0.25% / repair >= 0.75% of construction "
        "cost), upi_id (the SOCIETY's own UPI ID), upi_name, noc_pct, interest_pct (general body rate), grace_days, due_days, bill_day, "
        "gstin, gst_on, committee [{name, role, phone, flat}], term_ends, auditor, visitor_days, morning_time, rules. "
        "action=head (owner): key (service|water|lift|sinking|repair|property_tax|insurance|parking|education|election|<new>), rate "
        "(HER number: per flat / per sqft / per tap / % / total; parking {car, two_wheeler}), label, basis per_flat|per_sqft|per_tap|"
        "lift|parking|fund_pct|area_share|per_member, fund, remove. action=flat (owner): unit (new, e.g. 'A-101') or flat (existing), "
        "wing, carpet_sqft, cost (architect-certified construction cost), taps, lift, owner_name, owner_phone, owner_email, joint, "
        "member_since, share_cert, shares, occupancy self|tenant|vacant, tenant_name, tenant_phone, tenant_from, tenant_to, "
        "opening_due, no_messages, notes. action=import_flats (owner): file_id (member list CSV / Excel). action=nominate (owner): flat, "
        "name, relation, share_pct, revoke. action=transfer (owner): flat, new_owner, phone, premium, on, share_cert. action=parking "
        "(owner): flat, slot, kind car|two_wheeler, resolution (GB resolution ref), remove. action=bills: period YYYY-MM, flats -> "
        "drafts + ONE card for her tap (never say they were sent). action=receipt (owner): flat, amount, mode upi|cash|cheque|neft, "
        "ref, day (only when the money really came). action=remind: flats, text, via self|business, min_days -> message card. "
        "action=message: flats (or ['all']), text, via -> message card. action=penalty: flat, what, amount, rule (bye-law / "
        "resolution) -> card. action=complaint: text (member's words as data), flat, kind complaint|request. action=complaint_update: "
        "complaint, status open|assigned|working|resolved|closed, note, contract. action=notice: kind notice|circular|agm|sgm|"
        "committee|defaulters|minutes, title, body, meeting, audience, flats -> draft. action=notice_send: notice -> card. "
        "action=meeting (owner): kind agm|sgm|committee, day, time, place, agenda [..]. action=meeting_held (owner): meeting, present "
        "[names / flats] or present_count, chair, notes. action=resolution (owner): meeting, text, proposer, seconder, for, against. "
        "action=minutes_final (owner): meeting, text. action=contract (owner): vendor, kind lift|security|housekeeping|water_tank|pest|"
        "fire|garden|cctv|generator|pump|other, phone, amount, per, start, end, visits, individual, contract. action=spend: kind "
        "repair|amc|purchase|tax|utility|audit|other, what, amount (from the vendor's quote / bill), vendor, contract, fund "
        "general|repair|sinking, resolution -> card. action=spend_done (owner): spend, amount, ref, day. action=staff (owner): name, "
        "role, agency, flats, phone, verified_on, status, staff. action=visitor_in: name, flat, purpose, phone, vehicle, kind. "
        "action=visitor_out: visit. action=audit_done (owner): fy (e.g. 2526), on, auditor. action=forget (owner): flat, who "
        "tenant|history. action=register (Excel for the auditor)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "head", "flat", "import_flats", "nominate", "transfer", "parking", "bills",
                                               "receipt", "remind", "message", "penalty", "complaint", "complaint_update", "notice",
                                               "notice_send", "meeting", "meeting_held", "resolution", "minutes_final", "contract",
                                               "spend", "spend_done", "staff", "visitor_in", "visitor_out", "audit_done", "forget",
                                               "register"]},
         "name": {"type": "string"}, "reg_no": {"type": "string"}, "address": {"type": "string"}, "state": {"type": "string"},
         "upi_id": {"type": "string"}, "upi_name": {"type": "string"}, "noc_pct": {"type": "number"}, "interest_pct": {"type": "number"},
         "grace_days": {"type": "integer"}, "due_days": {"type": "integer"}, "bill_day": {"type": "integer"}, "gstin": {"type": "string"},
         "gst_on": {"type": "boolean"}, "committee": {"type": "array", "items": {"type": "object"}}, "term_ends": {"type": "string"},
         "auditor": {"type": "string"}, "visitor_days": {"type": "integer"}, "morning_time": {"type": "string"}, "rules": {"type": "string"},
         "key": {"type": "string"}, "rate": {}, "label": {"type": "string"}, "basis": {"type": "string"}, "fund": {"type": "string"},
         "remove": {"type": "boolean"}, "unit": {"type": "string"}, "flat": {"type": "string"}, "wing": {"type": "string"},
         "carpet_sqft": {"type": "number"}, "cost": {"type": "number"}, "taps": {"type": "integer"}, "lift": {"type": "boolean"},
         "owner_name": {"type": "string"}, "owner_phone": {"type": "string"}, "owner_email": {"type": "string"},
         "joint": {"type": "array", "items": {"type": "string"}}, "member_since": {"type": "string"}, "share_cert": {"type": "string"},
         "shares": {"type": "string"}, "occupancy": {"type": "string"}, "tenant_name": {"type": "string"}, "tenant_phone": {"type": "string"},
         "tenant_from": {"type": "string"}, "tenant_to": {"type": "string"}, "opening_due": {"type": "number"},
         "no_messages": {"type": "boolean"}, "notes": {"type": "string"}, "file_id": {"type": "string"}, "relation": {"type": "string"},
         "share_pct": {"type": "number"}, "revoke": {"type": "boolean"}, "new_owner": {"type": "string"}, "phone": {"type": "string"},
         "premium": {"type": "number"}, "on": {"type": "string"}, "slot": {"type": "string"}, "kind": {"type": "string"},
         "resolution": {"type": "string"}, "period": {"type": "string"}, "flats": {"type": "array", "items": {"type": "string"}},
         "amount": {"type": "number"}, "mode": {"type": "string"}, "ref": {"type": "string"}, "day": {"type": "string"},
         "text": {"type": "string"}, "via": {"type": "string"}, "min_days": {"type": "integer"}, "what": {"type": "string"},
         "rule": {"type": "string"}, "complaint": {"type": "string"}, "status": {"type": "string"}, "note": {"type": "string"},
         "contract": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}, "meeting": {"type": "string"},
         "audience": {"type": "string"}, "notice": {"type": "string"}, "time": {"type": "string"}, "place": {"type": "string"},
         "agenda": {"type": "array", "items": {"type": "string"}}, "present": {"type": "array", "items": {"type": "string"}},
         "present_count": {"type": "integer"}, "chair": {"type": "string"}, "proposer": {"type": "string"}, "seconder": {"type": "string"},
         "for": {"type": "integer"}, "against": {"type": "integer"}, "vendor": {"type": "string"}, "per": {"type": "string"},
         "start": {"type": "string"}, "end": {"type": "string"}, "visits": {"type": "string"}, "individual": {"type": "boolean"},
         "spend": {"type": "string"}, "role": {"type": "string"}, "agency": {"type": "string"}, "verified_on": {"type": "string"},
         "staff": {"type": "string"}, "purpose": {"type": "string"}, "vehicle": {"type": "string"}, "visit": {"type": "string"},
         "fy": {"type": "string"}, "who": {"type": "string"}},
         "required": ["action"]}},
    {"name": "society_dekho", "description": (
        "Read the society (nothing changes). what=day (bills not made, urgent / old complaints, defaulters, cards waiting for her, "
        "dates coming) | flats (q) | flat (flat: member, nominations, parking, bills, receipts) | bills (period, status, flat) | dues "
        "(aging, defaulters) | complaints (status) | notices | meetings | meeting (meeting) | contracts | spends (status) | staff | "
        "visitors (inside) | parking | accounts (fy: income & expenditure, funds, receipts, defaulters, audit dates) | calendar (AGM / "
        "audit / election / contracts / police verification) | cards (her taps waiting) | settings | rules (caps, never, sources)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "flats", "flat", "bills", "dues", "complaints", "notices", "meetings", "meeting",
                                             "contracts", "spends", "staff", "visitors", "parking", "accounts", "calendar", "cards",
                                             "settings", "rules"]},
         "q": {"type": "string"}, "flat": {"type": "string"}, "period": {"type": "string"}, "status": {"type": "string"},
         "meeting": {"type": "string"}, "inside": {"type": "boolean"}, "fy": {"type": "string"}},
         "required": ["what"]}},
]
SOCIETY_LABELS = {"society": "Society ka kaam kar raha hoon", "society_dekho": "Society ka register dekh raha hoon"}

OWNER_ONLY = ("settings", "head", "flat", "import_flats", "nominate", "transfer", "parking", "receipt", "meeting", "meeting_held",
              "resolution", "minutes_final", "contract", "spend_done", "staff", "audit_done", "forget", "register")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..society import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("Society ka kaam graahak ke liye nahi.")
    if action in OWNER_ONLY and not _owner(ctx):
        raise ToolError("Yeh sirf owner / secretary kar sakti hain.")
    if action in OWNER_ONLY:
        actor = "owner" if actor == "owner" else actor
    f = _s(a.get("flat"))
    try:
        if action == "settings":
            return S.save_settings(t, actor, **{k: a[k] for k in S._SET_KEYS if k in a})
        if action == "head":
            return S.set_head(t, _s(a.get("key")), a.get("rate"), _s(a.get("label")), _s(a.get("basis")), _s(a.get("fund")),
                              bool(a.get("remove")), actor)
        if action == "flat":
            return S.save_flat(t, _s(a.get("unit")), f, actor, **{k: a[k] for k in S._FLAT_KEYS if k in a})
        if action == "import_flats":
            from ..mailbox import service as ms
            try:
                name, _m, data = ms.load_files(t, [{"type": "file", "file_id": _s(a.get("file_id"))}])[0]
            except Exception:
                raise ToolError("file_id nahi mila (member list ki sheet bhejiye).")
            return S.import_flats(t, data, name or "flats.csv", actor)
        if action == "nominate":
            return S.nominate(t, f, _s(a.get("name")), _s(a.get("relation")), a.get("share_pct"), bool(a.get("revoke")), actor)
        if action == "transfer":
            return S.transfer(t, f, _s(a.get("new_owner")), _s(a.get("phone")), a.get("premium"), _s(a.get("on")), _s(a.get("share_cert")), actor)
        if action == "parking":
            return S.parking(t, f, _s(a.get("slot")), _s(a.get("kind") or "car"), _s(a.get("resolution")), bool(a.get("remove")), actor)
        if action == "bills":
            return S.make_bills(t, _s(a.get("period")), a.get("flats"), actor, conv)
        if action == "receipt":
            return S.receive(t, f, a.get("amount"), _s(a.get("mode") or "upi"), _s(a.get("ref")), _s(a.get("day")), actor)
        if action == "remind":
            return S.remind(t, a.get("flats"), _s(a.get("text")), _s(a.get("via") or "self"), int(a.get("min_days") or 0), actor, conv)
        if action == "message":
            return S.message(t, a.get("flats") or ([f] if f else []), _s(a.get("text")), _s(a.get("via") or "self"), actor, conv)
        if action == "penalty":
            return S.penalty_request(t, f, _s(a.get("what")), a.get("amount"), _s(a.get("rule")), actor, conv)
        if action == "complaint":
            return S.complaint_new(t, _s(a.get("text")), f, _s(a.get("kind") or "complaint"), actor, conv)
        if action == "complaint_update":
            return S.complaint_update(t, _s(a.get("complaint")), _s(a.get("status")), _s(a.get("note")), _s(a.get("contract")), actor)
        if action == "notice":
            return S.notice_draft(t, _s(a.get("kind") or "notice"), _s(a.get("title")), _s(a.get("body")), _s(a.get("meeting")),
                                  _s(a.get("audience") or "all"), a.get("flats"), actor)
        if action == "notice_send":
            return S.notice_send(t, _s(a.get("notice")), actor, conv)
        if action == "meeting":
            return S.meeting_plan(t, _s(a.get("kind") or "agm"), _s(a.get("day")), _s(a.get("time")), _s(a.get("place")), a.get("agenda"), actor)
        if action == "meeting_held":
            return S.meeting_held(t, _s(a.get("meeting")), a.get("present"), a.get("present_count"), _s(a.get("chair")),
                                  _s(a.get("notes") or a.get("note")), actor)
        if action == "resolution":
            return S.resolution(t, _s(a.get("meeting")), _s(a.get("text")), _s(a.get("proposer")), _s(a.get("seconder")), a.get("for"),
                                a.get("against"), actor)
        if action == "minutes_final":
            return S.minutes_final(t, _s(a.get("meeting")), _s(a.get("text")), actor)
        if action == "contract":
            return S.contract_save(t, _s(a.get("vendor")), _s(a.get("kind") or "other"), _s(a.get("phone")), a.get("amount"),
                                   _s(a.get("per") or "year"), _s(a.get("start")), _s(a.get("end")), _s(a.get("visits")), a.get("individual"),
                                   _s(a.get("contract")), _s(a.get("status")), _s(a.get("notes")), actor)
        if action == "spend":
            return S.spend_request(t, _s(a.get("kind") or "other"), _s(a.get("what")), a.get("amount"), _s(a.get("vendor")),
                                   _s(a.get("contract")), _s(a.get("fund") or "general"), _s(a.get("resolution")), actor, conv)
        if action == "spend_done":
            return S.spend_done(t, _s(a.get("spend")), a.get("amount"), _s(a.get("ref")), _s(a.get("day")), actor)
        if action == "staff":
            return S.staff_save(t, _s(a.get("name")), _s(a.get("role") or "other"), _s(a.get("agency")), a.get("flats"), _s(a.get("phone")),
                                _s(a.get("verified_on")), _s(a.get("status")), _s(a.get("staff")), actor)
        if action == "visitor_in":
            return S.visit_in(t, _s(a.get("name")), f, _s(a.get("purpose")), _s(a.get("phone")), _s(a.get("vehicle")),
                              _s(a.get("kind") or "visitor"), actor)
        if action == "visitor_out":
            return S.visit_out(t, _s(a.get("visit")))
        if action == "audit_done":
            return S.mark_audit(t, _s(a.get("fy")), _s(a.get("on")), _s(a.get("auditor")), actor)
        if action == "forget":
            return S.forget(t, f, _s(a.get("who") or "tenant"), actor)
        if action == "register":
            return S.register_file(t, conv)
    except (S.SocietyError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..society import rules as R
    from ..society import service as S
    t = ctx.tenant_id
    if (getattr(ctx, "actor", "owner") or "").startswith("customer:"):
        raise ToolError("Society ki jaankari graahak ke liye nahi.")
    try:
        if what == "day":
            return S.day(t)
        if what == "flats":
            return {"flats": S.flats(t, _s(a.get("q")))}
        if what == "flat":
            return S.flat_view(t, _s(a.get("flat")))
        if what == "bills":
            return {"bills": S.bills(t, _s(a.get("period")), _s(a.get("status")), _s(a.get("flat")))}
        if what == "dues":
            return S.dues(t)
        if what == "complaints":
            return {"complaints": S.complaints(t, _s(a.get("status") or "open"))}
        if what == "notices":
            return {"notices": S.notices(t, _s(a.get("status")))}
        if what == "meetings":
            return {"meetings": S.meetings(t, _s(a.get("status")))}
        if what == "meeting":
            return S.meeting_view(t, _s(a.get("meeting")))
        if what == "contracts":
            return {"contracts": S.contracts(t)}
        if what == "spends":
            return {"spends": S.spends(t, _s(a.get("status")))}
        if what == "staff":
            return {"staff": S.staff_list(t)}
        if what == "visitors":
            return {"visits": S.visits(t, bool(a.get("inside")))}
        if what == "parking":
            return {"parking": S.parking_register(t)}
        if what == "accounts":
            return S.accounts(t, _s(a.get("fy")))
        if what == "calendar":
            return {"calendar": S.calendar(t)}
        if what == "cards":
            return {"cards": S.cards(t, _s(a.get("status") or "waiting"))}
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            st = S.settings(t)
            return {"never": list(R.NEVER), "law": st["law"], "caps": st["caps"], "bases": R.BASES,
                    "sources": [{"what": w, "url": u, "date": d} for w, u, d in R.SOURCES]}
    except (S.SocietyError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def society(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def society_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


SOCIETY_HANDLERS = {"society": society, "society_dekho": society_dekho}
