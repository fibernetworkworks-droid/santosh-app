"""#37 Quantity Take-off + #38 Rate Analyst + #39 BOQ Builder & Abstract + #41 Cost Controller +
#49 Retention / Price-variation / Escalation calculator (v0.531.0, Wave 2 C8).

Every quantity goes through construction/is1200.py and lands with its trail (qty, formula, inputs,
IS ref) in `cqs_takeoff`; a recompute must match bit-for-bit. Rates refuse to save without a source
(SOR item / quote). The BOQ multiplies the two and the abstract totals by head. Cost control is
arithmetic on her budgets. Retention / PV / escalation are pure calculators with the contract's own
numbers - every result says "working paper": certify toh billing engineer karega."""
from __future__ import annotations

import json

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _dump, _j, _num, _rs, today)
from . import is1200 as M
from .models import CqsBoq, CqsBudget, CqsRate, CqsTakeoff


def takeoff(tenant: str, project: str, item: str, kind: str, params: dict, dwg_ref: str = "",
            by: str = "") -> dict:
    """One measured line through the IS 1200 library, stored with the trail."""
    if not str(project or "").strip() or not str(item or "").strip():
        raise CstError("Project aur item bataiye (jaise 'Footing PCC M10').")
    if not isinstance(params, dict):
        raise CstError("Dimensions object mein bhejo ({length, breadth, depth, ...}).")
    try:
        t = M.compute(kind, params)
    except ValueError as ex:
        raise CstError(str(ex)) from None
    with _LOCK, session() as s:
        x = CqsTakeoff(tenant_id=tenant, project=project.strip()[:160], item=item.strip()[:200],
                       is_ref=t["is_ref"][:80], kind=(kind or "").strip().lower()[:30], unit=t["unit"][:12],
                       qty=t["qty"], formula=t["formula"][:200], inputs=_dump(t["inputs"]),
                       dwg_ref=dwg_ref[:80], by=by[:80])
        s.add(x)
        s.flush()
        tid = x.id
    return {"takeoff_id": tid, "qty": t["qty"], "unit": t["unit"], "formula": t["formula"],
            "inputs": t["inputs"], "is_ref": t["is_ref"],
            "say": f"Naap line juda: {item} = {t['qty']:g} {t['unit']} ({t['is_ref']}). Trail saath hai - "
                   "certification billing engineer ki, yeh working paper hai."}


def recompute(tenant: str, takeoff_id: str) -> dict:
    """The trail law, runnable: stored inputs through the same formula, bit-for-bit ya farq dikhao."""
    with session() as s:
        x = s.get(CqsTakeoff, takeoff_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Take-off line nahi mili.")
        trail = {"kind": x.kind, "inputs": _j(x.inputs, {})}
        stored, item = x.qty, x.item
    try:
        again = M.recompute(trail)
    except ValueError as ex:
        raise CstError(str(ex)) from None
    ok = again == stored
    return {"takeoff_id": takeoff_id, "stored": stored, "recomputed": again, "bit_for_bit": ok,
            "say": (f"Recalculate bilkul wahi number aaya: {stored:g} = {again:g} - trail sahi."
                    if ok else f"FARQ: stored {stored} vs recomputed {again} - yeh line dobara naapo.")}


def rate_buildup(tenant: str, item: str, unit: str, components: list, overhead_pct=None, profit_pct=None,
                 source: str = "") -> dict:
    """#38: component rows {head, qty, unit, rate, source} -> subtotal, + overhead, + profit.
    Bina source ke rate nahi bachta (SOR item / quote ref - kaunsi kitab, kaunsa page)."""
    if not str(item or "").strip():
        raise CstError("Item bataiye.")
    src = str(source or "").strip()
    if not src:
        raise CstError("Rate ka SOURCE bataiye (SOR item no / quote kaunse vendor se) - bina source ke "
                       "rate save nahi hota.")
    rows, subtotal = [], 0.0
    for c in (components or []):
        if not isinstance(c, dict) or not str(c.get("head", "")).strip():
            continue
        q, r = _num(c.get("qty")), _num(c.get("rate"))
        amt = round(q * r, 2)
        rows.append({"head": str(c.get("head"))[:120], "qty": q, "unit": str(c.get("unit", ""))[:12],
                     "rate": r, "amount": amt, "source": str(c.get("source", ""))[:120]})
        subtotal += amt
    if not rows:
        raise CstError("Rate build-up ke components bhejo [{head, qty, unit, rate, source}].")
    ovh, prof = _num(overhead_pct), _num(profit_pct)
    rate = round(subtotal * (1 + ovh / 100.0) * (1 + prof / 100.0), 2)
    with _LOCK, session() as s:
        x = CqsRate(tenant_id=tenant, item=item.strip()[:200], unit=unit[:12], analysis=_dump(rows),
                    overhead_pct=ovh, profit_pct=prof, rate=rate, source=src[:200])
        s.add(x)
        s.flush()
        rid = x.id
    return {"rate_id": rid, "rate": rate, "subtotal": round(subtotal, 2), "overhead_pct": ovh,
            "profit_pct": prof, "components": rows, "source": src,
            "say": f"Rate ban gaya: {item} = {_rs(rate)}/{unit or 'unit'} (components {_rs(subtotal)}"
                   f"{f' + {ovh:g}% overhead' if ovh else ''}{f' + {prof:g}% profit' if prof else ''}) "
                   f"- source: {src}. Yeh estimate hai; contract rate baad mein verify hota hai."}


def boq_add(tenant: str, project: str, item: str, unit: str, qty=None, rate=None, head: str = "",
            takeoff_id: str = "", rate_id: str = "") -> dict:
    """#39 one BOQ line: qty x rate = amount (rounded 2, the only rounding in the chain)."""
    if not str(project or "").strip() or not str(item or "").strip():
        raise CstError("Project aur item bataiye.")
    q, r = _num(qty), _num(rate)
    if q <= 0 or r <= 0:
        raise CstError("Qty aur rate dono chahiye (> 0) - BOQ line adhoori nahi bachti.")
    amt = round(q * r, 2)
    with _LOCK, session() as s:
        x = CqsBoq(tenant_id=tenant, project=project.strip()[:160], item=item.strip()[:200], unit=unit[:12],
                   qty=q, rate=r, amount=amt, head=head[:80], takeoff_id=takeoff_id[:40], rate_id=rate_id[:40])
        s.add(x)
        s.flush()
        bid = x.id
    return {"boq_id": bid, "amount": amt,
            "say": f"BOQ line: {item} - {q:g} {unit or 'unit'} x {_rs(r)} = {_rs(amt)}"
                   + (f" (head: {head})" if head else "") + "."}


def abstract(tenant: str, project: str) -> dict:
    """#39 the abstract: totals by head + the grand total, each line's trail still in its row."""
    with session() as s:
        rows = s.scalars(select(CqsBoq).where(CqsBoq.tenant_id == tenant, CqsBoq.project == project)).all()
    if not rows:
        raise CstError(f"'{project}' mein BOQ lines nahi mili.")
    by_head: dict[str, float] = {}
    for r in rows:
        h = r.head or "uncategorised"
        by_head[h] = round(by_head.get(h, 0.0) + r.amount, 2)
    total = round(sum(r.amount for r in rows), 2)
    return {"project": project, "lines": len(rows), "by_head": by_head, "total": total,
            "say": f"Abstract ({project}): {len(rows)} lines, {_rs(total)} total. Heads: "
                   + ", ".join(f"{k} {_rs(v)}" for k, v in sorted(by_head.items(), key=lambda kv: -kv[1])[:8])}


def budget(tenant: str, project: str, head: str, budget=None, committed=None, actual=None, note: str = "") -> dict:
    """#41 upsert one cost head; variance is arithmetic against whatever she recorded."""
    if not str(project or "").strip() or not str(head or "").strip():
        raise CstError("Project aur cost head bataiye.")
    with _LOCK, session() as s:
        x = s.scalars(select(CqsBudget).where(CqsBudget.tenant_id == tenant, CqsBudget.project == project,
                                              CqsBudget.head == head)).first()
        if x is None:
            x = CqsBudget(tenant_id=tenant, project=project[:160], head=head[:120])
            s.add(x)
        if budget is not None:
            x.budget = _num(budget)
        if committed is not None:
            x.committed = _num(committed)
        if actual is not None:
            x.actual = _num(actual)
        if note:
            x.note = note[:200]
        s.flush()
        b, c, a = x.budget, x.committed, x.actual
    var = round(b - a, 2)
    over = a > b + 1e-9 and b > 0
    return {"project": project, "head": head, "budget": b, "committed": c, "actual": a, "variance": var,
            "say": f"{head}: budget {_rs(b)}, committed {_rs(c)}, actual {_rs(a)} -> {'OVER' if over else 'variance'} {_rs(abs(var))}"
                   + (". Budget se aage - PM ko dikhao." if over else ".")}


def retention(bill_amount, pct) -> dict:
    """#49 retention: the contract's own % held back - her contract numbers, arithmetic only."""
    amt, p = _num(bill_amount), _num(pct)
    if amt <= 0:
        raise CstError("Bill amount bataiye.")
    if p <= 0:
        raise CstError("Aapke contract ka retention % bataiye (Hoola contract se % nahi maanta bina likhe).")
    held = round(amt * p / 100.0, 2)
    return {"bill": amt, "pct": p, "held": held, "payable": round(amt - held, 2),
            "formula": f"held = bill x {p:g}% ; payable = bill - held",
            "say": f"Retention DRAFT: {_rs(amt)} bill par {p:g}% = {_rs(held)} ruka, {_rs(amt - held)} payable. "
                   "Contract ke clause se mila lo - working paper hai."}


def price_variation(amount, workable_pct, base_index, current_index) -> dict:
    """#49 price variation / escalation: amount x workable% x (CI - BI) / BI - the contract's indices."""
    a, w = _num(amount), _num(workable_pct)
    bi, ci = _num(base_index), _num(current_index)
    if a <= 0:
        raise CstError("Bill / running amount bataiye.")
    if bi <= 0:
        raise CstError("Base index zero nahi ho sakta - contract ka base index bataiye.")
    delta = (ci - bi) / bi
    pv = round(a * (w / 100.0) * delta, 2)
    return {"amount": a, "workable_pct": w, "base_index": bi, "current_index": ci, "index_delta": round(delta, 6),
            "pv": pv,
            "formula": f"PV = {a:g} x {w:g}% x ({ci:g} - {bi:g}) / {bi:g}",
            "say": f"Price-variation DRAFT: {_rs(pv)} ({'+' if pv >= 0 else ''}{delta * 100:.2f}% index shift par, "
                   f"{w:g}% workable). Contract ka PV clause iska base hai - baat saaf karke dikhao."}


def day(tenant: str, project: str = "") -> dict:
    """The QS morning: how many take-off lines, BOQ value, over-budget heads."""
    with session() as s:
        tks = s.scalars(select(CqsTakeoff).where(CqsTakeoff.tenant_id == tenant)).all()
        bos = s.scalars(select(CqsBoq).where(CqsBoq.tenant_id == tenant)).all()
        buds = s.scalars(select(CqsBudget).where(CqsBudget.tenant_id == tenant)).all()
    if project:
        tks = [r for r in tks if r.project == project]
        bos = [r for r in bos if r.project == project]
        buds = [r for r in buds if r.project == project]
    over = [b for b in buds if b.budget > 0 and b.actual > b.budget + 1e-9]
    val = round(sum(r.amount for r in bos), 2)
    say = (f"QS desk{' - ' + project if project else ''}: {len(tks)} take-off lines (trail ke saath), "
           f"BOQ value {_rs(val)}, {len(over)} head(s) over budget.")
    return {"takeoffs": len(tks), "boq_lines": len(bos), "boq_value": val, "over_budget": len(over), "say": say}
