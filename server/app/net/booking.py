"""v0.113 Services and bookings on the same deal engine (research "quote, tap, proof, warranty", Diagrams 3.1 / 4.1 / 4.5).

A service is an ordinary deal whose ask carries `service` {what, at, when, area} (items optional) and whose quote carries
the free SLOTS - "slots as quotes":
  * Seller side: her rate card = stock rows with kind "service" (price, GST, warranty days; never counted) + her
    `ServiceRules` (open days, hours, slot length, how many jobs per slot, earliest / furthest booking, visit charge and
    whether it is adjusted into the repair bill, where the work happens, default warranty, job prefix J).
    `draft` builds the quote by code: matched rate-card lines (+ a visit charge line) and `free_slots` (her hours minus
    every booked / held slot), at most 3 per day, 6 in all. The quote also carries `estimate` {min, max} (a range she
    gives for unknown work; the bill can only grow past it by lines the customer approves on site) and `service`.
  * Buyer side: `check_extra` re-checks the slots (future, on the hour grid of the slot length is not assumed, max 8,
    unique, inside 60 days) and the estimate. Her tap on one slot = `deal.confirm(slot=, address=)`: the address (only
    for work at her place) is released ONLY now, with the confirm. The seller's Hoola checks the slot is still free.
  * Accept = a job number (J-1001), the slot is held; no pick list, no money card yet (the bill comes when the work is
    done, see job.py). Reminders (`tick`): the customer 1 day and 2 hours before, the seller in the morning of the day.
A clinic appointment is the same thing with work "at my place" and a fee line; the token = the job number.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, now, session
from . import policy

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
AT = ("their_place", "my_place")                      # from the SELLER's side: at the customer's place / at my shop / clinic
HOLD_STATES = ("confirmed", "accepted", "on_way", "working")
MAX_SLOTS_SHOWN, PER_DAY = 6, 3
STATS = {"drafts": 0, "slot_taken": 0, "reminders": 0}


class ServiceRules(Base):
    __tablename__ = "hoola_service_rules"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    days: Mapped[list] = mapped_column(JSON, default=lambda: ["mon", "tue", "wed", "thu", "fri", "sat"])
    open_at: Mapped[str] = mapped_column(String(5), default="09:00")
    close_at: Mapped[str] = mapped_column(String(5), default="19:00")
    slot_minutes: Mapped[int] = mapped_column(Integer, default=60)
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    lead_minutes: Mapped[int] = mapped_column(Integer, default=60)
    horizon_days: Mapped[int] = mapped_column(Integer, default=7)
    visit_fee: Mapped[float] = mapped_column(Float, default=0.0)
    visit_gst: Mapped[float] = mapped_column(Float, default=0.0)
    visit_adjust: Mapped[bool] = mapped_column(Boolean, default=True)    # visit charge waived when the repair is done
    at: Mapped[str] = mapped_column(String(12), default="their_place")
    warranty_days: Mapped[int] = mapped_column(Integer, default=30)
    prefix: Mapped[str] = mapped_column(String(6), default="J")
    closed_on: Mapped[list] = mapped_column(JSON, default=list)        # holiday dates YYYY-MM-DD
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def _dl():
    from . import deal as dl
    return dl


def _tz(tenant: str):
    try:
        from ..life import tz_of
        return tz_of(tenant)
    except Exception:
        return timezone(timedelta(hours=5, minutes=30))


def _utc(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _hm(x: str) -> time:
    h, m = (int(v) for v in str(x).split(":"))
    return time(h, m)


def rules(tenant: str) -> ServiceRules:
    with session() as s:
        r = s.get(ServiceRules, tenant)
        if r is None:
            r = ServiceRules(tenant_id=tenant, days=["mon", "tue", "wed", "thu", "fri", "sat"], open_at="09:00", close_at="19:00",
                             slot_minutes=60, capacity=1, lead_minutes=60, horizon_days=7, visit_fee=0.0, visit_gst=0.0,
                             visit_adjust=True, at="their_place", warranty_days=30, prefix="J", closed_on=[], updated_at=now())
            s.add(r)
            s.flush()
        s.expunge(r)
        return r


def rules_view(tenant: str) -> dict[str, Any]:
    r = rules(tenant)
    return {"days": r.days or [], "open_at": r.open_at, "close_at": r.close_at, "slot_minutes": r.slot_minutes,
            "capacity": r.capacity, "lead_minutes": r.lead_minutes, "horizon_days": r.horizon_days, "visit_fee": r.visit_fee,
            "visit_gst": r.visit_gst, "visit_adjust": r.visit_adjust, "at": r.at, "warranty_days": r.warranty_days,
            "prefix": r.prefix, "closed_on": r.closed_on or [], "services": [x for x in _dl().stock(tenant) if x["kind"] == "service"]}


def set_rules(tenant: str, **kw) -> dict[str, Any]:
    dl = _dl()
    E = dl.DealError
    rules(tenant)
    with session() as s:
        r = s.get(ServiceRules, tenant)
        if "days" in kw and kw["days"] is not None:
            ds = [str(x).lower()[:3] for x in (kw["days"] if isinstance(kw["days"], list) else str(kw["days"]).split(","))]
            ds = list(DAYS) if any(x in ("dai", "roz", "all") for x in ds) else [x for x in DAYS if x in ds]
            if not ds:
                raise E("days: mon..sun")
            r.days = ds
        for k in ("open_at", "close_at"):
            if kw.get(k):
                try:
                    _hm(kw[k])
                except Exception:
                    raise E(f"{k}: HH:MM")
                setattr(r, k, f"{_hm(kw[k]).hour:02d}:{_hm(kw[k]).minute:02d}")
        for k, lo, hi in (("slot_minutes", 10, 480), ("capacity", 1, 50), ("lead_minutes", 0, 2880), ("horizon_days", 1, 60),
                          ("warranty_days", 0, 3650)):
            if kw.get(k) is not None:
                v = dl._num(kw[k], lo, hi)
                if v is None:
                    raise E(f"{k}: {lo}-{hi}")
                setattr(r, k, int(v))
        if kw.get("visit_fee") is not None:
            v = dl._num(kw["visit_fee"], 0, 1e6)
            if v is None:
                raise E("visit_fee galat")
            r.visit_fee = dl._r2(v)
        if kw.get("visit_gst") is not None:
            g = dl._num(kw["visit_gst"], 0, 40)
            if g is None or g not in dl.GST_RATES:
                raise E("visit_gst galat")
            r.visit_gst = g
        if isinstance(kw.get("visit_adjust"), bool):
            r.visit_adjust = kw["visit_adjust"]
        if kw.get("at") in AT:
            r.at = kw["at"]
        if isinstance(kw.get("prefix"), str) and kw["prefix"].strip().isalpha() and len(kw["prefix"].strip()) <= 6:
            r.prefix = kw["prefix"].strip().upper()
        if isinstance(kw.get("closed_on"), list):
            out = []
            for x in kw["closed_on"][:60]:
                try:
                    out.append(date.fromisoformat(str(x)).isoformat())
                except ValueError:
                    raise E(f"closed_on: {x} (YYYY-MM-DD)")
            r.closed_on = sorted(set(out))
        if _hm(r.close_at) <= _hm(r.open_at):
            raise E("band hone ka samay khulne ke baad ho")
        r.updated_at = now()
    return rules_view(tenant)


# ---------------------------------------------------------------- slots
def _slot_of(d) -> str:
    return str(((d.ask or {}).get("slot")) or "")


def taken(tenant: str, exclude: str = "") -> dict[str, int]:
    """How many jobs hold each slot start (UTC iso, minute precision): confirmed / booked / on the way / working, plus
    warranty revisits that have a slot."""
    dl = _dl()
    out: dict[str, int] = {}
    with session() as s:
        rows = s.scalars(select(dl.Deal).where(dl.Deal.tenant_id == tenant, dl.Deal.role == "seller")).all()
        for d in rows:
            if d.id == exclude or not (d.ask or {}).get("service"):
                continue
            keys = []
            if d.state in HOLD_STATES and _slot_of(d):
                keys.append(_slot_of(d))
            rv = ((d.job or {}).get("revisit") or {})
            if rv.get("slot") and rv.get("status") == "booked":
                keys.append(rv["slot"])
            for k in keys:
                t = _key(k)
                if t:
                    out[t] = out.get(t, 0) + 1
    return out


def _key(iso: str) -> str:
    d = _dl()._when(iso)
    return _utc(d).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M") if d else ""


def _grid(r: ServiceRules, tenant: str, day: date) -> list[datetime]:
    tz = _tz(tenant)
    if DAYS[day.weekday()] not in (r.days or []) or day.isoformat() in (r.closed_on or []):
        return []
    t = datetime.combine(day, _hm(r.open_at), tz)
    end = datetime.combine(day, _hm(r.close_at), tz)
    out = []
    while t + timedelta(minutes=r.slot_minutes) <= end:
        out.append(t)
        t += timedelta(minutes=r.slot_minutes)
    return out


def free_slots(tenant: str, n: int = MAX_SLOTS_SHOWN, exclude: str = "", start: datetime | None = None) -> list[str]:
    r = rules(tenant)
    used = taken(tenant, exclude)
    tz = _tz(tenant)
    earliest = (start or now()) + timedelta(minutes=r.lead_minutes)
    today = earliest.astimezone(tz).date()
    out = []
    for k in range(0, r.horizon_days + 1):
        per = 0
        for t in _grid(r, tenant, today + timedelta(days=k)):
            if t < earliest:
                continue
            key = t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")
            if used.get(key, 0) >= r.capacity:
                continue
            out.append(t.astimezone(timezone.utc).replace(microsecond=0).isoformat())
            per += 1
            if per >= PER_DAY or len(out) >= n:
                break
        if len(out) >= n:
            break
    return out


def slot_free(tenant: str, slot: str, exclude: str = "") -> bool:
    r = rules(tenant)
    t = _dl()._when(slot)
    if t is None or t < now():
        return False
    local = _utc(t).astimezone(_tz(tenant))
    if not any(abs((g - local).total_seconds()) < 60 for g in _grid(r, tenant, local.date())):
        return False
    return taken(tenant, exclude).get(_key(slot), 0) < r.capacity


def say_slot(tenant: str, iso: str) -> str:
    t = _dl()._when(iso)
    if t is None:
        return ""
    loc = _utc(t).astimezone(_tz(tenant))
    day = loc.date()
    today = now().astimezone(_tz(tenant)).date()
    d = "aaj" if day == today else ("kal" if day == today + timedelta(days=1) else loc.strftime("%d/%m"))
    h = loc.hour % 12 or 12
    return f"{d} {h}:{loc.minute:02d} {'am' if loc.hour < 12 else 'pm'}"


# ---------------------------------------------------------------- ask / quote
def check_service(raw: Any) -> dict[str, Any] | None:
    if not raw:
        return None
    if not isinstance(raw, dict):
        raise _dl().DealError("service: {what, at, when}")
    what = policy.quote(raw.get("what"), 300)
    if not what:
        raise _dl().DealError("Kya kaam karwana hai? (service.what)")
    at = raw.get("at") if raw.get("at") in ("home", "visit", "") else ""
    return {"what": what, "at": at, "when": policy.quote(raw.get("when"), 120), "area": policy.quote(raw.get("area"), 160)}


def draft(tenant: str, ask: dict[str, Any]) -> dict[str, Any]:
    """The seller's quote for a service, made by code from her rate card + her free slots."""
    dl = _dl()
    r = rules(tenant)
    svc = ask.get("service") or {}
    cat = [x for x in dl._catalog_items(tenant) if x.get("kind") == "service"]
    lines = []
    asked = list(ask.get("items") or []) or [{"item": svc.get("what", ""), "qty": 1, "unit": ""}]
    free_text = not (ask.get("items") or [])
    for a in asked:
        m = dl.match(cat, a["item"]) if cat else None
        if m is None and free_text and r.visit_fee > 0:
            continue                                   # e.g. a clinic: the fee line is the quote, the words stay the 'what'
        if m is None:
            lines.append({"item": a["item"][:120], "asked": float(a["qty"]), "qty": float(a["qty"]), "unit": a.get("unit", ""),
                          "price": None, "gst_pct": 0.0, "amount": 0.0, "gst": 0.0, "status": "not_found"})
            continue
        lines.append(dl._line(m["name"], float(a["qty"]), float(a["qty"]), m["unit"] or a.get("unit", ""),
                              dl.price_for(m, float(a["qty"])), m["gst_pct"], "ok", stock_id=m["id"], asked_as=a["item"]))
    if r.visit_fee > 0 and not any("visit" in dl.norm(l["item"]) for l in lines):
        lines.insert(0, dl._line("Visit charge", 1.0, 1.0, "visit", r.visit_fee, r.visit_gst, "ok"))
    q = dl.totals({"lines": lines})
    q["slots"] = free_slots(tenant)
    q["slot_minutes"] = r.slot_minutes
    q["service"] = {"what": svc.get("what", ""), "at": r.at, "warranty_days": _warranty_for(tenant, lines)}
    q["estimate"] = {}
    STATS["drafts"] += 1
    return q


def _warranty_for(tenant: str, lines: list[dict[str, Any]]) -> int:
    dl = _dl()
    r = rules(tenant)
    best = None
    with session() as s:
        for l in lines:
            if not l.get("stock_id"):
                continue
            it = s.get(dl.StockItem, l["stock_id"])
            if it is not None and it.warranty_days is not None:
                best = max(best or 0, it.warranty_days)
    return int(best if best is not None else r.warranty_days)


def quote_extra(tenant: str, d, base: dict[str, Any], slots: Any = None, estimate: Any = None) -> dict[str, Any]:
    """What a service quote carries besides the lines, fresh at send time (her own slot choice / estimate allowed)."""
    dl = _dl()
    r = rules(tenant)
    if slots:
        pick = [s for s in (slots if isinstance(slots, list) else [slots]) if slot_free(tenant, str(s), d.id)]
        if not pick:
            raise dl.DealError("Yeh samay khaali nahi (ya aapke ghanton ke bahar).")
        sl = [_dl()._when(s).astimezone(timezone.utc).replace(microsecond=0).isoformat() for s in pick][:8]
    else:
        sl = free_slots(tenant, exclude=d.id)
    if not sl:
        raise dl.DealError("Agle dinon mein koi khaali samay nahi. Niyam mein ghante / din badhaiye.")
    est = {}
    if estimate:
        lo, hi = dl._num((estimate or {}).get("min"), 0, dl.MAX_TOTAL), dl._num((estimate or {}).get("max"), 0, dl.MAX_TOTAL)
        if lo is None or hi is None or hi < lo:
            raise dl.DealError("estimate: {min, max} (min <= max)")
        est = {"min": dl._r2(lo), "max": dl._r2(hi)}
    svc = dict((base.get("service") or {}))
    return {"slots": sl, "slot_minutes": r.slot_minutes, "estimate": est,
            "service": {"what": policy.quote(svc.get("what") or ((d.ask or {}).get("service") or {}).get("what"), 300),
                        "at": r.at, "warranty_days": int(svc.get("warranty_days") or _warranty_for(tenant, base.get("lines") or []))}}


def check_extra(body: dict[str, Any]) -> dict[str, Any]:
    """The buyer's check of a service quote's slots / estimate (empty for goods)."""
    if not isinstance(body.get("service"), dict):
        return {}
    dl = _dl()
    E = dl.DealError
    raw = body.get("slots")
    if not isinstance(raw, list) or not raw or len(raw) > 8:
        raise E("slots galat")
    out = []
    for x in raw:
        t = dl._when(x)
        if t is None or t < now() - timedelta(minutes=1) or t > now() + timedelta(days=60):
            raise E("slot galat (beet chuka / bahut aage)")
        iso = _utc(t).astimezone(timezone.utc).replace(microsecond=0).isoformat()
        if iso in out:
            raise E("slot dohraya")
        out.append(iso)
    mins = dl._num(body.get("slot_minutes"), 5, 1440)
    if mins is None:
        raise E("slot_minutes galat")
    est = body.get("estimate") if isinstance(body.get("estimate"), dict) else {}
    e2 = {}
    if est:
        lo, hi = dl._num(est.get("min"), 0, dl.MAX_TOTAL), dl._num(est.get("max"), 0, dl.MAX_TOTAL)
        if lo is None or hi is None or hi < lo:
            raise E("estimate galat")
        e2 = {"min": dl._r2(lo), "max": dl._r2(hi)}
    svc = body["service"]
    wd = dl._num(svc.get("warranty_days"), 0, 3650)
    return {"slots": out, "slot_minutes": int(mins), "estimate": e2,
            "service": {"what": policy.quote(svc.get("what"), 300), "at": svc.get("at") if svc.get("at") in AT else "their_place",
                        "warranty_days": int(wd or 0)}}


def confirm_part(d, slot: str, address: str) -> dict[str, Any]:
    """Buyer: her chosen slot (must be one offered) and, for work at her place, the address - released only now."""
    dl = _dl()
    q = d.quote or {}
    if not q.get("service"):
        return {}
    slots = q.get("slots") or []
    if not slot and len(slots) == 1:
        slot = slots[0]
    t = dl._when(slot) if slot else None
    iso = _utc(t).astimezone(timezone.utc).replace(microsecond=0).isoformat() if t else ""
    if iso not in slots:
        raise dl.DealError("Inme se ek samay chuniye: " + ", ".join(say_slot(d.tenant_id, s) for s in slots))
    out = {"slot": iso}
    if q["service"].get("at") == "their_place":
        addr = policy.quote(address, 300)
        if not addr:
            raise dl.DealError("Kaam aapke ghar / jagah par hoga: pata likhiye (sirf booking par hi unhe jaata hai).")
        if policy.secret_found(addr):
            raise dl.DealError("Pate mein mana ki gayi jaankari hai.")
        out["address"] = addr
    return out


def on_confirm(tenant: str, d, raw: dict[str, Any]) -> dict[str, Any]:
    """Seller: the slot must be one offered and still free; the address is kept with the job."""
    dl = _dl()
    q = d.quote or {}
    if not q.get("service"):
        return {}
    iso = str(raw.get("slot") or "")
    if iso not in (q.get("slots") or []):
        raise dl.DealError("yeh samay quote mein nahi tha")
    if not slot_free(tenant, iso, d.id):
        STATS["slot_taken"] += 1
        raise dl.DealError("yeh samay ab khaali nahi; naya quote maangiye")
    out = {"slot": iso}
    if q["service"].get("at") == "their_place":
        addr = policy.quote(raw.get("address"), 300)
        if not addr:
            raise dl.DealError("pata nahi aaya")
        out["address"] = addr
    return out


def is_service(d) -> bool:
    return bool((d.quote or {}).get("service") or (d.ask or {}).get("service"))


# ---------------------------------------------------------------- reminders
def tick() -> int:
    dl = _dl()
    n = 0
    with session() as s:
        rows = s.scalars(select(dl.Deal).where(dl.Deal.state.in_(("accepted", "on_way")))).all()
        for r in rows:
            s.expunge(r)
    for d in rows:
        try:
            if not is_service(d) or not _slot_of(d):
                continue
            t = _utc(dl._when(_slot_of(d)))
            if t is None:
                continue
            left = t - now()
            tm = dict(d.timers or {})
            key = None
            if d.role == "buyer":
                if timedelta(hours=1) < left <= timedelta(hours=2) and not tm.get("rem_2h"):
                    key, say = "rem_2h", f"Yaad dila doon: {dl._say_who(d.peer)} {say_slot(d.tenant_id, _slot_of(d))} ko ({d.number})."
                elif timedelta(hours=2) < left <= timedelta(hours=24) and not tm.get("rem_1d"):
                    key, say = "rem_1d", f"Kal / aaj: {dl._say_who(d.peer)} ke saath {say_slot(d.tenant_id, _slot_of(d))} ({d.number})."
            else:
                if timedelta(0) < left <= timedelta(hours=12) and not tm.get("rem_job"):
                    key, say = "rem_job", (f"Aaj ka kaam {d.number}: {((d.quote or {}).get('service') or {}).get('what', '')} "
                                           f"{say_slot(d.tenant_id, _slot_of(d))}" +
                                           (f", pata: {(d.ask or {}).get('address')}" if (d.ask or {}).get("address") else ""))
            if key:
                tm[key] = 1
                with session() as s:
                    row = s.get(dl.Deal, d.id)
                    if row is not None:
                        row.timers = tm
                dl._publish(d.tenant_id, dl._get(d.tenant_id, d.id), "info", say)
                STATS["reminders"] += 1
                n += 1
        except Exception:
            continue
    return n


_ = (Integer, Float)
