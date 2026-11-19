"""P11 SAMUDAAY (docs/HOOLA_PROMPTING_PLAN.md part 9 + part 12 decision 5): recipes written by users, for everyone.

OFF until the owner switches it on (`prompting_community`); the plan says community opens only after the ledger has real
numbers, and that is her call. While it is off nothing can be submitted and nothing is listed.

The road, every step a person's tap:
  1. A user offers one of her SAVED prompts as a recipe (submit). It is screened at once (the share screen: hidden
     instructions, secret asks, links, send-without-asking) and refused if it carries a phone number, an e-mail address
     or her business memory - a recipe must not leak who she is. What she typed that is hers becomes a blank.
  2. The owner reads it in the review list and approves or refuses it (owner only).
  3. An approved recipe sits on the Recipes shelf (and on the public /prompts pages) under the name the writer chose,
     never her account. Every use is screened again.
  4. Pay-on-kept, as the plan proposes: each use goes into the outcome ledger under recipe `com:<id>`, so a writer sees
     how often results from her recipe were kept. NO money is paid by Hoola here - paying writers is a later decision
     of the owner's; the count is only recorded."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, as_utc, new_id, now, session
from . import anatomy as A

PREFIX = "com:"
STATES = ("submitted", "approved", "refused", "withdrawn")
MAX_OPEN = 10                        # a writer's recipes waiting for review at once


class CommunityRecipe(Base):
    __tablename__ = "prompt_community"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    section: Mapped[str] = mapped_column(String(20), default="")
    title: Mapped[str] = mapped_column(String(120), default="")
    makes: Mapped[str] = mapped_column(String(200), default="")
    by: Mapped[str] = mapped_column(String(60), default="")
    brief: Mapped[str] = mapped_column(Text, default="{}")
    blanks: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(12), default="submitted", index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommunityError(ValueError):
    pass


_OK: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _OK:
        CommunityRecipe.__table__.create(eng, checkfirst=True)
        _OK.add(id(eng))


def on() -> bool:
    from ..config import get_settings
    return bool(getattr(get_settings(), "prompting_community", False))


def _need_on() -> None:
    if not on():
        raise CommunityError("Community recipes are switched off.")


_PERSONAL = [(re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"), "a phone number"),
             (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "an e-mail address"),
             (re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"), "a GSTIN")]


def _text_of(brief: dict[str, Any]) -> str:
    return " ".join([str(brief.get("intent") or "")] + [str((v or {}).get("value") or "")
                                                        for v in (brief.get("slots") or {}).values()])


def problems(brief: dict[str, Any]) -> list[str]:
    """Why a recipe cannot go to everyone (empty = clean)."""
    from . import store as S
    out = list(S.screen(brief))
    text = _text_of(brief)
    out += [f"it carries {what}" for rx, what in _PERSONAL if rx.search(text)]
    return list(dict.fromkeys(out))


def _as_recipe(brief: dict[str, Any]) -> dict[str, Any]:
    """Her saved brief -> a recipe brief: parts from her business memory dropped (they are who she is), every kept part
    marked as the recipe's."""
    slots = {}
    for k, v in (brief.get("slots") or {}).items():
        if not isinstance(v, dict) or v.get("source") in ("her_memory", "her_default"):
            continue
        slots[k] = {"value": str(v.get("value") or ""), "source": "recipe"}
    return {"section": brief["section"], "intent": str(brief.get("intent") or ""), "slots": slots}


def _view(r: CommunityRecipe, rates: dict | None = None, full: bool = False) -> dict[str, Any]:
    rid = PREFIX + r.id
    out = {"id": rid, "section": r.section, "title": r.title, "makes": r.makes, "by": r.by or "A Hoola user",
           "blanks": json.loads(r.blanks or "[]"), "starter": False, "community": True, "status": r.status,
           "reason": r.reason, "at": as_utc(r.created_at).isoformat() if r.created_at else None}
    if rates and rid in rates:
        out["kept"] = rates[rid]
    if full:
        out["brief"] = json.loads(r.brief or "{}")
    return out


def submit(tenant: str, saved_id: str, title: str = "", makes: str = "", by: str = "") -> dict[str, Any]:
    _need_on()
    ensure_table()
    from . import brief as B
    from . import store as S
    p = S.get(tenant, saved_id)
    if not p:
        raise KeyError(saved_id)
    rec = _as_recipe(p.get("brief") or {})
    rec = B.validate(rec)
    bad = problems(rec)
    if bad:
        raise CommunityError("This prompt cannot be offered to everyone: " + "; ".join(bad) + ".")
    with session() as s:
        open_n = sum(1 for _ in s.execute(select(CommunityRecipe.id).where(
            CommunityRecipe.tenant_id == tenant, CommunityRecipe.status == "submitted")))
        if open_n >= MAX_OPEN:
            raise CommunityError(f"You already have {MAX_OPEN} recipes waiting for review.")
        c = CommunityRecipe(id=new_id("pcr"), tenant_id=tenant, section=rec["section"],
                            title=(title or p.get("title") or A.SECTIONS[rec["section"]]["label"])[:120],
                            makes=(makes or A.SECTIONS[rec["section"]]["makes"])[:200], by=(by or "").strip()[:60],
                            brief=json.dumps(rec), blanks="[]")
        s.add(c)
        s.flush()
        return _view(c, full=True)


def mine(tenant: str) -> list[dict[str, Any]]:
    ensure_table()
    rates = _rates()
    with session() as s:
        q = select(CommunityRecipe).where(CommunityRecipe.tenant_id == tenant).order_by(CommunityRecipe.created_at.desc())
        return [_view(c, rates) for c in s.execute(q).scalars()]


def withdraw(tenant: str, cid: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        c = s.get(CommunityRecipe, cid.removeprefix(PREFIX))
        if c is None or c.tenant_id != tenant:
            raise KeyError(cid)
        c.status, c.decided_at = "withdrawn", now()
        return _view(c)


def review_list() -> list[dict[str, Any]]:
    """The owner's queue: everything waiting, with what a reader would see."""
    ensure_table()
    with session() as s:
        q = select(CommunityRecipe).where(CommunityRecipe.status == "submitted").order_by(CommunityRecipe.created_at)
        out = []
        for c in s.execute(q).scalars():
            v = _view(c, full=True)
            v["problems"] = problems(v["brief"])
            out.append(v)
        return out


def decide(cid: str, action: str, reason: str = "") -> dict[str, Any]:
    """The owner's tap. Approving screens again; a recipe that fails the screen now cannot be approved."""
    ensure_table()
    if action not in ("approve", "refuse"):
        raise CommunityError("approve or refuse")
    with session() as s:
        c = s.get(CommunityRecipe, cid.removeprefix(PREFIX))
        if c is None:
            raise KeyError(cid)
        if c.status != "submitted":
            raise CommunityError("Only a recipe waiting for review can be decided.")
        if action == "approve":
            bad = problems(json.loads(c.brief or "{}"))
            if bad:
                raise CommunityError("It cannot be approved: " + "; ".join(bad) + ".")
            c.status, c.reason = "approved", ""
        else:
            c.status, c.reason = "refused", (reason or "Refused by Hoola.")[:300]
        c.decided_at = now()
        return _view(c)


def _rates() -> dict[str, dict[str, int]]:
    try:
        from . import ledger as L
        return {k: v for k, v in L.recipe_rates().items() if k.startswith(PREFIX)}
    except Exception:       # noqa: BLE001
        return {}


def listing(section: str = "", q: str = "") -> list[dict[str, Any]]:
    """Approved recipes for the shelf (empty while the switch is off)."""
    if not on():
        return []
    ensure_table()
    words = [w for w in (q or "").lower().split() if w]
    rates = _rates()
    with session() as s:
        qq = select(CommunityRecipe).where(CommunityRecipe.status == "approved")
        out = []
        for c in s.execute(qq).scalars():
            if section and c.section != section:
                continue
            hay = (c.title + " " + c.makes).lower()
            if all(w in hay for w in words):
                out.append(_view(c, rates))
        return out


def get(cid: str) -> dict[str, Any] | None:
    if not on():
        return None
    ensure_table()
    with session() as s:
        c = s.get(CommunityRecipe, cid.removeprefix(PREFIX))
        return _view(c, _rates(), full=True) if c is not None and c.status == "approved" else None


def use(cid: str) -> dict[str, Any]:
    """An approved recipe -> a brief in the user's workbench (screened again; the ledger sees recipe `com:<id>`)."""
    from . import brief as B
    r = get(cid)
    if r is None:
        raise KeyError(cid)
    bad = problems(r["brief"])
    if bad:
        raise CommunityError("This recipe cannot be used: " + "; ".join(bad) + ".")
    raw = dict(r["brief"])
    raw["recipe_id"] = r["id"]
    return {"brief": B.validate(raw)}
