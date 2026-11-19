"""v0.412 NAKSHA LIVE (App Sahayak Pillar D, Phases 50-51): maps, rider location sharing and live tracking.

  * HER SWITCH: tracking is OFF until she turns it on for one list (the order list by default) and names the statuses that
    mean "on the way" ("Out for delivery" / "In progress"). The next app build then carries the shift button, the rider's
    location service and the maps; an older build simply never shows them.
  * THE RIDER STARTS IT: a staff account taps "Start shift" after a plain notice (Play's prominent-disclosure rule) and
    the phone's own permission dialog. Positions are accepted ONLY while that shift is on, are kept as ONE current point
    (no trail is stored), and are wiped when the shift ends. A shift left on is treated as ended after SHIFT_HOURS.
  * WHO SEES IT: staff and the owner see every rider on shift; a customer sees ONLY the rider that has HER order, and only
    while that order is in an "on the way" status. The server decides that list each time the rider moves - the phone is
    never trusted with it.
  * ETA is an ESTIMATE in code (straight line x road factor at the rider's speed or a city speed), said as an estimate.
  * GEOFENCES: when the rider comes within NEAR_M of the order's location the order is marked near, within ARRIVE_M
    arrived (once each), through the normal row write - so it is journaled, goes live (Pillar C) and is in her records.
  * Positions travel over the live stream (Pillar C signals), so nothing new runs on her server."""
from __future__ import annotations

import json
import logging
import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, now, session
from ..site import webapp as W
from .models import AppProject

log = logging.getLogger(__name__)
STATS = {"shifts": 0, "positions": 0, "near": 0, "arrived": 0, "refused": 0}

SHIFT_HOURS = 14
FRESH_S = 120                    # an older position is "last seen", not live
NEAR_M, ARRIVE_M = 500, 100
ROAD = 1.35                      # straight line -> roads (an estimate)
CITY_KMH = 18.0                  # used when the rider is standing / the phone gives no speed
DEFAULT_ON_THE_WAY = {"orders": ["Out for delivery"], "requests": ["In progress"], "bookings": ["Confirmed"]}
LOC = __import__("re").compile(r"^\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$")


class AppRider(Base):
    """One row per staff account that has ever started a shift: the shift state + its ONE current position."""
    __tablename__ = "app_rider"
    id: Mapped[str] = mapped_column(String(90), primary_key=True)        # site + member
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    member: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(60), default="")
    on: Mapped[int] = mapped_column(Integer, default=0)
    started: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    acc: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)   # m/s from the phone
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)
    at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_OK = False


def ensure_table() -> None:
    global _OK
    if _OK:
        return
    from .. import db as _db
    if _db._engine is not None:
        AppRider.__table__.create(_db._engine, checkfirst=True)
        _OK = True


class TrackError(W.AppError):
    pass


def _site(r: AppProject) -> str:
    return "app:" + r.id


def _aware(t: datetime | None) -> datetime | None:
    if t is None:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def point(s: Any) -> tuple[float, float] | None:
    m = LOC.match(str(s or ""))
    if not m:
        return None
    a, b = float(m.group(1)), float(m.group(2))
    return (a, b) if -90 <= a <= 90 and -180 <= b <= 180 else None


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Straight-line kilometres (haversine)."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * math.asin(min(1.0, math.sqrt(h)))


def eta_min(dist_km: float, speed_ms: float | None) -> int:
    kmh = (speed_ms or 0) * 3.6
    kmh = kmh if 5 <= kmh <= 90 else CITY_KMH
    return max(1, math.ceil(dist_km * ROAD / kmh * 60))


# ---------------------------------------------------------------- her settings
def settings(r: AppProject) -> dict[str, Any]:
    from . import backend as BE
    sch = BE.schema(r)
    t = dict(BE.ensure(r).get("track") or {})
    colls = {c["key"]: c for c in sch["collections"]}
    coll = t.get("coll") or sch.get("order") or next((k for k, c in colls.items() if _loc_key(c)), "")
    c = colls.get(coll)
    statuses = [s for s in (t.get("statuses") or DEFAULT_ON_THE_WAY.get(coll) or []) if c is None or s in _status_options(c)]
    return {"on": bool(t.get("on")) and c is not None, "coll": coll if c is not None else "", "statuses": statuses,
            "loc": _loc_key(c) if c else "", "options": _status_options(c) if c else [],
            "lists": [{"key": k, "label": x.get("label", k), "statuses": _status_options(x), "location": bool(_loc_key(x))}
                      for k, x in colls.items()],
            "near_m": NEAR_M, "arrive_m": ARRIVE_M}


def _loc_key(c: dict[str, Any] | None) -> str:
    return next((f["key"] for f in (c or {}).get("fields") or [] if f.get("type") == "location"), "")


def _status_options(c: dict[str, Any] | None) -> list[str]:
    f = next((f for f in (c or {}).get("fields") or [] if f.get("key") == "status"), None)
    return [str(x) for x in (f or {}).get("options") or []]


def save_settings(r: AppProject, body: dict[str, Any]) -> dict[str, Any]:
    """Her tap in the console / phone: {on, coll, statuses}."""
    from . import backend as BE
    sch = BE.schema(r)
    colls = {c["key"]: c for c in sch["collections"]}
    coll = str(body.get("coll") or sch.get("order") or "")
    c = colls.get(coll)
    if c is None:
        raise TrackError("This list is not in the app.", 400)
    opts = _status_options(c)
    if not opts:
        raise TrackError(f"{c.get('label', coll)} has no status - tracking needs a status.", 400)
    want = [str(s) for s in (body.get("statuses") or DEFAULT_ON_THE_WAY.get(coll) or []) if str(s) in opts]
    if not want:
        raise TrackError("Choose at least one 'on the way' status.", 400)
    BE.patch_backend(r, {"track": {"on": bool(body.get("on")), "coll": coll, "statuses": want}})
    return settings(r)


def _on(r: AppProject) -> dict[str, Any]:
    st = settings(r)
    if not st["on"]:
        raise TrackError("Live tracking is off (the shop has not switched it on).", 409)
    return st


# ---------------------------------------------------------------- shifts
def _rid(r: AppProject, member: str) -> str:
    return f"{_site(r)}|{member}"


def _active(x: AppRider | None) -> bool:
    if x is None or not x.on or x.started is None:
        return False
    return now() - _aware(x.started) < timedelta(hours=SHIFT_HOURS)


def _staff(w: W.Who, r: AppProject | None = None) -> None:
    if w.m is None:
        raise TrackError("Please log in first.", 401)
    if not w.staff:
        if r is not None and (w.m.role or "") == "partner":      # v0.435 PARIVAAR: an approved delivery partner too
            from . import family as FA
            if FA.is_rider(r, w):
                return
        raise TrackError("Shifts are for staff only.", 403)


def shift(r: AppProject, w: W.Who, on: bool) -> dict[str, Any]:
    _staff(w, r)
    st = _on(r) if on else settings(r)
    ensure_table()
    name = (w.m.name or w.m.email.split("@")[0])
    with session() as s:
        x = s.get(AppRider, _rid(r, w.id))
        if x is None:
            x = AppRider(id=_rid(r, w.id), site_id=_site(r), member=w.id)
            s.add(x)
        x.name = name[:60]
        was = _active(x)
        x.on = 1 if on else 0
        if on and not was:
            x.started = now()
            STATS["shifts"] += 1
        if not on:                                          # the shift ends: the position goes with it
            x.lat = x.lng = x.acc = x.speed = x.heading = None
            x.at = None
    if not on and st.get("coll"):
        from . import live as LV
        LV._write_signal(_site(r), w.id, name, True, "pos", "", {"off": True, "orders": _orders_of(r, st, w.id, None, None)})
    return {"on": bool(on), "started": now().isoformat() if on else ""}


def _orders_of(r: AppProject, st: dict[str, Any], rider: str, here: tuple[float, float] | None,
               speed: float | None) -> dict[str, dict[str, Any]]:
    """This rider's rows that are on their way now -> {row id: {to: customer, km, eta_min, near, arrived}} (+ geofences)."""
    from . import backend as BE
    out: dict[str, dict[str, Any]] = {}
    cut = now() - timedelta(days=3)
    with session() as s:
        rows = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == _site(r), W.SiteAppRow.coll == st["coll"],
                                                    W.SiteAppRow.updated_at >= cut).limit(3000)).all()
        for x in rows:
            s.expunge(x)
    for x in rows:
        d = BE._j(x.data, {})
        if str(d.get("_to") or "") != rider or str(d.get("status") or "") not in st["statuses"]:
            continue
        item: dict[str, Any] = {"to": x.owner or ""}
        dest = point(d.get(st["loc"])) if st["loc"] else None
        if here and dest:
            dist = km(here, dest)
            item["km"], item["eta_min"] = round(dist, 2), eta_min(dist, speed)
            mark: dict[str, Any] = {}
            if dist * 1000 <= NEAR_M and not d.get("_near"):
                mark["_near"] = now().isoformat()
                STATS["near"] += 1
            if dist * 1000 <= ARRIVE_M and not d.get("_arrived"):
                mark["_arrived"] = now().isoformat()
                STATS["arrived"] += 1
            if mark:
                BE._merge(x.id, mark)                       # journaled -> live row event -> her records
            item["near"] = bool(d.get("_near") or mark.get("_near"))
            item["arrived"] = bool(d.get("_arrived") or mark.get("_arrived"))
        out[x.id] = item
    return out


def position(r: AppProject, w: W.Who, body: dict[str, Any]) -> dict[str, Any]:
    """POST /track/pos from the rider's phone while the shift is on."""
    _staff(w, r)
    st = _on(r)
    try:
        lat, lng = float(body.get("lat")), float(body.get("lng"))
    except (TypeError, ValueError):
        raise TrackError("The location is not valid.", 400)
    if not (-90 <= lat <= 90 and -180 <= lng <= 180) or (lat == 0 and lng == 0):
        raise TrackError("The location is not valid.", 400)

    def num(k: str, lo: float, hi: float) -> float | None:
        try:
            v = float(body.get(k))
        except (TypeError, ValueError):
            return None
        return v if lo <= v <= hi else None
    acc, speed, heading = num("acc", 0, 5000), num("speed", 0, 80), num("heading", 0, 360)
    if acc is not None and acc > 1000:
        return {"ok": True, "kept": False, "why": "too rough"}   # a 1 km guess would make the map jump
    try:
        W.rate(f"track-pos:{_site(r)}:{w.id}", 1, 2)
    except W.AppError:
        return {"ok": True, "kept": False, "why": "too fast"}
    ensure_table()
    with session() as s:
        x = s.get(AppRider, _rid(r, w.id))
        if not _active(x):
            STATS["refused"] += 1
            raise TrackError("The shift is off - Start shift first.", 409)
        x.lat, x.lng, x.acc, x.speed, x.heading, x.at = lat, lng, acc, speed, heading, now()
        name = x.name
    STATS["positions"] += 1
    orders = _orders_of(r, st, w.id, (lat, lng), speed)
    from . import live as LV
    LV._write_signal(_site(r), w.id, name, True, "pos", "",
                     {"lat": round(lat, 6), "lng": round(lng, 6), "at": now().isoformat(), "speed": speed, "orders": orders})
    return {"ok": True, "kept": True, "orders": len(orders)}


# ---------------------------------------------------------------- what people see
def _rider(r: AppProject, member: str) -> AppRider | None:
    ensure_table()
    with session() as s:
        x = s.get(AppRider, _rid(r, member))
        if x is not None:
            s.expunge(x)
    return x


def _first(n: str) -> str:
    return (str(n or "").strip().split(" ") or [""])[0][:30]


def order(r: AppProject, w: W.Who, coll: str, row_id: str) -> dict[str, Any]:
    """GET /track/c/<coll>/<id>: the customer's own order (or staff): where its rider is, distance, ETA, near / arrived."""
    from . import backend as BE
    if w.m is None and not w.owner:
        raise TrackError("Please log in first.", 401)
    st = settings(r)
    with session() as s:
        x = s.get(W.SiteAppRow, row_id)
        if x is not None:
            s.expunge(x)
    if x is None or x.site_id != _site(r) or x.coll != coll or not (w.staff or (w.id and x.owner == w.id)):
        raise TrackError("This entry was not found.", 404)
    d = BE._j(x.data, {})
    dest = point(d.get(st["loc"])) if st["loc"] else None
    out: dict[str, Any] = {"tracking": False, "status": str(d.get("status") or ""), "near": bool(d.get("_near")),
                           "arrived": bool(d.get("_arrived")), "dest": {"lat": dest[0], "lng": dest[1]} if dest else None}
    if not st["on"] or coll != st["coll"]:
        return {**out, "why": "off"}
    if out["status"] not in st["statuses"]:
        return {**out, "why": "not_on_the_way"}
    rid = str(d.get("_to") or "")
    rd = _rider(r, rid) if rid else None
    if rd is None or not _active(rd):
        return {**out, "why": "no_rider"}
    out["rider"] = {"name": _first(rd.name), "member": rid if w.staff else "rider"}
    if rd.lat is None or rd.at is None:
        return {**out, "why": "no_position"}
    age = (now() - _aware(rd.at)).total_seconds()
    out["rider"].update({"lat": rd.lat, "lng": rd.lng, "at": _aware(rd.at).isoformat(), "fresh": age <= FRESH_S})
    out["tracking"] = True
    if dest:
        dist = km((rd.lat, rd.lng), dest)
        out["km"], out["eta_min"] = round(dist, 2), eta_min(dist, rd.speed)
        out["eta_note"] = "estimate"
    return out


def riders(r: AppProject, w: W.Who) -> dict[str, Any]:
    """Staff / the owner: every rider on shift with the last position and how many of their orders are on the way."""
    if not w.staff:
        raise TrackError("You do not have permission for this.", 403)
    st = settings(r)
    ensure_table()
    with session() as s:
        xs = s.scalars(select(AppRider).where(AppRider.site_id == _site(r), AppRider.on == 1)).all()
        for x in xs:
            s.expunge(x)
    out = []
    for x in xs:
        if not _active(x):
            continue
        item: dict[str, Any] = {"member": x.member, "name": _first(x.name), "started": _aware(x.started).isoformat()}
        if x.lat is not None and x.at is not None:
            age = (now() - _aware(x.at)).total_seconds()
            item.update({"lat": x.lat, "lng": x.lng, "at": _aware(x.at).isoformat(), "fresh": age <= FRESH_S})
        item["orders"] = len(_orders_of(r, st, x.member, None, None)) if st["on"] else 0
        out.append(item)
    return {"on": st["on"], "riders": out}


def mine(r: AppProject, w: W.Who) -> dict[str, Any]:
    """The rider's own shift state (the shift button)."""
    _staff(w, r)
    x = _rider(r, w.id)
    return {"on": _active(x), "started": _aware(x.started).isoformat() if _active(x) and x.started else "",
            "tracking": settings(r)["on"]}
