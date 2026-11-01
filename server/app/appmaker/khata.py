"""v0.359 KHATA (App Sahayak Phase 23, owner: "START PHASE 23"): the customer's udhaar ledger, the way an Indian shop keeps it.

Staff mark an order "on credit" -> the order's SERVER total is written to that customer's khata once; when the customer
pays, staff (or she) record it (cash / UPI / other, amount, note) - money never moves here, the app only remembers. The
customer sees her own balance and entries; staff and the owner see who owes how much. Entries are append-only rows (a wrong
one is corrected by a new one, never edited): SiteAppRow coll "_khata", owner "" (a customer deleting her account does not
erase the shop's ledger; the entry keeps her member id + name). A cancelled credited order is reversed by itself, once."""
from __future__ import annotations

import json
import re
import threading
from typing import Any

from sqlalchemy import select

from ..db import now, session
from ..site import webapp as W
from .models import AppProject

COLL = "_khata"
MODES = ("cash", "upi", "card", "bank", "other")
MAX_AMT = 10_000_000
_LOCK = threading.Lock()
STATS = {"credits": 0, "payments": 0, "reversals": 0}


class KhataError(W.AppError):
    pass


def _site(r: AppProject) -> str:
    from . import backend as BE
    return BE.bid(r)


def _entries(r: AppProject, member: str = "") -> list[dict[str, Any]]:
    from . import backend as BE
    with session() as s:
        q = select(W.SiteAppRow).where(W.SiteAppRow.site_id == _site(r), W.SiteAppRow.coll == COLL)
        rows = s.scalars(q.order_by(W.SiteAppRow.created_at.asc())).all()
        out = []
        for x in rows:
            d = BE._j(x.data, {})
            if member and d.get("member") != member:
                continue
            out.append({"id": x.id, **d, "at": x.created_at.isoformat() if x.created_at else ""})
    return out


def _add(r: AppProject, entry: dict[str, Any]) -> dict[str, Any]:
    with session() as s:
        row = W.SiteAppRow(site_id=_site(r), coll=COLL, owner="", data=json.dumps(entry, ensure_ascii=False))
        s.add(row)
        s.flush()
        rid = row.id
    return {"id": rid, **entry}


def _balance(entries: list[dict[str, Any]]) -> float:
    return round(sum(float(e.get("amount") or 0) * (1 if e.get("kind") == "credit" else -1) for e in entries), 2)


def _who_name(r: AppProject, member: str) -> str:
    with session() as s:
        m = s.get(W.SiteAppMember, member)
        return (m.name or m.email.split("@")[0]) if m is not None and m.site_id == _site(r) else ""


def credit(r: AppProject, coll: str, row_id: str, w: W.Who) -> dict[str, Any]:
    """Staff: this order was given on credit -> its server total goes to the customer's khata (once per order)."""
    from . import backend as BE
    if not w.staff:
        raise KhataError("Udhaar sirf staff likh sakta hai.", 403)
    sch = BE.schema(r)
    W.coll(sch, coll)
    with _LOCK:
        with session() as s:
            row = s.get(W.SiteAppRow, row_id)
            if row is None or row.site_id != _site(r) or row.coll != coll:
                raise KhataError("Yeh entry nahi mili.", 404)
            d = BE._j(row.data, {})
            if d.get("_khata"):
                return {"already": True, "khata": d["_khata"], **summary(r, row.owner)}
            if not row.owner:
                raise KhataError("Yeh order bina account ke aaya; udhaar sirf account wale customer ke naam likhta hai.", 409)
            if str(d.get("status") or "").strip().lower() == "cancelled":
                raise KhataError("Cancelled order udhaar par nahi likhta.", 409)
            try:
                amt = round(float(d.get("total") or 0), 2)
            except (TypeError, ValueError):
                amt = 0.0
            if amt <= 0:
                raise KhataError("Is entry ki koi rakam nahi (total) - udhaar mein kya likhein?", 409)
            member = row.owner
        e = _add(r, {"member": member, "name": _who_name(r, member), "kind": "credit", "amount": amt, "order": row_id,
                     "coll": coll, "note": f"Order {row_id[-6:].upper()} on credit", "by": w.id or "owner"})
        BE._merge(row_id, {"_khata": e["id"], "_ev": now().isoformat()})
    STATS["credits"] += 1
    return {"entry": e, **summary(r, member)}


def payment(r: AppProject, member: str, amount: Any, mode: str, note: str, w: W.Who) -> dict[str, Any]:
    """Staff / her: the customer paid (recorded only - Hoola never sees or moves the money)."""
    if not w.staff:
        raise KhataError("Payment sirf staff likh sakta hai.", 403)
    if not _who_name(r, member):
        raise KhataError("Yeh customer nahi mila.", 404)
    try:
        amt = round(float(str(amount).replace(",", "").replace("₹", "").strip()), 2)
    except (TypeError, ValueError):
        raise KhataError("Rakam number mein likhiye.")
    if not 0 < amt <= MAX_AMT:
        raise KhataError(f"Rakam 1 se {MAX_AMT:,} tak.")
    mode = str(mode or "cash").strip().lower()
    if mode not in MODES:
        raise KhataError("Kaise mila: " + " / ".join(MODES))
    note = re.sub(r"[\x00-\x1f\x7f]+", " ", str(note or "")).strip()[:200]
    with _LOCK:
        e = _add(r, {"member": member, "name": _who_name(r, member), "kind": "payment", "amount": amt, "mode": mode,
                     "note": note, "by": w.id or "owner"})
    STATS["payments"] += 1
    return {"entry": e, **summary(r, member)}


def reverse_order(r: AppProject, row_id: str) -> None:
    """A credited order cancelled -> one reversing entry (the original stays, as in a paper khata)."""
    from . import backend as BE
    with _LOCK:
        with session() as s:
            row = s.get(W.SiteAppRow, row_id)
            d = BE._j(row.data, {}) if row is not None else {}
            if not d.get("_khata") or d.get("_khata_back"):
                return
            orig = s.get(W.SiteAppRow, d["_khata"])
            od = BE._j(orig.data, {}) if orig is not None else {}
            d["_khata_back"] = True
            row.data = json.dumps(d, ensure_ascii=False)
        if od.get("amount"):
            _add(r, {"member": od.get("member"), "name": od.get("name", ""), "kind": "payment", "amount": float(od["amount"]),
                     "mode": "other", "note": f"Order {row_id[-6:].upper()} cancelled - udhaar wapas", "order": row_id, "by": "system"})
            STATS["reversals"] += 1


def summary(r: AppProject, member: str) -> dict[str, Any]:
    es = _entries(r, member)
    return {"member": member, "name": _who_name(r, member) or (es[-1].get("name") if es else ""), "balance": _balance(es),
            "entries": list(reversed(es))[:100]}


def mine(r: AppProject, w: W.Who) -> dict[str, Any]:
    if w.m is None:
        raise KhataError("Pehle login kijiye.", 401)
    out = summary(r, w.m.id)
    for e in out["entries"]:
        e.pop("by", None)
    return out


def dues(r: AppProject, w: W.Who) -> dict[str, Any]:
    """Staff / her: every customer with a khata, biggest balance first."""
    if not w.staff:
        raise KhataError("Yeh sirf staff ke liye hai.", 403)
    per: dict[str, list[dict[str, Any]]] = {}
    for e in _entries(r):
        per.setdefault(str(e.get("member") or ""), []).append(e)
    people = [{"member": m, "name": es[-1].get("name") or "Customer", "balance": _balance(es), "last": es[-1]["at"],
               "entries": len(es)} for m, es in per.items() if m]
    people.sort(key=lambda p: -p["balance"])
    return {"customers": people, "total_due": round(sum(p["balance"] for p in people if p["balance"] > 0), 2)}
