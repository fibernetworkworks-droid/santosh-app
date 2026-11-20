"""v0.999.43 ACCOUNTS DESK - the GST & Accounts employee's own section with its own chat (the SEO / Social desks' twin).

Owner (20 Nov 2026): "OK FINE PERFECT. NOW LETS MOVE TO NEXT EMPLOYEE" -> the design
(claude.ai/artifact/SEsautNMYTn6DTx6S1DZH8) -> "GO BUILD... USE CAN EVEN ATTACH THE FILES, PHOTOS, DOC IN CHAT".

- The Accounts chat = a Conversation with kind 'accounts', kept out of every Hoola chat list (callconv.not_call), like the
  SEO / Social / Hoola Computer chats; facts she tells it still reach her one memory.
- A turn in it (or in a voice call started from it) gets the desk's state as a block (`block`) and the accounts desk tool
  in view (`FAMILIES`). She can attach bills, photos, PDFs, statements and spreadsheets in the chat: the tool reads a bill
  into a DRAFT and a statement into bank lines.
- What it may change: drafts only (a bill draft's figures, Hoola-side return drafts, proposed bank matches). Adding a bill
  to the register, sending credit decisions or a return to the portal, filing, recording TDS, closing a month and moving
  money stay her taps (filing also needs her OTP) - said in the block and enforced by the tool.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.accountschat")

KIND = "accounts"
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
FAMILIES = ["accountsdesk"]


def is_accounts(conv: str) -> bool:
    """True for the Accounts chat, and for a voice call started from it (the call record's origin)."""
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
        log.exception("accounts chat kind read failed")
        return False
    _OF[conv] = hit
    return hit


def _q(tenant: str):
    return select(Conversation).where(Conversation.tenant_id == tenant, Conversation.kind == KIND,
                                      or_(Conversation.deleted.is_(None), Conversation.deleted.is_(False)))


def greeting(tenant: str) -> str:
    """The first words of a new Accounts chat, from the real desk (never invented numbers)."""
    try:
        from .agent.accountsdesk_tools import summary
        d = summary(tenant)
    except Exception:   # noqa: BLE001
        d = {}
    if not d.get("hired"):
        return "I am your GST & Accounts employee. Hire me from AI Employees to start."
    needs = []
    if not d.get("gstins"):
        needs.append("connect your GSTIN in Settings (your portal username + the OTP the portal sends you)")
    n = int(d.get("bills_to_check") or 0)
    if n:
        needs.append(f"check {n} bill{'s' if n > 1 else ''} I read")
    m = int(d.get("bank_to_confirm") or 0)
    if m:
        needs.append(f"confirm {m} bank line{'s' if m > 1 else ''} I matched")
    soon = [x for x in d.get("dues") or [] if 0 <= int(x.get("days_left", 99)) <= 7]
    if soon:
        n0, dl = soon[0].get("name") or soon[0]["what"], int(soon[0]["days_left"])
        needs.append(f"{n0} is due today" if dl == 0 else f"{n0} is due in {dl} day{'s' if dl != 1 else ''}")
    line = "Hello. " + ("Today: " + "; ".join(needs) + ". " if needs else "Nothing needs you right now. ")
    return line + "Attach a bill, a photo or a statement here, or ask me about your GST and accounts."


def current(tenant: str) -> dict[str, Any]:
    with session() as s:
        c = s.scalars(_q(tenant).order_by(func.coalesce(Conversation.last_at, Conversation.created_at).desc()).limit(1)).first()
        if c is not None:
            _OF[c.id] = True
            return {"id": c.id, "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    with session() as s:          # her newest untouched Accounts chat first: no pile of empty ones
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title="Accounts chat")
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


# ---------------------------------------------------------------- what a turn in the Accounts chat knows
def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        txt = _block(tenant)
    except Exception:   # noqa: BLE001
        log.exception("accounts block failed")
        txt = ("\n\n<accounts_desk>You are the GST & Accounts employee in her Accounts desk chat. The desk could not be read just "
               "now; use accounts_desk action=read.</accounts_desk>")
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


RULES = ("You are her GST & Accounts employee, talking in the Accounts desk's own chat (or a voice call started from it). "
         "Answer from HER register and the figures below or from accounts_desk action=read; never invent a figure, rate, due "
         "date or rule - if a number is not known, say so. Plain English, short; amounts in rupees. A file she attaches "
         "(a bill photo / PDF, a bank statement, a sheet) comes with its file_id: read a bill with accounts_desk "
         "action=read_bill and a statement with action=import_statement, then say what you read and what the checks found. "
         "You MAY change drafts (a bill draft's figures with action=fix_bill - say before -> after), prepare GSTR-1 / GSTR-3B "
         "drafts inside Hoola, propose bank matches and work out TDS. You can NOT add a bill to the register, send credit "
         "decisions or a return to the GST portal, file a return, record TDS, close or lock a month, or pay anything: for "
         "those tell her to tap Add to register / Send decisions / Save to portal / File with OTP / Record / Close on the desk "
         "next to this chat. Money always moves at her bank. Never ask for her GST portal password or an OTP in the chat. "
         "This is preparation, not professional tax or legal advice. ")


def _block(tenant: str) -> str:
    from .agent.accountsdesk_tools import summary
    d = summary(tenant)
    if not d.get("hired"):
        return f"\n\n<accounts_desk>{RULES}The GST & Accounts employee is not hired yet: tell her to hire it from AI Employees.</accounts_desk>"
    tm, lm = d.get("this_month") or {}, d.get("last_month") or {}
    mo = lambda m: (f"{m.get('period')}: {m.get('documents', 0)} documents; sales {m.get('sales', {}).get('count', 0)} bills, taxable "
                    f"Rs {m.get('sales', {}).get('taxable', 0)}, tax Rs {m.get('sales', {}).get('tax', 0)}; purchases "
                    f"{m.get('purchases', {}).get('count', 0)} bills, tax Rs {m.get('purchases', {}).get('tax', 0)}"
                    f"{'; LOCKED' if m.get('locked') else ''}")
    dues = "; ".join(f"{x['what']} {x['date']} ({x['days_left']} days)" for x in d.get("dues") or []) or "none"
    ev = "\n".join(f"- {e}" for e in d.get("recent") or []) or "- none"
    return (f"\n\n<accounts_desk>{RULES}\nHer GSTINs: {', '.join(d.get('gstins') or []) or 'none connected yet'}. "
            f"Filing scheme: {d.get('scheme')}. Trust: {d.get('trust')}.\n{mo(lm)}.\n{mo(tm)} (so far).\n"
            f"Due dates: {dues}.\nBills read and waiting for her check: {d.get('bills_to_check', 0)}. Bank lines matched and "
            f"waiting for her confirm: {d.get('bank_to_confirm', 0)}.\nRecent changes:\n{ev}\n</accounts_desk>")


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    @router.get("/api/accounts/chat", dependencies=[Depends(require_key)])
    def accounts_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.get("/api/accounts/desk", dependencies=[Depends(require_key)])
    def accounts_desk(tenant: str = Depends(current_tenant)):
        """What waits for her (the Today page's Needs you list) - the same summary the chat reads."""
        from .agent.accountsdesk_tools import summary
        return summary(tenant)

    @router.post("/api/accounts/chat/new", dependencies=[Depends(require_key)])
    def accounts_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/accounts/chat/{conv}/ok", dependencies=[Depends(require_key)])
    def accounts_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Accounts chat")
        return {"ok": True}

    app.include_router(router)
