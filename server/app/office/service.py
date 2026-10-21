"""v0.85 Daftar Sahayak: Hoola works as the office manager.

The job, end to end (owner's spec + office-manager research, O*NET 11-3012 / 43-1011):
  1. Gets the job: she says it in chat or on a call, or forwards a bill, photo, file or message ("printer ka toner khatam",
     "AC kharab hai", "fire NOC kab renew hai?", "Rahul ko Friday tak report").
  2. Tracks supplies, repairs and renewals:
       supplies   stock book per item; daily use is LEARNED from the use log (last 30 days); reorder point = daily use x
                  lead days + safety days of use (or her own minimum, whichever is higher); suggested order = 30 days of use.
       repairs    tickets R-0001 with priority and a due time from the SLA (urgent 4 h, high 24 h, normal 72 h, low 7 days);
                  the same asset / area breaking again within 90 days is pointed out (AMC or replace?).
       renewals   licences, AMC, insurance, rent, subscriptions, domain, vehicle, taxes, bills; reminders at her windows
                  (30 / 15 / 7 / 1 / 0 days) and every day once overdue; repeating ones roll to the next due date when done;
                  a new amount more than 10% above last time is pointed out.
  3. Reminds the team of deadlines: today's / tomorrow's / overdue deadlines in the morning list, and a nudge message DRAFT
     per person (wa.me / sms link) that SHE sends. Hoola never messages the team by itself.
  4. Writes the weekly office note: tickets opened / closed / on time, stock used and bought, money approved, petty cash,
     renewals done and coming, deadlines met and missed, next week's deadlines; as a chat card and a Word file.
  5. Waits for her Haan on spending money: every purchase, paid repair and renewal payment is a spend card (S-0001) that
     shows the checks (last price, rise %, month budget left). Approve = go-ahead and a vendor message draft; money itself
     is paid by her in her own app. Petty cash already spent is only recorded.
  6. Delivers and learns: every change goes into the item / ticket / renewal log; real daily use, real repair times and
     real prices feed the next checks; the chat turn itself is learned as a procedure (v0.64).
"""
from __future__ import annotations

import json
import logging
import math
import re
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger("santosh.office")
_LOCK = threading.Lock()

DAYS = ("Som", "Mangal", "Budh", "Guru", "Shukra", "Shani", "Ravi")
PRIORITIES = ("urgent", "high", "normal", "low")
PRIORITY_LABEL = {"urgent": "Turant", "high": "Zaroori", "normal": "Normal", "low": "Aaram se"}
SLA_HOURS = {"urgent": 4, "high": 24, "normal": 72, "low": 168}
TICKET_STATUS = ("open", "assigned", "waiting", "done", "cancelled")
TICKET_OPEN = ("open", "assigned", "waiting")
CATEGORIES = ("ac", "electrical", "plumbing", "it", "printer", "internet", "furniture", "cleaning", "pest", "cctv",
              "ups", "water", "lift", "vehicle", "other")
RENEWAL_KINDS = {"licence": "Licence / registration", "amc": "AMC (maintenance contract)", "insurance": "Insurance",
                 "rent": "Rent / lease", "subscription": "Software / subscription", "domain": "Domain / hosting",
                 "vehicle": "Vehicle (insurance / PUC / fitness)", "tax": "Tax / filing", "bill": "Bill (electricity / net)",
                 "certificate": "Certificate / NOC", "other": "Other"}
# typical repeat in months, used when she does not say (from Indian office practice; she can change any)
USUAL_EVERY = {"licence": 12, "amc": 12, "insurance": 12, "rent": 11, "subscription": 12, "domain": 12, "vehicle": 12,
               "tax": 12, "bill": 1, "certificate": 12, "other": 12}
SPEND_KINDS = ("purchase", "repair", "renewal", "other")
DEFAULT_WINDOWS = [30, 15, 7, 1, 0]


class OfficeError(Exception):
    pass


# ---------------------------------------------------------------- tables
class OfficeSettings(Base):
    __tablename__ = "office_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    office_name: Mapped[str] = mapped_column(String(120), default="")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:30")
    note_day: Mapped[int] = mapped_column(Integer, default=4)               # 0 = Monday ... 4 = Friday
    note_time: Mapped[str] = mapped_column(String(5), default="17:30")
    windows: Mapped[str] = mapped_column(String(80), default=json.dumps(DEFAULT_WINDOWS))
    lead_days: Mapped[int] = mapped_column(Integer, default=3)              # usual days a vendor takes to deliver
    safety_days: Mapped[int] = mapped_column(Integer, default=3)            # extra days of stock kept
    month_budget_paise: Mapped[int] = mapped_column(Integer, default=0)     # 0 = no budget line
    team: Mapped[str] = mapped_column(Text, default="[]")                   # [{name, phone, role}]
    rules: Mapped[str] = mapped_column(Text, default="[]")                  # her own sentences
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    last_note: Mapped[str] = mapped_column(String(10), default="")
    seq_ticket: Mapped[int] = mapped_column(Integer, default=0)
    seq_spend: Mapped[int] = mapped_column(Integer, default=0)


class OfficeVendor(Base):
    __tablename__ = "office_vendors"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ov"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    category: Mapped[str] = mapped_column(String(40), default="")
    gstin: Mapped[str] = mapped_column(String(20), default="")
    udyam: Mapped[bool | None] = mapped_column(Boolean, nullable=True)     # micro / small (MSME) supplier: pay within 45 days
    notes: Mapped[str] = mapped_column(Text, default="")


class OfficeItem(Base):
    __tablename__ = "office_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("oi"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    unit: Mapped[str] = mapped_column(String(20), default="pcs")
    qty: Mapped[float] = mapped_column(Float, default=0)
    min_qty: Mapped[float] = mapped_column(Float, default=0)                # her own minimum (0 = learn it)
    lead_days: Mapped[int] = mapped_column(Integer, default=0)              # 0 = office default
    vendor_id: Mapped[str] = mapped_column(String(40), default="")
    price_paise: Mapped[int] = mapped_column(Integer, default=0)            # last price per unit
    on_order: Mapped[float] = mapped_column(Float, default=0)               # approved, not yet received
    location: Mapped[str] = mapped_column(String(60), default="")
    log: Mapped[str] = mapped_column(Text, default="[]")                    # [{at, d, why, by, price}]
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class OfficeTicket(Base):
    __tablename__ = "office_tickets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ot"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    asset: Mapped[str] = mapped_column(String(120), default="")             # "AC cabin 2", "reception printer"
    category: Mapped[str] = mapped_column(String(20), default="other")
    priority: Mapped[str] = mapped_column(String(10), default="normal")
    status: Mapped[str] = mapped_column(String(12), default="open")
    vendor_id: Mapped[str] = mapped_column(String(40), default="")
    assigned_to: Mapped[str] = mapped_column(String(80), default="")
    cost_paise: Mapped[int] = mapped_column(Integer, default=0)
    photos: Mapped[str] = mapped_column(Text, default="[]")
    log: Mapped[str] = mapped_column(Text, default="[]")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OfficeRenewal(Base):
    __tablename__ = "office_renewals"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("or"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="other")
    name: Mapped[str] = mapped_column(String(160), default="")
    due_on: Mapped[str] = mapped_column(String(10), default="")             # local date
    every_months: Mapped[int] = mapped_column(Integer, default=12)          # 0 = one time
    amount_paise: Mapped[int] = mapped_column(Integer, default=0)
    vendor_id: Mapped[str] = mapped_column(String(40), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    files: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(10), default="active")      # active | stopped
    notice_by: Mapped[str | None] = mapped_column(String(10), nullable=True)  # last day to say "don't renew" (auto-renewing contracts)
    reminded: Mapped[str] = mapped_column(String(40), default="")          # "<due_on>:<window>" last reminder sent
    history: Mapped[str] = mapped_column(Text, default="[]")               # [{done_on, due_on, paid}]


class OfficeDeadline(Base):
    __tablename__ = "office_deadlines"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("od"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    owner: Mapped[str] = mapped_column(String(80), default="")             # a team member's name
    due_on: Mapped[str] = mapped_column(String(10), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="open")        # open | done | dropped
    done_on: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OfficePetty(Base):
    __tablename__ = "office_petty"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("op"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    on: Mapped[str] = mapped_column(String(10), default="")
    what: Mapped[str] = mapped_column(String(200), default="")
    amount_paise: Mapped[int] = mapped_column(Integer, default=0)          # + money put in, - money spent
    by: Mapped[str] = mapped_column(String(80), default="")
    bill: Mapped[str] = mapped_column(String(60), default="")              # file id of the bill photo
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OfficeBill(Base):
    """A vendor bill: due date, MSME 45-day rule (Income Tax s.43B(h)), GST ITC 180-day rule (CGST Rule 37), duplicates."""
    __tablename__ = "office_bills"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ob"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    vendor_id: Mapped[str] = mapped_column(String(40), default="")
    number: Mapped[str] = mapped_column(String(60), default="")
    bill_date: Mapped[str] = mapped_column(String(10), default="")
    due_on: Mapped[str] = mapped_column(String(10), default="")
    amount_paise: Mapped[int] = mapped_column(Integer, default=0)
    gst_paise: Mapped[int] = mapped_column(Integer, default=0)
    what: Mapped[str] = mapped_column(String(200), default="")
    file_id: Mapped[str] = mapped_column(String(60), default="")
    paid_on: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OfficeSpend(Base):
    __tablename__ = "office_spends"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("os"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    kind: Mapped[str] = mapped_column(String(12), default="other")
    title: Mapped[str] = mapped_column(String(200), default="")
    lines: Mapped[str] = mapped_column(Text, default="[]")                 # [{item_id, name, qty, unit, price_paise}]
    amount_paise: Mapped[int] = mapped_column(Integer, default=0)
    vendor_id: Mapped[str] = mapped_column(String(40), default="")
    ref_id: Mapped[str] = mapped_column(String(40), default="")            # ticket / renewal id
    checks: Mapped[str] = mapped_column(Text, default="[]")                # what Hoola checked, in words
    status: Mapped[str] = mapped_column(String(10), default="pending")    # pending | approved | rejected
    note: Mapped[str] = mapped_column(Text, default="")
    conv: Mapped[str] = mapped_column(String(40), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ---------------------------------------------------------------- small helpers
def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _rs(paise: int) -> str:
    r = int(paise or 0) / 100
    return f"₹{int(r):,}" if r == int(r) else f"₹{r:,.2f}"


def _paise(v) -> int:
    if v in (None, ""):
        return 0
    try:
        return int(round(float(str(v).replace(",", "").replace("₹", "").replace("Rs", "").replace("rs", "").strip()) * 100))
    except ValueError:
        raise OfficeError(f"'{v}' rupaye ki rakam nahi lagti.")


def _num(v, field: str = "qty") -> float:
    if v in (None, ""):
        return 0.0
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        raise OfficeError(f"{field} '{v}' number nahi hai.")


def _digits(p: str) -> str:
    d = re.sub(r"\D", "", str(p or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    return d[-10:] if len(d) >= 10 else d


def _tz(tenant: str):
    from ..life import tz_of
    return tz_of(tenant)


def today(tenant: str) -> date:
    return datetime.now(_tz(tenant)).date()


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _date(tenant: str, v: str | None, field: str = "date") -> str:
    """'2026-10-28' / '28/10' / 'aaj' / 'kal' / 'parso' / '5 din' / '2 hafte' / '3 mahine' -> YYYY-MM-DD ('' if empty)."""
    s = str(v or "").strip().lower()
    if not s:
        return ""
    t = today(tenant)
    if s in ("aaj", "today"):
        return t.isoformat()
    if s in ("kal", "tomorrow"):
        return (t + timedelta(days=1)).isoformat()
    if s in ("parso", "parson"):
        return (t + timedelta(days=2)).isoformat()
    m = re.fullmatch(r"(\d{1,3})\s*(din|days?|d)(\s*(mein|baad|me|after))?", s)
    if m:
        return (t + timedelta(days=int(m.group(1)))).isoformat()
    m = re.fullmatch(r"(\d{1,2})\s*(hafte|hafta|weeks?|w)(\s*(mein|baad|me|after))?", s)
    if m:
        return (t + timedelta(days=7 * int(m.group(1)))).isoformat()
    m = re.fullmatch(r"(\d{1,2})\s*(mahine|mahina|months?)(\s*(mein|baad|me|after))?", s)
    if m:
        return _add_months(t, int(m.group(1))).isoformat()
    try:
        m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?", s)
        if m:
            y = int(m.group(3)) if m.group(3) else t.year
            y = y + 2000 if y < 100 else y
            d = date(y, int(m.group(2)), int(m.group(1)))
            if not m.group(3) and d < t - timedelta(days=60):
                d = date(y + 1, d.month, d.day)
            return d.isoformat()
    except ValueError:
        pass
    raise OfficeError(f"{field} '{v}' samajh nahi aaya (jaise 28/10, 2026-10-28, kal, 5 din, 3 mahine).")


def _add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    last = [31, 29 if (y % 4 == 0 and (y % 100 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(y, m, min(d.day, last))


def _nice(d: str) -> str:
    try:
        x = date.fromisoformat(d)
    except (TypeError, ValueError):
        return d or "-"
    return f"{DAYS[x.weekday()]} {x.day:02d}/{x.month:02d}/{x.year}"


def _days_left(tenant: str, d: str) -> int | None:
    try:
        return (date.fromisoformat(d) - today(tenant)).days
    except (TypeError, ValueError):
        return None


def _push_log(row, what: str, by: str = "owner", **extra) -> None:
    lg = _j(row.log, [])
    lg.append({"at": now().isoformat(), "what": what[:300], "by": by} | extra)
    row.log = json.dumps(lg[-120:], ensure_ascii=False)


def _publish(tenant: str, kind: str, payload: dict[str, Any], conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("office publish failed")


def _tidy(s: str, n: int = 200) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()[:n]


def _match(name: str, q: str) -> bool:
    a, b = name.lower(), q.lower().strip()
    return bool(b) and (b == a or b in a or all(w in a for w in b.split()))


# ---------------------------------------------------------------- settings
def _settings_row(s, tenant: str) -> OfficeSettings:
    r = s.get(OfficeSettings, tenant)
    if r is None:
        r = OfficeSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def _settings_view(r: OfficeSettings) -> dict[str, Any]:
    return {"enabled": r.enabled, "office_name": r.office_name, "morning_time": r.morning_time, "note_day": r.note_day,
            "note_day_name": DAYS[r.note_day % 7], "note_time": r.note_time, "windows": _j(r.windows, DEFAULT_WINDOWS),
            "lead_days": r.lead_days, "safety_days": r.safety_days,
            "month_budget": r.month_budget_paise / 100 if r.month_budget_paise else 0, "team": _j(r.team, []),
            "rules": _j(r.rules, []), "sla_hours": SLA_HOURS}


def settings(tenant: str) -> dict[str, Any]:
    with session() as s:
        return _settings_view(_settings_row(s, tenant))


def _hhmm(v: str, field: str) -> str:
    m = re.fullmatch(r"(\d{1,2})[:.](\d{2})", str(v).strip())
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        raise OfficeError(f"{field} '{v}' samay nahi lagta (jaise 09:30).")
    return f"{int(m.group(1)):02d}:{m.group(2)}"


def save_settings(tenant: str, **kw: Any) -> dict[str, Any]:
    with session() as s:
        r = _settings_row(s, tenant)
        if "enabled" in kw and kw["enabled"] is not None:
            r.enabled = bool(kw["enabled"])
        if kw.get("office_name") is not None:
            r.office_name = _tidy(kw["office_name"], 120)
        if kw.get("morning_time"):
            r.morning_time = _hhmm(kw["morning_time"], "morning_time")
        if kw.get("note_time"):
            r.note_time = _hhmm(kw["note_time"], "note_time")
        if kw.get("note_day") not in (None, ""):
            v = kw["note_day"]
            if isinstance(v, str) and not v.isdigit():
                names = {d.lower(): i for i, d in enumerate(DAYS)} | {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                                                                      "friday": 4, "saturday": 5, "sunday": 6}
                if v.strip().lower() not in names:
                    raise OfficeError("note_day: Som..Ravi ya Monday..Sunday")
                v = names[v.strip().lower()]
            r.note_day = int(v) % 7
        if kw.get("windows") is not None:
            w = sorted({int(x) for x in kw["windows"] if str(x).strip().lstrip("-").isdigit() and 0 <= int(x) <= 180}, reverse=True)
            r.windows = json.dumps(w or DEFAULT_WINDOWS)
        for k in ("lead_days", "safety_days"):
            if kw.get(k) not in (None, ""):
                setattr(r, k, max(0, min(90, int(kw[k]))))
        if kw.get("month_budget") not in (None, ""):
            r.month_budget_paise = max(0, _paise(kw["month_budget"]))
        if kw.get("team") is not None:
            team = []
            for m in kw["team"][:60]:
                if isinstance(m, str):
                    m = {"name": m}
                if isinstance(m, dict) and _tidy(m.get("name"), 80):
                    team.append({"name": _tidy(m.get("name"), 80), "phone": _digits(m.get("phone", "")),
                                 "role": _tidy(m.get("role", ""), 60)})
            r.team = json.dumps(team, ensure_ascii=False)
        if kw.get("rules") is not None:
            r.rules = json.dumps([_tidy(x, 300) for x in kw["rules"] if _tidy(x, 300)][:40], ensure_ascii=False)
        return _settings_view(r)


def _person(s, tenant: str, name: str) -> dict[str, Any]:
    for m in _j(_settings_row(s, tenant).team, []):
        if _match(m["name"], name) or _match(name, m["name"]):
            return m
    return {"name": _tidy(name, 80), "phone": ""}


# ---------------------------------------------------------------- vendors
def _vendor_view(v: OfficeVendor | None) -> dict[str, Any] | None:
    if v is None:
        return None
    return {"id": v.id, "name": v.name, "phone": v.phone, "email": v.email, "category": v.category, "gstin": v.gstin,
            "udyam": bool(v.udyam), "notes": v.notes}


def _find_vendor(s, tenant: str, ref: str) -> OfficeVendor | None:
    ref = str(ref or "").strip()
    if not ref:
        return None
    v = s.get(OfficeVendor, ref)
    if v is not None and v.tenant_id == tenant:
        return v
    rows = s.scalars(select(OfficeVendor).where(OfficeVendor.tenant_id == tenant)).all()
    d = _digits(ref)
    for v in rows:
        if (len(d) >= 10 and v.phone == d) or v.name.lower() == ref.lower():
            return v
    for v in rows:
        if _match(v.name, ref):
            return v
    return None


def vendor_upsert(tenant: str, name: str, phone: str = "", email: str = "", category: str = "", gstin: str = "",
                  notes: str = "", vendor: str = "", udyam: bool | None = None) -> dict[str, Any]:
    with session() as s:
        v = _find_vendor(s, tenant, vendor or name)
        if v is None:
            if not _tidy(name):
                raise OfficeError("Vendor ka naam chahiye.")
            v = OfficeVendor(tenant_id=tenant, name=_tidy(name, 120))
            s.add(v)
        if phone:
            v.phone = _digits(phone)
        for k, val in (("email", email), ("category", category), ("gstin", gstin), ("notes", notes)):
            if val:
                setattr(v, k, _tidy(val, 300))
        if name and vendor:
            v.name = _tidy(name, 120)
        if udyam is not None:
            v.udyam = bool(udyam)
        warn = ""
        if gstin:
            try:
                from ..india.money import gstin_ok
                if not gstin_ok(v.gstin.upper()):
                    warn = "GSTIN ka check digit galat lagta hai; vendor se dobara confirm kijiye."
            except Exception:
                pass
        s.flush()
        return _vendor_view(v) | ({"warn": warn} if warn else {})


def vendors(tenant: str, q: str = "") -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(OfficeVendor).where(OfficeVendor.tenant_id == tenant).order_by(OfficeVendor.name)).all()
        return [_vendor_view(v) for v in rows if not q or _match(v.name + " " + v.category, q)]


# ---------------------------------------------------------------- supplies
def _use_per_day(it: OfficeItem) -> float:
    """Real daily use, learned from the last 30 days of 'used' entries (0 until there is some history)."""
    cutoff = now() - timedelta(days=30)
    used, first = 0.0, None
    for e in _j(it.log, []):
        try:
            at = datetime.fromisoformat(e["at"])
        except (KeyError, ValueError):
            continue
        at = _utc(at)
        if e.get("why") == "used" and at >= cutoff:
            used += -float(e.get("d", 0))
            first = at if first is None or at < first else first
    if used <= 0 or first is None:
        return 0.0
    span = max(7.0, (now() - first).total_seconds() / 86400)     # at least a week, so one burst doesn't look like daily use
    return used / span


def _reorder_point(it: OfficeItem, st: OfficeSettings) -> tuple[float, float, str]:
    """(reorder point, suggested order, how it was worked out)."""
    per = _use_per_day(it)
    lead = it.lead_days or st.lead_days
    learned = math.ceil(per * (lead + st.safety_days)) if per else 0
    point = max(it.min_qty or 0, learned)
    why = (f"roz ~{per:.1f} {it.unit} use x ({lead} din vendor + {st.safety_days} din safety) = {learned}" if per else
           "abhi use ka record kam hai")
    if it.min_qty and it.min_qty >= learned:
        why = f"aapka minimum {it.min_qty:g} {it.unit}" + (f" ({why})" if per else "")
    suggest = max(math.ceil(per * 30), math.ceil(point * 2 - it.qty), 1) if (per or point) else 1
    return point, float(suggest), why


def _item_view(it: OfficeItem, st: OfficeSettings, vendor: OfficeVendor | None = None) -> dict[str, Any]:
    point, suggest, why = _reorder_point(it, st)
    low = (it.qty + it.on_order) <= point and (point > 0)
    per = _use_per_day(it)
    return {"id": it.id, "name": it.name, "unit": it.unit, "qty": it.qty, "min_qty": it.min_qty, "on_order": it.on_order,
            "reorder_point": point, "suggest": suggest, "why": why, "low": low, "per_day": round(per, 2),
            "days_left": (round(it.qty / per, 1) if per else None), "price": _rs(it.price_paise) if it.price_paise else "",
            "price_rupees": it.price_paise / 100 if it.price_paise else None, "location": it.location,
            "vendor": _vendor_view(vendor), "lead_days": it.lead_days or st.lead_days, "log": _j(it.log, [])[-12:]}


def _find_item(s, tenant: str, ref: str) -> OfficeItem | None:
    ref = str(ref or "").strip()
    if not ref:
        return None
    it = s.get(OfficeItem, ref)
    if it is not None and it.tenant_id == tenant:
        return it
    rows = s.scalars(select(OfficeItem).where(OfficeItem.tenant_id == tenant)).all()
    for it in rows:
        if it.name.lower() == ref.lower():
            return it
    for it in rows:
        if _match(it.name, ref):
            return it
    return None


def item_upsert(tenant: str, name: str, qty: Any = None, unit: str = "", min_qty: Any = None, lead_days: Any = None,
                vendor: str = "", price: Any = None, location: str = "", by: str = "owner") -> dict[str, Any]:
    with session() as s:
        st = _settings_row(s, tenant)
        it = _find_item(s, tenant, name)
        if it is None:
            if not _tidy(name):
                raise OfficeError("Saamaan ka naam chahiye.")
            it = OfficeItem(tenant_id=tenant, name=_tidy(name, 120), unit=_tidy(unit, 20) or "pcs", log="[]")
            s.add(it)
            if qty not in (None, ""):
                it.qty = _num(qty)
                _push_log(it, f"shuru: {it.qty:g} {it.unit}", by, d=it.qty, why="count")
        elif qty not in (None, ""):
            new = _num(qty)
            if new != it.qty:
                _push_log(it, f"gina: {it.qty:g} -> {new:g}", by, d=new - it.qty, why="count")
                it.qty = new
        if unit:
            it.unit = _tidy(unit, 20)
        if min_qty not in (None, ""):
            it.min_qty = max(0.0, _num(min_qty, "min_qty"))
        if lead_days not in (None, ""):
            it.lead_days = max(0, int(_num(lead_days, "lead_days")))
        if price not in (None, ""):
            it.price_paise = _paise(price)
        if location:
            it.location = _tidy(location, 60)
        v = None
        if vendor:
            v = _find_vendor(s, tenant, vendor)
            if v is None:
                v = OfficeVendor(tenant_id=tenant, name=_tidy(vendor, 120))
                s.add(v)
                s.flush()
            it.vendor_id = v.id
        s.flush()
        return _item_view(it, st, v or (s.get(OfficeVendor, it.vendor_id) if it.vendor_id else None))


def use(tenant: str, item: str, qty: Any, note: str = "", by: str = "owner") -> dict[str, Any]:
    with session() as s:
        st = _settings_row(s, tenant)
        it = _find_item(s, tenant, item)
        if it is None:
            raise OfficeError(f"'{item}' stock list mein nahi hai. Pehle item_add karein.")
        q = _num(qty)
        if q <= 0:
            raise OfficeError("Kitna use hua? (0 se zyada)")
        it.qty = max(0.0, it.qty - q)
        _push_log(it, f"use {q:g} {it.unit}" + (f": {note}" if note else ""), by, d=-q, why="used")
        s.flush()
        v = _item_view(it, st, s.get(OfficeVendor, it.vendor_id) if it.vendor_id else None)
    return v | {"say": f"{v['name']}: {v['qty']:g} {v['unit']} bacha." + (" Kam hai: reorder ka card bana sakti hoon." if v["low"] else "")}


def restock(tenant: str, item: str, qty: Any, price: Any = None, vendor: str = "", by: str = "owner") -> dict[str, Any]:
    with session() as s:
        st = _settings_row(s, tenant)
        it = _find_item(s, tenant, item)
        if it is None:
            raise OfficeError(f"'{item}' stock list mein nahi hai.")
        q = _num(qty)
        if q <= 0:
            raise OfficeError("Kitna aaya?")
        it.qty += q
        it.on_order = max(0.0, it.on_order - q)
        p = _paise(price) if price not in (None, "") else 0
        note = ""
        if p:
            if it.price_paise and p > it.price_paise * 1.15:
                note = f"Daam pichhli baar se {round((p / it.price_paise - 1) * 100)}% zyada ({_rs(it.price_paise)} -> {_rs(p)})."
            it.price_paise = p
        if vendor:
            v = _find_vendor(s, tenant, vendor) or OfficeVendor(tenant_id=tenant, name=_tidy(vendor, 120))
            if not v.id:
                s.add(v)
                s.flush()
            it.vendor_id = v.id
        _push_log(it, f"aaya {q:g} {it.unit}" + (f" @ {_rs(p)}" if p else ""), by, d=q, why="received", price=p)
        s.flush()
        return _item_view(it, st, s.get(OfficeVendor, it.vendor_id) if it.vendor_id else None) | {"price_note": note}


def items(tenant: str, q: str = "", low_only: bool = False) -> list[dict[str, Any]]:
    with session() as s:
        st = _settings_row(s, tenant)
        vs = {v.id: v for v in s.scalars(select(OfficeVendor).where(OfficeVendor.tenant_id == tenant)).all()}
        out = [_item_view(it, st, vs.get(it.vendor_id)) for it in
               s.scalars(select(OfficeItem).where(OfficeItem.tenant_id == tenant).order_by(OfficeItem.name)).all()
               if not q or _match(it.name, q)]
    return [x for x in out if x["low"]] if low_only else out


# ---------------------------------------------------------------- money: her Haan on every spend
def _month_spent(s, tenant: str) -> int:
    t = today(tenant)
    start = datetime(t.year, t.month, 1, tzinfo=_tz(tenant)).astimezone(timezone.utc).replace(tzinfo=None)
    rows = s.scalars(select(OfficeSpend).where(OfficeSpend.tenant_id == tenant, OfficeSpend.status == "approved")).all()
    return sum(r.amount_paise for r in rows if r.decided_at and _utc(r.decided_at).replace(tzinfo=None) >= start)


def _spend_view(s, r: OfficeSpend) -> dict[str, Any]:
    st = _settings_row(s, r.tenant_id)
    v = s.get(OfficeVendor, r.vendor_id) if r.vendor_id else None
    spent = _month_spent(s, r.tenant_id)
    out = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "lines": _j(r.lines, []),
           "amount": _rs(r.amount_paise) if r.amount_paise else "", "amount_rupees": r.amount_paise / 100 if r.amount_paise else None,
           "vendor": _vendor_view(v), "checks": _j(r.checks, []), "status": r.status, "note": r.note, "ref_id": r.ref_id,
           "month_spent": _rs(spent), "created_at": r.created_at.isoformat()}
    if st.month_budget_paise:
        left = st.month_budget_paise - spent
        out["month_budget"] = _rs(st.month_budget_paise)
        out["month_left"] = _rs(max(0, left))
        if r.status == "pending" and r.amount_paise > left:
            out["over_budget"] = True
    if r.status == "approved" and v is not None:
        out["vendor_message"] = _vendor_text(s, r, v)
        out |= _links(v, out["vendor_message"])
    return out


def _links(v: OfficeVendor, text: str) -> dict[str, str]:
    out = {}
    if v.phone:
        out["wa_link"] = f"https://wa.me/91{v.phone}?text={quote(text)}"
        out["sms_link"] = f"sms:+91{v.phone}?body={quote(text)}"
    if v.email:
        out["mail_link"] = f"mailto:{v.email}?subject={quote('Order from ' + 'office')}&body={quote(text)}"
    return out


def _vendor_text(s, r: OfficeSpend, v: OfficeVendor) -> str:
    st = _settings_row(s, r.tenant_id)
    who = st.office_name or "hamara office"
    if r.kind == "purchase":
        lines = "; ".join(f"{l['name']} {l['qty']:g} {l.get('unit', '')}".strip() for l in _j(r.lines, []))
        return f"Namaste {v.name} ji, {who} ke liye order: {lines}. Kripya rate aur delivery date bata dijiye. Dhanyavaad."
    if r.kind == "repair":
        return f"Namaste {v.name} ji, {who}: {r.title}. Aap kab aa sakte hain? Dhanyavaad."
    if r.kind == "renewal":
        return f"Namaste {v.name} ji, {who}: {r.title} renew karna hai. Kripya invoice / process bata dijiye."
    return f"Namaste {v.name} ji, {who}: {r.title}."


def _new_spend(s, tenant: str, kind: str, title: str, amount_paise: int, vendor_id: str = "", lines: list | None = None,
               ref_id: str = "", checks: list[str] | None = None, conv: str = "") -> OfficeSpend:
    st = _settings_row(s, tenant)
    # the same thing already waiting for her: never ask twice
    for r in s.scalars(select(OfficeSpend).where(OfficeSpend.tenant_id == tenant, OfficeSpend.status == "pending",
                                                OfficeSpend.kind == kind)).all():
        if (ref_id and r.ref_id == ref_id) or (not ref_id and r.title == title and r.vendor_id == vendor_id):
            return r
    st.seq_spend += 1
    r = OfficeSpend(tenant_id=tenant, number=f"S-{st.seq_spend:04d}", kind=kind if kind in SPEND_KINDS else "other",
                    title=_tidy(title, 200), amount_paise=max(0, amount_paise), vendor_id=vendor_id,
                    lines=json.dumps(lines or [], ensure_ascii=False), ref_id=ref_id,
                    checks=json.dumps(checks or [], ensure_ascii=False), conv=conv)
    s.add(r)
    s.flush()
    return r


def spend_request(tenant: str, title: str, amount: Any, kind: str = "other", vendor: str = "", why: str = "",
                  conv: str = "") -> dict[str, Any]:
    with session() as s:
        v = _find_vendor(s, tenant, vendor) if vendor else None
        if vendor and v is None:
            v = OfficeVendor(tenant_id=tenant, name=_tidy(vendor, 120))
            s.add(v)
            s.flush()
        checks = [why] if why else []
        r = _new_spend(s, tenant, kind, title, _paise(amount), v.id if v else "", checks=checks, conv=conv)
        view = _spend_view(s, r)
    _publish(tenant, "office_spend", view, conv)
    return {"spend": view, "say": f"Kharcha card {view['number']} bana: aapki Haan ke baad hi aage badhega."}


def reorder(tenant: str, names: list[str] | None = None, conv: str = "") -> dict[str, Any]:
    """Low items (or the ones she named) -> one spend card per vendor, with the checks in words."""
    made = []
    with session() as s:
        st = _settings_row(s, tenant)
        rows = s.scalars(select(OfficeItem).where(OfficeItem.tenant_id == tenant)).all()
        pick = []
        for it in rows:
            point, suggest, why = _reorder_point(it, st)
            wanted = names and any(_match(it.name, n) for n in names)
            if wanted or (not names and (it.qty + it.on_order) <= point and point > 0):
                pick.append((it, suggest, why))
        if not pick:
            return {"spends": [], "say": "Abhi kuch kam nahi hai."}
        by_vendor: dict[str, list] = {}
        for it, sug, why in pick:
            by_vendor.setdefault(it.vendor_id, []).append((it, sug, why))
        for vid, group in by_vendor.items():
            lines, checks, total = [], [], 0
            for it, sug, why in group:
                lines.append({"item_id": it.id, "name": it.name, "qty": sug, "unit": it.unit, "price_paise": it.price_paise})
                total += int(round(it.price_paise * sug))
                checks.append(f"{it.name}: {it.qty:g} {it.unit} bacha, reorder point {math.ceil(_reorder_point(it, st)[0])} ({why}); "
                              f"order {sug:g}" + (f" @ pichhla daam {_rs(it.price_paise)}" if it.price_paise else " (daam pata nahi)"))
            v = s.get(OfficeVendor, vid) if vid else None
            title = "Saamaan: " + ", ".join(l["name"] for l in lines)[:150]
            r = _new_spend(s, tenant, "purchase", title, total, vid, lines, checks=checks, conv=conv)
            if not v:
                r.note = "Vendor set nahi hai: approve ke baad kisse mangwana hai bataiye."
            made.append(_spend_view(s, r))
    for m in made:
        _publish(tenant, "office_spend", m, conv)
    return {"spends": made, "say": f"{len(made)} kharcha card bane. Aapki Haan ke baad vendor ka message draft milega."}


def decide_spend(tenant: str, spend_id: str, approve: bool, amount: Any = None, note: str = "") -> dict[str, Any]:
    with session() as s:
        r = s.get(OfficeSpend, spend_id)
        if r is None or r.tenant_id != tenant:
            r = s.scalars(select(OfficeSpend).where(OfficeSpend.tenant_id == tenant, OfficeSpend.number == str(spend_id).upper())).first()
        if r is None:
            raise OfficeError("Yeh kharcha card nahi mila.")
        if r.status != "pending":
            return {"spend": _spend_view(s, r), "say": "Is par faisla ho chuka hai."}
        if amount not in (None, ""):
            r.amount_paise = _paise(amount)
        r.status = "approved" if approve else "rejected"
        r.decided_at = now()
        if note:
            r.note = _tidy(note, 300)
        if approve:
            if r.kind == "purchase":
                for l in _j(r.lines, []):
                    it = s.get(OfficeItem, l.get("item_id") or "")
                    if it is not None:
                        it.on_order += float(l.get("qty") or 0)
                        _push_log(it, f"order manzoor {r.number}: {float(l.get('qty') or 0):g} {it.unit}", "owner", why="ordered")
            elif r.kind == "repair":
                t = s.get(OfficeTicket, r.ref_id)
                if t is not None:
                    t.cost_paise = r.amount_paise
                    _push_log(t, f"kharcha manzoor {_rs(r.amount_paise)} ({r.number})")
            elif r.kind == "renewal":
                rn = s.get(OfficeRenewal, r.ref_id)
                if rn is not None:
                    rn.notes = (rn.notes + f"\nPayment manzoor {_rs(r.amount_paise)} ({r.number}); bhugtan aap apne app se karengi.").strip()
        view = _spend_view(s, r)
        conv = r.conv
    _publish(tenant, "office_spend", view, conv)
    if approve:
        say = f"{view['number']} manzoor." + (" Vendor ka message draft card par hai: aap tap karengi tabhi jayega." if view.get("vendor_message")
                                              else "") + " Paise aap apne app se dengi."
    else:
        say = f"{view['number']} mana. Kuch nahi kiya."
    return {"spend": view, "say": say}


def spends(tenant: str, status: str = "pending") -> list[dict[str, Any]]:
    with session() as s:
        q = select(OfficeSpend).where(OfficeSpend.tenant_id == tenant)
        if status and status != "all":
            q = q.where(OfficeSpend.status == status)
        return [_spend_view(s, r) for r in s.scalars(q.order_by(OfficeSpend.created_at.desc()).limit(80)).all()]


# ---------------------------------------------------------------- repairs / maintenance
def _ticket_view(s, t: OfficeTicket, tenant: str) -> dict[str, Any]:
    v = s.get(OfficeVendor, t.vendor_id) if t.vendor_id else None
    due = _utc(t.due_at)
    late = t.status in TICKET_OPEN and due is not None and now() > due
    out = {"id": t.id, "number": t.number, "title": t.title, "asset": t.asset, "category": t.category, "priority": t.priority,
           "priority_label": PRIORITY_LABEL.get(t.priority, t.priority), "status": t.status, "assigned_to": t.assigned_to,
           "vendor": _vendor_view(v), "cost": _rs(t.cost_paise) if t.cost_paise else "", "photos": _j(t.photos, []),
           "due_at": due.isoformat() if due else None, "late": late, "log": _j(t.log, [])[-15:],
           "created_at": t.created_at.isoformat(), "done_at": t.done_at.isoformat() if t.done_at else None}
    if due is not None and t.status in TICKET_OPEN:
        hrs = (due - now()).total_seconds() / 3600
        out["due_in"] = (f"{abs(hrs):.0f} ghante der" if hrs < 0 else f"{hrs:.0f} ghante mein")
    return out


def _find_ticket(s, tenant: str, ref: str) -> OfficeTicket:
    ref = str(ref or "").strip()
    t = s.get(OfficeTicket, ref)
    if t is not None and t.tenant_id == tenant:
        return t
    m = re.fullmatch(r"(?:r-?)?(\d{1,5})", ref.lower())
    if m:
        t = s.scalars(select(OfficeTicket).where(OfficeTicket.tenant_id == tenant, OfficeTicket.number == f"R-{int(m.group(1)):04d}")).first()
        if t is not None:
            return t
    for t in s.scalars(select(OfficeTicket).where(OfficeTicket.tenant_id == tenant, OfficeTicket.status.in_(TICKET_OPEN))
                       .order_by(OfficeTicket.created_at.desc())).all():
        if ref and (_match(t.title, ref) or _match(t.asset, ref)):
            return t
    raise OfficeError(f"Ticket '{ref}' nahi mila.")


def _category_of(text: str) -> str:
    t = text.lower()
    pairs = [("ac", ("ac ", " ac", "air condition", "cooling")), ("printer", ("printer", "toner", "cartridge", "xerox", "copier")),
             ("internet", ("internet", "wifi", "wi-fi", "router", "net nahi", "broadband")), ("electrical", ("light", "bijli", "switch", "fan", "socket", "mcb", "wiring")),
             ("plumbing", ("tap", "nal", "leak", "toilet", "pipe", "washroom")), ("it", ("computer", "laptop", "pc", "software", "email", "mouse", "keyboard")),
             ("ups", ("ups", "inverter", "battery")), ("cctv", ("cctv", "camera", "dvr")), ("water", ("ro", "water", "paani", "purifier")),
             ("furniture", ("chair", "table", "kursi", "almari", "door", "lock")), ("cleaning", ("safai", "clean", "dust")),
             ("pest", ("pest", "cockroach", "rat", "chuha", "termite")), ("lift", ("lift", "elevator")), ("vehicle", ("car", "bike", "gaadi", "vehicle"))]
    for cat, words in pairs:
        if any(w in f" {t} " for w in words):
            return cat
    return "other"


def ticket_new(tenant: str, title: str, asset: str = "", category: str = "", priority: str = "", vendor: str = "",
               assigned_to: str = "", photos: list[str] | None = None, by: str = "owner", conv: str = "") -> dict[str, Any]:
    title = _tidy(title, 200)
    if not title:
        raise OfficeError("Kya kharab hai? (title)")
    pr = (priority or "").lower().strip()
    pr = {"turant": "urgent", "zaroori": "high", "jaldi": "high", "aaram": "low"}.get(pr, pr)
    if pr not in PRIORITIES:
        low = title.lower()
        pr = "urgent" if any(w in low for w in ("aag", "fire", "short circuit", "spark", "smoke", "dhua", "pani bhar", "flood",
                                                  "gas", "lift band", "atka")) else "normal"
    with session() as s:
        st = _settings_row(s, tenant)
        st.seq_ticket += 1
        cat = category if category in CATEGORIES else _category_of(title + " " + asset)
        t = OfficeTicket(tenant_id=tenant, number=f"R-{st.seq_ticket:04d}", title=title, asset=_tidy(asset, 120), category=cat,
                         priority=pr, assigned_to=_tidy(assigned_to, 80), photos=json.dumps(photos or []), log="[]",
                         due_at=now() + timedelta(hours=SLA_HOURS[pr]))
        if vendor:
            v = _find_vendor(s, tenant, vendor) or OfficeVendor(tenant_id=tenant, name=_tidy(vendor, 120), category=cat)
            if not v.id:
                s.add(v)
                s.flush()
            t.vendor_id = v.id
            t.status = "assigned"
        elif not t.vendor_id:   # the vendor who fixed this kind of thing before
            prev = s.scalars(select(OfficeTicket).where(OfficeTicket.tenant_id == tenant, OfficeTicket.category == cat,
                                                        OfficeTicket.vendor_id != "").order_by(OfficeTicket.created_at.desc())).first()
            if prev is not None:
                t.vendor_id = prev.vendor_id
        _push_log(t, f"khola: {title} ({PRIORITY_LABEL[pr]}, {SLA_HOURS[pr]} ghante mein theek hona chahiye)", by)
        s.add(t)
        s.flush()
        # earlier work: the same thing breaking again
        since = now() - timedelta(days=90)
        key = (t.asset or "").lower()
        repeats = []
        for o in s.scalars(select(OfficeTicket).where(OfficeTicket.tenant_id == tenant, OfficeTicket.id != t.id)).all():
            if _utc(o.created_at) < since:
                continue
            if (key and key == (o.asset or "").lower()) or (not key and o.category == cat and cat != "other" and _match(o.title, title.split()[0])):
                repeats.append(o.number)
        view = _ticket_view(s, t, tenant)
    notes = []
    if repeats:
        notes.append(f"Yeh 90 din mein {len(repeats) + 1}vi baar ({', '.join(repeats)}). AMC ya badalne ka sochiye.")
    if view["vendor"] and not vendor:
        notes.append(f"Pichhli baar {view['vendor']['name']} ne theek kiya tha; unhe hi bula sakte hain.")
    _publish(tenant, "office", {"what": "ticket", "ticket": view}, conv)
    return {"ticket": view, "notes": notes,
            "say": f"{view['number']} khola: {title}. {view['priority_label']}, {SLA_HOURS[pr]} ghante mein." + (" " + " ".join(notes) if notes else "")}


def ticket_update(tenant: str, ticket: str, status: str = "", note: str = "", vendor: str = "", assigned_to: str = "",
                  cost: Any = None, by: str = "owner", conv: str = "") -> dict[str, Any]:
    card = None
    with session() as s:
        t = _find_ticket(s, tenant, ticket)
        if vendor:
            v = _find_vendor(s, tenant, vendor) or OfficeVendor(tenant_id=tenant, name=_tidy(vendor, 120), category=t.category)
            if not v.id:
                s.add(v)
                s.flush()
            t.vendor_id = v.id
            if t.status == "open":
                t.status = "assigned"
            _push_log(t, f"vendor: {v.name}", by)
        if assigned_to:
            t.assigned_to = _tidy(assigned_to, 80)
            _push_log(t, f"diya: {t.assigned_to}", by)
        if status:
            st_ = {"theek": "done", "ho gaya": "done", "fixed": "done", "band": "cancelled"}.get(status.lower(), status.lower())
            if st_ not in TICKET_STATUS:
                raise OfficeError("status = open | assigned | waiting | done | cancelled")
            t.status = st_
            if st_ == "done":
                t.done_at = now()
                took = (now() - _utc(t.created_at)).total_seconds() / 3600
                on_time = _utc(t.due_at) is None or now() <= _utc(t.due_at)
                _push_log(t, f"theek: {took:.0f} ghante mein, " + ("samay par" if on_time else "der se"), by)
            else:
                _push_log(t, f"status: {st_}", by)
        if note:
            _push_log(t, note, by)
        if cost not in (None, ""):
            p = _paise(cost)
            if p and p != t.cost_paise:
                prev = [o.cost_paise for o in s.scalars(select(OfficeTicket).where(
                    OfficeTicket.tenant_id == tenant, OfficeTicket.category == t.category, OfficeTicket.cost_paise > 0,
                    OfficeTicket.id != t.id)).all()]
                checks = [f"{t.number}: {t.title}" + (f" ({t.asset})" if t.asset else "")]
                if prev:
                    avg = sum(prev) / len(prev)
                    checks.append(f"Is tarah ki repair pehle average {_rs(int(avg))} mein hui ({len(prev)} baar)"
                                  + (f"; yeh {round((p / avg - 1) * 100)}% zyada" if p > avg * 1.15 else ""))
                r = _new_spend(s, tenant, "repair", f"Repair {t.number}: {t.title}", p, t.vendor_id, ref_id=t.id, checks=checks, conv=conv)
                card = _spend_view(s, r)
        view = _ticket_view(s, t, tenant)
    if card:
        _publish(tenant, "office_spend", card, conv)
    _publish(tenant, "office", {"what": "ticket", "ticket": view}, conv)
    out = {"ticket": view, "say": f"{view['number']}: {view['status']}."}
    if card:
        out["spend"] = card
        out["say"] += f" Kharcha {card['amount']} ka card aapki Haan ke liye."
    return out


def tickets(tenant: str, status: str = "open") -> list[dict[str, Any]]:
    with session() as s:
        q = select(OfficeTicket).where(OfficeTicket.tenant_id == tenant)
        if status == "open":
            q = q.where(OfficeTicket.status.in_(TICKET_OPEN))
        elif status and status != "all":
            q = q.where(OfficeTicket.status == status)
        rows = s.scalars(q.order_by(OfficeTicket.created_at.desc()).limit(100)).all()
        out = [_ticket_view(s, t, tenant) for t in rows]
    rank = {p: i for i, p in enumerate(PRIORITIES)}
    return sorted(out, key=lambda x: (x["status"] not in TICKET_OPEN, not x["late"], rank.get(x["priority"], 9)))


# ---------------------------------------------------------------- renewals & compliance calendar
def _renewal_view(s, r: OfficeRenewal) -> dict[str, Any]:
    v = s.get(OfficeVendor, r.vendor_id) if r.vendor_id else None
    left = _days_left(r.tenant_id, r.due_on)
    return {"id": r.id, "kind": r.kind, "kind_label": RENEWAL_KINDS.get(r.kind, r.kind), "name": r.name, "due_on": r.due_on,
            "due_nice": _nice(r.due_on), "days_left": left, "overdue": left is not None and left < 0,
            "every_months": r.every_months, "amount": _rs(r.amount_paise) if r.amount_paise else "",
            "amount_rupees": r.amount_paise / 100 if r.amount_paise else None, "vendor": _vendor_view(v), "notes": r.notes,
            "files": _j(r.files, []), "status": r.status, "history": _j(r.history, [])[-6:],
            "notice_by": r.notice_by or "", "notice_left": _days_left(r.tenant_id, r.notice_by) if r.notice_by else None}


def _find_renewal(s, tenant: str, ref: str) -> OfficeRenewal:
    ref = str(ref or "").strip()
    r = s.get(OfficeRenewal, ref)
    if r is not None and r.tenant_id == tenant:
        return r
    for r in s.scalars(select(OfficeRenewal).where(OfficeRenewal.tenant_id == tenant).order_by(OfficeRenewal.due_on)).all():
        if ref and _match(r.name, ref):
            return r
    raise OfficeError(f"Renewal '{ref}' nahi mila.")


def _kind_of(name: str, kind: str) -> str:
    if kind in RENEWAL_KINDS:
        return kind
    n = name.lower()
    for k, words in (("amc", ("amc", "maintenance contract", "service contract")), ("insurance", ("insurance", "bima", "policy")),
                     ("rent", ("rent", "kiraya", "lease")), ("domain", ("domain", "hosting", "website")),
                     ("subscription", ("software", "subscription", "licence key", "tally", "zoho", "office 365", "antivirus")),
                     ("vehicle", ("puc", "vehicle", "gaadi", "car", "fitness")), ("certificate", ("noc", "fire", "certificate")),
                     ("tax", ("tax", "gst", "tds", "professional tax", "property tax", "filing")),
                     ("bill", ("bill", "electricity", "bijli", "internet", "broadband", "phone")),
                     ("licence", ("licence", "license", "registration", "shop act", "gumasta", "trade", "fssai"))):
        if any(w in n for w in words):
            return k
    return "other"


def renewal_add(tenant: str, name: str, due_on: str, kind: str = "", every_months: Any = None, amount: Any = None,
                vendor: str = "", notes: str = "", files: list[str] | None = None, notice_by: str = "") -> dict[str, Any]:
    name = _tidy(name, 160)
    if not name:
        raise OfficeError("Kis cheez ka renewal? (naam)")
    due = _date(tenant, due_on, "due_on")
    if not due:
        raise OfficeError("Renewal ki tareekh chahiye.")
    k = _kind_of(name, kind)
    with session() as s:
        r = s.scalars(select(OfficeRenewal).where(OfficeRenewal.tenant_id == tenant, OfficeRenewal.name == name)).first()
        if r is None:
            r = OfficeRenewal(tenant_id=tenant, name=name, kind=k, history="[]")
            s.add(r)
        r.due_on = due
        r.every_months = int(every_months) if every_months not in (None, "") else USUAL_EVERY.get(k, 12)
        if amount not in (None, ""):
            r.amount_paise = _paise(amount)
        if vendor:
            v = _find_vendor(s, tenant, vendor) or OfficeVendor(tenant_id=tenant, name=_tidy(vendor, 120))
            if not v.id:
                s.add(v)
                s.flush()
            r.vendor_id = v.id
        if notes:
            r.notes = _tidy(notes, 600)
        if notice_by:
            r.notice_by = _date(tenant, notice_by, "notice_by")
        if files:
            r.files = json.dumps(list(dict.fromkeys(_j(r.files, []) + list(files)))[:10])
        r.status = "active"
        s.flush()
        view = _renewal_view(s, r)
    left = view["days_left"]
    say = f"{name}: {view['due_nice']} ko renew ({left} din baaki)." if left is not None and left >= 0 else f"{name}: tareekh nikal chuki hai ({-left} din pehle)!"
    say += f" Har {view['every_months']} mahine." if view["every_months"] else ""
    return {"renewal": view, "say": say}


def renewal_done(tenant: str, renewal: str, paid: Any = None, next_due: str = "", note: str = "") -> dict[str, Any]:
    with session() as s:
        r = _find_renewal(s, tenant, renewal)
        p = _paise(paid) if paid not in (None, "") else 0
        hist = _j(r.history, [])
        warn = ""
        last_paid = next((h.get("paid", 0) for h in reversed(hist) if h.get("paid")), 0)
        if p and last_paid and p > last_paid * 1.10:
            warn = f"Is baar {_rs(p)}, pichhli baar {_rs(last_paid)} ({round((p / last_paid - 1) * 100)}% zyada)."
        hist.append({"done_on": today(tenant).isoformat(), "due_on": r.due_on, "paid": p, "note": _tidy(note, 200)})
        r.history = json.dumps(hist[-20:], ensure_ascii=False)
        if p:
            r.amount_paise = p
        if next_due:
            r.due_on = _date(tenant, next_due, "next_due")
        elif r.every_months:
            base = date.fromisoformat(r.due_on) if r.due_on else today(tenant)
            r.due_on = _add_months(base, r.every_months).isoformat()
        else:
            r.status = "stopped"
        r.reminded = ""
        r.notice_by = None
        view = _renewal_view(s, r)
    say = f"{view['name']} renew ho gaya." + (f" Agli baar {view['due_nice']}." if view["status"] == "active" else "")
    return {"renewal": view, "warn": warn, "say": (say + (" " + warn if warn else ""))}


def renewal_pay(tenant: str, renewal: str, amount: Any = None, conv: str = "") -> dict[str, Any]:
    with session() as s:
        r = _find_renewal(s, tenant, renewal)
        p = _paise(amount) if amount not in (None, "") else r.amount_paise
        hist = _j(r.history, [])
        last_paid = next((h.get("paid", 0) for h in reversed(hist) if h.get("paid")), 0)
        checks = [f"{RENEWAL_KINDS.get(r.kind, r.kind)} · due {_nice(r.due_on)}"]
        if last_paid:
            checks.append(f"Pichhli baar {_rs(last_paid)}" + (f"; is baar {round((p / last_paid - 1) * 100)}% zyada" if p > last_paid * 1.10 else ""))
        sp = _new_spend(s, tenant, "renewal", f"Renewal: {r.name}", p, r.vendor_id, ref_id=r.id, checks=checks, conv=conv)
        view = _spend_view(s, sp)
    _publish(tenant, "office_spend", view, conv)
    return {"spend": view, "say": f"{r.name} ka bhugtan card ({view['amount'] or 'rakam batayiye'}) aapki Haan ke liye. Paise aap apne app se dengi."}


def renewals(tenant: str, within_days: int | None = None, status: str = "active") -> list[dict[str, Any]]:
    with session() as s:
        q = select(OfficeRenewal).where(OfficeRenewal.tenant_id == tenant)
        if status and status != "all":
            q = q.where(OfficeRenewal.status == status)
        out = [_renewal_view(s, r) for r in s.scalars(q.order_by(OfficeRenewal.due_on)).all()]
    if within_days is not None:
        out = [r for r in out if r["days_left"] is not None and r["days_left"] <= within_days]
    return out


# ---------------------------------------------------------------- team deadlines
def _deadline_view(s, d: OfficeDeadline) -> dict[str, Any]:
    left = _days_left(d.tenant_id, d.due_on)
    who = _person(s, d.tenant_id, d.owner) if d.owner else {"name": "", "phone": ""}
    return {"id": d.id, "title": d.title, "owner": d.owner, "owner_phone": who.get("phone", ""), "due_on": d.due_on,
            "due_nice": _nice(d.due_on), "days_left": left, "late": d.status == "open" and left is not None and left < 0,
            "status": d.status, "note": d.note, "done_on": d.done_on}


def deadline_add(tenant: str, title: str, due_on: str, owner: str = "", note: str = "") -> dict[str, Any]:
    title = _tidy(title, 200)
    if not title:
        raise OfficeError("Kaam kya hai?")
    due = _date(tenant, due_on, "due_on")
    if not due:
        raise OfficeError("Kab tak? (due_on)")
    with session() as s:
        d = OfficeDeadline(tenant_id=tenant, title=title, owner=_tidy(owner, 80), due_on=due, note=_tidy(note, 400))
        s.add(d)
        s.flush()
        # earlier work: how this person usually does
        hist = s.scalars(select(OfficeDeadline).where(OfficeDeadline.tenant_id == tenant, OfficeDeadline.owner == d.owner,
                                                      OfficeDeadline.status == "done")).all() if d.owner else []
        late = sum(1 for h in hist if h.done_on and h.done_on > h.due_on)
        view = _deadline_view(s, d)
    tip = f" {d.owner} ne pichhle {len(hist)} mein se {late} der se diye; ek din pehle yaad dilaungi." if hist and late else ""
    return {"deadline": view, "say": f"Likh liya: {title}" + (f" ({owner})" if owner else "") + f", {view['due_nice']} tak.{tip}"}


def _find_deadline(s, tenant: str, ref: str) -> OfficeDeadline:
    ref = str(ref or "").strip()
    d = s.get(OfficeDeadline, ref)
    if d is not None and d.tenant_id == tenant:
        return d
    for d in s.scalars(select(OfficeDeadline).where(OfficeDeadline.tenant_id == tenant, OfficeDeadline.status == "open")
                       .order_by(OfficeDeadline.due_on)).all():
        if ref and (_match(d.title, ref) or _match(d.owner, ref)):
            return d
    raise OfficeError(f"Deadline '{ref}' nahi mili.")


def deadline_done(tenant: str, deadline: str, dropped: bool = False) -> dict[str, Any]:
    with session() as s:
        d = _find_deadline(s, tenant, deadline)
        d.status = "dropped" if dropped else "done"
        d.done_on = today(tenant).isoformat()
        view = _deadline_view(s, d)
    on_time = view["done_on"] <= view["due_on"]
    return {"deadline": view, "say": f"{view['title']}: " + ("chhod diya." if dropped else ("samay par ho gaya." if on_time else "ho gaya (der se)."))}


def deadlines(tenant: str, status: str = "open", owner: str = "") -> list[dict[str, Any]]:
    with session() as s:
        q = select(OfficeDeadline).where(OfficeDeadline.tenant_id == tenant)
        if status and status != "all":
            q = q.where(OfficeDeadline.status == status)
        rows = s.scalars(q.order_by(OfficeDeadline.due_on)).all()
        return [_deadline_view(s, d) for d in rows if not owner or _match(d.owner, owner)]


def nudge(tenant: str, deadline: str = "", owner: str = "", conv: str = "") -> dict[str, Any]:
    """A reminder message DRAFT for a team member (wa.me / sms link). She sends it; Hoola never does."""
    with session() as s:
        st = _settings_row(s, tenant)
        rows = [_find_deadline(s, tenant, deadline)] if deadline else [
            d for d in s.scalars(select(OfficeDeadline).where(OfficeDeadline.tenant_id == tenant, OfficeDeadline.status == "open")).all()
            if (not owner or _match(d.owner, owner)) and (_days_left(tenant, d.due_on) or 0) <= 1]
        if not rows:
            return {"cards": [], "say": "Abhi yaad dilane layak koi deadline nahi."}
        by: dict[str, list[OfficeDeadline]] = {}
        for d in rows:
            by.setdefault(d.owner or "", []).append(d)
        cards = []
        for who, ds in by.items():
            p = _person(s, tenant, who) if who else {"name": "", "phone": ""}
            parts = []
            for d in ds:
                left = _days_left(tenant, d.due_on)
                when = "aaj" if left == 0 else ("kal" if left == 1 else (f"{-left} din pehle tha" if left is not None and left < 0 else _nice(d.due_on)))
                parts.append(f"{d.title} ({when})")
            text = (f"Namaste {who or ''} ji, yaad dila rahi hoon: " + "; ".join(parts) + ". Koi madad chahiye to bataiye."
                    + (f" - {st.office_name}" if st.office_name else "")).replace("  ", " ")
            card = {"id": "n" + ds[0].id, "who": who, "phone": p.get("phone", ""), "text": text,
                    "deadlines": [d.id for d in ds]}
            if p.get("phone"):
                card["wa_link"] = f"https://wa.me/91{p['phone']}?text={quote(text)}"
                card["sms_link"] = f"sms:+91{p['phone']}?body={quote(text)}"
            cards.append(card)
    for c in cards:
        _publish(tenant, "office_nudge", c, conv)
    return {"cards": cards, "say": f"{len(cards)} yaad-dihani ke draft card par: aap tap karengi tabhi jayenge."}


# ---------------------------------------------------------------- petty cash
def petty_add(tenant: str, amount: Any, what: str, kind: str = "out", by: str = "", on: str = "", bill: str = "") -> dict[str, Any]:
    p = abs(_paise(amount))
    if not p:
        raise OfficeError("Rakam chahiye.")
    with session() as s:
        e = OfficePetty(tenant_id=tenant, on=_date(tenant, on) or today(tenant).isoformat(), what=_tidy(what, 200) or "kharcha",
                        amount_paise=p if kind == "in" else -p, by=_tidy(by, 80), bill=_tidy(bill, 60))
        s.add(e)
        s.flush()
    book = petty(tenant)
    return {"entry": {"id": e.id, "what": e.what, "amount": _rs(p), "kind": kind}, "balance": book["balance"],
            "say": f"Likh liya: {'aaya' if kind == 'in' else 'kharcha'} {_rs(p)} ({what}). Petty cash mein {book['balance']} bacha."
                   + ("" if bill or kind == "in" else " Bill ki photo ho to bhej dijiye.")}


def petty(tenant: str, days: int = 31) -> dict[str, Any]:
    with session() as s:
        rows = s.scalars(select(OfficePetty).where(OfficePetty.tenant_id == tenant).order_by(OfficePetty.on.desc(), OfficePetty.created_at.desc())).all()
        bal = sum(r.amount_paise for r in rows)
        since = (today(tenant) - timedelta(days=days)).isoformat()
        recent = [r for r in rows if r.on >= since]
        spent = -sum(r.amount_paise for r in recent if r.amount_paise < 0)
        no_bill = sum(1 for r in recent if r.amount_paise < 0 and not r.bill)
        return {"balance": _rs(bal), "balance_rupees": bal / 100, "spent": _rs(spent), "days": days, "no_bill": no_bill,
                "entries": [{"id": r.id, "on": r.on, "what": r.what, "amount": _rs(abs(r.amount_paise)),
                             "kind": "in" if r.amount_paise > 0 else "out", "by": r.by, "bill": r.bill} for r in recent[:80]]}


# ---------------------------------------------------------------- India starter list (editable defaults, never hard rules)
STARTERS = [
    {"name": "Shop & Establishment registration / intimation", "kind": "licence", "every_months": 0,
     "tip": "Maharashtra 2017 Act: under 10 workers = one-time intimation (Form F); 10+ = registration up to 10 years. Other states differ."},
    {"name": "Trade licence (municipal)", "kind": "licence", "every_months": 12, "tip": "Usually yearly; city rules differ."},
    {"name": "Fire NOC / Form B certificate", "kind": "certificate", "every_months": 6,
     "tip": "Maharashtra: Form B from a licensed agency every January and July; other states 1-5 years."},
    {"name": "Fire extinguisher refill / service", "kind": "amc", "every_months": 12, "tip": "IS 2190: monthly look, yearly service, refill after any use."},
    {"name": "AC AMC", "kind": "amc", "every_months": 12, "tip": "Usually yearly with quarterly service visits."},
    {"name": "UPS / inverter AMC", "kind": "amc", "every_months": 12, "tip": ""},
    {"name": "RO / water purifier service", "kind": "amc", "every_months": 12, "tip": "Filter change every 6-12 months."},
    {"name": "Pest control", "kind": "amc", "every_months": 12, "tip": "Contract yearly, visits monthly or quarterly."},
    {"name": "CCTV AMC", "kind": "amc", "every_months": 12, "tip": ""},
    {"name": "Office rent agreement (leave & licence)", "kind": "rent", "every_months": 11,
     "tip": "Maharashtra: registration compulsory; 11-month terms are common, with an escalation each renewal."},
    {"name": "Office insurance (fire / burglary)", "kind": "insurance", "every_months": 12, "tip": ""},
    {"name": "Professional Tax (PTEC)", "kind": "tax", "every_months": 12, "tip": "Maharashtra: firm's own PT once a year; check the date with your CA."},
    {"name": "Domain + email (Google Workspace / Microsoft 365)", "kind": "domain", "every_months": 12, "tip": ""},
    {"name": "Tally / accounting software", "kind": "subscription", "every_months": 12, "tip": ""},
    {"name": "Antivirus", "kind": "subscription", "every_months": 12, "tip": ""},
    {"name": "Vehicle insurance", "kind": "vehicle", "every_months": 12, "tip": ""},
    {"name": "Vehicle PUC", "kind": "vehicle", "every_months": 12, "tip": "BS-VI yearly, older vehicles every 6 months."},
]


def starters(tenant: str) -> list[dict[str, Any]]:
    have = {r["name"].lower() for r in renewals(tenant, status="all")}
    return [x | {"added": x["name"].lower() in have} for x in STARTERS]


# ---------------------------------------------------------------- vendor bills: MSME 45 days, GST 180 days, duplicates
MSME_DAYS = 45          # Income Tax s.43B(h): pay a micro / small (Udyam) supplier within 45 days or lose the deduction
ITC_DAYS = 180          # CGST Rule 37: unpaid after 180 days of the invoice -> input tax credit to be reversed


def _bill_view(s, b: OfficeBill) -> dict[str, Any]:
    v = s.get(OfficeVendor, b.vendor_id) if b.vendor_id else None
    out = {"id": b.id, "vendor": _vendor_view(v), "number": b.number, "bill_date": b.bill_date, "due_on": b.due_on,
           "due_nice": _nice(b.due_on) if b.due_on else "", "amount": _rs(b.amount_paise), "amount_rupees": b.amount_paise / 100,
           "gst": _rs(b.gst_paise) if b.gst_paise else "", "what": b.what, "file_id": b.file_id, "paid_on": b.paid_on,
           "paid": bool(b.paid_on), "flags": []}
    if not b.paid_on:
        left = _days_left(b.tenant_id, b.due_on) if b.due_on else None
        out["days_left"] = left
        if left is not None and left < 0:
            out["flags"].append(f"Due date {-left} din pehle nikal gayi")
        try:
            age = (today(b.tenant_id) - date.fromisoformat(b.bill_date)).days if b.bill_date else None
        except ValueError:
            age = None
        out["age_days"] = age
        if age is not None and v is not None and v.udyam and age >= MSME_DAYS - 10:
            out["flags"].append(f"MSME supplier: {MSME_DAYS} din mein dena zaroori (abhi {age} din); der hui to kharcha tax mein nahi ghatega")
        if age is not None and b.gst_paise and age >= ITC_DAYS - 30:
            out["flags"].append(f"GST: {ITC_DAYS} din tak bhugtan nahi hua to ITC wapas karna padega (abhi {age} din)")
    return out


def bill_add(tenant: str, vendor: str, amount: Any, number: str = "", bill_date: str = "", due_on: str = "", gst: Any = None,
             what: str = "", file_id: str = "") -> dict[str, Any]:
    p = _paise(amount)
    if not p:
        raise OfficeError("Bill ki rakam chahiye.")
    with session() as s:
        v = _find_vendor(s, tenant, vendor) if vendor else None
        if vendor and v is None:
            v = OfficeVendor(tenant_id=tenant, name=_tidy(vendor, 120))
            s.add(v)
            s.flush()
        bd = _date(tenant, bill_date, "bill_date") or today(tenant).isoformat()
        dup = None
        for o in s.scalars(select(OfficeBill).where(OfficeBill.tenant_id == tenant, OfficeBill.vendor_id == (v.id if v else ""))).all():
            if (number and o.number and o.number.lower() == number.strip().lower()) or (o.amount_paise == p and o.bill_date == bd):
                dup = o
                break
        if dup is not None:
            return {"bill": _bill_view(s, dup), "duplicate": True,
                    "say": f"Yeh bill pehle se darj hai ({dup.number or dup.bill_date}, {_rs(dup.amount_paise)}). Dobara nahi joda."}
        b = OfficeBill(tenant_id=tenant, vendor_id=v.id if v else "", number=_tidy(number, 60), bill_date=bd,
                       due_on=_date(tenant, due_on, "due_on"), amount_paise=p,
                       gst_paise=_paise(gst) if gst not in (None, "") else 0, what=_tidy(what, 200), file_id=_tidy(file_id, 60))
        s.add(b)
        s.flush()
        view = _bill_view(s, b)
    return {"bill": view, "say": f"Bill darj: {view['vendor']['name'] if view['vendor'] else ''} {view['amount']}"
                                 + (f", due {view['due_nice']}" if view["due_on"] else "") + ". Bhugtan aap apne app se karengi."}


def bill_paid(tenant: str, bill: str, on: str = "") -> dict[str, Any]:
    with session() as s:
        b = s.get(OfficeBill, bill)
        if b is None or b.tenant_id != tenant:
            b = next((x for x in s.scalars(select(OfficeBill).where(OfficeBill.tenant_id == tenant, OfficeBill.paid_on == "")).all()
                      if bill and (x.number.lower() == bill.lower() or _match(x.what, bill))), None)
        if b is None:
            raise OfficeError("Yeh bill nahi mila.")
        b.paid_on = _date(tenant, on) or today(tenant).isoformat()
        view = _bill_view(s, b)
    return {"bill": view, "say": f"Bill {view['number'] or view['amount']} paid likh diya."}


def bills(tenant: str, unpaid: bool = True) -> list[dict[str, Any]]:
    with session() as s:
        q = select(OfficeBill).where(OfficeBill.tenant_id == tenant)
        if unpaid:
            q = q.where(OfficeBill.paid_on == "")
        out = [_bill_view(s, b) for b in s.scalars(q.order_by(OfficeBill.bill_date)).all()]
    return sorted(out, key=lambda b: (not b["flags"], b.get("days_left") if b.get("days_left") is not None else 999))


# ---------------------------------------------------------------- the morning list
def day(tenant: str) -> dict[str, Any]:
    t = today(tenant)
    with session() as s:
        st = _settings_row(s, tenant)
        windows = _j(st.windows, DEFAULT_WINDOWS)
    rn = renewals(tenant)
    due_ren = [r for r in rn if r["days_left"] is not None and (r["days_left"] < 0 or r["days_left"] <= max((windows or [0]) + [60]))]
    low = items(tenant, low_only=True)
    tk = tickets(tenant, "open")
    late_t = [x for x in tk if x["late"]]
    dl = deadlines(tenant, "open")
    dl_now = [d for d in dl if d["days_left"] is not None and d["days_left"] <= 1]
    pend = spends(tenant, "pending")
    bl = [b for b in bills(tenant) if b["flags"] or (b.get("days_left") is not None and b["days_left"] <= 3)]
    notice = [r for r in rn if r.get("notice_left") is not None and 0 <= r["notice_left"] <= 7]
    lines = []
    if due_ren:
        lines.append("Renewal: " + "; ".join(f"{r['name']} " + (f"{-r['days_left']} din se baaki!" if r["overdue"] else
                                                                    ("aaj" if r["days_left"] == 0 else f"{r['days_left']} din mein"))
                                             for r in due_ren[:6]))
    if low:
        lines.append("Kam saamaan: " + ", ".join(f"{i['name']} ({i['qty']:g} {i['unit']})" for i in low[:8]))
    if late_t:
        lines.append("Der wali repair: " + ", ".join(f"{x['number']} {x['title']}" for x in late_t[:6]))
    elif tk:
        lines.append(f"Khuli repair: {len(tk)}")
    if dl_now:
        lines.append("Deadline: " + "; ".join(f"{d['title']}" + (f" ({d['owner']})" if d["owner"] else "") + " - "
                                             + ("aaj" if d["days_left"] == 0 else ("kal" if d["days_left"] == 1 else f"{-d['days_left']} din der"))
                                             for d in dl_now[:8]))
    if notice:
        lines.append("Mana karne ki aakhri tareekh: " + "; ".join(f"{r['name']} ({r['notice_left']} din)" for r in notice[:4]))
    if bl:
        lines.append("Bill: " + "; ".join(f"{(b['vendor'] or {}).get('name', '')} {b['amount']}"
                                          + (f" - {b['flags'][0]}" if b["flags"] else f" - {b['days_left']} din mein due") for b in bl[:6]))
    if pend:
        lines.append(f"Aapki Haan baaki: {len(pend)} kharcha card")
    text = (f"Office ka din, {_nice(t.isoformat())}:\n- " + "\n- ".join(lines)) if lines else f"Office ka din, {_nice(t.isoformat())}: sab theek, koi zaroori kaam nahi."
    return {"date": t.isoformat(), "nice": _nice(t.isoformat()), "text": text, "renewals": due_ren, "low": low, "tickets": tk,
            "late_tickets": late_t, "deadlines": dl_now, "pending_spends": pend, "open_deadlines": len(dl), "bills": bl,
            "notice": notice}


def due_mornings() -> list[str]:
    out = []
    with session() as s:
        for r in s.scalars(select(OfficeSettings).where(OfficeSettings.enabled.is_(True))).all():
            local = datetime.now(_tz(r.tenant_id))
            d = local.date().isoformat()
            try:
                hh, mm = [int(x) for x in (r.morning_time or "09:30").split(":")]
            except ValueError:
                hh, mm = 9, 30
            late = (local.hour * 60 + local.minute) - (hh * 60 + mm)
            if r.last_morning != d and 0 <= late <= 180:
                r.last_morning = d
                out.append(r.tenant_id)
    return out


def send_morning(tenant: str) -> dict[str, Any]:
    from ..events import notify
    from ..net.service import home_conv
    d = day(tenant)
    windows = set(settings(tenant)["windows"]) | {60}
    # renewal reminders: once per window (60 / 30 / 15 / 7 / 1 / 0 days), every day once overdue or past the notice date
    fresh = []
    with session() as s:
        for rv in d["renewals"]:
            r = s.get(OfficeRenewal, rv["id"])
            left = rv["days_left"]
            if r is None or left is None:
                continue
            w = "over" + today(tenant).isoformat() if left < 0 else min((w for w in windows if w >= left), default=left)
            tag = f"{r.due_on}:{w}"
            if r.reminded != tag:
                r.reminded = tag
                fresh.append(rv)
    d["renewals"] = fresh
    lines = [ln for ln in d["text"].split("\n- ")[1:] if not ln.startswith("Renewal:")]
    if fresh:
        lines.insert(0, "Renewal: " + "; ".join(f"{r['name']} " + (f"{-r['days_left']} din se baaki!" if r["overdue"] else
                                                                    ("aaj" if r["days_left"] == 0 else f"{r['days_left']} din mein"))
                                                 for r in fresh[:6]))
    d["text"] = (f"Office ka din, {d['nice']}:\n- " + "\n- ".join(lines)) if lines else d["text"].split("\n- ")[0]
    has_work = d["renewals"] or d["low"] or d["late_tickets"] or d["deadlines"] or d["pending_spends"] or d["bills"] or d["notice"]
    if not has_work:
        return d
    conv = home_conv(tenant)
    try:
        notify(conv, d["text"])
    except Exception:
        pass
    _publish(tenant, "office_day", {"date": d["date"], "nice": d["nice"], "text": d["text"], "renewals": len(d["renewals"]),
                                    "low": len(d["low"]), "late_tickets": len(d["late_tickets"]), "deadlines": len(d["deadlines"]),
                                    "pending_spends": len(d["pending_spends"])}, conv)
    if d["deadlines"]:
        nudge(tenant, conv=conv)
    return d


# ---------------------------------------------------------------- the weekly office note
def weekly_note(tenant: str, make_file: bool = False, conv: str = "") -> dict[str, Any]:
    t = today(tenant)
    since = t - timedelta(days=7)
    since_dt = datetime(since.year, since.month, since.day, tzinfo=_tz(tenant)).astimezone(timezone.utc)
    with session() as s:
        st = _settings_row(s, tenant)
        tks = s.scalars(select(OfficeTicket).where(OfficeTicket.tenant_id == tenant)).all()
        opened = [x for x in tks if _utc(x.created_at) >= since_dt]
        closed = [x for x in tks if x.done_at and _utc(x.done_at) >= since_dt]
        on_time = [x for x in closed if x.due_at is None or _utc(x.done_at) <= _utc(x.due_at)]
        still = [x for x in tks if x.status in TICKET_OPEN]
        used: dict[str, float] = {}
        bought: dict[str, float] = {}
        for it in s.scalars(select(OfficeItem).where(OfficeItem.tenant_id == tenant)).all():
            for e in _j(it.log, []):
                try:
                    at = _utc(datetime.fromisoformat(e["at"]))
                except (KeyError, ValueError):
                    continue
                if at < since_dt:
                    continue
                if e.get("why") == "used":
                    used[f"{it.name} ({it.unit})"] = used.get(f"{it.name} ({it.unit})", 0) - float(e.get("d", 0))
                if e.get("why") == "received":
                    bought[f"{it.name} ({it.unit})"] = bought.get(f"{it.name} ({it.unit})", 0) + float(e.get("d", 0))
        sp = [r for r in s.scalars(select(OfficeSpend).where(OfficeSpend.tenant_id == tenant)).all()
              if r.decided_at and _utc(r.decided_at) >= since_dt]
        approved = sum(r.amount_paise for r in sp if r.status == "approved")
        pend = s.scalars(select(OfficeSpend).where(OfficeSpend.tenant_id == tenant, OfficeSpend.status == "pending")).all()
        pet = [r for r in s.scalars(select(OfficePetty).where(OfficePetty.tenant_id == tenant)).all() if r.on >= since.isoformat()]
        pet_spent = -sum(r.amount_paise for r in pet if r.amount_paise < 0)
        ren_done = []
        for r in s.scalars(select(OfficeRenewal).where(OfficeRenewal.tenant_id == tenant)).all():
            for h in _j(r.history, []):
                if h.get("done_on", "") >= since.isoformat():
                    ren_done.append(r.name)
        name = st.office_name or "Office"
    coming = [r for r in renewals(tenant) if r["days_left"] is not None and r["days_left"] <= 30]
    dls = deadlines(tenant, "all")
    met = [d for d in dls if d["status"] == "done" and d["done_on"] >= since.isoformat()]
    met_ok = [d for d in met if d["done_on"] <= d["due_on"]]
    missed = [d for d in dls if d["status"] == "open" and d["late"]]
    nxt = [d for d in dls if d["status"] == "open" and d["days_left"] is not None and 0 <= d["days_left"] <= 7]
    low = items(tenant, low_only=True)
    L = [f"# {name}: hafte ka office note", f"{_nice(since.isoformat())} se {_nice(t.isoformat())}", "",
         "## Repair aur maintenance",
         f"- Naye: {len(opened)} · Theek hue: {len(closed)} (samay par {len(on_time)}) · Abhi khule: {len(still)}"]
    L += [f"- {x.number} {x.title} ({PRIORITY_LABEL.get(x.priority, x.priority)})" for x in still[:8]]
    L += ["", "## Saamaan"]
    L += [f"- Use hua: {k} {v:g}" for k, v in sorted(used.items(), key=lambda kv: -kv[1])[:8]] or ["- Is hafte koi use darj nahi"]
    L += [f"- Aaya: {k} {v:g}" for k, v in bought.items()][:8]
    if low:
        L.append("- Kam hai: " + ", ".join(f"{i['name']} ({i['qty']:g})" for i in low[:8]))
    L += ["", "## Kharcha",
          f"- Manzoor: {_rs(approved)} ({sum(1 for r in sp if r.status == 'approved')} card) · Mana: {sum(1 for r in sp if r.status == 'rejected')}",
          f"- Petty cash se: {_rs(pet_spent)} · Haan baaki: {len(pend)} card"]
    L += ["", "## Renewal"]
    L += [f"- Renew hua: {n}" for n in ren_done] or ["- Is hafte koi renew nahi hua"]
    L += [f"- Aane wale: {r['name']} - {r['due_nice']}" + (f" ({r['amount']})" if r["amount"] else "") for r in coming[:8]]
    L += ["", "## Team deadlines",
          f"- Puri hui: {len(met)} (samay par {len(met_ok)}) · Der wali abhi khuli: {len(missed)}"]
    L += [f"- Der: {d['title']} ({d['owner'] or '-'}) - {d['due_nice']}" for d in missed[:8]]
    L += [f"- Agle hafte: {d['title']} ({d['owner'] or '-'}) - {d['due_nice']}" for d in nxt[:10]]
    text = "\n".join(L)
    out = {"text": text, "week_from": since.isoformat(), "week_to": t.isoformat(),
           "numbers": {"tickets_opened": len(opened), "tickets_closed": len(closed), "on_time": len(on_time), "open": len(still),
                       "approved": _rs(approved), "petty": _rs(pet_spent), "renewals_done": len(ren_done),
                       "renewals_coming": len(coming), "deadlines_met": len(met), "deadlines_missed": len(missed)}}
    if make_file:
        try:
            from .. import chatfiles
            from ..officegen import make_docx
            f = chatfiles.store(tenant, f"office_note_{t.isoformat()}.docx", make_docx(f"{name}: weekly office note", text),
                                "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            out["file"] = {k: f.get(k) for k in ("file_id", "name", "url", "size") if f.get(k)}
            _publish(tenant, "pc_file", {**f, "source": "office", "title": "Hafte ka office note"}, conv)
        except Exception as e:
            log.warning("office note file failed: %s", e)
        _publish(tenant, "office_note", {"text": text, "numbers": out["numbers"], "file": out.get("file"),
                                         "week_from": out["week_from"], "week_to": out["week_to"]}, conv)
    return out


def due_notes() -> list[str]:
    out = []
    with session() as s:
        for r in s.scalars(select(OfficeSettings).where(OfficeSettings.enabled.is_(True))).all():
            local = datetime.now(_tz(r.tenant_id))
            d = local.date().isoformat()
            if local.weekday() != (r.note_day % 7) or r.last_note == d:
                continue
            try:
                hh, mm = [int(x) for x in (r.note_time or "17:30").split(":")]
            except ValueError:
                hh, mm = 17, 30
            late = (local.hour * 60 + local.minute) - (hh * 60 + mm)
            if 0 <= late <= 240:
                r.last_note = d
                used = s.scalars(select(OfficeItem.id).where(OfficeItem.tenant_id == r.tenant_id).limit(1)).first() or \
                    s.scalars(select(OfficeTicket.id).where(OfficeTicket.tenant_id == r.tenant_id).limit(1)).first() or \
                    s.scalars(select(OfficeRenewal.id).where(OfficeRenewal.tenant_id == r.tenant_id).limit(1)).first() or \
                    s.scalars(select(OfficeDeadline.id).where(OfficeDeadline.tenant_id == r.tenant_id).limit(1)).first()
                if used:
                    out.append(r.tenant_id)
    return out


def send_note(tenant: str) -> dict[str, Any]:
    from ..events import notify
    from ..net.service import home_conv
    conv = home_conv(tenant)
    n = weekly_note(tenant, make_file=True, conv=conv)
    try:
        notify(conv, "Hafte ka office note taiyaar hai (Word file card par). Kisi ko bhejna ho to bataiye; main bina aapki haan ke nahi bhejungi.")
    except Exception:
        pass
    return n


# ---------------------------------------------------------------- for the agent
def overview(tenant: str) -> dict[str, Any]:
    d = day(tenant)
    return {"today": d["text"], "pending_spends": d["pending_spends"], "bills": d["bills"], "low": d["low"][:10], "open_tickets": d["tickets"][:10],
            "renewals_soon": renewals(tenant, 45)[:10], "deadlines": deadlines(tenant, "open")[:12], "petty": petty(tenant)["balance"],
            "settings": settings(tenant)}


def prompt_block(tenant: str) -> str:
    with session() as s:
        r = s.get(OfficeSettings, tenant)
        if r is None or not r.enabled:
            return ""
        n_items = len(s.scalars(select(OfficeItem.id).where(OfficeItem.tenant_id == tenant)).all())
        n_t = len(s.scalars(select(OfficeTicket.id).where(OfficeTicket.tenant_id == tenant, OfficeTicket.status.in_(TICKET_OPEN))).all())
        n_r = len(s.scalars(select(OfficeRenewal.id).where(OfficeRenewal.tenant_id == tenant, OfficeRenewal.status == "active")).all())
    if not (n_items or n_t or n_r):
        return ""
    return (f"DAFTAR: she uses Hoola as office manager ({n_items} stock items, {n_t} open repairs, {n_r} renewals tracked); "
            "use office / office_dekho for supplies, repairs, renewals, team deadlines, petty cash and the weekly note.")
