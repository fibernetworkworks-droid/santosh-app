"""v0.115 Franchise Sahayak: Hoola as a franchise owner's coworker, end to end.

  1. Gets the job: "aaj Koregaon outlet ki sale 48,000", the POS day-end export (Petpooja / POSist CSV), "is mahine ka
     royalty statement", "kaun sa outlet ghaate mein", "FSSAI kab khatam", a brand audit / opening checklist.
  2. Does the work, step by step: her agreements (brand, royalty %, marketing %, tech fee, minimum guarantee, base gross /
     net, foreign franchisor, term, lock-in, notice), outlets (rent, lease, targets), daily sales, monthly costs by kind,
     royalty + marketing + GST (or reverse charge) + TDS per month, outlet P&L with ratios, break-even, licence dates,
     SOP checklist scores.
  3. Checked against the rules and earlier work: minimum-guarantee top-up, GST 18% / RCM, TDS Sec 393(1) on royalty
     (Rs 50,000 a year) and rent (Rs 50,000 a month), FSSAI renewal window / late fee / after-expiry penalties, cost
     ratios vs her targets, sales vs the same weekday last week, outlets compared, agreement renewal notice / lock-in /
     lease end, failed SOP items that keep coming back.
  4. Ready as a card, a file or a draft: royalty statement + the monthly sales report for the franchisor (draft), outlet
     P&L Excel, licence list, audit score card.
  5. Waits for her Haan: the statement / report goes to the franchisor only on her Haan (owner); Hoola never pays royalty,
     never files on the FSSAI / municipal portal, never reads the agreement as legal advice.
  6. Delivers and learns: statements marked paid, ratios month by month, recurring audit misses, best / worst outlet.
"""
from __future__ import annotations

import csv
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

log = logging.getLogger("santosh.franchise")
_LOCK = threading.Lock()


class FrError(Exception):
    pass


class FrSettings(Base):
    __tablename__ = "fr_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company: Mapped[str] = mapped_column(String(160), default="")
    state: Mapped[str] = mapped_column(String(2), default="27")
    tds_applies: Mapped[bool] = mapped_column(Boolean, default=True)       # she must deduct TDS (company / firm / audited)
    morning_time: Mapped[str] = mapped_column(String(5), default="10:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")


class FrAgreement(Base):
    __tablename__ = "fr_agreements"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fa"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    brand: Mapped[str] = mapped_column(String(120), default="")
    franchisor: Mapped[str] = mapped_column(String(160), default="")
    contact: Mapped[str] = mapped_column(String(160), default="")          # email / phone for reports
    royalty_pct: Mapped[float] = mapped_column(Float, default=0.0)
    marketing_pct: Mapped[float] = mapped_column(Float, default=0.0)
    tech_fee: Mapped[float] = mapped_column(Float, default=0.0)            # fixed per outlet per month
    min_guarantee: Mapped[float] = mapped_column(Float, default=0.0)       # minimum royalty per outlet per month
    base: Mapped[str] = mapped_column(String(5), default="net")             # net (after discount, before GST) | gross
    foreign: Mapped[bool] = mapped_column(Boolean, default=False)
    franchisor_state: Mapped[str] = mapped_column(String(2), default="")
    due_day: Mapped[int] = mapped_column(Integer, default=10)
    start: Mapped[str] = mapped_column(String(10), default="")
    term_years: Mapped[int] = mapped_column(Integer, default=0)
    lock_in_years: Mapped[int] = mapped_column(Integer, default=0)
    notice_months: Mapped[int] = mapped_column(Integer, default=0)
    checklist: Mapped[str] = mapped_column(Text, default="[]")             # brand SOP items
    notes: Mapped[str] = mapped_column(Text, default="")


class FrOutlet(Base):
    __tablename__ = "fr_outlets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fo"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    agreement_id: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    city: Mapped[str] = mapped_column(String(60), default="")
    opened_on: Mapped[str] = mapped_column(String(10), default="")
    rent: Mapped[float] = mapped_column(Float, default=0.0)                # per month
    lease_end: Mapped[str] = mapped_column(String(10), default="")
    escalation_pct: Mapped[float] = mapped_column(Float, default=0.0)
    escalation_on: Mapped[str] = mapped_column(String(10), default="")
    targets: Mapped[str] = mapped_column(Text, default="{}")
    manager_phone: Mapped[str] = mapped_column(String(20), default="")


class FrSale(Base):
    __tablename__ = "fr_sales"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fs"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    outlet_id: Mapped[str] = mapped_column(String(40), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)
    gross: Mapped[float] = mapped_column(Float, default=0.0)               # before discount, before GST
    discount: Mapped[float] = mapped_column(Float, default=0.0)
    gst: Mapped[float] = mapped_column(Float, default=0.0)
    net: Mapped[float] = mapped_column(Float, default=0.0)                 # after discount, before GST
    orders: Mapped[int] = mapped_column(Integer, default=0)
    channels: Mapped[str] = mapped_column(Text, default="{}")


class FrCost(Base):
    __tablename__ = "fr_costs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    outlet_id: Mapped[str] = mapped_column(String(40), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="other")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str] = mapped_column(String(200), default="")


class FrLicence(Base):
    __tablename__ = "fr_licences"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    outlet_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="other")
    number: Mapped[str] = mapped_column(String(40), default="")
    valid_to: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(String(200), default="")


class FrAudit(Base):
    __tablename__ = "fr_audits"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fu"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    outlet_id: Mapped[str] = mapped_column(String(40), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="daily")         # daily | brand
    items: Mapped[str] = mapped_column(Text, default="[]")                 # [{item, ok, note}]
    score: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str] = mapped_column(Text, default="")


class FrStatement(Base):
    __tablename__ = "fr_statements"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ft"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    agreement_id: Mapped[str] = mapped_column(String(40), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    data: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(10), default="draft")      # draft | approved | paid
    paid_on: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ---------------------------------------------------------------- helpers
def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _num(v) -> float:
    if v in (None, ""):
        return 0.0
    s = str(v).replace(",", "").replace("₹", "")
    m = re.search(r"-?\d+(\.\d+)?", s)
    n = float(m.group(0)) if m else 0.0
    if re.search(r"lakh|lac", s, re.I):
        n *= 1e5
    elif re.search(r"\d\s*k\b", s, re.I):
        n *= 1e3
    return n


def _rs(v) -> str:
    v = round(float(v or 0))
    s = str(abs(v))
    if len(s) > 3:
        s = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", s[:-3]) + "," + s[-3:]
    return ("-" if v < 0 else "") + "₹" + s


def today(tenant: str) -> date:
    from ..life import tz_of
    return datetime.now(tz_of(tenant)).date()


def _date(v, default: date | None = None) -> date | None:
    if isinstance(v, date):
        return v
    if v in (None, ""):
        return default
    from ..analyst.service import _date as d
    return d(v) or default


def add_months(d: date, n: int) -> date:
    from calendar import monthrange
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, monthrange(y, m)[1]))


def _month(v: str, on: date) -> str:
    if v and re.fullmatch(r"\d{4}-\d{2}", v):
        return v
    if v in ("last", "pichhla", "pichle"):
        return add_months(on.replace(day=1), -1).strftime("%Y-%m")
    d = _date(v)
    return (d or on).strftime("%Y-%m")


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
        log.exception("franchise publish failed")


def _st(s, tenant: str) -> FrSettings:
    r = s.get(FrSettings, tenant)
    if r is None:
        r = FrSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def settings(tenant: str) -> dict:
    with session() as s:
        r = _st(s, tenant)
        return {"company": r.company, "state": r.state, "tds_applies": r.tds_applies, "morning_time": r.morning_time}


def save_settings(tenant: str, **kw: Any) -> dict:
    with session() as s:
        r = _st(s, tenant)
        if kw.get("company") is not None:
            r.company = str(kw["company"])[:160]
        if kw.get("state"):
            r.state = str(kw["state"]).zfill(2)[:2]
        if "tds_applies" in kw:
            r.tds_applies = bool(kw["tds_applies"])
        if kw.get("morning_time"):
            r.morning_time = str(kw["morning_time"]).zfill(5)[:5]
    return settings(tenant)


# ---------------------------------------------------------------- agreements + outlets
def _agr(s, tenant: str, ref: str) -> FrAgreement:
    rows = s.scalars(select(FrAgreement).where(FrAgreement.tenant_id == tenant)).all()
    if not rows:
        raise FrError("Pehle brand ka agreement jodiye (brand, royalty %, marketing %).")
    if not ref:
        if len(rows) == 1:
            return rows[0]
        raise FrError("Kaun sa brand? " + ", ".join(r.brand for r in rows))
    for r in rows:
        if r.id == ref or r.brand.lower() == ref.lower() or ref.lower() in r.brand.lower():
            return r
    raise FrError(f"Brand '{ref}' nahi mila.")


def _agr_view(a: FrAgreement) -> dict:
    d = R.agreement_dates(_date(a.start), a.term_years, a.notice_months, a.lock_in_years, add_months) if a.start else {}
    return {"id": a.id, "brand": a.brand, "franchisor": a.franchisor, "contact": a.contact, "royalty_pct": a.royalty_pct,
            "marketing_pct": a.marketing_pct, "tech_fee": a.tech_fee, "min_guarantee": a.min_guarantee, "base": a.base,
            "foreign": a.foreign, "franchisor_state": a.franchisor_state, "due_day": a.due_day, "start": a.start,
            "term_years": a.term_years, "lock_in_years": a.lock_in_years, "notice_months": a.notice_months,
            "checklist": _j(a.checklist, []), "dates": d, "notes": a.notes}


def save_agreement(tenant: str, brand: str, **kw: Any) -> dict:
    if not str(brand).strip():
        raise FrError("Brand ka naam chahiye.")
    with _LOCK, session() as s:
        a = next((r for r in s.scalars(select(FrAgreement).where(FrAgreement.tenant_id == tenant)).all()
                  if r.brand.lower() == str(brand).strip().lower()), None)
        new = a is None
        if new:
            a = FrAgreement(tenant_id=tenant, brand=str(brand).strip()[:120])
            s.add(a)
        for k in ("royalty_pct", "marketing_pct"):
            if kw.get(k) not in (None, ""):
                v = _num(kw[k])
                if not 0 <= v <= 30:
                    raise FrError(f"{k} 0-30% ke beech.")
                setattr(a, k, v)
        for k in ("tech_fee", "min_guarantee"):
            if kw.get(k) not in (None, ""):
                setattr(a, k, _num(kw[k]))
        for k in ("franchisor", "contact", "notes"):
            if kw.get(k):
                setattr(a, k, str(kw[k])[:500])
        if kw.get("base") in ("net", "gross"):
            a.base = kw["base"]
        if "foreign" in kw and kw["foreign"] is not None:
            a.foreign = bool(kw["foreign"])
        if kw.get("franchisor_state"):
            a.franchisor_state = str(kw["franchisor_state"]).zfill(2)[:2]
        for k in ("due_day", "term_years", "lock_in_years", "notice_months"):
            if kw.get(k) not in (None, ""):
                setattr(a, k, max(0, int(_num(kw[k]))))
        if kw.get("start"):
            d = _date(kw["start"])
            if not d:
                raise FrError("Agreement shuru hone ki tareekh samajh nahi aayi.")
            a.start = d.isoformat()
        if isinstance(kw.get("checklist"), list):
            a.checklist = json.dumps([str(x).strip()[:120] for x in kw["checklist"] if str(x).strip()][:60], ensure_ascii=False)
        s.flush()
        v = _agr_view(a)
    say = f"{'Naya brand' if new else 'Update'}: {v['brand']} - royalty {v['royalty_pct']:g}%" + (f", marketing {v['marketing_pct']:g}%" if v["marketing_pct"] else "") \
        + (f", min {_rs(v['min_guarantee'])}/mahina" if v["min_guarantee"] else "") + (" (videshi franchisor: GST reverse charge)" if v["foreign"] else "") + "."
    if v["dates"].get("notice_by"):
        say += f" Renewal notice {v['dates']['notice_by']} tak."
    return {"agreement": v, "say": say}


def agreements(tenant: str) -> list[dict]:
    with session() as s:
        return [_agr_view(a) for a in s.scalars(select(FrAgreement).where(FrAgreement.tenant_id == tenant)).all()]


def _outlet(s, tenant: str, ref: str) -> FrOutlet:
    rows = s.scalars(select(FrOutlet).where(FrOutlet.tenant_id == tenant)).all()
    if not rows:
        raise FrError("Pehle outlet jodiye.")
    if not ref:
        if len(rows) == 1:
            return rows[0]
        raise FrError("Kaun sa outlet? " + ", ".join(r.name for r in rows))
    for r in rows:
        if r.id == ref or r.name.lower() == ref.lower():
            return r
    hits = [r for r in rows if ref.lower() in r.name.lower() or ref.lower() == r.city.lower()]
    if len(hits) == 1:
        return hits[0]
    raise FrError(f"Outlet '{ref}' nahi mila." if not hits else "Kai outlet: " + ", ".join(h.name for h in hits))


def save_outlet(tenant: str, name: str, brand: str = "", city: str = "", opened_on: str = "", rent=None, lease_end: str = "",
                escalation_pct=None, escalation_on: str = "", targets: dict | None = None, manager_phone: str = "") -> dict:
    if not str(name).strip():
        raise FrError("Outlet ka naam chahiye.")
    with _LOCK, session() as s:
        o = next((r for r in s.scalars(select(FrOutlet).where(FrOutlet.tenant_id == tenant)).all() if r.name.lower() == name.strip().lower()), None)
        new = o is None
        if new:
            a = _agr(s, tenant, brand)
            o = FrOutlet(tenant_id=tenant, agreement_id=a.id, name=name.strip()[:120])
            s.add(o)
        elif brand:
            o.agreement_id = _agr(s, tenant, brand).id
        if city:
            o.city = str(city)[:60]
        for k, v in (("opened_on", opened_on), ("lease_end", lease_end), ("escalation_on", escalation_on)):
            if v:
                d = _date(v)
                if not d:
                    raise FrError(f"Tareekh samajh nahi aayi: {v}")
                setattr(o, k, d.isoformat())
        if rent not in (None, ""):
            o.rent = _num(rent)
        if escalation_pct not in (None, ""):
            o.escalation_pct = _num(escalation_pct)
        if targets:
            t = _j(o.targets, {})
            t.update({k: float(v) for k, v in targets.items() if k in R.COST_KINDS})
            o.targets = json.dumps(t)
        if manager_phone:
            o.manager_phone = re.sub(r"[^\d+]", "", str(manager_phone))[:20]
        s.flush()
        v = {"id": o.id, "name": o.name, "city": o.city, "agreement_id": o.agreement_id, "rent": o.rent, "lease_end": o.lease_end,
             "targets": {**R.TARGETS, **_j(o.targets, {})}}
    say = f"{'Naya outlet' if new else 'Update'}: {v['name']}" + (f", kiraya {_rs(v['rent'])}" if v["rent"] else "") + "."
    if v["rent"] and v["rent"] > R.TDS_RENT["month_threshold"]:
        say += f" Kiraya Rs 50,000/mahina se upar: TDS {R.TDS_RENT['rate']:g}% (Sec 393(1)) kaatna pad sakta hai."
    return {"outlet": v, "say": say}


def outlets(tenant: str) -> list[dict]:
    with session() as s:
        ags = {a.id: a.brand for a in s.scalars(select(FrAgreement).where(FrAgreement.tenant_id == tenant)).all()}
        return [{"id": o.id, "name": o.name, "brand": ags.get(o.agreement_id, ""), "city": o.city, "rent": o.rent, "lease_end": o.lease_end,
                 "opened_on": o.opened_on, "targets": {**R.TARGETS, **_j(o.targets, {})}}
                for o in s.scalars(select(FrOutlet).where(FrOutlet.tenant_id == tenant).order_by(FrOutlet.name)).all()]


# ---------------------------------------------------------------- sales + costs
def add_sale(tenant: str, outlet: str, net=None, day: str = "", gross=None, discount=None, gst=None, orders=None,
             channels: dict | None = None) -> dict:
    on = today(tenant)
    d = _date(day, on - timedelta(days=0))
    if d > on:
        raise FrError("Aage ki tareekh ki sale nahi.")
    g, disc = _num(gross), _num(discount)
    n = _num(net) if net not in (None, "") else (g - disc)
    if n <= 0 and g <= 0:
        raise FrError("Sale ki rakam bataiye.")
    if not g:
        g = n + disc
    with _LOCK, session() as s:
        o = _outlet(s, tenant, outlet)
        row = s.scalars(select(FrSale).where(FrSale.outlet_id == o.id, FrSale.day == d.isoformat())).first() or \
            FrSale(tenant_id=tenant, outlet_id=o.id, day=d.isoformat())
        s.add(row)
        row.gross, row.discount, row.net, row.gst = round(g, 2), round(disc, 2), round(n, 2), round(_num(gst), 2)
        row.orders = int(_num(orders))
        if channels:
            row.channels = json.dumps({str(k)[:20]: _num(v) for k, v in channels.items()})
        oid, oname = o.id, o.name
    cmp = _same_day_last_week(tenant, oid, d)
    say = f"{oname} {d.strftime('%d %b')}: {_rs(n)}" + (f", {int(_num(orders))} bill (ausat {_rs(n / _num(orders))})" if _num(orders) else "")
    if cmp is not None:
        say += f"; pichhle hafte isi din se {'+' if cmp >= 0 else ''}{cmp}%."
    return {"say": say + ("" if say.endswith(".") else "."), "vs_last_week": cmp}


def _same_day_last_week(tenant: str, oid: str, d: date) -> int | None:
    with session() as s:
        a = s.scalars(select(FrSale).where(FrSale.outlet_id == oid, FrSale.day == d.isoformat())).first()
        b = s.scalars(select(FrSale).where(FrSale.outlet_id == oid, FrSale.day == (d - timedelta(days=7)).isoformat())).first()
        if not a or not b or not b.net:
            return None
        return round((a.net - b.net) * 100 / b.net)


_COLS = {"day": ("date", "bill date", "day", "business date"), "gross": ("gross", "gross sales", "sub total", "subtotal", "my amount"),
         "discount": ("discount", "discounts"), "gst": ("tax", "gst", "total tax", "taxes"), "net": ("net", "net sales", "net amount"),
         "orders": ("orders", "bills", "no of bills", "invoices", "order count"), "outlet": ("outlet", "restaurant", "store", "location"),
         "total": ("total", "grand total")}


def import_sales(tenant: str, outlet: str = "", data: bytes | None = None, name: str = "sales.csv", file_id: str = "") -> dict:
    """POS day-wise export (Petpooja / POSist / any CSV or Excel with date + sales columns)."""
    from ..analyst.service import _load_file, _rows
    if file_id:
        name, data = _load_file(tenant, file_id)
    rows = _rows(name, data or b"")
    hi, cols = None, {}
    for i, r in enumerate(rows[:15]):
        h = [re.sub(r"\s+", " ", str(x or "").strip().lower()) for x in r]
        f = {}
        for j, x in enumerate(h):
            for k, ns in _COLS.items():
                if x in ns and k not in f:
                    f[k] = j
        if "day" in f and ({"net", "gross", "total"} & set(f)):
            hi, cols = i, f
            break
    if hi is None:
        raise FrError("File mein tareekh aur sale (net / gross / total) ka column chahiye.")
    n, errs = 0, []
    for r in rows[hi + 1:]:
        g = lambda k: r[cols[k]] if k in cols and cols[k] < len(r) else None  # noqa: E731
        d = _date(g("day"))
        if not d:
            continue
        net = _num(g("net")) if "net" in cols else (_num(g("gross")) - _num(g("discount")) if "gross" in cols else _num(g("total")) - _num(g("gst")))
        try:
            add_sale(tenant, str(g("outlet") or outlet), net, d.isoformat(), g("gross"), g("discount"), g("gst"), g("orders"))
            n += 1
        except FrError as e:
            errs.append(f"{d}: {e}")
    return {"days": n, "errors": errs[:20], "say": f"{n} din ki sale chadhi." + (f" {len(errs)} line mein dikkat." if errs else "")}


_KIND_WORDS = {"food": ("food", "raw", "maal", "kirana", "material", "cogs", "sabzi", "doodh", "milk", "inventory"),
               "staff": ("staff", "salary", "salaries", "wages", "tankhwah", "payroll"),
               "rent": ("rent", "kiraya", "cam", "lease"), "utility": ("bijli", "electric", "power", "water", "pani", "gas", "utility", "lpg"),
               "aggregator": ("swiggy", "zomato", "aggregator", "commission", "magicpin"),
               "marketing": ("marketing", "ads", "pamphlet", "promotion", "local"), "maintenance": ("repair", "maintenance", "amc", "service")}


def cost_kind(kind: str) -> str:
    k = str(kind or "").lower().strip()
    if k in R.COST_KINDS:
        return k
    for c, words in _KIND_WORDS.items():
        if any(w in k for w in words):
            return c
    return "other"


def add_cost(tenant: str, outlet: str, kind: str, amount, month: str = "", note: str = "") -> dict:
    k = cost_kind(kind)
    amt = _num(amount)
    if amt <= 0:
        raise FrError("Kharche ki rakam bataiye.")
    m = _month(month, today(tenant))
    with session() as s:
        o = _outlet(s, tenant, outlet)
        s.add(FrCost(tenant_id=tenant, outlet_id=o.id, month=m, kind=k, amount=round(amt, 2), note=str(note)[:200]))
        oname = o.name
    return {"say": f"{oname} {m}: {R.COST_KINDS[k]} {_rs(amt)} likha."}


# ---------------------------------------------------------------- royalty statement (her Haan to send)
def _sales_month(s, oid: str, month: str) -> dict:
    rows = s.scalars(select(FrSale).where(FrSale.outlet_id == oid, FrSale.day.like(f"{month}-%"))).all()
    return {"gross": round(sum(r.gross for r in rows), 2), "discount": round(sum(r.discount for r in rows), 2), "net": round(sum(r.net for r in rows), 2),
            "gst": round(sum(r.gst for r in rows), 2), "orders": sum(r.orders for r in rows), "days": len(rows)}


def statement(tenant: str, brand: str = "", month: str = "", conv: str = "") -> dict:
    on = today(tenant)
    m = _month(month or "last", on)
    with _LOCK, session() as s:
        st = _st(s, tenant)
        a = _agr(s, tenant, brand)
        outs = s.scalars(select(FrOutlet).where(FrOutlet.agreement_id == a.id)).all()
        if not outs:
            raise FrError(f"{a.brand} ka koi outlet nahi.")
        lines, tot = [], {"base": 0.0, "royalty": 0.0, "min_topup": 0.0, "marketing": 0.0, "tech": 0.0}
        for o in outs:
            sm = _sales_month(s, o.id, m)
            base = sm["gross"] if a.base == "gross" else sm["net"]
            ry = R.royalty(base, a.royalty_pct, a.min_guarantee)
            mk = round(base * a.marketing_pct / 100, 2)
            lines.append({"outlet": o.name, "days": sm["days"], "orders": sm["orders"], "gross": sm["gross"], "discount": sm["discount"],
                          "net": sm["net"], "base": round(base, 2), **ry, "marketing": mk, "tech": a.tech_fee})
            tot["base"] += base
            tot["royalty"] += ry["royalty"]
            tot["min_topup"] += ry["min_topup"]
            tot["marketing"] += mk
            tot["tech"] += a.tech_fee
        fees = round(tot["royalty"] + tot["marketing"] + tot["tech"], 2)
        intra = not a.franchisor_state or a.franchisor_state == st.state
        g = R.fee_gst(fees, a.foreign, intra)
        fy0 = _fy_start(date.fromisoformat(m + "-01")).strftime("%Y-%m")
        before = sum(_j(x.data, {}).get("fees", 0.0) for x in s.scalars(select(FrStatement).where(
            FrStatement.agreement_id == a.id, FrStatement.month >= fy0, FrStatement.month < m)).all())
        tds = R.tds_on_fee(before, tot["royalty"] + tot["tech"], st.tds_applies and not a.foreign)
        payable = round(fees + (0 if a.foreign else g["gst"]) - tds["tds"], 2)
        data = {"month": m, "brand": a.brand, "lines": lines, **{k: round(v, 2) for k, v in tot.items()}, "fees": fees, "gst": g, "tds": tds,
                "payable": payable, "due": (date.fromisoformat(m + "-01").replace(day=1) + timedelta(days=32)).replace(day=min(a.due_day or 10, 28)).isoformat()}
        row = s.scalars(select(FrStatement).where(FrStatement.agreement_id == a.id, FrStatement.month == m)).first()
        if row and row.status == "paid":
            raise FrError(f"{m} ka statement bhara ja chuka hai.")
        if row is None:
            row = FrStatement(tenant_id=tenant, agreement_id=a.id, month=m)
            s.add(row)
        row.data, row.status = json.dumps(data, ensure_ascii=False), "draft"
        s.flush()
        sid = row.id
    f = statement_file(tenant, sid, conv)
    say = (f"{a.brand} {m}: sale {_rs(tot['base'])} ({a.base}), royalty {_rs(tot['royalty'])}" + (f" (min guarantee top-up {_rs(tot['min_topup'])})" if tot["min_topup"] else "")
           + (f", marketing {_rs(tot['marketing'])}" if tot["marketing"] else "") + (f", tech {_rs(tot['tech'])}" if tot["tech"] else "")
           + f". {g['say']}" + (f" TDS {_rs(tds['tds'])} kaatiye (Sec 393(1), 10%)." if tds["tds"] else "")
           + f" Dena {_rs(payable)} {data['due']} tak. Franchisor ko report bhejne se pehle aapki haan.")
    _publish(tenant, "fr_statement", {"statement_id": sid, "brand": a.brand, "month": m, "payable": payable}, conv)
    return {"statement_id": sid, "statement": data, "file": f["file"], "say": say}


def statement_file(tenant: str, sid: str, conv: str = "") -> dict:
    import openpyxl
    from .. import chatfiles
    with session() as s:
        row = s.get(FrStatement, sid)
        if not row or row.tenant_id != tenant:
            raise FrError("Statement nahi mila.")
        d = _j(row.data, {})
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales report"
    ws.append([f"{d['brand']} - monthly sales & royalty - {d['month']}"])
    ws.append(["Outlet", "Days", "Bills", "Gross", "Discount", "Net", "Royalty base", "Royalty", "Min guarantee top-up", "Marketing", "Tech fee"])
    for x in d["lines"]:
        ws.append([x["outlet"], x["days"], x["orders"], x["gross"], x["discount"], x["net"], x["base"], x["royalty"], x["min_topup"], x["marketing"], x["tech"]])
    ws.append([])
    ws.append(["Fees total", d["fees"]])
    ws.append(["GST 18%" + (" (RCM, paid by us)" if d["gst"]["how"] == "rcm" else ""), d["gst"]["gst"]])
    ws.append(["TDS deducted", d["tds"]["tds"]])
    ws.append(["Net payable", d["payable"], "Due", d["due"]])
    bio = io.BytesIO()
    wb.save(bio)
    f = chatfiles.store(tenant, f"Royalty-{re.sub(r'[^A-Za-z0-9]+', '_', d['brand'])}-{d['month']}.xlsx", bio.getvalue(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    _publish(tenant, "pc_file", {**f, "source": "franchise", "title": f"Royalty {d['brand']} {d['month']}"}, conv)
    return {"file": f}


def approve_statement(tenant: str, sid: str) -> dict:
    with session() as s:
        row = s.get(FrStatement, sid)
        if not row or row.tenant_id != tenant:
            raise FrError("Statement nahi mila.")
        if row.status == "paid":
            raise FrError("Pehle se bhara.")
        row.status = "approved"
        d = _j(row.data, {})
        a = s.get(FrAgreement, row.agreement_id)
        firm = _st(s, tenant).company
        to = a.contact if a else ""
    text = (f"Dear {d['brand']} team,\nPlease find attached the sales and royalty statement for {d['month']}: royalty base Rs {d['base']:,.0f}, "
            f"royalty Rs {d['royalty']:,.0f}, marketing Rs {d['marketing']:,.0f}, net payable Rs {d['payable']:,.0f}"
            + (f" after TDS of Rs {d['tds']['tds']:,.0f}" if d["tds"]["tds"] else "") + f". Payment will be made by {d['due']}.\nRegards,\n{firm}")
    return {"to": to, "text": text, "say": "Haan mili: franchisor ke liye message taiyaar (Excel saath lagaakar aap bhejiye). Payment aap bank se karengi."}


def mark_paid(tenant: str, sid: str, on: str = "") -> dict:
    with session() as s:
        row = s.get(FrStatement, sid)
        if not row or row.tenant_id != tenant:
            raise FrError("Statement nahi mila.")
        row.status, row.paid_on = "paid", (_date(on, today(tenant))).isoformat()
        d = _j(row.data, {})
    say = f"{d['brand']} {d['month']} ka {_rs(d['payable'])} bhara, note kiya."
    if d["tds"]["tds"]:
        say += " TDS agle mahine ki 7 tareekh tak jama kariye aur 26Q mein dikhaiye."
    if d["gst"]["how"] == "rcm":
        say += " RCM ka IGST is mahine ke 3B mein cash se."
    return {"say": say}


def statements(tenant: str, brand: str = "") -> list[dict]:
    with session() as s:
        q = select(FrStatement).where(FrStatement.tenant_id == tenant)
        if brand:
            q = q.where(FrStatement.agreement_id == _agr(s, tenant, brand).id)
        return [{"id": x.id, "month": x.month, "status": x.status, "paid_on": x.paid_on, **{k: _j(x.data, {}).get(k) for k in ("brand", "payable", "due", "base")}}
                for x in s.scalars(q.order_by(FrStatement.month.desc())).all()][:60]


# ---------------------------------------------------------------- P&L, compare
def pnl(tenant: str, outlet: str, month: str = "") -> dict:
    on = today(tenant)
    m = _month(month or "last", on)
    with session() as s:
        o = _outlet(s, tenant, outlet)
        a = s.get(FrAgreement, o.agreement_id)
        sm = _sales_month(s, o.id, m)
        costs: dict[str, float] = {}
        for c in s.scalars(select(FrCost).where(FrCost.outlet_id == o.id, FrCost.month == m)).all():
            costs[c.kind] = costs.get(c.kind, 0.0) + c.amount
        if "rent" not in costs and o.rent:
            costs["rent"] = o.rent
        base = sm["gross"] if a.base == "gross" else sm["net"]
        ry = R.royalty(base, a.royalty_pct, a.min_guarantee)
        fees = ry["royalty"] + base * a.marketing_pct / 100 + a.tech_fee
        if "royalty" not in costs:
            costs["royalty"] = round(fees, 2)
        targets = {**R.TARGETS, **_j(o.targets, {})}
        name = o.name
    total_cost = sum(costs.values())
    profit = round(sm["net"] - total_cost, 2)
    rt = R.ratios(sm["net"], costs)
    fl = R.flags(rt, targets)
    var_pct = sum(rt.get(k, 0) for k in ("food", "aggregator")) + a.royalty_pct + a.marketing_pct
    fixed = sum(v for k, v in costs.items() if k not in ("food", "aggregator", "royalty")) + a.tech_fee
    be = R.break_even(fixed, var_pct)
    missing = [R.COST_KINDS[k] for k in ("food", "staff") if k not in costs]
    say = (f"{name} {m}: sale {_rs(sm['net'])} ({sm['days']} din), kharcha {_rs(total_cost)}, {'munafa' if profit >= 0 else 'ghaata'} {_rs(abs(profit))}"
           + (f" ({profit * 100 / sm['net']:.1f}%)" if sm["net"] else "") + ".")
    if fl:
        say += " Zyada: " + ", ".join(fl) + "."
    if be:
        say += f" Break-even ~{_rs(be)}/mahina."
    if missing:
        say += " Kharcha nahi likha: " + ", ".join(missing) + "."
    return {"outlet": name, "month": m, "sales": sm, "costs": {k: round(v, 2) for k, v in costs.items()}, "ratios": rt, "targets": targets,
            "profit": profit, "flags": fl, "break_even": be, "say": say}


def compare(tenant: str, month: str = "") -> dict:
    rows = []
    for o in outlets(tenant):
        try:
            p = pnl(tenant, o["id"], month)
        except FrError:
            continue
        rows.append({"outlet": o["name"], "brand": o["brand"], "net": p["sales"]["net"], "orders": p["sales"]["orders"],
                     "aov": round(p["sales"]["net"] / p["sales"]["orders"], 0) if p["sales"]["orders"] else None, "profit": p["profit"],
                     "margin_pct": round(p["profit"] * 100 / p["sales"]["net"], 1) if p["sales"]["net"] else None, "flags": p["flags"]})
    rows.sort(key=lambda r: -(r["margin_pct"] or -999))
    say = ""
    if rows:
        say = f"Sabse achha: {rows[0]['outlet']} ({rows[0]['margin_pct']}%)."
        if len(rows) > 1:
            say += f" Sabse kamzor: {rows[-1]['outlet']} ({rows[-1]['margin_pct']}%)" + (f" - {', '.join(rows[-1]['flags'][:2])}" if rows[-1]["flags"] else "") + "."
    return {"outlets": rows, "say": say or "Abhi data nahi."}


def pnl_file(tenant: str, month: str = "", conv: str = "") -> dict:
    import openpyxl
    from .. import chatfiles
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Outlets"
    kinds = list(R.COST_KINDS)
    ws.append(["Outlet", "Month", "Net sales", "Bills"] + [R.COST_KINDS[k] for k in kinds] + ["Profit", "Margin %"])
    for o in outlets(tenant):
        try:
            p = pnl(tenant, o["id"], month)
        except FrError:
            continue
        ws.append([o["name"], p["month"], p["sales"]["net"], p["sales"]["orders"]] + [p["costs"].get(k, 0) for k in kinds]
                  + [p["profit"], round(p["profit"] * 100 / p["sales"]["net"], 1) if p["sales"]["net"] else ""])
    bio = io.BytesIO()
    wb.save(bio)
    f = chatfiles.store(tenant, "Outlet_PnL.xlsx", bio.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    _publish(tenant, "pc_file", {**f, "source": "franchise", "title": "Outlet P&L"}, conv)
    return {"file": f, "say": "Har outlet ka P&L Excel mein."}


# ---------------------------------------------------------------- licences, agreement dates
def save_licence(tenant: str, outlet: str, kind: str, valid_to: str, number: str = "", note: str = "") -> dict:
    k = kind if kind in R.LICENCES else next((c for c, (label, _) in R.LICENCES.items() if kind.lower() in label.lower()), "other")
    d = _date(valid_to)
    if not d:
        raise FrError("Licence kab tak valid hai (tareekh)?")
    with session() as s:
        o = _outlet(s, tenant, outlet)
        row = s.scalars(select(FrLicence).where(FrLicence.outlet_id == o.id, FrLicence.kind == k)).first() or \
            FrLicence(tenant_id=tenant, outlet_id=o.id, kind=k)
        s.add(row)
        row.valid_to, row.number, row.note = d.isoformat(), str(number)[:40] or row.number, str(note)[:200]
        oname = o.name
    stv = R.licence_status(k, d, today(tenant))
    return {"say": f"{oname}: {stv['text']}", "status": stv}


def licences(tenant: str) -> dict:
    on = today(tenant)
    out = []
    with session() as s:
        names = {o.id: o.name for o in s.scalars(select(FrOutlet).where(FrOutlet.tenant_id == tenant)).all()}
        for l2 in s.scalars(select(FrLicence).where(FrLicence.tenant_id == tenant)).all():
            st = R.licence_status(l2.kind, date.fromisoformat(l2.valid_to), on)
            out.append({"id": l2.id, "outlet": names.get(l2.outlet_id, ""), "kind": l2.kind, "name": R.LICENCES.get(l2.kind, ("", 0))[0],
                        "number": l2.number, "valid_to": l2.valid_to, **st})
    out.sort(key=lambda x: x["days"])
    due = [x for x in out if x["state"] != "ok"]
    return {"licences": out, "due": due, "say": (f"{len(due)} licence par dhyaan: " + "; ".join(f"{x['outlet']} {x['text']}" for x in due[:4])) if due else "Saare licence theek."}


def dates_watch(tenant: str) -> list[dict]:
    on = today(tenant)
    out = []
    for a in agreements(tenant):
        d = a["dates"]
        for k, label in (("notice_by", "renewal notice"), ("end", "agreement khatam"), ("lock_in_till", "lock-in khatam")):
            if d.get(k):
                dd = date.fromisoformat(d[k])
                if 0 <= (dd - on).days <= 120:
                    out.append({"what": f"{a['brand']}: {label}", "on": d[k], "days": (dd - on).days})
    with session() as s:
        for o in s.scalars(select(FrOutlet).where(FrOutlet.tenant_id == tenant)).all():
            for k, label in (("lease_end", "lease khatam"), ("escalation_on", f"kiraya {o.escalation_pct:g}% badhega")):
                v = getattr(o, k)
                if v:
                    dd = date.fromisoformat(v)
                    if 0 <= (dd - on).days <= 90:
                        out.append({"what": f"{o.name}: {label}", "on": v, "days": (dd - on).days})
    return sorted(out, key=lambda x: x["days"])


# ---------------------------------------------------------------- SOP audits
def audit(tenant: str, outlet: str, failed: list[str] | None = None, items: list[dict] | None = None, kind: str = "daily",
          day: str = "", note: str = "") -> dict:
    on = today(tenant)
    d = _date(day, on)
    with _LOCK, session() as s:
        o = _outlet(s, tenant, outlet)
        a = s.get(FrAgreement, o.agreement_id)
        checklist = _j(a.checklist, [])
        if items:
            res = [{"item": str(x.get("item", ""))[:120], "ok": bool(x.get("ok")), "note": str(x.get("note", ""))[:200]} for x in items if isinstance(x, dict)]
        else:
            if not checklist:
                raise FrError("Brand ka SOP checklist nahi jodha (agreement mein checklist).")
            bad = [f.lower() for f in failed or []]
            res = [{"item": c, "ok": not any(b in c.lower() for b in bad), "note": ""} for c in checklist]
        if not res:
            raise FrError("Checklist khaali.")
        score = round(sum(1 for x in res if x["ok"]) * 100 / len(res), 1)
        s.add(FrAudit(tenant_id=tenant, outlet_id=o.id, day=d.isoformat(), kind=kind[:12], items=json.dumps(res, ensure_ascii=False), score=score,
                      note=str(note)[:500]))
        since = (d - timedelta(days=30)).isoformat()
        misses: dict[str, int] = {}
        for au in s.scalars(select(FrAudit).where(FrAudit.outlet_id == o.id, FrAudit.day >= since)).all():
            for x in _j(au.items, []):
                if not x["ok"]:
                    misses[x["item"]] = misses.get(x["item"], 0) + 1
        oname, phone = o.name, o.manager_phone
    repeat = [k for k, v in misses.items() if v >= 3]
    failed_now = [x["item"] for x in res if not x["ok"]]
    say = f"{oname} {kind} audit: {score:g}%." + (f" Chooke: {', '.join(failed_now)}." if failed_now else " Sab theek.")
    if repeat:
        say += f" Baar-baar chook (30 din mein 3+): {', '.join(repeat)} - manager se baat kariye."
    draft = {"to": phone, "text": f"{oname} audit {d.strftime('%d %b')}: {score:g}%. Theek kariye: {', '.join(failed_now)}."} if failed_now and phone else None
    return {"score": score, "failed": failed_now, "repeat": repeat, "draft": draft, "say": say}


# ---------------------------------------------------------------- day
def day(tenant: str) -> dict:
    on = today(tenant)
    y = on - timedelta(days=1)
    parts, sales = [], []
    with session() as s:
        for o in s.scalars(select(FrOutlet).where(FrOutlet.tenant_id == tenant)).all():
            r = s.scalars(select(FrSale).where(FrSale.outlet_id == o.id, FrSale.day == y.isoformat())).first()
            sales.append({"outlet": o.name, "net": r.net if r else None, "vs_last_week": _same_day_last_week(tenant, o.id, y) if r else None})
        due_st = [x for x in s.scalars(select(FrStatement).where(FrStatement.tenant_id == tenant, FrStatement.status != "paid")).all()]
    missing = [x["outlet"] for x in sales if x["net"] is None]
    if sales and any(x["net"] is not None for x in sales):
        parts.append("Kal: " + ", ".join(f"{x['outlet']} {_rs(x['net'])}" + (f" ({'+' if x['vs_last_week'] >= 0 else ''}{x['vs_last_week']}%)" if x["vs_last_week"] is not None else "")
                                         for x in sales if x["net"] is not None))
    if missing:
        parts.append("Kal ki sale nahi aayi: " + ", ".join(missing))
    lic = licences(tenant)["due"]
    if lic:
        parts.append(f"{len(lic)} licence par dhyaan")
    for st in due_st:
        d = _j(st.data, {})
        dd = _date(d.get("due"))
        if dd and (dd - on).days <= 3:
            parts.append(f"{d.get('brand')} royalty {_rs(d.get('payable'))} {d.get('due')} tak")
    if on.day <= 3 and agreements(tenant):
        parts.append("Pichhle mahine ka royalty statement banana hai")
    watch = dates_watch(tenant)
    if watch:
        parts.append(f"{watch[0]['what']} {watch[0]['on']}")
    return {"sales": sales, "licences": lic, "watch": watch, "say": ("; ".join(parts) + ".") if parts else "Franchise: sab theek."}


def due_mornings() -> list[str]:
    from ..life import tz_of
    out = []
    with session() as s:
        for r in s.scalars(select(FrSettings)).all():
            if not s.scalars(select(FrOutlet.id).where(FrOutlet.tenant_id == r.tenant_id).limit(1)).first():
                continue
            local = datetime.now(tz_of(r.tenant_id))
            try:
                hh, mm = [int(x) for x in (r.morning_time or "10:00").split(":")]
            except ValueError:
                hh, mm = 10, 0
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
    text = "Franchise: " + d["say"]
    conv = home_conv(tenant)
    try:
        notify(conv, text)
    except Exception:
        pass
    _publish(tenant, "fr_day", {"text": text}, conv)
    return {"text": text}


_ = (csv,)
