"""#91 Builder's Accounting & Reconciliation (v0.512.0, Wave 1, tier A). Project-wise books: one entry
per line, receipts in, payments / dues out, vendor ageing on the unsettled rows. The khata PATTERN comes
from net/khata.py (KhataAccount / KhataEntry); these are the builder's project books. Money moves on her
tap elsewhere (payroll / UPI / bank) - here Hoola keeps the record and says who is owed what."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _date, _num, _rs, today)
from .models import CBookEntry

HEADS = ("labour", "material", "hire", "subcontract", "approval", "misc", "receipt")


def entry(tenant: str, project: str, side: str, amount, head: str = "misc", party: str = "", day: str = "",
          settled: bool = True, due_day: str = "", ref: str = "", note: str = "", conv: str = "") -> dict:
    if (side or "") not in ("in", "out"):
        raise CstError("side: in (aaya) | out (gaya / dena hai)")
    amt = round(_num(amount), 2)
    if amt <= 0:
        raise CstError("Rakam bataiye.")
    if not str(project or "").strip():
        raise CstError("Project bataiye.")
    h = (head or "misc").strip().lower()
    if h not in HEADS:
        raise CstError("head: " + " | ".join(HEADS))
    d = _date(day, today(tenant))
    dd = _date(due_day)
    with _LOCK, session() as s:
        s.add(CBookEntry(tenant_id=tenant, project=project.strip()[:160], day=d.isoformat(), party=party[:160],
                         side=side, head=h, amount=amt, settled=bool(settled) or side == "in",
                         due_day=(dd or d).isoformat(), ref=str(ref)[:120], note=note[:300]))
        inc = sum(x.amount for x in s.scalars(select(CBookEntry).where(CBookEntry.tenant_id == tenant,
                                                                       CBookEntry.project == project.strip()[:160], CBookEntry.side == "in")).all())
        out = sum(x.amount for x in s.scalars(select(CBookEntry).where(CBookEntry.tenant_id == tenant,
                                                                       CBookEntry.project == project.strip()[:160], CBookEntry.side == "out")).all())
    from .common import publish
    publish(tenant, "const_books", {"kind": "entry", "project": project, "side": side, "amount": amt}, conv)
    say = (f"{project}: {'aaya' if side == 'in' else 'gaya'} {_rs(amt)} ({h}{' - ' + party if party else ''}). "
           f"Project book: in {_rs(inc)}, out {_rs(out)}, balance {_rs(inc - out)}.")
    if side == "out" and not settled:
        say += f" ABHI TAK UNSETTLED - due {(dd or d).strftime('%d %b')} se ageing chalegi."
    return {"in": round(inc, 2), "out": round(out, 2), "say": say}


def settle(tenant: str, ref: str = "", entry_id: str = "", day: str = "") -> dict:
    """Mark an unsettled out-row paid (after her payment) - the ageing list's closure."""
    d = _date(day, today(tenant))
    with _LOCK, session() as s:
        rows = s.scalars(select(CBookEntry).where(CBookEntry.tenant_id == tenant, CBookEntry.side == "out",
                                                  CBookEntry.settled == False)).all()  # noqa: E712
        x = None
        if entry_id:
            x = next((r for r in rows if r.id == entry_id), None)
        elif ref:
            x = next((r for r in rows if ref.lower() in (r.ref or "").lower() or ref.lower() in (r.party or "").lower()), None)
        if not x:
            raise CstError("Unsettled entry nahi mili (id / ref / party se dhoondo).")
        x.settled = True
        x.due_day = d.isoformat()
        pid, amt, party = x.project, x.amount, x.party
    return {"say": f"{party} ({pid}) ki {_rs(amt)} settled ho gayi."}


def book(tenant: str, project: str) -> dict:
    if not str(project or "").strip():
        raise CstError("Project bataiye.")
    p = project.strip()[:160]
    with session() as s:
        rows = s.scalars(select(CBookEntry).where(CBookEntry.tenant_id == tenant, CBookEntry.project == p)
                         .order_by(CBookEntry.day, CBookEntry.created_at)).all()
    inc = round(sum(r.amount for r in rows if r.side == "in"), 2)
    out = round(sum(r.amount for r in rows if r.side == "out"), 2)
    by_head: dict[str, float] = {}
    for r in rows:
        if r.side == "out":
            by_head[r.head] = round(by_head.get(r.head, 0.0) + r.amount, 2)
    due = round(sum(r.amount for r in rows if r.side == "out" and not r.settled), 2)
    lines = [f"{r.day} {'+' if r.side == 'in' else '-'}{_rs(r.amount)} {r.head}{' - ' + r.party if r.party else ''}{' (UNSETTLED)' if (r.side == 'out' and not r.settled) else ''}"
             for r in rows[-12:]]
    say = (f"{p} ki kitab: in {_rs(inc)}, out {_rs(out)}, balance {_rs(inc - out)}, abhi baki {_rs(due)}. "
           "Khaarch: " + ", ".join(f"{k} {_rs(v)}" for k, v in sorted(by_head.items(), key=lambda x: -x[1])[:5]) + ".")
    return {"in": inc, "out": out, "balance": round(inc - out, 2), "unsettled": due, "by_head": by_head,
            "lines": lines, "say": say}


def ageing(tenant: str, project: str = "") -> dict:
    """Vendor ageing on unsettled out-rows: 0-30 / 31-60 / 60+ days, the sheet the accountant signs."""
    t0 = today(tenant)
    with session() as s:
        q = select(CBookEntry).where(CBookEntry.tenant_id == tenant, CBookEntry.side == "out",
                                     CBookEntry.settled == False)  # noqa: E712
        if project:
            q = q.where(CBookEntry.project == project.strip()[:160])
        rows = s.scalars(q).all()
    buckets = {"0-30": 0.0, "31-60": 0.0, "60+": 0.0}
    parties: dict[str, float] = {}
    for r in rows:
        due = _date(r.due_day) or t0
        days = (t0 - due).days
        b = "0-30" if days <= 30 else ("31-60" if days <= 60 else "60+")
        buckets[b] = round(buckets[b] + r.amount, 2)
        if r.party:
            parties[r.party] = round(parties.get(r.party, 0.0) + r.amount, 2)
    total = round(sum(buckets.values()), 2)
    say = (f"Ageing{' (' + project + ')' if project else ''}: total dena {_rs(total)} - 0-30 din {_rs(buckets['0-30'])}, "
           f"31-60 {_rs(buckets['31-60'])}, 60+ {_rs(buckets['60+'])}."
           + (" Sabse bade: " + ", ".join(f"{k} {_rs(v)}" for k, v in sorted(parties.items(), key=lambda x: -x[1])[:3]) if parties else ""))
    return {"buckets": buckets, "parties": parties, "total": total, "say": say}
