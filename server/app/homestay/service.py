"""Homestay Sahayak: Hoola as a homestay / B&B / farm stay / villa host's coworker (1-6 rooms).

  1. Rooms (R-01) with HER rates (weekday / weekend / special dates, extra person) and HER menu for meals / add-ons.
  2. One calendar for every channel: direct enquiries (hold -> confirmed only when HER tap sends the confirmation), OTA bookings from
     the mail SHE pastes (Airbnb / Booking.com / MakeMyTrip / Agoda / Goibibo: dates, code, guests, payout read as data) and the iCal
     export file SHE gives. A room can never be booked twice for a night: refused in code, from every source, with a clash alert.
     Her own calendar goes out as an .ics link (no guest names) that she adds in the OTA's own "import calendar" page.
  3. Guests (G-001): ID numbers only in the Pehchaan Locker ({id:...}); foreign guests -> Form C (Form-III) data sheet + 24 h clock
     (Immigration and Foreigners Act 2025), she submits on indianfrro.gov.in and notes the reference; police intimation when her thana asks.
  4. Messages to guests (confirmation with HER cancellation policy shown upfront, check-in instructions, house rules, advance / balance
     UPI link to HER UPI ID, review request - the same text for everyone) are cards: only HER tap sends them.
  5. Cancel / refund / spend = cards decided only by HER tap (fingerprint once a phone key is active). Money never moves.
  6. Turnover tasks between stays (clean, linen, laundry, restock, check) due before the next check-in; state registration checklist +
     renewal reminders (state starters with sources); monthly earnings, occupancy, ADR, RevPAR by source; DPDP forget.
"""
from __future__ import annotations

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
from .models import HsAlert, HsBooking, HsCard, HsGuest, HsPayment, HsRoom, HsSettings, HsTask

log = logging.getLogger("santosh.homestay")
_LOCK = threading.RLock()
LIVE = ("hold", "confirmed", "checked_in", "blocked")
MONEY_KINDS = ("cancel", "refund", "spend")
STATUS_LABEL = {"hold": "Hold (pakki nahi)", "confirmed": "Pakki", "checked_in": "Ghar mein", "checked_out": "Chale gaye",
                "cancelled": "Radd", "no_show": "Nahi aaye", "blocked": "Band"}
MSG_KINDS = ("confirmation", "checkin_info", "house_rules", "payment", "review", "cancellation", "custom")
TURNOVER = (("clean", "Kamra saaf + bathroom"), ("linen", "Chadar / towel badlo"), ("laundry", "Laundry"),
            ("restock", "Sabun / paani / chai saman bharo"), ("check", "Toota / kharab dekho, photo"))


class StayError(Exception):
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


def _date(v, tenant: str = "") -> date | None:
    return R.parse_date(v, today(tenant) if tenant else None)


def _rs(v: float | None) -> str:
    if v is None:
        return ""
    try:
        from ..india.money import inr
        return inr(v)
    except Exception:
        return f"₹{v:,.0f}"


def _r2(v) -> float:
    return round(float(v or 0) + 1e-9, 2)


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("homestay publish failed")


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


def _st(s, tenant: str) -> HsSettings:
    r = s.get(HsSettings, tenant)
    if r is None:
        r = HsSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def _next(s, tenant: str, key: str) -> int:
    st = _st(s, tenant)
    seq = _j(st.seq, {})
    seq[key] = int(seq.get(key, 0)) + 1
    st.seq = _dump(seq)
    return seq[key]


def _clean(text, n: int = 500) -> str:
    return R.scrub(str(text or ""), n)


def _hash(v) -> str:
    return hashlib.sha256(_dump(v).encode()).hexdigest()


def _log(b: HsBooking, what: str) -> None:
    lg = _j(b.log, [])
    lg.append({"at": clock().isoformat(timespec="minutes"), "what": what[:200]})
    b.log = _dump(lg[-60:])


def _once(s, tenant: str, key: str) -> bool:
    k = f"{tenant}:{key}"[:200]
    if s.get(HsAlert, k) is not None:
        return False
    s.add(HsAlert(key=k, tenant_id=tenant))
    s.flush()
    return True


# ---------------------------------------------------------------- settings
_SET_KEYS = ("business", "host_name", "phone", "address", "city", "state", "pin", "map_link", "kind", "in_flat", "serves_food", "upi_id",
             "upi_name", "gstin", "checkin_time", "checkout_time", "house_rules", "checkin_info", "advance_pct", "hold_hours", "policy",
             "menu", "count_children", "review_link", "police_intimation", "staff", "morning_time", "rules")


def _upi(r: HsSettings) -> tuple[str, str]:
    if r.upi_id:
        return r.upi_id, r.upi_name or r.business or r.host_name
    try:
        from ..employee import service as emp
        p = emp.profile(r.tenant_id) or {}
        return p.get("upi_id") or "", p.get("upi_name") or p.get("business_name") or r.business
    except Exception:
        return "", ""


def _settings_view(r: HsSettings) -> dict:
    vpa, vname = _upi(r)
    out = {k: getattr(r, k) for k in _SET_KEYS if k not in ("policy", "menu", "staff")}
    out.update({"policy": _j(r.policy, []), "policy_text": R.policy_text(_j(r.policy, [])), "menu": _j(r.menu, {}),
                "staff": _j(r.staff, []), "upi_effective": vpa, "upi_name_effective": vname,
                "ical_link": f"/api/homestay-ical/{r.tenant_id}/{_ical_token(r)}.ics"})
    return out


def _ical_token(r: HsSettings) -> str:
    seq = _j(r.seq, {})
    return str(seq.get("ical_token") or "")


def settings(tenant: str) -> dict:
    with session() as s:
        r = _st(s, tenant)
        if not _ical_token(r):
            seq = _j(r.seq, {})
            seq["ical_token"] = secrets.token_urlsafe(18)
            r.seq = _dump(seq)
        return _settings_view(r)


def _parse_menu(v) -> dict:
    if isinstance(v, dict):
        out = {}
        for k, x in v.items():
            k = str(k).strip().lower()[:40]
            if k.endswith("__per"):
                out[k] = str(x) if str(x) in ("person_day", "day", "once") else "person_day"
            elif R.money(x) > 0:
                out[k] = R.money(x)
        return out
    out = {}
    for m in re.finditer(r"([A-Za-z][A-Za-z ]{1,30}?)\s*[-:=]?\s*(?:₹|rs\.?)?\s*(\d[\d,]*)", str(v or "")):
        out[m.group(1).strip().lower()] = R.money(m.group(2))
    return out


def save_settings(tenant: str, **kw: Any) -> dict:
    with _LOCK, session() as s:
        r = _st(s, tenant)
        for k in _SET_KEYS:
            if k not in kw or kw[k] is None:
                continue
            v = kw[k]
            if k in ("in_flat", "serves_food", "count_children", "police_intimation"):
                setattr(r, k, bool(v))
            elif k == "advance_pct":
                r.advance_pct = max(0.0, min(100.0, R.money(v)))
            elif k == "hold_hours":
                r.hold_hours = max(1, min(168, int(R.money(v))))
            elif k == "policy":
                tiers = v if isinstance(v, list) else R.parse_policy(str(v))
                clean = sorted([{"days": max(0, int(R.money(t.get("days")))), "pct": max(0.0, min(100.0, R.money(t.get("pct"))))}
                                for t in tiers if isinstance(t, dict)], key=lambda t: -t["days"])
                if str(v).strip() and not clean:
                    raise StayError("Policy samajh nahi aayi. Aise likhiye: '7 din pehle 100%, 2 din pehle 50%, uske baad kuch nahi'.")
                r.policy = _dump(clean)
            elif k == "menu":
                menu = _j(r.menu, {})
                menu.update(_parse_menu(v))
                r.menu = _dump(menu)
            elif k == "staff":
                lst = v if isinstance(v, list) else [{"name": x.strip()} for x in str(v).split(",") if x.strip()]
                r.staff = _dump([{"name": _clean(x.get("name"), 60), "phone": R.phone10(x.get("phone")), "role": _clean(x.get("role"), 30)}
                                 for x in lst if isinstance(x, dict) and x.get("name")][:20])
            elif k in ("checkin_time", "checkout_time", "morning_time"):
                if v and not re.fullmatch(r"\d{1,2}:\d{2}", str(v)):
                    raise StayError("Samay HH:MM mein (jaise 12:00).")
                setattr(r, k, str(v))
            elif k == "state":
                r.state = str(v).upper()[:4]
            elif k == "gstin":
                g = str(v).strip().upper()
                if g:
                    from ..india.money import gstin_ok
                    if not gstin_ok(g):
                        raise StayError("GSTIN sahi nahi (check digit).")
                r.gstin = g
            elif k == "phone":
                r.phone = R.phone10(v)
            elif k == "pin":
                p = re.sub(r"\D", "", str(v))
                if p and not re.fullmatch(r"[1-9]\d{5}", p):
                    raise StayError("PIN 6 ank.")
                r.pin = p
            elif k in ("map_link", "review_link"):
                u = str(v).strip()
                if u and not u.startswith("https://"):
                    raise StayError("Link https:// se shuru ho.")
                setattr(r, k, u[:300])
            elif k == "checkin_info":
                if re.search(r"\b(password|wifi pass|pin)\b", str(v), re.I):
                    raise StayError("Password / PIN yahan mat likhiye; mehmaan ko aap khud bataiye.")
                r.checkin_info = _clean(v, 2000)
            else:
                setattr(r, k, _clean(v, 3000))
    return {"settings": settings(tenant), "say": "Homestay ki settings save."}


# ---------------------------------------------------------------- rooms
_ROOM_KEYS = ("name", "kind", "beds", "base_guests", "max_guests", "base_rate", "weekend_rate", "extra_person", "special", "ota_names",
              "active", "notes")


def _room_view(r: HsRoom) -> dict:
    return {"id": r.id, "number": r.number, "name": r.name, "kind": r.kind, "beds": r.beds, "base_guests": r.base_guests,
            "max_guests": r.max_guests, "base_rate": r.base_rate, "weekend_rate": r.weekend_rate, "extra_person": r.extra_person,
            "special": _j(r.special, {}), "ota_names": _j(r.ota_names, []), "active": r.active, "notes": r.notes,
            "priced": r.base_rate > 0}


def _room(s, tenant: str, ref: str) -> HsRoom:
    ref = str(ref or "").strip()
    r = s.get(HsRoom, ref)
    if r and r.tenant_id == tenant:
        return r
    rows = s.scalars(select(HsRoom).where(HsRoom.tenant_id == tenant)).all()
    low = ref.lower()
    for x in rows:
        if low and (x.number.lower() == low or x.name.lower() == low or low in [n.lower() for n in _j(x.ota_names, [])]):
            return x
    m = re.fullmatch(r"(?:r-?|room\s*|kamra\s*)?0*(\d{1,2})", low)
    if m:
        for x in rows:
            if x.number == f"R-{int(m.group(1)):02d}":
                return x
    raise StayError(f"Kamra '{ref}' nahi mila.")


def save_room(tenant: str, room: str = "", **kw: Any) -> dict:
    warn = []
    with _LOCK, session() as s:
        if room:
            r = _room(s, tenant, room)
        else:
            if not str(kw.get("name") or "").strip():
                raise StayError("Kamre ka naam chahiye (jaise 'Neem room').")
            n = len(s.scalars(select(HsRoom).where(HsRoom.tenant_id == tenant)).all())
            if n >= 12:
                raise StayError("12 kamron tak (yeh homestay ke liye hai; bade hotel ke liye Front office Sahayak).")
            r = HsRoom(tenant_id=tenant, number=f"R-{_next(s, tenant, 'room'):02d}", base_guests=2, max_guests=3, base_rate=0.0,
                       weekend_rate=0.0, extra_person=0.0, special="{}", ota_names="[]", active=True)
            s.add(r)
            if n + 1 > 6:
                warn.append("Zyada tar rajyon ki homestay scheme 6 kamron tak hai: apne rajya ka niyam dekhiye.")
        for k in _ROOM_KEYS:
            if k not in kw or kw[k] is None:
                continue
            v = kw[k]
            if k in ("base_rate", "weekend_rate", "extra_person"):
                setattr(r, k, max(0.0, R.money(v)))
            elif k in ("base_guests", "max_guests"):
                setattr(r, k, max(1, min(30, int(R.money(v)))))
            elif k == "special":
                sp = _j(r.special, {})
                for d, x in (v.items() if isinstance(v, dict) else []):
                    dd = R.parse_date(d)
                    if dd and R.money(x) > 0:
                        sp[dd.isoformat()] = R.money(x)
                    elif dd:
                        sp.pop(dd.isoformat(), None)
                r.special = _dump(sp)
            elif k == "ota_names":
                r.ota_names = _dump([_clean(x, 80) for x in (v if isinstance(v, list) else str(v).split(",")) if str(x).strip()][:10])
            elif k == "active":
                r.active = bool(v)
            else:
                setattr(r, k, _clean(v, 400))
        if r.max_guests < r.base_guests:
            r.max_guests = r.base_guests
        s.flush()
        view = _room_view(r)
    if not view["priced"]:
        warn.append("Is kamre ka daam abhi nahi diya: quote mein khaali rahega.")
    return {"room": view, "warnings": warn, "say": f"{view['number']} {view['name']} save." + (" " + " ".join(warn) if warn else "")}


def rooms(tenant: str) -> list[dict]:
    with session() as s:
        return [_room_view(r) for r in s.scalars(select(HsRoom).where(HsRoom.tenant_id == tenant).order_by(HsRoom.number)).all()]


# ---------------------------------------------------------------- guests
_GUEST_KEYS = ("email", "country", "city", "no_messages", "notes")


def _guest_view(g: HsGuest, full: bool = False) -> dict:
    fc = _j(g.form_c, {})
    out = {"id": g.id, "number": g.number, "name": g.name, "phone": g.phone, "email": g.email, "country": g.country, "city": g.city,
           "foreign": _foreign(g), "ids": [{k: x.get(k) for k in ("kind", "ref", "masked")} for x in _j(g.ids, [])],
           "no_messages": g.no_messages, "stays": g.stays, "forgotten": g.forgotten}
    if full:
        out["form_c"] = {k: fc.get(k, "") for k, _ in R.FORM_C_FIELDS}
        out["notes"] = g.notes
    return out


def _foreign(g: HsGuest) -> bool:
    c = (g.country or "IN").strip().upper()
    return c not in ("IN", "IND", "INDIA", "BHARAT", "")


def _guest(s, tenant: str, ref: str) -> HsGuest:
    ref = str(ref or "").strip()
    g = s.get(HsGuest, ref)
    if g and g.tenant_id == tenant:
        return g
    low = ref.lower()
    for x in s.scalars(select(HsGuest).where(HsGuest.tenant_id == tenant)).all():
        if low and (x.number.lower() == low or (x.phone and x.phone == R.phone_any(ref)) or x.name.lower() == low):
            return x
    raise StayError(f"Mehmaan '{ref}' nahi mila.")


def _lock_id(tenant: str, kind: str, value: str, who: str) -> dict:
    from .. import idvault
    try:
        v = idvault.save(tenant, kind, value, f"mehmaan {who}", "Homestay guest")
    except Exception as e:
        raise StayError(f"{kind} number sahi nahi: {e}")
    return {"kind": kind, "ref": v["ref"], "masked": v["masked"], "rid": v["id"]}


def save_guest(tenant: str, guest: str = "", name: str = "", phone: str = "", aadhaar: str = "", passport: str = "", visa: str = "",
               id_kind: str = "", id_number: str = "", form_c: dict | None = None, **kw: Any) -> dict:
    """A guest. Aadhaar / passport / visa / other ID numbers go straight into her Pehchaan Locker: only {id:...} + masked kept."""
    with _LOCK, session() as s:
        if guest:
            g = _guest(s, tenant, guest)
        else:
            if not name.strip():
                raise StayError("Mehmaan ka naam chahiye.")
            p = R.phone_any(phone)
            if phone and not p:
                raise StayError("Phone sahi nahi (10 ank, ya videshi +desh code).")
            g = s.scalars(select(HsGuest).where(HsGuest.tenant_id == tenant, HsGuest.phone == p)).first() if p else None
            if g is None:
                g = HsGuest(tenant_id=tenant, number=f"G-{_next(s, tenant, 'guest'):03d}", ids="[]", form_c="{}", stays=0, country="IN")
                s.add(g)
        if name:
            g.name = _clean(name, 160)
        if phone:
            p = R.phone_any(phone)
            if not p:
                raise StayError("Phone sahi nahi (10 ank, ya videshi +desh code).")
            g.phone = p
        for k in _GUEST_KEYS:
            if k in kw and kw[k] is not None:
                setattr(g, k, bool(kw[k]) if k == "no_messages" else _clean(kw[k], 400))
        if form_c:
            fc = _j(g.form_c, {})
            for k, _ in R.FORM_C_FIELDS:
                if k in form_c and k not in ("passport_ref", "visa_ref"):
                    fc[k] = _clean(form_c[k], 200)
            g.form_c = _dump(fc)
        s.flush()
        gid, num = g.id, g.number
    jobs = [(k, v) for k, v in (("aadhaar", aadhaar), ("passport", passport), ("other", visa), (id_kind or "other", id_number)) if v]
    for kind, value in jobs:
        rec = _lock_id(tenant, kind, value, num)
        with _LOCK, session() as s:
            g = s.get(HsGuest, gid)
            ids = [x for x in _j(g.ids, []) if x.get("ref") != rec["ref"]]
            ids.append({**rec, "label": "visa" if value == visa else kind})
            g.ids = _dump(ids)
            fc = _j(g.form_c, {})
            if value == passport:
                fc["passport_ref"] = f"{rec['ref']} ({rec['masked']})"
            if value == visa:
                fc["visa_ref"] = f"{rec['ref']} ({rec['masked']})"
            g.form_c = _dump(fc)
    with session() as s:
        view = _guest_view(s.get(HsGuest, gid), True)
    say = f"{view['number']} {view['name']} save."
    if jobs:
        say += " ID number Pehchaan Locker mein (yahan sirf masked)."
    return {"guest": view, "say": say}


def guests(tenant: str, q: str = "") -> list[dict]:
    low = (q or "").lower()
    with session() as s:
        rows = s.scalars(select(HsGuest).where(HsGuest.tenant_id == tenant).order_by(HsGuest.created_at.desc())).all()
        return [_guest_view(g) for g in rows if not low or low in g.name.lower() or low in g.phone or low in g.number.lower()][:200]


# ---------------------------------------------------------------- calendar
def _is_live(b: HsBooking, at: datetime) -> bool:
    if b.status not in LIVE:
        return False
    if b.status == "hold" and b.hold_until and _aware(b.hold_until) < at:
        return False
    return True


def _clashes(s, tenant: str, room_ids: list[str], ci: date, co: date, exclude: str = "") -> list[HsBooking]:
    at = clock()
    out = []
    for b in s.scalars(select(HsBooking).where(HsBooking.tenant_id == tenant, HsBooking.status.in_(LIVE))).all():
        if b.id == exclude or not _is_live(b, at):
            continue
        if not set(_j(b.rooms, [])) & set(room_ids):
            continue
        bi, bo = R.parse_date(b.check_in), R.parse_date(b.check_out)
        if bi and bo and R.overlaps(ci, co, bi, bo):
            out.append(b)
    return out


def _clash_text(s, clashes: list[HsBooking]) -> str:
    parts = []
    for b in clashes[:4]:
        names = ", ".join(_room_names(s, b))
        parts.append(f"{b.number} ({R.SOURCE_LABEL.get(b.source, b.source)}, {names}, {b.check_in} se {b.check_out})")
    return "; ".join(parts)


def _room_names(s, b: HsBooking) -> list[str]:
    out = []
    for rid in _j(b.rooms, []):
        r = s.get(HsRoom, rid)
        out.append(r.name or r.number if r else "?")
    return out


def availability(tenant: str, check_in: str, check_out: str) -> dict:
    ci, co = _dates(tenant, check_in, check_out)
    with session() as s:
        free, busy = [], []
        for r in s.scalars(select(HsRoom).where(HsRoom.tenant_id == tenant, HsRoom.active.is_(True)).order_by(HsRoom.number)).all():
            c = _clashes(s, tenant, [r.id], ci, co)
            (busy if c else free).append({**_room_view(r), "taken_by": [b.number for b in c]})
    say = (f"{ci} se {co}: khaali " + (", ".join(x["name"] or x["number"] for x in free) or "koi nahi") + ".")
    return {"check_in": ci.isoformat(), "check_out": co.isoformat(), "free": free, "busy": busy, "say": say}


def calendar(tenant: str, start: str = "", days: int = 31) -> dict:
    st = _date(start, tenant) or today(tenant)
    days = max(1, min(120, int(days or 31)))
    end = st + timedelta(days=days)
    at = clock()
    with session() as s:
        rms = s.scalars(select(HsRoom).where(HsRoom.tenant_id == tenant, HsRoom.active.is_(True)).order_by(HsRoom.number)).all()
        grid = {r.id: [""] * days for r in rms}
        for b in s.scalars(select(HsBooking).where(HsBooking.tenant_id == tenant, HsBooking.status.in_(LIVE + ("checked_out",)))).all():
            if b.status != "checked_out" and not _is_live(b, at):
                continue
            bi, bo = R.parse_date(b.check_in), R.parse_date(b.check_out)
            if not bi or not bo or bo <= st or bi >= end:
                continue
            for rid in _j(b.rooms, []):
                if rid not in grid:
                    continue
                for i in range(days):
                    d = st + timedelta(days=i)
                    if bi <= d < bo:
                        grid[rid][i] = f"{b.number}|{b.status}|{b.source}"
        return {"start": st.isoformat(), "days": days,
                "rooms": [{"id": r.id, "number": r.number, "name": r.name, "nights": grid[r.id]} for r in rms]}


def _dates(tenant: str, check_in, check_out, nights: int = 0) -> tuple[date, date]:
    ci = _date(check_in, tenant)
    co = _date(check_out, tenant) if check_out else (ci + timedelta(days=int(nights)) if ci and nights else None)
    if not ci or not co:
        raise StayError("Check-in aur check-out ki taarikh chahiye.")
    if co <= ci:
        raise StayError("Check-out, check-in ke baad ho.")
    if (co - ci).days > 60:
        raise StayError("60 raat se lambi booking yahan nahi (lambe kiraye ke liye Property manager Sahayak).")
    return ci, co


# ---------------------------------------------------------------- bookings
def _menu(st: HsSettings) -> dict:
    return _j(st.menu, {})


def _quote_for(s, st: HsSettings, b: HsBooking) -> dict:
    rms = [_room_view(s.get(HsRoom, rid)) for rid in _j(b.rooms, []) if s.get(HsRoom, rid)]
    ci, co = R.parse_date(b.check_in), R.parse_date(b.check_out)
    q = R.quote(rms, ci, co, b.adults, b.children, _j(b.addons, []), _menu(st), st.gstin, st.count_children)
    top = max([x["rate"] for x in q["lines"] if x["kind"] == "room"] or [0])
    q["gst_note"] = R.gst_note(st.gstin, top, b.source not in ("direct", "block"))
    return q


def _booking_view(s, b: HsBooking, full: bool = False) -> dict:
    g = s.get(HsGuest, b.guest_id) if b.guest_id else None
    q = _j(b.quote, {})
    due = _r2(b.total - b.paid) if b.total else 0.0
    out = {"id": b.id, "number": b.number, "kind": b.kind, "status": b.status, "status_label": STATUS_LABEL.get(b.status, b.status),
           "source": b.source, "source_label": R.SOURCE_LABEL.get(b.source, b.source), "ota_ref": b.ota_ref,
           "check_in": b.check_in, "check_out": b.check_out, "nights": (R.parse_date(b.check_out) - R.parse_date(b.check_in)).days
           if b.check_in and b.check_out else 0, "rooms": _room_names(s, b), "room_ids": _j(b.rooms, []), "adults": b.adults,
           "children": b.children, "guest": _guest_view(g) if g else None, "total": b.total, "advance": b.advance, "paid": b.paid,
           "due": max(0.0, due), "refund_due": b.refund_due, "refunded": b.refunded, "missing": q.get("missing", []),
           "hold_until": _aware(b.hold_until).isoformat(timespec="minutes") if b.hold_until and b.status == "hold" else "",
           "checklist": _j(b.checklist, {}), "notes": b.notes}
    if full:
        out.update({"quote": q, "addons": _j(b.addons, []), "log": _j(b.log, []),
                    "payments": [{"id": p.id, "kind": p.kind, "amount": p.amount, "on": p.on, "mode": p.mode, "ref": p.ref, "void": p.void}
                                 for p in s.scalars(select(HsPayment).where(HsPayment.booking_id == b.id)).all()],
                    "tasks": [_task_view(s, t) for t in s.scalars(select(HsTask).where(HsTask.booking_id == b.id)).all()],
                    "cards": [_card_view(c) for c in s.scalars(select(HsCard).where(HsCard.target == b.id)).all()]})
    return out


def _booking(s, tenant: str, ref: str) -> HsBooking:
    ref = str(ref or "").strip()
    b = s.get(HsBooking, ref)
    if b and b.tenant_id == tenant:
        return b
    for x in s.scalars(select(HsBooking).where(HsBooking.tenant_id == tenant)).all():
        if ref and (x.number.lower() == ref.lower() or (x.ota_ref and x.ota_ref.upper() == ref.upper())):
            return x
    raise StayError(f"Booking '{ref}' nahi mili.")


def _room_ids(s, tenant: str, refs) -> list[str]:
    if isinstance(refs, str):
        refs = [x for x in re.split(r"[,+&]| aur | and ", refs) if x.strip()]
    ids = []
    for x in refs or []:
        r = _room(s, tenant, str(x))
        if not r.active:
            raise StayError(f"{r.name or r.number} abhi band (inactive) hai.")
        if r.id not in ids:
            ids.append(r.id)
    if not ids:
        raise StayError("Kaunsa kamra? (room)")
    return ids


def new_booking(tenant: str, rooms_ref, check_in, check_out="", guest: str = "", name: str = "", phone: str = "", adults: int = 2,
                children: int = 0, addons: list | None = None, source: str = "direct", ota_ref: str = "", total=None, advance=None,
                notes: str = "", nights: int = 0, actor: str = "owner", conv: str = "", ical_uid: str = "", kind: str = "stay",
                status: str = "") -> dict:
    """A stay or a block. Any night already taken in any of these rooms = REFUSED (no double booking, whatever the source)."""
    ci, co = _dates(tenant, check_in, check_out, nights)
    if ci < today(tenant) - timedelta(days=1) and source == "direct" and kind == "stay":
        raise StayError("Peechhe ki taarikh ki nayi booking nahi.")
    gid = ""
    if kind == "stay" and (guest or name):
        if guest:
            with session() as s:
                gid = _guest(s, tenant, guest).id
        else:
            gid = save_guest(tenant, name=name, phone=phone)["guest"]["id"]
    with _LOCK, session() as s:
        st = _st(s, tenant)
        ids = _room_ids(s, tenant, rooms_ref)
        clash = _clashes(s, tenant, ids, ci, co)
        if clash:
            raise StayError(f"DOUBLE BOOKING mana: yeh raatein pehle se li hui hain - {_clash_text(s, clash)}.")
        if kind == "stay":
            cap = sum(s.get(HsRoom, i).max_guests for i in ids)
            if int(adults or 0) + int(children or 0) > cap:
                raise StayError(f"{int(adults or 0) + int(children or 0)} log, in kamron mein {cap} tak jagah.")
        src = source if source in R.SOURCE_LABEL else "other"
        b = HsBooking(tenant_id=tenant, kind=kind, rooms=_dump(ids), guest_id=gid, source=src if kind == "stay" else (src if src != "direct" else "block"),
                      ota_ref=_clean(ota_ref, 40).upper(), ical_uid=ical_uid[:200], check_in=ci.isoformat(), check_out=co.isoformat(),
                      adults=max(0, int(adults or 0)), children=max(0, int(children or 0)), addons=_dump(_clean_addons(addons)),
                      notes=_clean(notes, 1000))
        b.number = f"{'B' if kind == 'stay' else 'K'}-{_next(s, tenant, 'booking' if kind == 'stay' else 'block'):04d}"
        if kind == "block":
            b.status = "blocked"
        elif status:
            b.status = status
        elif src == "direct":
            b.status = "hold"
            b.hold_until = clock() + timedelta(hours=st.hold_hours or 24)
        else:
            b.status = "confirmed"                       # the OTA already confirmed it (her mail / file)
        s.add(b)
        s.flush()
        if kind == "stay":
            q = _quote_for(s, st, b)
            b.quote = _dump(q)
            if total is not None and R.money(total) > 0:
                b.total = R.money(total)                 # her number / the OTA payout in her mail
            elif not q["missing"] and src == "direct":
                b.total = q["total"]
            if advance is not None and R.money(advance) > 0:
                b.advance = R.money(advance)
            elif src == "direct" and b.total and st.advance_pct:
                b.advance = round(b.total * st.advance_pct / 100)
        _log(b, f"Bani ({R.SOURCE_LABEL.get(b.source, b.source)}) - {actor_name(tenant, actor)}")
        view = _booking_view(s, b, True)
    out = {"booking": view}
    if kind == "block":
        out["say"] = f"{view['number']}: {', '.join(view['rooms'])} {view['check_in']} se {view['check_out']} band."
        return out
    say = f"{view['number']}: {', '.join(view['rooms'])}, {view['check_in']} se {view['check_out']} ({view['nights']} raat)"
    say += f", {view['status_label']}."
    if view["total"]:
        say += f" Kul {_rs(view['total'])}" + (f", advance {_rs(view['advance'])}" if view["advance"] else "") + "."
    if view["missing"] and not view["total"]:
        say += " Daam baaki: " + ", ".join(view["missing"][:3]) + "."
    if b.source == "direct" and gid:
        try:
            c = draft_message(tenant, view["id"], "confirmation", actor=actor, conv=conv)
            out["card"] = c["card"]
            say += " Confirmation ka message card taiyaar: aapke tap se jaayega, tabhi booking pakki."
        except StayError as e:
            say += f" (Confirmation abhi nahi: {e})"
    out["say"] = say
    _publish(tenant, "homestay_booking", {"booking": view, "say": say}, conv)
    return out


def _clean_addons(addons) -> list[dict]:
    out = []
    for a in addons or []:
        if isinstance(a, str):
            m = re.match(r"\s*(.+?)\s*(?:x\s*(\d+))?\s*$", a)
            a = {"item": m.group(1), "qty": int(m.group(2) or 0)} if m else {"item": a}
        if isinstance(a, dict) and str(a.get("item") or "").strip():
            out.append({"item": _clean(a["item"], 40).lower(), "qty": max(0.0, R.money(a.get("qty"))), "per": str(a.get("per") or "")})
    return out[:20]


_UPD = ("check_in", "check_out", "rooms", "adults", "children", "addons", "notes", "total", "advance")


def update_booking(tenant: str, booking: str, actor: str = "owner", **kw: Any) -> dict:
    with _LOCK, session() as s:
        st = _st(s, tenant)
        b = _booking(s, tenant, booking)
        if b.status not in ("hold", "confirmed", "blocked", "checked_in"):
            raise StayError(f"{b.number} {STATUS_LABEL.get(b.status, b.status)} hai; badal nahi sakte.")
        ci = _date(kw.get("check_in"), tenant) if kw.get("check_in") else R.parse_date(b.check_in)
        co = _date(kw.get("check_out"), tenant) if kw.get("check_out") else R.parse_date(b.check_out)
        if not ci or not co or co <= ci:
            raise StayError("Taarikh sahi nahi.")
        ids = _room_ids(s, tenant, kw["rooms"]) if kw.get("rooms") else _j(b.rooms, [])
        clash = _clashes(s, tenant, ids, ci, co, exclude=b.id)
        if clash:
            raise StayError(f"DOUBLE BOOKING mana: {_clash_text(s, clash)}.")
        b.check_in, b.check_out, b.rooms = ci.isoformat(), co.isoformat(), _dump(ids)
        for k in ("adults", "children"):
            if kw.get(k) is not None:
                setattr(b, k, max(0, int(R.money(kw[k]))))
        if kw.get("addons") is not None:
            b.addons = _dump(_clean_addons(kw["addons"]))
        if kw.get("notes") is not None:
            b.notes = _clean(kw["notes"], 1000)
        if b.kind == "stay":
            q = _quote_for(s, st, b)
            b.quote = _dump(q)
            money_set = False
            if kw.get("total") is not None:
                if not is_owner(actor):
                    raise StayError("Daam sirf owner tay karti hain.")
                b.total, money_set = R.money(kw["total"]), True
            elif b.source == "direct" and not q["missing"]:
                b.total = q["total"]
            if kw.get("advance") is not None:
                if not is_owner(actor):
                    raise StayError("Advance sirf owner tay karti hain.")
                b.advance = R.money(kw["advance"])
            elif b.source == "direct" and b.total and st.advance_pct and not money_set:
                b.advance = round(b.total * st.advance_pct / 100)
        _log(b, f"Badli - {actor_name(tenant, actor)}")
        view = _booking_view(s, b, True)
    return {"booking": view, "say": f"{view['number']} badli: {view['check_in']} se {view['check_out']}, kul {_rs(view['total']) or 'daam baaki'}."}


def bookings(tenant: str, status: str = "", when: str = "") -> list[dict]:
    t = today(tenant)
    with session() as s:
        rows = s.scalars(select(HsBooking).where(HsBooking.tenant_id == tenant, HsBooking.kind == "stay")
                         .order_by(HsBooking.check_in)).all()
        out = []
        for b in rows:
            if status and b.status != status:
                continue
            bo = R.parse_date(b.check_out)
            if when == "upcoming" and (not bo or bo < t or b.status in ("cancelled", "no_show", "checked_out")):
                continue
            if when == "past" and bo and bo >= t:
                continue
            out.append(_booking_view(s, b))
        return out[-300:]


def booking_view(tenant: str, booking: str) -> dict:
    with session() as s:
        return {"booking": _booking_view(s, _booking(s, tenant, booking), True)}


def confirm(tenant: str, booking: str, actor: str = "owner") -> dict:
    """She confirmed it herself (phone / in person): a hold becomes confirmed (still never over another booking)."""
    if not is_owner(actor):
        raise StayError("Booking pakki sirf owner karti hain (ya confirmation message ka tap).")
    with _LOCK, session() as s:
        b = _booking(s, tenant, booking)
        _make_confirmed(s, tenant, b, "Owner ne pakki ki")
        view = _booking_view(s, b)
    return {"booking": view, "say": f"{view['number']} pakki."}


def _make_confirmed(s, tenant: str, b: HsBooking, why: str) -> None:
    if b.status == "confirmed":
        return
    if b.status not in ("hold",):
        raise StayError(f"{b.number} {STATUS_LABEL.get(b.status, b.status)} hai.")
    clash = _clashes(s, tenant, _j(b.rooms, []), R.parse_date(b.check_in), R.parse_date(b.check_out), exclude=b.id)
    if clash:
        raise StayError(f"Hold ke beech kamra kisi aur ne le liya - {_clash_text(s, clash)}. Pakki nahi ho sakti.")
    b.status, b.hold_until = "confirmed", None
    _log(b, why)


def block(tenant: str, rooms_ref, start: str, end: str, note: str = "", actor: str = "owner") -> dict:
    return new_booking(tenant, rooms_ref, start, end, notes=note or "Khud band kiya", actor=actor, kind="block", source="block")


def unblock(tenant: str, booking: str, actor: str = "owner") -> dict:
    with _LOCK, session() as s:
        b = _booking(s, tenant, booking)
        if b.kind != "block":
            raise StayError("Yeh band nahi, mehmaan ki booking hai (cancel ke liye card).")
        b.status = "cancelled"
        _log(b, f"Khola - {actor_name(tenant, actor)}")
        return {"booking": _booking_view(s, b), "say": f"{b.number} khol diya."}


# ---------------------------------------------------------------- check-in / out / Form C
def check_in(tenant: str, booking: str, actor: str = "owner", id_seen: bool = False, guests_count: int | None = None) -> dict:
    with _LOCK, session() as s:
        st = _st(s, tenant)
        b = _booking(s, tenant, booking)
        if b.status not in ("confirmed", "hold"):
            raise StayError(f"{b.number} {STATUS_LABEL.get(b.status, b.status)} hai.")
        if b.status == "hold":
            if not is_owner(actor):
                raise StayError("Booking abhi hold par hai: owner pakki karein.")
            _make_confirmed(s, tenant, b, "Aate hi pakki")
        b.status, b.arrived_at = "checked_in", clock()
        if guests_count is not None:
            b.adults = max(1, int(guests_count))
        g = s.get(HsGuest, b.guest_id) if b.guest_id else None
        chk = _j(b.checklist, {})
        warns = []
        if id_seen:
            chk["id_seen"] = {"on": today(tenant).isoformat(), "by": actor_name(tenant, actor)}
        if g and not _j(g.ids, []) and "id_seen" not in chk:
            warns.append("Mehmaan ka photo ID abhi darj nahi (ID number Pehchaan Locker mein jaata hai).")
        if g and _foreign(g):
            due = clock() + timedelta(hours=24)
            chk["form_c"] = {"due": due.isoformat(timespec="minutes"), "done": False}
            miss = R.form_c_missing(_j(g.form_c, {}) | {"name": g.name, "nationality": _j(g.form_c, {}).get("nationality") or g.country})
            warns.append(f"Videshi mehmaan: Form C (Form-III) 24 ghante mein indianfrro.gov.in par ({due.astimezone(_tz(tenant)).strftime('%d %b %H:%M')} tak). "
                         + (f"Baaki jaankari: {', '.join(miss[:6])}." if miss else "Saari jaankari hai."))
        if st.police_intimation:
            chk.setdefault("police", {"done": False})
            warns.append("Thane ko mehmaan ki jaankari (aapka niyam) - ho jaaye to 'police done'.")
        b.checklist = _dump(chk)
        if g:
            g.stays += 1
        _log(b, f"Check-in - {actor_name(tenant, actor)}")
        view = _booking_view(s, b)
    say = f"{view['number']} check-in ho gaya." + (" " + " ".join(warns) if warns else "")
    if any("Form C" in w for w in warns):
        _publish(tenant, "homestay_alert", {"kind": "form_c", "booking": view["number"], "say": say})
    return {"booking": view, "warnings": warns, "say": say}


def form_c(tenant: str, booking: str) -> dict:
    """The Form C (Form-III) data sheet for HER filing on indianfrro.gov.in. Numbers stay masked: she opens them in her locker."""
    with session() as s:
        b = _booking(s, tenant, booking)
        g = s.get(HsGuest, b.guest_id) if b.guest_id else None
        if not g:
            raise StayError("Is booking mein mehmaan nahi.")
        if not _foreign(g):
            raise StayError("Bharatiya mehmaan: Form C nahi (thane ka guest register niyam alag).")
        st = _st(s, tenant)
        fc = _j(g.form_c, {}) | {"name": g.name, "contact_india": _j(g.form_c, {}).get("contact_india") or g.phone}
        fc.setdefault("nationality", g.country)
        fields = [{"key": k, "label": lab, "value": str(fc.get(k) or ""), "missing": not str(fc.get(k) or "").strip()}
                  for k, lab in R.FORM_C_FIELDS]
        chk = _j(b.checklist, {}).get("form_c") or {}
        return {"booking": b.number, "guest": g.number, "fields": fields, "missing": [f["label"] for f in fields if f["missing"]],
                "stay": {"arrived": _aware(b.arrived_at).isoformat(timespec="minutes") if b.arrived_at else b.check_in,
                         "check_out": b.check_out, "rooms": _room_names(s, b),
                         "host": {"name": st.business or st.host_name, "address": st.address, "city": st.city, "phone": st.phone}},
                "due": chk.get("due", ""), "done": bool(chk.get("done")), "ref": chk.get("ref", ""),
                "steps": ["indianfrro.gov.in > Form C > apna accommodation account (homestay OTP se activate)",
                          "Mehmaan ka passport / visa number Pehchaan Locker mein 'dekho' se kholiye (Hoola khud nahi bharta)",
                          "Arrival 24 ghante ke andar submit; jaate waqt departure bhi darj kijiye",
                          "Mila hua Form C reference yahan 'Form C ho gaya' mein likhiye"],
                "law": "Immigration and Foreigners Act 2025 (1 Sep 2025 se): Form-III / Form C 24 ghante mein; record 1 saal; Rs 50,000 tak har case."}


def form_c_done(tenant: str, booking: str, ref: str = "", stage: str = "arrival", actor: str = "owner") -> dict:
    with _LOCK, session() as s:
        b = _booking(s, tenant, booking)
        chk = _j(b.checklist, {})
        key = "form_c" if stage != "departure" else "form_c_out"
        item = chk.get(key) or {}
        item.update({"done": True, "ref": _clean(ref, 60), "on": clock().isoformat(timespec="minutes"), "by": actor_name(tenant, actor)})
        chk[key] = item
        b.checklist = _dump(chk)
        _log(b, f"Form C {'departure' if key == 'form_c_out' else 'arrival'} darj")
        return {"booking": _booking_view(s, b), "say": f"{b.number}: Form C ({'jaana' if key == 'form_c_out' else 'aana'}) darj."}


def mark_check(tenant: str, booking: str, item: str, done: bool = True, ref: str = "", actor: str = "owner") -> dict:
    if item not in ("id_seen", "police", "house_rules_signed", "keys_given"):
        raise StayError("item: id_seen | police | house_rules_signed | keys_given")
    with _LOCK, session() as s:
        b = _booking(s, tenant, booking)
        chk = _j(b.checklist, {})
        if done:
            chk[item] = {"done": True, "ref": _clean(ref, 60), "on": today(tenant).isoformat(), "by": actor_name(tenant, actor)}
        else:
            chk.pop(item, None)
        b.checklist = _dump(chk)
        return {"booking": _booking_view(s, b), "say": f"{b.number}: {item} {'ho gaya' if done else 'hata diya'}."}


def check_out(tenant: str, booking: str, actor: str = "owner") -> dict:
    """Guest left: turnover tasks for each room (due before the next check-in there); foreign guest -> departure on the FRRO portal."""
    warns = []
    with _LOCK, session() as s:
        st = _st(s, tenant)
        b = _booking(s, tenant, booking)
        if b.status != "checked_in":
            raise StayError(f"{b.number} {STATUS_LABEL.get(b.status, b.status)} hai (pehle check-in).")
        b.status, b.left_at = "checked_out", clock()
        on = today(tenant)
        made = 0
        for rid in _j(b.rooms, []):
            nxt = _next_arrival(s, tenant, rid, on)
            due = f"{nxt.check_in} {st.checkin_time}".strip() if nxt else ""
            for k, what in TURNOVER:
                s.add(HsTask(tenant_id=tenant, booking_id=b.id, room_id=rid, kind=k, what=what, day=on.isoformat(), due=due))
                made += 1
            if nxt and nxt.check_in == on.isoformat():
                warns.append(f"{(s.get(HsRoom, rid).name or '')}: aaj hi agle mehmaan ({nxt.number}) aa rahe hain - safai jaldi.")
        g = s.get(HsGuest, b.guest_id) if b.guest_id else None
        if g and _foreign(g):
            chk = _j(b.checklist, {})
            chk.setdefault("form_c_out", {"done": False})
            b.checklist = _dump(chk)
            warns.append("Videshi mehmaan: FRRO portal par departure darj kijiye.")
        due_amt = _r2(b.total - b.paid) if b.total else 0
        if due_amt > 0:
            warns.append(f"Abhi {_rs(due_amt)} baaki dikh raha hai.")
        _log(b, f"Check-out - {actor_name(tenant, actor)}")
        view = _booking_view(s, b)
    say = f"{view['number']} check-out. {made} safai / laundry kaam bane." + (" " + " ".join(warns) if warns else "")
    _publish(tenant, "homestay_booking", {"booking": view, "say": say})
    return {"booking": view, "tasks": made, "warnings": warns, "say": say}


def _next_arrival(s, tenant: str, room_id: str, on: date) -> HsBooking | None:
    best = None
    for b in s.scalars(select(HsBooking).where(HsBooking.tenant_id == tenant, HsBooking.kind == "stay",
                                               HsBooking.status.in_(("hold", "confirmed")))).all():
        if room_id in _j(b.rooms, []) and b.check_in >= on.isoformat() and (best is None or b.check_in < best.check_in):
            best = b
    return best


def no_show(tenant: str, booking: str, actor: str = "owner") -> dict:
    if not is_owner(actor):
        raise StayError("No-show sirf owner.")
    with _LOCK, session() as s:
        b = _booking(s, tenant, booking)
        if b.status not in ("confirmed", "hold"):
            raise StayError(f"{b.number} {STATUS_LABEL.get(b.status, b.status)} hai.")
        b.status = "no_show"
        _log(b, "Mehmaan nahi aaye")
        return {"booking": _booking_view(s, b), "say": f"{b.number}: no-show. Advance ka faisla aapki policy / aap tay karein."}


# ---------------------------------------------------------------- tasks
def _task_view(s, t: HsTask) -> dict:
    r = s.get(HsRoom, t.room_id) if t.room_id else None
    return {"id": t.id, "room": (r.name or r.number) if r else "", "what": t.what, "kind": t.kind, "day": t.day, "due": t.due,
            "assigned": t.assigned, "status": t.status, "done_by": t.done_by, "note": t.note}


def tasks(tenant: str, status: str = "open") -> list[dict]:
    with session() as s:
        q = select(HsTask).where(HsTask.tenant_id == tenant)
        if status:
            q = q.where(HsTask.status == status)
        return [_task_view(s, t) for t in s.scalars(q.order_by(HsTask.due, HsTask.created_at)).all()][:300]


def task_add(tenant: str, what: str, room: str = "", day: str = "", assigned: str = "") -> dict:
    with _LOCK, session() as s:
        rid = _room(s, tenant, room).id if room else ""
        t = HsTask(tenant_id=tenant, room_id=rid, what=_clean(what, 120), kind="other", day=(_date(day, tenant) or today(tenant)).isoformat(),
                   assigned=_clean(assigned, 80))
        s.add(t)
        s.flush()
        return {"task": _task_view(s, t), "say": "Kaam joda."}


def task_done(tenant: str, task: str, note: str = "", actor: str = "owner", skip: bool = False, assigned: str = "") -> dict:
    with _LOCK, session() as s:
        t = s.get(HsTask, task)
        if t is None or t.tenant_id != tenant:
            raise StayError("Kaam nahi mila.")
        if assigned:
            t.assigned = _clean(assigned, 80)
        else:
            t.status = "skipped" if skip else "done"
            t.done_by = actor_name(tenant, actor)
        if note:
            t.note = _clean(note, 300)
        return {"task": _task_view(s, t), "say": "Kaam " + ("diya" if assigned else ("chhoda" if skip else "ho gaya")) + "."}


# ---------------------------------------------------------------- payments
def pay_link(tenant: str, booking: str, kind: str = "") -> dict:
    with session() as s:
        st = _st(s, tenant)
        b = _booking(s, tenant, booking)
        vpa, vname = _upi(st)
        if not vpa:
            raise StayError("Aapka UPI ID settings mein nahi (upi_id).")
        if not b.total:
            raise StayError("Kul daam abhi tay nahi.")
        due = _r2(b.total - b.paid)
        adv = _r2(b.advance - b.paid) if b.advance else 0
        k = kind or ("advance" if adv > 0 else "balance")
        amt = adv if k == "advance" else due
        if amt <= 0:
            raise StayError("Kuch baaki nahi.")
        link = R.upi_link(vpa, vname, amt, f"{b.number} {k}")
        return {"booking": b.number, "kind": k, "amount": amt, "upi_id": vpa, "link": link,
                "say": f"{b.number}: {k} {_rs(amt)} ka UPI link aapke UPI ID ({vpa}) par. Mehmaan apne app se bharenge."}


def received(tenant: str, booking: str, amount, on: str = "", mode: str = "upi", ref: str = "", kind: str = "", actor: str = "owner") -> dict:
    """ONLY her word: money reached her. Hoola never collects."""
    if not is_owner(actor):
        raise StayError("'Paise mile' sirf owner bata sakti hain.")
    amt = R.money(amount)
    if amt <= 0:
        raise StayError("Raqam chahiye.")
    with _LOCK, session() as s:
        b = _booking(s, tenant, booking)
        if b.kind != "stay":
            raise StayError("Band dino par payment nahi.")
        k = kind or ("advance" if b.paid < b.advance else "balance")
        s.add(HsPayment(tenant_id=tenant, booking_id=b.id, kind=k, amount=amt, on=(_date(on, tenant) or today(tenant)).isoformat(),
                        mode=mode if mode in ("upi", "cash", "bank", "card", "ota", "cheque") else "upi", ref=_clean(ref, 60)))
        b.paid = _r2(b.paid + amt)
        _log(b, f"{_rs(amt)} mila ({mode})")
        view = _booking_view(s, b)
    say = f"{view['number']}: {_rs(amt)} darj. Ab tak {_rs(view['paid'])}" + (f", baaki {_rs(view['due'])}." if view["due"] else ", poora.")
    return {"booking": view, "say": say}


def void_payment(tenant: str, payment: str, actor: str = "owner") -> dict:
    if not is_owner(actor):
        raise StayError("Sirf owner.")
    with _LOCK, session() as s:
        p = s.get(HsPayment, payment)
        if p is None or p.tenant_id != tenant or p.void:
            raise StayError("Payment nahi mili.")
        p.void = True
        b = s.get(HsBooking, p.booking_id)
        if p.kind == "refund":
            b.refunded = _r2(b.refunded - p.amount)
        else:
            b.paid = _r2(b.paid - p.amount)
        _log(b, f"Payment {_rs(p.amount)} hatayi")
        return {"booking": _booking_view(s, b), "say": "Payment hatayi."}


# ---------------------------------------------------------------- cards (messages + money)
def _card_view(c: HsCard) -> dict:
    show = _j(c.show, {})
    return {"id": c.id, "number": c.number, "kind": c.kind, "sub": c.sub, "target": c.target, "show": show, "hash": c.hash,
            "status": c.status, "via": c.via, "reason": c.reason, "asked_by": c.asked_by, "money": c.kind in MONEY_KINDS and
            bool(show.get("amount")), "created_at": _aware(c.created_at).isoformat(timespec="minutes") if c.created_at else ""}


def _basis(s, c_kind: str, target: str) -> dict:
    if not target:
        return {}
    b = s.get(HsBooking, target)
    if not b:
        return {}
    g = s.get(HsGuest, b.guest_id) if b.guest_id else None
    base = {"status": b.status, "in": b.check_in,
            "out": b.check_out, "rooms": b.rooms, "total": b.total, "phone": g.phone if g else ""}
    if c_kind == "message":
        base["status"] = "live" if b.status in ("hold", "confirmed", "checked_in") else b.status
        base["advance"] = b.advance
    if c_kind in ("cancel", "refund"):
        base["paid"], base["refund_due"], base["refunded"] = b.paid, b.refund_due, b.refunded
    return base


def _make_card(s, tenant: str, kind: str, sub: str, target: str, show: dict, actor: str, conv: str) -> tuple[dict, bool]:
    h = _hash({"kind": kind, "sub": sub, "show": show, "basis": _basis(s, kind, target)})
    rows = s.scalars(select(HsCard).where(HsCard.tenant_id == tenant, HsCard.kind == kind, HsCard.sub == sub, HsCard.target == target,
                                          HsCard.status == "waiting")).all()
    for o in rows:
        if o.hash == h:
            return _card_view(o), True
        if target:                                        # a new card for the same thing replaces an older waiting one
            o.status = "stale"
    c = HsCard(tenant_id=tenant, number=f"C-{_next(s, tenant, 'card'):04d}", kind=kind, sub=sub, target=target, show=_dump(show), hash=h,
               asked_by=actor_name(tenant, actor), conv=conv)
    s.add(c)
    s.flush()
    return _card_view(c), False


def _facts(s, st: HsSettings, b: HsBooking, extra: dict | None = None) -> dict:
    g = s.get(HsGuest, b.guest_id) if b.guest_id else None
    vpa, vname = _upi(st)
    adv_due = _r2(b.advance - b.paid) if b.advance else 0
    link = R.upi_link(vpa, vname, adv_due, f"{b.number} advance") if adv_due > 0 else ""
    ci, co = R.parse_date(b.check_in), R.parse_date(b.check_out)
    f = {"guest": g.name if g else "", "business": st.business, "number": b.number,
         "check_in": ci.strftime("%d %b %Y") if ci else "", "check_out": co.strftime("%d %b %Y") if co else "",
         "nights": (co - ci).days if ci and co else "", "rooms_text": ", ".join(_room_names(s, b)),
         "people": b.adults + b.children, "total_text": _rs(b.total) if b.total else "",
         "advance_text": _rs(adv_due) if adv_due > 0 else "", "pay_link": link, "checkin_time": st.checkin_time,
         "checkout_time": st.checkout_time, "policy": R.policy_text(_j(st.policy, [])), "address": st.address, "map": st.map_link,
         "host_phone": st.phone, "instructions": st.checkin_info, "house_rules": st.house_rules, "review_link": st.review_link,
         "ota": R.SOURCE_LABEL.get(b.source) if b.source not in ("direct", "block", "other", "ical") else ""}
    f.update(extra or {})
    return f


def _links(phone: str, text: str) -> dict:
    if not phone:
        return {}
    num = phone.lstrip("+") if phone.startswith("+") else "91" + phone
    return {"whatsapp": f"https://wa.me/{num}?text={quote(text)}", "sms": f"sms:+{num}?body={quote(text)}"}


def draft_message(tenant: str, booking: str, sub: str = "custom", text: str = "", actor: str = "owner", conv: str = "",
                  extra: dict | None = None) -> dict:
    """A message to a guest = a card. Nothing is sent until HER tap."""
    if sub not in MSG_KINDS:
        raise StayError("kind: " + " | ".join(MSG_KINDS))
    with _LOCK, session() as s:
        st = _st(s, tenant)
        b = _booking(s, tenant, booking)
        if b.kind != "stay":
            raise StayError("Band dino ka koi mehmaan nahi.")
        g = s.get(HsGuest, b.guest_id) if b.guest_id else None
        if g is None or g.forgotten:
            raise StayError("Mehmaan ki jaankari nahi.")
        if g.no_messages:
            raise StayError("Mehmaan ne message mana kiya hai.")
        if sub == "confirmation" and b.status not in ("hold", "confirmed"):
            raise StayError(f"{b.number} {STATUS_LABEL.get(b.status, b.status)} hai.")
        if sub == "custom":
            from ..net import policy
            if not text.strip():
                raise StayError("Message ka text chahiye.")
            if policy.secret_found(text) or re.search(r"\b(otp|cvv|password|mpin)\b", text, re.I):
                raise StayError("Message mein OTP / PIN / card jaisi cheez; yeh kabhi nahi bheja jaata.")
        body = text.strip() and sub != "custom" and _clean(text, 3000) or R.message_text(sub, _facts(s, st, b, {"text": _clean(text, 3000), **(extra or {})}))
        show = {"title": f"{b.number} · {g.name}: {sub}", "text": body, "phone": g.phone, "guest": g.name, "booking": b.number,
                "blanks": R.blanks(body), "links": _links(g.phone, body)}
        view, existing = _make_card(s, tenant, "message", sub, b.id, show, actor, conv)
    if not existing:
        say = f"{view['number']}: {sub} message ka draft taiyaar (aapke tap se jaayega)."
        if view["show"]["blanks"]:
            say += " Khaali: " + ", ".join(view["show"]["blanks"]) + " - bharne ke baad hi jaayega."
        _publish(tenant, "homestay_card", {"card": view, "say": say}, conv)
    else:
        say = f"{view['number']} pehle se aapke tap ka intezaar kar raha hai."
    return {"card": view, "status": "needs_tap", "say": say}


def edit_message(tenant: str, card: str, text: str) -> dict:
    from ..net import policy
    if policy.secret_found(text) or re.search(r"\b(otp|cvv|password|mpin)\b", text, re.I):
        raise StayError("Message mein OTP / PIN / card jaisi cheez; yeh kabhi nahi bheja jaata.")
    with _LOCK, session() as s:
        c = s.get(HsCard, card)
        if c is None or c.tenant_id != tenant or c.kind != "message" or c.status != "waiting":
            raise StayError("Draft nahi mila.")
        show = _j(c.show, {})
        show["text"] = _clean(text, 3000)
        show["blanks"] = R.blanks(show["text"])
        show["links"] = _links(show.get("phone", ""), show["text"])
        c.show = _dump(show)
        c.hash = _hash({"kind": c.kind, "sub": c.sub, "show": show, "basis": _basis(s, c.kind, c.target)})
        return {"card": _card_view(c), "say": "Draft badla."}


async def send_message(tenant: str, card: str, via: str = "self", card_hash: str = "", by_tap: bool = False) -> dict:
    """ONLY her tap. via=self: she sends it from her own WhatsApp / SMS (the app opens the link; this marks it sent).
    via=business: her business WhatsApp number, only if the guest wrote to it (Meta's 24 h window, enforced by the inbox).
    A confirmation sent = the booking becomes confirmed (still never over another booking)."""
    if not by_tap:
        raise StayError("Mehmaan ko message sirf aapke tap se jaata hai.")
    with session() as s:
        c = s.get(HsCard, card)
        if c is None or c.tenant_id != tenant or c.kind != "message":
            raise StayError("Message nahi mila.")
        if c.status != "waiting":
            raise StayError(f"Yeh message {c.status} hai.")
        now_hash = _hash({"kind": c.kind, "sub": c.sub, "show": _j(c.show, {}), "basis": _basis(s, c.kind, c.target)})
        if not card_hash or card_hash != c.hash or now_hash != c.hash:
            if now_hash != c.hash:
                c.status = "stale"
            raise StayError("Booking card ke baad badal gayi; naya draft banaiye.")
        show = _j(c.show, {})
        if show.get("blanks") or R.blanks(show.get("text", "")):
            raise StayError("Message mein khaali jagah hai: " + ", ".join(R.blanks(show.get("text", ""))) + ". Pehle bhariye.")
        if not show.get("phone"):
            raise StayError("Mehmaan ka phone nahi.")
        text, phone, sub, target = show["text"], show["phone"], c.sub, c.target
    if via == "business":
        from ..employee import inbox
        from ..employee.models import BizContact
        wa = phone.lstrip("+") if phone.startswith("+") else "91" + phone
        with session() as s:
            bc = s.scalars(select(BizContact).where(BizContact.tenant_id == tenant, BizContact.wa_id == wa)).first()
            bid = bc.id if bc else ""
        if not bid:
            raise StayError("Mehmaan ne business number par kabhi message nahi kiya: apne phone se bhejiye.")
        try:
            await inbox.send(tenant, bid, text, by="owner")
        except inbox.InboxError as e:
            raise StayError(str(e))
    elif via != "self":
        raise StayError("via: self | business")
    with _LOCK, session() as s:
        c = s.get(HsCard, card)
        c.status, c.via, c.decided_at = "sent", via, now()
        b = s.get(HsBooking, target)
        extra = ""
        if sub == "confirmation" and b and b.status == "hold":
            try:
                _make_confirmed(s, tenant, b, "Confirmation bheja (owner ka tap)")
                extra = f" {b.number} ab pakki."
            except StayError as e:
                extra = f" Dhyaan: {e}"
        if b:
            _log(b, f"Message {sub} bheja ({via})")
            if sub == "review":
                chk = _j(b.checklist, {})
                chk["review_asked"] = {"on": today(tenant).isoformat()}
                b.checklist = _dump(chk)
        view = _card_view(c)
    return {"card": view, "say": ("Bhej diya (aapke tap se)." if via == "business" else "Aapke phone se bheja, darj kiya.") + extra}


def drop_card(tenant: str, card: str) -> dict:
    with session() as s:
        c = s.get(HsCard, card)
        if c is None or c.tenant_id != tenant:
            raise StayError("Card nahi mila.")
        if c.status == "waiting":
            c.status = "dropped"
        return {"card": _card_view(c), "say": "Card hataya."}


def cards(tenant: str, status: str = "waiting") -> list[dict]:
    with session() as s:
        q = select(HsCard).where(HsCard.tenant_id == tenant)
        if status:
            q = q.where(HsCard.status == status)
        return [_card_view(c) for c in s.scalars(q.order_by(HsCard.created_at.desc())).all()][:200]


def cancel_request(tenant: str, booking: str, by: str = "guest", reason: str = "", refund=None, actor: str = "owner", conv: str = "") -> dict:
    """Cancelling a stay = a card. Refund from HER written policy on what was paid (or her number); OTA bookings: the OTA refunds."""
    with _LOCK, session() as s:
        st = _st(s, tenant)
        b = _booking(s, tenant, booking)
        if b.kind != "stay" or b.status not in ("hold", "confirmed"):
            raise StayError(f"{b.number} cancel nahi ho sakti ({STATUS_LABEL.get(b.status, b.status)}).")
        ota = b.source not in ("direct",)
        calc = R.refund_for(_j(st.policy, []), b.paid, R.parse_date(b.check_in), today(tenant))
        if ota:
            amt, why = 0.0, f"{R.SOURCE_LABEL.get(b.source, b.source)} booking: cancel aur refund OTA ke page par aap karein; yahan sirf calendar khulega."
        elif refund is not None:
            amt, why = min(R.money(refund), b.paid), f"Aapki tay raqam (policy: {calc['why']})"
        elif calc["refund"] is None:
            if b.paid > 0:
                raise StayError(calc["why"] + " (refund=...)")
            amt, why = 0.0, "Kuch bhara nahi gaya."
        else:
            amt, why = calc["refund"], calc["why"]
        g = s.get(HsGuest, b.guest_id) if b.guest_id else None
        show = {"title": f"{b.number} radd ({'mehmaan ne' if by == 'guest' else 'aapne'})", "guest": g.name if g else "",
                "dates": f"{b.check_in} se {b.check_out}", "rooms": _room_names(s, b), "paid": b.paid, "amount": _r2(amt),
                "amount_text": _rs(amt) if amt else "", "why": why, "reason": _clean(reason, 300), "by": by, "ota": ota,
                "payee": g.name if g else ""}
        view, existing = _make_card(s, tenant, "cancel", "", b.id, show, actor, conv)
    say = f"{view['number']}: {show['title']} - wapas {_rs(amt) if amt else 'kuch nahi'}. {why} Aapke tap ka card bheja."
    if not existing:
        _publish(tenant, "homestay_card", {"card": view, "say": say}, conv)
    return {"card": view, "status": "needs_tap", "say": say}


def spend_request(tenant: str, what: str, amount, vendor: str = "", booking: str = "", actor: str = "owner", conv: str = "") -> dict:
    amt = R.money(amount)
    if amt <= 0:
        raise StayError("Kharche ki raqam chahiye (bill / vendor ka bataya).")
    if not str(what or "").strip():
        raise StayError("Kis cheez ka kharcha?")
    with _LOCK, session() as s:
        bid = _booking(s, tenant, booking).id if booking else ""
        show = {"title": f"Kharcha: {_clean(what, 120)}", "what": _clean(what, 300), "vendor": _clean(vendor, 120), "amount": amt,
                "amount_text": _rs(amt), "payee": _clean(vendor, 120)}
        view, existing = _make_card(s, tenant, "spend", _hash([what, amt, vendor])[:16], bid, show, actor, conv)
    say = f"{view['number']}: {show['title']} {_rs(amt)} - aapki haan ka card."
    if not existing:
        _publish(tenant, "homestay_card", {"card": view, "say": say}, conv)
    return {"card": view, "status": "needs_tap", "say": say}


def card_get(tenant: str, card: str) -> dict | None:
    with session() as s:
        c = s.get(HsCard, card)
        return _card_view(c) if c and c.tenant_id == tenant else None


def challenge(tenant: str, card: str) -> dict:
    """approvekey's message format (kind 'homestay'): the phone signs this card as it is NOW."""
    from .. import approvekey as ak
    c = card_get(tenant, card)
    if not c or c["status"] != "waiting" or c["kind"] not in MONEY_KINDS:
        raise StayError("Yeh card ab baaki nahi hai.")
    nonce = secrets.token_urlsafe(18)
    exp = datetime.now(timezone.utc) + ak.CHALLENGE_TTL
    msg = f"hoola-approve|v1|{tenant}|homestay|{card}|{c['hash']}|{nonce}|{int(exp.timestamp())}"
    with session() as s:
        ch = ak.ApproveChallenge(tenant_id=tenant, kind="homestay", target=card, digest=c["hash"], message=msg, expires_at=exp)
        s.add(ch)
        s.flush()
        chid = ch.id
    show = {"title": c["show"].get("title", "")[:80], "amount": c["show"].get("amount_text", ""), "payee": c["show"].get("payee", "")}
    return {"challenge_id": chid, "message": msg, "show": show, "expires_at": exp.isoformat()}


def _verify_fp(tenant: str, card: str, digest: str, proof: dict | None) -> None:
    from .. import approvekey as ak
    if not proof:
        raise StayError("fingerprint_needed")
    with session() as s:
        ak._settle(s, tenant)
        ok = ak._check(s, tenant, "homestay", card, proof, digest)
    if not ok:
        raise StayError("fingerprint_invalid")


def decide(tenant: str, card: str, yes: bool, card_hash: str = "", reason: str = "", proof: dict | None = None, by_tap: bool = False) -> dict:
    """ONLY her tap in the app (API). Cancel / refund / spend with money need her fingerprint once a phone key is active."""
    if not by_tap:
        raise StayError("Yeh faisla sirf aapke tap se (app ka card).")
    with session() as s:
        c = s.get(HsCard, card)
        if c is None or c.tenant_id != tenant or c.kind not in MONEY_KINDS:
            raise StayError("Card nahi mila.")
        if c.status != "waiting":
            return {"card": _card_view(c), "say": f"{c.number} pehle hi '{c.status}' hai."}
        now_hash = _hash({"kind": c.kind, "sub": c.sub, "show": _j(c.show, {}), "basis": _basis(s, c.kind, c.target)})
        if not card_hash or card_hash != c.hash or now_hash != c.hash:
            if now_hash != c.hash:
                c.status = "stale"
            raise StayError("Card ke baad cheezein badal gayi; naya card banaiye.")
        money = bool(_j(c.show, {}).get("amount"))
    if yes and money:
        from .. import approvekey as ak
        if ak.active_on(tenant):
            _verify_fp(tenant, card, card_hash, proof)
    follow = None
    with _LOCK, session() as s:
        c = s.get(HsCard, card)
        c.status, c.reason, c.decided_at = ("approved" if yes else "rejected"), _clean(reason, 300), now()
        show = _j(c.show, {})
        say = f"{c.number}: {'haan' if yes else 'nahi'}."
        if yes and c.kind == "cancel":
            b = s.get(HsBooking, c.target)
            b.status = "cancelled"
            b.refund_due = _r2(b.refund_due + float(show.get("amount") or 0))
            for t in s.scalars(select(HsTask).where(HsTask.booking_id == b.id, HsTask.status == "open")).all():
                t.status = "skipped"
            _log(b, f"Radd (aapka tap), wapas {_rs(show.get('amount') or 0)}")
            say = f"{c.number}: {b.number} radd, calendar khul gaya."
            if show.get("amount"):
                say += f" {_rs(show['amount'])} wapas aap khud bhejiye, phir 'refund ho gaya'."
            if show.get("ota"):
                say += " OTA par bhi cancel kijiye (Hoola OTA mein login nahi karta)."
            elif b.guest_id:
                follow = (b.id, {"refund_text": show.get("amount_text", "")})
        view = _card_view(c)
    out = {"card": view, "say": say}
    if follow:
        try:
            out["message"] = draft_message(tenant, follow[0], "cancellation", extra=follow[1])["card"]
            out["say"] += " Mehmaan ke liye message draft (aapke tap se)."
        except StayError:
            pass
    return out


def refund_done(tenant: str, booking: str, amount=None, ref: str = "", actor: str = "owner") -> dict:
    if not is_owner(actor):
        raise StayError("'Refund ho gaya' sirf owner.")
    with _LOCK, session() as s:
        b = _booking(s, tenant, booking)
        left = _r2(b.refund_due - b.refunded)
        if left <= 0:
            raise StayError("Koi refund baaki nahi (pehle cancel card par aapki haan).")
        amt = min(R.money(amount), left) if amount is not None else left
        s.add(HsPayment(tenant_id=tenant, booking_id=b.id, kind="refund", amount=amt, on=today(tenant).isoformat(), mode="upi", ref=_clean(ref, 60)))
        b.refunded = _r2(b.refunded + amt)
        _log(b, f"Refund {_rs(amt)} bheja (aapne)")
        return {"booking": _booking_view(s, b), "say": f"{b.number}: refund {_rs(amt)} darj."}


def spend_paid(tenant: str, card: str, ref: str = "", actor: str = "owner") -> dict:
    if not is_owner(actor):
        raise StayError("Sirf owner.")
    with _LOCK, session() as s:
        c = s.get(HsCard, card)
        if c is None or c.tenant_id != tenant or c.kind != "spend":
            raise StayError("Kharcha card nahi mila.")
        if c.status != "approved":
            raise StayError("Pehle card par aapki haan chahiye.")
        c.status, c.reason = "paid", (c.reason + " " + _clean(ref, 60)).strip()
        return {"card": _card_view(c), "say": f"{c.number}: kharcha diya darj."}


# ---------------------------------------------------------------- OTA mail + iCal file (HER data, never a login)
def _room_from_text(s, tenant: str, text: str) -> list[str]:
    low = (text or "").lower()
    rows = s.scalars(select(HsRoom).where(HsRoom.tenant_id == tenant, HsRoom.active.is_(True))).all()
    hit = [r.id for r in rows if (r.name and r.name.lower() in low) or any(n.lower() in low for n in _j(r.ota_names, []) if n)]
    if hit:
        return hit
    return [rows[0].id] if len(rows) == 1 else []


def ota_email(tenant: str, text: str, room: str = "", actor: str = "owner", conv: str = "") -> dict:
    """Her pasted OTA mail (data). New booking -> calendar (refused on a clash, with an alert); a cancellation mail frees the dates."""
    p = R.parse_ota_email(text, today(tenant))
    if p["cancelled"] and p["ref"]:
        with _LOCK, session() as s:
            try:
                b = _booking(s, tenant, p["ref"])
            except StayError:
                raise StayError(f"Cancel mail: {p['ref']} wali booking yahan nahi mili.")
            if b.status in ("hold", "confirmed"):
                b.status = "cancelled"
                _log(b, "OTA mail: cancel (OTA ne radd ki)")
            view = _booking_view(s, b)
        return {"parsed": p, "booking": view, "say": f"{view['number']}: {view['source_label']} ne cancel kiya, calendar khula. Refund OTA ka kaam."}
    if p["missing"]:
        return {"parsed": p, "status": "need_more", "say": "Mail se " + ", ".join(p["missing"]) + " nahi mila. Taarikh bata dijiye."}
    with session() as s:
        ids = [_room(s, tenant, room).id] if room else _room_from_text(s, tenant, text)
        existing = None
        if p["ref"]:
            existing = s.scalars(select(HsBooking).where(HsBooking.tenant_id == tenant, HsBooking.ota_ref == p["ref"])).first()
    if existing is not None:
        r = update_booking(tenant, existing.id, actor="owner", check_in=p["check_in"], check_out=p["check_out"])
        return {"parsed": p, **r, "say": f"{r['booking']['number']} ({p['ref']}) pehle se thi: taarikh mila di."}
    if not ids:
        return {"parsed": p, "status": "need_room", "say": "Kaunsa kamra? Mail mein kamre ka naam nahi mila (room=...)."}
    try:
        return {"parsed": p, **new_booking(tenant, ids, p["check_in"], p["check_out"], name=p["guest_name"] or "OTA mehmaan",
                                           phone=p["phone"], adults=p["adults"] or 1, children=p["children"], source=p["source"],
                                           ota_ref=p["ref"], total=p["amount"] or None, actor=actor, conv=conv)}
    except StayError as e:
        if "DOUBLE BOOKING" in str(e):
            say = (f"KHATRA: {R.SOURCE_LABEL.get(p['source'], p['source'])} ki booking {p['ref']} ({p['check_in']} se {p['check_out']}) "
                   f"ek pehle se bhari raat par aa gayi. Hoola ne darj nahi kiya. {e} Ek booking OTA / mehmaan se baat karke badliye.")
            _publish(tenant, "homestay_alert", {"kind": "clash", "say": say, "parsed": p}, conv)
            return {"parsed": p, "status": "clash", "say": say}
        raise


def ical_import(tenant: str, text: str, room: str, source: str = "", actor: str = "owner", conv: str = "") -> dict:
    """Her exported .ics (Airbnb / Booking.com / any). The file is a full snapshot: new events -> calendar, moved ones updated,
    future events no longer in the file -> freed. Clashes are refused and listed (never two bookings on one night)."""
    p = R.parse_ics(text)
    if not p["events"]:
        raise StayError("File mein koi booking / band din nahi mila (yeh .ics calendar file hai?).")
    src = source if source in R.SOURCE_LABEL else (p["source"] or "ical")
    made, updated, removed, clashes = [], [], [], []
    with session() as s:
        rid = _room(s, tenant, room).id
    seen = set()
    for e in p["events"]:
        uid = f"{src}:{rid}:{e['uid']}"[:200]
        seen.add(uid)
        with session() as s:
            ex = s.scalars(select(HsBooking).where(HsBooking.tenant_id == tenant, HsBooking.ical_uid == uid)).first()
            ex_id = ex.id if ex else ""
            same = ex is not None and ex.check_in == e["check_in"] and ex.check_out == e["check_out"]
            if ex is not None and ex.status not in LIVE:
                same = True
        if R.parse_date(e["check_out"]) < today(tenant):
            continue
        try:
            if ex_id and not same:
                update_booking(tenant, ex_id, check_in=e["check_in"], check_out=e["check_out"])
                updated.append(e["uid"])
            elif not ex_id:
                r = new_booking(tenant, [rid], e["check_in"], e["check_out"], name="", source=src, ota_ref=e["ref"], actor=actor,
                                ical_uid=uid, kind="stay" if e["reserved"] else "block", notes=e["summary"],
                                status="confirmed" if e["reserved"] else "")
                made.append(r["booking"]["number"])
        except StayError as ex2:
            clashes.append({"event": f"{e['check_in']} se {e['check_out']}", "why": str(ex2)})
    with _LOCK, session() as s:
        for b in s.scalars(select(HsBooking).where(HsBooking.tenant_id == tenant, HsBooking.ical_uid.like(f"{src}:{rid}:%"),
                                                   HsBooking.status.in_(("confirmed", "blocked")))).all():
            if b.ical_uid not in seen and b.check_out >= today(tenant).isoformat():
                b.status = "cancelled"
                _log(b, "Calendar file mein ab nahi")
                removed.append(b.number)
    say = f"{R.SOURCE_LABEL.get(src, src)} file: {len(made)} nayi, {len(updated)} badli, {len(removed)} hatayi."
    if clashes:
        say += f" {len(clashes)} TAKRAV (darj nahi kiye): " + "; ".join(c["event"] for c in clashes[:4]) + "."
        _publish(tenant, "homestay_alert", {"kind": "clash", "say": say, "clashes": clashes[:10]}, conv)
    return {"made": made, "updated": updated, "removed": removed, "clashes": clashes, "say": say}


def file_text(tenant: str, file_id: str, limit: int = 2_000_000) -> str:
    """Text of a file she sent in chat (her .ics export / saved OTA mail). Read as data."""
    from pathlib import Path
    from ..mailbox import service as ms
    try:
        f = ms._file_row(tenant, file_id)
        data = Path(f.stored_path).read_bytes()
    except Exception as e:
        raise StayError(f"File nahi mili: {e}")
    if len(data) > limit:
        raise StayError("File bahut badi.")
    return data.decode("utf-8", "replace")


def ical_export(tenant: str, room: str = "", token: str = "") -> str:
    """Her own calendar as .ics (no guest names / numbers): she adds this link in the OTA's 'import calendar' page."""
    with session() as s:
        if token:
            st = s.get(HsSettings, tenant)
            if st is None or not _ical_token(st) or not secrets.compare_digest(token, _ical_token(st)):
                raise StayError("not_found")
        rid = _room(s, tenant, room).id if room else ""
        at = clock()
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Hoola//Homestay//EN", "CALSCALE:GREGORIAN"]
        stamp = at.strftime("%Y%m%dT%H%M%SZ")
        for b in s.scalars(select(HsBooking).where(HsBooking.tenant_id == tenant, HsBooking.status.in_(LIVE))).all():
            if not _is_live(b, at) or (rid and rid not in _j(b.rooms, [])):
                continue
            if b.check_out < today(tenant).isoformat():
                continue
            lines += ["BEGIN:VEVENT", f"UID:{b.id}@hoola", f"DTSTAMP:{stamp}",
                      f"DTSTART;VALUE=DATE:{b.check_in.replace('-', '')}", f"DTEND;VALUE=DATE:{b.check_out.replace('-', '')}",
                      "SUMMARY:Not available", "END:VEVENT"]
        lines.append("END:VCALENDAR")
        return "\r\n".join(lines) + "\r\n"


# ---------------------------------------------------------------- registration
def registration(tenant: str) -> dict:
    with session() as s:
        st = _st(s, tenant)
        reg = _j(st.registration, {})
        foreign = any(_foreign(g) for g in s.scalars(select(HsGuest).where(HsGuest.tenant_id == tenant)).all())
        items = R.registration_items(st.state, foreign or bool(reg.get("foreign_guests")), st.serves_food, st.in_flat)
        done = reg.get("done", {})
        for it in items:
            it["done"] = done.get(it["id"]) or None
        info = R.state_info(st.state)
        vt = R.parse_date(reg.get("valid_to"))
        left = (vt - today(tenant)).days if vt else None
        return {"state": info, "number": reg.get("number", ""), "valid_to": reg.get("valid_to", ""), "days_left": left, "items": items,
                "missing": [i["text"] for i in items if i["must"] and not i["done"]]}


def registration_update(tenant: str, number: str = "", valid_to: str = "", item: str = "", done: bool = True, ref: str = "",
                        foreign_guests: bool | None = None) -> dict:
    with _LOCK, session() as s:
        st = _st(s, tenant)
        reg = _j(st.registration, {})
        if number:
            reg["number"] = _clean(number, 60)
        if valid_to:
            d = R.parse_date(valid_to)
            if not d:
                raise StayError("Valid-to taarikh sahi nahi.")
            reg["valid_to"] = d.isoformat()
        if foreign_guests is not None:
            reg["foreign_guests"] = bool(foreign_guests)
        if item:
            dd = reg.setdefault("done", {})
            if done:
                dd[item] = {"on": today(tenant).isoformat(), "ref": _clean(ref, 60)}
            else:
                dd.pop(item, None)
        st.registration = _dump(reg)
    return {"registration": registration(tenant), "say": "Registration ki jaankari save."}


# ---------------------------------------------------------------- reports
def _month_bounds(month: str, tenant: str) -> tuple[date, date]:
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", str(month or ""))
    t = today(tenant)
    y, mo = (int(m.group(1)), int(m.group(2))) if m else (t.year, t.month)
    start = date(y, mo, 1)
    end = date(y + (mo == 12), mo % 12 + 1, 1)
    return start, end


def report(tenant: str, month: str = "") -> dict:
    """Earnings and occupancy for a month: room-nights sold / available, ADR, RevPAR, by source, add-ons, money in, refunds."""
    start, end = _month_bounds(month, tenant)
    days = (end - start).days
    with session() as s:
        rms = s.scalars(select(HsRoom).where(HsRoom.tenant_id == tenant, HsRoom.active.is_(True))).all()
        avail = len(rms) * days
        sold, revenue, addons = 0, 0.0, 0.0
        by_src: dict[str, dict] = {}
        by_room: dict[str, int] = {r.id: 0 for r in rms}
        cancelled = 0
        for b in s.scalars(select(HsBooking).where(HsBooking.tenant_id == tenant, HsBooking.kind == "stay")).all():
            bi, bo = R.parse_date(b.check_in), R.parse_date(b.check_out)
            if not bi or not bo or bo <= start or bi >= end:
                continue
            if b.status in ("cancelled", "no_show"):
                cancelled += b.status == "cancelled"
                continue
            if b.status == "hold" and not _is_live(b, clock()):
                continue
            tot_n = max(1, (bo - bi).days)
            n_in = sum(1 for d in R.nights(bi, bo) if start <= d < end)
            rids = _j(b.rooms, [])
            sold += n_in * len(rids)
            for rid in rids:
                by_room[rid] = by_room.get(rid, 0) + n_in
            share = (b.total or 0) * n_in / tot_n
            revenue += share
            q = _j(b.quote, {})
            addons += sum(x["amount"] for x in q.get("lines", []) if x.get("kind") == "addon") * n_in / tot_n
            d = by_src.setdefault(b.source, {"source": R.SOURCE_LABEL.get(b.source, b.source), "bookings": 0, "nights": 0, "revenue": 0.0})
            d["bookings"] += 1
            d["nights"] += n_in * len(rids)
            d["revenue"] = _r2(d["revenue"] + share)
        pays = [p for p in s.scalars(select(HsPayment).where(HsPayment.tenant_id == tenant, HsPayment.void.is_(False))).all()
                if start.isoformat() <= p.on < end.isoformat()]
        money_in = _r2(sum(p.amount for p in pays if p.kind != "refund"))
        refunds = _r2(sum(p.amount for p in pays if p.kind == "refund"))
        spends = _r2(sum(float(_j(c.show, {}).get("amount") or 0) for c in s.scalars(select(HsCard).where(
            HsCard.tenant_id == tenant, HsCard.kind == "spend", HsCard.status.in_(("approved", "paid")))).all()
            if c.decided_at and start <= _aware(c.decided_at).astimezone(_tz(tenant)).date() < end))
        room_rows = [{"room": r.name or r.number, "nights": by_room.get(r.id, 0), "occupancy": round(100 * by_room.get(r.id, 0) / days, 1)}
                     for r in rms]
    occ = round(100 * sold / avail, 1) if avail else 0.0
    adr = round(revenue / sold, 2) if sold else 0.0
    revpar = round(revenue / avail, 2) if avail else 0.0
    say = (f"{start.strftime('%b %Y')}: {sold}/{avail} room-raat bhari ({occ}%), kamaai {_rs(revenue)} (ADR {_rs(adr)}, RevPAR {_rs(revpar)}). "
           f"Paise aaye {_rs(money_in)}, refund {_rs(refunds)}, kharcha {_rs(spends)}.")
    return {"month": start.strftime("%Y-%m"), "rooms": len(room_rows), "available": avail, "sold": sold, "occupancy": occ,
            "revenue": _r2(revenue), "adr": adr, "revpar": revpar, "addons": _r2(addons), "by_source": list(by_src.values()),
            "by_room": room_rows, "money_in": money_in, "refunds": refunds, "spends": spends, "cancelled": cancelled,
            "note": "OTA booking ka 'kul' = aapke mail mein likha payout (commission ke baad) - wahi gina.", "say": say}


def register_file(tenant: str, month: str = "", conv: str = "") -> dict:
    """Guest register + bookings + month report as Excel (her own records / thane ke liye; ID numbers never in it, only masked)."""
    from .. import chatfiles, officegen
    rep = report(tenant, month)
    with session() as s:
        rows = [["Booking", "Mehmaan", "Phone", "Desh", "ID (masked)", "Check-in", "Check-out", "Kamre", "Log", "Source", "Status", "Kul", "Mila",
                 "Form C"]]
        for b in s.scalars(select(HsBooking).where(HsBooking.tenant_id == tenant, HsBooking.kind == "stay").order_by(HsBooking.check_in)).all():
            g = s.get(HsGuest, b.guest_id) if b.guest_id else None
            fc = _j(b.checklist, {}).get("form_c") or {}
            rows.append([b.number, g.name if g else "", g.phone if g else "", g.country if g else "",
                         ", ".join(f"{x.get('kind')} {x.get('masked')}" for x in _j(g.ids, [])) if g else "", b.check_in, b.check_out,
                         ", ".join(_room_names(s, b)), b.adults + b.children, R.SOURCE_LABEL.get(b.source, b.source),
                         STATUS_LABEL.get(b.status, b.status), b.total, b.paid, ("ho gaya " + fc.get("ref", "")) if fc.get("done") else ("baaki" if fc else "")])
    sheets = {"Register": rows,
              "Mahina": [["Cheez", "Value"], ["Mahina", rep["month"]], ["Room-raat bhari", rep["sold"]], ["Room-raat kul", rep["available"]],
                         ["Occupancy %", rep["occupancy"]], ["Kamaai", rep["revenue"]], ["ADR", rep["adr"]], ["RevPAR", rep["revpar"]],
                         ["Paise aaye", rep["money_in"]], ["Refund", rep["refunds"]], ["Kharcha", rep["spends"]]],
              "Source": [["Source", "Bookings", "Raat", "Kamaai"]] + [[x["source"], x["bookings"], x["nights"], x["revenue"]] for x in rep["by_source"]]}
    data = officegen.make_xlsx("Homestay register", sheets)
    f = chatfiles.store(tenant, f"Homestay_register_{rep['month']}.xlsx", data,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    _publish(tenant, "pc_file", {**f, "source": "homestay", "title": "Homestay register"}, conv)
    return {"file": f, "say": "Guest register + mahine ka hisaab Excel mein."}


# ---------------------------------------------------------------- DPDP forget
def forget(tenant: str, guest: str, actor: str = "owner") -> dict:
    """DPDP: a guest's personal details go away after the stay. Foreign guests: only 1 year after the last departure
    (Immigration and Foreigners Rules keep accommodation records 1 year)."""
    if not is_owner(actor):
        raise StayError("Sirf owner.")
    rids = []
    with _LOCK, session() as s:
        g = _guest(s, tenant, guest)
        bks = s.scalars(select(HsBooking).where(HsBooking.tenant_id == tenant, HsBooking.guest_id == g.id)).all()
        if any(b.status in ("hold", "confirmed", "checked_in") for b in bks):
            raise StayError("Is mehmaan ki booking abhi chal rahi / aane wali hai.")
        last = max((R.parse_date(b.check_out) for b in bks if b.check_out), default=None)
        if _foreign(g) and last and (today(tenant) - last).days < 365:
            raise StayError(f"Videshi mehmaan ka record 1 saal rakhna hai ({(last + timedelta(days=365)).isoformat()} ke baad).")
        rids = [x.get("rid") for x in _j(g.ids, []) if x.get("rid")]
        g.name, g.phone, g.email, g.city, g.ids, g.form_c, g.notes = f"Purana mehmaan {g.number}", "", "", "", "[]", "{}", ""
        g.forgotten = True
        for c in s.scalars(select(HsCard).where(HsCard.tenant_id == tenant, HsCard.kind == "message",
                                                HsCard.target.in_([b.id for b in bks] or ["-"]))).all():
            c.show = _dump({"title": "(mita diya)", "text": ""})
            if c.status == "waiting":
                c.status = "dropped"
        num = g.number
    from .. import idvault
    for rid in rids:
        try:
            idvault.delete(tenant, rid)
        except Exception:
            log.info("idvault delete failed for %s", rid)
    return {"say": f"{num} ki niji jaankari mita di (booking ki taarikh / raqam hisaab ke liye bachi)."}


# ---------------------------------------------------------------- day / overview
def day(tenant: str) -> dict:
    t = today(tenant).isoformat()
    at = clock()
    with session() as s:
        stays = s.scalars(select(HsBooking).where(HsBooking.tenant_id == tenant, HsBooking.kind == "stay")).all()
        arr = [_booking_view(s, b) for b in stays if b.check_in == t and b.status in ("hold", "confirmed")]
        dep = [_booking_view(s, b) for b in stays if b.check_out == t and b.status == "checked_in"]
        inhouse = [_booking_view(s, b) for b in stays if b.status == "checked_in"]
        late_out = [b.number for b in stays if b.status == "checked_in" and b.check_out < t]
        formc = [b.number for b in stays if (_j(b.checklist, {}).get("form_c") or {}).get("done") is False]
        holds = [b.number for b in stays if b.status == "hold" and b.hold_until and _aware(b.hold_until) < at + timedelta(hours=6)]
        dues = [{"booking": b.number, "due": _r2(b.total - b.paid)} for b in stays if b.status in ("confirmed", "checked_in") and b.total
                and b.total - b.paid > 0.5 and b.check_in <= (today(tenant) + timedelta(days=1)).isoformat()]
        task_open = len(s.scalars(select(HsTask).where(HsTask.tenant_id == tenant, HsTask.status == "open")).all())
        waiting = len(s.scalars(select(HsCard).where(HsCard.tenant_id == tenant, HsCard.status == "waiting")).all())
    parts = []
    if arr:
        parts.append(f"Aaj aa rahe: {', '.join(a['number'] for a in arr)}")
    if dep:
        parts.append(f"aaj ja rahe: {', '.join(d['number'] for d in dep)}")
    if late_out:
        parts.append(f"check-out darj nahi: {', '.join(late_out)}")
    if formc:
        parts.append(f"Form C baaki: {', '.join(formc)}")
    if task_open:
        parts.append(f"{task_open} safai / laundry kaam khule")
    if dues:
        parts.append(f"{len(dues)} booking mein paise baaki")
    if holds:
        parts.append(f"hold khatam hone wale: {', '.join(holds)}")
    if waiting:
        parts.append(f"{waiting} card aapke tap ke intezaar mein")
    say = ("; ".join(parts) + ".") if parts else "Homestay mein aaj sab theek."
    return {"arrivals": arr, "departures": dep, "in_house": inhouse, "late_checkout": late_out, "form_c_pending": formc, "holds": holds,
            "dues": dues, "tasks_open": task_open, "waiting": waiting, "say": say[:1].upper() + say[1:]}


def overview(tenant: str) -> dict:
    return {"settings": settings(tenant), "rooms": rooms(tenant), "day": day(tenant), "upcoming": bookings(tenant, when="upcoming"),
            "cards": cards(tenant), "tasks": tasks(tenant), "registration": registration(tenant)}


# ---------------------------------------------------------------- worker
def _tenants() -> list[str]:
    with session() as s:
        return sorted(set(s.scalars(select(HsSettings.tenant_id)).all()) | set(s.scalars(select(HsBooking.tenant_id)).all()))


def _morning_due(tenant: str, loc: datetime) -> bool:
    with session() as s:
        r = s.get(HsSettings, tenant)
        if r is None or r.last_morning == loc.date().isoformat():
            return False
        try:
            hh, mm = (int(x) for x in (r.morning_time or "08:00").split(":"))
        except ValueError:
            hh, mm = 8, 0
        return (loc.hour, loc.minute) >= (hh, mm)


def _timers(tenant: str, loc: datetime) -> dict:
    out = {"expired": 0, "alerts": 0, "drafts": 0}
    on = loc.date()
    at = clock()
    pubs, drafts = [], []
    with _LOCK, session() as s:
        st = _st(s, tenant)
        for b in s.scalars(select(HsBooking).where(HsBooking.tenant_id == tenant, HsBooking.kind == "stay")).all():
            if b.status == "hold" and b.hold_until and _aware(b.hold_until) < at:
                b.status = "cancelled"
                _log(b, "Hold ka samay khatam: kamra khula")
                out["expired"] += 1
                pubs.append({"kind": "hold", "booking": b.number, "say": f"{b.number}: hold ka samay khatam, kamra phir khaali."})
                continue
            chk = _j(b.checklist, {})
            fc = chk.get("form_c") or {}
            if b.status == "checked_in" and fc and not fc.get("done") and fc.get("due"):
                due = datetime.fromisoformat(fc["due"])
                left = (_aware(due) - at).total_seconds() / 3600
                if left <= 12 and _once(s, tenant, f"fc12:{b.id}"):
                    pubs.append({"kind": "form_c", "booking": b.number,
                                 "say": f"{b.number}: Form C ke {max(0, int(left))} ghante bache (indianfrro.gov.in)."})
                if left <= 0 and _once(s, tenant, f"fc0:{b.id}"):
                    pubs.append({"kind": "form_c", "booking": b.number,
                                 "say": f"{b.number}: Form C ka 24 ghante ka samay nikal gaya - abhi bhariye (Rs 50,000 tak jurmana ho sakta hai)."})
            if b.status == "checked_in" and b.check_out < on.isoformat() and _once(s, tenant, f"late:{b.id}"):
                pubs.append({"kind": "checkout", "booking": b.number, "say": f"{b.number}: check-out ki taarikh nikal gayi - check-out darj kijiye."})
            if b.status == "checked_out" and b.left_at and b.guest_id and "review_asked" not in chk:
                left_day = _aware(b.left_at).astimezone(_tz(tenant)).date()
                if (on - left_day).days >= 1 and (on - left_day).days <= 7 and _once(s, tenant, f"rev:{b.id}"):
                    drafts.append((b.id, "review"))
            if b.status == "confirmed" and b.total and b.total - b.paid > 0.5 and b.check_in == (on + timedelta(days=1)).isoformat() \
                    and _once(s, tenant, f"bal:{b.id}"):
                drafts.append((b.id, "checkin_info"))
                drafts.append((b.id, "payment"))
            elif b.status == "confirmed" and b.check_in == (on + timedelta(days=1)).isoformat() and _once(s, tenant, f"info:{b.id}"):
                drafts.append((b.id, "checkin_info"))
        reg = _j(st.registration, {})
        vt = R.parse_date(reg.get("valid_to"))
        if vt:
            left = (vt - on).days
            ws = [w for w in (90, 60, 30, 7, 0) if left <= w]
            if ws and _once(s, tenant, f"reg:{vt}:{min(ws)}"):
                pubs.append({"kind": "registration", "say": (f"Homestay registration {vt.isoformat()} ko khatam ({left} din)." if left >= 0 else
                                                             f"Homestay registration {vt.isoformat()} ko khatam ho gaya!") + " Renewal ka kaam shuru kijiye."})
    for p in pubs:
        _publish(tenant, "homestay_alert", p)
        out["alerts"] += 1
    for bid, sub in drafts:
        try:
            draft_message(tenant, bid, sub, actor="routine")
            out["drafts"] += 1
        except StayError:
            pass
    return out


def tick(when: datetime | None = None) -> dict:
    """Worker, every minute (each owner throttled by once-keys): hold expiry, Form C 12 h / 24 h alerts, late check-out, review drafts
    a day after departure (same text for all), check-in info + balance drafts the day before, registration renewal windows, morning note."""
    n = _aware(when) or now()
    out = {"expired": 0, "alerts": 0, "drafts": 0, "morning": 0}
    for tenant in _tenants():
        try:
            loc = n.astimezone(_tz(tenant))
            r = _timers(tenant, loc)
            for k in r:
                out[k] += r[k]
            if _morning_due(tenant, loc):
                d = day(tenant)
                with session() as s:
                    _st(s, tenant).last_morning = loc.date().isoformat()
                if d["say"] != "Homestay mein aaj sab theek.":
                    _publish(tenant, "homestay_day", {"say": d["say"], "arrivals": len(d["arrivals"]), "departures": len(d["departures"]),
                                                      "tasks": d["tasks_open"], "waiting": d["waiting"], "form_c": len(d["form_c_pending"])})
                    out["morning"] += 1
        except Exception:
            log.exception("homestay tick failed for %s", tenant)
    return out
