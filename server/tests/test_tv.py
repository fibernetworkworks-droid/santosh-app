"""Hoola TV: only official free streams make the list; channels play on the phone or are cast to the TV."""
import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.tv import catalog

CHANNELS = """id,name,alt_names,network,owners,country,categories,is_nsfw,launched,closed,replaced_by,website
DDSahyadri.in,DD Sahyadri,,Doordarshan,Prasar Bharati,IN,general,FALSE,,,,https://ddsahyadri.gov.in
NDTVProfit.in,NDTV Profit,,NDTV,NDTV,IN,business,FALSE,,,,https://www.ndtvprofit.com
StarPlus.in,StarPlus,,Star,Disney Star,IN,entertainment,FALSE,,,,https://www.hotstar.com
SonyMax.in,Sony Max,,Sony,Culver Max,IN,movies,FALSE,,,,https://www.sonyliv.com
ZeeDilSe.in,Zee Dil Se,,Zee,Zee,IN,entertainment,FALSE,,,,
Copied.in,Copied TV,,,,IN,news,FALSE,,,,
Adult.in,Adult X,,,,IN,general,TRUE,,,,
Abroad.us,Abroad TV,,,,US,news,FALSE,,,,
Unknown.in,Unknown News,,,,IN,news,FALSE,,,,
"""
BLOCK = "channel,reason,ref\nCopied.in,dmca,https://x\n"
LOGOS = "channel,feed,in_use,tags,width,height,format,url\nDDSahyadri.in,,TRUE,,512,512,PNG,https://i.imgur.com/dd.png\n"
M3U = {
    "in.m3u": """#EXTM3U
#EXTINF:-1 tvg-id="NDTVProfit.in@SD",NDTV Profit (1080p)
https://ndtvprofit.akamaized.net/hls/live/index.m3u8
#EXTINF:-1 tvg-id="StarPlus.in@SD",StarPlus HD (1080p)
https://103.151.60.162/star/index.m3u8
#EXTINF:-1 tvg-id="SonyMax.in@SD",Sony Max (576p)
https://mumt03.tangotv.in/sonymax/index.m3u8
#EXTINF:-1 tvg-id="ZeeDilSe.in@SD",Zee Dil Se (1080p)
https://amg00862-amg00862c6-amgplt0173.playout.now3.amagi.tv/playlist.m3u8
#EXTINF:-1 tvg-id="Copied.in@SD",Copied TV (720p)
https://copiedtv.akamaized.net/index.m3u8
#EXTINF:-1 tvg-id="Adult.in@SD",Adult X
https://adultx.example.com/a.m3u8
#EXTINF:-1 tvg-id="Abroad.us@SD",Abroad TV
https://abroadtv.example.com/a.m3u8
#EXTINF:-1 tvg-id="Unknown.in@SD",Unknown News (720p)
https://d1xyz.cloudfront.net/live.m3u8
#EXTINF:-1 tvg-id="NDTVProfit.in@SD",NDTV Profit (480p) [Not 24/7]
http://ndtvprofit.example.com/plain.m3u8
""",
    "in_doordarshan.m3u": """#EXTM3U
#EXTINF:-1 tvg-id="DDSahyadri.in@SD",DD Sahyadri (504p)
https://d3qs3d2rkhfqrt.cloudfront.net/out/v1/sahyadri/index.m3u8
""",
    "in_samsung.m3u": "#EXTM3U\n", "in_distro.m3u": "#EXTM3U\n",
}


def test_only_official_free_streams_are_kept():
    chans = catalog.build(M3U, CHANNELS, BLOCK, LOGOS)
    names = {c["name"] for c in chans}
    assert names == {"DD Sahyadri", "NDTV Profit", "Zee Dil Se", "Abroad TV"}
    # dropped: bare IP pay channel, re-streamer, copyright blocklist, NSFW, unknown CDN, plain http
    by = {c["name"]: c for c in chans}
    assert by["Abroad TV"]["country"] == "US" and by["DD Sahyadri"]["country"] == "IN"
    assert catalog.trusted("us_pluto.m3u") and catalog.trusted("in_doordarshan.m3u") and not catalog.trusted("in.m3u")
    assert by["DD Sahyadri"]["logo_src"] == "https://i.imgur.com/dd.png"
    assert [s["source"] for s in by["NDTV Profit"]["streams"]] == ["broadcaster's own cdn"]
    assert by["Zee Dil Se"]["streams"][0]["source"] == "official free platform"
    assert by["DD Sahyadri"]["streams"][0]["source"] == "prasar bharati / nic"
    ok, why = catalog.official({"url": "https://jtbs.dpdns.org/x.m3u8", "title": "JTBS", "file": "in.m3u"}, {})
    assert not ok and why == "re-streamer / app feed"


def test_shipped_list_and_finding_channels(env):
    data = catalog.load()
    assert len(data["channels"]) >= 4000
    assert catalog.find("marathi")[0]["name"] == "DD Sahyadri"
    assert [c["name"] for c in catalog.find("aaj tak")] == ["Aaj Tak"]       # not "Takeshi's Castle"
    assert catalog.find("dw")[0]["name"] == "DW" and catalog.find("al jazeera")[0]["name"] == "Al Jazeera"
    assert catalog.find("bbc news")[0]["name"] == "BBC News"
    assert catalog.find("news")[0]["country"] == "IN"                          # India first
    countries = catalog.countries()
    assert countries[0]["code"] == "IN" and countries[0]["flag"] and len(countries) >= 100
    de = catalog.search(country="Germany", limit=5)
    assert de["total"] >= 100 and all(c["country"] == "DE" for c in de["channels"])
    assert catalog.search(country="DE", offset=5, limit=5)["channels"][0]["id"] != de["channels"][0]["id"]
    news = catalog.find("news")
    by_id = {c["id"]: c for c in data["channels"]}
    assert news and all("news" in by_id[n["id"]]["categories"] for n in news)
    assert catalog.find("star plus") == []                       # pay channels are not in Hoola TV
    names = {c["name"] for c in data["channels"] if c["country"] == "IN"}
    assert not any(n.startswith(("Star ", "StarPlus", "Sony ", "Colors")) for n in names)
    cats = catalog.categories()
    assert cats[0]["id"] == "news" and cats[0]["label"] == "News"


def _transport(routes):
    def handle(req):
        r = routes.get(str(req.url))
        if r is None:
            return httpx.Response(404)
        body, headers = r
        return httpx.Response(200, text=body, headers=headers)
    return httpx.Client(transport=httpx.MockTransport(handle))


def test_health_marks_working_and_tv_playable():
    chans = catalog.build(M3U, CHANNELS, BLOCK, LOGOS)
    c = _transport({
        "https://d3qs3d2rkhfqrt.cloudfront.net/out/v1/sahyadri/index.m3u8": ("#EXTM3U\n#EXT-X-VERSION:3\n", {"access-control-allow-origin": "*"}),
        "https://ndtvprofit.akamaized.net/hls/live/index.m3u8": ("#EXTM3U\n", {}),
    })
    out = {x["name"]: x for x in catalog.health(chans, client=c, workers=2)}
    assert out["DD Sahyadri"]["streams"][0] == {**out["DD Sahyadri"]["streams"][0], "ok": True, "castable": True}
    assert out["NDTV Profit"]["streams"][0]["ok"] is True and out["NDTV Profit"]["streams"][0]["castable"] is False
    assert out["Zee Dil Se"]["streams"][0]["ok"] is False


def test_refresh_downloads_checks_and_saves(env, monkeypatch, tmp_path):
    monkeypatch.setattr(catalog, "DATA_DIR", tmp_path / "tv")
    monkeypatch.setattr(catalog, "MIN_CHANNELS", 3)
    routes = {f"{catalog.RAW}/iptv/master/streams/{f}": (t, {}) for f, t in M3U.items()}
    routes[catalog.LIST_URL] = (json.dumps([{"name": f} for f in M3U] + [{"name": "README.md"}]), {})
    routes.update({f"{catalog.RAW}/database/master/data/channels.csv": (CHANNELS, {}),
                   f"{catalog.RAW}/database/master/data/blocklist.csv": (BLOCK, {}),
                   f"{catalog.RAW}/database/master/data/logos.csv": (LOGOS, {}),
                   f"{catalog.RAW}/database/master/data/countries.csv": ("name,code,languages,flag\nIndia,IN,hin,F\n", {}),
                   f"{catalog.RAW}/database/master/data/categories.csv": ("id,name,description\nnews,News,x\n", {})})
    r = catalog.refresh(client=_transport(routes), check=False)
    assert r == {"channels": 4, "working": 4}
    saved = json.loads((tmp_path / "tv" / "channels.json").read_text())
    assert {c["name"] for c in saved["channels"]} == {"DD Sahyadri", "NDTV Profit", "Zee Dil Se", "Abroad TV"}
    assert saved["countries"]["IN"]["name"] == "India" and "in_samsung.m3u" in saved["files"]
    # a broken download never replaces a good list
    monkeypatch.setattr(catalog, "MIN_CHANNELS", 100)
    with pytest.raises(RuntimeError):
        catalog.refresh(client=_transport(routes), check=False)
    catalog._cache.update(at=0.0, data=None)


@pytest.fixture()
def tv_app(env, monkeypatch):
    from app.bt import service as bt
    sent = []

    async def fake_run(tenant, conv, action, args=None, wait_s=None):
        sent.append((action, dict(args or {})))
        if action == "cast_play":
            return {"status": "ok", "action": action, "playing": True, "tv_name": "Living Room TV",
                    "say": "The channel is playing on Living Room TV."}
        return {"status": "ok", "action": action, "stopped": True}
    monkeypatch.setattr(bt, "run", fake_run)
    catalog._cache.update(at=0.0, data=None)
    return sent


def test_api_lists_plays_and_casts(tv_app):
    from app import main
    with TestClient(main.app) as c:
        c.post("/api/conversations")
        r = c.get("/api/tv/channels").json()
        assert r["total"] >= 4000 and len(r["channels"]) == 90 and r["categories"] and r["countries"][0]["code"] == "IN"
        more = c.get("/api/tv/channels", params={"offset": 90}).json()
        assert "countries" not in more and more["channels"][0]["id"] != r["channels"][0]["id"]
        us = c.get("/api/tv/channels", params={"country": "US", "category": "news"}).json()
        assert us["channels"] and all(x["country"] == "US" for x in us["channels"])
        r = c.get("/api/tv/channels", params={"country": "IN"}).json()
        dd = next(x for x in r["channels"] if x["name"] == "DD Sahyadri")
        assert dd["logo"] == f"/api/logo/tv/{dd['id']}"
        d = c.get(f"/api/tv/channels/{dd['id']}").json()
        assert d["url"].startswith("https://") and d["name"] == "DD Sahyadri"
        assert c.get("/api/tv/channels/nope").status_code == 404
        cast = c.post("/api/tv/cast", json={"channel": dd["id"]}).json()
        assert cast["playing"] is True and cast["channel"] == "DD Sahyadri"
        assert tv_app[-1][0] == "cast_play" and tv_app[-1][1]["url"] == d["url"] and tv_app[-1][1]["title"] == "DD Sahyadri"
        assert c.post("/api/tv/stop").json()["stopped"] is True


def test_avatar_plays_on_phone_and_tv(tv_app):
    from app.agent.tools import Ctx, ToolError, dispatch
    from app.db import Conversation, DeviceAction, session
    with session() as s:
        conv = Conversation(tenant_id="default")
        s.add(conv)
        s.flush()
        cid = conv.id
    ctx = Ctx("default", cid)
    found = asyncio.run(dispatch("tv_channel", {"action": "find", "query": "bhajan"}, ctx))
    assert found["channels"] and all(ch["category_label"] == "Bhakti" for ch in found["channels"])
    us = asyncio.run(dispatch("tv_channel", {"action": "find", "query": "news", "country": "United States"}, ctx))
    assert us["channels"] and all(ch["country"] == "US" for ch in us["channels"])
    phone = asyncio.run(dispatch("tv_channel", {"action": "play", "query": "DD Sahyadri", "on": "phone"}, ctx))
    assert phone["channel"] == "DD Sahyadri" and phone["sent_to_phone"] is True
    with session() as s:
        a = s.query(DeviceAction).filter_by(conversation_id=cid, type="tv_play").one()
        assert a.payload["name"] == "DD Sahyadri"
    tv = asyncio.run(dispatch("tv_channel", {"action": "play", "query": "aaj tak", "on": "tv"}, ctx))
    assert tv["playing"] is True and tv["channel"] == "Aaj Tak"
    with pytest.raises(ToolError, match="free channel nahi mila"):
        asyncio.run(dispatch("tv_channel", {"action": "play", "query": "star plus", "on": "tv"}, ctx))


def test_cast_requests_are_checked(env):
    from app.bt import service as bt
    with pytest.raises(bt.BtError):
        bt.create("default", "", "cast_play", {"url": "http://plain.example.com/a.m3u8"})
    p = bt.create("default", "", "cast_play", {"url": "https://x.example.com/a.m3u8", "title": "DD <b>News</b>",
                                                "logo": "javascript:alert(1)"})
    assert p["args"] == {"url": "https://x.example.com/a.m3u8", "title": "DD bNews/b"}
    res = bt.clean_result({"tvs": [{"name": "Hall TV‮", "model": "Chromecast"}, "junk"], "playing": 1})
    assert res == {"tvs": [{"name": "Hall TV", "model": "Chromecast"}], "playing": True}


def test_tv_logo_resolves(env):
    from app.bazar import logos
    dd = catalog.find("DD Sahyadri")[0]
    kind, url = logos.resolve("tv", dd["id"])
    assert kind == "url" and url.startswith("https://")
    assert logos.resolve("tv", "nope") is None
