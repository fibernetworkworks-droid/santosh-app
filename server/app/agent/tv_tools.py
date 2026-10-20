"""Hoola TV for the avatar: free live channels on the phone or the TV."""
from __future__ import annotations

from .tools import Ctx, ToolError

TV_TOOLS = [
    {"name": "tv_channel", "description": (
        "Hoola TV: about 4,300 free, official live TV channels from 140 countries (India first). India: all Doordarshan "
        "channels incl. DD Sahyadri / Girnar / Bangla / Tamil..., Sansad TV, free news like Zee News, NDTV, Aaj Tak, India TV, "
        "ABP, Republic, Manorama, Asianet, bhakti like Aastha, music. World: BBC News, Al Jazeera, DW, France 24, CNN, "
        "Bloomberg, Euronews, ABC News, Red Bull TV and the free Samsung TV Plus / Pluto TV / Rakuten / Plex channels. "
        "action=find (query: channel name or a kind like 'news', 'bhajan', 'Marathi', 'movies'; country: a country name or "
        "code like 'US' / 'Germany' to look only there), action=play (query or channel id; on='phone' plays in the Hoola "
        "app, on='tv' plays on the Chromecast / Android TV / Google TV on the same Wi-Fi; tv = which TV if several), "
        "action=stop (stop on the TV), action=tvs (which TVs Hoola can play on). Paid channels (Star, Sony, Colors, Zee TV, "
        "HBO, live sports) are NOT here: say they need their own app. If the TV can't be cast to (many Samsung / LG TVs), "
        "use tv_remote with app='youtube' and search='<channel> live' to play the channel's official YouTube live stream on "
        "that TV."), "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["find", "play", "stop", "tvs"]},
         "query": {"type": "string"}, "country": {"type": "string"}, "on": {"type": "string", "enum": ["phone", "tv"]},
         "tv": {"type": "string"}}, "required": ["action"]}},
]

TV_LABELS = {"tv_channel": "TV channel laga raha hoon"}


async def tv_channel(ctx: Ctx, action, query="", on="phone", tv="", country="", **_):
    from ..tv import catalog, service
    try:
        if action == "find":
            hits = catalog.find(str(query or ""), limit=8, country=str(country or ""))
            return {"channels": [{k: h[k] for k in ("id", "name", "category_label", "country", "on_tv")} for h in hits],
                    "note": "Free official channels only." if hits else "Koi free channel nahi mila."}
        if action == "tvs":
            return await service.tvs(ctx.tenant_id, ctx.conversation_id)
        if action == "stop":
            return await service.stop_on_tv(ctx.tenant_id, ctx.conversation_id, str(tv or ""))
        if action == "play":
            q = str(query or "").strip()
            if not q:
                raise ToolError("Kaunsa channel? query mein naam do.")
            ch = catalog.get(q) or None
            cid = q if ch else service.pick(q, str(country or ""))["id"]
            if on == "tv":
                return await service.play_on_tv(ctx.tenant_id, ctx.conversation_id, cid, str(tv or ""))
            d = service.detail(cid)
            from .life_tools import _device_action
            return {"channel": d["name"], **_device_action(ctx, "tv_play", {"channel": d["id"], "name": d["name"]},
                                                           f"{d['name']} Hoola app mein chal raha hai.")}
    except service.TvError as e:
        raise ToolError(str(e))
    raise ToolError("action: find, play, stop ya tvs")


TV_HANDLERS = {"tv_channel": tv_channel}
