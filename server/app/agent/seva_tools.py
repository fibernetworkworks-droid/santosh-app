"""Seva Sahayak tools (customer support). `seva_dekho` only reads; `seva` does the work for her / her team. Refunds and
exceptions are only ASKED here (a card); her tap in the app decides (`POST /api/seva/exceptions/{id}/decide`).

The `biz_seva_*` tools are for WhatsApp customers (actor customer:<contact>): always about that one customer, answers only
from her knowledge base, their own tickets only. They are never offered to the owner's model (coordinator adds them to
employee.inbox BIZ_TOOLS and roles CUSTOMER_TOOLS)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

SEVA_TOOLS = [
    {"name": "seva", "description": (
        "Customer support desk of her business (Seva Sahayak). Knowledge base = ONLY source of answers for customers. "
        "action=kb_add: question, answer, kind faq|policy, aliases [other ways customers ask] (her own words go live at once). "
        "action=kb_import: file_id (her PDF / Word / Excel / text) or url (her own website page) or text -> DRAFT entries she must "
        "approve. action=kb_approve: ids (owner only). action=kb_edit: entry_id + question / answer / aliases. action=kb_remove: "
        "entry_id (owner only). action=ask: question (test what a customer would be told). action=macro_add: name, text (canned "
        "reply; placeholders only {name} {ticket} {status} {business}; translated to Hinglish / Hindi / Marathi / English, used only "
        "after approval). action=macro_approve: macro_id (owner only). action=ticket: text, channel phone|walkin|email|whatsapp|other, "
        "name, phone, category, priority urgent|high|normal|low (guessed if empty; a duplicate of an open ticket of the same customer "
        "is joined to it). action=update: ticket (number), status open|pending (waiting on customer, SLA paused)|on_hold|resolved|closed, "
        "priority, public (line the customer sees), note (internal, never shown), assignee. action=reply: ticket + text or macro "
        "(sends to the customer: business WhatsApp / Hoola Network, else a draft she sends). action=note: ticket, text. "
        "action=merge: ticket, into (same customer only). action=exception: kind refund|waiver|goodwill|replacement|extension|other, "
        "amount, reason, ticket -> a card ONLY she decides by tap (checked against her policy; you never promise it). "
        "action=sent: exception_id, ref (she paid from her own app; Hoola tells the customer). action=csat: ticket, score 1-5. "
        "action=settings (owner only): kind shop|isp|ecommerce|clinic (SLA preset), sla {priority: [first_response_h, resolve_h]}, "
        "ecommerce, officer, officer_contact (grievance officer), refund_days, refund_max, replace_days, goodwill_max, cancel_hours, "
        "refund_mode, lang, csat_on, auto_ack, morning_time."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["kb_add", "kb_import", "kb_approve", "kb_edit", "kb_remove", "ask", "macro_add",
                                               "macro_approve", "ticket", "update", "reply", "note", "merge", "exception", "sent",
                                               "csat", "settings"]},
         "question": {"type": "string"}, "answer": {"type": "string"}, "kind": {"type": "string"},
         "aliases": {"type": "array", "items": {"type": "string"}}, "file_id": {"type": "string"}, "url": {"type": "string"},
         "text": {"type": "string"}, "ids": {"type": "array", "items": {"type": "string"}}, "entry_id": {"type": "string"},
         "name": {"type": "string"}, "macro_id": {"type": "string"}, "macro": {"type": "string"}, "channel": {"type": "string"},
         "phone": {"type": "string"}, "category": {"type": "string"}, "priority": {"type": "string"}, "ticket": {"type": "string"},
         "status": {"type": "string"}, "public": {"type": "string"}, "note": {"type": "string"}, "assignee": {"type": "string"},
         "into": {"type": "string"}, "amount": {"type": "number"}, "reason": {"type": "string"}, "days_since": {"type": "number"},
         "exception_id": {"type": "string"}, "ref": {"type": "string"}, "score": {"type": "integer"}, "comment": {"type": "string"},
         "sla": {"type": "object"}, "ecommerce": {"type": "boolean"}, "officer": {"type": "string"}, "officer_contact": {"type": "string"},
         "refund_days": {"type": "number"}, "refund_max": {"type": "number"}, "replace_days": {"type": "number"},
         "goodwill_max": {"type": "number"}, "cancel_hours": {"type": "number"}, "refund_mode": {"type": "string"},
         "lang": {"type": "string"}, "csat_on": {"type": "boolean"}, "auto_ack": {"type": "boolean"}, "morning_time": {"type": "string"}},
         "required": ["action"]}},
    {"name": "seva_dekho", "description": (
        "Read the support desk (nothing changes). what=day (open / late / waiting exceptions / gaps) | tickets (status: open | "
        "resolved | ..., q) | ticket (ticket: notes, SLA, exceptions) | kb (status live|draft, q) | gaps (questions the knowledge "
        "base could not answer) | macros | exceptions (status) | report (days: first response / resolution time, SLA %, deflection, "
        "CSAT, top questions) | duplicates | settings | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "tickets", "ticket", "kb", "gaps", "macros", "exceptions", "report", "duplicates",
                                             "settings", "rules"]},
         "status": {"type": "string"}, "q": {"type": "string"}, "ticket": {"type": "string"}, "days": {"type": "integer"}},
         "required": ["what"]}},
]

BIZ_SEVA_TOOLS = [
    {"name": "biz_seva_answer", "description": (
        "ALWAYS call this FIRST for any question of this customer (timings, prices, plans, policy, how-to). Answers ONLY from the "
        "business's own knowledge base. status=answered -> send `reply` (you may add one friendly word, nothing else, no new facts). "
        "clarify -> ask which of `candidates` they mean. unknown -> never guess: biz_handover or (if it is a problem) "
        "biz_seva_ticket. `exception` present -> refund / discount asks go to biz_seva_request, never promise."),
     "input_schema": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}},
    {"name": "biz_seva_ticket", "description": (
        "Register a real problem / complaint of THIS customer as a support ticket (category and priority are guessed). A repeat of "
        "their open complaint is joined to it. Tell them the ticket number and `status_line`."),
     "input_schema": {"type": "object", "properties": {"text": {"type": "string"}, "category": {"type": "string"}},
                      "required": ["text"]}},
    {"name": "biz_seva_status", "description": "Status of THIS customer's own tickets (optionally one number). Read the `line` to them.",
     "input_schema": {"type": "object", "properties": {"number": {"type": "string"}}}},
    {"name": "biz_seva_request", "description": (
        "This customer asks for a refund / waiver / discount / replacement / anything outside the rules: sends a request to the "
        "owner. Only the owner decides; tell the customer `customer_say`, never promise."),
     "input_schema": {"type": "object", "properties": {
         "kind": {"type": "string", "enum": ["refund", "waiver", "goodwill", "replacement", "extension", "other"]},
         "amount": {"type": "number"}, "reason": {"type": "string"}, "ticket": {"type": "string"}}, "required": ["kind", "reason"]}},
    {"name": "biz_seva_rate", "description": "The customer answered the 1-5 rating question after a ticket was closed.",
     "input_schema": {"type": "object", "properties": {"score": {"type": "integer"}, "comment": {"type": "string"},
                                                        "ticket": {"type": "string"}}, "required": ["score"]}},
]

SEVA_LABELS = {"seva": "Graahak seva ka kaam kar raha hoon", "seva_dekho": "Shikayatein aur Gyaan dekh raha hoon",
               "biz_seva_answer": "Gyaan mein jawab dhoondh raha hoon", "biz_seva_ticket": "Shikayat darj kar raha hoon",
               "biz_seva_status": "Shikayat ka haal dekh raha hoon", "biz_seva_request": "Owner ko arzi bhej raha hoon",
               "biz_seva_rate": "Rating likh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _by(ctx: Ctx) -> str:
    return (getattr(ctx, "actor", "owner") or "owner")[:60]


_SETTINGS_KEYS = ("kind", "sla", "ecommerce", "officer", "officer_contact", "refund_days", "refund_max", "replace_days", "goodwill_max",
                  "cancel_hours", "refund_mode", "lang", "csat_on", "auto_ack", "morning_time")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..seva import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    tk = _s(a.get("ticket"))
    try:
        if action == "kb_add":
            return S.kb_add(t, _s(a.get("question")), _s(a.get("answer")), _s(a.get("kind")) or "faq", a.get("aliases") or [])
        if action == "kb_import":
            return S.kb_import(t, file_id=_s(a.get("file_id")), url=_s(a.get("url")), text=_s(a.get("text")))
        if action == "kb_approve":
            if not _owner(ctx):
                raise ToolError("Gyaan ko manzoori sirf owner deti hain.")
            return S.kb_approve(t, a.get("ids") or _s(a.get("entry_id")))
        if action == "kb_edit":
            return S.kb_edit(t, _s(a.get("entry_id")), **{k: a[k] for k in ("question", "answer", "aliases", "kind") if k in a})
        if action == "kb_remove":
            if not _owner(ctx):
                raise ToolError("Sirf owner.")
            return S.kb_remove(t, _s(a.get("entry_id")))
        if action == "ask":
            return S.answer(t, _s(a.get("question") or a.get("text")), "test")
        if action == "macro_add":
            return S.macro_add(t, _s(a.get("name")), _s(a.get("text")), _s(a.get("lang")))
        if action == "macro_approve":
            if not _owner(ctx):
                raise ToolError("Taiyaar jawab ko manzoori sirf owner deti hain.")
            return S.macro_approve(t, _s(a.get("macro_id")))
        if action == "ticket":
            return S.new_ticket(t, _s(a.get("text")), _s(a.get("channel")) or "phone", "", _s(a.get("name")), _s(a.get("phone")),
                                _s(a.get("category")), _s(a.get("priority")), _by(ctx), conv)
        if action == "update":
            return S.update(t, tk, _s(a.get("status")), _s(a.get("priority")), _s(a.get("public")), _s(a.get("note")),
                            a.get("assignee"), _s(a.get("category")), _by(ctx))
        if action == "reply":
            return S.reply(t, tk, _s(a.get("text")), _s(a.get("macro")), _by(ctx))
        if action == "note":
            return S.note(t, tk, _s(a.get("text") or a.get("note")), _by(ctx))
        if action == "merge":
            return S.merge(t, tk, _s(a.get("into")), _by(ctx))
        if action == "exception":
            out = S.exception_request(t, _s(a.get("kind")) or "refund", _s(a.get("reason")), a.get("amount") or 0, tk, a.get("days_since"),
                                      _by(ctx), conv)
            return out | {"needs_tap": True, "note": "Card bhej diya. Faisla sirf owner ki tap se hota hai; khud haan mat kaho."}
        if action == "sent":
            if not _owner(ctx):
                raise ToolError("Paise bhejne ki pushti sirf owner.")
            return S.mark_sent(t, _s(a.get("exception_id")), _s(a.get("ref")))
        if action == "csat":
            return S.csat(t, tk, a.get("score") or 0, _s(a.get("comment")))
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Seva ke niyam sirf owner badalti hain.")
            return S.save_settings(t, **{k: a[k] for k in _SETTINGS_KEYS if k in a})
    except S.SevaError as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..seva import rules as R
    from ..seva import service as S
    t = ctx.tenant_id
    try:
        if what == "day":
            return S.day(t)
        if what == "tickets":
            return {"tickets": S.tickets(t, _s(a.get("status")) or "open", _s(a.get("q")))[:60]}
        if what == "ticket":
            return S.ticket(t, _s(a.get("ticket")))
        if what == "kb":
            return {"entries": S.kb_list(t, _s(a.get("status")), _s(a.get("q")))[:80]}
        if what == "gaps":
            return {"gaps": S.gaps(t, int(a.get("days") or 30), 15)}
        if what == "macros":
            return {"macros": S.macros(t)}
        if what == "exceptions":
            return {"exceptions": S.exceptions(t, _s(a.get("status")))[:60]}
        if what == "report":
            return S.report(t, int(a.get("days") or 30))
        if what == "duplicates":
            return {"duplicates": S.duplicates(t)}
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"never": list(R.NEVER), "sla_default": R.SLA_DEFAULT, "presets": R.SLA_PRESETS,
                    "law": {"ecommerce": "Grievance officer: 48 ghante mein pavti, 1 mahine mein hal (E-Commerce Rules 2020)",
                            "dpdp": "Data se judi shikayat 90 din (DPDP Rules 2025; mukhya niyam 13 May 2027 se)",
                            "upi": "Fail UPI / IMPS: T+1 mein wapas, der par ₹100 roz bank deta hai (RBI 20 Sep 2019)",
                            "consumer": "National Consumer Helpline 1915, e-Jagriti"}}
    except S.SevaError as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def seva(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def seva_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


# ---------------------------------------------------------------- the customer's tools (WhatsApp inbox, actor customer:<id>)
def _customer(ctx: Ctx):
    from ..employee.inbox import _contact
    c = _contact(ctx)                 # raises ToolError unless this is a WhatsApp customer of this business
    return c, f"wa:{c.wa_id}", (c.name or "") + f" (WhatsApp …{c.wa_id[-4:]})"


async def biz_seva_answer(ctx: Ctx, question: str = "", **_):
    from ..seva import service as S
    _c, key, _label = _customer(ctx)
    try:
        out = await asyncio.to_thread(S.answer, ctx.tenant_id, str(question or ""), "whatsapp", key)
    except S.SevaError as ex:
        raise ToolError(str(ex))
    out.pop("entry_id", None)
    return out


async def biz_seva_ticket(ctx: Ctx, text: str = "", category: str = "", **_):
    from ..seva import service as S
    c, key, label = _customer(ctx)
    try:
        out = await asyncio.to_thread(S.new_ticket, ctx.tenant_id, str(text or ""), "whatsapp", key, label, "", str(category or ""), "",
                                      f"customer:{c.id}")
    except S.SevaError as ex:
        raise ToolError(str(ex))
    v = out["ticket"]
    return {"ticket": out["number"], "status_line": out["status_line"], "duplicate": bool(out.get("duplicate")),
            "priority": v["priority"], "note": "Graahak ko ticket number aur status line batao. Samay ka waada mat karo."}


async def biz_seva_status(ctx: Ctx, number: str = "", **_):
    from ..seva import service as S
    _c, key, _label = _customer(ctx)
    try:
        return await asyncio.to_thread(S.customer_status, ctx.tenant_id, key, str(number or ""))
    except S.SevaError as ex:
        raise ToolError(str(ex))


async def biz_seva_request(ctx: Ctx, kind: str = "other", reason: str = "", amount: float = 0, ticket: str = "", **_):
    from ..seva import service as S
    c, key, label = _customer(ctx)
    try:
        out = await asyncio.to_thread(S.exception_request, ctx.tenant_id, str(kind or "other"), str(reason or ""), amount or 0,
                                      str(ticket or ""), None, f"customer:{c.id}", "", key, label)
    except S.SevaError as ex:
        raise ToolError(str(ex))
    return {"request": out["exception"]["number"], "customer_say": out.get("customer_say", ""), "duplicate": bool(out.get("duplicate"))}


async def biz_seva_rate(ctx: Ctx, score: int = 0, comment: str = "", ticket: str = "", **_):
    from ..seva import service as S
    _c, key, _label = _customer(ctx)
    try:
        return await asyncio.to_thread(S.csat, ctx.tenant_id, str(ticket or ""), score, str(comment or ""), key)
    except S.SevaError as ex:
        raise ToolError(str(ex))


SEVA_HANDLERS = {"seva": seva, "seva_dekho": seva_dekho, "biz_seva_answer": biz_seva_answer, "biz_seva_ticket": biz_seva_ticket,
                 "biz_seva_status": biz_seva_status, "biz_seva_request": biz_seva_request, "biz_seva_rate": biz_seva_rate}
BIZ_SEVA_HANDLERS = {k: v for k, v in SEVA_HANDLERS.items() if k.startswith("biz_")}
