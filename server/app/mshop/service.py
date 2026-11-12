"""v0.88 Mobile Dukaan Sahayak: a mobile recharge + repair shop's coworker.

  1. Gets the job: she tells Hoola (chat / call) or forwards a photo / bill / the customer's message.
  2. Logs every repair job with photos: customer, phone, brand / model, IMEI (Luhn-checked), fault, what was handed over
     (SIM, memory card, cover, charger), condition, intake photos and photos at delivery, kept in the shop's own store
     (chat files vanish after 24 h; these are warranty proof).
  3. Tells the customer when it is ready, checked against her rules and earlier work: promised date vs how long this
     fault really took, a device coming back inside its warranty, the same IMEI already open, price from her list and
     what this model + fault cost before.
  4. Keeps warranty dates per part / fault (her days), so "warranty hai kya?" has an answer by IMEI or phone.
  5. Waits for her Haan on charging the customer: Hoola prepares the bill (parts + labour + GST if she is registered),
     she approves or changes it; only then the 'ready' message with the amount + her UPI link becomes a draft she sends.
     Money only moves on the customer's own tap.
  6. Delivers and learns: delivery closes the job with a log and warranty; days / charges per model + fault and comebacks
     feed the next estimate. Recharges are logged with validity and commission; plans about to expire become reminder
     drafts (she sends). Hoola never recharges or pays itself.

Never: changing / repairing an IMEI (Telecommunications Act 2023 s.42(3)(c): up to 3 years + Rs 50 lakh), unlocking a
phone (FRP / iCloud / pattern) without proof that it is the customer's, keeping a customer's phone passcode.
"""
from __future__ import annotations

import io
import json
import logging
import re
import statistics
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger("santosh.mshop")
_LOCK = threading.Lock()
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

# fault id -> label, words, default warranty days, usual days to fix
FAULTS: dict[str, dict] = {
    "display": {"label": "Display / touch", "words": ("display", "screen", "touch", "combo", "folder", "lcd", "amoled", "oled",
                                                       "crack", "toota", "tuta", "glass", "lines", "black screen"), "warranty": 30, "days": 1},
    "battery": {"label": "Battery", "words": ("battery", "backup", "phool", "swell", "drain", "charge nahi tikta"), "warranty": 90, "days": 1},
    "charging_port": {"label": "Charging port", "words": ("charging", "charge nahi", "port", "c type", "type c", "usb", "jack"),
                      "warranty": 30, "days": 1},
    "speaker": {"label": "Speaker / ringer / earpiece", "words": ("speaker", "ringer", "earpiece", "awaaz", "sound", "aawaz"),
                "warranty": 30, "days": 1},
    "mic": {"label": "Mic", "words": ("mic", "microphone"), "warranty": 30, "days": 1},
    "camera": {"label": "Camera", "words": ("camera", "lens", "photo blur"), "warranty": 30, "days": 2},
    "back_panel": {"label": "Back panel / body", "words": ("back panel", "back glass", "body", "housing", "frame", "back cover"),
                   "warranty": 7, "days": 1},
    "buttons": {"label": "Buttons", "words": ("button", "power key", "volume key", "power button"), "warranty": 30, "days": 1},
    "network": {"label": "Network / SIM", "words": ("network", "sim", "signal", "antenna", "no service"), "warranty": 15, "days": 2},
    "water": {"label": "Water damage", "words": ("water", "paani", "pani", "geela", "liquid", "bhig"), "warranty": 0, "days": 3},
    "software": {"label": "Software / hang / dead", "words": ("software", "hang", "restart", "update", "flash", "virus", "logo",
                                                              "dead", "bootloop", "slow"), "warranty": 7, "days": 1},
    "motherboard": {"label": "Motherboard / IC", "words": ("ic", "board", "motherboard", "short", "dead set", "emmc"),
                    "warranty": 30, "days": 4},
    "unlock": {"label": "Lock / FRP / pattern hatana", "words": ("frp", "google lock", "icloud", "pattern", "password bhool",
                                                                 "unlock", "lock khol"), "warranty": 0, "days": 1},
    "other": {"label": "Something else", "words": (), "warranty": 7, "days": 2},
}
STATUSES = ("received", "diagnosing", "waiting_customer", "waiting_part", "repairing", "ready", "delivered", "returned", "cancelled")
STATUS_LABEL = {"received": "Received", "diagnosing": "Checking", "waiting_customer": "Waiting for customer's approval",
                "waiting_part": "Waiting for part", "repairing": "Repair in progress", "ready": "Ready", "delivered": "Handed over",
                "returned": "Returned unrepaired", "cancelled": "Cancelled"}
OPEN = ("received", "diagnosing", "waiting_customer", "waiting_part", "repairing", "ready")
ACCESSORIES = ("sim", "memory_card", "cover", "charger", "cable", "earphone", "box", "back_cover")
OPERATORS = {"jio": "Jio", "airtel": "Airtel", "vi": "Vi", "bsnl": "BSNL", "mtnl": "MTNL"}
DEFAULT_TERMS = ("The customer is responsible for the data on the phone. No warranty on a water-damaged phone. "
                 "The shop is not responsible if a ready phone is not collected within {unclaimed} days. "
                 "Warranty covers only the replaced part, not breakage / water damage.")
DEFAULT_READY = ("Hello {name}, your {device} is ready ({work}). Total {amount}{balance_line}. "
                 "Please collect it from {shop}. Job no. {number}.")
IMEI_CHANGE = re.compile(r"imei\s*(?:change|badal|repair|write|likh|null|fix|thik)|(?:change|badal|repair|write|null|fix)\s*(?:the\s*)?imei", re.I)
PASSCODE = re.compile(r"((?:pass(?:word|code)?|pattern|pin|lock)\s*(?:code|no\.?|number)?\s*(?:hai|is|:|=|-)?\s*)"
                      r"((?=[0-9A-Za-z]*\d)[0-9A-Za-z]{3,12})", re.I)


class MShopError(Exception):
    pass


class MShopSettings(Base):
    __tablename__ = "mshop_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    shop_name: Mapped[str] = mapped_column(String(120), default="")
    gstin: Mapped[str] = mapped_column(String(20), default="")
    gst_on: Mapped[bool] = mapped_column(Boolean, default=False)              # 18% on repair (SAC 998716) when registered
    prices: Mapped[str] = mapped_column(Text, default="{}")                   # {"display": 1500, "battery": 900, ...} labour+part guide
    warranty: Mapped[str] = mapped_column(Text, default="{}")                 # {fault: days} her own
    fix_days: Mapped[str] = mapped_column(Text, default="{}")                 # {fault: days} her own
    jobs_per_day: Mapped[int] = mapped_column(Integer, default=0)             # 0 = no limit
    unclaimed_days: Mapped[int] = mapped_column(Integer, default=30)
    commission: Mapped[str] = mapped_column(Text, default="{}")               # {operator: percent}
    remind_days: Mapped[int] = mapped_column(Integer, default=2)              # recharge reminder this many days before expiry
    terms: Mapped[str] = mapped_column(Text, default="")
    ready_template: Mapped[str] = mapped_column(Text, default="")
    rules: Mapped[str] = mapped_column(Text, default="[]")
    morning_time: Mapped[str] = mapped_column(String(5), default="10:00")
    last_morning: Mapped[str] = mapped_column(String(10), default="")
    seq: Mapped[int] = mapped_column(Integer, default=0)


class MShopCustomer(Base):
    __tablename__ = "mshop_customers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RepairJob(Base):
    __tablename__ = "mshop_jobs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mj"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    customer_id: Mapped[str] = mapped_column(String(40), index=True)
    brand: Mapped[str] = mapped_column(String(40), default="")
    model: Mapped[str] = mapped_column(String(80), default="")
    imei: Mapped[str] = mapped_column(String(20), default="", index=True)
    problem: Mapped[str] = mapped_column(Text, default="")
    faults: Mapped[str] = mapped_column(Text, default="[]")
    accessories: Mapped[str] = mapped_column(Text, default="[]")
    condition: Mapped[str] = mapped_column(Text, default="")
    proof: Mapped[str] = mapped_column(String(200), default="")              # ownership proof for unlock jobs (bill / box seen)
    status: Mapped[str] = mapped_column(String(20), default="received")
    received_on: Mapped[str] = mapped_column(String(10), default="")
    promised_on: Mapped[str] = mapped_column(String(10), default="")
    estimate_paise: Mapped[int] = mapped_column(Integer, default=0)
    customer_ok: Mapped[bool] = mapped_column(Boolean, default=False)        # customer agreed to the estimate
    parts: Mapped[str] = mapped_column(Text, default="[]")                   # [{name, price_paise, cost_paise, warranty_days}]
    labour_paise: Mapped[int] = mapped_column(Integer, default=0)
    bill: Mapped[str] = mapped_column(Text, default="{}")                    # {lines, gst, total, status pending|approved|rejected}
    paid_paise: Mapped[int] = mapped_column(Integer, default=0)
    warranty_of: Mapped[str] = mapped_column(String(40), default="")         # earlier job this is a warranty claim of
    warranty_until: Mapped[str] = mapped_column(String(10), default="")
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_on: Mapped[str] = mapped_column(String(10), default="")
    technician: Mapped[str] = mapped_column(String(60), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class RepairPhoto(Base):
    __tablename__ = "mshop_photos"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    job_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(8), default="in")               # in | out | part
    path: Mapped[str] = mapped_column(String(300), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Recharge(Base):
    __tablename__ = "mshop_recharges"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="", index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    operator: Mapped[str] = mapped_column(String(12), default="")
    amount_paise: Mapped[int] = mapped_column(Integer, default=0)
    validity_days: Mapped[int] = mapped_column(Integer, default=0)
    plan: Mapped[str] = mapped_column(String(200), default="")
    via: Mapped[str] = mapped_column(String(40), default="")                 # Jio POS Plus / Airtel Mitra / Vi app / UPI...
    day: Mapped[str] = mapped_column(String(10), index=True)
    expires_on: Mapped[str] = mapped_column(String(10), default="", index=True)
    commission_paise: Mapped[int] = mapped_column(Integer, default=0)
    reminded: Mapped[bool] = mapped_column(Boolean, default=False)
    void: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ---------------------------------------------------------------- helpers
def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _tz(tenant: str):
    from ..life import tz_of
    return tz_of(tenant)


def today(tenant: str) -> date:
    return datetime.now(_tz(tenant)).date()


def _rs(paise: int) -> str:
    r = int(paise or 0) / 100
    return f"₹{int(r):,}" if r == int(r) else f"₹{r:,.2f}"


def _paise(v) -> int:
    if v in (None, ""):
        return 0
    try:
        return int(round(float(str(v).replace(",", "").replace("₹", "").replace("Rs", "").replace("rs", "").strip()) * 100))
    except ValueError:
        raise MShopError(f"'{v}' does not look like an amount in rupees.")


def _digits(p: str) -> str:
    d = re.sub(r"\D", "", str(p or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d[-10:] if len(d) >= 10 else d


def _date(tenant: str, v: str | None, field: str = "date") -> str:
    from ..darzi import service as dz
    try:
        return dz._date(tenant, v, field)
    except dz.DarziError as e:
        raise MShopError(str(e))


def _nice(d: str) -> str:
    try:
        x = date.fromisoformat(d)
    except (TypeError, ValueError):
        return d or "-"
    return f"{DAYS[x.weekday()]} {x.day:02d}/{x.month:02d}"


def imei_ok(imei: str) -> bool:
    """15-digit IMEI with a valid Luhn check digit."""
    d = re.sub(r"\D", "", imei or "")
    if len(d) != 15:
        return False
    total = 0
    for i, ch in enumerate(d):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            n = n - 9 if n > 9 else n
        total += n
    return total % 10 == 0


def faults_of(text: str, given: list[str] | None = None) -> list[str]:
    out = [f for f in (given or []) if f in FAULTS]
    t = " " + re.sub(r"\s+", " ", str(text or "").lower()) + " "
    for fid, spec in FAULTS.items():
        if fid in out or fid == "other":
            continue
        if any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t) for w in spec["words"]):
            out.append(fid)
    return out or ["other"]


def _scrub(text: str) -> tuple[str, bool]:
    """A passcode written into notes is removed (Hoola never keeps a customer's lock code)."""
    out, n = PASSCODE.subn(lambda m: m.group(1) + "[removed]", text or "")
    return out, n > 0


def _row(s, tenant: str) -> MShopSettings:
    r = s.get(MShopSettings, tenant)
    if r is None:
        r = MShopSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def _sv(r: MShopSettings) -> dict[str, Any]:
    w = _j(r.warranty, {})
    fd = _j(r.fix_days, {})
    return {"enabled": bool(r.enabled), "shop_name": r.shop_name, "gstin": r.gstin, "gst_on": bool(r.gst_on),
            "prices": _j(r.prices, {}), "warranty": {f: int(w.get(f, spec["warranty"])) for f, spec in FAULTS.items()},
            "fix_days": {f: int(fd.get(f, spec["days"])) for f, spec in FAULTS.items()}, "jobs_per_day": r.jobs_per_day,
            "unclaimed_days": r.unclaimed_days, "commission": _j(r.commission, {}), "remind_days": r.remind_days,
            "terms": r.terms or DEFAULT_TERMS.format(unclaimed=r.unclaimed_days), "ready_template": r.ready_template or DEFAULT_READY,
            "rules": _j(r.rules, []), "morning_time": r.morning_time,
            "faults": [{"id": f, "label": s["label"]} for f, s in FAULTS.items()],
            "operators": [{"id": k, "label": v} for k, v in OPERATORS.items()]}


def settings(tenant: str) -> dict[str, Any]:
    with session() as s:
        return _sv(_row(s, tenant))


def _shop(tenant: str, r: MShopSettings) -> str:
    if r.shop_name:
        return r.shop_name
    try:
        from ..employee import service as emp
        return (emp.profile(tenant) or {}).get("business_name") or "the shop"
    except Exception:
        return "the shop"


def save_settings(tenant: str, **kw: Any) -> dict[str, Any]:
    with session() as s:
        r = _row(s, tenant)
        for k in ("shop_name", "terms", "ready_template", "morning_time"):
            if kw.get(k) is not None:
                v = str(kw[k]).strip()
                if k == "morning_time" and v and not re.fullmatch(r"\d{1,2}:\d{2}", v):
                    raise MShopError("Give the morning time as HH:MM.")
                setattr(r, k, v[:2000])
        if kw.get("gstin") is not None:
            g = str(kw["gstin"]).strip().upper()
            if g and not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", g):
                raise MShopError("The GSTIN does not look right (15 characters).")
            r.gstin = g
        if kw.get("gst_on") is not None:
            r.gst_on = bool(kw["gst_on"])
            if r.gst_on and not r.gstin:
                raise MShopError("Add the GSTIN first to charge GST.")
        if kw.get("enabled") is not None:
            r.enabled = bool(kw["enabled"])
        for k, lo, hi in (("jobs_per_day", 0, 500), ("unclaimed_days", 1, 365), ("remind_days", 0, 15)):
            if kw.get(k) is not None:
                try:
                    v = int(kw[k])
                except (TypeError, ValueError):
                    raise MShopError(f"{k} must be a number.")
                if not lo <= v <= hi:
                    raise MShopError(f"{k} must be between {lo} and {hi}.")
                setattr(r, k, v)
        for k in ("prices", "warranty", "fix_days", "commission"):
            if kw.get(k):
                cur = _j(getattr(r, k), {})
                for key, v in dict(kw[k]).items():
                    key = str(key).lower().strip()
                    if k == "commission":
                        key = key if key in OPERATORS else ""
                    else:
                        key = key if key in FAULTS else faults_of(key)[0]
                    if not key:
                        continue
                    if v in (None, ""):
                        cur.pop(key, None)
                    else:
                        try:
                            num = float(v)
                        except (TypeError, ValueError):
                            raise MShopError(f"{k}: '{v}' is not a number.")
                        if num < 0 or num > (100 if k == "commission" else 1_000_000):
                            raise MShopError(f"{k}: {v} is not valid.")
                        cur[key] = num if k in ("prices", "commission") else int(num)
                setattr(r, k, json.dumps(cur))
        if kw.get("rules") is not None:
            r.rules = json.dumps([str(x).strip()[:300] for x in kw["rules"] or [] if str(x).strip()][:30], ensure_ascii=False)
        return _sv(r)


def _customer(s, tenant: str, name: str = "", phone: str = "") -> MShopCustomer:
    ph = _digits(phone)
    c = None
    if len(ph) == 10:
        c = s.scalars(select(MShopCustomer).where(MShopCustomer.tenant_id == tenant, MShopCustomer.phone == ph)).first()
    if c is None and name.strip() and not ph:
        rows = [x for x in s.scalars(select(MShopCustomer).where(MShopCustomer.tenant_id == tenant)).all()
                if x.name.lower() == name.strip().lower()]
        c = rows[0] if len(rows) == 1 else None
    if c is None:
        if not name.strip() and len(ph) != 10:
            raise MShopError("The customer's name or a 10-digit phone number is needed.")
        c = MShopCustomer(tenant_id=tenant, name=(name.strip() or ph)[:120], phone=ph)
        s.add(c)
        s.flush()
    elif name.strip() and c.name == c.phone:
        c.name = name.strip()[:120]
    return c


def _log(j: RepairJob, what: str, by: str = "owner") -> None:
    lg = _j(j.log, [])
    lg.append({"at": now().isoformat(timespec="seconds"), "what": what[:300], "by": by})
    j.log = json.dumps(lg[-200:], ensure_ascii=False)


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("mshop publish failed")


# ---------------------------------------------------------------- earlier work
def _history(s, tenant: str, brand: str, model: str, faults: list[str]) -> dict[str, Any]:
    """Charges and days for the same fault (same model first), from delivered jobs."""
    rows = s.scalars(select(RepairJob).where(RepairJob.tenant_id == tenant, RepairJob.status == "delivered")
                     .order_by(RepairJob.updated_at.desc()).limit(400)).all()
    same_model, same_fault = [], []
    for j in rows:
        jf = set(_j(j.faults, []))
        if not jf & set(faults):
            continue
        total = int(_j(j.bill, {}).get("total_paise") or 0)
        try:
            days = (date.fromisoformat(j.delivered_on) - date.fromisoformat(j.received_on)).days if not j.ready_at else \
                (j.ready_at.date() - date.fromisoformat(j.received_on)).days
        except (TypeError, ValueError):
            days = None
        rec = {"total": total, "days": days}
        same_fault.append(rec)
        if model and j.model.lower() == model.lower() and (not brand or j.brand.lower() == brand.lower()):
            same_model.append(rec)
    base = same_model if len(same_model) >= 1 else same_fault
    totals = [x["total"] for x in base if x["total"]]
    days = [x["days"] for x in base if x["days"] is not None]
    return {"n": len(base), "model_match": bool(same_model), "charge": int(statistics.median(totals)) if totals else 0,
            "days": round(statistics.mean(days)) if days else None}


def _comebacks(s, tenant: str, fault: str) -> tuple[int, int]:
    rows = s.scalars(select(RepairJob).where(RepairJob.tenant_id == tenant, RepairJob.status == "delivered")).all()
    done = [j for j in rows if fault in _j(j.faults, [])]
    back = [j for j in rows if j.warranty_of and fault in _j(j.faults, [])]
    return len(back), len(done)


def _warranty_hit(s, tenant: str, imei: str, phone: str, faults: list[str]) -> RepairJob | None:
    t = today(tenant).isoformat()
    q = select(RepairJob).where(RepairJob.tenant_id == tenant, RepairJob.status == "delivered", RepairJob.warranty_until >= t)
    for j in s.scalars(q.order_by(RepairJob.updated_at.desc())).all():
        same_dev = (imei and j.imei == imei) or (not imei and phone and (s.get(MShopCustomer, j.customer_id) or MShopCustomer()).phone == phone)
        if same_dev and set(_j(j.faults, [])) & set(faults):
            return j
    return None


# ---------------------------------------------------------------- repair jobs
def _photo_view(p: RepairPhoto) -> dict:
    return {"id": p.id, "kind": p.kind, "note": p.note, "url": f"/api/mshop/photos/{p.id}", "at": p.created_at.isoformat()}


def _job_view(s, j: RepairJob, full: bool = True) -> dict[str, Any]:
    c = s.get(MShopCustomer, j.customer_id)
    bill = _j(j.bill, {})
    total = int(bill.get("total_paise") or 0) if bill.get("status") == "approved" else 0
    v = {"id": j.id, "number": j.number, "status": j.status, "status_label": STATUS_LABEL.get(j.status, j.status),
         "customer": {"id": c.id, "name": c.name, "phone": c.phone} if c else {"id": j.customer_id, "name": "?", "phone": ""},
         "device": f"{j.brand} {j.model}".strip() or "Phone", "brand": j.brand, "model": j.model, "imei": j.imei,
         "imei_ok": imei_ok(j.imei) if j.imei else None, "problem": j.problem,
         "faults": [{"id": f, "label": FAULTS.get(f, FAULTS["other"])["label"]} for f in _j(j.faults, [])],
         "accessories": _j(j.accessories, []), "condition": j.condition, "proof": j.proof, "received_on": j.received_on,
         "promised_on": j.promised_on, "promised_nice": _nice(j.promised_on), "estimate": _rs(j.estimate_paise) if j.estimate_paise else "",
         "customer_ok": j.customer_ok, "parts": _j(j.parts, []), "labour": _rs(j.labour_paise), "bill": bill,
         "total": _rs(total) if total else "", "paid": _rs(j.paid_paise), "balance": _rs(max(0, total - j.paid_paise)) if total else "",
         "balance_paise": max(0, total - j.paid_paise) if total else 0, "warranty_of": j.warranty_of,
         "warranty_until": j.warranty_until, "warranty_nice": _nice(j.warranty_until) if j.warranty_until else "",
         "delivered_on": j.delivered_on, "technician": j.technician, "notes": j.notes, "created_at": j.created_at.isoformat()}
    if j.status in OPEN and j.promised_on:
        try:
            left = (date.fromisoformat(j.promised_on) - today(j.tenant_id)).days
            v["days_left"], v["late"] = left, left < 0 and j.status != "ready"
        except ValueError:
            pass
    if j.status == "ready" and j.ready_at:
        ra = j.ready_at if j.ready_at.tzinfo else j.ready_at.replace(tzinfo=timezone.utc)
        v["waiting_days"] = (now() - ra).days
    if full:
        v["photos"] = [_photo_view(p) for p in s.scalars(select(RepairPhoto).where(RepairPhoto.job_id == j.id)
                                                           .order_by(RepairPhoto.created_at)).all()]
        v["log"] = _j(j.log, [])[-40:]
    return v


def _get(s, tenant: str, ref: str) -> RepairJob:
    ref = str(ref or "").strip()
    j = s.get(RepairJob, ref) if ref else None
    if j is None and ref:
        num = ref.upper().replace(" ", "")
        if re.fullmatch(r"\d+", num):
            num = f"M-{int(num):04d}"
        elif re.fullmatch(r"M-?\d+", num):
            num = f"M-{int(num.replace('M', '').replace('-', '')):04d}"
        j = s.scalars(select(RepairJob).where(RepairJob.tenant_id == tenant, RepairJob.number == num)).first()
        if j is None and re.fullmatch(r"\d{15}", ref):
            j = s.scalars(select(RepairJob).where(RepairJob.tenant_id == tenant, RepairJob.imei == ref)
                          .order_by(RepairJob.created_at.desc())).first()
    if j is None or j.tenant_id != tenant:
        raise MShopError(f"Repair job '{ref}' not found.")
    return j


def check_job(tenant: str, problem: str = "", faults: list[str] | None = None, brand: str = "", model: str = "",
              imei: str = "", phone: str = "", promised_on: str = "", proof: str = "") -> dict[str, Any]:
    """What her rules and earlier work say before promising a date / price."""
    fs = faults_of(problem, faults)
    problems, notes = [], []
    imei_d = re.sub(r"\D", "", imei or "")
    if IMEI_CHANGE.search(problem or ""):
        problems.append("Changing / writing an IMEI is against the law (Telecommunications Act 2023, section 42(3)(c): up to 3 years in "
                        "jail and a fine of up to ₹50 lakh). Do not take this job.")
    if "unlock" in fs and not proof.strip():
        problems.append("Before removing a lock / FRP / iCloud, see proof that this phone belongs to this customer (bill / box / ID) "
                        "and write it in 'proof'.")
    if imei_d and not imei_ok(imei_d):
        notes.append("The IMEI does not look like a valid 15-digit number (check digit wrong). Dial *#06# on the phone and check again; "
                     "to know if it is genuine: SMS 'KYM <IMEI>' to 14422.")
    t = today(tenant)
    with session() as s:
        sv = _sv(_row(s, tenant))
        need = max(sv["fix_days"].get(f, 1) for f in fs)
        h = _history(s, tenant, brand, model, fs)
        if h["days"] is not None and h["days"] > need:
            notes.append(f"The last {h['n']} such jobs actually took ~{h['days']} days (rule {need}).")
            need = h["days"]
        price = sum(float(sv["prices"].get(f) or 0) for f in fs)
        if h["charge"]:
            notes.append(f"{'This model' if h['model_match'] else 'This kind of work'}, last {h['n']} jobs: median bill {_rs(h['charge'])}.")
        if price:
            notes.append(f"From your list: {_rs(int(price * 100))}.")
        for f in fs:
            back, done = _comebacks(s, tenant, f)
            if done >= 5 and back / done >= 0.2:
                notes.append(f"{FAULTS[f]['label']}: {back}/{done} phones came back under warranty: check the part / supplier.")
        w = _warranty_hit(s, tenant, imei_d, _digits(phone), fs)
        if w is not None:
            notes.append(f"This phone was repaired in {w.number}, warranty until {_nice(w.warranty_until)}: warranty claim "
                         "(no charge for the part, only if the owner agrees).")
        if imei_d:
            dup = s.scalars(select(RepairJob).where(RepairJob.tenant_id == tenant, RepairJob.imei == imei_d,
                                                    RepairJob.status.in_(OPEN))).first()
            if dup is not None:
                problems.append(f"This phone (IMEI) is already in the shop as job {dup.number}.")
        earliest = t + timedelta(days=need)
        cap = sv["jobs_per_day"]
        if cap:
            for _ in range(60):
                n = len(s.scalars(select(RepairJob.id).where(RepairJob.tenant_id == tenant, RepairJob.promised_on == earliest.isoformat(),
                                                             RepairJob.status.in_(OPEN))).all())
                if n < cap:
                    break
                earliest += timedelta(days=1)
        pr = _date(tenant, promised_on, "Date") if promised_on else ""
        if pr:
            if pr < t.isoformat():
                problems.append(f"{_nice(pr)} has already passed.")
            elif pr < earliest.isoformat():
                problems.append(f"{_nice(pr)} is too soon: by the rule / past jobs the earliest is {_nice(earliest.isoformat())}.")
    return {"faults": fs, "problems": problems, "notes": notes, "earliest": earliest.isoformat(), "earliest_nice": _nice(earliest.isoformat()),
            "estimate_paise": int(price * 100) or h["charge"], "estimate": _rs(int(price * 100) or h["charge"]) if (price or h["charge"]) else "",
            "warranty_claim_of": w.id if w is not None else "", "your_rules": sv["rules"], "promised_on": pr, "ok": not problems}


def new_job(tenant: str, name: str = "", phone: str = "", brand: str = "", model: str = "", imei: str = "", problem: str = "",
            faults: list[str] | None = None, accessories: list[str] | None = None, condition: str = "", promised_on: str = "",
            estimate=None, advance=None, proof: str = "", photos: list[str] | None = None, technician: str = "",
            force: bool = False, by: str = "owner", conv: str = "") -> dict[str, Any]:
    """Log the repair job (job card). Rule problems come back first; force=true only after she agrees (never for IMEI)."""
    problem, scrubbed = _scrub(problem)
    condition, s2 = _scrub(condition)
    if not problem.strip():
        raise MShopError("What is wrong with the phone?")
    imei_d = re.sub(r"\D", "", imei or "")
    if not promised_on:
        promised_on = check_job(tenant, problem, faults, brand, model, imei_d, phone, "", proof)["earliest"]
    ck = check_job(tenant, problem, faults, brand, model, imei_d, phone, promised_on, proof)
    hard = [p for p in ck["problems"] if "against the law" in p or "has already passed" in p or "is already in the shop" in p]
    if hard or (ck["problems"] and not force):
        return {"saved": False, "check": ck, "say": "The job is not saved yet. " + " ".join(ck["problems"])}
    with _LOCK, session() as s:
        st = _row(s, tenant)
        c = _customer(s, tenant, name, phone)
        st.seq = (st.seq or 0) + 1
        acc = [a for a in (str(x).lower().strip().replace(" ", "_") for x in (accessories or [])) if a in ACCESSORIES]
        j = RepairJob(tenant_id=tenant, number=f"M-{st.seq:04d}", customer_id=c.id, brand=brand.strip()[:40].title(),
                      model=model.strip()[:80], imei=imei_d[:20], problem=problem.strip()[:2000], faults=json.dumps(ck["faults"]),
                      accessories=json.dumps(acc), condition=condition.strip()[:1000], proof=proof.strip()[:200],
                      received_on=today(tenant).isoformat(), promised_on=ck["promised_on"],
                      estimate_paise=_paise(estimate) if estimate not in (None, "") else ck["estimate_paise"],
                      paid_paise=_paise(advance) if advance not in (None, "") else 0, warranty_of=ck["warranty_claim_of"],
                      technician=technician.strip()[:60])
        s.add(j)
        s.flush()
        _log(j, f"Job taken: {j.brand} {j.model} - {problem[:120]}; return {_nice(j.promised_on)}"
                + (f"; advance {_rs(j.paid_paise)}" if j.paid_paise else "")
                + (f"; warranty claim of earlier job" if j.warranty_of else "")
                + ("; the owner approved outside the rule: " + " ".join(ck["problems"]) if ck["problems"] else ""), by)
        jid = j.id
    added = []
    for fid in photos or []:
        try:
            added.append(attach_chat_photo(tenant, jid, str(fid), "in"))
        except MShopError as e:
            log.info("photo skipped: %s", e)
    with session() as s:
        v = _job_view(s, s.get(RepairJob, jid))
    say = (f"Job {v['number']} saved: {v['customer']['name']}, {v['device']}, {', '.join(f['label'] for f in v['faults'])}. "
           f"Return {v['promised_nice']}" + (f", estimate {v['estimate']}" if v["estimate"] else "") + ".")
    if added:
        say += f" {len(added)} photos added."
    elif not photos:
        say += " Take photos of the phone (front, back, screen): they help with warranty."
    if scrubbed or s2:
        say += " A lock password was in the note and has been removed: Hoola never keeps a customer's password."
    if ck["notes"]:
        say += " Note: " + " ".join(ck["notes"][:4])
    _publish(tenant, "mshop", {"job": v["id"], "status": v["status"]}, conv)
    return {"saved": True, "job": v, "check": ck, "say": say}


# ---------------------------------------------------------------- photos (kept: warranty proof)
def _store_dir(tenant: str, job_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", tenant)[:64]
    p = Path("data") / "mshop" / safe / job_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def add_photo(tenant: str, job: str, data: bytes, name: str = "photo.jpg", kind: str = "in", note: str = "") -> dict:
    if not data or len(data) > 15 * 1024 * 1024:
        raise MShopError("The photo is empty or larger than 15 MB.")
    if not (data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n" or data[8:12] == b"WEBP" or data[4:12] in (b"ftypheic", b"ftypmif1")):
        raise MShopError("This does not look like a photo (JPG / PNG / WEBP / HEIC).")
    kind = kind if kind in ("in", "out", "part") else "in"
    with session() as s:
        j = _get(s, tenant, job)
        n = len(s.scalars(select(RepairPhoto.id).where(RepairPhoto.job_id == j.id)).all())
        if n >= 30:
            raise MShopError("Up to 30 photos per job.")
        ext = {b"\x89P": ".png"}.get(data[:2], ".webp" if data[8:12] == b"WEBP" else (".heic" if data[4:8] == b"ftyp" else ".jpg"))
        path = _store_dir(tenant, j.id) / f"{kind}_{n + 1:02d}{ext}"
        path.write_bytes(data)
        p = RepairPhoto(tenant_id=tenant, job_id=j.id, kind=kind, path=str(path), note=note[:200])
        s.add(p)
        _log(j, f"Photo ({'on arrival' if kind == 'in' else 'on handover' if kind == 'out' else 'part'}) added")
        s.flush()
        return _photo_view(p)


def attach_chat_photo(tenant: str, job: str, file_id: str, kind: str = "in") -> dict:
    """A photo she sent in chat (file_id) is copied into the shop's own store (chat files vanish after 24 h)."""
    from ..mailbox import service as ms
    try:
        name, _mime, data = ms.load_files(tenant, [{"type": "file", "file_id": file_id}])[0]
    except Exception as e:
        raise MShopError(f"Photo {file_id} not found: {e}")
    return add_photo(tenant, job, data, name, kind)


def photo_file(tenant: str, photo_id: str) -> tuple[Path, str]:
    with session() as s:
        p = s.get(RepairPhoto, photo_id)
        if p is None or p.tenant_id != tenant or not Path(p.path).exists():
            raise MShopError("Photo not found.")
        ext = Path(p.path).suffix.lower()
        return Path(p.path), {".png": "image/png", ".webp": "image/webp", ".heic": "image/heic"}.get(ext, "image/jpeg")


# ---------------------------------------------------------------- status, parts, the bill (her Haan), ready, deliver
def set_status(tenant: str, job: str, status: str, note: str = "", by: str = "owner", conv: str = "") -> dict[str, Any]:
    status = str(status or "").lower().strip()
    alias = {"jaanch": "diagnosing", "check": "diagnosing", "part": "waiting_part", "repair": "repairing", "taiyaar": "ready",
             "done": "ready", "de diya": "delivered", "wapas": "returned", "not repaired": "returned", "cancel": "cancelled",
             "customer": "waiting_customer", "haan baaki": "waiting_customer"}
    status = alias.get(status, status)
    if status not in STATUSES:
        raise MShopError("Status: " + " | ".join(STATUSES))
    if status == "delivered":
        return deliver(tenant, job, note=note, by=by, conv=conv)
    with session() as s:
        j = _get(s, tenant, job)
        if j.status in ("delivered", "cancelled", "returned") and status != "returned":
            raise MShopError(f"Job {j.number} is already {STATUS_LABEL[j.status]}.")
        j.status = status
        if status == "ready":
            j.ready_at = now()
        _log(j, f"Status: {STATUS_LABEL[status]}" + (f" ({note})" if note else ""), by)
        s.flush()
        v = _job_view(s, j, False)
    out: dict[str, Any] = {"job": v, "say": f"Job {v['number']} is now: {v['status_label']}."}
    if status == "waiting_customer":
        out["draft"] = estimate_message(tenant, v["id"])
        out["say"] += " A draft message with the estimate is ready for the customer."
    if status == "ready":
        b = prepare_bill(tenant, v["id"], conv=conv)
        out["bill"] = b["bill"]
        out["say"] += f" Bill {b['bill']['total']} is ready; the 'ready' message goes to the customer only after your approval."
    _publish(tenant, "mshop", {"job": v["id"], "status": status}, conv)
    return out


def add_part(tenant: str, job: str, name: str, price=None, cost=None, warranty_days: int | None = None, labour=None,
             by: str = "owner") -> dict[str, Any]:
    """A part used (what the customer pays, what it cost her) and/or the labour charge."""
    with session() as s:
        j = _get(s, tenant, job)
        parts = _j(j.parts, [])
        if name and name.strip():
            f = faults_of(name)[0]
            sv = _sv(_row(s, tenant))
            parts.append({"name": name.strip()[:80], "price_paise": _paise(price), "cost_paise": _paise(cost),
                          "warranty_days": int(warranty_days) if warranty_days is not None else sv["warranty"].get(f, 7),
                          "fault": f})
            j.parts = json.dumps(parts, ensure_ascii=False)
            _log(j, f"Part: {name}" + (f" {_rs(_paise(price))}" if price not in (None, "") else ""), by)
        if labour not in (None, ""):
            j.labour_paise = _paise(labour)
            _log(j, f"Labour {_rs(j.labour_paise)}", by)
        s.flush()
        v = _job_view(s, j, False)
    return {"job": v, "say": f"Job {v['number']}: likh liya."}


def prepare_bill(tenant: str, job: str, conv: str = "") -> dict[str, Any]:
    """Hoola prepares what to charge (parts + labour, GST if registered); it waits for her Haan (card)."""
    with session() as s:
        j = _get(s, tenant, job)
        st = _row(s, tenant)
        sv = _sv(st)
        parts = _j(j.parts, [])
        lines = [{"what": p["name"], "paise": int(p.get("price_paise") or 0)} for p in parts if int(p.get("price_paise") or 0)]
        if j.labour_paise:
            lines.append({"what": "Labour / service", "paise": j.labour_paise})
        why = []
        if not lines:
            fs = _j(j.faults, [])
            h = _history(s, tenant, j.brand, j.model, fs)
            base = j.estimate_paise or sum(int(float(sv["prices"].get(f) or 0) * 100) for f in fs) or h["charge"]
            if base:
                lines.append({"what": ", ".join(FAULTS.get(f, FAULTS["other"])["label"] for f in fs), "paise": base})
                why.append("From the estimate / your list / past jobs" if not j.estimate_paise else "The estimate told to the customer")
        if j.warranty_of:
            why.append("Warranty claim: if you wish, do not charge for the part (tap No and change the price).")
        sub = sum(x["paise"] for x in lines)
        gst = int(round(sub * 0.18)) if st.gst_on else 0
        bill = {"lines": lines, "subtotal_paise": sub, "gst_paise": gst, "total_paise": sub + gst, "total": _rs(sub + gst),
                "status": "pending", "why": why, "gst_note": "GST 18% (SAC 998716)" if st.gst_on else ""}
        if not sub:
            bill["status"] = "needs_price"
        j.bill = json.dumps(bill, ensure_ascii=False)
        _log(j, f"Bill ready {bill['total']} (owner's approval pending)")
        s.flush()
        v = _job_view(s, j, False)
    card = {"job_id": v["id"], "number": v["number"], "customer": v["customer"]["name"], "device": v["device"],
            "paid": v["paid"], **bill}
    _publish(tenant, "mshop_bill", card, conv)
    return {"bill": card, "say": f"{v['number']} bill {bill['total']}: waiting for your approval."}


def decide_bill(tenant: str, job: str, approve: bool, total=None, conv: str = "") -> dict[str, Any]:
    """Her Haan / change / Mana on the bill (only from her tap or her own words as the owner)."""
    with session() as s:
        j = _get(s, tenant, job)
        bill = _j(j.bill, {})
        if not bill:
            raise MShopError("No bill has been made yet.")
        if not approve:
            bill["status"] = "rejected"
            j.bill = json.dumps(bill, ensure_ascii=False)
            _log(j, "Bill: declined by the owner")
            v = _job_view(s, j, False)
            out = {"job": v, "say": "All right. Tell me the correct amount and I will make the bill again."}
        else:
            if total not in (None, ""):
                new = _paise(total)
                if new <= 0:
                    raise MShopError("The amount is not right.")
                if new != bill.get("total_paise"):
                    bill["lines"] = [{"what": "Total (set by the owner)", "paise": new}]
                    bill["subtotal_paise"], bill["gst_paise"], bill["total_paise"] = new, 0, new
                    bill["total"] = _rs(new)
            if not bill.get("total_paise"):
                raise MShopError("Give the bill amount.")
            bill["status"] = "approved"
            j.bill = json.dumps(bill, ensure_ascii=False)
            _log(j, f"Bill confirmed (owner's approval): {bill['total']}")
            s.flush()
            v = _job_view(s, j, False)
            out = {"job": v, "say": f"{v['number']}: {bill['total']} confirmed."}
    card = {"job_id": v["id"], "number": v["number"], "customer": v["customer"]["name"], "device": v["device"], "paid": v["paid"], **bill}
    _publish(tenant, "mshop_bill", card, conv)
    if approve and v["status"] == "ready":
        out["ready"] = ready_card(tenant, v["id"], conv)
        out["say"] += " The 'ready' message draft is on the card: you send it."
    return out


def _upi_link(tenant: str, paise: int, note: str) -> str:
    try:
        from ..employee import service as emp
        p = emp.profile(tenant) or {}
        upi, nm = p.get("upi_id") or "", p.get("upi_name") or p.get("business_name") or ""
    except Exception:
        upi, nm = "", ""
    if not upi or paise <= 0:
        return ""
    return f"upi://pay?pa={quote(upi)}&pn={quote(nm)}&am={paise / 100:.2f}&cu=INR&tn={quote(note[:40])}"


def ready_card(tenant: str, job: str, conv: str = "") -> dict[str, Any]:
    """'Phone taiyaar hai' with the approved amount: a draft she sends (her WhatsApp / SMS / business WhatsApp)."""
    with session() as s:
        j = _get(s, tenant, job)
        st = _row(s, tenant)
        bill = _j(j.bill, {})
        if bill.get("status") != "approved":
            raise MShopError("Your approval on the bill is needed first (Hoola does not quote a price without approval).")
        v = _job_view(s, j, False)
        bal = v["balance_paise"]
        tpl = st.ready_template or DEFAULT_READY
        vals = {"name": v["customer"]["name"].split(" ")[0], "device": v["device"],
                "work": ", ".join(f["label"] for f in v["faults"]), "amount": bill["total"],
                "balance_line": (f", balance {_rs(bal)}" if bal and bal != bill["total_paise"] else ""),
                "shop": _shop(tenant, st), "number": v["number"]}
        try:
            text = tpl.format(**vals)
        except (KeyError, IndexError, ValueError):
            text = DEFAULT_READY.format(**vals)
        upi = _upi_link(tenant, bal, f"{v['number']} repair")
    ph = v["customer"]["phone"]
    card = {"job_id": v["id"], "number": v["number"], "customer": v["customer"]["name"], "phone": ph, "text": text,
            "amount": bill["total"], "balance": _rs(bal), "upi_link": upi,
            "wa_link": f"https://wa.me/91{ph}?text={quote(text + (chr(10) + 'UPI: ' + upi if upi else ''))}" if len(ph) == 10 else "",
            "sms_link": f"sms:+91{ph}?body={quote(text)}" if len(ph) == 10 else "", "status": "draft"}
    _publish(tenant, "mshop_ready", card, conv)
    return card


def estimate_message(tenant: str, job: str) -> dict[str, Any]:
    with session() as s:
        j = _get(s, tenant, job)
        v = _job_view(s, j, False)
        shop = _shop(tenant, _row(s, tenant))
    text = (f"Hello {v['customer']['name'].split(' ')[0]}, your {v['device']} needs work on: "
            f"{', '.join(f['label'] for f in v['faults'])}. Estimate {v['estimate'] or '(to be told)'}"
            f", by {v['promised_nice']}. If that is fine, reply 'yes'. - {shop}")
    ph = v["customer"]["phone"]
    return {"text": text, "wa_link": f"https://wa.me/91{ph}?text={quote(text)}" if len(ph) == 10 else ""}


def customer_agreed(tenant: str, job: str, estimate=None, by: str = "owner") -> dict[str, Any]:
    with session() as s:
        j = _get(s, tenant, job)
        j.customer_ok = True
        if estimate not in (None, ""):
            j.estimate_paise = _paise(estimate)
        if j.status == "waiting_customer":
            j.status = "repairing"
        _log(j, "Customer approved the estimate", by)
        v = _job_view(s, j, False)
    return {"job": v, "say": f"{v['number']}: customer's approval recorded, work started."}


def pay(tenant: str, job: str, amount, how: str = "", by: str = "owner") -> dict[str, Any]:
    p = _paise(amount)
    if p <= 0:
        raise MShopError("How many rupees were received?")
    with session() as s:
        j = _get(s, tenant, job)
        j.paid_paise += p
        _log(j, f"Payment received: {_rs(p)}" + (f" ({how})" if how else ""), by)
        v = _job_view(s, j, False)
    return {"job": v, "say": f"{v['number']}: {_rs(p)} recorded. Total received {v['paid']}" + (f", balance {v['balance']}" if v["balance"] else "") + "."}


def deliver(tenant: str, job: str, paid_now=None, note: str = "", by: str = "owner", conv: str = "") -> dict[str, Any]:
    with session() as s:
        j = _get(s, tenant, job)
        if j.status in ("cancelled", "delivered"):
            raise MShopError(f"Job {j.number} is already {STATUS_LABEL[j.status]}.")
        if _j(j.bill, {}).get("status") != "approved" and j.status != "returned":
            raise MShopError("The bill does not have your approval: confirm the bill first (or status 'returned' if it goes back unrepaired).")
        if paid_now not in (None, ""):
            pn = _paise(paid_now)
            if pn:
                j.paid_paise += pn
                _log(j, f"Received on handover: {_rs(pn)}", by)
        sv = _sv(_row(s, tenant))
        t = today(tenant)
        days = [int(p.get("warranty_days") or 0) for p in _j(j.parts, [])] or \
               [sv["warranty"].get(f, 7) for f in _j(j.faults, [])]
        wd = max(days or [0])
        j.warranty_until = (t + timedelta(days=wd)).isoformat() if wd > 0 and j.status != "returned" else ""
        late = 0
        try:
            late = (t - date.fromisoformat(j.promised_on)).days
        except ValueError:
            pass
        j.status, j.delivered_on = ("delivered" if j.status != "returned" else "returned"), t.isoformat()
        if not j.ready_at:
            j.ready_at = now()
        took = (t - date.fromisoformat(j.received_on)).days if j.received_on else 0
        _log(j, f"Handed over ({'on time' if late <= 0 else f'{late} days late'}, {took} days)"
                + (f"; warranty until {_nice(j.warranty_until)}" if j.warranty_until else "") + (f"; {note}" if note else ""), by)
        s.flush()
        v = _job_view(s, j)
    say = f"{v['number']} handed over to {v['customer']['name']}." + (f" Warranty until {v['warranty_nice']}." if v["warranty_until"] else "")
    if v["balance_paise"] > 0:
        say += f" Balance {v['balance']} is still to be collected."
    if not any(p["kind"] == "out" for p in v.get("photos", [])):
        say += " Take a photo at handover too (for warranty)."
    _publish(tenant, "mshop", {"job": v["id"], "status": v["status"]}, conv)
    return {"job": v, "say": say}


def update_job(tenant: str, job: str, promised_on: str = "", notes: str = "", technician: str = "", imei: str = "",
               proof: str = "", estimate=None, force: bool = False, by: str = "owner") -> dict[str, Any]:
    with session() as s:
        j = _get(s, tenant, job)
        changed = []
        if promised_on:
            ck = check_job(tenant, j.problem, _j(j.faults, []), j.brand, j.model, "", "", promised_on, j.proof or proof)
            pr = ck["promised_on"]
            if ck["problems"] and not force and any("jaldi" in p or "beet" in p for p in ck["problems"]):
                return {"saved": False, "check": ck, "say": " ".join(ck["problems"])}
            j.promised_on = pr
            changed.append(f"return {_nice(pr)}")
        if notes:
            clean, sc = _scrub(notes)
            j.notes = (j.notes + "\n" + clean).strip()[-2000:]
            changed.append("note" + (" (password removed)" if sc else ""))
        if technician:
            j.technician = technician.strip()[:60]
            changed.append(f"technician {j.technician}")
        if imei:
            j.imei = re.sub(r"\D", "", imei)[:20]
            changed.append("IMEI" + ("" if imei_ok(j.imei) else " (check digit wrong)"))
        if proof:
            j.proof = proof.strip()[:200]
            changed.append("saboot")
        if estimate not in (None, ""):
            j.estimate_paise = _paise(estimate)
            changed.append(f"estimate {_rs(j.estimate_paise)}")
        _log(j, "Changed: " + ", ".join(changed or ["nothing"]), by)
        v = _job_view(s, j, False)
    return {"saved": True, "job": v, "say": f"{v['number']}: {', '.join(changed) or 'nothing changed'}."}


def get_job(tenant: str, job: str) -> dict[str, Any]:
    with session() as s:
        return _job_view(s, _get(s, tenant, job))


def jobs(tenant: str, status: str = "open", q: str = "", limit: int = 80) -> list[dict[str, Any]]:
    with session() as s:
        qq = select(RepairJob).where(RepairJob.tenant_id == tenant)
        st = (status or "").lower()
        if st in ("open", "chalu", ""):
            qq = qq.where(RepairJob.status.in_(OPEN))
        elif st in STATUSES:
            qq = qq.where(RepairJob.status == st)
        rows = s.scalars(qq.order_by(RepairJob.created_at.desc()).limit(500)).all()
        out = []
        needle = (q or "").lower().strip()
        for j in rows:
            v = _job_view(s, j, False)
            if needle and needle not in " ".join([v["number"].lower(), v["customer"]["name"].lower(), v["customer"]["phone"],
                                                   v["device"].lower(), v["imei"]]):
                continue
            out.append(v)
            if len(out) >= limit:
                break
    if st in ("open", "chalu", ""):
        out.sort(key=lambda v: (v["status"] == "ready", v.get("promised_on") or "9999"))
    return out


def warranty(tenant: str, q: str) -> dict[str, Any]:
    """Is this phone / customer under warranty? By IMEI, phone number or job number."""
    d = re.sub(r"\D", "", q or "")
    with session() as s:
        rows = s.scalars(select(RepairJob).where(RepairJob.tenant_id == tenant, RepairJob.status == "delivered")
                         .order_by(RepairJob.updated_at.desc())).all()
        hits = []
        for j in rows:
            c = s.get(MShopCustomer, j.customer_id)
            if (len(d) == 15 and j.imei == d) or (len(d) >= 10 and c and c.phone == _digits(d)) or \
                    (q and j.number.lower() == str(q).strip().lower()):
                v = _job_view(s, j, False)
                v["under_warranty"] = bool(j.warranty_until and j.warranty_until >= today(tenant).isoformat())
                v["parts_warranty"] = [{"name": p["name"], "days": p.get("warranty_days", 0)} for p in _j(j.parts, [])]
                hits.append(v)
    if not hits:
        return {"found": [], "say": "No earlier repair found for this IMEI / phone / job."}
    a = hits[0]
    say = (f"{a['number']} ({a['device']}, {_nice(a['delivered_on'])}): "
           + (f"it IS under warranty until {a['warranty_nice']}." if a["under_warranty"] else
              (f"warranty ended on {a['warranty_nice']}." if a["warranty_until"] else "this job had no warranty.")))
    return {"found": hits[:10], "say": say}


def slip_pdf(tenant: str, job: str) -> bytes:
    """Job card (intake) / bill: number, customer, device, IMEI, fault, accessories, condition, dates, money, terms."""
    from reportlab.lib.pagesizes import A5
    from reportlab.pdfgen import canvas
    with session() as s:
        j = _get(s, tenant, job)
        v = _job_view(s, j, False)
        st = _row(s, tenant)
        sv = _sv(st)
        shop = _shop(tenant, st)
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A5)
    w, h = A5
    y = h - 34

    def line(text: str, size: int = 10, bold: bool = False, gap: int = 14):
        nonlocal y
        if y < 40:
            pdf.showPage()
            y = h - 34
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(26, y, str(text).replace("₹", "Rs ").encode("latin-1", "replace").decode("latin-1")[:96])
        y -= gap

    line(shop, 14, True, 18)
    if sv["gstin"]:
        line(f"GSTIN {sv['gstin']}", 8)
    line(f"Job {v['number']}   ·   {v['received_on']}   ·   {v['status_label']}", 10, True)
    line(f"Customer: {v['customer']['name']}  {v['customer']['phone']}")
    line(f"Phone: {v['device']}   IMEI: {v['imei'] or '-'}")
    line(f"Fault: {v['problem'][:80]}")
    line(f"With it: {', '.join(v['accessories']) or 'nothing'}")
    if v["condition"]:
        line(f"Condition: {v['condition'][:85]}", 9)
    line(f"Return: {v['promised_nice']}" + (f"   Estimate: {v['estimate']}" if v["estimate"] else ""), 10, True, 18)
    bill = v["bill"]
    if bill.get("status") == "approved":
        for ln in bill.get("lines", []):
            line(f"  {ln['what'][:60]}   {_rs(ln['paise'])}")
        if bill.get("gst_paise"):
            line(f"  GST 18% (SAC 998716)   {_rs(bill['gst_paise'])}")
        line(f"Total {bill['total']}   Paid {v['paid']}   Balance {v['balance'] or _rs(0)}", 11, True)
    else:
        line(f"Advance: {v['paid']}")
    if v["warranty_until"]:
        line(f"Warranty: until {v['warranty_nice']}", 10, True)
    y -= 6
    terms = sv["terms"]
    for k in range(0, len(terms), 95):
        line(terms[k:k + 95], 7, gap=10)
    pdf.showPage()
    pdf.save()
    return buf.getvalue()


def slip_file(tenant: str, job: str, conv: str = "") -> dict[str, Any]:
    from .. import chatfiles
    v = get_job(tenant, job)
    f = chatfiles.store(tenant, f"Job-{v['number']}.pdf", slip_pdf(tenant, job), "application/pdf")
    _publish(tenant, "pc_file", {**f, "source": "mshop", "title": f"Job {v['number']}"}, conv)
    return {"file": f, "say": f"Job {v['number']} slip (PDF) is ready."}


# ---------------------------------------------------------------- recharges
def add_recharge(tenant: str, number: str, amount, operator: str = "", validity_days: int | None = None, name: str = "",
                 plan: str = "", via: str = "", day: str = "") -> dict[str, Any]:
    """A recharge she did (in Jio POS Plus / Airtel Mitra / Vi / her app): validity -> expiry reminder, commission."""
    ph = _digits(number)
    if len(ph) != 10:
        raise MShopError("A 10-digit mobile number is needed.")
    p = _paise(amount)
    if p <= 0 or p > 50000 * 100:
        raise MShopError("The recharge amount is not right.")
    op = str(operator or "").lower().strip()
    op = {"vodafone": "vi", "idea": "vi", "vodafone idea": "vi", "reliance jio": "jio"}.get(op, op)
    d = date.fromisoformat(_date(tenant, day, "Day")) if day else today(tenant)
    with session() as s:
        st = _row(s, tenant)
        if not op:
            prev = s.scalars(select(Recharge).where(Recharge.tenant_id == tenant, Recharge.number == ph, Recharge.void.is_(False))
                             .order_by(Recharge.created_at.desc())).first()
            op = prev.operator if prev else ""
            name = name or (prev.name if prev else "")
        if op and op not in OPERATORS:
            raise MShopError("Operator: jio | airtel | vi | bsnl | mtnl")
        comm = float(_j(st.commission, {}).get(op) or 0)
        vd = int(validity_days) if validity_days not in (None, "") else 0
        r = Recharge(tenant_id=tenant, number=ph, name=name.strip()[:120], operator=op, amount_paise=p, validity_days=vd,
                     plan=plan.strip()[:200], via=via.strip()[:40], day=d.isoformat(),
                     expires_on=(d + timedelta(days=vd)).isoformat() if vd else "", commission_paise=int(round(p * comm / 100)))
        s.add(r)
        s.flush()
        rid = r.id
        exp = r.expires_on
    say = (f"{OPERATORS.get(op, op or 'Recharge')} {_rs(p)} - {ph[-4:]} recorded"
           + (f", plan ends on {_nice(exp)}: I will remind you {_row_remind(tenant)} days before" if exp else
              " (tell me the validity and I will remind you before it ends)") + ".")
    return {"id": rid, "expires_on": exp, "say": say}


def _row_remind(tenant: str) -> int:
    with session() as s:
        return _row(s, tenant).remind_days


def recharges_day(tenant: str, on: str = "") -> dict[str, Any]:
    d = _date(tenant, on, "Day") if on else today(tenant).isoformat()
    with session() as s:
        rows = s.scalars(select(Recharge).where(Recharge.tenant_id == tenant, Recharge.day == d, Recharge.void.is_(False))).all()
        by_op: dict[str, dict] = {}
        for r in rows:
            b = by_op.setdefault(r.operator or "?", {"count": 0, "amount": 0, "commission": 0})
            b["count"] += 1
            b["amount"] += r.amount_paise
            b["commission"] += r.commission_paise
    tot = sum(b["amount"] for b in by_op.values())
    com = sum(b["commission"] for b in by_op.values())
    return {"date": d, "count": sum(b["count"] for b in by_op.values()), "amount": _rs(tot), "commission": _rs(com),
            "by_operator": {OPERATORS.get(k, k): {"count": v["count"], "amount": _rs(v["amount"]), "commission": _rs(v["commission"])}
                            for k, v in by_op.items()}}


def due_recharges(tenant: str, within: int | None = None) -> list[dict[str, Any]]:
    """Customers whose plan ends soon (latest recharge per number), with a reminder draft each (she sends)."""
    t = today(tenant)
    with session() as s:
        st = _row(s, tenant)
        days = st.remind_days if within is None else within
        shop = _shop(tenant, st)
        rows = s.scalars(select(Recharge).where(Recharge.tenant_id == tenant, Recharge.void.is_(False), Recharge.expires_on != "")
                         .order_by(Recharge.created_at.desc())).all()
        latest: dict[str, Recharge] = {}
        for r in rows:
            latest.setdefault(r.number, r)
        out = []
        for r in latest.values():
            left = (date.fromisoformat(r.expires_on) - t).days
            if 0 <= left <= days:
                text = (f"Hello{' ' + r.name.split(' ')[0] if r.name else ''}, your {OPERATORS.get(r.operator, '')} plan ends on "
                        f"{_nice(r.expires_on)}. For a recharge, come to {shop} or reply here.")
                out.append({"id": r.id, "number": r.number, "name": r.name, "operator": OPERATORS.get(r.operator, r.operator),
                            "last_amount": _rs(r.amount_paise), "expires_on": r.expires_on, "nice": _nice(r.expires_on),
                            "days_left": left, "reminded": r.reminded, "text": text,
                            "wa_link": f"https://wa.me/91{r.number}?text={quote(text)}"})
    return sorted(out, key=lambda x: x["expires_on"])


def mark_reminded(tenant: str, recharge_id: str) -> dict:
    with session() as s:
        r = s.get(Recharge, recharge_id)
        if r is None or r.tenant_id != tenant:
            raise MShopError("Recharge not found.")
        r.reminded = True
    return {"ok": True}


def void_recharge(tenant: str, recharge_id: str) -> dict:
    with session() as s:
        r = s.get(Recharge, recharge_id)
        if r is None or r.tenant_id != tenant:
            raise MShopError("Recharge not found.")
        r.void = True
        return {"ok": True, "say": f"Recharge of {_rs(r.amount_paise)} removed."}


def recent_recharges(tenant: str, limit: int = 60) -> list[dict]:
    with session() as s:
        rows = s.scalars(select(Recharge).where(Recharge.tenant_id == tenant, Recharge.void.is_(False))
                         .order_by(Recharge.created_at.desc()).limit(limit)).all()
        return [{"id": r.id, "number": r.number, "name": r.name, "operator": OPERATORS.get(r.operator, r.operator),
                 "amount": _rs(r.amount_paise), "validity_days": r.validity_days, "expires_on": r.expires_on,
                 "commission": _rs(r.commission_paise), "day": r.day, "via": r.via} for r in rows]


# ---------------------------------------------------------------- the day
def day(tenant: str) -> dict[str, Any]:
    t = today(tenant).isoformat()
    with session() as s:
        sv = _sv(_row(s, tenant))
        rows = s.scalars(select(RepairJob).where(RepairJob.tenant_id == tenant, RepairJob.status.in_(OPEN))).all()
        vs = [_job_view(s, j, False) for j in rows]
        pend_bills = [v for v in vs if v["bill"].get("status") in ("pending", "needs_price")]
    due_today = [v for v in vs if v["promised_on"] == t and v["status"] != "ready"]
    late = [v for v in vs if v.get("late")]
    parts = [v for v in vs if v["status"] == "waiting_part"]
    unclaimed = [v for v in vs if v["status"] == "ready" and (v.get("waiting_days") or 0) >= min(7, sv["unclaimed_days"])]
    rc = recharges_day(tenant, (today(tenant) - timedelta(days=1)).isoformat())
    due = due_recharges(tenant)
    lines = ["Mobile shop: " + _nice(t)]
    if due_today:
        lines.append("To hand back today: " + "; ".join(f"{v['customer']['name']} ({v['device']}, {v['number']})" for v in due_today))
    if late:
        lines.append("Late: " + "; ".join(f"{v['customer']['name']} {v['number']}" for v in late))
    if parts:
        lines.append("Waiting for a part: " + "; ".join(f"{v['number']} {v['device']}" for v in parts))
    if pend_bills:
        lines.append(f"{len(pend_bills)} bills are waiting for your approval.")
    if unclaimed:
        lines.append("Ready, not collected: " + "; ".join(f"{v['customer']['name']} {v['number']} ({v['waiting_days']} days)" for v in unclaimed))
    if due:
        lines.append(f"{len(due)} customers' recharges end within {sv['remind_days']} days: reminder drafts are ready.")
    if rc["count"]:
        lines.append(f"Yesterday: {rc['count']} recharges, {rc['amount']}, commission {rc['commission']}.")
    if len(lines) == 1:
        lines.append("No special work today.")
    return {"date": t, "nice": _nice(t), "open": len(vs), "due_today": due_today, "late": late, "waiting_part": parts,
            "unclaimed": unclaimed, "bills_pending": len(pend_bills), "recharge_due": due, "recharges_yesterday": rc,
            "text": "\n".join(lines)}


def due_mornings() -> list[str]:
    from ..life import tz_of
    out = []
    with session() as s:
        for r in s.scalars(select(MShopSettings).where(MShopSettings.enabled.is_(True))).all():
            local = datetime.now(tz_of(r.tenant_id))
            d = local.date().isoformat()
            try:
                hh, mm = [int(x) for x in (r.morning_time or "10:00").split(":")]
            except ValueError:
                hh, mm = 10, 0
            late = (local.hour * 60 + local.minute) - (hh * 60 + mm)
            if r.last_morning != d and 0 <= late <= 180:
                r.last_morning = d
                out.append(r.tenant_id)
    return out


def send_morning(tenant: str) -> dict[str, Any]:
    from ..events import notify
    from ..net.service import home_conv
    d = day(tenant)
    if d["open"] == 0 and not d["recharge_due"] and not d["recharges_yesterday"]["count"]:
        return d
    conv = home_conv(tenant)
    try:
        notify(conv, d["text"])
    except Exception:
        pass
    _publish(tenant, "mshop_day", {"date": d["date"], "nice": d["nice"], "text": d["text"],
                                   "recharge_due": d["recharge_due"][:20], "late": len(d["late"]),
                                   "bills_pending": d["bills_pending"]}, conv)
    return d


# ---------------------------------------------------------------- a customer on WhatsApp: only their own jobs
def customer_jobs(tenant: str, wa_id: str) -> list[dict[str, Any]]:
    ph = _digits(wa_id)
    if len(ph) != 10:
        return []
    with session() as s:
        cs = s.scalars(select(MShopCustomer).where(MShopCustomer.tenant_id == tenant, MShopCustomer.phone == ph)).all()
        out = []
        for c in cs:
            for j in s.scalars(select(RepairJob).where(RepairJob.tenant_id == tenant, RepairJob.customer_id == c.id)
                               .order_by(RepairJob.created_at.desc()).limit(10)).all():
                if j.status == "cancelled":
                    continue
                bill = _j(j.bill, {})
                out.append({"number": j.number, "device": f"{j.brand} {j.model}".strip(), "status": STATUS_LABEL.get(j.status, j.status),
                            "ready": j.status == "ready", "promised": _nice(j.promised_on),
                            "amount": bill.get("total") if bill.get("status") == "approved" else "",
                            "warranty_until": _nice(j.warranty_until) if j.warranty_until else ""})
        return out


def prompt_block(tenant: str) -> str:
    with session() as s:
        r = s.get(MShopSettings, tenant)
        if r is None or not r.enabled:
            return ""
        n = len(s.scalars(select(RepairJob.id).where(RepairJob.tenant_id == tenant, RepairJob.status.in_(OPEN))).all())
    return f"MOBILE SHOP: she runs a mobile recharge + repair shop ({n} open repair jobs); use mobile_shop / mobile_shop_dekho."
