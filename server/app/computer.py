"""v0.890 HOOLA COMPUTER - one section for the two computers Hoola works on.

Owner (13 Nov 2026): "LETS DEVELOP A SECTION FOR IT NAME HOOLA COMPUTER --- IN THIS 2 SECTION -- HOOLA PC, USER PC ---
IF USER ENABLE IT -- USER WILL DOWNLOAD .EXE IN USER PC --- STEPS SHOWN IN THAT SECTION AND FOR HOOLA PC --- USER WILL
LAND ON ITS WORKSPACE DIRECTLY --- IN BOTH SECTION CHAT IS DIFFERENT --- IT WILL NOT MIX WITH HOOLA PERSONAL CHAT,
SESSION CHAT --- BOTH SECTION HAS ITS OWN CHAT. WHERE AS VOICE CALL REMAIN SAME FOR BOTH COMPUTERS", then "GO" on the
design (and Hoola remembers facts across chats: chats separate, one Hoola who knows her).

- A computer chat = a Conversation with kind 'computer' and computer 'hoola' (Hoola PC) or 'mine' (her PC). It is
  left out of every chat list / 'the chat she is in' (callconv.not_call), so it never mixes with her Hoola chats.
- A turn in a computer chat ALWAYS runs on that computer: agent.where.remember returns the fixed place (hoolapc / pc)
  for it, so the PC tools, pick.py and the place note all follow without guessing.
- 'Use my PC' is HER switch (computer_prefs). Default: on when she already has a paired personal PC.
- The workspace shows the task running on that computer for her, whichever chat or call started it - that is how
  the one voice call shows up in the computer section.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Boolean, DateTime, String, func, or_, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, Conversation, Message, now, session

log = logging.getLogger("santosh.computer")

KIND = "computer"
WHICH = ("hoola", "mine")
PLACE = {"hoola": "hoolapc", "mine": "pc"}
TITLE = {"hoola": "Hoola PC", "mine": "Your PC"}
DOWNLOAD = "https://github.com/fibernetworkworks-droid/santosh-app/releases/download/desktop-latest/SantoshDesktop.exe"
_OF: dict[str, str] = {}          # conv id -> 'hoola' | 'mine' | '' (a conversation never changes kind)


class ComputerPref(Base):
    __tablename__ = "computer_prefs"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mine_on: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_TABLE_OK: set[int] = set()


def ensure_table() -> None:
    from . import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _TABLE_OK:
        return
    ComputerPref.__table__.create(bind=eng, checkfirst=True)
    _TABLE_OK.add(id(eng))


def _utc(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- which computer a chat belongs to
def which_of(conv: str) -> str:
    """'hoola' | 'mine' for a Hoola Computer chat, '' for any other conversation."""
    if not conv:
        return ""
    if conv in _OF:
        return _OF[conv]
    try:
        with session() as s:
            c = s.get(Conversation, conv)
            w = (c.computer or "") if (c is not None and (c.kind or "") == KIND) else ""
    except Exception:   # noqa: BLE001
        log.exception("computer kind read failed")
        return ""
    w = w if w in WHICH else ""
    _OF[conv] = w
    return w


def place_of(conv: str) -> str:
    """The fixed place of a computer chat for agent.where ('hoolapc' / 'pc'), '' otherwise."""
    return PLACE.get(which_of(conv), "")


# ---------------------------------------------------------------- her switch
def _paired(tenant: str) -> list[dict[str, Any]]:
    try:
        from .pc import service as pcs
        return pcs.devices(tenant)
    except Exception:   # noqa: BLE001
        log.exception("devices read failed")
        return []


def mine_on(tenant: str) -> bool:
    ensure_table()
    with session() as s:
        row = s.get(ComputerPref, tenant)
        if row is not None and row.mine_on is not None:
            return bool(row.mine_on)
    return bool(_paired(tenant))      # never chosen: on when she already has a paired PC


def set_mine(tenant: str, on: bool) -> bool:
    ensure_table()
    with session() as s:
        row = s.get(ComputerPref, tenant)
        if row is None:
            row = ComputerPref(tenant_id=tenant)
            s.add(row)
        row.mine_on, row.at = bool(on), now()
    return bool(on)


# ---------------------------------------------------------------- what runs on each computer now
def _running(tenant: str, which: str) -> dict[str, Any] | None:
    """The task running on that computer for her right now (from ANY chat or call of hers)."""
    try:
        from .pc import operator as pcop
    except Exception:   # noqa: BLE001
        return None
    best = None
    for o in list(pcop.OPS.values()):
        if o.tenant != tenant or o.task_obj is None or o.task_obj.done():
            continue
        is_hoola = o.kind == pcop.HOOLA_PC_KIND
        if (which == "hoola") != is_hoola:
            continue
        if best is None or o.created > best.created:
            best = o
    if best is None:
        return None
    from_call = False
    try:
        from .callconv import is_call
        from_call = is_call(best.conv)
    except Exception:   # noqa: BLE001
        pass
    return {"session_id": best.id, "task": best.task[:200], "status": best.status, "step": best.step,
            "steps_max": best.steps_max, "thought": (getattr(best, "thought", "") or best.action or "")[:200],
            "pc": best.device_name, "conv": best.conv, "from": "call" if from_call else
            ("computer" if which_of(best.conv) else "chat"), "started": best.created}


def status(tenant: str) -> dict[str, Any]:
    from .pc.hub import hub
    try:
        pcs = hub.hoola_pcs(tenant)
    except Exception:   # noqa: BLE001
        pcs = []
    devs = _paired(tenant)
    return {
        "hoola": {"online": bool(pcs), "count": len(pcs), "running": _running(tenant, "hoola"),
                  "last": _last(tenant, "hoola")},
        "mine": {"on": mine_on(tenant), "devices": devs, "online": any(d.get("online") for d in devs),
                 "running": _running(tenant, "mine"), "last": _last(tenant, "mine"), "download": DOWNLOAD},
    }


# ---------------------------------------------------------------- the computer's own chats
def _q(tenant: str, which: str):
    return select(Conversation).where(Conversation.tenant_id == tenant, Conversation.kind == KIND,
                                      Conversation.computer == which,
                                      or_(Conversation.deleted.is_(None), Conversation.deleted.is_(False)))


def chats(tenant: str, which: str, limit: int = 60) -> list[dict[str, Any]]:
    first = (select(Message.display).where(Message.conversation_id == Conversation.id, Message.role == "user",
                                           Message.display.is_not(None), Message.display != "")
             .order_by(Message.id).limit(1).correlate(Conversation).scalar_subquery())
    at = func.coalesce(Conversation.last_at, Conversation.created_at)
    q = _q(tenant, which).add_columns(first).order_by(at.desc()).limit(max(1, min(int(limit or 60), 200)))
    out = []
    from .turnresult import brief
    with session() as s:
        rows = s.execute(q).all()
    for k, (c, first_text) in enumerate(rows):
        when = _utc(c.last_at or c.created_at)
        out.append({"id": c.id, "title": (c.title or str(first_text or "").strip().replace("\n", " ")[:80] or "New task"),
                    "updated_at": when.isoformat() if when else "", "empty": not first_text,
                    "result": brief(tenant, c.id) if k < 20 and first_text else None})
    return out


def _last(tenant: str, which: str) -> dict[str, Any] | None:
    try:
        rows = chats(tenant, which, 5)
    except Exception:   # noqa: BLE001
        return None
    for r in rows:
        if not r["empty"]:
            return {"id": r["id"], "title": r["title"], "result": r["result"]}
    return None


def new_chat(tenant: str, which: str) -> dict[str, Any]:
    if which not in WHICH:
        raise ValueError("which")
    with session() as s:        # her newest untouched one first: no pile of empty "New task" chats
        for c in s.scalars(_q(tenant, which).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "reused": True}
        c = Conversation(tenant_id=tenant, kind=KIND, computer=which)
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = which
    greet = ("Hoola PC is ready. Tell me the work - a portal, a form, a download, a list of entries - and I will do it "
             "here on Hoola's own computer." if which == "hoola" else
             "Your PC is connected to this chat. Tell me what to do on it and I will work in Chrome or your apps.")
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=greet, display=greet, in_history=False,
                      delivered_to_agent=True))
    return {"id": cid, "reused": False}


def owns(tenant: str, conv: str, which: str) -> bool:
    with session() as s:
        c = s.get(Conversation, conv)
        return bool(c is not None and c.tenant_id == tenant and (c.kind or "") == KIND and (c.computer or "") == which
                    and not c.deleted)


# ---------------------------------------------------------------- routes
router = APIRouter()


class MineIn(BaseModel):
    on: bool


def _which(which: str) -> str:
    if which not in WHICH:
        raise HTTPException(404, "Unknown computer (hoola | mine)")
    return which


def mount(app, current_tenant, require_key) -> None:

    @router.get("/api/computer", dependencies=[Depends(require_key)])
    def computer_status(tenant: str = Depends(current_tenant)):
        return status(tenant)

    @router.get("/api/computer/{which}/chats", dependencies=[Depends(require_key)])
    def computer_chats(which: str, limit: int = 60, tenant: str = Depends(current_tenant)):
        return {"chats": chats(tenant, _which(which), limit)}

    @router.post("/api/computer/{which}/chats", dependencies=[Depends(require_key)])
    def computer_new_chat(which: str, tenant: str = Depends(current_tenant)):
        which = _which(which)
        if which == "mine" and not mine_on(tenant):
            raise HTTPException(409, "Turn on 'Use my PC' first")
        return new_chat(tenant, which)

    @router.put("/api/computer/mine", dependencies=[Depends(require_key)])
    def computer_mine(body: MineIn, tenant: str = Depends(current_tenant)):
        return {"on": set_mine(tenant, body.on)}

    @router.post("/api/computer/mine/pair", dependencies=[Depends(require_key)])
    def computer_pair(tenant: str = Depends(current_tenant)):
        from .pc import service as pcs
        set_mine(tenant, True)
        return {**pcs.pair_start(tenant), "download": DOWNLOAD}

    app.include_router(router)
