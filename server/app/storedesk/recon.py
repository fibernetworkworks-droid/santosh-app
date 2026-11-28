"""Reconciliation, month-end and close-out.

What the work should have used = her QS quantity for the work package x her % done. What it did use = issued to it - returned from
it - what is still unused at the work front (her entry). The difference against her allowance is the variance; for free-issue material
the same is worked out per subcontractor, and what is beyond the allowance x the rate from HER subcontract is a recovery DRAFT for the
Contracts desk - deducting it is her decision. The likely cause is named only where the records show it; nobody is accused."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from ..db import now, session
from .core import (LOCK, S, SdDoc, SdHolder, SdItem, StoreError, balances, doc_view, find_item, get_doc, lot_cost, lots_fifo, num, number,
                   post, settings, show_qty, store_id, store_names, tables, tier_for, today, valuation)
from .models import SdBudget, SdMove

STEEL = ("rebar", "steel", "bar", "tmt", "b500", "fe500")


def _allow(b: SdBudget | None, it: SdItem, st: dict[str, Any], holder: SdHolder | None = None) -> float:
    if holder is not None and holder.allowance >= 0:
        return holder.allowance
    if b is not None and b.allowance >= 0:
        return b.allowance
    if it.wastage >= 0:
        return it.wastage
    return float(st["wastage"])


def _flows(s, tenant: str) -> dict[str, Any]:
    """Per (item, work) and per (holder, item, work): net issued, returns, scrap returned."""
    by_work: dict[tuple[str, str], float] = defaultdict(float)
    by_hold: dict[tuple[str, str, str], float] = defaultdict(float)
    returns: dict[tuple[str, str], float] = defaultdict(float)
    for m in s.scalars(select(SdMove).where(SdMove.tenant_id == tenant)).all():
        if m.from_pos == "available" and m.to_pos in ("used", "holder"):
            by_work[(m.item_id, m.work)] += m.qty
            if m.to_pos == "holder":
                by_hold[(m.holder, m.item_id, m.work)] += m.qty
        elif m.to_pos == "available" and m.from_pos in ("used", "holder"):
            by_work[(m.item_id, m.work)] -= m.qty
            returns[(m.item_id, m.work)] += m.qty
            if m.from_pos == "holder":
                by_hold[(m.holder, m.item_id, m.work)] -= m.qty
    return {"work": by_work, "hold": by_hold, "returns": returns}


def reconcile(tenant: str, item: str = "") -> dict[str, Any]:
    tables()
    st = settings(tenant)
    with session() as s:
        its = {r.id: r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()}
        only = find_item(s, tenant, item).id if item else None
        fl = _flows(s, tenant)
        buds = [b for b in s.scalars(select(SdBudget).where(SdBudget.tenant_id == tenant)).all() if only is None or b.item_id == only]
        rows, seen = [], set()
        tot: dict[str, dict[str, float]] = defaultdict(lambda: {"theo": 0.0, "actual": 0.0, "allowed": 0.0})
        for b in buds:
            it = its.get(b.item_id)
            if it is None:
                continue
            seen.add((b.item_id, b.work))
            theo = b.qty * b.done / 100
            issued = fl["work"].get((b.item_id, b.work), 0.0)
            actual = issued - b.unused
            al = _allow(b, it, st)
            allowed = theo * (1 + al / 100)
            var = actual - theo
            pct = (var / theo * 100) if theo else None
            excess = max(actual - allowed, 0.0)
            hints = []
            if theo == 0 and actual > 1e-9:
                hints.append("Material went to this work but no progress is recorded for it - check the % done")
            if excess > 1e-9 and any(w in it.name.lower() for w in STEEL) and fl["returns"].get((b.item_id, b.work), 0) <= 1e-9:
                hints.append("No cut pieces or scrap were returned from this work - count what is lying at the work front before deciding")
            if excess > 1e-9 and b.unused == 0 and b.done < 100:
                hints.append("Nothing is recorded as unused at the work front while the work is not finished")
            if b.done == 0 and not issued:
                hints.append("Not started")
            rows.append({"work": b.work, "name": b.name, "item_id": it.id, "item": it.name, "unit": it.unit, "qty": round(b.qty, 3), "done": b.done,
                         "theoretical": round(theo, 3), "issued": round(issued, 3), "unused": round(b.unused, 3), "actual": round(actual, 3),
                         "variance": round(var, 3), "pct": round(pct, 2) if pct is not None else None, "allowance": al,
                         "excess": round(excess, 3), "value": round(excess * (it.price or 0), 2), "hints": hints})
            t = tot[it.id]
            t["theo"] += theo
            t["actual"] += actual
            t["allowed"] += allowed
        nobud = [{"item": its[i].name, "work": w or "(no work named)", "issued": round(q, 3), "unit": its[i].unit}
                 for (i, w), q in fl["work"].items() if (i, w) not in seen and q > 1e-9 and i in its and (only is None or i == only)]
        items = []
        for iid, t in tot.items():
            it = its[iid]
            v = t["actual"] - t["theo"]
            items.append({"item_id": iid, "item": it.name, "unit": it.unit, "theoretical": round(t["theo"], 3), "actual": round(t["actual"], 3),
                          "pct": round(v / t["theo"] * 100, 2) if t["theo"] else None, "excess": round(max(t["actual"] - t["allowed"], 0), 3),
                          "value": round(max(t["actual"] - t["allowed"], 0) * (it.price or 0), 2)})
        holders = _holders(s, tenant, st, its, fl, buds, only)
    over = [r for r in rows if r["excess"] > 1e-9]
    return {"rows": rows, "items": sorted(items, key=lambda r: -(r["value"] or 0)), "holders": holders, "no_budget": nobud,
            "currency": st["currency"],
            "say": (f"{len(rows)} work package line(s) reconciled; {len(over)} over their allowance" +
                    (f", most on {max(over, key=lambda r: r['value'])['work']}" if over else "") + "." +
                    (f" {len(nobud)} issue line(s) have no QS quantity to compare with." if nobud else ""))}


def _holders(s, tenant: str, st: dict[str, Any], its: dict[str, SdItem], fl: dict[str, Any], buds: list[SdBudget], only: str | None) -> list[dict[str, Any]]:
    hs = {h.name.lower(): h for h in s.scalars(select(SdHolder).where(SdHolder.tenant_id == tenant)).all()}
    bud = {(b.item_id, b.work): b for b in buds}
    agg: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: {"theo": 0.0, "actual": 0.0})
    for (h, i, w), q in fl["hold"].items():
        if only and i != only:
            continue
        b = bud.get((i, w))
        total_to_work = fl["work"].get((i, w), 0.0)
        share = (q / total_to_work) if total_to_work > 1e-9 else 1.0
        theo = (b.qty * b.done / 100 * share) if b else 0.0
        unused = (b.unused * share) if b else 0.0
        agg[(h, i)]["theo"] += theo
        agg[(h, i)]["actual"] += q - unused
    out = []
    for (h, i), t in agg.items():
        it = its.get(i)
        if it is None:
            continue
        hr = hs.get(h.lower())
        al = _allow(None, it, st, hr)
        allowed = t["theo"] * (1 + al / 100)
        excess = max(t["actual"] - allowed, 0.0)
        rate = float((hr.rate or {}).get(i)) if hr and (hr.rate or {}).get(i) is not None else None
        rec = round(excess * rate * (1 + (hr.uplift or 0) / 100), 2) if rate is not None and hr is not None else None
        out.append({"holder": h, "item_id": i, "item": it.name, "unit": it.unit, "theoretical": round(t["theo"], 3), "actual": round(t["actual"], 3),
                    "pct": round((t["actual"] - t["theo"]) / t["theo"] * 100, 2) if t["theo"] else None, "allowance": al,
                    "excess": round(excess, 3), "rate": rate, "uplift": hr.uplift if hr else None, "recovery": rec,
                    "clause": hr.clause if hr else "", "known": hr is not None})
    return sorted(out, key=lambda r: -(r["recovery"] or 0))


def draft_recovery(tenant: str, holder: str, item: str, who: str = "") -> dict[str, Any]:
    """A recovery DRAFT for the Contracts desk, with the clause it rests on. Deducting it is her decision."""
    r = reconcile(tenant, item)
    row = next((x for x in r["holders"] if x["holder"].lower() == S(holder, 120).lower()), None)
    if row is None:
        raise StoreError(f"{holder} holds no free-issue {item} to reconcile.")
    if row["excess"] <= 1e-9:
        raise StoreError(f"{holder} is within the allowance on {row['item']}: nothing to recover.")
    if row["recovery"] is None:
        raise StoreError(f"No rate for {row['item']} in {holder}'s subcontract record - add the rate and the clause first.")
    with LOCK, session() as s:
        d = SdDoc(tenant_id=tenant, kind="recovery", number=number(s, tenant, "recovery"), status="draft", party=row["holder"],
                  data={**row, "currency": r["currency"], "for": "Contracts desk"}, who=S(who, 80), day=today(tenant).isoformat())
        s.add(d)
        s.flush()
        v = doc_view(s, d)
    v["say"] = (f"{v['number']}: {row['holder']} used {show_qty({'unit': row['unit']}, row['excess'])} of {row['item']} beyond the {row['allowance']:g}% allowance; "
                f"at the subcontract rate that is {r['currency']} {row['recovery']:,.2f}" + (f" ({row['clause']})" if row["clause"] else "") +
                ". A draft for the Contracts desk - whether to deduct it is your decision.")
    return v


def decide_recovery(tenant: str, id: str, decision: str, who: str, note: str = "") -> dict[str, Any]:
    if decision not in ("deduct", "waive", "sent"):
        raise StoreError("Decision: deduct, waive or sent (to the Contracts desk).")
    if not S(who):
        raise StoreError("Give the name of the person deciding.")
    with LOCK, session() as s:
        d = get_doc(s, tenant, id, "recovery")
        d.status, d.approver = {"deduct": "deduct", "waive": "waived", "sent": "sent"}[decision], S(who, 80)
        d.data = {**(d.data or {}), "decision_note": S(note, 300)}
        d.updated_at = now()
        v = doc_view(s, d)
    v["say"] = f"{v['number']} marked {v['status']} by {who}. Hoola deducts nothing - the Contracts desk and your accounts do that."
    return v


# ---------------------------------------------------------------- scrap and write-off
def scrap(tenant: str, item: str, qty: Any, who: str, role: str, reason: str, store: str = "", unit: str = "", sale_value: Any = None,
          buyer: str = "", from_blocked: bool = False) -> dict[str, Any]:
    """Scrap or a scrap sale: the approver her tiers name for that value (by role)."""
    tables()
    who, role, reason = S(who, 80), S(role, 60), S(reason, 300)
    if not who or not reason:
        raise StoreError("Scrapping needs the approver's name and the reason.")
    with LOCK, session() as s:
        it = find_item(s, tenant, item)
        from .core import to_base
        base, qin, uin = to_base(it, qty, unit)
        sid = store_id(s, tenant, store)
        pos = "blocked" if from_blocked else "available"
        picks = lots_fifo(s, tenant, it, sid, pos, base)
        value = sum(q * lot_cost(s, l, it) for l, q in picks)
        t = tier_for(tenant, value)
        if role.lower() != t["who"].lower():
            raise StoreError(f"Scrapping {show_qty(it, base)} of {it.name} (value {value:,.2f}) is approved by the {t['who']}, per your tiers.")
        sv = num(sale_value, "Sale value", allow_zero=True) if sale_value not in (None, "") else None
        n = number(s, tenant, "scrap")
        for l, q in picks:
            post(s, tenant, "scrap", it, q, (sid, pos), ("", "scrap"), lot=l, cost=lot_cost(s, l, it),
                 doc={"scrap": n, "sale": (sv * q / base) if sv is not None else None, "buyer": S(buyer, 120)}, who=who,
                 approver=f"{who} ({role})", note=reason, day=today(tenant).isoformat(), qty_in=qin, unit_in=uin)
        s.add(SdDoc(tenant_id=tenant, kind="adjust", number=n, status="approved", store_id=sid, approver=f"{who} ({role})",
                    data={"item_id": it.id, "item": it.name, "unit": it.unit, "qty": -base, "value": -round(value, 2), "reason": reason, "scrap": True,
                          "sale": sv, "buyer": S(buyer, 120)}, day=today(tenant).isoformat()))
    return {"value": round(value, 2), "say": f"{n}: {show_qty(it, base)} of {it.name} scrapped (value {value:,.2f})" + (f", sold for {sv:,.2f} to {buyer}" if sv else "") + f" - approved by {who}."}


# ---------------------------------------------------------------- month-end and close-out
def month_end(tenant: str, month: str = "") -> dict[str, Any]:
    tables()
    st = settings(tenant)
    m = S(month, 7) or today(tenant).strftime("%Y-%m")
    try:
        first = date.fromisoformat(m + "-01")
    except ValueError:
        raise StoreError("Month: YYYY-MM.")
    nxt = (first + timedelta(days=32)).replace(day=1)
    a, b = first.isoformat(), (nxt - timedelta(days=1)).isoformat()
    with session() as s:
        val = valuation(s, tenant)
        grni, gval = [], 0.0
        for d in s.scalars(select(SdDoc).where(SdDoc.tenant_id == tenant, SdDoc.kind == "grn", SdDoc.status == "confirmed")).all():
            if (d.data or {}).get("invoiced"):
                continue
            v = 0.0
            for ln in d.lines or []:
                from .models import SdLot
                lot = s.get(SdLot, ln.get("lot_id")) if ln.get("lot_id") else None
                v += ln.get("accept", 0) * ((lot.cost if lot else 0) or 0)
            grni.append({"number": d.number, "supplier": d.party, "day": d.day, "value": round(v, 2), "doc_no": (d.data or {}).get("doc_no", "")})
            gval += v
        moves = s.scalars(select(SdMove).where(SdMove.tenant_id == tenant, SdMove.day >= a, SdMove.day <= b)).all()
        its = {r.id: r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()}
        wo = sum(x.qty * x.cost for x in moves if x.to_pos in ("adjust", "scrap") and x.from_pos in ("available", "blocked"))
        gain = sum(x.qty * x.cost for x in moves if x.from_pos == "adjust")
        sales = sum(float((x.doc or {}).get("sale") or 0) for x in moves if x.to_pos == "scrap")
        by_work: dict[str, float] = defaultdict(float)
        for x in moves:
            if x.from_pos == "available" and x.to_pos in ("used", "holder"):
                by_work[x.work or "(no work named)"] += x.qty * x.cost
            elif x.to_pos == "available" and x.from_pos in ("used", "holder"):
                by_work[x.work or "(no work named)"] -= x.qty * x.cost
        recv = sum(x.qty * x.cost for x in moves if x.from_pos == "outside")
    rec = reconcile(tenant)
    th = sum(r["theoretical"] * (its[r["item_id"]].price or 0) for r in rec["rows"] if r["item_id"] in its)
    ac = sum(r["actual"] * (its[r["item_id"]].price or 0) for r in rec["rows"] if r["item_id"] in its)
    return {"month": m, "currency": st["currency"], "valuation": val, "grni": grni, "grni_value": round(gval, 2), "write_offs": round(wo, 2),
            "gains": round(gain, 2), "scrap_sales": round(sales, 2), "received": round(recv, 2),
            "by_work": sorted(({"work": k, "value": round(v, 2)} for k, v in by_work.items()), key=lambda r: -r["value"]),
            "wastage_pct": round((ac - th) / th * 100, 2) if th else None}


def close_out(tenant: str, store: str = "") -> dict[str, Any]:
    """What is left at the end of a project: stock to transfer, return or sell as scrap, holders to settle, papers still open."""
    tables()
    with session() as s:
        names = store_names(s, tenant)
        sid = store_id(s, tenant, store) if store else None
        its = {r.id: r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()}
        left: dict[tuple[str, str, str], float] = defaultdict(float)
        holders: dict[tuple[str, str], float] = defaultdict(float)
        for (i, l, stx, p, h), q in balances(s, tenant).items():
            if p == "holder":
                holders[(h, i)] += q
            elif sid is None or stx == sid:
                left[(stx, i, p)] += q
        openp = [doc_view(s, d) for d in s.scalars(select(SdDoc).where(SdDoc.tenant_id == tenant, SdDoc.status.in_(("draft", "waiting", "transit", "short", "counting", "recount")))).all()]
    return {"surplus": [{"store": names.get(st, ""), "item": its[i].name, "unit": its[i].unit, "where": p, "qty": round(q, 3),
                         "value": round(q * (its[i].price or 0), 2)} for (st, i, p), q in sorted(left.items()) if q > 1e-9 and i in its],
            "holders": [{"holder": h, "item": its[i].name, "unit": its[i].unit, "qty": round(q, 3)} for (h, i), q in holders.items() if q > 1e-9 and i in its],
            "open": [{"number": d["number"], "kind": d["kind"], "status": d["status"]} for d in openp],
            "say": "Each line: transfer to another project, return to the supplier, sell as scrap or keep - each decided by a named person."}
