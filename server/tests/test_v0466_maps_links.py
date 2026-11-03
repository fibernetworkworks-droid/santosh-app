"""v0.466 Phase 7 KAAGAZ PAR - links, not pictures.

The plan's first form (a Static Maps picture saved into a PDF / sent on WhatsApp) breaches ToS 3.2.3(a)/(b); see
docs/research/maps/05_static_maps_licence.md. Pinned here: the tool never fetches or stores an image, offers a Street View
link only when the free metadata call says a panorama exists, and costs nothing."""
from __future__ import annotations

import asyncio
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app import maps, mapsbill
from app.config import get_settings


@pytest.fixture
def lk(env, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "k")
    get_settings.cache_clear()
    seen, mode = [], {"sv": "OK", "fail": False}

    def handler(req: httpx.Request):
        seen.append(req)
        if "streetview/metadata" in req.url.path:
            if mode["fail"]:
                return httpx.Response(403, json={"error_message": "not enabled"})
            if mode["sv"] == "OK":
                return httpx.Response(200, json={"status": "OK", "pano_id": "PANO123", "date": "2023-05"})
            return httpx.Response(200, json={"status": mode["sv"]})
        if req.url.path == "/v1/places:searchText":
            return httpx.Response(200, json={"places": [{"id": "P1", "displayName": {"text": "Akola Station"},
                                                         "formattedAddress": "Akola", "location": {"latitude": 20.71, "longitude": 77.0}}]})
        return httpx.Response(404)
    maps.set_client(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default"); s.add(c); s.flush(); conv = c.id
    maps.save_location("default", 20.7, 77.0, 15)
    yield {"seen": seen, "mode": mode, "conv": conv}
    maps.set_client(None)


def _run(lk, **kw):
    from app.agent import maps_tools
    from app.agent.tools import Ctx
    return asyncio.run(maps_tools.maps_links(Ctx(tenant_id="default", conversation_id=lk["conv"]), **kw))


def test_links_are_googles_own_documented_url_scheme():
    v = urlparse(maps.view_link(20.71, 77.0, place_id="P1", name="Akola Station"))
    q = parse_qs(v.query)
    assert v.netloc == "www.google.com" and q["api"] == ["1"] and q["query_place_id"] == ["P1"] and q["query"] == ["Akola Station"]
    s = parse_qs(urlparse(maps.streetview_link(20.71, 77.0, "PANO123")).query)
    assert s["map_action"] == ["pano"] and s["viewpoint"] == ["20.71,77.0"] and s["pano"] == ["PANO123"]


def test_a_place_gets_a_view_link_and_a_streetview_link_when_a_panorama_exists(lk):
    r = _run(lk, place="Akola Station")
    assert "google.com/maps/search" in r["view"] and "pano" in r["streetview"] and "PANO123" in r["streetview"]
    assert r["streetview_date"] == "2023-05"


def test_no_panorama_means_no_streetview_link_and_it_says_so(lk):
    lk["mode"]["sv"] = "ZERO_RESULTS"
    r = _run(lk, lat=20.71, lng=77.0)
    assert r["streetview"] is None and "nahi hai" in r["streetview_note"]


def test_the_streetview_check_is_free_and_no_image_is_ever_fetched(lk):
    _run(lk, lat=20.71, lng=77.0, directions=True)
    assert mapsbill.usage("default")["inr"] == 0
    for q in lk["seen"]:
        assert "staticmap" not in q.url.path and not q.url.path.endswith("/streetview"), "an image request would be a licence breach"


def test_a_failed_streetview_check_does_not_lose_the_view_link(lk):
    lk["mode"]["fail"] = True
    r = _run(lk, lat=20.71, lng=77.0)
    assert r["view"] and r["streetview"] is None and "nahi dekh paya" in r["streetview_note"]


def test_directions_link_and_bad_input(lk):
    from app.agent.tools import ToolError
    r = _run(lk, lat=20.71, lng=77.0, directions=True)
    assert "dir" in r["directions"]
    with pytest.raises(ToolError):
        _run(lk)
    with pytest.raises(ToolError):
        _run(lk, lat=95, lng=77.0)


def test_without_a_maps_key_the_search_link_still_works(env, monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    get_settings.cache_clear()
    from app.agent import maps_tools
    from app.agent.tools import Ctx
    r = asyncio.run(maps_tools.maps_links(Ctx(tenant_id="default", conversation_id="c"), place="Akola Station"))
    assert "google.com/maps/search" in r["view"] and r["streetview"] is None


def test_the_tool_is_registered(env):
    from app.agent.tools import TOOLS, HANDLERS
    assert "maps_links" in {t["name"] for t in TOOLS} and "maps_links" in HANDLERS
