"""Google Maps tools: nearby places, directions with traffic, and opening navigation on the phone."""
from __future__ import annotations

from .. import maps, mapsbill
from ..config import get_settings
from ..events import bus
from .tools import Ctx, ToolError

MAPS_TOOLS = [
    {"name": "maps_search", "description": (
        "Find real places on Google Maps: shops, restaurants, hospitals, ATMs, petrol pumps, chemists, hotels, offices, "
        "any business or landmark. 'near' is a place name, or leave it empty for near the user (their phone location). "
        "Returns name, address, rating, open now, phone, distance and a Maps link for each."),
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "What to find, e.g. 'medical store', '24 hour hospital', 'Haldiram Nagpur'"},
         "near": {"type": "string", "description": "Area or place to search around; empty = near the user"},
         "open_now": {"type": "boolean"}}, "required": ["query"]}},
    {"name": "maps_directions", "description": (
        "Distance, travel time with live traffic and the route between two places (car, bike/two-wheeler, walk or "
        "public transport). Origin empty = the user's current location. Also shows a 'Start navigation' button on "
        "the phone."),
     "input_schema": {"type": "object", "properties": {
         "destination": {"type": "string"}, "origin": {"type": "string"},
         "mode": {"type": "string", "enum": ["car", "bike", "walk", "transit"]}}, "required": ["destination"]}},
    {"name": "maps_navigate", "description": "Open Google Maps navigation on the user's phone to a place (one tap).",
     "input_schema": {"type": "object", "properties": {
         "destination": {"type": "string"}, "mode": {"type": "string", "enum": ["car", "bike", "walk", "transit"]}},
         "required": ["destination"]}},
    # v0.449 Phase 3 PAAS KYA HAI
    {"name": "maps_nearby", "description": (
        "What is around a point, BY CATEGORY - the 'chemist near me' / 'petrol pump is kahan' question. Use this "
        "instead of maps_search when the user names a KIND of place rather than a particular one, because it "
        "searches by Google's own place types and ranks by real distance.\n"
        "'kinds' are Google place types, e.g. pharmacy, hospital, doctor, bank, atm, gas_station, hardware_store, "
        "electrician, plumber, restaurant, school, gym, hotel, courier_service, real_estate_agency, "
        "building_materials_store, wholesaler, tailor, travel_agency (up to 50).\n"
        "Hard limits set by Google, not by us: the area is a CIRCLE (radius up to 50 km), at most 20 results come "
        "back, and there is NO next page - for a wider sweep, call it again around a different point.\n"
        "The list gives name, address, distance, type and a Maps link. Phone, website, rating and opening hours "
        "are NOT in the list (they cost more) - call maps_place with a place_id to get them for one place the "
        "user picks."),
     "input_schema": {"type": "object", "properties": {
         "kinds": {"type": "array", "items": {"type": "string"}, "description": "Google place types, e.g. ['pharmacy']"},
         "near": {"type": "string", "description": "Area or place to search around; empty = where the user is now"},
         "radius_km": {"type": "number", "description": "Up to 50. Default 2"},
         "limit": {"type": "integer", "description": "Up to 20. Default 12"},
         "rank": {"type": "string", "enum": ["distance", "popularity"]}}, "required": ["kinds"]}},
    {"name": "maps_place", "description": (
        "Everything about ONE place, from its place_id: phone number, website, rating, review count and the week's "
        "opening hours. Call this when the user picks a place from a maps_nearby / maps_search list, or asks for a "
        "number, website or timings. One place at a time on purpose - these fields are the expensive ones, so they "
        "are bought for the place she actually wants and never for a whole list.\n"
        "Never store or repeat this as a saved list: it is read fresh each time it is shown."),
     "input_schema": {"type": "object", "properties": {
         "place_id": {"type": "string", "description": "From a maps_nearby or maps_search result"}},
         "required": ["place_id"]}},
    # v0.463 Phase 4 SABSE PAAS
    {"name": "maps_nearest", "description": (
        "Which of THESE places is nearest by real road time - 'in 8 mein se kaun sa godown sabse paas hai', 'which "
        "of my 5 workers is closest to this customer', 'nearest branch'. Gives true road distance and travel time "
        "with live traffic from the starting point (or points) to every candidate, ranked, using Google's route "
        "matrix. Use this when she already HAS the list; to FIND places of a kind use maps_nearby; one trip's "
        "route and steps = maps_directions.\n"
        "'candidates' are place names, 'lat,lng', or objects {name, lat, lng} (objects from a maps_nearby result "
        "cost nothing to locate; a plain name costs one lookup). 'origins' empty = where she is now.\n"
        "Every origin x candidate pair is billed, so it is capped (default 100 pairs). With ONE origin and more "
        "candidates than that, the closest by straight line are checked on the road and the answer says so. A "
        "pair Google cannot route is reported as unreachable, never guessed."),
     "input_schema": {"type": "object", "properties": {
         "candidates": {"type": "array", "items": {}, "description": "Places to compare (names, 'lat,lng' or {name,lat,lng})"},
         "origins": {"type": "array", "items": {}, "description": "Where from; empty = the user's location"},
         "mode": {"type": "string", "enum": ["car", "bike", "walk", "transit"]},
         "top": {"type": "integer", "description": "How many best to return per origin. Default 3"}},
         "required": ["candidates"]}},
    # v0.464 Phase 6 PATA PAKKA
    {"name": "maps_address_check", "description": (
        "Check ONE Indian delivery address with Google before it becomes a failed delivery: is it complete, is the "
        "PIN right, was anything unreadable, and how far did Google get - 'pakka' (the house matched), 'sadak_tak' "
        "(only the road / block matched - very common for landmark-style addresses and NOT wrong; confirm by phone "
        "or landmark) or 'galat' (something unconfirmed, missing, or the PIN was replaced). Returns the corrected "
        "single-line address and its location. One address per call, each is billed - never run it over a whole "
        "customer list. Read live, not stored."),
     "input_schema": {"type": "object", "properties": {
         "address": {"type": "string", "description": "The address as written (house, street, landmark, area)"},
         "pin": {"type": "string", "description": "6-digit PIN if known"},
         "city": {"type": "string"}, "state": {"type": "string"}}, "required": ["address"]}},
    {"name": "maps_pata", "description": (
        "What address is AT this spot (reverse geocode): a latitude/longitude -> the nearest address. Empty "
        "lat/lng = where the user is now. For turning a pin / shared location / driver position into words."),
     "input_schema": {"type": "object", "properties": {
         "lat": {"type": "number"}, "lng": {"type": "number"}}}},
    # v0.465 Phase 5 DIN KA RASTA
    {"name": "maps_route_plan", "description": (
        "Plan the DAY'S STOP ORDER: which order to visit these stops so the driving is least, with time windows, "
        "service time and truck capacity (Google Route Optimization). 'aaj ke 12 delivery kis kram mein', 'driver "
        "ka din plan karo'. It only PROPOSES an order - nothing is assigned or sent; she decides. For 'which ONE of "
        "these is nearest' use maps_nearest; for one trip's route and steps use maps_directions.\n"
        "'stops': names / 'lat,lng' / objects {name, lat, lng, service_min, window:'10:00-12:00', load}. "
        "'vehicles': optional list {name, start, end, capacity, from:'09:00', until:'19:00'}; empty = one vehicle "
        "from where she is, returning there. Each stop is billed, so it is capped (default 40). A stop Google "
        "cannot fit is reported with its reason, never dropped quietly."),
     "input_schema": {"type": "object", "properties": {
         "stops": {"type": "array", "items": {}, "description": "Places to visit"},
         "vehicles": {"type": "array", "items": {}, "description": "Optional vehicles; empty = one from her location"},
         "day": {"type": "string", "description": "YYYY-MM-DD; default today"}}, "required": ["stops"]}},
    # v0.466 Phase 7 KAAGAZ PAR (links, never a stored map picture - see docs/research/maps/05_static_maps_licence.md)
    {"name": "maps_links", "description": (
        "Google Maps LINKS for a place, to put in a PDF, a WhatsApp message or a bill: 'is jagah ka map bhej do', "
        "'Street View dikhao'. Gives a 'view on Google Maps' link, optionally a directions link, and a Street View "
        "link ONLY if Google really has a panorama there (checked free). Free; nothing is stored.\n"
        "Use LINKS, never a downloaded map picture: Google's terms forbid saving or re-sharing its map / Street View "
        "images in a file (a picture pasted into a PDF is exactly that), but a link that opens Google's own map is fine.\n"
        "'place' is a name / address / 'lat,lng', or pass lat+lng (+ place_id from a maps_nearby result)."),
     "input_schema": {"type": "object", "properties": {
         "place": {"type": "string"}, "lat": {"type": "number"}, "lng": {"type": "number"},
         "place_id": {"type": "string"}, "name": {"type": "string"},
         "directions": {"type": "boolean", "description": "also a directions link from where she is"},
         "streetview": {"type": "boolean", "description": "also check Street View (default true)"}}}},
    {"name": "maps_kharcha", "description": (
        "Today's Google Maps spend for this user: calls made, how many were inside Google's free monthly "
        "allowance, rupees spent, the daily cap and what is left. Use it when she asks what Maps is costing, or "
        "to explain why a maps tool just refused."),
     "input_schema": {"type": "object", "properties": {}}},
]

MAPS_LABELS = {"maps_search": "Google Maps par dhoondh raha hoon", "maps_directions": "Rasta aur samay dekh raha hoon",
               "maps_navigate": "Phone par navigation bhej raha hoon",
               "maps_nearby": "Aas-paas dekh raha hoon", "maps_place": "Jagah ki poori detail le raha hoon",
               "maps_nearest": "Sabse paas wala dekh raha hoon",
               "maps_address_check": "Address jaanch raha hoon", "maps_pata": "Is jagah ka pata dekh raha hoon",
               "maps_route_plan": "Din ka rasta bana raha hoon",
               "maps_links": "Map ke links bana raha hoon",
               "maps_kharcha": "Maps ka kharcha dekh raha hoon"}


def _mode(m) -> str:
    return maps.MODES.get(str(m or "car").lower(), "DRIVE")


def _open_card(ctx: Ctx, url: str, label: str, message: str = "") -> None:
    bus.publish(ctx.conversation_id, "bazar_open", {"kind": "app", "url": url, "package": maps.MAPS_PACKAGE,
                                                    "label": label, "pack": "Google Maps", "message": message})


async def maps_search(ctx: Ctx, query, near="", open_now=False, **_):
    here = maps.where_am_i(ctx.tenant_id)
    try:
        center = here if maps._is_here(near) else (await maps.geocode(str(near), near=here, tenant_id=ctx.tenant_id) if near else here)
        if not maps.configured():
            raise maps.MapsError("")
        places = await maps.search_places(str(query), near=center, open_now=bool(open_now), tenant_id=ctx.tenant_id)
    except maps.MapsError as e:
        link = maps.search_link(str(query) + (f" {near}" if near and not maps._is_here(near) else ""), here if not near else None)
        _open_card(ctx, link, "Google Maps par dekhiye", f"'{query}' Google Maps par")
        raise ToolError((str(e) + " " if str(e) else "") + "Google Maps ka search link phone par bhej diya hai; "
                        "details ke liye google_search use karo.")
    if not places:
        return {"places": [], "message": f"'{query}' ke liye Google Maps par kuch nahi mila."}
    return {"near": (center or {}).get("name", near or ""), "places": places,
            "note": "Show 2-4 best options briefly (name, distance, rating, open/closed). Offer directions or a call."}


async def maps_directions(ctx: Ctx, destination, origin="", mode="car", **_):
    m = _mode(mode)
    here = maps.where_am_i(ctx.tenant_id)
    if not maps.configured():
        link = maps.nav_link(str(destination), None if maps._is_here(origin) else str(origin), m)
        _open_card(ctx, link, "Navigation shuru karein", f"{destination} tak ka rasta")
        raise ToolError("Google Maps key set nahi hai, isliye samay/doori nahi nikal saka; navigation button phone par bhej diya.")
    try:
        src = await maps.resolve(origin, ctx.tenant_id, near=here)
        if src is None:
            raise ToolError("Aap abhi kahan hain? Phone mein Santosh ko location permission dijiye ya jagah ka naam bataiye.")
        dst = await maps.resolve(destination, ctx.tenant_id, near=src)
        if dst is None:
            raise ToolError(f"'{destination}' Google Maps par nahi mila. Thoda aur detail bataiye (area, shehar).")
        r = await maps.route(src, dst, m, tenant_id=ctx.tenant_id)
    except maps.MapsError as e:
        raise ToolError(str(e))
    link = maps.nav_link(dst, None if src.get("source") == "phone" else src, r["mode"])
    _open_card(ctx, link, "Navigation shuru karein", f"{dst.get('name', destination)}: {r['distance_km']} km, {r['duration']}")
    return {"from": src.get("name"), "to": dst.get("name"), "to_address": dst.get("address", ""), **r,
            "phone": "A 'Navigation shuru karein' button is shown in the chat."}


async def maps_navigate(ctx: Ctx, destination, mode="car", **_):
    m = _mode(mode)
    dest = str(destination)
    if maps.configured():
        try:
            g = await maps.geocode(dest, near=maps.where_am_i(ctx.tenant_id), tenant_id=ctx.tenant_id)
            if g:
                dest = {"lat": g["lat"], "lng": g["lng"]}
        except maps.MapsError:
            pass
    link = maps.nav_link(dest, None, m)
    _open_card(ctx, link, "Navigation shuru karein", f"{destination} ke liye Google Maps")
    return {"sent_to_phone": True, "link": link, "note": "Tell the user to tap 'Navigation shuru karein'."}


# ---------------------------------------------------------------- v0.449 Phase 2 + 3
def _places_card(ctx: Ctx, title: str, places: list[dict], near: str = "", cost_inr: float | None = None) -> None:
    """Phase 2 NAKSHA DIKHE: the result as a card instead of a wall of addresses.

    Deliberately NO map. Google's terms allow Places content with no map at all (SST 14.1) and FORBID it on a
    non-Google map (SST 14.2 / ToS 3.2.3(e)), so a free-tiles map here would be a licence breach - the Google
    map is a paid option behind a setting, not a default. Attribution rides on the card because ToS 3.2.2(b)
    requires it wherever this content is shown, with or without a map.
    """
    bus.publish(ctx.conversation_id, "maps_places", {
        "title": title, "near": near, "attribution": maps.ATTRIBUTION,
        "cost_inr": round(cost_inr, 4) if cost_inr is not None else None,
        "places": [{k: v for k, v in p.items() if k in
                    ("place_id", "name", "address", "distance_km", "type", "rating", "reviews",
                     "open_now", "phone", "website", "maps_link", "lat", "lng", "status", "hours")}
                   for p in places[:20]]})


async def maps_nearby(ctx: Ctx, kinds, near="", radius_km=2, limit=12, rank="distance", **_):
    here = maps.where_am_i(ctx.tenant_id)
    if not maps.configured():
        raise ToolError("Google Maps abhi connect nahi hai (server par GOOGLE_MAPS_API_KEY set nahi hai).")
    want = [str(k).strip() for k in (kinds if isinstance(kinds, list) else [kinds]) if str(k).strip()]
    if not want:
        raise ToolError("Kis tarah ki jagah dhoondhni hai? (jaise pharmacy, bank, gas_station)")
    try:
        center = here if maps._is_here(near) else (
            await maps.geocode(str(near), near=here, tenant_id=ctx.tenant_id) if near else here)
        if center is None:
            raise ToolError("Aap abhi kahan hain? Phone mein location permission dijiye ya jagah ka naam bataiye.")
        before = mapsbill.usage(ctx.tenant_id)["inr"]
        places = await maps.nearby(center, want, radius_m=int(float(radius_km or 2) * 1000),
                                   limit=int(limit or 12), rank=str(rank or "distance"),
                                   tenant_id=ctx.tenant_id)
    except maps.MapsError as e:
        raise ToolError(str(e))
    spent = round(mapsbill.usage(ctx.tenant_id)["inr"] - before, 4)
    label = ", ".join(want[:3])
    if not places:
        return {"places": [], "message": f"{label} is dayre mein ({radius_km} km) Google Maps par kuch nahi mila. "
                                         f"Dayra bada karke dekhein?"}
    _places_card(ctx, label, places, near=(center or {}).get("name", near or ""), cost_inr=spent)
    return {"near": (center or {}).get("name", near or ""), "kinds": want, "count": len(places),
            "places": places, "cost_inr": spent, "attribution": maps.ATTRIBUTION,
            "note": ("Card already shown to her. Name the best 2-4 with distance. Phone / website / rating / "
                     "timings are NOT here on purpose - if she wants those for one place, call maps_place with "
                     "its place_id. Never save this as a list; it is read fresh each time."),
            "limits": f"Google returns at most {maps.NEARBY_MAX_RESULTS} and has no next page."}


async def maps_place(ctx: Ctx, place_id, **_):
    if not maps.configured():
        raise ToolError("Google Maps abhi connect nahi hai.")
    try:
        before = mapsbill.usage(ctx.tenant_id)["inr"]
        row = await maps.place_details(str(place_id), tenant_id=ctx.tenant_id)
    except maps.MapsError as e:
        raise ToolError(str(e))
    row["cost_inr"] = round(mapsbill.usage(ctx.tenant_id)["inr"] - before, 4)
    _places_card(ctx, row.get("name", "Jagah"), [row], cost_inr=row["cost_inr"])
    row["note"] = ("Card shown. Give her the phone / timings / website she asked for. This is read live from "
                   "Google and must not be stored or re-used as a saved list.")
    return row


async def _locate(ctx: Ctx, item, near) -> dict | None:
    """One candidate/origin -> {name, lat, lng}. Objects with coordinates and 'lat,lng' text cost nothing; a
    plain name is one geocode (billed, capped, cached place_id)."""
    if isinstance(item, dict):
        lat, lng = item.get("lat"), item.get("lng", item.get("lon"))
        try:
            if lat is not None and lng is not None:
                la, lo = float(lat), float(lng)
                if -90 <= la <= 90 and -180 <= lo <= 180:
                    return {"name": str(item.get("name") or f"{la},{lo}"), "lat": la, "lng": lo,
                            "place_id": item.get("place_id", ""), "address": item.get("address", "")}
        except (TypeError, ValueError):
            return None
        item = item.get("name") or item.get("address") or ""
    text = str(item or "").strip()
    if not text:
        return None
    if maps._is_here(text):
        return maps.where_am_i(ctx.tenant_id)
    g = await maps.geocode(text, near=near, tenant_id=ctx.tenant_id)
    return {**g, "name": text if not g else (g.get("name") or text)} if g else None


MAX_CANDIDATES = 25
MAX_ORIGINS = 5


async def maps_nearest(ctx: Ctx, candidates, origins=None, mode="car", top=3, **_):
    if not maps.configured():
        raise ToolError("Google Maps abhi connect nahi hai (server par GOOGLE_MAPS_API_KEY set nahi hai).")
    cands = candidates if isinstance(candidates, list) else [candidates]
    cands = [c for c in cands if c not in (None, "", {})]
    if not cands:
        raise ToolError("Kin jagahon mein se sabse paas dhoondhna hai? Unke naam ya location bataiye.")
    if len(cands) > MAX_CANDIDATES:
        raise ToolError(f"Ek baar mein {MAX_CANDIDATES} jagah tak hi dekh sakta hoon; {len(cands)} hain. "
                        f"Do hisson mein baant dein.")
    srcs = origins if isinstance(origins, list) else ([origins] if origins else [])
    srcs = [o for o in srcs if o not in (None, "", {})] or ["here"]
    if len(srcs) > MAX_ORIGINS:
        raise ToolError(f"Ek baar mein {MAX_ORIGINS} shuruaati jagah tak.")
    m = _mode(mode)
    here = maps.where_am_i(ctx.tenant_id)
    try:
        o_pts, d_pts, missing = [], [], []
        for o in srcs:
            pt = await _locate(ctx, o, here)
            if pt is None:
                raise ToolError("Aap abhi kahan hain? Phone mein location permission dijiye ya jagah ka naam bataiye."
                                if maps._is_here(str(o)) else f"'{o}' Google Maps par nahi mila.")
            o_pts.append(pt)
        for c in cands:
            pt = await _locate(ctx, c, o_pts[0])
            if pt is None:
                missing.append(str(c.get("name") if isinstance(c, dict) else c))
            else:
                d_pts.append(pt)
        if not d_pts:
            raise ToolError("Inmein se koi jagah Google Maps par nahi mili: " + ", ".join(missing)[:200])
        cap = max(1, int(get_settings().maps_matrix_max or 100))
        prefiltered = False
        if len(o_pts) * len(d_pts) > cap:
            if len(o_pts) == 1:       # shortlist by straight line, then ask the road about the shortlist only
                d_pts.sort(key=lambda d: maps._km(o_pts[0], d))
                d_pts, prefiltered = d_pts[:cap], True
            else:
                raise ToolError(f"{len(o_pts)} x {len(d_pts)} jodiyan hain; ek baar mein {cap} tak hi "
                                f"(har jodi ka alag paisa lagta hai). Kam jagah dein.")
        before = mapsbill.usage(ctx.tenant_id)["inr"]
        rows = await maps.matrix(o_pts, d_pts, m, tenant_id=ctx.tenant_id)
    except maps.MapsError as e:
        raise ToolError(str(e))
    spent = round(mapsbill.usage(ctx.tenant_id)["inr"] - before, 4)
    n = max(1, min(int(top or 3), 10))
    result, card = [], []
    for o, row in zip(o_pts, rows):
        ranked = sorted(((d, c) for d, c in zip(d_pts, row) if c["ok"]), key=lambda t: t[1]["duration_min"])
        bad = [d["name"] for d, c in zip(d_pts, row) if not c["ok"]]
        best = [{"name": d["name"], "address": d.get("address", ""), "distance_km": c["distance_km"],
                 "duration_min": c["duration_min"], "duration": c["duration"],
                 "straight_km": round(maps._km(o, d), 1)} for d, c in ranked[:n]]
        result.append({"from": o.get("name"), "nearest": best[0] if best else None, "ranked": best,
                       "unreachable": bad})
        if not card:
            card = [{"name": b["name"], "address": b.get("address", ""), "distance_km": b["distance_km"],
                     "type": f"{b['duration']} · {'gaadi se' if m == 'DRIVE' else 'raste se'}"} for b in best]
    if card:
        _places_card(ctx, "Sabse paas", card, near=o_pts[0].get("name", ""), cost_inr=spent)
    out = {"mode": m, "compared": len(d_pts), "results": result, "cost_inr": spent,
           "attribution": maps.ATTRIBUTION}
    if prefiltered:
        out["prefiltered"] = (f"{len(cands)} mein se straight-line par sabse paas {cap} ko road par check kiya "
                              f"(har jodi ka paisa lagta hai). Baaki door hain, par road se alag ho sakta hai.")
    if missing:
        out["not_found"] = missing
    out["note"] = ("Card shown for the first starting point. Name the winner with minutes and km in one line, "
                   "then the runner-up. These are live road times with traffic and change - never store them. "
                   "Say plainly anything in 'unreachable' / 'not_found' / 'prefiltered'.")
    return out


async def maps_address_check(ctx: Ctx, address, pin="", city="", state="", **_):
    if not maps.configured():
        raise ToolError("Google Maps abhi connect nahi hai (server par GOOGLE_MAPS_API_KEY set nahi hai).")
    try:
        before = mapsbill.usage(ctx.tenant_id)["inr"]
        r = await maps.validate_address(str(address), str(pin or ""), str(city or ""), str(state or ""),
                                        tenant_id=ctx.tenant_id)
    except maps.MapsError as e:
        raise ToolError(str(e))
    r["cost_inr"] = round(mapsbill.usage(ctx.tenant_id)["inr"] - before, 4)
    r["note"] = ("Say the grade in one plain line, then the reasons that matter and the corrected address. "
                 "'sadak_tak' is normal for landmark addresses - suggest confirming by phone, do not call it wrong. "
                 "Read live from Google: do not store it as a customer record.")
    return r


async def maps_pata(ctx: Ctx, lat=None, lng=None, **_):
    if not maps.configured():
        raise ToolError("Google Maps abhi connect nahi hai (server par GOOGLE_MAPS_API_KEY set nahi hai).")
    if lat is None or lng is None:
        here = maps.where_am_i(ctx.tenant_id)
        if here is None:
            raise ToolError("Aap abhi kahan hain? Phone mein location permission dijiye ya lat/lng bataiye.")
        lat, lng = here["lat"], here["lng"]
    try:
        before = mapsbill.usage(ctx.tenant_id)["inr"]
        r = await maps.reverse_geocode(float(lat), float(lng), tenant_id=ctx.tenant_id)
    except (maps.MapsError, ValueError) as e:
        raise ToolError(str(e))
    if r is None:
        return {"address": "", "message": "Is point ka koi pata Google ke paas nahi."}
    r["cost_inr"] = round(mapsbill.usage(ctx.tenant_id)["inr"] - before, 4)
    return r


async def _stop_with_extras(ctx: Ctx, item, near) -> dict | None:
    pt = await _locate(ctx, item, near)
    if pt is None:
        return None
    if isinstance(item, dict):
        for k in ("service_min", "window", "load"):
            if item.get(k) not in (None, ""):
                pt[k] = item[k]
    return pt


async def maps_route_plan(ctx: Ctx, stops, vehicles=None, day="", **_):
    from datetime import date
    from .. import mapsopt
    if not maps.configured():
        raise ToolError("Google Maps abhi connect nahi hai (server par GOOGLE_MAPS_API_KEY set nahi hai).")
    if not mapsopt.configured():
        raise ToolError("Din ka rasta ke liye Google Cloud project aur service-account file chahiye (server par "
                        "ROUTE_OPT_PROJECT aur ROUTE_OPT_SA_FILE) - Maps ki API key isme nahi chalti. "
                        "Abhi order tay nahi kar sakta; maps_nearest se sabse paas wala dekh sakta hoon.")
    raw = [x for x in (stops if isinstance(stops, list) else [stops]) if x not in (None, "", {})]
    if not raw:
        raise ToolError("Kin jagahon ka rasta banana hai? Stops bataiye.")
    try:
        d = date.fromisoformat(str(day)) if day else None
    except ValueError:
        raise ToolError("Taarikh YYYY-MM-DD mein chahiye.")
    here = maps.where_am_i(ctx.tenant_id)
    try:
        vs_in = [v for v in (vehicles if isinstance(vehicles, list) else []) if v]
        veh = []
        for i, v in enumerate(vs_in or [{}]):
            v = v if isinstance(v, dict) else {"start": v}
            start = await _locate(ctx, v.get("start") or "here", here) if (v.get("start") or here) else None
            if start is None:
                raise ToolError("Gaadi kahan se chalegi? Phone mein location permission dijiye ya shuruaat ki jagah bataiye.")
            end = await _locate(ctx, v["end"], here) if v.get("end") else None
            veh.append({"name": v.get("name") or f"Gaadi {i + 1}", "start": start, "end": end,
                        "capacity": v.get("capacity"), "from": v.get("from"), "until": v.get("until")})
        pts, missing = [], []
        for item in raw:
            pt = await _stop_with_extras(ctx, item, veh[0]["start"])
            (pts if pt else missing).append(pt or str(item.get("name") if isinstance(item, dict) else item))
        if not pts:
            raise ToolError("Inmein se koi jagah Google Maps par nahi mili: " + ", ".join(missing)[:200])
        before = mapsbill.usage(ctx.tenant_id)["inr"]
        plan = await mapsopt.optimize(pts, veh, d, tenant_id=ctx.tenant_id)
    except (maps.MapsError, ValueError) as e:
        raise ToolError(str(e))
    plan["cost_inr"] = round(mapsbill.usage(ctx.tenant_id)["inr"] - before, 4)
    for r in plan["routes"][:3]:
        _places_card(ctx, f"Din ka rasta - {r['vehicle']}",
                     [{"name": f"{s['order']}. {s['stop']}", "distance_km": s["leg_km"],
                       "type": f"{s['arrive']} pahunchenge · {s['leg_min']} min", "lat": s["lat"], "lng": s["lng"]}
                      for s in r["stops"]], near="", cost_inr=plan["cost_inr"])
    if missing:
        plan["not_found"] = missing
    plan["attribution"] = maps.ATTRIBUTION
    plan["note"] = ("This is a PROPOSED order only - nothing was assigned or sent. Give her the order in one short "
                    "list per vehicle (stop, arrival time) with total km and drive time, then say plainly anything in "
                    "'skipped' / 'not_found' / a false 'complete'. Times are live-traffic estimates for that day.")
    return plan


async def maps_links(ctx: Ctx, place="", lat=None, lng=None, place_id="", name="", directions=False,
                     streetview=True, **_):
    if lat is None or lng is None:
        if not str(place or "").strip():
            raise ToolError("Kis jagah ka link chahiye? Naam, pata ya lat/lng bataiye.")
        if not maps.configured():
            # no key: the search link still works - it needs none
            link = maps.search_link(str(place), maps.where_am_i(ctx.tenant_id))
            return {"name": str(place), "view": link, "streetview": None,
                    "note": "Maps key set nahi, isliye Street View nahi dekh paya; search link diya."}
        try:
            pt = await maps.resolve(str(place), ctx.tenant_id, near=maps.where_am_i(ctx.tenant_id))
        except maps.MapsError as e:
            raise ToolError(str(e))
        if pt is None:
            raise ToolError(f"'{place}' Google Maps par nahi mila. Area / shehar ke saath bataiye.")
        lat, lng = pt["lat"], pt["lng"]
        name = name or pt.get("name") or str(place)
    try:
        la, lo = float(lat), float(lng)
    except (TypeError, ValueError):
        raise ToolError("lat/lng sahi nahi hain.")
    if not (-90 <= la <= 90 and -180 <= lo <= 180):
        raise ToolError("lat/lng sahi nahi hain.")
    out: dict = {"name": name or f"{la},{lo}", "view": maps.view_link(la, lo, str(place_id or ""), str(name or ""))}
    if directions:
        out["directions"] = maps.nav_link({"lat": la, "lng": lo}, None, "DRIVE", navigate=False)
    out["streetview"] = None
    if streetview and maps.configured():
        try:
            sv = await maps.streetview_check(la, lo, tenant_id=ctx.tenant_id)
        except maps.MapsError as e:
            out["streetview_note"] = f"Street View nahi dekh paya: {e}"
        else:
            if sv["available"]:
                out["streetview"] = maps.streetview_link(la, lo, sv["pano_id"])
                out["streetview_date"] = sv["date"]
            else:
                out["streetview_note"] = "Yahan Street View nahi hai."
    out["attribution"] = maps.ATTRIBUTION
    out["note"] = ("Put these LINKS in the PDF / message as plain text or hyperlinks. Do not fetch or embed a map "
                   "or Street View picture: the terms forbid storing or re-sharing Google's images in a file.")
    return out


async def maps_kharcha(ctx: Ctx, **_):
    u = mapsbill.usage(ctx.tenant_id)
    return {**u, "note": ("Rupees are an estimate: Google's own list is in USD and bills the billing account's "
                          "currency. 'free_calls' were inside Google's free monthly allowance, so they cost "
                          "nothing. A call that would cross cap_inr is refused before it is made.")}


MAPS_HANDLERS = {"maps_search": maps_search, "maps_directions": maps_directions, "maps_navigate": maps_navigate,
                 "maps_nearby": maps_nearby, "maps_place": maps_place, "maps_nearest": maps_nearest,
                 "maps_address_check": maps_address_check, "maps_pata": maps_pata,
                 "maps_route_plan": maps_route_plan, "maps_links": maps_links, "maps_kharcha": maps_kharcha}
