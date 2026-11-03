"""v0.469 Phase 10: solar_check (Solar API Building Insights) + maps_snap (Roads snapToRoads).

Shapes from Google's discovery documents (solar v1 buildingInsights:findClosest, roads v1 snapToRoads). Pinned: the request
shape, a not-covered place is reported and NOT billed, layouts are Google's own numbers, the 100-point ceiling, unsnapped
points are named, billing + refund, and nothing is stored."""
from __future__ import annotations

import asyncio

import httpx
import pytest

from app import maps, mapsbill
from app.config import get_settings


@pytest.fixture
def sr(env, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "k")
    get_settings.cache_clear()
    seen, mode = [], {"solar": 200, "roads": 200}

    def handler(req: httpx.Request):
        seen.append(req)
        if req.url.host == "solar.googleapis.com":
            if mode["solar"] == 404:
                return httpx.Response(404, json={"error": {"status": "NOT_FOUND", "message": "Requested entity was not found."}})
            if mode["solar"] != 200:
                return httpx.Response(mode["solar"], json={"error": {"message": "API not enabled"}})
            return httpx.Response(200, json={
                "imageryQuality": "MEDIUM", "imageryDate": {"year": 2023, "month": 4, "day": 9},
                "solarPotential": {"maxArrayPanelsCount": 40, "maxArrayAreaMeters2": 80.5, "panelCapacityWatts": 400,
                                   "maxSunshineHoursPerYear": 1900.4,
                                   "wholeRoofStats": {"areaMeters2": 120.26},
                                   "solarPanelConfigs": [{"panelsCount": n, "yearlyEnergyDcKwh": n * 600.0}
                                                         for n in range(4, 41, 2)],
                                   "financialAnalyses": [{"monthlyBill": {"units": "100"}}]}})
        if req.url.host == "roads.googleapis.com":
            if mode["roads"] != 200:
                return httpx.Response(mode["roads"], json={"error": {"message": "x"}})
            return httpx.Response(200, json={"snappedPoints": [
                {"location": {"latitude": 20.7001, "longitude": 77.0001}, "originalIndex": 0, "placeId": "A"},
                {"location": {"latitude": 20.7101, "longitude": 77.0101}, "originalIndex": 2, "placeId": "B"}],
                "warningMessage": ""})
        return httpx.Response(404)
    maps.set_client(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    yield {"seen": seen, "mode": mode}
    maps.set_client(None)


def _ctx():
    from app.agent.tools import Ctx
    return Ctx(tenant_id="default", conversation_id="c")


def test_solar_reads_googles_numbers_and_picks_layouts(sr):
    from app.agent import maps_tools
    r = asyncio.run(maps_tools.solar_check(_ctx(), lat=20.7, lng=77.0))
    q = sr["seen"][0]
    assert q.url.path == "/v1/buildingInsights:findClosest" and "location.latitude=20.7" in str(q.url)
    assert q.headers["x-goog-api-key"] == "k" and "key=" not in str(q.url)
    assert r["covered"] and r["max_panels"] == 40 and r["roof_area_m2"] == 120.3 and r["imagery_date"] == "2023-4-9"
    assert [x["panels"] for x in r["layouts"]] == [10, 20, 40]
    assert r["layouts"][2]["yearly_dc_kwh"] == 24000, "Google's own figure, untouched"
    assert "financial" not in str(r).lower() and "DC" in r["note"], "no invented or US-based money numbers"
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_SOLAR) == "1"


def test_a_place_google_has_no_roof_data_for_is_not_covered_and_not_billed(sr):
    from app.agent import maps_tools
    sr["mode"]["solar"] = 404
    r = asyncio.run(maps_tools.solar_check(_ctx(), lat=20.7, lng=77.0))
    assert r["covered"] is False and "nahi hai" in r["message"]
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_SOLAR) in (None, "0")


def test_a_failed_solar_call_is_refunded_and_explained(sr):
    from app.agent import maps_tools
    from app.agent.tools import ToolError
    sr["mode"]["solar"] = 403
    with pytest.raises(ToolError):
        asyncio.run(maps_tools.solar_check(_ctx(), lat=20.7, lng=77.0))
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_SOLAR) in (None, "0")


def test_snap_request_shape_distance_and_unsnapped_points(sr):
    from app.agent import maps_tools
    pts = [{"lat": 20.7, "lng": 77.0}, "20.705,77.005", {"latitude": 20.71, "longitude": 77.01}]
    r = asyncio.run(maps_tools.maps_snap(_ctx(), pts))
    q = sr["seen"][0]
    assert q.url.path == "/v1/snapToRoads" and "path=20.7%2C77.0%7C20.705%2C77.005%7C20.71%2C77.01" in str(q.url)
    assert "travelMode=DRIVING" in str(q.url) and "interpolate=false" in str(q.url)
    assert r["not_snapped"] == [1], "point 1 had no snapped equivalent and is named, not invented"
    assert 1.0 < r["snapped_km"] < 2.0
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_ROADS) == "1"


def test_snap_refuses_more_than_100_points_and_bad_points_before_any_call(sr):
    from app.agent import maps_tools
    from app.agent.tools import ToolError
    with pytest.raises(ToolError):
        asyncio.run(maps_tools.maps_snap(_ctx(), [{"lat": 20.0, "lng": 77.0}] * 101))
    with pytest.raises(ToolError):
        asyncio.run(maps_tools.maps_snap(_ctx(), [{"lat": 95, "lng": 77.0}]))
    with pytest.raises(ToolError):
        asyncio.run(maps_tools.maps_snap(_ctx(), ["not a point"]))
    assert not sr["seen"]


def test_a_failed_snap_is_refunded(sr):
    from app.agent import maps_tools
    from app.agent.tools import ToolError
    sr["mode"]["roads"] = 403
    with pytest.raises(ToolError):
        asyncio.run(maps_tools.maps_snap(_ctx(), [{"lat": 20.7, "lng": 77.0}]))
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_ROADS) in (None, "0")


def test_prices_are_the_sourced_india_list_and_guesses_are_reported(env):
    assert mapsbill._INDIA[mapsbill.SKU_SOLAR] == 4.00 and mapsbill._GLOBAL[mapsbill.SKU_SOLAR] == 10.00
    assert mapsbill._INDIA[mapsbill.SKU_ROADS] == 3.00 and mapsbill._FREE_INDIA[mapsbill.SKU_ROADS] == 35000
    assert mapsbill.SKU_ROADS in mapsbill.ASSUMED_TIER


def test_registered_and_nothing_is_stored(env):
    from app.agent.tools import TOOLS, HANDLERS
    for n in ("solar_check", "maps_snap"):
        assert n in {t["name"] for t in TOOLS} and n in HANDLERS
    import inspect
    assert "session(" not in inspect.getsource(maps.solar_building) + inspect.getsource(maps.snap_to_roads)
