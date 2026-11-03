"""v0.465 Phase 5 DIN KA RASTA - Route Optimization.

Field names / auth come from Google's own proto (googleapis/googleapis), not memory: JSON durations are "300s",
timestamps RFC 3339, int64 a string, LatLng {latitude, longitude}; proto3 omits zero ints (so a missing
shipmentIndex / vehicleIndex means 0); the service's only scope is cloud-platform, so it is OAuth + a project id.
Pinned here: the request shape, parsing incl. the omitted-zero trap, skipped stops reported with their reason,
billing per shipment BEFORE the call with a refund on failure, a missing credential costs nothing."""
from __future__ import annotations

import asyncio
import json
from datetime import date

import httpx
import pytest

from app import maps, mapsbill, mapsopt
from app.config import get_settings

DAY = date(2026, 11, 4)
STOPS = [{"name": "Sai Medical", "lat": 20.70, "lng": 77.00, "service_min": 5, "window": "10:00-12:00", "load": 3},
         {"name": "Jan Aushadhi", "lat": 20.75, "lng": 77.05},
         {"name": "Far Clinic", "lat": 21.50, "lng": 78.00}]
VEH = [{"name": "MH30-1", "start": {"lat": 20.72, "lng": 77.02}, "capacity": 10, "from": "09:00", "until": "18:00"}]


def test_request_shape_follows_the_proto_json_mapping():
    r = mapsopt.build_request(STOPS, VEH, DAY)
    m = r["model"]
    s0 = m["shipments"][0]["deliveries"][0]
    assert s0["arrivalLocation"] == {"latitude": 20.70, "longitude": 77.00}
    assert s0["duration"] == "300s"
    # 10:00 and 12:00 IST on 4 Nov = 04:30Z and 06:30Z
    assert s0["timeWindows"] == [{"startTime": "2026-11-04T04:30:00Z", "endTime": "2026-11-04T06:30:00Z"}]
    assert m["shipments"][0]["loadDemands"] == {"units": {"amount": "3"}}, "int64 is a JSON string"
    v = m["vehicles"][0]
    assert v["loadLimits"] == {"units": {"maxLoad": "10"}} and v["travelMode"] == "DRIVING"
    assert v["endLocation"] == v["startLocation"], "default: back where it started"
    assert v["startTimeWindows"] == [{"startTime": "2026-11-04T03:30:00Z"}]
    assert v["endTimeWindows"] == [{"endTime": "2026-11-04T12:30:00Z"}]
    assert m["globalStartTime"] == "2026-11-03T18:30:00Z" and m["globalEndTime"] == "2026-11-04T18:30:00Z"
    assert r["considerRoadTraffic"] is True
    for sh in m["shipments"]:
        assert "penaltyCost" not in sh, "no penalty = mandatory (proto: unspecified penalty is infinite)"


def test_bad_inputs_are_refused_before_any_call():
    with pytest.raises(mapsopt.OptError):
        mapsopt.build_request([], VEH, DAY)
    with pytest.raises(mapsopt.OptError):
        mapsopt.build_request([{**STOPS[0], "window": "10-12"}], VEH, DAY)


RESP = {"routes": [{
    # vehicleIndex omitted = 0; the first visit's shipmentIndex omitted = 0 (proto3 drops zeros)
    "vehicleStartTime": "2026-11-04T03:30:00Z", "vehicleEndTime": "2026-11-04T05:10:00Z",
    "visits": [{"startTime": "2026-11-04T04:30:00Z"}, {"shipmentIndex": 1, "startTime": "2026-11-04T04:50:00Z"}],
    "transitions": [{"travelDuration": "900s", "travelDistanceMeters": 4200},
                    {"travelDuration": "600s", "travelDistanceMeters": 3100},
                    {"travelDuration": "420s", "travelDistanceMeters": 2500}],
    "metrics": {"travelDistanceMeters": 9800, "travelDuration": "1920s"}}],
    "skippedShipments": [{"index": 2, "reasons": [{"code": "CANNOT_BE_PERFORMED_WITHIN_VEHICLE_DURATION_LIMIT"}]}]}


def test_parse_reads_zero_omitted_indexes_and_local_times():
    p = mapsopt.parse_response(RESP, STOPS, VEH)
    r = p["routes"][0]
    assert r["vehicle"] == "MH30-1" and [s["stop"] for s in r["stops"]] == ["Sai Medical", "Jan Aushadhi"]
    assert r["stops"][0]["arrive"] == "10:00" and r["stops"][1]["arrive"] == "10:20"
    assert r["stops"][0]["leg_km"] == 4.2 and r["stops"][0]["leg_min"] == 15
    assert r["back_km"] == 2.5 and r["back_min"] == 7
    assert r["total_km"] == 9.8 and r["drive_min"] == 32
    assert p["complete"] is True and p["placed"] == 2 and p["submitted"] == 3


def test_a_skipped_stop_is_reported_with_googles_reason_never_dropped():
    p = mapsopt.parse_response(RESP, STOPS, VEH)
    assert p["skipped"] == [{"stop": "Far Clinic", "why": ["gaadi ke kaam ke samay mein nahi aata"]}]


def test_an_unknown_reason_code_is_passed_through_and_a_missing_stop_flags_incomplete():
    r = {"routes": [], "skippedShipments": [{"index": 0, "reasons": [{"code": "SOMETHING_NEW"}]}]}
    p = mapsopt.parse_response(r, STOPS, VEH)
    assert p["skipped"][0]["why"] == ["SOMETHING_NEW"]
    assert p["complete"] is False, "3 submitted, 1 accounted for - must not read as a full plan"


@pytest.fixture
def ro(env, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "k")
    monkeypatch.setenv("ROUTE_OPT_PROJECT", "my-proj")
    monkeypatch.setenv("ROUTE_OPT_SA_FILE", "/nonexistent/sa.json")
    get_settings.cache_clear()
    monkeypatch.setattr(mapsopt, "_token", lambda: "TOKEN123")
    seen, mode = [], {"status": 200}

    def handler(req: httpx.Request):
        seen.append(req)
        if "optimizeTours" in req.url.path:
            return httpx.Response(mode["status"], json=RESP if mode["status"] == 200 else {"error": {"message": "denied"}})
        if req.url.path == "/v1/places:searchText":
            q = json.loads(req.content)["textQuery"]
            return httpx.Response(200, json={"places": [{"id": "P", "displayName": {"text": q}, "formattedAddress": q,
                                                         "location": {"latitude": 20.7, "longitude": 77.0}}]})
        return httpx.Response(404)
    maps.set_client(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default"); s.add(c); s.flush(); conv = c.id
    maps.save_location("default", 20.72, 77.02, 15)
    yield {"seen": seen, "mode": mode, "conv": conv}
    maps.set_client(None)
    mapsopt.reset()


def _ctx(conv):
    from app.agent.tools import Ctx
    return Ctx(tenant_id="default", conversation_id=conv)


def _plan(ro, stops=None, **kw):
    from app.agent import maps_tools
    return asyncio.run(maps_tools.maps_route_plan(_ctx(ro["conv"]), stops or STOPS, **kw))


def _calls(ro):
    return [q for q in ro["seen"] if "optimizeTours" in q.url.path]


def test_end_to_end_uses_oauth_and_the_project_in_the_path_not_the_maps_key(ro):
    r = _plan(ro)
    q = _calls(ro)[0]
    assert q.url.path == "/v1/projects/my-proj:optimizeTours"
    assert q.headers["authorization"] == "Bearer TOKEN123" and "x-goog-api-key" not in q.headers and "key=" not in str(q.url)
    assert r["routes"][0]["stops"][0]["stop"] == "Sai Medical" and r["skipped"][0]["stop"] == "Far Clinic"
    assert "PROPOSED" in r["note"]


def test_it_is_billed_per_shipment_before_the_call(ro):
    _plan(ro)
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_OPT) == "3"
    assert mapsbill.SKU_OPT in mapsbill.ASSUMED_TIER, "unit + tier are a guess and must be reported as one"


def test_a_denied_call_is_refunded_and_explained(ro):
    from app.agent.tools import ToolError
    ro["mode"]["status"] = 403
    with pytest.raises(ToolError) as e:
        _plan(ro)
    assert "enable" in str(e.value)
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_OPT) in (None, "0")


def test_a_cap_refuses_before_any_call(ro, monkeypatch):
    from app.agent.tools import ToolError
    monkeypatch.setenv("MAPS_DAILY_INR", "0.0001")
    get_settings.cache_clear()
    monkeypatch.setitem(mapsbill._FREE_INDIA, mapsbill.SKU_OPT, 0)
    with pytest.raises(ToolError):
        _plan(ro)
    assert not _calls(ro)


def test_too_many_stops_is_refused_not_trimmed(ro, monkeypatch):
    from app.agent.tools import ToolError
    monkeypatch.setenv("MAPS_OPT_MAX_STOPS", "2")
    get_settings.cache_clear()
    with pytest.raises(ToolError):
        _plan(ro)
    assert not _calls(ro)


def test_missing_credentials_say_what_is_needed_and_cost_nothing(env, monkeypatch):
    from app.agent import maps_tools
    from app.agent.tools import Ctx, ToolError
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "k")
    monkeypatch.delenv("ROUTE_OPT_PROJECT", raising=False)
    monkeypatch.delenv("ROUTE_OPT_SA_FILE", raising=False)
    get_settings.cache_clear()
    with pytest.raises(ToolError) as e:
        asyncio.run(maps_tools.maps_route_plan(Ctx(tenant_id="default", conversation_id="c"), STOPS))
    assert "ROUTE_OPT_PROJECT" in str(e.value) and "nahi chalti" in str(e.value)
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_OPT) in (None, "0")


def test_a_card_is_drawn_and_the_tool_is_reachable_on_a_call(ro):
    _plan(ro)
    from app.db import Event, session
    from sqlalchemy import select
    with session() as s:
        cards = [e.payload for e in s.scalars(select(Event).where(Event.conversation_id == ro["conv"], Event.kind == "maps_places")).all()]
    assert len(cards) == 1 and cards[0]["title"].startswith("Din ka rasta") and cards[0]["attribution"] == "Google"
    from app import voice
    from app.agent.tools import TOOLS, HANDLERS
    assert "maps_route_plan" in {t["name"] for t in TOOLS} and "maps_route_plan" in HANDLERS and "maps_route_plan" in voice.VOICE_TOOL_NAMES
