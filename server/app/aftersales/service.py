"""After-sales Sahayak: Hoola as a dealer's / service business's after-sales coworker, end to end.

  1. Gets the job: "Kothrud ke Sharma ji ka Kent RO 12 March ko lagaya", her installed-base sheet (Excel / CSV), "AC
     service ka season aa gaya, kiska due hai?", "Sunil ko kal Ramesh ji ke ghar bhejo", the technician's "filter badla,
     TDS 60, membrane theek", "Luminous ka claim no. 4471 aaya".
  2. Does the work: installed-base register (customer, product, model, serial, install date, warranty end from the
     INSTALL date, AMC plan / expiry, area + pincode); service schedule per product type (her own months / km / hours or
     the starting values) -> next due per machine; due list; reminder drafts; technician roster (skills, areas /
     pincodes, visits a day, days off) -> free slots grouped by area so a technician's day stays in one part of town,
     never two visits at once, travel time between areas; job card for the technician (checklist per product, readings,
     warranty / AMC cover, past visits); visit done -> parts, readings, photos, customer signature picture -> next due.
  3. Checked against the rules and earlier work: who pays (brand warranty / comprehensive AMC / labour-only AMC /
     customer), part prices from her list only, readings vs the last visit, a machine back within 30 days ("comeback"),
     warranty counted from installation (DoCA Nov 2023), utility vs marketing WhatsApp wording (Meta).
  4. Ready as a card, a file or a draft: due-list reminder drafts, visit confirmation, the visit report PDF + message,
     AMC renewal notice, warranty claim list.
  5. Waits for her: a CHARGE to the customer only on her tap (`decide_charge(by_tap=True)` = API only); a business
     WhatsApp template / message only on her tap (`send_message`, API only); drafts she sends from her own phone.
     Hoola never moves money and never messages a customer by itself.
  6. Delivers and learns: next due from the real visit date and the machine's real usage per day, technician's on-time
     record and comebacks, claim days with each brand, AMC renewal rate and revenue.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import re
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import rules as R

log = logging.getLogger("santosh.aftersales")
_LOCK = threading.Lock()
OPEN = ("booked", "on_way")
MAX_PHOTOS = 20


class AsError(Exception):
    pass


# ---------------------------------------------------------------- tables
class AsSettings(Base):
    __tablename__ = "aftersales_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    gst_on: Mapped[bool] = mapped_column(Boolean, default=False)
    gst_pct: Mapped[float] = mapped_column(Float, default=18.0)
    sac: Mapped[str] = mapped_column(String(8), default="9987")
    schedule: Mapped[str] = mapped_column(Text, default="{}")       # {ptype: {months, usage}}
    prices: Mapped[str] = mapped_column(Text, default="{}")         # {"visit": 300, "ro": 350, "parts": {"sediment filter": 250}}
    day_start: Mapped[str] = mapped_column(String(5), default="09:30")
    day_end: Mapped[str] = mapped_column(String(5), default="18:30")
    work_days: Mapped[str] = mapped_column(String(40), default="[0,1,2,3,4,5]")
    travel_minutes: Mapped[int] = mapped_column(Integer, default=30)
    lead_minutes: Mapped[int] = mapped_column(Integer, default=60)
    remind_days: Mapped[int] = mapped_column(Integer, default=7)     # reminder drafts this many days before due
    terms: Mapped[str] = mapped_column(Text, default="")
    rules: Mapped[str] = mapped_column(Text, default="[]")
    morning_time: Mapped[str] = mapped_column(String(5), default="08:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    seq_visit: Mapped[int] = mapped_column(Integer, default=0)
    seq_claim: Mapped[int] = mapped_column(Integer, default=0)


class AsCustomer(Base):
    __tablename__ = "aftersales_customers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("asc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(15), default="", index=True)
    area: Mapped[str] = mapped_column(String(80), default="")
    pincode: Mapped[str] = mapped_column(String(6), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    no_messages: Mapped[bool] = mapped_column(Boolean, default=False)   # said "message mat bhejo"
    marketing_ok: Mapped[bool] = mapped_column(Boolean, default=False)  # agreed to offers / renewal notices
    notes: Mapped[str] = mapped_column(Text, default="")


class AsUnit(Base):
    __tablename__ = "aftersales_units"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("asu"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    customer_id: Mapped[str] = mapped_column(String(40), index=True)
    ptype: Mapped[str] = mapped_column(String(20), default="other")
    brand: Mapped[str] = mapped_column(String(60), default="")
    model: Mapped[str] = mapped_column(String(80), default="")
    serial: Mapped[str] = mapped_column(String(60), default="", index=True)
    installed_on: Mapped[str] = mapped_column(String(10), default="")
    purchased_on: Mapped[str] = mapped_column(String(10), default="")
    warranty_until: Mapped[str] = mapped_column(String(10), default="")
    warranty_note: Mapped[str] = mapped_column(String(300), default="")
    amc_plan: Mapped[str] = mapped_column(String(20), default="")
    amc_start: Mapped[str] = mapped_column(String(10), default="")
    amc_until: Mapped[str] = mapped_column(String(10), default="")
    amc_visits: Mapped[int] = mapped_column(Integer, default=0)
    amc_price: Mapped[float] = mapped_column(Float, default=0.0)
    amc_history: Mapped[str] = mapped_column(Text, default="[]")
    last_service: Mapped[str] = mapped_column(String(10), default="")
    reading: Mapped[float | None] = mapped_column(Float, nullable=True)
    reading_on: Mapped[str] = mapped_column(String(10), default="")
    per_day: Mapped[float | None] = mapped_column(Float, nullable=True)
    next_due: Mapped[str] = mapped_column(String(10), default="", index=True)
    due_why: Mapped[str] = mapped_column(String(120), default="")
    reminded_for: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(10), default="active")   # active | removed
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AsTech(Base):
    __tablename__ = "aftersales_techs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ast"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    phone: Mapped[str] = mapped_column(String(15), default="")
    skills: Mapped[str] = mapped_column(Text, default="[]")       # ptypes; [] = all
    areas: Mapped[str] = mapped_column(Text, default="[]")        # names / pincode prefixes; [] = everywhere
    per_day: Mapped[int] = mapped_column(Integer, default=6)
    off_days: Mapped[str] = mapped_column(String(40), default="[6]")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AsVisit(Base):
    __tablename__ = "aftersales_visits"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("asv"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    unit_id: Mapped[str] = mapped_column(String(40), index=True)
    customer_id: Mapped[str] = mapped_column(String(40), index=True)
    tech_id: Mapped[str] = mapped_column(String(40), index=True, default="")
    kind: Mapped[str] = mapped_column(String(12), default="service")
    start: Mapped[str] = mapped_column(String(16), index=True, default="")   # local "YYYY-MM-DD HH:MM"
    minutes: Mapped[int] = mapped_column(Integer, default=60)
    status: Mapped[str] = mapped_column(String(10), default="booked")       # booked | on_way | done | cancelled | no_show
    problem: Mapped[str] = mapped_column(Text, default="")
    checklist: Mapped[str] = mapped_column(Text, default="{}")
    readings: Mapped[str] = mapped_column(Text, default="{}")
    parts: Mapped[str] = mapped_column(Text, default="[]")
    labour: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    photos: Mapped[str] = mapped_column(Text, default="[]")
    signature: Mapped[str] = mapped_column(String(300), default="")
    signed_by: Mapped[str] = mapped_column(String(80), default="")
    done_on: Mapped[str] = mapped_column(String(16), default="")
    cover: Mapped[str] = mapped_column(Text, default="{}")
    charge: Mapped[str] = mapped_column(Text, default="{}")    # {lines, gst, total, status none|pending|needs_price|approved|rejected, paid}
    report_file: Mapped[str] = mapped_column(String(60), default="")
    comeback_of: Mapped[str] = mapped_column(String(40), default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AsMessage(Base):
    __tablename__ = "aftersales_messages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("asm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    customer_id: Mapped[str] = mapped_column(String(40), index=True)
    unit_id: Mapped[str] = mapped_column(String(40), default="")
    visit_id: Mapped[str] = mapped_column(String(40), default="")
    kind: Mapped[str] = mapped_column(String(16), default="due")     # due | visit | report | amc | warranty
    key: Mapped[str] = mapped_column(String(80), default="", index=True)  # dedupe: kind:unit:date
    phone: Mapped[str] = mapped_column(String(15), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(10), default="UTILITY")
    template: Mapped[str] = mapped_column(String(60), default="")
    params: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(10), default="draft")  # draft | sent | skipped
    via: Mapped[str] = mapped_column(String(12), default="")
    wa_msg_id: Mapped[str] = mapped_column(String(80), default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AsClaim(Base):
    __tablename__ = "aftersales_claims"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("asw"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    unit_id: Mapped[str] = mapped_column(String(40), index=True)
    visit_id: Mapped[str] = mapped_column(String(40), default="")
    brand: Mapped[str] = mapped_column(String(60), default="")
    part: Mapped[str] = mapped_column(String(120), default="")
    fault: Mapped[str] = mapped_column(Text, default="")
    brand_ref: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(14), default="raised")   # raised | approved | part_received | rejected | settled
    raised_on: Mapped[str] = mapped_column(String(10), default="")
    updated_on: Mapped[str] = mapped_column(String(10), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    settled: Mapped[float] = mapped_column(Float, default=0.0)
    log: Mapped[str] = mapped_column(Text, default="[]")


CLAIM_STATES = ("raised", "approved", "part_received", "rejected", "settled")


# ---------------------------------------------------------------- helpers
def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _dump(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def _num(v) -> float | None:
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"-?\d+(\.\d+)?", str(v).replace(",", "").replace("₹", ""))
    return float(m.group(0)) if m else None


def _rs(v) -> str:
    v = round(float(v or 0))
    s = str(abs(v))
    if len(s) > 3:
        s = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", s[:-3]) + "," + s[-3:]
    return ("-" if v < 0 else "") + "₹" + s


def _digits(p) -> str:
    d = re.sub(r"\D", "", str(p or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d[-10:] if len(d) >= 10 else d


def _tz(tenant: str):
    from ..life import tz_of
    return tz_of(tenant)


def now_local(tenant: str) -> datetime:
    """Her wall clock, without tzinfo (visits are stored in her local time). Tests replace this."""
    return datetime.now(_tz(tenant)).replace(tzinfo=None, second=0, microsecond=0)


def today(tenant: str) -> date:
    return now_local(tenant).date()


def _date(v, default: date | None = None) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if v in (None, ""):
        return default
    from ..analyst.service import _date as d
    s = str(v).strip()
    return d(s[:10]) or d(s) or default


def _when(tenant: str, v) -> datetime | None:
    """'2026-10-25 11:00', '25-10-2026 3:30 pm', 'kal 11 baje', 'aaj 4 baje' -> local naive datetime."""
    if isinstance(v, datetime):
        return v.replace(tzinfo=None, second=0, microsecond=0)
    s = re.sub(r"^(\d{4}-\d\d-\d\d)t", r"\1 ", str(v or "").strip().lower())
    if not s:
        return None
    base = today(tenant)
    if re.search(r"\b(parso|parson)\b", s):
        d = base + timedelta(days=2)
    elif re.search(r"\b(kal|tomorrow)\b", s):
        d = base + timedelta(days=1)
    elif re.search(r"\b(aaj|today)\b", s):
        d = base
    else:
        m = re.search(r"\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}", s)
        d = _date(m.group(0)) if m else None
        if d is None:
            return None
        s = s.replace(m.group(0), " ")
    m = re.search(r"(\d{1,2})(?::|\.)(\d{2})\s*(am|pm)?|(\d{1,2})\s*(am|pm|baje)", s)
    hh, mm = 10, 0
    if m:
        if m.group(1):
            hh, mm, ap = int(m.group(1)), int(m.group(2)), m.group(3)
        else:
            hh, mm, ap = int(m.group(4)), 0, m.group(5)
        if ap == "pm" and hh < 12:
            hh += 12
        if ap == "am" and hh == 12:
            hh = 0
        if ap == "baje" and 1 <= hh <= 7:
            hh += 12                     # "4 baje" in a shop day = 4 pm
        if re.search(r"\b(shaam|sham|evening|dopahar)\b", s) and hh < 12:
            hh += 12
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return datetime(d.year, d.month, d.day, hh, mm)


def _fmt(t: datetime) -> str:
    return t.strftime("%Y-%m-%d %H:%M")


def _say_when(start: str) -> str:
    try:
        t = datetime.strptime(start, "%Y-%m-%d %H:%M")
    except ValueError:
        return start
    h = t.strftime("%I:%M").lstrip("0")
    return f"{t.day} {t.strftime('%b')}, {h} {'baje subah' if t.hour < 12 else 'baje'}"


def _hm(s: str, default: str) -> tuple[int, int]:
    try:
        h, m = [int(x) for x in (s or default).split(":")]
        return h, m
    except ValueError:
        h, m = [int(x) for x in default.split(":")]
        return h, m


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("aftersales publish failed")


def _st(s, tenant: str) -> AsSettings:
    r = s.get(AsSettings, tenant)
    if r is None:
        r = AsSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def _log(row, what: str, by: str = "owner") -> None:
    lg = _j(row.log, [])
    lg.append({"at": now().isoformat(timespec="seconds"), "by": by, "what": what[:300]})
    row.log = _dump(lg[-60:])


def _business(tenant: str, st: AsSettings | None = None) -> str:
    if st is not None and st.business:
        return st.business
    try:
        from ..employee import service as emp
        p = emp.profile(tenant) or {}
        return p.get("business_name") or ""
    except Exception:
        return ""


def _first(name: str) -> str:
    n = str(name or "").strip().split(" ")
    return n[0] if n and n[0] else "Graahak"


def _wa(phone: str, text: str) -> str:
    return f"https://wa.me/91{phone}?text={quote(text)}" if len(phone) == 10 else ""


def _sms(phone: str, text: str) -> str:
    return f"sms:+91{phone}?body={quote(text)}" if len(phone) == 10 else ""


# ---------------------------------------------------------------- settings
def _sv(r: AsSettings) -> dict:
    return {"business": r.business, "phone": r.phone, "address": r.address, "gstin": r.gstin, "gst_on": r.gst_on, "gst_pct": r.gst_pct,
            "sac": r.sac, "schedule": _j(r.schedule, {}), "prices": _j(r.prices, {}), "day_start": r.day_start, "day_end": r.day_end,
            "work_days": _j(r.work_days, []), "travel_minutes": r.travel_minutes, "lead_minutes": r.lead_minutes,
            "remind_days": r.remind_days, "terms": r.terms, "rules": _j(r.rules, []), "morning_time": r.morning_time}


def settings(tenant: str) -> dict:
    with session() as s:
        return _sv(_st(s, tenant))


def save_settings(tenant: str, **kw: Any) -> dict:
    with session() as s:
        r = _st(s, tenant)
        for k in ("business", "address", "terms", "sac"):
            if kw.get(k) is not None:
                setattr(r, k, str(kw[k]).strip()[:500])
        if kw.get("phone"):
            r.phone = _digits(kw["phone"])
        if kw.get("gstin"):
            from ..gstp.rules import valid_gstin
            g = str(kw["gstin"]).strip().upper()
            if not valid_gstin(g):
                raise AsError(f"GSTIN galat lagta hai: {g}")
            r.gstin = g
        if kw.get("gst_on") is not None:
            if kw["gst_on"] and not (r.gstin or kw.get("gstin")):
                raise AsError("GST lagane ke liye pehle GSTIN chahiye.")
            r.gst_on = bool(kw["gst_on"])
        for k in ("gst_pct",):
            if _num(kw.get(k)) is not None:
                r.gst_pct = max(0.0, min(40.0, _num(kw[k])))
        for k, lo, hi in (("travel_minutes", 0, 240), ("lead_minutes", 0, 1440), ("remind_days", 0, 60)):
            if _num(kw.get(k)) is not None:
                setattr(r, k, int(max(lo, min(hi, _num(kw[k])))))
        for k in ("day_start", "day_end", "morning_time"):
            if kw.get(k):
                m = re.match(r"^(\d{1,2}):(\d{2})$", str(kw[k]).strip())
                if not m:
                    raise AsError(f"{k}: samay HH:MM mein likhiye")
                setattr(r, k, f"{int(m.group(1)):02d}:{m.group(2)}")
        if kw.get("work_days") is not None:
            days = sorted({int(x) for x in kw["work_days"] if str(x).isdigit() and 0 <= int(x) <= 6})
            if not days:
                raise AsError("Kam se kam ek kaam ka din chahiye (0 = Somvar ... 6 = Ravivar).")
            r.work_days = _dump(days)
        if isinstance(kw.get("prices"), dict):
            p = _j(r.prices, {})
            for k, v in kw["prices"].items():
                if k == "parts" and isinstance(v, dict):
                    parts = p.get("parts") or {}
                    for pn, pv in v.items():
                        if _num(pv) is not None:
                            parts[str(pn).strip().lower()[:60]] = _num(pv)
                    p["parts"] = parts
                elif _num(v) is not None:
                    p[str(k).strip().lower()[:30]] = _num(v)
            r.prices = _dump(p)
        if kw.get("rule"):
            rl = _j(r.rules, [])
            if str(kw["rule"]).strip() not in rl:
                rl.append(str(kw["rule"]).strip()[:300])
            r.rules = _dump(rl[-30:])
        return _sv(r)


def set_schedule(tenant: str, ptype: str, months=None, usage=None) -> dict:
    pt = R.ptype_of(ptype, ptype)
    with session() as s:
        r = _st(s, tenant)
        sch = _j(r.schedule, {})
        cur = sch.get(pt) or {}
        if _num(months) is not None:
            if not 1 <= _num(months) <= 60:
                raise AsError("Mahine 1 se 60 ke beech.")
            cur["months"] = int(_num(months))
        if _num(usage) is not None:
            cur["usage"] = float(_num(usage))
        if not cur:
            sch.pop(pt, None)
        else:
            sch[pt] = cur
        r.schedule = _dump(sch)
        units = s.scalars(select(AsUnit).where(AsUnit.tenant_id == tenant, AsUnit.ptype == pt, AsUnit.status == "active")).all()
        for u in units:
            _recompute(u, sch)
    lab = R.PRODUCTS[pt]["label"]
    return {"ptype": pt, "schedule": cur, "updated": len(units),
            "say": f"{lab}: har {R.interval_months(pt, sch)} mahine" + (f" ya {cur['usage']:g} {R.PRODUCTS[pt].get('usage_unit', '')}" if cur.get("usage") else "")
                   + f". {len(units)} machine ki agli tareekh nayi."}


def schedules(tenant: str) -> list[dict]:
    sch = settings(tenant)["schedule"]
    out = []
    for k, p in R.PRODUCTS.items():
        mine = sch.get(k) or {}
        out.append({"ptype": k, "label": p["label"], "months": R.interval_months(k, sch), "usage": R.usage_step(k, sch) or None,
                    "usage_unit": p.get("usage_unit", ""), "mine": bool(mine), "checklist": p["checklist"]})
    return out


# ---------------------------------------------------------------- customers + installed base
def _customer(s, tenant: str, name: str = "", phone: str = "", area: str = "", pincode: str = "", address: str = "", cid: str = "") -> AsCustomer:
    ph = _digits(phone)
    c = None
    if cid:
        c = s.get(AsCustomer, cid)
        if c is None or c.tenant_id != tenant:
            raise AsError("Graahak nahi mila.")
    if c is None and len(ph) == 10:
        c = s.scalars(select(AsCustomer).where(AsCustomer.tenant_id == tenant, AsCustomer.phone == ph)).first()
    if c is None and name and not ph:
        hits = s.scalars(select(AsCustomer).where(AsCustomer.tenant_id == tenant)).all()
        hits = [h for h in hits if h.name.lower() == str(name).strip().lower()]
        if len(hits) == 1:
            c = hits[0]
    if c is None:
        if not str(name).strip() and len(ph) != 10:
            raise AsError("Graahak ka naam ya 10 ank ka mobile chahiye.")
        if ph and len(ph) != 10:
            raise AsError(f"Mobile number 10 ank ka chahiye: {phone}")
        c = AsCustomer(tenant_id=tenant, phone=ph)
        s.add(c)
    if name:
        c.name = str(name).strip()[:120]
    if area:
        c.area = str(area).strip()[:80]
    pin = re.sub(r"\D", "", str(pincode or ""))
    if pin:
        if not re.fullmatch(r"[1-9]\d{5}", pin):
            raise AsError(f"Pincode 6 ank ka chahiye: {pincode}")
        c.pincode = pin
    if address:
        c.address = str(address).strip()[:500]
        if not c.pincode:
            m = re.search(r"\b([1-9]\d{5})\b", c.address)
            if m:
                c.pincode = m.group(1)
    s.flush()
    return c


def save_customer(tenant: str, name: str = "", phone: str = "", area: str = "", pincode: str = "", address: str = "", customer: str = "",
                  no_messages: bool | None = None, marketing_ok: bool | None = None, notes: str = "") -> dict:
    with _LOCK, session() as s:
        c = _customer(s, tenant, name, phone, area, pincode, address, customer)
        if no_messages is not None:
            c.no_messages = bool(no_messages)
        if marketing_ok is not None:
            c.marketing_ok = bool(marketing_ok)
        if notes:
            c.notes = str(notes)[:1000]
        return _cust_view(c)


def _cust_view(c: AsCustomer) -> dict:
    return {"id": c.id, "name": c.name, "phone": c.phone, "area": c.area, "pincode": c.pincode, "address": c.address,
            "no_messages": c.no_messages, "marketing_ok": c.marketing_ok, "notes": c.notes}


def _recompute(u: AsUnit, schedule: dict) -> None:
    amc_on = bool(_date(u.amc_until) and _date(u.amc_until) >= today(u.tenant_id))
    nd = R.next_due(u.ptype, _date(u.last_service), _date(u.installed_on), schedule, u.amc_visits if amc_on else 0,
                    u.reading, u.per_day, _date(u.reading_on))
    u.next_due = nd["due"].isoformat() if nd["due"] else ""
    u.due_why = nd["why"][:120]


def _place(c: AsCustomer | None) -> dict:
    return {"area": c.area if c else "", "pincode": c.pincode if c else ""}


def save_unit(tenant: str, unit: str = "", ptype: str = "", brand: str = "", model: str = "", serial: str = "", installed_on: str = "",
              purchased_on: str = "", warranty_months=None, warranty_until: str = "", last_service: str = "", reading=None, notes: str = "",
              name: str = "", phone: str = "", area: str = "", pincode: str = "", address: str = "", customer: str = "",
              status: str = "") -> dict:
    with _LOCK, session() as s:
        st = _st(s, tenant)
        sch = _j(st.schedule, {})
        u = _unit(s, tenant, unit) if unit else None
        new = u is None
        if new:
            c = _customer(s, tenant, name, phone, area, pincode, address, customer)
            if serial:
                dup = s.scalars(select(AsUnit).where(AsUnit.tenant_id == tenant, AsUnit.serial == str(serial).strip(), AsUnit.status == "active")).first()
                if dup:
                    raise AsError(f"Serial {serial} pehle se register hai ({dup.brand} {dup.model}).")
            u = AsUnit(tenant_id=tenant, customer_id=c.id)
            s.add(u)
        else:
            c = s.get(AsCustomer, u.customer_id)
            if any((name, phone, area, pincode, address)):
                _customer(s, tenant, name, phone if _digits(phone) != c.phone else "", area, pincode, address, c.id)
        text = " ".join(str(x) for x in (ptype, brand, model) if x)
        if ptype or new:
            u.ptype = R.ptype_of(text, ptype)
        for k, v in (("brand", brand), ("model", model), ("serial", serial), ("notes", notes)):
            if v:
                setattr(u, k, str(v).strip()[:300 if k == "notes" else 80])
        for k, v in (("installed_on", installed_on), ("purchased_on", purchased_on), ("last_service", last_service)):
            if v:
                d = _date(v)
                if not d:
                    raise AsError(f"Tareekh samajh nahi aayi: {v}")
                if d > today(tenant):
                    raise AsError(f"Yeh tareekh aage ki hai: {v}")
                setattr(u, k, d.isoformat())
        if not u.installed_on and u.purchased_on:
            u.installed_on = u.purchased_on
        if warranty_until:
            d = _date(warranty_until)
            if not d:
                raise AsError(f"Warranty ki tareekh samajh nahi aayi: {warranty_until}")
            u.warranty_until = d.isoformat()
        elif warranty_months is not None or (new and u.installed_on):
            months = int(_num(warranty_months) or R.PRODUCTS[u.ptype]["warranty"])
            w = R.warranty_until(_date(u.installed_on), months, _date(u.purchased_on))
            if w["until"]:
                u.warranty_until = w["until"].isoformat()
            u.warranty_note = w["note"][:300]
        if _num(reading) is not None:
            _set_reading(u, _num(reading), today(tenant))
        if status in ("active", "removed"):
            u.status = status
        _recompute(u, sch)
        s.flush()
        v = _unit_view(s, u)
    say = (f"{'Naya' if new else 'Update'}: {v['customer']['name'] or v['customer']['phone']} ka {v['label']}"
           + (f" {v['brand']} {v['model']}".rstrip() if v["brand"] or v["model"] else "") + ".")
    if v["warranty_until"]:
        say += f" Warranty {v['warranty_until']} tak (install se)."
    if v["warranty_note"]:
        say += " " + v["warranty_note"]
    if v["next_due"]:
        say += f" Agli service {v['next_due']} ({v['due_why']})."
    return {"unit": v, "say": say}


def _set_reading(u: AsUnit, val: float, on: date) -> None:
    prev, prev_on = u.reading, _date(u.reading_on)
    if prev is not None and prev_on and on > prev_on and val >= prev:
        pdv = (val - prev) / max(1, (on - prev_on).days)
        u.per_day = round(pdv if u.per_day is None else 0.6 * pdv + 0.4 * u.per_day, 2)
    u.reading, u.reading_on = val, on.isoformat()


def _unit(s, tenant: str, ref: str) -> AsUnit:
    ref = str(ref or "").strip()
    if not ref:
        raise AsError("Kaun si machine? (serial / graahak ka naam / mobile)")
    u = s.get(AsUnit, ref)
    if u and u.tenant_id == tenant:
        return u
    rows = s.scalars(select(AsUnit).where(AsUnit.tenant_id == tenant, AsUnit.status == "active")).all()
    hit = [r for r in rows if r.serial and r.serial.lower() == ref.lower()]
    if len(hit) == 1:
        return hit[0]
    ph = _digits(ref)
    cust = {c.id: c for c in s.scalars(select(AsCustomer).where(AsCustomer.tenant_id == tenant)).all()}
    words = [w for w in re.split(r"\s+", ref.lower()) if w]
    hits = []
    for r in rows:
        c = cust.get(r.customer_id)
        hay = " ".join([c.name if c else "", c.phone if c else "", r.brand, r.model, r.serial, R.PRODUCTS.get(r.ptype, {}).get("label", ""), r.ptype]).lower()
        if (len(ph) == 10 and c and c.phone == ph) or all(w in hay for w in words):
            hits.append(r)
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise AsError(f"Machine '{ref}' nahi mili.")
    raise AsError("Kai machine mili: " + "; ".join(f"{(cust.get(h.customer_id).name if cust.get(h.customer_id) else '')} {h.brand} {h.model} "
                                                   f"({h.serial or h.id})" for h in hits[:6]))


def _unit_view(s, u: AsUnit, full: bool = False) -> dict:
    c = s.get(AsCustomer, u.customer_id)
    on = today(u.tenant_id)
    nd = _date(u.next_due)
    v = {"id": u.id, "ptype": u.ptype, "label": R.PRODUCTS.get(u.ptype, R.PRODUCTS["other"])["label"], "brand": u.brand, "model": u.model,
         "serial": u.serial, "installed_on": u.installed_on, "purchased_on": u.purchased_on, "warranty_until": u.warranty_until,
         "warranty_note": u.warranty_note, "in_warranty": bool(_date(u.warranty_until) and _date(u.warranty_until) >= on),
         "amc": {"plan": u.amc_plan, "start": u.amc_start, "until": u.amc_until, "visits": u.amc_visits, "price": u.amc_price,
                 "active": bool(_date(u.amc_until) and _date(u.amc_until) >= on)} if u.amc_until else None,
         "last_service": u.last_service, "reading": u.reading, "reading_on": u.reading_on, "per_day": u.per_day,
         "next_due": u.next_due, "due_why": u.due_why, "days_to_due": (nd - on).days if nd else None, "status": u.status,
         "notes": u.notes, "customer": _cust_view(c) if c else {"name": "", "phone": "", "area": "", "pincode": ""}}
    if full:
        vs = s.scalars(select(AsVisit).where(AsVisit.unit_id == u.id).order_by(AsVisit.start.desc()).limit(20)).all()
        v["visits"] = [_visit_brief(s, x) for x in vs]
        v["claims"] = [_claim_view(x) for x in s.scalars(select(AsClaim).where(AsClaim.unit_id == u.id)).all()]
    return v


def get_unit(tenant: str, unit: str) -> dict:
    with session() as s:
        return _unit_view(s, _unit(s, tenant, unit), True)


def units(tenant: str, q: str = "", limit: int = 200) -> list[dict]:
    with session() as s:
        rows = s.scalars(select(AsUnit).where(AsUnit.tenant_id == tenant, AsUnit.status == "active").order_by(AsUnit.next_due)).all()
        out = [_unit_view(s, u) for u in rows]
    if q:
        words = q.lower().split()
        out = [u for u in out if all(w in " ".join([u["customer"]["name"], u["customer"]["phone"], u["customer"]["area"], u["customer"]["pincode"],
                                                     u["brand"], u["model"], u["serial"], u["label"]]).lower() for w in words)]
    return out[:limit]


_IMPORT_COLS = {
    "name": ("name", "customer", "customer name", "graahak", "naam", "client"),
    "phone": ("phone", "mobile", "mobile no", "contact", "phone no", "number", "mob"),
    "product": ("product", "type", "item", "machine", "category", "product type"),
    "brand": ("brand", "company", "make"),
    "model": ("model", "model no", "model number"),
    "serial": ("serial", "serial no", "sr no", "serial number", "s/n", "sl no"),
    "installed_on": ("install date", "installation date", "installed on", "date of installation", "install", "installed"),
    "purchased_on": ("purchase date", "invoice date", "bill date", "date of purchase", "purchase"),
    "warranty": ("warranty", "warranty months", "warranty till", "warranty end", "warranty upto", "warranty expiry"),
    "amc_until": ("amc", "amc expiry", "amc end", "amc till", "amc upto", "amc valid till"),
    "amc_plan": ("amc type", "amc plan", "plan"),
    "area": ("area", "locality", "location", "city", "gaon"),
    "pincode": ("pincode", "pin", "pin code", "zip"),
    "address": ("address", "pata"),
    "last_service": ("last service", "last service date", "service date", "last visit"),
}


def import_units(tenant: str, data: bytes | None = None, name: str = "units.csv", file_id: str = "") -> dict:
    from ..analyst.service import _rows
    if file_id:
        from ..analyst.service import _load_file
        name, data = _load_file(tenant, file_id)
    if not data:
        raise AsError("File khaali hai.")
    rows = _rows(name, data)
    hi, cols = None, {}
    for i, r in enumerate(rows[:15]):
        h = [re.sub(r"\s+", " ", str(x or "").strip().lower().strip(":.")) for x in r]
        f = {}
        for j, x in enumerate(h):
            for k, ns in _IMPORT_COLS.items():
                if x in ns and k not in f:
                    f[k] = j
        if ("name" in f or "phone" in f) and ({"product", "model", "serial", "brand"} & set(f)):
            hi, cols = i, f
            break
    if hi is None:
        raise AsError("Sheet mein graahak (naam / mobile) aur product / model / serial ke column chahiye.")
    added, skipped, problems = 0, 0, []
    for n, r in enumerate(rows[hi + 1:], start=hi + 2):
        g = lambda k: (str(r[cols[k]]).strip() if k in cols and cols[k] < len(r) and r[cols[k]] is not None else "")  # noqa: E731
        if not any(g(k) for k in cols):
            continue
        w = g("warranty")
        wm, wu = (None, "")
        if w:
            if _date(w):
                wu = w
            elif _num(w) is not None:
                wm = _num(w) * (12 if re.search(r"(year|yr|saal|varsh)", w.lower()) else 1)
        try:
            out = save_unit(tenant, ptype=g("product"), brand=g("brand"), model=g("model"), serial=g("serial"),
                            installed_on=g("installed_on"), purchased_on=g("purchased_on"), warranty_months=wm, warranty_until=wu,
                            last_service=g("last_service"), name=g("name"), phone=g("phone"), area=g("area"), pincode=g("pincode"),
                            address=g("address"))
            if g("amc_until"):
                d = _date(g("amc_until"))
                if d:
                    plan = "comprehensive" if "comp" in g("amc_plan").lower() and "non" not in g("amc_plan").lower() else "non_comprehensive"
                    _amc_row(tenant, out["unit"]["id"], plan, until=d)
            added += 1
        except AsError as e:
            skipped += 1
            if len(problems) < 10:
                problems.append(f"line {n}: {e}")
    return {"added": added, "skipped": skipped, "problems": problems,
            "say": f"{added} machine register mein jodi" + (f", {skipped} chhodi ({'; '.join(problems[:3])})" if skipped else "") + "."}


# ---------------------------------------------------------------- AMC
def _amc_row(tenant: str, unit_id: str, plan: str, start: date | None = None, until: date | None = None, months: int = 12,
             visits: int | None = None, price: float | None = None) -> None:
    with session() as s:
        u = s.get(AsUnit, unit_id)
        hist = _j(u.amc_history, [])
        st = start or (until and R.add_months(until, -months)) or today(tenant)
        un = until or (R.add_months(st, months) - timedelta(days=1))
        if u.amc_until:
            hist.append({"plan": u.amc_plan, "start": u.amc_start, "until": u.amc_until, "price": u.amc_price})
        u.amc_plan = plan if plan in R.AMC_PLANS else "non_comprehensive"
        u.amc_start, u.amc_until = st.isoformat(), un.isoformat()
        u.amc_visits = int(visits if visits is not None else R.PRODUCTS[u.ptype]["amc_visits"])
        u.amc_price = float(price or 0)
        u.amc_history = _dump(hist[-10:])
        _recompute(u, _j(_st(s, tenant).schedule, {}))


def set_amc(tenant: str, unit: str, plan: str = "non_comprehensive", start: str = "", months=12, visits=None, price=None) -> dict:
    """Her record of an AMC the customer took (or renewed). Recording it is bookkeeping; asking the customer to pay is her own act."""
    with session() as s:
        uid = _unit(s, tenant, unit).id
    plan = str(plan or "non_comprehensive").lower().replace("-", "_").replace(" ", "_")
    if plan in ("comp", "full"):
        plan = "comprehensive"
    if plan not in R.AMC_PLANS:
        plan = "non_comprehensive"
    st = _date(start) if start else None
    if start and not st:
        raise AsError(f"AMC shuru ki tareekh samajh nahi aayi: {start}")
    m = int(_num(months) or 12)
    if not 1 <= m <= 60:
        raise AsError("AMC 1 se 60 mahine.")
    _amc_row(tenant, uid, plan, st, None, m, int(_num(visits)) if _num(visits) is not None else None, _num(price))
    v = get_unit(tenant, uid)
    a = v["amc"]
    return {"unit": v, "say": f"AMC ({'comprehensive: part + labour' if a['plan'] == 'comprehensive' else 'labour / visit'}) {a['start']} se {a['until']} tak, "
                              f"{a['visits']} visit" + (f", {_rs(a['price'])}" if a["price"] else "") + f". Agli service {v['next_due']}."}


def amc_view(tenant: str) -> dict:
    on = today(tenant)
    with session() as s:
        rows = s.scalars(select(AsUnit).where(AsUnit.tenant_id == tenant, AsUnit.status == "active")).all()
        cust = {c.id: c for c in s.scalars(select(AsCustomer).where(AsCustomer.tenant_id == tenant)).all()}
        visits = s.scalars(select(AsVisit).where(AsVisit.tenant_id == tenant, AsVisit.status == "done")).all()
    active, expiring, renewed, lapsed = [], {30: [], 60: [], 90: []}, 0, []
    yearly, by_type = 0.0, {}
    for u in rows:
        un, st = _date(u.amc_until), _date(u.amc_start)
        c = cust.get(u.customer_id)
        if un and un >= on:
            months = max(1, round(((un - st).days + 1) / 30.4)) if st else 12
            per_year = u.amc_price * 12 / months if u.amc_price else 0
            yearly += per_year
            by_type[u.ptype] = by_type.get(u.ptype, 0) + 1
            row = {"unit_id": u.id, "customer": c.name if c else "", "phone": c.phone if c else "", "label": R.PRODUCTS[u.ptype]["label"],
                   "plan": u.amc_plan, "until": u.amc_until, "price": u.amc_price, "days_left": (un - on).days}
            active.append(row)
            for k in (30, 60, 90):
                if (un - on).days <= k:
                    expiring[k].append(row)
                    break
        for h in _j(u.amc_history, []):
            hu = _date(h.get("until"))
            if hu and (on - hu).days <= 365:
                if u.amc_start and _date(u.amc_start) and (_date(u.amc_start) - hu).days <= 60:
                    renewed += 1
        if un and un < on and (on - un).days <= 365:
            lapsed.append({"unit_id": u.id, "customer": c.name if c else "", "label": R.PRODUCTS[u.ptype]["label"], "ended": u.amc_until})
    month0 = on.replace(day=1)
    ch_month, ch_paid, unpaid = 0.0, 0.0, []
    for v in visits:
        ch = _j(v.charge, {})
        if ch.get("status") != "approved":
            continue
        d = _date(v.done_on[:10])
        if d and d >= month0:
            ch_month += ch.get("total", 0)
            ch_paid += ch.get("paid", 0)
        if ch.get("paid", 0) < ch.get("total", 0):
            unpaid.append({"visit_id": v.id, "number": v.number, "due": round(ch["total"] - ch.get("paid", 0), 2), "on": v.done_on[:10]})
    rate = round(renewed * 100 / (renewed + len(lapsed))) if (renewed + len(lapsed)) else None
    at_risk = sum(r["price"] for r in expiring[30] + expiring[60] + expiring[90])
    say = (f"AMC chal rahe: {len(active)} (saal ka ~{_rs(yearly)}). 90 din mein khatam: {sum(len(x) for x in expiring.values())} ({_rs(at_risk)})."
           + (f" Renewal {rate}%." if rate is not None else "") + f" Is mahine visit charge {_rs(ch_month)}, mila {_rs(ch_paid)}.")
    return {"active": sorted(active, key=lambda r: r["days_left"]), "count": len(active), "yearly_value": round(yearly, 2),
            "by_type": by_type, "expiring": expiring, "at_risk": round(at_risk, 2), "renewed": renewed, "lapsed": lapsed[:50],
            "renewal_rate": rate, "charges_month": round(ch_month, 2), "paid_month": round(ch_paid, 2),
            "unpaid": unpaid[:50], "say": say}


# ---------------------------------------------------------------- technicians
def _tech_view(t: AsTech) -> dict:
    return {"id": t.id, "name": t.name, "phone": t.phone, "skills": _j(t.skills, []), "areas": _j(t.areas, []), "per_day": t.per_day,
            "off_days": _j(t.off_days, []), "active": t.active}


def save_tech(tenant: str, name: str = "", tech: str = "", phone: str = "", skills: list | None = None, areas: list | None = None,
              per_day=None, off_days: list | None = None, active: bool | None = None) -> dict:
    with _LOCK, session() as s:
        t = _tech(s, tenant, tech) if tech else None
        if t is None:
            if not str(name).strip():
                raise AsError("Technician ka naam chahiye.")
            t = s.scalars(select(AsTech).where(AsTech.tenant_id == tenant, AsTech.name == str(name).strip())).first()
        if t is None:
            t = AsTech(tenant_id=tenant, name=str(name).strip()[:80])
            s.add(t)
        elif name:
            t.name = str(name).strip()[:80]
        if phone:
            ph = _digits(phone)
            if len(ph) != 10:
                raise AsError("Technician ka mobile 10 ank ka.")
            t.phone = ph
        if skills is not None:
            t.skills = _dump(sorted({R.ptype_of(x, x) for x in skills if str(x).strip()}))
        if areas is not None:
            t.areas = _dump([str(a).strip()[:40] for a in areas if str(a).strip()][:30])
        if _num(per_day) is not None:
            t.per_day = int(max(1, min(20, _num(per_day))))
        if off_days is not None:
            t.off_days = _dump(sorted({int(x) for x in off_days if str(x).isdigit() and 0 <= int(x) <= 6}))
        if active is not None:
            t.active = bool(active)
        s.flush()
        return _tech_view(t)


def _tech(s, tenant: str, ref: str) -> AsTech:
    t = s.get(AsTech, ref) if ref else None
    if t and t.tenant_id == tenant:
        return t
    rows = s.scalars(select(AsTech).where(AsTech.tenant_id == tenant)).all()
    hits = [r for r in rows if r.name.lower() == str(ref).strip().lower()] or [r for r in rows if str(ref).strip().lower() in r.name.lower()]
    if len(hits) == 1:
        return hits[0]
    raise AsError(f"Technician '{ref}' nahi mila." if not hits else "Kai technician: " + ", ".join(h.name for h in hits))


def techs(tenant: str) -> list[dict]:
    with session() as s:
        out = []
        for t in s.scalars(select(AsTech).where(AsTech.tenant_id == tenant)).all():
            v = _tech_view(t)
            done = s.scalars(select(AsVisit).where(AsVisit.tech_id == t.id, AsVisit.status == "done")).all()
            late = 0
            for x in done:
                if x.done_on and x.start and x.done_on[:10] > x.start[:10]:
                    late += 1
            v["visits_done"] = len(done)
            v["comebacks"] = sum(1 for x in done if x.comeback_of)
            v["late"] = late
            out.append(v)
        return out


# ---------------------------------------------------------------- slots + booking
def _day_visits(s, tenant: str, d: date) -> list[AsVisit]:
    return s.scalars(select(AsVisit).where(AsVisit.tenant_id == tenant, AsVisit.status.in_(OPEN),
                                           AsVisit.start >= d.isoformat(), AsVisit.start < (d + timedelta(days=1)).isoformat())).all()


def _span(v: AsVisit) -> tuple[datetime, datetime]:
    t = datetime.strptime(v.start, "%Y-%m-%d %H:%M")
    return t, t + timedelta(minutes=v.minutes)


def _fits(t: datetime, minutes: int, place: dict, others: list[tuple[datetime, datetime, dict]], travel: int) -> tuple[bool, str]:
    """No overlap with the technician's other visits; travel time between different areas."""
    e = t + timedelta(minutes=minutes)
    for a, b, pl in others:
        if t < b and a < e:
            return False, "clash"
        gap = 0 if R.same_area(place, pl) else travel
        if gap and (t < b + timedelta(minutes=gap) and a - timedelta(minutes=gap) < e):
            return False, "travel"
    return True, ""


def slots(tenant: str, unit: str, days: int = 5, tech: str = "", day: str = "", minutes=None, n: int = 8, exclude: str = "") -> dict:
    with session() as s:
        st = _st(s, tenant)
        u = _unit(s, tenant, unit)
        c = s.get(AsCustomer, u.customer_id)
        place = _place(c)
        mins = int(_num(minutes) or R.PRODUCTS[u.ptype]["minutes"])
        tl = [_tech(s, tenant, tech)] if tech else [t for t in s.scalars(select(AsTech).where(AsTech.tenant_id == tenant, AsTech.active.is_(True))).all()]
        if not tl:
            raise AsError("Pehle technician jodiye (naam, skill, area).")
        skilled = [t for t in tl if not _j(t.skills, []) or u.ptype in _j(t.skills, [])]
        pool = skilled or tl
        local = [t for t in pool if R.covers_area(_j(t.areas, []), place)]
        pool = local or pool
        work_days = _j(st.work_days, [0, 1, 2, 3, 4, 5])
        sh, sm = _hm(st.day_start, "09:30")
        eh, em = _hm(st.day_end, "18:30")
        earliest = now_local(tenant) + timedelta(minutes=st.lead_minutes)
        d0 = _date(day) or earliest.date()
        cands = []
        for k in range(max(1, min(int(days), 30))):
            d = d0 + timedelta(days=k)
            if d.weekday() not in work_days:
                continue
            visits = [v for v in _day_visits(s, tenant, d) if v.id != exclude]
            vplace = {v.id: _place(s.get(AsCustomer, v.customer_id)) for v in visits}
            for t in pool:
                if d.weekday() in _j(t.off_days, []):
                    continue
                mine = [v for v in visits if v.tech_id == t.id]
                if len(mine) >= t.per_day:
                    continue
                others = [(*_span(v), vplace[v.id]) for v in mine]
                near = sum(1 for _, _, pl in others if R.same_area(place, pl))
                cur = datetime(d.year, d.month, d.day, sh, sm)
                end = datetime(d.year, d.month, d.day, eh, em)
                per = 0
                while cur + timedelta(minutes=mins) <= end and per < 2:
                    if cur >= earliest:
                        ok, _ = _fits(cur, mins, place, others, st.travel_minutes)
                        if ok:
                            adj = any(R.same_area(place, pl) and (abs((cur - b).total_seconds()) <= 1800 or abs((cur + timedelta(minutes=mins) - a).total_seconds()) <= 1800)
                                      for a, b, pl in others)
                            score = near * 10 + (6 if adj else 0) + (3 if t in local else 0) + (2 if t in skilled and _j(t.skills, []) else 0) - k
                            why = []
                            if near:
                                why.append(f"usi din {t.name} ke {near} visit isi area mein")
                            if t in local and _j(t.areas, []):
                                why.append("unka area")
                            if _j(t.skills, []) and u.ptype in _j(t.skills, []):
                                why.append("is machine ka kaam aata hai")
                            cands.append({"tech_id": t.id, "tech": t.name, "start": _fmt(cur), "minutes": mins, "score": score,
                                          "why": ", ".join(why) or "khaali samay"})
                            per += 1
                            if adj or near:
                                cur += timedelta(minutes=mins)
                                continue
                    cur += timedelta(minutes=30)
        cands.sort(key=lambda x: (-x["score"], x["start"]))
        out = cands[:max(1, min(int(n), 20))]
        label = R.PRODUCTS[u.ptype]["label"]
        cname = c.name if c else ""
    note = "" if skilled else f"Kisi technician ki skill mein {label} nahi likha: sab dikhaye."
    return {"unit_id": u.id, "customer": cname, "label": label, "area": place, "slots": out, "note": note,
            "say": (f"{cname} ({place['area'] or place['pincode'] or 'area nahi likha'}) ke {label} ke liye: "
                    + "; ".join(f"{_say_when(x['start'])} {x['tech']}" for x in out[:4]) + ".") if out else "Agle dino mein koi khaali samay nahi mila."}


def _next_number(st: AsSettings, kind: str) -> str:
    if kind == "visit":
        st.seq_visit += 1
        return f"V-{st.seq_visit:04d}"
    st.seq_claim += 1
    return f"W-{st.seq_claim:04d}"


def book(tenant: str, unit: str, start: str = "", tech: str = "", kind: str = "service", problem: str = "", minutes=None,
         force: bool = False, conv: str = "", by: str = "owner") -> dict:
    kind = kind if kind in R.KINDS else "service"
    sug = None
    if start and _when(tenant, start) is None:
        raise AsError("Samay aise likhiye: 2026-10-25 11:00 (ya 'kal 11 baje').")
    if not start:
        sl = slots(tenant, unit, days=14, tech=tech, minutes=minutes)
        if not sl["slots"]:
            raise AsError("Koi khaali samay nahi mila; din / technician badal kar dekhiye.")
        sug = sl["slots"][0]
        start, tech = sug["start"], sug["tech_id"]
    elif not tech:
        t0 = _fmt(_when(tenant, start))
        with session() as s_:
            uid = _unit(s_, tenant, unit).id
        free = _free_at(tenant, uid, t0, minutes)
        if not free:
            sl = slots(tenant, uid, days=7, minutes=minutes, day=t0[:10])
            raise AsError(f"{_say_when(t0)} par koi technician khaali nahi. Khaali samay: "
                          + ("; ".join(f"{_say_when(x['start'])} {x['tech']}" for x in sl["slots"][:4]) or "is hafte nahi"))
        sug = free[0]
        start, tech = sug["start"], sug["tech_id"]
    t = _when(tenant, start)
    if t is None:
        raise AsError("Samay aise likhiye: 2026-10-25 11:00 (ya 'kal 11 baje').")
    warns = []
    with _LOCK, session() as s:
        st = _st(s, tenant)
        u = _unit(s, tenant, unit)
        c = s.get(AsCustomer, u.customer_id)
        tk = _tech(s, tenant, tech)
        mins = int(_num(minutes) or R.PRODUCTS[u.ptype]["minutes"])
        if t < now_local(tenant):
            raise AsError("Yeh samay nikal chuka hai.")
        if t > now_local(tenant) + timedelta(days=90):
            raise AsError("90 din ke andar ka samay chuniye.")
        if not tk.active:
            raise AsError(f"{tk.name} abhi kaam par nahi (inactive).")
        visits = _day_visits(s, tenant, t.date())
        mine = [v for v in visits if v.tech_id == tk.id]
        others = [(*_span(v), _place(s.get(AsCustomer, v.customer_id))) for v in mine]
        ok, why = _fits(t, mins, _place(c), others, st.travel_minutes)
        if not ok and why == "clash":
            raise AsError(f"{tk.name} us samay doosre visit par hain: ek technician ke do visit ek saath nahi.")
        sh, sm = _hm(st.day_start, "09:30")
        eh, em = _hm(st.day_end, "18:30")
        rule = []
        if not ok:
            rule.append(f"Pichhle / agle visit se area alag hai: {st.travel_minutes} min aane-jaane ka samay nahi bachta.")
        if t.weekday() not in _j(st.work_days, []) or not (t.hour * 60 + t.minute >= sh * 60 + sm and (t + timedelta(minutes=mins)).hour * 60
                                                            + (t + timedelta(minutes=mins)).minute <= eh * 60 + em):
            rule.append(f"Kaam ke samay ({st.day_start}-{st.day_end}) / din ke bahar.")
        if t.weekday() in _j(tk.off_days, []):
            rule.append(f"{tk.name} ki chhutti ka din.")
        if len(mine) >= tk.per_day:
            rule.append(f"{tk.name} ke aaj {len(mine)} visit pehle se (had {tk.per_day}).")
        if rule and not force:
            raise AsError(" ".join(rule) + " Phir bhi rakhna ho to force=true.")
        warns += rule
        if _j(tk.skills, []) and u.ptype not in _j(tk.skills, []):
            warns.append(f"{tk.name} ki skill list mein {R.PRODUCTS[u.ptype]['label']} nahi.")
        if not R.covers_area(_j(tk.areas, []), _place(c)):
            warns.append(f"{c.area or c.pincode or 'Yeh area'} {tk.name} ke area mein nahi.")
        dup = s.scalars(select(AsVisit).where(AsVisit.unit_id == u.id, AsVisit.status.in_(OPEN))).first()
        if dup:
            warns.append(f"Is machine ka visit {dup.number} ({_say_when(dup.start)}) pehle se khula hai.")
        last = s.scalars(select(AsVisit).where(AsVisit.unit_id == u.id, AsVisit.status == "done").order_by(AsVisit.done_on.desc())).first()
        comeback = ""
        if last and last.done_on and (t.date() - _date(last.done_on[:10])).days <= 30 and kind in ("repair", "service", "warranty"):
            comeback = last.id
            warns.append(f"30 din ke andar dobara ({last.number}): comeback - pichhla kaam dekhiye, charge soch-samajh kar.")
        number = _next_number(st, "visit")
        v = AsVisit(tenant_id=tenant, number=number, unit_id=u.id, customer_id=c.id, tech_id=tk.id, kind=kind, start=_fmt(t), minutes=mins,
                    problem=_scrub(problem)[:1000], comeback_of=comeback)
        _log(v, f"Book: {_say_when(v.start)}, {tk.name}", by)
        s.add(v)
        s.flush()
        vid = v.id
        out = _visit_view(s, v)
    msg = _draft_visit_confirm(tenant, vid)
    card = {"visit_id": vid, "number": out["number"], "start": out["start"], "when": _say_when(out["start"]), "tech": out["tech"]["name"],
            "customer": out["customer"]["name"], "area": out["customer"]["area"], "label": out["unit"]["label"], "status": "booked",
            "message": msg, "warnings": warns}
    _publish(tenant, "aftersales_visit", card, conv)
    return {"visit": out, "message": msg, "warnings": warns, "suggested": sug,
            "say": f"{out['number']}: {out['customer']['name']} ka {out['unit']['label']}, {_say_when(out['start'])}, {out['tech']['name']}."
                   + (" Dhyaan: " + " ".join(warns) if warns else "") + " Graahak ko pakka karne ka message draft taiyaar (aap bhejiye)."}


def _free_at(tenant: str, unit_id: str, start: str, minutes=None) -> list[dict]:
    t = datetime.strptime(start, "%Y-%m-%d %H:%M")
    out = []
    with session() as s:
        st = _st(s, tenant)
        u = s.get(AsUnit, unit_id)
        c = s.get(AsCustomer, u.customer_id)
        mins = int(_num(minutes) or R.PRODUCTS[u.ptype]["minutes"])
        visits = _day_visits(s, tenant, t.date())
        for tk in s.scalars(select(AsTech).where(AsTech.tenant_id == tenant, AsTech.active.is_(True))).all():
            if t.weekday() in _j(tk.off_days, []):
                continue
            mine = [v for v in visits if v.tech_id == tk.id]
            if len(mine) >= tk.per_day:
                continue
            ok, _ = _fits(t, mins, _place(c), [(*_span(v), _place(s.get(AsCustomer, v.customer_id))) for v in mine], st.travel_minutes)
            if ok:
                skill = not _j(tk.skills, []) or u.ptype in _j(tk.skills, [])
                area = R.covers_area(_j(tk.areas, []), _place(c))
                out.append({"tech_id": tk.id, "tech": tk.name, "start": start, "minutes": mins, "score": skill * 3 + area * 2, "why": ""})
    return sorted(out, key=lambda x: -x["score"])


def _scrub(text: str) -> str:
    """Never keep a PIN / OTP / password a customer said about their device or account."""
    return re.sub(r"(?i)\b(pin|otp|password|passcode|pattern|lock code)\b\s*[:=-]?\s*\S+", r"\1 [hataya]", str(text or ""))


def _get_visit(s, tenant: str, ref: str) -> AsVisit:
    v = s.get(AsVisit, ref) if ref else None
    if v is None and ref:
        v = s.scalars(select(AsVisit).where(AsVisit.tenant_id == tenant, AsVisit.number == str(ref).strip().upper())).first()
    if v is None or v.tenant_id != tenant:
        raise AsError("Visit nahi mila.")
    return v


def _visit_brief(s, v: AsVisit) -> dict:
    t = s.get(AsTech, v.tech_id) if v.tech_id else None
    ch = _j(v.charge, {})
    return {"id": v.id, "number": v.number, "kind": v.kind, "start": v.start, "status": v.status, "tech": t.name if t else "",
            "done_on": v.done_on, "charge_status": ch.get("status", ""), "total": ch.get("total", 0)}


def _visit_view(s, v: AsVisit) -> dict:
    u = s.get(AsUnit, v.unit_id)
    c = s.get(AsCustomer, v.customer_id)
    t = s.get(AsTech, v.tech_id) if v.tech_id else None
    photos = _j(v.photos, [])
    return {"id": v.id, "number": v.number, "kind": v.kind, "start": v.start, "when": _say_when(v.start), "minutes": v.minutes,
            "status": v.status, "problem": v.problem, "checklist": _j(v.checklist, {}), "readings": _j(v.readings, {}),
            "parts": _j(v.parts, []), "labour": v.labour, "notes": v.notes, "photos": [{"id": p["id"], "kind": p["kind"]} for p in photos],
            "signed": bool(v.signature), "signed_by": v.signed_by, "done_on": v.done_on, "cover": _j(v.cover, {}), "charge": _j(v.charge, {}),
            "report_file": v.report_file, "comeback_of": v.comeback_of, "log": _j(v.log, []),
            "unit": _unit_view(s, u) if u else {}, "customer": _cust_view(c) if c else {}, "tech": _tech_view(t) if t else {"name": ""}}


def get_visit(tenant: str, visit: str) -> dict:
    with session() as s:
        return _visit_view(s, _get_visit(s, tenant, visit))


def visits(tenant: str, day: str = "", status: str = "", tech: str = "", limit: int = 200) -> list[dict]:
    with session() as s:
        q = select(AsVisit).where(AsVisit.tenant_id == tenant)
        if day:
            d = _date(day) or (today(tenant) + timedelta(days=1) if day in ("kal", "tomorrow") else today(tenant))
            q = q.where(AsVisit.start >= d.isoformat(), AsVisit.start < (d + timedelta(days=1)).isoformat())
        if status:
            q = q.where(AsVisit.status.in_(OPEN) if status == "open" else AsVisit.status == status)
        if tech:
            q = q.where(AsVisit.tech_id == _tech(s, tenant, tech).id)
        rows = s.scalars(q.order_by(AsVisit.start).limit(limit)).all()
        return [_visit_view(s, v) for v in rows]


def reschedule(tenant: str, visit: str, start: str, tech: str = "", force: bool = False, conv: str = "") -> dict:
    with session() as s:
        v = _get_visit(s, tenant, visit)
        if v.status not in OPEN:
            raise AsError(f"Visit {v.number} {v.status} hai.")
        vid, tid, mins = v.id, v.tech_id, v.minutes
    t = _when(tenant, start)
    if t is None:
        raise AsError("Naya samay samajh nahi aaya.")
    tech_id = tid
    if tech:
        with session() as s:
            tech_id = _tech(s, tenant, tech).id
    # check the new time against everybody else (this visit excluded)
    with _LOCK, session() as s:
        st = _st(s, tenant)
        v = s.get(AsVisit, vid)
        tk = s.get(AsTech, tech_id)
        c = s.get(AsCustomer, v.customer_id)
        if t < now_local(tenant):
            raise AsError("Yeh samay nikal chuka hai.")
        mine = [x for x in _day_visits(s, tenant, t.date()) if x.tech_id == tk.id and x.id != vid]
        ok, why = _fits(t, mins, _place(c), [(*_span(x), _place(s.get(AsCustomer, x.customer_id))) for x in mine], st.travel_minutes)
        if not ok and why == "clash":
            raise AsError(f"{tk.name} us samay doosre visit par hain.")
        if not ok and not force:
            raise AsError(f"Aane-jaane ka {st.travel_minutes} min nahi bachta; phir bhi ho to force=true.")
        if len(mine) >= tk.per_day and not force:
            raise AsError(f"{tk.name} ke us din {len(mine)} visit pehle se.")
        old = v.start
        v.start, v.tech_id = _fmt(t), tk.id
        _log(v, f"Samay badla: {_say_when(old)} -> {_say_when(v.start)} ({tk.name})")
        out = _visit_view(s, v)
    msg = _draft_visit_confirm(tenant, vid)
    _publish(tenant, "aftersales_visit", {"visit_id": vid, "number": out["number"], "start": out["start"], "when": out["when"], "tech": out["tech"]["name"],
                                          "customer": out["customer"]["name"], "label": out["unit"]["label"], "status": "booked", "message": msg}, conv)
    return {"visit": out, "message": msg, "say": f"{out['number']} ab {out['when']}, {out['tech']['name']}. Graahak ko naya samay batane ka draft taiyaar."}


def set_status(tenant: str, visit: str, status: str, note: str = "", by: str = "owner") -> dict:
    if status not in ("on_way", "cancelled", "no_show", "booked"):
        raise AsError("status: on_way | cancelled | no_show | booked (kaam poora = done action)")
    with session() as s:
        v = _get_visit(s, tenant, visit)
        if v.status == "done":
            raise AsError("Yeh visit poora ho chuka.")
        v.status = status
        _log(v, f"{status}" + (f": {note}" if note else ""), by)
        out = _visit_view(s, v)
    words = {"on_way": "raste mein", "cancelled": "radd", "no_show": "graahak nahi mile", "booked": "phir se book"}
    return {"visit": out, "say": f"{out['number']} {words[status]}."}


def job_card(tenant: str, visit: str) -> dict:
    """What the technician needs: address, product, cover (who pays), checklist, readings, last visits, problems before."""
    with session() as s:
        v = _get_visit(s, tenant, visit)
        x = _visit_view(s, v)
        past = s.scalars(select(AsVisit).where(AsVisit.unit_id == v.unit_id, AsVisit.status == "done").order_by(AsVisit.done_on.desc()).limit(3)).all()
        past_lines = [f"{p.done_on[:10]} {p.number}: " + ", ".join(f"{pp.get('name')}" for pp in _j(p.parts, [])) + (f" {p.notes[:60]}" if p.notes else "")
                      for p in past]
    u = x["unit"]
    on = _date(x["start"][:10]) or today(tenant)
    cov = R.coverage(on, _date(u.get("warranty_until")), _date((u.get("amc") or {}).get("until")), (u.get("amc") or {}).get("plan", ""))
    p = R.PRODUCTS.get(u.get("ptype", "other"), R.PRODUCTS["other"])
    c = x["customer"]
    lines = [f"Job card {x['number']} ({x['kind']}) - {x['when']}",
             f"Graahak: {c.get('name', '')} {c.get('phone', '')}", f"Pata: {c.get('address') or c.get('area', '')} {c.get('pincode', '')}".strip(),
             f"Machine: {u.get('label')} {u.get('brand', '')} {u.get('model', '')} Sr {u.get('serial') or '-'}",
             f"Kharcha kiska: {cov['say']}"]
    if x["problem"]:
        lines.append(f"Shikayat: {x['problem']}")
    if x["comeback_of"]:
        lines.append("Dhyaan: 30 din mein dobara aaya (comeback).")
    if u.get("reading") is not None:
        lines.append(f"Pichhli reading: {u['reading']:g} ({u.get('reading_on')})")
    lines.append("Checklist: " + "; ".join(p["checklist"]))
    if p["readings"]:
        lines.append("Readings likhein: " + ", ".join(p["readings"]))
    if past_lines:
        lines.append("Pichhle visit: " + " | ".join(past_lines))
    lines.append("Graahak ka sign (photo) lein. Graahak se PIN / OTP / password kabhi na maangein.")
    text = "\n".join(lines)
    tp = x["tech"].get("phone", "")
    return {"visit_id": x["id"], "number": x["number"], "text": text, "checklist": p["checklist"], "readings": p["readings"], "cover": cov,
            "tech": x["tech"].get("name", ""), "wa_link": _wa(tp, text), "say": f"{x['number']} ka job card {x['tech'].get('name', '')} ke liye taiyaar (WhatsApp draft)."}


# ---------------------------------------------------------------- visit done, photos, charge (her tap), report
def _store_dir(tenant: str, visit_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", tenant)[:64]
    p = Path("data") / "aftersales" / safe / visit_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def add_photo(tenant: str, visit: str, data: bytes, kind: str = "work") -> dict:
    """A work / before / after photo or the customer's signature picture. Re-encoded (EXIF / GPS dropped)."""
    from PIL import Image, ImageOps
    if not data or len(data) > 15 * 1024 * 1024:
        raise AsError("Photo khaali hai ya 15 MB se badi.")
    kind = kind if kind in ("before", "after", "work", "part", "signature") else "work"
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        raise AsError("Yeh photo nahi khuli (JPG / PNG / WEBP).")
    with _LOCK, session() as s:
        v = _get_visit(s, tenant, visit)
        photos = _j(v.photos, [])
        if kind != "signature" and len(photos) >= MAX_PHOTOS:
            raise AsError(f"Ek visit mein {MAX_PHOTOS} photo tak.")
        im = ImageOps.exif_transpose(im)
        im.thumbnail((1600, 1600))
        pid = new_id("asp")
        d = _store_dir(tenant, v.id)
        if kind == "signature":
            path = d / "signature.png"
            bg = Image.new("RGB", im.size, "white")
            if im.mode in ("RGBA", "LA"):
                bg.paste(im, mask=im.split()[-1])
            else:
                bg.paste(im.convert("RGB"))
            bg.save(path, "PNG", optimize=True)
            v.signature = str(path)
            _log(v, "Graahak ka sign liya")
        else:
            path = d / f"{pid}.jpg"
            im.convert("RGB").save(path, "JPEG", quality=82, optimize=True)
            photos.append({"id": pid, "kind": kind, "path": str(path)})
            v.photos = _dump(photos)
            _log(v, f"Photo ({kind})")
        return {"id": pid if kind != "signature" else "signature", "kind": kind, "photos": len(photos), "signed": bool(v.signature)}


def attach_file(tenant: str, visit: str, file_id: str, kind: str = "work") -> dict:
    from ..analyst.service import _load_file
    try:
        _name, data = _load_file(tenant, file_id)
    except Exception as e:
        raise AsError(f"File {file_id} nahi mili: {e}")
    return add_photo(tenant, visit, data, kind)


def photo_file(tenant: str, visit: str, pid: str) -> tuple[Path, str]:
    with session() as s:
        v = _get_visit(s, tenant, visit)
        if pid == "signature" and v.signature and Path(v.signature).exists():
            return Path(v.signature), "image/png"
        for p in _j(v.photos, []):
            if p["id"] == pid and Path(p["path"]).exists():
                return Path(p["path"]), "image/jpeg"
    raise AsError("Photo nahi mili.")


def _price_of(prices: dict, part: str) -> float | None:
    pl = prices.get("parts") or {}
    key = str(part).strip().lower()
    if key in pl:
        return float(pl[key])
    hits = [v for k, v in pl.items() if k in key or key in k]
    return float(hits[0]) if len(hits) == 1 else None


def _build_charge(st: AsSettings, u: AsUnit, parts: list[dict], labour: float | None, cov: dict, kind: str) -> dict:
    prices = _j(st.prices, {})
    lines, needs = [], False
    visit_fee = prices.get(u.ptype, prices.get("visit"))
    if cov["labour"]:
        lines.append({"what": "Visit / labour", "amount": 0.0, "note": cov["by"]})
    elif labour is not None:
        lines.append({"what": "Labour", "amount": round(labour, 2), "note": ""})
    elif visit_fee is not None:
        lines.append({"what": "Visit charge", "amount": round(float(visit_fee), 2), "note": "aapki list se"})
    elif kind != "install":
        lines.append({"what": "Visit charge", "amount": None, "note": "daam aapki list mein nahi"})
        needs = True
    for p in parts:
        qty = max(1.0, float(_num(p.get("qty")) or 1))
        if cov["parts"]:
            lines.append({"what": f"{p['name']} x{qty:g}", "amount": 0.0, "note": cov["by"]})
            continue
        price = _num(p.get("price"))
        if price is None:
            price = _price_of(prices, p["name"])
        if price is None:
            needs = True
            lines.append({"what": f"{p['name']} x{qty:g}", "amount": None, "note": "daam nahi pata"})
        else:
            lines.append({"what": f"{p['name']} x{qty:g}", "amount": round(price * qty, 2), "note": ""})
    sub = round(sum(x["amount"] or 0 for x in lines), 2)
    gst = round(sub * st.gst_pct / 100, 2) if st.gst_on and sub > 0 else 0.0
    total = round(sub + gst, 2)
    status = "needs_price" if needs else ("pending" if total > 0 else "none")
    return {"lines": lines, "subtotal": sub, "gst": gst, "gst_pct": st.gst_pct if st.gst_on else 0, "sac": st.sac if st.gst_on else "",
            "total": total, "status": status, "paid": 0.0}


def complete(tenant: str, visit: str, checklist: dict | list | None = None, readings: dict | None = None, parts: list | None = None,
             labour=None, notes: str = "", signed_by: str = "", done_at: str = "", conv: str = "", by: str = "owner") -> dict:
    """The technician's 'kaam poora': what was done, readings, parts. Next due moves from the REAL visit date; any charge to the
    customer becomes a card for HER tap."""
    with _LOCK, session() as s:
        st = _st(s, tenant)
        v = _get_visit(s, tenant, visit)
        if v.status == "done":
            raise AsError(f"{v.number} pehle hi poora ho chuka.")
        if v.status in ("cancelled", "no_show"):
            raise AsError(f"{v.number} {v.status} hai.")
        u = s.get(AsUnit, v.unit_id)
        p = R.PRODUCTS.get(u.ptype, R.PRODUCTS["other"])
        cl = {}
        if isinstance(checklist, list):
            for item in checklist:
                for k in p["checklist"]:
                    if str(item).lower() in k.lower() or k.lower() in str(item).lower():
                        cl[k] = "ok"
        elif isinstance(checklist, dict):
            for k, val in checklist.items():
                val = str(val).lower()
                cl[str(k)[:80]] = "ok" if val in ("ok", "true", "haan", "yes", "1", "done") else ("na" if val in ("na", "n/a") else "not_ok")
        missing = [k for k in p["checklist"] if k not in cl]
        rd = {str(k)[:30]: (_num(val) if _num(val) is not None else str(val)[:40]) for k, val in (readings or {}).items()}
        pts = []
        for x in parts or []:
            if isinstance(x, str):
                x = {"name": x}
            if not str(x.get("name") or "").strip():
                continue
            pts.append({"name": str(x["name"]).strip()[:80], "qty": _num(x.get("qty")) or 1, "price": _num(x.get("price")),
                        "warranty_days": int(_num(x.get("warranty_days")) or 0)})
        when = _when(tenant, done_at) if done_at else now_local(tenant)
        if when is None:
            raise AsError("Kaam ki tareekh samajh nahi aayi.")
        d = when.date()
        cov = R.coverage(d, _date(u.warranty_until), _date(u.amc_until), u.amc_plan)
        flags = []
        usage_key = next((k for k in p["readings"] if k in ("odometer_km", "run_hours")), "")
        if usage_key and isinstance(rd.get(usage_key), float):
            if u.reading is not None and rd[usage_key] < u.reading:
                flags.append(f"{usage_key} {rd[usage_key]:g} pichhli reading {u.reading:g} se kam: dobara dekhiye.")
            else:
                _set_reading(u, rd[usage_key], d)
        if u.ptype == "ro" and isinstance(rd.get("tds_out"), float) and rd["tds_out"] > 150:
            flags.append(f"Output TDS {rd['tds_out']:g}: membrane / filter dekhiye.")
        if u.ptype == "inverter" and isinstance(rd.get("backup_minutes"), float) and rd["backup_minutes"] < 30:
            flags.append("Backup 30 min se kam: battery badalne ki baat graahak se (daam aapki haan se).")
        v.checklist, v.readings, v.parts = _dump(cl), _dump(rd), _dump(pts)
        v.labour = _num(labour)
        v.notes = _scrub(notes)[:1500]
        if signed_by:
            v.signed_by = str(signed_by)[:80]
        v.status, v.done_on = "done", _fmt(when)
        v.cover = _dump(cov)
        charge = _build_charge(st, u, pts, v.labour, cov, v.kind)
        v.charge = _dump(charge)
        _log(v, "Kaam poora" + (f", {len(pts)} part" if pts else ""), by)
        if v.kind in ("service", "amc", "inspection", "install", "repair", "warranty"):
            u.last_service = d.isoformat()
            u.reminded_for = ""
        _recompute(u, _j(st.schedule, {}))
        claim_hint = [x["name"] for x in pts] if cov["by"] == "warranty" and pts else []
        out = _visit_view(s, v)
        vid, number = v.id, v.number
    say = f"{number} poora. Agli service {out['unit']['next_due']} ({out['unit']['due_why']})."
    if missing:
        say += f" Checklist mein baaki: {', '.join(missing[:4])}."
    if flags:
        say += " Dhyaan: " + " ".join(flags)
    if claim_hint:
        say += f" Warranty mein part badla ({', '.join(claim_hint[:3])}): brand se claim daaliye (action=claim)."
    if charge["status"] in ("pending", "needs_price"):
        _charge_card(tenant, vid, conv)
        say += (f" Graahak se {_rs(charge['total'])} lena hai: card par aapki haan ke baad hi report mein jaayega." if charge["status"] == "pending"
                else " Kuch daam aapki list mein nahi: card par total likh kar haan kijiye.")
    else:
        say += f" Charge nahi ({cov['say']})."
    return {"visit": out, "missing": missing, "flags": flags, "claim_parts": claim_hint, "charge": charge, "say": say}


def _charge_card(tenant: str, visit_id: str, conv: str = "") -> dict:
    with session() as s:
        v = s.get(AsVisit, visit_id)
        x = _visit_view(s, v)
    ch = x["charge"]
    card = {"visit_id": x["id"], "number": x["number"], "customer": x["customer"].get("name", ""), "label": x["unit"].get("label", ""),
            "lines": ch.get("lines", []), "gst": ch.get("gst", 0), "total": ch.get("total", 0), "status": ch.get("status"),
            "cover": x["cover"].get("say", ""), "hash": _charge_hash(ch)}
    _publish(tenant, "aftersales_charge", card, conv)
    return card


def _charge_hash(ch: dict) -> str:
    return hashlib.sha256(_dump({"l": ch.get("lines"), "t": ch.get("total")}).encode()).hexdigest()[:16]


def decide_charge(tenant: str, visit: str, yes: bool, total=None, by_tap: bool = False, hash_: str = "", conv: str = "") -> dict:
    """ONLY her tap in the app (API). Haan = this amount may be asked from the customer; a changed total replaces the lines'
    sum; Mana = no charge (free / goodwill)."""
    if not by_tap:
        raise AsError("Graahak se paisa maangne ki haan sirf aapke tap se (app mein card).")
    with session() as s:
        v = _get_visit(s, tenant, visit)
        ch = _j(v.charge, {})
        if ch.get("status") not in ("pending", "needs_price"):
            raise AsError("Is visit par haan ka koi charge baaki nahi.")
        if hash_ and hash_ != _charge_hash(ch):
            raise AsError("Card ke baad charge badal gaya: naya card dekhiye.")
        if not yes:
            ch["status"] = "rejected"
            ch["total"] = 0.0
            _log(v, "Charge: mana (free)")
        else:
            t = _num(total)
            if ch["status"] == "needs_price" and t is None:
                raise AsError("Kuch daam pata nahi: total likh kar haan kijiye.")
            if t is not None:
                if t < 0 or t > 500000:
                    raise AsError("Total sahi nahi lagta.")
                ch["total_changed_from"] = ch.get("total")
                ch["total"] = round(t, 2)
            ch["status"] = "approved"
            ch["approved_at"] = now().isoformat(timespec="seconds")
            _log(v, f"Charge haan: {_rs(ch['total'])}")
        v.charge = _dump(ch)
        number = v.number
    return {"charge": ch, "say": f"{number}: " + (f"{_rs(ch['total'])} graahak se lena tay (aapki haan). Report mein UPI link ke saath jaayega."
                                                 if yes else "Is visit ka charge nahi liya jaayega.")}


def mark_paid(tenant: str, visit: str, amount=None, how: str = "") -> dict:
    """She says the customer paid (cash / UPI in her own app). Hoola never collects."""
    with session() as s:
        v = _get_visit(s, tenant, visit)
        ch = _j(v.charge, {})
        if ch.get("status") != "approved":
            raise AsError("Pehle charge par aapki haan chahiye.")
        a = _num(amount)
        a = ch["total"] - ch.get("paid", 0) if a is None else a
        if a <= 0:
            raise AsError("Raqam sahi nahi.")
        ch["paid"] = round(ch.get("paid", 0) + a, 2)
        v.charge = _dump(ch)
        _log(v, f"Paisa mila {_rs(a)} {how}".strip())
        left = round(ch["total"] - ch["paid"], 2)
        return {"charge": ch, "say": f"{v.number}: {_rs(a)} mila" + (f", baaki {_rs(left)}." if left > 0 else ", poora mil gaya.")}


def _upi(tenant: str, amount: float, note: str) -> str:
    try:
        from ..employee import service as emp
        p = emp.profile(tenant) or {}
        upi, nm = p.get("upi_id") or "", p.get("upi_name") or p.get("business_name") or ""
    except Exception:
        upi, nm = "", ""
    if not upi or amount <= 0:
        return ""
    return f"upi://pay?pa={quote(upi)}&pn={quote(nm)}&am={amount:.2f}&cu=INR&tn={quote(note[:40])}"


def _latin(t) -> str:
    return str(t).replace("₹", "Rs ").encode("latin-1", "replace").decode("latin-1")


def report_pdf(tenant: str, visit: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    st = settings(tenant)
    x = get_visit(tenant, visit)
    if x["status"] != "done":
        raise AsError("Report kaam poora hone ke baad.")
    with session() as s:
        v = s.get(AsVisit, x["id"])
        photos = [p for p in _j(v.photos, []) if Path(p["path"]).exists()][:4]
        sig = v.signature if v.signature and Path(v.signature).exists() else ""
    u, c, ch = x["unit"], x["customer"], x["charge"]
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 40

    def t(xx, text, size=9.0, bold=False, right=False):
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        (pdf.drawRightString if right else pdf.drawString)(xx, y, _latin(text)[:110])

    def nl(k=13):
        nonlocal y
        y -= k
        if y < 70:
            pdf.showPage()
            y = h - 40

    t(30, st["business"] or _business(tenant) or "Service report", 13, True)
    t(w - 30, f"Visit {x['number']}", 11, True, True)
    nl(15)
    if st["address"] or st["phone"]:
        t(30, f"{st['address'][:80]} {('Ph ' + st['phone']) if st['phone'] else ''}".strip(), 8)
        nl(12)
    if st["gstin"]:
        t(30, f"GSTIN {st['gstin']}", 8)
        nl(12)
    t(30, "SERVICE VISIT REPORT", 11, True)
    nl(16)
    for k, val in (("Customer", f"{c.get('name', '')}  {c.get('phone', '')}"), ("Address", f"{c.get('address') or c.get('area', '')} {c.get('pincode', '')}"),
                   ("Product", f"{u.get('label')} {u.get('brand', '')} {u.get('model', '')}"), ("Serial no.", u.get("serial") or "-"),
                   ("Installed", u.get("installed_on") or "-"), ("Warranty till", u.get("warranty_until") or "-"),
                   ("AMC", f"{(u.get('amc') or {}).get('plan', '')} till {(u.get('amc') or {}).get('until', '')}" if u.get("amc") else "-"),
                   ("Visit", f"{x['kind']} - {x['done_on']} by {x['tech'].get('name', '')}"), ("Covered by", x["cover"].get("say", ""))):
        t(30, k, 9, True)
        t(120, val)
        nl()
    if x["problem"]:
        nl(4)
        t(30, "Complaint", 9, True)
        t(120, x["problem"][:95])
        nl()
    nl(6)
    t(30, "Checklist", 10, True)
    nl()
    p = R.PRODUCTS.get(u.get("ptype", "other"), R.PRODUCTS["other"])
    for k in list(dict.fromkeys(p["checklist"] + list(x["checklist"].keys()))):
        mark = {"ok": "OK", "not_ok": "NOT OK", "na": "N/A"}.get(x["checklist"].get(k), "-")
        t(40, k)
        t(330, mark, 9, mark == "NOT OK")
        nl(12)
    if x["readings"]:
        nl(4)
        t(30, "Readings", 10, True)
        nl()
        for k, val in x["readings"].items():
            t(40, k.replace("_", " "))
            t(330, f"{val:g}" if isinstance(val, float) else str(val))
            nl(12)
    if x["parts"]:
        nl(4)
        t(30, "Parts used", 10, True)
        nl()
        for pp in x["parts"]:
            t(40, f"{pp['name']} x{pp['qty']:g}" + (f"  (part warranty {pp['warranty_days']} days)" if pp.get("warranty_days") else ""))
            nl(12)
    nl(6)
    t(30, "Charges", 10, True)
    nl()
    if ch.get("status") == "approved":
        for ln in ch.get("lines", []):
            t(40, ln["what"] + (f" ({ln['note']})" if ln.get("note") and ln["note"] in ("warranty", "amc") else ""))
            t(w - 30, f"{(ln['amount'] or 0):,.2f}", 9, False, True)
            nl(12)
        if ch.get("gst"):
            t(40, f"GST @ {ch['gst_pct']:g}% (SAC {ch.get('sac', '')})")
            t(w - 30, f"{ch['gst']:,.2f}", 9, False, True)
            nl(12)
        if ch.get("total_changed_from") is not None:
            t(40, "Amount as agreed")
            nl(12)
        t(40, "TOTAL", 10, True)
        t(w - 30, f"Rs {ch['total']:,.2f}", 10, True, True)
        nl(12)
        if ch.get("paid"):
            t(40, f"Received Rs {ch['paid']:,.2f}")
            nl(12)
    elif ch.get("status") in ("none", "rejected"):
        t(40, f"No charge ({x['cover'].get('by', '')})" if ch.get("status") == "none" else "No charge")
        nl(12)
    else:
        t(40, "Charges to be confirmed by the business.")
        nl(12)
    nl(4)
    t(30, "Next service due", 10, True)
    t(150, f"{u.get('next_due') or '-'}  ({u.get('due_why', '')})")
    nl()
    if x["notes"]:
        t(30, "Technician notes", 9, True)
        nl(12)
        for i in range(0, min(len(x["notes"]), 400), 100):
            t(40, x["notes"][i:i + 100], 8.5)
            nl(11)
    if photos:
        nl(8)
        if y < 200:
            pdf.showPage()
            y = h - 40
        t(30, "Photos", 10, True)
        nl(8)
        xx = 30
        for ph in photos:
            try:
                img = ImageReader(ph["path"])
                iw, ih = img.getSize()
                sc = min(120 / iw, 120 / ih)
                pdf.drawImage(img, xx, y - ih * sc, iw * sc, ih * sc)
                pdf.setFont("Helvetica", 7)
                pdf.drawString(xx, y - ih * sc - 9, ph["kind"])
                xx += 132
            except Exception:
                continue
        y -= 145
    nl(10)
    if y < 140:
        pdf.showPage()
        y = h - 40
    if sig:
        try:
            img = ImageReader(sig)
            iw, ih = img.getSize()
            sc = min(160 / iw, 60 / ih)
            pdf.drawImage(img, 30, y - ih * sc, iw * sc, ih * sc)
            y -= ih * sc + 12
        except Exception:
            pass
    t(30, f"Customer: {x['signed_by'] or c.get('name', '')}" + ("" if sig else " (signature not taken)"), 8.5)
    t(w - 30, f"Technician: {x['tech'].get('name', '')}", 8.5, False, True)
    nl(16)
    if st["terms"]:
        for i in range(0, min(len(st["terms"]), 600), 110):
            t(30, st["terms"][i:i + 110], 7.5)
            nl(10)
    pdf.showPage()
    pdf.save()
    return buf.getvalue()


def report(tenant: str, visit: str, conv: str = "") -> dict:
    """Visit report PDF (her file, shareable) + the customer message as a DRAFT she sends (or a utility template on her tap)."""
    from .. import chatfiles
    x = get_visit(tenant, visit)
    data = report_pdf(tenant, x["id"])
    f = chatfiles.store(tenant, f"Service-report-{x['number']}.pdf", data, "application/pdf")
    with session() as s:
        v = s.get(AsVisit, x["id"])
        v.report_file = str(f.get("file_id") or "")[:60]
        _log(v, "Report PDF bana")
    _publish(tenant, "pc_file", {**f, "source": "aftersales", "title": f"Service report {x['number']}"}, conv)
    msg = _draft_report(tenant, x["id"])
    _publish(tenant, "aftersales_report", {"visit_id": x["id"], "number": x["number"], "customer": x["customer"].get("name", ""),
                                           "file": {k: f.get(k) for k in ("file_id", "name", "url")}, "message": msg}, conv)
    ch = x["charge"]
    say = f"{x['number']} ki report PDF taiyaar + graahak ke liye message draft."
    if ch.get("status") in ("pending", "needs_price"):
        say += " Charge par aapki haan abhi baaki: message mein raqam nahi daali."
    return {"file": f, "message": msg, "say": say}


# ---------------------------------------------------------------- messages (drafts; sending only on her tap)
def _msg_view(m: AsMessage) -> dict:
    return {"id": m.id, "kind": m.kind, "customer_id": m.customer_id, "unit_id": m.unit_id, "visit_id": m.visit_id, "phone": m.phone,
            "text": m.text, "category": m.category, "template": m.template, "params": _j(m.params, []), "status": m.status, "via": m.via,
            "wa_link": _wa(m.phone, m.text), "sms_link": _sms(m.phone, m.text), "created": m.created_at.isoformat() if m.created_at else ""}


def _draft(tenant: str, customer_id: str, kind: str, key: str, text: str, template: str, params: list, unit_id: str = "",
           visit_id: str = "") -> dict | None:
    with session() as s:
        c = s.get(AsCustomer, customer_id)
        if c is None:
            return None
        if c.no_messages:
            return {"skipped": True, "reason": f"{c.name} ne message mana kiya hai", "customer": c.name}
        cat = R.TEMPLATES.get(template, {}).get("category") or R.classify(text)
        if R.classify(text) == "MARKETING":
            cat = "MARKETING"
        old = s.scalars(select(AsMessage).where(AsMessage.tenant_id == tenant, AsMessage.key == key)).first() if key else None
        if old is not None:
            if old.status == "draft":
                old.text, old.params, old.category = text, _dump(params), cat
            return _msg_view(old) | {"existing": True}
        m = AsMessage(tenant_id=tenant, customer_id=c.id, unit_id=unit_id, visit_id=visit_id, kind=kind, key=key, phone=c.phone,
                      text=text[:1500], category=cat, template=template, params=_dump([str(p)[:200] for p in params]))
        s.add(m)
        s.flush()
        return _msg_view(m)


def _draft_visit_confirm(tenant: str, visit_id: str) -> dict | None:
    x = get_visit(tenant, visit_id)
    tech, when = x["tech"].get("name", "technician"), _say_when(x["start"])
    first, label = _first(x["customer"].get("name")), x["unit"].get("label", "machine")
    text = (f"Namaste {first} ji, aapke {label} ke liye technician {tech} aayenge, samay: {when}. Visit number {x['number']}. "
            f"Samay badalna ho to reply karein.")
    return _draft(tenant, x["customer"]["id"], "visit", f"visit:{x['id']}:{x['start']}", text, "service_visit_confirmed",
                  [first, label, tech, when, x["number"]], x["unit"].get("id", ""), x["id"])


def _work_line(x: dict) -> str:
    bits = [pp["name"] for pp in x["parts"][:3]]
    done = [k for k, val in x["checklist"].items() if val == "ok"][:2]
    rd = [f"{k.replace('_', ' ')} {val:g}" if isinstance(val, float) else f"{k} {val}" for k, val in list(x["readings"].items())[:2]]
    return ", ".join(bits + done + rd)[:180] or "service poori"


def _draft_report(tenant: str, visit_id: str) -> dict | None:
    x = get_visit(tenant, visit_id)
    first, label = _first(x["customer"].get("name")), x["unit"].get("label", "machine")
    nd = _date(x["unit"].get("next_due"))
    nxt = nd.strftime("%b %Y") if nd else "-"
    work = _work_line(x)
    text = f"Namaste {first} ji, aapke {label} ki service (visit {x['number']}) poori hui. Kaam: {work}. Agli service: {nxt}."
    ch = x["charge"]
    if ch.get("status") == "approved" and ch.get("total", 0) > ch.get("paid", 0):
        due = round(ch["total"] - ch.get("paid", 0), 2)
        upi = _upi(tenant, due, f"{x['number']} service")
        text += f" Charge {_rs(due)}." + (f" UPI: {upi}" if upi else "")
    elif ch.get("status") in ("none",):
        text += f" Is visit ka koi charge nahi ({x['cover'].get('by', '')})."
    text += " Sawaal ho to reply karein."
    return _draft(tenant, x["customer"]["id"], "report", f"report:{x['id']}", text, "service_visit_report",
                  [first, label, x["number"], work, nxt], x["unit"].get("id", ""), x["id"])


def due(tenant: str, within: int = 15) -> dict:
    on = today(tenant)
    lim = on + timedelta(days=max(0, min(int(within), 120)))
    with session() as s:
        rows = s.scalars(select(AsUnit).where(AsUnit.tenant_id == tenant, AsUnit.status == "active")).all()
        open_units = {v.unit_id: v for v in s.scalars(select(AsVisit).where(AsVisit.tenant_id == tenant, AsVisit.status.in_(OPEN))).all()}
        items, amc, warranty = [], [], []
        for u in rows:
            v = _unit_view(s, u)
            nd = _date(u.next_due)
            if nd and nd <= lim:
                bv = open_units.get(u.id)
                items.append(v | {"overdue": nd < on, "booked": {"number": bv.number, "start": bv.start} if bv else None,
                                  "reminded": u.reminded_for == u.next_due})
            au = _date(u.amc_until)
            if au and on <= au <= on + timedelta(days=30):
                amc.append(v)
            wu = _date(u.warranty_until)
            if wu and on <= wu <= on + timedelta(days=30) and not (au and au >= on):
                warranty.append(v)
    items.sort(key=lambda x: (x["next_due"], x["customer"]["area"]))
    over = sum(1 for x in items if x["overdue"])
    by_area: dict[str, int] = {}
    for x in items:
        k = x["customer"]["area"] or x["customer"]["pincode"] or "-"
        by_area[k] = by_area.get(k, 0) + 1
    say = (f"{len(items)} machine ki service {within} din mein due ({over} late)." if items else "Agle din mein koi service due nahi.")
    if amc:
        say += f" {len(amc)} AMC 30 din mein khatam."
    if warranty:
        say += f" {len(warranty)} ki warranty 30 din mein khatam (AMC ki baat aap karein)."
    return {"due": items, "overdue": over, "by_area": by_area, "amc_ending": amc, "warranty_ending": warranty, "say": say}


def remind(tenant: str, within: int | None = None, kind: str = "due", unit: str = "", conv: str = "", publish: bool = True) -> dict:
    """Reminder DRAFTS (service due / AMC ending). She sends them: wa.me from her phone, or a template on her tap."""
    st = settings(tenant)
    biz = st["business"] or _business(tenant) or "[aapki dukaan]"
    within = st["remind_days"] if within is None else within
    made, skipped = [], []
    if kind == "amc":
        d = due(tenant, 30)
        targets = d["amc_ending"]
    else:
        d = due(tenant, within)
        targets = [x for x in d["due"] if not x["booked"]]
    if unit:
        uid = get_unit(tenant, unit)["id"]
        targets = [x for x in targets if x["id"] == uid]
    for x in targets:
        first, label = _first(x["customer"]["name"]), x["label"]
        if kind == "amc":
            until = x["amc"]["until"]
            dd = _date(until)
            nice = f"{dd.day} {dd.strftime('%b')}" if dd else until
            text = f"Namaste {first} ji, {biz} se: aapke {label} ka AMC {nice} ko khatam ho raha hai. Aage jaari rakhna ho to reply karein."
            m = _draft(tenant, x["customer"]["id"], "amc", f"amc:{x['id']}:{until}", text, "amc_expiry_notice", [first, biz, label, nice], x["id"])
        else:
            dd = _date(x["next_due"])
            nice = f"{dd.day} {dd.strftime('%b')}" if dd else x["next_due"]
            prod = label + (f" ({x['model']})" if x["model"] else "")
            text = (f"Namaste {first} ji, {biz} se: aapke {prod} ki service {nice} tak due hai. "
                    f"Technician kab bhejein? Suvidha ka din aur samay reply karein.")
            if x["amc"] and x["amc"]["active"]:
                text += " (Yeh visit aapke AMC mein shaamil hai.)"
            m = _draft(tenant, x["customer"]["id"], "due", f"due:{x['id']}:{x['next_due']}", text, "service_due_reminder",
                       [first, biz, prod, nice], x["id"])
            if m and not m.get("skipped"):
                with session() as s:
                    u = s.get(AsUnit, x["id"])
                    u.reminded_for = u.next_due
        if m is None:
            continue
        if m.get("skipped"):
            skipped.append(m)
        elif not m.get("existing"):
            made.append(m)
    drafts = [m for m in made]
    if publish and drafts:
        _publish(tenant, "aftersales_reminders", {"kind": kind, "count": len(drafts), "messages": drafts[:30],
                                                  "say": f"{len(drafts)} reminder draft ({'AMC' if kind == 'amc' else 'service due'})"}, conv)
    say = f"{len(drafts)} naye reminder draft." if drafts else "Koi naya reminder nahi (pehle se bane / bheje)."
    if skipped:
        say += f" {len(skipped)} graahak ne message mana kiya hai: unhe nahi."
    if kind == "amc" and drafts:
        say += " AMC renewal wala message Meta ke hisaab se 'marketing' hai: template sirf unhe jo offers ke liye haan keh chuke."
    return {"messages": drafts, "skipped": skipped, "say": say}


def messages(tenant: str, status: str = "draft", kind: str = "", limit: int = 200) -> list[dict]:
    with session() as s:
        q = select(AsMessage).where(AsMessage.tenant_id == tenant)
        if status:
            q = q.where(AsMessage.status == status)
        if kind:
            q = q.where(AsMessage.kind == kind)
        out = []
        cust = {c.id: c.name for c in s.scalars(select(AsCustomer).where(AsCustomer.tenant_id == tenant)).all()}
        for m in s.scalars(q.order_by(AsMessage.created_at.desc()).limit(limit)).all():
            out.append(_msg_view(m) | {"customer": cust.get(m.customer_id, "")})
        return out


def message_mark(tenant: str, msg_id: str, status: str) -> dict:
    """She sent it herself from her phone (sent) / doesn't want it (skipped)."""
    if status not in ("sent", "skipped", "draft"):
        raise AsError("status: sent | skipped")
    with session() as s:
        m = s.get(AsMessage, msg_id)
        if m is None or m.tenant_id != tenant:
            raise AsError("Message nahi mila.")
        m.status = status
        if status == "sent":
            m.via, m.sent_at = m.via or "her_phone", now()
        return _msg_view(m)


async def send_message(tenant: str, msg_id: str, via: str = "template", by_tap: bool = False) -> dict:
    """ONLY her tap (API). via=template: her approved Meta template (any time; marketing only to customers who said yes to
    offers). via=business: free text from her business number, only inside 24 h of the customer's last message."""
    from ..whatsapp import WhatsAppError, get_whatsapp
    if not by_tap:
        raise AsError("Graahak ko business WhatsApp sirf aapke tap se jaata hai.")
    with session() as s:
        m = s.get(AsMessage, msg_id)
        if m is None or m.tenant_id != tenant:
            raise AsError("Message nahi mila.")
        if m.status != "draft":
            raise AsError(f"Yeh message {m.status} hai.")
        c = s.get(AsCustomer, m.customer_id)
        if c is None or len(c.phone) != 10:
            raise AsError("Graahak ka 10 ank ka mobile nahi.")
        if c.no_messages:
            raise AsError(f"{c.name} ne message mana kiya hai.")
        from ..employee.models import BizContact
        bc = s.scalars(select(BizContact).where(BizContact.tenant_id == tenant, BizContact.wa_id == "91" + c.phone)).first()
        if bc is not None and bc.opted_out:
            raise AsError(f"{c.name} ne WhatsApp par STOP likha hai.")
        if m.category == "MARKETING" and via == "template" and not c.marketing_ok:
            raise AsError(f"Yeh 'marketing' message hai aur {c.name} ne offers / renewal messages ki haan nahi di. Apne phone se baat kijiye.")
        text, tpl, params, cat, phone = m.text, m.template, _j(m.params, []), m.category, c.phone
        bc_id = bc.id if bc else ""
        if via == "template":
            from ..db import Template
            row = s.scalars(select(Template).where(Template.tenant_id == tenant, Template.name == tpl)).first()
            if row is None or row.status != "APPROVED":
                raise AsError(f"Template '{tpl}' Meta se approved nahi (status: {row.status if row else 'nahi bana'}). "
                              "Pehle 'Templates' mein bhejiye, ya draft apne phone se bhejiye.")
            lang = row.language
    if R.classify(text) == "MARKETING" and cat == "UTILITY":
        raise AsError("Message mein offer / renewal ki baat hai: yeh utility template se nahi jaa sakta.")
    if via == "template":
        try:
            wamid = await get_whatsapp().send_template("91" + phone, tpl, lang, params)
        except WhatsAppError as e:
            raise AsError(f"WhatsApp ne nahi liya: {e}")
    elif via == "business":
        if not bc_id:
            raise AsError("Is graahak ne business number par kabhi message nahi kiya: template ya apna phone.")
        from ..employee import inbox
        try:
            mv = await inbox.send(tenant, bc_id, text, by="owner")
        except inbox.InboxError as e:
            raise AsError(str(e))
        wamid = mv.get("wa_msg_id", "") if isinstance(mv, dict) else ""
    else:
        raise AsError("via: template | business")
    with session() as s:
        m = s.get(AsMessage, msg_id)
        m.status, m.via, m.wa_msg_id, m.sent_at = "sent", via, str(wamid or "")[:80], now()
        return _msg_view(m) | {"say": "Bhej diya (aapke tap se)."}


def templates(tenant: str) -> list[dict]:
    from ..db import Template
    from ..whatsapp.templates import check_template
    with session() as s:
        rows = {t.name: t for t in s.scalars(select(Template).where(Template.tenant_id == tenant)).all()}
    out = []
    for k, t in R.TEMPLATES.items():
        chk = check_template(k, t["language"], t["category"], t["body"], t["example"], t.get("footer"))
        r = rows.get(k)
        out.append({"name": k, "category": t["category"], "language": t["language"], "body": t["body"], "footer": t.get("footer", ""),
                    "example": t["example"], "check": chk, "status": r.status if r else "NOT_SUBMITTED",
                    "reason": r.rejection_reason if r else None})
    return out


async def submit_template(tenant: str, name: str, by_tap: bool = False) -> dict:
    """Send one of the recommended templates to Meta for approval from her WhatsApp Business account (her tap)."""
    from ..db import Template
    from ..whatsapp import WhatsAppError, get_whatsapp
    from ..whatsapp.templates import check_template
    if not by_tap:
        raise AsError("Template Meta ko aapke tap se jaata hai.")
    t = R.TEMPLATES.get(name)
    if not t:
        raise AsError("Yeh template nahi: " + ", ".join(R.TEMPLATES))
    chk = check_template(name, t["language"], t["category"], t["body"], t["example"], t.get("footer"))
    if not chk["ok"]:
        raise AsError("; ".join(chk["errors"]))
    with session() as s:
        r = s.scalars(select(Template).where(Template.tenant_id == tenant, Template.name == name)).first()
        if r is not None and r.status in ("PENDING", "APPROVED"):
            return {"name": name, "status": r.status, "say": f"'{name}' pehle se {r.status}."}
    try:
        res = await get_whatsapp().create_template(name, t["language"], t["category"], t["body"], t["example"], t.get("footer"))
    except WhatsAppError as e:
        raise AsError(f"Meta ne nahi liya: {e}")
    with session() as s:
        r = s.scalars(select(Template).where(Template.tenant_id == tenant, Template.name == name)).first()
        if r is None:
            r = Template(tenant_id=tenant, name=name, language=t["language"], category=t["category"], body=t["body"],
                         footer=t.get("footer"), example_values=list(t["example"]))
            s.add(r)
        r.meta_id, r.status, r.updated_at = res.get("meta_id"), res.get("status", "PENDING"), now()
        st = r.status
    return {"name": name, "status": st, "say": f"'{name}' Meta ko bheja ({st}). Approve hone par graahak ko template se bhej sakti hain."}


# ---------------------------------------------------------------- warranty claims with the brand
def _claim_view(c: AsClaim) -> dict:
    return {"id": c.id, "number": c.number, "unit_id": c.unit_id, "visit_id": c.visit_id, "brand": c.brand, "part": c.part, "fault": c.fault,
            "brand_ref": c.brand_ref, "status": c.status, "raised_on": c.raised_on, "updated_on": c.updated_on, "amount": c.amount,
            "settled": c.settled, "log": _j(c.log, [])}


def claim(tenant: str, unit: str = "", visit: str = "", part: str = "", fault: str = "", brand_ref: str = "", amount=None) -> dict:
    with _LOCK, session() as s:
        st = _st(s, tenant)
        v = _get_visit(s, tenant, visit) if visit else None
        u = s.get(AsUnit, v.unit_id) if v else _unit(s, tenant, unit)
        on = today(tenant)
        wu = _date(u.warranty_until)
        warn = ""
        if not wu or (v and v.done_on and _date(v.done_on[:10]) > wu) or (not v and on > wu):
            warn = f"Warranty {u.warranty_until or 'likhi nahi'}: brand mana kar sakta hai."
        if not part and v:
            part = ", ".join(p["name"] for p in _j(v.parts, []))
        if not str(part).strip():
            raise AsError("Kaunsa part / kya kharab hua?")
        c = AsClaim(tenant_id=tenant, number=_next_number(st, "claim"), unit_id=u.id, visit_id=v.id if v else "", brand=u.brand,
                    part=str(part)[:120], fault=_scrub(fault)[:500], brand_ref=str(brand_ref)[:60], raised_on=on.isoformat(),
                    updated_on=on.isoformat(), amount=float(_num(amount) or 0))
        _log(c, "Claim daala" + (f" (brand no. {brand_ref})" if brand_ref else ""))
        s.add(c)
        s.flush()
        out = _claim_view(c)
        ser, mdl = u.serial, u.model
    sheet = (f"Warranty claim {out['number']}: {out['brand']} {mdl} Sr {ser or '-'}; part: {out['part']}; kharabi: {out['fault'] or '-'}; "
             f"install {get_unit(tenant, out['unit_id'])['installed_on'] or '-'}.")
    return {"claim": out, "text": sheet, "warning": warn,
            "say": f"Claim {out['number']} ({out['brand'] or 'brand'}: {out['part']}) likha." + (f" {warn}" if warn else "")
                   + " Brand ke portal / service centre par aap daaliye; complaint number milte hi bataiye."}


def claim_update(tenant: str, claim_id: str, status: str = "", brand_ref: str = "", settled=None, note: str = "") -> dict:
    with session() as s:
        c = s.get(AsClaim, claim_id) if claim_id else None
        if c is None:
            c = s.scalars(select(AsClaim).where(AsClaim.tenant_id == tenant, AsClaim.number == str(claim_id).upper())).first()
        if c is None or c.tenant_id != tenant:
            raise AsError("Claim nahi mila.")
        if status:
            if status not in CLAIM_STATES:
                raise AsError("status: " + " | ".join(CLAIM_STATES))
            c.status = status
        if brand_ref:
            c.brand_ref = str(brand_ref)[:60]
        if _num(settled) is not None:
            c.settled = _num(settled)
        c.updated_on = today(tenant).isoformat()
        _log(c, f"{status or 'update'}" + (f": {note}" if note else ""))
        days = (today(tenant) - _date(c.raised_on)).days if _date(c.raised_on) else 0
        out = _claim_view(c)
    return {"claim": out, "say": f"Claim {out['number']}: {out['status']}" + (f" ({days} din mein)" if status in ("settled", "rejected", "part_received") else "") + "."}


def claims(tenant: str, status: str = "") -> dict:
    on = today(tenant)
    with session() as s:
        q = select(AsClaim).where(AsClaim.tenant_id == tenant)
        if status:
            q = q.where(AsClaim.status == status)
        rows = [_claim_view(c) for c in s.scalars(q.order_by(AsClaim.raised_on.desc())).all()]
    stuck = [c for c in rows if c["status"] in ("raised", "approved") and _date(c["updated_on"]) and (on - _date(c["updated_on"])).days >= 15]
    brands: dict[str, list] = {}
    for c in rows:
        if c["status"] in ("settled", "part_received", "rejected") and _date(c["raised_on"]) and _date(c["updated_on"]):
            brands.setdefault(c["brand"] or "-", []).append((_date(c["updated_on"]) - _date(c["raised_on"])).days)
    avg = {b: round(sum(x) / len(x)) for b, x in brands.items()}
    return {"claims": rows, "stuck": stuck, "brand_days": avg,
            "say": f"{sum(1 for c in rows if c['status'] in ('raised', 'approved'))} claim khule" + (f", {len(stuck)} 15 din se ruke" if stuck else "") + "."}


# ---------------------------------------------------------------- the day + worker
def day(tenant: str) -> dict:
    on = today(tenant)
    parts = []
    vs = visits(tenant, on.isoformat())
    open_v = [v for v in vs if v["status"] in OPEN]
    if open_v:
        per: dict[str, int] = {}
        for v in open_v:
            per[v["tech"].get("name", "-")] = per.get(v["tech"].get("name", "-"), 0) + 1
        parts.append("Aaj ke visit: " + ", ".join(f"{k} {n}" for k, n in per.items()))
    d = due(tenant, 7)
    if d["due"]:
        unbooked = [x for x in d["due"] if not x["booked"]]
        if unbooked:
            parts.append(f"{len(unbooked)} machine ki service hafte mein due, visit book nahi ({d['overdue']} late)")
    if d["amc_ending"]:
        parts.append(f"{len(d['amc_ending'])} AMC 30 din mein khatam")
    with session() as s:
        pend = s.scalars(select(AsVisit).where(AsVisit.tenant_id == tenant, AsVisit.status == "done")).all()
        waiting = [v.number for v in pend if _j(v.charge, {}).get("status") in ("pending", "needs_price")]
        no_report = [v.number for v in pend if not v.report_file and v.done_on and (on - (_date(v.done_on[:10]) or on)).days <= 7]
        late = [v.number for v in s.scalars(select(AsVisit).where(AsVisit.tenant_id == tenant, AsVisit.status.in_(OPEN),
                                                                    AsVisit.start < on.isoformat())).all()]
    if waiting:
        parts.append(f"{len(waiting)} visit ke charge par aapki haan baaki ({', '.join(waiting[:3])})")
    if no_report:
        parts.append(f"{len(no_report)} poore visit ki report graahak ko nahi gayi")
    if late:
        parts.append(f"{len(late)} pichhle visit ab tak poore nahi likhe ({', '.join(late[:3])})")
    cl = claims(tenant)
    if cl["stuck"]:
        parts.append(f"{len(cl['stuck'])} warranty claim 15 din se ruke - brand se poochhiye")
    drafts = len(messages(tenant, "draft"))
    if drafts:
        parts.append(f"{drafts} message draft bhejne baaki")
    return {"parts": parts, "visits": vs, "due": d["due"][:50], "charges_waiting": waiting, "say": ("; ".join(parts) + ".") if parts else "After-sales: sab theek."}


def due_mornings() -> list[str]:
    out = []
    with session() as s:
        for r in s.scalars(select(AsSettings)).all():
            if not s.scalars(select(AsUnit.id).where(AsUnit.tenant_id == r.tenant_id).limit(1)).first():
                continue
            local = now_local(r.tenant_id)
            hh, mm = _hm(r.morning_time, "08:30")
            late = (local.hour * 60 + local.minute) - (hh * 60 + mm)
            d = local.date().isoformat()
            if r.last_morning != d and 0 <= late <= 180:
                r.last_morning = d
                out.append(r.tenant_id)
    return out


def send_morning(tenant: str) -> dict:
    from ..events import notify
    from ..net.service import home_conv
    r = remind(tenant, publish=False)
    d = day(tenant)
    if not d["parts"]:
        return {"text": ""}
    text = "After-sales: " + d["say"]
    if r["messages"]:
        text += f" Aaj {len(r['messages'])} naye reminder draft bane."
    conv = home_conv(tenant)
    try:
        notify(conv, text)
    except Exception:
        pass
    _publish(tenant, "aftersales_day", {"text": text, "drafts": len(r["messages"])}, conv)
    return {"text": text}


def tick(now=None) -> int:  # noqa: A002 - worker calls tick(now)
    """Worker: once a day at her morning time - reminder drafts for machines due soon (never sent by themselves) + the day note."""
    n = 0
    for t in due_mornings():
        try:
            if send_morning(t)["text"]:
                n += 1
        except Exception:
            log.exception("aftersales morning failed for %s", t)
    return n


def overview(tenant: str) -> dict:
    return {"day": day(tenant), "settings": settings(tenant), "techs": techs(tenant), "amc": amc_view(tenant), "claims": claims(tenant),
            "drafts": messages(tenant, "draft")[:60], "schedules": schedules(tenant)}


def decode_b64(data: str) -> bytes:
    s = str(data or "")
    if "," in s[:80] and s.startswith("data:"):
        s = s.split(",", 1)[1]
    try:
        return base64.b64decode(s, validate=False)
    except Exception:
        raise AsError("File ka data sahi nahi (base64).")


def prompt_block(tenant: str) -> str:
    try:
        d = day(tenant)
    except Exception:
        return ""
    return ("AFTER-SALES: " + d["say"]) if d["parts"] else ""
