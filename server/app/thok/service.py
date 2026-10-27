"""v0.107 Thok Sahayak: Hoola as a wholesale trader's coworker, end to end.

  1. Gets the job: a retailer's order said or pasted ("Gupta Kirana: atta 10 bori, cheeni 5 bag"), "Sharma ji ne 50,000
     ka cheque diya", a supplier's bill, "kiska paisa baaki hai", "aaj kis route par vasooli", "kya mangwana hai".
  2. Does the work, step by step: matches each item to HER stock list (the Hoola Deals stock: price, bulk tiers, GST,
     free quantity), prices it, splits CGST / SGST or IGST by the buyer's state, checks stock and the party's credit
     (limit, overdue, oldest bill), numbers the bill, works out the due date; allocates payments to the oldest bills;
     tracks cheques (PDC date, cleared, bounced with the Sec 138 dates); purchases update stock and average cost.
  3. Checked against the rules and earlier work: GST invoice fields and HSN digits, e-way bill limits (inter-state
     Rs 50,000, state limit intra-state), e-invoice (IRN) above Rs 5 crore AATO, cash Rs 2 lakh bar (Sec 221), TDS on
     purchase (Sec 393(1)), MSME supplier 15 / 45 days, credit limits, aging, sales speed for reorder.
  4. Ready as a card, a file or a draft: the order card, the GST tax invoice PDF, reminder / bill WhatsApp drafts,
     party ledger Excel, reorder list and purchase-order draft per supplier, the day's summary.
  5. Waits for her Haan: a bill is made only on her Haan (owner tap), and every message to a party is a draft she sends.
     Hoola never takes or pays money and never makes the e-way bill / IRN on the portal itself.
  6. Delivers and learns: stock goes down on billing and up on purchase, average cost and margins update, a party's
     payment habit (days to pay) is learned and shown on the next order.
"""
from __future__ import annotations

import io
import json
import logging
import re
import threading
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import rules as R

log = logging.getLogger("santosh.thok")
_LOCK = threading.Lock()


class ThokError(Exception):
    pass


class ThokSettings(Base):
    __tablename__ = "thok_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    firm: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    state: Mapped[str] = mapped_column(String(2), default="27")
    address: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    bank: Mapped[str] = mapped_column(Text, default="")                     # printed on the bill as she wrote it
    terms: Mapped[str] = mapped_column(Text, default="Goods once sold will not be taken back. Subject to local jurisdiction.")
    aato: Mapped[float] = mapped_column(Float, default=0.0)                 # aggregate turnover (for HSN digits / e-invoice)
    last_fy_turnover: Mapped[float] = mapped_column(Float, default=0.0)     # for TDS on purchase
    prefix: Mapped[str] = mapped_column(String(4), default="TS")
    counters: Mapped[str] = mapped_column(Text, default="{}")               # {fy: last number}
    credit_days: Mapped[int] = mapped_column(Integer, default=15)
    morning_time: Mapped[str] = mapped_column(String(5), default="08:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")


class ThokParty(Base):
    __tablename__ = "thok_parties"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="customer")       # customer | supplier | both
    name: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    state: Mapped[str] = mapped_column(String(2), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    credit_limit: Mapped[float] = mapped_column(Float, default=0.0)
    credit_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    route: Mapped[str] = mapped_column(String(40), default="")              # beat: "Mon", "Akot road"...
    msme: Mapped[bool] = mapped_column(Boolean, default=False)              # supplier is a micro / small enterprise
    pan_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    opening: Mapped[float] = mapped_column(Float, default=0.0)              # + they owe her (customer) / she owes them (supplier)
    whatsapp_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ThokItem(Base):
    """What the wholesaler needs beyond the shared stock list: HSN, average cost, supplier, lead time."""
    __tablename__ = "thok_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ti"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(140), index=True)               # = hoola_stock.key
    hsn: Mapped[str] = mapped_column(String(8), default="")
    cost: Mapped[float] = mapped_column(Float, default=0.0)                 # weighted average purchase rate (before GST)
    supplier_id: Mapped[str] = mapped_column(String(40), default="")
    lead_days: Mapped[int] = mapped_column(Integer, default=3)


class ThokOrder(Base):
    __tablename__ = "thok_orders"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("to"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    party_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(16), default="", index=True)
    status: Mapped[str] = mapped_column(String(10), default="draft")       # draft | billed | cancelled
    lines: Mapped[str] = mapped_column(Text, default="[]")
    taxable: Mapped[float] = mapped_column(Float, default=0.0)
    tax: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)               # rounded grand total
    paid: Mapped[float] = mapped_column(Float, default=0.0)
    intra: Mapped[bool] = mapped_column(Boolean, default=True)
    bill_date: Mapped[str] = mapped_column(String(10), default="")
    due_date: Mapped[str] = mapped_column(String(10), default="", index=True)
    checks: Mapped[str] = mapped_column(Text, default="{}")                 # credit / stock / eway / einvoice
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ThokPayment(Base):
    __tablename__ = "thok_payments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tq"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    party_id: Mapped[str] = mapped_column(String(40), index=True)
    direction: Mapped[str] = mapped_column(String(3), default="in")         # in (from a customer) | out (she paid a supplier)
    mode: Mapped[str] = mapped_column(String(8), default="cash")            # cash | upi | neft | cheque
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    on: Mapped[str] = mapped_column(String(10), default="")
    cheque_no: Mapped[str] = mapped_column(String(12), default="")
    cheque_date: Mapped[str] = mapped_column(String(10), default="")
    bank: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(10), default="cleared")      # cleared | pending | bounced
    memo_date: Mapped[str] = mapped_column(String(10), default="")
    alloc: Mapped[str] = mapped_column(Text, default="[]")                  # [{order_id|purchase_id, amount}]
    note: Mapped[str] = mapped_column(Text, default="")


class ThokPurchase(Base):
    __tablename__ = "thok_purchases"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("tb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    supplier_id: Mapped[str] = mapped_column(String(40), index=True)
    bill_no: Mapped[str] = mapped_column(String(30), default="")
    bill_date: Mapped[str] = mapped_column(String(10), default="")
    lines: Mapped[str] = mapped_column(Text, default="[]")
    taxable: Mapped[float] = mapped_column(Float, default=0.0)
    tax: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    paid: Mapped[float] = mapped_column(Float, default=0.0)
    due_date: Mapped[str] = mapped_column(String(10), default="")
    tds: Mapped[float] = mapped_column(Float, default=0.0)


# ---------------------------------------------------------------- helpers
def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _rs(v) -> str:
    v = round(float(v or 0))
    s = str(abs(v))
    if len(s) > 3:
        s = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", s[:-3]) + "," + s[-3:]
    return ("-" if v < 0 else "") + "₹" + s


def _tz(tenant: str):
    from ..life import tz_of
    return tz_of(tenant)


def today(tenant: str) -> date:
    return datetime.now(_tz(tenant)).date()


def _date(v, default: date | None = None) -> date | None:
    if isinstance(v, date):
        return v
    if v in (None, ""):
        return default
    from ..analyst.service import _date as d
    return d(v) or default


def fy_of(d: date) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y % 100:02d}-{(y + 1) % 100:02d}"


def _fy_start(d: date) -> date:
    return date(d.year if d.month >= 4 else d.year - 1, 4, 1)


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("thok publish failed")


def _st(s, tenant: str) -> ThokSettings:
    r = s.get(ThokSettings, tenant)
    if r is None:
        r = ThokSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def settings(tenant: str) -> dict:
    with session() as s:
        r = _st(s, tenant)
        return {"firm": r.firm, "gstin": r.gstin, "state": r.state, "address": r.address, "phone": r.phone, "bank": r.bank,
                "terms": r.terms, "aato": r.aato, "last_fy_turnover": r.last_fy_turnover, "prefix": r.prefix,
                "credit_days": r.credit_days, "morning_time": r.morning_time, "hsn_digits": R.hsn_digits(r.aato),
                "einvoice": r.aato > R.EINV_AATO}


def save_settings(tenant: str, **kw: Any) -> dict:
    from ..gstp.rules import valid_gstin
    with session() as s:
        r = _st(s, tenant)
        if kw.get("gstin"):
            g = str(kw["gstin"]).strip().upper()
            if not valid_gstin(g):
                raise ThokError(f"GSTIN galat lagta hai: {g}")
            r.gstin, r.state = g, g[:2]
        for k in ("firm", "address", "phone", "bank", "terms"):
            if kw.get(k) is not None:
                setattr(r, k, str(kw[k]).strip()[:600])
        if kw.get("prefix"):
            p = re.sub(r"[^A-Z0-9]", "", str(kw["prefix"]).upper())[:4]
            if p:
                r.prefix = p
        for k in ("aato", "last_fy_turnover"):
            if kw.get(k) not in (None, ""):
                setattr(r, k, R.money(kw[k]))
        if kw.get("credit_days") not in (None, ""):
            r.credit_days = max(0, min(int(kw["credit_days"]), 180))
        if kw.get("state") and not r.gstin:
            r.state = str(kw["state"]).zfill(2)[:2]
        if kw.get("morning_time"):
            r.morning_time = str(kw["morning_time"]).zfill(5)[:5]
    return settings(tenant)


# ---------------------------------------------------------------- parties
def _party(s, tenant: str, ref: str, kind: str = "") -> ThokParty:
    ref = str(ref or "").strip()
    if not ref:
        raise ThokError("Kaun si party? Naam ya phone bataiye.")
    p = s.get(ThokParty, ref)
    if p and p.tenant_id == tenant:
        return p
    rows = s.scalars(select(ThokParty).where(ThokParty.tenant_id == tenant)).all()
    if kind:
        rows = [r for r in rows if r.kind in (kind, "both")]
    digits = re.sub(r"\D", "", ref)
    if len(digits) >= 10:
        for r in rows:
            if r.phone.endswith(digits[-10:]):
                return r
    up = ref.upper()
    for r in rows:
        if r.gstin and r.gstin == up:
            return r
    exact = [r for r in rows if r.name.lower() == ref.lower()]
    if len(exact) == 1:
        return exact[0]
    hits = [r for r in rows if ref.lower() in r.name.lower()]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise ThokError("Is naam ki kai party: " + ", ".join(h.name for h in hits[:6]) + ". Poora naam ya phone bataiye.")
    raise ThokError(f"Party '{ref}' nahi mili. Pehle jodiye.")


def save_party(tenant: str, name: str = "", party: str = "", kind: str = "", phone: str = "", gstin: str = "", address: str = "",
               credit_limit=None, credit_days=None, route: str = "", msme: bool | None = None, pan_ok: bool | None = None,
               opening=None, whatsapp_ok: bool | None = None, notes: str = "", state: str = "") -> dict:
    from ..gstp.rules import valid_gstin
    with _LOCK, session() as s:
        p = _party(s, tenant, party) if party else None
        new = p is None
        if new:
            if not str(name).strip():
                raise ThokError("Party ka naam chahiye.")
            p = ThokParty(tenant_id=tenant)
            s.add(p)
        if name:
            p.name = re.sub(r"\s+", " ", str(name)).strip()[:160]
        if kind in ("customer", "supplier", "both"):
            p.kind = kind
        if phone:
            p.phone = re.sub(r"[^\d+]", "", str(phone))[-13:]
        if gstin:
            g = str(gstin).strip().upper()
            if not valid_gstin(g):
                raise ThokError(f"GSTIN galat lagta hai: {g} (15 akshar, aakhri check akshar milna chahiye).")
            p.gstin, p.state = g, g[:2]
        elif state:
            p.state = str(state).zfill(2)[:2]
        if address:
            p.address = str(address)[:400]
        if credit_limit not in (None, ""):
            p.credit_limit = R.money(credit_limit)
        if credit_days not in (None, ""):
            p.credit_days = max(0, min(int(credit_days), 180))
        if route:
            p.route = str(route)[:40]
        if msme is not None:
            p.msme = bool(msme)
        if pan_ok is not None:
            p.pan_ok = bool(pan_ok)
        if opening not in (None, ""):
            p.opening = R.money(opening)
        if whatsapp_ok is not None:
            p.whatsapp_ok = bool(whatsapp_ok)
        if notes:
            p.notes = str(notes)[:1000]
        s.flush()
        pid = p.id
    v = party_view(tenant, pid)
    return {"party": v, "say": f"{'Nayi party' if new else 'Update'}: {v['name']}" + (f" (GSTIN {v['gstin']})" if v["gstin"] else "")
            + (f", limit {_rs(v['credit_limit'])}" if v["credit_limit"] else "") + "."}


def _cust_ledger(s, tenant: str, p: ThokParty, on: date) -> dict:
    orders = s.scalars(select(ThokOrder).where(ThokOrder.party_id == p.id, ThokOrder.status == "billed")).all()
    billed = sum(o.total for o in orders)
    received = sum(x.amount for x in s.scalars(select(ThokPayment).where(ThokPayment.party_id == p.id, ThokPayment.direction == "in",
                                                                         ThokPayment.status == "cleared")).all())
    pending_chq = sum(x.amount for x in s.scalars(select(ThokPayment).where(ThokPayment.party_id == p.id, ThokPayment.direction == "in",
                                                                            ThokPayment.status == "pending")).all())
    outstanding = R.r2(p.opening + billed - received)
    overdue, oldest, buckets = 0.0, 0, {b[2]: 0.0 for b in R.AGING}
    for o in orders:
        due = R.r2(o.total - o.paid)
        if due <= 0.5:
            continue
        bd, dd = _date(o.bill_date, on), _date(o.due_date, on)
        buckets[R.aging_bucket((on - bd).days)] += due
        if dd < on:
            overdue += due
            oldest = max(oldest, (on - dd).days)
    days_to_pay = []
    for o in orders:
        if o.paid >= o.total - 0.5 and o.bill_date:
            last = _j(o.checks, {}).get("paid_on")
            if last:
                days_to_pay.append((_date(last, on) - _date(o.bill_date, on)).days)
    return {"billed": R.r2(billed), "received": R.r2(received), "outstanding": outstanding, "overdue": R.r2(overdue),
            "oldest_overdue_days": oldest, "aging": {k: R.r2(v) for k, v in buckets.items()}, "cheques_pending": R.r2(pending_chq),
            "avg_days_to_pay": round(sum(days_to_pay) / len(days_to_pay)) if days_to_pay else None}


def _supp_ledger(s, tenant: str, p: ThokParty, on: date) -> dict:
    bills = s.scalars(select(ThokPurchase).where(ThokPurchase.supplier_id == p.id)).all()
    paid = sum(x.amount for x in s.scalars(select(ThokPayment).where(ThokPayment.party_id == p.id, ThokPayment.direction == "out")).all())
    total = sum(b.total - b.tds for b in bills)
    return {"bought": R.r2(total), "paid": R.r2(paid), "payable": R.r2(p.opening + total - paid)}


def party_view(tenant: str, ref: str) -> dict:
    on = today(tenant)
    with session() as s:
        p = _party(s, tenant, ref)
        v = {"id": p.id, "name": p.name, "kind": p.kind, "phone": p.phone, "gstin": p.gstin, "state": p.state, "address": p.address,
             "credit_limit": p.credit_limit, "credit_days": p.credit_days, "route": p.route, "msme": p.msme, "pan_ok": p.pan_ok,
             "opening": p.opening, "whatsapp_ok": p.whatsapp_ok, "notes": p.notes}
        if p.kind in ("customer", "both"):
            v["ledger"] = _cust_ledger(s, tenant, p, on)
        if p.kind in ("supplier", "both"):
            v["supplier"] = _supp_ledger(s, tenant, p, on)
    return v


def parties(tenant: str, kind: str = "", route: str = "") -> list[dict]:
    with session() as s:
        q = select(ThokParty.id).where(ThokParty.tenant_id == tenant)
        ids = s.scalars(q.order_by(ThokParty.name)).all()
    out = [party_view(tenant, i) for i in ids]
    if kind:
        out = [p for p in out if p["kind"] in (kind, "both")]
    if route:
        out = [p for p in out if route.lower() in p["route"].lower()]
    return out


# ---------------------------------------------------------------- items (on top of the shared stock list)
def _meta(s, tenant: str, key: str) -> ThokItem | None:
    return s.scalars(select(ThokItem).where(ThokItem.tenant_id == tenant, ThokItem.key == key)).first()


def save_item(tenant: str, name: str, price=None, gst_pct=None, unit: str = "", qty=None, hsn: str = "", cost=None,
              supplier: str = "", lead_days=None, low_at=None, tiers: list | None = None) -> dict:
    from ..net import deal
    if not str(name).strip():
        raise ThokError("Item ka naam chahiye.")
    raw: dict[str, Any] = {"name": str(name).strip()}
    if price not in (None, ""):
        raw["price"] = R.money(price)
    if gst_pct not in (None, ""):
        g = float(gst_pct)
        if g not in R.GST_SLABS:
            raise ThokError("GST ab sirf 0 / 5 / 18 / 40% (22 Sep 2025 se).")
        raw["gst_pct"] = g
    if unit:
        raw["unit"] = R.UNITS.get(str(unit).lower(), str(unit).upper()[:10])
    if qty not in (None, ""):
        raw["qty"] = float(qty)
    if low_at not in (None, ""):
        raw["low_at"] = float(low_at)
    if tiers is not None:
        raw["tiers"] = tiers
    try:
        res = deal.set_stock(tenant, [raw])
    except deal.DealError as e:
        raise ThokError(str(e))
    it = res["items"][0]
    key = deal.norm(it["name"])
    with session() as s:
        m = _meta(s, tenant, key) or ThokItem(tenant_id=tenant, key=key)
        s.add(m)
        if hsn:
            h = re.sub(r"\D", "", str(hsn))
            if len(h) not in (4, 6, 8):
                raise ThokError("HSN 4, 6 ya 8 ank ka hota hai.")
            m.hsn = h
        if cost not in (None, ""):
            m.cost = R.money(cost)
        if supplier:
            m.supplier_id = _party(s, tenant, supplier, "supplier").id
        if lead_days not in (None, ""):
            m.lead_days = max(0, min(int(lead_days), 90))
        meta = {"hsn": m.hsn, "cost": m.cost, "supplier_id": m.supplier_id, "lead_days": m.lead_days}
    return {"item": {**it, **meta}, "say": f"{it['name']}: daam {_rs(it['price'])}/{it['unit'] or 'unit'}, GST {it['gst_pct']:g}%"
            + (f", stock {it['qty']:g}" if it["qty"] is not None else "") + (f", HSN {meta['hsn']}" if meta["hsn"] else "") + "."}


def items(tenant: str, q: str = "") -> list[dict]:
    from ..net import deal
    out = deal.stock(tenant, q)
    with session() as s:
        metas = {m.key: m for m in s.scalars(select(ThokItem).where(ThokItem.tenant_id == tenant)).all()}
    for it in out:
        m = metas.get(deal.norm(it["name"]))
        it.update({"hsn": m.hsn if m else "", "cost": m.cost if m else 0.0, "lead_days": m.lead_days if m else 3,
                   "supplier_id": m.supplier_id if m else "",
                   "margin_pct": round((it["price"] - m.cost) * 100 / it["price"], 1) if m and m.cost and it["price"] else None})
    return out


# ---------------------------------------------------------------- orders -> bill (her Haan)
def _order_view(o: ThokOrder, p: ThokParty | None) -> dict:
    return {"id": o.id, "number": o.number, "status": o.status, "party_id": o.party_id, "party": p.name if p else "", "phone": p.phone if p else "",
            "lines": _j(o.lines, []), "taxable": o.taxable, "tax": o.tax, "total": o.total, "paid": o.paid, "balance": R.r2(o.total - o.paid),
            "intra": o.intra, "bill_date": o.bill_date, "due_date": o.due_date, "checks": _j(o.checks, {}), "note": o.note}


def take_order(tenant: str, party: str, text: str = "", lines: list | None = None, note: str = "", conv: str = "") -> dict:
    """Her retailer's order -> priced lines from HER stock list, stock + credit checked -> a draft for her Haan."""
    from ..net import deal
    asked = list(lines or []) or R.parse_order(text)
    if not asked:
        raise ThokError("Order mein item samajh nahi aaye. Aise likhiye: 'atta 10 bori, cheeni 5 bag'.")
    cat = deal._catalog_items(tenant)
    if not cat:
        raise ThokError("Pehle apni stock / daam list jodiye (item, daam, GST).")
    on = today(tenant)
    with session() as s:
        st = _st(s, tenant)
        p = _party(s, tenant, party, "customer")
        intra = R.is_intra(st.state, p.state)
        metas = {m.key: m for m in s.scalars(select(ThokItem).where(ThokItem.tenant_id == tenant)).all()}
        out, missing, short = [], [], []
        for a in asked:
            name = str(a.get("item") or a.get("name") or "").strip()
            qty = float(a.get("qty") or 0)
            if not name or qty <= 0:
                continue
            it = deal.match(cat, name)
            if it is None:
                missing.append(name)
                continue
            rate = R.money(a["rate"]) if a.get("rate") not in (None, "") else deal.price_for(it, qty)
            taxable = R.r2(rate * qty)
            tx = R.tax_split(taxable, it["gst_pct"], intra)
            m = metas.get(it["key"])
            line = {"item": it["name"], "key": it["key"], "qty": qty, "unit": it["unit"] or a.get("unit") or "", "rate": R.r2(rate),
                    "list_rate": it["price"], "gst_pct": it["gst_pct"], "hsn": m.hsn if m else "", "taxable": taxable, **tx}
            if it.get("free") is not None and it["free"] < qty:
                short.append(f"{it['name']} (hai {it['free']:g}, chahiye {qty:g})")
                line["short"] = True
            out.append(line)
        if not out:
            raise ThokError("Koi item stock list mein nahi mila: " + ", ".join(missing))
        taxable = R.r2(sum(x["taxable"] for x in out))
        tax = R.r2(sum(x["tax"] for x in out))
        total = float(round(taxable + tax))
        led = _cust_ledger(s, tenant, p, on)
        credit = R.credit_check(led["outstanding"], led["overdue"], p.credit_limit, total, led["oldest_overdue_days"])
        ewb, limit = R.eway_needed(total, st.state, p.state)
        hsn_need = R.hsn_digits(st.aato)
        no_hsn = [x["item"] for x in out if p.gstin and len(x["hsn"]) < hsn_need]
        checks = {"credit": credit, "short": short, "missing": missing, "eway": {"needed": ewb, "limit": limit},
                  "einvoice": bool(p.gstin) and st.aato > R.EINV_AATO, "hsn_missing": no_hsn,
                  "avg_days_to_pay": led["avg_days_to_pay"], "outstanding_before": led["outstanding"]}
        o = ThokOrder(tenant_id=tenant, party_id=p.id, lines=json.dumps(out, ensure_ascii=False), taxable=taxable, tax=tax, total=total,
                      intra=intra, checks=json.dumps(checks, ensure_ascii=False), note=str(note)[:500])
        s.add(o)
        s.flush()
        v = _order_view(o, p)
    say = f"{v['party']} ka order: {len(out)} item, {_rs(taxable)} + GST {_rs(tax)} = {_rs(total)}."
    if missing:
        say += " List mein nahi: " + ", ".join(missing) + "."
    if short:
        say += " Stock kam: " + ", ".join(short) + "."
    if credit["level"] != "ok":
        say += " Credit: " + credit["text"]
    if ewb:
        say += f" E-way bill chahiye (maal {_rs(limit)} se upar)."
    if no_hsn:
        say += f" HSN ({hsn_need} ank) nahi: " + ", ".join(no_hsn) + "."
    say += " Bill banaun? (aapki haan)"
    _publish(tenant, "thok_order", {"order_id": v["id"], "party": v["party"], "total": total, "level": credit["level"]}, conv)
    return {"order": v, "say": say}


def _next_number(st: ThokSettings, d: date) -> str:
    c = _j(st.counters, {})
    fy = fy_of(d)
    n = int(c.get(fy, 0)) + 1
    c[fy] = n
    st.counters = json.dumps(c)
    return f"{st.prefix}/{fy}/{n:04d}"[:16]


def bill(tenant: str, order_id: str, bill_date: str = "", lines: list | None = None, conv: str = "", by: str = "owner") -> dict:
    """Her Haan: the draft becomes a numbered GST tax invoice, stock goes down, due date set, PDF + a draft for the party."""
    from ..net import deal
    on = today(tenant)
    with _LOCK, session() as s:
        o = s.get(ThokOrder, order_id)
        if not o or o.tenant_id != tenant:
            raise ThokError("Order nahi mila.")
        if o.status != "draft":
            raise ThokError(f"Yeh order pehle se {o.status} hai ({o.number}).")
        st = _st(s, tenant)
        p = s.get(ThokParty, o.party_id)
        ls = _j(o.lines, [])
        if lines:                                   # she changed a qty / rate on the card
            by_item = {str(x.get("item", "")).lower(): x for x in lines if isinstance(x, dict)}
            for x in ls:
                ch = by_item.get(x["item"].lower())
                if ch:
                    if ch.get("qty") not in (None, ""):
                        x["qty"] = float(ch["qty"])
                    if ch.get("rate") not in (None, ""):
                        x["rate"] = R.r2(R.money(ch["rate"]))
                    x["taxable"] = R.r2(x["qty"] * x["rate"])
                    x.update(R.tax_split(x["taxable"], x["gst_pct"], o.intra))
            ls = [x for x in ls if x["qty"] > 0]
            o.taxable = R.r2(sum(x["taxable"] for x in ls))
            o.tax = R.r2(sum(x["tax"] for x in ls))
            o.total = float(round(o.taxable + o.tax))
        bd = _date(bill_date, on)
        o.lines = json.dumps(ls, ensure_ascii=False)
        o.number = _next_number(st, bd)
        o.bill_date = bd.isoformat()
        days = p.credit_days if p.credit_days is not None else st.credit_days
        o.due_date = (bd + timedelta(days=days)).isoformat()
        o.status = "billed"
        ck = _j(o.checks, {})
        ck["billed_by"] = by
        ck["round_off"] = R.r2(o.total - o.taxable - o.tax)
        o.checks = json.dumps(ck, ensure_ascii=False)
        oid = o.id
    try:
        deal.set_stock(tenant, [{"name": x["item"], "add": -x["qty"]} for x in ls])
    except deal.DealError:
        log.exception("stock update failed")
    allocate(tenant, _order_party(tenant, oid))      # an advance already paid fills this bill
    f = invoice_file(tenant, oid, conv)
    v = get_order(tenant, oid)
    ck = v["checks"]
    say = f"Bill {v['number']} bana: {v['party']} {_rs(v['total'])}, due {v['due_date']}."
    if ck.get("eway", {}).get("needed"):
        say += " E-way bill portal par banaiye (Part B: gaadi number) maal nikalne se pehle."
    if ck.get("einvoice"):
        say += " Aapka turnover Rs 5 crore se upar: is B2B bill ka IRN (e-invoice) apne GSP / portal se lijiye."
    text = (f"Namaste {v['party']}, bill {v['number']} dinank {v['bill_date']}: {_rs(v['total'])}. Bhugtan {v['due_date']} tak. "
            f"Dhanyavaad. - {settings(tenant)['firm'] or 'aapke supplier'}")
    return {"order": v, "file": f["file"], "draft": {"to": v["phone"], "text": text}, "say": say}


def _order_party(tenant: str, oid: str) -> str:
    with session() as s:
        return s.get(ThokOrder, oid).party_id


def get_order(tenant: str, order_id: str) -> dict:
    with session() as s:
        o = s.get(ThokOrder, order_id)
        if not o or o.tenant_id != tenant:
            o = s.scalars(select(ThokOrder).where(ThokOrder.tenant_id == tenant, ThokOrder.number == order_id)).first()
        if not o:
            raise ThokError("Order / bill nahi mila.")
        return _order_view(o, s.get(ThokParty, o.party_id))


def cancel_order(tenant: str, order_id: str, reason: str = "") -> dict:
    from ..net import deal
    with _LOCK, session() as s:
        o = s.get(ThokOrder, order_id)
        if not o or o.tenant_id != tenant:
            raise ThokError("Order nahi mila.")
        if o.status == "cancelled":
            raise ThokError("Pehle se cancel.")
        if o.paid > 0:
            raise ThokError("Is bill par paisa aa chuka hai; pehle payment hataiye ya credit note banaiye.")
        was = o.status
        o.status = "cancelled"
        o.note = (o.note + f" | Cancel: {reason}")[:500]
        ls = _j(o.lines, [])
        num = o.number
    if was == "billed":
        try:
            deal.set_stock(tenant, [{"name": x["item"], "add": x["qty"]} for x in ls])
        except deal.DealError:
            log.exception("stock back failed")
        return {"say": f"Bill {num} cancel, maal stock mein wapas. GSTR-1 se pehle ho to bill hata dijiye; baad mein ho to credit note banaiye."}
    return {"say": "Order cancel."}


def orders(tenant: str, status: str = "", party: str = "", limit: int = 100) -> list[dict]:
    with session() as s:
        q = select(ThokOrder).where(ThokOrder.tenant_id == tenant)
        if status:
            q = q.where(ThokOrder.status == status)
        if party:
            q = q.where(ThokOrder.party_id == _party(s, tenant, party).id)
        ps = {p.id: p for p in s.scalars(select(ThokParty).where(ThokParty.tenant_id == tenant)).all()}
        return [_order_view(o, ps.get(o.party_id)) for o in s.scalars(q.order_by(ThokOrder.created_at.desc()).limit(limit)).all()]


def invoice_pdf(tenant: str, order_id: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    from ..india.money import STATE_CODES, rupees_words
    v = get_order(tenant, order_id)
    st = settings(tenant)
    with session() as s:
        p = s.get(ThokParty, v["party_id"])
        pv = {"name": p.name, "gstin": p.gstin, "state": p.state, "address": p.address, "phone": p.phone}
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 40

    def t(x, text, size=9, bold=False, right=False):
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        s_ = str(text).replace("₹", "Rs ").encode("latin-1", "replace").decode("latin-1")
        (pdf.drawRightString if right else pdf.drawString)(x, y, s_[:110])

    t(w / 2 - 40, "TAX INVOICE", 13, True)
    y -= 20
    t(30, st["firm"] or "-", 12, True)
    t(w - 30, f"Invoice No: {v['number']}", 9, True, True)
    y -= 13
    t(30, f"GSTIN: {st['gstin'] or '-'}   State: {STATE_CODES.get(st['state'], '')} ({st['state']})")
    t(w - 30, f"Date: {v['bill_date']}", 9, False, True)
    y -= 12
    t(30, (st["address"] or "")[:95])
    t(w - 30, f"Due: {v['due_date']}", 9, False, True)
    y -= 12
    if st["phone"]:
        t(30, f"Phone: {st['phone']}")
        y -= 12
    y -= 6
    t(30, "Bill to:", 9, True)
    y -= 12
    t(30, pv["name"], 10, True)
    y -= 12
    t(30, f"GSTIN: {pv['gstin'] or 'Unregistered'}   Place of supply: {STATE_CODES.get(pv['state'] or st['state'], '')} ({pv['state'] or st['state']})")
    y -= 12
    if pv["address"]:
        t(30, pv["address"][:95])
        y -= 12
    t(30, "Reverse charge: No")
    y -= 18
    cols = [(30, "#"), (48, "Item"), (230, "HSN"), (280, "Qty"), (345, "Rate"), (405, "Taxable"), (465, "GST%"), (565, "Tax")]
    for x, name in cols:
        t(x, name, 8.5, True, x == 565)
    y -= 4
    pdf.line(30, y, w - 30, y)
    y -= 12
    for i, ln in enumerate(v["lines"], 1):
        if y < 120:
            pdf.showPage()
            y = h - 40
        t(30, i, 8.5)
        t(48, ln["item"][:34], 8.5)
        t(230, ln.get("hsn") or "-", 8.5)
        t(280, f"{ln['qty']:g} {ln.get('unit', '')}", 8.5)
        t(345, f"{ln['rate']:,.2f}", 8.5)
        t(405, f"{ln['taxable']:,.2f}", 8.5)
        t(465, f"{ln['gst_pct']:g}", 8.5)
        t(565, f"{ln['tax']:,.2f}", 8.5, False, True)
        y -= 12
    pdf.line(30, y + 4, w - 30, y + 4)
    y -= 8
    cg, sg, ig = (sum(x.get(k, 0) for x in v["lines"]) for k in ("cgst", "sgst", "igst"))
    rows = [("Taxable value", v["taxable"])]
    rows += [("CGST", cg), ("SGST", sg)] if v["intra"] else [("IGST", ig)]
    rows += [("Round off", v["checks"].get("round_off", 0.0)), ("GRAND TOTAL", v["total"])]
    for k, amt in rows:
        t(450, k, 9, k == "GRAND TOTAL")
        t(565, f"{amt:,.2f}", 9, k == "GRAND TOTAL", True)
        y -= 13
    t(30, "In words: " + rupees_words(v["total"], "en")[:100], 8.5)
    y -= 18
    if st["bank"]:
        t(30, "Bank: " + st["bank"][:100], 8.5)
        y -= 12
    for k in range(0, len(st["terms"]), 110):
        t(30, st["terms"][k:k + 110], 7.5)
        y -= 10
    y -= 24
    t(w - 30, f"For {st['firm'] or ''}", 9, True, True)
    y -= 30
    t(w - 30, "Authorised signatory", 8.5, False, True)
    pdf.showPage()
    pdf.save()
    return buf.getvalue()


def invoice_file(tenant: str, order_id: str, conv: str = "") -> dict:
    from .. import chatfiles
    v = get_order(tenant, order_id)
    if v["status"] != "billed":
        raise ThokError("Pehle bill banaiye (aapki haan).")
    f = chatfiles.store(tenant, f"Bill-{v['number'].replace('/', '-')}.pdf", invoice_pdf(tenant, order_id), "application/pdf")
    _publish(tenant, "pc_file", {**f, "source": "thok", "title": f"Bill {v['number']}"}, conv)
    return {"file": f, "say": f"Bill {v['number']} PDF."}


# ---------------------------------------------------------------- money in / out (Hoola never touches money)
def allocate(tenant: str, party_id: str) -> None:
    """Cleared receipts fill the oldest bills first (recomputed from scratch so it never drifts)."""
    on = today(tenant)
    with _LOCK, session() as s:
        p = s.get(ThokParty, party_id)
        if p is None:
            return
        bills = s.scalars(select(ThokOrder).where(ThokOrder.party_id == party_id, ThokOrder.status == "billed")
                          .order_by(ThokOrder.bill_date, ThokOrder.number)).all()
        pays = s.scalars(select(ThokPayment).where(ThokPayment.party_id == party_id, ThokPayment.direction == "in",
                                                    ThokPayment.status == "cleared").order_by(ThokPayment.on)).all()
        pool = max(0.0, -p.opening)
        opening_due = max(0.0, p.opening)
        for o in bills:
            o.paid = 0.0
        for pay in pays:
            amt = pay.amount
            take = min(amt, opening_due)
            opening_due -= take
            amt -= take
            alloc = [{"opening": R.r2(take)}] if take else []
            for o in bills:
                if amt <= 0.005:
                    break
                room = o.total - o.paid
                if room <= 0.005:
                    continue
                put = min(room, amt)
                o.paid = R.r2(o.paid + put)
                amt -= put
                alloc.append({"order": o.number, "amount": R.r2(put)})
                if o.paid >= o.total - 0.005:
                    ck = _j(o.checks, {})
                    ck["paid_on"] = pay.on or on.isoformat()
                    o.checks = json.dumps(ck, ensure_ascii=False)
            if amt > 0.005:
                alloc.append({"advance": R.r2(amt)})
            pay.alloc = json.dumps(alloc)
        _ = pool


def receive(tenant: str, party: str, amount, mode: str = "cash", on: str = "", cheque_no: str = "", cheque_date: str = "",
            bank: str = "", note: str = "") -> dict:
    """A customer paid HER (cash / UPI / NEFT / cheque). Hoola only writes it down and fills the oldest bills."""
    amt = R.money(amount)
    if amt <= 0:
        raise ThokError("Rakam bataiye.")
    mode = (mode or "cash").lower()
    mode = "upi" if mode in ("gpay", "phonepe", "paytm", "upi") else "neft" if mode in ("neft", "rtgs", "imps", "bank") else \
        "cheque" if mode.startswith("ch") else "cash"
    d = _date(on, today(tenant))
    warn = ""
    with _LOCK, session() as s:
        p = _party(s, tenant, party, "customer")
        if mode == "cash":
            same_day = sum(x.amount for x in s.scalars(select(ThokPayment).where(ThokPayment.party_id == p.id, ThokPayment.mode == "cash",
                                                                                ThokPayment.on == d.isoformat())).all())
            if same_day + amt >= R.CASH_LIMIT:
                warn = (f"Dhyaan: {p.name} se aaj nakad {_rs(same_day + amt)} ho gaya. Rs 2 lakh ya zyada nakad ek din / ek sauda mein lena "
                        "Sec 221 (purana 269ST) mein mana hai; utni hi penalty lag sakti hai. Aage bank / UPI se lijiye.")
        cd = _date(cheque_date, d) if mode == "cheque" else None
        status = "pending" if mode == "cheque" else "cleared"
        if mode == "cheque" and not cheque_no:
            raise ThokError("Cheque number bataiye.")
        if cd and cd < d - timedelta(days=90):
            raise ThokError("Cheque ki tareekh 3 mahine se purani: bank nahi lega.")
        pay = ThokPayment(tenant_id=tenant, party_id=p.id, direction="in", mode=mode, amount=R.r2(amt), on=d.isoformat(),
                          cheque_no=str(cheque_no)[:12], cheque_date=cd.isoformat() if cd else "", bank=str(bank)[:60], status=status,
                          note=(note + (" | " + warn if warn else ""))[:500])
        s.add(pay)
        s.flush()
        pid, name, payid = p.id, p.name, pay.id
    allocate(tenant, pid)
    led = party_view(tenant, pid)["ledger"]
    if mode == "cheque":
        say = (f"{name} ka cheque {cheque_no} {_rs(amt)} ({cd.isoformat()}) note kiya. Clear hone par bills mein judega"
               + (f"; {cd.strftime('%d %b')} se pehle bank mein mat daaliye" if cd > d else "") + ".")
    else:
        say = f"{name} se {_rs(amt)} {mode} mila. Ab baaki {_rs(led['outstanding'])}."
    if warn:
        say += " " + warn
    return {"payment_id": payid, "ledger": led, "warning": warn, "say": say}


def cheque(tenant: str, payment_id: str, status: str, memo_date: str = "", reason: str = "") -> dict:
    if status not in ("cleared", "bounced"):
        raise ThokError("status: cleared | bounced")
    with _LOCK, session() as s:
        pay = s.get(ThokPayment, payment_id)
        if not pay or pay.tenant_id != tenant or pay.mode != "cheque":
            raise ThokError("Cheque nahi mila.")
        pay.status = status
        memo = _date(memo_date, today(tenant))
        if status == "bounced":
            pay.memo_date = memo.isoformat()
            pay.note = (pay.note + f" | Bounce: {reason}")[:500]
        pid, amt, no = pay.party_id, pay.amount, pay.cheque_no
        name = s.get(ThokParty, pid).name
    allocate(tenant, pid)
    if status == "cleared":
        return {"say": f"Cheque {no} clear: {_rs(amt)} {name} ke bills mein juda."}
    steps = R.cheque_steps(memo)
    _publish(tenant, "thok_alert", {"text": f"{name} ka cheque {no} ({_rs(amt)}) bounce. " + steps["say"]})
    return {"steps": steps, "say": f"{name} ka cheque {no} ({_rs(amt)}) bounce: bill phir se baaki. {steps['say']} Paise ke baad "
            f"{steps['pay_window']}; na mile to {steps['complaint_window']}."}


def payments(tenant: str, party: str = "", status: str = "") -> list[dict]:
    with session() as s:
        q = select(ThokPayment).where(ThokPayment.tenant_id == tenant)
        if party:
            q = q.where(ThokPayment.party_id == _party(s, tenant, party).id)
        if status:
            q = q.where(ThokPayment.status == status)
        ps = {p.id: p.name for p in s.scalars(select(ThokParty).where(ThokParty.tenant_id == tenant)).all()}
        return [{"id": x.id, "party": ps.get(x.party_id, ""), "direction": x.direction, "mode": x.mode, "amount": x.amount, "on": x.on,
                 "cheque_no": x.cheque_no, "cheque_date": x.cheque_date, "status": x.status, "memo_date": x.memo_date,
                 "alloc": _j(x.alloc, []), "note": x.note}
                for x in s.scalars(q.order_by(ThokPayment.on.desc())).all()][:300]


# ---------------------------------------------------------------- outstanding, reminders
def outstanding(tenant: str, route: str = "") -> dict:
    ps = [p for p in parties(tenant, "customer", route) if p.get("ledger")]
    rows = []
    for p in ps:
        l2 = p["ledger"]
        if l2["outstanding"] <= 0.5 and not l2["cheques_pending"]:
            continue
        rows.append({"party_id": p["id"], "party": p["name"], "phone": p["phone"], "route": p["route"], "outstanding": l2["outstanding"],
                     "overdue": l2["overdue"], "oldest_overdue_days": l2["oldest_overdue_days"], "aging": l2["aging"],
                     "limit": p["credit_limit"], "over_limit": bool(p["credit_limit"]) and l2["outstanding"] > p["credit_limit"],
                     "cheques_pending": l2["cheques_pending"], "avg_days_to_pay": l2["avg_days_to_pay"]})
    rows.sort(key=lambda r: (-r["overdue"], -r["outstanding"]))
    tot = {k: R.r2(sum(r["aging"][k] for r in rows)) for k in ("0-30", "31-60", "61-90", "90+")}
    total = R.r2(sum(r["outstanding"] for r in rows))
    over = R.r2(sum(r["overdue"] for r in rows))
    return {"parties": rows, "total": total, "overdue": over, "aging": tot,
            "say": f"Bazaar mein {_rs(total)} baaki, jismein {_rs(over)} due date paar; 90+ din: {_rs(tot['90+'])}."}


def reminder_drafts(tenant: str, route: str = "") -> dict:
    firm = settings(tenant)["firm"] or "aapke supplier"
    out = []
    with session() as s:
        ok = {p.id: p.whatsapp_ok for p in s.scalars(select(ThokParty).where(ThokParty.tenant_id == tenant)).all()}
    for r in outstanding(tenant, route)["parties"]:
        if r["overdue"] <= 0 or not ok.get(r["party_id"], True):
            continue
        tone = "kripya aaj-kal mein bhugtan kar dijiye" if r["oldest_overdue_days"] <= 30 else \
            "kaafi din ho gaye hain, kripya jaldi bhugtan karein taaki agla maal samay par bhej sakein"
        out.append({"party": r["party"], "to": r["phone"], "overdue": r["overdue"],
                    "text": f"Namaste {r['party']}, aapke {_rs(r['overdue'])} ke bill due date paar ho gaye hain (kul baaki {_rs(r['outstanding'])}); "
                            f"{tone}. UPI / NEFT / cheque. Dhanyavaad - {firm}"})
    return {"drafts": out, "say": f"{len(out)} party ke liye vasooli message draft (aap bhejengi)."}


def route_plan(tenant: str, route: str = "") -> dict:
    """Today's beat: whose money to collect and whose order to take (by the route / weekday she gave each party)."""
    day = today(tenant).strftime("%a")
    r = route or day
    o = outstanding(tenant, r)
    names = [p["name"] for p in parties(tenant, "customer", r)]
    return {"route": r, "collect": o["parties"], "visit": names,
            "say": f"Aaj ({r}): {len(names)} dukaan, vasooli {_rs(o['total'])}" + (f" (due paar {_rs(o['overdue'])})" if o["overdue"] else "") + "."}


def statement_file(tenant: str, party: str, conv: str = "") -> dict:
    import openpyxl
    from .. import chatfiles
    v = party_view(tenant, party)
    rows = []
    with session() as s:
        for o in s.scalars(select(ThokOrder).where(ThokOrder.party_id == v["id"], ThokOrder.status == "billed")).all():
            rows.append((o.bill_date, f"Bill {o.number}", o.total, 0.0))
        for x in s.scalars(select(ThokPayment).where(ThokPayment.party_id == v["id"], ThokPayment.direction == "in")).all():
            if x.status == "cleared":
                rows.append((x.on, f"{x.mode.upper()} {x.cheque_no}".strip(), 0.0, x.amount))
            elif x.status == "bounced":
                rows.append((x.memo_date or x.on, f"Cheque {x.cheque_no} bounce (no credit)", 0.0, 0.0))
    rows.sort()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ledger"
    ws.append([settings(tenant)["firm"], "", "", "", ""])
    ws.append([f"Party: {v['name']}", v["gstin"], "", "", ""])
    ws.append(["Date", "Particulars", "Debit (bill)", "Credit (payment)", "Balance"])
    bal = v["opening"]
    ws.append(["", "Opening balance", "", "", bal])
    for d, what, dr, cr in rows:
        bal = R.r2(bal + dr - cr)
        ws.append([d, what, dr or "", cr or "", bal])
    bio = io.BytesIO()
    wb.save(bio)
    f = chatfiles.store(tenant, f"Ledger-{re.sub(r'[^A-Za-z0-9]+', '_', v['name'])[:30]}.xlsx", bio.getvalue(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    _publish(tenant, "pc_file", {**f, "source": "thok", "title": f"Ledger {v['name']}"}, conv)
    return {"file": f, "balance": bal, "say": f"{v['name']} ka khaata: baaki {_rs(bal)}. Party ko bhejna aapki haan se."}


# ---------------------------------------------------------------- purchases, suppliers
def purchase(tenant: str, supplier: str, text: str = "", lines: list | None = None, bill_no: str = "", bill_date: str = "",
             agreed_days=None, paid=None) -> dict:
    """A supplier's bill: stock in, average cost, MSME due date, TDS on purchase check. She pays; Hoola only notes."""
    from ..net import deal
    raw = list(lines or []) or R.parse_order(text)
    if not raw:
        raise ThokError("Bill ke item samajh nahi aaye: 'atta 50 bori @ 1450'.")
    on = today(tenant)
    bd = _date(bill_date, on)
    cat = deal._catalog_items(tenant)
    with session() as s:
        st = _st(s, tenant)
        p = _party(s, tenant, supplier, "supplier")
        intra = R.is_intra(st.state, p.state)
        out = []
        for a in raw:
            name = str(a.get("item") or a.get("name") or "").strip()
            qty, rate = float(a.get("qty") or 0), R.money(a.get("rate"))
            if not name or qty <= 0 or rate <= 0:
                raise ThokError(f"'{name or a}': maatra aur rate (@) dono chahiye.")
            it = deal.match(cat, name) if cat else None
            gst = float(a.get("gst_pct")) if a.get("gst_pct") not in (None, "") else (it["gst_pct"] if it else 0.0)
            taxable = R.r2(qty * rate)
            out.append({"item": it["name"] if it else name, "known": bool(it), "qty": qty, "rate": rate, "gst_pct": gst, "taxable": taxable,
                        **R.tax_split(taxable, gst, intra)})
        taxable = R.r2(sum(x["taxable"] for x in out))
        tax = R.r2(sum(x["tax"] for x in out))
        total = float(round(taxable + tax))
        fy0 = _fy_start(bd).isoformat()
        fy_purch = sum(b.taxable for b in s.scalars(select(ThokPurchase).where(ThokPurchase.supplier_id == p.id,
                                                                               ThokPurchase.bill_date >= fy0)).all())
        tds = R.tds_on_purchase(fy_purch, taxable, st.last_fy_turnover, p.pan_ok)
        due = R.msme_due(bd, int(agreed_days) if agreed_days not in (None, "") else None) if p.msme else \
            bd + timedelta(days=int(agreed_days or 30))
        b = ThokPurchase(tenant_id=tenant, supplier_id=p.id, bill_no=str(bill_no)[:30], bill_date=bd.isoformat(),
                         lines=json.dumps(out, ensure_ascii=False), taxable=taxable, tax=tax, total=total, due_date=due.isoformat(),
                         tds=tds["tds"])
        s.add(b)
        # average cost per item
        for x in out:
            key = deal.norm(x["item"])
            m = _meta(s, tenant, key) or ThokItem(tenant_id=tenant, key=key)
            s.add(m)
            have = next((c["free"] for c in cat if c["key"] == key), None) or 0.0
            m.cost = R.r2((m.cost * have + x["rate"] * x["qty"]) / (have + x["qty"])) if m.cost and have else x["rate"]
            if not m.supplier_id:
                m.supplier_id = p.id
        s.flush()
        bid, pname, msme = b.id, p.name, p.msme
        pid = p.id
    try:
        deal.set_stock(tenant, [{"name": x["item"], "add": x["qty"]} for x in out if x["known"]])
    except deal.DealError:
        log.exception("stock in failed")
    if paid not in (None, "") and R.money(paid) > 0:
        pay_supplier(tenant, pid, paid, "neft", bd.isoformat(), note=f"bill {bill_no}")
    new_items = [x["item"] for x in out if not x["known"]]
    say = f"{pname} ka bill {bill_no}: {_rs(taxable)} + GST {_rs(tax)} = {_rs(total)}. Stock badha."
    if new_items:
        say += " Nayi cheez (daam list mein jodiye, tab stock judega): " + ", ".join(new_items) + "."
    say += (f" MSME supplier: {due.strftime('%d %b')} tak bhugtan (warna kharcha is saal nahi ghatega)." if msme else f" Bhugtan {due.strftime('%d %b')} tak.")
    if tds["applies"]:
        say += f" TDS Sec 393(1): {_rs(tds['tds'])} kaatiye ({tds['rate']}% on {_rs(tds['on'])}) aur 26Q mein dikhaiye."
    return {"purchase_id": bid, "lines": out, "total": total, "due_date": due.isoformat(), "tds": tds, "say": say}


def pay_supplier(tenant: str, supplier: str, amount, mode: str = "neft", on: str = "", note: str = "") -> dict:
    """She paid a supplier (Hoola never pays): note it against the oldest bills."""
    amt = R.money(amount)
    if amt <= 0:
        raise ThokError("Rakam bataiye.")
    d = _date(on, today(tenant))
    with _LOCK, session() as s:
        p = _party(s, tenant, supplier, "supplier")
        s.add(ThokPayment(tenant_id=tenant, party_id=p.id, direction="out", mode=(mode or "neft")[:8], amount=R.r2(amt), on=d.isoformat(),
                          note=str(note)[:300]))
        left = amt
        for b in s.scalars(select(ThokPurchase).where(ThokPurchase.supplier_id == p.id).order_by(ThokPurchase.bill_date)).all():
            room = b.total - b.tds - b.paid
            if room <= 0.005 or left <= 0.005:
                continue
            put = min(room, left)
            b.paid = R.r2(b.paid + put)
            left -= put
        pid, name = p.id, p.name
    return {"say": f"{name} ko {_rs(amt)} diya, note kiya. Ab dena {_rs(party_view(tenant, pid)['supplier']['payable'])}."}


def payables(tenant: str) -> dict:
    on = today(tenant)
    out = []
    with session() as s:
        ps = {p.id: p for p in s.scalars(select(ThokParty).where(ThokParty.tenant_id == tenant)).all()}
        for b in s.scalars(select(ThokPurchase).where(ThokPurchase.tenant_id == tenant).order_by(ThokPurchase.due_date)).all():
            left = R.r2(b.total - b.tds - b.paid)
            if left <= 0.5:
                continue
            p = ps.get(b.supplier_id)
            dd = _date(b.due_date, on)
            out.append({"supplier": p.name if p else "", "msme": bool(p and p.msme), "bill_no": b.bill_no, "bill_date": b.bill_date,
                        "due_date": b.due_date, "days_left": (dd - on).days, "amount": left})
    soon = [x for x in out if x["msme"] and x["days_left"] <= 5]
    return {"bills": out, "total": R.r2(sum(x["amount"] for x in out)), "msme_soon": soon,
            "say": f"Suppliers ko dena {_rs(sum(x['amount'] for x in out))}" + (f"; MSME {len(soon)} bill 5 din mein / paar." if soon else ".")}


# ---------------------------------------------------------------- stock speed, reorder, margins
def _sold(tenant: str, days: int = 30) -> dict[str, float]:
    since = (today(tenant) - timedelta(days=days)).isoformat()
    sold: dict[str, float] = {}
    with session() as s:
        for o in s.scalars(select(ThokOrder).where(ThokOrder.tenant_id == tenant, ThokOrder.status == "billed",
                                                   ThokOrder.bill_date >= since)).all():
            for x in _j(o.lines, []):
                sold[x["key"]] = sold.get(x["key"], 0.0) + float(x["qty"])
    return sold


def reorder(tenant: str, cover_days: int = 15) -> dict:
    sold = _sold(tenant, 30)
    its = items(tenant)
    with session() as s:
        ps = {p.id: p for p in s.scalars(select(ThokParty).where(ThokParty.tenant_id == tenant)).all()}
    from ..net import deal
    by_sup: dict[str, list] = {}
    for it in its:
        key = deal.norm(it["name"])
        sd = sold.get(key, 0.0)
        if it["free"] is None:
            continue
        q = R.reorder_qty(sd, it["free"], it["lead_days"], cover_days)
        low = it.get("low")
        if q <= 0 and not low:
            continue
        sup = ps.get(it["supplier_id"])
        days_left = round(it["free"] / (sd / 30), 1) if sd else None
        by_sup.setdefault(sup.name if sup else "", []).append({"item": it["name"], "unit": it["unit"], "free": it["free"], "sold_30": sd,
                                                               "days_left": days_left, "order_qty": q or (it.get("low_at") or 0),
                                                               "phone": sup.phone if sup else ""})
    drafts = []
    firm = settings(tenant)["firm"]
    for sup, rows in by_sup.items():
        if not sup:
            continue
        lines = "\n".join(f"- {r['item']}: {r['order_qty']:g} {r['unit']}" for r in rows)
        drafts.append({"supplier": sup, "to": rows[0]["phone"], "text": f"Namaste, kripya yeh maal bhej dijiye:\n{lines}\nRate pichhle bill jaisa. - {firm}"})
    n = sum(len(v) for v in by_sup.values())
    return {"suppliers": by_sup, "drafts": drafts,
            "say": f"{n} item mangwane laayak (pichhle 30 din ki bikri + {cover_days} din ka stock)." + (" Supplier ko order draft taiyaar (aap bhejengi)." if drafts else "")}


def margins(tenant: str, days: int = 30) -> dict:
    since = (today(tenant) - timedelta(days=days)).isoformat()
    with session() as s:
        metas = {m.key: m.cost for m in s.scalars(select(ThokItem).where(ThokItem.tenant_id == tenant)).all()}
        agg: dict[str, dict] = {}
        for o in s.scalars(select(ThokOrder).where(ThokOrder.tenant_id == tenant, ThokOrder.status == "billed", ThokOrder.bill_date >= since)).all():
            for x in _j(o.lines, []):
                a = agg.setdefault(x["item"], {"item": x["item"], "qty": 0.0, "sales": 0.0, "cost": 0.0, "known": True})
                a["qty"] += x["qty"]
                a["sales"] += x["taxable"]
                c = metas.get(x["key"], 0.0)
                if not c:
                    a["known"] = False
                a["cost"] += c * x["qty"]
    rows = []
    for a in agg.values():
        gp = a["sales"] - a["cost"] if a["known"] else None
        rows.append({**{k: R.r2(v) if isinstance(v, float) else v for k, v in a.items()}, "profit": R.r2(gp) if gp is not None else None,
                     "margin_pct": round(gp * 100 / a["sales"], 1) if gp is not None and a["sales"] else None})
    rows.sort(key=lambda r: -(r["profit"] or 0))
    known = [r for r in rows if r["profit"] is not None]
    tot_s, tot_p = sum(r["sales"] for r in known), sum(r["profit"] for r in known)
    thin = [r["item"] for r in known if r["margin_pct"] is not None and r["margin_pct"] < 2]
    return {"items": rows, "sales": R.r2(sum(r["sales"] for r in rows)), "profit": R.r2(tot_p),
            "margin_pct": round(tot_p * 100 / tot_s, 1) if tot_s else None,
            "say": f"Pichhle {days} din: bikri {_rs(sum(r['sales'] for r in rows))}" + (f", munafa {_rs(tot_p)} ({tot_p * 100 / tot_s:.1f}%)" if tot_s else "")
            + (". Bahut patla munafa: " + ", ".join(thin[:5]) if thin else "") + "."}


# ---------------------------------------------------------------- day
def day(tenant: str) -> dict:
    from ..net import deal
    on = today(tenant).isoformat()
    with session() as s:
        sales = sum(o.total for o in s.scalars(select(ThokOrder).where(ThokOrder.tenant_id == tenant, ThokOrder.status == "billed",
                                                                       ThokOrder.bill_date == on)).all())
        drafts = len(s.scalars(select(ThokOrder.id).where(ThokOrder.tenant_id == tenant, ThokOrder.status == "draft")).all())
        coll = sum(x.amount for x in s.scalars(select(ThokPayment).where(ThokPayment.tenant_id == tenant, ThokPayment.direction == "in",
                                                                        ThokPayment.on == on, ThokPayment.status != "bounced")).all())
        ps = {p.id: p.name for p in s.scalars(select(ThokParty).where(ThokParty.tenant_id == tenant)).all()}
        deposit = [{"party": ps.get(x.party_id, ""), "cheque_no": x.cheque_no, "amount": x.amount, "cheque_date": x.cheque_date}
                   for x in s.scalars(select(ThokPayment).where(ThokPayment.tenant_id == tenant, ThokPayment.status == "pending",
                                                                ThokPayment.cheque_date <= on)).all()]
        bounced = [{"party": ps.get(x.party_id, ""), "cheque_no": x.cheque_no, "amount": x.amount, **R.cheque_steps(_date(x.memo_date, today(tenant)))}
                   for x in s.scalars(select(ThokPayment).where(ThokPayment.tenant_id == tenant, ThokPayment.status == "bounced")).all()
                   if x.memo_date and _date(x.memo_date, today(tenant)) >= today(tenant) - timedelta(days=75)]
    o = outstanding(tenant)
    pay = payables(tenant)
    low = deal.low_stock(tenant)
    parts = [f"Aaj bikri {_rs(sales)}, vasooli {_rs(coll)}"]
    if drafts:
        parts.append(f"{drafts} order bill ke liye aapki haan ke intezaar mein")
    if deposit:
        parts.append(f"{len(deposit)} cheque aaj bank mein daalne hain ({_rs(sum(d['amount'] for d in deposit))})")
    if bounced:
        parts.append(f"{len(bounced)} bounce cheque: notice ki aakhri tareekh {bounced[0]['notice_by']}")
    if o["overdue"]:
        parts.append(f"due paar {_rs(o['overdue'])}")
    if pay["msme_soon"]:
        parts.append(f"MSME supplier ke {len(pay['msme_soon'])} bill 5 din mein")
    if low:
        parts.append("stock kam: " + ", ".join(x["name"] for x in low[:5]))
    return {"sales": sales, "collected": coll, "drafts": drafts, "deposit": deposit, "bounced": bounced, "outstanding": o["total"],
            "overdue": o["overdue"], "payables": pay["total"], "msme_soon": pay["msme_soon"], "low_stock": low,
            "say": "; ".join(parts) + "."}


def due_mornings() -> list[str]:
    from ..life import tz_of
    out = []
    with session() as s:
        for r in s.scalars(select(ThokSettings)).all():
            if not s.scalars(select(ThokParty.id).where(ThokParty.tenant_id == r.tenant_id).limit(1)).first():
                continue
            local = datetime.now(tz_of(r.tenant_id))
            try:
                hh, mm = [int(x) for x in (r.morning_time or "08:30").split(":")]
            except ValueError:
                hh, mm = 8, 30
            late = (local.hour * 60 + local.minute) - (hh * 60 + mm)
            d = local.date().isoformat()
            if r.last_morning != d and 0 <= late <= 180:
                r.last_morning = d
                out.append(r.tenant_id)
    return out


def send_morning(tenant: str) -> dict:
    from ..events import notify
    from ..net.service import home_conv
    d = day(tenant)
    r = route_plan(tenant)
    text = "Thok: " + r["say"] + " " + d["say"].split("; ", 1)[-1] if r["visit"] else "Thok: " + d["say"]
    conv = home_conv(tenant)
    try:
        notify(conv, text)
    except Exception:
        pass
    _publish(tenant, "thok_day", {"text": text}, conv)
    return {"text": text}
