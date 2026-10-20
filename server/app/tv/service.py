"""Hoola TV: find a free channel and play it on the phone, or on the TV (Chromecast / Android TV / Google TV over
Wi-Fi, through the phone). For TVs that can't be cast to (many Samsung / LG), Hoola's TV remote can open YouTube on the
TV and play the channel's official live stream instead."""
from __future__ import annotations

from typing import Any

from ..config import get_settings
from . import catalog


class TvError(Exception):
    pass


def pick(query: str) -> dict:
    hits = catalog.find(query, limit=5)
    if not hits:
        raise TvError(f"'{query}' naam ka free channel nahi mila. Hoola TV mein sirf free, official channels hain "
                      "(Doordarshan, free news, bhakti, music...). Paid channels (Star, Sony, Colors) ke liye unka app.")
    return hits[0]


def detail(cid: str) -> dict:
    c = catalog.get(cid)
    if c is None:
        raise TvError("Yeh channel nahi mila.")
    st = catalog.stream_for(c)
    if st is None:
        raise TvError(f"{c['name']} abhi chal nahi raha. Thodi der baad try kijiye.")
    v = catalog.view(c)
    return {**v, "url": st["url"], "user_agent": st.get("user_agent", ""), "referrer": st.get("referrer", ""),
            "alternates": [s["url"] for s in c["streams"][1:] if s.get("ok", True)]}


async def play_on_tv(tenant: str, conversation_id: str, cid: str, tv: str = "") -> dict[str, Any]:
    from ..bt import service as bt
    c = catalog.get(cid)
    if c is None:
        raise TvError("Yeh channel nahi mila.")
    st = catalog.stream_for(c, for_tv=True)
    if st is None:
        return {"status": "failed", "channel": c["name"],
                "error": f"{c['name']} sirf phone pe chalta hai (TV is stream ko nahi le sakta). Phone pe chalayein, ya TV pe "
                         f"YouTube khol kar '{c['name']} live' chalayein (tv_remote app=youtube)."}
    base = get_settings().public_base_url.rstrip("/")
    args = {"url": st["url"], "title": c["name"], "tv": tv}
    if base.startswith("https://") and c.get("logo_src"):
        args["logo"] = f"{base}/api/logo/tv/{cid}"
    res = await bt.run(tenant, conversation_id, "cast_play", args)
    return {"channel": c["name"], **res}


async def stop_on_tv(tenant: str, conversation_id: str, tv: str = "") -> dict[str, Any]:
    from ..bt import service as bt
    return await bt.run(tenant, conversation_id, "cast_stop", {"tv": tv})


async def tvs(tenant: str, conversation_id: str) -> dict[str, Any]:
    from ..bt import service as bt
    return await bt.run(tenant, conversation_id, "cast_tvs", {})
