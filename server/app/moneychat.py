"""v0.999.156 MONEY SAFETY DESK - the Money Safety Assistant's own section, like the business desks (owner: "Money Safety
Assistant --- now lets make a seperate panel as same as in bussiness section has. show design here first perfectly" ->
the design claude.ai/artifact/BWjghhnCL3daja6RgrkMeE -> "go").

- The Money Safety chat = a Conversation with kind 'money', kept out of every Hoola chat list (callconv.not_call), like the
  Accounts / Support chats; facts she tells it still reach her one memory.
- A turn in it (or in a voice call started from it) gets the desk's state as a block (`block`) and the money-safety tool
  (`paisa_sahayak`, family finguard) in view.
- The desk's pages call the F1 engine (fin/desks/safety.py through /api/fin/safety/*). Every letter is a draft SHE sends;
  "I've sent it" / "Closed" are her taps on a case (`set_state`). Nothing here moves money, files, decides or sends.
- Her country lives in the employee's settings (`country`); the engine's rule levels decide what a date may be called:
  checked = a deadline, source_read = a reminder, verify = "not confirmed - check this".
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.moneychat")

KIND = "money"
KEY = "paisa_sahayak"           # the Hub employee
TOOL = "paisa_sahayak"          # its tool (same name)
FAMILIES = ["finguard"]
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
STATES = ("drafted", "sent", "tracking", "closed")
COUNTRIES = ("GB", "US", "IN", "AE", "SG", "AU", "CA", "IE", "DE", "SA")


class MoneyError(ValueError):
    pass


def is_money(conv: str) -> bool:
    """True for the Money Safety chat, and for a voice call started from it (the call record's origin)."""
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
        log.exception("money chat kind read failed")
        return False
    _OF[conv] = hit
    return hit


# ---------------------------------------------------------------- the desk
def _hire():
    from .employee import hire
    return hire


def country(tenant: str) -> str:
    try:
        cc = str(_hire().settings(tenant, KEY).get("country") or "").upper()
    except Exception:   # noqa: BLE001
        cc = ""
    if cc:
        return cc
    try:                                      # else the first country of her finance workspace
        from .fin import profile as PR
        for w in PR.workspaces(tenant):
            for c in w.get("countries") or []:
                return str(c).upper()
    except Exception:   # noqa: BLE001
        pass
    return ""


def set_country(tenant: str, cc: str) -> dict[str, Any]:
    cc = str(cc or "").strip().upper()
    if len(cc) != 2 or not cc.isalpha():
        raise MoneyError("country: the two-letter country code, for example GB.")
    _hire().save_settings(tenant, KEY, country=cc)
    forget(tenant)
    return {"country": cc}


def _draft(s, case_id: str):
    from .fin import models as M
    return s.query(M.FinDraft).filter(M.FinDraft.case_id == case_id, M.FinDraft.kind == "letter") \
        .order_by(M.FinDraft.created_at.desc()).first()


def _letter(s, case_id: str) -> str:
    d = _draft(s, case_id)
    return d.body if d else ""


def _more(s, case_id: str) -> dict[str, Any]:
    """What the engine said with the letter (time limits at their level, evidence, route), kept on the draft."""
    import json
    d = _draft(s, case_id)
    try:
        return (json.loads(d.meta or "{}") if d else {}).get("case") or {}
    except ValueError:
        return {}


def cases(tenant: str, with_letters: bool = False) -> list[dict[str, Any]]:
    from .fin import models as M
    M.ensure()
    with session() as s:
        rows = s.query(M.FinCase).filter(M.FinCase.tenant_id == tenant, M.FinCase.employee == "safety") \
            .order_by(M.FinCase.created_at.desc()).limit(100).all()
        out = []
        for r in rows:
            row = {"id": r.id, "part": r.part, "title": r.title, "state": r.state or "drafted", "due": r.due or "",
                   "decider": r.decider, "created_at": r.created_at.isoformat() if r.created_at else ""}
            if with_letters:
                row["letter"] = _letter(s, r.id)
            out.append(row)
        return out


def case(tenant: str, case_id: str) -> dict[str, Any]:
    from .fin import models as M
    M.ensure()
    with session() as s:
        r = s.get(M.FinCase, case_id)
        if r is None or r.tenant_id != tenant or r.employee != "safety":
            raise MoneyError("No such case.")
        return {"id": r.id, "part": r.part, "title": r.title, "state": r.state or "drafted", "due": r.due or "",
                "created_at": r.created_at.isoformat() if r.created_at else "", "letter": _letter(s, r.id), **_more(s, r.id)}


def set_state(tenant: str, case_id: str, state: str) -> dict[str, Any]:
    """Her tap on a case: I've sent it / waiting / closed / back to draft. Only the state moves - nothing is sent."""
    if state not in STATES:
        raise MoneyError("state: drafted | sent | tracking | closed.")
    from .fin import models as M
    from .db import now
    M.ensure()
    with session() as s:
        r = s.get(M.FinCase, case_id)
        if r is None or r.tenant_id != tenant or r.employee != "safety":
            raise MoneyError("No such case.")
        r.state = state
        r.updated_at = now()
        s.commit()
    forget(tenant)
    return case(tenant, case_id)


def summary(tenant: str) -> dict[str, Any]:
    h = _hire()
    st = h.status(tenant, KEY)
    if st not in ("hired", "paused"):
        return {"hired": False, "status": st, "say": "The Money Safety Assistant is not hired. Hire it from AI Employees."}
    with session() as s:
        trust = h._view(h._row(s, tenant, KEY)).get("trust") or ""    # noqa: SLF001
    cs = cases(tenant)
    open_ = [c for c in cs if c["state"] != "closed"]
    return {"hired": True, "status": st, "trust": {"seekh": "Learning", "saathi": "Partner", "bharosa": "Trusted"}.get(trust, "Learning"),
            "country": country(tenant), "countries": list(COUNTRIES), "cases": cs,
            "open": len(open_), "to_send": sum(1 for c in open_ if c["state"] == "drafted"),
            "due": sorted([c for c in open_ if c["due"]], key=lambda c: c["due"])[:5]}


def owns(tenant: str, conv: str) -> bool:
    with session() as s:
        c = s.get(Conversation, conv)
        return bool(c is not None and c.tenant_id == tenant and (c.kind or "") == KIND and not c.deleted)


# ---------------------------------------------------------------- the chat
def _q(tenant: str):
    return select(Conversation).where(Conversation.tenant_id == tenant, Conversation.kind == KIND,
                                      or_(Conversation.deleted.is_(None), Conversation.deleted.is_(False)))


def greeting(tenant: str) -> str:
    d = summary(tenant)
    if not d.get("hired"):
        return "I am your Money Safety Assistant. Hire me from AI Employees to start."
    needs = []
    if not d.get("country"):
        needs.append("tell me your country in Settings, so I use its rules")
    if d.get("to_send"):
        n = d["to_send"]
        needs.append(f"{n} letter{'s' if n > 1 else ''} I drafted {'are' if n > 1 else 'is'} waiting for you to send")
    line = "Hello. " + ("Today: " + "; ".join(needs) + ". " if needs else "Nothing needs you right now. ")
    return line + ("Paste a message you are not sure about, or tell me what went wrong with a payment. "
                   "I never ask for your PIN, password, card number or a code.")


def current(tenant: str) -> dict[str, Any]:
    with session() as s:
        c = s.scalars(_q(tenant).order_by(func.coalesce(Conversation.last_at, Conversation.created_at).desc()).limit(1)).first()
        if c is not None:
            _OF[c.id] = True
            return {"id": c.id, "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    with session() as s:          # her newest untouched Money Safety chat first: no pile of empty ones
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title="Money Safety chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    hi = greeting(tenant)
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=hi, display=hi, in_history=False,
                      delivered_to_agent=True))
    return {"id": cid, "new": True}


# ---------------------------------------------------------------- what a turn in the Money Safety chat knows
RULES = ("You are her Money Safety Assistant, talking in the Money Safety desk's own chat (or a voice call started from it). "
         "Use the " + TOOL + " tool: check_pay for a message, link or payment request (links are read as text, never opened); "
         "refund_claim, card_dispute, complaint_global, credit_dispute, id_theft and deposit_check need her two-letter country. "
         "A letter you draft is saved as a case on the desk next to this chat; SHE sends it - never say it was sent. "
         "Say a date the way the tool gives it: only a 'deadline' is a legal deadline; a 'reminder' is from the official page; "
         "'not confirmed - check this' means act early and check. Never invent a time limit, a limit or a phone number. "
         "If she already paid a scammer: tell her first to call her bank on the number on her card. Never ask for, accept or "
         "repeat a PIN, OTP, password, card number or security code. Nothing you do moves money. Plain English, short. "
         "This is help to act, not legal advice. ")


def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        d = summary(tenant)
        if not d.get("hired"):
            txt = f"\n\n<money_safety_desk>{RULES}The Money Safety Assistant is not hired yet: tell her to hire it from AI Employees.</money_safety_desk>"
        else:
            cs = "\n".join(f"- {c['title']}: {c['state']}{', next date ' + c['due'] if c['due'] else ''}"
                           for c in d["cases"] if c["state"] != "closed")[:2400] or "- none"
            txt = (f"\n\n<money_safety_desk>{RULES}\nHer country: {d.get('country') or 'not set yet - ask her, or ask her to set it in Settings'}."
                   f"\nOpen cases:\n{cs}</money_safety_desk>")
    except Exception:   # noqa: BLE001
        log.exception("money block failed")
        txt = f"\n\n<money_safety_desk>{RULES}The desk could not be read just now.</money_safety_desk>"
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


# ---------------------------------------------------------------- routes
router = APIRouter()


def _err(e: Exception):
    raise HTTPException(400, str(e))


def mount(app, current_tenant, require_key) -> None:
    dep = [Depends(require_key)]

    @router.get("/api/money/chat", dependencies=dep)
    def money_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/money/chat/new", dependencies=dep)
    def money_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/money/chat/{conv}/ok", dependencies=dep)
    def money_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Money Safety chat")
        return {"ok": True}

    @router.get("/api/money/desk", dependencies=dep)
    def money_desk(tenant: str = Depends(current_tenant)):
        return summary(tenant)

    @router.put("/api/money/country", dependencies=dep)
    def money_country(body: dict, tenant: str = Depends(current_tenant)):
        try:
            return set_country(tenant, (body or {}).get("country"))
        except Exception as e:   # noqa: BLE001
            _err(e)

    @router.get("/api/money/cases/{case_id}", dependencies=dep)
    def money_case(case_id: str, tenant: str = Depends(current_tenant)):
        try:
            return case(tenant, case_id)
        except MoneyError as e:
            raise HTTPException(404, str(e))

    @router.post("/api/money/cases/{case_id}/state", dependencies=dep)
    def money_case_state(case_id: str, body: dict, tenant: str = Depends(current_tenant)):
        try:
            return set_state(tenant, case_id, str((body or {}).get("state") or ""))
        except MoneyError as e:
            _err(e)

    app.include_router(router)
