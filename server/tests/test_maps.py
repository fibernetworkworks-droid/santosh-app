"""Google Maps: places, directions with traffic, geocoding for cabs, phone location, navigation cards."""
import asyncio
import json

import httpx
import pytest
from sqlalchemy import select


@pytest.fixture
def mp(env, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-maps-key")
    from app.config import get_settings
    get_settings.cache_clear()
    from app import maps
    seen = []

    def handler(req: httpx.Request):
        seen.append(req)
        assert req.headers.get("x-goog-api-key") == "test-maps-key" or req.url.params.get("key") == "test-maps-key"
        if req.url.path == "/v1/places:searchText":
            body = json.loads(req.content)
            assert "X-Goog-FieldMask" in req.headers or "x-goog-fieldmask" in req.headers
            if "station" in body["textQuery"].lower():
                return httpx.Response(200, json={"places": [{"displayName": {"text": "Akola Railway Station"},
                                                             "formattedAddress": "Station Rd, Akola", "location": {"latitude": 20.7096, "longitude": 77.0024}}]})
            return httpx.Response(200, json={"places": [
                {"displayName": {"text": "Sai Medical"}, "formattedAddress": "Tilak Rd, Akola", "location": {"latitude": 20.705, "longitude": 77.01},
                 "rating": 4.4, "userRatingCount": 120, "currentOpeningHours": {"openNow": True}, "nationalPhoneNumber": "0724 243 0000",
                 "googleMapsUri": "https://maps.google.com/?cid=1"}]})
        if req.url.path == "/directions/v2:computeRoutes":
            body = json.loads(req.content)
            assert body["routingPreference"] == "TRAFFIC_AWARE"
            return httpx.Response(200, json={"routes": [{"duration": "1500s", "staticDuration": "900s", "distanceMeters": 6400,
                                                         "description": "via NH53", "legs": [{"steps": [
                                                             {"navigationInstruction": {"instructions": "Head north on Tilak Rd"}}]}]}]})
        return httpx.Response(404)

    maps.set_client(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default"); s.add(c); s.flush(); conv = c.id
    maps.save_location("default", 20.7002, 77.0082, 15)
    yield {"maps": maps, "conv": conv, "seen": seen}
    maps.set_client(None)


def _ctx(conv):
    from app.agent.tools import Ctx
    return Ctx(tenant_id="default", conversation_id=conv)


def _events(conv, kind):
    from app.db import Event, session
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == kind)).all()]


def test_near_me_search_uses_phone_location(mp):
    from app.agent.tools import dispatch
    out = asyncio.run(dispatch("maps_search", {"query": "medical store", "open_now": True}, _ctx(mp["conv"])))
    p = out["places"][0]
    assert p["name"] == "Sai Medical" and p["open_now"] is True and p["distance_km"] < 2
    body = json.loads(mp["seen"][0].content)
    assert body["locationBias"]["circle"]["center"] == {"latitude": 20.7002, "longitude": 77.0082} and body["regionCode"] == "IN"


def test_directions_with_traffic_and_nav_button(mp):
    from app.agent.tools import dispatch
    out = asyncio.run(dispatch("maps_directions", {"destination": "Akola railway station"}, _ctx(mp["conv"])))
    assert out["distance_km"] == 6.4 and out["duration"] == "25 min" and "Traffic" in out["traffic"]
    card = _events(mp["conv"], "bazar_open")[-1]
    assert card["package"] == "com.google.android.apps.maps"
    assert card["url"].startswith("https://www.google.com/maps/dir/?api=1&destination=20.7096%2C77.0024")


def test_uber_gets_exact_coordinates_and_phone_pickup(mp):
    from app.agent.tools import dispatch
    from app.bazar import config as bzc
    bzc.reset_settings()
    out = asyncio.run(dispatch("bazar_run", {"pack_id": "uber-india", "tool": "ride_link",
                                             "args": {"drop": "Akola railway station"}}, _ctx(mp["conv"])))
    assert "pickup[latitude]=20.7002" in out["deep_link"] and "dropoff[latitude]=20.7096" in out["deep_link"]


def test_without_key_still_sends_navigation(env, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.agent.tools import ToolError, dispatch
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default"); s.add(c); s.flush(); conv = c.id
    out = asyncio.run(dispatch("maps_navigate", {"destination": "Shegaon temple"}, _ctx(conv)))
    assert out["link"].startswith("https://www.google.com/maps/dir/?api=1&destination=Shegaon%20temple")
    with pytest.raises(ToolError, match="search link"):
        asyncio.run(dispatch("maps_search", {"query": "petrol pump"}, _ctx(conv)))


def test_location_api(mp):
    from fastapi.testclient import TestClient
    from app import main
    c = TestClient(main.app)
    assert c.put("/api/location", json={"lat": 18.52, "lng": 73.85, "accuracy_m": 20}).status_code == 200
    assert mp["maps"].where_am_i("default")["lat"] == 18.52
    assert c.put("/api/location", json={"lat": 200, "lng": 0}).status_code == 422
