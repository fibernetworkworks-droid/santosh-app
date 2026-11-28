"""Demand: what each work package should use (her QS quantities and norms), the look-ahead (what is needed by when), indents raised
against the budget, and the shortfall forecast - stock available plus orders due before the need-by date, against the demand.
Every quantity here is hers (the take-off, the % done, the look-ahead); Hoola only adds up."""
from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any

from sqlalchemy import select

from ..db import now, session
from .core import (LOCK, S, SdDoc, SdItem, StoreError, balances, doc_view, find_item, get_doc, num, number, reorder, settings, show_qty,
                   store_id, tables, to_base, today)
from .issue import _budget_line
from .models import SdBudget


def _row(b: SdBudget, it: SdItem | None) -> dict[str, Any]:
    return {"id": b.id, "work": b.work, "name": b.name, "item_id": b.item_id, "item": it.name if it else "?", "unit": it.unit if it else "",
            "qty": b.qty, "allowance": b.allowance, "done": b.done, "unused": b.unused, "need_by": b.need_by, "need_qty": b.need_qty, "source": b.source}


def budgets(tenant: str, work: str = "") -> list[dict[str, Any]]:
    tables()
    with session() as s:
        its = {r.id: r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()}
        q = select(SdBudget).where(SdBudget.tenant_id == tenant)
        if work:
            q = q.where(SdBudget.work == S(work, 80))
        return [_row(b, its.get(b.item_id)) for b in s.scalars(q.order_by(SdBudget.work, SdBudget.created_at)).all()]


def save_budget(tenant: str, work: str, item: str, qty: Any = None, unit: str = "", name: str = "", allowance: Any = None, done: Any = None,
                unused: Any = None, need_by: str = "", need_qty: Any = None, source: str = "") -> dict[str, Any]:
    tables()
    work = S(work, 80)
    if not work:
        raise StoreError("Give the work package or cost code, like 'Slab L6' or 03-21-06.")
    with LOCK, session() as s:
        it = find_item(s, tenant, item)
        b = s.scalars(select(SdBudget).where(SdBudget.tenant_id == tenant, SdBudget.work == work, SdBudget.item_id == it.id)).first()
        if b is None:
            if qty in (None, ""):
                raise StoreError(f"Give the quantity {work} should use of {it.name} (from the QS take-off).")
            b = SdBudget(tenant_id=tenant, work=work, item_id=it.id)
            s.add(b)
        if qty not in (None, ""):
            b.qty = to_base(it, qty, unit)[0]
        if name:
            b.name = S(name, 120)
        if allowance not in (None, ""):
            a = num(allowance, "Allowance %", allow_zero=True)
            if a > 50:
                raise StoreError("Allowance: at most 50%.")
            b.allowance = a
        if done not in (None, ""):
            d = num(done, "Done %", allow_zero=True)
            if d > 100:
                raise StoreError("Done: 0 to 100%.")
            b.done = d
        if unused not in (None, ""):
            b.unused = to_base(it, unused, unit)[0] if num(unused, "Unused", allow_zero=True) else 0.0
        if need_by:
            try:
                b.need_by = date.fromisoformat(S(need_by, 10)).isoformat()
            except ValueError:
                raise StoreError("Need-by: YYYY-MM-DD.")
        if need_qty not in (None, ""):
            b.need_qty = to_base(it, need_qty, unit)[0] if num(need_qty, "Needed", allow_zero=True) else 0.0
        if source:
            b.source = S(source, 200)
        s.flush()
        out = _row(b, it)
    out["say"] = f"{work}: {it.name} {show_qty(it, out['qty'])} should be used" + (f", {out['done']:g}% done" if out["done"] else "") + "."
    return out


def import_budgets(tenant: str, text: str, source: str = "") -> dict[str, Any]:
    """CSV with columns work, item, qty, unit, allowance, done, unused, need_by, need_qty, name - e.g. the QS take-off export."""
    rows = list(csv.DictReader(io.StringIO(str(text or "")[:2_000_000])))
    if not rows:
        raise StoreError("Paste a CSV with at least: work, item, qty.")
    ok, bad = 0, []
    for i, r in enumerate(rows[:5000], 2):
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        try:
            save_budget(tenant, r.get("work") or r.get("work_package") or r.get("cost_code") or "", r.get("item") or "", r.get("qty") or r.get("quantity"),
                        r.get("unit", ""), r.get("name", ""), r.get("allowance") or None, r.get("done") or None, r.get("unused") or None,
                        r.get("need_by", ""), r.get("need_qty") or None, source or "pasted CSV")
            ok += 1
        except StoreError as e:
            bad.append(f"line {i}: {e}")
    return {"saved": ok, "errors": bad[:30], "say": f"{ok} budget line(s) saved" + (f", {len(bad)} refused" if bad else "") + "."}


def progress(tenant: str, work: str, done: Any, unused: dict[str, Any] | None = None) -> dict[str, Any]:
    """Her % complete for a work package (and what is left unused at its work front, item by item)."""
    tables()
    d = num(done, "Done %", allow_zero=True)
    if d > 100:
        raise StoreError("Done: 0 to 100%.")
    with LOCK, session() as s:
        rows = s.scalars(select(SdBudget).where(SdBudget.tenant_id == tenant, SdBudget.work == S(work, 80))).all()
        if not rows:
            raise StoreError(f"No budget for '{work}' yet.")
        for b in rows:
            b.done = d
        for k, v in (unused or {}).items():
            it = find_item(s, tenant, k)
            b = next((r for r in rows if r.item_id == it.id), None)
            if b is None:
                raise StoreError(f"{work} has no budget for {it.name}.")
            b.unused = to_base(it, v, "")[0] if num(v, "Unused", allow_zero=True) else 0.0
    return {"work": work, "done": d, "say": f"{work}: {d:g}% done."}


def delete_budget(tenant: str, id: str) -> dict[str, Any]:
    with LOCK, session() as s:
        b = s.get(SdBudget, id)
        if b is None or b.tenant_id != tenant:
            raise StoreError("That budget line is not yours.")
        s.delete(b)
    return {"say": "Budget line removed."}


# ---------------------------------------------------------------- indents
def draft_indent(tenant: str, item: str, qty: Any, unit: str = "", work: str = "", need_by: str = "", store: str = "", by: str = "",
                 note: str = "") -> dict[str, Any]:
    tables()
    with LOCK, session() as s:
        it = find_item(s, tenant, item)
        base, qin, uin = to_base(it, qty, unit)
        sid = store_id(s, tenant, store)
        avail = sum(q for (i, l, st, p, h), q in balances(s, tenant, [it.id]).items() if p == "available")
        warn = []
        if avail >= base:
            warn.append(f"{show_qty(it, avail)} is already available - an order may not be needed")
        bl = _budget_line(s, tenant, it, S(work, 80), base) if work else None
        if bl and bl["over"]:
            warn.append(f"Takes {bl['work']} to {bl['share']:.0%} of its budget (allowance included)")
        if need_by:
            try:
                date.fromisoformat(S(need_by, 10))
            except ValueError:
                raise StoreError("Need-by: YYYY-MM-DD.")
        d = SdDoc(tenant_id=tenant, kind="indent", number=number(s, tenant, "indent"), status="waiting", store_id=sid, party=S(by, 80),
                  data={"item_id": it.id, "item": it.name, "unit": it.unit, "qty": round(base, 6), "qty_in": qin, "unit_in": uin,
                        "work": S(work, 80), "need_by": S(need_by, 10), "note": S(note, 300), "available": round(avail, 3), "budget": bl, "warn": warn},
                  day=today(tenant).isoformat(), who=S(by, 80))
        s.add(d)
        s.flush()
        v = doc_view(s, d)
    v["say"] = f"Indent {v['number']}: {show_qty(it, base)} of {it.name}" + (f" for {work}" if work else "") + (f" by {need_by}" if need_by else "") + \
        ". " + (" ".join(w + "." for w in warn) + " " if warn else "") + "It waits for approval."
    return v


def decide_indent(tenant: str, id: str, decision: str, who: str, note: str = "") -> dict[str, Any]:
    """A named person approves or turns down an indent. Approving does not place an order - the buyer records the purchase order."""
    tables()
    who = S(who, 80)
    if not who:
        raise StoreError("Give the name of the person deciding.")
    if decision not in ("approve", "reject", "ordered"):
        raise StoreError("Decision: approve, reject or ordered.")
    with LOCK, session() as s:
        d = get_doc(s, tenant, id, "indent")
        if decision == "ordered":
            if d.status != "approved":
                raise StoreError("Only an approved indent is marked ordered.")
            d.status = "ordered"
        else:
            if d.status != "waiting":
                raise StoreError(f"{d.number} is already {d.status}.")
            d.status = "approved" if decision == "approve" else "rejected"
        d.approver = who
        d.data = {**(d.data or {}), "decision_note": S(note, 300)}
        d.updated_at = now()
        v = doc_view(s, d)
    v["say"] = f"{v['number']} {v['status']} by {who}."
    return v


# ---------------------------------------------------------------- what runs short
def shortfall(tenant: str) -> list[dict[str, Any]]:
    """For every item with look-ahead demand: available now + open orders due by each need-by date, against the demand in date order.
    The first date it runs short and by how much."""
    tables()
    with session() as s:
        its = {r.id: r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()}
        bal = balances(s, tenant)
        avail: dict[str, float] = {}
        for (i, l, st, p, h), q in bal.items():
            if p == "available":
                avail[i] = avail.get(i, 0.0) + q
        pos = s.scalars(select(SdDoc).where(SdDoc.tenant_id == tenant, SdDoc.kind == "po", SdDoc.status.in_(("open", "part")))).all()
        dem = [b for b in s.scalars(select(SdBudget).where(SdBudget.tenant_id == tenant)).all() if b.need_qty > 0 and b.need_by]
        out = []
        for iid in sorted({b.item_id for b in dem}):
            it = its.get(iid)
            if it is None:
                continue
            rows = sorted((b for b in dem if b.item_id == iid), key=lambda b: b.need_by)
            incoming = sorted(((p.data or {}).get("due") or "9999-12-31", y["qty"] - y.get("received", 0), p.number)
                              for p in pos for y in (p.lines or []) if y["item_id"] == iid and y["qty"] - y.get("received", 0) > 1e-9)
            have, need, first = avail.get(iid, 0.0), 0.0, None
            for b in rows:
                need += b.need_qty
                arrive = sum(q for due, q, _n in incoming if due <= b.need_by)
                gap = have + arrive - need
                if gap < -1e-9 and first is None:
                    first = {"date": b.need_by, "short": round(-gap, 3), "work": b.work}
            out.append({"item_id": iid, "item": it.name, "unit": it.unit, "available": round(have, 3), "demand": round(need, 3),
                        "incoming": [{"due": d, "qty": round(q, 3), "po": n} for d, q, n in incoming], "short": first,
                        "works": [{"work": b.work, "need_by": b.need_by, "qty": b.need_qty} for b in rows]})
        return sorted(out, key=lambda r: (r["short"] is None, (r["short"] or {}).get("date", "")))


def reorder_list(tenant: str) -> list[dict[str, Any]]:
    tables()
    st = settings(tenant)
    with session() as s:
        its = [r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all() if r.active]
        bal = balances(s, tenant)
        avail: dict[str, float] = {}
        for (i, l, stx, p, h), q in bal.items():
            if p == "available":
                avail[i] = avail.get(i, 0.0) + q
        out = []
        for it in its:
            r = reorder(s, tenant, it, st)
            a = avail.get(it.id, 0.0)
            out.append({"item_id": it.id, "item": it.name, "unit": it.unit, "available": round(a, 3), "rop": r["rop"], "basis": r["basis"],
                        "avg": r["avg"], "days_cover": round(a / r["avg"], 1) if r["avg"] > 0 else None, "below": bool(r["rop"]) and a <= r["rop"] + 1e-9,
                        "max": it.max_qty, "suggest": round(max((it.max_qty or (r["rop"] * 2)) - a, 0), 3) if r["rop"] and a <= r["rop"] else 0})
        return sorted(out, key=lambda x: (not x["below"], x["days_cover"] if x["days_cover"] is not None else 1e9))
