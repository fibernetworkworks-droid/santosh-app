"""v0.999.38 SOCIAL DESK - the Social Media Manager's own section with its own chat (the SEO desk's twin).

Owner (19 Nov 2026): "NOW LETS MOVE TO NEXT AI EMPLOYEE SECTION" -> the design (claude.ai/artifact/MkKK3knH9dzYJJWh7kyAfT)
-> "GO BUILD".

- The Social chat = a Conversation with kind 'social'. It is kept out of every Hoola chat list (callconv.not_call), like the
  SEO and Hoola Computer chats; facts she tells it still reach her one memory.
- A turn in it (or in a voice call started from it: the call record's origin is the Social chat) gets the desk's state as
  a block (`block`) and the social desk + writer + ads tools in view (`FAMILIES`).
- What it may change: drafts only (a post's caption / time / where it goes, a reply draft) through `social_desk`. Posting,
  sending a reply, approving and starting an ad stay her taps on the desk - said in the block and enforced by the tool.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.socialchat")

KIND = "social"
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
FAMILIES = ["socialdesk", "kalam", "ads"]


def is_social(conv: str) -> bool:
    """True for the Social chat, and for a voice call started from it (the call record's origin)."""
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
        log.exception("social chat kind read failed")
        return False
    _OF[conv] = hit
    return hit


def _q(tenant: str):
    return select(Conversation).where(Conversation.tenant_id == tenant, Conversation.kind == KIND,
                                      or_(Conversation.deleted.is_(None), Conversation.deleted.is_(False)))


def greeting(tenant: str) -> str:
    """The first words of a new Social chat, from the real desk (never invented numbers)."""
    try:
        from .agent.socialdesk_tools import summary
        d = summary(tenant)
    except Exception:   # noqa: BLE001
        d = {}
    if not d.get("hired"):
        return "I am your Social Media Manager. Hire me from AI Employees to start."
    if not d.get("onboarded"):
        return ("Hello, I am your Social Media Manager. Tell me about your business on the right (a few short steps), connect "
                "Instagram or your Facebook Page, and I will read your last 50 posts, find what works and plan your month.")
    needs = []
    if not d.get("accounts"):
        needs.append("connect Instagram or your Facebook Page")
    if d.get("calendar_status") == "draft" and (d.get("posts") or {}).get("total"):
        needs.append(f"approve your calendar ({d['posts']['total']} posts)")
    w = len(d.get("waiting_ok_today") or [])
    if w:
        needs.append(f"OK {w} post{'s' if w > 1 else ''} planned for today")
    n = int((d.get("inbox") or {}).get("needs") or 0)
    if n:
        needs.append(f"answer {n} comment{'s' if n > 1 else ''} or DM{'s' if n > 1 else ''}")
    line = "Hello. " + ("Today I need you to " + ", ".join(needs) + ". " if needs else "Nothing needs you right now. ")
    return line + "Ask me anything about your posts, or tell me what to post."


def current(tenant: str) -> dict[str, Any]:
    with session() as s:
        c = s.scalars(_q(tenant).order_by(func.coalesce(Conversation.last_at, Conversation.created_at).desc()).limit(1)).first()
        if c is not None:
            _OF[c.id] = True
            return {"id": c.id, "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    with session() as s:          # her newest untouched Social chat first: no pile of empty ones
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title="Social chat")
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


# ---------------------------------------------------------------- what a turn in the Social chat knows
def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        txt = _block(tenant)
    except Exception:   # noqa: BLE001
        log.exception("social block failed")
        txt = ("\n\n<social_desk>You are the Social Media Manager in her Social desk chat. The desk could not be read just "
               "now; use social_desk action=read.</social_desk>")
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


RULES = ("You are her Social Media Manager, talking in the Social desk's own chat (or a voice call started from it). Answer "
         "from HER real numbers below or from social_desk action=read; never invent a figure, price or offer - if a number "
         "is not known, say so. Plain English, short. You MAY change drafts with social_desk (a post's caption, hook, "
         "hashtags, time or where it goes; a reply draft; rewrite the calendar draft) - say exactly what you changed, "
         "before -> after. You can NOT post, send a reply, approve a post, hide a comment or start an ad: for those tell her "
         "to tap OK / Send reply / Publish now / Start on the desk next to this chat. Spending money (ads, boosts) is always "
         "her tap. ")


def _block(tenant: str) -> str:
    from .agent.socialdesk_tools import summary
    d = summary(tenant)
    if not d.get("hired"):
        return f"\n\n<social_desk>{RULES}The Social Media Manager is not hired yet: tell her to hire it from AI Employees.</social_desk>"
    if not d.get("onboarded"):
        return (f"\n\n<social_desk>{RULES}Her desk is not set up yet: she answers a few questions and connects Instagram or "
                "her Facebook Page on the screen next to this chat.</social_desk>")
    acc = "; ".join(f"{a['platform']} {a['handle']} ({a['status']}{', ' + str(a['followers']) + ' followers' if a.get('followers') is not None else ''})"
                    for a in d.get("accounts") or []) or "none connected"
    kp = "; ".join(f"{k['name']}: {k['now']} (was {k['was']})" for k in d.get("numbers") or []) or "none yet"
    stg = d.get("strategy") or {}
    po = d.get("posts") or {}
    wait = "; ".join(f"{p['hook']} (id {p['id']})" for p in d.get("waiting_ok_today") or []) or "none"
    ev = "\n".join(f"- {e}" for e in d.get("recent") or []) or "- none"
    return (f"\n\n<social_desk>{RULES}\nBusiness: {d.get('business', '')}. Trust: {d.get('trust')}. "
            f"Posting paused: {d.get('posting_paused')}.\nAccounts: {acc}.\nNumbers (30 days): {kp}.\n"
            f"Judged on: {stg.get('judged_on') or 'not set'}. Content themes: {', '.join(stg.get('pillars') or []) or 'none yet'}.\n"
            f"Calendar: {d.get('calendar_status')} - {po.get('total', 0)} posts ({po.get('drafts', 0)} drafts, "
            f"{po.get('approved', 0)} approved, {po.get('posted', 0)} posted). Waiting for her OK today: {wait}.\n"
            f"Inbox: {d.get('inbox') or {}}.\nHer facts for replies (only these are ever quoted): {d.get('facts') or 'none given'}.\n"
            f"Recent activity:\n{ev}\n</social_desk>")


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    @router.get("/api/social/chat", dependencies=[Depends(require_key)])
    def social_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/social/chat/new", dependencies=[Depends(require_key)])
    def social_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/social/chat/{conv}/ok", dependencies=[Depends(require_key)])
    def social_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Social chat")
        return {"ok": True}

    app.include_router(router)
