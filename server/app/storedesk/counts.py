"""Counts: a plan by class (A often, C rarely), blind count sheets (the book quantity is hidden until both counters have entered
theirs), two counters, a recount by a third person when the difference is over tolerance, and an adjustment that waits for the
approver her value tiers name. Every receipt, slip and transfer for that store must be closed before the count starts. Hoola never
posts an adjustment."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from ..db import now, session
from .core import (LOCK, S, SdDoc, SdItem, StoreError, abc, balances, doc_view, find_item, get_doc, lot_cost, lots_fifo, num, number,
                   post, settings, show_qty, store_id, store_names, tables, tier_for, today)
from .models import SdMove

HIDE = ("book", "diff", "pct", "value")


def _last_counted(s, tenant: str) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for d in s.scalars(select(SdDoc).where(SdDoc.tenant_id == tenant, SdDoc.kind == "count", SdDoc.status == "closed")).all():
        for ln in d.lines or []:
            k = (d.store_id, ln["item_id"])
            out[k] = max(out.get(k, ""), d.day or "")
    return out


def plan(tenant: str) -> list[dict[str, Any]]:
    """Items due a count in each store: by class and her days, plus items whose records were corrected lately."""
    tables()
    st = settings(tenant)
    days = st["count_days"]
    with session() as s:
        cls = abc(s, tenant)
        last = _last_counted(s, tenant)
        names = store_names(s, tenant)
        its = {r.id: r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()}
        since = (today(tenant) - timedelta(days=30)).isoformat()
        odd = {m.item_id for m in s.scalars(select(SdMove).where(SdMove.tenant_id == tenant, SdMove.kind == "reverse", SdMove.day >= since)).all()}
        where: dict[tuple[str, str], float] = {}
        for (i, l, stx, p, h), q in balances(s, tenant).items():
            if p in ("available", "hold", "blocked") and stx:
                where[(stx, i)] = where.get((stx, i), 0.0) + q
        out = []
        for (sid, iid), q in where.items():
            it = its.get(iid)
            if it is None or q <= 1e-9:
                continue
            c = cls.get(iid, "C")
            lastd = last.get((sid, iid), "")
            due_in = int(days.get(c, 90))
            age = (today(tenant) - date.fromisoformat(lastd)).days if lastd else None
            due = age is None or age >= due_in or iid in odd
            out.append({"store_id": sid, "store": names.get(sid, ""), "item_id": iid, "item": it.name, "class": c, "last": lastd,
                        "every": due_in, "due": due, "why": "corrected lately" if iid in odd else ("never counted" if lastd == "" else f"last counted {age} days ago")})
        return sorted(out, key=lambda r: (not r["due"], r["class"], r["item"]))


def _pending(s, tenant: str, sid: str) -> list[str]:
    out = []
    for d in s.scalars(select(SdDoc).where(SdDoc.tenant_id == tenant, SdDoc.kind.in_(("grn", "slip")), SdDoc.status.in_(("draft", "transit")))).all():
        if d.store_id == sid or (d.data or {}).get("to_store") == sid:
            out.append(d.number)
    return out


def open_count(tenant: str, store: str = "", items: list[str] | None = None, counters: list[str] | None = None) -> dict[str, Any]:
    tables()
    cs = [S(c, 80) for c in (counters or []) if S(c, 80)]
    if len(cs) != 2 or cs[0].lower() == cs[1].lower():
        raise StoreError("A count needs two different people counting. Give both names.")
    with LOCK, session() as s:
        sid = store_id(s, tenant, store)
        pend = _pending(s, tenant, sid)
        if pend:
            raise StoreError("Close these first, so the book is right before counting: " + ", ".join(pend[:12]) + ".")
        bal = balances(s, tenant)
        on: dict[str, float] = {}
        for (i, l, stx, p, h), q in bal.items():
            if stx == sid and p in ("available", "hold", "blocked"):
                on[i] = on.get(i, 0.0) + q
        if items:
            ids = [find_item(s, tenant, x).id for x in items]
        else:
            ids = [r["item_id"] for r in plan(tenant) if r["store_id"] == sid and r["due"]]
            if not ids:
                ids = [i for i, q in on.items() if q > 1e-9]
        if not ids:
            raise StoreError("Nothing in that store to count.")
        its = {r.id: r for r in s.scalars(select(SdItem).where(SdItem.id.in_(ids))).all()}
        lines = [{"item_id": i, "item": its[i].name, "unit": its[i].unit, "book": round(on.get(i, 0.0), 6), "c1": None, "c2": None, "c3": None,
                  "result": "to count"} for i in ids if i in its]
        d = SdDoc(tenant_id=tenant, kind="count", number=number(s, tenant, "count"), status="counting", store_id=sid,
                  data={"counters": cs, "recounter": ""}, lines=lines, day=today(tenant).isoformat())
        s.add(d)
        s.flush()
        v = _view(s, d)
    v["say"] = f"Count {v['number']} open for {len(lines)} item(s): two counters, blind - the book shows after both have counted."
    return v


def _view(s, d: SdDoc) -> dict[str, Any]:
    v = doc_view(s, d)
    both = all(ln.get("c1") is not None and ln.get("c2") is not None for ln in d.lines or [])
    if not both and d.status == "counting":
        v["lines"] = [{k: x for k, x in ln.items() if k not in HIDE} for ln in v["lines"]]
        v["blind"] = True
    return v


def enter(tenant: str, id: str, who: str, counts: dict[str, Any]) -> dict[str, Any]:
    """A counter enters their figures (item -> quantity in the base unit)."""
    tables()
    who = S(who, 80)
    st = settings(tenant)
    with LOCK, session() as s:
        d = get_doc(s, tenant, id, "count")
        if d.status not in ("counting", "recount"):
            raise StoreError(f"{d.number} is {d.status}.")
        x = d.data or {}
        cs = x.get("counters") or []
        if d.status == "counting":
            if who.lower() not in [c.lower() for c in cs]:
                raise StoreError(f"{d.number} is counted by {' and '.join(cs)}.")
            slot = "c1" if who.lower() == cs[0].lower() else "c2"
        else:
            rc = x.get("recounter") or ""
            if not rc:
                raise StoreError("Name the person recounting first (not one of the two counters).")
            if who.lower() != rc.lower():
                raise StoreError(f"The recount is by {rc}.")
            slot = "c3"
        lines = [dict(ln) for ln in d.lines]
        its = {r.id: r for r in s.scalars(select(SdItem).where(SdItem.id.in_([ln["item_id"] for ln in lines]))).all()}
        for k, v in (counts or {}).items():
            it = find_item(s, tenant, k)
            ln = next((y for y in lines if y["item_id"] == it.id), None)
            if ln is None:
                raise StoreError(f"{it.name} is not on {d.number}.")
            ln[slot] = num(v, f"Count for {it.name}", allow_zero=True)
        tol = float(st["tolerance"])
        for ln in lines:
            it = its[ln["item_id"]]
            t = it.tol_pct if it.tol_pct >= 0 else tol
            if d.status == "counting" and ln.get("c1") is not None and ln.get("c2") is not None:
                c1, c2 = ln["c1"], ln["c2"]
                agree = abs(c1 - c2) <= max(abs(c1), abs(c2), 1e-9) * t / 100
                counted = (c1 + c2) / 2 if agree else None
                _settle(ln, counted, t, it, s, d.tenant_id, agree)
            elif d.status == "recount" and ln.get("result") == "recount" and ln.get("c3") is not None:
                _settle(ln, ln["c3"], t, it, s, d.tenant_id, True, final=True)
        d.lines = lines
        if all(ln.get("result") not in ("to count", "recount") for ln in lines):
            d.status = "closed"
            _adjust_drafts(s, d, its)
        elif any(ln.get("result") == "recount" for ln in lines) and all(ln.get("c1") is not None and ln.get("c2") is not None for ln in lines):
            d.status = "recount"
        d.updated_at = now()
        v = _view(s, d)
    rc = sum(1 for ln in v["lines"] if ln.get("result") == "recount")
    v["say"] = (f"{v['number']}: " + (f"{rc} item(s) need a recount by a third person." if rc else
                                      "closed." if v["status"] == "closed" else "waiting for the other counter."))
    return v


def _settle(ln: dict[str, Any], counted: float | None, tol: float, it: SdItem, s, tenant: str, agree: bool, final: bool = False) -> None:
    if counted is None:
        ln["result"] = "recount"
        ln["why"] = "the two counts do not agree"
        return
    book = ln["book"]
    diff = counted - book
    pct = (diff / book * 100) if book else (0.0 if diff == 0 else 100.0)
    ln.update({"counted": round(counted, 6), "diff": round(diff, 6), "pct": round(pct, 2), "value": round(diff * (it.price or 0), 2)})
    if abs(diff) <= 1e-9:
        ln["result"] = "matches"
    elif abs(pct) <= tol + 1e-9 and not final:
        ln["result"] = "within"
    elif not final:
        ln["result"] = "recount"
        ln["why"] = f"{pct:+.1f}% against your ±{tol:g}%"
    else:
        ln["result"] = "within" if abs(pct) <= tol + 1e-9 else "adjust"


def recounter(tenant: str, id: str, who: str) -> dict[str, Any]:
    who = S(who, 80)
    with LOCK, session() as s:
        d = get_doc(s, tenant, id, "count")
        cs = [c.lower() for c in (d.data or {}).get("counters") or []]
        if not who or who.lower() in cs:
            raise StoreError("The recount is by a third person - not one of the two counters.")
        d.data = {**(d.data or {}), "recounter": who}
        d.updated_at = now()
        v = _view(s, d)
    v["say"] = f"{who} recounts {d.number}."
    return v


def _adjust_drafts(s, d: SdDoc, its: dict[str, SdItem]) -> None:
    for ln in d.lines:
        if ln.get("result") not in ("adjust", "within") or abs(ln.get("diff") or 0) <= 1e-9:
            continue
        it = its[ln["item_id"]]
        t = tier_for(d.tenant_id, ln.get("value") or 0)
        a = SdDoc(tenant_id=d.tenant_id, kind="adjust", number=number(s, d.tenant_id, "adjust"), status="waiting", store_id=d.store_id,
                  data={"item_id": it.id, "item": it.name, "unit": it.unit, "qty": ln["diff"], "value": ln.get("value") or 0, "count": d.number,
                        "count_id": d.id, "tier": t, "reason": "", "within": ln["result"] == "within"},
                  day=today(d.tenant_id).isoformat())
        s.add(a)
        s.flush()
        ln["adjust"] = a.number


def approve_adjust(tenant: str, id: str, who: str, role: str, reason: str, decision: str = "approve") -> dict[str, Any]:
    """The approver her tiers name posts the adjustment (or turns it down). The role must be the tier's."""
    tables()
    who, role, reason = S(who, 80), S(role, 60), S(reason, 300)
    if not who:
        raise StoreError("Give the approver's name.")
    if not reason:
        raise StoreError("Give the reason: count error, damage, theft suspected, unit mix-up, an issue never recorded.")
    with LOCK, session() as s:
        a = get_doc(s, tenant, id, "adjust")
        if a.status != "waiting":
            raise StoreError(f"{a.number} is already {a.status}.")
        x = a.data or {}
        need = (x.get("tier") or {}).get("who", "")
        if decision == "approve" and need and role.lower() != need.lower():
            raise StoreError(f"{a.number} is worth {x.get('value', 0):,.2f}: it is approved by the {need}, per your tiers.")
        it = s.get(SdItem, x["item_id"])
        if decision == "approve":
            q = float(x["qty"])
            day = today(tenant).isoformat()
            ref = {"adjust": a.number, "count": x.get("count", "")}
            if q > 0:
                post(s, tenant, "adjust", it, q, ("", "adjust"), (a.store_id, "available"), cost=it.price, doc=ref, who=who, approver=f"{who} ({role})",
                     note=reason, day=day)
            else:
                for l, lq in lots_fifo(s, tenant, it, a.store_id, "available", -q):
                    post(s, tenant, "adjust", it, lq, (a.store_id, "available"), ("", "adjust"), lot=l, cost=lot_cost(s, l, it), doc=ref, who=who,
                         approver=f"{who} ({role})", note=reason, day=day)
            a.status = "approved"
        elif decision == "reject":
            a.status = "rejected"
        else:
            raise StoreError("Decision: approve or reject.")
        a.approver = f"{who} ({role})"
        a.data = {**x, "reason": reason}
        a.updated_at = now()
        v = doc_view(s, a)
    v["say"] = f"{v['number']} {v['status']} by {who}: {show_qty(it, x['qty'])} of {it.name}."
    return v


def accuracy(tenant: str, days: int = 90) -> dict[str, Any]:
    """Share of counted value that matched the book within tolerance, over closed counts in the window."""
    tables()
    since = (today(tenant) - timedelta(days=days)).isoformat()
    with session() as s:
        its = {r.id: r for r in s.scalars(select(SdItem).where(SdItem.tenant_id == tenant)).all()}
        tot = ok = 0.0
        n = 0
        for d in s.scalars(select(SdDoc).where(SdDoc.tenant_id == tenant, SdDoc.kind == "count", SdDoc.status == "closed", SdDoc.day >= since)).all():
            for ln in d.lines or []:
                it = its.get(ln["item_id"])
                w = abs(ln.get("book") or 0) * ((it.price if it else 0) or 1)
                tot += w
                ok += w if ln.get("result") in ("matches", "within") else 0
                n += 1
        return {"lines": n, "accuracy": round(ok / tot, 4) if tot else None}
