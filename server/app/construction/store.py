"""#61 Material Planner & Store Manager (v0.512.0, Wave 1). GRN in, issue out, min-max by consumption
norm, and the reconciliation Hoola owns end to end (tier A): received vs issued vs on-hand with the
wastage %, so the store in-charge signs a clean sheet instead of guessing. Cement / steel stock alerts
ride the DPR. Hoola never invents a rate or a quantity; the GRN carries the challan / invoice number."""
from __future__ import annotations

from sqlalchemy import select

from ..db import new_id, session
from . import gates
from .common import (CstError, _LOCK, _date, _dump, _j, _num, _rs, publish, today)
from .models import CStoreGrn, CStoreIssue, CStoreLot


def upsert_lot(tenant: str, item: str, unit: str = "", min_qty=None, max_qty=None, note: str = "") -> dict:
    name = str(item or "").strip()
    if not name:
        raise CstError("Item ka naam bataiye (jaise 'Cement OPC 53').")
    with _LOCK, session() as s:
        x = next((r for r in s.scalars(select(CStoreLot).where(CStoreLot.tenant_id == tenant)).all()
                  if r.item.lower() == name.lower()), None)
        new = x is None
        if new:
            x = CStoreLot(tenant_id=tenant, item=name[:120])
            s.add(x)
        if unit:
            x.unit = unit[:12]
        if min_qty not in (None, ""):
            x.min_qty = abs(_num(min_qty))
        if max_qty not in (None, ""):
            x.max_qty = abs(_num(max_qty))
        if note:
            x.note = note[:200]
        s.flush()                                               # defaults (min/max 0.0) land before the say
        return {"item": x.item, "unit": x.unit, "min_qty": x.min_qty, "max_qty": x.max_qty,
                "say": f"{'Naya' if new else 'Update'} store item: {x.item} ({x.unit or '-'}), min {x.min_qty:g}, max {x.max_qty:g}."}


def grn(tenant: str, item: str, qty, rate=None, vendor: str = "", invoice_no: str = "", vehicle: str = "",
        site: str = "", day: str = "", ok: bool = True, note: str = "", by: str = "", conv: str = "") -> dict:
    q = _num(qty)
    if not str(item or "").strip() or q <= 0:
        raise CstError("Item aur maatra (qty) bataiye.")
    d = _date(day, today(tenant))
    with _LOCK, session() as s:
        lot = _lot(s, tenant, item, unit_hint="")
        s.add(CStoreGrn(tenant_id=tenant, item=lot.item.lower(), unit=lot.unit, qty=q, rate=_num(rate), vendor=vendor[:160],
                        invoice_no=str(invoice_no)[:60], vehicle=str(vehicle)[:40], site=site[:160],
                        day=d.isoformat(), ok=bool(ok), note=note[:300], by=by[:80]))
        lot_id, bal, minq, unit = lot.id, balance(s, tenant, lot.item), lot.min_qty, lot.unit
    alert = f" Reorder level {minq:g} {unit} se neeche!" if (minq and bal <= minq) else ""
    say = f"GRN: {lot.item} {q:g} {unit} aaya ({vendor or 'vendor? '}, challan {invoice_no or '-'}). Stock ab {bal:g} {unit}.{alert}"
    publish(tenant, "const_store", {"kind": "grn", "item": lot.item, "qty": q}, conv)
    return {"item": lot.item, "balance": bal, "say": say}


def issue(tenant: str, item: str, qty, site: str = "", gang: str = "", purpose: str = "", day: str = "",
          waste: bool = False, by: str = "", note: str = "", conv: str = "") -> dict:
    q = _num(qty)
    if not str(item or "").strip() or q <= 0:
        raise CstError("Item aur maatra (qty) bataiye.")
    d = _date(day, today(tenant))
    with _LOCK, session() as s:
        lot = _lot(s, tenant, item, unit_hint="")
        bal = balance(s, tenant, lot.item)
        if bal < q:
            raise CstError(f"{lot.item}: stock {bal:g} {lot.unit} hai, {q:g} nahi. Pehle GRN yaado.")
        s.add(CStoreIssue(tenant_id=tenant, item=lot.item.lower(), unit=lot.unit, qty=q, site=site[:160], gang=gang[:120],
                          purpose=purpose[:200], day=d.isoformat(), waste=bool(waste), by=by[:80], note=note[:300]))
        bal2 = balance(s, tenant, lot.item)
        lot_id, minq, unit, lot_name = lot.id, lot.min_qty, lot.unit, lot.item
    alert = f" Reorder level {minq:g} {unit} se neeche!" if (minq and bal2 <= minq) else ""
    say = f"Issue: {lot_name} {q:g} {unit} {'(wastage likha)' if waste else ''} -> {site or '-'}{' / ' + gang if gang else ''}. Stock ab {bal2:g} {unit}.{alert}"
    publish(tenant, "const_store", {"kind": "issue", "item": lot_name, "qty": q}, conv)
    return {"item": lot_name, "balance": bal2, "say": say}


def _lot(s, tenant: str, item: str, unit_hint: str = "") -> CStoreLot:
    name = str(item).strip()
    x = next((r for r in s.scalars(select(CStoreLot).where(CStoreLot.tenant_id == tenant)).all()
              if r.item.lower() == name.lower()), None)
    if x is None:
        x = CStoreLot(tenant_id=tenant, item=name[:120], unit=unit_hint[:12])
        s.add(x)
        s.flush()
    return x


def balance(s, tenant: str, item: str) -> float:
    item_l = str(item).strip().lower()
    got = sum(g.qty for g in s.scalars(select(CStoreGrn).where(CStoreGrn.tenant_id == tenant, CStoreGrn.item == item_l)).all())
    out = sum(i.qty for i in s.scalars(select(CStoreIssue).where(CStoreIssue.tenant_id == tenant, CStoreIssue.item == item_l)).all())
    return round(got - out, 3)


def reconcile(tenant: str, item: str = "") -> dict:
    """Received vs issued vs on-hand vs written-off, with the wastage % - the sheet the store in-charge signs."""
    with session() as s:
        rows = s.scalars(select(CStoreLot).where(CStoreLot.tenant_id == tenant)).all()
        if item:
            rows = [r for r in rows if r.item.lower() == str(item).strip().lower()]
            if not rows:
                raise CstError(f"'{item}' store mein nahi.")
        out = []
        for lot in rows:
            got = sum(g.qty for g in s.scalars(select(CStoreGrn).where(CStoreGrn.tenant_id == tenant, CStoreGrn.item == lot.item.lower())).all())
            iss = s.scalars(select(CStoreIssue).where(CStoreIssue.tenant_id == tenant, CStoreIssue.item == lot.item.lower())).all()
            used = sum(i.qty for i in iss if not i.waste)
            waste = sum(i.qty for i in iss if i.waste)
            on_hand = round(got - used - waste, 3)
            w_pct = round(waste * 100 / got, 2) if got else 0.0
            out.append({"item": lot.item, "unit": lot.unit, "received": round(got, 3), "issued": round(used, 3),
                        "waste": round(waste, 3), "on_hand": on_hand, "wastage_pct": w_pct,
                        "min": lot.min_qty, "reorder": bool(lot.min_qty and on_hand <= lot.min_qty)})
        low = [r["item"] for r in out if r["reorder"]]
        say = (f"Milan: {len(out)} item. " + "; ".join(
            f"{r['item']}: aaya {r['received']:g}, gaya {r['issued']:g}, barbadi {r['waste']:g} ({r['wastage_pct']:g}%), bacha {r['on_hand']:g} {r['unit']}"
            for r in out[:4]) + ("..." if len(out) > 4 else ""))
        if low:
            say += f" DOBARA MANGWAO: {', '.join(low)}."
        return {"items": out, "say": say}


def lots(tenant: str) -> list[dict]:
    with session() as s:
        return [{"item": r.item, "unit": r.unit, "min_qty": r.min_qty, "max_qty": r.max_qty,
                 "balance": balance(s, tenant, r.item)} for r in s.scalars(select(CStoreLot).where(CStoreLot.tenant_id == tenant)).all()]
