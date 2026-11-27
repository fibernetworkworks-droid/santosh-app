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
from pydantic import BaseModel, Field
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
    bg: Mapped[bool | None] = mapped_column(Boolean, nullable=True)   # v0.999.47 work in the background on her PC
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


def bg_on(tenant: str) -> bool:
    """v0.999.47 'Work in the background' on her own PC (Claude Cowork background windows): Hoola acts through the
    PC's accessibility (exact mode) and never takes her mouse or keyboard without her yes. Default off."""
    ensure_table()
    with session() as s:
        row = s.get(ComputerPref, tenant)
        return bool(row is not None and row.bg)


def set_bg(tenant: str, on: bool) -> bool:
    ensure_table()
    with session() as s:
        row = s.get(ComputerPref, tenant)
        if row is None:
            row = ComputerPref(tenant_id=tenant)
            s.add(row)
        row.bg, row.at = bool(on), now()
    return bool(on)


# ---------------------------------------------------------------- what runs on each computer now
def _running(tenant: str, which: str) -> dict[str, Any] | None:
    """The task running on that computer for her right now (from ANY chat or call of hers)."""
    try:
        from .pc import operator as pcop
    except Exception:   # noqa: BLE001
        return None
    best = None
    live = []
    for o in list(pcop.OPS.values()):
        if o.tenant != tenant or o.task_obj is None or o.task_obj.done():
            continue
        is_hoola = o.kind == pcop.HOOLA_PC_KIND
        if (which == "hoola") != is_hoola:
            continue
        live.append(o)
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
            ("computer" if which_of(best.conv) else "chat"), "started": best.created,
            # v0.999.37 her hands: she has the screen / a sign-in waits on her private form / her other jobs at once
            "takeover": bool(getattr(best, "takeover", False)),
            # v0.999.233 COMPUTER V2: the step waiting for her yes, answered right on the job panel
            **({"pending": {"id": str(best.pending.get("id") or ""), "what": str(best.pending.get("what") or "")[:300]}}
               if best.status == "needs_confirm" and isinstance(getattr(best, "pending", None), dict) else {}),
            **({"login": {k: v for k, v in (_hands_login(best) or {}).items() if k != "session_id"}}
               if getattr(best, "login", None) and best.login.get("status") == "pending" else {}),
            "others": [{"session_id": o.id, "task": o.task[:120], "status": o.status, "pc": o.device_name}
                       for o in sorted(live, key=lambda o: o.created) if o is not best]}


def _agent_email(tenant: str) -> str:
    try:   # v0.999.47 Hoola's own address (empty until the owner sets up the mail domain)
        from . import agentmail
        return agentmail.address(tenant) if agentmail.configured() else ""
    except Exception:   # noqa: BLE001
        return ""


DOWNLOADS = {   # v0.999.145 the redesign's Connect page: one download per system (build-desktop.yml releases)
    "windows": DOWNLOAD,
    "mac": "https://github.com/fibernetworkworks-droid/santosh-app/releases/download/desktop-mac-latest/Hoola-Desktop-mac.zip",
    "linux": "https://github.com/fibernetworkworks-droid/santosh-app/releases/download/desktop-linux-latest/Hoola-Desktop-linux.tar.gz"}


def _chrome_ready(tenant: str) -> bool:
    try:   # v0.999.145 her Chrome extension is connected (Hoola can work in her own Chrome tabs)
        from .pc import extlink
        return bool(extlink.ready(tenant))
    except Exception:   # noqa: BLE001
        return False


def choose(tenant: str, text: str) -> dict[str, Any]:
    """v0.999.145 'Let Hoola choose': her PC for a site that refuses cloud computers (when her PC is on), Hoola PC
    otherwise. -> {which, why}."""
    try:
        from .pc import portals
        from .pc.lessons import sites_of
        blocked = next((h for h in sites_of(text) if portals.blocked_for_cloud(h)), "")
    except Exception:   # noqa: BLE001
        blocked = ""
    devs = _paired(tenant)
    mine_ok = mine_on(tenant) and any(d.get("online") for d in devs)
    if blocked and mine_ok:
        return {"which": "mine", "why": f"{blocked} refuses cloud computers, so it runs on your PC"}
    if blocked:
        return {"which": "hoola", "why": f"{blocked} refuses cloud computers and your PC is not on - Hoola PC will try and tell you"}
    return {"which": "hoola", "why": "Hoola PC works even when your PC is off"}


def status(tenant: str) -> dict[str, Any]:
    from .pc.hub import hub
    try:
        pcs = hub.hoola_pcs(tenant)
    except Exception:   # noqa: BLE001
        pcs = []
    devs = _paired(tenant)
    return {
        "hoola": {"online": bool(pcs), "count": len(pcs), "running": _running(tenant, "hoola"),
                  "last": _last(tenant, "hoola"), "email": _agent_email(tenant)},
        "mine": {"on": mine_on(tenant), "background": bg_on(tenant), "devices": devs, "online": any(d.get("online") for d in devs),
                 "chrome": _chrome_ready(tenant), "downloads": DOWNLOADS,
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


class TakeIn(BaseModel):
    on: bool = True


class InputIn(BaseModel):
    op: str
    x: float | None = None
    y: float | None = None
    text: str = ""
    keys: str = ""
    amount: int = 0


class LoginIn(BaseModel):
    id: str
    username: str = ""
    password: str = ""
    skip: bool = False
    save: bool = False          # v0.999.47 'Save for next time' (her tick)
    use_saved: bool = False     # v0.999.47 'Use saved sign-in' (her tap)
    use_onepw: bool = False     # v0.999.51 'Use 1Password sign-in' (her tap)

    def __repr__(self) -> str:          # never printed with the password in it
        return f"LoginIn(id={self.id!r}, skip={self.skip})"

    __str__ = __repr__


class OnePwIn(BaseModel):
    token: str = ""
    vault_id: str = ""

    def __repr__(self) -> str:          # never printed with the token in it
        return f"OnePwIn(vault_id={self.vault_id!r})"

    __str__ = __repr__


def _hands_login(op):
    from .pc.hands import login_public
    return login_public(op)


def _op(tenant: str, sid: str):
    from .pc import operator as pcop
    op = pcop.get(tenant, sid)
    if op is None:
        raise HTTPException(404, "That task is not running")
    return op


class MineIn(BaseModel):
    on: bool


class DecideIn(BaseModel):
    yes: bool
    id: str = Field(default="", max_length=40)


class ChooseIn(BaseModel):
    text: str = Field(default="", max_length=4000)


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

    @router.post("/api/computer/choose", dependencies=[Depends(require_key)])
    def computer_choose(body: ChooseIn, tenant: str = Depends(current_tenant)):
        return choose(tenant, body.text)

    @router.post("/api/computer/task/{sid}/decide", dependencies=[Depends(require_key)])
    def computer_decide(sid: str, body: DecideIn, tenant: str = Depends(current_tenant)):
        """v0.999.233 her yes / no for the step a PC job is waiting on (same as the approval card)."""
        from .pc import operator as pcop
        op = pcop.get(tenant, sid)
        if op is None:
            raise HTTPException(404, "That job is not running")
        pend = op.pending if isinstance(getattr(op, "pending", None), dict) else None
        if not pend or (body.id and body.id != pend.get("id")):
            raise HTTPException(409, "Nothing is waiting for your answer on that job now")
        if not pcop.decide(tenant, sid, str(pend.get("id")), bool(body.yes)):
            raise HTTPException(409, "That question was already answered")
        return {"ok": True, "yes": bool(body.yes)}

    @router.put("/api/computer/mine", dependencies=[Depends(require_key)])
    def computer_mine(body: MineIn, tenant: str = Depends(current_tenant)):
        return {"on": set_mine(tenant, body.on)}

    @router.put("/api/computer/mine/background", dependencies=[Depends(require_key)])
    def computer_mine_bg(body: MineIn, tenant: str = Depends(current_tenant)):
        return {"background": set_bg(tenant, body.on)}

    @router.post("/api/computer/mine/pair", dependencies=[Depends(require_key)])
    def computer_pair(tenant: str = Depends(current_tenant)):
        from .pc import service as pcs
        set_mine(tenant, True)
        return {**pcs.pair_start(tenant), "download": DOWNLOAD}

    # v0.999.37 HER HANDS on the live screen: take control / give it back, her own clicks and keys, the sign-in form
    @router.post("/api/computer/task/{sid}/takeover", dependencies=[Depends(require_key)])
    def computer_takeover(sid: str, body: TakeIn, tenant: str = Depends(current_tenant)):
        from .pc import hands
        try:
            return hands.take(_op(tenant, sid), body.on)
        except ValueError as e:
            raise HTTPException(409, str(e))

    @router.post("/api/computer/task/{sid}/input", dependencies=[Depends(require_key)])
    async def computer_input(sid: str, body: InputIn, tenant: str = Depends(current_tenant)):
        from .pc import hands
        try:
            return await hands.act(_op(tenant, sid), body.op, body.x, body.y, body.text, body.keys, body.amount)
        except ValueError as e:
            raise HTTPException(409, str(e))
        except HTTPException:
            raise
        except Exception as e:   # noqa: BLE001  the PC did not answer
            raise HTTPException(502, f"The PC did not take it ({type(e).__name__})")

    @router.post("/api/computer/task/{sid}/login", dependencies=[Depends(require_key)])
    def computer_login(sid: str, body: LoginIn, tenant: str = Depends(current_tenant)):
        from .pc import hands
        ok = hands.give_login(_op(tenant, sid), body.id, body.username, body.password, skip=body.skip,
                              save=body.save, use_saved=body.use_saved, use_onepw=body.use_onepw)
        body.password = body.username = ""
        if not ok:
            raise HTTPException(409, "That sign-in is no longer waiting")
        return {"ok": True}

    # v0.999.51 1Password (a service account for her Hoola vault): status, connect (token only from this form), disconnect
    @router.get("/api/computer/1password", dependencies=[Depends(require_key)])
    def computer_onepw(tenant: str = Depends(current_tenant)):
        from .pc import onepw
        return onepw.status(tenant)

    @router.post("/api/computer/1password", dependencies=[Depends(require_key)])
    async def computer_onepw_connect(body: OnePwIn, tenant: str = Depends(current_tenant)):
        from .pc import onepw
        try:
            return await onepw.connect(tenant, body.token, body.vault_id)
        except onepw.OnePwError as e:
            raise HTTPException(400, str(e))
        finally:
            body.token = ""

    @router.delete("/api/computer/1password", dependencies=[Depends(require_key)])
    def computer_onepw_off(tenant: str = Depends(current_tenant)):
        from .pc import onepw
        return {"ok": onepw.disconnect(tenant)}

    # v0.999.47 her saved sign-ins: the list (user names masked, never a password) and delete
    @router.get("/api/computer/logins", dependencies=[Depends(require_key)])
    def computer_logins(tenant: str = Depends(current_tenant)):
        from .pc import vault
        return {"logins": vault.list_(tenant)}

    @router.delete("/api/computer/logins/{lid}", dependencies=[Depends(require_key)])
    def computer_login_delete(lid: str, tenant: str = Depends(current_tenant)):
        from .pc import vault
        if not vault.delete(tenant, lid):
            raise HTTPException(404, "Not found")
        return {"ok": True}

    app.include_router(router)
