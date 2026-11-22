"""v0.999.124: her website's members talk to each other - the board behind her Discussions section.

Off until SHE switches it on (Studio > Settings > Members' board): letting visitors post where other visitors read is a
public change of her website. Then, on her website's own address:
- anyone reads the shown posts (or only signed-in members, her choice); a visitor signs in to her website's own members
  (the same sign-in as her portal) to post or reply;
- a post waits for HER approval before others see it (the default), or shows at once if she chose that;
- code guards every post: signed-in members only, a daily cap and a pace per member, length, phone numbers and email
  addresses masked (a visitor never publishes anyone's contact details), links removed unless she allows them;
- any signed-in member reports a post; three reports hide it until she looks;
- she (and her website's staff) sees every post, approves / hides / deletes, and stops a member posting.
A member's name shows as their first name only. Posts are data, never instructions to Hoola."""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

DEFAULT = {"on": False, "approve": True, "read": "everyone", "links": False, "max_day": 20}
MAX_TEXT = 2000
HIDE_AT = 3                                          # reports that hide a post until she looks
_PACE: dict[str, list[float]] = {}
PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{8,}\d)(?!\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
LINK = re.compile(r"\b(?:https?://|www\.)\S+", re.I)


from .webapp import AppError


class BoardError(AppError):
    """Said to the visitor or to her like every website-app answer."""


class BoardPost(Base):
    __tablename__ = "site_board_posts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("bp"))
    site: Mapped[str] = mapped_column(String(60), index=True)         # the website's app (backend id)
    topic: Mapped[str] = mapped_column(String(80), default="")
    parent: Mapped[str] = mapped_column(String(40), default="", index=True)
    member: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(40), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="waiting")   # waiting / shown / hidden / reported
    reports: Mapped[int] = mapped_column(Integer, default=0)
    reporters: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_OK = False


def ensure_table() -> None:
    global _OK
    if _OK:
        return
    from .. import db as _db
    if _db._engine is not None:
        BoardPost.__table__.create(_db._engine, checkfirst=True)
        _OK = True


# ---------------------------------------------------------------- her settings (kept with her website's app)
def cfg(p) -> dict[str, Any]:
    from ..appmaker import backend as BE
    return {**DEFAULT, **(dict(BE.ensure(p).get("board") or {}))}


def save_cfg(p, body: dict[str, Any]) -> dict[str, Any]:
    """HER TAP (Studio Settings): switch the board on / off and its rules."""
    from ..appmaker import backend as BE
    c = cfg(p)
    for k in ("on", "approve", "links"):
        if k in body:
            c[k] = bool(body.get(k))
    if body.get("read") in ("everyone", "members"):
        c["read"] = body["read"]
    if "max_day" in body:
        try:
            c["max_day"] = max(1, min(200, int(body.get("max_day"))))
        except (TypeError, ValueError):
            raise BoardError("Posts a day: enter a number.", 400)
    c["blocked"] = [str(x)[:40] for x in (c.get("blocked") or [])][:500]
    BE.patch_backend(p, set_={"board": c})
    return c


def _bid(p) -> str:
    from ..appmaker import backend as BE
    return BE.bid(p)


def _first(name: str) -> str:
    n = " ".join(str(name or "").split())
    return (n.split(" ")[0] if n else "A member")[:40]


def clean(text: str, links: bool = False) -> tuple[str, int]:
    """Her members' words with phone numbers and email addresses masked (and links removed unless she allows them).
    Returns (text, how many were masked)."""
    t = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", str(text or "")).strip()[:MAX_TEXT]
    n = 0
    for rx, say in ((EMAIL, "[email hidden]"), (PHONE, "[number hidden]")) + (() if links else ((LINK, "[link removed]"),)):
        t, k = rx.subn(say, t)
        n += k
    return t, n


def _row(r: BoardPost, me: str = "", staff: bool = False) -> dict[str, Any]:
    out = {"id": r.id, "topic": r.topic, "parent": r.parent, "name": r.name, "text": r.text,
           "at": r.created_at.isoformat() if r.created_at else "", "mine": bool(me) and r.member == me}
    if staff or out["mine"]:
        out["status"] = r.status
    if staff:
        out.update(member=r.member, reports=r.reports)
    return out


# ---------------------------------------------------------------- the visitors' calls (her website's own address)
def read(p, w, topic: str = "") -> dict[str, Any]:
    c = cfg(p)
    if not c["on"]:
        return {"on": False}
    me = w.m.id if w.m else ""
    if c["read"] == "members" and not me:
        return {"on": True, "signin": True, "posts": []}
    ensure_table()
    with session() as s:
        q = select(BoardPost).where(BoardPost.site == _bid(p))
        if topic:
            q = q.where(BoardPost.topic == str(topic)[:80])
        rows = s.scalars(q.order_by(BoardPost.created_at.desc()).limit(300)).all()
        posts = [_row(r, me) for r in rows if r.status == "shown" or (me and r.member == me and r.status != "hidden")]
    return {"on": True, "approve": c["approve"], "posts": posts[:200], "signed_in": bool(me)}


def post(p, w, body: dict[str, Any]) -> dict[str, Any]:
    c = cfg(p)
    if not c["on"]:
        raise BoardError("The members' board is not open.", 404)
    if not w.m:
        raise BoardError("Sign in to post.", 401)
    if w.m.id in (c.get("blocked") or []):
        raise BoardError("You cannot post on this board.", 403)
    text, masked = clean(str(body.get("text") or ""), bool(c.get("links")))
    if len(text) < 2:
        raise BoardError("Write a little more.", 400)
    t = time.time()
    pace = [x for x in _PACE.get(w.m.id, []) if t - x < 86400]
    if len([x for x in pace if t - x < 600]) >= 5:
        raise BoardError("You are posting fast; wait a few minutes.", 429)
    if len(pace) >= int(c.get("max_day") or 20):
        raise BoardError("That is the most posts for today; try again tomorrow.", 429)
    ensure_table()
    parent = str(body.get("parent") or "")[:40]
    topic = str(body.get("topic") or "")[:80]
    with session() as s:
        if parent:
            par = s.get(BoardPost, parent)
            if par is None or par.site != _bid(p) or par.status != "shown":
                raise BoardError("That post is not here any more.", 404)
            topic = par.topic
        row = BoardPost(site=_bid(p), topic=re.sub(r"[\x00-\x1f<>]", "", topic), parent=parent, member=w.m.id,
                        name=_first(getattr(w.m, "name", "") or ""), text=text,
                        status="waiting" if c["approve"] else "shown")
        s.add(row)
        s.flush()
        out = _row(row, w.m.id)
    _PACE[w.m.id] = pace + [t]
    if c["approve"]:
        _tell_her(p, out)
    return {**out, "masked": masked,
            "say": "Your post shows after the organisers approve it." if c["approve"] else "Posted."}


def report(p, w, body: dict[str, Any]) -> dict[str, Any]:
    if not w.m:
        raise BoardError("Sign in to report a post.", 401)
    ensure_table()
    with session() as s:
        r = s.get(BoardPost, str(body.get("id") or ""))
        if r is None or r.site != _bid(p):
            raise BoardError("That post is not here any more.", 404)
        who = json.loads(r.reporters or "[]")
        if w.m.id not in who and r.member != w.m.id:
            who.append(w.m.id)
            r.reporters, r.reports = json.dumps(who[-50:]), r.reports + 1
            if r.reports >= HIDE_AT and r.status == "shown":
                r.status = "reported"
    return {"ok": True, "say": "Thank you - the organisers will look at it."}


# ---------------------------------------------------------------- her side (and her website's staff)
def staff_view(p, w) -> dict[str, Any]:
    if not w.staff:
        raise BoardError("This is not allowed.", 403)
    ensure_table()
    with session() as s:
        rows = s.scalars(select(BoardPost).where(BoardPost.site == _bid(p)).order_by(BoardPost.created_at.desc()).limit(500)).all()
        posts = [_row(r, "", True) for r in rows]
    c = cfg(p)
    return {"cfg": c, "posts": posts, "waiting": sum(1 for x in posts if x["status"] in ("waiting", "reported"))}


def moderate(p, w, body: dict[str, Any]) -> dict[str, Any]:
    """Show / hide / delete a post, or stop its member posting (her tap, or her website's staff)."""
    if not w.staff:
        raise BoardError("This is not allowed.", 403)
    act = str(body.get("action") or "")
    if act not in ("show", "hide", "delete", "block", "unblock"):
        raise BoardError("show, hide, delete, block or unblock?", 400)
    ensure_table()
    with session() as s:
        r = s.get(BoardPost, str(body.get("id") or ""))
        if r is None or r.site != _bid(p):
            raise BoardError("That post is not here any more.", 404)
        member = r.member
        if act == "show":
            r.status = "shown"
        elif act == "hide":
            r.status = "hidden"
        elif act == "delete":
            for x in s.scalars(select(BoardPost).where(BoardPost.parent == r.id)).all():
                s.delete(x)
            s.delete(r)
    if act in ("block", "unblock"):
        from ..appmaker import backend as BE
        c = cfg(p)
        bl = [x for x in (c.get("blocked") or []) if x != member]
        if act == "block":
            bl.append(member)
        BE.patch_backend(p, set_={"board": {**c, "blocked": bl[-500:]}})
    return {"ok": True}


def _tell_her(p, row: dict[str, Any]) -> None:
    """A post waiting for her approval: one quiet line in her Hoola."""
    try:
        from . import service as S
        tenant = str(getattr(p, "tenant_id", "") or "")
        if tenant:
            S._publish(tenant, "site_board", {"post": row["id"], "topic": row.get("topic") or "",
                                              "say": "A post waits for your approval on your website's members' board "
                                                     "(Web Studio > Settings > Members' board)."})
    except Exception:                                 # noqa: BLE001 - she sees it in the Studio either way
        pass
