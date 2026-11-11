"""Google Maps Phase 5 DIN KA RASTA: Route Optimization - the day's stop ORDER for one or more vehicles.

Source of every field here: Google's own proto (github.com/googleapis/googleapis, google/maps/routeoptimization/v1/
route_optimization_service.proto) - the prose docs were unreachable. From it:
  * POST https://routeoptimization.googleapis.com/v1/{parent=projects/*}:optimizeTours  (body = the request, JSON)
  * the service declares ONE auth scope, https://www.googleapis.com/auth/cloud-platform  -> OAuth from a service
    account, NOT the Maps API key; and the parent is a Google Cloud PROJECT id. So this needs two settings the Maps
    key never needed (route_opt_project, route_opt_sa_file) and says so when they are missing.
  * JSON mapping: durations "300s", timestamps RFC 3339, int64 as a string, LatLng {latitude, longitude}.

What it does NOT do: assign anything. The answer is a PROPOSED order; a person taps before it drives anything.
Never invents an order - a shipment the solver skipped is reported with Google's own reason code.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import maps, mapsbill
from .config import get_settings

log = logging.getLogger("santosh.mapsopt")

URL = "https://routeoptimization.googleapis.com/v1/projects/{project}:optimizeTours"
SCOPE = "https://www.googleapis.com/auth/cloud-platform"
MAX_VEHICLES = 5
LOAD_KEY = "units"

# Google's SkippedShipment.Reason.Code, in her words. Unknown codes are passed through, not hidden.
REASONS = {
    "NO_VEHICLE": "no vehicle was given at all",
    "DEMAND_EXCEEDS_VEHICLE_CAPACITY": "the load is more than the vehicle's capacity",
    "CANNOT_BE_PERFORMED_WITHIN_VEHICLE_DISTANCE_LIMIT": "it does not fit within the vehicle's distance limit",
    "CANNOT_BE_PERFORMED_WITHIN_VEHICLE_DURATION_LIMIT": "it does not fit within the vehicle's working time",
    "CANNOT_BE_PERFORMED_WITHIN_VEHICLE_TRAVEL_DURATION_LIMIT": "it does not fit within the vehicle's driving time",
    "CANNOT_BE_PERFORMED_WITHIN_VEHICLE_TIME_WINDOWS": "its time window does not match the vehicle's",
    "VEHICLE_NOT_ALLOWED": "this vehicle is not allowed for this stop",
    "VEHICLE_IGNORED": "vehicle left out",
    "SHIPMENT_IGNORED": "stop left out",
}

_lock = threading.Lock()
_creds = None


class OptError(maps.MapsError):
    pass


def configured() -> bool:
    s = get_settings()
    return bool(s.route_opt_project.strip() and s.route_opt_sa_file.strip())


def reset() -> None:      # tests / config change
    global _creds
    with _lock:
        _creds = None


def _token() -> str:
    """OAuth access token from the service-account file (cached, refreshed near expiry). Blocking: call in a thread."""
    global _creds
    s = get_settings()
    if not configured():
        raise OptError("The day's route plan needs a Google Cloud project and a service-account file "
                       "(ROUTE_OPT_PROJECT and ROUTE_OPT_SA_FILE on the server). The Maps API key does not work for this.")
    with _lock:
        if _creds is None:
            from google.oauth2 import service_account
            try:
                with open(s.route_opt_sa_file, encoding="utf-8") as f:
                    info = json.load(f)
                _creds = service_account.Credentials.from_service_account_info(info, scopes=[SCOPE])
            except (OSError, ValueError, KeyError) as e:
                raise OptError(f"Could not read the service-account file: {type(e).__name__}") from e
        if not _creds.valid or (_creds.expiry and (_creds.expiry.timestamp() - time.time()) < 120):
            import google.auth.transport.requests
            try:
                _creds.refresh(google.auth.transport.requests.Request())
            except Exception as e:                                  # network / bad key: say so, never leak the key
                raise OptError(f"Could not get a token from Google ({type(e).__name__}).") from e
        return _creds.token


# ---------------------------------------------------------------- pure: request in, plan out
def _hm(text: str) -> tuple[int, int]:
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", str(text or ""))
    if not m or int(m.group(1)) > 24 or int(m.group(2)) > 59:
        raise OptError(f"Could not understand the time '{text}' (HH:MM is needed, for example 10:30).")
    return int(m.group(1)), int(m.group(2))


def _at(day: date, hm: str, tz: ZoneInfo) -> datetime:
    h, m = _hm(hm)
    return (datetime(day.year, day.month, day.day, tzinfo=tz) + timedelta(hours=h, minutes=m))


def _ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ll(p: dict) -> dict:
    return {"latitude": float(p["lat"]), "longitude": float(p["lng"])}


def build_request(stops: list[dict], vehicles: list[dict], day: date, tz_name: str = "Asia/Kolkata",
                  search: str = "RETURN_FAST") -> dict:
    """The optimizeTours body. `stops` = {name, lat, lng, service_min?, window? 'HH:MM-HH:MM', load?};
    `vehicles` = {name, start{lat,lng}, end{lat,lng}?, capacity?, from? 'HH:MM', until? 'HH:MM'}.
    Every stop is a mandatory shipment (no penalty_cost = infinite per the proto): the solver may skip one only
    when it is truly infeasible, and then says why."""
    if not stops or not vehicles:
        raise OptError("At least one stop and one vehicle are needed.")
    tz = ZoneInfo(tz_name)
    g0 = datetime(day.year, day.month, day.day, tzinfo=tz)
    shipments = []
    for i, st in enumerate(stops):
        visit: dict = {"arrivalLocation": _ll(st), "label": str(st.get("name") or f"stop {i + 1}")[:60]}
        if float(st.get("service_min") or 0) > 0:
            visit["duration"] = f"{int(round(float(st['service_min']) * 60))}s"
        w = st.get("window")
        if w:
            a, _, b = str(w).partition("-")
            visit["timeWindows"] = [{"startTime": _ts(_at(day, a, tz)), "endTime": _ts(_at(day, b, tz))}]
        sh: dict = {"deliveries": [visit], "label": visit["label"]}
        if int(st.get("load") or 0) > 0:
            sh["loadDemands"] = {LOAD_KEY: {"amount": str(int(st["load"]))}}
        shipments.append(sh)
    vs = []
    for i, v in enumerate(vehicles):
        vh: dict = {"label": str(v.get("name") or f"gaadi {i + 1}")[:60], "travelMode": "DRIVING",
                    "startLocation": _ll(v["start"]), "endLocation": _ll(v.get("end") or v["start"]),
                    # our own relative weights: time first, distance a tie-break. Units are only comparable to each
                    # other, never rupees.
                    "costPerTraveledHour": 1.0, "costPerKilometer": 0.05}
        if v.get("from"):
            vh["startTimeWindows"] = [{"startTime": _ts(_at(day, v["from"], tz))}]
        if v.get("until"):
            vh["endTimeWindows"] = [{"endTime": _ts(_at(day, v["until"], tz))}]
        if int(v.get("capacity") or 0) > 0:
            vh["loadLimits"] = {LOAD_KEY: {"maxLoad": str(int(v["capacity"]))}}
        vs.append(vh)
    return {"model": {"shipments": shipments, "vehicles": vs, "globalStartTime": _ts(g0),
                      "globalEndTime": _ts(g0 + timedelta(days=1))},
            "considerRoadTraffic": True, "populatePolylines": False, "searchMode": search, "timeout": "30s"}


def _dur(v) -> int:
    try:
        return int(float(str(v or "0").rstrip("s")))
    except ValueError:
        return 0


def parse_response(resp: dict, stops: list[dict], vehicles: list[dict], tz_name: str = "Asia/Kolkata") -> dict:
    """Google's answer -> a plan in her terms. Shipment/vehicle indexes are Google's; JSON omits zero ints, so
    a missing shipmentIndex / vehicleIndex means 0 (proto3 default)."""
    tz = ZoneInfo(tz_name)

    def local(t: str) -> str:
        try:
            return datetime.fromisoformat(str(t).replace("Z", "+00:00")).astimezone(tz).strftime("%H:%M")
        except ValueError:
            return ""
    routes = []
    seen = 0
    for r in resp.get("routes") or []:
        vi = int(r.get("vehicleIndex") or 0)
        vname = vehicles[vi].get("name") if 0 <= vi < len(vehicles) else f"gaadi {vi + 1}"
        visits, trans = r.get("visits") or [], r.get("transitions") or []
        out = []
        for k, v in enumerate(visits):
            si = int(v.get("shipmentIndex") or 0)
            leg = trans[k] if k < len(trans) else {}
            st = stops[si] if 0 <= si < len(stops) else {}
            out.append({"order": k + 1, "stop": st.get("name") or v.get("shipmentLabel") or f"stop {si + 1}",
                        "arrive": local(v.get("startTime", "")),
                        "leg_km": round(float(leg.get("travelDistanceMeters") or 0) / 1000, 1),
                        "leg_min": round(_dur(leg.get("travelDuration")) / 60),
                        "lat": st.get("lat"), "lng": st.get("lng")})
        seen += len(out)
        last = trans[len(visits)] if len(visits) < len(trans) else {}
        m = r.get("metrics") or {}
        km = round(float(m.get("travelDistanceMeters") or sum(float((t or {}).get("travelDistanceMeters") or 0) for t in trans)) / 1000, 1)
        drive = round(_dur(m.get("travelDuration")) / 60) or round(sum(_dur((t or {}).get("travelDuration")) for t in trans) / 60)
        routes.append({"vehicle": vname, "start": local(r.get("vehicleStartTime", "")), "end": local(r.get("vehicleEndTime", "")),
                       "stops": out, "back_km": round(float(last.get("travelDistanceMeters") or 0) / 1000, 1),
                       "back_min": round(_dur(last.get("travelDuration")) / 60), "total_km": km, "drive_min": drive,
                       "traffic_warning": bool(r.get("hasTrafficInfeasibilities"))})
    skipped = []
    for sk in resp.get("skippedShipments") or []:
        si = int(sk.get("index") or 0)
        codes = [(x or {}).get("code", "") for x in sk.get("reasons") or []]
        skipped.append({"stop": (stops[si].get("name") if 0 <= si < len(stops) else sk.get("label")) or f"stop {si + 1}",
                        "why": [REASONS.get(c, c or "no reason given") for c in codes] or ["Google gave no reason"]})
    return {"routes": routes, "skipped": skipped, "placed": seen, "submitted": len(stops),
            "complete": seen + len(skipped) == len(stops),
            "validation_errors": [str((e or {}).get("displayName") or (e or {}).get("name") or e)[:160]
                                  for e in resp.get("validationErrors") or []]}


# ---------------------------------------------------------------- the call
async def optimize(stops: list[dict], vehicles: list[dict], day: date | None = None, tenant_id: str = "",
                   tz_name: str = "Asia/Kolkata") -> dict:
    s = get_settings()
    if len(vehicles) > MAX_VEHICLES:
        raise OptError(f"At most {MAX_VEHICLES} vehicles at a time.")
    cap = max(1, int(s.maps_opt_max_stops or 40))
    if len(stops) > cap:
        raise OptError(f"At most {cap} stops at a time (each stop is charged); there are {len(stops)}. Split them into two parts.")
    day = day or datetime.now(ZoneInfo(tz_name)).date()
    body = build_request(stops, vehicles, day, tz_name)
    token = await asyncio.to_thread(_token)                     # before billing: a missing key costs nothing
    rc = maps._bill(tenant_id, mapsbill.SKU_OPT, len(stops))
    try:
        r = await maps._client().post(URL.format(project=s.route_opt_project.strip()), json=body,
                                      headers={"Authorization": f"Bearer {token}"}, timeout=60)
    except Exception:
        maps._unbill(rc)
        raise
    if r.status_code >= 400:
        maps._unbill(rc)
        if r.status_code in (401, 403):
            raise OptError("Google refused Route Optimization: enable this API in the project and "
                           "give the service account access.")
        raise OptError(maps._explain(r))
    plan = parse_response(r.json() or {}, stops, vehicles, tz_name)
    plan["day"] = day.isoformat()
    return plan
