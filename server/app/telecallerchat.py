"""v0.999.66 AI TELECALLER DESK - the Telecaller employee's own section with its own chat (the Lead desk's twin).

Owner (21 Nov 2026): "WE DONT WANT HUMAN TO CALL ANY MORE --- EVERY CALL TO BE GENERATED AND TALK BY AI ONLY ON HUMAN
PROVIDED DATA" + "PROVIDE A AI CALLCENTER A KNOWLEDGE INPUT VIA APIs, CONNECTOR, PDF / ALL DOCUMENTS" + "MAKE IT GLOBAL".

- The Telecaller chat = a Conversation with kind 'telecall', kept out of every Hoola chat list (callconv.not_call).
- A turn in it (or a voice call started from it) gets the desk's state as a block and the call-centre + telecall tools in
  view (`FAMILIES`).
- What the chat may do: write / change the call script (a DRAFT), add business knowledge (it waits for her OK), make call
  lists, put her people on them, show her the start card, pause / stop a list, try a call in Test chat. Approving the
  script or knowledge, starting a list, keys, switching the line on and confirming a country's law stay HER taps.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.telecallerchat")

KIND = "telecall"
HIRE_KEY = "telecaller"
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
FAMILIES = ["callcentre", "telecall"]


def is_tele(conv: str) -> bool:
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
        log.exception("telecaller chat kind read failed")
        return False
    _OF[conv] = hit
    return hit


def _q(tenant: str):
    return select(Conversation).where(Conversation.tenant_id == tenant, Conversation.kind == KIND,
                                      or_(Conversation.deleted.is_(None), Conversation.deleted.is_(False)))


def summary(tenant: str) -> dict[str, Any]:
    """What the desk and the chat know: hired, the line, the script, knowledge, the lists, today's calls."""
    from .callcentre import knowledge as K
    from .callcentre import outbound as O
    from .callcentre import service as S
    from .employee import hire
    st = hire.status(tenant, HIRE_KEY)
    if st not in ("hired", "paused"):
        return {"hired": False}
    cfg = S.settings(tenant)
    sc, dr = S.approved(tenant), S.draft(tenant)
    src = K.sources(tenant)
    lists = O.lists(tenant)
    calls = S.calls(tenant, 50)
    out = [c for c in calls if c.get("direction") == "out"]
    msgs = S.messages(tenant)
    return {"hired": True, "status": st, "line_on": cfg["line_on"], "provider": cfg["provider"], "number": cfg["number"],
            "country": cfg.get("country"), "currency": cfg.get("currency"), "creds_set": cfg["creds_set"],
            "script_version": (sc or {}).get("version"), "draft_version": (dr or {}).get("version"),
            "knowledge": {"sources": len(src), "waiting": sum(1 for x in src if x["status"] == "waiting"),
                          "facts": sum(x["facts"] for x in src if x["status"] == "approved")},
            "lists": [{k: x[k] for k in ("id", "name", "status", "people")} for x in lists[:10]],
            "running": sum(1 for x in lists if x["status"] == "running"),
            "calls_out": len(out), "calls_in": len(calls) - len(out), "messages": len(msgs),
            "spent_today": O.spent_today(tenant), "problems": O._ready_problems(tenant)}


def greeting(tenant: str) -> str:
    try:
        d = summary(tenant)
    except Exception:   # noqa: BLE001
        d = {}
    if not d.get("hired"):
        return "I am your Telecaller. Hire me from AI Employees to start."
    bits = []
    if d.get("running"):
        bits.append(f"{d['running']} call list{'s are' if d['running'] > 1 else ' is'} calling")
    if (d.get("knowledge") or {}).get("waiting"):
        bits.append(f"{d['knowledge']['waiting']} knowledge source{'s wait' if d['knowledge']['waiting'] > 1 else ' waits'} for your OK")
    if d.get("problems"):
        bits.append("before I can call: " + "; ".join(d["problems"][:3]))
    return ("Hello. I make and speak every call for you, only to the people you give me. "
            + ("Now: " + "; ".join(bits) + ". " if bits else "")
            + "Give me a list (a sheet or your leads), tell me what your business sells and its prices, or attach a price "
              "list, brochure or policy PDF. Calls start only when you tap Start on a list.")


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
        c = Conversation(tenant_id=tenant, kind=KIND, title="Telecaller chat")
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


RULES = ("You are her AI Telecaller, talking in the Telecaller desk's own chat (or a voice call started from it). Hoola "
         "itself makes and speaks every call - no person dials - and ONLY to people in HER data (her sheets, her Telecaller "
         "leads, her Lead Generation leads, her customers). Plain English, short. Never invent a number, a price, a count. "
         "THE SCRIPT: what the line says comes from her approved script (call_centre action=script / faq_add / edit, with "
         "steps [{name, say}] for the call flow) and her approved BUSINESS KNOWLEDGE. A script change is a draft until she "
         "approves it in the app (action=submit sends the card). "
         "KNOWLEDGE: when she tells you about products, prices, services, branches, staff, policies - or attaches a price "
         "list / brochure / policy / FAQ file - add it with call_centre action=knowledge_add (kind text with her words, "
         "file with the file_id, url for a page of her website, sheet for a Google Sheet, system for SAP / Salesforce / an "
         "app she joined on the Systems page). Facts wait for HER approval in the app; say so. An API with a key, and a "
         "live lookup (order status by the caller's number), are set up only in the app: keys never go in chat. "
         "CALL LISTS: call_centre action=list_new (name, goal = why Hoola calls, purpose, basis: asked = they asked to be "
         "contacted, customer = her customers, cold = they never asked; hours, at_once, max_tries, daily_cap money a day, "
         "voicemail words, fields = the answers she wants back), then list_people (file_id of her sheet, or lead_ids), "
         "then list_card - the card goes to HER and ONLY her tap on Start begins the calls. Never say calls started before "
         "she tapped. Pause / stop with list_pause / list_stop. "
         "RULES she cannot switch off: every call opens by saying it is an AI calling for her business; the person's own "
         "local calling hours (their time zone); people who said 'do not call' are never called again; cold lists only in "
         "India and only from her registered 140 / 1600 line; outside India a country's rules must be confirmed by her "
         "(the call-centre read tool, what=countries). Try a call without calling anyone: call_centre action=test_chat. "
         "Read the desk with the call-centre read tool: what=lists / list / knowledge / calls / day. ")


def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        d = summary(tenant)
        if not d.get("hired"):
            txt = f"\n\n<telecaller_desk>{RULES}The Telecaller is not hired yet: tell her to hire it from AI Employees.</telecaller_desk>"
        else:
            kn = d.get("knowledge") or {}
            ls = "; ".join(f"{x['name']} ({x['status']}, {(x.get('people') or {}).get('total', 0)} people)" for x in d.get("lists") or []) or "none"
            txt = (f"\n\n<telecaller_desk>{RULES}\nPhone line: {d.get('provider')} {d.get('number') or '(no number yet)'}, "
                   f"incoming AI answering {'ON' if d.get('line_on') else 'OFF'}. Country {d.get('country')}, currency "
                   f"{d.get('currency')}. Script: running v{d.get('script_version') or '-'}, draft v{d.get('draft_version') or '-'}. "
                   f"Knowledge: {kn.get('sources', 0)} sources, {kn.get('facts', 0)} approved facts, {kn.get('waiting', 0)} "
                   f"waiting for her. Call lists: {ls}. Calls (last 50): {d.get('calls_out', 0)} made, {d.get('calls_in', 0)} "
                   f"answered. Open call-back messages: {d.get('messages', 0)}. Spent in 24 h: {d.get('spent_today')} "
                   f"{d.get('currency')}. Not ready: {'; '.join(d.get('problems') or []) or 'nothing'}.</telecaller_desk>")
    except Exception:   # noqa: BLE001
        log.exception("telecaller block failed")
        txt = f"\n\n<telecaller_desk>{RULES}The desk could not be read just now; use the call-centre read tool (what=day).</telecaller_desk>"
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


router = APIRouter()


def mount(app, current_tenant, require_key, static_dir, version: str) -> None:
    @router.get("/api/telecaller/desk", dependencies=[Depends(require_key)])
    def tele_desk(tenant: str = Depends(current_tenant)):
        return summary(tenant)

    @router.get("/api/telecaller/chat", dependencies=[Depends(require_key)])
    def tele_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/telecaller/chat/new", dependencies=[Depends(require_key)])
    def tele_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/telecaller/chat/{conv}/ok", dependencies=[Depends(require_key)])
    def tele_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Telecaller chat")
        return {"ok": True}

    app.include_router(router)
