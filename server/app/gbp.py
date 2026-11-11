"""Google Maps Phase 8a APNI DUKAAN (READ side): her own Business Profile - locations and the Performance numbers.

Specs: Google's machine-readable API definitions (the discovery documents for mybusinessaccountmanagement v1,
mybusinessbusinessinformation v1 and businessprofileperformance v1 - the prose docs were unreachable). NOT covered
because their spec could not be read: reviews, posts and Q&A live only in the legacy My Business v4 API, whose
discovery document is gone - so there is deliberately no review / post code here (see docs/HISTORY.md v0.467).

Rules baked in (docs/research/maps/02_places_and_business_profile.md): the Business Profile policies forbid to
*"pre-fetch, cache, index, or store"* its content and to aggregate it, so NOTHING from these answers is written down -
every call reads live and hands the answer to the person who asked. Read-only: no write here. The first writes
(hours / phone / description) need a hash-bound tap and the 10-edits-a-minute cap; they are the next step.

Gate: every call fails with a quota of 0 until Google approves her Cloud project for Basic API access, and her
Google sign-in must carry the business.manage scope. Both are reported by name, never guessed around.
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta

import httpx

from . import google_auth

SCOPE = "https://www.googleapis.com/auth/business.manage"
ACCOUNTS_URL = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
INFO_URL = "https://mybusinessbusinessinformation.googleapis.com/v1/"
PERF_URL = "https://businessprofileperformance.googleapis.com/v1/"
READ_MASK = "name,title,storefrontAddress,phoneNumbers,websiteUri,regularHours,metadata,openInfo"
METRICS = {   # DailyMetric enum values, from the Performance API's own definition
    "BUSINESS_IMPRESSIONS_DESKTOP_MAPS": "Seen on Maps (computer)",
    "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH": "Shown in Search (computer)",
    "BUSINESS_IMPRESSIONS_MOBILE_MAPS": "Seen on Maps (phone)",
    "BUSINESS_IMPRESSIONS_MOBILE_SEARCH": "Shown in Search (phone)",
    "BUSINESS_DIRECTION_REQUESTS": "Asked for directions",
    "CALL_CLICKS": "Tapped Call",
    "WEBSITE_CLICKS": "Opened the website",
    "BUSINESS_CONVERSATIONS": "Messages received",
    "BUSINESS_BOOKINGS": "Booking hui",
}
MAX_ACCOUNTS = 5
MAX_LOCATIONS = 20
MAX_DAYS = 540          # the Performance API serves a limited look-back; asked beyond this we refuse rather than guess


class GbpError(Exception):
    """The message is written for her."""


_client: httpx.AsyncClient | None = None


def set_client(c) -> None:   # tests
    global _client
    _client = c


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=20)
    return _client


async def _headers(tenant_id: str) -> dict:
    try:
        creds = await asyncio.to_thread(google_auth.credentials_for, tenant_id, [SCOPE])
    except google_auth.GoogleReconnect as e:
        raise GbpError(str(e)) from None
    if creds is None:
        raise GbpError("Not signed in with Google. Connect Google first (with the Business Profile permission).")
    return {"Authorization": f"Bearer {creds.token}"}


def explain(r: httpx.Response) -> str:
    try:
        err = (r.json() or {}).get("error", {})
    except ValueError:
        err = {}
    st, msg = str(err.get("status", "")), str(err.get("message", r.text))[:200]
    low = msg.lower()
    if r.status_code == 401 or "insufficient authentication scopes" in low or "insufficient_scope" in low:
        return ("The Google sign-in does not have the Business Profile permission (business.manage). Connect Google again and "
                "tick the Business Profile box.")
    if "has not been used" in low or "is disabled" in low or "service_disabled" in low:
        return "This Business Profile API is not enabled in the Google Cloud project."
    if r.status_code == 429 or st == "RESOURCE_EXHAUSTED" or "quota" in low:
        return ("Google has not granted Business Profile API access yet (quota 0): this will not work until the 'Application for "
                "Basic API Access' is approved. After approval the quota shows 300 per minute.")
    if r.status_code == 403:
        return "Google refused: this Google account has no access to that Business Profile, or the API is not approved."
    return f"Google Business Profile error {r.status_code}: {msg}"


async def _get(url: str, headers: dict, params=None) -> dict:
    r = await _http().get(url, headers=headers, params=params)
    if r.status_code >= 400:
        raise GbpError(explain(r))
    return r.json() or {}


def _addr(a: dict | None) -> str:
    a = a or {}
    parts = list(a.get("addressLines") or []) + [a.get("sublocality"), a.get("locality"),
                                                 a.get("administrativeArea"), a.get("postalCode")]
    return ", ".join(str(p) for p in parts if p)


def _hours(h: dict | None) -> list[str]:
    out = []
    for p in (h or {}).get("periods") or []:
        o, c = p.get("openTime") or {}, p.get("closeTime") or {}
        out.append(f"{str(p.get('openDay', ''))[:3].title()} "
                   f"{int(o.get('hours') or 0):02d}:{int(o.get('minutes') or 0):02d}-"
                   f"{int(c.get('hours') or 0):02d}:{int(c.get('minutes') or 0):02d}")
    return out


def location_row(loc: dict) -> dict:
    md = loc.get("metadata") or {}
    row = {"location": loc.get("name", ""), "title": loc.get("title", ""), "address": _addr(loc.get("storefrontAddress")),
           "phone": (loc.get("phoneNumbers") or {}).get("primaryPhone", ""), "website": loc.get("websiteUri", ""),
           "hours": _hours(loc.get("regularHours")), "maps_link": md.get("mapsUri", ""),
           "review_link": md.get("newReviewUri", ""), "place_id": md.get("placeId", ""),
           "edit_pending": bool(md.get("hasPendingEdits")),
           "status": (loc.get("openInfo") or {}).get("status", "")}
    return {k: v for k, v in row.items() if v not in ("", [], None, False)}


async def locations(tenant_id: str) -> list[dict]:
    """Her accounts' locations, read live (nothing kept)."""
    h = await _headers(tenant_id)
    accts = (await _get(ACCOUNTS_URL, h, {"pageSize": 20})).get("accounts") or []
    out: list[dict] = []
    for a in accts[:MAX_ACCOUNTS]:
        name = a.get("name", "")
        if not name:
            continue
        data = await _get(f"{INFO_URL}{name}/locations", h, {"readMask": READ_MASK, "pageSize": MAX_LOCATIONS})
        for loc in data.get("locations") or []:
            row = location_row(loc)
            row["account"] = a.get("accountName") or name
            out.append(row)
    return out[:MAX_LOCATIONS]


def _loc_name(loc: str) -> str:
    s = str(loc or "").strip()
    s = s.split("/locations/")[-1] if "/locations/" in s else s.replace("locations/", "")
    if not s.isdigit():
        raise GbpError("The location number (locations/123...) is needed - gbp_locations gives it.")
    return f"locations/{s}"


def sum_series(resp: dict) -> dict:
    """metric -> total over the range. Values arrive as strings; a metric with no days returns 0, never a guess."""
    out: dict = {}
    for ms in resp.get("multiDailyMetricTimeSeries") or []:
        for ts in ms.get("dailyMetricTimeSeries") or []:
            m = ts.get("dailyMetric", "")
            tot = 0
            for dv in (ts.get("timeSeries") or {}).get("datedValues") or []:
                try:
                    tot += int(dv.get("value") or 0)
                except (TypeError, ValueError):
                    pass
            out[m] = out.get(m, 0) + tot
    return out


async def numbers(tenant_id: str, location: str, days: int | None = 30, today: date | None = None) -> dict:
    days = 30 if days is None else int(days)        # an explicit 0 is refused below, never turned into 30
    if not 1 <= days <= MAX_DAYS:
        raise GbpError(f"Days must be between 1 and {MAX_DAYS}.")
    name = _loc_name(location)
    end = (today or date.today()) - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    params = [("dailyMetrics", m) for m in METRICS]
    for k, d in (("startDate", start), ("endDate", end)):
        params += [(f"dailyRange.{k}.year", d.year), (f"dailyRange.{k}.month", d.month), (f"dailyRange.{k}.day", d.day)]
    h = await _headers(tenant_id)
    resp = await _get(f"{PERF_URL}{name}:fetchMultiDailyMetricsTimeSeries", h, params)
    tot = sum_series(resp)
    seen = {m: tot.get(m, 0) for m in METRICS}
    shown = seen.get("BUSINESS_IMPRESSIONS_DESKTOP_MAPS", 0) + seen.get("BUSINESS_IMPRESSIONS_DESKTOP_SEARCH", 0) \
        + seen.get("BUSINESS_IMPRESSIONS_MOBILE_MAPS", 0) + seen.get("BUSINESS_IMPRESSIONS_MOBILE_SEARCH", 0)
    return {"location": name, "from": start.isoformat(), "to": end.isoformat(), "days": days,
            "times_shown": shown,
            "actions": {METRICS[m]: seen[m] for m in METRICS if not m.startswith("BUSINESS_IMPRESSIONS")},
            "shown_where": {METRICS[m]: seen[m] for m in METRICS if m.startswith("BUSINESS_IMPRESSIONS")},
            "has_data": any(seen.values())}
