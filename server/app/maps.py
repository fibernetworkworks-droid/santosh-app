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

from .config import get_settings
from .db import Profile, UserLocation, session

log = logging.getLogger("santosh.maps")

PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
MAPS_PACKAGE = "com.google.android.apps.maps"
FRESH = timedelta(minutes=45)

MODES = {"drive": "DRIVE", "car": "DRIVE", "driving": "DRIVE", "bike": "TWO_WHEELER", "two_wheeler": "TWO_WHEELER",
         "scooter": "TWO_WHEELER", "walk": "WALK", "walking": "WALK", "transit": "TRANSIT", "bus": "TRANSIT",
         "train": "TRANSIT", "metro": "TRANSIT"}
LINK_MODE = {"DRIVE": "driving", "TWO_WHEELER": "two-wheeler", "WALK": "walking", "TRANSIT": "transit"}

_http: httpx.AsyncClient | None = None


class MapsError(Exception):
    pass


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
        raise MapsError("Google Maps abhi connect nahi hai (server par GOOGLE_MAPS_API_KEY set nahi hai).")
    return k


def _explain(r: httpx.Response) -> str:
    try:
        msg = r.json().get("error", {}).get("message") or r.json().get("error_message") or r.text
    except Exception:
        msg = r.text
    if r.status_code == 403 or "not enabled" in msg.lower() or "has not been used" in msg.lower():
        return "Google Cloud mein yeh Maps API enable nahi hai (Places API (New), Routes API, Geocoding API) ya billing band hai."
    if "API key not valid" in msg:
        return "Google Maps API key sahi nahi hai."
    return f"Google Maps error {r.status_code}: {msg[:160]}"


# ---------------------------------------------------------------- user location
def save_location(tenant_id: str, lat: float, lng: float, accuracy_m: float | None = None) -> None:
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise MapsError("Location sahi nahi hai")
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
                return {"lat": row.lat, "lng": row.lng, "source": "phone", "name": "aapki location"}
        p = s.get(Profile, tenant_id)
        if p is not None and p.lat is not None and p.lon is not None:
            return {"lat": p.lat, "lng": p.lon, "source": "city", "name": p.city or "aapka shehar"}
        if row is not None:
            return {"lat": row.lat, "lng": row.lng, "source": "phone_old", "name": "aapki aakhri location"}
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
                        radius_m: int = 5000, language: str = "en") -> list[dict]:
    body: dict = {"textQuery": query, "languageCode": language, "regionCode": "IN", "pageSize": max(1, min(limit, 10))}
    if near:
        body["locationBias"] = {"circle": {"center": {"latitude": near["lat"], "longitude": near["lng"]},
                                           "radius": float(max(200, min(radius_m, 50000)))}}
    if open_now:
        body["openNow"] = True
    fields = ("places.id,places.displayName,places.formattedAddress,places.location,places.rating,"
              "places.userRatingCount,places.currentOpeningHours.openNow,places.nationalPhoneNumber,"
              "places.googleMapsUri,places.primaryTypeDisplayName,places.priceLevel")
    r = await _client().post(PLACES_URL, json=body, headers={"X-Goog-Api-Key": _key(), "X-Goog-FieldMask": fields})
    if r.status_code >= 400:
        raise MapsError(_explain(r))
    out = []
    for p in r.json().get("places", []):
        loc = p.get("location") or {}
        item = {"name": (p.get("displayName") or {}).get("text", ""), "address": p.get("formattedAddress", ""),
                "lat": loc.get("latitude"), "lng": loc.get("longitude"), "rating": p.get("rating"),
                "reviews": p.get("userRatingCount"), "type": (p.get("primaryTypeDisplayName") or {}).get("text", ""),
                "open_now": (p.get("currentOpeningHours") or {}).get("openNow"), "phone": p.get("nationalPhoneNumber", ""),
                "maps_link": p.get("googleMapsUri", "")}
        if near and item["lat"] is not None:
            item["distance_km"] = round(_km(near, {"lat": item["lat"], "lng": item["lng"]}), 1)
        out.append(item)
    return out


async def geocode(address: str, near: dict | None = None) -> dict | None:
    """Address or place name -> {lat, lng, name, address}. Uses Places text search (handles 'Akola station')."""
    m = _LATLNG.match(address or "")
    if m:
        return {"lat": float(m.group(1)), "lng": float(m.group(2)), "name": address, "address": address}
    try:
        hits = await search_places(address, near=near, limit=1, radius_m=30000)
    except MapsError:
        hits = []
    if hits and hits[0]["lat"] is not None:
        h = hits[0]
        return {"lat": h["lat"], "lng": h["lng"], "name": h["name"] or address, "address": h["address"]}
    r = await _client().get(GEOCODE_URL, params={"address": address, "region": "in", "key": _key()})
    if r.status_code >= 400:
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
    return f"{h} ghante {m} min" if h else f"{m} min"


async def route(origin: dict, destination: dict, mode: str = "DRIVE", language: str = "en-IN") -> dict:
    def wp(x):
        return {"location": {"latLng": {"latitude": x["lat"], "longitude": x["lng"]}}}
    body: dict = {"origin": wp(origin), "destination": wp(destination), "travelMode": mode, "languageCode": language,
                  "units": "METRIC", "computeAlternativeRoutes": False}
    if mode in ("DRIVE", "TWO_WHEELER"):
        body["routingPreference"] = "TRAFFIC_AWARE"
    fields = ("routes.duration,routes.staticDuration,routes.distanceMeters,routes.description,routes.warnings,"
              "routes.legs.steps.navigationInstruction,routes.legs.steps.distanceMeters")
    r = await _client().post(ROUTES_URL, json=body, headers={"X-Goog-Api-Key": _key(), "X-Goog-FieldMask": fields})
    if r.status_code >= 400:
        if mode == "TWO_WHEELER":  # not offered on every road; fall back to car
            return await route(origin, destination, "DRIVE", language)
        raise MapsError(_explain(r))
    routes = r.json().get("routes") or []
    if not routes:
        raise MapsError("Is jagah tak rasta nahi mila.")
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
        traffic = f"Traffic hai: aam din se {_human(secs - free)} zyada"
    return {"distance_km": round((rt.get("distanceMeters") or 0) / 1000, 1), "duration": _human(secs),
            "duration_min": round(secs / 60), "traffic": traffic, "via": rt.get("description", ""), "mode": mode,
            "first_steps": steps[:6], "warnings": rt.get("warnings", [])}


async def resolve(text: str | None, tenant_id: str, near: dict | None = None) -> dict | None:
    """'here' -> phone location; 'lat,lng' -> point; a name -> geocoded point (biased to the user's area)."""
    if _is_here(text):
        return where_am_i(tenant_id)
    return await geocode(str(text), near=near)
