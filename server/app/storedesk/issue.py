"""Issues, returns, transfers and free-issue material.

Every issue names the work it is for (a work package or cost code) - without it the material cannot be reconciled later, so it is
refused. Lots are picked oldest first and carried along, so 'which heat went into column C4' has an answer. A slip is drafted (by the
chat or the desk) and posted only when a named person confirms it. Free-issue material to a subcontractor stays the company's stock
'with' that holder until reconciliation. A transfer is two steps: out (in transit) and in at the other store; a short arrival is a
named difference, never lost stock."""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select

from ..db import now, session
from .core import (LOCK, S, SdDoc, SdHolder, SdItem, StoreError, balances, doc_view, find_item, get_doc, lot_cost, lots_fifo, num,
                   number, post, show_qty, store_id, store_names, tables, to_base, today)
from .models import SdBudget

KINDS = ("issue", "return", "transfer")


def holders(tenant: str) -> list[dict[str, Any]]:
    tables()
    with session() as s:
        return [{"id": r.id, "name": r.name, "allowance": r.allowance, "rate": r.rate or {}, "uplift": r.uplift, "clause": r.clause}
                for r in s.scalars(select(SdHolder).where(SdHolder.tenant_id == tenant).order_by(SdHolder.name)).all()]


def save_holder(tenant: str, name: str, allowance: Any = None, rates: dict | None = None, uplift: Any = None, clause: str = "",
                id: str = "") -> dict[str, Any]:
    """A subcontractor that holds free-issue material: the allowance and the recovery rate come from HER subcontract (with the clause)."""
    tables()
    name = S(name, 120)
    with LOCK, session() as s:
        r = None
        if id:
            r = s.get(SdHolder, id)
            if r is None or r.tenant_id != tenant:
                raise StoreError("That subcontractor is not yours.")
        else:
            if not name:
                raise StoreError("Give the subcontractor's name.")
            r = next((x for x in s.scalars(select(SdHolder).where(SdHolder.tenant_id == tenant)).all() if x.name.lower() == name.lower()), None)
            if r is None:
                r = SdHolder(tenant_id=tenant, name=name, rate={})
                s.add(r)
        if name:
            r.name = name
        if allowance not in (None, ""):
            a = num(allowance, "Allowance %", allow_zero=True)
            if a > 50:
                raise StoreError("Allowance: at most 50%.")
            r.allowance = a
        if rates:
            rr = dict(r.rate or {})
            for k, v in rates.items():
                it = find_item(s, tenant, k)
                rr[it.id] = num(v, f"Rate for {it.name}", allow_zero=True)
            r.rate = rr
        if uplift not in (None, ""):
            r.uplift = num(uplift, "Uplift %", allow_zero=True)
        if clause:
            r.clause = S(clause, 200)
        s.flush()
        return {"id": r.id, "name": r.name, "allowance": r.allowance, "rate": r.rate, "uplift": r.uplift, "clause": r.clause,
                "say": f"{r.name} saved" + (f" (allowance {r.allowance:g}%, clause {r.clause})" if r.allowance >= 0 and r.clause else "") + "."}


def _budget_line(s, tenant: str, it: SdItem, work: str, extra: float) -> dict[str, Any] | None:
    b = s.scalars(select(SdBudget).where(SdBudget.tenant_id == tenant, SdBudget.item_id == it.id, SdBudget.work == work)).first()
    if b is None or not b.qty:
        return None
    used = _work_used(s, tenant, it.id, work)
    allow = b.allowance if b.allowance >= 0 else (it.wastage if it.wastage >= 0 else None)
    from .core import settings as _st
    allow = allow if allow is not None else float(_st(tenant)["wastage"])
    budget = b.qty * (1 + allow / 100)
    after = used + extra
    return {"work": work, "name": b.name, "budget": round(budget, 3), "used": round(used, 3), "after": round(after, 3),
            "share": round(after / budget, 4) if budget else None, "over": after > budget + 1e-9}


def _work_used(s, tenant: str, item_id: str, work: str) -> float:
    from .models import SdMove
    q = 0.0
    for m in s.scalars(select(SdMove).where(SdMove.tenant_id == tenant, SdMove.item_id == item_id, SdMove.work == work)).all():
        if m.from_pos == "available" and m.to_pos in ("used", "holder"):
            q += m.qty
        elif m.to_pos == "available" and m.from_pos in ("used", "holder"):
            q -= m.qty
    return q


def draft_slip(tenant: str, kind: str, item: str, qty: Any, unit: str = "", store: str = "", to_store: str = "", work: str = "",
               holder: str = "", person: str = "", who: str = "", note: str = "", from_holder: str = "", id: str = "") -> dict[str, Any]:
    """An issue / return / transfer slip, checked, waiting for a named person to confirm it."""
    tables()
    if kind not in KINDS:
        raise StoreError("Slip: issue, return or transfer.")
    with LOCK, session() as s:
        it = find_item(s, tenant, item)
        base, qin, uin = to_base(it, qty, unit)
        sid = store_id(s, tenant, store)
        warn: list[str] = []
        data: dict[str, Any] = {"item_id": it.id, "item": it.name, "unit": it.unit, "qty": round(base, 6), "qty_in": qin, "unit_in": uin,
                                "work": S(work, 80), "holder": S(holder, 120), "person": S(person, 80), "note": S(note, 300),
                                "from_holder": S(from_holder, 120)}
        if kind == "issue":
            if not data["work"] and it.category != "tool":
                raise StoreError("Say which work it is for (a work package or cost code) - an issue without it cannot be reconciled.")
            if it.category == "tool" and not data["person"]:
                raise StoreError("A returnable tool is issued to a person: give the name.")
            have = sum(q for (i, l, st, p, h), q in balances(s, tenant, [it.id]).items() if st == sid and p == "available")
            if have + 1e-9 < base:
                raise StoreError(f"{it.name}: {show_qty(it, have)} available in {store_names(s, tenant).get(sid)}, not {show_qty(it, base)}.")
            picks = lots_fifo(s, tenant, it, sid, "available", base)
            data["lots"] = [{"lot": l, "qty": q} for l, q in picks]
            if data["holder"]:
                if not s.scalars(select(SdHolder).where(SdHolder.tenant_id == tenant)).all() or not any(
                        h.name.lower() == data["holder"].lower() for h in s.scalars(select(SdHolder).where(SdHolder.tenant_id == tenant)).all()):
                    warn.append(f"{data['holder']} has no allowance or recovery rate recorded yet - add them from the subcontract")
            bl = _budget_line(s, tenant, it, data["work"], base) if data["work"] else None
            if bl:
                data["budget"] = bl
                if bl["over"]:
                    warn.append(f"Takes {bl['work']} to {bl['share']:.0%} of its {it.name} budget (allowance included)")
            elif data["work"]:
                warn.append(f"No budget for {it.name} on {data['work']} yet - it cannot be reconciled until the QS quantity is in")
        elif kind == "return":
            if data["from_holder"]:
                have = sum(q for (i, l, st, p, h), q in balances(s, tenant, [it.id]).items() if p == "holder" and h.lower() == data["from_holder"].lower())
                if have + 1e-9 < base:
                    raise StoreError(f"{data['from_holder']} holds {show_qty(it, have)} of {it.name}, not {show_qty(it, base)}.")
            elif not data["work"]:
                raise StoreError("Say which work it comes back from (the same work package it was issued to).")
        else:
            tid = store_id(s, tenant, to_store)
            if tid == sid:
                raise StoreError("A transfer goes to another store.")
            data["to_store"] = tid
            have = sum(q for (i, l, st, p, h), q in balances(s, tenant, [it.id]).items() if st == sid and p == "available")
            if have + 1e-9 < base:
                raise StoreError(f"{it.name}: {show_qty(it, have)} available, not {show_qty(it, base)}.")
            data["lots"] = [{"lot": l, "qty": q} for l, q in lots_fifo(s, tenant, it, sid, "available", base)]
        data["warn"] = warn
        if id:
            d = get_doc(s, tenant, id, "slip")
            if d.status != "draft":
                raise StoreError(f"{d.number} is already {d.status}.")
        else:
            d = SdDoc(tenant_id=tenant, kind="slip", number=number(s, tenant, kind), status="draft")
            s.add(d)
        d.store_id, d.party, d.lines, d.data, d.who = sid, data["holder"] or data["person"] or data["from_holder"], [], {**data, "type": kind}, S(who, 80)
        d.day = today(tenant).isoformat()
        d.updated_at = now()
        s.flush()
        v = doc_view(s, d)
    word = {"issue": "Issue", "return": "Return", "transfer": "Transfer"}[kind]
    v["say"] = (f"{word} slip {v['number']}: {show_qty(it, base)} of {it.name}" + (f" for {data['work']}" if data["work"] else "") +
                (f" to {data['holder']}" if data["holder"] else "") + ". " + (" ".join(w + "." for w in warn) + " " if warn else "") +
                "A named person confirms it.")
    return v


def confirm_slip(tenant: str, id: str, who: str, received: Any = None) -> dict[str, Any]:
    tables()
    who = S(who, 80)
    if not who:
        raise StoreError("Who is confirming the slip? Give the person's name.")
    with LOCK, session() as s:
        d = get_doc(s, tenant, id, "slip")
        if d.status != "draft":
            raise StoreError(f"{d.number} is already {d.status}.")
        x = d.data or {}
        it = s.get(SdItem, x["item_id"])
        t, day = x["type"], today(tenant).isoformat()
        ref = {"slip": d.number, "slip_id": d.id}
        if t == "issue":
            picks = lots_fifo(s, tenant, it, d.store_id, "available", x["qty"])   # picked again: stock may have moved since the draft
            for l, q in picks:
                if x.get("holder"):
                    post(s, tenant, "issue_free", it, q, (d.store_id, "available"), ("", "holder"), lot=l, holder=x["holder"], work=x["work"],
                         cost=lot_cost(s, l, it), doc=ref, who=who, note=x.get("note", ""), day=day, qty_in=x["qty_in"], unit_in=x["unit_in"])
                else:
                    post(s, tenant, "issue", it, q, (d.store_id, "available"), ("", "used"), lot=l, work=x["work"] or ("tool: " + x["person"]),
                         cost=lot_cost(s, l, it), doc={**ref, "person": x.get("person", "")}, who=who, note=x.get("note", ""), day=day,
                         qty_in=x["qty_in"], unit_in=x["unit_in"])
            d.status = "posted"
        elif t == "return":
            if x.get("from_holder"):
                bal = balances(s, tenant, [it.id])
                left = x["qty"]
                for (i, l, st, p, h), q in sorted(bal.items(), key=lambda kv: kv[0][1]):
                    if p != "holder" or h.lower() != x["from_holder"].lower() or q <= 1e-9:
                        continue
                    take = min(q, left)
                    post(s, tenant, "return", it, take, ("", "holder"), (d.store_id, "available"), lot=l, holder=h, work=x.get("work", ""),
                         cost=lot_cost(s, l, it), doc=ref, who=who, note=x.get("note", ""), day=day)
                    left -= take
                    if left <= 1e-9:
                        break
            else:
                post(s, tenant, "return", it, x["qty"], ("", "used"), (d.store_id, "available"), work=x["work"], cost=it.price, doc=ref,
                     who=who, note=x.get("note", ""), day=day)
            d.status = "posted"
        else:
            picks = lots_fifo(s, tenant, it, d.store_id, "available", x["qty"])
            for l, q in picks:
                post(s, tenant, "transfer_out", it, q, (d.store_id, "available"), (x["to_store"], "transit"), lot=l, cost=lot_cost(s, l, it),
                     doc=ref, who=who, note=x.get("note", ""), day=day)
            x = {**x, "lots": [{"lot": l, "qty": q} for l, q in picks], "sent": day}
            d.data = x
            d.status = "transit"
        d.approver = who
        d.updated_at = now()
        v = doc_view(s, d)
    v["say"] = f"{v['number']} confirmed by {who}" + (" - in transit until the other store receives it." if v["status"] == "transit" else ".")
    return v


def receive_transfer(tenant: str, id: str, who: str, qty: Any = None) -> dict[str, Any]:
    """The other store receives a transfer. Less than was sent stays 'in transit' as a named difference for a person to settle."""
    tables()
    who = S(who, 80)
    if not who:
        raise StoreError("Who received it at the other store? Give the name.")
    with LOCK, session() as s:
        d = get_doc(s, tenant, id, "slip")
        x = d.data or {}
        if x.get("type") != "transfer" or d.status != "transit":
            raise StoreError(f"{d.number} is not a transfer in transit.")
        it = s.get(SdItem, x["item_id"])
        sent = x["qty"]
        got = to_base(it, qty, "")[0] if qty not in (None, "") else sent
        if got > sent + 1e-9:
            raise StoreError(f"More than was sent ({show_qty(it, sent)}): record the extra as its own receipt.")
        left, day = got, today(tenant).isoformat()
        for ln in x.get("lots") or [{"lot": "", "qty": sent}]:
            take = min(ln["qty"], left)
            if take > 1e-9:
                post(s, tenant, "transfer_in", it, take, (x["to_store"], "transit"), (x["to_store"], "available"), lot=ln["lot"],
                     cost=lot_cost(s, ln["lot"], it), doc={"slip": d.number, "slip_id": d.id}, who=who, day=day)
                left -= take
        short = round(sent - got, 6)
        d.data = {**x, "received": got, "received_by": who, "received_on": day, "short": short}
        d.status = "short" if short > 1e-9 else "posted"
        d.updated_at = now()
        v = doc_view(s, d)
    v["say"] = (f"{v['number']}: {show_qty(it, got)} received by {who}." +
                (f" {show_qty(it, short)} short - it stays in transit as a named difference until a person settles it." if short > 1e-9 else ""))
    return v


def cancel_slip(tenant: str, id: str, who: str) -> dict[str, Any]:
    with LOCK, session() as s:
        d = get_doc(s, tenant, id, "slip")
        if d.status != "draft":
            raise StoreError(f"{d.number} is {d.status}: a posted slip is reversed, not cancelled.")
        d.status, d.approver = "cancelled", S(who, 80)
        d.updated_at = now()
        v = doc_view(s, d)
    v["say"] = f"{v['number']} cancelled."
    return v


def transit(tenant: str) -> list[dict[str, Any]]:
    tables()
    with session() as s:
        names = store_names(s, tenant)
        out = []
        for d in s.scalars(select(SdDoc).where(SdDoc.tenant_id == tenant, SdDoc.kind == "slip", SdDoc.status.in_(("transit", "short")))).all():
            x = d.data or {}
            days = (today(tenant) - date.fromisoformat(x.get("sent") or d.day)).days if (x.get("sent") or d.day) else 0
            out.append({**doc_view(s, d), "from": names.get(d.store_id, ""),
                        "to": names.get(x.get("to_store"), ""), "days": days})
        return out


def held_by(tenant: str) -> list[dict[str, Any]]:
    """What each subcontractor holds of free-issue material, item by item."""
    tables()
    with session() as s:
        its = {r.id: r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()}
        agg: dict[tuple[str, str], float] = {}
        for (i, l, st, p, h), q in balances(s, tenant).items():
            if p == "holder":
                agg[(h, i)] = agg.get((h, i), 0.0) + q
        return [{"holder": h, "item_id": i, "item": its[i].name if i in its else "?", "unit": its[i].unit if i in its else "", "qty": round(q, 3)}
                for (h, i), q in sorted(agg.items()) if q > 1e-9]
