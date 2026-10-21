"""v0.82 Darzi Sahayak: Hoola works as a tailor's / boutique's coworker.

  1. Gets the job: she tells Hoola in chat or on a call, or forwards a bill / photo of the order book / customer's
     message; the model turns it into `new_order` (customer, garments, measurements, trial and delivery dates, price,
     advance).
  2. Keeps every customer's measurements: per customer, per person (her daughter...), per garment, every version kept;
     a new measurement is compared with the last one (big changes are pointed out).
  3. Tracks delivery dates and trials, CHECKED against her rules (pieces per day, minimum days per garment, closed day,
     rush charge, her own written rules) and earlier work (how long this garment really took before, this customer's
     last price / style, old measurements). Morning summary: today's trials and deliveries, late ones, the week's load.
  4. 'Ready for pickup': a card with the message draft (her WhatsApp opens with it; or the official business WhatsApp
     when the customer wrote in the last 24 h) and a PDF job slip. Hoola never sends it by itself: her tap.
  5. Waits for her Haan on a new price: any price not in her list (or different from it) becomes a quote card; Hoola
     prepares it (her list, her earlier orders, rush charge), she decides. Money is never taken: UPI link / cash is hers.
  6. Delivers and learns: delivery closes the order with a log (what happened, on time or late, balance); the time each
     garment really takes feeds the next checks, and the chat turn itself is learned as a procedure (v0.64).
"""
from __future__ import annotations

import io
import json
import logging
import re
import statistics
import threading
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import garments as G

log = logging.getLogger("santosh.darzi")
_LOCK = threading.Lock()

STATUSES = ("new", "cutting", "stitching", "trial", "ready", "delivered", "cancelled")
STATUS_LABEL = {"new": "Naya", "cutting": "Cutting", "stitching": "Silai chal rahi", "trial": "Trial / fitting",
                "ready": "Taiyaar", "delivered": "De diya", "cancelled": "Cancel"}
OPEN = ("new", "cutting", "stitching", "trial", "ready")
DAYS = ("Som", "Mangal", "Budh", "Guru", "Shukra", "Shani", "Ravi")
DEFAULT_READY = ("Namaste {name} ji, aapka {items} taiyaar hai. {shop} se kabhi bhi le jaiye. "
                 "{balance_line}Order no. {number}. Dhanyavaad!")


class DarziError(Exception):
    pass


# ---------------------------------------------------------------- tables
class DarziSettings(Base):
    __tablename__ = "darzi_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    shop_name: Mapped[str] = mapped_column(String(120), default="")
    unit: Mapped[str] = mapped_column(String(8), default="inch")             # inch | cm
    pieces_per_day: Mapped[int] = mapped_column(Integer, default=10)         # how many pieces can be finished a day (0 = no limit)
    closed_days: Mapped[str] = mapped_column(String(40), default="[]")       # [6] = Sunday closed (0 = Monday)
    rush_percent: Mapped[int] = mapped_column(Integer, default=0)            # extra % when faster than the usual days
    min_days: Mapped[str] = mapped_column(Text, default="{}")                # {garment: days} her own minimums
    prices: Mapped[str] = mapped_column(Text, default="{}")                  # {garment: rupees}
    rules: Mapped[str] = mapped_column(Text, default="[]")                   # her own words ["Bridal blouse 15 din se kam nahi"]
    remeasure_months: Mapped[int] = mapped_column(Integer, default=6)
    ready_template: Mapped[str] = mapped_column(Text, default="")
    morning_time: Mapped[str] = mapped_column(String(5), default="09:30")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    seq: Mapped[int] = mapped_column(Integer, default=0)                     # order numbers D-0001...


class DarziCustomer(Base):
    __tablename__ = "darzi_customers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="", index=True)   # digits only
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DarziMeasure(Base):
    __tablename__ = "darzi_measures"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    customer_id: Mapped[str] = mapped_column(String(40), index=True)
    person: Mapped[str] = mapped_column(String(60), default="")              # '' = the customer; else 'beti', 'Riya'...
    garment: Mapped[str] = mapped_column(String(30), default="other")
    values: Mapped[str] = mapped_column(Text, default="{}")
    unit: Mapped[str] = mapped_column(String(8), default="inch")
    note: Mapped[str] = mapped_column(Text, default="")                      # style / fitting notes ("loose fitting", "deep back")
    source: Mapped[str] = mapped_column(String(20), default="chat")          # chat | call | photo | app
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DarziOrder(Base):
    __tablename__ = "darzi_orders"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("do"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    customer_id: Mapped[str] = mapped_column(String(40), index=True)
    items: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(16), default="new")
    received_on: Mapped[str] = mapped_column(String(10), default="")        # local dates YYYY-MM-DD
    trial_on: Mapped[str] = mapped_column(String(10), default="")
    deliver_on: Mapped[str] = mapped_column(String(10), default="")
    rush: Mapped[bool] = mapped_column(Boolean, default=False)
    rush_paise: Mapped[int] = mapped_column(Integer, default=0)
    total_paise: Mapped[int] = mapped_column(Integer, default=0)
    paid_paise: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    photos: Mapped[str] = mapped_column(Text, default="[]")                 # file ids (fabric, design, the order slip)
    log: Mapped[str] = mapped_column(Text, default="[]")
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_on: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class DarziQuote(Base):
    __tablename__ = "darzi_quotes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dq"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    order_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    item: Mapped[int] = mapped_column(Integer, default=0)                   # index in the order's items
    garment: Mapped[str] = mapped_column(String(30), default="other")
    price_paise: Mapped[int] = mapped_column(Integer, default=0)            # what Hoola prepared (0 = she must say)
    list_paise: Mapped[int] = mapped_column(Integer, default=0)             # her list price, if any
    why: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="pending")      # pending | approved | rejected
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
        return int(round(float(str(v).replace(",", "").replace("₹", "").replace("rs", "").replace("Rs", "").strip()) * 100))
    except ValueError:
        raise DarziError(f"'{v}' rupaye ki rakam nahi lagti.")


def _digits(p: str) -> str:
    d = re.sub(r"\D", "", str(p or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d[-10:] if len(d) >= 10 else d


def _tz(tenant: str):
    from ..life import tz_of
    return tz_of(tenant)


def today(tenant: str) -> date:
    return datetime.now(_tz(tenant)).date()


def _date(tenant: str, v: str | None, field: str = "date") -> str:
    """'2026-10-28' / '28/10' / '28-10-2026' / 'aaj' / 'kal' / 'parso' / '5 din' -> YYYY-MM-DD ('' if empty)."""
    s = str(v or "").strip().lower()
    if not s:
        return ""
    t = today(tenant)
    if s in ("aaj", "today"):
        return t.isoformat()
    if s in ("kal", "tomorrow"):
        return (t + timedelta(days=1)).isoformat()
    if s in ("parso", "parson", "day after tomorrow"):
        return (t + timedelta(days=2)).isoformat()
    m = re.fullmatch(r"(\d{1,3})\s*(din|days?|d)(\s*(mein|baad|me|after))?", s)
    if m:
        return (t + timedelta(days=int(m.group(1)))).isoformat()
    m = re.fullmatch(r"(\d{1,2})\s*(hafte|hafta|weeks?|w)(\s*(mein|baad|me|after))?", s)
    if m:
        return (t + timedelta(days=7 * int(m.group(1)))).isoformat()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    try:
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?", s)
        if m:
            y = int(m.group(3)) if m.group(3) else t.year
            y = y + 2000 if y < 100 else y
            d = date(y, int(m.group(2)), int(m.group(1)))
            if not m.group(3) and d < t - timedelta(days=30):
                d = date(y + 1, d.month, d.day)
            return d.isoformat()
    except ValueError:
        pass
    raise DarziError(f"{field} '{v}' samajh nahi aaya (jaise 28/10, 2026-10-28, kal, 5 din).")


def _nice(d: str) -> str:
    try:
        x = date.fromisoformat(d)
    except (TypeError, ValueError):
        return d or "-"
    return f"{DAYS[x.weekday()]} {x.day:02d}/{x.month:02d}"


# ---------------------------------------------------------------- settings (her rules)
def _settings_row(s, tenant: str) -> DarziSettings:
    row = s.get(DarziSettings, tenant)
    if row is None:
        row = DarziSettings(tenant_id=tenant)
        s.add(row)
        s.flush()
    return row


def _settings_view(r: DarziSettings) -> dict[str, Any]:
    return {"enabled": bool(r.enabled), "shop_name": r.shop_name, "unit": r.unit, "pieces_per_day": r.pieces_per_day,
            "closed_days": _j(r.closed_days, []), "rush_percent": r.rush_percent,
            "min_days": {k: v for k, v in _j(r.min_days, {}).items()},
            "prices": {k: v for k, v in _j(r.prices, {}).items()}, "rules": _j(r.rules, []),
            "remeasure_months": r.remeasure_months, "ready_template": r.ready_template or DEFAULT_READY,
            "morning_time": r.morning_time,
            "usual_days": {g: (_j(r.min_days, {}).get(g) or spec["days"]) for g, spec in G.GARMENTS.items()}}


def settings(tenant: str) -> dict[str, Any]:
    with session() as s:
        return _settings_view(_settings_row(s, tenant))


def _shop_name(tenant: str, r: DarziSettings) -> str:
    if r.shop_name:
        return r.shop_name
    try:
        from ..employee import service as emp
        return (emp.profile(tenant) or {}).get("business_name") or "dukaan"
    except Exception:
        return "dukaan"


def save_settings(tenant: str, **kw: Any) -> dict[str, Any]:
    """Change her rules. prices / min_days are MERGED ({garment: value}, value null = remove); rules replace."""
    with session() as s:
        r = _settings_row(s, tenant)
        for k in ("shop_name", "ready_template", "morning_time"):
            if kw.get(k) is not None:
                v = str(kw[k]).strip()
                if k == "morning_time" and v and not re.fullmatch(r"\d{1,2}:\d{2}", v):
                    raise DarziError("Subah ka samay HH:MM mein (jaise 09:30).")
                setattr(r, k, v[:2000])
        if kw.get("unit") is not None:
            u = str(kw["unit"]).lower().strip()
            if u not in ("inch", "cm"):
                raise DarziError("Naap inch ya cm mein.")
            r.unit = u
        for k in ("pieces_per_day", "rush_percent", "remeasure_months"):
            if kw.get(k) is not None:
                try:
                    v = int(kw[k])
                except (TypeError, ValueError):
                    raise DarziError(f"{k} ek number hona chahiye.")
                if v < 0 or v > 1000:
                    raise DarziError(f"{k} 0 se 1000 ke beech.")
                setattr(r, k, v)
        if kw.get("enabled") is not None:
            r.enabled = bool(kw["enabled"])
        if kw.get("closed_days") is not None:
            days = []
            for d in kw["closed_days"] or []:
                if isinstance(d, int) and 0 <= d <= 6:
                    days.append(d)
                else:
                    w = str(d).lower()[:3]
                    names = {"som": 0, "mon": 0, "man": 1, "tue": 1, "bud": 2, "wed": 2, "gur": 3, "thu": 3, "shu": 4,
                             "fri": 4, "sha": 5, "sat": 5, "rav": 6, "sun": 6, "ita": 6}
                    if w in names:
                        days.append(names[w])
            r.closed_days = json.dumps(sorted(set(days)))
        if kw.get("prices"):
            cur = _j(r.prices, {})
            for g, v in dict(kw["prices"]).items():
                gid = G.garment_of(g)
                if v in (None, "", 0):
                    cur.pop(gid, None)
                else:
                    cur[gid] = _paise(v) / 100
            r.prices = json.dumps(cur)
        if kw.get("min_days"):
            cur = _j(r.min_days, {})
            for g, v in dict(kw["min_days"]).items():
                gid = G.garment_of(g)
                if v in (None, "", 0):
                    cur.pop(gid, None)
                else:
                    cur[gid] = max(0, min(90, int(v)))
            r.min_days = json.dumps(cur)
        if kw.get("rules") is not None:
            rules = [str(x).strip()[:300] for x in (kw["rules"] or []) if str(x).strip()][:30]
            r.rules = json.dumps(rules, ensure_ascii=False)
        return _settings_view(r)


# ---------------------------------------------------------------- customers + measurements
def _cust_view(c: DarziCustomer) -> dict[str, Any]:
    return {"id": c.id, "name": c.name, "phone": c.phone, "notes": c.notes, "created_at": c.created_at.isoformat()}


def _find_customer(s, tenant: str, ref: str = "", name: str = "", phone: str = "") -> DarziCustomer | None:
    if ref:
        c = s.get(DarziCustomer, ref)
        if c is not None and c.tenant_id == tenant:
            return c
    ph = _digits(phone or (ref if re.fullmatch(r"[\d +\-]{10,16}", ref or "") else ""))
    if len(ph) == 10:
        c = s.scalars(select(DarziCustomer).where(DarziCustomer.tenant_id == tenant, DarziCustomer.phone == ph)).first()
        if c is not None:
            return c
    nm = (name or ref or "").strip().lower()
    if nm and not re.fullmatch(r"[\d +\-]+", nm):
        rows = s.scalars(select(DarziCustomer).where(DarziCustomer.tenant_id == tenant)).all()
        exact = [c for c in rows if c.name.strip().lower() == nm]
        if len(exact) == 1:
            return exact[0]
        part = [c for c in rows if nm in c.name.strip().lower()]
        if len(part) == 1 and not exact:
            return part[0]
        if len(exact) > 1 or len(part) > 1:
            many = exact or part
            raise DarziError("Is naam ke kai graahak hain: " + ", ".join(f"{c.name} ({c.phone[-4:] or 'no phone'}) id={c.id}"
                                                                         for c in many[:6]) + ". Phone ya id bataiye.")
    return None


def customer_upsert(tenant: str, name: str = "", phone: str = "", notes: str = "", customer: str = "") -> dict[str, Any]:
    with session() as s:
        c = _find_customer(s, tenant, customer, name, phone)
        if c is None:
            if not (name or "").strip():
                raise DarziError("Graahak ka naam chahiye.")
            c = DarziCustomer(tenant_id=tenant, name=name.strip()[:120], phone=_digits(phone))
            s.add(c)
            s.flush()
        else:                                          # found (by id / phone / name): keep the saved name
            if phone and not c.phone:
                c.phone = _digits(phone)
            if notes:
                c.notes = (c.notes + "\n" + notes.strip())[-2000:].strip()
        return _cust_view(c)


def _measure_view(m: DarziMeasure) -> dict[str, Any]:
    vals = _j(m.values, {})
    return {"id": m.id, "customer_id": m.customer_id, "person": m.person, "garment": m.garment,
            "garment_label": G.GARMENTS.get(m.garment, G.GARMENTS["other"])["label"], "values": vals,
            "shown": ", ".join(f"{G.label(k)} {v:g}" for k, v in vals.items()), "unit": m.unit, "note": m.note,
            "source": m.source, "created_at": m.created_at.isoformat()}


def _latest_measure(s, tenant: str, customer_id: str, garment: str, person: str = "") -> DarziMeasure | None:
    return s.scalars(select(DarziMeasure).where(DarziMeasure.tenant_id == tenant, DarziMeasure.customer_id == customer_id,
                                                DarziMeasure.garment == garment, DarziMeasure.person == (person or ""))
                     .order_by(DarziMeasure.created_at.desc())).first()


def save_measure(tenant: str, customer: str = "", garment: str = "", values: Any = None, person: str = "", note: str = "",
                 unit: str = "", source: str = "chat", name: str = "", phone: str = "") -> dict[str, Any]:
    """A new set of measurements (old ones are kept). Returns what was understood, what's missing, and how it differs
    from last time (> 1 inch / 2.5 cm is pointed out: check it before cutting)."""
    vals = G.clean_values(values)
    if not vals and not note:
        raise DarziError("Koi naap samajh nahi aaya. Jaise: chest 34, kamar 30, lambai 15, bahi 11.5.")
    gid = G.garment_of(garment)
    c = customer_upsert(tenant, name=name, phone=phone, customer=customer) if (name or phone or customer) else None
    if c is None:
        raise DarziError("Kis graahak ka naap hai? Naam ya phone bataiye.")
    with session() as s:
        st = _settings_row(s, tenant)
        u = (unit or st.unit or "inch").lower()
        prev = _latest_measure(s, tenant, c["id"], gid, person.strip())
        changes = []
        if prev is not None:
            old = _j(prev.values, {})
            lim = 2.5 if u == "cm" else 1.0
            for k, v in vals.items():
                if k in old and abs(float(old[k]) - v) > lim:
                    changes.append(f"{G.label(k)}: pehle {old[k]:g}, ab {v:g}")
            merged = {**old, **vals}                    # a partial update keeps the other old numbers
        else:
            merged = vals
        m = DarziMeasure(tenant_id=tenant, customer_id=c["id"], person=person.strip()[:60], garment=gid,
                         values=json.dumps(merged), unit=u, note=(note or (prev.note if prev else "")).strip()[:1000],
                         source=(source or "chat")[:20])
        s.add(m)
        s.flush()
        out = _measure_view(m)
    out["customer"] = c
    out["missing"] = [G.label(f) for f in G.missing(gid, merged)]
    out["changed"] = changes
    out["say"] = (f"{c['name']}{' (' + person + ')' if person else ''} ka {out['garment_label']} naap save: {out['shown']}."
                  + (f" Abhi chahiye: {', '.join(out['missing'])}." if out["missing"] else "")
                  + (f" Dhyaan dein, pichhli baar se fark: {'; '.join(changes)}. Cutting se pehle ek baar check kar lein."
                     if changes else ""))
    return out


def measures(tenant: str, customer: str = "", name: str = "", phone: str = "", garment: str = "",
             history: bool = False) -> dict[str, Any]:
    with session() as s:
        c = _find_customer(s, tenant, customer, name, phone)
        if c is None:
            raise DarziError("Graahak nahi mila.")
        q = select(DarziMeasure).where(DarziMeasure.tenant_id == tenant, DarziMeasure.customer_id == c.id)
        if garment:
            q = q.where(DarziMeasure.garment == G.garment_of(garment))
        rows = s.scalars(q.order_by(DarziMeasure.created_at.desc())).all()
        latest, seen = [], set()
        for m in rows:
            key = (m.garment, m.person)
            if history or key not in seen:
                latest.append(_measure_view(m))
                seen.add(key)
        return {"customer": _cust_view(c), "measures": latest[:60]}


def customers(tenant: str, q: str = "", limit: int = 100) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(DarziCustomer).where(DarziCustomer.tenant_id == tenant)
                         .order_by(DarziCustomer.created_at.desc())).all()
        qq = (q or "").strip().lower()
        out = []
        for c in rows:
            if qq and qq not in c.name.lower() and _digits(qq) not in (c.phone or "-"):
                continue
            v = _cust_view(c)
            v["open_orders"] = len(s.scalars(select(DarziOrder.id).where(DarziOrder.tenant_id == tenant, DarziOrder.customer_id == c.id,
                                                                         DarziOrder.status.in_(OPEN))).all())
            out.append(v)
            if len(out) >= limit:
                break
        return out


# ---------------------------------------------------------------- earlier work: how long things really take, last prices
def _taken_days(s, tenant: str) -> dict[str, list[int]]:
    rows = s.scalars(select(DarziOrder).where(DarziOrder.tenant_id == tenant, DarziOrder.status == "delivered")
                     .order_by(DarziOrder.updated_at.desc()).limit(300)).all()
    out: dict[str, list[int]] = {}
    for o in rows:
        try:
            done = o.ready_at.astimezone(_tz(tenant)).date() if o.ready_at else date.fromisoformat(o.delivered_on)
            days = (done - date.fromisoformat(o.received_on)).days
        except (TypeError, ValueError):
            continue
        for it in _j(o.items, []):
            out.setdefault(it.get("garment", "other"), []).append(max(0, days))
    return out


def _last_prices(s, tenant: str, garment: str, customer_id: str = "") -> list[int]:
    q = select(DarziOrder).where(DarziOrder.tenant_id == tenant, DarziOrder.status != "cancelled")
    if customer_id:
        q = q.where(DarziOrder.customer_id == customer_id)
    out = []
    for o in s.scalars(q.order_by(DarziOrder.created_at.desc()).limit(60)).all():
        for it in _j(o.items, []):
            if it.get("garment") == garment and it.get("price_paise"):
                out.append(int(it["price_paise"]))
    return out[:10]


def _load(s, tenant: str, day: str, skip_order: str = "") -> int:
    rows = s.scalars(select(DarziOrder).where(DarziOrder.tenant_id == tenant, DarziOrder.deliver_on == day,
                                              DarziOrder.status.in_(OPEN))).all()
    return sum(sum(int(i.get("qty", 1) or 1) for i in _j(o.items, [])) for o in rows if o.id != skip_order)


# ---------------------------------------------------------------- the checks
def _norm_items(items: Any) -> list[dict[str, Any]]:
    if isinstance(items, str):
        items = [{"garment": x.strip()} for x in re.split(r",| aur | and |\+", items) if x.strip()]
    out = []
    for raw in items or []:
        if isinstance(raw, str):
            raw = {"garment": raw}
        g = G.garment_of(str(raw.get("garment") or raw.get("what") or ""))
        try:
            qty = max(1, min(100, int(raw.get("qty") or raw.get("quantity") or 1)))
        except (TypeError, ValueError):
            qty = 1
        it = {"garment": g, "label": str(raw.get("label") or G.GARMENTS[g]["label"])[:80], "qty": qty,
              "person": str(raw.get("person") or "").strip()[:60], "fabric": str(raw.get("fabric") or "")[:200],
              "style": str(raw.get("style") or raw.get("design") or "")[:500]}
        if raw.get("price") not in (None, ""):
            it["asked_paise"] = _paise(raw.get("price"))
        if raw.get("price_paise"):
            it["price_paise"] = int(raw["price_paise"])
        if g == "other" and raw.get("garment"):
            it["label"] = str(raw.get("garment"))[:80]
        out.append(it)
    if not out:
        raise DarziError("Kya silna hai? (blouse, suit, lehenga, shirt, pant, alteration...)")
    return out


def check(tenant: str, items: Any, deliver_on: str = "", trial_on: str = "", customer: str = "", name: str = "",
          phone: str = "", skip_order: str = "") -> dict[str, Any]:
    """Every rule and earlier-work check for a job, before it is promised. problems = must change or she must agree;
    notes = good to know. Also says the earliest date her rules allow."""
    its = _norm_items(items)
    t = today(tenant)
    problems: list[str] = []
    notes: list[str] = []
    with session() as s:
        st = _settings_row(s, tenant)
        sv = _settings_view(st)
        c = None
        try:
            c = _find_customer(s, tenant, customer, name, phone)
        except DarziError as e:
            notes.append(str(e))
        need_days = max(sv["usual_days"].get(i["garment"], 3) for i in its)
        taken = _taken_days(s, tenant)
        for i in its:
            past = taken.get(i["garment"], [])
            if len(past) >= 3:
                real = round(statistics.mean(past[:10]))
                if real > sv["usual_days"].get(i["garment"], 3):
                    notes.append(f"Pichhle {len(past[:10])} {i['label']} mein asal mein ~{real} din lage "
                                 f"(niyam {sv['usual_days'].get(i['garment'], 3)} din).")
                    need_days = max(need_days, real)
        closed = set(sv["closed_days"])
        pieces = sum(i["qty"] for i in its)

        def ok_day(d: date) -> bool:
            if d.weekday() in closed:
                return False
            cap = sv["pieces_per_day"]
            return not cap or _load(s, tenant, d.isoformat(), skip_order) + pieces <= cap

        earliest = t + timedelta(days=need_days)
        for _ in range(120):
            if ok_day(earliest):
                break
            earliest += timedelta(days=1)
        dl = _date(tenant, deliver_on, "Delivery date") if deliver_on else ""
        tr = _date(tenant, trial_on, "Trial date") if trial_on else ""
        rush = False
        if dl:
            d = date.fromisoformat(dl)
            if d < t:
                problems.append(f"Delivery date {_nice(dl)} beet chuki hai.")
            elif (d - t).days < need_days:
                rush = True
                msg = (f"{_nice(dl)} sirf {(d - t).days} din mein hai; aapke niyam se {need_days} din chahiye "
                       f"(sabse jaldi {_nice(earliest.isoformat())}).")
                problems.append(msg + (f" Jaldi ka charge {sv['rush_percent']}% lagega." if sv["rush_percent"] else ""))
            if d.weekday() in closed:
                problems.append(f"{_nice(dl)} ko dukaan band rehti hai.")
            cap = sv["pieces_per_day"]
            if cap:
                load = _load(s, tenant, dl, skip_order)
                if load + pieces > cap:
                    problems.append(f"{_nice(dl)} ko pehle se {load} kapde dene hain (roz {cap} ka niyam); yeh {pieces} aur "
                                    f"jodne se zyada ho jayega. Agla khaali din: {_nice(earliest.isoformat()) if earliest > d else 'dekhiye'}.")
        if tr:
            if dl and tr > dl:
                problems.append("Trial delivery ke baad nahi ho sakta.")
            if date.fromisoformat(tr) < t:
                problems.append(f"Trial date {_nice(tr)} beet chuki hai.")
            elif date.fromisoformat(tr).weekday() in closed:
                problems.append(f"Trial {_nice(tr)} ko dukaan band hai.")
        prices = sv["prices"]
        for i in its:
            gl = prices.get(i["garment"])
            i["list_price"] = gl
            if c is not None:
                m = _latest_measure(s, tenant, c.id, i["garment"], i["person"])
                if m is None and G.GARMENTS[i["garment"]]["must"]:
                    problems.append(f"{c.name}{' (' + i['person'] + ')' if i['person'] else ''} ka {i['label']} naap nahi hai.")
                elif m is not None:
                    age = (now() - (m.created_at if m.created_at.tzinfo else m.created_at.replace(tzinfo=now().tzinfo))).days
                    if age > 30 * sv["remeasure_months"]:
                        notes.append(f"{i['label']} ka naap {age // 30} mahine purana hai: dobara naap lena theek rahega.")
                    miss = G.missing(i["garment"], _j(m.values, {}))
                    if miss:
                        problems.append(f"{i['label']} ke naap mein {', '.join(G.label(f) for f in miss)} nahi hai.")
                    if m.note:
                        notes.append(f"{i['label']} style note: {m.note[:200]}")
                    i["measure_id"] = m.id
                last = _last_prices(s, tenant, i["garment"], c.id)
                if last:
                    notes.append(f"{c.name} ka pichhla {i['label']}: {_rs(last[0])}.")
            elif G.GARMENTS[i["garment"]]["must"]:
                notes.append("Naya graahak: naap lena hoga.")
            if i.get("asked_paise") and gl and i["asked_paise"] != _paise(gl):
                notes.append(f"{i['label']}: list mein {_rs(_paise(gl))}, yahan {_rs(i['asked_paise'])}: aapki haan ke liye card banega.")
            elif not i.get("asked_paise") and not gl:
                notes.append(f"{i['label']} ka daam list mein nahi: Hoola daam taiyaar karega, aapki haan ke baad pakka.")
        return {"items": its, "problems": problems, "notes": notes, "earliest": earliest.isoformat(),
                "earliest_nice": _nice(earliest.isoformat()), "need_days": need_days, "rush": rush,
                "rush_percent": sv["rush_percent"], "deliver_on": dl, "trial_on": tr, "your_rules": sv["rules"],
                "ok": not problems}


# ---------------------------------------------------------------- orders
def _order_view(s, o: DarziOrder, full: bool = True) -> dict[str, Any]:
    c = s.get(DarziCustomer, o.customer_id)
    its = _j(o.items, [])
    bal = max(0, o.total_paise - o.paid_paise)
    v = {"id": o.id, "number": o.number, "status": o.status, "status_label": STATUS_LABEL.get(o.status, o.status),
         "customer": _cust_view(c) if c else {"id": o.customer_id, "name": "?", "phone": ""},
         "items": [{**i, "price": _rs(i["price_paise"]) if i.get("price_paise") else "", "measure": None} for i in its],
         "what": ", ".join(f"{i.get('qty', 1)} {i.get('label')}" for i in its),
         "received_on": o.received_on, "trial_on": o.trial_on, "deliver_on": o.deliver_on,
         "trial_nice": _nice(o.trial_on) if o.trial_on else "", "deliver_nice": _nice(o.deliver_on),
         "rush": o.rush, "rush_charge": _rs(o.rush_paise) if o.rush_paise else "",
         "total": _rs(o.total_paise), "paid": _rs(o.paid_paise), "balance": _rs(bal), "balance_paise": bal,
         "total_paise": o.total_paise, "paid_paise": o.paid_paise, "notes": o.notes, "photos": _j(o.photos, []),
         "delivered_on": o.delivered_on, "created_at": o.created_at.isoformat()}
    pend = s.scalars(select(DarziQuote).where(DarziQuote.order_id == o.id, DarziQuote.status == "pending")).all()
    v["quote_pending"] = [q.id for q in pend]
    if o.status in OPEN and o.deliver_on:
        try:
            left = (date.fromisoformat(o.deliver_on) - today(o.tenant_id)).days
            v["days_left"] = left
            v["late"] = left < 0 and o.status != "ready"
        except ValueError:
            pass
    if full:
        v["log"] = _j(o.log, [])[-30:]
        for i in v["items"]:
            if i.get("measure_id"):
                m = s.get(DarziMeasure, i["measure_id"])
                i["measure"] = _measure_view(m) if m else None
    return v


def _log(o: DarziOrder, what: str, by: str = "owner") -> None:
    lg = _j(o.log, [])
    lg.append({"at": now().isoformat(timespec="seconds"), "what": what[:300], "by": by})
    o.log = json.dumps(lg[-200:], ensure_ascii=False)


def _recompute(o: DarziOrder, rush_percent: int) -> None:
    its = _j(o.items, [])
    base = sum(int(i.get("price_paise") or 0) * int(i.get("qty", 1) or 1) for i in its)
    o.rush_paise = int(round(base * rush_percent / 100)) if o.rush and rush_percent else 0
    o.total_paise = base + o.rush_paise


def _get_order(s, tenant: str, ref: str) -> DarziOrder:
    ref = str(ref or "").strip()
    o = s.get(DarziOrder, ref) if ref else None
    if o is None and ref:
        num = ref.upper()
        if re.fullmatch(r"\d+", num):
            num = f"D-{int(num):04d}"
        elif re.fullmatch(r"D-?\d+", num):
            num = f"D-{int(num.replace('D', '').replace('-', '')):04d}"
        o = s.scalars(select(DarziOrder).where(DarziOrder.tenant_id == tenant, DarziOrder.number == num)).first()
    if o is None or o.tenant_id != tenant:
        raise DarziError(f"Order '{ref}' nahi mila.")
    return o


def _publish(tenant: str, kind: str, payload: dict[str, Any], conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("darzi publish failed")


def _quote_view(s, q: DarziQuote) -> dict[str, Any]:
    o = s.get(DarziOrder, q.order_id) if q.order_id else None
    c = s.get(DarziCustomer, o.customer_id) if o else None
    return {"id": q.id, "order_id": q.order_id, "order_number": o.number if o else "", "customer": c.name if c else "",
            "garment": q.garment, "label": G.GARMENTS.get(q.garment, G.GARMENTS["other"])["label"],
            "price": _rs(q.price_paise) if q.price_paise else "", "price_rupees": q.price_paise / 100 if q.price_paise else None,
            "list_price": _rs(q.list_paise) if q.list_paise else "", "why": q.why, "status": q.status,
            "created_at": q.created_at.isoformat()}


def _prepare_price(s, tenant: str, i: dict[str, Any], customer_id: str, sv: dict) -> tuple[int, str]:
    """What Hoola proposes for an item without a settled price, and why (her list, her earlier orders, her words)."""
    gl = _paise(sv["prices"].get(i["garment"])) if sv["prices"].get(i["garment"]) else 0
    if i.get("asked_paise"):
        why = f"Aapne {_rs(i['asked_paise'])} kaha" + (f"; list mein {_rs(gl)} hai" if gl else "; yeh list mein naya hai")
        return i["asked_paise"], why
    mine = _last_prices(s, tenant, i["garment"], customer_id)
    allp = _last_prices(s, tenant, i["garment"])
    if mine:
        return mine[0], f"Is graahak ka pichhla {i['label']} {_rs(mine[0])} ka tha."
    if allp:
        mid = int(statistics.median(allp))
        return mid, f"Pichhle {len(allp)} {i['label']} ka beech ka daam {_rs(mid)}."
    return 0, f"{i['label']} ka daam pehli baar: aap bataiye."


def new_order(tenant: str, items: Any, customer: str = "", name: str = "", phone: str = "", deliver_on: str = "",
              trial_on: str = "", advance: Any = None, notes: str = "", photos: list[str] | None = None,
              force: bool = False, by: str = "owner", conv: str = "") -> dict[str, Any]:
    """Take the job. Runs `check` first: with problems and force=False nothing is saved, the problems come back so they
    can be fixed or she can agree (force=True after she said yes). Prices outside her list become quote cards."""
    if not (customer or name or phone):
        raise DarziError("Graahak ka naam / phone chahiye.")
    if not deliver_on:
        ck = check(tenant, items, "", trial_on, customer, name, phone)
        deliver_on = ck["earliest"]
    ck = check(tenant, items, deliver_on, trial_on, customer, name, phone)
    hard = [p for p in ck["problems"] if "beet chuki" in p or "delivery ke baad" in p]
    if hard or (ck["problems"] and not force):
        return {"saved": False, "check": ck,
                "say": "Order abhi save nahi kiya. " + " ".join(ck["problems"])
                       + ("" if hard else " Theek karke dobara bhejiye, ya owner maan jaaye to force=true.")}
    c = customer_upsert(tenant, name=name, phone=phone, customer=customer)
    with _LOCK, session() as s:
        st = _settings_row(s, tenant)
        sv = _settings_view(st)
        st.seq = (st.seq or 0) + 1
        o = DarziOrder(tenant_id=tenant, number=f"D-{st.seq:04d}", customer_id=c["id"], status="new",
                       received_on=today(tenant).isoformat(), trial_on=ck["trial_on"], deliver_on=ck["deliver_on"],
                       rush=bool(ck["rush"]), notes=(notes or "")[:2000], photos=json.dumps([str(x) for x in (photos or [])][:20]))
        s.add(o)
        s.flush()
        its, quotes = [], []
        for idx, i in enumerate(ck["items"]):
            gl = _paise(sv["prices"][i["garment"]]) if sv["prices"].get(i["garment"]) else 0
            asked = i.pop("asked_paise", 0)
            i.pop("list_price", None)
            if asked and (asked == gl):
                i["price_paise"] = asked
            elif not asked and gl:
                i["price_paise"] = gl
            else:
                i["asked_paise"] = asked
                price, why = _prepare_price(s, tenant, i, c["id"], sv)
                i.pop("asked_paise", None)
                q = DarziQuote(tenant_id=tenant, order_id=o.id, item=idx, garment=i["garment"], price_paise=price,
                               list_paise=gl, why=why)
                s.add(q)
                quotes.append(q)
            its.append(i)
        o.items = json.dumps(its, ensure_ascii=False)
        _recompute(o, sv["rush_percent"])
        adv = _paise(advance) if advance not in (None, "") else 0
        o.paid_paise = adv
        _log(o, f"Order liya: {', '.join(str(i['qty']) + ' ' + i['label'] for i in its)}; delivery {_nice(o.deliver_on)}"
                + (f", trial {_nice(o.trial_on)}" if o.trial_on else "") + (f"; advance {_rs(adv)}" if adv else "")
                + ("; owner ne niyam se hatkar haan kahi: " + " ".join(ck["problems"]) if ck["problems"] else ""), by)
        s.flush()
        view = _order_view(s, o)
        qviews = [_quote_view(s, q) for q in quotes]
    for qv in qviews:
        _publish(tenant, "darzi_quote", qv, conv)
    _publish(tenant, "darzi_order", {k: view[k] for k in ("id", "number", "status", "status_label", "what", "deliver_on",
                                                          "deliver_nice", "trial_nice", "total", "balance")} | {"customer": view["customer"]["name"]}, conv)
    say = (f"Order {view['number']} save: {view['customer']['name']}, {view['what']}, delivery {view['deliver_nice']}"
           + (f", trial {view['trial_nice']}" if view["trial_nice"] else "") + f". Kul {view['total']}, advance {view['paid']}, baaki {view['balance']}.")
    if qviews:
        say += " " + "; ".join(f"{q['label']} ka daam ({q['price'] or 'aap batayengi'}) aapki haan ke liye card par hai" for q in qviews) + "."
    if ck["notes"]:
        say += " Dhyaan: " + " ".join(ck["notes"][:4])
    return {"saved": True, "order": view, "quotes": qviews, "check": ck, "say": say}


def update_order(tenant: str, order: str, deliver_on: str = "", trial_on: str = "", notes: str = "", items: Any = None,
                 force: bool = False, by: str = "owner") -> dict[str, Any]:
    with session() as s:
        o = _get_order(s, tenant, order)
        cust, cur_items, oid = o.customer_id, _j(o.items, []), o.id
    ck = check(tenant, items if items is not None else cur_items, deliver_on or o.deliver_on, trial_on or o.trial_on,
               customer=cust, skip_order=oid)
    if ck["problems"] and not force:
        return {"saved": False, "check": ck, "say": "Badlav save nahi kiya: " + " ".join(ck["problems"])}
    with session() as s:
        o = _get_order(s, tenant, order)
        sv = _settings_view(_settings_row(s, tenant))
        changed = []
        if deliver_on and ck["deliver_on"] != o.deliver_on:
            changed.append(f"delivery {_nice(o.deliver_on)} -> {_nice(ck['deliver_on'])}")
            o.deliver_on = ck["deliver_on"]
        if trial_on and ck["trial_on"] != o.trial_on:
            changed.append(f"trial -> {_nice(ck['trial_on'])}")
            o.trial_on = ck["trial_on"]
        if notes:
            o.notes = (o.notes + "\n" + notes).strip()[-2000:]
            changed.append("note")
        if items is not None:
            old = {(i["garment"], i.get("person", "")): i for i in cur_items}
            new = []
            for i in ck["items"]:
                prev = old.get((i["garment"], i.get("person", "")))
                i.pop("list_price", None)
                if prev and prev.get("price_paise") and not i.get("asked_paise"):
                    i["price_paise"] = prev["price_paise"]
                elif not i.get("asked_paise") and sv["prices"].get(i["garment"]):
                    i["price_paise"] = _paise(sv["prices"][i["garment"]])
                elif i.get("asked_paise"):
                    gl = _paise(sv["prices"].get(i["garment"]) or 0)
                    if i["asked_paise"] == gl:
                        i["price_paise"] = gl
                    else:
                        s.add(DarziQuote(tenant_id=tenant, order_id=o.id, item=len(new), garment=i["garment"],
                                         price_paise=i["asked_paise"], list_paise=gl, why=f"Aapne {_rs(i['asked_paise'])} kaha"))
                    i.pop("asked_paise", None)
                new.append(i)
            o.items = json.dumps(new, ensure_ascii=False)
            changed.append("kapde")
        o.rush = bool(ck["rush"])
        _recompute(o, sv["rush_percent"])
        _log(o, "Badla: " + ", ".join(changed or ["kuch nahi"]), by)
        s.flush()
        v = _order_view(s, o)
    return {"saved": True, "order": v, "check": ck, "say": f"Order {v['number']} badla: {', '.join(changed) or 'kuch nahi'}."}


def set_status(tenant: str, order: str, status: str, note: str = "", by: str = "owner", conv: str = "") -> dict[str, Any]:
    status = str(status or "").lower().strip()
    alias = {"silai": "stitching", "stitch": "stitching", "fitting": "trial", "taiyaar": "ready", "done": "ready",
             "diya": "delivered", "de diya": "delivered", "pickup": "delivered", "cancel": "cancelled", "cut": "cutting"}
    status = alias.get(status, status)
    if status not in STATUSES:
        raise DarziError("Status: " + " | ".join(STATUSES))
    if status == "delivered":
        return deliver(tenant, order, note=note, by=by, conv=conv)
    with session() as s:
        o = _get_order(s, tenant, order)
        if o.status in ("delivered", "cancelled"):
            raise DarziError(f"Order {o.number} pehle hi {STATUS_LABEL[o.status]} hai.")
        o.status = status
        if status == "ready":
            o.ready_at = now()
        _log(o, f"Status: {STATUS_LABEL[status]}" + (f" ({note})" if note else ""), by)
        s.flush()
        v = _order_view(s, o)
    out = {"order": v, "say": f"Order {v['number']} ab: {v['status_label']}."}
    if status == "ready":
        r = ready_card(tenant, v["id"], conv=conv)
        out["ready"] = r
        out["say"] += " 'Taiyaar hai' ka message draft card par hai; aap tap karengi tabhi jayega."
    return out


def pay(tenant: str, order: str, amount: Any, how: str = "", by: str = "owner") -> dict[str, Any]:
    """Note money she received (cash / her UPI). Hoola never takes money itself."""
    p = _paise(amount)
    if p <= 0:
        raise DarziError("Kitne rupaye mile?")
    with session() as s:
        o = _get_order(s, tenant, order)
        o.paid_paise += p
        _log(o, f"Paise mile: {_rs(p)}" + (f" ({how})" if how else ""), by)
        s.flush()
        v = _order_view(s, o)
    return {"order": v, "say": f"{v['number']}: {_rs(p)} likh liya. Kul mila {v['paid']}, baaki {v['balance']}."}


def deliver(tenant: str, order: str, paid_now: Any = None, note: str = "", by: str = "owner", conv: str = "") -> dict[str, Any]:
    """Close the job: delivered, money noted, a log of how it went (on time / late; the days it really took)."""
    with session() as s:
        o = _get_order(s, tenant, order)
        if o.status == "cancelled":
            raise DarziError("Cancel hua order deliver nahi hota.")
        if paid_now not in (None, ""):
            p = _paise(paid_now)
            if p:
                o.paid_paise += p
                _log(o, f"Delivery par mile: {_rs(p)}", by)
        t = today(tenant)
        o.status, o.delivered_on = "delivered", t.isoformat()
        if not o.ready_at:
            o.ready_at = now()
        late = 0
        try:
            late = (t - date.fromisoformat(o.deliver_on)).days
        except ValueError:
            pass
        took = (t - date.fromisoformat(o.received_on)).days if o.received_on else 0
        how = ("samay par" if late <= 0 else f"{late} din der se")
        _log(o, f"De diya ({how}, {took} din lage)" + (f"; {note}" if note else ""), by)
        s.flush()
        v = _order_view(s, o)
    v["took_days"], v["late_days"] = took, max(0, late)
    say = f"Order {v['number']} {v['customer']['name']} ko de diya, {how} ({took} din)."
    if v["balance_paise"] > 0:
        say += f" Baaki {v['balance']} abhi lena hai."
    _publish(tenant, "darzi_order", {"id": v["id"], "number": v["number"], "status": "delivered", "status_label": v["status_label"],
                                     "what": v["what"], "customer": v["customer"]["name"], "balance": v["balance"]}, conv)
    return {"order": v, "log": v.get("log", []), "say": say}


def cancel(tenant: str, order: str, reason: str = "", by: str = "owner") -> dict[str, Any]:
    with session() as s:
        o = _get_order(s, tenant, order)
        if o.status == "delivered":
            raise DarziError("Diya hua order cancel nahi hota.")
        o.status = "cancelled"
        for q in s.scalars(select(DarziQuote).where(DarziQuote.order_id == o.id, DarziQuote.status == "pending")).all():
            q.status = "rejected"
        _log(o, "Cancel" + (f": {reason}" if reason else ""), by)
        s.flush()
        v = _order_view(s, o, full=False)
    return {"order": v, "say": f"Order {v['number']} cancel. Advance {v['paid']} lautana ho to aap khud dijiye."}


def get_order(tenant: str, order: str) -> dict[str, Any]:
    with session() as s:
        return _order_view(s, _get_order(s, tenant, order))


def orders(tenant: str, status: str = "", customer: str = "", limit: int = 60) -> list[dict[str, Any]]:
    with session() as s:
        q = select(DarziOrder).where(DarziOrder.tenant_id == tenant)
        st = (status or "").lower()
        if st in ("open", "chalu", "pending"):
            q = q.where(DarziOrder.status.in_(OPEN))
        elif st in STATUSES:
            q = q.where(DarziOrder.status == st)
        if customer:
            c = _find_customer(s, tenant, customer, customer, customer)
            if c is None:
                return []
            q = q.where(DarziOrder.customer_id == c.id)
        rows = s.scalars(q.order_by(DarziOrder.created_at.desc()).limit(max(1, min(300, limit)))).all()
        out = [_order_view(s, o, full=False) for o in rows]
    if st in ("open", "chalu", "pending", ""):
        out.sort(key=lambda v: (v["status"] not in OPEN, v.get("deliver_on") or "9999"))
    return out


# ---------------------------------------------------------------- quotes: Hoola prepares, she decides
def quotes(tenant: str, status: str = "pending") -> list[dict[str, Any]]:
    with session() as s:
        q = select(DarziQuote).where(DarziQuote.tenant_id == tenant)
        if status:
            q = q.where(DarziQuote.status == status)
        return [_quote_view(s, x) for x in s.scalars(q.order_by(DarziQuote.created_at.desc()).limit(100)).all()]


def decide_quote(tenant: str, quote_id: str, approve: bool, price: Any = None, to_list: bool | None = None,
                 conv: str = "") -> dict[str, Any]:
    """Her answer to a price card. Called only from her tap in the app (or her own words to Hoola as the owner)."""
    with session() as s:
        q = s.get(DarziQuote, quote_id)
        if q is None or q.tenant_id != tenant:
            raise DarziError("Yeh daam card nahi mila.")
        if q.status != "pending":
            raise DarziError("Is card par pehle hi faisla ho chuka.")
        st = _settings_row(s, tenant)
        o = s.get(DarziOrder, q.order_id) if q.order_id else None
        if not approve:
            q.status = "rejected"
            if o is not None:
                _log(o, f"{G.GARMENTS.get(q.garment, G.GARMENTS['other'])['label']} ka daam {_rs(q.price_paise)}: owner ne mana kiya")
            s.flush()
            v = _quote_view(s, q)
            say = "Theek hai, yeh daam nahi. Sahi daam bataiye to order mein daal doon."
        else:
            p = _paise(price) if price not in (None, "") else q.price_paise
            if p <= 0:
                raise DarziError("Daam bataiye (rupaye).")
            q.status, q.price_paise = "approved", p
            if to_list is None:
                to_list = not q.list_paise                      # a garment new to her list is added to it
            if to_list:
                pr = _j(st.prices, {})
                pr[q.garment] = p / 100
                st.prices = json.dumps(pr)
            if o is not None:
                its = _j(o.items, [])
                if 0 <= q.item < len(its):
                    its[q.item]["price_paise"] = p
                    o.items = json.dumps(its, ensure_ascii=False)
                _recompute(o, st.rush_percent)
                _log(o, f"Daam pakka (owner ki haan): {its[q.item]['label'] if 0 <= q.item < len(its) else q.garment} {_rs(p)}")
            s.flush()
            v = _quote_view(s, q)
            say = f"{v['label']} {_rs(p)} pakka" + (" aur daam ki list mein bhi daal diya." if to_list else ".")
    _publish(tenant, "darzi_quote", v, conv)
    return {"quote": v, "say": say}


# ---------------------------------------------------------------- 'ready for pickup': draft, her WhatsApp, the slip
def _ready_text(tenant: str, s, o: DarziOrder) -> str:
    st = _settings_row(s, tenant)
    c = s.get(DarziCustomer, o.customer_id)
    bal = max(0, o.total_paise - o.paid_paise)
    tpl = st.ready_template or DEFAULT_READY
    its = _j(o.items, [])
    vals = {"name": (c.name if c else "").split(" ")[0] or "ji", "items": ", ".join(i.get("label", "") for i in its),
            "shop": _shop_name(tenant, st), "number": o.number, "balance": _rs(bal),
            "balance_line": f"Baaki {_rs(bal)}. " if bal else "", "deliver": _nice(o.deliver_on)}
    try:
        return tpl.format(**vals).strip()
    except (KeyError, IndexError, ValueError):
        return DEFAULT_READY.format(**vals).strip()


def ready_card(tenant: str, order: str, conv: str = "") -> dict[str, Any]:
    """The 'taiyaar hai' message as a draft card. Never sent by Hoola on its own: her tap opens her WhatsApp with it, or
    (when the customer wrote to the business number in the last 24 h) sends it through the official API."""
    from ..employee import inbox
    with session() as s:
        o = _get_order(s, tenant, order)
        c = s.get(DarziCustomer, o.customer_id)
        text = _ready_text(tenant, s, o)
        ph = c.phone if c else ""
        v = _order_view(s, o, full=False)
    contact_id, api_ok = "", False
    if ph:
        try:
            from ..employee.models import BizContact
            with session() as s:
                bc = s.scalars(select(BizContact).where(BizContact.tenant_id == tenant)).all()
                for x in bc:
                    if _digits(x.wa_id) == ph and not x.opted_out:
                        contact_id, api_ok = x.id, inbox._window_open(x)
                        break
        except Exception:
            pass
    from urllib.parse import quote
    card = {"order_id": v["id"], "number": v["number"], "customer": v["customer"]["name"], "phone": ph, "text": text,
            "what": v["what"], "balance": v["balance"], "wa_link": f"https://wa.me/91{ph}?text={quote(text)}" if len(ph) == 10 else "",
            "sms_link": f"sms:+91{ph}?body={quote(text)}" if len(ph) == 10 else "", "can_business": api_ok,
            "contact_id": contact_id, "status": "draft"}
    _publish(tenant, "darzi_ready", card, conv)
    return card


async def send_ready_business(tenant: str, order: str, text: str = "") -> dict[str, Any]:
    """Her tap on 'Business WhatsApp se bhejo': the official Cloud API, inside the 24 h window only."""
    from ..employee import inbox
    with session() as s:
        o = _get_order(s, tenant, order)
        body = (text or _ready_text(tenant, s, o)).strip()
        c = s.get(DarziCustomer, o.customer_id)
        ph = c.phone if c else ""
        oid = o.id
    from ..employee.models import BizContact
    with session() as s:
        bc = [x for x in s.scalars(select(BizContact).where(BizContact.tenant_id == tenant)).all() if _digits(x.wa_id) == ph]
        cid = bc[0].id if bc else ""
    if not cid:
        raise DarziError("Is graahak ne business WhatsApp par kabhi message nahi kiya: apne WhatsApp se bhejiye (draft taiyaar hai).")
    try:
        await inbox.send(tenant, cid, body, by="owner")
    except inbox.InboxError as e:
        raise DarziError(str(e))
    with session() as s:
        o = s.get(DarziOrder, oid)
        _log(o, "'Taiyaar hai' message business WhatsApp se bheja (owner ke tap par)")
    return {"sent": True, "say": "Message bhej diya."}


def mark_told(tenant: str, order: str, how: str = "whatsapp") -> dict[str, Any]:
    with session() as s:
        o = _get_order(s, tenant, order)
        _log(o, f"Graahak ko bataya ({how})")
        return {"ok": True}


def slip_pdf(tenant: str, order: str) -> bytes:
    """The job slip: order no, customer, garments with measurements and style, dates, money. Plain Latin text (Rs)."""
    from reportlab.lib.pagesizes import A5
    from reportlab.pdfgen import canvas
    with session() as s:
        o = _get_order(s, tenant, order)
        v = _order_view(s, o)
        shop = _shop_name(tenant, _settings_row(s, tenant))
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A5)
    w, h = A5
    y = h - 36

    def line(text: str, size: int = 10, bold: bool = False, gap: int = 14):
        nonlocal y
        if y < 40:
            pdf.showPage()
            y = h - 36
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        safe = str(text).replace("₹", "Rs ").encode("latin-1", "replace").decode("latin-1")
        pdf.drawString(28, y, safe[:95])
        y -= gap

    line(shop, 14, True, 18)
    line(f"Order {v['number']}   ·   {v['received_on']}", 10, True)
    line(f"Graahak: {v['customer']['name']}   {v['customer'].get('phone', '')}")
    line(f"Trial: {v['trial_nice'] or '-'}    Delivery: {v['deliver_nice']}" + ("   (JALDI)" if v["rush"] else ""), 10, True, 20)
    for i in v["items"]:
        line(f"{i.get('qty', 1)} x {i.get('label')}" + (f" ({i['person']})" if i.get("person") else "")
             + (f"   {i['price']}" if i.get("price") else "   daam baaki"), 11, True)
        if i.get("fabric"):
            line(f"   Kapda: {i['fabric']}", 9)
        if i.get("style"):
            line(f"   Style: {i['style'][:85]}", 9)
        m = i.get("measure")
        if m and m.get("values"):
            parts = [f"{G.label(k)} {val:g}" for k, val in m["values"].items()]
            for k in range(0, len(parts), 4):
                line("   " + ",  ".join(parts[k:k + 4]), 9, gap=12)
            if m.get("note"):
                line(f"   Note: {m['note'][:85]}", 9)
        y -= 4
    y -= 6
    if v["rush_charge"]:
        line(f"Jaldi ka charge: {v['rush_charge']}")
    line(f"Kul: {v['total']}    Mila: {v['paid']}    Baaki: {v['balance']}", 11, True)
    if v["notes"]:
        line(f"Note: {v['notes'][:90]}", 9)
    pdf.showPage()
    pdf.save()
    return buf.getvalue()


def slip_file(tenant: str, order: str, conv: str = "") -> dict[str, Any]:
    from .. import chatfiles
    data = slip_pdf(tenant, order)
    v = get_order(tenant, order)
    f = chatfiles.store(tenant, f"Order-{v['number']}-{re.sub(r'[^A-Za-z0-9]+', '-', v['customer']['name'])[:30]}.pdf", data,
                        "application/pdf")
    _publish(tenant, "pc_file", {**f, "source": "darzi", "title": f"Order {v['number']} slip"}, conv)
    return {"file": f, "say": f"Order {v['number']} ki slip (PDF) taiyaar."}


# ---------------------------------------------------------------- the day: trials, deliveries, late, the week's load
def day(tenant: str, on: str = "") -> dict[str, Any]:
    d = _date(tenant, on) if on else today(tenant).isoformat()
    t = today(tenant).isoformat()
    with session() as s:
        st = _settings_view(_settings_row(s, tenant))
        rows = s.scalars(select(DarziOrder).where(DarziOrder.tenant_id == tenant, DarziOrder.status.in_(OPEN))).all()
        trials = [_order_view(s, o, False) for o in rows if o.trial_on == d and o.status not in ("ready",)]
        deliveries = [_order_view(s, o, False) for o in rows if o.deliver_on == d]
        late = [_order_view(s, o, False) for o in rows if o.deliver_on and o.deliver_on < t and o.status != "ready"]
        waiting = []
        for o in rows:
            if o.status == "ready" and o.ready_at:
                ra = o.ready_at if o.ready_at.tzinfo else o.ready_at.replace(tzinfo=now().tzinfo)
                if (now() - ra).days >= 3:
                    waiting.append(_order_view(s, o, False))
        week = []
        base = date.fromisoformat(d)
        for k in range(7):
            dd = (base + timedelta(days=k)).isoformat()
            n = _load(s, tenant, dd)
            week.append({"date": dd, "nice": _nice(dd), "pieces": n, "cap": st["pieces_per_day"],
                         "full": bool(st["pieces_per_day"]) and n >= st["pieces_per_day"]})
        pend = s.scalars(select(DarziQuote).where(DarziQuote.tenant_id == tenant, DarziQuote.status == "pending")).all()
        open_n = len(rows)
    lines = [f"Darzi: {_nice(d)}"]
    if trials:
        lines.append("Trial: " + "; ".join(f"{o['customer']['name']} ({o['what']}, {o['number']})" for o in trials))
    if deliveries:
        lines.append("Dena hai: " + "; ".join(f"{o['customer']['name']} ({o['what']}, {o['status_label']})" for o in deliveries))
    if late:
        lines.append("Der ho gayi: " + "; ".join(f"{o['customer']['name']} {o['number']} ({_nice(o['deliver_on'])} ka)" for o in late))
    if waiting:
        lines.append("Taiyaar par 3+ din se nahi le gaye: " + "; ".join(f"{o['customer']['name']} {o['number']}" for o in waiting))
    full = [w["nice"] for w in week if w["full"]]
    if full:
        lines.append("Bhare hue din: " + ", ".join(full))
    if pend:
        lines.append(f"{len(pend)} daam aapki haan ka intezaar kar rahe hain.")
    if len(lines) == 1:
        lines.append("Aaj koi trial / delivery nahi." if open_n else "Koi chalu order nahi.")
    return {"date": d, "nice": _nice(d), "trials": trials, "deliveries": deliveries, "late": late, "waiting_pickup": waiting,
            "week": week, "quotes_pending": len(pend), "open_orders": open_n, "text": "\n".join(lines)}


def due_mornings() -> list[str]:
    """Tailors whose morning time has come today (and who have work): marks them done for today."""
    from ..life import tz_of
    out = []
    with session() as s:
        for r in s.scalars(select(DarziSettings).where(DarziSettings.enabled.is_(True))).all():
            local = datetime.now(tz_of(r.tenant_id))
            d = local.date().isoformat()
            try:
                hh, mm = [int(x) for x in (r.morning_time or "09:30").split(":")]
            except ValueError:
                hh, mm = 9, 30
            late = (local.hour * 60 + local.minute) - (hh * 60 + mm)
            if r.last_morning != d and 0 <= late <= 180:
                r.last_morning = d
                has = s.scalars(select(DarziOrder.id).where(DarziOrder.tenant_id == r.tenant_id,
                                                            DarziOrder.status.in_(OPEN)).limit(1)).first()
                if has:
                    out.append(r.tenant_id)
    return out


def send_morning(tenant: str) -> dict[str, Any]:
    from ..events import notify
    from ..net.service import home_conv
    d = day(tenant)
    conv = home_conv(tenant)
    try:
        notify(conv, d["text"])
    except Exception:
        pass
    _publish(tenant, "darzi_day", {k: d[k] for k in ("date", "nice", "text", "quotes_pending", "open_orders")}
             | {"trials": len(d["trials"]), "deliveries": len(d["deliveries"]), "late": len(d["late"])}, conv)
    return d


# ---------------------------------------------------------------- for a customer on WhatsApp (only their own orders)
def customer_orders(tenant: str, wa_id: str) -> list[dict[str, Any]]:
    ph = _digits(wa_id)
    if len(ph) != 10:
        return []
    with session() as s:
        cs = s.scalars(select(DarziCustomer).where(DarziCustomer.tenant_id == tenant, DarziCustomer.phone == ph)).all()
        out = []
        for c in cs:
            for o in s.scalars(select(DarziOrder).where(DarziOrder.tenant_id == tenant, DarziOrder.customer_id == c.id)
                               .order_by(DarziOrder.created_at.desc()).limit(10)).all():
                if o.status == "cancelled":
                    continue
                if o.status == "delivered" and o.delivered_on and o.delivered_on < (today(tenant) - timedelta(days=30)).isoformat():
                    continue
                its = _j(o.items, [])
                out.append({"number": o.number, "what": ", ".join(f"{i.get('qty', 1)} {i.get('label')}" for i in its),
                            "status": STATUS_LABEL.get(o.status, o.status), "ready": o.status == "ready",
                            "trial": _nice(o.trial_on) if o.trial_on else "", "delivery": _nice(o.deliver_on),
                            "balance": _rs(max(0, o.total_paise - o.paid_paise))})
        return out


def prompt_block(tenant: str) -> str:
    """One line for the system prompt when she runs a tailoring business (so Hoola uses the darzi tools)."""
    with session() as s:
        r = s.get(DarziSettings, tenant)
        if r is None or not r.enabled:
            return ""
        n = len(s.scalars(select(DarziOrder.id).where(DarziOrder.tenant_id == tenant, DarziOrder.status.in_(OPEN))).all())
    return f"DARZI: she runs a tailoring shop ({n} open orders); use darzi / darzi_dekho for orders, measurements, trials, prices."
