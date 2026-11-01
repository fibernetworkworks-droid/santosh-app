"""v0.360 DELIVERY (App Sahayak Phase 24, owner: "START PHASE 24"): delivery charge, delivery area and shop hours.

She sets a delivery fee, free delivery above an amount, optionally the PIN codes she delivers to, and her opening hours /
days. The SERVER adds the fee to the order (never a number from the phone); the cart shows the same rule from the app
content. An order from a PIN outside her area, or placed while she is closed, is NEVER refused (the phone's outbox would lose
it): it is placed with `delivery_note` saying so, and her chat is told. Receipts / GST invoices show delivery as its own line
(SAC 9968, her default rate); a coupon discounts the goods only. Kept in AppProject.backend["delivery"]."""
from __future__ import annotations

import json
import re
from datetime import timedelta
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
            "hours": (f"{h['open']}-{h['close']}" + (" " + ",".join(DAYS[d] for d in h.get("days") or []) if h.get("days") else ""))
            if h.get("open") else ""}


def view(r: AppProject) -> dict[str, Any]:
    g = settings(r)
    return {"fee": g.get("fee", 0), "free_above": g.get("free_above"), "pins": g.get("pins") or [], "hours": g.get("hours") or {},
            "open_now": is_open(g), "on": bool(g),
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
        notes.append(f"Dukaan abhi band hai - khulte hi ({h.get('open', '')}) order dekha jayega")
        STATS["closed"] += 1
    if notes:
        out["delivery_note"] = "; ".join(notes) + "."
    if fee:
        STATS["fees"] += 1
    return fee, out
