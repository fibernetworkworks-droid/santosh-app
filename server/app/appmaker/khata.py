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
import urllib.parse as _up
from datetime import timedelta as _td
from typing import Any

from sqlalchemy import select

from ..db import now, session
from ..site import webapp as W
from .models import AppProject
from . import locks as LK                     # v0.390 one cross-process lock per app

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
        raise KhataError("Only staff can record credit.", 403)
    sch = BE.schema(r)
    W.coll(sch, coll)
    with LK.app(r.id):
        with session() as s:
            row = s.get(W.SiteAppRow, row_id)
            if row is None or row.site_id != _site(r) or row.coll != coll:
                raise KhataError("This entry was not found.", 404)
            d = BE._j(row.data, {})
            if d.get("_khata"):
                return {"already": True, "khata": d["_khata"], **summary(r, row.owner)}
            if not row.owner:
                raise KhataError("This order came without an account; credit can only be recorded for a customer with an account.", 409)
            if str(d.get("status") or "").strip().lower() == "cancelled":
                raise KhataError("A cancelled order cannot be put on credit.", 409)
            try:
                amt = round(float(d.get("total") or 0), 2)
            except (TypeError, ValueError):
                amt = 0.0
            if amt <= 0:
                raise KhataError("This entry has no amount (total) - there is nothing to put on credit.", 409)
            member = row.owner
        e = _add(r, {"member": member, "name": _who_name(r, member), "kind": "credit", "amount": amt, "order": row_id,
                     "coll": coll, "note": f"Order {row_id[-6:].upper()} on credit", "by": w.id or "owner"})
        BE._merge(row_id, {"_khata": e["id"], "_ev": now().isoformat()})
    STATS["credits"] += 1
    return {"entry": e, **summary(r, member)}


def payment(r: AppProject, member: str, amount: Any, mode: str, note: str, w: W.Who) -> dict[str, Any]:
    """Staff / her: the customer paid (recorded only - Hoola never sees or moves the money)."""
    if not w.staff:
        raise KhataError("Only staff can record a payment.", 403)
    if not _who_name(r, member):
        raise KhataError("This customer was not found.", 404)
    try:
        amt = round(float(str(amount).replace(",", "").replace("₹", "").strip()), 2)
    except (TypeError, ValueError):
        raise KhataError("Write the amount as a number.")
    if not 0 < amt <= MAX_AMT:
        raise KhataError(f"The amount must be from 1 to {MAX_AMT:,}.")
    mode = str(mode or "cash").strip().lower()
    if mode not in MODES:
        raise KhataError("How it was received: " + " / ".join(MODES))
    note = re.sub(r"[\x00-\x1f\x7f]+", " ", str(note or "")).strip()[:200]
    with LK.app(r.id):
        e = _add(r, {"member": member, "name": _who_name(r, member), "kind": "payment", "amount": amt, "mode": mode,
                     "note": note, "by": w.id or "owner"})
    STATS["payments"] += 1
    return {"entry": e, **summary(r, member)}


def reverse_order(r: AppProject, row_id: str) -> None:
    """A credited order cancelled -> one reversing entry (the original stays, as in a paper khata)."""
    from . import backend as BE
    with LK.app(r.id):
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
                     "mode": "other", "note": f"Order {row_id[-6:].upper()} cancelled - credit reversed", "order": row_id, "by": "system"})
            STATS["reversals"] += 1


def summary(r: AppProject, member: str) -> dict[str, Any]:
    es = _entries(r, member)
    return {"member": member, "name": _who_name(r, member) or (es[-1].get("name") if es else ""), "balance": _balance(es),
            "entries": list(reversed(es))[:100]}


def mine(r: AppProject, w: W.Who) -> dict[str, Any]:
    if w.m is None:
        raise KhataError("Log in first.", 401)
    out = summary(r, w.m.id)
    for e in out["entries"]:
        e.pop("by", None)
    return out


def dues(r: AppProject, w: W.Who) -> dict[str, Any]:
    """Staff / her: every customer with a khata, biggest balance first."""
    if not w.staff:
        raise KhataError("This is for staff only.", 403)
    per: dict[str, list[dict[str, Any]]] = {}
    for e in _entries(r):
        per.setdefault(str(e.get("member") or ""), []).append(e)
    people = [{"member": m, "name": es[-1].get("name") or "Customer", "balance": _balance(es), "last": es[-1]["at"],
               "entries": len(es)} for m, es in per.items() if m]
    people.sort(key=lambda p: -p["balance"])
    return {"customers": people, "total_due": round(sum(p["balance"] for p in people if p["balance"] > 0), 2)}


# ---------------------------------------------------------------- v0.375 KHATA YAAD (App Sahayak Phase 39): payment reminders
# For customers who owe, a plain English reminder ready to go, two official ways, both started ONLY by her:
#   * "phone": a wa.me link with the text filled in - she opens it and sends it herself from her own WhatsApp (nothing
#     automated, no personal-WhatsApp automation ever);
#   * "template": her official WhatsApp Business number (Meta Cloud API) with a UTILITY template SHE got approved, params
#     [customer name, amount, shop] - only by her tap (by_tap), never to someone who wrote STOP to her business number, at
#     most once per customer every 3 days. The customer's number = the phone on her latest order in this app.
REMIND_EVERY_DAYS = 3
STATS.update({"reminders": 0, "reminder_refused": 0})


def _phone_of(r: AppProject, member: str) -> str:
    from . import backend as BE
    with session() as s:
        rows = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == _site(r), W.SiteAppRow.owner == member)
                         .order_by(W.SiteAppRow.created_at.desc()).limit(20)).all()
        for x in rows:
            ph = re.sub(r"\D", "", str(BE._j(x.data, {}).get("phone") or ""))[-10:]
            if len(ph) == 10:
                return ph
    return ""


def _last_reminded(r: AppProject) -> dict[str, str]:
    from . import backend as BE
    with session() as s:
        row = s.get(AppProject, r.id)
        return dict(BE._j(row.backend if row else r.backend, {}).get("khata_remind") or {})


def reminder_text(r: AppProject, name: str, amount: float) -> str:
    return (f"Hello {name.split()[0] if name else ''}, you have Rs {amount:,.0f} due on credit at {r.name or 'our shop'}. "
            "Please pay when convenient. Thank you.").replace("  ", " ")


def reminders(r: AppProject) -> dict[str, Any]:
    """Her list: every customer who owes, the ready text, the wa.me link (her own phone), whether the business template may go."""
    last = _last_reminded(r)
    now_ = now()
    out = []
    for p in dues(r, W.Who(owner=True))["customers"]:
        if p["balance"] <= 0:
            continue
        ph = _phone_of(r, p["member"])
        text = reminder_text(r, p["name"], p["balance"])
        when = last.get(p["member"], "")
        try:
            recent = bool(when) and (now_ - datetime_from(when)) < _td(days=REMIND_EVERY_DAYS)
        except ValueError:
            recent = False
        out.append({"member": p["member"], "name": p["name"], "balance": p["balance"], "phone": ph, "text": text,
                    "link": f"https://wa.me/91{ph}?text={_up.quote(text)}" if ph else "", "last": when, "recent": recent})
    return {"customers": out, "every_days": REMIND_EVERY_DAYS,
            "note": "Open in WhatsApp = you send it yourself. Business template = your approved UTILITY template, only by your tap."}


def datetime_from(s: str):
    from datetime import datetime as _dt, timezone
    d = _dt.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


async def send_reminder(r: AppProject, member: str, template: str, by_tap: bool) -> dict[str, Any]:
    """Her tap: the reminder through her WhatsApp Business number with her approved UTILITY template."""
    import json as _json
    from sqlalchemy import select as _sel
    from ..db import Template
    from ..employee.models import BizContact
    from ..whatsapp.client import WhatsAppError, get_whatsapp
    from . import backend as BE
    if not by_tap:
        raise KhataError("A business WhatsApp message goes to a customer only with your tap.", 403)
    p = next((x for x in reminders(r)["customers"] if x["member"] == member), None)
    if p is None:
        raise KhataError("This customer has no credit due.", 404)
    if not p["phone"]:
        raise KhataError("No 10-digit mobile number was found for this customer in any order.", 409)
    if p["recent"]:
        STATS["reminder_refused"] += 1
        raise KhataError(f"{p['name']} was already reminded in the last {REMIND_EVERY_DAYS} days.", 409)
    with session() as s:
        bc = s.scalars(_sel(BizContact).where(BizContact.tenant_id == r.tenant_id, BizContact.wa_id == "91" + p["phone"])).first()
        if bc is not None and bc.opted_out:
            STATS["reminder_refused"] += 1
            raise KhataError(f"{p['name']} wrote STOP to your business number - remind them only from your own phone.", 409)
        row = s.scalars(_sel(Template).where(Template.tenant_id == r.tenant_id, Template.name == template)).first()
        if row is None or row.status != "APPROVED":
            raise KhataError(f"Template '{template}' is not approved by Meta. Get a UTILITY template made under 'Templates' "
                             "(for example: Hello {{1}}, you have Rs {{2}} due at {{3}}...), or send it yourself with 'Open in WhatsApp'.", 409)
        if (row.category or "").upper() != "UTILITY":
            raise KhataError("A credit reminder needs a UTILITY template (not marketing).", 409)
        lang = row.language
    try:
        wamid = await get_whatsapp().send_template("91" + p["phone"], template, lang,
                                                   [p["name"].split()[0] or "Customer", f"{p['balance']:,.0f}", r.name or "our shop"])
    except WhatsAppError as e:
        raise KhataError(f"WhatsApp did not accept it: {e}", 502)
    with LK.app(r.id), session() as s:
        row = s.get(AppProject, r.id)
        be = BE._j(row.backend, {})
        last = dict(be.get("khata_remind") or {})
        last[member] = now().isoformat()
        be["khata_remind"] = last
        row.backend = _json.dumps(be, ensure_ascii=False)
    STATS["reminders"] += 1
    return {"ok": True, "member": member, "wa_msg_id": str(wamid or "")[:80], "say": f"Reminder sent to {p['name']} (on your tap)."}
