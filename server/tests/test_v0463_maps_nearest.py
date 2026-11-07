"""v0.463 Phase 4 SABSE PAAS - computeRouteMatrix and "nearest of these N".

What is worth pinning: (1) the matrix is billed PER ELEMENT and the cap refuses it BEFORE the call, (2) a pair
Google cannot route is reported unreachable, never guessed, (3) a failed call is refunded, (4) a big list is
shortlisted by straight line instead of billing every pair, (5) coordinates the caller already has cost no lookup.
"""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app import mapsbill
from app.config import get_settings


@pytest.fixture
def mx(env, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-maps-key")
    get_settings.cache_clear()
    from app import maps
    seen, mode = [], {"fail": False}

    def handler(req: httpx.Request):
        seen.append(req)
        if req.url.path == "/distanceMatrix/v2:computeRouteMatrix":
            if mode["fail"]:
                return httpx.Response(403, json={"error": {"message": "API not enabled"}})
            b = json.loads(req.content)
            out = []
            for i in range(len(b["origins"])):
                for j, d in enumerate(b["destinations"]):
                    ll = d["waypoint"]["location"]["latLng"]
                    if ll["latitude"] == 0.5:      # a pair with no road
                        out.append({"originIndex": i, "destinationIndex": j, "status": {"code": 5},
                                    "condition": "ROUTE_NOT_FOUND"})
                        continue
                    km = abs(ll["latitude"] - 20.0) * 100
                    out.append({"originIndex": i, "destinationIndex": j, "status": {}, "condition": "ROUTE_EXISTS",
                                "distanceMeters": int(km * 1000), "duration": f"{int(km * 60)}s"})
            return httpx.Response(200, json=out[::-1])       # order is not guaranteed: indexes must be used
        if req.url.path == "/v1/places:searchText":
            q = json.loads(req.content)["textQuery"]
            lat = {"Godown A": 20.30, "Godown B": 20.10}.get(q)
            if lat is None:
                return httpx.Response(200, json={})
            return httpx.Response(200, json={"places": [{"id": "P" + q[-1], "displayName": {"text": q},
                                                         "formattedAddress": q + ", Akola",
                                                         "location": {"latitude": lat, "longitude": 77.0}}]})
        return httpx.Response(404)

    maps.set_client(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default"); s.add(c); s.flush(); conv = c.id
    maps.save_location("default", 20.0, 77.0, 15)
    yield {"maps": maps, "conv": conv, "seen": seen, "mode": mode}
    maps.set_client(None)


def _ctx(conv):
    from app.agent.tools import Ctx
    return Ctx(tenant_id="default", conversation_id=conv)


def _pts(*lats):
    return [{"name": f"P{l}", "lat": l, "lng": 77.0} for l in lats]


def _run(mx, cands, **kw):
    from app.agent import maps_tools
    return asyncio.run(maps_tools.maps_nearest(_ctx(mx["conv"]), cands, **kw))


def _matrix_calls(mx):
    return [q for q in mx["seen"] if "computeRouteMatrix" in q.url.path]


def test_nearest_is_ranked_by_road_time_and_matches_by_index_not_order(mx):
    r = _run(mx, _pts(20.3, 20.1, 20.2))
    assert [x["name"] for x in r["results"][0]["ranked"]] == ["P20.1", "P20.2", "P20.3"]
    assert r["results"][0]["nearest"]["name"] == "P20.1"
    assert r["results"][0]["nearest"]["distance_km"] == 10.0


def test_the_matrix_is_billed_per_element_not_per_request(mx):
    _run(mx, _pts(20.1, 20.2, 20.3, 20.4))          # 1 origin x 4 destinations
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_MATRIX) == "4"
    assert len(_matrix_calls(mx)) == 1


def test_coordinates_she_already_has_cost_no_lookup(mx):
    _run(mx, _pts(20.1, 20.2))
    assert not [q for q in mx["seen"] if q.url.path == "/v1/places:searchText"]


def test_a_plain_name_is_located_first(mx):
    r = _run(mx, ["Godown A", "Godown B"])
    assert r["results"][0]["nearest"]["name"] == "Godown B"


def test_a_pair_with_no_road_is_unreachable_not_guessed(mx):
    r = _run(mx, _pts(0.5, 20.1))
    row = r["results"][0]
    assert row["unreachable"] == ["P0.5"]
    assert [x["name"] for x in row["ranked"]] == ["P20.1"]


def test_a_cap_refuses_the_matrix_before_any_call(mx, monkeypatch):
    from app.agent.tools import ToolError
    monkeypatch.setenv("MAPS_DAILY_INR", "0.01")
    get_settings.cache_clear()
    monkeypatch.setitem(mapsbill._FREE_INDIA, mapsbill.SKU_MATRIX, 0)
    with pytest.raises(ToolError):
        _run(mx, _pts(20.1, 20.2, 20.3))
    assert not _matrix_calls(mx), "the refusal must come BEFORE the HTTP call"


def test_a_failed_call_is_refunded(mx):
    from app.agent.tools import ToolError
    mx["mode"]["fail"] = True
    with pytest.raises(ToolError):
        _run(mx, _pts(20.1, 20.2))
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_MATRIX) in (None, "0")


def test_a_long_list_from_one_origin_is_shortlisted_by_straight_line(mx, monkeypatch):
    monkeypatch.setenv("MAPS_MATRIX_MAX", "3")
    get_settings.cache_clear()
    r = _run(mx, _pts(20.9, 20.5, 20.1, 20.3, 20.7))
    assert r["compared"] == 3 and "prefiltered" in r
    assert [x["name"] for x in r["results"][0]["ranked"]] == ["P20.1", "P20.3", "P20.5"]
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_MATRIX) == "3"


def test_many_origins_over_the_limit_is_refused_not_trimmed(mx, monkeypatch):
    from app.agent.tools import ToolError
    monkeypatch.setenv("MAPS_MATRIX_MAX", "4")
    get_settings.cache_clear()
    with pytest.raises(ToolError):
        _run(mx, _pts(20.1, 20.2, 20.3), origins=_pts(20.0, 20.05))
    assert not _matrix_calls(mx)


def test_the_request_asks_only_for_the_fields_it_needs_and_draws_a_card(mx):
    _run(mx, _pts(20.1, 20.2))
    mask = _matrix_calls(mx)[0].headers["x-goog-fieldmask"]
    assert "duration" in mask and "distanceMeters" in mask and "polyline" not in mask
    from app.db import Event, session
    from sqlalchemy import select
    with session() as s:
        cards = [e.payload for e in s.scalars(select(Event).where(
            Event.conversation_id == mx["conv"], Event.kind == "maps_places")).all()]
    assert len(cards) == 1 and cards[0]["attribution"] == "Google"


def test_the_tool_is_registered_and_reachable_on_a_call(env):
    from app.agent.tools import TOOLS, HANDLERS
    assert "maps_nearest" in {t["name"] for t in TOOLS} and "maps_nearest" in HANDLERS
    from app import voice
    assert "maps_nearest" in voice.VOICE_TOOL_NAMES
