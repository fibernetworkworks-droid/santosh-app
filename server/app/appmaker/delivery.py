"""v0.360 DELIVERY (App Sahayak Phase 24, owner: "START PHASE 24"): delivery charge, delivery area and shop hours.

She sets a delivery fee, free delivery above an amount, optionally the PIN codes she delivers to, and her opening hours /
days. The SERVER adds the fee to the order (never a number from the phone); the cart shows the same rule from the app
content. An order from a PIN outside her area, or placed while she is closed, is NEVER refused (the phone's outbox would lose
it): it is placed with `delivery_note` saying so, and her chat is told. Receipts / GST invoices show delivery as its own line
(SAC 9968, her default rate); a coupon discounts the goods only. Kept in AppProject.backend["delivery"]."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any

from ..db import now, session
from ..site import webapp as W
from .models import AppProject

PIN = re.compile(r"(?<!\d)([1-9]\d{5})(?!\d)")
HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
STATS = {"fees": 0, "outside": 0, "closed": 0}


class DeliveryError(W.AppError):
    pass


def settings(r: AppProject) -> dict[str, Any]:
    from . import backend as BE
    with session() as s:
        row = s.get(AppProject, r.id)
        return dict(BE._j(row.backend if row else r.backend, {}).get("delivery") or {})


def _ist():
    return now() + timedelta(hours=5, minutes=30)


def is_open(g: dict[str, Any], at=None) -> bool:
    if (at or _ist()).strftime("%Y-%m-%d") in (g.get("holidays") or []):     # v0.377 CHHUTTI: her holiday = closed
        return False
    h = g.get("hours") or {}
    if not h.get("open") or not h.get("close"):
        return True
    t = at or _ist()
    if h.get("days") and t.weekday() not in h["days"]:
        return False
    hm = t.strftime("%H:%M")
    return h["open"] <= hm < h["close"] if h["open"] < h["close"] else (hm >= h["open"] or hm < h["close"])  # past midnight


def public(r: AppProject) -> dict[str, Any] | None:
    """What the cart needs (in the app content): fee, free above, area on, open now, hours text."""
    g = settings(r)
    if not g:
        return None
    h = g.get("hours") or {}
    return {"fee": g.get("fee", 0), "free_above": g.get("free_above"), "area": bool(g.get("pins")), "open": is_open(g),
            "slots": bool(g.get("slots")),                                          # v0.371 the cart shows the slot picker
            "hours": (f"{h['open']}-{h['close']}" + (" " + ",".join(DAYS[d] for d in h.get("days") or []) if h.get("days") else ""))
            if h.get("open") else ""}


def view(r: AppProject) -> dict[str, Any]:
    g = settings(r)
    return {"fee": g.get("fee", 0), "free_above": g.get("free_above"), "pins": g.get("pins") or [], "hours": g.get("hours") or {},
            "open_now": is_open(g), "on": bool(g), "slots": g.get("slots") or [], "days": g.get("days", 0), "cutoff": g.get("cutoff", 0),
            "holidays": g.get("holidays") or [],
            "note": "Orders outside the area or while closed are still taken, with a note - nobody's order is lost."}


def _money(v: Any, what: str) -> float | None:
    if v in (None, ""):
        return None
    try:
        f = round(float(str(v).replace(",", "").replace("₹", "").strip()), 2)
    except (TypeError, ValueError):
        raise DeliveryError(f"{what}: number chahiye.")
    if not 0 <= f <= 100000:
        raise DeliveryError(f"{what}: 0 se 1,00,000 tak.")
    return f


def save(r: AppProject, body: dict[str, Any]) -> dict[str, Any]:
    """{fee, free_above, pins: "411001, 411002" | [...], hours: {open "09:00", close "21:00", days [0..6]}, off: true}."""
    from . import backend as BE
    from . import stock as SK
    body = body if isinstance(body, dict) else {}
    with session() as s:
        row = s.get(AppProject, r.id)
        be = BE._j(row.backend, {})
        if body.get("off"):
            be.pop("delivery", None)
        else:
            g = dict(be.get("delivery") or {})
            if "fee" in body:
                g["fee"] = _money(body["fee"], "Delivery charge") or 0
            if "free_above" in body:
                g["free_above"] = _money(body["free_above"], "Free above")
            if "pins" in body:
                raw = body["pins"] if isinstance(body["pins"], list) else re.split(r"[\s,;]+", str(body["pins"] or ""))
                pins = sorted({str(p).strip() for p in raw if str(p).strip()})
                bad = [p for p in pins if not re.fullmatch(r"[1-9]\d{5}", p)]
                if bad:
                    raise DeliveryError("PIN code 6 ank ka: " + ", ".join(bad[:5]))
                g["pins"] = pins[:2000]
            if "hours" in body:
                h = body["hours"] if isinstance(body["hours"], dict) else {}
                if h.get("open") or h.get("close"):
                    if not (HHMM.match(str(h.get("open") or "")) and HHMM.match(str(h.get("close") or ""))):
                        raise DeliveryError("Samay HH:MM (jaise 09:00 aur 21:00).")
                    days = sorted({int(d) for d in (h.get("days") or []) if str(d).isdigit() and 0 <= int(d) <= 6})
                    g["hours"] = {"open": h["open"], "close": h["close"], **({"days": days} if days else {})}
                else:
                    g.pop("hours", None)
            be["delivery"] = {k: v for k, v in g.items() if v is not None}
        row.backend = json.dumps(be, ensure_ascii=False)
        r.backend = row.backend
    SK._flush(r)
    return view(r)


def fee_for(g: dict[str, Any], goods: float) -> float:
    if not g:
        return 0.0
    if g.get("free_above") is not None and goods >= float(g["free_above"]):
        return 0.0
    return round(float(g.get("fee") or 0), 2)


def pin_of(data: dict[str, Any]) -> str:
    for k in ("pin", "pincode", "pin_code", "postal_code", "zip"):
        m = PIN.search(str(data.get(k) or ""))
        if m:
            return m.group(1)
    for k, v in data.items():
        if k not in ("phone", "utr") and isinstance(v, str):
            m = PIN.search(v)
            if m and ("address" in k or "pin" in k or len(v) > 15):
                return m.group(1)
    return ""


def on_order(r: AppProject, goods: float, data: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """At order time: (fee, fields for the row). Outside the area / closed = a note, never a refusal."""
    g = settings(r)
    if not g:
        return 0.0, {}
    fee = fee_for(g, goods)
    out: dict[str, Any] = {"delivery": fee} if fee or g.get("fee") else {}
    notes = []
    if g.get("pins"):
        pin = pin_of(data)
        if pin and pin not in g["pins"]:
            notes.append(f"PIN {pin} delivery area ke bahar hai - dukaan aapko call karegi")
            STATS["outside"] += 1
        elif not pin:
            notes.append("Address mein PIN code nahi mila - dukaan confirm karegi")
    if not is_open(g):
        h = g.get("hours") or {}
        if _ist().strftime("%Y-%m-%d") in (g.get("holidays") or []):
            notes.append("Aaj dukaan ki chhutti hai - khulte hi order dekha jayega")
        else:
            notes.append(f"Dukaan abhi band hai - khulte hi ({h.get('open', '')}) order dekha jayega")
        STATS["closed"] += 1
    if notes:
        out["delivery_note"] = "; ".join(notes) + "."
    if fee:
        STATS["fees"] += 1
    return fee, out


# ---------------------------------------------------------------- v0.371 SLOT (App Sahayak Phase 35): delivery time slots
# She sets slots ({label "9-11 am", start "09:00", end "11:00", cap orders}), how many days ahead customers may book (0-6) and
# a cut-off (minutes before a slot starts). The cart asks GET /slots (fresh: the slots with room, for today + the days ahead);
# the order carries "slot": "YYYY-MM-DD|HH:MM" and the SERVER checks it again under a lock (exists, not past its cut-off, a
# working day, room left counting the slot's non-cancelled orders). A slot that filled up in between never loses the order:
# it is placed without a slot + delivery_note, and her chat is told. Rows carry `slot` (the key) and `slot_label`.
import threading as _th

_SLOT_LOCK = _th.Lock()
STATS.update({"slots_booked": 0, "slots_full": 0})


def _slots_cfg(g: dict[str, Any]) -> tuple[list[dict[str, Any]], int, int]:
    return list(g.get("slots") or []), int(g.get("days") or 0), int(g.get("cutoff") or 0)


def save_slots(r: AppProject, slots: Any, days: Any = 0, cutoff: Any = 0) -> dict[str, Any]:
    """[{label, start HH:MM, end HH:MM, cap}] (max 12), days ahead 0-6, cut-off 0-720 minutes. [] removes slots."""
    from . import backend as BE
    from . import stock as SK
    out = []
    for x in (slots if isinstance(slots, list) else [])[:12]:
        if not isinstance(x, dict):
            continue
        st, en = str(x.get("start") or ""), str(x.get("end") or "")
        if not (HHMM.match(st) and HHMM.match(en) and st < en):
            raise DeliveryError("Slot ka samay HH:MM, shuru < khatam (jaise 09:00 - 11:00).")
        try:
            cap = int(float(str(x.get("cap") or 0)))
        except ValueError:
            cap = 0
        if not 1 <= cap <= 1000:
            raise DeliveryError("Har slot mein 1 se 1000 orders.")
        label = re.sub(r"[\x00-\x1f]+", " ", str(x.get("label") or f"{st}-{en}")).strip()[:30]
        out.append({"label": label, "start": st, "end": en, "cap": cap})
    try:
        d, c = int(float(str(days or 0))), int(float(str(cutoff or 0)))
    except ValueError:
        raise DeliveryError("Din aur cut-off number mein.")
    if not 0 <= d <= 6 or not 0 <= c <= 720:
        raise DeliveryError("Aage ke din 0-6, cut-off 0-720 minute.")
    with session() as s:
        row = s.get(AppProject, r.id)
        be = BE._j(row.backend, {})
        g = dict(be.get("delivery") or {})
        if out:
            g.update({"slots": out, "days": d, "cutoff": c})
        else:
            for k in ("slots", "days", "cutoff"):
                g.pop(k, None)
        be["delivery"] = g
        row.backend = json.dumps(be, ensure_ascii=False)
        r.backend = row.backend
    SK._flush(r)
    return view(r) | {"slots": out, "days": d, "cutoff": c}


def _booked(r: AppProject) -> dict[str, int]:
    """Non-cancelled orders per slot key (only the ones still to come)."""
    from sqlalchemy import select
    from . import backend as BE
    sch = BE.schema(r)
    order = sch.get("order") or ""
    today = _ist().strftime("%Y-%m-%d")
    n: dict[str, int] = {}
    with session() as s:
        for (data,) in s.execute(select(W.SiteAppRow.data).where(W.SiteAppRow.site_id == BE.bid(r), W.SiteAppRow.coll == order,
                                                                 W.SiteAppRow.data.like('%"_slot": "%'))).all():
            d = BE._j(data, {})
            k = str(d.get("_slot") or "")
            if k[:10] >= today and str(d.get("status") or "").strip().lower() != "cancelled":
                n[k] = n.get(k, 0) + 1
    return n


def available(r: AppProject) -> dict[str, Any]:
    """The cart's list: [{key, day, label, left}] for today + the days ahead, past their cut-off / full ones left out."""
    g = settings(r)
    slots, days, cutoff = _slots_cfg(g)
    if not slots:
        return {"slots": [], "on": False}
    booked = _booked(r)
    now_ = _ist()
    out = []
    h = g.get("hours") or {}
    for i in range(days + 1):
        day = now_ + timedelta(days=i)
        if h.get("days") and day.weekday() not in h["days"]:
            continue
        ds = day.strftime("%Y-%m-%d")
        if ds in (g.get("holidays") or []):                 # v0.377 no slots on her holidays
            continue
        for sl in slots:
            start = datetime.strptime(f"{ds} {sl['start']}", "%Y-%m-%d %H:%M")
            if start - timedelta(minutes=cutoff) <= now_.replace(tzinfo=None):
                continue
            key = f"{ds}|{sl['start']}"
            left = sl["cap"] - booked.get(key, 0)
            if left > 0:
                out.append({"key": key, "day": "Today" if i == 0 else ("Tomorrow" if i == 1 else day.strftime("%a %d %b")),
                            "label": sl["label"], "left": left})
    return {"slots": out, "on": True}


def book(r: AppProject, key: str) -> tuple[dict[str, Any], str]:
    """At order time, under a lock: ({slot, slot_label}, "") or ({}, why) - never a refusal."""
    key = str(key or "").strip()
    if not key:
        return {}, ""
    with _SLOT_LOCK:
        hit = next((x for x in available(r)["slots"] if x["key"] == key), None)
        if hit is None:
            STATS["slots_full"] += 1
            return {}, "Chuna hua delivery slot ab khaali nahi (bhar gaya / samay nikal gaya) - dukaan call karke samay tay karegi"
        STATS["slots_booked"] += 1
        return {"slot": key, "slot_label": f"{hit['day']} {hit['label']}"}, ""


def confirm(r: AppProject, row_id: str) -> None:
    """After the row is written (two orders may pass `book` at the same moment): the slot's orders by time - a row beyond the
    slot's cap loses the slot and gets the note instead (never a lost order)."""
    from sqlalchemy import select
    from . import backend as BE
    with _SLOT_LOCK:
        with session() as s:
            row = s.get(W.SiteAppRow, row_id)
            d = BE._j(row.data, {}) if row is not None else {}
            key = str(d.get("_slot") or "")
            if not key:
                return
            cap = next((x["cap"] for x in _slots_cfg(settings(r))[0] if x["start"] == key[11:]), 0)
            same = [x for x in s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == row.site_id, W.SiteAppRow.coll == row.coll,
                                                                    W.SiteAppRow.data.like(f'%"_slot": "{key}"%'))).all()
                    if str(BE._j(x.data, {}).get("status") or "").strip().lower() != "cancelled"]
            same.sort(key=lambda x: (x.created_at, x.id))
            if [x.id for x in same].index(row_id) < cap:
                return
            for k in ("_slot", "_slot_label"):
                d.pop(k, None)
            why = "Chuna hua delivery slot usi waqt bhar gaya - dukaan call karke samay tay karegi."
            d["_delivery_note"] = (d.get("_delivery_note", "").rstrip(".") + "; " if d.get("_delivery_note") else "") + why
            row.data = json.dumps(d, ensure_ascii=False)
            STATS["slots_full"] += 1



# ---------------------------------------------------------------- v0.377 CHHUTTI (App Sahayak Phase 41)
def save_holidays(r: AppProject, dates: Any) -> dict[str, Any]:
    """Her holidays: YYYY-MM-DD dates (past ones dropped, max 60)."""
    from . import backend as BE
    from . import stock as SK
    raw = dates if isinstance(dates, list) else re.split(r"[\s,;]+", str(dates or ""))
    out = set()
    today = _ist().strftime("%Y-%m-%d")
    for d in raw:
        d = str(d).strip()
        if not d:
            continue
        try:
            datetime.strptime(d, "%Y-%m-%d")
        except ValueError:
            raise DeliveryError(f"Chhutti ki tareekh YYYY-MM-DD: {d}")
        if d >= today:
            out.add(d)
    with session() as s:
        row = s.get(AppProject, r.id)
        be = BE._j(row.backend, {})
        g = dict(be.get("delivery") or {})
        if out:
            g["holidays"] = sorted(out)[:60]
        else:
            g.pop("holidays", None)
        be["delivery"] = g
        row.backend = json.dumps(be, ensure_ascii=False)
        r.backend = row.backend
    SK._flush(r)
    return view(r)


def change_slot(r: AppProject, coll: str, row_id: str, key: str, w: W.Who) -> dict[str, Any]:
    """Move an order to another free slot: its customer before the current slot's cut-off, staff any time. The new slot is
    booked under the same lock and re-counted after the write (v0.371)."""
    from . import backend as BE
    g = settings(r)
    slots, _days, cutoff = _slots_cfg(g)
    if not slots:
        raise DeliveryError("Is app mein delivery slots nahi hain.", 409)
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        if row is None or row.site_id != BE.bid(r) or row.coll != coll:
            raise DeliveryError("Yeh order nahi mila.", 404)
        d = BE._j(row.data, {})
        owner = row.owner
    if not (w.staff or (w.id and owner == w.id)):
        raise DeliveryError("Yeh order nahi mila.", 404)
    if str(d.get("status") or "").strip().lower() in ("cancelled", "delivered", "done", "completed"):
        raise DeliveryError("Yeh order poora / cancel ho chuka - samay nahi badalta.", 409)
    cur = str(d.get("_slot") or "")
    if cur and not w.staff:
        start = datetime.strptime(cur.replace("|", " "), "%Y-%m-%d %H:%M")
        if start - timedelta(minutes=cutoff) <= _ist().replace(tzinfo=None):
            raise DeliveryError("Ab samay badalne ka waqt nikal gaya - dukaan se baat kijiye.", 409)
    if key == cur:
        return {"slot": cur, "slot_label": d.get("_slot_label", "")}
    sf, why = book(r, key)
    if why:
        raise DeliveryError(why + ".", 409)
    old = {k: d.get(k) for k in ("_slot", "_slot_label", "_delivery_note")}
    BE._merge(row_id, {"_" + k: v for k, v in sf.items()} | {"_ev": now_iso()})
    confirm(r, row_id)
    d2 = BE._j(BE._row(BE.bid(r), row_id).data, {})
    if d2.get("_slot") != key:                         # lost the race: the order keeps exactly what it had
        with session() as s:
            row = s.get(W.SiteAppRow, row_id)
            dd = BE._j(row.data, {})
            for k, v in old.items():
                if v in (None, ""):
                    dd.pop(k, None)
                else:
                    dd[k] = v
            row.data = json.dumps(dd, ensure_ascii=False)
        raise DeliveryError("Yeh slot usi waqt bhar gaya - doosra chuniye.", 409)
    if d2.get("_delivery_note") and "slot" in str(d2.get("_delivery_note")).lower() and not old.get("_delivery_note"):
        BE._merge(row_id, {"_delivery_note": ""})      # an earlier "slot full" note no longer applies
    return {"slot": key, "slot_label": d2.get("_slot_label", "")}


def now_iso() -> str:
    return now().isoformat()
