"""v0.464 Phase 6 PATA PAKKA - Address Validation + reverse geocode.

Response shapes come from Google's own discovery document (addressvalidation.googleapis.com/$discovery),
not from memory. What is worth pinning: an Indian landmark address that validates only to the ROAD is not
called wrong; a replaced PIN / unconfirmed part IS; nothing is stored; a failed call is refunded; billed once."""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app import maps, mapsbill
from app.config import get_settings


def verdict(**kw):
    base = {"addressComplete": True, "validationGranularity": "PREMISE", "geocodeGranularity": "PREMISE"}
    base.update(kw)
    return base


def comp(t, text, **kw):
    return {"componentType": t, "componentName": {"text": text}, "confirmationLevel": "CONFIRMED", **kw}


def test_a_matched_house_is_pakka():
    g, why = maps.grade_address(verdict(), {"addressComponents": [comp("route", "Tilak Road")]})
    assert g == "pakka" and why == []


def test_a_road_only_match_is_not_called_wrong():
    """The Indian reality: 'Ram Mandir ke paas, Tilak Road' validates to the road. That is not a bad address."""
    g, why = maps.grade_address(verdict(validationGranularity="ROUTE"), {"addressComponents": []})
    assert g == "sadak_tak"
    assert any("sadak" in w for w in why)


def test_a_replaced_pin_is_galat_and_says_the_right_one():
    g, why = maps.grade_address(verdict(hasReplacedComponents=True), {
        "addressComponents": [comp("postal_code", "444001", replaced=True)]})
    assert g == "galat" and any("444001" in w for w in why)


def test_unconfirmed_missing_and_unresolved_are_galat_and_named():
    g, why = maps.grade_address(verdict(hasUnconfirmedComponents=True, addressComplete=False), {
        "unconfirmedComponentTypes": ["locality"], "missingComponentTypes": ["route"], "unresolvedTokens": ["xyzzy"]})
    text = " ".join(why)
    assert g == "galat" and "locality" in text and "route" in text and "xyzzy" in text


def test_spelling_fixes_are_reported_but_do_not_fail_a_good_address():
    g, why = maps.grade_address(verdict(), {"addressComponents": [comp("route", "Tilak Road", spellCorrected=True)]})
    assert g == "pakka" and any("spelling" in w for w in why)


def test_an_incomplete_address_with_no_other_flag_is_still_galat():
    g, _ = maps.grade_address(verdict(addressComplete=False), {})
    assert g == "galat"


@pytest.fixture
def av(env, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-maps-key")
    get_settings.cache_clear()
    seen, mode = [], {"fail": False}

    def handler(req: httpx.Request):
        seen.append(req)
        if req.url.host == "addressvalidation.googleapis.com":
            if mode["fail"]:
                return httpx.Response(403, json={"error": {"message": "API not enabled"}})
            return httpx.Response(200, json={"result": {
                "verdict": verdict(validationGranularity="ROUTE"),
                "address": {"formattedAddress": "Tilak Rd, Akola, Maharashtra 444001, India",
                            "addressComponents": [comp("route", "Tilak Road"), comp("postal_code", "444001")]},
                "geocode": {"location": {"latitude": 20.7, "longitude": 77.0}, "placeId": "PID1"},
                "metadata": {"residential": True}}, "responseId": "r1"})
        if "geocode" in req.url.path:
            return httpx.Response(200, json={"status": "OK", "results": [
                {"formatted_address": "Tilak Rd, Akola", "place_id": "PID1", "types": ["route"]}]})
        return httpx.Response(404)
    maps.set_client(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default"); s.add(c); s.flush(); conv = c.id
    maps.save_location("default", 20.7, 77.0, 15)
    yield {"conv": conv, "seen": seen, "mode": mode}
    maps.set_client(None)


def _ctx(conv):
    from app.agent.tools import Ctx
    return Ctx(tenant_id="default", conversation_id=conv)


def test_the_request_is_an_indian_postal_address_with_the_key_in_a_header(av):
    from app.agent import maps_tools
    r = asyncio.run(maps_tools.maps_address_check(_ctx(av["conv"]), "Near Ram Mandir, Tilak Road", pin="444 001", city="Akola"))
    q = av["seen"][0]
    body = json.loads(q.content)["address"]
    assert body["regionCode"] == "IN" and body["postalCode"] == "444001" and body["locality"] == "Akola"
    assert body["addressLines"] == ["Near Ram Mandir, Tilak Road"]
    assert q.headers["x-goog-api-key"] == "test-maps-key" and "key=" not in str(q.url)
    assert r["grade"] == "sadak_tak" and r["corrected"].startswith("Tilak Rd") and r["lat"] == 20.7


def test_it_is_billed_once_at_the_address_sku(av):
    from app.agent import maps_tools
    asyncio.run(maps_tools.maps_address_check(_ctx(av["conv"]), "Tilak Road, Akola"))
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_ADDRESS_ENT) == "1"
    assert mapsbill.SKU_ADDRESS_ENT in mapsbill.ASSUMED_TIER, "the tier is a guess and must be reported as one"


def test_a_failed_call_is_refunded(av):
    from app.agent import maps_tools
    from app.agent.tools import ToolError
    av["mode"]["fail"] = True
    with pytest.raises(ToolError):
        asyncio.run(maps_tools.maps_address_check(_ctx(av["conv"]), "Tilak Road, Akola"))
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_ADDRESS_ENT) in (None, "0")


def test_an_empty_or_huge_address_is_refused_before_any_call(av):
    from app.agent import maps_tools
    from app.agent.tools import ToolError
    for bad in ("", "x" * 400):
        with pytest.raises(ToolError):
            asyncio.run(maps_tools.maps_address_check(_ctx(av["conv"]), bad))
    assert not av["seen"]


def test_nothing_from_the_answer_is_written_to_the_place_cache(av):
    from app.agent import maps_tools
    asyncio.run(maps_tools.maps_address_check(_ctx(av["conv"]), "Tilak Road, Akola"))
    assert mapsbill.cached_latlng("PID1") is None


def test_reverse_geocode_uses_the_phone_location_when_none_given(av):
    from app.agent import maps_tools
    r = asyncio.run(maps_tools.maps_pata(_ctx(av["conv"])))
    assert r["address"] == "Tilak Rd, Akola"
    assert "latlng=20.7%2C77.0" in str(av["seen"][0].url) or "latlng=20.7,77.0" in str(av["seen"][0].url)
    assert mapsbill.usage("default")["by_sku"].get(mapsbill.SKU_GEOCODE) == "1"


def test_the_tools_are_registered_and_reach_a_call(env):
    from app.agent.tools import TOOLS, HANDLERS
    names = {t["name"] for t in TOOLS}
    from app import voice
    for n in ("maps_address_check", "maps_pata"):
        assert n in names and n in HANDLERS and n in voice.VOICE_TOOL_NAMES
