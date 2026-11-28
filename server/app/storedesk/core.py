"""The Material Store's core: settings, stores, items and their units, lots, and the movement ledger.

Stock is never a number someone types: it is what the ledger says came into a place minus what left it. A place is (store, position,
holder); positions are hold (received, waiting for quality), available, blocked (rejected, waiting to go back), transit (between
stores), holder (free-issue material a subcontractor holds - still the company's) - and the outside world: outside (suppliers), used
(went into the work), vendor (returned), scrap, adjust (a count difference a person approved). Every movement is a row; a mistake is
a counter-row with the approver's name, never an edit."""
from __future__ import annotations

import logging
import math
import re
import threading
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from statistics import pstdev
from typing import Any, Iterable

from sqlalchemy import func, select

from ..db import new_id, now, session
from . import packs as P
from .models import ALL, SdDoc, SdHolder, SdItem, SdLot, SdMove, SdSettings, SdStore  # noqa: F401

log = logging.getLogger("santosh.storedesk")
LOCK = threading.RLock()

INSIDE = ("hold", "available", "blocked", "transit", "holder")        # still the company's stock
OUTSIDE = ("outside", "used", "vendor", "scrap", "adjust")
VALUED = ("hold", "available", "blocked", "transit")   # free-issue material is charged to the work when it is issued; the holder ledger tracks it
CATEGORIES = ("bulk", "consumable", "tool", "client")
TRACE = ("none", "batch", "heat", "serial")
CURRENCIES = re.compile(r"^[A-Z]{3}$")
FIELDS = ("company", "project", "country", "currency", "units", "valuation", "gaap", "language", "tolerance", "receive_tol", "wastage",
          "tiers", "count_days", "lead_days", "service_z", "stale_days", "transit_days", "hold_days", "overdue_days", "packs_off")
DEFAULT_TIERS = [[2000, "Store in-charge"], [20000, "Project manager"], [None, "Finance"]]
DEFAULT_COUNT = {"A": 30, "B": 90, "C": 180}


class StoreError(ValueError):
    pass


_READY: set[int] = set()


def tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    for m in ALL:
        m.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


def today(tenant: str) -> date:
    try:
        from ..life import tz_of
        return datetime.now(tz_of(tenant)).date()
    except Exception:   # noqa: BLE001
        return datetime.now(timezone.utc).date()


def _day(v: Any, tenant: str) -> str:
    if not v:
        return today(tenant).isoformat()
    try:
        return date.fromisoformat(str(v)[:10]).isoformat()
    except ValueError:
        raise StoreError(f"Date '{v}': write it as YYYY-MM-DD.")


def num(v: Any, name: str = "Quantity", allow_zero: bool = False, allow_neg: bool = False) -> float:
    if v is None or v == "":
        raise StoreError(f"{name}: give a number.")
    try:
        x = float(str(v).replace(",", "").strip()) if not isinstance(v, (int, float)) else float(v)
    except ValueError:
        raise StoreError(f"{name}: '{v}' is not a number.")
    if math.isnan(x) or math.isinf(x):
        raise StoreError(f"{name}: not a number.")
    if not allow_neg and x < 0:
        raise StoreError(f"{name}: cannot be below zero.")
    if not allow_zero and x == 0 and not allow_neg:
        raise StoreError(f"{name}: must be more than zero.")
    return x


def S(v: Any, n: int = 200) -> str:
    return ("" if v is None else str(v)).strip()[:n]


# ---------------------------------------------------------------- settings
def settings(tenant: str) -> dict[str, Any]:
    tables()
    with session() as s:
        r = s.get(SdSettings, tenant)
        d = {k: (getattr(r, k) if r else None) for k in FIELDS}
    d["set"] = r is not None
    defaults = {"company": "", "project": "", "country": "", "currency": "USD", "units": "metric", "valuation": "wavg", "gaap": "ifrs",
                "language": "en", "tolerance": 2.0, "receive_tol": 2.0, "wastage": 3.0, "tiers": DEFAULT_TIERS, "count_days": DEFAULT_COUNT,
                "lead_days": 7, "service_z": 1.65, "stale_days": 45, "transit_days": 2, "hold_days": 3, "overdue_days": 1, "packs_off": []}
    for k, v in defaults.items():
        if d.get(k) in (None, "", [], {}) and not (k in ("company", "project", "country") and d.get(k) == ""):
            d[k] = v
    d["pack"] = P.pack(d["country"])
    return d


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    tables()
    clean: dict[str, Any] = {}
    for k, v in f.items():
        if k not in FIELDS or v is None:
            continue
        if k in ("company", "project"):
            clean[k] = S(v, 120)
        elif k == "country":
            c = S(v, 4).upper()
            if c and not re.fullmatch(r"[A-Z]{2}", c):
                raise StoreError("Country: the two-letter code, like AE, IN, GB, US, KE.")
            clean[k] = c
        elif k == "currency":
            c = S(v, 10).upper()
            if not CURRENCIES.match(c):
                raise StoreError("Currency: the three-letter code, like AED, INR, GBP, USD, EUR.")
            clean[k] = c
        elif k == "units":
            if v not in ("metric", "imperial"):
                raise StoreError("Units: metric or imperial.")
            clean[k] = v
        elif k == "gaap":
            if v not in ("ifrs", "usgaap", "local"):
                raise StoreError("Accounting rules: IFRS, US GAAP or local.")
            clean[k] = v
        elif k == "valuation":
            if v not in ("fifo", "wavg", "lifo"):
                raise StoreError("Valuation: FIFO, weighted average or LIFO.")
            clean[k] = v
        elif k == "language":
            clean[k] = S(v, 10) or "en"
        elif k in ("tolerance", "receive_tol", "wastage"):
            x = num(v, k, allow_zero=True)
            if x > 50:
                raise StoreError(f"{k}: at most 50%.")
            clean[k] = x
        elif k in ("lead_days", "stale_days", "transit_days", "hold_days", "overdue_days"):
            x = int(num(v, k, allow_zero=True))
            if x > 3650:
                raise StoreError(f"{k}: at most 3650 days.")
            clean[k] = x
        elif k == "service_z":
            x = num(v, "Safety factor", allow_zero=True)
            if x > 4:
                raise StoreError("Safety factor: 0 to 4 (1.65 covers about 95% of days).")
            clean[k] = x
        elif k == "tiers":
            clean[k] = _tiers(v)
        elif k == "count_days":
            if not isinstance(v, dict):
                raise StoreError("Count plan: days for A, B and C.")
            clean[k] = {c: int(num(v.get(c, DEFAULT_COUNT[c]), f"Days for class {c}")) for c in "ABC"}
        elif k == "packs_off":
            clean[k] = [S(x, 40) for x in (v or [])][:50]
    cur = settings(tenant)
    val = clean.get("valuation", cur["valuation"])
    gaap = clean.get("gaap", cur["gaap"])
    if val == "lifo" and gaap != "usgaap":
        raise StoreError("LIFO is not allowed under IFRS (IAS 2). Choose FIFO or weighted average, or set US GAAP if that is what your books follow.")
    with LOCK, session() as s:
        r = s.get(SdSettings, tenant)
        if r is None:
            r = SdSettings(tenant_id=tenant)
            s.add(r)
            for k, v in (("tiers", DEFAULT_TIERS), ("count_days", DEFAULT_COUNT), ("packs_off", []), ("legacy_done", {})):
                setattr(r, k, v)
        for k, v in clean.items():
            setattr(r, k, v)
        r.updated_at = now()
    out = settings(tenant)
    out["say"] = "Settings saved."
    return out


def _tiers(v: Any) -> list[list[Any]]:
    if not isinstance(v, list) or not v:
        raise StoreError("Approval tiers: a list of [up to this value, who approves], the last one for anything above.")
    out = []
    for row in v[:6]:
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            raise StoreError("Each approval tier: [up to this value, who approves].")
        lim = None if row[0] in (None, "", "above") else num(row[0], "Tier limit")
        who = S(row[1], 60)
        if not who:
            raise StoreError("Each approval tier needs who approves.")
        out.append([lim, who])
    if out[-1][0] is not None:
        out.append([None, out[-1][1]])
    return out


def tier_for(tenant: str, value: float) -> dict[str, Any]:
    tiers = settings(tenant)["tiers"]
    for i, (lim, who) in enumerate(tiers):
        if lim is None or abs(value) <= float(lim):
            return {"tier": i + 1, "who": who, "limit": lim}
    return {"tier": len(tiers), "who": tiers[-1][1], "limit": None}


# ---------------------------------------------------------------- stores
def stores(tenant: str, all_: bool = False) -> list[dict[str, Any]]:
    tables()
    with session() as s:
        rows = s.scalars(select(SdStore).where(SdStore.tenant_id == tenant).order_by(SdStore.created_at)).all()
        return [{"id": r.id, "name": r.name, "project": r.project, "kind": r.kind, "active": r.active} for r in rows if all_ or r.active]


def save_store(tenant: str, name: str, project: str = "", kind: str = "main", id: str = "", active: bool | None = None) -> dict[str, Any]:
    tables()
    name = S(name, 80)
    if not name and not id:
        raise StoreError("Give the store a name, like 'Main store' or 'Yard 2'.")
    if kind not in ("main", "yard", "sub", "container"):
        raise StoreError("Store kind: main, yard, sub or container.")
    with LOCK, session() as s:
        if id:
            r = s.get(SdStore, id)
            if r is None or r.tenant_id != tenant:
                raise StoreError("That store is not yours.")
        else:
            if any(x.name.lower() == name.lower() for x in s.scalars(select(SdStore).where(SdStore.tenant_id == tenant)).all()):
                raise StoreError(f"There is already a store called '{name}'.")
            r = SdStore(tenant_id=tenant)
            s.add(r)
        if name:
            r.name = name
        r.project = S(project, 120) or r.project or ""
        r.kind = kind
        if active is not None:
            r.active = bool(active)
        s.flush()
        return {"id": r.id, "name": r.name, "project": r.project, "kind": r.kind, "active": r.active, "say": f"Store '{r.name}' saved."}


def store_id(s, tenant: str, ref: str = "") -> str:
    ref = S(ref, 80)
    rows = s.scalars(select(SdStore).where(SdStore.tenant_id == tenant).order_by(SdStore.created_at)).all()
    if not ref:
        act = [r for r in rows if r.active]
        if act:
            return act[0].id
        r = SdStore(tenant_id=tenant, name="Main store", kind="main")
        s.add(r)
        s.flush()
        return r.id
    for r in rows:
        if r.id == ref or r.name.lower() == ref.lower():
            return r.id
    hits = [r for r in rows if ref.lower() in r.name.lower()]
    if len(hits) == 1:
        return hits[0].id
    raise StoreError(f"No store called '{ref}'. Stores: " + (", ".join(r.name for r in rows) or "none yet") + ".")


def store_names(s, tenant: str) -> dict[str, str]:
    return {r.id: r.name for r in s.scalars(select(SdStore).where(SdStore.tenant_id == tenant)).all()}


# ---------------------------------------------------------------- items and units
ITEM_FIELDS = ("code", "name", "category", "unit", "conv", "cls", "critical", "min_qty", "max_qty", "lead_days", "shelf_days", "trace",
               "inspect", "tol_pct", "wastage", "mass_per_m", "mass_src", "max_minutes", "price", "note", "active")


def item_view(r: SdItem) -> dict[str, Any]:
    return {k: getattr(r, k) for k in ITEM_FIELDS} | {"id": r.id}


def items(tenant: str, all_: bool = False) -> list[dict[str, Any]]:
    tables()
    with session() as s:
        return [item_view(r) for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant).order_by(SdItem.name)).all() if all_ or r.active]


def find_item(s, tenant: str, ref: str) -> SdItem:
    ref = S(ref, 120)
    if not ref:
        raise StoreError("Which item? Give its name or code.")
    rows = s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()
    for r in rows:
        if r.id == ref or (r.code and r.code.lower() == ref.lower()) or r.name.lower() == ref.lower():
            return r
    low = ref.lower()
    hits = [r for r in rows if low in r.name.lower() and r.active]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise StoreError(f"'{ref}' matches several items: " + ", ".join(h.name for h in hits[:8]) + ". Say which one.")
    raise StoreError(f"No item called '{ref}' in the store yet. Add it first (name, unit).")


def save_item(tenant: str, **f: Any) -> dict[str, Any]:
    tables()
    with LOCK, session() as s:
        r = None
        if f.get("id"):
            r = s.get(SdItem, S(f["id"], 40))
            if r is None or r.tenant_id != tenant:
                raise StoreError("That item is not yours.")
        name = S(f.get("name"), 120)
        if r is None:
            if not name:
                raise StoreError("Give the item a name, like 'Cement CEM I 42.5N'.")
            if any(x.name.lower() == name.lower() for x in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()):
                raise StoreError(f"'{name}' is already an item.")
            r = SdItem(tenant_id=tenant, name=name, conv={}, docs=[])
            s.add(r)
        for k in ITEM_FIELDS:
            if k not in f or f[k] is None or k == "id":
                continue
            v = f[k]
            if k in ("code", "name", "note", "mass_src"):
                setattr(r, k, S(v, 300 if k in ("note", "mass_src") else 120))
            elif k == "unit":
                u = S(v, 12).lower()
                if not u:
                    raise StoreError("Give the item's base unit, like kg, t, bag, m3, no.")
                setattr(r, k, u)
            elif k == "category":
                if v not in CATEGORIES:
                    raise StoreError("Category: bulk, consumable, tool (returnable) or client (client-supplied).")
                r.category = v
            elif k == "trace":
                if v not in TRACE:
                    raise StoreError("Traceability: none, batch, heat (heat number + certificate) or serial.")
                r.trace = v
            elif k == "cls":
                c = S(v, 2).upper()
                if c not in ("", "A", "B", "C"):
                    raise StoreError("Class: A, B, C or empty for worked out.")
                r.cls = c
            elif k in ("critical", "inspect", "active"):
                setattr(r, k, bool(v))
            elif k == "conv":
                if not isinstance(v, dict):
                    raise StoreError("Units: {'bag': 50} means 1 bag is 50 of the base unit.")
                r.conv = {S(a, 12).lower(): num(b, f"How many {r.unit} in 1 {a}") for a, b in v.items() if S(a, 12)}
            elif k in ("tol_pct", "wastage"):
                x = -1.0 if v in ("", -1, "-1") else num(v, k, allow_zero=True)
                if x > 50:
                    raise StoreError(f"{k}: at most 50%.")
                setattr(r, k, x)
            elif k in ("lead_days", "shelf_days", "max_minutes"):
                setattr(r, k, int(num(v, k, allow_zero=True)))
            else:
                setattr(r, k, num(v, k, allow_zero=True))
        if r.trace == "heat" and not r.inspect:
            r.inspect = True                       # a heat without its certificate waits for the QC engineer
        s.flush()
        d = item_view(r)
    d["say"] = f"Item '{d['name']}' saved ({d['unit']})."
    return d


def to_base(it: SdItem, qty: Any, unit: str = "") -> tuple[float, float, str]:
    q = num(qty)
    u = S(unit, 12).lower()
    if not u or u == it.unit:
        return q, q, it.unit
    if u in (it.conv or {}):
        return q * float(it.conv[u]), q, u
    std = P.UNITS.get(it.unit, {})
    if u in std:
        return q * std[u], q, u
    raise StoreError(f"'{unit}' is not a unit for {it.name}. Its base unit is {it.unit}" +
                     (f"; it also takes {', '.join(sorted(it.conv))}" if it.conv else "") + ". Add the conversion in the item.")


def show_qty(it: SdItem | dict, q: float) -> str:
    unit = it.unit if isinstance(it, SdItem) else it["unit"]
    r = round(q, 3)
    return f"{r:,.3f}".rstrip("0").rstrip(".") + f" {unit}"


# ---------------------------------------------------------------- the ledger
def _seq(s, tenant: str) -> int:
    return int(s.scalar(select(func.max(SdMove.seq)).where(SdMove.tenant_id == tenant)) or 0) + 1


def post(s, tenant: str, kind: str, it: SdItem, qty: float, frm: tuple[str, str], to: tuple[str, str], *, lot: str = "",
         holder: str = "", work: str = "", cost: float | None = None, doc: dict | None = None, who: str = "", approver: str = "",
         note: str = "", day: str = "", qty_in: float | None = None, unit_in: str = "", reverses: str = "") -> SdMove:
    if qty <= 0:
        raise StoreError("A movement needs a quantity above zero.")
    if frm[1] in INSIDE:
        have = balance(s, tenant, it.id, store=frm[0], pos=frm[1], lot=lot or None, holder=holder if frm[1] == "holder" else None)
        if have + 1e-9 < qty:
            where = {"available": "available", "hold": "on hold", "blocked": "blocked", "transit": "in transit", "holder": f"with {holder}"}[frm[1]]
            raise StoreError(f"{it.name}: only {show_qty(it, have)} {where} there, not {show_qty(it, qty)}.")
    m = SdMove(id=new_id("smv"), seq=_seq(s, tenant), tenant_id=tenant, kind=kind, item_id=it.id, lot_id=lot or "", qty=round(qty, 6),
               qty_in=qty if qty_in is None else qty_in, unit_in=unit_in or it.unit, from_store=frm[0] or "", from_pos=frm[1],
               to_store=to[0] or "", to_pos=to[1], holder=S(holder, 120), work=S(work, 80), cost=float(cost if cost is not None else (it.price or 0)),
               doc=doc or {}, who=S(who, 80), approver=S(approver, 80), note=S(note, 300), day=day or "", reverses=reverses or "")
    s.add(m)
    s.flush()
    return m


def balances(s, tenant: str, item_ids: Iterable[str] | None = None) -> dict[tuple[str, str, str, str, str], float]:
    """(item, lot, store, pos, holder) -> quantity, for every inside position."""
    out: dict[tuple, float] = defaultdict(float)
    ids = list(item_ids) if item_ids is not None else None
    for side, sign in (("to", 1), ("from", -1)):
        st, ps = getattr(SdMove, f"{side}_store"), getattr(SdMove, f"{side}_pos")
        q = select(SdMove.item_id, SdMove.lot_id, st, ps, SdMove.holder, func.sum(SdMove.qty)).where(SdMove.tenant_id == tenant, ps.in_(INSIDE))
        if ids is not None:
            q = q.where(SdMove.item_id.in_(ids))
        for item, lot, store, pos, holder, qty in s.execute(q.group_by(SdMove.item_id, SdMove.lot_id, st, ps, SdMove.holder)).all():
            out[(item, lot or "", store or "", pos, holder if pos == "holder" else "")] += sign * float(qty or 0)
    return {k: round(v, 6) for k, v in out.items() if abs(v) > 1e-9}


def balance(s, tenant: str, item_id: str, store: str | None = None, pos: str | None = None, lot: str | None = None,
            holder: str | None = None) -> float:
    t = 0.0
    for (i, l, st, p, h), q in balances(s, tenant, [item_id]).items():
        if (store is None or st == store) and (pos is None or p == pos) and (lot is None or l == lot) and (holder is None or h == holder):
            t += q
    return round(t, 6)


def lots_fifo(s, tenant: str, it: SdItem, store: str, pos: str, qty: float, holder: str = "") -> list[tuple[str, float]]:
    """Oldest lots first (the day they came in, then the order they were made)."""
    bal = balances(s, tenant, [it.id])
    have = {l: q for (i, l, st, p, h), q in bal.items() if st == store and p == pos and (pos != "holder" or h == holder) and q > 1e-9}
    if sum(have.values()) + 1e-9 < qty:
        raise StoreError(f"{it.name}: only {show_qty(it, sum(have.values()))} {pos} there, not {show_qty(it, qty)}.")
    meta = {r.id: (r.received or "", r.created_at.isoformat() if r.created_at else "") for r in
            s.scalars(select(SdLot).where(SdLot.id.in_([l for l in have if l]))).all()} if any(have) else {}
    order = sorted(have, key=lambda l: meta.get(l, ("", "")) if l else ("", ""))
    out, left = [], qty
    for l in order:
        take = min(have[l], left)
        if take > 1e-9:
            out.append((l, round(take, 6)))
            left -= take
        if left <= 1e-9:
            break
    return out


def lot_cost(s, lot: str, it: SdItem) -> float:
    if lot:
        r = s.get(SdLot, lot)
        if r is not None and r.cost:
            return r.cost
    return it.price or 0.0


def reverse(tenant: str, move_id: str, approver: str, reason: str) -> dict[str, Any]:
    """A mistake gets a counter-row with the approver's name; the original stays."""
    tables()
    approver, reason = S(approver, 80), S(reason, 300)
    if not approver:
        raise StoreError("A reversal needs the name of the person who approves it.")
    if not reason:
        raise StoreError("Say why it is being reversed.")
    with LOCK, session() as s:
        m = s.get(SdMove, move_id)
        if m is None or m.tenant_id != tenant:
            raise StoreError("That movement is not yours.")
        if m.reversed_by:
            raise StoreError("That movement was already reversed.")
        if m.kind == "reverse":
            raise StoreError("A reversal cannot itself be reversed: record the right movement instead.")
        it = s.get(SdItem, m.item_id)
        r = post(s, tenant, "reverse", it, m.qty, (m.to_store, m.to_pos), (m.from_store, m.from_pos), lot=m.lot_id, holder=m.holder,
                 work=m.work, cost=m.cost, doc={"reverses": m.id, **(m.doc or {})}, who=approver, approver=approver,
                 note=reason, day=today(tenant).isoformat(), reverses=m.id)
        m.reversed_by = r.id
        return {"id": r.id, "say": f"Reversed: {it.name} {show_qty(it, m.qty)} ({m.kind}) - approved by {approver}."}


def ledger(tenant: str, item: str = "", store: str = "", limit: int = 200) -> list[dict[str, Any]]:
    tables()
    with session() as s:
        q = select(SdMove).where(SdMove.tenant_id == tenant)
        it = None
        if item:
            it = find_item(s, tenant, item)
            q = q.where(SdMove.item_id == it.id)
        rows = s.scalars(q.order_by(SdMove.seq.desc()).limit(max(1, min(int(limit), 2000)))).all()
        names = store_names(s, tenant)
        its = {r.id: r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()}
        lots = {r.id: r.ref for r in s.scalars(select(SdLot).where(SdLot.id.in_([m.lot_id for m in rows if m.lot_id]))).all()} if rows else {}
        sid = store_id(s, tenant, store) if store else ""
        out = []
        for m in rows:
            if sid and sid not in (m.from_store, m.to_store):
                continue
            i = its.get(m.item_id)
            out.append({"id": m.id, "seq": m.seq, "kind": m.kind, "item": i.name if i else "?", "unit": i.unit if i else "", "qty": m.qty,
                        "qty_in": m.qty_in, "unit_in": m.unit_in, "lot": lots.get(m.lot_id, ""), "from": _place(names, m.from_store, m.from_pos, m.holder),
                        "to": _place(names, m.to_store, m.to_pos, m.holder), "from_pos": m.from_pos, "to_pos": m.to_pos, "work": m.work,
                        "holder": m.holder, "who": m.who, "approver": m.approver, "note": m.note, "day": m.day,
                        "at": m.at.isoformat() if m.at else "", "doc": m.doc or {}, "reversed": bool(m.reversed_by), "reverses": m.reverses,
                        "cost": m.cost})
        return out


def _place(names: dict[str, str], store: str, pos: str, holder: str) -> str:
    if pos == "holder":
        return holder or "a subcontractor"
    if pos in OUTSIDE:
        return {"outside": "supplier", "used": "the work", "vendor": "back to supplier", "scrap": "scrap", "adjust": "count adjustment"}[pos]
    n = names.get(store, "store")
    return n if pos == "available" else f"{n} ({ {'hold': 'quality hold', 'blocked': 'blocked', 'transit': 'in transit'}[pos]})"


# ---------------------------------------------------------------- numbers worked out from the ledger
def daily_use(s, tenant: str, item_id: str, days: int = 60, end: date | None = None) -> list[float]:
    end = end or today(tenant)
    start = end - timedelta(days=days - 1)
    used: dict[str, float] = defaultdict(float)
    for m in s.scalars(select(SdMove).where(SdMove.tenant_id == tenant, SdMove.item_id == item_id, SdMove.day >= start.isoformat(),
                                            SdMove.day <= end.isoformat())).all():
        if m.from_pos == "available" and m.to_pos in ("used", "holder") and m.kind != "reverse":
            used[m.day] += m.qty
        elif m.to_pos == "available" and m.from_pos in ("used", "holder"):
            used[m.day] -= m.qty
    if not used:
        return []
    first = min(used)
    d0 = date.fromisoformat(first)
    n = (end - d0).days + 1
    return [round(used.get((d0 + timedelta(days=i)).isoformat(), 0.0), 6) for i in range(n)]


def reorder(s, tenant: str, it: SdItem, st: dict[str, Any] | None = None) -> dict[str, Any]:
    st = st or settings(tenant)
    lead = it.lead_days or int(st["lead_days"])
    series = daily_use(s, tenant, it.id)
    if not series:
        return {"avg": 0.0, "sd": None, "lead": lead, "safety": 0.0, "rop": it.min_qty or 0.0, "basis": "your minimum (no use yet)", "days": 0}
    avg = sum(series) / len(series)
    if len(series) >= 14:
        sd = pstdev(series)
        safety = float(st["service_z"]) * sd * math.sqrt(lead)
        rop = avg * lead + safety
        basis = f"{avg:,.2f} {it.unit} a day x {lead} days + safety {safety:,.2f} ({len(series)} days of use)"
    else:
        sd, safety, rop = None, 0.0, avg * lead
        basis = f"{avg:,.2f} {it.unit} a day x {lead} days (fewer than 14 days of use - no safety stock worked out yet)"
    if it.min_qty and it.min_qty > rop:
        basis += f"; your minimum {it.min_qty:g} is higher, so it is used"
        rop = it.min_qty
    return {"avg": round(avg, 4), "sd": round(sd, 4) if sd is not None else None, "lead": lead, "safety": round(safety, 3),
            "rop": round(rop, 3), "basis": basis, "days": len(series)}


def abc(s, tenant: str) -> dict[str, str]:
    """A/B/C by the value of what was used in the last 90 days (80% / next 15% / the rest); her own class wins."""
    end = today(tenant)
    start = (end - timedelta(days=89)).isoformat()
    val: dict[str, float] = defaultdict(float)
    for m in s.scalars(select(SdMove).where(SdMove.tenant_id == tenant, SdMove.day >= start)).all():
        if m.from_pos == "available" and m.to_pos in ("used", "holder"):
            val[m.item_id] += m.qty * (m.cost or 0)
    its = s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()
    tot = sum(val.values())
    out: dict[str, str] = {}
    run = 0.0
    for iid, v in sorted(val.items(), key=lambda x: -x[1]):
        run += v
        out[iid] = "A" if tot and (run - v) / tot < 0.8 else "B" if tot and (run - v) / tot < 0.95 else "C"
    for r in its:
        if r.cls:
            out[r.id] = r.cls
        out.setdefault(r.id, "C")
    return out


def valuation(s, tenant: str, method: str | None = None) -> dict[str, Any]:
    """Stock value by HER method. FIFO: what is left is valued at the lots it came from. Weighted average: a moving average re-worked at
    every receipt. LIFO only under US GAAP. Items with no price are counted and named, never valued at a guess."""
    st = settings(tenant)
    method = method or st["valuation"]
    if method == "lifo" and st["gaap"] != "usgaap":
        raise StoreError("LIFO is not allowed under IFRS (IAS 2).")
    its = {r.id: r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()}
    bal = balances(s, tenant)
    on: dict[str, float] = defaultdict(float)
    by_lot: dict[tuple[str, str], float] = defaultdict(float)
    for (i, l, st_, p, h), q in bal.items():
        if p not in VALUED:
            continue
        on[i] += q
        by_lot[(i, l)] += q
    lot_rows = {r.id: r for r in s.scalars(select(SdLot).where(SdLot.tenant_id == tenant)).all()}
    rows, total, unpriced = [], 0.0, []
    for iid, q in on.items():
        it = its.get(iid)
        if it is None or q <= 1e-9:
            continue
        if method == "fifo":
            v = sum(lq * ((lot_rows[l].cost if l in lot_rows and lot_rows[l].cost else it.price) or 0) for (i, l), lq in by_lot.items() if i == iid)
        elif method == "lifo":
            recs = sorted((r for r in lot_rows.values() if r.item_id == iid), key=lambda r: (r.received or "", r.created_at.isoformat() if r.created_at else ""))
            left, v = q, 0.0
            for r in recs:   # what is left is valued at the OLDEST layers (the newest were used first)
                got = _lot_received(s, tenant, r.id)
                take = min(left, got)
                v += take * (r.cost or it.price or 0)
                left -= take
                if left <= 1e-9:
                    break
            v += max(left, 0) * (it.price or 0)
        else:
            v = q * _wavg(s, tenant, it)
        if not v and q > 0:
            unpriced.append(it.name)
        rows.append({"item_id": iid, "item": it.name, "unit": it.unit, "qty": round(q, 3), "value": round(v, 2),
                     "unit_cost": round(v / q, 4) if q else 0})
        total += v
    rows.sort(key=lambda r: -r["value"])
    return {"method": method, "currency": st["currency"], "total": round(total, 2), "items": rows, "unpriced": unpriced,
            "note": {"fifo": "First in, first out: what is left is valued at the lots it came from.",
                     "wavg": "Weighted average: the average cost is worked out again at every receipt.",
                     "lifo": "Last in, first out (US GAAP only)."}[method] +
                     " Material issued to a subcontractor is charged to the work when it is issued; it is tracked on its own."}


def _lot_received(s, tenant: str, lot: str) -> float:
    return float(s.scalar(select(func.sum(SdMove.qty)).where(SdMove.tenant_id == tenant, SdMove.lot_id == lot, SdMove.from_pos == "outside")) or 0)


def _wavg(s, tenant: str, it: SdItem) -> float:
    avg, q = 0.0, 0.0
    for m in s.scalars(select(SdMove).where(SdMove.tenant_id == tenant, SdMove.item_id == it.id).order_by(SdMove.seq)).all():
        inn, out = m.to_pos in VALUED, m.from_pos in VALUED
        if inn and not out:
            c = m.cost if m.from_pos in ("outside", "adjust") else avg
            if q + m.qty > 1e-9:
                avg = (q * avg + m.qty * (c or 0)) / (q + m.qty)
            q += m.qty
        elif out and not inn:
            q -= m.qty
    return avg or (it.price or 0)


# ---------------------------------------------------------------- numbering
PREFIX = {"grn": "GRN", "issue": "IS", "return": "RT", "transfer": "T", "po": "PO", "indent": "IN", "count": "C", "adjust": "AD",
          "recovery": "RC", "scrap": "SC"}


def number(s, tenant: str, kind: str) -> str:
    n = int(s.scalar(select(func.count(SdDoc.id)).where(SdDoc.tenant_id == tenant, SdDoc.number.like(PREFIX[kind] + "-%"))) or 0) + 1
    return f"{PREFIX[kind]}-{n:04d}"


def doc_view(s, d: SdDoc) -> dict[str, Any]:
    names = store_names(s, d.tenant_id)
    return {"id": d.id, "kind": d.kind, "number": d.number, "status": d.status, "store_id": d.store_id, "store": names.get(d.store_id, ""),
            "party": d.party, "lines": d.lines or [], "data": d.data or {}, "who": d.who, "approver": d.approver, "day": d.day,
            "created": d.created_at.isoformat() if d.created_at else "", "updated": d.updated_at.isoformat() if d.updated_at else ""}


def get_doc(s, tenant: str, ref: str, kind: str | None = None) -> SdDoc:
    ref = S(ref, 40)
    d = s.get(SdDoc, ref)
    if d is None:
        d = s.scalars(select(SdDoc).where(SdDoc.tenant_id == tenant, SdDoc.number == ref.upper())).first()
    if d is None or d.tenant_id != tenant or (kind and d.kind != kind):
        raise StoreError(f"No {kind or 'paper'} '{ref}'.")
    return d


def docs(tenant: str, kind: str, status: str = "", limit: int = 200) -> list[dict[str, Any]]:
    tables()
    with session() as s:
        q = select(SdDoc).where(SdDoc.tenant_id == tenant, SdDoc.kind == kind)
        if status:
            q = q.where(SdDoc.status == status)
        return [doc_view(s, d) for d in s.scalars(q.order_by(SdDoc.created_at.desc()).limit(limit)).all()]


# ---------------------------------------------------------------- old store rows (v0.512 const_store) come in once
def bring_legacy(tenant: str) -> int:
    """Every row the older store tool wrote (cstore_lots / grn / issues) lands in this ledger once, in the default store: a receipt as
    receive (straight to available - it was accepted then), an issue as issue (or scrap when it was written off)."""
    tables()
    try:
        from ..construction.models import CStoreGrn, CStoreIssue, CStoreLot
    except Exception:   # noqa: BLE001
        return 0
    n = 0
    with LOCK, session() as s:
        st = s.get(SdSettings, tenant)
        done = dict(st.legacy_done or {}) if st else {}
        try:
            olds = s.scalars(select(CStoreLot).where(CStoreLot.tenant_id == tenant)).all()
        except Exception:   # noqa: BLE001  (the old tables may not exist on this server)
            return 0
        grns = s.scalars(select(CStoreGrn).where(CStoreGrn.tenant_id == tenant)).all()
        iss = s.scalars(select(CStoreIssue).where(CStoreIssue.tenant_id == tenant)).all()
        if not (olds or grns or iss):
            return 0
        sid = store_id(s, tenant)
        mine = {r.name.lower(): r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()}

        def item(name: str, unit: str = "", mn: float = 0, mx: float = 0) -> SdItem:
            r = mine.get(name.lower())
            if r is None:
                r = SdItem(tenant_id=tenant, name=name[:120], unit=(unit or "no").lower()[:12], conv={}, docs=[], min_qty=mn or 0.0, max_qty=mx or 0.0)
                s.add(r)
                s.flush()
                mine[name.lower()] = r
            return r
        for o in olds:
            if done.get(o.id):
                continue
            item(o.item, o.unit, o.min_qty, o.max_qty)
            done[o.id] = 1
        for g in sorted(grns, key=lambda x: (x.day or "", x.created_at or now())):
            if done.get(g.id):
                continue
            it = item(next((o.item for o in olds if o.item.lower() == g.item), g.item), g.unit)
            lot = SdLot(tenant_id=tenant, item_id=it.id, cost=g.rate or 0.0, received=g.day or "")
            s.add(lot)
            s.flush()
            if g.rate:
                it.price = g.rate
            post(s, tenant, "receive", it, g.qty, ("", "outside"), (sid, "available"), lot=lot.id, cost=g.rate or 0.0,
                 doc={"legacy": g.id, "supplier": g.vendor, "doc_no": g.invoice_no}, who=g.by, note=g.note or "from the older store records",
                 day=g.day or "")
            done[g.id] = 1
            n += 1
        for i in sorted(iss, key=lambda x: (x.day or "", x.created_at or now())):
            if done.get(i.id):
                continue
            it = item(next((o.item for o in olds if o.item.lower() == i.item), i.item), i.unit)
            have = balance(s, tenant, it.id, store=sid, pos="available")
            q = min(i.qty, have)
            if q > 1e-9:
                for lot, lq in lots_fifo(s, tenant, it, sid, "available", q):
                    post(s, tenant, "scrap" if i.waste else "issue", it, lq, (sid, "available"), ("", "scrap" if i.waste else "used"), lot=lot,
                         work=i.purpose or i.site, holder="", cost=lot_cost(s, lot, it), doc={"legacy": i.id, "gang": i.gang},
                         who=i.by, approver="older record" if i.waste else "", note=i.note or "from the older store records", day=i.day or "")
            done[i.id] = 1
            n += 1
        if st is None:
            st = SdSettings(tenant_id=tenant, tiers=DEFAULT_TIERS, count_days=DEFAULT_COUNT, packs_off=[])
            s.add(st)
        st.legacy_done = done
    return n
