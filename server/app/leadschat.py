"""v0.999.52 LEAD DESK - the Lead Generation employee's own section with its own chat (the Accounts desk's twin).

Owner (20 Nov 2026): "PERFECT GO WITH LEAD GENEARTION --- FIRST CHECK HOW CURRENTLY IT IS" -> the design
(claude.ai/artifact/FTaYVw37EiqT7gp1NAGGkg) -> "GO BUILD".

- The Lead Generation chat = a Conversation with kind 'leads', kept out of every Hoola chat list (callconv.not_call).
- A turn in it (or a voice call started from it) gets the desk's state as a block and the lead tools in view
  (`FAMILIES`: the leads engine + the lead desk). A CSV / Excel she attaches goes into the store as her list.
- What it may change: a lead's stage, follow-up and notes, saved searches, and message DRAFTS. Starting a paid search,
  handing a list to the campaign desk or the Telecaller, opting out and forgetting stay her taps; nothing is ever sent.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.leadschat")

KIND = "leads"
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
FAMILIES = ["leadsdesk", "leads"]


def is_leads(conv: str) -> bool:
    """True for the Lead Generation chat, and for a voice call started from it (the call record's origin)."""
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
        log.exception("leads chat kind read failed")
        return False
    _OF[conv] = hit
    return hit


def _q(tenant: str):
    return select(Conversation).where(Conversation.tenant_id == tenant, Conversation.kind == KIND,
                                      or_(Conversation.deleted.is_(None), Conversation.deleted.is_(False)))


def greeting(tenant: str) -> str:
    """The first words of a new Lead Generation chat, from the real desk (never invented numbers)."""
    try:
        from .leads import pipeline as PL
        d = PL.summary(tenant)
    except Exception:   # noqa: BLE001
        d = {}
    if not d.get("hired"):
        return "I am your Lead Generation employee. Hire me from AI Employees to start."
    c, needs = d.get("counts") or {}, []
    n = len(d.get("due") or [])
    if n:
        needs.append(f"{n} follow-up{'s are' if n > 1 else ' is'} due")
    if d.get("no_phone"):
        needs.append(f"{d['no_phone']} lead{'s have' if d['no_phone'] > 1 else ' has'} no phone yet")
    line = f"Hello. You have {c.get('all', 0)} leads kept. " + ("Today: " + "; ".join(needs) + ". " if needs else "")
    return line + ("Tell me who you want to reach (for example 'dentists in Pune'), or attach your own list as a CSV or Excel file. "
                   "I find and keep leads; nothing is sent without your tap.")


def current(tenant: str) -> dict[str, Any]:
    with session() as s:
        c = s.scalars(_q(tenant).order_by(func.coalesce(Conversation.last_at, Conversation.created_at).desc()).limit(1)).first()
        if c is not None:
            _OF[c.id] = True
            return {"id": c.id, "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    with session() as s:          # her newest untouched Lead Generation chat first: no pile of empty ones
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title="Lead Generation chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    hi = greeting(tenant)
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=hi, display=hi, in_history=False,
                      delivered_to_agent=True))
    return {"id": cid, "new": True}


def owns(tenant: str, conv: str) -> bool:
    with session() as s:
        c = s.get(Conversation, conv)
        return bool(c is not None and c.tenant_id == tenant and (c.kind or "") == KIND and not c.deleted)


# ---------------------------------------------------------------- what a turn in the Lead Generation chat knows
def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        txt = _block(tenant)
    except Exception:   # noqa: BLE001
        log.exception("leads block failed")
        txt = ("\n\n<lead_desk>You are the Lead Generation employee in her Lead Generation chat. The desk could not be read "
               "just now; use leads_desk action=read.</lead_desk>")
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


RULES = ("You are her Lead Generation employee, talking in the Lead Generation desk's own chat (or a voice call started from "
         "it). You find businesses that may buy from her, keep one clean row per business with its source, and help her "
         "follow them up. Answer from HER store (the counts below, leads_desk action=read, leads_list) - never invent a "
         "business, a phone number, a count or a price. Plain English, short. "
         "FINDING: before a search say where you will look, how many rows at most and what it costs (IndiaMART and her own "
         "list are free; Google Maps place details cost money per business; a paid seller is off until it is set up). "
         "THE PUBLIC MAPS LISTINGS SCAN is your widest free source: Google Maps' public listing pages read area by area "
         "(leads_desk action=scan query + near + sweep_km + max_rows). Prefer it when she wants many businesses of one kind "
         "in a city and does not want to pay; it runs in the background at one request a second, so say it has STARTED "
         "and where the results will appear, never that it finished. If the scan is OFF (below), ask her once whether to "
         "switch it on; only after her clear yes call leads_run action=scrape_optin on=true. Run a FREE search when she asked for it; for a search that costs money show "
         "the plan and wait for her yes. A CSV / Excel she attaches comes with its file_id: put it in with leads_desk "
         "action=import_file, then say how many rows went in, how many were the same business twice and how many had no "
         "phone. FOLLOWING UP: you MAY set a lead's stage (new, contacted, interested, not interested, won), set a follow-up "
         "date, add her notes and save a search, and say what you changed. To message a lead, write the words with "
         "leads_desk action=draft - it gives a WhatsApp link she taps to send from her own phone; never say a message was "
         "sent. You can NOT send anything, start a campaign, hand a list to the campaign desk or the Telecaller, opt a "
         "business out or forget one: tell her to tap it on the desk next to this chat. A business that opted out is never "
         "contacted again. Businesses only - never lists of private people, never anything behind a login. ")


def _block(tenant: str) -> str:
    from .leads import pipeline as PL
    d = PL.summary(tenant)
    if not d.get("hired"):
        return f"\n\n<lead_desk>{RULES}The Lead Generation employee is not hired yet: tell her to hire it from AI Employees.</lead_desk>"
    c = d.get("counts") or {}
    due = "; ".join(f"{x['name']} ({x['city'] or '-'}, due {x['follow_on']}{': ' + x['note'] if x.get('note') else ''})"
                    for x in d.get("due") or []) or "none"
    run = "; ".join(f"{r['ask'][:60]} ({r['status']}, {r['kept']} kept)" for r in d.get("running") or []) or "none"
    sv = "; ".join(f"{x['name']} ({x['lane']}{', weekly' if x['weekly'] else ''})" for x in d.get("saved") or []) or "none"
    return (f"\n\n<lead_desk>{RULES}\nTrust: {d.get('trust')}. Leads kept: {c.get('all', 0)} (new {c.get('new', 0)}, "
            f"contacted {c.get('contacted', 0)}, interested {c.get('interested', 0)}, not interested {c.get('not_interested', 0)}, "
            f"won {c.get('won', 0)}, opted out {c.get('opted_out', 0)}). New this week: {d.get('new_this_week', 0)}. "
            f"Without a phone: {d.get('no_phone', 0)}.\nFollow-ups due: {due}.\nSearches running: {run}.\n"
            f"Saved searches: {sv}.\nPublic Maps listings scan: {'ON' if d.get('scrape_on') else 'OFF'}"
            f"{' (a scan is running now)' if d.get('scan_running') else ''}.</lead_desk>")


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    @router.get("/api/leads/chat", dependencies=[Depends(require_key)])
    def leads_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/leads/chat/new", dependencies=[Depends(require_key)])
    def leads_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/leads/chat/{conv}/ok", dependencies=[Depends(require_key)])
    def leads_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Lead Generation chat")
        return {"ok": True}

    app.include_router(router)
