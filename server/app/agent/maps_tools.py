"""Google Maps tools: nearby places, directions with traffic, and opening navigation on the phone."""
from __future__ import annotations

from .. import maps, mapsbill
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
    {"name": "maps_kharcha", "description": (
        "Today's Google Maps spend for this user: calls made, how many were inside Google's free monthly "
        "allowance, rupees spent, the daily cap and what is left. Use it when she asks what Maps is costing, or "
        "to explain why a maps tool just refused."),
     "input_schema": {"type": "object", "properties": {}}},
]

MAPS_LABELS = {"maps_search": "Google Maps par dhoondh raha hoon", "maps_directions": "Rasta aur samay dekh raha hoon",
               "maps_navigate": "Phone par navigation bhej raha hoon",
               "maps_nearby": "Aas-paas dekh raha hoon", "maps_place": "Jagah ki poori detail le raha hoon",
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


async def maps_kharcha(ctx: Ctx, **_):
    u = mapsbill.usage(ctx.tenant_id)
    return {**u, "note": ("Rupees are an estimate: Google's own list is in USD and bills the billing account's "
                          "currency. 'free_calls' were inside Google's free monthly allowance, so they cost "
                          "nothing. A call that would cross cap_inr is refused before it is made.")}


MAPS_HANDLERS = {"maps_search": maps_search, "maps_directions": maps_directions, "maps_navigate": maps_navigate,
                 "maps_nearby": maps_nearby, "maps_place": maps_place, "maps_kharcha": maps_kharcha}
