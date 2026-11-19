"""Google Maps for Santosh: places near the user, directions with live traffic, address -> coordinates, and
navigation links that open the Google Maps app.

Uses Google Maps Platform with GOOGLE_MAPS_API_KEY (Places API (New), Routes API, Geocoding API).
Without a key, navigation and search links still work (they need no key); search/directions report that the
key is missing so the agent can fall back to google_search.
"""
from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

import httpx

from . import mapsbill
from .config import get_settings
from .db import Profile, UserLocation, session

log = logging.getLogger("santosh.maps")

PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"    # v0.449 Phase 3
DETAILS_URL = "https://places.googleapis.com/v1/places/"               # v0.449 Phase 3: + place_id
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
VALIDATE_URL = "https://addressvalidation.googleapis.com/v1:validateAddress"          # v0.464 Phase 6
MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"   # v0.463 Phase 4
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# v0.449 Phase 3. The field mask picks the SKU, so these ARE the price list - see docs/research/maps/
# 02_places_and_business_profile.md. Enterprise is where phone / website / rating / hours live; Nearby Search
# has no cheap tier at all (every field on it is Pro or above), which is why the list pass defaults to Pro and
# the expensive fields are bought one place at a time by place_details().
_PRO_FIELDS = ("places.id,places.displayName,places.formattedAddress,places.location,"
               "places.primaryTypeDisplayName,places.businessStatus,places.googleMapsUri")
_ENT_EXTRA = (",places.rating,places.userRatingCount,places.nationalPhoneNumber,places.websiteUri,"
              "places.currentOpeningHours.openNow")
# one place, bought on open: same names without the "places." prefix (Place Details is a single resource)
_DETAILS_FIELDS = ("id,displayName,formattedAddress,location,primaryTypeDisplayName,businessStatus,"
                   "googleMapsUri,rating,userRatingCount,nationalPhoneNumber,internationalPhoneNumber,"
                   "websiteUri,currentOpeningHours,regularOpeningHours")
# Nearby Search: circle only (no rectangle), radius <= 50 km, 20 results, NO paging. Documented ceilings.
NEARBY_MAX_RADIUS_M = 50000
NEARBY_MAX_RESULTS = 20
# computeRouteMatrix documented ceilings: 625 elements (origins x destinations); 100 for TRANSIT. Our own
# per-call limit (maps_matrix_max setting) sits below these because EVERY element is a billable event.
MATRIX_HARD_MAX = 625
MATRIX_HARD_MAX_TRANSIT = 100
# Google requires its attribution wherever this content is shown, with or without a map (ToS 3.2.2(b)).
ATTRIBUTION = "Google"
MAPS_PACKAGE = "com.google.android.apps.maps"
FRESH = timedelta(minutes=45)

MODES = {"drive": "DRIVE", "car": "DRIVE", "driving": "DRIVE", "bike": "TWO_WHEELER", "two_wheeler": "TWO_WHEELER",
         "scooter": "TWO_WHEELER", "walk": "WALK", "walking": "WALK", "transit": "TRANSIT", "bus": "TRANSIT",
         "train": "TRANSIT", "metro": "TRANSIT"}
LINK_MODE = {"DRIVE": "driving", "TWO_WHEELER": "two-wheeler", "WALK": "walking", "TRANSIT": "transit"}

_http: httpx.AsyncClient | None = None


class MapsError(Exception):
    pass


def _bill(tenant_id: str, sku: str, n: int = 1) -> "mapsbill.Receipt":
    """Charge the call BEFORE it goes out, so the cap can refuse pre-flight. A cap hit becomes a MapsError, so
    every existing `except MapsError` handler already shows her a sensible line instead of a surprise bill."""
    try:
        return mapsbill.charge(tenant_id or "_shared", sku, n)
    except mapsbill.MapsCapped as e:
        raise MapsError(str(e)) from e


def _unbill(receipt) -> None:
    """Google's billable event is a SUCCESSFUL request, so a call that came back 4xx/5xx costs her nothing.
    Without this, a key missing an API would answer 403 every time and still burn the whole daily cap and the
    month's free allowance."""
    try:
        mapsbill.refund(receipt)
    except Exception:           # a refund must never turn into the error she sees
        log.exception("maps refund failed")


def configured() -> bool:
    return bool(get_settings().google_maps_api_key.strip())


def _client() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(timeout=15)
    return _http


def set_client(c) -> None:  # tests
    global _http
    _http = c


def _key() -> str:
    k = get_settings().google_maps_api_key.strip()
    if not k:
        raise MapsError("Google Maps is not connected yet (GOOGLE_MAPS_API_KEY is not set on the server).")
    return k


def _explain(r: httpx.Response) -> str:
    try:
        msg = r.json().get("error", {}).get("message") or r.json().get("error_message") or r.text
    except Exception:
        msg = r.text
    if r.status_code == 403 or "not enabled" in msg.lower() or "has not been used" in msg.lower():
        return "This Maps API is not enabled in Google Cloud (Places API (New), Routes API, Geocoding API) or billing is off."
    if "API key not valid" in msg:
        return "The Google Maps API key is not valid."
    return f"Google Maps error {r.status_code}: {msg[:160]}"


# ---------------------------------------------------------------- user location
def save_location(tenant_id: str, lat: float, lng: float, accuracy_m: float | None = None) -> None:
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise MapsError("The location is not valid")
    with session() as s:
        row = s.get(UserLocation, tenant_id)
        if row is None:
            row = UserLocation(tenant_id=tenant_id, lat=lat, lng=lng)
            s.add(row)
        row.lat, row.lng, row.accuracy_m, row.at = lat, lng, accuracy_m, datetime.now(timezone.utc)


def where_am_i(tenant_id: str) -> dict | None:
    """Fresh phone GPS first, then the saved city from the profile."""
    with session() as s:
        row = s.get(UserLocation, tenant_id)
        if row is not None:
            at = row.at if row.at.tzinfo else row.at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - at < FRESH:
                return {"lat": row.lat, "lng": row.lng, "source": "phone", "name": "your location"}
        p = s.get(Profile, tenant_id)
        if p is not None and p.lat is not None and p.lon is not None:
            return {"lat": p.lat, "lng": p.lon, "source": "city", "name": p.city or "your city"}
        if row is not None:
            return {"lat": row.lat, "lng": row.lng, "source": "phone_old", "name": "your last location"}
    return None


_LATLNG = re.compile(r"^\s*(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\s*$")
HERE_WORDS = {"", "here", "me", "my location", "current location", "yahan", "yaha", "idhar", "mere paas", "ghar", "home",
              "abhi jahan hoon", "mai jahan hu", "near me", "my place"}


def _is_here(text: str | None) -> bool:
    return (text or "").strip().lower() in HERE_WORDS


# ---------------------------------------------------------------- links (no key needed)
def nav_link(destination: str | dict, origin: str | dict | None = None, mode: str = "DRIVE", navigate: bool = True) -> str:
    def fmt(x):
        return f"{x['lat']},{x['lng']}" if isinstance(x, dict) else str(x)
    q = {"api": "1", "destination": fmt(destination), "travelmode": LINK_MODE.get(mode, "driving")}
    if origin is not None:
        q["origin"] = fmt(origin)
    if navigate:
        q["dir_action"] = "navigate"
    return "https://www.google.com/maps/dir/?" + urlencode(q, quote_via=quote)


def search_link(query: str, near: dict | None = None) -> str:
    q = query + (f" near {near['lat']},{near['lng']}" if near else "")
    return "https://www.google.com/maps/search/?" + urlencode({"api": "1", "query": q}, quote_via=quote)


# ---------------------------------------------------------------- Places / Geocoding / Routes
def _km(a: dict, b: dict) -> float:
    r = 6371.0
    la1, la2 = math.radians(a["lat"]), math.radians(b["lat"])
    dla, dlo = la2 - la1, math.radians(b["lng"] - a["lng"])
    h = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


async def search_places(query: str, near: dict | None = None, open_now: bool = False, limit: int = 6,
                        radius_m: int = 5000, language: str = "en", tenant_id: str = "",
                        tier: str = "enterprise") -> list[dict]:
    """Text Search. `tier` picks the SKU: "pro" = name / address / location / type (no phone, rating or hours),
    "enterprise" = those too. v0.449 bills the call and keeps the two things the licence permits."""
    body: dict = {"textQuery": query, "languageCode": language, "regionCode": "IN", "pageSize": max(1, min(limit, 10))}
    if near:
        body["locationBias"] = {"circle": {"center": {"latitude": near["lat"], "longitude": near["lng"]},
                                           "radius": float(max(200, min(radius_m, 50000)))}}
    if open_now:
        body["openNow"] = True
    ent = str(tier or "enterprise").lower() != "pro"
    fields = _PRO_FIELDS + (_ENT_EXTRA if ent else "")
    sku = mapsbill.SKU_TEXT_ENT if ent else mapsbill.SKU_TEXT_PRO
    rc = _bill(tenant_id, sku)
    r = await _client().post(PLACES_URL, json=body, headers={"X-Goog-Api-Key": _key(), "X-Goog-FieldMask": fields})
    if r.status_code >= 400:
        _unbill(rc)
        raise MapsError(_explain(r))
    out = []
    for p in r.json().get("places", []):
        loc = p.get("location") or {}
        item = {"name": (p.get("displayName") or {}).get("text", ""), "address": p.get("formattedAddress", ""),
                "lat": loc.get("latitude"), "lng": loc.get("longitude"), "rating": p.get("rating"),
                "reviews": p.get("userRatingCount"), "type": (p.get("primaryTypeDisplayName") or {}).get("text", ""),
                "open_now": (p.get("currentOpeningHours") or {}).get("openNow"), "phone": p.get("nationalPhoneNumber", ""),
                "maps_link": p.get("googleMapsUri", "")}
        item["place_id"] = p.get("id", "")
        if near and item["lat"] is not None:
            item["distance_km"] = round(_km(near, {"lat": item["lat"], "lng": item["lng"]}), 1)
        if get_settings().maps_cache:
            mapsbill.remember(item["place_id"], item["lat"], item["lng"], query)
        out.append(item)
    return out


async def geocode(address: str, near: dict | None = None, tenant_id: str = "") -> dict | None:
    """Address or place name -> {lat, lng, name, address}. Uses Places text search (handles 'Akola station')."""
    m = _LATLNG.match(address or "")
    if m:
        return {"lat": float(m.group(1)), "lng": float(m.group(2)), "name": address, "address": address}
    try:
        hits = await search_places(address, near=near, limit=1, radius_m=30000, tenant_id=tenant_id, tier="pro")
    except MapsError:
        hits = []
    if hits and hits[0]["lat"] is not None:
        h = hits[0]
        return {"lat": h["lat"], "lng": h["lng"], "name": h["name"] or address, "address": h["address"]}
    rc = _bill(tenant_id, mapsbill.SKU_GEOCODE)
    r = await _client().get(GEOCODE_URL, params={"address": address, "region": "in", "key": _key()})
    if r.status_code >= 400:
        _unbill(rc)
        raise MapsError(_explain(r))
    data = r.json()
    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        raise MapsError(f"Google Maps: {data.get('status')} {data.get('error_message', '')}"[:200])
    res = data.get("results") or []
    if not res:
        return None
    g = res[0]
    loc = g["geometry"]["location"]
    return {"lat": loc["lat"], "lng": loc["lng"], "name": address, "address": g.get("formatted_address", "")}


def _secs(v: str | None) -> int:
    try:
        return int(float(str(v or "0").rstrip("s")))
    except ValueError:
        return 0


def _human(secs: int) -> str:
    h, m = divmod(max(0, secs) // 60, 60)
    return f"{h} h {m} min" if h else f"{m} min"


async def route(origin: dict, destination: dict, mode: str = "DRIVE", language: str = "en-IN",
                tenant_id: str = "") -> dict:
    def wp(x):
        return {"location": {"latLng": {"latitude": x["lat"], "longitude": x["lng"]}}}
    body: dict = {"origin": wp(origin), "destination": wp(destination), "travelMode": mode, "languageCode": language,
                  "units": "METRIC", "computeAlternativeRoutes": False}
    if mode in ("DRIVE", "TWO_WHEELER"):
        body["routingPreference"] = "TRAFFIC_AWARE"
    fields = ("routes.duration,routes.staticDuration,routes.distanceMeters,routes.description,routes.warnings,"
              "routes.legs.steps.navigationInstruction,routes.legs.steps.distanceMeters")
    rc = _bill(tenant_id, mapsbill.SKU_ROUTES)
    r = await _client().post(ROUTES_URL, json=body, headers={"X-Goog-Api-Key": _key(), "X-Goog-FieldMask": fields})
    if r.status_code >= 400:
        _unbill(rc)
        if mode == "TWO_WHEELER":  # not offered on every road; fall back to car
            return await route(origin, destination, "DRIVE", language, tenant_id)
        raise MapsError(_explain(r))
    routes = r.json().get("routes") or []
    if not routes:
        raise MapsError("No route found to this place.")
    rt = routes[0]
    secs, free = _secs(rt.get("duration")), _secs(rt.get("staticDuration"))
    steps = []
    for leg in rt.get("legs", []):
        for st in leg.get("steps", []):
            ins = (st.get("navigationInstruction") or {}).get("instructions")
            if ins:
                steps.append(ins)
    traffic = ""
    if free and secs > free * 1.25 and secs - free > 300:
        traffic = f"There is traffic: {_human(secs - free)} more than a normal day"
    return {"distance_km": round((rt.get("distanceMeters") or 0) / 1000, 1), "duration": _human(secs),
            "duration_min": round(secs / 60), "traffic": traffic, "via": rt.get("description", ""), "mode": mode,
            "first_steps": steps[:6], "warnings": rt.get("warnings", [])}


# ---------------------------------------------------------------- v0.463 Phase 4: SABSE PAAS
async def matrix(origins: list[dict], destinations: list[dict], mode: str = "DRIVE", language: str = "en-IN",
                 tenant_id: str = "") -> list[list[dict]]:
    """Routes computeRouteMatrix: real road distance + time from every origin to every destination.

    Returns rows[origin][destination] = {"ok": True, "distance_km", "duration_min", "duration"} or
    {"ok": False, "reason"} - an element Google could not route is REPORTED as unreachable, never filled in
    with a straight-line guess (a wrong ETA looks exactly as confident as a right one).

    Billing: this is the one SKU Google charges PER ELEMENT (origins x destinations), so a 10x10 matrix is 100
    events and is charged as 100 BEFORE the call - the cap refuses it rather than discovering the bill after.
    """
    if not origins or not destinations:
        raise MapsError("A matrix needs at least one origin and one destination.")
    n = len(origins) * len(destinations)
    ceiling = MATRIX_HARD_MAX_TRANSIT if mode == "TRANSIT" else MATRIX_HARD_MAX
    mine = max(1, int(get_settings().maps_matrix_max or 100))
    if n > min(ceiling, mine):
        raise MapsError(f"{len(origins)} x {len(destinations)} = {n} pairs; at most {min(ceiling, mine)} at a time "
                        f"(each pair is charged separately). Give fewer places.")

    def wp(x):
        return {"waypoint": {"location": {"latLng": {"latitude": x["lat"], "longitude": x["lng"]}}}}
    body: dict = {"origins": [wp(o) for o in origins], "destinations": [wp(d) for d in destinations],
                  "travelMode": mode, "languageCode": language, "units": "METRIC"}
    if mode in ("DRIVE", "TWO_WHEELER"):
        body["routingPreference"] = "TRAFFIC_AWARE"
    fields = "originIndex,destinationIndex,status,condition,distanceMeters,duration"
    rc = _bill(tenant_id, mapsbill.SKU_MATRIX, n)
    r = await _client().post(MATRIX_URL, json=body, headers={"X-Goog-Api-Key": _key(), "X-Goog-FieldMask": fields})
    if r.status_code >= 400:
        _unbill(rc)
        if mode == "TWO_WHEELER":                     # not offered everywhere; fall back to car, as route() does
            return await matrix(origins, destinations, "DRIVE", language, tenant_id)
        raise MapsError(_explain(r))
    try:
        data = r.json()
    except ValueError:
        _unbill(rc)
        raise MapsError("Could not read the answer from Google Maps.")
    if isinstance(data, dict):
        data = [data]
    rows: list[list[dict]] = [[{"ok": False, "reason": "Google did not answer for this pair"}
                               for _ in destinations] for _ in origins]
    for el in data:
        try:
            i, j = int(el.get("originIndex", 0)), int(el.get("destinationIndex", 0))
        except (TypeError, ValueError):
            continue
        if not (0 <= i < len(origins) and 0 <= j < len(destinations)):
            continue
        st = el.get("status") or {}
        if (st.get("code") or 0) != 0 or el.get("condition") not in (None, "ROUTE_EXISTS"):
            rows[i][j] = {"ok": False, "reason": "No route found to this place"}
            continue
        secs = _secs(el.get("duration"))
        rows[i][j] = {"ok": True, "distance_km": round((el.get("distanceMeters") or 0) / 1000, 1),
                      "duration_min": round(secs / 60), "duration": _human(secs)}
    return rows


# ---------------------------------------------------------------- v0.466 Phase 7: KAAGAZ PAR (links, not pictures)
SOLAR_URL = "https://solar.googleapis.com/v1/buildingInsights:findClosest"       # v0.469 Phase 10
SNAP_URL = "https://roads.googleapis.com/v1/snapToRoads"
SNAP_MAX_POINTS = 100                          # Roads API's documented per-request ceiling
STREETVIEW_META_URL = "https://maps.googleapis.com/maps/api/streetview/metadata"


def view_link(lat: float, lng: float, place_id: str = "", name: str = "") -> str:
    """Opens the place on Google's own map (Maps URLs). No key, no fee, nothing of Google's stored."""
    q = {"api": "1", "query": (name or f"{lat},{lng}")}
    if place_id:
        q["query_place_id"] = place_id
    return "https://www.google.com/maps/search/?" + urlencode(q, quote_via=quote)


def streetview_link(lat: float, lng: float, pano_id: str = "") -> str:
    q = {"api": "1", "map_action": "pano", "viewpoint": f"{lat},{lng}"}
    if pano_id:
        q["pano"] = pano_id
    return "https://www.google.com/maps/@?" + urlencode(q, quote_via=quote)


async def streetview_check(lat: float, lng: float, tenant_id: str = "") -> dict:
    """Is there a Street View panorama here? The metadata call is a FREE SKU (charged as 0 through the same path
    so it still shows up in usage). Nothing is stored; pano_id is the only thing the terms let anyone cache."""
    rc = _bill(tenant_id, mapsbill.SKU_STREETVIEW_META)
    r = await _client().get(STREETVIEW_META_URL, params={"location": f"{float(lat)},{float(lng)}", "key": _key()})
    if r.status_code >= 400:
        _unbill(rc)
        raise MapsError(_explain(r))
    d = r.json() or {}
    st = d.get("status", "")
    if st not in ("OK", "ZERO_RESULTS", "NOT_FOUND"):
        _unbill(rc)
        raise MapsError(f"Google Maps: {st} {d.get('error_message', '')}"[:200])
    return {"available": st == "OK", "pano_id": d.get("pano_id", "") if st == "OK" else "",
            "date": d.get("date", "") if st == "OK" else ""}


# ---------------------------------------------------------------- v0.469 Phase 10: BAAKI SAB (solar + roads)
def _pick_configs(configs: list[dict], max_panels: int) -> list[dict]:
    """A few arrangements from Google's own list (ordered by panel count): about 25 / 50 / 100 % of the maximum.
    Google's DC energy numbers are passed through untouched - nothing here is a financial guess."""
    out, seen = [], set()
    for frac in (0.25, 0.5, 1.0):
        target = max(1, round(max_panels * frac))
        c = min(configs, key=lambda x: abs(int(x.get("panelsCount") or 0) - target), default=None)
        if c and c.get("panelsCount") not in seen:
            seen.add(c.get("panelsCount"))
            out.append({"panels": int(c.get("panelsCount") or 0), "yearly_dc_kwh": round(float(c.get("yearlyEnergyDcKwh") or 0))})
    return out


async def solar_building(lat: float, lng: float, tenant_id: str = "") -> dict:
    """Solar API Building Insights for the building nearest a point: roof size, how many panels fit, sunshine, and what
    a few layouts would generate. Permitted use is feasibility / design / a requested proposal for an address (SST 20.1);
    nothing is stored. Coverage is not universal: a place Google has no imagery for answers NOT_FOUND and is reported
    as 'not covered', never filled in. Billed per successful request."""
    if not (-90 <= float(lat) <= 90 and -180 <= float(lng) <= 180):
        raise MapsError("The location is not valid")
    rc = _bill(tenant_id, mapsbill.SKU_SOLAR)
    r = await _client().get(SOLAR_URL, params={"location.latitude": float(lat), "location.longitude": float(lng),
                                               "requiredQuality": "BASE"}, headers={"X-Goog-Api-Key": _key()})
    if r.status_code == 404:                       # no building / imagery here: not a successful result, not billed
        _unbill(rc)
        return {"covered": False}
    if r.status_code >= 400:
        _unbill(rc)
        raise MapsError(_explain(r))
    d = r.json() or {}
    sp = d.get("solarPotential") or {}
    whole = sp.get("wholeRoofStats") or {}
    mx = int(sp.get("maxArrayPanelsCount") or 0)
    im = d.get("imageryDate") or {}
    return {"covered": True, "quality": d.get("imageryQuality", ""),
            "imagery_date": "-".join(str(im.get(k)) for k in ("year", "month", "day") if im.get(k)),
            "roof_area_m2": round(float(whole.get("areaMeters2") or 0), 1),
            "max_panels": mx, "max_array_area_m2": round(float(sp.get("maxArrayAreaMeters2") or 0), 1),
            "panel_watts": sp.get("panelCapacityWatts"), "sunshine_hours_per_year": sp.get("maxSunshineHoursPerYear"),
            "layouts": _pick_configs(sp.get("solarPanelConfigs") or [], mx) if mx else [],
            "attribution": ATTRIBUTION}


async def snap_to_roads(points: list[dict], mode: str = "DRIVING", interpolate: bool = False,
                        tenant_id: str = "") -> dict:
    """Roads API snapToRoads: a GPS trail -> the road it was on. At most 100 points a request. Billed per request.
    The snapped lat/lng are returned live and not kept (Roads allows lat/lng for 30 days, nothing else)."""
    if not points:
        raise MapsError("At least one point is needed.")
    if len(points) > SNAP_MAX_POINTS:
        raise MapsError(f"At most {SNAP_MAX_POINTS} points at a time; there are {len(points)}. Split them into parts.")
    for p in points:
        if not (-90 <= p["lat"] <= 90 and -180 <= p["lng"] <= 180):
            raise MapsError("A point is not valid (lat/lng).")
    mode = mode if mode in ("DRIVING", "WALKING", "CYCLING") else "DRIVING"
    path = "|".join(f"{p['lat']},{p['lng']}" for p in points)
    rc = _bill(tenant_id, mapsbill.SKU_ROADS)
    r = await _client().get(SNAP_URL, params={"path": path, "travelMode": mode, "interpolate": str(bool(interpolate)).lower()},
                            headers={"X-Goog-Api-Key": _key()})
    if r.status_code >= 400:
        _unbill(rc)
        raise MapsError(_explain(r))
    d = r.json() or {}
    sp = d.get("snappedPoints") or []
    snapped = [{"lat": (x.get("location") or {}).get("latitude"), "lng": (x.get("location") or {}).get("longitude"),
                "original_index": x.get("originalIndex")} for x in sp]
    km = sum(_km({"lat": a["lat"], "lng": a["lng"]}, {"lat": b["lat"], "lng": b["lng"]})
             for a, b in zip(snapped, snapped[1:]) if None not in (a["lat"], a["lng"], b["lat"], b["lng"]))
    kept = {x["original_index"] for x in snapped if x["original_index"] is not None}
    return {"snapped": snapped, "snapped_km": round(km, 2),
            "not_snapped": [i for i in range(len(points)) if i not in kept],
            "warning": d.get("warningMessage", ""), "attribution": ATTRIBUTION}


# ---------------------------------------------------------------- v0.464 Phase 6: PATA PAKKA
_FINE = ("PREMISE", "SUB_PREMISE")                 # the house / flat itself was matched
_ROAD = ("ROUTE", "BLOCK", "PREMISE_PROXIMITY")    # only as far as the street / block / near the building


def grade_address(verdict: dict, address: dict) -> tuple[str, list[str]]:
    """Plain verdict from Google's own flags, in code. Three grades, because Indian addresses ("Ram Mandir ke
    paas, Tilak Road") very often validate only to the road - that is NOT a wrong address and must not be
    called one:  pakka (house matched) | sadak_tak (matched to the road / block only) | galat (something in it
    is unconfirmed, missing or was replaced).  Returns (grade, reasons in Hinglish)."""
    v, a = verdict or {}, address or {}
    why: list[str] = []
    bad = False
    if v.get("hasUnconfirmedComponents") or a.get("unconfirmedComponentTypes"):
        bad = True
        why.append("Some parts could not be confirmed: " + ", ".join(a.get("unconfirmedComponentTypes") or ["a part of the address"]))
    if a.get("missingComponentTypes"):
        bad = True
        why.append("The address is missing: " + ", ".join(a["missingComponentTypes"]))
    if a.get("unresolvedTokens"):
        bad = True
        why.append("These words were not understood: " + ", ".join(a["unresolvedTokens"]))
    if not v.get("addressComplete") and not bad:
        bad = True
        why.append("The address does not look complete.")
    for c in a.get("addressComponents") or []:
        nm = (c.get("componentName") or {}).get("text", "")
        t = c.get("componentType", "")
        if c.get("replaced"):
            bad = True
            why.append(f"{t} was replaced (now: {nm}) - what was written was wrong")
        elif c.get("confirmationLevel") == "UNCONFIRMED_AND_SUSPICIOUS":
            bad = True
            why.append(f"{t} '{nm}' looks doubtful")
        if c.get("spellCorrected"):
            why.append(f"{t} spelling corrected: {nm}")
        if c.get("inferred"):
            why.append(f"{t} added automatically: {nm}")
    if bad:
        return "galat", why
    if v.get("validationGranularity") in _FINE:
        return "pakka", why
    if v.get("validationGranularity") in _ROAD:
        why.append("Confirmed only up to the road / block, not the house number - confirm a landmark or phone number before delivery.")
        return "sadak_tak", why
    why.append("Google could not be that sure.")
    return "sadak_tak", why


async def validate_address(address: str, pin: str = "", city: str = "", state: str = "",
                           tenant_id: str = "") -> dict:
    """Address Validation API for an Indian address. Billed per request (assumed Enterprise tier - the dearest -
    until her bill says otherwise), refused first by the cap, refunded if the call fails.

    NOTHING is stored: this is a customer's address and Google content. Only the live answer is returned."""
    text = re.sub(r"\s+", " ", str(address or "")).strip()
    if not text:
        raise MapsError("An address is needed.")
    body_addr: dict = {"regionCode": "IN", "addressLines": [text]}
    if pin:
        body_addr["postalCode"] = re.sub(r"\D", "", str(pin))[:6]
    if city:
        body_addr["locality"] = str(city).strip()
    if state:
        body_addr["administrativeArea"] = str(state).strip()
    if sum(len(str(x)) for x in body_addr.values() if not isinstance(x, list)) + len(text) > 280:
        raise MapsError("The address is too long (up to 280 characters).")
    rc = _bill(tenant_id, mapsbill.SKU_ADDRESS_ENT)
    r = await _client().post(VALIDATE_URL, json={"address": body_addr},
                             headers={"X-Goog-Api-Key": _key()})
    if r.status_code >= 400:
        _unbill(rc)
        raise MapsError(_explain(r))
    res = (r.json() or {}).get("result") or {}
    verdict, addr, geo = res.get("verdict") or {}, res.get("address") or {}, res.get("geocode") or {}
    grade, why = grade_address(verdict, addr)
    loc = geo.get("location") or {}
    flagged = [{"type": c.get("componentType"), "text": (c.get("componentName") or {}).get("text", ""),
                "confirmation": c.get("confirmationLevel", "").replace("CONFIRMATION_LEVEL_", "").lower(),
                **{k: True for k in ("replaced", "spellCorrected", "inferred", "unexpected") if c.get(k)}}
               for c in addr.get("addressComponents") or []]
    return {"grade": grade, "reasons": why, "corrected": addr.get("formattedAddress", ""),
            "granularity": verdict.get("validationGranularity", ""),
            "geocode_granularity": verdict.get("geocodeGranularity", ""),
            "lat": loc.get("latitude"), "lng": loc.get("longitude"), "place_id": geo.get("placeId", ""),
            "components": flagged, "business": (res.get("metadata") or {}).get("business"),
            "residential": (res.get("metadata") or {}).get("residential"),
            "next_action": verdict.get("possibleNextAction", ""), "attribution": ATTRIBUTION}


async def reverse_geocode(lat: float, lng: float, tenant_id: str = "") -> dict | None:
    """A point -> the address Google gives it (Geocoding API, latlng). Live only, never stored."""
    if not (-90 <= float(lat) <= 90 and -180 <= float(lng) <= 180):
        raise MapsError("The location is not valid")
    rc = _bill(tenant_id, mapsbill.SKU_GEOCODE)
    r = await _client().get(GEOCODE_URL, params={"latlng": f"{float(lat)},{float(lng)}", "region": "in",
                                                 "language": "en", "key": _key()})
    if r.status_code >= 400:
        _unbill(rc)
        raise MapsError(_explain(r))
    data = r.json()
    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        _unbill(rc)
        raise MapsError(f"Google Maps: {data.get('status')} {data.get('error_message', '')}"[:200])
    res = data.get("results") or []
    if not res:
        return None
    g = res[0]
    return {"address": g.get("formatted_address", ""), "place_id": g.get("place_id", ""),
            "types": g.get("types", []), "attribution": ATTRIBUTION}


# ---------------------------------------------------------------- v0.449 Phase 3: nearby + details
def _place_row(p: dict, near: dict | None = None) -> dict:
    loc = p.get("location") or {}
    hours = p.get("currentOpeningHours") or {}
    item = {"place_id": p.get("id", ""), "name": (p.get("displayName") or {}).get("text", ""),
            "address": p.get("formattedAddress", ""), "lat": loc.get("latitude"), "lng": loc.get("longitude"),
            "type": (p.get("primaryTypeDisplayName") or {}).get("text", ""),
            "status": p.get("businessStatus", ""), "maps_link": p.get("googleMapsUri", ""),
            "rating": p.get("rating"), "reviews": p.get("userRatingCount"),
            "phone": p.get("nationalPhoneNumber", "") or p.get("internationalPhoneNumber", ""),
            "website": p.get("websiteUri", ""), "open_now": hours.get("openNow")}
    if near and item["lat"] is not None:
        item["distance_km"] = round(_km(near, {"lat": item["lat"], "lng": item["lng"]}), 1)
    return {k: v for k, v in item.items() if v not in ("", None)}


async def nearby(center: dict, kinds: list[str] | None = None, radius_m: int = 2000, limit: int = 12,
                 rank: str = "distance", language: str = "en", tenant_id: str = "",
                 tier: str = "") -> list[dict]:
    """Places Nearby Search: what is around a point, by category.

    Documented ceilings, enforced here rather than discovered in production: the area is a CIRCLE ONLY (there
    is no rectangle on Nearby Search), the radius cannot exceed 50 km, at most 20 results come back, and there
    is NO paging - 20 is the hard ceiling for one request, so a wider sweep means tiling circles.

    `kinds` are Table A place types (`pharmacy`, `hardware_store`, `doctor`, `bank`...), at most 50.
    `tier` defaults to the maps_nearby_tier setting: "pro" leaves out phone / website / rating / hours, which
    are Enterprise-priced and are meant to be bought one place at a time by place_details() on open.
    """
    if not center or center.get("lat") is None:
        raise MapsError("A nearby search needs a point (lat/lng).")
    radius = float(max(1, min(int(radius_m or 2000), NEARBY_MAX_RADIUS_M)))
    body: dict = {"languageCode": language, "regionCode": "IN",
                  "maxResultCount": max(1, min(int(limit or 12), NEARBY_MAX_RESULTS)),
                  "rankPreference": "DISTANCE" if str(rank or "distance").lower().startswith("dist") else "POPULARITY",
                  "locationRestriction": {"circle": {
                      "center": {"latitude": center["lat"], "longitude": center["lng"]}, "radius": radius}}}
    if kinds:
        body["includedTypes"] = [str(k).strip() for k in kinds if str(k).strip()][:50]
    ent = str(tier or get_settings().maps_nearby_tier or "pro").lower() != "pro"
    fields = _PRO_FIELDS + (_ENT_EXTRA if ent else "")
    sku = mapsbill.SKU_NEARBY_ENT if ent else mapsbill.SKU_NEARBY_PRO
    rc = _bill(tenant_id, sku)
    r = await _client().post(NEARBY_URL, json=body, headers={"X-Goog-Api-Key": _key(), "X-Goog-FieldMask": fields})
    if r.status_code >= 400:
        _unbill(rc)
        raise MapsError(_explain(r))
    out = []
    for p in r.json().get("places", []):
        item = _place_row(p, near=center)
        if get_settings().maps_cache:
            mapsbill.remember(item.get("place_id", ""), item.get("lat"), item.get("lng"),
                              ",".join(kinds or [])[:300])
        out.append(item)
    return out


async def place_details(place_id: str, language: str = "en", tenant_id: str = "") -> dict:
    """One place, bought on open: phone, website, rating, hours. This is the Enterprise half of the
    cheap-list / details-on-open split - the fields are deliberately NOT fetched for a whole result page.

    Nothing from this answer is written down except the place_id and the lat/lng (see mapsbill): the terms
    permit caching those two and nothing else, so the card is re-fetched each time it is opened.
    """
    pid = str(place_id or "").strip()
    if not pid:
        raise MapsError("place_id is needed.")
    rc = _bill(tenant_id, mapsbill.SKU_DETAILS_ENT)
    r = await _client().get(DETAILS_URL + quote(pid, safe=""),
                            params={"languageCode": language},
                            headers={"X-Goog-Api-Key": _key(), "X-Goog-FieldMask": _DETAILS_FIELDS})
    if r.status_code >= 400:
        _unbill(rc)
        raise MapsError(_explain(r))
    row = _place_row(r.json())
    hrs = (r.json().get("regularOpeningHours") or {}).get("weekdayDescriptions") or []
    if hrs:
        row["hours"] = hrs[:7]
    if get_settings().maps_cache:
        mapsbill.remember(row.get("place_id", pid), row.get("lat"), row.get("lng"))
    row["attribution"] = ATTRIBUTION
    return row


async def resolve(text: str | None, tenant_id: str, near: dict | None = None) -> dict | None:
    """'here' -> phone location; 'lat,lng' -> point; a name -> geocoded point (biased to the user's area)."""
    if _is_here(text):
        return where_am_i(tenant_id)
    return await geocode(str(text), near=near, tenant_id=tenant_id)
