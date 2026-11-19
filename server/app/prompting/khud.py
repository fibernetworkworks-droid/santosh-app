"""P10 KHUD SEEKHE (self-improving): the outcome ledger changes Hoola Prompting's questions, defaults and recipes -
but only by rule, only with a measured gain, and only on a tap.

What it can propose (each from the SHAPE rows of users who share; never anyone's words):
  ask_off  - stop asking a question: results were kept about as often whether she answered it or not
             (both sides >= MIN_SIDE graded runs, rates within SAME points) - fewer questions, no loss.
  default  - pre-select an option: one of a part's own listed options was kept clearly more often than the others
             (>= MARGIN points, both sides >= MIN_SIDE) - still shown as Hoola's suggestion, she confirms it.
  recipe   - change a starter recipe's value: runs from that recipe where people picked another option were kept
             clearly more often than runs that kept the recipe's own value.
  alert    - an engine or wording change made results worse: the newest dialect / model's kept rate fell >= MARGIN
             below the one before it. An alert is information - nothing is changed by it.
Her own:   her usual choice - an option she picked in at least 3 of her last 4 prompts of that kind; offered to her,
           used only after HER tap, shown as "your usual choice".

THE RULE THE PLAN SET (P10's gate): a proposed change that does not gain is refused. `decide` re-measures at the moment
of the tap; if the gain is not there now, the accept is refused with the numbers. An owner-written change with no
evidence is refused the same way. Accepted changes can be undone.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, as_utc, new_id, now, session
from . import anatomy as A

MIN_SIDE = 8          # graded runs needed on EACH side before anything is said
MARGIN = 10           # points of kept rate that count as a real gain (or a real drop)
SAME = 5              # within this many points = "makes no difference"
DAYS = 180
KINDS = ("ask_off", "default", "recipe", "alert")
HER_DOMAIN = ("her_words", "her_answer", "her_memory", "her_default", "recipe")


class PromptChange(Base):
    """A change Hoola proposes to itself, and what happened to it."""
    __tablename__ = "prompt_changes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    kind: Mapped[str] = mapped_column(String(12), index=True)
    section: Mapped[str] = mapped_column(String(20), default="")
    slot: Mapped[str] = mapped_column(String(40), default="")
    recipe: Mapped[str] = mapped_column(String(60), default="")
    value: Mapped[str] = mapped_column(String(160), default="")
    evidence: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(12), default="proposed", index=True)   # proposed|accepted|refused|undone|dismissed
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PromptUsual(Base):
    """Her own usual choice for a part of one kind of prompt - offered, used only after her yes."""
    __tablename__ = "prompt_usual"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    section: Mapped[str] = mapped_column(String(20), default="")
    slot: Mapped[str] = mapped_column(String(40), default="")
    value: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(12), default="offered")    # offered|on|declined
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class KhudError(ValueError):
    pass


_OK: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _OK:
        PromptChange.__table__.create(eng, checkfirst=True)
        PromptUsual.__table__.create(eng, checkfirst=True)
        _OK.add(id(eng))


# ---------------------------------------------------------------- reading the ledger
def _graded(tenant: str | None = None, days: int = DAYS) -> list[Any]:
    from . import ledger as L
    return [r for r in L._rows(tenant, days) if r.grade in L.GRADES and r.grade != "unused"]


def _j(s: Any) -> dict:
    try:
        v = json.loads(s or "{}")
        return v if isinstance(v, dict) else {}
    except ValueError:
        return {}


def _rate(rows: list[Any]) -> dict[str, Any]:
    from . import ledger as L
    k = sum(1 for r in rows if r.grade in L.KEPT)
    return {"kept": k, "of": len(rows), "rate": round(100 * k / len(rows)) if rows else None}


def _filled(r: Any, slot: str) -> bool:
    return _j(r.slots).get(slot, "") in HER_DOMAIN


# ---------------------------------------------------------------- the five measurements
def measure(kind: str, section: str, slot: str = "", recipe: str = "", value: str = "",
            rows: list[Any] | None = None) -> dict[str, Any]:
    """The evidence for one change, measured now. {"gain": bool, "say": str, ...numbers}."""
    rows = [r for r in (rows if rows is not None else _graded()) if r.section == section]
    if kind == "ask_off":
        w, wo = [r for r in rows if _filled(r, slot)], [r for r in rows if not _filled(r, slot)]
        a, b = _rate(w), _rate(wo)
        enough = a["of"] >= MIN_SIDE and b["of"] >= MIN_SIDE
        gain = enough and abs(a["rate"] - b["rate"]) < SAME
        say = (f"Answered: kept {a['kept']} of {a['of']} ({a['rate']}%). Not answered: kept {b['kept']} of {b['of']} "
               f"({b['rate']}%).") if enough else f"Not enough results yet ({a['of']} answered, {b['of']} not; {MIN_SIDE} each needed)."
        return {"gain": gain, "with": a, "without": b, "say": say,
                "why_not": "" if gain else ("The answer changes how often results are kept." if enough else say)}
    if kind in ("default", "recipe"):
        if kind == "recipe":
            rows = [r for r in rows if r.recipe == recipe]
        picked = [r for r in rows if _j(r.choices).get(slot)]
        this = [r for r in picked if _j(r.choices).get(slot) == value]
        other = [r for r in picked if _j(r.choices).get(slot) != value]
        if kind == "recipe":
            base = _recipe_value(recipe, slot)
            other = [r for r in picked if _j(r.choices).get(slot) == base]
        a, b = _rate(this), _rate(other)
        enough = a["of"] >= MIN_SIDE and b["of"] >= MIN_SIDE
        gain = enough and a["rate"] - b["rate"] >= MARGIN
        against = "the recipe's own value" if kind == "recipe" else "the other choices"
        say = (f"'{value}': kept {a['kept']} of {a['of']} ({a['rate']}%). {against.capitalize()}: kept {b['kept']} of "
               f"{b['of']} ({b['rate']}%).") if enough else f"Not enough results yet ({a['of']} with '{value}', {b['of']} with {against})."
        return {"gain": gain, "with": a, "without": b, "say": say,
                "why_not": "" if gain else (f"'{value}' is not kept at least {MARGIN} points more often than {against}." if enough else say)}
    if kind == "alert":
        field = "model" if slot == "model" else "dialect"
        vals = [getattr(r, field) or "" for r in sorted(rows, key=lambda r: as_utc(r.handed_at))]
        seen = list(dict.fromkeys(v for v in vals if v))
        if len(seen) < 2:
            return {"gain": False, "say": "Only one version seen.", "why_not": "Only one version seen."}
        new, old = seen[-1], seen[-2]
        a, b = _rate([r for r in rows if getattr(r, field) == new]), _rate([r for r in rows if getattr(r, field) == old])
        enough = a["of"] >= MIN_SIDE and b["of"] >= MIN_SIDE
        drop = enough and b["rate"] - a["rate"] >= MARGIN
        say = (f"{field.capitalize()} {new}: kept {a['rate']}% of {a['of']}. Before ({old}): kept {b['rate']}% of {b['of']}."
               if enough else "Not enough results on both versions yet.")
        return {"gain": drop, "new": new, "old": old, "with": a, "without": b, "say": say,
                "why_not": "" if drop else "No real drop."}
    raise KhudError("Unknown kind of change.")


def _recipe_value(recipe_id: str, slot: str) -> str:
    from . import recipes as R
    r = next((x for x in R.RECIPES if x["id"] == recipe_id), None)
    return str((r or {}).get("slots", {}).get(slot) or "") if r else ""


# ---------------------------------------------------------------- proposing
def _key(kind: str, section: str, slot: str, recipe: str, value: str) -> tuple:
    return (kind, section, slot, recipe, value)


def scan(days: int = DAYS) -> list[dict[str, Any]]:
    """Look at the ledger and propose every change that has its gain right now. Idempotent: a change already proposed
    / accepted / dismissed is not proposed again; a refused one may come back when the numbers change."""
    ensure_table()
    rows = _graded(None, days)
    found: list[dict[str, Any]] = []
    for sec in A.ORDER:
        srows = [r for r in rows if r.section == sec]
        if len(srows) < 2 * MIN_SIDE:
            continue
        for k in A.required(sec):                                   # questions worth not asking
            m = measure("ask_off", sec, k, rows=srows)
            if m["gain"]:
                found.append({"kind": "ask_off", "section": sec, "slot": k, "recipe": "", "value": "", "m": m})
        for sl in A.slots(sec):                                     # defaults
            if not sl.get("options"):
                continue
            best = None
            for opt in sl["options"]:
                m = measure("default", sec, sl["key"], value=opt, rows=srows)
                if m["gain"] and (best is None or m["with"]["rate"] > best[1]["with"]["rate"]):
                    best = (opt, m)
            if best:
                found.append({"kind": "default", "section": sec, "slot": sl["key"], "recipe": "", "value": best[0], "m": best[1]})
        for rid in sorted({r.recipe for r in srows if r.recipe and not r.recipe.startswith("web:")}):   # recipe changes
            for sl in A.slots(sec):
                if not sl.get("options"):
                    continue
                base = _recipe_value(rid, sl["key"])
                for opt in sl["options"]:
                    if opt == base or not base:
                        continue
                    m = measure("recipe", sec, sl["key"], rid, opt, rows=srows)
                    if m["gain"]:
                        found.append({"kind": "recipe", "section": sec, "slot": sl["key"], "recipe": rid, "value": opt, "m": m})
        for field in ("dialect", "model"):                         # health alerts
            m = measure("alert", sec, field, rows=srows)
            if m["gain"]:
                found.append({"kind": "alert", "section": sec, "slot": field, "recipe": "", "value": m["new"], "m": m})
    added = []
    with session() as s:
        have = {_key(c.kind, c.section, c.slot, c.recipe, c.value): c for c in s.execute(select(PromptChange)).scalars()}
        for f in found:
            k = _key(f["kind"], f["section"], f["slot"], f["recipe"], f["value"])
            old = have.get(k)
            if old is not None and old.status in ("proposed", "accepted", "dismissed"):
                continue
            if old is not None:                                     # refused / undone before - the numbers moved again
                old.status, old.evidence, old.reason, old.decided_at = "proposed", json.dumps(f["m"]), "", None
                added.append(_view(old))
                continue
            c = PromptChange(id=new_id("pch"), kind=f["kind"], section=f["section"], slot=f["slot"], recipe=f["recipe"],
                             value=f["value"], evidence=json.dumps(f["m"]))
            s.add(c)
            s.flush()
            added.append(_view(c))
    return added


def propose(kind: str, section: str, slot: str = "", recipe: str = "", value: str = "") -> dict[str, Any]:
    """The owner writes a change herself. It is measured like any other; with no gain it is refused at once."""
    ensure_table()
    if kind not in ("ask_off", "default", "recipe"):
        raise KhudError("Only questions, defaults and recipe values can be changed here.")
    if section not in A.SECTIONS or (slot and not A.slot(section, slot)):
        raise KhudError("Unknown kind of prompt or part.")
    if kind in ("default", "recipe"):
        sl = A.slot(section, slot)
        if not sl or value not in (sl.get("options") or []):
            raise KhudError("Choose one of that part's own options.")
    m = measure(kind, section, slot, recipe, value)
    with session() as s:
        c = PromptChange(id=new_id("pch"), kind=kind, section=section, slot=slot, recipe=recipe[:60], value=value[:160],
                         evidence=json.dumps(m), status="proposed" if m["gain"] else "refused",
                         reason="" if m["gain"] else "No gain shown: " + m["why_not"],
                         decided_at=None if m["gain"] else now())
        s.add(c)
        s.flush()
        return _view(c)


def _view(c: PromptChange) -> dict[str, Any]:
    ev = _j(c.evidence)
    sec = A.SECTIONS.get(c.section, {})
    lab = (A.slot(c.section, c.slot) or {}).get("label", c.slot) if c.section in A.SECTIONS else c.slot
    what = {"ask_off": f"Stop asking for '{lab}' in {sec.get('label', c.section)} prompts",
            "default": f"Pre-select '{c.value}' for '{lab}' in {sec.get('label', c.section)} prompts",
            "recipe": f"In the recipe '{c.recipe}', use '{c.value}' for '{lab}'",
            "alert": f"{sec.get('label', c.section)} results got worse after the {c.slot} changed to {c.value}"}.get(c.kind, c.kind)
    return {"id": c.id, "kind": c.kind, "section": c.section, "slot": c.slot, "recipe": c.recipe, "value": c.value,
            "what": what, "evidence": ev.get("say", ""), "status": c.status, "reason": c.reason,
            "at": as_utc(c.created_at).isoformat() if c.created_at else None}


def listing(status: str = "") -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        q = select(PromptChange).order_by(PromptChange.created_at.desc()).limit(200)
        return [_view(c) for c in s.execute(q).scalars() if not status or c.status == status]


def decide(cid: str, action: str) -> dict[str, Any]:
    """The owner's tap: accept (re-measured now - no gain = refused), refuse, dismiss (an alert she has seen), undo."""
    ensure_table()
    with session() as s:
        c = s.get(PromptChange, cid)
        if c is None:
            raise KeyError(cid)
        if action == "accept":
            if c.kind == "alert":
                raise KhudError("An alert changes nothing - mark it seen instead.")
            if c.status != "proposed":
                raise KhudError("Only a proposed change can be accepted.")
            m = measure(c.kind, c.section, c.slot, c.recipe, c.value)
            c.evidence = json.dumps(m)
            if not m["gain"]:
                c.status, c.reason = "refused", "No gain shown when it was checked again: " + m["why_not"]
            else:
                c.status = "accepted"
        elif action == "refuse":
            c.status, c.reason = "refused", "Refused by the owner."
        elif action == "dismiss":
            c.status = "dismissed"
        elif action == "undo":
            if c.status != "accepted":
                raise KhudError("Only an accepted change can be undone.")
            c.status = "undone"
        else:
            raise KhudError("accept, refuse, dismiss or undo")
        c.decided_at = now()
        _CACHE.clear()
        return _view(c)


# ---------------------------------------------------------------- what the rest of Prompting reads
_CACHE: dict[str, Any] = {}


def _accepted() -> list[PromptChange]:
    if "rows" not in _CACHE:
        try:
            ensure_table()
            with session() as s:
                rows = list(s.execute(select(PromptChange).where(PromptChange.status == "accepted")).scalars())
                s.expunge_all()
            _CACHE["rows"] = rows
        except Exception:       # noqa: BLE001 - a missing table never breaks a prompt
            _CACHE["rows"] = []
    return _CACHE["rows"]


def asked_off(section: str) -> set[str]:
    return {c.slot for c in _accepted() if c.kind == "ask_off" and c.section == section}


def default_for(section: str) -> dict[str, str]:
    return {c.slot: c.value for c in _accepted() if c.kind == "default" and c.section == section}


def recipe_values(recipe_id: str) -> dict[str, str]:
    return {c.slot: c.value for c in _accepted() if c.kind == "recipe" and c.recipe == recipe_id}


# ---------------------------------------------------------------- her own usual choices
def usual_scan(tenant: str) -> list[dict[str, Any]]:
    """Options she picked in at least 3 of her last 4 prompts of a kind - offered once each."""
    ensure_table()
    from . import ledger as L
    rows = L._rows(tenant, 365)
    found = []
    for sec in A.ORDER:
        mine = [r for r in rows if r.section == sec][:4]
        if len(mine) < 3:
            continue
        for sl in A.slots(sec):
            if not sl.get("options"):
                continue
            picks = [_j(r.choices).get(sl["key"]) for r in mine]
            for opt in sl["options"]:
                if sum(1 for p in picks if p == opt) >= 3:
                    found.append((sec, sl["key"], opt))
    out = []
    with session() as s:
        have = {(u.section, u.slot): u for u in s.execute(select(PromptUsual).where(PromptUsual.tenant_id == tenant)).scalars()}
        for sec, slot, opt in found:
            u = have.get((sec, slot))
            if u is not None and (u.value == opt or u.status == "on"):
                continue                                            # already offered / declined / her standing choice
            if u is None:
                u = PromptUsual(id=new_id("pus"), tenant_id=tenant, section=sec, slot=slot)
                s.add(u)
            u.value, u.status = opt, "offered"
            s.flush()
            out.append(_uview(u))
    return out


def _uview(u: PromptUsual) -> dict[str, Any]:
    lab = (A.slot(u.section, u.slot) or {}).get("label", u.slot) if u.section in A.SECTIONS else u.slot
    return {"id": u.id, "section": u.section, "slot": u.slot, "value": u.value, "status": u.status,
            "what": f"Always start {A.SECTIONS.get(u.section, {}).get('label', u.section)} prompts with '{lab}': {u.value}"}


def usuals(tenant: str) -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        return [_uview(u) for u in s.execute(select(PromptUsual).where(PromptUsual.tenant_id == tenant)).scalars()]


def usual_decide(tenant: str, uid: str, on: bool) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        u = s.get(PromptUsual, uid)
        if u is None or u.tenant_id != tenant:
            raise KeyError(uid)
        u.status = "on" if on else "declined"
        return _uview(u)


def her_usual(tenant: str, section: str) -> dict[str, str]:
    try:
        ensure_table()
        with session() as s:
            return {u.slot: u.value for u in s.execute(select(PromptUsual).where(
                PromptUsual.tenant_id == tenant, PromptUsual.section == section, PromptUsual.status == "on")).scalars()}
    except Exception:       # noqa: BLE001
        return {}
