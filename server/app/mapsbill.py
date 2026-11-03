"""v0.449 PAISA PEHLE - the priced, capped, terms-shaped layer under every Google Maps call.

Three jobs, and the first one is why this file exists:

1. A DAILY RUPEE CAP THAT REFUSES. Until now `maps.py` called Google and Google billed her, with no cache, no
   cap and no budget anywhere - a loop over a list of addresses billed every row. Studio and Arena have had a
   ceiling for versions (`studio_project_usd`, `site_arena_max_inr`); Maps had none. `charge()` raises
   MapsCapped BEFORE the call goes out, so the answer is "aaj ka Maps budget khatam" and never a surprise bill.

2. A CACHE WHOSE SHAPE COMES FROM THE LICENCE, NOT FROM CONVENIENCE. Google Maps Platform is licensed as a
   live lookup service, not a data source (docs/research/maps/01_terms_caching_and_leads.md). The Places
   section of the Service Specific Terms is exactly 14.1-14.3 and permits caching exactly two things:
     - `place_id`, indefinitely   (SST A.3: "Customer may cache the Google ID values")
     - lat / lng, for 30 days     (SST 14.3: "after which Customer must delete the cached latitude and
                                   longitude values")
   There is NO permission anywhere for a name, address, phone, website, rating or opening hours, and ToS
   3.2.3(b) makes the absence of a permission a prohibition ("Customer will not cache Google Maps Content
   except as expressly permitted"). So this cache stores place_id + lat/lng + HER OWN query text, and nothing
   else, ever. Adding a `name` column to this table would be a licence breach, not an optimisation.

3. A NUMBER SHE CAN SEE. Every call's cost is recorded, so a result can carry what it cost and the proof card
   can print rupees per answer.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .config import get_settings
from .db import Base, session

log = logging.getLogger("santosh.mapsbill")

# ---------------------------------------------------------------- the licence's own clock
LATLNG_TTL = timedelta(days=30)   # SST 14.3 / 6.3.1 - not a tuning knob. Raising it is a breach.


class MapsCapped(Exception):
    """Today's Maps budget is spent. Raised BEFORE the HTTP call, so nothing is billed."""


# ---------------------------------------------------------------- price table
# USD per 1,000 requests at the first volume tier (0-100,000). Filled from Google's own SKU pages; a SKU we
# could not source is left None ON PURPOSE rather than guessed, and None is charged at _fallback_usd() - the
# highest rate we do know - so an unknown price can only ever make the cap FIRE EARLY, never overspend.
# Sources + the India price list: docs/research/maps/04_prices.md
SKU_TEXT_IDS = "places.text.ids"            # Essentials (IDs Only) - free, Unlimited, but returns no name
SKU_TEXT_PRO = "places.text.pro"
SKU_TEXT_ENT = "places.text.enterprise"
SKU_NEARBY_PRO = "places.nearby.pro"        # Nearby has NO Essentials tier: every field is Pro or above
SKU_NEARBY_ENT = "places.nearby.enterprise"
SKU_DETAILS_IDS = "places.details.ids"
SKU_DETAILS_PRO = "places.details.pro"
SKU_DETAILS_ENT = "places.details.enterprise"
SKU_DETAILS_REFRESH = "places.details.refresh"
SKU_GEOCODE = "geocoding"
SKU_ROUTES = "routes.compute"
SKU_MATRIX = "routes.matrix"                # Phase 4 - billed PER ELEMENT, see UNIT below
SKU_DETAILS_ESS = "places.details.essentials"
SKU_AUTOCOMPLETE = "places.autocomplete"            # Phase 6
SKU_AUTOCOMPLETE_SESSION = "places.autocomplete.session"
SKU_ADDRESS_PRO = "address.pro"                     # Phase 6
SKU_ADDRESS_ENT = "address.enterprise"
SKU_DYNAMIC_MAP = "maps.dynamic"                    # Phase 2 option B - a Google map load
SKU_STATIC_MAP = "maps.static"                      # Phase 7
SKU_STREETVIEW = "streetview.static"                # Phase 7
SKU_STREETVIEW_META = "streetview.metadata"         # free - check a panorama exists before paying for it

# ---------------------------------------------------------------- the price list
# USD per 1,000 billable events, first paid tier. India is a SEPARATE and much cheaper list, in USD, with 7x
# the free caps and only two paid bands - so using the global numbers for Indian traffic overstates the bill
# roughly threefold. Sources and the full table: docs/research/maps/04_prices.md
#
# THE BILLING UNIT IS THE REQUEST, not the result. Each Places SKU's billable event is "Successful request
# for <tier> fields", and "The request is billed at the highest SKU applicable to the requested fields" - so
# the field mask picks the TIER and the request is charged once. One Text Search returning 20 places with an
# Enterprise field in the mask is ONE Enterprise event, not twenty. Counting results would overstate ~20x.
# The exception is computeRouteMatrix: "billed per ELEMENT returned from the request" - origins x destinations.
_INDIA: dict[str, float] = {
    SKU_TEXT_IDS: 0.0, SKU_TEXT_PRO: 9.60, SKU_TEXT_ENT: 10.50,
    SKU_NEARBY_PRO: 9.60, SKU_NEARBY_ENT: 10.50,
    SKU_DETAILS_IDS: 0.0, SKU_DETAILS_ESS: 1.50, SKU_DETAILS_PRO: 5.10, SKU_DETAILS_ENT: 6.00,
    SKU_DETAILS_REFRESH: 0.0,
    SKU_GEOCODE: 1.50, SKU_ROUTES: 4.50, SKU_MATRIX: 4.50,
    SKU_AUTOCOMPLETE: 0.85, SKU_AUTOCOMPLETE_SESSION: 0.0,
    SKU_ADDRESS_PRO: 5.10, SKU_ADDRESS_ENT: 7.50,
    SKU_DYNAMIC_MAP: 2.10, SKU_STATIC_MAP: 0.60, SKU_STREETVIEW: 2.10, SKU_STREETVIEW_META: 0.0,
}
_GLOBAL: dict[str, float] = {
    SKU_TEXT_IDS: 0.0, SKU_TEXT_PRO: 32.00, SKU_TEXT_ENT: 35.00,
    SKU_NEARBY_PRO: 32.00, SKU_NEARBY_ENT: 35.00,
    SKU_DETAILS_IDS: 0.0, SKU_DETAILS_ESS: 5.00, SKU_DETAILS_PRO: 17.00, SKU_DETAILS_ENT: 20.00,
    SKU_DETAILS_REFRESH: 0.0,
    SKU_GEOCODE: 5.00, SKU_ROUTES: 15.00, SKU_MATRIX: 15.00,
    SKU_AUTOCOMPLETE: 2.83, SKU_AUTOCOMPLETE_SESSION: 0.0,
    SKU_ADDRESS_PRO: 17.00, SKU_ADDRESS_ENT: 25.00,
    SKU_DYNAMIC_MAP: 7.00, SKU_STATIC_MAP: 2.00, SKU_STREETVIEW: 7.00, SKU_STREETVIEW_META: 0.0,
}
# ASSUMED, and said so out loud: Routes is tiered Essentials / Pro / Enterprise and no Google page we found
# maps OUR field mask (TRAFFIC_AWARE + navigationInstruction) to a tier. We charge the DEAREST tier for
# routes and the matrix, which can only make the cap fire early. ASSUMED_TIER is reported by /api/maps/usage
# so the guess is visible instead of silent, and is the first thing to fix against her real bill.
ASSUMED_TIER = {SKU_ROUTES: "enterprise", SKU_MATRIX: "enterprise", SKU_ADDRESS_ENT: "enterprise"}

# Free events a MONTH, per SKU. These belong to the BILLING ACCOUNT, not to one user: "Google aggregates
# service usage for all projects linked to the customer billing account", so the counter below is global
# across every tenant sharing the key. UNLIMITED means free however often it is called.
UNLIMITED = -1
_FREE_INDIA: dict[str, int] = {
    SKU_TEXT_IDS: UNLIMITED, SKU_TEXT_PRO: 35000, SKU_TEXT_ENT: 7000,
    SKU_NEARBY_PRO: 35000, SKU_NEARBY_ENT: 7000,
    SKU_DETAILS_IDS: UNLIMITED, SKU_DETAILS_ESS: 70000, SKU_DETAILS_PRO: 35000, SKU_DETAILS_ENT: 7000,
    SKU_DETAILS_REFRESH: UNLIMITED,
    SKU_GEOCODE: 70000, SKU_ROUTES: 7000, SKU_MATRIX: 7000,
    SKU_AUTOCOMPLETE: 70000, SKU_AUTOCOMPLETE_SESSION: UNLIMITED,
    SKU_ADDRESS_PRO: 35000, SKU_ADDRESS_ENT: 7000,
    SKU_DYNAMIC_MAP: 70000, SKU_STATIC_MAP: 70000, SKU_STREETVIEW: 70000, SKU_STREETVIEW_META: UNLIMITED,
}
_FREE_GLOBAL: dict[str, int] = {
    SKU_TEXT_IDS: UNLIMITED, SKU_TEXT_PRO: 5000, SKU_TEXT_ENT: 1000,
    SKU_NEARBY_PRO: 5000, SKU_NEARBY_ENT: 1000,
    SKU_DETAILS_IDS: UNLIMITED, SKU_DETAILS_ESS: 10000, SKU_DETAILS_PRO: 5000, SKU_DETAILS_ENT: 1000,
    SKU_DETAILS_REFRESH: UNLIMITED,
    SKU_GEOCODE: 10000, SKU_ROUTES: 1000, SKU_MATRIX: 1000,
    SKU_AUTOCOMPLETE: 10000, SKU_AUTOCOMPLETE_SESSION: UNLIMITED,
    SKU_ADDRESS_PRO: 5000, SKU_ADDRESS_ENT: 1000,
    SKU_DYNAMIC_MAP: 10000, SKU_STATIC_MAP: 10000, SKU_STREETVIEW: 10000, SKU_STREETVIEW_META: UNLIMITED,
}

PER_REQUEST = "request"
PER_ELEMENT = "element"
UNIT: dict[str, str] = {SKU_MATRIX: PER_ELEMENT}   # everything else is per request


def _india() -> bool:
    return str(get_settings().maps_price_list or "india").lower() == "india"


def RATES() -> dict[str, float]:
    return _INDIA if _india() else _GLOBAL


def FREE_CAP() -> dict[str, int]:
    return _FREE_INDIA if _india() else _FREE_GLOBAL


def _fallback_usd() -> float:
    """A SKU we never priced is charged at the dearest one we know, so an unknown rate can only make the cap
    fire EARLY, never overspend."""
    known = [v for v in RATES().values() if v]
    return max(known) if known else float(get_settings().maps_unknown_sku_usd)


def rate_usd(sku: str) -> float:
    r = RATES().get(sku)
    return _fallback_usd() if r is None else float(r)


def price_usd(sku: str, n: int = 1) -> float:
    """What n events cost once the free cap is gone."""
    return max(0, n) * rate_usd(sku) / 1000.0


def price_inr(sku: str, n: int = 1) -> float:
    return price_usd(sku, n) * float(get_settings().maps_usd_inr)


def unsourced() -> list[str]:
    """SKUs charged at the conservative fallback because no rate was sourced. Surfaced by /api/maps/usage so a
    wrong cap is visible rather than silent."""
    r = RATES()
    return sorted(k for k in UNIT if k not in r) + sorted(k for k, v in r.items() if v is None)


# ---------------------------------------------------------------- tables
_ready = False


def ensure_tables() -> None:
    """Self-heal, per the v0.190.1 lesson: a database born before these models were registered has no table
    and every query would die 'no such table'. The first call after deploy creates them in place."""
    global _ready
    if _ready:
        return
    from . import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None:
        MapsSpend.__table__.create(eng, checkfirst=True)
        MapsPlaceCache.__table__.create(eng, checkfirst=True)
        MapsFree.__table__.create(eng, checkfirst=True)
    _ready = True


class MapsSpend(Base):
    """One row per tenant per day. The cap reads this and nothing else."""
    __tablename__ = "maps_spend"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)   # f"{tenant}:{day}"
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    calls: Mapped[int] = mapped_column(Integer, default=0)
    free_calls: Mapped[int] = mapped_column(Integer, default=0)   # inside the month's free allowance
    usd: Mapped[float] = mapped_column(Float, default=0.0)
    inr: Mapped[float] = mapped_column(Float, default=0.0)
    by_sku: Mapped[str] = mapped_column(Text, default="")   # "sku=n;sku=n" - cheap, no JSON migration needed
    refused: Mapped[int] = mapped_column(Integer, default=0)


class MapsFree(Base):
    """This month's free allowance, per SKU, GLOBAL across tenants - because the allowance belongs to the
    billing account, not to a person: "Google aggregates service usage for all projects linked to the customer
    billing account". A per-tenant counter would hand the same free calls out many times over and the real
    bill would arrive anyway."""
    __tablename__ = "maps_free"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)   # f"{YYYY-MM}:{sku}"
    month: Mapped[str] = mapped_column(String(7), index=True)
    sku: Mapped[str] = mapped_column(String(60), index=True)
    used: Mapped[int] = mapped_column(Integer, default=0)


class MapsPlaceCache(Base):
    """place_id (kept) + lat/lng (30 days, then DELETED) + her own query. NOTHING ELSE MAY BE ADDED HERE -
    see the module docstring. No name, no address, no phone, no rating, no hours."""
    __tablename__ = "maps_place_cache"
    place_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    latlng_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Her own words, not Google content. The Place IDs guide: "To refresh results in the event of an obsolete
    # place ID, store the original request that returned that place ID."
    query: Mapped[str] = mapped_column(String(300), default="")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------- the cap
def _today() -> date:
    return datetime.now(timezone.utc).date()


def _month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def free_left(sku: str) -> int:
    """How many free events of this SKU remain this month, account-wide. -1 = unlimited."""
    ensure_tables()
    cap = FREE_CAP().get(sku)
    if cap is None:
        return 0
    if cap == UNLIMITED:
        return UNLIMITED
    with session() as s:
        row = s.get(MapsFree, f"{_month()}:{sku}")
        return max(0, int(cap) - int(row.used if row else 0))


def _split_free(sku: str, n: int) -> tuple[int, int]:
    """(free_events, billed_events) for n events of this SKU."""
    left = free_left(sku)
    if left == UNLIMITED:
        return n, 0
    free = min(n, left)
    return free, n - free


def usage(tenant_id: str, day: date | None = None) -> dict:
    ensure_tables()
    d = day or _today()
    cap = float(get_settings().maps_daily_inr)
    with session() as s:   # every value is read INSIDE the session: a detached row raises once it is expired
        row = s.get(MapsSpend, f"{tenant_id}:{d.isoformat()}")
        spent = float(row.inr or 0.0) if row else 0.0
        calls = int(row.calls or 0) if row else 0
        free_calls = int(row.free_calls or 0) if row else 0
        usd = float(row.usd or 0.0) if row else 0.0
        refused = int(row.refused or 0) if row else 0
        by_sku = dict(p.split("=", 1) for p in (row.by_sku or "").split(";") if "=" in p) if row else {}
        free_rows = {r.sku: int(r.used or 0) for r in s.query(MapsFree).filter(MapsFree.month == _month()).all()}
    return {"day": d.isoformat(), "month": _month(),
            "calls": calls, "free_calls": free_calls,
            "inr": round(spent, 4), "usd": round(usd, 6),
            "cap_inr": cap, "left_inr": round(max(0.0, cap - spent), 4) if cap > 0 else None,
            "refused": refused, "by_sku": by_sku,
            "price_list": "india" if _india() else "global",
            "free_used_this_month": free_rows,
            "free_cap": {k: v for k, v in FREE_CAP().items() if free_rows.get(k)},
            "assumed_tier": ASSUMED_TIER, "unsourced_skus": unsourced()}


def quote_inr(sku: str, n: int = 1) -> float:
    """What this call would actually cost her RIGHT NOW - free while the month's allowance lasts."""
    _, billed = _split_free(sku, max(1, n))
    return price_inr(sku, billed)


def would_exceed(tenant_id: str, sku: str, n: int = 1) -> bool:
    u = usage(tenant_id)
    if u["cap_inr"] <= 0:
        return False
    return (u["inr"] + quote_inr(sku, n)) > u["cap_inr"]


@dataclass(frozen=True)
class Receipt:
    """Exactly what one call was charged. refund() reverses THIS rather than guessing afterwards how many of
    the events had been free - the first version guessed, undid the free side first, and gave back ₹0 for a
    failed call that had really been billed."""
    tenant_id: str
    sku: str
    n: int
    free: int
    billed: int
    inr: float
    usd: float
    day: date
    month: str

    def __float__(self) -> float:      # so `cost = charge(...)` still reads as rupees
        return self.inr


def charge(tenant_id: str, sku: str, n: int = 1) -> Receipt:
    """Record n billable events and return the receipt. Raises MapsCapped if this call would cross today's cap,
    BEFORE anything is spent - and without consuming the free allowance.

    `n` is REQUESTS for every SKU except computeRouteMatrix, which Google bills per element (origins x
    destinations), so its caller passes the element count. A cap of 0 or less means no ceiling.
    """
    ensure_tables()
    n = max(1, int(n))
    free_n, billed_n = _split_free(sku, n)
    cost = price_inr(sku, billed_n)
    d, mon = _today(), _month()
    key = f"{tenant_id}:{d.isoformat()}"
    cap = float(get_settings().maps_daily_inr)
    # Read AND write in ONE transaction, so there is no gap between "is there room?" and "take it".
    # Only the refusal needs a second transaction (below), because raising would roll the first one back.
    spent_now, over = 0.0, False
    with session() as s:
        row = s.get(MapsSpend, key)
        spent_now = float(row.inr or 0.0) if row is not None else 0.0
        over = cap > 0 and spent_now + cost > cap
        if not over:
            if row is None:
                row = MapsSpend(id=key, tenant_id=tenant_id, day=d)
                s.add(row)
                s.flush()
            row.calls = int(row.calls or 0) + n
            row.free_calls = int(row.free_calls or 0) + free_n
            row.usd = float(row.usd or 0.0) + price_usd(sku, billed_n)
            row.inr = float(row.inr or 0.0) + cost
            counts = dict(p.split("=", 1) for p in (row.by_sku or "").split(";") if "=" in p)
            counts[sku] = str(int(counts.get(sku, "0") or 0) + n)
            row.by_sku = ";".join(f"{k}={v}" for k, v in sorted(counts.items()))[:4000]
            if FREE_CAP().get(sku) not in (None, UNLIMITED):
                fkey = f"{mon}:{sku}"
                fr = s.get(MapsFree, fkey)
                if fr is None:
                    fr = MapsFree(id=fkey, month=mon, sku=sku)
                    s.add(fr)
                    s.flush()
                fr.used = int(fr.used or 0) + n
    if over:
        # The refusal is counted in its OWN transaction: raising inside the session above would roll the
        # increment back with it, and she would never see that anything had been refused.
        with session() as s2:
            r2 = s2.get(MapsSpend, key)
            if r2 is None:
                r2 = MapsSpend(id=key, tenant_id=tenant_id, day=d)
                s2.add(r2)
                s2.flush()
            r2.refused = int(r2.refused or 0) + 1
        log.warning("maps cap hit tenant=%s sku=%s spent=%.2f cap=%.2f", tenant_id, sku, spent_now, cap)
        raise MapsCapped(
            f"Aaj ka Google Maps budget (\u20b9{cap:.0f}) khatam ho gaya hai - ab tak \u20b9{spent_now:.2f} "
            f"lag chuke hain. Kal phir se chalega, ya aap cap badha sakti hain.")
    return Receipt(tenant_id=tenant_id, sku=sku, n=n, free=free_n, billed=billed_n,
                   inr=cost, usd=price_usd(sku, billed_n), day=d, month=mon)


def refund(receipt: Receipt | None) -> None:
    """Give back exactly what a FAILED call was charged. Google's billable event is a *successful* request
    ("Successful request for Enterprise fields"), so a 403 from an API that is not enabled, or a 5xx, costs
    her nothing - but charge() runs before the HTTP call so the cap can refuse pre-flight. Without this, a
    storm of 403s would burn her whole daily cap and the month's free allowance for calls Google never
    charged for."""
    if receipt is None:
        return
    ensure_tables()
    with session() as s:
        row = s.get(MapsSpend, f"{receipt.tenant_id}:{receipt.day.isoformat()}")
        if row is not None:
            row.calls = max(0, int(row.calls or 0) - receipt.n)
            row.free_calls = max(0, int(row.free_calls or 0) - receipt.free)
            row.usd = max(0.0, float(row.usd or 0.0) - receipt.usd)
            row.inr = max(0.0, float(row.inr or 0.0) - receipt.inr)
            counts = dict(p.split("=", 1) for p in (row.by_sku or "").split(";") if "=" in p)
            left = max(0, int(counts.get(receipt.sku, "0") or 0) - receipt.n)
            if left:
                counts[receipt.sku] = str(left)
            else:
                counts.pop(receipt.sku, None)
            row.by_sku = ";".join(f"{k}={v}" for k, v in sorted(counts.items()))[:4000]
        fr = s.get(MapsFree, f"{receipt.month}:{receipt.sku}")
        if fr is not None:
            fr.used = max(0, int(fr.used or 0) - receipt.n)


# ---------------------------------------------------------------- the cache (place_id + lat/lng only)
def remember(place_id: str, lat: float | None = None, lng: float | None = None, query: str = "") -> None:
    if not place_id:
        return
    ensure_tables()
    with session() as s:
        row = s.get(MapsPlaceCache, place_id)
        if row is None:
            row = MapsPlaceCache(place_id=place_id, query=(query or "")[:300])
            s.add(row)
        if lat is not None and lng is not None:
            row.lat, row.lng = float(lat), float(lng)
            row.latlng_at = datetime.now(timezone.utc)
        if query and not row.query:
            row.query = query[:300]


def cached_latlng(place_id: str) -> dict | None:
    """The permitted 30-day lat/lng, or None. Age is checked HERE as well as in the sweep, so an expired value
    can never be served just because the sweeper has not run yet."""
    if not place_id:
        return None
    ensure_tables()
    with session() as s:
        row = s.get(MapsPlaceCache, place_id)
        if row is None or row.lat is None or row.lng is None or row.latlng_at is None:
            return None
        at = row.latlng_at if row.latlng_at.tzinfo else row.latlng_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - at >= LATLNG_TTL:
            return None
        return {"lat": float(row.lat), "lng": float(row.lng), "place_id": place_id}


def sweep() -> int:
    """DELETE every lat/lng older than 30 days, keeping the place_id. This is the licence's own requirement
    (SST 14.3), not housekeeping. Returns how many were cleared."""
    ensure_tables()
    cutoff = datetime.now(timezone.utc) - LATLNG_TTL
    n = 0
    with session() as s:
        rows = s.query(MapsPlaceCache).filter(   # filtered in SQL, not by loading every cached place
            MapsPlaceCache.latlng_at.isnot(None), MapsPlaceCache.latlng_at <= cutoff).all()
        for row in rows:
            at = row.latlng_at if row.latlng_at.tzinfo else row.latlng_at.replace(tzinfo=timezone.utc)
            if at <= cutoff:
                row.lat = row.lng = row.latlng_at = None
                n += 1
    if n:
        log.info("maps cache: deleted lat/lng of %d places past the 30-day licence limit", n)
    return n
