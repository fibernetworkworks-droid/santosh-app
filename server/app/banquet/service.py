"""Banquet Sahayak: Hoola as a banquet hall / lawn / hotel-banquet sales coworker, end to end.

  1. Her venue: halls / lawns with seated + floating capacity, slots (subah / shaam / pura din) with HER times, menu packages per
     plate (veg / non-veg / Jain) at HER prices, extras (decor, DJ, rooms ...) at HER prices. Nothing is ever priced by Hoola.
  2. Enquiries from calls / WhatsApp / her paste -> lead (E-0001) with the facts that are written, linked to the Telecaller list,
     free halls for that date + slot + guests.
  3. Availability calendar: tentative HOLDS that expire by themselves and CONFIRMED blocks. A hall + day + slot already held or
     confirmed by someone else is refused in code (a full day clashes with morning and evening) - even for her.
  4. Quotation by code (plates = max(guarantee, final / actual count), her hall rent, extras, approved discount, GST per line,
     CGST + SGST at the venue), payment schedule, booking terms with the cancellation / refund table shown upfront, BEO / function
     sheet for kitchen and staff, final guest-count lock date, noise / loudspeaker 10 pm note, post-event bill, receipts.

Waits for HER tap (only the app API passes by_tap=True; tools only make the card):
  * the quotation and the booking terms (contract) going to the client, the post-event bill, any message to a client,
  * turning a hold into a confirmed booking,
  * any discount and any refund (her phone's fingerprint once a phone key is active: approvekey kind "banquet"),
  * any payment request (the client pays to HER UPI ID in their own app; Hoola never takes or sends money)."""
from __future__ import annotations

import io
import json
import logging
import re
import secrets
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote as urlq

from sqlalchemy import select

from ..db import new_id, now, session
from . import rules as R
from .models import (
    BanquetAlert,
    BanquetBlock,
    BanquetBooking,
    BanquetCard,
    BanquetExtra,
    BanquetHall,
    BanquetLead,
    BanquetPackage,
    BanquetSettings,
)

log = logging.getLogger("santosh.banquet")
_LOCK = threading.RLock()
MONEY_CARDS = ("discount", "refund")
CARD_KINDS = ("quote", "contract", "confirm", "discount", "refund", "pay", "bill", "message")
CARD_TITLE = {"quote": "Quotation client ko", "contract": "Booking terms client ko", "confirm": "Hold ko pakki booking",
              "discount": "Discount", "refund": "Refund", "pay": "Paise maangna", "bill": "Event ke baad ka bill",
              "message": "Client ko message"}
STATUS = {"draft": "Draft", "hold": "Hold (kachchi)", "confirmed": "Pakki", "done": "Ho gaya", "cancelled": "Radd"}


class BanquetError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def _j(s: str | None, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _dump(v) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


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
    s = str(v).strip()[:10]
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def _num(v) -> float | None:
    if v is None or v == "" or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d.\-]", "", str(v).replace(",", ""))
    try:
        return float(s) if s not in ("", "-", ".") else None
    except ValueError:
        return None


def _int(v) -> int | None:
    n = _num(v)
    return int(n) if n is not None and n >= 0 else None


def _rs(v: float | None) -> str:
    if v is None:
        return "[daam?]"
    try:
        from ..india.money import inr
        return inr(v)
    except Exception:
        return f"₹{v:,.0f}"


def _pdf_rs(v: float | None) -> str:
    return "[ ? ]" if v is None else "Rs. " + f"{v:,.2f}"


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("banquet publish failed")


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


def _st(s, tenant: str) -> BanquetSettings:
    r = s.get(BanquetSettings, tenant)
    if r is None:
        r = BanquetSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def _slots(st: BanquetSettings) -> dict:
    v = _j(st.slots, {})
    out = {}
    for k in R.SLOTS:
        d = v.get(k) or {}
        out[k] = {"label": R.SLOT_LABEL[k], "from": R.hhmm(d.get("from"), R.DEFAULT_SLOTS[k]["from"]),
                  "to": R.hhmm(d.get("to"), R.DEFAULT_SLOTS[k]["to"])}
    return out


def _stages_of(st: BanquetSettings) -> list[dict]:
    return _j(st.stages, []) or [dict(x) for x in R.DEFAULT_STAGES]


def _policy_of(st: BanquetSettings) -> list[dict]:
    return _j(st.cancel, []) or [dict(x) for x in R.DEFAULT_CANCEL]


def _wa(phone: str, text: str) -> str:
    d = R.phone(phone)
    return f"https://wa.me/91{d}?text={urlq(text)}" if d else ""


def _sms(phone: str, text: str) -> str:
    d = R.phone(phone)
    return f"sms:+91{d}?body={urlq(text)}" if d else ""


def _upi_of(tenant: str) -> tuple[str, str]:
    with session() as s:
        st = _st(s, tenant)
        upi, nm = st.upi_id, st.venue
    if not upi:
        try:
            from ..employee import service as emp
            p = emp.profile(tenant) or {}
            upi = p.get("upi_id") or ""
            nm = nm or p.get("upi_name") or p.get("business_name") or ""
        except Exception:
            upi = ""
    return upi, nm


def _upi(tenant: str, amount: float, note: str) -> str:
    upi, nm = _upi_of(tenant)
    if not upi or amount <= 0:
        return ""
    return f"upi://pay?pa={urlq(upi)}&pn={urlq(nm)}&am={amount:.2f}&cu=INR&tn={urlq(note[:40])}"


def _store(tenant: str, name: str, data: bytes, mime: str, conv: str = "", title: str = "") -> dict:
    from .. import chatfiles
    f = chatfiles.store(tenant, name, data, mime)
    _publish(tenant, "pc_file", {**f, "source": "banquet", "title": title or name}, conv)
    return f


def _fy(d: date) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


def _log(b: BanquetBooking, text: str, by: str = "") -> None:
    lg = _j(b.log, [])
    lg.append({"at": now().isoformat(), "what": R.clean(text, 300), "by": by})
    b.log = _dump(lg[-80:])


# ---------------------------------------------------------------- settings
_SET_KEYS = ("venue", "gstin", "address", "phone", "email", "upi_id", "specified", "gst_food", "gst_hall", "gst_extra", "slots",
             "hold_hours", "lock_days", "stages", "cancel", "terms", "music_end", "validity_days", "morning_time", "rules")


def _settings_view(st: BanquetSettings) -> dict:
    probs, notes = R.check_cancel(_policy_of(st))
    return {"venue": st.venue, "gstin": st.gstin, "address": st.address, "phone": st.phone, "email": st.email, "upi_id": st.upi_id,
            "specified": bool(st.specified), "gst_food": R.food_gst(bool(st.specified), st.gst_food), "gst_food_set": st.gst_food,
            "gst_hall": st.gst_hall, "gst_extra": st.gst_extra, "slots": _slots(st), "hold_hours": st.hold_hours,
            "lock_days": st.lock_days, "stages": _stages_of(st), "stages_starter": not _j(st.stages, []),
            "cancel": _policy_of(st), "cancel_starter": not _j(st.cancel, []), "cancel_lines": R.policy_lines(_policy_of(st)),
            "cancel_notes": notes, "terms": st.terms, "music_end": st.music_end, "validity_days": st.validity_days,
            "morning_time": st.morning_time, "rules": st.rules,
            "gst_note": ("GST aapke CA se pakka karein: khana / banquet 'specified premises' (pichhle saal koi room Rs 7,500 se upar, "
                         "ya opt-in) par 18% ITC ke saath, warna 5% bina ITC; sirf hall ka kiraya 18%; rooms Rs 7,500 tak 5%, upar 18%.")}


def settings(tenant: str) -> dict:
    with session() as s:
        return _settings_view(_st(s, tenant))


def save_settings(tenant: str, **kw: Any) -> dict:
    with _LOCK, session() as s:
        st = _st(s, tenant)
        for k in ("venue", "address", "email", "terms", "rules"):
            if k in kw and kw[k] is not None:
                setattr(st, k, R.clean(kw[k], 2000 if k in ("terms", "rules") else 300))
        if "phone" in kw:
            p = R.phone(kw["phone"])
            if kw["phone"] and not p:
                raise BanquetError("Phone 10 ankon ka mobile number chahiye.")
            st.phone = p
        if "gstin" in kw:
            g = str(kw["gstin"] or "").strip().upper()
            if g:
                from ..india.money import gstin_ok
                if not gstin_ok(g):
                    raise BanquetError("GSTIN sahi nahi lagta (check digit nahi mila).")
            st.gstin = g
        if "upi_id" in kw:
            u = str(kw["upi_id"] or "").strip()
            if u and not re.fullmatch(r"[\w.\-]{2,64}@[A-Za-z]{2,32}", u):
                raise BanquetError("UPI ID jaisa 'naam@bank' chahiye.")
            st.upi_id = u
        if "specified" in kw:
            st.specified = bool(kw["specified"])
        if "gst_food" in kw:
            v = _num(kw["gst_food"])
            st.gst_food = v
        for k in ("gst_hall", "gst_extra"):
            if k in kw and _num(kw[k]) is not None:
                v = _num(kw[k])
                if not 0 <= v <= 40:
                    raise BanquetError("GST % 0-40 ke beech.")
                setattr(st, k, v)
        if "slots" in kw and isinstance(kw["slots"], dict):
            cur = _slots(st)
            for k, d in kw["slots"].items():
                if k in R.SLOTS and isinstance(d, dict):
                    cur[k] = {"from": R.hhmm(d.get("from"), cur[k]["from"]), "to": R.hhmm(d.get("to"), cur[k]["to"])}
            st.slots = _dump({k: {"from": v["from"], "to": v["to"]} for k, v in cur.items()})
        for k, lo, hi in (("hold_hours", 1, 24 * 14), ("lock_days", 0, 30), ("validity_days", 1, 60)):
            if k in kw and _int(kw[k]) is not None:
                setattr(st, k, max(lo, min(hi, _int(kw[k]))))
        if "stages" in kw:
            stg = [{"label": R.clean(x.get("label"), 80), "pct": _num(x.get("pct")) or 0,
                    "days_before": _int(x.get("days_before"))} for x in (kw["stages"] or []) if isinstance(x, dict)]
            if stg:
                probs = R.check_stages(stg)
                if probs:
                    raise BanquetError(" ".join(probs))
            st.stages = _dump(stg) if stg else ""
        if "cancel" in kw:
            pol = [x for x in (kw["cancel"] or []) if isinstance(x, dict)]
            if pol:
                probs, _ = R.check_cancel(pol)
                if probs:
                    raise BanquetError(" ".join(probs))
                pol = [{"days_before": int(x["days_before"]), "refund_pct": float(x["refund_pct"])} for x in pol]
            st.cancel = _dump(pol) if pol else ""
        for k, d in (("music_end", "22:00"), ("morning_time", "09:00")):
            if k in kw:
                setattr(st, k, R.hhmm(kw[k], d))
        view = _settings_view(st)
    return {"settings": view, "say": "Venue ke niyam save." + (" " + " ".join(view["cancel_notes"]) if view["cancel_notes"] else "")}


# ---------------------------------------------------------------- halls / packages / extras (HER numbers)
def _hall_view(h: BanquetHall) -> dict:
    return {"id": h.id, "name": h.name, "kind": h.kind, "seated": h.seated, "floating": h.floating, "rent": h.rent,
            "rent_full": h.rent_full, "rent_text": _rs(h.rent) if h.rent is not None else "khane ke saath / bataya nahi",
            "notes": h.notes, "active": h.active, "open_air": h.kind in R.OPEN_AIR}


def hall_save(tenant: str, name: str, kind: str = "", seated=None, floating=None, rent=None, rent_full=None, notes: str = "",
              hall_id: str = "", active: bool | None = None) -> dict:
    name = R.clean(name, 120)
    with _LOCK, session() as s:
        h = None
        if hall_id:
            h = _hall(s, tenant, hall_id)
        elif name:
            h = s.scalars(select(BanquetHall).where(BanquetHall.tenant_id == tenant, BanquetHall.name == name)).first()
        if h is None:
            if not name:
                raise BanquetError("Hall / lawn ka naam chahiye.")
            h = BanquetHall(tenant_id=tenant, name=name)
            s.add(h)
        if name:
            h.name = name
        if kind:
            k = kind.lower().strip()
            if k not in R.HALL_KINDS:
                raise BanquetError("kind: " + " / ".join(R.HALL_KINDS))
            h.kind = k
        for k, v in (("seated", seated), ("floating", floating)):
            if v is not None and v != "":
                n = _int(v)
                if n is None:
                    raise BanquetError(f"{k} number chahiye.")
                setattr(h, k, n)
        for k, v in (("rent", rent), ("rent_full", rent_full)):
            if v is not None and v != "":
                n = _num(v)
                if n is None or n < 0:
                    raise BanquetError("Kiraya number chahiye.")
                setattr(h, k, n)
        if notes:
            h.notes = R.clean(notes, 500)
        if active is not None:
            h.active = bool(active)
        if not (h.seated or h.floating):
            raise BanquetError("Kam se kam ek capacity (seated ya floating) chahiye.")
        s.flush()
        v = _hall_view(h)
    return {"hall": v, "say": f"{v['name']}: {v['seated']} baithe / {v['floating']} khade."}


def _hall(s, tenant: str, ref: str) -> BanquetHall:
    ref = (ref or "").strip()
    h = s.get(BanquetHall, ref) if ref else None
    if h is None or h.tenant_id != tenant:
        rows = s.scalars(select(BanquetHall).where(BanquetHall.tenant_id == tenant)).all()
        h = next((x for x in rows if x.name.lower() == ref.lower()), None) or \
            next((x for x in rows if ref and ref.lower() in x.name.lower()), None)
    if h is None:
        raise BanquetError(f"Hall '{ref}' nahi mila.")
    return h


def halls(tenant: str) -> list[dict]:
    with session() as s:
        return [_hall_view(h) for h in s.scalars(select(BanquetHall).where(BanquetHall.tenant_id == tenant).order_by(BanquetHall.name)).all()]


def _pkg_view(p: BanquetPackage) -> dict:
    return {"id": p.id, "name": p.name, "diet": p.diet, "diet_label": R.DIET_LABEL.get(p.diet, p.diet), "price": p.price,
            "price_text": _rs(p.price) + " / plate", "items": _j(p.items, []), "min_plates": p.min_plates, "active": p.active}


def package_save(tenant: str, name: str, price=None, diet: str = "", items: Any = None, min_plates=None, package_id: str = "",
                 active: bool | None = None) -> dict:
    name = R.clean(name, 120)
    with _LOCK, session() as s:
        p = None
        if package_id:
            p = _pkg(s, tenant, package_id)
        elif name:
            p = s.scalars(select(BanquetPackage).where(BanquetPackage.tenant_id == tenant, BanquetPackage.name == name)).first()
        fresh = p is None
        if fresh:
            if not name:
                raise BanquetError("Package ka naam chahiye.")
            p = BanquetPackage(tenant_id=tenant, name=name)
        pr = _num(price)
        if pr is not None:
            if pr <= 0:
                raise BanquetError("Plate ka daam 0 se zyada.")
            p.price = pr
        elif fresh:
            raise BanquetError("Plate ka daam aapka batana zaroori hai (Hoola daam nahi gadhta).")
        if fresh:
            s.add(p)
        if name:
            p.name = name
        d = R.diet_of(diet) or (diet if diet in R.DIETS else "")
        if d:
            p.diet = d
        elif fresh:
            p.diet = R.diet_of(name) or "veg"
        if items is not None:
            if isinstance(items, str):
                items = [x for x in re.split(r"[,\n;]+", items)]
            p.items = _dump([R.clean(x, 80) for x in items if str(x).strip()][:60])
        if min_plates is not None and min_plates != "":
            p.min_plates = _int(min_plates) or 0
        if active is not None:
            p.active = bool(active)
        s.flush()
        v = _pkg_view(p)
    return {"package": v, "say": f"{v['name']} ({v['diet_label']}) {v['price_text']}."}


def _pkg(s, tenant: str, ref: str) -> BanquetPackage:
    ref = (ref or "").strip()
    p = s.get(BanquetPackage, ref) if ref else None
    if p is None or p.tenant_id != tenant:
        rows = s.scalars(select(BanquetPackage).where(BanquetPackage.tenant_id == tenant)).all()
        p = next((x for x in rows if x.name.lower() == ref.lower()), None) or \
            next((x for x in rows if ref and ref.lower() in x.name.lower()), None)
    if p is None:
        raise BanquetError(f"Package '{ref}' nahi mila.")
    return p


def packages(tenant: str) -> list[dict]:
    with session() as s:
        return [_pkg_view(p) for p in s.scalars(select(BanquetPackage).where(BanquetPackage.tenant_id == tenant).order_by(BanquetPackage.price)).all()]


def _extra_view(x: BanquetExtra) -> dict:
    return {"id": x.id, "name": x.name, "kind": x.kind, "price": x.price, "unit": x.unit, "gst_pct": x.gst_pct,
            "price_text": f"{_rs(x.price)} / {x.unit}", "active": x.active}


def extra_save(tenant: str, name: str, price=None, kind: str = "", unit: str = "", gst_pct=None, extra_id: str = "") -> dict:
    name = R.clean(name, 120)
    with _LOCK, session() as s:
        x = s.get(BanquetExtra, extra_id) if extra_id else None
        if x is not None and x.tenant_id != tenant:
            x = None
        if x is None and name:
            x = s.scalars(select(BanquetExtra).where(BanquetExtra.tenant_id == tenant, BanquetExtra.name == name)).first()
        fresh = x is None
        pr = _num(price)
        if fresh:
            if not name or pr is None:
                raise BanquetError("Extra ka naam aur aapka daam dono chahiye.")
            x = BanquetExtra(tenant_id=tenant, name=name)
            s.add(x)
        if pr is not None:
            if pr < 0:
                raise BanquetError("Daam 0 ya zyada.")
            x.price = pr
        k = (kind or "").lower().strip()
        if not k and fresh:
            low = name.lower()
            k = "rooms" if "room" in low else "dj" if "dj" in low else "decor" if re.search(r"decor|sajawat|flower|phool|mandap|stage", low) else "other"
        if k:
            x.kind = k if k in R.EXTRA_KINDS else "other"
        if unit:
            x.unit = unit if unit in ("event", "plate", "room_night", "hour", "nos") else "nos"
        elif fresh and x.kind == "rooms":
            x.unit = "room_night"
        if gst_pct is not None and gst_pct != "":
            x.gst_pct = _num(gst_pct)
        s.flush()
        v = _extra_view(x)
    return {"extra": v, "say": f"{v['name']} {v['price_text']}."}


def extras(tenant: str) -> list[dict]:
    with session() as s:
        return [_extra_view(x) for x in s.scalars(select(BanquetExtra).where(BanquetExtra.tenant_id == tenant).order_by(BanquetExtra.name)).all()]


# ---------------------------------------------------------------- availability (holds expire; clashes refused)
def _expire_holds(s, tenant: str) -> list[BanquetBlock]:
    n = clock()
    gone = []
    for b in s.scalars(select(BanquetBlock).where(BanquetBlock.tenant_id == tenant, BanquetBlock.kind == "hold",
                                                  BanquetBlock.active.is_(True))).all():
        if b.expires_at and _aware(b.expires_at) <= n:
            b.active = False
            gone.append(b)
            bk = s.get(BanquetBooking, b.booking_id) if b.booking_id else None
            if bk is not None and bk.status == "hold":
                bk.status = "draft"
                bk.hold_until = None
                _log(bk, "Hold ka samay khatam: hall chhoot gaya")
    return gone


def _clashes(s, tenant: str, hall_id: str, day: str, slot: str, booking_id: str = "") -> list[BanquetBlock]:
    _expire_holds(s, tenant)
    rows = s.scalars(select(BanquetBlock).where(BanquetBlock.tenant_id == tenant, BanquetBlock.hall_id == hall_id,
                                                BanquetBlock.day == day, BanquetBlock.active.is_(True))).all()
    return [b for b in rows if R.slots_clash(b.slot, slot) and not (booking_id and b.booking_id == booking_id)]


def _clash_say(s, blocks: list[BanquetBlock]) -> str:
    parts = []
    for b in blocks:
        bk = s.get(BanquetBooking, b.booking_id) if b.booking_id else None
        who = f"{bk.number} {bk.client}" if bk else (b.note or "aapne band kiya")
        parts.append(f"{R.SLOT_LABEL.get(b.slot, b.slot)}: {'pakki booking' if b.kind == 'confirmed' else 'hold' if b.kind == 'hold' else 'band'} ({who})")
    return "; ".join(parts)


def free(tenant: str, day: str, slot: str = "", guests=None, style: str = "") -> dict:
    """Free halls for a day + slot (+ guests). style seated | floating decides the capacity column (default: either fits)."""
    d = _date(day)
    if d is None:
        raise BanquetError("Tareekh samajh nahi aayi (jaise 2026-12-12).")
    sl = R.slot_of(slot) or "evening"
    g = _int(guests)
    out = []
    with _LOCK, session() as s:
        for h in s.scalars(select(BanquetHall).where(BanquetHall.tenant_id == tenant, BanquetHall.active.is_(True))).all():
            cl = _clashes(s, tenant, h.id, d.isoformat(), sl)
            cap = h.seated if style == "seated" else h.floating if style == "floating" else max(h.seated, h.floating)
            fits = g is None or cap >= g
            out.append({"hall": _hall_view(h), "free": not cl, "fits": fits, "why": _clash_say(s, cl) if cl else "",
                        "capacity": cap})
    good = [x for x in out if x["free"] and x["fits"]]
    if good:
        say = f"{d.isoformat()} {R.SLOT_LABEL[sl]}: khaali " + ", ".join(f"{x['hall']['name']} ({x['capacity']})" for x in good) + "."
    else:
        say = f"{d.isoformat()} {R.SLOT_LABEL[sl]}: koi hall khaali nahi" + (f" jo {g} logon ke liye ho" if g else "") + "."
    return {"day": d.isoformat(), "slot": sl, "guests": g, "halls": out, "say": say}


def calendar(tenant: str, month: str = "") -> dict:
    t0 = today(tenant)
    m = re.fullmatch(r"(20\d\d)-(\d{1,2})", (month or "").strip())
    y, mo = (int(m.group(1)), int(m.group(2))) if m else (t0.year, t0.month)
    first = date(y, mo, 1)
    last = (date(y + (mo == 12), mo % 12 + 1, 1) - timedelta(days=1))
    with _LOCK, session() as s:
        _expire_holds(s, tenant)
        hs = {h.id: h.name for h in s.scalars(select(BanquetHall).where(BanquetHall.tenant_id == tenant)).all()}
        rows = s.scalars(select(BanquetBlock).where(BanquetBlock.tenant_id == tenant, BanquetBlock.active.is_(True),
                                                    BanquetBlock.day >= first.isoformat(), BanquetBlock.day <= last.isoformat())).all()
        days: dict[str, list] = {}
        for b in rows:
            bk = s.get(BanquetBooking, b.booking_id) if b.booking_id else None
            days.setdefault(b.day, []).append({"hall": hs.get(b.hall_id, ""), "hall_id": b.hall_id, "slot": b.slot, "kind": b.kind,
                                               "booking": bk.number if bk else "", "client": bk.client if bk else b.note,
                                               "expires_at": _aware(b.expires_at).isoformat() if b.expires_at else ""})
    return {"month": f"{y}-{mo:02d}", "halls": [{"id": k, "name": v} for k, v in hs.items()], "days": days}


def close_slot(tenant: str, hall: str, day: str, slot: str, note: str = "", actor: str = "owner") -> dict:
    """Her own block (maintenance, family use ...). Same clash rule."""
    if not is_owner(actor):
        raise BanquetError("Hall band karna sirf owner.")
    d = _date(day)
    sl = R.slot_of(slot)
    if d is None or not sl:
        raise BanquetError("Tareekh aur slot (subah / shaam / pura din) chahiye.")
    with _LOCK, session() as s:
        h = _hall(s, tenant, hall)
        cl = _clashes(s, tenant, h.id, d.isoformat(), sl)
        if cl:
            raise BanquetError(f"{h.name} {d.isoformat()} pehle se: {_clash_say(s, cl)}.")
        s.add(BanquetBlock(tenant_id=tenant, hall_id=h.id, day=d.isoformat(), slot=sl, kind="closed", note=R.clean(note, 200) or "band"))
    return {"say": f"{h.name} {d.isoformat()} {R.SLOT_LABEL[sl]} band kiya."}


def open_slot(tenant: str, hall: str, day: str, slot: str, actor: str = "owner") -> dict:
    if not is_owner(actor):
        raise BanquetError("Sirf owner.")
    sl = R.slot_of(slot)
    with _LOCK, session() as s:
        h = _hall(s, tenant, hall)
        n = 0
        for b in s.scalars(select(BanquetBlock).where(BanquetBlock.tenant_id == tenant, BanquetBlock.hall_id == h.id,
                                                      BanquetBlock.day == str(_date(day) or ""), BanquetBlock.kind == "closed",
                                                      BanquetBlock.active.is_(True))).all():
            if not sl or b.slot == sl:
                b.active = False
                n += 1
    return {"say": f"{n} band slot khole."}


# ---------------------------------------------------------------- enquiries (leads)
def _lead_view(x: BanquetLead) -> dict:
    return {"id": x.id, "number": x.number, "name": x.name, "phone": x.phone, "source": x.source, "event_type": x.event_type,
            "event_label": R.EVENT_LABEL.get(x.event_type, ""), "day": x.day, "slot": x.slot, "guests": x.guests, "diet": x.diet,
            "budget": x.budget, "notes": x.notes, "status": x.status, "lost_reason": x.lost_reason, "follow_up": x.follow_up,
            "tele_lead": x.tele_lead, "booking_id": x.booking_id,
            "created_at": _aware(x.created_at).isoformat() if x.created_at else ""}


def _lead(s, tenant: str, ref: str) -> BanquetLead:
    ref = (ref or "").strip()
    x = s.get(BanquetLead, ref) if ref else None
    if x is None or x.tenant_id != tenant:
        x = s.scalars(select(BanquetLead).where(BanquetLead.tenant_id == tenant, BanquetLead.number == ref.upper())).first()
    if x is None and R.phone(ref):
        x = s.scalars(select(BanquetLead).where(BanquetLead.tenant_id == tenant, BanquetLead.phone == R.phone(ref))
                      .order_by(BanquetLead.created_at.desc())).first()
    if x is None:
        raise BanquetError(f"Enquiry '{ref}' nahi mili.")
    return x


def enquiry(tenant: str, text: str = "", name: str = "", phone: str = "", source: str = "", event_type: str = "", day: str = "",
            slot: str = "", guests=None, diet: str = "", budget=None, notes: str = "", actor: str = "owner", conv: str = "") -> dict:
    """A new enquiry from a call / WhatsApp / her paste. The pasted text is DATA: only facts written in it are taken."""
    t0 = today(tenant)
    got = R.parse_enquiry(text, t0) if text else {}
    f = {"name": R.clean(name, 120) or got.get("name", ""), "phone": R.phone(phone) or got.get("phone", ""),
         "event_type": (event_type if event_type in R.EVENT_LABEL else R.event_of(event_type)) or got.get("event_type", ""),
         "day": (_date(day) or R.date_of(day, t0) or _date(got.get("day") or got.get("date"))),
         "slot": R.slot_of(slot) or got.get("slot", ""), "guests": _int(guests) if guests not in (None, "") else got.get("guests"),
         "diet": R.diet_of(diet) or got.get("diet", ""), "budget": _num(budget) if budget not in (None, "") else got.get("budget")}
    if phone and not f["phone"]:
        raise BanquetError(f"'{phone}' sahi mobile number nahi lagta.")
    if not (f["phone"] or f["name"]):
        raise BanquetError("Graahak ka naam ya phone chahiye.")
    if f["day"] and f["day"] < t0:
        raise BanquetError(f"{f['day'].isoformat()} beet chuki tareekh hai.")
    src = (source or ("paste" if text else "call")).lower()
    src = src if src in ("call", "whatsapp", "walk_in", "paste", "website", "referral", "instagram") else "call"
    with _LOCK, session() as s:
        st = _st(s, tenant)
        x = None
        if f["phone"]:
            x = s.scalars(select(BanquetLead).where(BanquetLead.tenant_id == tenant, BanquetLead.phone == f["phone"],
                                                    BanquetLead.status.notin_(("booked", "lost")))).first()
        fresh = x is None
        if fresh:
            st.enq_seq += 1
            x = BanquetLead(tenant_id=tenant, number=f"E-{st.enq_seq:04d}", source=src)
            s.add(x)
        for k in ("name", "phone", "event_type", "slot", "diet"):
            if f[k]:
                setattr(x, k, f[k])
        if f["day"]:
            x.day = f["day"].isoformat()
        if f["guests"]:
            x.guests = f["guests"]
        if f["budget"]:
            x.budget = f["budget"]
        nt = R.clean(notes or text, 1500)
        if nt:
            x.notes = ((x.notes + "\n") if x.notes and not fresh else "") + nt
        if not x.follow_up:
            x.follow_up = (t0 + timedelta(days=1)).isoformat()
        s.flush()
        lid = x.id
    tele = ""
    if f["phone"]:
        try:
            from ..telecall import service as tc
            r = tc.add_lead(tenant, name=f["name"], phone=f["phone"], source="enquiry", purpose="sales",
                            need=f"{R.EVENT_LABEL.get(f['event_type'], 'Function')} {f['day'].isoformat() if f['day'] else ''} "
                                 f"{f['guests'] or ''} log".strip(), amount=f["budget"], consent=True, by=actor)
            tele = str((r.get("lead") or {}).get("id") or "")
        except Exception:
            log.info("telecall link skipped", exc_info=True)
    with session() as s:
        x = s.get(BanquetLead, lid)
        if tele:
            x.tele_lead = tele
        v = _lead_view(x)
    av = None
    if v["day"]:
        try:
            av = free(tenant, v["day"], v["slot"] or "evening", v["guests"])
        except BanquetError:
            av = None
    missing = [k for k, lab in (("day", "tareekh"), ("slot", "subah / shaam"), ("guests", "kitne log"), ("diet", "veg / non-veg / Jain"))
               if not v[k]]
    say = f"{v['number']} {v['name'] or v['phone']}: enquiry darj" + (" (Telecaller list mein bhi)" if tele else "") + "."
    if av:
        say += " " + av["say"]
    if missing:
        say += " Poochhna baaki: " + ", ".join(lab for k, lab in (("day", "tareekh"), ("slot", "subah / shaam"), ("guests", "kitne log"),
                                                                    ("diet", "veg / non-veg / Jain")) if k in missing) + "."
    return {"lead": v, "fresh": fresh, "availability": av, "missing": missing, "say": say}


def lead_update(tenant: str, ref: str, status: str = "", follow_up: str = "", lost_reason: str = "", notes: str = "",
                actor: str = "owner") -> dict:
    with _LOCK, session() as s:
        x = _lead(s, tenant, ref)
        if status:
            if status not in ("new", "contacted", "visit", "quoted", "hold", "booked", "lost"):
                raise BanquetError("status: new / contacted / visit / quoted / hold / booked / lost")
            if status == "lost" and not (lost_reason or x.lost_reason):
                raise BanquetError("Kyun nahi hua (daam / tareekh / jagah ...) likhiye: agli baar kaam aayega.")
            x.status = status
        if lost_reason:
            x.lost_reason = R.clean(lost_reason, 300)
        if follow_up:
            d = _date(follow_up) or R.date_of(follow_up, today(tenant))
            if d is None:
                raise BanquetError("Follow-up tareekh samajh nahi aayi.")
            x.follow_up = d.isoformat()
        if notes:
            x.notes = (x.notes + "\n" if x.notes else "") + R.clean(notes, 800)
        v = _lead_view(x)
    return {"lead": v, "say": f"{v['number']}: {v['status']}."}


def leads(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        q = select(BanquetLead).where(BanquetLead.tenant_id == tenant)
        if status:
            q = q.where(BanquetLead.status == status)
        return [_lead_view(x) for x in s.scalars(q.order_by(BanquetLead.created_at.desc())).all()][:200]


# ---------------------------------------------------------------- bookings
def _bk(s, tenant: str, ref: str) -> BanquetBooking:
    ref = (ref or "").strip()
    b = s.get(BanquetBooking, ref) if ref else None
    if b is None or b.tenant_id != tenant:
        b = s.scalars(select(BanquetBooking).where(BanquetBooking.tenant_id == tenant, BanquetBooking.number == ref.upper())).first()
    if b is None:
        raise BanquetError(f"Booking '{ref}' nahi mili.")
    return b


def _paid(b: BanquetBooking) -> float:
    return round(sum(float(p.get("amount") or 0) for p in _j(b.payments, []) if p.get("kind") != "refund"), 2)


def _refunded(b: BanquetBooking) -> float:
    return round(sum(float(p.get("amount") or 0) for p in _j(b.payments, []) if p.get("kind") == "refund"), 2)


def _clean_menu(s, tenant: str, menu: Any) -> list[dict]:
    out = []
    for m in menu or []:
        if isinstance(m, str):
            m = {"package": m}
        if not isinstance(m, dict):
            continue
        p = _pkg(s, tenant, str(m.get("package_id") or m.get("package") or m.get("name") or ""))
        out.append({"package_id": p.id, "plates": _int(m.get("plates"))})
    return out


def _clean_extras(s, tenant: str, items: Any, actor: str) -> list[dict]:
    out = []
    rows = s.scalars(select(BanquetExtra).where(BanquetExtra.tenant_id == tenant)).all()
    for m in items or []:
        if isinstance(m, str):
            m = {"name": m}
        if not isinstance(m, dict):
            continue
        ref = str(m.get("extra_id") or m.get("extra") or m.get("name") or "").strip()
        x = next((e for e in rows if e.id == ref), None) or next((e for e in rows if e.name.lower() == ref.lower()), None) or \
            next((e for e in rows if ref and ref.lower() in e.name.lower()), None)
        price = _num(m.get("price"))
        if price is not None and not is_owner(actor):
            raise BanquetError("Naya daam sirf owner bata sakti hain.")
        out.append({"extra_id": x.id if x else "", "name": x.name if x else R.clean(ref, 120), "qty": _num(m.get("qty")) or 1,
                    "price": price, "nights": _int(m.get("nights"))})
    return out


def _booking_view(s, b: BanquetBooking, full: bool = False) -> dict:
    h = s.get(BanquetHall, b.hall_id) if b.hall_id else None
    st = _st(s, b.tenant_id)
    sl = _slots(st).get(b.slot, {})
    ev = _date(b.day)
    v = {"id": b.id, "number": b.number, "lead_id": b.lead_id, "hall_id": b.hall_id, "hall": h.name if h else "",
         "hall_kind": h.kind if h else "", "day": b.day, "slot": b.slot, "slot_label": R.SLOT_LABEL.get(b.slot, b.slot),
         "time": f"{sl.get('from', '')}-{sl.get('to', '')}", "event_type": b.event_type, "event_label": R.EVENT_LABEL.get(b.event_type, ""),
         "client": b.client, "phone": b.phone, "email": b.email, "client_gstin": b.client_gstin, "guests": b.guests,
         "guarantee": b.guarantee, "final_count": b.final_count, "actual_count": b.actual_count, "locked": b.locked,
         "lock_date": R.lock_date(ev, st.lock_days).isoformat() if ev else "", "status": b.status,
         "status_label": STATUS.get(b.status, b.status), "hold_until": _aware(b.hold_until).isoformat() if b.hold_until else "",
         "discount": b.discount, "discount_note": b.discount_note, "paid": _paid(b), "refunded": _refunded(b),
         "paid_text": _rs(_paid(b)), "forgotten": b.forgotten}
    if full:
        q = _quote(s, b.tenant_id, b)
        v.update({"menu": _menu_view(s, b), "extras": _j(b.extras, []), "hall_rent": b.hall_rent, "quote": q,
                  "payments": _j(b.payments, []), "stages": _stage_rows(s, b, q), "bill": _j(b.bill, {}),
                  "beo_notes": b.beo_notes, "timeline": _j(b.timeline, []), "notes": b.notes, "cancel": _j(b.cancel, {}),
                  "log": _j(b.log, [])[-30:], "noise": R.noise_note(h.kind if h else "hall", sl.get("to", "23:00"), st.music_end),
                  "cancel_lines": R.policy_lines(_j(b.cancel, {}).get("policy") or _policy_of(st)),
                  "cards": [_card_view(c) for c in s.scalars(select(BanquetCard).where(BanquetCard.booking_id == b.id)
                                                             .order_by(BanquetCard.created_at.desc())).all()][:20]})
    return v


def _menu_view(s, b: BanquetBooking) -> list[dict]:
    out = []
    for m in _j(b.menu, []):
        p = s.get(BanquetPackage, m.get("package_id"))
        if p:
            out.append({**_pkg_view(p), "plates": m.get("plates")})
    return out


_BK_KEYS = ("hall", "day", "slot", "event_type", "client", "phone", "email", "client_gstin", "guests", "guarantee", "menu", "extras",
            "hall_rent", "notes", "beo_notes", "timeline")


def booking_save(tenant: str, booking: str = "", lead: str = "", actor: str = "owner", conv: str = "", **kw: Any) -> dict:
    """New draft booking (from an enquiry or fresh) or an update. Money-side changes after the quote make waiting cards stale."""
    t0 = today(tenant)
    with _LOCK, session() as s:
        st = _st(s, tenant)
        if booking:
            b = _bk(s, tenant, booking)
            if b.status in ("done", "cancelled"):
                raise BanquetError(f"{b.number} '{STATUS[b.status]}' hai: badlaav nahi.")
        else:
            st.bk_seq += 1
            b = BanquetBooking(tenant_id=tenant, number=f"B-{st.bk_seq:04d}", conv=conv)
            s.add(b)
            if lead:
                x = _lead(s, tenant, lead)
                b.lead_id, b.client, b.phone = x.id, x.name, x.phone
                b.event_type, b.guests = x.event_type or "other", x.guests
                if x.day:
                    b.day = x.day
                if x.slot:
                    b.slot = x.slot
                x.booking_id = b.id
        if "client" in kw and kw["client"]:
            b.client = R.clean(kw["client"], 120)
        if "phone" in kw and kw["phone"]:
            p = R.phone(kw["phone"])
            if not p:
                raise BanquetError("Phone 10 ankon ka mobile number chahiye.")
            b.phone = p
        if "email" in kw and kw["email"] is not None:
            b.email = R.clean(kw["email"], 120)
        if "client_gstin" in kw and kw["client_gstin"]:
            from ..india.money import gstin_ok
            g = str(kw["client_gstin"]).strip().upper()
            if not gstin_ok(g):
                raise BanquetError("Client ka GSTIN sahi nahi lagta.")
            b.client_gstin = g
        if "event_type" in kw and kw["event_type"]:
            et = kw["event_type"] if kw["event_type"] in R.EVENT_LABEL else (R.event_of(kw["event_type"]) or "other")
            b.event_type = et
        moving = False
        nh, nd, ns = b.hall_id, b.day, b.slot
        if kw.get("hall"):
            nh = _hall(s, tenant, str(kw["hall"])).id
        if kw.get("day"):
            d = _date(kw["day"]) or R.date_of(kw["day"], t0)
            if d is None:
                raise BanquetError("Tareekh samajh nahi aayi.")
            if d < t0:
                raise BanquetError("Beeti tareekh par booking nahi.")
            nd = d.isoformat()
        if kw.get("slot"):
            ns = R.slot_of(kw["slot"]) or ""
            if not ns:
                raise BanquetError("Slot: subah / shaam / pura din.")
        if (nh, nd, ns) != (b.hall_id, b.day, b.slot):
            moving = b.status in ("hold", "confirmed")
            if moving:
                cl = _clashes(s, tenant, nh, nd, ns, b.id)
                if cl:
                    raise BanquetError(f"Wahan pehle se: {_clash_say(s, cl)}. Double booking nahi hogi.")
                if b.status == "confirmed" and not is_owner(actor):
                    raise BanquetError("Pakki booking ki tareekh / hall sirf owner badal sakti hain.")
                for blk in s.scalars(select(BanquetBlock).where(BanquetBlock.booking_id == b.id, BanquetBlock.active.is_(True))).all():
                    blk.hall_id, blk.day, blk.slot = nh, nd, ns
            b.hall_id, b.day, b.slot = nh, nd, ns
        for k in ("guests", "guarantee"):
            if k in kw and kw[k] not in (None, ""):
                n = _int(kw[k])
                if n is None:
                    raise BanquetError(f"{k} number chahiye.")
                setattr(b, k, n)
        if "menu" in kw and kw["menu"] is not None:
            b.menu = _dump(_clean_menu(s, tenant, kw["menu"]))
        if "extras" in kw and kw["extras"] is not None:
            b.extras = _dump(_clean_extras(s, tenant, kw["extras"], actor))
        if "hall_rent" in kw and kw["hall_rent"] is not None:
            b.hall_rent = bool(kw["hall_rent"])
        for k in ("notes", "beo_notes"):
            if k in kw and kw[k]:
                setattr(b, k, R.clean(kw[k], 2000))
        if "timeline" in kw and isinstance(kw["timeline"], list):
            b.timeline = _dump([{"at": R.hhmm(x.get("at"), ""), "what": R.clean(x.get("what"), 120)}
                                for x in kw["timeline"] if isinstance(x, dict) and x.get("what")][:30])
        h = s.get(BanquetHall, b.hall_id) if b.hall_id else None
        warn = []
        g = b.final_count or b.guests
        if h and g and g > max(h.seated, h.floating):
            warn.append(f"{g} log {h.name} ki capacity ({h.seated} baithe / {h.floating} khade) se zyada: fire NOC ki seema dekhiye.")
        _log(b, "Booking badli" if booking else "Booking bani", actor_name(tenant, actor))
        s.flush()
        v = _booking_view(s, b, full=True)
    say = f"{v['number']} {v['client'] or ''}: {v['hall'] or 'hall?'} {v['day'] or 'tareekh?'} {v['slot_label']}."
    if moving:
        say += " Hall / tareekh badli (clash nahi)."
    if warn:
        say += " " + " ".join(warn)
    return {"booking": v, "warnings": warn, "say": say}


def hold(tenant: str, booking: str, hours=None, actor: str = "owner", conv: str = "") -> dict:
    """Tentative hold: the slot is kept for her hold_hours and then frees itself. Clash = refused."""
    with _LOCK, session() as s:
        st = _st(s, tenant)
        b = _bk(s, tenant, booking)
        if b.status not in ("draft", "hold"):
            raise BanquetError(f"{b.number} '{STATUS[b.status]}' hai.")
        if not (b.hall_id and b.day and b.slot):
            raise BanquetError("Hold ke liye hall, tareekh aur slot chahiye.")
        if _date(b.day) < today(tenant):
            raise BanquetError("Beeti tareekh.")
        hrs = _int(hours) or st.hold_hours
        if not is_owner(actor):
            hrs = min(hrs, st.hold_hours)
        hrs = max(1, min(hrs, 24 * 14))
        cl = _clashes(s, tenant, b.hall_id, b.day, b.slot, b.id)
        if cl:
            raise BanquetError(f"Yeh slot pehle se: {_clash_say(s, cl)}. Double booking nahi hogi; doosra hall / slot dekhiye.")
        until = clock() + timedelta(hours=hrs)
        blk = s.scalars(select(BanquetBlock).where(BanquetBlock.booking_id == b.id, BanquetBlock.active.is_(True))).first()
        if blk is None:
            blk = BanquetBlock(tenant_id=tenant, hall_id=b.hall_id, day=b.day, slot=b.slot, kind="hold", booking_id=b.id)
            s.add(blk)
        blk.expires_at = until
        b.status, b.hold_until = "hold", until
        if b.lead_id:
            x = s.get(BanquetLead, b.lead_id)
            if x and x.status not in ("booked", "lost"):
                x.status = "hold"
        _log(b, f"Hold {hrs} ghante", actor_name(tenant, actor))
        v = _booking_view(s, b)
    loc = _aware(until).astimezone(_tz(tenant))
    return {"booking": v, "say": f"{v['number']} {v['hall']} {v['day']} {v['slot_label']}: hold {loc.strftime('%d-%m %H:%M')} tak. "
                                 "Pakki booking aapki haan se hogi."}


def release(tenant: str, booking: str, actor: str = "owner") -> dict:
    with _LOCK, session() as s:
        b = _bk(s, tenant, booking)
        if b.status == "confirmed" and not is_owner(actor):
            raise BanquetError("Pakki booking chhodna = cancel: sirf owner.")
        if b.status == "confirmed":
            raise BanquetError("Pakki booking ke liye 'cancel' kijiye (refund policy ke saath).")
        for blk in s.scalars(select(BanquetBlock).where(BanquetBlock.booking_id == b.id, BanquetBlock.active.is_(True))).all():
            blk.active = False
        if b.status == "hold":
            b.status, b.hold_until = "draft", None
        _log(b, "Hold chhoda", actor_name(tenant, actor))
        v = _booking_view(s, b)
    return {"booking": v, "say": f"{v['number']}: hold chhoda, slot khaali."}


# ---------------------------------------------------------------- quotation maths (by code, HER numbers only)
def _quote(s, tenant: str, b: BanquetBooking, actual: bool = False) -> dict:
    st = _st(s, tenant)
    h = s.get(BanquetHall, b.hall_id) if b.hall_id else None
    food_pct = R.food_gst(bool(st.specified), st.gst_food)
    lines, blanks, notes = [], [], []
    menu = _j(b.menu, [])
    count = R.plates_billed(b.guests, b.guarantee, b.final_count, b.actual_count if actual else None)
    for m in menu:
        p = s.get(BanquetPackage, m.get("package_id"))
        if p is None:
            continue
        plates = m.get("plates") if len(menu) > 1 else (m.get("plates") or count)
        if len(menu) == 1 and plates and p.min_plates and plates < p.min_plates:
            notes.append(f"{p.name}: kam se kam {p.min_plates} plate (aapka niyam) lagaya.")
            plates = p.min_plates
        if not plates:
            blanks.append(f"{p.name}: kitni plate?")
        amt = round(plates * p.price, 2) if plates else None
        lines.append({"kind": "food", "name": f"{p.name} ({R.DIET_LABEL.get(p.diet, p.diet)})", "qty": plates, "unit": "plate",
                      "rate": p.price, "amount": amt, "gst_pct": food_pct, "sac": "9963"})
    with_food = bool(menu)
    if b.hall_rent and h is not None:
        rent = h.rent_full if b.slot == "full" and h.rent_full is not None else (h.rent if b.slot != "full" else None)
        if rent is None and b.slot == "full" and h.rent is not None:
            blanks.append(f"{h.name}: pure din ka kiraya?")
        elif rent is None and not with_food:
            blanks.append(f"{h.name}: kiraya?")
        if rent is not None:
            lines.append({"kind": "hall", "name": f"{h.name} kiraya ({R.SLOT_LABEL.get(b.slot, b.slot)})", "qty": 1, "unit": "slot",
                          "rate": rent, "amount": rent, "gst_pct": food_pct if with_food else st.gst_hall,
                          "sac": "9963" if with_food else "997212"})
    elif not h:
        blanks.append("Hall chuniye.")
    for e in _j(b.extras, []):
        x = s.get(BanquetExtra, e.get("extra_id")) if e.get("extra_id") else None
        price = e.get("price") if e.get("price") is not None else (x.price if x else None)
        unit = x.unit if x else "nos"
        qty = float(e.get("qty") or 1)
        if unit == "room_night":
            qty = qty * (e.get("nights") or 1)
        if unit == "plate":
            qty = count or 0
        pct = x.gst_pct if x and x.gst_pct is not None else (R.room_gst(price or 0) if (x and x.kind == "rooms") else st.gst_extra)
        if price is None:
            blanks.append(f"{e.get('name')}: daam?")
        lines.append({"kind": "extra", "name": e.get("name") or (x.name if x else "Extra"), "qty": qty, "unit": unit, "rate": price,
                      "amount": round(qty * price, 2) if price is not None else None, "gst_pct": pct,
                      "sac": "9963" if x and x.kind == "rooms" else "9985"})
    if not lines:
        blanks.append("Menu package ya hall kiraya: kuch to chahiye.")
    sub = round(sum(ln["amount"] or 0 for ln in lines), 2)
    disc = min(round(b.discount or 0, 2), sub)
    groups: dict[float, float] = {}
    for ln in lines:
        if ln["amount"]:
            groups[ln["gst_pct"]] = groups.get(ln["gst_pct"], 0) + ln["amount"]
    gst = []
    left = disc
    keys = sorted(groups)
    for i, pct in enumerate(keys):
        base = groups[pct]
        cut = round(disc * base / sub, 2) if sub and i < len(keys) - 1 else round(left, 2)
        left -= cut
        taxable = round(base - cut, 2)
        sp = R.gst_split(taxable, pct)
        gst.append({"pct": pct, "base": taxable, **sp})
    tax = round(sum(g["tax"] for g in gst), 2)
    total = round(sub - disc + tax, 2)
    words = ""
    try:
        from ..india.money import rupees_words
        words = rupees_words(total, "en")
    except Exception:
        pass
    if b.guarantee and count and b.guarantee > (b.final_count or b.guests or 0):
        notes.append(f"Minimum guarantee {b.guarantee} plate ka bill banega, chahe log kam aayen.")
    return {"lines": lines, "subtotal": sub, "discount": disc, "gst": gst, "tax": tax, "total": total,
            "total_text": _rs(total) if not blanks else "[khaali jagah]", "words": words, "plates": count, "blanks": blanks,
            "notes": notes, "intra": True, "specified": bool(st.specified),
            "gst_note": "Function aapke venue par: place of supply = venue (IGST Act s.12(3)(c)), isliye CGST + SGST."}


def quote(tenant: str, booking: str) -> dict:
    with session() as s:
        b = _bk(s, tenant, booking)
        return {"booking": b.number, "quote": _quote(s, tenant, b)}


def _stage_rows(s, b: BanquetBooking, q: dict | None = None) -> list[dict]:
    snap = _j(b.stages, [])
    if snap:
        return snap
    st = _st(s, b.tenant_id)
    q = q or _quote(s, b.tenant_id, b)
    tmpl = _stages_of(st)
    ev = _date(b.day)
    booked = _aware(b.created_at).astimezone(_tz(b.tenant_id)).date() if b.created_at else today(b.tenant_id)
    amts = R.split_amount(q["total"], tmpl) if not q["blanks"] else [None] * len(tmpl)
    return [{"label": t["label"], "pct": t["pct"], "amount": a, "due": R.stage_due(ev, booked, t.get("days_before")).isoformat() if ev else "",
             "requested": False} for t, a in zip(tmpl, amts)]


# ---------------------------------------------------------------- cards (HER tap only)
def _card_view(c: BanquetCard) -> dict:
    sh = _j(c.show, {})
    return {"id": c.id, "kind": c.kind, "title": CARD_TITLE.get(c.kind, c.kind), "status": c.status, "hash": c.hash,
            "show": {k: v for k, v in sh.items() if not k.startswith("_")}, "booking_id": c.booking_id,
            "money": c.kind in MONEY_CARDS, "asked_by": c.asked_by, "reason": c.reason, "result": _j(c.result, {}),
            "created_at": _aware(c.created_at).isoformat() if c.created_at else ""}


def _show(s, tenant: str, kind: str, b: BanquetBooking | None, inp: dict) -> dict:
    """What the card shows, rebuilt from the state NOW (the hash covers it: any change after the card = stale)."""
    if b is None:
        return {"kind": kind, **inp}
    st = _st(s, tenant)
    h = s.get(BanquetHall, b.hall_id) if b.hall_id else None
    base = {"booking": b.number, "client": b.client, "phone": b.phone, "hall": h.name if h else "", "day": b.day,
            "slot": R.SLOT_LABEL.get(b.slot, b.slot), "event": R.EVENT_LABEL.get(b.event_type, "")}
    if kind == "quote":
        q = _quote(s, tenant, b)
        return {**base, "lines": q["lines"], "discount": q["discount"], "gst": q["gst"], "total": q["total"], "total_text": q["total_text"],
                "plates": q["plates"], "guarantee": b.guarantee, "valid_until": inp.get("valid_until", ""),
                "cancel_lines": R.policy_lines(_policy_of(st)), "_in": inp}
    if kind == "contract":
        q = _quote(s, tenant, b)
        ev = _date(b.day)
        return {**base, "total": q["total"], "total_text": q["total_text"], "stages": _stage_rows(s, b, q),
                "cancel_lines": R.policy_lines(_policy_of(st)), "policy": _policy_of(st), "guarantee": b.guarantee,
                "lock_date": R.lock_date(ev, st.lock_days).isoformat() if ev else "", "terms": st.terms,
                "music": R.noise_note(h.kind if h else "hall", _slots(st)[b.slot]["to"] if b.slot in R.SLOTS else "23:00", st.music_end),
                "_in": inp}
    if kind == "confirm":
        q = _quote(s, tenant, b)
        return {**base, "total": q["total"], "total_text": q["total_text"], "paid": _paid(b), "paid_text": _rs(_paid(b)),
                "status": b.status, "hold_until": _aware(b.hold_until).isoformat() if b.hold_until else "", "_in": inp}
    if kind == "discount":
        q = _quote(s, tenant, b)
        return {**base, "amount": inp.get("amount"), "amount_text": _rs(inp.get("amount")), "reason": inp.get("reason", ""),
                "subtotal": q["subtotal"], "current_discount": b.discount, "_in": inp}
    if kind == "refund":
        return {**base, "amount": inp.get("amount"), "amount_text": _rs(inp.get("amount")), "pct": inp.get("pct"),
                "paid": _paid(b) - _refunded(b), "days_before": inp.get("days_before"), "why": inp.get("why", ""),
                "status": b.status, "_in": inp}
    if kind == "pay":
        upi, _ = _upi_of(tenant)
        return {**base, "label": inp.get("label", ""), "amount": inp.get("amount"), "amount_text": _rs(inp.get("amount")), "upi": upi,
                "paid": _paid(b), "_in": inp}
    if kind == "bill":
        q = _quote(s, tenant, b, actual=True)
        paid = _paid(b) - _refunded(b)
        return {**base, "lines": q["lines"], "discount": q["discount"], "gst": q["gst"], "total": q["total"], "total_text": q["total_text"],
                "plates": q["plates"], "actual": b.actual_count, "guarantee": b.guarantee, "paid": paid,
                "balance": round(q["total"] - paid, 2), "balance_text": _rs(round(q["total"] - paid, 2)), "_in": inp}
    if kind == "message":
        return {**base, "text": inp.get("text", ""), "_in": inp}
    raise BanquetError(f"card '{kind}' nahi pehchana.")


def _make_card(tenant: str, kind: str, booking_ref: str, inp: dict, actor: str = "owner", conv: str = "") -> dict:
    with _LOCK, session() as s:
        b = _bk(s, tenant, booking_ref) if booking_ref else None
        show = _show(s, tenant, kind, b, inp)
        h = R.digest(show)
        old = s.scalars(select(BanquetCard).where(BanquetCard.tenant_id == tenant, BanquetCard.kind == kind,
                                                  BanquetCard.booking_id == (b.id if b else ""),
                                                  BanquetCard.status == "waiting")).all()
        for o in old:
            if o.hash == h:
                return {"card": _card_view(o), "status": "needs_tap", "existing": True,
                        "say": "Yahi card pehle se aapki haan ka intezaar kar raha hai."}
            o.status = "stale"
        c = BanquetCard(tenant_id=tenant, booking_id=b.id if b else "", kind=kind, show=_dump(show), hash=h,
                        asked_by=actor_name(tenant, actor), conv=conv or (b.conv if b else ""))
        s.add(c)
        s.flush()
        v = _card_view(c)
        cv = c.conv
    say = f"{CARD_TITLE[kind]}: {v['show'].get('booking', '')} aapki haan ka card bheja hai."
    _publish(tenant, "banquet_card", {"card": v, "say": say}, cv)
    return {"card": v, "status": "needs_tap", "say": say}


def card_view(tenant: str, card_id: str) -> dict:
    with session() as s:
        c = s.get(BanquetCard, card_id)
        if c is None or c.tenant_id != tenant:
            raise BanquetError("Card nahi mila.")
        return _card_view(c)


def cards(tenant: str, status: str = "waiting") -> list[dict]:
    with session() as s:
        q = select(BanquetCard).where(BanquetCard.tenant_id == tenant)
        if status:
            q = q.where(BanquetCard.status == status)
        return [_card_view(c) for c in s.scalars(q.order_by(BanquetCard.created_at.desc())).all()][:100]


def card_challenge(tenant: str, card_id: str) -> dict:
    """approvekey's message format (kind 'banquet'): her phone signs this money card (discount / refund) as it is NOW."""
    from .. import approvekey as ak
    c = card_view(tenant, card_id)
    if c["status"] != "waiting" or c["kind"] not in MONEY_CARDS:
        raise BanquetError("Yeh card ab baaki nahi hai.")
    nonce = secrets.token_urlsafe(18)
    exp = datetime.now(timezone.utc) + ak.CHALLENGE_TTL
    msg = f"hoola-approve|v1|{tenant}|banquet|{card_id}|{c['hash']}|{nonce}|{int(exp.timestamp())}"
    with session() as s:
        ch = ak.ApproveChallenge(tenant_id=tenant, kind="banquet", target=card_id, digest=c["hash"], message=msg, expires_at=exp)
        s.add(ch)
        s.flush()
        chid = ch.id
    sh = c["show"]
    return {"challenge_id": chid, "message": msg, "show": {"title": f"{c['title']} {sh.get('booking', '')}",
                                                           "amount": sh.get("amount_text", ""), "payee": sh.get("client", "")},
            "expires_at": exp.isoformat()}


def _verify_fingerprint(tenant: str, card_id: str, digest: str, proof: dict | None) -> None:
    from .. import approvekey as ak
    if not proof:
        raise BanquetError("fingerprint_needed")
    with session() as s:
        ak._settle(s, tenant)
        ok = ak._check(s, tenant, "banquet", card_id, proof, digest)
    if not ok:
        raise BanquetError("fingerprint_invalid")


def decide(tenant: str, card_id: str, yes: bool, card_hash: str = "", reason: str = "", proof: dict | None = None,
           by_tap: bool = False, conv: str = "") -> dict:
    """ONLY from the app's API (her tap). The card's hash must still match the state NOW; money cards need her fingerprint once
    a phone key is active."""
    if not by_tap:
        raise BanquetError("Yeh sirf aapke tap se (app ka card).")
    with session() as s:
        c = s.get(BanquetCard, card_id)
        if c is None or c.tenant_id != tenant:
            raise BanquetError("Card nahi mila.")
        if c.status != "waiting":
            return {"card": _card_view(c), "say": f"Yeh card pehle hi '{c.status}' hai."}
        b = s.get(BanquetBooking, c.booking_id) if c.booking_id else None
        inp = _j(c.show, {}).get("_in", {})
        try:
            now_hash = R.digest(_show(s, tenant, c.kind, b, inp))
        except BanquetError:
            now_hash = ""
        ch = c.hash
        bad = not card_hash or card_hash != ch or now_hash != ch
        kind = c.kind
    if bad:
        if now_hash != ch:
            with _LOCK, session() as s:
                s.get(BanquetCard, card_id).status = "stale"
        raise BanquetError("Card ke baad kuch badal gaya; naya card dekhiye.")
    if yes and kind in MONEY_CARDS:
        from .. import approvekey as ak
        if ak.active_on(tenant):
            _verify_fingerprint(tenant, card_id, card_hash, proof)
    if not yes:
        with _LOCK, session() as s:
            c = s.get(BanquetCard, card_id)
            c.status, c.reason, c.decided_at = "rejected", R.clean(reason, 300), now()
            v = _card_view(c)
        return {"card": v, "say": f"{CARD_TITLE[kind]}: nahi."}
    fn = {"quote": _do_quote, "contract": _do_contract, "confirm": _do_confirm, "discount": _do_discount, "refund": _do_refund,
          "pay": _do_pay, "bill": _do_bill, "message": _do_message}[kind]
    out = fn(tenant, card_id, conv)
    with _LOCK, session() as s:
        c = s.get(BanquetCard, card_id)
        if c.status == "waiting":
            c.status, c.decided_at = "approved", now()
        c.result = _dump({k: v for k, v in out.items() if k in ("draft", "file_id", "say")})
        out["card"] = _card_view(c)
    return out


def _mark_paid(rows: list[dict], paid_total: float) -> None:
    left = paid_total
    for r in rows:
        amt = float(r.get("amount") or 0)
        r["paid"] = left >= amt - 0.5
        left -= amt


def _draft(phone: str, text: str, **extra) -> dict:
    return {"text": text, "wa": _wa(phone, text), "sms": _sms(phone, text), **extra}


def _card_ctx(card_id: str) -> tuple[dict, str]:
    with session() as s:
        c = s.get(BanquetCard, card_id)
        return _j(c.show, {}), c.booking_id


def _do_quote(tenant: str, card_id: str, conv: str) -> dict:
    sh, bid = _card_ctx(card_id)
    pdf = quote_pdf(tenant, bid, final=True, valid_until=sh.get("valid_until", ""))
    with _LOCK, session() as s:
        b = s.get(BanquetBooking, bid)
        st = _st(s, tenant)
        b.quote_no += 1
        b.quote_sent = R.digest(sh)
        _log(b, "Quotation aapki haan se final", "Owner")
        if b.lead_id:
            x = s.get(BanquetLead, b.lead_id)
            if x and x.status in ("new", "contacted", "visit"):
                x.status = "quoted"
        num, phone, client, venue = b.number, b.phone, b.client, st.venue
    f = _store(tenant, f"{num}_quotation.pdf", pdf, "application/pdf", conv, f"{num} quotation")
    text = (f"Namaste {client} ji, {venue or 'hamare venue'} ki taraf se {sh.get('event') or 'function'} ({sh.get('day')}, "
            f"{sh.get('slot')}, {sh.get('hall')}) ka quotation {num}: kul {sh.get('total_text')} (GST samet)"
            + (f", {sh['valid_until']} tak valid" if sh.get("valid_until") else "") + ". Cancellation / refund ki shartein PDF mein hain. "
            "Hall abhi pakka nahi: advance aur booking ke baad hi pakka hoga.")
    return {"draft": _draft(phone, text, file_id=f.get("file_id", "")), "file_id": f.get("file_id", ""),
            "say": f"{num} quotation final PDF bana; message draft taiyaar: aap khud bhejiye (PDF saath lagaiye)."}


def _do_contract(tenant: str, card_id: str, conv: str) -> dict:
    sh, bid = _card_ctx(card_id)
    pdf = contract_pdf(tenant, bid, final=True)
    with _LOCK, session() as s:
        b = s.get(BanquetBooking, bid)
        b.contract_ok = R.digest(sh)
        cx = _j(b.cancel, {})
        cx["policy"] = sh.get("policy") or []
        b.cancel = _dump(cx)
        _log(b, "Booking terms aapki haan se final", "Owner")
        num, phone, client = b.number, b.phone, b.client
    f = _store(tenant, f"{num}_booking_terms.pdf", pdf, "application/pdf", conv, f"{num} booking terms")
    text = (f"Namaste {client} ji, booking {num} ki shartein (payment schedule, cancellation / refund, final guest count ki "
            f"tareekh {sh.get('lock_date')}) PDF mein bhej rahe hain. Padh kar haan likh dijiye.")
    return {"draft": _draft(phone, text, file_id=f.get("file_id", "")), "file_id": f.get("file_id", ""),
            "say": f"{num} booking terms final; draft taiyaar, aap bhejiye."}


def _do_confirm(tenant: str, card_id: str, conv: str) -> dict:
    with _LOCK:                                                              # check + block under one lock
        return _confirm_now(tenant, card_id)


def _confirm_now(tenant: str, card_id: str) -> dict:
    with _LOCK, session() as s:
        c = s.get(BanquetCard, card_id)
        b = s.get(BanquetBooking, c.booking_id)
        if b.status not in ("draft", "hold"):
            raise BanquetError(f"{b.number} '{STATUS[b.status]}' hai.")
        cl = _clashes(s, tenant, b.hall_id, b.day, b.slot, b.id)
        why = f"Ab yeh slot khaali nahi: {_clash_say(s, cl)}. Double booking nahi hogi." if cl else ""
    if why:
        with _LOCK, session() as s:
            s.get(BanquetCard, card_id).status = "stale"
        raise BanquetError(why)
    with _LOCK, session() as s:
        c = s.get(BanquetCard, card_id)
        b = s.get(BanquetBooking, c.booking_id)
        for blk in s.scalars(select(BanquetBlock).where(BanquetBlock.booking_id == b.id, BanquetBlock.active.is_(True))).all():
            blk.active = False
        s.add(BanquetBlock(tenant_id=tenant, hall_id=b.hall_id, day=b.day, slot=b.slot, kind="confirmed", booking_id=b.id))
        q = _quote(s, tenant, b)
        b.stages = _dump(_stage_rows(s, b, q))
        cx = _j(b.cancel, {})
        cx.setdefault("policy", _policy_of(_st(s, tenant)))
        b.cancel = _dump(cx)
        b.status, b.hold_until = "confirmed", None
        if b.lead_id:
            x = s.get(BanquetLead, b.lead_id)
            if x:
                x.status = "booked"
        _log(b, "Pakki booking (aapki haan)", "Owner")
        v = _booking_view(s, b)
        paid = _paid(b)
    note = "" if paid else " Abhi koi advance darj nahi: paise maangne ka card bana sakte hain."
    text = (f"Namaste {v['client']} ji, aapki booking {v['number']} pakki: {v['hall']}, {v['day']} {v['slot_label']} ({v['time']}). "
            f"Final mehmaan sankhya {v['lock_date']} tak bata dijiye. Dhanyavaad.")
    return {"booking": v, "draft": _draft(v["phone"], text), "say": f"{v['number']} pakki ho gayi (slot block).{note} Client ko draft taiyaar."}


def _do_discount(tenant: str, card_id: str, conv: str) -> dict:
    sh, bid = _card_ctx(card_id)
    with _LOCK, session() as s:
        b = s.get(BanquetBooking, bid)
        b.discount = float(sh.get("amount") or 0)
        b.discount_note = R.clean(sh.get("reason"), 200)
        if b.status == "confirmed" and _j(b.stages, []):
            old_rows = {r["label"]: r for r in _j(b.stages, [])}
            b.stages = ""                                                    # re-split on the new total
            rows = _stage_rows(s, b)
            _mark_paid(rows, _paid(b))
            for r in rows:
                r["requested"] = bool(old_rows.get(r["label"], {}).get("requested"))
            b.stages = _dump(rows)
        _log(b, f"Discount {_rs(b.discount)} (aapki haan)", "Owner")
        v = _booking_view(s, b)
    return {"booking": v, "say": f"{v['number']}: discount {_rs(v['discount'])} laga. Naya quotation card bana sakte hain."}


def _do_refund(tenant: str, card_id: str, conv: str) -> dict:
    sh, bid = _card_ctx(card_id)
    with _LOCK, session() as s:
        b = s.get(BanquetBooking, bid)
        cx = _j(b.cancel, {})
        cx["refund_ok"] = {"amount": sh.get("amount"), "card": card_id, "at": now().isoformat(), "sent": False}
        b.cancel = _dump(cx)
        _log(b, f"Refund {_rs(sh.get('amount'))} manzoor (aapki haan); aap khud bhejengi", "Owner")
        num, phone, client = b.number, b.phone, b.client
    text = (f"Namaste {client} ji, booking {num} ka refund {sh.get('amount_text')} manzoor hua hai; hum jaldi aapke khate / UPI mein "
            "bhej denge. Hum kabhi OTP / PIN nahi maangte.")
    return {"draft": _draft(phone, text), "say": f"{num}: refund {sh.get('amount_text')} manzoor. Paise aap apne bank / UPI app se "
                                                 "bhejiye, phir 'refund bhej diya' darj kijiye (Hoola paise nahi bhejta)."}


def _do_pay(tenant: str, card_id: str, conv: str) -> dict:
    sh, bid = _card_ctx(card_id)
    with _LOCK, session() as s:
        b = s.get(BanquetBooking, bid)
        rows = _j(b.stages, [])
        for r in rows:
            if r.get("label") == sh.get("label"):
                r["requested"] = True
        if rows:
            b.stages = _dump(rows)
        _log(b, f"Paise maange: {sh.get('label')} {sh.get('amount_text')}", "Owner")
        num, phone, client = b.number, b.phone, b.client
    with session() as s:
        venue = _st(s, tenant).venue
    link = _upi(tenant, float(sh.get("amount") or 0), f"{num} {sh.get('label')}")
    text = (f"Namaste {client} ji, booking {num} ({sh.get('day')}) ki '{sh.get('label')}': {sh.get('amount_text')}."
            + (f" UPI se bhejiye: {link}" if link else "") + f" Dhanyavaad, {venue or ''}".rstrip(", ") + ". Hum kabhi OTP / PIN nahi maangte.")
    return {"draft": _draft(phone, text, upi=link), "say": "Message draft (UPI link aapke UPI ID ka) taiyaar: aap bhejiye. Paise mile to "
                                                          "'paise mile' darj kijiye; receipt wahin banegi."}


def _do_bill(tenant: str, card_id: str, conv: str) -> dict:
    sh, bid = _card_ctx(card_id)
    with _LOCK, session() as s:
        b = s.get(BanquetBooking, bid)
        b.bill = _dump({k: sh.get(k) for k in ("lines", "discount", "gst", "total", "plates", "paid", "balance")} |
                       {"card": card_id, "at": now().isoformat()})
        _log(b, f"Event ke baad ka bill {sh.get('total_text')} (aapki haan)", "Owner")
        num, phone, client = b.number, b.phone, b.client
    pdf = bill_pdf(tenant, bid)
    f = _store(tenant, f"{num}_bill.pdf", pdf, "application/pdf", conv, f"{num} bill")
    bal = float(sh.get("balance") or 0)
    link = _upi(tenant, bal, f"{num} final bill") if bal > 0 else ""
    text = (f"Namaste {client} ji, {num} ka final bill: kul {sh.get('total_text')}, jama {_rs(sh.get('paid'))}, "
            + (f"baaki {sh.get('balance_text')}." if bal > 0 else "kuch baaki nahi.") + (f" UPI: {link}" if link else ""))
    return {"draft": _draft(phone, text, file_id=f.get("file_id", ""), upi=link), "file_id": f.get("file_id", ""),
            "say": f"{num} bill PDF bana; draft taiyaar, aap bhejiye."}


def _do_message(tenant: str, card_id: str, conv: str) -> dict:
    sh, _bid = _card_ctx(card_id)
    return {"draft": _draft(sh.get("phone", ""), sh.get("text", "")), "say": "Message draft taiyaar: aap khud bhejiye."}


# ---------------------------------------------------------------- card requests (tools / app make these; never decide)
def quote_request(tenant: str, booking: str, actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        b = _bk(s, tenant, booking)
        st = _st(s, tenant)
        if b.status in ("done", "cancelled"):
            raise BanquetError(f"{b.number} '{STATUS[b.status]}' hai.")
        q = _quote(s, tenant, b)
        if q["blanks"]:
            raise BanquetError("Pehle khaali jagah bhariye: " + "; ".join(q["blanks"][:6]))
        if not (b.client and R.phone(b.phone)):
            raise BanquetError("Client ka naam aur mobile chahiye.")
        valid = (today(tenant) + timedelta(days=st.validity_days)).isoformat()
    return _make_card(tenant, "quote", booking, {"valid_until": valid}, actor, conv)


def contract_request(tenant: str, booking: str, actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        b = _bk(s, tenant, booking)
        q = _quote(s, tenant, b)
        if q["blanks"]:
            raise BanquetError("Pehle khaali jagah bhariye: " + "; ".join(q["blanks"][:6]))
        if b.status in ("done", "cancelled") or not (b.client and R.phone(b.phone)):
            raise BanquetError("Booking chalu ho aur client ka naam + mobile ho.")
    return _make_card(tenant, "contract", booking, {}, actor, conv)


def confirm_request(tenant: str, booking: str, actor: str = "owner", conv: str = "") -> dict:
    with _LOCK, session() as s:
        b = _bk(s, tenant, booking)
        if b.status not in ("draft", "hold"):
            raise BanquetError(f"{b.number} '{STATUS[b.status]}' hai.")
        if not (b.hall_id and b.day and b.slot and b.client and R.phone(b.phone)):
            raise BanquetError("Hall, tareekh, slot, client ka naam aur mobile chahiye.")
        cl = _clashes(s, tenant, b.hall_id, b.day, b.slot, b.id)
        if cl:
            raise BanquetError(f"Yeh slot pehle se: {_clash_say(s, cl)}. Double booking nahi hogi.")
    return _make_card(tenant, "confirm", booking, {}, actor, conv)


def discount_request(tenant: str, booking: str, amount=None, pct=None, reason: str = "", actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        b = _bk(s, tenant, booking)
        q = _quote(s, tenant, b)
        a = _num(amount)
        if a is None and _num(pct) is not None:
            a = round(q["subtotal"] * _num(pct) / 100.0, 2)
        if a is None or a <= 0:
            raise BanquetError("Discount kitna (rupaye ya %)?")
        if a > q["subtotal"]:
            raise BanquetError("Discount bill se zyada nahi.")
        if not str(reason or "").strip():
            raise BanquetError("Discount ki wajah likhiye.")
    return _make_card(tenant, "discount", booking, {"amount": a, "reason": R.clean(reason, 200)}, actor, conv)


def pay_request(tenant: str, booking: str, stage: str = "", amount=None, actor: str = "owner", conv: str = "") -> dict:
    with session() as s:
        b = _bk(s, tenant, booking)
        if b.status in ("cancelled", "done"):
            raise BanquetError(f"{b.number} '{STATUS[b.status]}' hai.")
        rows = _stage_rows(s, b)
        label, amt = "", _num(amount)
        if stage:
            r = next((x for x in rows if x["label"].lower() == stage.lower() or stage.lower() in x["label"].lower()), None)
            if r is None and stage.isdigit() and 0 < int(stage) <= len(rows):
                r = rows[int(stage) - 1]
            if r is None:
                raise BanquetError("Kisht nahi mili: " + " / ".join(x["label"] for x in rows))
            label, amt = r["label"], amt if amt is not None else r["amount"]
        else:
            label = "Bhugtaan"
        if amt is None or amt <= 0:
            raise BanquetError("Rakam chahiye (quotation mein khaali jagah to nahi?).")
        if not R.phone(b.phone):
            raise BanquetError("Client ka mobile chahiye.")
    return _make_card(tenant, "pay", booking, {"label": label, "amount": round(amt, 2)}, actor, conv)


def message_request(tenant: str, booking: str, text: str, actor: str = "owner", conv: str = "") -> dict:
    t = R.clean(text, 1500)
    if not t:
        raise BanquetError("Message ka text chahiye.")
    if re.search(r"\b(otp|pin|cvv|password)\b", t, re.I) and "nahi maangte" not in t.lower():
        raise BanquetError("OTP / PIN / password wala message nahi.")
    with session() as s:
        b = _bk(s, tenant, booking)
        if not R.phone(b.phone):
            raise BanquetError("Client ka mobile chahiye.")
    return _make_card(tenant, "message", booking, {"text": t}, actor, conv)


def bill_request(tenant: str, booking: str, actual=None, actor: str = "owner", conv: str = "") -> dict:
    with _LOCK, session() as s:
        b = _bk(s, tenant, booking)
        if b.status != "confirmed":
            raise BanquetError("Bill pakki booking ka hi.")
        if _date(b.day) and _date(b.day) > today(tenant):
            raise BanquetError("Event ke baad ka bill event ke din / baad.")
        if actual not in (None, ""):
            n = _int(actual)
            if n is None:
                raise BanquetError("Asal plate ginti number chahiye.")
            b.actual_count = n
        q = _quote(s, tenant, b, actual=True)
        if q["blanks"]:
            raise BanquetError("Khaali jagah: " + "; ".join(q["blanks"][:6]))
    return _make_card(tenant, "bill", booking, {"actual": actual}, actor, conv)


# ---------------------------------------------------------------- money she records (owner only), counts, cancel
def paid(tenant: str, booking: str, amount, mode: str = "upi", ref: str = "", day: str = "", actor: str = "owner") -> dict:
    """She says money came (her UPI app / cash / bank). A receipt number is made; GST on an advance for services is due when it is
    received (CGST s.13) - a receipt voucher (Rule 50) is her accountant's step."""
    if not is_owner(actor):
        raise BanquetError("Paise mile, yeh sirf owner darj karti hain.")
    a = _num(amount)
    if a is None or a <= 0:
        raise BanquetError("Kitne paise mile?")
    md = (mode or "upi").lower()
    if md not in ("upi", "cash", "bank", "cheque", "card"):
        md = "other"
    d = _date(day) or today(tenant)
    with _LOCK, session() as s:
        st = _st(s, tenant)
        b = _bk(s, tenant, booking)
        if b.status == "cancelled":
            raise BanquetError("Radd booking par paise nahi.")
        st.rc_seq += 1
        rc = f"R/{_fy(d)}/{st.rc_seq:04d}"
        pays = _j(b.payments, [])
        pays.append({"id": new_id("bpm"), "receipt": rc, "amount": round(a, 2), "mode": md, "ref": R.clean(ref, 40)[-12:],
                     "day": d.isoformat(), "kind": "in"})
        b.payments = _dump(pays)
        rows = _j(b.stages, [])
        _mark_paid(rows, _paid(b))
        if rows:
            b.stages = _dump(rows)
        warn = []
        if md == "cash" and a >= 200000:
            warn.append("Ek din mein ek vyakti se Rs 2 lakh+ cash lena mana hai (Income-tax Act 2025 s.221, purana 269ST).")
        _log(b, f"Paise mile {_rs(a)} ({md}) receipt {rc}", "Owner")
        v = _booking_view(s, b)
    return {"booking": v, "receipt": rc, "warnings": warn,
            "say": f"{v['number']}: {_rs(a)} mile, receipt {rc}. Kul jama {v['paid_text']}." + (" " + " ".join(warn) if warn else "")}


def receipt_pdf(tenant: str, booking: str, receipt: str) -> bytes:
    with session() as s:
        b = _bk(s, tenant, booking)
        st = _st(s, tenant)
        p = next((x for x in _j(b.payments, []) if x.get("receipt") == receipt), None)
        if p is None:
            raise BanquetError("Receipt nahi mili.")
        blocks = _head(st, f"Receipt {receipt}") + [
            ("p", f"Received from {b.client} for booking {b.number} ({b.day}, {R.SLOT_LABEL.get(b.slot, b.slot)})."),
            ("table", [["Date", "Mode", "Ref", "Amount"], [p["day"], p["mode"], p.get("ref", ""), _pdf_rs(p["amount"])]], [90, 70, 120, 120]),
            ("p", "Advance / part payment against the booking. Tax invoice at the time of supply / as per GST rules.")]
    return _pdf(f"Receipt {receipt}", blocks)


def set_count(tenant: str, booking: str, final, actor: str = "owner") -> dict:
    """Final guest count: free until the lock date; after it only an increase (owner) - the kitchen has already bought for it."""
    n = _int(final)
    if n is None or n <= 0:
        raise BanquetError("Final mehmaan sankhya number chahiye.")
    with _LOCK, session() as s:
        b = _bk(s, tenant, booking)
        st = _st(s, tenant)
        if b.status not in ("hold", "confirmed", "draft"):
            raise BanquetError(f"{b.number} '{STATUS[b.status]}' hai.")
        ev = _date(b.day)
        lk = R.lock_date(ev, st.lock_days) if ev else None
        past_lock = b.locked or (lk is not None and today(tenant) >= lk)
        note = ""
        if past_lock:
            cur = b.final_count or b.guests or 0
            if n < cur:
                raise BanquetError(f"Final count {lk.isoformat() if lk else ''} ko lock ho chuka ({cur}); ab kam nahi hoga, bill "
                                   f"{max(cur, b.guarantee or 0)} plate ka banega.")
            if not is_owner(actor):
                raise BanquetError("Lock ke baad badhana sirf owner (kitchen se pooch kar).")
            note = " Lock ke baad badhaya: kitchen ko bata dijiye (BEO dobara banaiye)."
        b.final_count = n
        h = s.get(BanquetHall, b.hall_id) if b.hall_id else None
        if h and n > max(h.seated, h.floating):
            note += f" {n} log {h.name} ki capacity se zyada!"
        _log(b, f"Final count {n}", actor_name(tenant, actor))
        v = _booking_view(s, b)
    return {"booking": v, "say": f"{v['number']}: final count {n}.{note}"}


def lock_count(tenant: str, booking: str, actor: str = "owner") -> dict:
    with _LOCK, session() as s:
        b = _bk(s, tenant, booking)
        b.locked = True
        if not b.final_count:
            b.final_count = b.guests
        _log(b, f"Final count lock: {b.final_count}", actor_name(tenant, actor))
        v = _booking_view(s, b)
    return {"booking": v, "say": f"{v['number']}: final count {v['final_count']} lock."}


def cancel(tenant: str, booking: str, reason: str = "", by: str = "client", actor: str = "owner", conv: str = "") -> dict:
    """Owner only. The hall is freed at once; a refund (her policy, shown upfront) becomes a card for HER fingerprint tap."""
    if not is_owner(actor):
        raise BanquetError("Booking radd sirf owner.")
    if not str(reason or "").strip():
        raise BanquetError("Radd karne ki wajah likhiye.")
    with _LOCK, session() as s:
        b = _bk(s, tenant, booking)
        if b.status in ("cancelled", "done"):
            raise BanquetError(f"{b.number} pehle hi '{STATUS[b.status]}' hai.")
        ev = _date(b.day)
        days = (ev - today(tenant)).days if ev else 0
        cx = _j(b.cancel, {})
        policy = cx.get("policy") or _policy_of(_st(s, tenant))
        got = _paid(b) - _refunded(b)
        if by == "venue":
            pct, amt = 100.0, round(got, 2)                                  # her side cancelled: everything back
        else:
            pct, amt = R.refund_for(policy, max(days, 0), got)
        for blk in s.scalars(select(BanquetBlock).where(BanquetBlock.booking_id == b.id, BanquetBlock.active.is_(True))).all():
            blk.active = False
        for c in s.scalars(select(BanquetCard).where(BanquetCard.booking_id == b.id, BanquetCard.status == "waiting")).all():
            c.status = "stale"
        cx.update({"at": now().isoformat(), "reason": R.clean(reason, 300), "by": by, "days_before": days, "refund_pct": pct,
                   "refund": amt, "paid": got, "policy": policy})
        b.cancel = _dump(cx)
        b.status = "cancelled"
        if b.lead_id:
            x = s.get(BanquetLead, b.lead_id)
            if x:
                x.status, x.lost_reason = "lost", "cancel: " + R.clean(reason, 200)
        _log(b, f"Radd ({by}): {R.clean(reason, 200)}", "Owner")
        num = b.number
    out = {"say": f"{num} radd; hall khaali. Jama {_rs(got)}, policy se {pct:g}% = {_rs(amt)} wapas."}
    if amt > 0:
        card = _make_card(tenant, "refund", num, {"amount": amt, "pct": pct, "days_before": days,
                                                  "why": "venue ne radd kiya" if by == "venue" else f"{days} din pehle radd"}, actor, conv)
        out["card"] = card["card"]
        out["say"] += " Refund aapki haan (fingerprint) ke card par."
    return out


def refund_sent(tenant: str, booking: str, ref: str = "", actor: str = "owner") -> dict:
    if not is_owner(actor):
        raise BanquetError("Sirf owner.")
    with _LOCK, session() as s:
        b = _bk(s, tenant, booking)
        cx = _j(b.cancel, {})
        ok = cx.get("refund_ok")
        if not ok:
            raise BanquetError("Pehle refund card par aapki haan chahiye.")
        if ok.get("sent"):
            raise BanquetError("Refund pehle hi darj hai.")
        ok["sent"], ok["ref"] = True, R.clean(ref, 40)[-12:]
        cx["refund_ok"] = ok
        b.cancel = _dump(cx)
        pays = _j(b.payments, [])
        pays.append({"id": new_id("bpm"), "receipt": "", "amount": float(ok.get("amount") or 0), "mode": "refund", "ref": ok["ref"],
                     "day": today(tenant).isoformat(), "kind": "refund"})
        b.payments = _dump(pays)
        _log(b, f"Refund bheja {_rs(ok.get('amount'))}", "Owner")
        v = _booking_view(s, b)
    return {"booking": v, "say": f"{v['number']}: refund {_rs(ok.get('amount'))} bheja darj."}


def done(tenant: str, booking: str, actor: str = "owner") -> dict:
    if not is_owner(actor):
        raise BanquetError("Sirf owner.")
    with _LOCK, session() as s:
        b = _bk(s, tenant, booking)
        if b.status != "confirmed":
            raise BanquetError("Sirf pakki booking poori hoti hai.")
        if not _j(b.bill, {}):
            raise BanquetError("Pehle event ke baad ka bill (aapki haan se) banaiye.")
        b.status = "done"
        _log(b, "Event poora", "Owner")
        v = _booking_view(s, b)
    return {"booking": v, "say": f"{v['number']} poora. Feedback maangna ho to message card banaiye."}


def forget(tenant: str, booking: str, actor: str = "owner") -> dict:
    """DPDP Act 2023 / Rules 2025: after the event (done / cancelled + refund settled) the client's personal details are removed;
    numbers stay for her accounts."""
    if not is_owner(actor):
        raise BanquetError("Sirf owner.")
    with _LOCK, session() as s:
        b = _bk(s, tenant, booking)
        cx = _j(b.cancel, {})
        if b.status not in ("done", "cancelled"):
            raise BanquetError("Event poora / radd hone ke baad hi.")
        pending = s.scalars(select(BanquetCard).where(BanquetCard.booking_id == b.id, BanquetCard.kind == "refund",
                                                      BanquetCard.status == "waiting")).first()
        if pending is not None or (cx.get("refund_ok") and not cx["refund_ok"].get("sent")):
            raise BanquetError("Pehle refund ka faisla / bhejna poora kijiye.")
        b.client, b.phone, b.email, b.client_gstin = "Client (hataya)", "", "", ""
        b.notes, b.beo_notes = "", ""
        b.forgotten = True
        if b.lead_id:
            x = s.get(BanquetLead, b.lead_id)
            if x:
                x.name, x.phone, x.notes = "Client (hataya)", "", ""
        for c in s.scalars(select(BanquetCard).where(BanquetCard.booking_id == b.id)).all():
            c.show = _dump({"booking": b.number, "hataya": True})
            c.result = "{}"
        _log(b, "Client ki details hata di (DPDP)", "Owner")
    return {"say": f"{b.number}: client ki personal details hata di; hisaab ke number rahe."}


# ---------------------------------------------------------------- PDFs
def _pdf(title: str, blocks: list[tuple], watermark: str = "") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape

    from .. import indicpdf
    pdf = indicpdf.blocks_pdf(title, blocks, watermark)
    if pdf:
        return pdf
    ss = getSampleStyleSheet()
    small = ss["BodyText"].clone("small", fontSize=8.5, leading=10.5)

    def txt(t: str) -> str:
        return indicpdf.rl_markup(escape(str(t or "").replace("₹", "Rs. ")))
    story: list = []
    for b in blocks:
        if b[0] == "h":
            story.append(Paragraph(txt(b[1]), ss["Heading2"]))
        elif b[0] == "h1":
            story.append(Paragraph(txt(b[1]), ss["Title"]))
        elif b[0] == "p":
            story.append(Paragraph(txt(b[1]), ss["BodyText"]))
        elif b[0] == "table":
            rows = [[Paragraph(txt(c), small) for c in r] for r in b[1]]
            t = Table(rows, colWidths=b[2] if len(b) > 2 else None, repeatRows=1)
            t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.append(t)
        story.append(Spacer(1, 6))
    bio = io.BytesIO()

    def mark(c, _d):
        if watermark:
            c.saveState()
            c.setFont("Helvetica-Bold", 46)
            c.setFillColor(colors.Color(0.85, 0.2, 0.2, alpha=0.18))
            c.translate(300, 420)
            c.rotate(35)
            c.drawCentredString(0, 0, watermark)
            c.restoreState()
    doc = SimpleDocTemplate(bio, pagesize=A4, title=title, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    doc.build(story, onFirstPage=mark, onLaterPages=mark)
    return bio.getvalue()


def _head(st: BanquetSettings, title: str) -> list[tuple]:
    who = " · ".join(x for x in (st.venue, f"GSTIN {st.gstin}" if st.gstin else "") if x)
    contact = " · ".join(x for x in (st.address, st.phone, st.email) if x)
    out = [("h1", title)]
    if who:
        out.append(("p", who))
    if contact:
        out.append(("p", contact))
    return out


def _money_blocks(q: dict) -> list[tuple]:
    rows = [["Item", "Qty", "Unit", "Rate", "Amount", "GST%"]]
    for ln in q["lines"]:
        rows.append([ln["name"], "" if ln["qty"] is None else f"{ln['qty']:g}", ln["unit"], _pdf_rs(ln["rate"]), _pdf_rs(ln["amount"]),
                     f"{ln['gst_pct']:g}"])
    out = [("table", rows, [190, 45, 50, 75, 85, 40])]
    t = [["", "Amount"], ["Subtotal", _pdf_rs(q["subtotal"])]]
    if q["discount"]:
        t.append(["Discount", "- " + _pdf_rs(q["discount"])])
    for g in q["gst"]:
        t.append([f"CGST {g['pct'] / 2:g}% on {_pdf_rs(g['base'])}", _pdf_rs(g["cgst"])])
        t.append([f"SGST {g['pct'] / 2:g}% on {_pdf_rs(g['base'])}", _pdf_rs(g["sgst"])])
    t.append(["TOTAL", _pdf_rs(q["total"])])
    out.append(("table", t, [330, 120]))
    if q.get("words"):
        out.append(("p", f"In words: {q['words']}"))
    return out


def _event_line(s, b: BanquetBooking) -> str:
    h = s.get(BanquetHall, b.hall_id) if b.hall_id else None
    sl = _slots(_st(s, b.tenant_id)).get(b.slot, {})
    return (f"{R.EVENT_LABEL.get(b.event_type, 'Function')} · {h.name if h else ''} · {b.day} · "
            f"{R.SLOT_LABEL.get(b.slot, b.slot)} {sl.get('from', '')}-{sl.get('to', '')}")


def quote_pdf(tenant: str, booking: str, final: bool = False, valid_until: str = "") -> bytes:
    with session() as s:
        b = _bk(s, tenant, booking)
        st = _st(s, tenant)
        q = _quote(s, tenant, b)
        blocks = _head(st, f"Quotation {b.number}") + [
            ("p", f"For: {b.client}" + (f" (GSTIN {b.client_gstin})" if b.client_gstin else "")),
            ("p", _event_line(s, b) + (f" · Plates {q['plates']}" if q["plates"] else "") +
             (f" · Minimum guarantee {b.guarantee}" if b.guarantee else "")),
            *_money_blocks(q)]
        menu = _menu_view(s, b)
        if menu:
            blocks.append(("h", "Menu"))
            for m in menu:
                blocks.append(("p", f"{m['name']} ({m['diet_label']}): " + ", ".join(m["items"]) if m["items"] else f"{m['name']} ({m['diet_label']})"))
        blocks.append(("h", "Cancellation and refund (shown before booking)"))
        for ln in R.policy_lines(_policy_of(st)):
            blocks.append(("p", "• " + ln))
        if valid_until:
            blocks.append(("p", f"Quotation valid till {valid_until}. The hall is NOT blocked by this quotation; it is held / confirmed only "
                                "after the advance and the venue's confirmation."))
        if q["blanks"]:
            blocks.append(("p", "Blanks: " + "; ".join(q["blanks"])))
        blocks.append(("p", q["gst_note"]))
    return _pdf(f"Quotation {b.number}", blocks, "" if final else "DRAFT - NOT SENT")


def contract_pdf(tenant: str, booking: str, final: bool = False) -> bytes:
    with session() as s:
        b = _bk(s, tenant, booking)
        st = _st(s, tenant)
        q = _quote(s, tenant, b)
        h = s.get(BanquetHall, b.hall_id) if b.hall_id else None
        ev = _date(b.day)
        sl = _slots(st).get(b.slot, {})
        blocks = _head(st, f"Booking terms {b.number}") + [
            ("p", f"Client: {b.client} · Mobile: {b.phone}"), ("p", _event_line(s, b)),
            ("p", f"Expected guests {b.guests or '-'} · Minimum guarantee {b.guarantee or '-'} plates · Final guest count to be given by "
                  f"{R.lock_date(ev, st.lock_days).isoformat() if ev else '-'}; after that it can only go up and the bill is for the "
                  "higher of the guarantee and the final / actual count."),
            *_money_blocks(q), ("h", "Payment schedule")]
        rows = [["Instalment", "%", "Amount", "Due"]] + [[r["label"], f"{r['pct']:g}%", _pdf_rs(r["amount"]), r["due"]]
                                                         for r in _stage_rows(s, b, q)]
        blocks.append(("table", rows, [200, 40, 100, 90]))
        blocks.append(("h", "Cancellation and refund"))
        for ln in R.policy_lines(_j(b.cancel, {}).get("policy") or _policy_of(st)):
            blocks.append(("p", "• " + ln))
        blocks.append(("p", "If the venue cancels, everything paid is refunded in full."))
        blocks.append(("h", "Music, loudspeaker and timings"))
        blocks.append(("p", R.noise_note(h.kind if h else "hall", sl.get("to", "23:00"), st.music_end) +
                       " Loudspeaker / DJ only with the written permission of the local authority (Noise Pollution Rules 2000)."))
        blocks.append(("h", "Other terms"))
        blocks.append(("p", st.terms or "Payments to the venue's own UPI ID / bank only; the venue never asks for an OTP or PIN. Damage to "
                       "the property is charged at actuals. Liquor only with the licence / permit required by the state excise law. "
                       "Outside caterers / decorators only with the venue's written OK."))
        blocks.append(("p", "Client signature: ____________________    Venue: ____________________"))
    return _pdf(f"Booking terms {b.number}", blocks, "" if final else "DRAFT - NOT SENT")


def bill_pdf(tenant: str, booking: str) -> bytes:
    with session() as s:
        b = _bk(s, tenant, booking)
        st = _st(s, tenant)
        bill = _j(b.bill, {})
        q = {"lines": bill.get("lines", []), "subtotal": round(sum((x.get("amount") or 0) for x in bill.get("lines", [])), 2),
             "discount": bill.get("discount", 0), "gst": bill.get("gst", []), "total": bill.get("total", 0), "words": ""}
        try:
            from ..india.money import rupees_words
            q["words"] = rupees_words(q["total"], "en")
        except Exception:
            pass
        blocks = _head(st, f"Bill {b.number}") + [
            ("p", f"To: {b.client}" + (f" (GSTIN {b.client_gstin})" if b.client_gstin else "")), ("p", _event_line(s, b)),
            ("p", f"Plates billed {bill.get('plates')} (minimum guarantee {b.guarantee or '-'}, actual {b.actual_count or '-'})"),
            *_money_blocks(q), ("table", [["Paid", _pdf_rs(bill.get("paid"))], ["Balance", _pdf_rs(bill.get("balance"))]], [330, 120])]
        pays = [p for p in _j(b.payments, [])]
        if pays:
            blocks.append(("table", [["Date", "Receipt", "Mode", "Amount"]] + [[p["day"], p.get("receipt", ""), p["mode"], _pdf_rs(p["amount"])]
                                                                              for p in pays], [90, 110, 80, 120]))
    return _pdf(f"Bill {b.number}", blocks)


def beo(tenant: str, booking: str, conv: str = "", actor: str = "owner") -> dict:
    """BEO / function sheet for the kitchen and staff (internal: no client tap needed). Plates per diet, menu, timings, setup,
    extras, noise note; amounts left out."""
    with session() as s:
        b = _bk(s, tenant, booking)
        if b.status not in ("hold", "confirmed"):
            raise BanquetError("BEO hold / pakki booking ka.")
        st = _st(s, tenant)
        h = s.get(BanquetHall, b.hall_id) if b.hall_id else None
        sl = _slots(st).get(b.slot, {})
        q = _quote(s, tenant, b)
        menu = _menu_view(s, b)
        plates = q["plates"]
        food = []
        for m in menu:
            n = m["plates"] if len(menu) > 1 else plates
            food.append({"package": m["name"], "diet": m["diet_label"], "plates": n, "items": m["items"]})
        missing = []
        if not plates:
            missing.append("plate ginti")
        if not menu:
            missing.append("menu")
        ex = [{"name": e.get("name"), "qty": e.get("qty"), "nights": e.get("nights")} for e in _j(b.extras, [])]
        noise = R.noise_note(h.kind if h else "hall", sl.get("to", "23:00"), st.music_end)
        sheet = {"booking": b.number, "event": R.EVENT_LABEL.get(b.event_type, ""), "client": b.client, "phone": b.phone,
                 "hall": h.name if h else "", "day": b.day, "slot": R.SLOT_LABEL.get(b.slot, b.slot), "time": f"{sl.get('from')}-{sl.get('to')}",
                 "guests": b.guests, "final": b.final_count, "guarantee": b.guarantee, "locked": b.locked, "food": food, "extras": ex,
                 "timeline": _j(b.timeline, []), "notes": b.beo_notes, "noise": noise, "missing": missing}
        blocks = [("h1", f"BEO / Function sheet {b.number}"), ("p", f"{st.venue} · {_event_line(s, b)}"),
                  ("p", f"Client: {b.client} ({b.phone}) · Guests expected {b.guests or '-'} · Final {b.final_count or '-'}"
                        f"{' (LOCKED)' if b.locked else ''} · Guarantee {b.guarantee or '-'}"), ("h", "Kitchen")]
        rows = [["Package", "Diet", "Plates", "Items"]] + [[f["package"], f["diet"], str(f["plates"] or "?"), ", ".join(f["items"])] for f in food]
        blocks.append(("table", rows, [120, 50, 50, 300]))
        if any(f["diet"] == "Jain" for f in food):
            blocks.append(("p", "Jain counter: no onion, garlic, root vegetables; separate utensils and serving staff."))
        if ex:
            blocks.append(("h", "Setup / extras"))
            blocks.append(("table", [["Item", "Qty", "Nights"]] + [[e["name"], f"{e['qty']:g}" if e["qty"] else "", str(e["nights"] or "")]
                                                                  for e in ex], [250, 60, 60]))
        if sheet["timeline"]:
            blocks.append(("h", "Run of event"))
            blocks.append(("table", [["Time", "What"]] + [[t["at"], t["what"]] for t in sheet["timeline"]], [70, 380]))
        if b.beo_notes:
            blocks.append(("h", "Notes"))
            blocks.append(("p", b.beo_notes))
        blocks.append(("h", "Music / safety"))
        blocks.append(("p", noise))
        blocks.append(("p", "Fire exits clear; head count within the hall's licensed occupancy; FSSAI licence displayed in the kitchen."))
        if missing:
            blocks.append(("p", "Missing: " + ", ".join(missing)))
        num = b.number
    pdf = _pdf(f"BEO {num}", blocks)
    f = _store(tenant, f"{num}_BEO.pdf", pdf, "application/pdf", conv, f"{num} function sheet")
    return {"beo": sheet, "file_id": f.get("file_id", ""),
            "say": f"{num} BEO / function sheet taiyaar (kitchen + staff ke liye)." + (f" Baaki: {', '.join(missing)}." if missing else "")}


# ---------------------------------------------------------------- views, day, worker
def bookings(tenant: str, status: str = "", day_from: str = "") -> list[dict]:
    with session() as s:
        q = select(BanquetBooking).where(BanquetBooking.tenant_id == tenant)
        if status:
            q = q.where(BanquetBooking.status == status)
        if day_from:
            q = q.where(BanquetBooking.day >= day_from)
        return [_booking_view(s, b) for b in s.scalars(q.order_by(BanquetBooking.day)).all()][:300]


def booking_view(tenant: str, ref: str) -> dict:
    with _LOCK, session() as s:
        _expire_holds(s, tenant)
        return _booking_view(s, _bk(s, tenant, ref), full=True)


def day(tenant: str) -> dict:
    t0 = today(tenant)
    tom = (t0 + timedelta(days=1)).isoformat()
    with _LOCK, session() as s:
        st = _st(s, tenant)
        _expire_holds(s, tenant)
        bs = s.scalars(select(BanquetBooking).where(BanquetBooking.tenant_id == tenant,
                                                    BanquetBooking.status.in_(("hold", "confirmed")))).all()
        today_ev = [_booking_view(s, b) for b in bs if b.day == t0.isoformat() and b.status == "confirmed"]
        tom_ev = [_booking_view(s, b) for b in bs if b.day == tom and b.status == "confirmed"]
        soon = clock() + timedelta(hours=12)
        holds = [_booking_view(s, b) for b in bs if b.status == "hold" and b.hold_until and _aware(b.hold_until) <= soon]
        locks = [_booking_view(s, b) for b in bs if b.status == "confirmed" and not b.locked and b.day
                 and R.lock_date(_date(b.day), st.lock_days) <= t0 + timedelta(days=2)]
        due = []
        for b in bs:
            if b.status != "confirmed":
                continue
            for r in _j(b.stages, []):
                if r.get("due") and r["due"] <= t0.isoformat() and not r.get("paid") and not r.get("requested"):
                    due.append(f"{b.number} {r['label']} {_rs(r.get('amount'))}")
        follow = [_lead_view(x) for x in s.scalars(select(BanquetLead).where(BanquetLead.tenant_id == tenant,
                                                                            BanquetLead.status.in_(("new", "contacted", "visit", "quoted")))).all()
                  if x.follow_up and x.follow_up <= t0.isoformat()]
        unbilled = [b.number for b in bs if b.status == "confirmed" and b.day and b.day < t0.isoformat() and not _j(b.bill, {})]
        waiting = s.scalars(select(BanquetCard).where(BanquetCard.tenant_id == tenant, BanquetCard.status == "waiting")).all()
    parts = []
    if today_ev:
        parts.append("Aaj: " + "; ".join(f"{v['number']} {v['hall']} {v['slot_label']} ({v['final_count'] or v['guests'] or '?'} log)" for v in today_ev))
    if tom_ev:
        parts.append("Kal: " + "; ".join(f"{v['number']} {v['hall']} {v['slot_label']}" for v in tom_ev) + " (BEO taiyaar?)")
    if holds:
        parts.append("Hold khatam hone wale: " + ", ".join(f"{v['number']} {v['client']}" for v in holds))
    if locks:
        parts.append("Final count lock paas: " + ", ".join(f"{v['number']} ({v['lock_date']})" for v in locks))
    if due:
        parts.append("Kisht ka samay: " + "; ".join(due[:6]))
    if follow:
        parts.append("Follow-up: " + ", ".join(f"{x['number']} {x['name'] or x['phone']}" for x in follow[:8]))
    if unbilled:
        parts.append("Event ho gaye, bill baaki: " + ", ".join(unbilled))
    if waiting:
        parts.append(f"{len(waiting)} card aapki haan ka intezaar kar rahe")
    return {"today": today_ev, "tomorrow": tom_ev, "holds_expiring": holds, "locks": locks, "stages_due": due, "follow_ups": follow,
            "unbilled": unbilled, "waiting": len(waiting), "say": (". ".join(parts) + ".") if parts else "Banquet ka aaj sab theek."}


def overview(tenant: str) -> dict:
    return {"settings": settings(tenant), "halls": halls(tenant), "packages": packages(tenant), "extras": extras(tenant),
            "day": day(tenant), "cards": cards(tenant), "leads": leads(tenant)[:50],
            "bookings": bookings(tenant, day_from=today(tenant).isoformat())}


def _once(s, tenant: str, key: str) -> bool:
    k = f"{tenant}:{key}"[:200]
    if s.get(BanquetAlert, k) is not None:
        return False
    s.add(BanquetAlert(key=k, tenant_id=tenant))
    return True


def _tenants() -> list[str]:
    with session() as s:
        return sorted(set(s.scalars(select(BanquetBooking.tenant_id)).all()) | set(s.scalars(select(BanquetSettings.tenant_id)).all()))


def tick(when: datetime | None = None) -> dict:
    """Worker, every minute: expire holds (and tell her), hold ending in 6 h, final-count lock on its date (+ 2-day reminder),
    instalments due, event tomorrow (BEO), event over without a bill (once each); morning note at her time."""
    n = _aware(when) or now()
    out = {"alerts": 0, "expired": 0, "locked": 0, "morning": 0}
    for tenant in _tenants():
        try:
            loc = n.astimezone(_tz(tenant))
            on = loc.date()
            alerts = []
            with _LOCK, session() as s:
                st = _st(s, tenant)
                for blk in s.scalars(select(BanquetBlock).where(BanquetBlock.tenant_id == tenant, BanquetBlock.kind == "hold",
                                                                BanquetBlock.active.is_(True))).all():
                    exp = _aware(blk.expires_at)
                    bk = s.get(BanquetBooking, blk.booking_id) if blk.booking_id else None
                    num = bk.number if bk else ""
                    if exp and exp <= n:
                        blk.active = False
                        if bk is not None and bk.status == "hold":
                            bk.status, bk.hold_until = "draft", None
                            _log(bk, "Hold ka samay khatam: hall chhoot gaya")
                        out["expired"] += 1
                        alerts.append({"kind": "hold_expired", "booking": num, "say": f"{num} ka hold khatam; {blk.day} ka slot ab khaali."})
                    elif exp and exp <= n + timedelta(hours=6) and _once(s, tenant, f"hold6:{blk.id}:{exp.isoformat()}"):
                        alerts.append({"kind": "hold_soon", "booking": num,
                                       "say": f"{num} ka hold {exp.astimezone(_tz(tenant)).strftime('%d-%m %H:%M')} par khatam: advance aaya? "
                                              "Pakka karna ho to card banau?"})
                for b in s.scalars(select(BanquetBooking).where(BanquetBooking.tenant_id == tenant, BanquetBooking.status == "confirmed")).all():
                    ev = _date(b.day)
                    if ev is None:
                        continue
                    lk = R.lock_date(ev, st.lock_days)
                    if not b.locked and on >= lk:
                        b.locked = True
                        b.final_count = b.final_count or b.guests
                        _log(b, f"Final count apne aap lock: {b.final_count}")
                        out["locked"] += 1
                        alerts.append({"kind": "locked", "booking": b.number, "say": f"{b.number}: final count {b.final_count or '?'} lock ho gaya "
                                                                                      "(ab sirf badh sakta hai). BEO bana dijiye."})
                    elif not b.locked and on >= lk - timedelta(days=2) and _once(s, tenant, f"lock2:{b.id}:{lk.isoformat()}"):
                        alerts.append({"kind": "lock_soon", "booking": b.number,
                                       "say": f"{b.number}: final mehmaan sankhya {lk.isoformat()} tak chahiye; client se poochne ka message card banau?"})
                    for r in _j(b.stages, []):
                        if r.get("due") and r["due"] <= on.isoformat() and not r.get("paid") and not r.get("requested") \
                                and _once(s, tenant, f"stage:{b.id}:{r['label']}:{r['due']}"):
                            alerts.append({"kind": "stage", "booking": b.number,
                                           "say": f"{b.number} '{r['label']}' {_rs(r.get('amount'))} ka samay aa gaya; maangne ka card banau?"})
                    if ev == on + timedelta(days=1) and _once(s, tenant, f"eve:{b.id}"):
                        alerts.append({"kind": "tomorrow", "booking": b.number, "say": f"Kal {b.number} ka function: BEO / function sheet taiyaar?"})
                    if ev < on and not _j(b.bill, {}) and _once(s, tenant, f"bill:{b.id}"):
                        alerts.append({"kind": "bill", "booking": b.number, "say": f"{b.number} ka function ho gaya: asal plate ginti batayiye, bill card banau."})
            for a in alerts:
                _publish(tenant, "banquet_alert", a)
                out["alerts"] += 1
            with session() as s:
                r = s.get(BanquetSettings, tenant)
                due_m = False
                if r is not None and r.last_morning != on.isoformat():
                    try:
                        hh, mm = (int(z) for z in (r.morning_time or "09:00").split(":"))
                    except ValueError:
                        hh, mm = 9, 0
                    due_m = (loc.hour, loc.minute) >= (hh, mm)
                    if due_m:
                        r.last_morning = on.isoformat()
            if due_m:
                d = day(tenant)
                if d["say"] != "Banquet ka aaj sab theek.":
                    _publish(tenant, "banquet_day", {"say": d["say"], "today": len(d["today"]), "tomorrow": len(d["tomorrow"]),
                                                     "waiting": d["waiting"]})
                    out["morning"] += 1
        except Exception:
            log.exception("banquet tick failed for %s", tenant)
    return out
