"""Rentdesk Sahayak: Hoola as a property manager (rented flats / houses / rooms, shops / offices / godowns, PG / hostel beds).

  1. Units (U-001) and tenants (P-001; Aadhaar / PAN only as Pehchaan Locker references) -> tenancies T-0001 (leave & licence /
     rent / MTA agreement: start, months, rent, deposit, maintenance, due day, escalation, lock-in, notice) with checks (unit
     already let, deposit vs the Model Tenancy Act cap in MTA states, TDS / GST / HRA notes) and the state checklist
     (MH: IGR e-registration s.55, police information, society).
  2. Ledger: rent / maintenance charges per licence month (worker), deposit at the start, payments she marks received (allocated
     to the oldest dues, numbered receipts R/2627/0001, receipt PDF with the HRA fields), UPI link to HER UPI ID (the tenant pays
     in their own app), Galla UPI credit only as a hint, a BizDue mirror so tenants on her business WhatsApp see their own dues.
  3. Reminders: before the due day and after her grace days -> message DRAFTS (one per tenancy and stage). Every message to a
     tenant is a draft until HER tap: her own WhatsApp / SMS (wa.me / sms link) or the business number inside Meta's 24 h window.
  4. Agreement draft (Word, blanks for every fact she didn't give, "draft for your lawyer"), renewal / escalation / lock-in dates,
     notices (rent increase, renewal, vacate) -> `rentdesk_approval` card -> letter + message draft only after her tap.
  5. Repairs M-0001 (tenant / her words; category + urgency from Hinglish words) -> her vendor -> quote -> repair approval card
     (money: fingerprint once a phone key is active) -> tenant charge only when the agreement says tenant pays and she approved.
  6. Move-in / move-out inspection (rooms x items, conditions, meters, keys, photos re-encoded without EXIF / GPS) -> settlement:
     deposit held - dues - HER deductions (amounts only from her, wear and tear noted) = refund -> deduction card (fingerprint)
     -> statement PDF + refund message draft -> she pays the refund herself and taps "Maine de diya".
  Never: moving money, sending a message by itself, inventing rent / deposit / stamp duty / dates, scraping IGR / police portals."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import secrets
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from sqlalchemy import select

from ..db import new_id, now, session
from . import rules as R
from .models import (
    RdAlert,
    RdApproval,
    RdCharge,
    RdInspection,
    RdMessage,
    RdPayment,
    RdPerson,
    RdPhoto,
    RdRequest,
    RdSettings,
    RdSettlement,
    RdTenancy,
    RdUnit,
    RdVendor,
)

log = logging.getLogger("santosh.rentdesk")
_LOCK = threading.RLock()
MONEY_KINDS = ("deduction", "repair")
APPROVAL_LABEL = {"deduction": "Deposit se katauti", "rent_change": "Kiraya badlav", "notice": "Notice", "repair": "Repair kharcha"}
TENANCY_STATUS = {"draft": "Draft", "active": "Chalu", "notice": "Notice par", "ended": "Khatam", "cancelled": "Radd"}
MAX_PHOTOS = 40


class RentError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _dump(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=str, sort_keys=True)


def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def clock() -> datetime:
    return now()


def _tz(tenant: str):
    from ..life import tz_of
    return tz_of(tenant)


def today(tenant: str) -> date:
    return clock().astimezone(_tz(tenant)).date()


def _date(v) -> date | None:
    return R.parse_date(v)


def _iso(d: date | None) -> str:
    return d.isoformat() if d else ""


def _rs(v: float | None) -> str:
    if v is None:
        return ""
    try:
        from ..india.money import inr
        return inr(v)
    except Exception:
        return f"₹{v:,.0f}"


def _r2(v: float) -> float:
    return round(float(v or 0) + 1e-9, 2)


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("rentdesk publish failed")


def is_owner(actor: str) -> bool:
    a = actor or "owner"
    return a == "owner" or a.startswith("approved:")


def actor_name(tenant: str, actor: str) -> str:
    if is_owner(actor):
        return "Owner"
    try:
        from ..employee.service import actor_label
        return actor_label(tenant, actor)
    except Exception:
        return str(actor)[:40]


def _st(s, tenant: str) -> RdSettings:
    r = s.get(RdSettings, tenant)
    if r is None:
        r = RdSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def _next(s, tenant: str, key: str) -> int:
    st = _st(s, tenant)
    seq = _j(st.seq, {})
    seq[key] = int(seq.get(key, 0)) + 1
    st.seq = _dump(seq)
    return seq[key]


def _clean(text: str, n: int = 500) -> str:
    return R.scrub(text, n)


def _hash(v) -> str:
    return hashlib.sha256(_dump(v).encode()).hexdigest()


# ---------------------------------------------------------------- settings
_SET_KEYS = ("business", "landlord_name", "landlord_address", "landlord_phone", "receipt_full_pan", "state", "city", "upi_id",
             "upi_name", "gstin", "agency", "remind_before", "grace_days", "renewal_windows", "minor_repair_limit", "mirror_dues",
             "morning_time", "rules")


def _settings_view(r: RdSettings) -> dict:
    up = _upi(r)
    return {"business": r.business, "landlord_name": r.landlord_name, "landlord_address": r.landlord_address,
            "landlord_phone": r.landlord_phone, "pan": _pan_masked(r), "pan_set": bool(r.pan_ref), "receipt_full_pan": r.receipt_full_pan,
            "state": r.state, "state_label": R.state_label(r.state), "city": r.city, "upi_id": r.upi_id, "upi_name": r.upi_name,
            "upi_used": up[0], "gstin": r.gstin, "agency": r.agency, "remind_before": r.remind_before, "grace_days": r.grace_days,
            "renewal_windows": _j(r.renewal_windows, [60, 30, 15, 7]), "minor_repair_limit": r.minor_repair_limit or None,
            "mirror_dues": r.mirror_dues, "morning_time": r.morning_time, "rules": r.rules}


def _pan_masked(r: RdSettings) -> str:
    if not r.pan_ref:
        return ""
    try:
        from .. import idvault
        for x in idvault.list_(r.tenant_id):
            if x["ref"] == r.pan_ref:
                return x["masked"]
    except Exception:
        pass
    return "(locker mein)"


def _upi(r: RdSettings) -> tuple[str, str]:
    if r.upi_id:
        return r.upi_id, r.upi_name or r.landlord_name or r.business
    try:
        from ..employee import service as emp
        p = emp.profile(r.tenant_id) or {}
        return p.get("upi_id") or "", p.get("upi_name") or p.get("business_name") or r.landlord_name
    except Exception:
        return "", ""


def settings(tenant: str) -> dict:
    with session() as s:
        return _settings_view(_st(s, tenant))


def save_settings(tenant: str, pan: str = "", **kw: Any) -> dict:
    """Her settings. A PAN goes into the Pehchaan Locker (only the reference is kept)."""
    ref = ""
    if pan:
        from .. import idvault
        try:
            ref = idvault.save(tenant, "pan", pan, "self", "Rentdesk receipts")["ref"]
        except Exception as e:
            raise RentError(f"PAN sahi nahi: {e}")
    with _LOCK, session() as s:
        r = _st(s, tenant)
        for k in _SET_KEYS:
            if k not in kw or kw[k] is None:
                continue
            v = kw[k]
            if k in ("remind_before", "grace_days"):
                setattr(r, k, max(0, min(30, int(R.money(v)))))
            elif k == "minor_repair_limit":
                r.minor_repair_limit = max(0.0, R.money(v))
            elif k in ("receipt_full_pan", "agency", "mirror_dues"):
                setattr(r, k, bool(v))
            elif k == "renewal_windows":
                ws = sorted({int(R.money(x)) for x in (v if isinstance(v, list) else str(v).split(",")) if 0 < R.money(x) <= 365},
                            reverse=True)
                r.renewal_windows = _dump(ws or [60, 30, 15, 7])
            elif k == "morning_time":
                if not re.fullmatch(r"\d{1,2}:\d{2}", str(v)):
                    raise RentError("Subah ka samay HH:MM mein.")
                r.morning_time = str(v)
            elif k == "state":
                r.state = str(v).upper()[:4]
            elif k == "gstin":
                g = str(v).strip().upper()
                if g:
                    from ..india.money import gstin_ok
                    if not gstin_ok(g):
                        raise RentError("GSTIN sahi nahi (check digit).")
                r.gstin = g
            elif k == "landlord_phone":
                r.landlord_phone = R.phone10(v)
            else:
                setattr(r, k, _clean(str(v), 2000))
        if ref:
            r.pan_ref = ref
    return {"settings": settings(tenant), "say": "Rentdesk ki settings save."}


# ---------------------------------------------------------------- units
def _unit(s, tenant: str, ref: str) -> RdUnit:
    ref = str(ref or "").strip()
    if not ref:
        raise RentError("Kaun sa unit? (U-001 / naam)")
    u = s.get(RdUnit, ref)
    if u is not None and u.tenant_id == tenant:
        return u
    rows = s.scalars(select(RdUnit).where(RdUnit.tenant_id == tenant, RdUnit.archived.is_(False))).all()
    low = ref.lower()
    for u in rows:
        if u.number.lower() == low or u.label.lower() == low:
            return u
    hits = [u for u in rows if low in f"{u.label} {u.building}".lower()]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise RentError(f"'{ref}' se {len(hits)} unit milte hain: " + ", ".join(f"{u.number} {u.label}" for u in hits[:6]))
    raise RentError(f"Unit '{ref}' nahi mila.")


def _live_tenancy(s, unit_id: str) -> RdTenancy | None:
    return s.scalars(select(RdTenancy).where(RdTenancy.unit_id == unit_id, RdTenancy.status.in_(("active", "notice")))).first()


def _unit_view(s, u: RdUnit) -> dict:
    t = _live_tenancy(s, u.id)
    p = s.get(RdPerson, t.person_id) if t else None
    return {"id": u.id, "number": u.number, "label": u.label, "building": u.building, "kind": u.kind,
            "kind_label": R.UNIT_KINDS.get(u.kind, u.kind), "use": u.use, "address": u.address, "city": u.city, "pin": u.pin,
            "area_sqft": u.area_sqft or None, "area_note": u.area_note, "furnished": u.furnished, "inventory": _j(u.inventory, []),
            "owner_name": u.owner_name, "owner_phone": u.owner_phone, "rent_ask": u.rent_ask or None, "deposit_ask": u.deposit_ask or None,
            "maintenance": u.maintenance or None, "electricity_no": u.electricity_no, "notes": u.notes,
            "status": ("notice" if t.status == "notice" else "occupied") if t else "vacant",
            "tenancy": t.number if t else "", "tenancy_id": t.id if t else "", "tenant_name": p.name if p else ""}


_UNIT_KEYS = ("label", "building", "kind", "use", "address", "city", "pin", "area_sqft", "area_note", "furnished", "inventory",
              "owner_name", "owner_phone", "rent_ask", "deposit_ask", "maintenance", "electricity_no", "notes", "archived")


def save_unit(tenant: str, unit: str = "", **kw: Any) -> dict:
    with _LOCK, session() as s:
        if unit:
            u = _unit(s, tenant, unit)
            new = False
        else:
            if not str(kw.get("label") or "").strip():
                raise RentError("Unit ka naam chahiye (Flat 302 / Shop 4 / Bed B2).")
            u = RdUnit(tenant_id=tenant, number=f"U-{_next(s, tenant, 'unit'):03d}")
            s.add(u)
            new = True
        for k in _UNIT_KEYS:
            if k not in kw or kw[k] is None:
                continue
            v = kw[k]
            if k == "kind":
                u.kind = v if v in R.UNIT_KINDS else "other"
                if "use" not in kw:
                    u.use = "commercial" if u.kind in R.COMMERCIAL_KINDS else "residential"
            elif k == "use":
                u.use = "commercial" if str(v).startswith("comm") else "residential"
            elif k in ("area_sqft", "rent_ask", "deposit_ask", "maintenance"):
                setattr(u, k, max(0.0, R.money(v)))
            elif k == "pin":
                p = re.sub(r"\D", "", str(v))
                if p and not re.fullmatch(r"[1-9]\d{5}", p):
                    raise RentError("PIN code 6 ank ka.")
                u.pin = p
            elif k == "owner_phone":
                u.owner_phone = R.phone10(v)
            elif k == "inventory":
                items = v if isinstance(v, list) else [x for x in re.split(r"[,\n;]", str(v)) if x.strip()]
                out = []
                for it in items[:80]:
                    if isinstance(it, dict):
                        out.append({"item": _clean(str(it.get("item") or ""), 80), "qty": int(R.money(it.get("qty")) or 1)})
                    else:
                        m = re.match(r"\s*(\d+)\s*[xX]?\s*(.+)", str(it))
                        out.append({"item": _clean((m.group(2) if m else str(it)).strip(), 80), "qty": int(m.group(1)) if m else 1})
                u.inventory = _dump([x for x in out if x["item"]])
            elif k == "archived":
                if v and _live_tenancy(s, u.id):
                    raise RentError("Is unit mein abhi kirayedar hai.")
                u.archived = bool(v)
            else:
                setattr(u, k, _clean(str(v), 1000))
        s.flush()
        view = _unit_view(s, u)
    return {"unit": view, "new": new, "say": f"{view['number']} {view['label']} save" + (" (naya)." if new else ".")}


def units(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        rows = s.scalars(select(RdUnit).where(RdUnit.tenant_id == tenant, RdUnit.archived.is_(False)).order_by(RdUnit.number)).all()
        out = [_unit_view(s, u) for u in rows]
    return [u for u in out if not status or u["status"] == status]


# ---------------------------------------------------------------- people
def _person(s, tenant: str, ref: str) -> RdPerson:
    ref = str(ref or "").strip()
    p = s.get(RdPerson, ref) if ref else None
    if p is not None and p.tenant_id == tenant:
        return p
    rows = s.scalars(select(RdPerson).where(RdPerson.tenant_id == tenant, RdPerson.forgotten.is_(False))).all()
    ph = R.phone10(ref)
    for p in rows:
        if p.number.lower() == ref.lower() or (ph and p.phone == ph):
            return p
    hits = [p for p in rows if ref and ref.lower() in p.name.lower()]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise RentError(f"'{ref}' naam ke {len(hits)} log: " + ", ".join(f"{p.number} {p.name}" for p in hits[:6]))
    raise RentError(f"Kirayedar '{ref}' nahi mila.")


def _person_view(p: RdPerson, full: bool = False) -> dict:
    ids = _j(p.ids, {})
    v = {"id": p.id, "number": p.number, "name": p.name, "phone": p.phone, "kind": p.kind, "lang": p.lang,
         "no_messages": p.no_messages, "forgotten": p.forgotten, "gstin": p.gstin, "composition": p.composition,
         "ids": {k: x.get("masked", "") for k, x in ids.items()}}
    if full:
        v |= {"email": p.email, "employer": p.employer, "address": p.address, "members": _j(p.members, []), "emergency": p.emergency,
              "notes": p.notes, "id_refs": {k: x.get("ref", "") for k, x in ids.items()}}
    return v


def save_person(tenant: str, person: str = "", name: str = "", phone: str = "", aadhaar: str = "", pan: str = "", **kw: Any) -> dict:
    """A tenant / licensee. Aadhaar / PAN straight into the Pehchaan Locker; only {id:...} + masked kept here."""
    with _LOCK, session() as s:
        if person:
            p = _person(s, tenant, person)
            new = False
        else:
            if not name.strip():
                raise RentError("Kirayedar ka naam chahiye.")
            ph = R.phone10(phone)
            if phone and not ph:
                raise RentError("Mobile 10 ank ka (6-9 se shuru).")
            if ph:
                dup = s.scalars(select(RdPerson).where(RdPerson.tenant_id == tenant, RdPerson.phone == ph,
                                                       RdPerson.forgotten.is_(False))).first()
                if dup:
                    p, new = dup, False
                else:
                    p, new = RdPerson(tenant_id=tenant, number=f"P-{_next(s, tenant, 'person'):03d}"), True
                    s.add(p)
            else:
                p, new = RdPerson(tenant_id=tenant, number=f"P-{_next(s, tenant, 'person'):03d}"), True
                s.add(p)
        if p.forgotten:
            raise RentError("Is kirayedar ki jaankari mita di gayi thi.")
        if name:
            p.name = _clean(name, 160)
        if phone:
            ph = R.phone10(phone)
            if not ph:
                raise RentError("Mobile 10 ank ka (6-9 se shuru).")
            p.phone = ph
        for k in ("email", "kind", "employer", "address", "emergency", "lang", "notes", "gstin"):
            if kw.get(k) is not None:
                v = str(kw[k])
                if k == "kind":
                    v = v if v in ("individual", "family", "student", "company", "firm") else "individual"
                if k == "gstin":
                    v = v.strip().upper()
                    if v:
                        from ..india.money import gstin_ok
                        if not gstin_ok(v):
                            raise RentError("Kirayedar ka GSTIN sahi nahi.")
                setattr(p, k, _clean(v, 1000))
        for k in ("no_messages", "composition"):
            if kw.get(k) is not None:
                setattr(p, k, bool(kw[k]))
        if kw.get("members") is not None:
            m = kw["members"]
            p.members = _dump([_clean(str(x), 80) for x in (m if isinstance(m, list) else str(m).split(",")) if str(x).strip()][:12])
        s.flush()
        pid, pnum, pname = p.id, p.number, p.name
    got = {}
    for kind, val in (("aadhaar", aadhaar), ("pan", pan)):
        if not val:
            continue
        from .. import idvault
        try:
            rec = idvault.save(tenant, kind, val, f"kirayedar {pnum}", f"Rentdesk {pname}"[:120])
        except Exception as e:
            raise RentError(f"{kind.upper()} sahi nahi: {e}")
        got[kind] = {"ref": rec["ref"], "masked": rec["masked"], "record": rec["id"]}
    with _LOCK, session() as s:
        p = s.get(RdPerson, pid)
        if got:
            p.ids = _dump({**_j(p.ids, {}), **got})
        view = _person_view(p, True)
    return {"person": view, "new": new, "say": f"{view['number']} {view['name']} save" + (" (naya)." if new else ".")
            + (" ID locker mein (masked)." if aadhaar or pan else "")}


def people(tenant: str, q: str = "") -> list[dict]:
    with session() as s:
        rows = s.scalars(select(RdPerson).where(RdPerson.tenant_id == tenant, RdPerson.forgotten.is_(False))
                         .order_by(RdPerson.number)).all()
        return [_person_view(p) for p in rows if not q or q.lower() in f"{p.name} {p.phone} {p.number}".lower()]


# ---------------------------------------------------------------- tenancies
def _tenancy(s, tenant: str, ref: str) -> RdTenancy:
    ref = str(ref or "").strip()
    t = s.get(RdTenancy, ref) if ref else None
    if t is not None and t.tenant_id == tenant:
        return t
    rows = s.scalars(select(RdTenancy).where(RdTenancy.tenant_id == tenant)).all()
    for t in rows:
        if t.number.lower() == ref.lower():
            return t
    # unit number / label or tenant name -> its live tenancy
    for t in rows:
        if t.status not in ("active", "notice", "draft"):
            continue
        u, p = s.get(RdUnit, t.unit_id), s.get(RdPerson, t.person_id)
        hay = f"{u.number if u else ''} {u.label if u else ''} {p.name if p else ''}".lower()
        if ref and ref.lower() in hay:
            return t
    raise RentError(f"Tenancy '{ref}' nahi mili (T-0001 / unit / kirayedar ka naam).")


def _rent_on(t: RdTenancy, d: date) -> float:
    hist = sorted(_j(t.rent_history, []), key=lambda x: x.get("from", ""))
    rent = t.rent
    if hist:
        rent = hist[0]["rent"]
        for h in hist:
            if h.get("from", "") <= d.isoformat():
                rent = h["rent"]
    return float(rent)


def _held_deposit(s, t: RdTenancy) -> float:
    return _r2(sum(c.paid for c in s.scalars(select(RdCharge).where(RdCharge.tenancy_id == t.id, RdCharge.kind == "deposit")).all()))


def _open_charges(s, t: RdTenancy, include_deposit: bool = True) -> list[RdCharge]:
    q = select(RdCharge).where(RdCharge.tenancy_id == t.id, RdCharge.status.in_(("open", "part")))
    rows = s.scalars(q.order_by(RdCharge.due_on, RdCharge.created_at)).all()
    return [c for c in rows if include_deposit or c.kind != "deposit"]


def _charge_view(c: RdCharge) -> dict:
    return {"id": c.id, "kind": c.kind, "kind_label": R.CHARGE_KINDS.get(c.kind, c.kind), "period": c.period, "due_on": c.due_on,
            "amount": c.amount, "paid": c.paid, "left": _r2(c.amount - c.paid), "status": c.status, "note": c.note,
            "amount_text": _rs(c.amount), "left_text": _rs(c.amount - c.paid)}


def _notes(s, t: RdTenancy, u: RdUnit, p: RdPerson, st: RdSettings) -> list[str]:
    out = R.deposit_check(st.state, u.use, t.rent, t.deposit)
    out.append(R.tds_note(p.kind, t.rent, u.use))
    out.append(R.gst_note(u.kind, u.use, bool(p.gstin), p.composition, st.gstin, t.rent if u.kind == "pg_bed" else 0.0))
    if (st.state or "").upper() == "MH" and t.kind == "leave_licence":
        out.append("Maharashtra: L&L likhit aur registered hona zaroori (Rent Control Act s.55, landlord ki zimmedari; na ho to "
                   "kirayedar ki baat maani jaati hai; 3 mahine tak jail / Rs 5,000). IGR par online e-registration.")
    if R.is_mta(st.state):
        out.append("Model Tenancy Act wala rajya: agreement 2 mahine mein Rent Authority ko; kiraya badhane se 3 mahine pehle likhit notice.")
    if not st.state:
        out.append("Niyam mein apna rajya (MH ...) likhiye: checklist / kanoon ki baatein usi se.")
    return [x for x in out if x]


def _tenancy_view(s, t: RdTenancy, full: bool = False) -> dict:
    u, p, st = s.get(RdUnit, t.unit_id), s.get(RdPerson, t.person_id), _st(s, t.tenant_id)
    on = today(t.tenant_id)
    opens = _open_charges(s, t)
    due_now = [c for c in opens if c.due_on and c.due_on <= on.isoformat()]
    end = _date(t.end)
    v = {"id": t.id, "number": t.number, "kind": t.kind, "kind_label": R.AGREEMENT_KINDS.get(t.kind, t.kind), "status": t.status,
         "status_label": TENANCY_STATUS.get(t.status, t.status), "unit": u.number if u else "", "unit_label": u.label if u else "",
         "unit_id": t.unit_id, "person_id": t.person_id, "tenant_name": (p.name if p else ""), "tenant_phone": (p.phone if p else ""),
         "start": t.start, "end": t.end, "months": t.months, "rent": t.rent, "rent_text": _rs(t.rent), "deposit": t.deposit,
         "deposit_text": _rs(t.deposit), "maintenance": t.maintenance or None, "maintenance_by": t.maintenance_by, "due_day": t.due_day,
         "escalation_pct": t.escalation_pct or None, "escalation_every": t.escalation_every or None, "lock_in_months": t.lock_in_months,
         "notice_months": t.notice_months, "registration": _j(t.registration, {}), "police": _j(t.police, {}),
         "notice_on": t.notice_on, "vacate_on": t.vacate_on, "days_left": (end - on).days if end else None,
         "due_now": _r2(sum(c.amount - c.paid for c in due_now)), "due_now_text": _rs(sum(c.amount - c.paid for c in due_now)),
         "deposit_held": _held_deposit(s, t), "advance": t.advance or None}
    if full:
        done = _j(t.checklist, {})
        v |= {"charges": [_charge_view(c) for c in s.scalars(select(RdCharge).where(RdCharge.tenancy_id == t.id)
                                                              .order_by(RdCharge.due_on.desc())).all()[:60]],
              "payments": [_pay_view(x) for x in s.scalars(select(RdPayment).where(RdPayment.tenancy_id == t.id, RdPayment.void.is_(False))
                                                          .order_by(RdPayment.created_at.desc())).all()[:40]],
              "checklist": [{**i, "done": done.get(i["id"], "")} for i in R.checklist(st.state, t.kind, t.months, u.use if u else "residential")],
              "notes": _notes(s, t, u, p, st) if u and p else [], "files": _j(t.files, []), "rent_history": _j(t.rent_history, []),
              "purpose": t.purpose, "stamp_duty": t.stamp_duty, "reg_fee": t.reg_fee, "lock_in_until": _iso(R.add_months(_date(t.start), t.lock_in_months))
              if t.lock_in_months and _date(t.start) else "", "escalations": _escalation_dates(t), "other_notes": t.notes,
              "person": _person_view(p) if p else {}, "unit_view": _unit_view(s, u) if u else {}}
    return v


_TEN_KEYS = ("kind", "start", "months", "rent", "deposit", "maintenance", "maintenance_by", "due_day", "escalation_pct",
             "escalation_every", "lock_in_months", "notice_months", "purpose", "stamp_duty", "reg_fee", "notes")
MONEY_LOCKED = ("rent", "deposit", "maintenance", "escalation_pct", "escalation_every", "start", "months")


def _apply_tenancy(t: RdTenancy, kw: dict) -> None:
    for k in _TEN_KEYS:
        if k not in kw or kw[k] is None or kw[k] == "":
            continue
        v = kw[k]
        if k == "kind":
            t.kind = v if v in R.AGREEMENT_KINDS else "rent"
        elif k == "start":
            d = _date(v)
            if not d:
                raise RentError("Shuru ki taarikh DD-MM-YYYY mein.")
            t.start = d.isoformat()
        elif k in ("months", "due_day", "escalation_every", "lock_in_months", "notice_months"):
            n = int(R.money(v))
            lim = {"months": (1, 600), "due_day": (0, 28), "escalation_every": (0, 120), "lock_in_months": (0, 120), "notice_months": (0, 12)}[k]
            if not lim[0] <= n <= lim[1]:
                raise RentError(f"{k}: {lim[0]}-{lim[1]} ke beech.")
            setattr(t, k, n)
        elif k in ("rent", "deposit", "maintenance", "escalation_pct"):
            x = R.money(v)
            if x < 0 or (k == "escalation_pct" and x > 50) or x > 50_000_000:
                raise RentError(f"{k}: {v} sahi nahi lagta.")
            setattr(t, k, x)
        elif k in ("stamp_duty", "reg_fee"):
            setattr(t, k, max(0.0, R.money(v)))
        elif k == "maintenance_by":
            t.maintenance_by = "tenant" if str(v).startswith(("ten", "kiray")) else "owner"
        else:
            setattr(t, k, _clean(str(v), 1000))
    s0 = _date(t.start)
    if s0:
        t.end = R.end_of(s0, t.months).isoformat()


def new_tenancy(tenant: str, unit: str, person: str, actor: str = "owner", conv: str = "", **kw: Any) -> dict:
    """A DRAFT tenancy. Rent / deposit only from her words; nothing is billed until `activate`."""
    with _LOCK, session() as s:
        u, p, st = _unit(s, tenant, unit), _person(s, tenant, person), _st(s, tenant)
        t = RdTenancy(tenant_id=tenant, number=f"T-{_next(s, tenant, 'tenancy'):04d}", unit_id=u.id, person_id=p.id,
                      kind=R.default_kind(st.state), months=11)
        kw.setdefault("rent", u.rent_ask or None)
        kw.setdefault("deposit", u.deposit_ask or None)
        if u.maintenance and "maintenance" not in kw:
            kw["maintenance"] = u.maintenance
        _apply_tenancy(t, kw)
        if not t.start:
            raise RentError("Shuru ki taarikh chahiye.")
        s.add(t)
        s.flush()
        view = _tenancy_view(s, t, True)
    blanks = [w for w, ok in (("kiraya", view["rent"] > 0), ("deposit", view["deposit"] > 0)) if not ok]
    say = (f"{view['number']}: {view['unit']} {view['unit_label']} -> {view['tenant_name']}, {view['start']} se {view['end']} "
           f"({view['months']} mahine), kiraya {view['rent_text'] or '[?]'}, deposit {view['deposit_text'] or '[?]'}. Draft hai; "
           "agreement banaiye aur 'activate' kijiye.")
    if blanks:
        say += " Baaki: " + ", ".join(blanks) + " (aapka number)."
    return {"tenancy": view, "say": say}


def from_propagent_deal(tenant: str, deal: str, start: str = "", actor: str = "owner", conv: str = "") -> dict:
    """v0.144 Makaan link: a rent / lease deal she closed in the Property Sahayak becomes a DRAFT tenancy here (unit from the
    listing, tenant from the lead, rent / deposit from the deal she agreed). Nothing is billed, sent or activated: she checks it
    and says 'activate'. Owner only; a deal that already made a tenancy is not copied twice."""
    from ..propagent.models import PropagentDeal, PropagentLead, PropagentListing
    with session() as s:
        D = s.scalars(select(PropagentDeal).where(PropagentDeal.tenant_id == tenant,
                                                  (PropagentDeal.id == deal) | (PropagentDeal.number == deal.upper()))).first()
        if D is None:
            raise RentError("Woh property deal nahi mili.")
        if D.purpose not in ("rent", "lease"):
            raise RentError("Yeh sale deal hai; kirayedari sirf rent / lease deal se banti hai.")
        if D.status not in ("agreement", "registered", "done"):
            raise RentError("Deal abhi pakki nahi (agreement / registry ke baad hi kirayedari banaiye).")
        L = s.get(PropagentListing, D.listing_id)
        l = s.get(PropagentLead, D.lead_id) if D.lead_id else None
        if L is None or l is None or l.forgotten:
            raise RentError("Deal mein listing ya kirayedar ki jaankari nahi bachi.")
        tag = f"[propagent {D.number}]"
        old = s.scalars(select(RdTenancy).where(RdTenancy.tenant_id == tenant, RdTenancy.notes.contains(tag))).first()
        if old is not None:
            raise RentError(f"Is deal se kirayedari {old.number} pehle hi bani hai.")
        unit_kw = {"label": (L.title or f"{L.kind} {L.locality}").strip()[:120], "kind": L.kind if L.kind in R.UNIT_KINDS else "other",
                   "address": L.address, "city": L.city, "pin": L.pin, "area_sqft": L.carpet_sqft or None,
                   "furnished": L.furnishing, "owner_name": L.owner_name, "owner_phone": L.owner_phone,
                   "rent_ask": D.price or None, "deposit_ask": D.deposit or None}
        person = (l.name, l.phone)
        rent, dep, num, avail = D.price or None, D.deposit or None, D.number, L.available_from
    u = save_unit(tenant, "", **{k: v for k, v in unit_kw.items() if v not in (None, "")})["unit"]
    p = save_person(tenant, "", person[0] or "Kirayedar", person[1])["person"]
    start = start or avail or today(tenant).isoformat()
    out = new_tenancy(tenant, u["number"], p["number"], actor, conv, start=start, rent=rent, deposit=dep,
                      notes=f"{tag} property deal se bani")
    out["say"] = f"Deal {num} se: " + out["say"]
    return out


def update_tenancy(tenant: str, tenancy: str, **kw: Any) -> dict:
    with _LOCK, session() as s:
        t = _tenancy(s, tenant, tenancy)
        if t.status in ("ended", "cancelled"):
            raise RentError(f"{t.number} khatam ho chuki hai.")
        if t.status != "draft" and any(k in kw and kw[k] not in (None, "") for k in MONEY_LOCKED):
            raise RentError("Chalu tenancy mein kiraya / deposit / taarikh seedhe nahi badalte: kiraya badlav ka card (action=rent_change) "
                            "ya naya agreement.")
        _apply_tenancy(t, kw)
        view = _tenancy_view(s, t, True)
    return {"tenancy": view, "say": f"{view['number']} update."}


def activate(tenant: str, tenancy: str, conv: str = "") -> dict:
    """Owner: the agreement is signed / she says go. Deposit charge + first rent charges are made."""
    with _LOCK, session() as s:
        t = _tenancy(s, tenant, tenancy)
        if t.status != "draft":
            raise RentError(f"{t.number} pehle se {TENANCY_STATUS.get(t.status, t.status)}.")
        if t.rent <= 0:
            raise RentError("Kiraya (aapka number) chahiye.")
        other = _live_tenancy(s, t.unit_id)
        if other is not None:
            end = _date(other.end)
            if not end or end >= _date(t.start):
                raise RentError(f"Is unit mein {other.number} abhi chalu hai ({other.end} tak). Pehle use khatam kijiye.")
        t.status = "active"
        if not _j(t.rent_history, []):
            t.rent_history = _dump([{"from": t.start, "rent": t.rent, "why": "agreement"}])
        if t.deposit > 0:
            s.add(RdCharge(tenant_id=tenant, tenancy_id=t.id, kind="deposit", period="", due_on=t.start, amount=t.deposit,
                           note="Security deposit"))
        s.flush()
        tid = t.id
    made = bill_due(tenant, tid)
    with session() as s:
        view = _tenancy_view(s, s.get(RdTenancy, tid), True)
    pend = [i["what"] for i in view["checklist"] if not i["done"] and i["id"] in ("registration", "police", "agreement")]
    say = f"{view['number']} chalu. {made['made']} charge bane (deposit + kiraya)."
    if pend:
        say += " Abhi baaki: " + "; ".join(pend[:3])
    return {"tenancy": view, "say": say}


def tenancy_view(tenant: str, tenancy: str) -> dict:
    with session() as s:
        return _tenancy_view(s, _tenancy(s, tenant, tenancy), True)


def tenancies(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        q = select(RdTenancy).where(RdTenancy.tenant_id == tenant)
        if status:
            q = q.where(RdTenancy.status == status)
        return [_tenancy_view(s, t) for t in s.scalars(q.order_by(RdTenancy.created_at.desc())).all()[:200]]


def check_item(tenant: str, tenancy: str, item: str, done: bool = True, ref: str = "", on: str = "", office: str = "",
               actor: str = "owner") -> dict:
    """Tick a checklist line. registration / police also keep the doc / reference number she gives."""
    with _LOCK, session() as s:
        t = _tenancy(s, tenant, tenancy)
        ids = {i["id"] for i in R.checklist(_st(s, tenant).state, t.kind, t.months, "residential")} | {"rent_authority", "society"}
        if item not in ids:
            raise RentError("Checklist line: " + ", ".join(sorted(ids)))
        d = (_date(on) or today(tenant)).isoformat()
        c = _j(t.checklist, {})
        if done:
            c[item] = d
        else:
            c.pop(item, None)
        t.checklist = _dump(c)
        if item in ("registration", "police"):
            rec = {"status": "done" if done else "pending", "ref": _clean(ref, 60), "date": d if done else "", "office": _clean(office, 120)}
            setattr(t, item, _dump(rec))
        view = _tenancy_view(s, t, True)
    return {"tenancy": view, "say": f"{view['number']}: '{item}' {'ho gaya' if done else 'baaki'}."}


# ---------------------------------------------------------------- ledger
def _mirror_due(s, tenant: str, c: RdCharge, t: RdTenancy, jobs: list) -> None:
    """Queue a BizDue mirror (made AFTER this session closes: another module's write inside ours would lock SQLite)."""
    st = _st(s, tenant)
    p = s.get(RdPerson, t.person_id)
    if not st.mirror_dues or not p or not p.phone or c.kind == "deposit" or c.biz_due_id:
        return
    u = s.get(RdUnit, t.unit_id)
    jobs.append(("due", c.id, p.name, p.phone, c.amount, c.due_on, f"{R.CHARGE_KINDS.get(c.kind, c.kind)} {c.period} {u.label if u else ''}"[:200]))


def _mirror_paid(c: RdCharge, jobs: list) -> None:
    if c.biz_due_id:
        jobs.append(("paid", c.biz_due_id))


def _run_mirrors(tenant: str, jobs: list) -> None:
    from ..employee import inbox
    made = {}
    for j in jobs:
        try:
            if j[0] == "due":
                made[j[1]] = inbox.add_due(tenant, j[2], j[3], j[4], j[5], j[6]).get("id", "")
            else:
                inbox.set_due(tenant, j[1], status="paid")
        except Exception as e:
            log.info("rentdesk due mirror skipped: %s", e)
    if made:
        with session() as s:
            for cid, did in made.items():
                c = s.get(RdCharge, cid)
                if c is not None:
                    c.biz_due_id = did


def bill_due(tenant: str, tenancy: str = "", upto: date | None = None) -> dict:
    """Rent (+ maintenance the tenant pays) per licence month up to `upto` + her reminder days. Runs by itself (worker)."""
    made, jobs = 0, []
    with _LOCK, session() as s:
        st = _st(s, tenant)
        q = select(RdTenancy).where(RdTenancy.tenant_id == tenant, RdTenancy.status.in_(("active", "notice")))
        if tenancy:
            q = q.where(RdTenancy.id == _tenancy(s, tenant, tenancy).id)
        lim = (upto or today(tenant)) + timedelta(days=max(st.remind_before, 0) + 1)
        for t in s.scalars(q).all():
            start, end = _date(t.start), _date(t.vacate_on) or _date(t.end)
            if not start or not end:
                continue
            have = {(c.kind, c.period) for c in s.scalars(select(RdCharge).where(RdCharge.tenancy_id == t.id)).all()}
            for ps in R.periods(start, end, lim):
                per = ps.isoformat()[:7] if start.day == 1 else ps.isoformat()
                due = R.due_date(ps, t.due_day, start).isoformat()
                for kind, amt in (("rent", _rent_on(t, ps)), ("maintenance", t.maintenance if t.maintenance_by == "tenant" else 0)):
                    if amt <= 0 or (kind, per) in have:
                        continue
                    c = RdCharge(tenant_id=tenant, tenancy_id=t.id, kind=kind, period=per, due_on=due, amount=_r2(amt))
                    s.add(c)
                    s.flush()
                    have.add((kind, per))
                    made += 1
                    if t.advance > 0:
                        use = min(t.advance, c.amount)
                        c.paid, t.advance = _r2(use), _r2(t.advance - use)
                        c.status = "paid" if c.paid >= c.amount - 0.005 else "part"
                    if c.status != "paid":
                        _mirror_due(s, tenant, c, t, jobs)
    _run_mirrors(tenant, jobs)
    return {"made": made}


def _pay_view(x: RdPayment) -> dict:
    return {"id": x.id, "receipt_no": x.receipt_no, "amount": x.amount, "amount_text": _rs(x.amount), "on": x.on, "mode": x.mode,
            "ref_tail": x.ref_tail, "alloc": _j(x.alloc, []), "hint": x.hint, "by": x.by}


def _galla_hint(tenant: str, amount: float, on: date) -> str:
    try:
        from ..galla.service import GallaEntry
        days = {(on + timedelta(days=k)).isoformat() for k in range(-3, 4)}
        with session() as s:
            rows = s.scalars(select(GallaEntry).where(GallaEntry.tenant_id == tenant, GallaEntry.void.is_(False),
                                                      GallaEntry.amount_paise == int(round(amount * 100)))).all()
            hit = [g for g in rows if g.day in days]
        if hit:
            g = hit[0]
            return f"Galla mein {g.day} ko {_rs(amount)} ki UPI aayi thi" + (f" ({g.payer})" if g.payer else "") + ": sirf ishaara, saboot nahi."
    except Exception:
        pass
    return ""


def receive(tenant: str, tenancy: str, amount, on: str = "", mode: str = "upi", ref: str = "", charge: str = "",
            actor: str = "owner", conv: str = "") -> dict:
    """She says money came (UPI / bank / cash / cheque). Allocated to the oldest dues (or the charge she names), receipt numbered."""
    if not is_owner(actor):
        raise RentError("Paisa mila sirf owner bata sakti hain.")
    a = R.money(amount)
    if a <= 0:
        raise RentError("Kitne mile? (rakam)")
    mode = mode if mode in ("upi", "bank", "cash", "cheque") else "upi"
    d = _date(on) or today(tenant)
    with _LOCK, session() as s:
        t = _tenancy(s, tenant, tenancy)
        if t.status in ("draft", "cancelled"):
            raise RentError(f"{t.number} abhi chalu nahi.")
        opens = _open_charges(s, t)
        if charge:
            opens = [c for c in opens if c.id == charge] + [c for c in opens if c.id != charge]
        left, alloc, jobs = a, [], []
        for c in opens:
            if left <= 0.005:
                break
            take = min(left, _r2(c.amount - c.paid))
            c.paid = _r2(c.paid + take)
            c.status = "paid" if c.paid >= c.amount - 0.005 else "part"
            left = _r2(left - take)
            alloc.append({"charge_id": c.id, "kind": c.kind, "period": c.period, "amount": take})
            if c.status == "paid":
                _mirror_paid(c, jobs)
        if left > 0.005:
            t.advance = _r2(t.advance + left)
            alloc.append({"charge_id": "", "kind": "advance", "period": "", "amount": left})
        no = f"R/{R.fy_of(d)}/{_next(s, tenant, 'receipt:' + R.fy_of(d)):04d}"
        x = RdPayment(tenant_id=tenant, tenancy_id=t.id, receipt_no=no, amount=a, on=d.isoformat(), mode=mode,
                      ref_tail=re.sub(r"\W", "", str(ref))[-4:], alloc=_dump(alloc), by=actor_name(tenant, actor))
        s.add(x)
        s.flush()
        pid = x.id
        p, st = s.get(RdPerson, t.person_id), _st(s, tenant)
        annual = _rent_on(t, d) * 12
        notes = R.receipt_notes(annual, mode, a, bool(st.pan_ref))
        tv = _tenancy_view(s, t)
    _run_mirrors(tenant, jobs)
    hint = _galla_hint(tenant, a, d) if mode == "upi" else ""
    with session() as s:
        x = s.get(RdPayment, pid)
        x.hint = hint[:300]
        view = _pay_view(x)
    say = f"{view['receipt_no']}: {view['amount_text']} mila ({tv['tenant_name']}, {tv['unit_label']})."
    if tv["due_now"] > 0:
        say += f" Abhi bhi baaki {tv['due_now_text']}."
    if hint:
        say += " " + hint
    if notes:
        say += " " + " ".join(notes)
    try:
        msg = draft_message(tenant, tv["id"], "receipt", ref=pid, conv=conv, publish=False)
    except RentError:
        msg = {}
    pub = {"payment": view, "tenancy": tv["number"], "tenancy_id": tv["id"], "message": msg.get("message"), "say": say}
    _publish(tenant, "rentdesk_receipt", pub, conv)
    return {"payment": view, "tenancy": tv, "notes": notes, "message": msg.get("message"), "say": say + " Receipt ka message draft taiyaar (aapke tap se jaayega)."}


def void_payment(tenant: str, payment: str, actor: str = "owner") -> dict:
    if not is_owner(actor):
        raise RentError("Sirf owner.")
    with _LOCK, session() as s:
        x = s.get(RdPayment, payment)
        if x is None or x.tenant_id != tenant or x.void:
            raise RentError("Payment nahi mili.")
        t = s.get(RdTenancy, x.tenancy_id)
        for al in _j(x.alloc, []):
            if al.get("kind") == "advance":
                t.advance = _r2(max(0.0, t.advance - al["amount"]))
                continue
            c = s.get(RdCharge, al.get("charge_id"))
            if c:
                c.paid = _r2(max(0.0, c.paid - al["amount"]))
                c.status = "open" if c.paid <= 0.005 else "part"
        x.void = True
        return {"payment": _pay_view(x), "say": f"{x.receipt_no} radd; dues wapas khule."}


def add_charge(tenant: str, tenancy: str, kind: str, amount, due_on: str = "", note: str = "", actor: str = "owner") -> dict:
    """A one-off bill she adds (electricity / water / late fee as per agreement). Owner only: it is a charge to the tenant."""
    if not is_owner(actor):
        raise RentError("Kirayedar par charge sirf owner laga sakti hain.")
    k = kind if kind in R.CHARGE_KINDS and kind not in ("rent", "deposit") else "other"
    a = R.money(amount)
    if a <= 0:
        raise RentError("Rakam (bill / agreement se) chahiye.")
    with _LOCK, session() as s:
        t = _tenancy(s, tenant, tenancy)
        c = RdCharge(tenant_id=tenant, tenancy_id=t.id, kind=k, due_on=(_date(due_on) or today(tenant)).isoformat(), amount=_r2(a),
                     note=_clean(note, 200))
        s.add(c)
        s.flush()
        jobs = []
        _mirror_due(s, tenant, c, t, jobs)
        out = {"charge": _charge_view(c), "say": f"{t.number}: {R.CHARGE_KINDS[k]} {_rs(a)} joda."}
    _run_mirrors(tenant, jobs)
    return out


def waive(tenant: str, charge: str, actor: str = "owner") -> dict:
    if not is_owner(actor):
        raise RentError("Sirf owner maaf kar sakti hain.")
    with _LOCK, session() as s:
        c = s.get(RdCharge, charge)
        if c is None or c.tenant_id != tenant:
            raise RentError("Charge nahi mila.")
        c.status = "waived"
        jobs = []
        _mirror_paid(c, jobs)
        out = {"charge": _charge_view(c), "say": f"{R.CHARGE_KINDS.get(c.kind, c.kind)} {c.period} maaf."}
    _run_mirrors(tenant, jobs)
    return out


def pay_link(tenant: str, tenancy: str) -> dict:
    """upi://pay to HER UPI ID for what is due now. The tenant pays in their own app; Hoola never takes money."""
    with session() as s:
        t = _tenancy(s, tenant, tenancy)
        st = _st(s, tenant)
        upi, nm = _upi(st)
        v = _tenancy_view(s, t)
    if not upi:
        raise RentError("Aapka UPI ID nahi hai (Niyam ya Employee profile mein daaliye).")
    amt = v["due_now"]
    if amt <= 0:
        return {"url": "", "say": "Abhi kuch baaki nahi."}
    url = f"upi://pay?pa={quote(upi)}&pn={quote(nm or '')}&am={amt:.2f}&cu=INR&tn={quote(('Rent ' + v['unit'] + ' ' + v['number'])[:40])}"
    return {"url": url, "amount": amt, "upi_id": upi, "say": f"{_rs(amt)} ka UPI link (paise seedhe aapke UPI ID par)."}


def statement(tenant: str, tenancy: str) -> dict:
    with session() as s:
        t = _tenancy(s, tenant, tenancy)
        v = _tenancy_view(s, t, True)
    billed = sum(c["amount"] for c in v["charges"] if c["status"] != "waived")
    paid = sum(c["paid"] for c in v["charges"])
    return {"tenancy": v["number"], "charges": v["charges"], "payments": v["payments"], "billed": _r2(billed), "paid": _r2(paid),
            "due_now": v["due_now"], "deposit_held": v["deposit_held"], "advance": v["advance"],
            "say": f"{v['number']}: bill {_rs(billed)}, mila {_rs(paid)}, abhi baaki {v['due_now_text'] or _rs(0)}, deposit paas {_rs(v['deposit_held'])}."}


def _latin(t) -> str:
    from .. import indicpdf                   # v0.144 Devanagari kept: the PDF is printed with Hindi / Marathi fonts
    return indicpdf.keep(t)


def receipt_pdf(tenant: str, payment: str) -> bytes:
    """Rent receipt with the fields an employer asks for HRA (Form 124): landlord name, address, PAN, period, amount, mode."""
    from reportlab.lib.pagesizes import A5
    from reportlab.pdfgen import canvas  # noqa: F401
    from .. import indicpdf as _indicpdf
    with session() as s:
        x = s.get(RdPayment, payment)
        if x is None or x.tenant_id != tenant:
            raise RentError("Receipt nahi mili.")
        t = s.get(RdTenancy, x.tenancy_id)
        u, p, st = s.get(RdUnit, t.unit_id), s.get(RdPerson, t.person_id), _st(s, tenant)
        pan, full_ref = "", (st.pan_ref if st.receipt_full_pan else "")
        pan_ref = st.pan_ref
        alloc = _j(x.alloc, [])
        data = dict(no=x.receipt_no, on=x.on, amount=x.amount, mode=x.mode, ref=x.ref_tail, void=x.void,
                    landlord=st.landlord_name or st.business or "[landlord name]", addr=st.landlord_address or "[landlord address]",
                    tenant_name=p.name if p and not p.forgotten else "Tenant", unit=f"{u.label}, {u.building}, {u.address} {u.pin}".strip(", ")
                    if u else "", pan="")
    if full_ref:
        try:
            from .. import idvault
            got = idvault.resolve(tenant, full_ref)
            pan = got[0] if got else ""
        except Exception:
            pan = ""
    if not pan and pan_ref:
        with session() as s:
            pan = _pan_masked(_st(s, tenant))
    data["pan"] = pan or "[PAN]"
    try:
        from ..india.money import rupees_words
        words = rupees_words(data["amount"], "en")
    except Exception:
        words = ""
    bio = io.BytesIO()
    c = _indicpdf.Canvas(bio, pagesize=A5)
    w, h = A5
    y = h - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(36, y, _latin("RENT RECEIPT" + (" (CANCELLED)" if data["void"] else "")))
    c.setFont("Helvetica", 10)
    y -= 22
    for line in (f"Receipt no: {data['no']}        Date: {data['on']}",
                 f"Received with thanks from {data['tenant_name']}",
                 f"the sum of Rs {data['amount']:,.2f} ({words})" if words else f"the sum of Rs {data['amount']:,.2f}",
                 f"by {data['mode'].upper()}" + (f" (ref ...{data['ref']})" if data["ref"] else ""),
                 "towards:"):
        c.drawString(36, y, _latin(line)[:95])
        y -= 16
    for al in alloc:
        c.drawString(52, y, _latin(f"- {R.CHARGE_KINDS.get(al.get('kind'), al.get('kind', ''))} {al.get('period', '')}: Rs {al['amount']:,.2f}")[:90])
        y -= 14
    y -= 6
    for line in (f"Premises: {data['unit']}"[:95], f"Landlord / licensor: {data['landlord']}", f"Address: {data['addr']}"[:95],
                 f"Landlord PAN: {data['pan']}"):
        c.drawString(36, y, _latin(line))
        y -= 16
    if data["mode"] == "cash" and data["amount"] > 5000:
        c.rect(w - 110, 60, 70, 50)
        c.setFont("Helvetica", 7)
        c.drawString(w - 106, 64, "Revenue stamp")
    c.setFont("Helvetica", 10)
    c.drawString(36, 70, _latin("Signature: ____________________"))
    c.setFont("Helvetica", 7)
    c.drawString(36, 40, _latin("Prepared by Hoola from the owner's record."))
    c.showPage()
    c.save()
    return bio.getvalue()


def receipt_file(tenant: str, payment: str, conv: str = "") -> dict:
    from .. import chatfiles
    pdf = receipt_pdf(tenant, payment)
    with session() as s:
        no = s.get(RdPayment, payment).receipt_no.replace("/", "-")
    f = chatfiles.store(tenant, f"Rent_receipt_{no}.pdf", pdf, "application/pdf")
    _publish(tenant, "pc_file", {**f, "source": "rentdesk", "title": f"Rent receipt {no}"}, conv)
    return {"file": f, "say": f"Receipt {no} PDF."}


# ---------------------------------------------------------------- messages (drafts; HER tap sends)
def _msg_view(s, m: RdMessage) -> dict:
    p = s.get(RdPerson, m.person_id) if m.person_id else None
    ph = p.phone if p and not p.forgotten else ""
    return {"id": m.id, "kind": m.kind, "text": m.text, "hash": m.hash, "status": m.status, "via": m.via, "to": p.name if p else "",
            "phone": ph, "no_messages": bool(p and p.no_messages), "tenancy_id": m.tenancy_id,
            "wa": f"https://wa.me/91{ph}?text={quote(m.text)}" if ph else "", "sms": f"sms:{ph}?body={quote(m.text)}" if ph else "",
            "sent_at": _aware(m.sent_at).isoformat(timespec="minutes") if m.sent_at else ""}


def _msg_text(s, t: RdTenancy, kind: str, ref: str, extra: dict) -> str:
    u, p, st = s.get(RdUnit, t.unit_id), s.get(RdPerson, t.person_id), _st(s, t.tenant_id)
    nm = (p.name.split()[0] if p and p.name else "ji")
    who = st.landlord_name or st.business or "aapke makaan malik"
    unit = f"{u.label}{', ' + u.building if u and u.building else ''}" if u else ""
    en = p is not None and p.lang == "en"
    opens = [c for c in _open_charges(s, t) if c.kind != "deposit" or t.status == "active"]
    due = _r2(sum(c.amount - c.paid for c in opens if c.due_on <= (extra.get("upto") or "9999")))
    upi, _ = _upi(st)
    pay = f" UPI: {upi}" if upi else ""
    if kind == "reminder":
        return (f"Namaste {nm}, {unit} ka kiraya {_rs(due)} {extra.get('due_on', '')} ko due hai.{pay} Dhanyavaad, {who}" if not en else
                f"Hello {nm}, rent of {_rs(due)} for {unit} is due on {extra.get('due_on', '')}.{pay} Thank you, {who}")
    if kind == "late":
        return (f"Namaste {nm}, {unit} ka {_rs(due)} abhi baaki hai (due {extra.get('due_on', '')}). Jaldi bhej dijiye.{pay} Koi dikkat ho "
                f"to bata dijiye. - {who}" if not en else
                f"Hello {nm}, {_rs(due)} for {unit} is pending (due {extra.get('due_on', '')}). Please pay at the earliest.{pay} - {who}")
    if kind == "receipt":
        x = s.get(RdPayment, ref)
        amt = _rs(x.amount) if x else ""
        return (f"Namaste {nm}, {amt} mil gaye, dhanyavaad. Receipt no {x.receipt_no if x else ''}. - {who}" if not en else
                f"Hello {nm}, received {amt} with thanks. Receipt no {x.receipt_no if x else ''}. - {who}")
    if kind == "refund":
        return (f"Namaste {nm}, aapka deposit hisaab: {extra.get('summary', '')}. - {who}" if not en else
                f"Hello {nm}, your deposit settlement: {extra.get('summary', '')}. - {who}")
    if kind == "repair":
        return f"Namaste {nm}, {unit}: {extra.get('summary', '')} - {who}"
    if kind in ("notice", "rent_change", "renewal"):
        return extra.get("text") or ""
    return str(extra.get("text") or "")


def draft_message(tenant: str, tenancy: str, kind: str = "custom", text: str = "", ref: str = "", conv: str = "",
                  publish: bool = True, **extra: Any) -> dict:
    """A DRAFT for the tenant. Nothing is sent here: only `send_message(by_tap=True)` from her app."""
    from ..net import policy
    if text and (policy.secret_found(text) or re.search(r"\b(otp|pin|cvv|password|mpin)\b", text, re.I)):
        raise RentError("Message mein OTP / PIN / card / Aadhaar jaisi cheez hai; yeh kabhi nahi bheja jaata.")
    with _LOCK, session() as s:
        t = _tenancy(s, tenant, tenancy)
        p = s.get(RdPerson, t.person_id)
        if p is None or p.forgotten:
            raise RentError("Kirayedar ki jaankari nahi.")
        body = _clean(text, 1500) if kind == "custom" else _msg_text(s, t, kind, ref, {**extra, "text": _clean(text, 3000)})
        if not body.strip():
            raise RentError("Message khaali hai.")
        if policy.secret_found(body):
            raise RentError("Message mein OTP / PIN / card / Aadhaar jaisi cheez hai; yeh kabhi nahi bheja jaata.")
        old = s.scalars(select(RdMessage).where(RdMessage.tenancy_id == t.id, RdMessage.kind == kind, RdMessage.status == "draft",
                                                RdMessage.ref == str(ref))).all()
        for o in old:
            if kind != "custom":
                o.status = "dropped"
        m = RdMessage(tenant_id=tenant, tenancy_id=t.id, person_id=p.id, kind=kind, ref=str(ref)[:40], text=body[:3000])
        s.add(m)
        s.flush()
        m.hash = _hash({"id": m.id, "text": m.text, "phone": p.phone})
        view = _msg_view(s, m)
    say = f"{view['to']} ke liye message draft: aapke tap se hi jaayega."
    if view["no_messages"]:
        say += " (Inhone message mana kiya hai; sirf apne phone se, soch kar.)"
    if publish:
        _publish(tenant, "rentdesk_message", {"message": view, "say": say}, conv)
    return {"message": view, "status": "needs_tap", "say": say}


def edit_message(tenant: str, msg: str, text: str) -> dict:
    with _LOCK, session() as s:
        m = s.get(RdMessage, msg)
        if m is None or m.tenant_id != tenant or m.status != "draft":
            raise RentError("Draft nahi mila.")
        from ..net import policy
        if policy.secret_found(text) or re.search(r"\b(otp|pin|cvv|password|mpin)\b", text, re.I):
            raise RentError("Message mein OTP / PIN / card jaisi cheez hai; yeh kabhi nahi bheja jaata.")
        m.text = _clean(text, 3000)
        p = s.get(RdPerson, m.person_id)
        m.hash = _hash({"id": m.id, "text": m.text, "phone": p.phone if p else ""})
        return {"message": _msg_view(s, m), "say": "Draft badla."}


async def send_message(tenant: str, msg: str, via: str = "self", card_hash: str = "", by_tap: bool = False) -> dict:
    """ONLY her tap. via=self: she sends it from her own WhatsApp / SMS (the app opens the link; this marks it sent).
    via=business: her business WhatsApp number, only if the tenant wrote to it (Meta's 24 h window, enforced by the inbox)."""
    if not by_tap:
        raise RentError("Kirayedar ko message sirf aapke tap se jaata hai.")
    with session() as s:
        m = s.get(RdMessage, msg)
        if m is None or m.tenant_id != tenant:
            raise RentError("Message nahi mila.")
        if m.status != "draft":
            raise RentError(f"Yeh message {m.status} hai.")
        p = s.get(RdPerson, m.person_id)
        now_hash = _hash({"id": m.id, "text": m.text, "phone": p.phone if p else ""})
        if not card_hash or card_hash != m.hash or now_hash != m.hash:
            raise RentError("Message badal gaya hai; naya draft dekhiye.")
        if p is None or not p.phone:
            raise RentError("Kirayedar ka mobile nahi.")
        text, phone = m.text, p.phone
    if via == "business":
        from ..employee import inbox
        from ..employee.models import BizContact
        with session() as s:
            bc = s.scalars(select(BizContact).where(BizContact.tenant_id == tenant, BizContact.wa_id == "91" + phone)).first()
            bid = bc.id if bc else ""
        if not bid:
            raise RentError("Kirayedar ne business number par kabhi message nahi kiya: apne phone se bhejiye.")
        try:
            await inbox.send(tenant, bid, text, by="owner")
        except inbox.InboxError as e:
            raise RentError(str(e))
    elif via != "self":
        raise RentError("via: self | business")
    with session() as s:
        m = s.get(RdMessage, msg)
        m.status, m.via, m.sent_at = "sent", via, now()
        return {"message": _msg_view(s, m), "say": "Bhej diya (aapke tap se)." if via == "business" else "Aapke phone se bheja, darj kiya."}


def drop_message(tenant: str, msg: str) -> dict:
    with session() as s:
        m = s.get(RdMessage, msg)
        if m is None or m.tenant_id != tenant:
            raise RentError("Message nahi mila.")
        if m.status == "draft":
            m.status = "dropped"
        return {"message": _msg_view(s, m), "say": "Draft hataya."}


def messages(tenant: str, status: str = "draft") -> list[dict]:
    with session() as s:
        q = select(RdMessage).where(RdMessage.tenant_id == tenant)
        if status:
            q = q.where(RdMessage.status == status)
        return [_msg_view(s, m) for m in s.scalars(q.order_by(RdMessage.created_at.desc())).all()[:100]]


# ---------------------------------------------------------------- approvals (HER tap only)
def _basis(s, kind: str, target: str) -> dict:
    """What the card was made from, read NOW: a change after the card makes it stale."""
    if kind == "deduction":
        se = s.get(RdSettlement, target)
        t = s.get(RdTenancy, se.tenancy_id) if se else None
        if not se or not t:
            return {}
        return {"lines": _j(se.lines, []), "dues": _r2(sum(c.amount - c.paid for c in _open_charges(s, t, False))),
                "held": _held_deposit(s, t)}
    if kind in ("rent_change", "notice"):
        t = s.get(RdTenancy, target)
        return {"rent": t.rent, "hist": _j(t.rent_history, []), "status": t.status, "end": t.end, "vacate": t.vacate_on} if t else {}
    if kind == "repair":
        r = s.get(RdRequest, target)
        return {"quote": r.quote, "vendor": r.vendor_id, "who": r.who_pays, "status": r.status} if r else {}
    return {}


def _approval_view(a: RdApproval) -> dict:
    show = _j(a.show, {})
    return {"id": a.id, "number": a.number, "kind": a.kind, "kind_label": APPROVAL_LABEL.get(a.kind, a.kind), "target": a.target,
            "show": show, "hash": a.hash, "status": a.status, "reason": a.reason, "asked_by": a.asked_by, "money": a.kind in MONEY_KINDS,
            "created_at": _aware(a.created_at).isoformat(timespec="minutes") if a.created_at else ""}


def _make_approval(s, tenant: str, kind: str, target: str, show: dict, actor: str, conv: str) -> tuple[dict, bool]:
    h = _hash({"show": show, "basis": _basis(s, kind, target)})
    for o in s.scalars(select(RdApproval).where(RdApproval.tenant_id == tenant, RdApproval.kind == kind, RdApproval.target == target,
                                                RdApproval.status == "waiting")).all():
        if o.hash == h:
            return _approval_view(o), True
        o.status = "stale"
    a = RdApproval(tenant_id=tenant, number=f"A-{_next(s, tenant, 'approval'):04d}", kind=kind, target=target, show=_dump(show),
                   hash=h, asked_by=actor_name(tenant, actor), conv=conv)
    s.add(a)
    s.flush()
    return _approval_view(a), False


def _ask(tenant: str, view: dict, existing: bool, conv: str) -> dict:
    if existing:
        return {"approval": view, "status": "needs_tap", "existing": True, "say": f"{view['number']} pehle se aapki haan ka intezaar kar raha hai."}
    say = f"{view['number']}: {view['kind_label']} - {view['show'].get('title', '')}. Aapki haan ka card bheja hai."
    if view["show"].get("checks"):
        say += " Dhyaan: " + " ".join(view["show"]["checks"])
    _publish(tenant, "rentdesk_approval", {"approval": view, "say": say}, conv)
    return {"approval": view, "status": "needs_tap", "say": say}


def approval_card(tenant: str, aid: str) -> dict | None:
    with session() as s:
        a = s.get(RdApproval, aid)
        return _approval_view(a) if a and a.tenant_id == tenant else None


def needs_fingerprint(tenant: str, aid: str) -> bool:
    from .. import approvekey as ak
    c = approval_card(tenant, aid)
    return bool(c and c["money"] and ak.active_on(tenant))


def challenge(tenant: str, aid: str) -> dict:
    """approvekey's message format (kind 'rentdesk'): the phone signs this card as it is NOW."""
    from .. import approvekey as ak
    c = approval_card(tenant, aid)
    if not c or c["status"] != "waiting":
        raise RentError("Yeh card ab baaki nahi hai.")
    nonce = secrets.token_urlsafe(18)
    exp = datetime.now(timezone.utc) + ak.CHALLENGE_TTL
    msg = f"hoola-approve|v1|{tenant}|rentdesk|{aid}|{c['hash']}|{nonce}|{int(exp.timestamp())}"
    with session() as s:
        ch = ak.ApproveChallenge(tenant_id=tenant, kind="rentdesk", target=aid, digest=c["hash"], message=msg, expires_at=exp)
        s.add(ch)
        s.flush()
        chid = ch.id
    show = {"title": f"{c['kind_label']}: {c['show'].get('title', '')}"[:80], "amount": c["show"].get("amount_text", ""),
            "payee": c["show"].get("payee", "")}
    return {"challenge_id": chid, "message": msg, "show": show, "expires_at": exp.isoformat()}


def _verify_fp(tenant: str, aid: str, digest: str, proof: dict | None) -> None:
    from .. import approvekey as ak
    if not proof:
        raise RentError("fingerprint_needed")
    with session() as s:
        ak._settle(s, tenant)
        ok = ak._check(s, tenant, "rentdesk", aid, proof, digest)
    if not ok:
        raise RentError("fingerprint_invalid")


def decide(tenant: str, aid: str, yes: bool, card_hash: str = "", reason: str = "", proof: dict | None = None,
           by_tap: bool = False, conv: str = "") -> dict:
    """ONLY her tap in the app (API). Deductions and repair spends need her fingerprint once a phone key is active."""
    if not by_tap:
        raise RentError("Yeh faisla sirf aapke tap se (app ka card).")
    with session() as s:
        a = s.get(RdApproval, aid)
        if a is None or a.tenant_id != tenant:
            raise RentError("Card nahi mila.")
        if a.status != "waiting":
            return {"approval": _approval_view(a), "say": f"{a.number} pehle hi '{a.status}' hai."}
        now_hash = _hash({"show": _j(a.show, {}), "basis": _basis(s, a.kind, a.target)})
        if not card_hash or card_hash != a.hash or now_hash != a.hash:
            if now_hash != a.hash:
                a.status = "stale"
            raise RentError("Card ke baad cheezein badal gayi; naya card banaiye.")
        kind = a.kind
    if yes and kind in MONEY_KINDS:
        from .. import approvekey as ak
        if ak.active_on(tenant):
            _verify_fp(tenant, aid, card_hash, proof)
    with _LOCK, session() as s:
        a = s.get(RdApproval, aid)
        a.status = "approved" if yes else "rejected"
        a.reason = _clean(reason, 300)
        a.decided_at = now()
        view = _approval_view(a)
        effect = _apply(s, tenant, a) if yes else _reject(s, tenant, a)
    out = {"approval": view, **effect}
    out.setdefault("say", f"{view['number']}: {'haan' if yes else 'nahi'}.")
    _run_mirrors(tenant, out.pop("_jobs", []))
    letter = out.pop("_letter", None)
    if letter:
        out["file"] = _letter_file(tenant, letter[0], letter[1], letter[2])
    follow = out.pop("_draft", None)
    if follow:
        try:
            d = draft_message(tenant, follow["tenancy"], follow["kind"], follow.get("text", ""), ref=follow.get("ref", ""),
                              conv=conv or view.get("conv", ""), summary=follow.get("summary", ""))
            out["message"] = d["message"]
            out["say"] += " Kirayedar ke liye message draft taiyaar (aapke tap se jaayega)."
        except RentError as e:
            out["say"] += f" (Message draft nahi bana: {e})"
    return out


def _reject(s, tenant: str, a: RdApproval) -> dict:
    if a.kind == "deduction":
        se = s.get(RdSettlement, a.target)
        if se:
            se.status = "draft"
    if a.kind == "repair":
        r = s.get(RdRequest, a.target)
        if r:
            r.status = "rejected"
            _rlog(r, "Owner ne kharcha mana kiya")
    return {"say": f"{a.number}: nahi kiya" + (f" ({a.reason})" if a.reason else "") + "."}


def _apply(s, tenant: str, a: RdApproval) -> dict:
    show = _j(a.show, {})
    if a.kind == "rent_change":
        t = s.get(RdTenancy, a.target)
        hist = _j(t.rent_history, [])
        hist.append({"from": show["from"], "rent": show["new"], "why": show.get("why", "")})
        t.rent_history = _dump(hist)
        t.rent = show["new"]
        for c in s.scalars(select(RdCharge).where(RdCharge.tenancy_id == t.id, RdCharge.kind == "rent", RdCharge.paid <= 0.005,
                                                  RdCharge.status == "open")).all():
            ps = _date(c.period if len(c.period) == 10 else c.period + "-01")
            if ps and ps.isoformat() >= show["from"]:
                c.amount = _r2(show["new"])
        st = _st(s, tenant)
        text = R.notice_text("rent_increase", {**_letter_facts(s, t, st), "old": show["old"], "new": show["new"], "from": show["from"],
                                               "clause": show.get("clause", "")})
        return {"say": f"{a.number}: kiraya {_rs(show['old'])} -> {_rs(show['new'])} {show['from']} se.", "_letter": (t.id, "Rent_revision", text),
                "_draft": {"tenancy": t.id, "kind": "rent_change", "text": _short_letter(text), "ref": a.id}}
    if a.kind == "notice":
        t = s.get(RdTenancy, a.target)
        st = _st(s, tenant)
        nk = show.get("notice_kind", "vacate")
        facts = {**_letter_facts(s, t, st), "vacate_on": show.get("vacate_on", ""), "notice_months": t.notice_months,
                 "reason": show.get("reason", ""), "end": t.end, "new": show.get("new_rent") or "", "from": show.get("from", "")}
        text = R.notice_text("renewal" if nk == "renewal" else "vacate", facts)
        if nk == "vacate":
            t.status, t.notice_on, t.notice_by, t.vacate_on = "notice", today(tenant).isoformat(), "owner", show.get("vacate_on", "")
        return {"say": f"{a.number}: {show.get('title', '')} ki chitthi taiyaar.", "_letter": (t.id, "Notice" if nk == "vacate" else "Renewal", text),
                "_draft": {"tenancy": t.id, "kind": "renewal" if nk == "renewal" else "notice", "text": _short_letter(text), "ref": a.id}}
    if a.kind == "repair":
        r = s.get(RdRequest, a.target)
        r.status = "approved"
        _rlog(r, f"Owner ne {_rs(r.quote)} maana ({'kirayedar dega' if r.who_pays == 'tenant' else 'owner dengi'})")
        out = {"say": f"{a.number}: repair {_rs(r.quote)} maana. Vendor ko aap batayiye / bulaiye (draft link card par)."}
        if r.who_pays == "tenant" and r.tenancy_id:
            t = s.get(RdTenancy, r.tenancy_id)
            c = RdCharge(tenant_id=tenant, tenancy_id=t.id, kind="repair", due_on=today(tenant).isoformat(), amount=_r2(r.quote),
                         note=f"{r.number} {r.category}")
            s.add(c)
            s.flush()
            out["_jobs"] = []
            _mirror_due(s, tenant, c, t, out["_jobs"])
            out["say"] += " Agreement ke hisaab se kirayedar par charge joda."
        return out
    if a.kind == "deduction":
        se = s.get(RdSettlement, a.target)
        t = s.get(RdTenancy, se.tenancy_id)
        calc = _settle_calc(s, t, se)
        se.calc = _dump(calc)
        alloc, jobs = [], []
        for c in _open_charges(s, t, False):
            take = _r2(c.amount - c.paid)
            c.paid, c.status = c.amount, "paid"
            alloc.append({"charge_id": c.id, "kind": c.kind, "period": c.period, "amount": take})
            _mirror_paid(c, jobs)
        if alloc:
            s.add(RdPayment(tenant_id=tenant, tenancy_id=t.id, receipt_no="", amount=_r2(sum(x["amount"] for x in alloc)),
                            on=today(tenant).isoformat(), mode="deposit", alloc=_dump(alloc), by="Deposit se (aapki haan)"))
        se.status = "approved"
        summ = (f"deposit {_rs(calc['held'])}, baaki kiraya / bill {_rs(calc['dues'])}, katauti {_rs(calc['deductions'])}"
                f" -> {'wapas ' + _rs(calc['refund']) if calc['refund'] >= 0 else 'aapko dena ' + _rs(-calc['refund'])}")
        return {"say": f"{a.number}: deposit hisaab maana ({summ}). Wapas paise aap khud bhejiye, phir 'Maine de diya'.",
                "settlement": _settle_view(s, se), "_jobs": jobs,
                "_draft": {"tenancy": t.id, "kind": "refund", "summary": summ, "ref": se.id}}
    return {}


def _short_letter(text: str) -> str:
    body = text.split("Subject:", 1)[-1]
    return ("Subject:" + body).split("(Draft prepared", 1)[0].strip()[:1500]


def _letter_facts(s, t: RdTenancy, st: RdSettings) -> dict:
    u, p = s.get(RdUnit, t.unit_id), s.get(RdPerson, t.person_id)
    return {"date": today(t.tenant_id).strftime("%d-%m-%Y"), "tenant": p.name if p else "", "unit": f"{u.label}, {u.building}, {u.address}".strip(", ")
            if u else "", "landlord": st.landlord_name or st.business, "landlord_address": st.landlord_address,
            "agreement_date": t.start, "fee_word": "licence fee" if t.kind == "leave_licence" else "rent"}


def _letter_file(tenant: str, tid: str, name: str, text: str) -> dict:
    try:
        from .. import chatfiles, officegen
        with session() as s:
            num = s.get(RdTenancy, tid).number
        data = officegen.make_docx("", text)
        f = chatfiles.store(tenant, f"{name}_{num}.docx", data,
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        with session() as s:
            t = s.get(RdTenancy, tid)
            files = _j(t.files, [])
            files.append({"file_id": f.get("file_id"), "name": f.get("name"), "kind": name.lower()})
            t.files = _dump(files[-30:])
        _publish(tenant, "pc_file", {**f, "source": "rentdesk", "title": name.replace("_", " ")})
        return {"file_id": f.get("file_id"), "name": f.get("name")}
    except Exception as e:
        log.info("rentdesk letter file failed: %s", e)
        return {}


def approvals(tenant: str, status: str = "waiting") -> list[dict]:
    with session() as s:
        q = select(RdApproval).where(RdApproval.tenant_id == tenant)
        if status:
            q = q.where(RdApproval.status == status)
        return [_approval_view(a) for a in s.scalars(q.order_by(RdApproval.created_at.desc())).all()[:80]]


def _escalation_dates(t: RdTenancy) -> list[str]:
    s0, end = _date(t.start), _date(t.end)
    if not (t.escalation_pct and t.escalation_every and s0 and end):
        return []
    out, k = [], 1
    while k < 100:
        d = R.add_months(s0, t.escalation_every * k)
        if d > end:
            break
        out.append(d.isoformat())
        k += 1
    return out


def rent_change(tenant: str, tenancy: str, new_rent=None, from_date: str = "", why: str = "", clause: str = "",
                actor: str = "owner", conv: str = "") -> dict:
    """A rent increase / revision CARD. New rent = her number, or her agreement's escalation %. Only her tap applies it."""
    with _LOCK, session() as s:
        t = _tenancy(s, tenant, tenancy)
        if t.status not in ("active", "notice"):
            raise RentError(f"{t.number} chalu nahi.")
        d = _date(from_date)
        if not d:
            nxt = [x for x in _escalation_dates(t) if x >= today(tenant).isoformat()]
            d = _date(nxt[0]) if nxt else None
        if not d:
            raise RentError("Kab se? (taarikh)")
        old = _rent_on(t, d)
        new = R.money(new_rent)
        auto = False
        if new <= 0:
            if not t.escalation_pct:
                raise RentError("Naya kiraya batayiye (agreement mein escalation % nahi hai).")
            new, auto = round(old * (1 + t.escalation_pct / 100)), True
        if new <= 0 or new > 50_000_000:
            raise RentError("Naya kiraya sahi nahi.")
        st = _st(s, tenant)
        checks = []
        if R.is_mta(st.state) and (d - today(tenant)).days < 90:
            checks.append("Model Tenancy Act: kiraya badhane se 3 mahine pehle likhit notice.")
        if t.escalation_pct and not auto and old and (new / old - 1) * 100 > t.escalation_pct + 0.01:
            checks.append(f"Agreement mein {t.escalation_pct:g}% likha hai; yeh {((new / old - 1) * 100):.1f}% hai.")
        if t.lock_in_months and t.escalation_every and _date(t.start) and d < R.add_months(_date(t.start), t.escalation_every):
            checks.append("Agreement ke escalation samay se pehle.")
        p = s.get(RdPerson, t.person_id)
        show = {"title": f"{t.number} {p.name if p else ''}: {_rs(old)} -> {_rs(new)} {d.isoformat()} se", "tenancy": t.number,
                "old": old, "new": float(new), "from": d.isoformat(), "why": _clean(why, 200) or (f"agreement {t.escalation_pct:g}%" if auto else ""),
                "clause": _clean(clause, 40), "checks": checks}
        view, existing = _make_approval(s, tenant, "rent_change", t.id, show, actor, conv)
    return _ask(tenant, view, existing, conv)


def notice_request(tenant: str, tenancy: str, notice_kind: str = "vacate", vacate_on: str = "", reason: str = "", new_rent=None,
                   from_date: str = "", actor: str = "owner", conv: str = "") -> dict:
    """Notice to vacate / renewal offer -> CARD. The letter + message draft come only after her tap."""
    nk = "renewal" if notice_kind == "renewal" else "vacate"
    with _LOCK, session() as s:
        t = _tenancy(s, tenant, tenancy)
        if t.status not in ("active", "notice"):
            raise RentError(f"{t.number} chalu nahi.")
        p = s.get(RdPerson, t.person_id)
        checks = []
        if nk == "vacate":
            d = _date(vacate_on) or (R.add_months(today(tenant), max(t.notice_months, 1)))
            if (d - today(tenant)).days < 30 * max(t.notice_months, 0) - 2:
                checks.append(f"Agreement mein {t.notice_months} mahine ka notice hai; yeh {(d - today(tenant)).days} din hai.")
            lock = R.add_months(_date(t.start), t.lock_in_months) if t.lock_in_months and _date(t.start) else None
            if lock and d < lock:
                checks.append(f"Lock-in {lock.isoformat()} tak hai.")
            show = {"title": f"{t.number} {p.name if p else ''}: ghar khali karne ka notice, {d.isoformat()} tak", "notice_kind": nk,
                    "vacate_on": d.isoformat(), "reason": _clean(reason, 300), "checks": checks}
        else:
            nr = R.money(new_rent)
            frm = _date(from_date) or (_date(t.end) + timedelta(days=1) if _date(t.end) else today(tenant))
            show = {"title": f"{t.number} {p.name if p else ''}: renewal {frm.isoformat()} se" + (f", {_rs(nr)}" if nr else ""),
                    "notice_kind": nk, "from": frm.isoformat(), "new_rent": nr or None, "checks": checks}
        view, existing = _make_approval(s, tenant, "notice", t.id, show, actor, conv)
    return _ask(tenant, view, existing, conv)


def tenant_notice(tenant: str, tenancy: str, vacate_on: str, on: str = "", actor: str = "owner") -> dict:
    """The TENANT gave notice (she tells Hoola). Recorded; billing stops after the vacate date."""
    with _LOCK, session() as s:
        t = _tenancy(s, tenant, tenancy)
        d = _date(vacate_on)
        if not d:
            raise RentError("Kab khali karenge? (taarikh)")
        t.status, t.notice_on, t.notice_by, t.vacate_on = "notice", (_date(on) or today(tenant)).isoformat(), "tenant", d.isoformat()
        checks = []
        days = (d - _date(t.notice_on)).days
        if days < 30 * t.notice_months - 2:
            checks.append(f"Agreement mein {t.notice_months} mahine ka notice; yeh {days} din ka hai (agreement dekhiye, faisla aapka).")
        lock = R.add_months(_date(t.start), t.lock_in_months) if t.lock_in_months and _date(t.start) else None
        if lock and d < lock:
            checks.append(f"Lock-in {lock.isoformat()} tak tha (agreement ki shart aapke vakil se).")
        view = _tenancy_view(s, t)
    return {"tenancy": view, "checks": checks, "say": f"{view['number']}: kirayedar {d.isoformat()} ko khali karenge. Move-out inspection "
            "us din kijiye." + (" Dhyaan: " + " ".join(checks) if checks else "")}


# ---------------------------------------------------------------- vendors + repairs
def save_vendor(tenant: str, name: str, phone: str = "", trade: str = "other", notes: str = "", vendor: str = "") -> dict:
    with _LOCK, session() as s:
        v = s.get(RdVendor, vendor) if vendor else None
        if v is None:
            if not name.strip():
                raise RentError("Vendor ka naam.")
            v = RdVendor(tenant_id=tenant)
            s.add(v)
        if name:
            v.name = _clean(name, 120)
        if phone:
            v.phone = R.phone10(phone)
            if not v.phone:
                raise RentError("Vendor ka mobile 10 ank ka.")
        v.trade = trade if trade in R.TRADES else "other"
        if notes:
            v.notes = _clean(notes, 500)
        s.flush()
        return {"vendor": _vendor_view(v), "say": f"Vendor {v.name} ({R.TRADES[v.trade]}) save."}


def _vendor_view(v: RdVendor) -> dict:
    return {"id": v.id, "name": v.name, "phone": v.phone, "trade": v.trade, "trade_label": R.TRADES.get(v.trade, v.trade), "notes": v.notes}


def vendors(tenant: str) -> list[dict]:
    with session() as s:
        return [_vendor_view(v) for v in s.scalars(select(RdVendor).where(RdVendor.tenant_id == tenant).order_by(RdVendor.name)).all()]


def _rlog(r: RdRequest, what: str) -> None:
    lg = _j(r.log, [])
    lg.append({"at": now().isoformat(timespec="minutes"), "what": what[:200]})
    r.log = _dump(lg[-40:])


def _req_view(s, r: RdRequest) -> dict:
    u = s.get(RdUnit, r.unit_id)
    v = s.get(RdVendor, r.vendor_id) if r.vendor_id else None
    photos = s.scalars(select(RdPhoto).where(RdPhoto.owner_kind == "request", RdPhoto.owner_id == r.id)).all()
    draft = ""
    if v and v.phone:
        txt = f"Namaste {v.name}, {u.label if u else ''} {u.building if u else ''} {u.address if u else ''}: {r.text[:200]}. Kab aa sakte hain?"
        draft = f"https://wa.me/91{v.phone}?text={quote(txt)}"
    return {"id": r.id, "number": r.number, "unit": u.number if u else "", "unit_label": u.label if u else "", "tenancy_id": r.tenancy_id,
            "text": r.text, "category": r.category, "category_label": R.TRADES.get(r.category, r.category), "urgent": r.urgent,
            "status": r.status, "vendor": _vendor_view(v) if v else None, "quote": r.quote or None, "quote_text": _rs(r.quote) if r.quote else "",
            "who_pays": r.who_pays, "paid": r.paid or None, "raised_by": r.raised_by, "log": _j(r.log, []), "vendor_wa": draft,
            "photos": [{"id": p.id, "item": p.item} for p in photos],
            "created_at": _aware(r.created_at).isoformat(timespec="minutes") if r.created_at else ""}


def request_new(tenant: str, unit: str, text: str, actor: str = "owner", by: str = "", conv: str = "") -> dict:
    t_ = _clean(text, 1500)
    if not t_:
        raise RentError("Kya kharab hai?")
    cat, urgent = R.repair_category(t_)
    with _LOCK, session() as s:
        u = _unit(s, tenant, unit)
        lt = _live_tenancy(s, u.id)
        same = s.scalars(select(RdRequest).where(RdRequest.unit_id == u.id, RdRequest.status.in_(("open", "assigned", "waiting_haan")),
                                                 RdRequest.category == cat)).first()
        if same and cat != "other":
            _rlog(same, f"Phir se bataya: {t_[:120]}")
            return {"request": _req_view(s, same), "existing": True, "say": f"{same.number} pehle se khula hai ({R.TRADES.get(cat)}); usi mein joda."}
        r = RdRequest(tenant_id=tenant, number=f"M-{_next(s, tenant, 'request'):04d}", unit_id=u.id, tenancy_id=lt.id if lt else "",
                      text=t_, category=cat, urgent=urgent, raised_by=by or actor_name(tenant, actor))
        s.add(r)
        s.flush()
        _rlog(r, "Shikayat darj")
        vs = s.scalars(select(RdVendor).where(RdVendor.tenant_id == tenant, RdVendor.trade == cat)).all()
        view = _req_view(s, r)
    say = f"{view['number']}: {view['unit_label']} - {view['category_label']}" + (" (JALDI)" if urgent else "") + " darj."
    if urgent:
        say += " Gas / bijli / paani ka khatra ho to pehle main switch / valve band karwaiye; zaroorat ho to 112 / gas agency emergency."
    if vs:
        say += " Vendor: " + ", ".join(v.name for v in vs[:3]) + "."
    _publish(tenant, "rentdesk_alert", {"kind": "repair", "request": view, "say": say}, conv)
    return {"request": view, "say": say}


def request_assign(tenant: str, request: str, vendor: str = "", quote_amount=None, who_pays: str = "", actor: str = "owner",
                   conv: str = "") -> dict:
    """Vendor + his quote. A quote > 0 becomes a repair CARD (her tap; fingerprint once a phone key is active)."""
    with _LOCK, session() as s:
        r = s.get(RdRequest, request)
        if r is None or r.tenant_id != tenant:
            rows = s.scalars(select(RdRequest).where(RdRequest.tenant_id == tenant, RdRequest.number == str(request).upper())).all()
            r = rows[0] if rows else None
        if r is None:
            raise RentError("Repair request nahi mili.")
        if r.status in ("done", "closed"):
            raise RentError(f"{r.number} band ho chuki.")
        if vendor:
            v = s.get(RdVendor, vendor) or next((x for x in s.scalars(select(RdVendor).where(RdVendor.tenant_id == tenant)).all()
                                                 if x.name.lower() == vendor.lower() or x.phone == R.phone10(vendor)), None)
            if v is None:
                raise RentError(f"Vendor '{vendor}' nahi mila (pehle vendor jodiye).")
            r.vendor_id = v.id
            r.status = "assigned"
            _rlog(r, f"Vendor: {v.name}")
        st = _st(s, tenant)
        q = R.money(quote_amount)
        if who_pays:
            r.who_pays = "tenant" if who_pays.startswith(("ten", "kiray")) else "owner"
        elif q and st.minor_repair_limit and q <= st.minor_repair_limit and r.tenancy_id:
            r.who_pays = "tenant"
        if q > 0:
            r.quote = q
            r.status = "waiting_haan"
            _rlog(r, f"Quote {_rs(q)}")
            u = s.get(RdUnit, r.unit_id)
            vend = s.get(RdVendor, r.vendor_id) if r.vendor_id else None
            past = [x.quote for x in s.scalars(select(RdRequest).where(RdRequest.tenant_id == tenant, RdRequest.category == r.category,
                                                                        RdRequest.status.in_(("approved", "done", "closed")))).all() if x.quote]
            checks = []
            if len(past) >= 2:
                med = sorted(past)[len(past) // 2]
                if q > med * 1.3:
                    checks.append(f"Is kaam ka aam kharcha {_rs(med)}; yeh {round((q / med - 1) * 100)}% zyada.")
            if r.who_pays == "tenant":
                checks.append("Kirayedar par charge lagega (agreement ki shart dekhiye).")
            show = {"title": f"{r.number} {u.label if u else ''}: {R.TRADES.get(r.category, r.category)} {_rs(q)}", "amount": q,
                    "amount_text": _rs(q), "payee": vend.name if vend else "", "who_pays": r.who_pays, "what": r.text[:200], "checks": checks}
            view, existing = _make_approval(s, tenant, "repair", r.id, show, actor, conv)
            rid = r.id
        else:
            rv = _req_view(s, r)
            return {"request": rv, "say": f"{rv['number']} update."}
    out = _ask(tenant, view, existing, conv)
    with session() as s:
        out["request"] = _req_view(s, s.get(RdRequest, rid))
    return out


def request_done(tenant: str, request: str, paid=None, note: str = "", actor: str = "owner") -> dict:
    with _LOCK, session() as s:
        r = s.get(RdRequest, request)
        if r is None or r.tenant_id != tenant:
            raise RentError("Repair request nahi mili.")
        if r.quote > 0 and r.status not in ("approved",) and not is_owner(actor):
            raise RentError("Kharche par pehle owner ki haan chahiye.")
        if r.quote > 0 and r.status == "waiting_haan":
            raise RentError(f"{r.number}: kharche ka card abhi aapki haan ka intezaar kar raha hai.")
        r.status = "done"
        r.paid = R.money(paid) or r.paid
        _rlog(r, "Kaam poora" + (f", diya {_rs(r.paid)}" if r.paid else "") + (f": {_clean(note, 120)}" if note else ""))
        view = _req_view(s, r)
    return {"request": view, "say": f"{view['number']} poora." + (" Kirayedar ko batane ka draft chahiye to action=message kind=repair." if view["tenancy_id"] else "")}


def requests(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        q = select(RdRequest).where(RdRequest.tenant_id == tenant)
        rows = s.scalars(q.order_by(RdRequest.created_at.desc())).all()[:150]
        out = [_req_view(s, r) for r in rows]
    if status == "open":
        return [r for r in out if r["status"] in ("open", "assigned", "waiting_haan", "approved")]
    return [r for r in out if not status or r["status"] == status]


# ---------------------------------------------------------------- photos (EXIF / GPS stripped)
def _store_dir(tenant: str, owner_id: str) -> Path:
    safe = re.sub(r"[^\w.-]", "_", tenant)[:64]
    p = Path("data") / "rentdesk" / safe / owner_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def add_photo(tenant: str, owner_kind: str, owner_id: str, data: bytes, item: str = "") -> dict:
    """A photo for an inspection item or a repair. Re-encoded from pixels: EXIF (GPS, camera, time) never kept."""
    from PIL import Image, ImageOps
    if owner_kind not in ("inspection", "request"):
        raise RentError("photo: inspection | request")
    if not data or len(data) > 15 * 1024 * 1024:
        raise RentError("Photo khaali hai ya 15 MB se badi.")
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        raise RentError("Yeh photo nahi khuli (JPG / PNG / WEBP).")
    with _LOCK, session() as s:
        obj = s.get(RdInspection if owner_kind == "inspection" else RdRequest, owner_id)
        if obj is None or obj.tenant_id != tenant:
            raise RentError("Inspection / request nahi mili.")
        n = len(s.scalars(select(RdPhoto).where(RdPhoto.owner_id == owner_id)).all())
        if n >= MAX_PHOTOS:
            raise RentError(f"{MAX_PHOTOS} photo tak.")
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((1600, 1600))
        pid = new_id("rdf")
        path = _store_dir(tenant, owner_id) / f"{pid}.jpg"
        im.save(path, "JPEG", quality=84, optimize=True)        # no exif= argument: nothing of the original metadata is written
        ph = RdPhoto(id=pid, tenant_id=tenant, owner_kind=owner_kind, owner_id=owner_id, item=_clean(item, 80), path=str(path),
                     width=im.width, height=im.height)
        s.add(ph)
        if owner_kind == "inspection" and item:
            items = _j(obj.items, [])
            for it in items:
                if it.get("key") == item or it.get("item", "").lower() == item.lower():
                    it.setdefault("photos", []).append(pid)
            obj.items = _dump(items)
        s.flush()
        return {"photo": {"id": pid, "item": ph.item, "width": im.width, "height": im.height}, "say": "Photo save (location / camera ki jaankari hata di)."}


def photo_bytes(tenant: str, pid: str) -> bytes:
    with session() as s:
        p = s.get(RdPhoto, pid)
        if p is None or p.tenant_id != tenant:
            raise RentError("Photo nahi mili.")
        return Path(p.path).read_bytes()


# ---------------------------------------------------------------- inspections
def _insp_view(s, x: RdInspection) -> dict:
    return {"id": x.id, "tenancy_id": x.tenancy_id, "kind": x.kind, "on": x.on, "items": _j(x.items, []), "meters": _j(x.meters, {}),
            "keys": x.keys, "status": x.status, "signed_by": x.signed_by,
            "photos": [{"id": p.id, "item": p.item} for p in s.scalars(select(RdPhoto).where(RdPhoto.owner_id == x.id)).all()]}


def inspection_start(tenant: str, tenancy: str, kind: str = "move_in", on: str = "") -> dict:
    kind = "move_out" if kind == "move_out" else "move_in"
    with _LOCK, session() as s:
        t = _tenancy(s, tenant, tenancy)
        ex = s.scalars(select(RdInspection).where(RdInspection.tenancy_id == t.id, RdInspection.kind == kind)).first()
        if ex:
            return {"inspection": _insp_view(s, ex), "existing": True, "say": f"{t.number} ka {kind} inspection pehle se hai."}
        u = s.get(RdUnit, t.unit_id)
        items = [{"key": f"i{i}", "room": r, "item": it, "condition": "", "note": "", "photos": []} for i, (r, it) in enumerate(R.STANDARD_ITEMS)]
        for j, inv in enumerate(_j(u.inventory, []) if u else []):
            items.append({"key": f"v{j}", "room": "Saamaan", "item": f"{inv['item']} x{inv.get('qty', 1)}", "condition": "", "note": "", "photos": []})
        if kind == "move_out":
            mi = s.scalars(select(RdInspection).where(RdInspection.tenancy_id == t.id, RdInspection.kind == "move_in")).first()
            if mi:
                items = [{**i, "condition": "", "note": "", "photos": []} for i in _j(mi.items, [])]
        x = RdInspection(tenant_id=tenant, tenancy_id=t.id, kind=kind, on=(_date(on) or today(tenant)).isoformat(), items=_dump(items))
        s.add(x)
        s.flush()
        return {"inspection": _insp_view(s, x), "say": f"{t.number}: {kind.replace('_', '-')} inspection shuru ({len(items)} cheezein). "
                "Har cheez ki halat (good / fair / damaged / missing) aur photo."}


def inspection_update(tenant: str, inspection: str, items: list | None = None, meters: dict | None = None, keys=None,
                      signed_by: str = "", close: bool = False) -> dict:
    with _LOCK, session() as s:
        x = s.get(RdInspection, inspection)
        if x is None or x.tenant_id != tenant:
            raise RentError("Inspection nahi mili.")
        if x.status == "closed":
            raise RentError("Inspection band ho chuki.")
        cur = _j(x.items, [])
        for it in items or []:
            if not isinstance(it, dict):
                continue
            cond = str(it.get("condition") or "").lower()
            cond = {"theek": "good", "achha": "good", "ok": "good", "thik": "fair", "toota": "damaged", "kharab": "damaged",
                    "gayab": "missing", "nahi": "missing"}.get(cond, cond)
            if cond and cond not in ("good", "fair", "damaged", "missing"):
                raise RentError("Halat: good / fair / damaged / missing.")
            hit = next((c for c in cur if c["key"] == it.get("key") or (it.get("item") and c["item"].lower() == str(it["item"]).lower()
                                                                         and c["room"].lower() == str(it.get("room", c["room"])).lower())), None)
            if hit is None:
                hit = {"key": f"x{len(cur)}", "room": _clean(it.get("room") or "Doosra", 40), "item": _clean(it.get("item") or "", 80),
                       "condition": "", "note": "", "photos": []}
                if not hit["item"]:
                    continue
                cur.append(hit)
            if cond:
                hit["condition"] = cond
            if it.get("note") is not None:
                hit["note"] = _clean(str(it["note"]), 200)
        x.items = _dump(cur)
        if meters:
            m = _j(x.meters, {})
            for k, v in meters.items():
                m[str(k)[:20]] = R.money(v)
            x.meters = _dump(m)
        if keys is not None:
            x.keys = int(R.money(keys))
        if signed_by:
            x.signed_by = _clean(signed_by, 160)
        if close:
            x.status = "closed"
            t = s.get(RdTenancy, x.tenancy_id)
            if x.kind == "move_in":
                c = _j(t.checklist, {})
                c["move_in"] = x.on
                t.checklist = _dump(c)
        return {"inspection": _insp_view(s, x), "say": "Inspection update" + (" aur band." if close else ".")}


def inspection_compare(tenant: str, tenancy: str) -> dict:
    with session() as s:
        t = _tenancy(s, tenant, tenancy)
        mi = s.scalars(select(RdInspection).where(RdInspection.tenancy_id == t.id, RdInspection.kind == "move_in")).first()
        mo = s.scalars(select(RdInspection).where(RdInspection.tenancy_id == t.id, RdInspection.kind == "move_out")).first()
        if not mo:
            raise RentError("Move-out inspection abhi nahi hui.")
        worse = R.compare_inspections(_j(mi.items, []) if mi else [], _j(mo.items, []))
        meters = {"move_in": _j(mi.meters, {}) if mi else {}, "move_out": _j(mo.meters, {})}
    say = (f"{len(worse)} cheezein pehle se kharab dikh rahi hain: " + "; ".join(f"{w['room']} {w['item']} ({w['was']} -> {w['now']})" for w in worse[:6])
           + ". Rakam aap likhiye (aam ghisaav nahi katta).") if worse else "Move-in se koi nayi kharabi darj nahi."
    if not mi:
        say += " (Move-in inspection darj nahi thi, isliye tulna kamzor hai.)"
    return {"worse": worse, "meters": meters, "say": say}


# ---------------------------------------------------------------- settlement
def _settle_calc(s, t: RdTenancy, se: RdSettlement) -> dict:
    held = _held_deposit(s, t)
    dues = _r2(sum(c.amount - c.paid for c in _open_charges(s, t, False)))
    ded = _r2(sum(x.get("amount", 0) for x in _j(se.lines, [])))
    return {"held": held, "dues": dues, "deductions": ded, "refund": _r2(held - dues - ded)}


def _settle_view(s, se: RdSettlement) -> dict:
    t = s.get(RdTenancy, se.tenancy_id)
    c = _settle_calc(s, t, se) if se.status in ("draft", "waiting") else (_j(se.calc, {}) or _settle_calc(s, t, se))
    return {"id": se.id, "tenancy_id": t.id, "tenancy": t.number, "lines": _j(se.lines, []), "status": se.status, **c,
            "held_text": _rs(c["held"]), "dues_text": _rs(c["dues"]), "deductions_text": _rs(c["deductions"]), "refund_text": _rs(abs(c["refund"])),
            "tenant_owes": c["refund"] < 0, "refund_paid": se.refund_paid or None, "approval_id": se.approval_id}


def settlement_start(tenant: str, tenancy: str) -> dict:
    with _LOCK, session() as s:
        t = _tenancy(s, tenant, tenancy)
        se = s.scalars(select(RdSettlement).where(RdSettlement.tenancy_id == t.id, RdSettlement.status != "rejected")).first()
        if se is None:
            se = RdSettlement(tenant_id=tenant, tenancy_id=t.id)
            s.add(se)
            s.flush()
        view = _settle_view(s, se)
    try:
        cmp = inspection_compare(tenant, tenancy)["worse"]
    except RentError:
        cmp = []
    view["suggest"] = cmp
    return {"settlement": view, "say": f"{view['tenancy']}: deposit {view['held_text']}, baaki kiraya / bill {view['dues_text']}. "
            + (f"{len(cmp)} kharab cheezein: rakam aap likhiye." if cmp else "Katauti ho to rakam aur wajah aap likhiye.")}


def settlement_line(tenant: str, settlement: str, what: str, amount, reason: str = "", photos: list | None = None,
                    remove: bool = False, actor: str = "owner") -> dict:
    """Her deduction line. Amount ONLY from her (bill / quote / her words); never a Hoola guess."""
    with _LOCK, session() as s:
        se = s.get(RdSettlement, settlement)
        if se is None or se.tenant_id != tenant:
            raise RentError("Settlement nahi mila.")
        if se.status not in ("draft", "waiting"):
            raise RentError("Settlement par faisla ho chuka.")
        lines = _j(se.lines, [])
        w = _clean(what, 120)
        if remove:
            lines = [x for x in lines if x.get("what", "").lower() != w.lower()]
        else:
            a = R.money(amount)
            if a <= 0:
                raise RentError("Katauti ki rakam (aapka number / bill) chahiye.")
            if not w:
                raise RentError("Kis cheez ki katauti?")
            lines = [x for x in lines if x.get("what", "").lower() != w.lower()]
            lines.append({"what": w, "amount": _r2(a), "reason": _clean(reason, 200), "photos": [str(p) for p in (photos or [])][:10]})
        se.lines = _dump(lines)
        if se.status == "waiting":
            se.status = "draft"                  # the card no longer matches: a new one is needed
        return {"settlement": _settle_view(s, se), "say": "Katauti line save."}


def settlement_request(tenant: str, settlement: str, actor: str = "owner", conv: str = "") -> dict:
    """Deductions / dues offset from the deposit -> CARD (fingerprint once a phone key is active). No deduction and no dues = no card."""
    with _LOCK, session() as s:
        se = s.get(RdSettlement, settlement)
        if se is None or se.tenant_id != tenant:
            raise RentError("Settlement nahi mila.")
        if se.status not in ("draft", "waiting"):
            raise RentError(f"Settlement {se.status} hai.")
        t = s.get(RdTenancy, se.tenancy_id)
        c = _settle_calc(s, t, se)
        if c["deductions"] <= 0 and c["dues"] <= 0:
            se.status, se.calc = "approved", _dump(c)
            view = _settle_view(s, se)
            return {"settlement": view, "say": f"Koi katauti nahi: poora deposit {view['held_text']} wapas. Aap khud bhejiye, phir 'Maine de diya'."}
        p = s.get(RdPerson, t.person_id)
        checks = []
        if c["refund"] < 0:
            checks.append(f"Deposit se zyada: kirayedar ko {_rs(-c['refund'])} aur dena hoga.")
        if any(not x.get("reason") for x in _j(se.lines, [])):
            checks.append("Kuch katauti bina wajah ke hain.")
        if not s.scalars(select(RdInspection).where(RdInspection.tenancy_id == t.id, RdInspection.kind == "move_in")).first():
            checks.append("Move-in inspection darj nahi: nuksaan ka saboot kamzor.")
        show = {"title": f"{t.number} {p.name if p else ''}: deposit {_rs(c['held'])} - dues {_rs(c['dues'])} - katauti {_rs(c['deductions'])}",
                "amount": c["deductions"] + c["dues"], "amount_text": _rs(c["deductions"] + c["dues"]), "payee": p.name if p else "",
                "lines": _j(se.lines, []), **c, "checks": checks}
        view, existing = _make_approval(s, tenant, "deduction", se.id, show, actor, conv)
        se.status, se.approval_id = "waiting", view["id"]
    return _ask(tenant, view, existing, conv)


def refund_paid(tenant: str, settlement: str, amount=None, ref: str = "", actor: str = "owner") -> dict:
    """She sent the refund herself. Ends the tenancy (unit vacant)."""
    if not is_owner(actor):
        raise RentError("Sirf owner.")
    with _LOCK, session() as s:
        se = s.get(RdSettlement, settlement)
        if se is None or se.tenant_id != tenant:
            raise RentError("Settlement nahi mila.")
        if se.status != "approved":
            raise RentError("Pehle deposit hisaab par aapki haan (card).")
        t = s.get(RdTenancy, se.tenancy_id)
        c = _j(se.calc, {}) or _settle_calc(s, t, se)
        se.refund_paid = R.money(amount) if amount not in (None, "") else max(0.0, c["refund"])
        se.refund_ref = re.sub(r"\W", "", str(ref))[-6:]
        se.status = "paid"
        for ch in s.scalars(select(RdCharge).where(RdCharge.tenancy_id == t.id, RdCharge.kind == "deposit")).all():
            ch.note = (ch.note + " | settled").strip(" |")
        t.status = "ended"
        if not t.vacate_on:
            t.vacate_on = today(tenant).isoformat()
        view = _settle_view(s, se)
    return {"settlement": view, "say": f"Deposit wapas {_rs(view['refund_paid'] or 0)} darj; {view['tenancy']} khatam, unit khali. "
            "Kuch din baad kirayedar ki jaankari mitane (DPDP) ke liye `forget`."}


def settlement_pdf(tenant: str, settlement: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas  # noqa: F401
    from .. import indicpdf as _indicpdf
    with session() as s:
        se = s.get(RdSettlement, settlement)
        if se is None or se.tenant_id != tenant:
            raise RentError("Settlement nahi mila.")
        v = _settle_view(s, se)
        t = s.get(RdTenancy, se.tenancy_id)
        u, p, st = s.get(RdUnit, t.unit_id), s.get(RdPerson, t.person_id), _st(s, tenant)
        dues = [_charge_view(c) for c in _open_charges(s, t, False)] if se.status in ("draft", "waiting") else []
        head = (st.landlord_name or st.business or "[landlord]", p.name if p else "", f"{u.label} {u.building}" if u else "", t.start,
                t.vacate_on or t.end)
    bio = io.BytesIO()
    c = _indicpdf.Canvas(bio, pagesize=A4)
    w, h = A4
    y = h - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, _latin(f"DEPOSIT SETTLEMENT - {v['tenancy']}" + ("" if se.status in ("approved", "paid") else " (DRAFT)")))
    c.setFont("Helvetica", 10)
    y -= 24
    for line in (f"Landlord: {head[0]}", f"Tenant: {head[1]}", f"Premises: {head[2]}", f"Period: {head[3]} to {head[4]}", ""):
        c.drawString(40, y, _latin(line))
        y -= 15
    rows = [("Security deposit held", v["held"])] + [(f"Less: {d['kind_label']} {d['period']}", -d["left"]) for d in dues]
    if not dues and v["dues"]:
        rows.append(("Less: pending rent / bills", -v["dues"]))
    rows += [(f"Less: {x['what']}" + (f" ({x['reason']})" if x.get("reason") else ""), -x["amount"]) for x in v["lines"]]
    for label, amt in rows:
        c.drawString(40, y, _latin(label)[:80])
        c.drawRightString(w - 40, y, _latin(f"Rs {amt:,.2f}"))
        y -= 15
    c.setFont("Helvetica-Bold", 11)
    y -= 5
    c.drawString(40, y, "Refund to tenant" if not v["tenant_owes"] else "Payable by tenant")
    c.drawRightString(w - 40, y, _latin(f"Rs {abs(v['refund']):,.2f}"))
    c.setFont("Helvetica", 8)
    c.drawString(40, 60, _latin("Normal wear and tear is not deducted. Prepared by Hoola from the owner's record; check with your lawyer if disputed."))
    c.showPage()
    c.save()
    return bio.getvalue()


def settlement_file(tenant: str, settlement: str, conv: str = "") -> dict:
    from .. import chatfiles
    pdf = settlement_pdf(tenant, settlement)
    f = chatfiles.store(tenant, f"Deposit_settlement_{settlement[-6:]}.pdf", pdf, "application/pdf")
    _publish(tenant, "pc_file", {**f, "source": "rentdesk", "title": "Deposit settlement"}, conv)
    return {"file": f, "say": "Deposit hisaab ka PDF."}


# ---------------------------------------------------------------- agreement draft
def agreement_text(tenant: str, tenancy: str) -> tuple[str, list[str]]:
    with session() as s:
        t = _tenancy(s, tenant, tenancy)
        u, p, st = s.get(RdUnit, t.unit_id), s.get(RdPerson, t.person_id), _st(s, tenant)
        blanks: list[str] = []

        def g(v, label):
            if v in (None, "", 0, 0.0):
                blanks.append(label)
                return f"[{label}]"
            return str(v)

        fee = "licence fee" if t.kind == "leave_licence" else "rent"
        who1, who2 = ("Licensor", "Licensee") if t.kind == "leave_licence" else ("Landlord", "Tenant")
        idl = ", ".join(f"{k.upper()} {v.get('masked', '')}" for k, v in _j(p.ids, {}).items()) if p else ""
        lines = [
            f"# {R.AGREEMENT_KINDS.get(t.kind, 'Agreement').upper()} - DRAFT",
            "**DRAFT prepared by Hoola from the owner's facts. Not legal advice: get it checked by a lawyer before signing / registration.**",
            "",
            f"This agreement is made at {g(st.city or (u.city if u else ''), 'place')} on {g('', 'date of signing')} between:",
            f"1. {g(st.landlord_name or st.business, 'owner name')}, residing at {g(st.landlord_address, 'owner address')} "
            f"(the {who1}){(' on behalf of owner ' + u.owner_name) if u and u.owner_name else ''};",
            f"2. {g(p.name if p else '', 'tenant name')}, permanent address {g(p.address if p else '', 'tenant permanent address')}"
            f"{(', ' + idl) if idl else ''} (the {who2}).",
            "",
            "## 1. Premises",
            f"{g(u.label if u else '', 'unit')}, {g(u.building if u else '', 'building')}, {g(u.address if u else '', 'address')} "
            f"{u.pin if u else ''}; area {g(u.area_sqft if u else 0, 'area sq ft')} sq ft{(' ' + u.area_note) if u and u.area_note else ''}; "
            f"{u.furnished or 'furnishing [as per annexure]' if u else ''}.",
            "## 2. Period",
            f"{t.months} months from {g(t.start, 'start date')} to {g(t.end, 'end date')}." +
            (f" Lock-in of {t.lock_in_months} months." if t.lock_in_months else ""),
            "## 3. Monthly " + fee,
            f"Rs {g(t.rent, 'monthly ' + fee)} per month, payable on or before day {t.due_day or 'the start day'} of each month by "
            f"bank transfer / UPI to the {who1}'s account. Receipts will be given for every payment.",
            ("## 4. Escalation\n" + f"The {fee} shall increase by {t.escalation_pct:g}% every {t.escalation_every} months.")
            if t.escalation_pct and t.escalation_every else "## 4. Escalation\nNo escalation during this period unless agreed in writing.",
            "## 5. Security deposit",
            f"Rs {g(t.deposit, 'security deposit')}, interest free, refundable at the end after the move-out inspection, less unpaid "
            "dues and the cost of damage beyond normal wear and tear, with a written statement.",
            "## 6. Maintenance and utilities",
            f"Society maintenance of Rs {t.maintenance:g} per month will be paid by the {who2 if t.maintenance_by == 'tenant' else who1}."
            if t.maintenance else "Society maintenance, if any, by the [who pays].",
            f"Electricity, water and gas bills for the period of occupation by the {who2} as per the meters"
            f"{(' (consumer no ' + u.electricity_no + ')') if u and u.electricity_no else ''}.",
            "## 7. Use",
            f"Only for {t.purpose or ('residence of the ' + who2 + ' and family' if (u and u.use == 'residential') else 'the business of the ' + who2)}. "
            "No sub-letting, assignment or illegal / hazardous use.",
            "## 8. Repairs",
            f"Minor day-to-day repairs by the {who2}" + (f" up to Rs {st.minor_repair_limit:g}" if st.minor_repair_limit else "") +
            f"; structural repairs by the {who1}. The {who1} may enter for inspection / repairs with 24 hours' notice.",
            "## 9. Notice",
            f"Either party may end this agreement with {t.notice_months} month(s) written notice" +
            (f", but not before the lock-in" if t.lock_in_months else "") + ".",
        ]
        if t.kind == "leave_licence":
            lines += ["## 10. Licence only",
                      "This is a leave and licence; no tenancy or other right in the premises is created. The Licensee shall vacate on "
                      "expiry or earlier termination (Maharashtra Rent Control Act 1999, s.24)."]
        if (st.state or "").upper() == "MH":
            lines += ["## 11. Registration and police intimation",
                      "This agreement shall be registered (Maharashtra Rent Control Act 1999, s.55; online e-registration with the IGR). "
                      f"Stamp duty Rs {g(t.stamp_duty, 'stamp duty (IGR calculator)')} and registration fee Rs {g(t.reg_fee, 'registration fee')} "
                      "borne by [who pays]. Tenant details will be given to the police as required."]
        else:
            lines += ["## 11. Stamp duty, registration, police",
                      f"Stamp duty Rs {g(t.stamp_duty, 'stamp duty as per state law')} borne by [who pays]; registered where the law requires; "
                      "tenant verification with the local police."]
        inv = _j(u.inventory, []) if u else []
        lines += ["## Annexure: fittings and furniture"] + ([f"- {x['item']} x{x.get('qty', 1)}" for x in inv] or ["- [list]"])
        lines += ["", f"{who1}: ____________________        {who2}: ____________________",
                  "Witness 1: ____________________        Witness 2: ____________________"]
        if st.rules:
            lines += ["", f"(Owner's own rules to add: {st.rules[:500]})"]
    return "\n".join(lines), blanks


def agreement_file(tenant: str, tenancy: str, conv: str = "") -> dict:
    from .. import chatfiles, officegen
    text, blanks = agreement_text(tenant, tenancy)
    data = officegen.make_docx("", text)
    with session() as s:
        num = _tenancy(s, tenant, tenancy).number
    f = chatfiles.store(tenant, f"Agreement_draft_{num}.docx", data,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    with _LOCK, session() as s:
        t = _tenancy(s, tenant, tenancy)
        files = _j(t.files, [])
        files.append({"file_id": f.get("file_id"), "name": f.get("name"), "kind": "agreement"})
        t.files = _dump(files[-30:])
        num = t.number
    _publish(tenant, "pc_file", {**f, "source": "rentdesk", "title": f"Agreement draft {num}"}, conv)
    say = f"{num}: agreement ka Word draft (vakil se padhwaiye)."
    if blanks:
        say += " Khaali jagah: " + ", ".join(blanks[:8]) + "."
    return {"file": f, "blanks": blanks, "say": say}


# ---------------------------------------------------------------- DPDP
def forget(tenant: str, person: str, actor: str = "owner") -> dict:
    """Erase a past tenant's personal details (DPDP: purpose over). Amounts / receipt numbers stay for her accounts."""
    if not is_owner(actor):
        raise RentError("Sirf owner.")
    with _LOCK, session() as s:
        p = _person(s, tenant, person)
        live = s.scalars(select(RdTenancy).where(RdTenancy.person_id == p.id, RdTenancy.status.in_(("draft", "active", "notice")))).all()
        if live:
            raise RentError("Is kirayedar ki tenancy abhi chalu hai.")
        ten_ids = [t.id for t in s.scalars(select(RdTenancy).where(RdTenancy.person_id == p.id)).all()]
        open_se = s.scalars(select(RdSettlement).where(RdSettlement.tenancy_id.in_(ten_ids), RdSettlement.status.in_(("draft", "waiting", "approved")))).all() \
            if ten_ids else []
        if open_se:
            raise RentError("Deposit hisaab abhi poora nahi (pehle 'Maine de diya').")
        recs = [x.get("record", "") for x in _j(p.ids, {}).values()]
        for ph in s.scalars(select(RdPhoto).where(RdPhoto.tenant_id == tenant)).all():
            insp = s.get(RdInspection, ph.owner_id)
            if insp and insp.tenancy_id in ten_ids:
                try:
                    Path(ph.path).unlink(missing_ok=True)
                except Exception:
                    pass
                s.delete(ph)
        for m in s.scalars(select(RdMessage).where(RdMessage.person_id == p.id)).all():
            m.text, m.status = "[mitaya]", "dropped" if m.status == "draft" else m.status
        num = p.number
        p.name, p.phone, p.email, p.address, p.members, p.emergency, p.employer = f"Purana kirayedar {num}", "", "", "", "[]", "", ""
        p.ids, p.notes, p.gstin, p.forgotten = "{}", "", "", True
    from .. import idvault
    for rid in recs:
        try:
            idvault.delete(tenant, rid)
        except Exception:
            pass
    return {"say": f"{num} ki niji jaankari mita di (naam, phone, ID, photo). Kiraye ke amount / receipt number hisaab ke liye rahe."}


# ---------------------------------------------------------------- tenants on her business WhatsApp
def customer_status(tenant: str, wa_id: str) -> dict:
    ph = R.phone10(wa_id)
    with session() as s:
        ps = s.scalars(select(RdPerson).where(RdPerson.tenant_id == tenant, RdPerson.phone == ph, RdPerson.forgotten.is_(False))).all() if ph else []
        out = []
        for p in ps:
            for t in s.scalars(select(RdTenancy).where(RdTenancy.person_id == p.id, RdTenancy.status.in_(("active", "notice")))).all():
                v = _tenancy_view(s, t)
                opens = [_charge_view(c) for c in _open_charges(s, t, t.status == "active")]
                out.append({"tenancy": v["number"], "unit": v["unit_label"], "rent": v["rent_text"], "due_now": v["due_now_text"] or _rs(0),
                            "open": [{"what": f"{c['kind_label']} {c['period']}", "left": c["left_text"], "due_on": c["due_on"]} for c in opens],
                            "end": v["end"], "id": v["id"]})
    link = ""
    if out:
        try:
            link = pay_link(tenant, out[0]["id"]).get("url", "")
        except RentError:
            link = ""
    for o in out:
        o.pop("id", None)
    return {"tenancies": out, "pay_link": link, "note": "Sirf isi number ki tenancy. Paise unke apne UPI app se; Hoola paise nahi leta."}


def customer_repair(tenant: str, wa_id: str, text: str) -> dict:
    ph = R.phone10(wa_id)
    with session() as s:
        ps = s.scalars(select(RdPerson).where(RdPerson.tenant_id == tenant, RdPerson.phone == ph, RdPerson.forgotten.is_(False))).all() if ph else []
        unit = ""
        for p in ps:
            t = s.scalars(select(RdTenancy).where(RdTenancy.person_id == p.id, RdTenancy.status.in_(("active", "notice")))).first()
            if t:
                unit = t.unit_id
                who = p.name
                break
    if not unit:
        raise RentError("Is number par koi chalu kirayedari nahi mili.")
    r = request_new(tenant, unit, text, actor="customer", by=f"Kirayedar {who}")
    rq = r["request"]
    return {"number": rq["number"], "category": rq["category_label"], "urgent": rq["urgent"],
            "say": f"Shikayat {rq['number']} darj; malik ko bata diya. Kharche ka faisla unka."}


# ---------------------------------------------------------------- day / overview / register
def day(tenant: str) -> dict:
    on = today(tenant)
    bill_due(tenant)
    with session() as s:
        st = _st(s, tenant)
        ts = s.scalars(select(RdTenancy).where(RdTenancy.tenant_id == tenant, RdTenancy.status.in_(("active", "notice")))).all()
        overdue, due_today, renew, pending, vacating = [], [], [], [], []
        for t in ts:
            v = _tenancy_view(s, t)
            for c in _open_charges(s, t, False):
                if c.due_on < on.isoformat():
                    overdue.append({"tenancy": v["number"], "who": v["tenant_name"], "unit": v["unit_label"], "what": f"{R.CHARGE_KINDS[c.kind]} {c.period}",
                                    "left": _r2(c.amount - c.paid), "days": (on - _date(c.due_on)).days})
                elif c.due_on == on.isoformat():
                    due_today.append({"tenancy": v["number"], "who": v["tenant_name"], "left": _r2(c.amount - c.paid)})
            if v["days_left"] is not None and 0 <= v["days_left"] <= max(_j(st.renewal_windows, [60]) or [60]) and t.status == "active":
                renew.append({"tenancy": v["number"], "who": v["tenant_name"], "end": v["end"], "days_left": v["days_left"]})
            done = _j(t.checklist, {})
            miss = [i for i in ("registration", "police") if i not in done]
            if miss and (on - _date(t.start)).days >= 0:
                pending.append({"tenancy": v["number"], "who": v["tenant_name"], "missing": miss})
            if t.vacate_on and 0 <= (_date(t.vacate_on) - on).days <= 30:
                vacating.append({"tenancy": v["number"], "who": v["tenant_name"], "on": t.vacate_on})
        drafts = len(s.scalars(select(RdMessage).where(RdMessage.tenant_id == tenant, RdMessage.status == "draft")).all())
        waiting = len(s.scalars(select(RdApproval).where(RdApproval.tenant_id == tenant, RdApproval.status == "waiting")).all())
        repairs = len([r for r in s.scalars(select(RdRequest).where(RdRequest.tenant_id == tenant)).all()
                       if r.status in ("open", "assigned", "waiting_haan", "approved")])
        vacant = len([u for u in s.scalars(select(RdUnit).where(RdUnit.tenant_id == tenant, RdUnit.archived.is_(False))).all()
                      if _live_tenancy(s, u.id) is None])
    parts = []
    if overdue:
        parts.append(f"Baaki: {len(overdue)} ({_rs(sum(x['left'] for x in overdue))})")
    if due_today:
        parts.append(f"Aaj due: {len(due_today)}")
    if drafts:
        parts.append(f"{drafts} message draft aapke tap ka intezaar")
    if waiting:
        parts.append(f"{waiting} card aapki haan ke liye")
    if renew:
        parts.append("Renewal jaldi: " + ", ".join(f"{x['tenancy']} ({x['days_left']} din)" for x in renew[:3]))
    if pending:
        parts.append("Registration / police baaki: " + ", ".join(x["tenancy"] for x in pending[:4]))
    if repairs:
        parts.append(f"{repairs} repair khule")
    if vacating:
        parts.append("Khali honge: " + ", ".join(f"{x['tenancy']} {x['on']}" for x in vacating[:3]))
    if vacant:
        parts.append(f"{vacant} unit khali")
    return {"overdue": overdue, "due_today": due_today, "renewals": renew, "pending": pending, "vacating": vacating, "drafts": drafts,
            "waiting": waiting, "repairs": repairs, "vacant": vacant, "say": ". ".join(parts) + "." if parts else "Kiraye ka sab theek."}


def overview(tenant: str) -> dict:
    return {"settings": settings(tenant), "day": day(tenant), "units": units(tenant), "tenancies": tenancies(tenant),
            "people": people(tenant), "approvals": approvals(tenant), "messages": messages(tenant), "requests": requests(tenant, "open"),
            "vendors": vendors(tenant), "unit_kinds": R.UNIT_KINDS, "trades": R.TRADES, "charge_kinds": R.CHARGE_KINDS,
            "never": list(R.NEVER)}


def register_file(tenant: str, conv: str = "") -> dict:
    from .. import chatfiles, officegen
    sheets = {
        "Units": [["Unit", "Naam", "Building", "Kind", "Status", "Kirayedar"]] +
                 [[u["number"], u["label"], u["building"], u["kind_label"], u["status"], u["tenant_name"]] for u in units(tenant)],
        "Tenancies": [["No", "Unit", "Kirayedar", "Shuru", "Khatam", "Kiraya", "Deposit", "Deposit paas", "Baaki", "Status"]] +
                     [[t["number"], t["unit_label"], t["tenant_name"], t["start"], t["end"], t["rent"], t["deposit"], t["deposit_held"],
                       t["due_now"], t["status_label"]] for t in tenancies(tenant)],
    }
    rows = [["Tenancy", "Receipt", "Date", "Amount", "Mode"]]
    with session() as s:
        for x in s.scalars(select(RdPayment).where(RdPayment.tenant_id == tenant, RdPayment.void.is_(False)).order_by(RdPayment.on)).all():
            t = s.get(RdTenancy, x.tenancy_id)
            rows.append([t.number if t else "", x.receipt_no, x.on, x.amount, x.mode])
    sheets["Payments"] = rows
    data = officegen.make_xlsx("Rent register", sheets)
    f = chatfiles.store(tenant, f"Rent_register_{today(tenant).isoformat()}.xlsx", data,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    _publish(tenant, "pc_file", {**f, "source": "rentdesk", "title": "Rent register"}, conv)
    return {"file": f, "say": "Units, tenancies aur payments ka Excel."}


# ---------------------------------------------------------------- worker
def _once(s, tenant: str, key: str) -> bool:
    k = f"{tenant}:{key}"[:200]
    if s.get(RdAlert, k) is not None:
        return False
    s.add(RdAlert(key=k, tenant_id=tenant))
    s.flush()
    return True


def _tenants() -> list[str]:
    with session() as s:
        return sorted(set(s.scalars(select(RdTenancy.tenant_id)).all()) | set(s.scalars(select(RdSettings.tenant_id)).all()))


def _reminders(tenant: str, on: date) -> int:
    n = 0
    jobs = []
    with _LOCK, session() as s:
        st = _st(s, tenant)
        for t in s.scalars(select(RdTenancy).where(RdTenancy.tenant_id == tenant, RdTenancy.status.in_(("active", "notice")))).all():
            p = s.get(RdPerson, t.person_id)
            if p is None or p.forgotten or not p.phone:
                continue
            for stage in ("before", "late"):
                hit = []
                for c in _open_charges(s, t, False):
                    d = _date(c.due_on)
                    if not d or stage in _j(c.reminded, []):
                        continue
                    if stage == "before" and 0 <= (d - on).days <= st.remind_before:
                        hit.append(c)
                    if stage == "late" and (on - d).days > st.grace_days:
                        hit.append(c)
                if not hit:
                    continue
                for c in hit:
                    c.reminded = _dump(_j(c.reminded, []) + [stage])
                if p.no_messages:
                    continue
                jobs.append((t.id, "reminder" if stage == "before" else "late", max(c.due_on for c in hit)))
    for tid, kind, due_on in jobs:
        try:
            draft_message(tenant, tid, kind, due_on=due_on, upto=due_on)
            n += 1
        except RentError:
            pass
    return n


def _date_alerts(tenant: str, on: date) -> int:
    n, pubs, esc = 0, [], []
    with _LOCK, session() as s:
        st = _st(s, tenant)
        wins = _j(st.renewal_windows, [60, 30, 15, 7])
        for t in s.scalars(select(RdTenancy).where(RdTenancy.tenant_id == tenant, RdTenancy.status.in_(("active", "notice")))).all():
            p = s.get(RdPerson, t.person_id)
            who = p.name if p else ""
            end = _date(t.end)
            if end and t.status == "active":
                left = (end - on).days
                ws = [w for w in wins if 0 <= left <= w]
                if ws and _once(s, tenant, f"ren:{t.id}:{t.end}:{min(ws)}"):
                    pubs.append({"kind": "renewal", "tenancy": t.number, "say": f"{t.number} {who}: agreement {t.end} ko khatam ({left} din). "
                                 "Renewal / notice? (action=notice kind=renewal | vacate)"})
            for d in _escalation_dates(t):
                dd = _date(d)
                if -60 <= (dd - on).days <= 30 and not any(h.get("from") == d for h in _j(t.rent_history, [])) and _once(s, tenant, f"esc:{t.id}:{d}"):
                    esc.append((t.id, d))
            start = _date(t.start)
            done = _j(t.checklist, {})
            if start and (on - start).days >= 7:
                miss = [i for i in ("registration", "police") if i not in done]
                if miss and _once(s, tenant, f"chk:{t.id}:{','.join(miss)}"):
                    pubs.append({"kind": "checklist", "tenancy": t.number, "say": f"{t.number} {who}: abhi baaki - " + ", ".join(miss)
                                 + (" (MH: s.55 registration landlord ki zimmedari; police jaankari BNS s.223)." if (st.state or '').upper() == "MH" else ".")})
        for se in s.scalars(select(RdSettlement).where(RdSettlement.tenant_id == tenant, RdSettlement.status == "paid")).all():
            t = s.get(RdTenancy, se.tenancy_id)
            p = s.get(RdPerson, t.person_id) if t else None
            if t and p and not p.forgotten and _date(t.vacate_on) and (on - _date(t.vacate_on)).days >= 90 and _once(s, tenant, f"dpdp:{p.id}"):
                pubs.append({"kind": "forget", "tenancy": t.number, "say": f"{t.number} khatam hue 90 din: {p.number} ki niji jaankari mita dein? (action=forget)"})
    for a in pubs:
        _publish(tenant, "rentdesk_alert", a)
        n += 1
    for tid, d in esc:
        try:
            rent_change(tenant, tid, from_date=d, why="agreement escalation", actor="routine")
            n += 1
        except RentError as e:
            log.info("rentdesk escalation card skipped: %s", e)
    return n


def _morning_due(tenant: str, loc: datetime) -> bool:
    with session() as s:
        r = s.get(RdSettings, tenant)
        if r is None or r.last_morning == loc.date().isoformat():
            return False
        try:
            hh, mm = (int(x) for x in (r.morning_time or "09:00").split(":"))
        except ValueError:
            hh, mm = 9, 0
        return (loc.hour, loc.minute) >= (hh, mm)


def tick(when: datetime | None = None) -> dict:
    """Worker, every minute (throttled per owner by once-keys): bill new licence months, reminder drafts (before due / after grace),
    renewal windows, escalation cards, registration / police nudges, DPDP forget nudge, morning note at her time."""
    n = _aware(when) or now()
    out = {"made": 0, "reminders": 0, "alerts": 0, "morning": 0}
    for tenant in _tenants():
        try:
            loc = n.astimezone(_tz(tenant))
            on = loc.date()
            out["made"] += bill_due(tenant, upto=on)["made"]
            out["reminders"] += _reminders(tenant, on)
            out["alerts"] += _date_alerts(tenant, on)
            if _morning_due(tenant, loc):
                d = day(tenant)
                with session() as s:
                    _st(s, tenant).last_morning = on.isoformat()
                if d["say"] != "Kiraye ka sab theek.":
                    _publish(tenant, "rentdesk_day", {"say": d["say"], "overdue": len(d["overdue"]), "drafts": d["drafts"],
                                                      "waiting": d["waiting"], "renewals": len(d["renewals"]), "repairs": d["repairs"]})
                    out["morning"] += 1
        except Exception:
            log.exception("rentdesk tick failed for %s", tenant)
    return out
