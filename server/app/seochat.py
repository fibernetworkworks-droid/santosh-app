"""v0.999.34 SEO DESK - the SEO Specialist's own section with its own chat.

Owner (19 Nov 2026), on the redesign: "IN THIS THERE WILL BE A SEO PANEL AND IN RIGHT A CHAT SECTION WHERE USER CAN ASK
QUERIES AND EVEN CAN TELL TO IMPROVE THIS AND EVEN CAN DO CHANGES IF REQUIRES --- A END TO END AI SEO EMPLOYEE", then
"SHOW THIS PANEL IN LEFT SIDE -- MAKE A SEPERATE SECTION. DONT SHOW HOOLA MAIN SIDE BAR ... CHAT SECTION WILL STAY THERE
EVEN PAGES IN LOADED" and "ALSO FROM APP A VOICE CALL CONNECTING TO THIS SEO EMPLOYEE", then "GO BUILD".

- The SEO chat = a Conversation with kind 'seo'. It is kept out of every Hoola chat list (callconv.not_call) like the
  Hoola Computer chats, so it never mixes with her own chats; facts she tells it still reach her one memory.
- A turn in the SEO chat (or in a voice call started from it: the call record's origin is the SEO chat) gets the desk's
  state as a block (`block`) and the SEO + website tools in view (`families`).
- What it may change: a website Hoola built and hosts for her (matched by host name) through the `website` tool, ONLY
  after she says yes to the exact change; any other website = it writes the fix for her to paste. Said in the block.
"""
from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.seochat")

KIND = "seo"
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}      # tenant -> (at, block) - the desk read is not free; a call turn reuses it
BLOCK_TTL = 60.0


# ---------------------------------------------------------------- which chat
def is_seo(conv: str) -> bool:
    """True for the SEO chat, and for a voice call started from it (the call record's origin)."""
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
        log.exception("seo chat kind read failed")
        return False
    _OF[conv] = hit
    return hit


def _q(tenant: str):
    return select(Conversation).where(Conversation.tenant_id == tenant, Conversation.kind == KIND,
                                      or_(Conversation.deleted.is_(None), Conversation.deleted.is_(False)))


def greeting(tenant: str) -> str:
    """The first words of a new SEO chat: what needs her today, from the real desk (never invented numbers)."""
    try:
        from .seo import desk as D
        d = D.desk_view(tenant)
    except Exception:   # noqa: BLE001
        d = {}
    if not d.get("hired"):
        return "I am your SEO Specialist. Hire me from AI Employees to start."
    if not d.get("onboarded"):
        return ("Hello, I am your SEO Specialist. Tell me your website on the right (four short steps) and I will check "
                "every page, read your Google numbers and write a 90-day plan for you to approve.")
    needs = []
    if not (d.get("google") or {}).get("connected"):
        needs.append("connect Google Search Console so I can read your real clicks")
    if d.get("roadmap_status") == "draft":
        needs.append(f"approve your 90-day plan ({d.get('roadmap_count', 0)} steps)")
    h = ((d.get("pro") or {}).get("health") or {})
    line = "Hello. " + ("Today I need you to " + " and ".join(needs) + ". " if needs else "")
    if h.get("total") is not None:
        line += f"Your website health is {h['total']} out of 100. "
    line += "Ask me anything about your SEO, or tell me what to improve."
    return line


def current(tenant: str) -> dict[str, Any]:
    """Her newest SEO chat; a new one (with today's greeting) when she has none."""
    with session() as s:
        c = s.scalars(_q(tenant).order_by(func.coalesce(Conversation.last_at, Conversation.created_at).desc()).limit(1)).first()
        if c is not None:
            _OF[c.id] = True
            return {"id": c.id, "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    with session() as s:          # her newest untouched SEO chat first: no pile of empty ones
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title="SEO chat")
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


# ---------------------------------------------------------------- where changes can go
def _host(url: str) -> str:
    h = (urlparse(url if "//" in (url or "") else "https://" + (url or "")).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def hoola_site(tenant: str, url: str) -> dict[str, Any] | None:
    """The website Hoola built and hosts for her at this address, or None (then Hoola cannot change it directly)."""
    want = _host(url)
    if not want:
        return None
    try:
        from .site import hosting
        for host, v in hosting.host_map().items():
            if v.get("tenant") == tenant and _host(host) == want:
                return {"site": v["site"], "host": host}
    except Exception:   # noqa: BLE001
        log.debug("hoola site lookup failed", exc_info=True)
    return None


# ---------------------------------------------------------------- what a turn in the SEO chat knows
def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        txt = _block(tenant)
    except Exception:   # noqa: BLE001
        log.exception("seo block failed")
        txt = "\n\n<seo_desk>You are the SEO Specialist in her SEO desk chat. The desk could not be read just now; " \
              "use seo_dekho for her numbers.</seo_desk>"
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


def _block(tenant: str) -> str:
    from .seo import desk as D
    d = D.desk_view(tenant)
    rules = ("You are her SEO Specialist, talking in the SEO desk's own chat (or a voice call started from it). Answer "
             "from HER real numbers below or from the seo / seo_dekho tools; never invent a figure - if a number is not "
             "known, say so. Plain English, short. When she asks to improve or fix something: say exactly what you will "
             "change (before -> after, page by page) and ask 'Shall I make this change?'. ")
    if not d.get("hired"):
        return f"\n\n<seo_desk>{rules}The SEO Specialist is not hired yet: tell her to hire it from AI Employees.</seo_desk>"
    if not d.get("onboarded"):
        return (f"\n\n<seo_desk>{rules}Her desk is not set up yet: she gives her website in the setup steps on the screen "
                "(or tell her you can set it up with the seo tool's onboarding when she gives the address).</seo_desk>")
    site = d.get("site") or {}
    hs = hoola_site(tenant, site.get("url", ""))
    if hs:
        change = (f"HER WEBSITE IS BUILT AND HOSTED BY HOOLA (website id {hs['site']}). You CAN change it with the "
                  "`website` tool (edit_lines / write_file / change), but ONLY after she said yes in this chat to that "
                  "exact change - never on your own. After a change, say what changed and that she can undo it in the "
                  "Web Studio's History.")
    else:
        change = ("Her website is NOT built by Hoola, so you cannot change it directly. Write the exact fix for her to "
                  "paste (the new title, the text, the file to upload, where it goes) or for her web person.")
    h = ((d.get("pro") or {}).get("health") or {})
    kp = "; ".join(f"{k['name']}: {k['now']} (was {k['baseline']})" for k in (d.get("kpis") or [])[:7])
    tasks = "\n".join(f"- [{t.get('priority') or t.get('level')}] {t.get('url', '')}: {t.get('text', '')} (fix: {t.get('fix', '')})"
                      for t in (d.get("open_tasks") or [])[:10])
    plan = d.get("board") or {}
    doing = [i["title"] for k in ("doing", "waiting_her") for i in plan.get(k, [])][:6]
    ev = "\n".join(f"- {e['at'][:10]} {e['text']}" for e in (d.get("events") or [])[:6])
    return (f"\n\n<seo_desk>{rules}\n{change}\n"
            f"Site: {site.get('name', '')} {site.get('url', '')}. Desk state: {d.get('state')}. Plan: {d.get('roadmap_status')} "
            f"({d.get('roadmap_count', 0)} steps). Google connected: {bool((d.get('google') or {}).get('connected'))}.\n"
            f"Health: {h.get('total', 'not checked yet')}/100.\nNumbers: {kp or 'none yet'}.\n"
            f"Open problems (newest check):\n{tasks or '- none'}\n"
            f"Plan steps in progress or waiting for her: {', '.join(doing) or 'none'}.\n"
            f"Recent activity:\n{ev or '- none'}\n</seo_desk>")


FAMILIES = ["seo", "site"]


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    @router.get("/api/seo/chat", dependencies=[Depends(require_key)])
    def seo_chat(tenant: str = Depends(current_tenant)):
        r = current(tenant)
        from .seo import desk as D
        d = D.desk_view(tenant)
        site = d.get("site") or {}
        hs = hoola_site(tenant, site.get("url", "")) if site else None
        return {**r, "can_change": bool(hs), "change_where": (hs or {}).get("host") or ""}

    @router.post("/api/seo/chat/new", dependencies=[Depends(require_key)])
    def seo_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/seo/chat/{conv}/ok", dependencies=[Depends(require_key)])
    def seo_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your SEO chat")
        return {"ok": True}

    app.include_router(router)
