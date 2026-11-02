"""v0.449 PAISA PEHLE + NAKSHA DIKHE + PAAS KYA HAI.

Three things are worth a test here and only one of them is ordinary:

1. THE CAP MUST NEVER OVERSPEND, and a refusal must still be VISIBLE afterwards. The first version of
   charge() raised inside the session that recorded the refusal, so the increment was rolled back with the
   exception and `refused` always read 0 - a cap that worked but could not be seen working.
2. THE CACHE MUST NOT GROW A GOOGLE-CONTENT COLUMN. Storing a business name or phone would be a licence
   breach (ToS 3.2.3(b): no caching except as expressly permitted; the Places SST permits place_id and
   lat/lng and nothing else). A test is the only thing that stops a future session "optimising" that in.
3. THE BILLING UNIT. Google bills Places PER REQUEST, not per returned place, except computeRouteMatrix which
   bills per element. Getting this backwards would overstate a search ~20x or understate a matrix 100x.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app import db, mapsbill
from app.config import get_settings


# ---------------------------------------------------------------- the price list
def test_india_price_list_is_the_default_and_is_cheaper(env):
    s = get_settings()
    assert s.maps_price_list == "india"
    assert mapsbill._india()
    # Google publishes a separate, cheaper India list in USD. Using the global numbers for Indian traffic
    # overstates the bill ~3x, which is why this is pinned.
    assert mapsbill._INDIA[mapsbill.SKU_TEXT_ENT] == 10.50
    assert mapsbill._GLOBAL[mapsbill.SKU_TEXT_ENT] == 35.00
    assert mapsbill._INDIA[mapsbill.SKU_TEXT_PRO] == 9.60
    assert mapsbill._INDIA[mapsbill.SKU_NEARBY_PRO] == 9.60
    assert mapsbill._INDIA[mapsbill.SKU_DETAILS_ENT] == 6.00
    # the free caps are 7x the global ones on the India list
    assert mapsbill._FREE_INDIA[mapsbill.SKU_TEXT_ENT] == 7000
    assert mapsbill._FREE_GLOBAL[mapsbill.SKU_TEXT_ENT] == 1000


def test_free_skus_cost_nothing_however_often(env):
    for sku in (mapsbill.SKU_TEXT_IDS, mapsbill.SKU_DETAILS_IDS, mapsbill.SKU_DETAILS_REFRESH):
        assert mapsbill.rate_usd(sku) == 0.0
        assert mapsbill.free_left(sku) == mapsbill.UNLIMITED
        assert mapsbill.charge("t", sku, 10_000).inr == 0.0


def test_an_unpriced_sku_is_charged_at_the_dearest_known_rate(env):
    """An unknown price must make the cap fire EARLY, never late."""
    assert mapsbill.rate_usd("something.we.never.priced") == max(v for v in mapsbill.RATES().values() if v)


# ---------------------------------------------------------------- free allowance
def test_calls_inside_the_free_allowance_cost_her_nothing(env, monkeypatch):
    monkeypatch.setitem(mapsbill._FREE_INDIA, mapsbill.SKU_TEXT_ENT, 2)
    assert mapsbill.quote_inr(mapsbill.SKU_TEXT_ENT) == 0.0
    assert mapsbill.charge("t1", mapsbill.SKU_TEXT_ENT).inr == 0.0
    assert mapsbill.charge("t1", mapsbill.SKU_TEXT_ENT).inr == 0.0
    assert mapsbill.free_left(mapsbill.SKU_TEXT_ENT) == 0
    paid = mapsbill.charge("t1", mapsbill.SKU_TEXT_ENT).inr
    assert paid == pytest.approx(10.50 / 1000 * get_settings().maps_usd_inr)
    u = mapsbill.usage("t1")
    assert u["calls"] == 3 and u["free_calls"] == 2


def test_the_free_allowance_is_shared_across_tenants(env, monkeypatch):
    """It belongs to the BILLING ACCOUNT, not to a person: "Google aggregates service usage for all projects
    linked to the customer billing account". A per-tenant counter would hand the same free calls out many
    times and the real bill would arrive anyway."""
    monkeypatch.setitem(mapsbill._FREE_INDIA, mapsbill.SKU_GEOCODE, 1)
    assert mapsbill.charge("alice", mapsbill.SKU_GEOCODE).inr == 0.0
    assert mapsbill.charge("bob", mapsbill.SKU_GEOCODE).inr > 0.0, "bob must not get alice's free call again"


# ---------------------------------------------------------------- the cap
def test_the_cap_refuses_and_never_overspends(env, monkeypatch):
    monkeypatch.setitem(mapsbill._FREE_INDIA, mapsbill.SKU_TEXT_ENT, 0)
    monkeypatch.setattr(get_settings(), "maps_daily_inr", 2.0, raising=False)
    spent = 0.0
    with pytest.raises(mapsbill.MapsCapped):
        for _ in range(500):
            spent += mapsbill.charge("t2", mapsbill.SKU_TEXT_ENT).inr
    u = mapsbill.usage("t2")
    assert u["inr"] <= u["cap_inr"], "the cap was crossed"
    assert u["inr"] == pytest.approx(spent)


def test_a_refusal_survives_the_exception_and_is_visible(env, monkeypatch):
    """The bug this test exists for: raising inside the recording session rolled the counter back, so a cap
    that was working looked like a cap that had never fired."""
    monkeypatch.setitem(mapsbill._FREE_INDIA, mapsbill.SKU_TEXT_ENT, 0)
    monkeypatch.setattr(get_settings(), "maps_daily_inr", 0.0001, raising=False)
    with pytest.raises(mapsbill.MapsCapped):
        mapsbill.charge("t3", mapsbill.SKU_TEXT_ENT)
    assert mapsbill.usage("t3")["refused"] == 1


def test_a_refused_call_does_not_eat_the_free_allowance(env, monkeypatch):
    monkeypatch.setitem(mapsbill._FREE_INDIA, mapsbill.SKU_TEXT_ENT, 0)
    monkeypatch.setattr(get_settings(), "maps_daily_inr", 0.0001, raising=False)
    monkeypatch.setitem(mapsbill._FREE_INDIA, mapsbill.SKU_GEOCODE, 5)
    with pytest.raises(mapsbill.MapsCapped):
        mapsbill.charge("t4", mapsbill.SKU_TEXT_ENT)
    assert mapsbill.free_left(mapsbill.SKU_GEOCODE) == 5


def test_cap_of_zero_means_no_ceiling(env, monkeypatch):
    monkeypatch.setitem(mapsbill._FREE_INDIA, mapsbill.SKU_TEXT_ENT, 0)
    monkeypatch.setattr(get_settings(), "maps_daily_inr", 0.0, raising=False)
    for _ in range(50):
        mapsbill.charge("t5", mapsbill.SKU_TEXT_ENT)
    assert mapsbill.usage("t5")["refused"] == 0


# ---------------------------------------------------------------- the billing unit
def test_places_bills_per_request_and_the_matrix_per_element(env, monkeypatch):
    """Each Places SKU's billable event is "Successful request for <tier> fields" and "The request is billed at
    the highest SKU applicable to the requested fields" - the field mask picks the TIER, the request is charged
    once. computeRouteMatrix is the exception: "billed per ELEMENT returned from the request"."""
    assert mapsbill.UNIT.get(mapsbill.SKU_MATRIX) == mapsbill.PER_ELEMENT
    assert mapsbill.UNIT.get(mapsbill.SKU_TEXT_ENT, mapsbill.PER_REQUEST) == mapsbill.PER_REQUEST
    monkeypatch.setitem(mapsbill._FREE_INDIA, mapsbill.SKU_MATRIX, 0)
    monkeypatch.setattr(get_settings(), "maps_daily_inr", 0.0, raising=False)
    one = mapsbill.charge("t6", mapsbill.SKU_MATRIX, 1).inr
    hundred = mapsbill.charge("t6", mapsbill.SKU_MATRIX, 100).inr
    assert hundred == pytest.approx(one * 100), "a 10x10 matrix is 100 billable events, not one"


# ---------------------------------------------------------------- the licence-shaped cache
def test_the_cache_stores_no_google_content_at_all(env):
    """ToS 3.2.3(b): no caching except as expressly permitted. The Places SST (14.1-14.3) permits place_id and
    lat/lng. A name, address, phone, website, rating or opening-hours column here would be a breach, so this
    test guards the table's shape rather than its behaviour."""
    cols = {c.name for c in mapsbill.MapsPlaceCache.__table__.columns}
    assert cols == {"place_id", "lat", "lng", "latlng_at", "query", "first_seen"}
    banned = {"name", "display_name", "address", "formatted_address", "phone", "national_phone_number",
              "website", "website_uri", "rating", "reviews", "user_rating_count", "hours", "opening_hours", "type"}
    assert not (cols & banned)


def test_latlng_expires_at_thirty_days_and_place_id_is_kept(env):
    mapsbill.remember("PID1", 21.0, 77.0, "medical store akola")
    assert mapsbill.cached_latlng("PID1") == {"lat": 21.0, "lng": 77.0, "place_id": "PID1"}
    with db.session() as s:
        s.get(mapsbill.MapsPlaceCache, "PID1").latlng_at = datetime.now(timezone.utc) - timedelta(days=31)
    # expired on READ, not only on sweep: a stale value must never be served because the sweeper is late
    assert mapsbill.cached_latlng("PID1") is None
    assert mapsbill.sweep() == 1
    with db.session() as s:
        row = s.get(mapsbill.MapsPlaceCache, "PID1")
        assert row.place_id == "PID1", "place_id may be kept indefinitely (SST A.3)"
        assert row.lat is None and row.lng is None, "lat/lng must be DELETED after 30 days (SST 14.3)"
        assert row.query == "medical store akola", "her own words are hers, not Google content"


def test_latlng_inside_thirty_days_is_kept(env):
    mapsbill.remember("PID2", 1.0, 2.0)
    with db.session() as s:
        s.get(mapsbill.MapsPlaceCache, "PID2").latlng_at = datetime.now(timezone.utc) - timedelta(days=29)
    assert mapsbill.sweep() == 0
    assert mapsbill.cached_latlng("PID2") is not None


def test_the_ttl_is_the_licences_and_not_a_tuning_knob(env):
    assert mapsbill.LATLNG_TTL == timedelta(days=30)


# ================================================================ Phase 3 tools + Phase 2 card
import asyncio
import json

import httpx


@pytest.fixture
def mp(env, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-maps-key")
    get_settings.cache_clear()
    from app import maps
    seen = []

    def handler(req: httpx.Request):
        seen.append(req)
        mask = req.headers.get("x-goog-fieldmask", "")
        if req.url.path == "/v1/places:searchNearby":
            body = json.loads(req.content)
            return httpx.Response(200, json={"places": [
                {"id": "PID_A", "displayName": {"text": "Sai Medical"}, "formattedAddress": "Tilak Rd, Akola",
                 "location": {"latitude": 20.705, "longitude": 77.01},
                 "primaryTypeDisplayName": {"text": "Pharmacy"}, "businessStatus": "OPERATIONAL",
                 "googleMapsUri": "https://maps.google.com/?cid=1",
                 # these must only come back when the mask asked for them
                 **({"rating": 4.4, "nationalPhoneNumber": "0724 243 0000"} if "rating" in mask else {})},
                {"id": "PID_B", "displayName": {"text": "Jan Aushadhi"}, "formattedAddress": "Ratanlal Plot, Akola",
                 "location": {"latitude": 20.71, "longitude": 77.02}}]})
        if req.url.path.startswith("/v1/places/"):
            return httpx.Response(200, json={
                "id": "PID_A", "displayName": {"text": "Sai Medical"}, "formattedAddress": "Tilak Rd, Akola",
                "location": {"latitude": 20.705, "longitude": 77.01}, "rating": 4.4, "userRatingCount": 120,
                "nationalPhoneNumber": "0724 243 0000", "websiteUri": "https://saimedical.example",
                "currentOpeningHours": {"openNow": True},
                "regularOpeningHours": {"weekdayDescriptions": ["Monday: 9 am - 9 pm"]}})
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
    from sqlalchemy import select
    with session() as s:
        return [e.payload for e in s.scalars(
            select(Event).where(Event.conversation_id == conv, Event.kind == kind).order_by(Event.id)).all()]


def test_nearby_returns_places_and_draws_a_card(mp):
    from app.agent import maps_tools
    r = asyncio.run(maps_tools.maps_nearby(_ctx(mp["conv"]), ["pharmacy"], radius_km=2))
    assert r["count"] == 2
    assert r["places"][0]["name"] == "Sai Medical"
    assert r["places"][0]["place_id"] == "PID_A"
    assert "distance_km" in r["places"][0]
    cards = _events(mp["conv"], "maps_places")
    assert len(cards) == 1 and len(cards[0]["places"]) == 2
    assert cards[0]["attribution"] == "Google", "ToS 3.2.2(b): attribution wherever this content is shown"


def test_the_nearby_list_does_not_buy_the_enterprise_fields(mp):
    """The cheap list / details-on-open split: phone, website, rating and hours are Enterprise-priced, so the
    list pass must not ask for them. The field mask is what picks the SKU."""
    from app.agent import maps_tools
    asyncio.run(maps_tools.maps_nearby(_ctx(mp["conv"]), ["pharmacy"]))
    nearby = [q for q in mp["seen"] if q.url.path == "/v1/places:searchNearby"]
    mask = nearby[-1].headers["x-goog-fieldmask"]
    for ent in ("rating", "nationalPhoneNumber", "websiteUri", "userRatingCount", "currentOpeningHours"):
        assert ent not in mask, f"{ent} is an Enterprise field and must not be in the list pass"
    assert "displayName" in mask and "formattedAddress" in mask
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_NEARBY_PRO) == "1"


def test_maps_place_buys_the_expensive_fields_for_one_place(mp):
    from app.agent import maps_tools
    r = asyncio.run(maps_tools.maps_place(_ctx(mp["conv"]), "PID_A"))
    assert r["phone"] == "0724 243 0000" and r["website"] == "https://saimedical.example"
    assert r["rating"] == 4.4 and r["hours"] == ["Monday: 9 am - 9 pm"]
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_DETAILS_ENT) == "1"


def test_nearby_enforces_googles_own_ceilings(mp):
    """Circle only, radius <= 50 km, <= 20 results, no paging. Enforced here rather than discovered live."""
    from app.agent import maps_tools
    asyncio.run(maps_tools.maps_nearby(_ctx(mp["conv"]), ["pharmacy"], radius_km=500, limit=99))
    body = json.loads([q for q in mp["seen"] if q.url.path == "/v1/places:searchNearby"][-1].content)
    assert body["locationRestriction"]["circle"]["radius"] == float(maps_tools.maps.NEARBY_MAX_RADIUS_M)
    assert body["maxResultCount"] == maps_tools.maps.NEARBY_MAX_RESULTS
    assert "rectangle" not in json.dumps(body), "Nearby Search has no rectangle"


def test_nearby_caches_only_place_id_and_latlng(mp):
    from app.agent import maps_tools
    asyncio.run(maps_tools.maps_nearby(_ctx(mp["conv"]), ["pharmacy"]))
    assert mapsbill.cached_latlng("PID_A") == {"lat": 20.705, "lng": 77.01, "place_id": "PID_A"}


def test_the_cap_stops_a_maps_tool_with_her_own_words(mp, monkeypatch):
    from app.agent import maps_tools
    from app.agent.tools import ToolError
    monkeypatch.setitem(mapsbill._FREE_INDIA, mapsbill.SKU_NEARBY_PRO, 0)
    monkeypatch.setattr(get_settings(), "maps_daily_inr", 0.0001, raising=False)
    with pytest.raises(ToolError) as e:
        asyncio.run(maps_tools.maps_nearby(_ctx(mp["conv"]), ["pharmacy"]))
    assert "budget" in str(e.value).lower()
    assert not [q for q in mp["seen"] if q.url.path == "/v1/places:searchNearby"], \
        "the cap must refuse BEFORE the call goes out, so nothing is billed"


def test_maps_kharcha_shows_the_bill(mp):
    from app.agent import maps_tools
    asyncio.run(maps_tools.maps_nearby(_ctx(mp["conv"]), ["pharmacy"]))
    r = asyncio.run(maps_tools.maps_kharcha(_ctx(mp["conv"])))
    assert r["calls"] == 1 and r["price_list"] == "india" and r["cap_inr"] > 0
    assert mapsbill.SKU_ROUTES in r["assumed_tier"], "a guessed tier must be visible, not silent"


def test_the_new_tools_are_registered_and_reachable_on_a_call(env):
    from app.agent.tools import HANDLERS, TOOL_LABELS, TOOLS
    from app import voice
    names = {t["name"] for t in TOOLS}
    for n in ("maps_nearby", "maps_place", "maps_kharcha"):
        assert n in names and n in HANDLERS and n in TOOL_LABELS
    # v0.442: every registered tool must have a route on a call (declared, or via santosh_kaam)
    for n in ("maps_nearby", "maps_place", "maps_kharcha"):
        assert voice.call_route(n), f"{n} has no way in on a voice call"


def test_a_failed_call_is_refunded(mp, monkeypatch):
    """Google's billable event is a SUCCESSFUL request. charge() runs before the HTTP call so the cap can
    refuse pre-flight, so a 4xx/5xx has to be given back - otherwise a key missing an API answers 403 every
    time and still burns the whole daily cap and the month's free allowance."""
    from app import maps
    from app.agent import maps_tools
    from app.agent.tools import ToolError
    monkeypatch.setitem(mapsbill._FREE_INDIA, mapsbill.SKU_NEARBY_PRO, 0)
    monkeypatch.setattr(get_settings(), "maps_daily_inr", 0.0, raising=False)
    maps.set_client(httpx.AsyncClient(transport=httpx.MockTransport(
        lambda req: httpx.Response(403, json={"error": {"message": "API has not been used"}}))))
    with pytest.raises(ToolError):
        asyncio.run(maps_tools.maps_nearby(_ctx(mp["conv"]), ["pharmacy"]))
    u = mapsbill.usage("default")
    assert u["inr"] == 0.0, "a failed call must cost her nothing"
    assert u["calls"] == 0 and not u["by_sku"]


def test_a_failed_call_gives_the_free_allowance_back(mp):
    from app import maps
    from app.agent import maps_tools
    from app.agent.tools import ToolError
    before = mapsbill.free_left(mapsbill.SKU_NEARBY_PRO)
    maps.set_client(httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(500))))
    with pytest.raises(ToolError):
        asyncio.run(maps_tools.maps_nearby(_ctx(mp["conv"]), ["pharmacy"]))
    assert mapsbill.free_left(mapsbill.SKU_NEARBY_PRO) == before


def test_a_refund_reverses_exactly_what_was_charged(env, monkeypatch):
    """It must not GUESS how many of the events had been free: the first version undid the free side first and
    gave back Rs 0 for a failed call that had really been billed."""
    mapsbill.refund(None)                                   # nothing to reverse
    monkeypatch.setitem(mapsbill._FREE_INDIA, mapsbill.SKU_GEOCODE, 0)
    rc = mapsbill.charge("t9", mapsbill.SKU_GEOCODE, 1)
    assert rc.billed == 1 and rc.free == 0 and rc.inr > 0
    mapsbill.refund(rc)
    u = mapsbill.usage("t9")
    assert u["calls"] == 0 and u["inr"] == 0.0 and u["free_calls"] == 0 and not u["by_sku"]
    mapsbill.refund(rc)                                     # twice must not go negative
    assert mapsbill.usage("t9")["inr"] == 0.0


def test_a_refund_of_a_free_call_returns_the_allowance_not_money(env, monkeypatch):
    monkeypatch.setitem(mapsbill._FREE_INDIA, mapsbill.SKU_GEOCODE, 5)
    rc = mapsbill.charge("t11", mapsbill.SKU_GEOCODE, 1)
    assert rc.free == 1 and rc.inr == 0.0
    assert mapsbill.free_left(mapsbill.SKU_GEOCODE) == 4
    mapsbill.refund(rc)
    assert mapsbill.free_left(mapsbill.SKU_GEOCODE) == 5
    assert mapsbill.usage("t11")["inr"] == 0.0


def test_usage_reads_its_values_inside_the_session(env):
    """A detached ORM row raises once expired, so usage() must not read the row after the session closes."""
    mapsbill.charge("t10", mapsbill.SKU_GEOCODE)
    u = mapsbill.usage("t10")        # would raise DetachedInstanceError if read outside
    assert u["calls"] == 1


def test_the_usage_route_answers_and_names_what_we_guessed(env, monkeypatch):
    """A route that exists is not a route that works - v0.399's lesson (the Systems page 500'd on open while
    its test only asserted the route existed). So this one CALLS it."""
    from fastapi.testclient import TestClient
    monkeypatch.setattr(env["settings"], "api_key", "secret")
    from app.main import app
    with TestClient(app) as c:
        assert c.get("/api/maps/usage").status_code == 401
        r = c.get("/api/maps/usage", headers={"Authorization": "Bearer secret"})
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("day", "month", "calls", "free_calls", "inr", "cap_inr", "refused",
                  "price_list", "assumed_tier", "unsourced_skus"):
            assert k in body, f"/api/maps/usage is missing {k}"
        assert body["price_list"] == "india"
        assert mapsbill.SKU_ROUTES in body["assumed_tier"]
