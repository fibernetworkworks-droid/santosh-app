"""v0.358 COUPON (App Sahayak Phase 22, owner: "START PHASE 22"): discount codes for her shop app.

She makes codes (DIWALI10): percent (1-90, optional cap in rupees) or flat rupees, optional minimum order, last date, total
uses and once per customer. The customer checks a code in the cart (GET /coupon) and sees the discount; the SERVER applies it
again when the order arrives (from its own priced subtotal, never a number the phone sends) and counts the use under a lock.
A code that fails at that moment (expired, used up, already used by her, order too small) never loses the order: the order
is placed at full price with `coupon_note` saying why. Kept in AppProject.backend["coupons"] - no new table."""
from __future__ import annotations

import json
import re
import threading
from datetime import date, timedelta
from typing import Any

from ..db import now, session
from ..site import webapp as W
from .models import AppProject
from . import locks as LK                     # v0.383 one cross-process lock per app

CODE = re.compile(r"^[A-Z0-9]{4,16}$")
MAX_CODES = 50
_LOCK = threading.Lock()
STATS = {"checked": 0, "applied": 0, "not_applied": 0}


class CouponError(W.AppError):
    pass


def _today() -> date:
    return (now() + timedelta(hours=5, minutes=30)).date()


def _all(r: AppProject) -> dict[str, dict[str, Any]]:
    from . import backend as BE
    with session() as s:
        row = s.get(AppProject, r.id)
        return dict(BE._j(row.backend if row else r.backend, {}).get("coupons") or {})


def active(r: AppProject) -> bool:
    t = _today().isoformat()
    return any(c.get("on", True) and (not c.get("until") or c["until"] >= t) and (c.get("uses") is None or c.get("used", 0) < c["uses"])
               for c in _all(r).values())


def view(r: AppProject) -> dict[str, Any]:
    t = _today().isoformat()
    out = []
    for code, c in sorted(_all(r).items()):
        live = c.get("on", True) and (not c.get("until") or c["until"] >= t) and (c.get("uses") is None or c.get("used", 0) < c["uses"])
        out.append({"code": code, **{k: v for k, v in c.items() if k != "who"}, "live": live, "customers": len(c.get("who") or [])})
    return {"coupons": out, "note": "The server checks every code again when the order arrives; a code that fails then never loses the order."}


def _money(v: Any, what: str, lo: float = 0, hi: float = 10_000_000) -> float:
    try:
        f = round(float(str(v).replace(",", "").replace("₹", "").strip()), 2)
    except (TypeError, ValueError):
        raise CouponError(f"{what}: number chahiye.")
    if not lo <= f <= hi:
        raise CouponError(f"{what}: {lo:g} se {hi:,.0f} tak.")
    return f


def save(r: AppProject, body: dict[str, Any]) -> dict[str, Any]:
    """Make / change a code: {code, kind percent|flat, value, cap?, min?, until? YYYY-MM-DD, uses?, once?, on?}; {code, delete: true}."""
    from . import backend as BE
    body = body if isinstance(body, dict) else {}
    code = re.sub(r"\s+", "", str(body.get("code") or "")).upper()
    if not CODE.match(code):
        raise CouponError("Code 4-16 akshar ka, sirf A-Z aur 0-9 (jaise DIWALI10).")
    with LK.app(r.id), session() as s:
        row = s.get(AppProject, r.id)
        be = BE._j(row.backend, {})
        cs = dict(be.get("coupons") or {})
        if body.get("delete"):
            cs.pop(code, None)
        else:
            c = dict(cs.get(code) or {"used": 0, "who": [], "made": now().isoformat()})
            if code not in cs and len(cs) >= MAX_CODES:
                raise CouponError(f"Ek app mein {MAX_CODES} codes tak.")
            kind = str(body.get("kind") or c.get("kind") or "percent")
            if kind not in ("percent", "flat"):
                raise CouponError("kind: percent ya flat.")
            c["kind"] = kind
            if "value" in body or "value" not in c:
                c["value"] = _money(body.get("value"), "Discount", 1, 90 if kind == "percent" else 1_000_000)
            for k, what in (("cap", "Zyada se zyada chhoot"), ("min", "Kam se kam order")):
                if k in body:
                    c[k] = _money(body[k], what, 1) if body[k] not in (None, "", 0, "0") else None
            if "until" in body:
                u = str(body.get("until") or "").strip()
                if u:
                    try:
                        date.fromisoformat(u)
                    except ValueError:
                        raise CouponError("Last date YYYY-MM-DD.")
                c["until"] = u or None
            if "uses" in body:
                c["uses"] = int(_money(body["uses"], "Kitni baar", 1, 1_000_000)) if body["uses"] not in (None, "") else None
            if "once" in body:
                c["once"] = bool(body["once"])
            if "on" in body:
                c["on"] = bool(body["on"])
            cs[code] = {k: v for k, v in c.items() if v is not None}
        be["coupons"] = cs
        row.backend = json.dumps(be, ensure_ascii=False)
        r.backend = row.backend
    from . import stock as SK
    SK._flush(r)                                   # the app's content (60 s cache) shows / hides the code box at once
    return view(r)


def _why(c: dict[str, Any] | None, subtotal: float, who: str) -> str:
    if c is None or not c.get("on", True):
        return "Yeh code nahi chalta."
    if c.get("until") and c["until"] < _today().isoformat():
        return "Yeh code khatam ho gaya."
    if c.get("uses") is not None and c.get("used", 0) >= c["uses"]:
        return "Yeh code poora istemaal ho chuka."
    if c.get("once") and who and who in (c.get("who") or []):
        return "Yeh code aap pehle hi istemaal kar chuke hain."
    if c.get("min") and subtotal < c["min"]:
        return f"Yeh code ₹{c['min']:g} ya zyada ke order par chalta hai."
    return ""


def discount_of(c: dict[str, Any], subtotal: float) -> float:
    d = subtotal * c["value"] / 100 if c["kind"] == "percent" else c["value"]
    if c["kind"] == "percent" and c.get("cap"):
        d = min(d, c["cap"])
    return round(max(0.0, min(d, subtotal)), 2)


def check(r: AppProject, code: str, cart: Any, w: W.Who) -> dict[str, Any]:
    """The cart's check before the order: {ok, discount, total, why}. Nothing is counted here."""
    from . import backend as BE
    code = re.sub(r"\s+", "", str(code or "")).upper()
    _items, subtotal = BE._priced(r, cart)
    c = _all(r).get(code) if CODE.match(code) else None
    why = _why(c, subtotal, w.id)
    STATS["checked"] += 1
    if why:
        return {"ok": False, "why": why, "subtotal": subtotal, "discount": 0, "total": subtotal}
    d = discount_of(c, subtotal)
    return {"ok": True, "code": code, "subtotal": subtotal, "discount": d, "total": round(subtotal - d, 2)}


def apply(r: AppProject, code: str, subtotal: float, w: W.Who) -> tuple[float, dict[str, Any]]:
    """At order time, under the lock: (discount, fields for the row). A failing code -> (0, {coupon_note: why})."""
    from . import backend as BE
    code = re.sub(r"\s+", "", str(code or "")).upper()
    if not code:
        return 0.0, {}
    with LK.app(r.id), session() as s:
        row = s.get(AppProject, r.id)
        be = BE._j(row.backend, {})
        cs = dict(be.get("coupons") or {})
        c = cs.get(code) if CODE.match(code) else None
        why = _why(c, subtotal, w.id)
        if why:
            STATS["not_applied"] += 1
            return 0.0, {"coupon": code[:16], "coupon_note": f"{code[:16]} nahi laga: {why}"}
        d = discount_of(c, subtotal)
        c = dict(c)
        c["used"] = int(c.get("used", 0)) + 1
        if w.id:
            c["who"] = (list(c.get("who") or []) + [w.id])[-5000:]
        cs[code] = c
        be["coupons"] = cs
        row.backend = json.dumps(be, ensure_ascii=False)
    STATS["applied"] += 1
    return d, {"coupon": code, "discount": d, "subtotal": subtotal}


def give_back(r: AppProject, code: str, who: str) -> None:
    """A cancelled order gives its coupon use back (the customer may use it again)."""
    from . import backend as BE
    with LK.app(r.id), session() as s:
        row = s.get(AppProject, r.id)
        be = BE._j(row.backend, {})
        cs = dict(be.get("coupons") or {})
        if code not in cs:
            return
        c = dict(cs[code])
        c["used"] = max(0, int(c.get("used", 0)) - 1)
        who_ = list(c.get("who") or [])
        if who in who_:
            who_.remove(who)
        c["who"] = who_
        cs[code] = c
        be["coupons"] = cs
        row.backend = json.dumps(be, ensure_ascii=False)
