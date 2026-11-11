"""v0.378 BAAT (App Sahayak Phase 42, owner: "START PHASE 42"): in-app chat between a customer and the shop.

A customer writes from "Message the shop" (one thread per customer account); staff and the owner see every thread with its
unread count and reply. Messages are SiteAppRow rows coll "_chat" owned by the customer (gone with her account), each
{by: member id or "owner", staff: bool, name, text, order?}. Each side is told at once where instant notifications are on
(v0.367 / v0.368) and through the background check (`backend.updates` kind chat) otherwise; a customer message also reaches
the owner's Hoola chat as a capped note - the customer's words are DATA for Hoola, never instructions. The owner replies only
by her own tap (console / phone), never through the agent on its own."""
from __future__ import annotations

import json
import re
import time
from typing import Any

from sqlalchemy import select

from ..db import now, session
from ..site import webapp as W
from .models import AppProject

COLL = "_chat"
MAX_TEXT = 1000
STATS = {"messages": 0, "replies": 0, "notes": 0, "notes_capped": 0}
_NOTES: dict[str, list[float]] = {}
NOTE_CAP_PER_HOUR = 20


class BaatError(W.AppError):
    pass


def _site(r: AppProject) -> str:
    from . import backend as BE
    return BE.bid(r)


def _clean(text: str) -> str:
    t = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]+", " ", str(text or "")).strip()
    if not t:
        raise BaatError("Write something.")
    return t[:MAX_TEXT]


def _rows(r: AppProject, member: str = "") -> list[W.SiteAppRow]:
    with session() as s:
        q = select(W.SiteAppRow).where(W.SiteAppRow.site_id == _site(r), W.SiteAppRow.coll == COLL)
        if member:
            q = q.where(W.SiteAppRow.owner == member)
        out = s.scalars(q.order_by(W.SiteAppRow.created_at.asc())).all()
        for x in out:
            s.expunge(x)
    return out


def _view(x: W.SiteAppRow) -> dict[str, Any]:
    from . import backend as BE
    d = BE._j(x.data, {})
    return {"id": x.id, "text": d.get("text", ""), "staff": bool(d.get("staff")), "name": d.get("name", ""), "order": d.get("order", ""),
            "at": x.created_at.isoformat() if x.created_at else ""}


def _mark_read(r: AppProject, member: str, side: str) -> None:
    """side 'staff' = staff opened the thread; 'customer' = the customer did."""
    from . import backend as BE
    with session() as s:
        for x in s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == _site(r), W.SiteAppRow.coll == COLL,
                                                      W.SiteAppRow.owner == member)).all():
            d = BE._j(x.data, {})
            if bool(d.get("staff")) == (side == "customer") and not d.get("read"):
                d["read"] = True
                x.data = json.dumps(d, ensure_ascii=False)


def _add(r: AppProject, member: str, by: str, staff: bool, name: str, text: str, order: str = "") -> dict[str, Any]:
    with session() as s:
        row = W.SiteAppRow(site_id=_site(r), coll=COLL, owner=member,
                           data=json.dumps({"by": by, "staff": staff, "name": name[:40], "text": text, "order": order[:40]}, ensure_ascii=False))
        s.add(row)
        s.flush()
        s.expunge(row)
    return _view(row)


def mine(r: AppProject, w: W.Who) -> dict[str, Any]:
    if w.m is None:
        raise BaatError("Please log in first.", 401)
    _mark_read(r, w.m.id, "customer")
    return {"messages": [_view(x) for x in _rows(r, w.m.id)][-200:]}


def write(r: AppProject, w: W.Who, text: str, order: str = "") -> dict[str, Any]:
    """A customer's message to the shop."""
    if w.m is None:
        raise BaatError("Please log in first.", 401)
    W.rate(f"chat|{_site(r)}|{w.m.id}", 20, 600)
    text = _clean(text)
    msg = _add(r, w.m.id, w.m.id, False, w.m.name or w.m.email.split("@")[0], text, str(order or ""))
    STATS["messages"] += 1
    _tell_shop(r, msg["name"], text)
    try:
        from . import turant as TU
        TU.later(r, TU.staff_ids(r), f"Message: {msg['name']}", text[:120], msg["id"])
    except Exception:                                         # noqa: BLE001
        pass
    return msg


def threads(r: AppProject, w: W.Who) -> dict[str, Any]:
    """Staff / her: every customer thread, newest first, with the last line and unread (customer messages not yet read)."""
    if not w.staff:
        raise BaatError("This is for staff only.", 403)
    from . import backend as BE
    per: dict[str, list[W.SiteAppRow]] = {}
    for x in _rows(r):
        per.setdefault(x.owner, []).append(x)
    out = []
    for member, xs in per.items():
        last = BE._j(xs[-1].data, {})
        name = next((BE._j(x.data, {}).get("name") for x in xs if not BE._j(x.data, {}).get("staff")), "") or "Customer"
        unread = sum(1 for x in xs if not BE._j(x.data, {}).get("staff") and not BE._j(x.data, {}).get("read"))
        out.append({"member": member, "name": name, "last": last.get("text", "")[:120], "at": xs[-1].created_at.isoformat() if xs[-1].created_at else "",
                    "unread": unread})
    out.sort(key=lambda t: t["at"], reverse=True)
    return {"threads": out, "unread": sum(t["unread"] for t in out)}


def thread(r: AppProject, w: W.Who, member: str) -> dict[str, Any]:
    if not w.staff:
        raise BaatError("This is for staff only.", 403)
    _mark_read(r, member, "staff")
    return {"member": member, "messages": [_view(x) for x in _rows(r, member)][-200:]}


def reply(r: AppProject, w: W.Who, member: str, text: str, her_tap: bool = True) -> dict[str, Any]:
    """Staff / her reply in a customer's thread (her: only from her own tap in the console / phone)."""
    if not w.staff:
        raise BaatError("This is for staff only.", 403)
    if w.owner and not her_tap:
        raise BaatError("A reply to a customer goes only by your tap.", 403)
    if not _rows(r, member):
        raise BaatError("This customer has not written anything yet.", 404)
    text = _clean(text)
    name = (r.name or "Shop") if w.owner else ((w.m.name or "Staff") if w.m else "Staff")
    msg = _add(r, member, "owner" if w.owner else w.id, True, name, text)
    STATS["replies"] += 1
    try:
        from . import turant as TU
        TU.later(r, [member], f"{r.name or 'Shop'}: reply", text[:120], msg["id"])
    except Exception:                                         # noqa: BLE001
        pass
    return msg


def _tell_shop(r: AppProject, name: str, text: str) -> None:
    t = time.time()
    hits = [x for x in _NOTES.get(r.id, []) if t - x < 3600]
    if len(hits) >= NOTE_CAP_PER_HOUR:
        STATS["notes_capped"] += 1
        _NOTES[r.id] = hits
        return
    _NOTES[r.id] = hits + [t]
    try:
        from .android.service import _note
        _note(r, f"{r.name or 'Your app'} ({r.number}): {name} wrote in the app (the customer's words): \"{text[:160]}\". "
                 "Reply from the app's data > Customer chats.")
        STATS["notes"] += 1
    except Exception:                                         # noqa: BLE001
        pass


def new_for(r: AppProject, w: W.Who, t0n) -> list[dict[str, Any]]:
    """For the background check: chat messages since t0 for this account (a customer: replies; staff: customer messages)."""
    from . import backend as BE
    out = []
    with session() as s:
        q = select(W.SiteAppRow).where(W.SiteAppRow.site_id == _site(r), W.SiteAppRow.coll == COLL, W.SiteAppRow.created_at > t0n)
        if not w.staff:
            q = q.where(W.SiteAppRow.owner == w.m.id)
        for x in s.scalars(q.order_by(W.SiteAppRow.created_at.asc()).limit(20)).all():
            d = BE._j(x.data, {})
            if bool(d.get("staff")) != (not w.staff):
                continue
            out.append({"kind": "chat", "coll": COLL, "id": x.id, "title": f"Message: {d.get('name', '')}"[:60], "status": d.get("text", "")[:80]})
    return out
