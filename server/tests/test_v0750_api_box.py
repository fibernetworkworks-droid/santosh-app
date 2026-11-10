"""v0.750 API BOX (owner: "WE WILL CREATE A BOX FOR PUBLIC APIS AND DEVELOP ONE CALLING API ... THAT SINGLE API GO TO
THAT BOX AND EXTRACT THE API REQUIRED" -> "NOW CREATE A BOX FOR FREE APIS FIRST").

Before: the model ran api_find -> api_docs -> api_call itself on every public-data ask. Now ONE call, api_box(need,
params), goes to a box of FREE APIs: tested starter recipes + every free call that worked before, minus the APIs the
health check marked dead, with a fallback to the next API and one answer shape. All offline (MockTransport)."""
import asyncio

import httpx
import pytest

from app.publicapis import box as BX
from app.publicapis import service as S


def _mock(handler, monkeypatch):
    from app import web
    monkeypatch.setattr(S, "_transport", httpx.MockTransport(handler))
    monkeypatch.setattr(BX, "_check_transport", httpx.MockTransport(handler))
    monkeypatch.setattr(web, "_public_host", lambda host: None)


def test_the_box_is_free_apis_with_tested_starter_recipes(env):
    st = BX.stats()
    assert st["free_apis"] >= 1300 and len(st["starter_recipes"]) == 23
    for r in BX.STARTER:
        row = S.by_id()[r["api_id"]]                                         # every recipe names a real catalog API
        assert (row["auth"] == "none") != bool(r.get("needs_key")), r["key"]  # free, or marked as needing her key
        assert r["url"].startswith("https://") and BX._fill(r["url"], {**r.get("defaults", {}), **r["example"]})
    from app.agent import tools as T
    assert "api_box" in T.HANDLERS and T.TOOLS[[t["name"] for t in T.TOOLS].index("api_box")]["name"] == "api_box"


def test_the_box_picks_the_right_recipe_from_plain_words(env):
    assert BX.plan("pincode details 444001", {"pincode": "444001"})[0]["key"] == "india_pincode"
    assert BX.plan("ifsc bank branch")[0]["key"] == "ifsc"
    assert BX.plan("USD to INR exchange rate")[0]["key"] == "currency_rate"
    assert BX.plan("mausam kaisa hai")[0]["key"] == "weather_now"
    assert BX.plan("anything", api="dictionary")[0]["key"] == "dictionary"   # a named recipe goes straight


def test_one_call_fills_calls_and_answers_in_one_shape(env, monkeypatch):
    seen = []

    def handler(req):
        seen.append(str(req.url))
        return httpx.Response(200, json=[{"Status": "Success", "PostOffice": [{"Name": "Akola", "District": "Akola"}]}])
    _mock(handler, monkeypatch)
    r = asyncio.run(BX.call("t1", "pincode details", {"pincode": "444001"}))
    assert r["ok"] and r["api"]["recipe"] == "india_pincode" and r["data"][0]["PostOffice"][0]["Name"] == "Akola"
    assert seen == ["https://api.postalpincode.in/pincode/444001"]
    assert BX.health_map()["tracking-postalpincode"]["status"] == "alive"
    # her value is quoted: it can never add a path, query or host of its own
    asyncio.run(BX.call("t1", "pincode", {"pincode": "../../evil?x=1"}))
    assert seen[-1] == "https://api.postalpincode.in/pincode/..%2F..%2Fevil%3Fx%3D1"


def test_a_failing_api_falls_back_and_is_hidden_after_two_failures(env, monkeypatch):
    def handler(req):
        if "open-meteo" in req.url.host and "forecast" in req.url.path:
            return httpx.Response(500, json={"error": True})
        return httpx.Response(200, json={"ok": 1})
    _mock(handler, monkeypatch)
    # a learned recipe for the same need, so there is somewhere to fall back to
    from app.db import session
    from app.publicapis.models import PublicApiRecipe
    with session() as s:
        s.add(PublicApiRecipe(api_id="weather-7timer", pattern="https://www.7timer.info/bin/api.pl?lat={}&lon={}",
                              example_params="lat,lon", ok_count=3, owners=1, first_tenant="x"))
    if "weather-7timer" not in S.by_id():
        pytest.skip("catalog row for the fallback not present")
    r = asyncio.run(BX.call("t1", "weather forecast", {"lat": "20.7", "lon": "77.0"}))
    assert r["ok"] and r["api"]["id"] == "weather-7timer" and r["tried"][0]["recipe"] == "weather_now"
    asyncio.run(BX.call("t1", "weather forecast", {"lat": "20.7", "lon": "77.0"}))
    assert BX.hidden(BX.health_map()["weather-open-meteo"])                   # failed twice in a row = out of the box
    assert all(p["api_id"] != "weather-open-meteo" for p in BX.plan("weather forecast"))


def test_missing_values_are_named_never_guessed(env, monkeypatch):
    _mock(lambda req: httpx.Response(200, json={}), monkeypatch)
    r = asyncio.run(BX.call("t1", "ifsc bank branch details"))
    assert not r["ok"] and r["params_needed"] == {"ifsc": "11-character IFSC code"}
    assert "closest_free_apis" in r and "api_docs + api_call" in r["hint"]


def test_the_health_check_classifies_and_refreshes_the_oldest_first(env, monkeypatch):
    def handler(req):
        h = req.url.host
        if "postalpincode" in h:
            return httpx.Response(404)
        if "razorpay" in h:
            return httpx.Response(403)
        return httpx.Response(200)
    _mock(handler, monkeypatch)
    res = asyncio.run(BX.check(limit=40))
    assert res["checked"] == 40 and sum(res["result"].values()) == 40
    asyncio.run(BX.check(limit=0))                                           # 0 = every free API
    hm = BX.health_map()
    assert hm["tracking-postalpincode"]["status"] == "dead" and BX.hidden(hm["tracking-postalpincode"])
    assert hm["finance-razorpay-ifsc"]["status"] == "blocked" and not BX.hidden(hm["finance-razorpay-ifsc"])
    assert BX.stats()["health"].get("hidden", 0) >= 1
    assert asyncio.run(BX.check(limit=10))["checked"] == 0                   # all checked today: nothing older than 30 days


def test_the_route_and_the_worker_slot(env, monkeypatch):
    from fastapi.testclient import TestClient
    from app import worker
    from app.main import app
    _mock(lambda req: httpx.Response(200, json={"amount": 1.0, "rates": {"INR": 93.9}}), monkeypatch)
    c = TestClient(app)
    r = c.post("/api/box/call", json={"need": "USD to INR", "params": {"from": "USD", "to": "INR"}}).json()
    assert r["ok"] and r["data"]["rates"]["INR"] == 93.9
    assert c.get("/api/box").json()["free_apis"] >= 1300
    called = []
    monkeypatch.setattr(BX, "check", lambda limit=0, older_days=30: called.append(limit))
    monkeypatch.setattr(worker, "_box_last", 0.0)
    asyncio.run(worker.api_box_jobs())                                       # conftest: API_BOX_CHECK_PER_DAY=0 = off
    assert called == []


def test_her_plain_words_open_the_box_family():
    from app.agent import admit
    for t in ("444001 pincode ki details do", "usd to inr exchange rate kya hai", "ifsc sbin0001234 kahan ka hai",
              "aaj ka bitcoin price"):
        assert "publicapi" in admit._match(t) and "publicapi" in admit._match(t, tight=True), t
    from app.agent import prompts
    assert "FIRST try api_box(need, params)" in open(prompts.__file__, encoding="utf-8").read()
