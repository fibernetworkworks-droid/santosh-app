"""v0.999.80 CUSTOMER SUPPORT DESK - the Customer Support employee's own section with its own chat (the Telecaller desk's twin).

Owner (21 Nov 2026): "NOW LETS MOVE TO NEXT EMPLOYEE" -> the 7-screen design claude.ai/artifact/EhbGoFv5QCxmbvkBQw8y5F ->
"GO BUILD". The engine is Seva Sahayak (`seva/`: knowledge answers with their source, tickets with reply deadlines, refunds
and exceptions only on her tap, saved replies, reports); this module adds the desk and its chat.

- The Support chat = a Conversation with kind 'support', kept out of every Hoola chat list (callconv.not_call, convs).
- A turn in it (or a voice call started from it) gets the desk's state as a block and the `seva` tools in view (`FAMILIES`).
- What the chat may do: add or change knowledge answers, read a file / page into DRAFT answers, write saved replies (drafts),
  open / update / reply to tickets, ask for an exception (a card). Approving drafts, deciding a refund or exception and the
  service rules stay HER taps on the desk.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.supportchat")

KIND = "support"
HIRE_KEY = "support"
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
FAMILIES = ["seva"]


def is_support(conv: str) -> bool:
    if not conv:
        return False
    if conv in _OF:
        return _OF[conv]
    hit = False
    try:
        with session() as s:
            c = s.get(Conversation, conv)
            if c is not None:
                if (c.kind or "") == KIND:
                    hit = True
                elif (c.kind or "") == "call" and c.origin_conv:
                    o = s.get(Conversation, c.origin_conv)
                    hit = bool(o is not None and (o.kind or "") == KIND)
    except Exception:   # noqa: BLE001
        log.exception("support chat kind read failed")
        return False
    _OF[conv] = hit
    return hit


def _q(tenant: str):
    return select(Conversation).where(Conversation.tenant_id == tenant, Conversation.kind == KIND,
                                      or_(Conversation.deleted.is_(None), Conversation.deleted.is_(False)))


def channels(tenant: str) -> list[dict[str, Any]]:
    """Where customers reach her, each with its real state (never a made-up 'connected')."""
    inbox_on = False
    try:
        from .employee import service as emp
        p = emp.profile(tenant) or {}
        inbox_on = bool(p.get("inbox_on") and p.get("enabled"))
    except Exception:   # noqa: BLE001
        pass
    tele = False
    try:
        from .employee import hire
        tele = hire.status(tenant, "telecaller") in ("hired", "paused")
    except Exception:   # noqa: BLE001
        pass
    return [
        {"key": "whatsapp", "name": "WhatsApp Business", "state": "on" if inbox_on else "off",
         "line": "Your own business number through the official WhatsApp API. Hoola answers from your knowledge and opens tickets."
         if inbox_on else "Turn on the business inbox in Hoola Employee (Profile > Hoola Employee in the app) to answer customers here."},
        {"key": "hoola", "name": "Hoola Network", "state": "on",
         "line": "Other people's avatars can raise a complaint with your avatar; it becomes a ticket here."},
        {"key": "phone", "name": "Phone calls", "state": "on" if tele else "manual",
         "line": "Your Telecaller line answers calls. Add a caller's problem as a ticket here or in the chat."
         if tele else "Add a caller's problem as a ticket here or in the chat. Hire the Telecaller to have Hoola answer your number."},
        {"key": "email", "name": "Email and walk-in", "state": "manual",
         "line": "Add the problem as a ticket (New ticket) or tell the chat; replies are drafts you send."},
        {"key": "web", "name": "Chat on your website", "state": "soon",
         "line": "Not joined to this desk yet. Website visitors' messages still reach you in the Web Studio."},
    ]


def summary(tenant: str) -> dict[str, Any]:
    """What the desk and the chat know: hired, today's note, tickets, exceptions, knowledge, numbers."""
    from .employee import hire
    from .seva import service as S
    st = hire.status(tenant, HIRE_KEY)
    if st not in ("hired", "paused"):
        return {"hired": False}
    day = S.day(tenant)
    tickets = S.tickets(tenant, "open")
    exc = S.exceptions(tenant, "pending")
    to_send = [e for e in S.exceptions(tenant, "approved") if e["kind"] in ("refund", "goodwill", "replacement") and e["amount"]]
    drafts = S.kb_list(tenant, "draft")
    live = S.kb_list(tenant, "live")
    rep = S.report(tenant, 7)
    gaps = S.gaps(tenant, 30, 10)
    return {"hired": True, "status": st, "say": day["say"], "parts": day["parts"], "open": day["open"], "late": day["late"],
            "urgent": sum(1 for t in tickets if t["priority"] == "urgent"),
            "waiting": len(exc), "to_send": len(to_send), "drafts": len(drafts), "answers": len(live), "gaps": len(gaps),
            "week": {k: rep.get(k) for k in ("tickets", "questions", "answered_by_kb", "deflection_pct", "first_response_median_h",
                                             "csat_avg", "csat_count")},
            "settings": S.settings(tenant), "channels": channels(tenant)}


def greeting(tenant: str) -> str:
    try:
        d = summary(tenant)
    except Exception:   # noqa: BLE001
        d = {}
    if not d.get("hired"):
        return "I am your Customer Support. Hire me from AI Employees to start."
    bits = []
    if d.get("waiting"):
        bits.append(f"{d['waiting']} refund or exception request{'s wait' if d['waiting'] > 1 else ' waits'} for your yes")
    if d.get("late"):
        bits.append(f"{len(d['late'])} ticket{'s are' if len(d['late']) > 1 else ' is'} past the reply time")
    if d.get("gaps"):
        bits.append(f"{d['gaps']} customer question{'s have' if d['gaps'] > 1 else ' has'} no answer in your knowledge yet")
    if not d.get("answers"):
        bits.append("your knowledge is empty, so I cannot answer customers yet")
    return ("Hello. I answer your customers only from your own knowledge, open a ticket for every real problem and tell them "
            "where it stands. Refunds and anything outside your policy always wait for you. "
            + ("Now: " + "; ".join(bits) + ". " if bits else "")
            + "Tell me your timings, prices and refund rules, or attach your price list or policy PDF, and I will turn it into answers "
              "for you to approve.")


def current(tenant: str) -> dict[str, Any]:
    with session() as s:
        c = s.scalars(_q(tenant).order_by(func.coalesce(Conversation.last_at, Conversation.created_at).desc()).limit(1)).first()
        if c is not None:
            _OF[c.id] = True
            return {"id": c.id, "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    with session() as s:
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title="Support chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    hi = greeting(tenant)
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=hi, display=hi, in_history=False, delivered_to_agent=True))
    return {"id": cid, "new": True}


def owns(tenant: str, conv: str) -> bool:
    with session() as s:
        c = s.get(Conversation, conv)
        return bool(c is not None and c.tenant_id == tenant and (c.kind or "") == KIND and not c.deleted)


RULES = ("You are her Customer Support employee, talking in the Support desk's own chat (or a voice call started from it). "
         "Plain English, short. Never invent a price, a date, a count or a promise. "
         "KNOWLEDGE: customers are answered ONLY from her knowledge (seva action=kb_add with question + answer + kind faq|policy; "
         "her own words go live at once). A file / her website page / pasted text becomes DRAFT answers with seva action=kb_import "
         "(file_id or url or text); drafts wait for HER approval on the Knowledge page - say so, never approve them yourself. "
         "Test an answer with seva action=ask. Questions customers asked that the knowledge could not answer: seva_dekho what=gaps. "
         "SAVED REPLIES: seva action=macro_add (name + text, placeholders {name} {ticket} {status} {business}); used only after she "
         "approves them. TICKETS: a real problem = seva action=ticket (text, channel, name, phone; priority and deadline are set by "
         "code, a repeat of the same customer's open ticket joins it). Change one with action=update (status, priority, public line "
         "the customer sees, internal note, assignee); action=reply sends to the customer on WhatsApp / Hoola Network, otherwise it "
         "is a draft she sends. Internal notes never reach a customer. REFUNDS AND EXCEPTIONS: anything outside her written policy "
         "(refund, waiver, discount, free visit, replacement, extension) = seva action=exception -> a card; ONLY her tap on the "
         "Approvals page decides; never say it is approved, never promise it to a customer; Hoola never moves money (she pays, then "
         "action=sent tells the customer). Service rules (reply times, refund days, grievance officer) are HER settings - change them "
         "with seva action=settings only when she asks in so many words. Never ask for or repeat an OTP, PIN, password or card "
         "number. Read the desk with seva_dekho: what=day / tickets / ticket / kb / gaps / macros / exceptions / report. ")


def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        d = summary(tenant)
        if not d.get("hired"):
            txt = f"\n\n<support_desk>{RULES}Customer Support is not hired yet: tell her to hire it from AI Employees.</support_desk>"
        else:
            w = d.get("week") or {}
            ch = "; ".join(f"{c['name']} {c['state']}" for c in d.get("channels") or [])
            txt = (f"\n\n<support_desk>{RULES}\nToday: {d.get('say')} Open tickets: {d.get('open', 0)} ({d.get('urgent', 0)} urgent, "
                   f"{len(d.get('late') or [])} late). Waiting for her yes: {d.get('waiting', 0)} exceptions; approved refunds still to "
                   f"pay: {d.get('to_send', 0)}. Knowledge: {d.get('answers', 0)} live answers, {d.get('drafts', 0)} drafts to approve, "
                   f"{d.get('gaps', 0)} unanswered questions. Last 7 days: {w.get('tickets') or 0} tickets, {w.get('questions') or 0} "
                   f"questions, {w.get('answered_by_kb') or 0} answered from knowledge. Channels: {ch}.</support_desk>")
    except Exception:   # noqa: BLE001
        log.exception("support block failed")
        txt = f"\n\n<support_desk>{RULES}The desk could not be read just now; use seva_dekho what=day.</support_desk>"
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


router = APIRouter()


def mount(app, current_tenant, require_key, static_dir, version: str) -> None:
    @router.get("/api/support/desk", dependencies=[Depends(require_key)])
    def support_desk(tenant: str = Depends(current_tenant)):
        return summary(tenant)

    @router.get("/api/support/chat", dependencies=[Depends(require_key)])
    def support_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/support/chat/new", dependencies=[Depends(require_key)])
    def support_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/support/chat/{conv}/ok", dependencies=[Depends(require_key)])
    def support_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Support chat")
        return {"ok": True}

    app.include_router(router)
