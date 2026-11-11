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
        raise CstError("Give the project and the item (for example 'Footing PCC M10').")
    if not isinstance(params, dict):
        raise CstError("Send the dimensions as an object ({length, breadth, depth, ...}).")
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
            "say": f"Measurement line added: {item} = {t['qty']:g} {t['unit']} ({t['is_ref']}). The trail is with it - "
                   "certification is the billing engineer's, this is a working paper."}


def recompute(tenant: str, takeoff_id: str) -> dict:
    """The trail law, runnable: stored inputs through the same formula, bit-for-bit ya farq dikhao."""
    with session() as s:
        x = s.get(CqsTakeoff, takeoff_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Take-off line not found.")
        trail = {"kind": x.kind, "inputs": _j(x.inputs, {})}
        stored, item = x.qty, x.item
    try:
        again = M.recompute(trail)
    except ValueError as ex:
        raise CstError(str(ex)) from None
    ok = again == stored
    return {"takeoff_id": takeoff_id, "stored": stored, "recomputed": again, "bit_for_bit": ok,
            "say": (f"Recalculation gave exactly the same number: {stored:g} = {again:g} - the trail is right."
                    if ok else f"DIFFERENCE: stored {stored} vs recomputed {again} - measure this line again.")}


def rate_buildup(tenant: str, item: str, unit: str, components: list, overhead_pct=None, profit_pct=None,
                 source: str = "") -> dict:
    """#38: component rows {head, qty, unit, rate, source} -> subtotal, + overhead, + profit.
    Bina source ke rate nahi bachta (SOR item / quote ref - kaunsi kitab, kaunsa page)."""
    if not str(item or "").strip():
        raise CstError("Give the item.")
    src = str(source or "").strip()
    if not src:
        raise CstError("Give the SOURCE of the rate (SOR item no / which vendor's quote) - a rate without a source "
                       "is not saved.")
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
        raise CstError("Send the rate build-up components [{head, qty, unit, rate, source}].")
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
            "say": f"Rate built: {item} = {_rs(rate)}/{unit or 'unit'} (components {_rs(subtotal)}"
                   f"{f' + {ovh:g}% overhead' if ovh else ''}{f' + {prof:g}% profit' if prof else ''}) "
                   f"- source: {src}. This is an estimate; the contract rate is verified later."}


def boq_add(tenant: str, project: str, item: str, unit: str, qty=None, rate=None, head: str = "",
            takeoff_id: str = "", rate_id: str = "") -> dict:
    """#39 one BOQ line: qty x rate = amount (rounded 2, the only rounding in the chain)."""
    if not str(project or "").strip() or not str(item or "").strip():
        raise CstError("Give the project and the item.")
    q, r = _num(qty), _num(rate)
    if q <= 0 or r <= 0:
        raise CstError("Both qty and rate are needed (> 0) - a BOQ line is never left incomplete.")
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
        raise CstError(f"'{project}' has no BOQ lines.")
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
        raise CstError("Give the project and the cost head.")
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
                   + (". Over budget - show it to the PM." if over else ".")}


def retention(bill_amount, pct) -> dict:
    """#49 retention: the contract's own % held back - her contract numbers, arithmetic only."""
    amt, p = _num(bill_amount), _num(pct)
    if amt <= 0:
        raise CstError("Give the bill amount.")
    if p <= 0:
        raise CstError("Give your contract's retention % (Hoola does not assume a % that is not written in the contract).")
    held = round(amt * p / 100.0, 2)
    return {"bill": amt, "pct": p, "held": held, "payable": round(amt - held, 2),
            "formula": f"held = bill x {p:g}% ; payable = bill - held",
            "say": f"Retention DRAFT: {_rs(amt)} bill at {p:g}% = {_rs(held)} held, {_rs(amt - held)} payable. "
                   "Match it with the contract clause - this is a working paper."}


def price_variation(amount, workable_pct, base_index, current_index) -> dict:
    """#49 price variation / escalation: amount x workable% x (CI - BI) / BI - the contract's indices."""
    a, w = _num(amount), _num(workable_pct)
    bi, ci = _num(base_index), _num(current_index)
    if a <= 0:
        raise CstError("Give the bill / running amount.")
    if bi <= 0:
        raise CstError("The base index cannot be zero - give the contract's base index.")
    delta = (ci - bi) / bi
    pv = round(a * (w / 100.0) * delta, 2)
    return {"amount": a, "workable_pct": w, "base_index": bi, "current_index": ci, "index_delta": round(delta, 6),
            "pv": pv,
            "formula": f"PV = {a:g} x {w:g}% x ({ci:g} - {bi:g}) / {bi:g}",
            "say": f"Price-variation DRAFT: {_rs(pv)} ({'+' if pv >= 0 else ''}{delta * 100:.2f}% on the index shift, "
                   f"{w:g}% workable). It is based on the contract's PV clause - state it plainly when you show it."}


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
    say = (f"QS desk{' - ' + project if project else ''}: {len(tks)} take-off lines (with the trail), "
           f"BOQ value {_rs(val)}, {len(over)} head(s) over budget.")
    return {"takeoffs": len(tks), "boq_lines": len(bos), "boq_value": val, "over_budget": len(over), "say": say}


# ---------------------------------------------------------------- Wave 4: #40 cost plan & VE, #89 GST
def cost_plan(tenant: str, project: str, rows: list, note: str = "") -> dict:
    """#40: rows [head, planned, estimate] - plan vs estimate variance, arithmetic; the value
    engineering DECISION stays with the cost manager / owner."""
    from . import models as WM
    if not rows:
        raise CstError("Cost plan rows are needed [head, planned, estimate].")
    out, tp, te = [], 0.0, 0.0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 3:
                continue
            p, e = _num(r[1]), _num(r[2])
            tp, te = tp + p, te + e
            var = round(e - p, 2)
            s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="cost_plan",
                                name=str(r[0])[:120],
                                data=_dump({"planned": p, "estimate": e, "var": var,
                                            "note": note[:200]})))
            out.append({"head": str(r[0])[:80], "planned": p, "estimate": e, "var": var,
                        "verdict": "over" if var > 0 else "under"})
    return {"ok": True, "rows": out, "total_planned": round(tp, 2), "total_estimate": round(te, 2),
            "total_var": round(te - tp, 2),
            "said": (f"The estimate differs from planned by {round(te - tp, 2):,.0f} - look at the VE options. "
                     "Approving the cost plan is the cost manager's/owner's job.")}


def ve_option(tenant: str, project: str, rows: list) -> dict:
    """#40: rows [option, saving(FED), risk_note] - the saving is HER number with its basis."""
    from . import models as WM
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 2:
                continue
            s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="ve", name=str(r[0])[:160],
                                data=_dump({"saving": _num(r[1]), "risk": str(r[2])[:200] if len(r) > 2 else ""})))
            made += 1
    return {"ok": True, "rows": made,
            "said": f"{made} VE option(s) in the register - the saving is your number, give the basis note; adopting it is the owner's decision."}


def gst_row(tenant: str, project: str, ref: str, rows: list, source: str = "") -> dict:
    """#89: works-contract GST rows [taxable_value, rate_pct, rcm(yes/no)] on a bill/RA ref.
    Rate FED ya pack row se (india.json gst_works_contract_pct); filing the CA's (tier C)."""
    from . import models as WM
    from .statepacks import national
    if not ref:
        raise CstError("Give the bill/RA ref the GST applies to.")
    if not rows:
        raise CstError("rows are needed [taxable_value, rate_pct, rcm].")
    if not source:
        pack = national()
        row = next((r for r in pack.get("rows", []) if r.get("rule_id") == "gst_works_contract_pct"), None)
        if not row:
            raise CstError("Give the source of the rate (notification/circular) - no pack row was found either.")
        source = f"india pack: {row.get('source', '')}"
        default_rate = float(row.get("value") or 0)
    else:
        default_rate = 0.0
    out, tot_tax = [], 0.0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 2:
                continue
            taxable, rate = _num(r[0]), _num(r[1]) if len(r) > 1 and _num(r[1]) else default_rate
            rcm = str(r[2])[:4].lower() == "yes" if len(r) > 2 else False
            tax = round(taxable * rate / 100, 2)
            tot_tax += tax
            s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="gst", ref=ref,
                                name="gst", data=_dump({"taxable": taxable, "rate_pct": rate,
                                                        "rcm": rcm, "tax": tax}), source=source))
            out.append({"taxable": taxable, "rate_pct": rate, "rcm": rcm, "tax": tax})
    return {"ok": True, "ref": ref, "rows": out, "tax_total": round(tot_tax, 2), "rate_source": source,
            "said": (f"GST {round(tot_tax, 2):,.0f} ({source[:60]}). The cash flow of an RCM row is "
                     "separate. Filing the return is the CA's job.")}


def gst_sum(tenant: str, project: str, ref: str, itc: float = 0.0, itc_source: str = "") -> dict:
    """Net = output tax (fed rows) - ITC (FED with its source). Filing stays the CA's."""
    from . import models as WM
    if itc > 0 and not itc_source:
        raise CstError("Give the source of the ITC (2B / credit note).")
    with session() as s:
        rows = s.scalars(select(WM.Cw4ExtItem).where(WM.Cw4ExtItem.tenant_id == tenant,
                                                     WM.Cw4ExtItem.project == project,
                                                     WM.Cw4ExtItem.kind == "gst",
                                                     WM.Cw4ExtItem.ref == ref)).all()
    if not rows:
        raise CstError(f"Ref '{ref}' has no GST rows - run action=gst_row first.")
    out_tax = round(sum(float(_j(r.data, {}).get("tax") or 0) for r in rows), 2)
    net = round(out_tax - itc, 2)
    return {"ok": True, "ref": ref, "output_tax": out_tax, "itc_fed": itc, "net_payable": net,
            "said": "This is a computation - only the CA files the return and makes the payment (tier C)."}
