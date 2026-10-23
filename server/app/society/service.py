"""Society Sahayak: Hoola as a housing society manager / the secretary's coworker, end to end.

  1. Members & flats register: owners, joint members, tenants, nominations, share certificates, parking slots (GB resolution),
     transfers (transfer premium cap), DPDP forget of people who left.
  2. Maintenance bills by HER heads (service charges, water by taps, lift, sinking / repair fund as % of the architect-certified
     construction cost, property tax / insurance by carpet area, parking, education / election fund), non-occupancy charges on
     let-out flats (Maharashtra cap 10% of service charges), simple interest on overdue principal at the general body's rate
     (Maharashtra cap 12%), GST only when the Rs 7,500 / Rs 20 lakh test is met; receipts fill the oldest bills.
  3. Dues list with aging, defaulters, reminder drafts; complaints / requests with status; notices / circulars; AGM / SGM /
     committee meetings: agenda, notice days, quorum, attendance, minutes, resolutions; vendors / AMC with renewal reminders;
     staff and visitor register (visitor rows deleted after her retention days); accounts summary for the auditor + Excel.
  4. HER tap, in code: bills going to members, any notice / circular, any message to a member, any spend (fingerprint once a
     phone key is active), any penalty. A tool can only make the card (`society_card`); only `decide_card(by_tap=True)` from
     the API decides, against the card's hash recomputed from the records as they are now. Money never moves: the bill text
     carries a UPI link to the SOCIETY's own UPI ID and she marks a receipt when the money really came.
"""
from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import logging
import re
import secrets
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from sqlalchemy import select

from ..db import now, session
from . import rules as R
from .models import (
    SocietyAlert,
    SocietyBill,
    SocietyCard,
    SocietyComplaint,
    SocietyContract,
    SocietyFlat,
    SocietyMeeting,
    SocietyMessage,
    SocietyNotice,
    SocietyPenalty,
    SocietyReceipt,
    SocietySettings,
    SocietySpend,
    SocietyStaff,
    SocietyVisit,
)

log = logging.getLogger("santosh.society")
_LOCK = threading.RLock()
CARD_KINDS = {"bills": "Maintenance bills", "notice": "Notice / circular", "message": "Members ko message", "spend": "Kharcha",
              "penalty": "Penalty"}
COMPLAINT_STATUS = {"open": "Khuli", "assigned": "Vendor ko di", "working": "Kaam chal raha", "resolved": "Theek hui", "closed": "Band"}
NOTICE_KINDS = {"notice": "Notice", "circular": "Circular", "agm": "AGM notice", "sgm": "SGM notice", "committee": "Committee meeting",
                "defaulters": "Defaulters list", "minutes": "Minutes"}


class SocietyError(Exception):
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
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if not v:
        return None
    s = str(v).strip()
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(s[:10], f).date()
        except ValueError:
            pass
    return None


def _iso(d: date | None) -> str:
    return d.isoformat() if d else ""


def _num(v) -> float:
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d.\-]", "", str(v).replace(",", ""))
    try:
        return float(s) if s not in ("", "-", ".") else 0.0
    except ValueError:
        return 0.0


rs = R.rs


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("society publish failed")


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
        return (actor or "")[:40]


def _need_owner(actor: str) -> None:
    if not is_owner(actor):
        raise SocietyError("Yeh sirf owner / secretary kar sakti hain.")


def _clean(text, n: int = 500) -> str:
    """Words from her / staff / members: secrets and long numbers never kept."""
    t = str(text or "")
    t = re.sub(r"\b(otp|pin|cvv|password|upi pin|mpin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [hataya]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){12,19}\b", "[hataya]", t)
    t = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "[hataya]", t)
    return t.strip()[:n]


def _st(s, tenant: str) -> SocietySettings:
    r = s.get(SocietySettings, tenant)
    if r is None:
        r = SocietySettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def _next(st: SocietySettings, kind: str) -> int:
    seq = _j(st.seq, {})
    seq[kind] = int(seq.get(kind, 0)) + 1
    st.seq = _dump(seq)
    return seq[kind]


def _fy_code(tenant: str) -> str:
    return R.fy_of(today(tenant))[2]


def _hash(v) -> str:
    return hashlib.sha256(_dump(v).encode()).hexdigest()


def _mask_phone(p: str) -> str:
    return f"XXXXXX{p[-4:]}" if p and len(p) >= 4 else ""


# ---------------------------------------------------------------- settings
_SET_KEYS = ("name", "reg_no", "address", "state", "upi_id", "upi_name", "heads", "noc_pct", "interest_pct", "grace_days", "due_days",
             "bill_day", "gstin", "gst_on", "committee", "term_ends", "auditor", "visitor_days", "morning_time", "rules")


def _heads(r: SocietySettings) -> list[dict]:
    h = _j(r.heads, [])
    return h if h else [dict(x) for x in R.DEFAULT_HEADS]


def _settings_view(r: SocietySettings) -> dict:
    sr = R.state_rules(r.state)
    heads = _heads(r)
    block, warn = R.check_heads(heads, r.state, r.noc_pct, r.interest_pct)
    return {"name": r.name, "reg_no": r.reg_no, "address": r.address, "state": r.state, "law": sr["law"], "upi_id": r.upi_id,
            "upi_name": r.upi_name, "heads": heads, "bases": R.BASES, "noc_pct": r.noc_pct, "interest_pct": r.interest_pct,
            "grace_days": r.grace_days, "due_days": r.due_days, "bill_day": r.bill_day, "gstin": r.gstin, "gst_on": r.gst_on,
            "committee": _j(r.committee, []), "term_ends": r.term_ends, "auditor": r.auditor, "audit_done": _j(r.audit_done, {}),
            "agm_done": _j(r.agm_done, {}), "visitor_days": r.visitor_days, "morning_time": r.morning_time, "rules": r.rules,
            "caps": {k: sr.get(k) for k in ("noc_cap_pct", "interest_cap_pct", "sinking_min_pct", "repair_min_pct")},
            "problems": block, "warnings": warn}


def settings(tenant: str) -> dict:
    with session() as s:
        return _settings_view(_st(s, tenant))


def _clean_heads(v) -> list[dict]:
    if not isinstance(v, list):
        raise SocietyError("heads ek list chahiye: [{key, label, basis, rate}].")
    out, seen = [], set()
    for h in v[:30]:
        if not isinstance(h, dict):
            continue
        key = re.sub(r"[^a-z0-9_]", "_", str(h.get("key") or h.get("label") or "").strip().lower())[:30]
        if not key or key in seen:
            continue
        seen.add(key)
        basis = str(h.get("basis") or "per_flat")
        if basis not in R.BASES:
            raise SocietyError(f"{key}: basis '{basis}' nahi chalega ({', '.join(R.BASES)}).")
        rate = h.get("rate")
        if isinstance(rate, dict):
            rate = {str(k): _num(x) for k, x in rate.items() if _num(x) > 0} or None
        elif rate not in (None, ""):
            rate = _num(rate)
            if rate < 0:
                raise SocietyError(f"{key}: rate minus nahi.")
        else:
            rate = None
        row = {"key": key, "label": _clean(h.get("label") or key.replace("_", " ").title(), 80), "basis": basis, "rate": rate}
        for flag in ("service", "agent"):
            if h.get(flag):
                row[flag] = True
        if h.get("fund") in R.FUNDS:
            row["fund"] = h["fund"]
        out.append(row)
    return out


def save_settings(tenant: str, actor: str = "owner", **kw: Any) -> dict:
    _need_owner(actor)
    with _LOCK, session() as s:
        r = _st(s, tenant)
        for k in _SET_KEYS:
            if k not in kw or kw[k] is None:
                continue
            v = kw[k]
            if k == "state":
                r.state = str(v).upper()[:4]
            elif k == "upi_id":
                from ..bazar.connectors.upi import valid_vpa
                u = str(v).strip()
                if u and not valid_vpa(u):
                    raise SocietyError(f"UPI ID '{u}' sahi nahi lagta (naam@bank).")
                r.upi_id = u
            elif k == "heads":
                r.heads = _dump(_clean_heads(v))
            elif k in ("noc_pct", "interest_pct"):
                x = _num(v)
                if not 0 <= x <= 100:
                    raise SocietyError(f"{k} 0-100 ke beech.")
                setattr(r, k, x)
            elif k in ("grace_days", "due_days", "visitor_days"):
                setattr(r, k, max(0, min(365, int(_num(v)))))
            elif k == "bill_day":
                r.bill_day = max(1, min(28, int(_num(v))))
            elif k == "gstin":
                g = str(v).strip().upper()
                if g:
                    from ..india.money import gstin_ok
                    if not gstin_ok(g):
                        raise SocietyError("GSTIN sahi nahi (check digit).")
                r.gstin = g
            elif k == "gst_on":
                r.gst_on = bool(v)
            elif k == "committee":
                rows = v if isinstance(v, list) else []
                r.committee = _dump([{"name": _clean(x.get("name"), 80), "role": _clean(x.get("role"), 40),
                                      "phone": R.phone10(x.get("phone") or ""), "flat": R.unit_key(x.get("flat") or "")}
                                     for x in rows if isinstance(x, dict) and x.get("name")][:21])
            elif k == "term_ends":
                d = _date(v)
                if v and not d:
                    raise SocietyError("term_ends ki taarikh samajh nahi aayi.")
                r.term_ends = _iso(d)
            elif k == "morning_time":
                if not re.fullmatch(r"\d{1,2}:\d{2}", str(v)):
                    raise SocietyError("Subah ka samay HH:MM mein.")
                r.morning_time = str(v)
            else:
                setattr(r, k, _clean(v, 2000))
        if r.gst_on and not r.gstin:
            raise SocietyError("GST lagana hai to society ka GSTIN chahiye.")
        block, warn = R.check_heads(_heads(r), r.state, r.noc_pct, r.interest_pct)
        if block:
            raise SocietyError(" ".join(block))
        view = _settings_view(r)
    say = "Society ki settings save." + (" Dhyaan: " + " ".join(warn) if warn else "")
    return {"settings": view, "say": say}


def set_head(tenant: str, key: str, rate=None, label: str = "", basis: str = "", fund: str = "", remove: bool = False,
             actor: str = "owner") -> dict:
    """One head's rate in her words (e.g. service 1500 per flat, sinking 0.25 %)."""
    _need_owner(actor)
    with session() as s:
        heads = _heads(_st(s, tenant))
    k = re.sub(r"[^a-z0-9_]", "_", str(key or label).strip().lower())[:30]
    if not k:
        raise SocietyError("Kaun sa head?")
    heads = [h for h in heads if h["key"] != k] if remove else heads
    if not remove:
        cur = next((h for h in heads if h["key"] == k), None)
        if cur is None:
            cur = {"key": k, "label": label or k.replace("_", " ").title(), "basis": basis or "per_flat"}
            heads.append(cur)
        if label:
            cur["label"] = label
        if basis:
            cur["basis"] = basis
        if fund:
            cur["fund"] = fund
        cur["rate"] = rate
    return save_settings(tenant, actor=actor, heads=heads)


# ---------------------------------------------------------------- flats / members
_FLAT_KEYS = ("wing", "carpet_sqft", "cost", "taps", "lift", "owner_name", "owner_phone", "owner_email", "joint", "member_since",
              "share_cert", "shares", "occupancy", "tenant_name", "tenant_phone", "tenant_from", "tenant_to", "opening_due",
              "no_messages", "notes")


def _flat(s, tenant: str, ref: str) -> SocietyFlat:
    ref = str(ref or "").strip()
    if not ref:
        raise SocietyError("Kaun sa flat? (jaise A-101)")
    f = s.get(SocietyFlat, ref)
    if f is not None and f.tenant_id == tenant:
        return f
    key = R.unit_key(ref)
    rows = s.scalars(select(SocietyFlat).where(SocietyFlat.tenant_id == tenant, SocietyFlat.status != "forgotten")).all()
    for f in rows:
        if f.unit == key:
            return f
    tail = [f for f in rows if key and (f.unit.endswith("-" + key) or f.unit.replace("-", "") == key.replace("-", ""))]
    if len(tail) == 1:
        return tail[0]
    if len(tail) > 1:
        raise SocietyError(f"'{ref}' se kai flat milte hain: " + ", ".join(f.unit for f in tail[:6]))
    low = ref.lower()
    byname = [f for f in rows if low and len(low) >= 3 and low in (f.owner_name or "").lower()]
    if len(byname) == 1:
        return byname[0]
    raise SocietyError(f"Flat '{ref}' nahi mila.")


def _outstanding(s, f: SocietyFlat) -> tuple[int, int, date | None]:
    """(due, advance, oldest unpaid due date) from issued bills and receipts."""
    bills = s.scalars(select(SocietyBill).where(SocietyBill.flat_id == f.id, SocietyBill.status.in_(("issued", "part", "paid")))).all()
    due = sum(max(0, b.total - b.paid) for b in bills)
    adv = sum(r.advance for r in s.scalars(select(SocietyReceipt).where(SocietyReceipt.flat_id == f.id)).all())
    oldest = None
    for b in sorted(bills, key=lambda b: b.due_date or ""):
        if b.total - b.paid > 0:
            oldest = _date(b.due_date)
            break
    return due, adv, oldest


def _use_advance(s, f: SocietyFlat, b: SocietyBill) -> int:
    """A member's unused advance (extra paid earlier) fills a newly issued bill."""
    used = 0
    for r in s.scalars(select(SocietyReceipt).where(SocietyReceipt.flat_id == f.id, SocietyReceipt.advance > 0)
                       .order_by(SocietyReceipt.created_at)).all():
        take = min(r.advance, b.total - b.paid)
        if take <= 0:
            break
        r.advance -= take
        b.paid += take
        r.applied = _dump(_j(r.applied, []) + [{"bill": b.number, "amount": take / 100}])
        used += take
    if used:
        b.status = "paid" if b.paid >= b.total else "part"
    return used


def _flat_view(s, f: SocietyFlat, full: bool = False) -> dict:
    due, adv, oldest = _outstanding(s, f)
    v = {"id": f.id, "unit": f.unit, "wing": f.wing, "carpet_sqft": f.carpet_sqft or None, "cost": f.cost / 100 if f.cost else None,
         "taps": f.taps, "lift": f.lift, "owner_name": f.owner_name, "owner_phone": f.owner_phone, "owner_email": f.owner_email,
         "joint": _j(f.joint, []), "member_since": f.member_since, "share_cert": f.share_cert, "shares": f.shares,
         "nominations": [n for n in _j(f.nominations, []) if not n.get("revoked")], "occupancy": f.occupancy,
         "tenant_name": f.tenant_name, "tenant_phone": f.tenant_phone, "tenant_from": f.tenant_from, "tenant_to": f.tenant_to,
         "parking": _j(f.parking, []), "no_messages": f.no_messages, "notes": f.notes, "due": due / 100, "due_text": rs(due),
         "advance": adv / 100, "oldest_due": _iso(oldest), "status": f.status}
    gaps = []
    if not f.owner_name:
        gaps.append("owner ka naam")
    if not f.carpet_sqft:
        gaps.append("carpet area")
    if not f.cost:
        gaps.append("construction cost (sinking / repair fund ke liye)")
    if f.taps is None:
        gaps.append("nal ki ginti")
    if not _j(f.nominations, []):
        gaps.append("nomination")
    v["missing"] = gaps
    if full:
        v["history"] = _j(f.history, [])
        v["bills"] = [_bill_view(s, b) for b in s.scalars(select(SocietyBill).where(SocietyBill.flat_id == f.id)
                                                             .order_by(SocietyBill.created_at.desc())).all()[:24]]
        v["receipts"] = [_receipt_view(r) for r in s.scalars(select(SocietyReceipt).where(SocietyReceipt.flat_id == f.id)
                                                              .order_by(SocietyReceipt.created_at.desc())).all()[:24]]
    return v


def save_flat(tenant: str, unit: str = "", flat: str = "", actor: str = "owner", **kw: Any) -> dict:
    _need_owner(actor)
    with _LOCK, session() as s:
        if flat:
            f = _flat(s, tenant, flat)
            new = False
        else:
            key = R.unit_key(unit)
            if not key:
                raise SocietyError("Flat number chahiye (jaise A-101).")
            f = s.scalars(select(SocietyFlat).where(SocietyFlat.tenant_id == tenant, SocietyFlat.unit == key,
                                                     SocietyFlat.status != "forgotten")).first()
            new = f is None
            if new:
                f = SocietyFlat(tenant_id=tenant, unit=key, wing=key.split("-")[0] if "-" in key else "")
                s.add(f)
        for k in _FLAT_KEYS:
            if k not in kw or kw[k] is None:
                continue
            v = kw[k]
            if k in ("owner_phone", "tenant_phone"):
                p = R.phone10(v)
                if v and not p:
                    raise SocietyError(f"{k}: 10 ankon ka mobile number chahiye.")
                setattr(f, k, p)
            elif k == "carpet_sqft":
                x = _num(v)
                if x < 0 or x > 50000:
                    raise SocietyError("Carpet area sahi nahi lagta.")
                f.carpet_sqft = x
            elif k in ("cost", "opening_due"):
                p = R.paise(v)
                if p < 0:
                    raise SocietyError(f"{k} minus nahi.")
                setattr(f, k, p)
            elif k == "taps":
                f.taps = max(0, int(_num(v)))
            elif k in ("lift", "no_messages"):
                setattr(f, k, bool(v))
            elif k == "occupancy":
                if v not in ("self", "tenant", "vacant"):
                    raise SocietyError("occupancy: self | tenant | vacant.")
                f.occupancy = v
            elif k == "joint":
                f.joint = _dump([_clean(x, 80) for x in (v if isinstance(v, list) else [v]) if x][:5])
            elif k in ("member_since", "tenant_from", "tenant_to"):
                d = _date(v)
                if v and not d:
                    raise SocietyError(f"{k}: taarikh samajh nahi aayi.")
                setattr(f, k, _iso(d))
            else:
                setattr(f, k, _clean(v, 300))
        s.flush()
        if f.opening_due and not s.scalars(select(SocietyBill).where(SocietyBill.flat_id == f.id, SocietyBill.number == "OPENING")).first():
            on = today(tenant)
            s.add(SocietyBill(tenant_id=tenant, number="OPENING", flat_id=f.id, period="opening", bill_date=on.isoformat(),
                              due_date=on.isoformat(), lines=_dump([{"head": "opening", "label": "Pichhla baaki (opening)",
                                                                       "amount": f.opening_due}]),
                              principal=f.opening_due, total=f.opening_due, status="issued"))
        view = _flat_view(s, f)
    say = f"{view['unit']} {'joda' if new else 'badla'}."
    if view["missing"]:
        say += " Baaki: " + ", ".join(view["missing"]) + "."
    return {"flat": view, "new": new, "say": say}


def flats(tenant: str, q: str = "") -> list[dict]:
    with session() as s:
        rows = s.scalars(select(SocietyFlat).where(SocietyFlat.tenant_id == tenant, SocietyFlat.status != "forgotten")
                         .order_by(SocietyFlat.unit)).all()
        ql = (q or "").lower()
        return [_flat_view(s, f) for f in rows if not ql or ql in f.unit.lower() or ql in (f.owner_name or "").lower()]


def flat_view(tenant: str, ref: str) -> dict:
    with session() as s:
        return _flat_view(s, _flat(s, tenant, ref), full=True)


_COLS = {"unit": ("flat", "unit", "flat no", "flat number", "room", "shop"), "owner_name": ("owner", "name", "member", "naam"),
         "owner_phone": ("phone", "mobile", "contact", "whatsapp"), "carpet_sqft": ("carpet", "area", "sq ft", "sqft"),
         "taps": ("tap", "nal", "inlet"), "cost": ("construction cost", "cost"), "occupancy": ("occupancy", "rented", "tenant"),
         "owner_email": ("email", "mail"), "share_cert": ("share cert", "certificate"), "opening_due": ("arrears", "baaki", "opening", "due")}


def import_flats(tenant: str, data: bytes, name: str = "flats.csv", actor: str = "owner") -> dict:
    """Her member list sheet (CSV / Excel). Columns found by name; bad rows listed, never guessed."""
    _need_owner(actor)
    rows: list[list] = []
    if name.lower().endswith((".xlsx", ".xlsm")):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        rows = [list(r) for r in wb.active.iter_rows(values_only=True)]
    else:
        rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig", errors="replace"))))
    head_i, cols = -1, {}
    for i, r in enumerate(rows[:15]):
        cells = [str(c or "").strip().lower() for c in r]
        found = {}
        for k, words in _COLS.items():
            for j, c in enumerate(cells):
                if c and any(c == w or c.startswith(w) for w in words) and k not in found and j not in found.values():
                    found[k] = j
        if "unit" in found:
            head_i, cols = i, found
            break
    if head_i < 0:
        raise SocietyError("Sheet mein 'Flat' / 'Unit' column nahi mila.")
    added = changed = 0
    bad = []
    for n, r in enumerate(rows[head_i + 1:], start=head_i + 2):
        def g(k):
            j = cols.get(k)
            return r[j] if j is not None and j < len(r) else None
        unit = str(g("unit") or "").strip()
        if not unit:
            continue
        kw: dict[str, Any] = {}
        for k in ("owner_name", "owner_email", "share_cert"):
            if g(k):
                kw[k] = str(g(k))
        if g("owner_phone"):
            p = R.phone10(str(g("owner_phone")))
            if p:
                kw["owner_phone"] = p
            else:
                bad.append(f"Row {n}: phone '{g('owner_phone')}' sahi nahi")
        for k in ("carpet_sqft", "taps", "cost", "opening_due"):
            if g(k) not in (None, ""):
                kw[k] = g(k)
        occ = str(g("occupancy") or "").lower()
        if occ:
            kw["occupancy"] = "tenant" if any(w in occ for w in ("tenant", "rent", "kiray", "yes", "haan")) else "self"
        try:
            out = save_flat(tenant, unit, actor=actor, **kw)
            added += out["new"]
            changed += not out["new"]
        except SocietyError as e:
            bad.append(f"Row {n}: {e}")
    return {"added": added, "changed": changed, "bad": bad[:30],
            "say": f"{added} flat jode, {changed} badle." + (f" {len(bad)} row mein dikkat." if bad else "")}


def nominate(tenant: str, flat: str, name: str, relation: str = "", share_pct=None, revoke: bool = False, actor: str = "owner") -> dict:
    """Nomination register (member's own signed form; Hoola keeps the register)."""
    _need_owner(actor)
    with _LOCK, session() as s:
        f = _flat(s, tenant, flat)
        noms = _j(f.nominations, [])
        if revoke:
            hit = [n for n in noms if n["name"].lower() == str(name).lower() and not n.get("revoked")]
            if not hit:
                raise SocietyError(f"'{name}' nomination mein nahi.")
            for n in hit:
                n["revoked"] = today(tenant).isoformat()
        else:
            if not name:
                raise SocietyError("Nominee ka naam chahiye.")
            pct = _num(share_pct) if share_pct not in (None, "") else None
            live = [n for n in noms if not n.get("revoked")]
            total = sum(n.get("share_pct") or 0 for n in live) + (pct or 0)
            if pct is not None and total > 100.01:
                raise SocietyError(f"Nominees ka hissa 100% se zyada ho jayega ({total:g}%).")
            noms.append({"name": _clean(name, 80), "relation": _clean(relation, 40), "share_pct": pct, "on": today(tenant).isoformat()})
        f.nominations = _dump(noms)
        view = _flat_view(s, f)
    return {"flat": view, "say": f"{view['unit']}: nomination register update. Asli form member ka sign kiya hua file mein rakhiye."}


def transfer(tenant: str, flat: str, new_owner: str, phone: str = "", premium=None, on: str = "", share_cert: str = "",
             actor: str = "owner") -> dict:
    """Ownership change (sale / gift / succession): old member to history (contact dropped), premium checked against the cap."""
    _need_owner(actor)
    if not new_owner:
        raise SocietyError("Naye member ka naam chahiye.")
    with _LOCK, session() as s:
        st = _st(s, tenant)
        sr = R.state_rules(st.state)
        prem = R.paise(premium)
        cap = sr.get("transfer_premium_cap")
        if cap and prem > cap:
            raise SocietyError(f"Transfer premium {rs(prem)}: {sr['law']} mein {rs(cap)} se zyada nahi.")
        f = _flat(s, tenant, flat)
        due, _, _ = _outstanding(s, f)
        hist = _j(f.history, [])
        hist.append({"owner": f.owner_name, "till": _iso(_date(on) or today(tenant)), "premium": prem / 100 if prem else None})
        f.history = _dump(hist)
        f.owner_name, f.owner_phone, f.owner_email = _clean(new_owner, 160), R.phone10(phone), ""
        f.joint, f.nominations = "[]", "[]"
        f.member_since = _iso(_date(on) or today(tenant))
        if share_cert:
            f.share_cert = _clean(share_cert, 40)
        view = _flat_view(s, f)
    say = (f"{view['unit']} ab {view['owner_name']} ke naam. Purane member ka phone hata diya (DPDP). Share certificate par naya naam "
           "endorse kijiye, nayi nomination lijiye.")
    if due:
        say += f" Dhyaan: is flat par {rs(due)} baaki hai."
    return {"flat": view, "say": say}


def parking(tenant: str, flat: str, slot: str, kind: str = "car", resolution: str = "", remove: bool = False, actor: str = "owner") -> dict:
    _need_owner(actor)
    slot = re.sub(r"\s+", "", str(slot or "")).upper()[:20]
    if not slot:
        raise SocietyError("Slot number chahiye.")
    with _LOCK, session() as s:
        st = _st(s, tenant)
        f = _flat(s, tenant, flat)
        mine = _j(f.parking, [])
        if remove:
            mine = [p for p in mine if p["slot"] != slot]
        else:
            if st.state == "MH" and not resolution:
                raise SocietyError("Parking allotment general body tay karti hai (Rules 2026): resolution ka hawala dijiye.")
            for o in s.scalars(select(SocietyFlat).where(SocietyFlat.tenant_id == tenant, SocietyFlat.id != f.id)).all():
                if any(p["slot"] == slot for p in _j(o.parking, [])):
                    raise SocietyError(f"Slot {slot} pehle se {o.unit} ko diya hai.")
            mine = [p for p in mine if p["slot"] != slot] + [{"slot": slot, "kind": kind if kind in ("car", "two_wheeler") else "car",
                                                                "resolution": _clean(resolution, 120)}]
        f.parking = _dump(mine)
        view = _flat_view(s, f)
    return {"flat": view, "say": f"{view['unit']}: parking {'hataya' if remove else slot + ' diya'}."}


def parking_register(tenant: str) -> list[dict]:
    out = []
    for f in flats(tenant):
        for p in f["parking"]:
            out.append({"slot": p["slot"], "kind": p.get("kind"), "unit": f["unit"], "owner": f["owner_name"], "resolution": p.get("resolution")})
    return sorted(out, key=lambda x: x["slot"])


# ---------------------------------------------------------------- bills
def _bill_view(s, b: SocietyBill) -> dict:
    f = s.get(SocietyFlat, b.flat_id)
    return {"id": b.id, "number": b.number, "unit": f.unit if f else "", "owner": f.owner_name if f else "", "period": b.period,
            "bill_date": b.bill_date, "due_date": b.due_date, "lines": [{**l, "amount": l["amount"] / 100} for l in _j(b.lines, [])],
            "principal": b.principal / 100, "interest": b.interest / 100, "gst": b.gst / 100, "total": b.total / 100,
            "total_text": rs(b.total), "paid": b.paid / 100, "status": b.status, "notes": b.notes}


def pay_link(tenant: str, amount_paise: int, note: str) -> str:
    with session() as s:
        st = _st(s, tenant)
        vpa, name = st.upi_id, st.upi_name or st.name
    if not vpa:
        try:
            from ..employee.service import profile
            p = profile(tenant) or {}
            vpa, name = p.get("upi_id") or "", name or p.get("upi_name") or ""
        except Exception:
            vpa = ""
    if not vpa or amount_paise <= 0:
        return ""
    return (f"upi://pay?pa={quote(vpa)}&pn={quote(name or 'Society')}&am={amount_paise / 100:.2f}&cu=INR&tn={quote(note[:60])}")


def _flat_calc(f: SocietyFlat) -> dict:
    return {"carpet_sqft": f.carpet_sqft, "taps": f.taps, "lift": f.lift, "parking": _j(f.parking, []), "cost": f.cost,
            "occupancy": f.occupancy}


def _batch_snapshot(s, batch: str) -> list:
    rows = s.scalars(select(SocietyBill).where(SocietyBill.batch_id == batch, SocietyBill.status == "draft")).all()
    out = []
    for b in rows:
        f = s.get(SocietyFlat, b.flat_id)
        out.append([f.unit if f else "", b.total, _j(b.lines, []), b.due_date])
    return sorted(out, key=lambda x: x[0])


def make_bills(tenant: str, period: str = "", only: list | None = None, actor: str = "owner", conv: str = "") -> dict:
    """Draft this month's bills for every flat (or `only`) and send ONE card for her tap. Nothing reaches members before it."""
    on = today(tenant)
    if period and not re.fullmatch(r"\d{4}-\d{2}", period):
        raise SocietyError("period YYYY-MM mein (jaise 2026-10).")
    period = period or on.strftime("%Y-%m")
    with _LOCK, session() as s:
        st = _st(s, tenant)
        heads = _heads(st)
        block, warn = R.check_heads(heads, st.state, st.noc_pct, st.interest_pct)
        if block:
            raise SocietyError(" ".join(block))
        q = select(SocietyFlat).where(SocietyFlat.tenant_id == tenant, SocietyFlat.status == "active")
        fl = s.scalars(q.order_by(SocietyFlat.unit)).all()
        if only:
            keys = {R.unit_key(x) for x in only}
            fl = [f for f in fl if f.unit in keys or f.id in only]
        if not fl:
            raise SocietyError("Koi flat register mein nahi.")
        # old drafts of this period are replaced, their card goes stale
        for b in s.scalars(select(SocietyBill).where(SocietyBill.tenant_id == tenant, SocietyBill.period == period,
                                                     SocietyBill.status == "draft")).all():
            s.delete(b)
        for c in s.scalars(select(SocietyCard).where(SocietyCard.tenant_id == tenant, SocietyCard.kind == "bills",
                                                     SocietyCard.status == "waiting")).all():
            if _j(c.data, {}).get("period") == period:
                c.status = "stale"
        s.flush()
        totals = {"carpet_total": sum(f.carpet_sqft or 0 for f in fl), "lift_flats": sum(1 for f in fl if f.lift),
                  "member_count": len(fl)}
        month_base = 0
        drafts, problems, skipped = [], [], []
        for f in fl:
            if s.scalars(select(SocietyBill).where(SocietyBill.flat_id == f.id, SocietyBill.period == period,
                                                   SocietyBill.status.in_(("issued", "part", "paid")))).first():
                skipped.append(f.unit)
                continue
            lines, probs = R.bill_lines(_flat_calc(f), heads, totals, st.noc_pct)
            for p in probs:
                problems.append(f"{f.unit}: {p}")
            for pen in s.scalars(select(SocietyPenalty).where(SocietyPenalty.flat_id == f.id, SocietyPenalty.status == "approved")).all():
                lines.append({"head": "penalty", "label": f"Penalty {pen.number}: {pen.what[:60]}", "amount": pen.amount, "penalty": pen.id})
            drafts.append((f, lines))
            month_base += sum(l["amount"] for l in lines if not l.get("agent"))
        if not any(l for _, l in drafts) and not skipped:
            raise SocietyError("Kisi bill mein ek bhi line nahi: heads ke rate set kijiye (set_head).")
        batch = secrets.token_hex(8)
        due = on + timedelta(days=st.due_days or 15)
        made, gst_notes = [], set()
        for f, lines in drafts:
            if not lines:
                problems.append(f"{f.unit}: koi line nahi bani.")
                continue
            prev = s.scalars(select(SocietyBill).where(SocietyBill.flat_id == f.id, SocietyBill.status.in_(("issued", "part")))).all()
            overdue = []
            for b in prev:
                unpaid_principal = max(0, b.principal - max(0, b.paid - b.interest - b.gst))
                overdue.append({"number": b.number, "due_date": _date(b.due_date), "unpaid": unpaid_principal})
            interest, irows = R.interest_on(overdue, st.interest_pct, on, st.grace_days)
            if interest:
                lines.append({"head": "interest", "label": f"Vyaaj {st.interest_pct:g}% saalana simple (baaki par)", "amount": interest,
                              "detail": irows})
            gst, note = R.gst_lines(lines, month_base * 12, st.gst_on)
            if note:
                gst_notes.add(note)
            principal = sum(l["amount"] for l in lines if l["head"] != "interest")
            n = _next(st, "bill")
            b = SocietyBill(tenant_id=tenant, number=f"MB/{_fy_code(tenant)}/{n:04d}", flat_id=f.id, period=period,
                            bill_date=on.isoformat(), due_date=due.isoformat(), lines=_dump(lines), principal=principal,
                            interest=interest, gst=gst, total=principal + interest + gst, batch_id=batch, status="draft")
            s.add(b)
            made.append(b)
        s.flush()
        if not made:
            raise SocietyError("Is mahine ke bill pehle hi gaye: " + ", ".join(skipped[:10]))
        snap = _batch_snapshot(s, batch)
        total = sum(b.total for b in made)
        data = {"period": period, "count": len(made), "total": total / 100, "total_text": rs(total), "due_date": due.isoformat(),
                "problems": problems[:30], "warnings": warn + sorted(gst_notes), "skipped": skipped,
                "sample": [_bill_view(s, b) for b in made[:3]], "upi": bool(st.upi_id)}
        card = _new_card(s, tenant, "bills", batch, f"{period} ke {len(made)} maintenance bill ({rs(total)})", data, _hash(snap),
                         actor, conv)
        view = _card_view(s, card)
    say = (f"{period} ke {len(made)} bill taiyaar ({rs(total)}), due {due:%d-%m-%Y}. Members tak tabhi jayenge jab aap card par "
           "Haan karengi.")
    if problems:
        say += f" {len(problems)} baat dekhni hai (card par)."
    if not data["upi"]:
        say += " Society ka UPI ID nahi diya: bill mein pay link nahi hoga."
    _publish(tenant, "society_card", {"card": view, "say": say}, conv)
    return {"card": view, "status": "needs_tap", "say": say}


def bills(tenant: str, period: str = "", status: str = "", flat: str = "") -> list[dict]:
    with session() as s:
        q = select(SocietyBill).where(SocietyBill.tenant_id == tenant)
        if period:
            q = q.where(SocietyBill.period == period)
        if status:
            q = q.where(SocietyBill.status == status)
        if flat:
            q = q.where(SocietyBill.flat_id == _flat(s, tenant, flat).id)
        return [_bill_view(s, b) for b in s.scalars(q.order_by(SocietyBill.created_at.desc())).all()[:300]]


def _bill_text(s, tenant: str, b: SocietyBill, st: SocietySettings) -> str:
    f = s.get(SocietyFlat, b.flat_id)
    due, _, _ = _outstanding(s, f)
    lines = "\n".join(f"- {l['label']}: {rs(l['amount'])}" for l in _j(b.lines, []))
    if b.gst:
        lines += f"\n- GST: {rs(b.gst)}"
    link = pay_link(tenant, due, f"{b.number} {f.unit}")
    txt = (f"Namaskar {f.owner_name or ''},\n{st.name or 'Society'}: {f.unit} ka maintenance bill {b.number} ({b.period}).\n{lines}\n"
           f"Is bill ka total: {rs(b.total)}. Kul baaki (pichhla mila kar): {rs(due)}. Aakhri taarikh: {_date(b.due_date):%d-%m-%Y}.")
    if link:
        txt += f"\nUPI se bharein: {link}"
    txt += "\nPaise bharne ke baad society ko bata dijiye. Hum kabhi OTP / PIN nahi maangte."
    return txt


def _wa(phone: str, text: str) -> str:
    return f"https://wa.me/91{phone}?text={quote(text)}" if phone else ""


def _bills_pdf(s, tenant: str, rows: list[SocietyBill], st: SocietySettings) -> dict | None:
    try:
        from reportlab.lib.pagesizes import A5
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A5)
        W, H = A5
        for b in rows:
            f = s.get(SocietyFlat, b.flat_id)
            y = H - 15 * mm
            c.setFont("Helvetica-Bold", 12)
            c.drawString(12 * mm, y, (st.name or "Housing Society")[:60])
            c.setFont("Helvetica", 8)
            y -= 5 * mm
            c.drawString(12 * mm, y, f"Reg: {st.reg_no}   {st.address[:70]}")
            y -= 8 * mm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(12 * mm, y, f"Maintenance bill {b.number}   Flat {f.unit if f else ''}   Period {b.period}")
            y -= 5 * mm
            c.setFont("Helvetica", 9)
            c.drawString(12 * mm, y, f"Member: {f.owner_name if f else ''}   Bill date {b.bill_date}   Due {b.due_date}")
            y -= 8 * mm
            for l in _j(b.lines, []):
                c.drawString(12 * mm, y, str(l["label"])[:60])
                c.drawRightString(W - 12 * mm, y, f"{l['amount'] / 100:,.2f}")
                y -= 5 * mm
            if b.gst:
                c.drawString(12 * mm, y, "GST")
                c.drawRightString(W - 12 * mm, y, f"{b.gst / 100:,.2f}")
                y -= 5 * mm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(12 * mm, y - 2 * mm, "Total")
            c.drawRightString(W - 12 * mm, y - 2 * mm, f"{b.total / 100:,.2f}")
            c.setFont("Helvetica", 7)
            c.drawString(12 * mm, 12 * mm, "Computer generated by Hoola for the society. Pay only to the society's own account / UPI ID.")
            c.showPage()
        c.save()
        return {"name": f"Maintenance_bills_{rows[0].period}.pdf", "data": buf.getvalue()}
    except Exception:
        log.exception("society bills pdf failed")
        return None


# ---------------------------------------------------------------- cards (HER tap only)
def _new_card(s, tenant: str, kind: str, target: str, title: str, data: dict, h: str, actor: str, conv: str) -> SocietyCard:
    c = SocietyCard(tenant_id=tenant, kind=kind, target=target, title=title[:200], hash=h, data=_dump(data),
                    asked_by=actor_name(tenant, actor), conv=conv)
    s.add(c)
    s.flush()
    return c


def _card_view(s, c: SocietyCard) -> dict:
    return {"id": c.id, "kind": c.kind, "kind_label": CARD_KINDS.get(c.kind, c.kind), "target": c.target, "title": c.title,
            "hash": c.hash, "data": _j(c.data, {}), "status": c.status, "reason": c.reason, "asked_by": c.asked_by,
            "money": c.kind == "spend",
            "created_at": _aware(c.created_at).isoformat(timespec="minutes") if c.created_at else ""}


def _snapshot(s, c: SocietyCard):
    if c.kind == "bills":
        return _batch_snapshot(s, c.target)
    if c.kind == "notice":
        n = s.get(SocietyNotice, c.target)
        if n is None:
            return None
        m = s.get(SocietyMeeting, n.meeting_id) if n.meeting_id else None
        return [n.kind, n.title, n.body, n.audience, _j(n.flats, []), m.day if m else "", m.time if m else ""]
    if c.kind == "message":
        m = s.get(SocietyMessage, c.target)
        return [m.kind, _j(m.flat_ids, []), m.text, _j(m.result, {}).get("via", "self")] if m else None
    if c.kind == "spend":
        x = s.get(SocietySpend, c.target)
        return [x.kind, x.what, x.amount, x.vendor, x.fund, x.resolution] if x else None
    if c.kind == "penalty":
        p = s.get(SocietyPenalty, c.target)
        return [p.flat_id, p.what, p.amount, p.rule] if p else None
    return None


def cards(tenant: str, status: str = "waiting") -> list[dict]:
    with session() as s:
        q = select(SocietyCard).where(SocietyCard.tenant_id == tenant)
        if status:
            q = q.where(SocietyCard.status == status)
        return [_card_view(s, c) for c in s.scalars(q.order_by(SocietyCard.created_at.desc())).all()[:100]]


def card(tenant: str, card_id: str) -> dict | None:
    with session() as s:
        c = s.get(SocietyCard, card_id)
        return _card_view(s, c) if c and c.tenant_id == tenant else None


def needs_fingerprint(tenant: str, card_id: str) -> bool:
    from .. import approvekey as ak
    c = card(tenant, card_id)
    return bool(c and c["kind"] == "spend" and ak.active_on(tenant))


def challenge(tenant: str, card_id: str) -> dict:
    """approvekey's message format (kind 'society'): the phone signs this card as it is NOW."""
    from .. import approvekey as ak
    c = card(tenant, card_id)
    if not c or c["status"] != "waiting":
        raise SocietyError("Yeh card ab baaki nahi hai.")
    nonce = secrets.token_urlsafe(18)
    exp = datetime.now(timezone.utc) + ak.CHALLENGE_TTL
    msg = f"hoola-approve|v1|{tenant}|society|{card_id}|{c['hash']}|{nonce}|{int(exp.timestamp())}"
    with session() as s:
        ch = ak.ApproveChallenge(tenant_id=tenant, kind="society", target=card_id, digest=c["hash"], message=msg, expires_at=exp)
        s.add(ch)
        s.flush()
        chid = ch.id
    d = c["data"]
    show = {"title": c["title"][:80], "amount": d.get("amount_text") or d.get("total_text") or "", "payee": d.get("vendor") or ""}
    return {"challenge_id": chid, "message": msg, "show": show, "expires_at": exp.isoformat()}


def _verify_fingerprint(tenant: str, card_id: str, digest: str, proof: dict | None) -> None:
    from .. import approvekey as ak
    if not proof:
        raise SocietyError("fingerprint_needed")
    with session() as s:
        ak._settle(s, tenant)
        ok = ak._check(s, tenant, "society", card_id, proof, digest)
    if not ok:
        raise SocietyError("fingerprint_invalid")


def decide_card(tenant: str, card_id: str, yes: bool, card_hash: str = "", reason: str = "", proof: dict | None = None,
                via: str = "", by_tap: bool = False) -> dict:
    """ONLY her tap in the app (API). The tool can never reach this with by_tap."""
    if not by_tap:
        raise SocietyError("Yeh faisla sirf aapke tap se (app ka card).")
    with _LOCK, session() as s:
        c = s.get(SocietyCard, card_id)
        if c is None or c.tenant_id != tenant:
            raise SocietyError("Card nahi mila.")
        if c.status != "waiting":
            return {"card": _card_view(s, c), "say": f"Yeh card pehle hi '{c.status}' hai."}
        snap = _snapshot(s, c)
        if snap is None or _hash(snap) != c.hash:
            c.status = "stale"
            raise SocietyError("Card ke baad cheezein badal gayi: naya card banwaiye.")
        if not card_hash or card_hash != c.hash:
            raise SocietyError("Card badal gaya hai; naya card dekhiye.")
        kind = c.kind
    if yes and kind == "spend":
        from .. import approvekey as ak
        if ak.active_on(tenant):
            _verify_fingerprint(tenant, card_id, card_hash, proof)
    with _LOCK, session() as s:
        c = s.get(SocietyCard, card_id)
        c.status = "approved" if yes else "rejected"
        c.reason = _clean(reason, 300)
        c.decided_at = now()
        out = {"card": None}
        if kind == "bills":
            out.update(_apply_bills(s, tenant, c, yes, via))
        elif kind == "notice":
            out.update(_apply_notice(s, tenant, c, yes))
        elif kind == "message":
            out.update(_apply_message(s, tenant, c, yes, via))
        elif kind == "spend":
            x = s.get(SocietySpend, c.target)
            x.status = "approved" if yes else "rejected"
            out["say"] = (f"{x.number} maana: {rs(x.amount)}. Paise society ke account se aap / treasurer dijiye, phir 'Maine de diya'."
                          if yes else f"{x.number}: kharcha nahi.")
        elif kind == "penalty":
            p = s.get(SocietyPenalty, c.target)
            p.status = "approved" if yes else "rejected"
            out["say"] = (f"{p.number} maana: agle bill mein {rs(p.amount)} judega." if yes else f"{p.number}: penalty nahi.")
        out["card"] = _card_view(s, c)
    after = out.pop("_after", None)
    if after:
        try:
            out.update(after())
        except Exception:
            log.exception("society after-tap file failed")
    return out


def _apply_bills(s, tenant: str, c: SocietyCard, yes: bool, via: str) -> dict:
    rows = s.scalars(select(SocietyBill).where(SocietyBill.batch_id == c.target, SocietyBill.status == "draft")).all()
    if not yes:
        for b in rows:
            b.status = "cancelled"
        return {"say": "Bill nahi bheje; drafts radd."}
    st = _st(s, tenant)
    drafts, sent = [], 0
    for b in rows:
        b.status = "issued"
        _use_advance(s, s.get(SocietyFlat, b.flat_id), b)
        for l in _j(b.lines, []):
            if l.get("penalty"):
                p = s.get(SocietyPenalty, l["penalty"])
                if p:
                    p.status, p.bill_id = "billed", b.id
    s.flush()
    for b in rows:
        f = s.get(SocietyFlat, b.flat_id)
        txt = _bill_text(s, tenant, b, st)
        item = {"unit": f.unit, "owner": f.owner_name, "text": txt, "wa": "" if f.no_messages else _wa(f.owner_phone, txt),
                "sent": False}
        if via == "business" and f.owner_phone and not f.no_messages:
            try:
                from ..employee import inbox
                item["sent"] = bool(inbox.notice_by_phone(tenant, "91" + f.owner_phone, txt))
                sent += item["sent"]
            except Exception:
                log.exception("society business send failed")
        drafts.append(item)
    ids, conv = [b.id for b in rows], c.conv

    def after():
        with session() as s2:
            rws = [s2.get(SocietyBill, i) for i in ids]
            raw = _bills_pdf(s2, tenant, [b for b in rws if b], _st(s2, tenant))
        pdf = None
        if raw:
            from .. import chatfiles
            pdf = chatfiles.store(tenant, raw["name"], raw["data"], "application/pdf")
        if pdf:
            _publish(tenant, "pc_file", {**pdf, "source": "society", "title": "Maintenance bills"}, conv)
        return {"file": pdf}
    say = f"{len(rows)} bill jaari. "
    if via == "business":
        say += f"{sent} business WhatsApp par gaye (sirf 24 ghante ki window wale); baaki ke WhatsApp draft aap bhejiye."
    else:
        say += "Har member ka WhatsApp draft taiyaar: aap bhejiye (ya society group mein PDF)."
    return {"bills": drafts, "_after": after, "say": say}


# ---------------------------------------------------------------- receipts / dues
def _receipt_view(r: SocietyReceipt) -> dict:
    return {"id": r.id, "number": r.number, "day": r.day, "amount": r.amount / 100, "amount_text": rs(r.amount), "mode": r.mode,
            "ref_tail": r.ref_tail, "applied": _j(r.applied, []), "advance": r.advance / 100, "by": r.by}


def _galla_hint(s, tenant: str, amount: int, day: str) -> str:
    try:
        from ..galla.service import GallaEntry
        hit = s.scalars(select(GallaEntry).where(GallaEntry.tenant_id == tenant, GallaEntry.day == day,
                                                 GallaEntry.amount_paise == amount, GallaEntry.void.is_(False))).first()
        if hit:
            return f"Galla mein {day} ko {rs(amount)} ka UPI credit dikha ({hit.app or 'UPI'}): yahi lagta hai (pakka saboot nahi)."
    except Exception:
        pass
    return ""


def receive(tenant: str, flat: str, amount, mode: str = "upi", ref: str = "", day: str = "", actor: str = "owner") -> dict:
    """She says the money came (UPI / cash / cheque / NEFT). Fills the oldest bills first; extra = advance."""
    _need_owner(actor)
    a = R.paise(amount)
    if a <= 0:
        raise SocietyError("Kitne paise mile? (rakam chahiye)")
    mode = mode if mode in ("upi", "cash", "cheque", "neft") else "upi"
    on = _date(day) or today(tenant)
    if on > today(tenant):
        raise SocietyError("Aage ki taarikh ki receipt nahi.")
    warn = []
    if mode == "cash" and a >= 20_000_000:
        warn.append("Ek din mein ek member se Rs 2 lakh ya zyada cash lena mana hai (Income-tax Act; purana 269ST): bank se lijiye.")
    with _LOCK, session() as s:
        st = _st(s, tenant)
        f = _flat(s, tenant, flat)
        left, applied = a, []
        for b in sorted(s.scalars(select(SocietyBill).where(SocietyBill.flat_id == f.id, SocietyBill.status.in_(("issued", "part")))).all(),
                        key=lambda b: (b.due_date or "", b.number)):
            if left <= 0:
                break
            take = min(left, b.total - b.paid)
            if take <= 0:
                continue
            b.paid += take
            b.status = "paid" if b.paid >= b.total else "part"
            applied.append({"bill": b.number, "amount": take / 100})
            left -= take
        n = _next(st, "receipt")
        r = SocietyReceipt(tenant_id=tenant, number=f"R/{_fy_code(tenant)}/{n:04d}", flat_id=f.id, day=on.isoformat(), amount=a,
                           mode=mode, ref_tail=re.sub(r"\D", "", ref)[-4:], applied=_dump(applied), advance=max(0, left),
                           by=actor_name(tenant, actor))
        s.add(r)
        s.flush()
        hint = _galla_hint(s, tenant, a, on.isoformat()) if mode == "upi" else ""
        view = _receipt_view(r)
        fv = _flat_view(s, f)
        text = (f"{st.name or 'Society'}: {f.unit} se {rs(a)} mile ({mode.upper()}), receipt {r.number}, {on:%d-%m-%Y}. "
                f"Baaki: {fv['due_text'] or rs(0)}. Dhanyavaad.")
    say = f"Receipt {view['number']}: {f.unit} se {rs(a)}." + (f" {rs(left)} advance." if left > 0 else "") + (" " + hint if hint else "")
    if warn:
        say += " Dhyaan: " + " ".join(warn)
    return {"receipt": view, "flat": fv, "receipt_text": text, "warnings": warn, "galla_hint": hint, "say": say + " Member ko receipt bhejni ho to 'message' card."}


def dues(tenant: str) -> dict:
    on = today(tenant)
    rows, buckets, total = [], {"0-30": 0, "31-90": 0, "91-180": 0, "180+": 0}, 0
    with session() as s:
        st = _st(s, tenant)
        for f in s.scalars(select(SocietyFlat).where(SocietyFlat.tenant_id == tenant, SocietyFlat.status == "active")).all():
            due, adv, oldest = _outstanding(s, f)
            if due <= 0:
                continue
            days = (on - oldest).days if oldest else 0
            b = R.aging(max(0, days))
            buckets[b] += due
            total += due
            rows.append({"unit": f.unit, "owner": f.owner_name, "due": due / 100, "due_text": rs(due), "oldest_due": _iso(oldest),
                         "days": max(0, days), "bucket": b, "defaulter": days > 90, "phone": bool(f.owner_phone),
                         "no_messages": f.no_messages})
        state = st.state
    rows.sort(key=lambda x: -x["due"])
    return {"flats": rows, "total": total / 100, "total_text": rs(total), "buckets": {k: v / 100 for k, v in buckets.items()},
            "defaulters": [r for r in rows if r["defaulter"]],
            "recovery": ("Bahut purana baaki: Section 154B-29 ke tahat Registrar ke paas recovery (Form Y-6, Rs 100 court fee) "
                         "general body / committee ke resolution ke baad." if state == "MH" else "Recovery aapke bye-laws aur state act se."),
            "say": f"Kul baaki {rs(total)}, {len(rows)} flat." if rows else "Kisi flat par baaki nahi."}


def remind(tenant: str, flats_: list | None = None, text: str = "", via: str = "self", min_days: int = 0, actor: str = "owner",
           conv: str = "") -> dict:
    """Dues reminder drafts for her tap (message card). Members who said no / without a phone are skipped and named."""
    d = dues(tenant)
    pick = d["flats"]
    if flats_:
        keys = {R.unit_key(x) for x in flats_}
        pick = [r for r in pick if r["unit"] in keys]
    pick = [r for r in pick if r["days"] >= min_days]
    if not pick:
        raise SocietyError("Yaad dilane laayak baaki kisi flat par nahi.")
    body = _clean(text, 800) or ("Namaskar {name}, {society}: flat {unit} par {amount} maintenance baaki hai. Kripya jaldi bharein: "
                                 "{link}. Bhar diya ho to is message ko ignore karein. Hum kabhi OTP / PIN nahi maangte.")
    return _message_card(tenant, "dues", [r["unit"] for r in pick], body, via, actor, conv)


def _render(s, tenant: str, f: SocietyFlat, text: str, st: SocietySettings) -> str:
    due, _, _ = _outstanding(s, f)
    link = pay_link(tenant, due, f"Dues {f.unit}") or "(society ka UPI ID nahi diya)"
    return (text.replace("{name}", f.owner_name or "").replace("{unit}", f.unit).replace("{amount}", rs(due))
            .replace("{link}", link).replace("{society}", st.name or "Society"))


def _message_card(tenant: str, kind: str, units: list[str], text: str, via: str, actor: str, conv: str) -> dict:
    if re.search(r"\[[^\]]{0,40}\]", text):
        raise SocietyError("Message mein [khaali] jagah baaki hai: pehle bhariye.")
    with _LOCK, session() as s:
        st = _st(s, tenant)
        fl, skipped = [], []
        for u in units:
            try:
                f = _flat(s, tenant, u)
            except SocietyError:
                skipped.append(f"{u}: nahi mila")
                continue
            if f.no_messages:
                skipped.append(f"{f.unit}: message nahi chahte")
            elif not f.owner_phone:
                skipped.append(f"{f.unit}: phone nahi")
            else:
                fl.append(f)
        if not fl:
            raise SocietyError("Kisi ko bhej nahi sakte: " + "; ".join(skipped[:8]))
        m = SocietyMessage(tenant_id=tenant, kind=kind, flat_ids=_dump(sorted(f.id for f in fl)), text=text,
                           result=_dump({"via": via if via in ("self", "business") else "self"}))
        s.add(m)
        s.flush()
        preview = [{"unit": f.unit, "owner": f.owner_name, "text": _render(s, tenant, f, text, st)} for f in fl[:3]]
        data = {"kind": kind, "count": len(fl), "preview": preview, "skipped": skipped, "via": _j(m.result, {}).get("via")}
        c = _new_card(s, tenant, "message", m.id, f"{len(fl)} members ko message ({kind})", data, _hash(_snapshot_msg(m)), actor, conv)
        view = _card_view(s, c)
    say = f"{len(fl)} members ke liye message taiyaar: aapki haan ke baad hi jayega." + (f" {len(skipped)} chhoot gaye." if skipped else "")
    _publish(tenant, "society_card", {"card": view, "say": say}, conv)
    return {"card": view, "status": "needs_tap", "say": say}


def _snapshot_msg(m: SocietyMessage) -> list:
    return [m.kind, _j(m.flat_ids, []), m.text, _j(m.result, {}).get("via", "self")]


def message(tenant: str, units: list | str, text: str, via: str = "self", actor: str = "owner", conv: str = "") -> dict:
    """Any message to members (custom / complaint update / receipt): only a card here."""
    if isinstance(units, str):
        units = [u for u in re.split(r"[,\s]+", units) if u]
    if not text:
        raise SocietyError("Message ka text chahiye.")
    if units == ["all"]:
        units = [f["unit"] for f in flats(tenant)]
    return _message_card(tenant, "custom", units, _clean(text, 1500), via, actor, conv)


def _apply_message(s, tenant: str, c: SocietyCard, yes: bool, via: str) -> dict:
    m = s.get(SocietyMessage, c.target)
    if not yes:
        m.status = "rejected"
        return {"say": "Message nahi bheja."}
    st = _st(s, tenant)
    chan = via or _j(m.result, {}).get("via", "self")
    items, sent = [], 0
    for fid in _j(m.flat_ids, []):
        f = s.get(SocietyFlat, fid)
        if f is None:
            continue
        txt = _render(s, tenant, f, m.text, st)
        it = {"unit": f.unit, "owner": f.owner_name, "text": txt, "wa": _wa(f.owner_phone, txt), "sent": False}
        if chan == "business":
            try:
                from ..employee import inbox
                it["sent"] = bool(inbox.notice_by_phone(tenant, "91" + f.owner_phone, txt))
                sent += it["sent"]
            except Exception:
                log.exception("society business send failed")
        items.append(it)
    m.status = "sent" if chan == "business" and sent == len(items) else "approved"
    m.result = _dump({"via": chan, "sent": sent, "count": len(items)})
    say = (f"{sent} business WhatsApp par gaye; baaki {len(items) - sent} ke draft aap bhejiye." if chan == "business"
           else f"{len(items)} WhatsApp draft taiyaar: har ek par tap karke aap bhejiye.")
    return {"messages": items, "say": say}


# ---------------------------------------------------------------- penalties
def penalty_request(tenant: str, flat: str, what: str, amount, rule: str, actor: str = "owner", conv: str = "") -> dict:
    a = R.paise(amount)
    if a <= 0:
        raise SocietyError("Penalty ki rakam (bye-law / resolution ke hisaab se) chahiye.")
    if not rule:
        raise SocietyError("Kis bye-law / general body resolution se penalty? Bina hawale ke penalty nahi (Rules 2026: koi charge Act / Rules ke bina nahi).")
    if not what:
        raise SocietyError("Kis baat ki penalty?")
    with _LOCK, session() as s:
        st = _st(s, tenant)
        f = _flat(s, tenant, flat)
        if re.search(r"\b(late|deri|interest|vyaaj)\b", what, re.I):
            raise SocietyError("Deri par alag penalty nahi: baaki par vyaaj hi lagta hai (general body ka rate).")
        n = _next(st, "penalty")
        p = SocietyPenalty(tenant_id=tenant, number=f"P-{n:04d}", flat_id=f.id, what=_clean(what, 300), amount=a, rule=_clean(rule, 200))
        s.add(p)
        s.flush()
        data = {"unit": f.unit, "owner": f.owner_name, "what": p.what, "amount": a / 100, "amount_text": rs(a), "rule": p.rule,
                "number": p.number}
        c = _new_card(s, tenant, "penalty", p.id, f"{f.unit}: penalty {rs(a)}", data, _hash([p.flat_id, p.what, p.amount, p.rule]), actor, conv)
        view = _card_view(s, c)
    say = f"{p.number}: {f.unit} par {rs(a)} penalty ka card aapki haan ke liye."
    _publish(tenant, "society_card", {"card": view, "say": say}, conv)
    return {"card": view, "status": "needs_tap", "say": say}


# ---------------------------------------------------------------- complaints
def _complaint_view(s, c: SocietyComplaint) -> dict:
    f = s.get(SocietyFlat, c.flat_id) if c.flat_id else None
    k = s.get(SocietyContract, c.contract_id) if c.contract_id else None
    age = (now() - _aware(c.created_at)).days if c.created_at else 0
    return {"id": c.id, "number": c.number, "unit": f.unit if f else "", "kind": c.kind, "category": c.category, "text": c.text,
            "urgent": c.urgent, "status": c.status, "status_label": COMPLAINT_STATUS.get(c.status, c.status),
            "vendor": k.vendor if k else "", "log": _j(c.log, []), "by": c.by, "age_days": age,
            "created_at": _aware(c.created_at).isoformat(timespec="minutes") if c.created_at else ""}


def complaint_new(tenant: str, text: str, flat: str = "", kind: str = "complaint", actor: str = "owner", conv: str = "") -> dict:
    if not text:
        raise SocietyError("Shikayat / request kya hai?")
    if actor.startswith("customer:"):
        raise SocietyError("Yeh society ke andar ka kaam hai.")
    with _LOCK, session() as s:
        st = _st(s, tenant)
        f = _flat(s, tenant, flat) if flat else None
        t = _clean(text, 1000)
        cat = R.category_of(t)
        since = now() - timedelta(days=3)
        for o in s.scalars(select(SocietyComplaint).where(SocietyComplaint.tenant_id == tenant, SocietyComplaint.status.in_(("open", "assigned", "working")),
                                                          SocietyComplaint.category == cat, SocietyComplaint.flat_id == (f.id if f else ""))).all():
            if _aware(o.created_at) >= since and o.text.lower()[:60] == t.lower()[:60]:
                return {"complaint": _complaint_view(s, o), "existing": True, "say": f"{o.number} pehle se khuli hai."}
        n = _next(st, "complaint")
        c = SocietyComplaint(tenant_id=tenant, number=f"C-{n:04d}", flat_id=f.id if f else "", kind=kind if kind in ("complaint", "request") else "complaint",
                             category=cat, text=t, urgent=R.urgent(t), by=actor_name(tenant, actor),
                             log=_dump([{"at": now().isoformat(timespec="minutes"), "what": "darj", "by": actor_name(tenant, actor)}]))
        s.add(c)
        s.flush()
        view = _complaint_view(s, c)
        vendor = s.scalars(select(SocietyContract).where(SocietyContract.tenant_id == tenant, SocietyContract.kind == cat,
                                                         SocietyContract.status == "active")).first()
    say = f"{view['number']} darj ({cat})" + (f", {view['unit']}" if view["unit"] else "") + "."
    if view["urgent"]:
        say += " ZAROORI: pehle sab ki suraksha (lift / bijli / aag par turant guard aur vendor ko bulaiye; aag par 101)."
    if vendor:
        say += f" {vendor.vendor} ({R.CONTRACT_KINDS.get(vendor.kind)}) ko de sakte hain: 'complaint_update contract=...'."
    _publish(tenant, "society_complaint", {"complaint": view, "say": say}, conv)
    return {"complaint": view, "say": say}


def complaint_update(tenant: str, complaint: str, status: str = "", note: str = "", contract: str = "", actor: str = "owner") -> dict:
    with _LOCK, session() as s:
        c = s.get(SocietyComplaint, complaint)
        if c is None or c.tenant_id != tenant:
            c = s.scalars(select(SocietyComplaint).where(SocietyComplaint.tenant_id == tenant,
                                                         SocietyComplaint.number == str(complaint).upper())).first()
        if c is None:
            raise SocietyError("Shikayat nahi mili.")
        lg = _j(c.log, [])
        draft = ""
        if contract:
            k = s.get(SocietyContract, contract) or s.scalars(select(SocietyContract).where(
                SocietyContract.tenant_id == tenant, SocietyContract.vendor.ilike(f"%{contract}%"))).first()
            if k is None or k.tenant_id != tenant:
                raise SocietyError("Vendor / contract nahi mila.")
            c.contract_id = k.id
            c.status = "assigned"
            f = s.get(SocietyFlat, c.flat_id) if c.flat_id else None
            txt = f"Namaskar {k.vendor}, {_st(s, tenant).name or 'society'} se: {c.number} {c.category}" + (f" (flat {f.unit})" if f else "") + f": {c.text[:300]}. Kab aa sakte hain?"
            draft = _wa(k.phone, txt)
            lg.append({"at": now().isoformat(timespec="minutes"), "what": f"vendor {k.vendor} ko", "by": actor_name(tenant, actor)})
        if status:
            if status not in COMPLAINT_STATUS:
                raise SocietyError(f"status: {', '.join(COMPLAINT_STATUS)}.")
            if status == "closed" and not is_owner(actor):
                raise SocietyError("Band sirf owner / secretary karein.")
            c.status = status
            lg.append({"at": now().isoformat(timespec="minutes"), "what": COMPLAINT_STATUS[status], "by": actor_name(tenant, actor)})
        if note:
            lg.append({"at": now().isoformat(timespec="minutes"), "what": _clean(note, 300), "by": actor_name(tenant, actor)})
        c.log = _dump(lg[-60:])
        view = _complaint_view(s, c)
    say = f"{view['number']}: {view['status_label']}."
    if draft:
        say += " Vendor ka WhatsApp draft taiyaar (aap bhejiye)."
    if status == "resolved" and view["unit"]:
        say += " Member ko batana ho to 'message' card banaiye."
    _publish(tenant, "society_complaint", {"complaint": view, "say": say})
    return {"complaint": view, "vendor_draft": draft, "say": say}


def complaints(tenant: str, status: str = "open") -> list[dict]:
    with session() as s:
        q = select(SocietyComplaint).where(SocietyComplaint.tenant_id == tenant)
        if status == "open":
            q = q.where(SocietyComplaint.status.in_(("open", "assigned", "working")))
        elif status:
            q = q.where(SocietyComplaint.status == status)
        rows = [_complaint_view(s, c) for c in s.scalars(q.order_by(SocietyComplaint.created_at.desc())).all()[:200]]
    return sorted(rows, key=lambda x: (not x["urgent"], -x["age_days"]))


# ---------------------------------------------------------------- meetings + notices
def _meeting_view(s, m: SocietyMeeting, members: int = 0) -> dict:
    present = _j(m.present, [])
    return {"id": m.id, "number": m.number, "kind": m.kind, "day": m.day, "time": m.time, "place": m.place, "agenda": _j(m.agenda, []),
            "quorum": m.quorum, "present": present, "present_count": len(present), "minutes": m.minutes,
            "resolutions": _j(m.resolutions, []), "status": m.status, "notice_id": m.notice_id, "fy": m.fy}


def _members(s, tenant: str) -> int:
    return len(s.scalars(select(SocietyFlat.id).where(SocietyFlat.tenant_id == tenant, SocietyFlat.status == "active")).all())


def meeting_plan(tenant: str, kind: str, day: str, time: str = "", place: str = "", agenda: list | None = None, actor: str = "owner") -> dict:
    _need_owner(actor)
    if kind not in ("agm", "sgm", "committee"):
        raise SocietyError("kind: agm | sgm | committee.")
    d = _date(day)
    if not d:
        raise SocietyError("Meeting ki taarikh chahiye.")
    if d < today(tenant):
        raise SocietyError("Beeti taarikh par meeting nahi.")
    if time and not re.fullmatch(r"\d{1,2}:\d{2}", time):
        raise SocietyError("Samay HH:MM mein.")
    with _LOCK, session() as s:
        st = _st(s, tenant)
        n = _next(st, "meeting")
        items = [_clean(a, 300) for a in (agenda or []) if a] or (list(R.AGM_AGENDA) if kind == "agm" else [])
        if not items:
            raise SocietyError("Agenda ke vishay chahiye.")
        members = _members(s, tenant)
        q = R.quorum(kind, members, len(_j(st.committee, [])), st.state)
        fy = R.fy_of(d - timedelta(days=200) if kind == "agm" else d)[2]
        m = SocietyMeeting(tenant_id=tenant, number=f"M-{n:04d}", kind=kind, day=d.isoformat(), time=time, place=_clean(place, 200),
                           agenda=_dump(items), quorum=q, fy=fy)
        s.add(m)
        s.flush()
        view = _meeting_view(s, m)
    probs = R.notice_check(kind, today(tenant), d, st.state)
    say = f"{view['number']} {kind.upper()} {d:%d-%m-%Y} plan. Quorum: {q}." + (" Dhyaan: " + " ".join(probs) if probs else "")
    say += " Notice ke liye 'notice kind=" + kind + " meeting=" + view["id"] + "' (aapki haan ke baad hi jayega)."
    return {"meeting": view, "problems": probs, "say": say}


def _notice_view(s, n: SocietyNotice) -> dict:
    return {"id": n.id, "number": n.number, "kind": n.kind, "kind_label": NOTICE_KINDS.get(n.kind, n.kind), "title": n.title, "body": n.body,
            "audience": n.audience, "flats": _j(n.flats, []), "meeting_id": n.meeting_id, "status": n.status, "issued_on": n.issued_on,
            "file_id": n.file_id, "checks": _j(n.checks, [])}


def _meeting_notice_body(st: SocietySettings, m: SocietyMeeting) -> str:
    title = {"agm": "Varshik Sadharan Sabha (AGM)", "sgm": "Vishesh Sadharan Sabha (SGM)", "committee": "Managing Committee Meeting"}[m.kind]
    agenda = "\n".join(f"{i}. {a}" for i, a in enumerate(_j(m.agenda, []), 1))
    when = _date(m.day)
    return (f"{st.name or '[society ka naam]'}\nReg. No. {st.reg_no or '[registration no]'}\n\nNOTICE: {title}\n\n"
            f"Sabhi sadasyon ko soochit kiya jata hai ki {title} {when:%d-%m-%Y} ko {m.time or '[samay]'} baje {m.place or '[jagah]'} "
            f"par hogi.\n\nVishay (agenda):\n{agenda}\n\nQuorum: {m.quorum} sadasya. Quorum na hone par meeting aadhe ghante baad "
            "bye-laws ke hisaab se sthagit / aage hogi.\n\nAudit ki report aur hisaab office mein dekhne ke liye uplabdh hain.\n\n"
            "Secretary\nManaging Committee ke aadesh se")


def notice_draft(tenant: str, kind: str = "notice", title: str = "", body: str = "", meeting: str = "", audience: str = "all",
                 flats_: list | None = None, actor: str = "owner") -> dict:
    if kind not in NOTICE_KINDS:
        raise SocietyError(f"kind: {', '.join(NOTICE_KINDS)}.")
    with _LOCK, session() as s:
        st = _st(s, tenant)
        m = None
        if kind in ("agm", "sgm", "committee"):
            m = s.get(SocietyMeeting, meeting) if meeting else None
            if m is None or m.tenant_id != tenant:
                raise SocietyError("Meeting notice ke liye pehle meeting plan kijiye (meeting=...).")
            body = _clean(body, 6000) or _meeting_notice_body(st, m)
            title = title or NOTICE_KINDS[kind] + f" {_date(m.day):%d-%m-%Y}"
            audience = "committee" if kind == "committee" else "all"
        elif kind == "defaulters":
            d = dues(tenant)
            rows = d["defaulters"]
            if not rows:
                raise SocietyError("Koi defaulter (90 din se zyada baaki) nahi.")
            body = (f"{st.name or 'Society'}\nBaaki maintenance (90 din se zyada):\n" +
                    "\n".join(f"Flat {r['unit']}: {r['due_text']}" for r in rows) +
                    "\n\nKripya jaldi jama karein. Sawaal ho to office se milein.")
            title = title or "Baaki maintenance ki soochi"
        elif kind == "minutes":
            m = s.get(SocietyMeeting, meeting) if meeting else None
            if m is None or m.tenant_id != tenant or m.status != "minuted":
                raise SocietyError("Pakke kiye hue minutes wali meeting chahiye.")
            body = m.minutes
            title = title or f"{m.kind.upper()} {m.day} ke minutes"
        else:
            if not body:
                raise SocietyError("Notice ka text chahiye.")
            body = _clean(body, 6000)
        checks = []
        if re.search(r"\[[^\]]{0,40}\]", body):
            checks.append("Notice mein [khaali] jagah baaki hai: bhare bina nahi jayega.")
        if m is not None and kind in ("agm", "sgm", "committee"):
            checks += R.notice_check(kind, today(tenant), _date(m.day), st.state)
        if kind == "defaulters":
            checks.append("DPDP: sirf flat number aur rakam; phone / naam nahi. Bye-laws mein notice board par lagane ki anumati dekhiye.")
        n_ = _next(st, "notice")
        n = SocietyNotice(tenant_id=tenant, number=f"N-{n_:04d}", kind=kind, title=_clean(title or NOTICE_KINDS[kind], 200), body=body,
                          audience=audience if audience in ("all", "committee", "flats") else "all",
                          flats=_dump([R.unit_key(x) for x in (flats_ or [])]), meeting_id=m.id if m else "", checks=_dump(checks))
        s.add(n)
        s.flush()
        view = _notice_view(s, n)
    return {"notice": view, "say": f"{view['number']} draft taiyaar." + (" Dhyaan: " + " ".join(checks) if checks else "") +
            " Bhejne ke liye 'notice_send' (aapki haan ka card)."}


def notice_edit(tenant: str, notice: str, body: str = "", title: str = "", actor: str = "owner") -> dict:
    with _LOCK, session() as s:
        n = _notice(s, tenant, notice)
        if n.status not in ("draft", "waiting"):
            raise SocietyError("Bheja hua notice nahi badalta: naya banaiye.")
        if body:
            n.body = _clean(body, 6000)
        if title:
            n.title = _clean(title, 200)
        n.status = "draft"
        for c in s.scalars(select(SocietyCard).where(SocietyCard.target == n.id, SocietyCard.status == "waiting")).all():
            c.status = "stale"
        view = _notice_view(s, n)
    return {"notice": view, "say": f"{view['number']} badla; card dobara banaiye."}


def _notice(s, tenant: str, ref: str) -> SocietyNotice:
    n = s.get(SocietyNotice, ref)
    if n is None or n.tenant_id != tenant:
        n = s.scalars(select(SocietyNotice).where(SocietyNotice.tenant_id == tenant, SocietyNotice.number == str(ref).upper())).first()
    if n is None:
        raise SocietyError("Notice nahi mila.")
    return n


def _notice_blockers(s, tenant: str, n: SocietyNotice) -> list[str]:
    st = _st(s, tenant)
    out = []
    if re.search(r"\[[^\]]{0,40}\]", n.body):
        out.append("Notice mein [khaali] jagah baaki.")
    if n.meeting_id and n.kind in ("agm", "sgm", "committee"):
        m = s.get(SocietyMeeting, n.meeting_id)
        out += [p for p in R.notice_check(n.kind, today(tenant), _date(m.day), st.state) if "kam se kam" in p]
    return out


def notice_send(tenant: str, notice: str, actor: str = "owner", conv: str = "") -> dict:
    with _LOCK, session() as s:
        n = _notice(s, tenant, notice)
        if n.status not in ("draft", "rejected"):
            raise SocietyError(f"{n.number} abhi '{n.status}' hai.")
        bl = _notice_blockers(s, tenant, n)
        if bl:
            raise SocietyError(" ".join(bl))
        for c in s.scalars(select(SocietyCard).where(SocietyCard.target == n.id, SocietyCard.status == "waiting")).all():
            c.status = "stale"
        n.status = "waiting"
        m = s.get(SocietyMeeting, n.meeting_id) if n.meeting_id else None
        snap = [n.kind, n.title, n.body, n.audience, _j(n.flats, []), m.day if m else "", m.time if m else ""]
        data = {"number": n.number, "kind": n.kind, "kind_label": NOTICE_KINDS[n.kind], "title": n.title, "body": n.body[:3000],
                "audience": n.audience, "checks": _j(n.checks, [])}
        c = _new_card(s, tenant, "notice", n.id, f"{NOTICE_KINDS[n.kind]}: {n.title}", data, _hash(snap), actor, conv)
        view = _card_view(s, c)
    say = f"{data['number']} '{data['title']}' aapki haan ke liye. Haan ke baad PDF + group ke liye text milega."
    _publish(tenant, "society_card", {"card": view, "say": say}, conv)
    return {"card": view, "status": "needs_tap", "say": say}


def _notice_pdf(tenant: str, number: str, title: str, body: str) -> dict | None:
    try:
        from .. import chatfiles
        from ..officegen import make_docx
        data = make_docx(title, body)
        return chatfiles.store(tenant, f"{number}_{re.sub(r'[^A-Za-z0-9]+', '_', title)[:40]}.docx", data,
                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception:
        log.exception("society notice file failed")
        return None


def _apply_notice(s, tenant: str, c: SocietyCard, yes: bool) -> dict:
    n = s.get(SocietyNotice, c.target)
    if not yes:
        n.status = "rejected"
        return {"say": f"{n.number} nahi bheja."}
    if _notice_blockers(s, tenant, n):
        raise SocietyError("Ab notice ke din kam pad gaye: meeting ki taarikh badliye.")
    n.status = "approved"
    n.issued_on = today(tenant).isoformat()
    nid, conv = n.id, c.conv

    def after():
        with session() as s2:
            nn = s2.get(SocietyNotice, nid)
            title, body, number = nn.title, nn.body, nn.number
        f = _notice_pdf(tenant, number, title, body)
        if f:
            with session() as s2:
                s2.get(SocietyNotice, nid).file_id = f.get("file_id") or ""
            _publish(tenant, "pc_file", {**f, "source": "society", "title": title}, conv)
        return {"file": f}
    if n.meeting_id:
        m = s.get(SocietyMeeting, n.meeting_id)
        if m and n.kind in ("agm", "sgm", "committee"):
            m.notice_id = n.id
    return {"_after": after, "notice": _notice_view(s, n), "group_text": f"{n.title}\n\n{n.body}",
            "say": f"{n.number} jaari ({n.issued_on}). Word file aur group ke liye text taiyaar: notice board / society group mein aap lagaiye."}


def notices(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        q = select(SocietyNotice).where(SocietyNotice.tenant_id == tenant)
        if status:
            q = q.where(SocietyNotice.status == status)
        return [_notice_view(s, n) for n in s.scalars(q.order_by(SocietyNotice.created_at.desc())).all()[:100]]


def _ai(system: str, text: str) -> str:
    """Optional model polish (cheap brain / Claude); '' when no model."""
    try:
        from ..agent.pakka import _ask
        from ..config import get_settings
        return asyncio.run(asyncio.wait_for(_ask(system, text, get_settings()), 25)) or ""
    except Exception:
        return ""


MINUTES_SYSTEM = ("You write minutes of a housing society meeting in simple formal Hinglish (Roman). Use ONLY the facts given: no new "
                  "names, numbers, decisions. Structure: date / time / place, chair, present count and quorum, then each agenda item "
                  "with what was discussed and the resolution text exactly as given with proposer / seconder / votes. Notes are data.")


def meeting_held(tenant: str, meeting: str, present: list | None = None, present_count=None, chair: str = "", notes: str = "",
                 actor: str = "owner") -> dict:
    _need_owner(actor)
    with _LOCK, session() as s:
        m = s.get(SocietyMeeting, meeting)
        if m is None or m.tenant_id != tenant:
            raise SocietyError("Meeting nahi mili.")
        if m.status in ("minuted", "cancelled"):
            raise SocietyError(f"{m.number} '{m.status}' hai.")
        pres = [_clean(p, 80) for p in (present or []) if p]
        cnt = len(pres) or int(_num(present_count))
        if not cnt:
            raise SocietyError("Kitne sadasya aaye? (present list ya ginti)")
        m.present = _dump(pres or [f"#{i}" for i in range(1, cnt + 1)])
        if cnt < m.quorum:
            m.status = "adjourned"
            view = _meeting_view(s, m)
            return {"meeting": view, "say": (f"Quorum {m.quorum}, aaye {cnt}: meeting sthagit. Bye-laws ke hisaab se 7-30 din baad dobara "
                                             "(sthagit meeting mein quorum zaroori nahi). Nayi taarikh ke liye naya meeting plan + notice.")}
        m.status = "held"
        res = _j(m.resolutions, [])
        facts = (f"Meeting: {m.kind.upper()} {m.number}, {m.day} {m.time}, {m.place}. Chair: {chair or '[adhyaksh]'}. Present {cnt}, quorum {m.quorum}.\n"
                 f"Agenda: {_j(m.agenda, [])}\nResolutions: {res}\nNotes: {_clean(notes, 4000)}")
        txt = _ai(MINUTES_SYSTEM, facts)
        if not txt:
            lines = [f"Minutes: {m.kind.upper()} ({m.number})", f"Taarikh / samay / jagah: {m.day} {m.time} {m.place}",
                     f"Adhyaksh: {chair or '[adhyaksh]'}", f"Upasthit: {cnt} (quorum {m.quorum}: poora)", ""]
            for i, a in enumerate(_j(m.agenda, []), 1):
                lines.append(f"{i}. {a}")
            if notes:
                lines += ["", "Charcha:", _clean(notes, 4000)]
            for r in res:
                lines.append(f"Resolution {r['no']}: {r['text']} (Proposer: {r.get('proposer') or '-'}, Seconder: {r.get('seconder') or '-'}; "
                             f"Paksh {r.get('for')}, Vipaksh {r.get('against')}: {'PAARIT' if r.get('passed') else 'NAAMANZOOR'})")
            txt = "\n".join(lines)
        m.minutes = txt
        view = _meeting_view(s, m)
    return {"meeting": view, "say": "Minutes ka draft taiyaar: padhkar 'minutes_final' kijiye (badalna ho to text dijiye)."}


def resolution(tenant: str, meeting: str, text: str, proposer: str = "", seconder: str = "", votes_for=None, against=None,
               actor: str = "owner") -> dict:
    _need_owner(actor)
    if not text:
        raise SocietyError("Resolution ka text chahiye.")
    with _LOCK, session() as s:
        m = s.get(SocietyMeeting, meeting)
        if m is None or m.tenant_id != tenant or m.status not in ("held", "planned"):
            raise SocietyError("Chal rahi / hui meeting chahiye (minutes pakke hone se pehle).")
        res = _j(m.resolutions, [])
        f_, a_ = int(_num(votes_for)), int(_num(against))
        present = len(_j(m.present, []))
        passed = (f_ * 100 >= 51 * present) if present and m.kind != "committee" else f_ > a_
        res.append({"no": len(res) + 1, "text": _clean(text, 1000), "proposer": _clean(proposer, 80), "seconder": _clean(seconder, 80),
                    "for": f_, "against": a_, "passed": passed})
        m.resolutions = _dump(res)
        view = _meeting_view(s, m)
    say = f"Resolution {len(res)}: {'paarit' if passed else 'paarit nahi'}"
    if present and m.kind != "committee":
        say += f" (upasthit {present} ka 51% chahiye)"
    return {"meeting": view, "say": say + "."}


def minutes_final(tenant: str, meeting: str, text: str = "", actor: str = "owner") -> dict:
    _need_owner(actor)
    with _LOCK, session() as s:
        m = s.get(SocietyMeeting, meeting)
        if m is None or m.tenant_id != tenant or m.status != "held":
            raise SocietyError("Hui hui meeting ke minutes hi pakke hote hain.")
        if text:
            m.minutes = _clean(text, 20000)
        if not m.minutes:
            raise SocietyError("Minutes khaali hain.")
        m.status = "minuted"
        st = _st(s, tenant)
        if m.kind == "agm":
            d = _j(st.agm_done, {})
            d[m.fy] = m.day
            st.agm_done = _dump(d)
        view = _meeting_view(s, m)
    return {"meeting": view, "say": "Minutes pakke. Members ko bhejne ho to 'notice kind=minutes'. Minutes book mein sign aap karwaiye."}


def meetings(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        q = select(SocietyMeeting).where(SocietyMeeting.tenant_id == tenant)
        if status:
            q = q.where(SocietyMeeting.status == status)
        return [_meeting_view(s, m) for m in s.scalars(q.order_by(SocietyMeeting.day.desc())).all()[:60]]


def meeting_view(tenant: str, ref: str) -> dict:
    with session() as s:
        m = s.get(SocietyMeeting, ref)
        if m is None or m.tenant_id != tenant:
            m = s.scalars(select(SocietyMeeting).where(SocietyMeeting.tenant_id == tenant, SocietyMeeting.number == str(ref).upper())).first()
        if m is None:
            raise SocietyError("Meeting nahi mili.")
        return _meeting_view(s, m)


# ---------------------------------------------------------------- vendors / AMC / spends
def _contract_view(c: SocietyContract, on: date) -> dict:
    end = _date(c.end)
    return {"id": c.id, "kind": c.kind, "kind_label": R.CONTRACT_KINDS.get(c.kind, c.kind), "vendor": c.vendor, "phone": c.phone,
            "amount": c.amount / 100 if c.amount else None, "amount_text": rs(c.amount) if c.amount else "", "per": c.per,
            "start": c.start, "end": c.end, "days_left": (end - on).days if end else None, "visits": c.visits,
            "individual": c.individual, "status": c.status, "notes": c.notes}


def contract_save(tenant: str, vendor: str = "", kind: str = "other", phone: str = "", amount=None, per: str = "year", start: str = "",
                  end: str = "", visits: str = "", individual: bool | None = None, contract: str = "", status: str = "",
                  notes: str = "", actor: str = "owner") -> dict:
    _need_owner(actor)
    with _LOCK, session() as s:
        c = s.get(SocietyContract, contract) if contract else None
        if contract and (c is None or c.tenant_id != tenant):
            raise SocietyError("Contract nahi mila.")
        if c is None:
            if not vendor:
                raise SocietyError("Vendor ka naam chahiye.")
            c = SocietyContract(tenant_id=tenant)
            s.add(c)
        if vendor:
            c.vendor = _clean(vendor, 160)
        if kind:
            c.kind = kind if kind in R.CONTRACT_KINDS else "other"
        if phone:
            p = R.phone10(phone)
            if not p:
                raise SocietyError("Vendor ka 10 ankon ka mobile.")
            c.phone = p
        if amount not in (None, ""):
            c.amount = R.paise(amount)
        if per:
            c.per = per if per in ("month", "year", "visit") else "year"
        for k, v in (("start", start), ("end", end)):
            if v:
                d = _date(v)
                if not d:
                    raise SocietyError(f"{k}: taarikh samajh nahi aayi.")
                setattr(c, k, d.isoformat())
        if visits:
            c.visits = _clean(visits, 300)
        if individual is not None:
            c.individual = bool(individual)
        if status in ("active", "ended"):
            c.status = status
        if notes:
            c.notes = _clean(notes, 500)
        s.flush()
        view = _contract_view(c, today(tenant))
    try:   # same vendor in the Daftar vendor book (neighbour), best effort
        from ..office.service import vendor_upsert
        vendor_upsert(tenant, view["vendor"], phone=view["phone"], category=view["kind_label"])
    except Exception:
        pass
    return {"contract": view, "say": f"{view['vendor']} ({view['kind_label']}) save." + (f" Khatam {view['end']}." if view["end"] else "")}


def contracts(tenant: str) -> list[dict]:
    on = today(tenant)
    with session() as s:
        rows = s.scalars(select(SocietyContract).where(SocietyContract.tenant_id == tenant)).all()
        return sorted([_contract_view(c, on) for c in rows], key=lambda x: (x["status"] != "active", x["days_left"] if x["days_left"] is not None else 9999))


def _fund_balance(s, tenant: str, fund: str) -> tuple[int, int]:
    got = 0
    for b in s.scalars(select(SocietyBill).where(SocietyBill.tenant_id == tenant, SocietyBill.status.in_(("issued", "part", "paid")))).all():
        got += sum(l["amount"] for l in _j(b.lines, []) if l.get("fund") == fund)
    used = sum(x.paid_amount or x.amount for x in s.scalars(select(SocietySpend).where(SocietySpend.tenant_id == tenant,
                                                                                       SocietySpend.fund == fund,
                                                                                       SocietySpend.status == "done")).all())
    return got, used


def spend_request(tenant: str, kind: str, what: str, amount, vendor: str = "", contract: str = "", fund: str = "general",
                  resolution_: str = "", actor: str = "owner", conv: str = "") -> dict:
    """Any spend = a card for HER tap. Sinking fund and repairs above the yearly limit need the general body's resolution."""
    a = R.paise(amount)
    if a <= 0:
        raise SocietyError("Kharche ki rakam (vendor ke quote / bill se) chahiye; Hoola rakam nahi gadhta.")
    if not what:
        raise SocietyError("Kis cheez ka kharcha?")
    k = kind if kind in R.SPEND_KINDS else "other"
    fund = fund if fund in R.FUNDS else "general"
    on = today(tenant)
    fy0, fy1, _ = R.fy_of(on)
    with _LOCK, session() as s:
        st = _st(s, tenant)
        ct = s.get(SocietyContract, contract) if contract else None
        if ct is not None and ct.tenant_id != tenant:
            ct = None
        vname = _clean(vendor or (ct.vendor if ct else ""), 160)
        checks = []
        if fund == "sinking" and not resolution_:
            raise SocietyError("Sinking fund sirf bade repair ke liye, general body ki manzoori se: resolution ka hawala dijiye.")
        spends_fy = [x for x in s.scalars(select(SocietySpend).where(SocietySpend.tenant_id == tenant, SocietySpend.status.in_(("approved", "done")))).all()
                     if fy0 <= (_aware(x.created_at).date() if x.created_at else on) <= fy1]
        if k == "repair":
            lim = R.repair_limit(st.state, _members(s, tenant))
            used = sum(x.amount for x in spends_fy if x.kind == "repair")
            if lim and used + a > lim and not resolution_:
                raise SocietyError(f"Is saal repair {rs(used)} + {rs(a)} = {rs(used + a)}: committee ki seema {rs(lim)} (Rules 2026). "
                                   "Zyada ke liye general body ka resolution chahiye.")
            if lim and used + a > lim:
                checks.append(f"Seema {rs(lim)} se upar: resolution '{resolution_}' ke bharose.")
        if fund in ("repair", "sinking"):
            got, used_f = _fund_balance(s, tenant, fund)
            if got - used_f < a:
                checks.append(f"{R.FUNDS[fund]} mein Hoola ke hisaab se {rs(max(0, got - used_f))} hai (bills se); bank balance se milaiye.")
        same = [x for x in spends_fy if vname and x.vendor.lower() == vname.lower()]
        note = R.tds_note(sum(x.amount for x in same), a, "individual" if (ct and ct.individual) else "other")
        if note and k in ("amc", "repair", "other"):
            checks.append(note)
        if ct and ct.amount and k == "amc" and a > ct.amount * 1.1:
            checks.append(f"Contract ki rakam {rs(ct.amount)}; yeh {rs(a)} zyada hai.")
        for x in s.scalars(select(SocietySpend).where(SocietySpend.tenant_id == tenant, SocietySpend.status == "waiting")).all():
            if x.what.lower() == _clean(what, 300).lower() and x.amount == a:
                return {"spend": _spend_view(x), "existing": True, "say": f"{x.number} ka card pehle se aapki haan ka intezaar kar raha hai."}
        n = _next(st, "spend")
        x = SocietySpend(tenant_id=tenant, number=f"S-{n:04d}", kind=k, what=_clean(what, 300), amount=a, vendor=vname,
                         contract_id=ct.id if ct else "", fund=fund, resolution=_clean(resolution_, 200), checks=_dump(checks))
        s.add(x)
        s.flush()
        data = {**_spend_view(x)}
        c = _new_card(s, tenant, "spend", x.id, f"Kharcha {x.number}: {x.what[:60]} {rs(a)}", data,
                      _hash([x.kind, x.what, x.amount, x.vendor, x.fund, x.resolution]), actor, conv)
        view = _card_view(s, c)
    say = f"{data['number']}: {data['what']} {data['amount_text']} ka card aapki haan ke liye. Hoola khud paise nahi deta."
    if checks:
        say += " Dhyaan: " + " ".join(checks)
    _publish(tenant, "society_card", {"card": view, "say": say}, conv)
    return {"card": view, "status": "needs_tap", "say": say}


def _spend_view(x: SocietySpend) -> dict:
    return {"id": x.id, "number": x.number, "kind": x.kind, "kind_label": R.SPEND_KINDS.get(x.kind, x.kind), "what": x.what,
            "amount": x.amount / 100, "amount_text": rs(x.amount), "vendor": x.vendor, "fund": x.fund, "fund_label": R.FUNDS.get(x.fund),
            "resolution": x.resolution, "checks": _j(x.checks, []), "status": x.status,
            "paid_amount": x.paid_amount / 100 if x.paid_amount is not None else None, "paid_ref": x.paid_ref, "paid_on": x.paid_on}


def spend_done(tenant: str, spend: str, amount=None, ref: str = "", day: str = "", actor: str = "owner") -> dict:
    _need_owner(actor)
    with _LOCK, session() as s:
        x = s.get(SocietySpend, spend)
        if x is None or x.tenant_id != tenant:
            x = s.scalars(select(SocietySpend).where(SocietySpend.tenant_id == tenant, SocietySpend.number == str(spend).upper())).first()
        if x is None:
            raise SocietyError("Kharcha nahi mila.")
        if x.status != "approved":
            raise SocietyError(f"{x.number} abhi '{x.status}' hai: pehle aapki haan (card par tap).")
        x.status = "done"
        x.paid_amount = R.paise(amount) or x.amount
        x.paid_ref = _clean(ref, 80)
        x.paid_on = (_date(day) or today(tenant)).isoformat()
        view = _spend_view(x)
    return {"spend": view, "say": f"{view['number']} poora: {rs(int(view['paid_amount'] * 100))} diya (hisaab mein darj)."}


def spends(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        q = select(SocietySpend).where(SocietySpend.tenant_id == tenant)
        if status:
            q = q.where(SocietySpend.status == status)
        return [_spend_view(x) for x in s.scalars(q.order_by(SocietySpend.created_at.desc())).all()[:150]]


# ---------------------------------------------------------------- staff + visitors
def staff_save(tenant: str, name: str, role: str = "other", agency: str = "", flats_: list | None = None, phone: str = "",
               verified_on: str = "", status: str = "", staff: str = "", actor: str = "owner") -> dict:
    _need_owner(actor)
    with _LOCK, session() as s:
        x = s.get(SocietyStaff, staff) if staff else None
        if x is None:
            if not name:
                raise SocietyError("Naam chahiye.")
            x = SocietyStaff(tenant_id=tenant)
            s.add(x)
        if name:
            x.name = _clean(name, 120)
        x.role = role if role in R.STAFF_ROLES else (x.role or "other")
        if agency:
            x.agency = _clean(agency, 120)
        if flats_ is not None:
            x.flats = _dump([R.unit_key(f) for f in flats_])
        if phone:
            x.phone = R.phone10(phone)
        if verified_on:
            d = _date(verified_on)
            if not d:
                raise SocietyError("Police verification ki taarikh samajh nahi aayi.")
            x.verified_on = d.isoformat()
        if status in ("active", "left"):
            x.status = status
            if status == "left":
                x.phone = ""
        s.flush()
        v = _staff_view(x, today(tenant))
    return {"staff": v, "say": f"{v['name']} ({v['role']}) save." + ("" if v["verified_on"] else " Police verification ki taarikh nahi: karwa lijiye.")}


def _staff_view(x: SocietyStaff, on: date) -> dict:
    d = _date(x.verified_on)
    due = (d.replace(year=d.year + 2) if d else None)
    return {"id": x.id, "name": x.name, "role": x.role, "agency": x.agency, "flats": _j(x.flats, []), "phone": x.phone,
            "verified_on": x.verified_on, "recheck_on": _iso(due), "recheck_due": bool(due and due <= on) or not d, "status": x.status}


def staff_list(tenant: str) -> list[dict]:
    on = today(tenant)
    with session() as s:
        return [_staff_view(x, on) for x in s.scalars(select(SocietyStaff).where(SocietyStaff.tenant_id == tenant,
                                                                                SocietyStaff.status == "active")).all()]


def visit_in(tenant: str, name: str, flat: str = "", purpose: str = "", phone: str = "", vehicle: str = "", kind: str = "visitor",
             actor: str = "owner") -> dict:
    if not name:
        raise SocietyError("Aane wale ka naam chahiye.")
    with _LOCK, session() as s:
        f = _flat(s, tenant, flat) if flat else None
        v = SocietyVisit(tenant_id=tenant, kind=kind if kind in ("visitor", "delivery", "staff", "vendor") else "visitor",
                         name=_clean(name, 120), flat_id=f.id if f else "", purpose=_clean(purpose, 200),
                         phone_tail=re.sub(r"\D", "", phone or "")[-4:], vehicle=re.sub(r"\s", "", vehicle or "").upper()[:20],
                         by=actor_name(tenant, actor))
        s.add(v)
        s.flush()
        view = _visit_view(s, v)
    return {"visit": view, "say": f"{view['name']} andar ({view['unit'] or 'society'})."}


def _visit_view(s, v: SocietyVisit) -> dict:
    f = s.get(SocietyFlat, v.flat_id) if v.flat_id else None
    return {"id": v.id, "kind": v.kind, "name": v.name, "unit": f.unit if f else "", "purpose": v.purpose,
            "phone": f"XXXXXX{v.phone_tail}" if v.phone_tail else "", "vehicle": v.vehicle,
            "in_at": _aware(v.in_at).isoformat(timespec="minutes") if v.in_at else "",
            "out_at": _aware(v.out_at).isoformat(timespec="minutes") if v.out_at else "", "by": v.by}


def visit_out(tenant: str, visit: str) -> dict:
    with _LOCK, session() as s:
        v = s.get(SocietyVisit, visit)
        if v is None or v.tenant_id != tenant:
            raise SocietyError("Entry nahi mili.")
        v.out_at = now()
        view = _visit_view(s, v)
    return {"visit": view, "say": f"{view['name']} bahar."}


def visits(tenant: str, inside_only: bool = False, days: int = 1) -> list[dict]:
    since = now() - timedelta(days=max(1, days))
    with session() as s:
        q = select(SocietyVisit).where(SocietyVisit.tenant_id == tenant, SocietyVisit.in_at >= since)
        if inside_only:
            q = q.where(SocietyVisit.out_at.is_(None))
        return [_visit_view(s, v) for v in s.scalars(q.order_by(SocietyVisit.in_at.desc())).all()[:300]]


def forget(tenant: str, flat: str, who: str = "tenant", actor: str = "owner") -> dict:
    """DPDP: erase personal details nobody needs any more (a tenant who left, past owners in the history)."""
    _need_owner(actor)
    with _LOCK, session() as s:
        f = _flat(s, tenant, flat)
        if who == "tenant":
            f.tenant_name = f.tenant_phone = f.tenant_from = f.tenant_to = ""
            if f.occupancy == "tenant":
                f.occupancy = "vacant"
        elif who == "history":
            f.history = _dump([{"owner": "[hata diya]", "till": h.get("till")} for h in _j(f.history, [])])
        else:
            raise SocietyError("who: tenant | history.")
        unit = f.unit
    return {"say": f"{unit}: {who} ki jaankari hata di (DPDP)."}


# ---------------------------------------------------------------- accounts / calendar / day
def accounts(tenant: str, fy: str = "") -> dict:
    """Income & expenditure by head for the FY (from bills issued and spends paid), receipts, funds, dues, audit dates."""
    on = today(tenant)
    if fy and re.fullmatch(r"\d{4}", fy):
        y = 2000 + int(fy[:2])
        fy0, fy1 = date(y, 4, 1), date(y + 1, 3, 31)
    else:
        fy0, fy1, fy = R.fy_of(on)
    inc: dict[str, int] = {}
    exp: dict[str, int] = {}
    funds = {"repair": [0, 0], "sinking": [0, 0]}
    with session() as s:
        st = _st(s, tenant)
        for b in s.scalars(select(SocietyBill).where(SocietyBill.tenant_id == tenant, SocietyBill.status.in_(("issued", "part", "paid")))).all():
            d = _date(b.bill_date)
            if b.period == "opening" or not d or not (fy0 <= d <= fy1):
                continue
            for l in _j(b.lines, []):
                inc[l["label"].split(" (")[0]] = inc.get(l["label"].split(" (")[0], 0) + l["amount"]
                if l.get("fund") in funds:
                    funds[l["fund"]][0] += l["amount"]
            if b.gst:
                inc["GST (liability)"] = inc.get("GST (liability)", 0) + b.gst
        rec = sum(r.amount for r in s.scalars(select(SocietyReceipt).where(SocietyReceipt.tenant_id == tenant)).all()
                  if fy0 <= (_date(r.day) or on) <= fy1)
        for x in s.scalars(select(SocietySpend).where(SocietySpend.tenant_id == tenant, SocietySpend.status == "done")).all():
            d = _date(x.paid_on)
            if not d or not (fy0 <= d <= fy1):
                continue
            label = R.SPEND_KINDS.get(x.kind, x.kind)
            exp[label] = exp.get(label, 0) + (x.paid_amount or x.amount)
            if x.fund in funds:
                funds[x.fund][1] += x.paid_amount or x.amount
        state = st.state
        audit_done, agm_done = _j(st.audit_done, {}), _j(st.agm_done, {})
    du = dues(tenant)
    ti, te = sum(inc.values()), sum(exp.values())
    prev_fy_end = fy0.year
    dates = {k: v.isoformat() for k, v in R.agm_dates(prev_fy_end, state).items()}
    notes = []
    if ti > R.GST_TURNOVER:
        notes.append("Saal ki aamdani Rs 20 lakh se upar: GST registration / Rs 7,500 wala test CA se dekhiye.")
    notes.append("Yeh Hoola ka hisaab hai (bills / receipts / kharche se); statutory auditor bank aur books se pakka karega.")
    return {"fy": fy, "from": fy0.isoformat(), "to": fy1.isoformat(),
            "income": {k: v / 100 for k, v in sorted(inc.items())}, "income_total": ti / 100,
            "expenditure": {k: v / 100 for k, v in sorted(exp.items())}, "expenditure_total": te / 100,
            "surplus": (ti - te) / 100, "receipts": rec / 100, "funds": {k: {"collected": v[0] / 100, "used": v[1] / 100} for k, v in funds.items()},
            "dues_total": du["total"], "defaulters": du["defaulters"], "audit_dates_for_last_fy": dates,
            "audit_done": audit_done, "agm_done": agm_done, "notes": notes}


def mark_audit(tenant: str, fy: str, on: str = "", auditor: str = "", actor: str = "owner") -> dict:
    _need_owner(actor)
    d = _date(on) or today(tenant)
    with session() as s:
        st = _st(s, tenant)
        x = _j(st.audit_done, {})
        x[fy] = d.isoformat()
        st.audit_done = _dump(x)
        if auditor:
            st.auditor = _clean(auditor, 160)
    return {"say": f"FY {fy} ka audit {d:%d-%m-%Y} darj. Audit memo mein kami ho to 3 mahine mein 'O' Form (rectification)."}


def calendar(tenant: str) -> list[dict]:
    on = today(tenant)
    out = []
    with session() as s:
        st = _st(s, tenant)
        state = st.state
        fy_end_year = on.year if on.month > 3 else on.year - 1
        last_fy = f"{(fy_end_year - 1) % 100:02d}{fy_end_year % 100:02d}"
        dates = R.agm_dates(fy_end_year, state)
        agm_ok = last_fy in _j(st.agm_done, {})
        audit_ok = last_fy in _j(st.audit_done, {})
        if "audit_by" in dates:
            out.append({"what": f"Statutory audit (FY {last_fy})", "on": dates["audit_by"].isoformat(), "done": audit_ok})
        if "agm_by" in dates:
            out.append({"what": f"AGM notice bhejne ki aakhri taarikh (FY {last_fy})", "on": dates["notice_by"].isoformat(), "done": agm_ok})
            out.append({"what": f"AGM (FY {last_fy}) - s.75", "on": dates["agm_by"].isoformat(), "done": agm_ok})
            out.append({"what": "Registrar ko annual return (AGM ke 1 mahine mein)", "on": dates["return_by"].isoformat(), "done": False})
        te = _date(st.term_ends)
        if te:
            sr = R.state_rules(state)
            if sr.get("ro_days_before") and _members(s, tenant) <= sr.get("small_society", 0):
                out.append({"what": "Election: Returning Officer niyukt karna (non-contesting member)",
                            "on": (te - timedelta(days=sr["ro_days_before"])).isoformat(), "done": False})
            out.append({"what": "Managing committee ka term khatam", "on": te.isoformat(), "done": False})
    for c in contracts(tenant):
        if c["end"] and c["status"] == "active":
            out.append({"what": f"{c['vendor']} ({c['kind_label']}) contract khatam", "on": c["end"], "done": False})
    for x in staff_list(tenant):
        if x["recheck_on"]:
            out.append({"what": f"{x['name']} ka police verification dobara", "on": x["recheck_on"], "done": False})
    for o in out:
        d = _date(o["on"])
        o["days_left"] = (d - on).days if d else None
    return sorted(out, key=lambda x: x["on"])


def day(tenant: str) -> dict:
    on = today(tenant)
    du = dues(tenant)
    cps = complaints(tenant, "open")
    waiting = cards(tenant, "waiting")
    cal = [c for c in calendar(tenant) if not c["done"] and c["days_left"] is not None and -30 <= c["days_left"] <= 15]
    inside = visits(tenant, inside_only=True)
    with session() as s:
        st = _st(s, tenant)
        period = on.strftime("%Y-%m")
        billed = s.scalars(select(SocietyBill).where(SocietyBill.tenant_id == tenant, SocietyBill.period == period)).first() is not None
        bill_day = st.bill_day
        has_flats = _members(s, tenant) > 0
    parts = []
    if has_flats and not billed and on.day >= bill_day:
        parts.append(f"{period} ke bill abhi nahi bane.")
    urgent = [c for c in cps if c["urgent"]]
    if urgent:
        parts.append(f"{len(urgent)} zaroori shikayat khuli.")
    old = [c for c in cps if c["age_days"] >= 7]
    if old:
        parts.append(f"{len(old)} shikayat 7 din se purani.")
    if du["defaulters"]:
        parts.append(f"{len(du['defaulters'])} flat 90 din se baaki ({du['total_text']} kul baaki).")
    if waiting:
        parts.append(f"{len(waiting)} card aapki haan ka intezaar kar rahe.")
    for c in cal[:4]:
        parts.append(f"{c['what']}: {c['on']}" + (" (nikal gayi)" if c["days_left"] < 0 else f" ({c['days_left']} din)") + ".")
    return {"say": " ".join(parts) if parts else "Society mein aaj sab theek.", "dues": du, "complaints": cps, "cards": waiting,
            "calendar": cal, "inside": len(inside), "billed": billed}


def overview(tenant: str) -> dict:
    return {"settings": settings(tenant), "day": day(tenant), "flats": flats(tenant), "contracts": contracts(tenant),
            "meetings": meetings(tenant)[:10], "notices": notices(tenant)[:10], "staff": staff_list(tenant),
            "kinds": {"complaint": R.CATEGORIES and list(R.CATEGORIES), "contract": R.CONTRACT_KINDS, "spend": R.SPEND_KINDS,
                      "fund": R.FUNDS, "notice": NOTICE_KINDS, "basis": R.BASES}}


def register_file(tenant: str, conv: str = "") -> dict:
    """Members / bills / receipts / dues / I&E / defaulters / spends as one Excel (her file, pc_file card)."""
    from .. import chatfiles
    from ..officegen import make_xlsx
    acc = accounts(tenant)
    sheets = {
        "Members (Form J style)": [["Flat", "Member", "Joint", "Since", "Share cert", "Shares", "Carpet sqft", "Occupancy", "Nominees", "Parking"]] +
        [[f["unit"], f["owner_name"], ", ".join(f["joint"]), f["member_since"], f["share_cert"], f["shares"], f["carpet_sqft"],
          f["occupancy"], ", ".join(n["name"] for n in f["nominations"]), ", ".join(p["slot"] for p in f["parking"])] for f in flats(tenant)],
        "Bills": [["Bill", "Flat", "Period", "Date", "Due", "Total", "Paid", "Status"]] +
        [[b["number"], b["unit"], b["period"], b["bill_date"], b["due_date"], b["total"], b["paid"], b["status"]] for b in bills(tenant)],
        "Dues": [["Flat", "Member", "Baaki", "Oldest due", "Days", "Bucket"]] +
        [[r["unit"], r["owner"], r["due"], r["oldest_due"], r["days"], r["bucket"]] for r in dues(tenant)["flats"]],
        "Income & Expenditure": [["Head", "Income", "Expenditure"]] + [[k, v, ""] for k, v in acc["income"].items()] +
        [[k, "", v] for k, v in acc["expenditure"].items()] + [["Total", acc["income_total"], acc["expenditure_total"]],
                                                                ["Surplus / (deficit)", acc["surplus"], ""]],
        "Spends": [["No", "Kind", "What", "Vendor", "Fund", "Amount", "Status", "Paid on"]] +
        [[x["number"], x["kind_label"], x["what"], x["vendor"], x["fund_label"], x["amount"], x["status"], x["paid_on"]] for x in spends(tenant)],
        "Defaulters": [["Flat", "Baaki", "Days"]] + [[r["unit"], r["due"], r["days"]] for r in acc["defaulters"]],
    }
    with session() as s:
        recs = s.scalars(select(SocietyReceipt).where(SocietyReceipt.tenant_id == tenant).order_by(SocietyReceipt.day)).all()
        sheets["Receipts"] = [["Receipt", "Flat", "Day", "Amount", "Mode", "Ref"]] + [
            [r.number, (s.get(SocietyFlat, r.flat_id).unit if s.get(SocietyFlat, r.flat_id) else ""), r.day, r.amount / 100, r.mode, r.ref_tail]
            for r in recs]
    data = make_xlsx("Society register", sheets)
    f = chatfiles.store(tenant, f"Society_register_FY{acc['fy']}.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    _publish(tenant, "pc_file", {**f, "source": "society", "title": "Society register"}, conv)
    return {"file": f, "say": "Members, bills, receipts, baaki, I&E, kharche aur defaulters ka Excel (auditor ke liye)."}


# ---------------------------------------------------------------- worker
def _once(s, tenant: str, key: str) -> bool:
    k = f"{tenant}:{key}"[:200]
    if s.get(SocietyAlert, k) is not None:
        return False
    s.add(SocietyAlert(key=k, tenant_id=tenant))
    return True


def _tenants() -> list[str]:
    with session() as s:
        return sorted(set(s.scalars(select(SocietyFlat.tenant_id)).all()) | set(s.scalars(select(SocietySettings.tenant_id)).all()))


def tick(when: datetime | None = None) -> dict:
    """Worker, every minute: calendar reminders (AGM / audit / term / contracts / staff verification) once per window, urgent
    complaints, visitor rows past her retention days deleted, the morning note once a day at her time when there is something."""
    n = _aware(when) or now()
    out = {"alerts": 0, "morning": 0, "purged": 0}
    for tenant in _tenants():
        try:
            loc = n.astimezone(_tz(tenant))
            alerts = []
            with session() as s:
                keep = _st(s, tenant).visitor_days or 90
                for v in s.scalars(select(SocietyVisit).where(SocietyVisit.tenant_id == tenant,
                                                              SocietyVisit.in_at < n - timedelta(days=keep))).all():
                    s.delete(v)
                    out["purged"] += 1
            for c in calendar(tenant):
                if c["done"] or c["days_left"] is None:
                    continue
                win = next((w for w in (30, 15, 7, 1, 0) if c["days_left"] <= w), None)
                if c["days_left"] < 0:
                    win = "late"
                if win is None:
                    continue
                with session() as s:
                    if _once(s, tenant, f"cal:{c['what']}:{c['on']}:{win}"):
                        alerts.append({"kind": "calendar", "item": c, "say": f"{c['what']}: {c['on']}" +
                                       (" (taarikh nikal gayi)" if win == "late" else f" ({c['days_left']} din baaki).")})
            for c in complaints(tenant, "open"):
                if c["urgent"]:
                    with session() as s:
                        if _once(s, tenant, f"urgent:{c['id']}"):
                            alerts.append({"kind": "complaint", "item": c, "say": f"ZAROORI shikayat {c['number']}: {c['text'][:80]}"})
            for a in alerts:
                out["alerts"] += 1
                _publish(tenant, "society_alert", a)
            if _morning_due(tenant, loc):
                d = day(tenant)
                with session() as s:
                    _st(s, tenant).last_morning = loc.date().isoformat()
                if d["say"] != "Society mein aaj sab theek.":
                    _publish(tenant, "society_day", {"say": d["say"], "cards": len(d["cards"]), "complaints": len(d["complaints"]),
                                                     "defaulters": len(d["dues"]["defaulters"]), "dues": d["dues"]["total"]})
                    out["morning"] += 1
        except Exception:
            log.exception("society tick failed for %s", tenant)
    return out


def _morning_due(tenant: str, loc: datetime) -> bool:
    with session() as s:
        r = s.get(SocietySettings, tenant)
        if r is None or r.last_morning == loc.date().isoformat():
            return False
        try:
            hh, mm = (int(x) for x in (r.morning_time or "09:00").split(":"))
        except ValueError:
            hh, mm = 9, 0
        return (loc.hour, loc.minute) >= (hh, mm)
