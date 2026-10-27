"""Google Maps tools: nearby places, directions with traffic, and opening navigation on the phone."""
from __future__ import annotations

from .. import maps
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
]

MAPS_LABELS = {"maps_search": "Google Maps par dhoondh raha hoon", "maps_directions": "Rasta aur samay dekh raha hoon",
               "maps_navigate": "Phone par navigation bhej raha hoon"}


def _mode(m) -> str:
    return maps.MODES.get(str(m or "car").lower(), "DRIVE")


def _open_card(ctx: Ctx, url: str, label: str, message: str = "") -> None:
    bus.publish(ctx.conversation_id, "bazar_open", {"kind": "app", "url": url, "package": maps.MAPS_PACKAGE,
                                                    "label": label, "pack": "Google Maps", "message": message})


async def maps_search(ctx: Ctx, query, near="", open_now=False, **_):
    here = maps.where_am_i(ctx.tenant_id)
    try:
        center = here if maps._is_here(near) else (await maps.geocode(str(near), near=here) if near else here)
        if not maps.configured():
            raise maps.MapsError("")
        places = await maps.search_places(str(query), near=center, open_now=bool(open_now))
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
        r = await maps.route(src, dst, m)
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
            g = await maps.geocode(dest, near=maps.where_am_i(ctx.tenant_id))
            if g:
                dest = {"lat": g["lat"], "lng": g["lng"]}
        except maps.MapsError:
            pass
    link = maps.nav_link(dest, None, m)
    _open_card(ctx, link, "Navigation shuru karein", f"{destination} ke liye Google Maps")
    return {"sent_to_phone": True, "link": link, "note": "Tell the user to tap 'Navigation shuru karein'."}


MAPS_HANDLERS = {"maps_search": maps_search, "maps_directions": maps_directions, "maps_navigate": maps_navigate}
