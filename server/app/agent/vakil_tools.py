"""Vakil Sahayak tools (lawyer's junior). `vakil_dekho` only reads; `vakil` does the work. Filing, any message / notice to a client
or the opposite party, and fee requests only become CARDS here: her tap in the app decides. Hoola is not a lawyer: drafts and
"andaaza" only; never invents sections, citations, dates or fees; eCourts only through what she pastes from the official app / site."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

VAKIL_TOOLS = [
    {"name": "vakil", "description": (
        "Lawyer's junior: case diary, hearing dates, cause lists, limitation, drafts, client updates, fee ledger. NOT legal advice: "
        "every result says 'andaaza / draft, vakil se pakka'. Never invent dates, section numbers, case law or fees. "
        "action=settings*: advocate, enrolment_no, office, address, phone, email, upi_id, state, place, closed_dates (court holidays), "
        "closed_weekdays (0=Mon..6=Sun), remind_days, morning_time. action=client: name (new) or client (C-001 / name to update), phone, "
        "email, address, kind individual|company|firm, id_ref ({id:...} locker reference ONLY, never the number), no_messages. "
        "action=matter: title (new, 'X vs Y') or matter (M-0001 / CNR / case no / name to update), client, client_phone, kind "
        "civil_suit|criminal|bail|cheque_138|consumer|family|writ|appeal|arbitration|property|recovery|labour|motor_accident|other, "
        "side, opposite, opposite_advocate, opposite_contact, court, court_no, case ('RCS 123/2024'), cnr (16 chars), filing_no, acts, "
        "stage, next_date, next_purpose, status*. action=hearing: matter, on, purpose, result, next_date, next_purpose, stage (what she "
        "says happened; never guess the next date). action=event: matter, on, what (list of dates & events). action=status: text (case "
        "status she copied from the official eCourts app / site), matter. action=cause_list: text (cause list she pasted), on. "
        "action=limitation: kind (money_loan, specific_performance, breach_contract, possession_title, suit_residuary, appeal_hc_civil, "
        "appeal_other_civil, appeal_hc_same, crim_appeal_hc, crim_appeal_other, acquittal_appeal, leave_defend, set_aside_exparte, review, "
        "revision, execution, application_residuary, or custom with n + unit d|m|y from her advocate), start, cc_applied, cc_ready, "
        "matter (saves it). action=deadline_done: deadline_id, status. action=doc: matter, key, state have|missing|na, file_id, label. "
        "action=draft: matter, kind adjournment|vakalatnama|dates_events|synopsis|notice_reply|note, words, reason, to. "
        "action=message: matter, to client|opposite|other, text, purpose, phone, email -> a card SHE taps (never say sent). "
        "action=filing: matter, what, file_ids, use_operator -> a card SHE taps (never say filed). action=fee_request: matter, amount "
        "(her number), for -> a card SHE taps. action=done: card_id, ref_no (after she sent / filed). action=fee*: matter, kind "
        "agreed|received|expense, amount, note. action=register (Excel). action=forget* (DPDP, client after all matters closed). "
        "* = owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["settings", "client", "matter", "hearing", "event", "status", "cause_list", "limitation",
                                               "deadline_done", "doc", "draft", "message", "filing", "fee_request", "done", "fee",
                                               "register", "forget"]},
         "matter": {"type": "string"}, "title": {"type": "string"}, "client": {"type": "string"}, "client_phone": {"type": "string"},
         "name": {"type": "string"}, "phone": {"type": "string"}, "email": {"type": "string"}, "address": {"type": "string"},
         "id_ref": {"type": "string"}, "no_messages": {"type": "boolean"}, "kind": {"type": "string"}, "side": {"type": "string"},
         "opposite": {"type": "string"}, "opposite_advocate": {"type": "string"}, "opposite_contact": {"type": "string"},
         "court": {"type": "string"}, "court_no": {"type": "string"}, "case": {"type": "string"}, "cnr": {"type": "string"},
         "filing_no": {"type": "string"}, "acts": {"type": "string"}, "stage": {"type": "string"}, "next_date": {"type": "string"},
         "next_purpose": {"type": "string"}, "status": {"type": "string"}, "notes": {"type": "string"}, "on": {"type": "string"},
         "purpose": {"type": "string"}, "result": {"type": "string"}, "what": {"type": "string"}, "text": {"type": "string"},
         "start": {"type": "string"}, "n": {"type": "integer"}, "unit": {"type": "string"}, "cc_applied": {"type": "string"},
         "cc_ready": {"type": "string"}, "label": {"type": "string"}, "deadline_id": {"type": "string"}, "key": {"type": "string"},
         "state": {"type": "string"}, "file_id": {"type": "string"}, "words": {"type": "string"}, "reason": {"type": "string"},
         "to": {"type": "string"}, "file_ids": {"type": "array", "items": {"type": "string"}}, "use_operator": {"type": "boolean"},
         "amount": {"type": "number"}, "for": {"type": "string"}, "card_id": {"type": "string"}, "ref_no": {"type": "string"},
         "note": {"type": "string"}, "advocate": {"type": "string"}, "enrolment_no": {"type": "string"}, "office": {"type": "string"},
         "upi_id": {"type": "string"}, "place": {"type": "string"}, "closed_dates": {"type": "array", "items": {"type": "string"}},
         "closed_weekdays": {"type": "array", "items": {"type": "integer"}}, "remind_days": {"type": "string"},
         "morning_time": {"type": "string"}, "rules": {"type": "string"}},
         "required": ["action"]}},
    {"name": "vakil_dekho", "description": (
        "Read the court diary (nothing changes). what=day (today's / tomorrow's dates, limitation near, dates not updated, cards "
        "waiting) | matters (status, q) | matter (matter: full diary, hearings, events, documents, deadlines, drafts, cards, fees) | "
        "clients | deadlines | cards | fees (matter) | settings | rules (limitation starter table + official eCourts routes)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "matters", "matter", "clients", "deadlines", "cards", "fees", "settings", "rules"]},
         "matter": {"type": "string"}, "status": {"type": "string"}, "q": {"type": "string"}},
         "required": ["what"]}},
]
VAKIL_LABELS = {"vakil": "Court diary ka kaam kar raha hoon", "vakil_dekho": "Court diary dekh raha hoon"}

_OWNER_ONLY = ("settings", "fee", "forget")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


_MATTER_KEYS = ("client", "client_phone", "kind", "side", "opposite", "opposite_advocate", "opposite_contact", "court", "court_no", "case",
                "cnr", "filing_no", "acts", "stage", "next_date", "next_purpose", "status", "notes")
_CLIENT_KEYS = ("phone", "email", "address", "kind", "id_ref", "no_messages", "notes")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..vakil import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    if _actor(ctx).startswith("customer:"):
        raise ToolError("Yeh vakil office ka andar ka kaam hai (client ki baat privileged hai).")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner.")
    mt = _s(a.get("matter"))
    try:
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in S._SET_KEYS if k in a})
        if action == "client":
            return S.save_client(t, _s(a.get("name")), _s(a.get("client")), **{k: a[k] for k in _CLIENT_KEYS if k in a})
        if action == "matter":
            if a.get("status") in ("closed", "disposed") and not _owner(ctx):
                raise ToolError("Matter band karna sirf owner.")
            return S.save_matter(t, _s(a.get("title")), mt, **{k: a[k] for k in _MATTER_KEYS if k in a})
        if action == "hearing":
            return S.hearing(t, mt, _s(a.get("on")), _s(a.get("purpose")), _s(a.get("result")), _s(a.get("next_date")),
                             _s(a.get("next_purpose")), _s(a.get("stage")), "her" if _owner(ctx) else _actor(ctx)[:40])
        if action == "event":
            return S.event(t, mt, _s(a.get("on")), _s(a.get("what")))
        if action == "status":
            return S.status_paste(t, _s(a.get("text")), mt)
        if action == "cause_list":
            return S.cause_list(t, _s(a.get("text")), _s(a.get("on")))
        if action == "limitation":
            return S.limitation(t, _s(a.get("kind")), _s(a.get("start")), mt, a.get("n"), _s(a.get("unit")), _s(a.get("cc_applied")),
                                _s(a.get("cc_ready")), _s(a.get("label")), bool(mt))
        if action == "deadline_done":
            return S.deadline_done(t, _s(a.get("deadline_id")), _s(a.get("status") or "done"))
        if action == "doc":
            return S.doc_set(t, mt, _s(a.get("key")), _s(a.get("state") or "have"), _s(a.get("file_id")), _s(a.get("note")),
                             _s(a.get("label")))
        if action == "draft":
            return S.draft(t, mt, _s(a.get("kind")), _s(a.get("words")), _s(a.get("reason")), _s(a.get("to")), conv)
        if action == "message":
            return S.message_request(t, mt, _s(a.get("to") or "client"), _s(a.get("text")), _s(a.get("purpose") or "update"),
                                     _s(a.get("phone")), _s(a.get("email")), conv)
        if action == "filing":
            return S.filing_request(t, mt, _s(a.get("what")), a.get("file_ids") or [], bool(a.get("use_operator")), _s(a.get("note")), conv)
        if action == "fee_request":
            return S.fee_request(t, mt, a.get("amount"), _s(a.get("for")), conv)
        if action == "done":
            return S.card_done(t, _s(a.get("card_id")), _s(a.get("ref_no")), _s(a.get("on")))
        if action == "fee":
            return S.fee_add(t, mt, _s(a.get("kind")), a.get("amount"), _s(a.get("note")), _s(a.get("on")), _s(a.get("ref_no")))
        if action == "register":
            return S.register_file(t, conv)
        if action == "forget":
            return S.forget(t, _s(a.get("client")))
    except (S.VakilError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..vakil import rules as R
    from ..vakil import service as S
    t, mt = ctx.tenant_id, _s(a.get("matter"))
    if _actor(ctx).startswith("customer:"):
        raise ToolError("Yeh vakil office ka andar ka kaam hai (client ki baat privileged hai).")
    try:
        if what == "day":
            return S.day(t)
        if what == "matters":
            return {"matters": S.matters(t, _s(a.get("status")), _s(a.get("q")))}
        if what == "matter":
            return S.matter_view(t, mt)
        if what == "clients":
            return {"clients": S.clients(t, _s(a.get("q")))}
        if what == "deadlines":
            return {"deadlines": S.deadlines(t, _s(a.get("status") or "open"))}
        if what == "cards":
            return {"cards": S.cards(t, _s(a.get("status") or "waiting"))}
        if what == "fees":
            return S.ledger(t, mt)
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"limits": {k: f"{v['label']}: {v['n']} {v['unit']} ({v['src']})" for k, v in R.LIMITS.items()},
                    "ask_only": R.ASK_ONLY, "official": R.OFFICIAL, "sources": R.SOURCES, "never": R.NEVER, "check": R.CHECK}
    except (S.VakilError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def vakil(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def vakil_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


VAKIL_HANDLERS = {"vakil": vakil, "vakil_dekho": vakil_dekho}
