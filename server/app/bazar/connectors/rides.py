"""Ride apps: Santosh sets pickup and drop and opens the app; the user taps Book.

Uber's universal link format is public. Other apps open by Android package until their links are verified on device.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

from ..packs.registry import Pack
from .base import Ctx, NeedsApproval, ToolError, ToolSpec


class RideExecutor:
    name = "ride"

    def tool_specs(self, pack: Pack, ctx: Ctx) -> list[ToolSpec]:
        loc = {"type": "object", "description": "A place: lat/lng if known, else just its name",
               "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}, "name": {"type": "string"}}}
        return [ToolSpec("ride_link", f"Open {pack.name} with pickup and drop already set. The user books in the app.",
                         {"type": "object", "properties": {"pickup": loc, "drop": loc}, "required": ["drop"]}, 1)]

    def call(self, pack: Pack, tool: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any] | NeedsApproval:
        if tool != "ride_link":
            raise ToolError(f"Unknown tool {tool}")
        drop = args.get("drop") or {}
        if isinstance(drop, str):
            drop = {"name": drop}
        pickup = args.get("pickup") or ctx.user.profile.get("home_location") or {}
        if isinstance(pickup, str):
            pickup = {"name": pickup}
        has_drop = drop.get("lat") is not None and drop.get("lng") is not None
        if not has_drop and not drop.get("name"):
            raise ToolError("I need the drop location. Which place?")
        tpl = pack.config.get("link") or ""
        url = ""
        if tpl and has_drop:
            if pickup.get("lat") is not None:
                url = tpl.format(plat=pickup["lat"], plng=pickup["lng"], dlat=drop["lat"], dlng=drop["lng"],
                                 dname=quote(str(drop.get("name", "Drop"))))
            elif "uber.com" in tpl:  # Uber supports the phone's current location as pickup
                url = (f"https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[latitude]={drop['lat']}"
                       f"&dropoff[longitude]={drop['lng']}&dropoff[nickname]={quote(str(drop.get('name', 'Drop')))}")
        elif "uber.com" in tpl and drop.get("name"):
            url = f"https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[formatted_address]={quote(str(drop['name']))}"
        pkg = pack.config.get("package", "")
        if not url and not pkg:
            raise ToolError(f"{pack.name} can't be opened from Santosh yet (no app link). Please open it directly.")
        return {"app": pack.name, "deep_link": url, "android_package": pkg, "link_verified": bool(pack.config.get("verified")),
                "pickup": pickup, "drop": drop,
                "message": f"Opening {pack.name}" + (" with your pickup and drop set. Check and tap Book." if url else
                                                     ". Set the drop to " + str(drop.get("name", "your destination")) + " and tap Book.")}

    def execute(self, pack: Pack, action: str, args: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
        raise ToolError("Ride packs have no approval actions")
