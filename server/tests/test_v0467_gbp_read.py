"""v0.467 Phase 8a APNI DUKAAN (read): her Business Profile locations + Performance numbers.

Shapes come from Google's discovery documents (accounts.list, accounts.locations.list with readMask,
locations.fetchMultiDailyMetricsTimeSeries with dailyRange.* and repeated dailyMetrics). Pinned: the request shape,
summing string values, an unapproved project (quota 0) is reported by name, read-only (no write verb ever), nothing
is stored, owner only."""
from __future__ import annotations

import asyncio
from datetime import date

import httpx
import pytest

from app import gbp, google_auth


class FakeCreds:
    token = "TOK"


@pytest.fixture
def g(env, monkeypatch):
    monkeypatch.setattr(google_auth, "credentials_for", lambda tenant, scopes=None: FakeCreds())
    seen, mode = [], {"status": 200}

    def handler(req: httpx.Request):
        seen.append(req)
        if mode["status"] != 200:
            body = {"error": {"status": mode.get("st", ""), "message": mode.get("msg", "x")}}
            return httpx.Response(mode["status"], json=body)
        if req.url.host == "mybusinessaccountmanagement.googleapis.com":
            return httpx.Response(200, json={"accounts": [{"name": "accounts/111", "accountName": "Sai Stores"}]})
        if req.url.host == "mybusinessbusinessinformation.googleapis.com":
            return httpx.Response(200, json={"locations": [{
                "name": "locations/222", "title": "Sai Medical",
                "storefrontAddress": {"addressLines": ["Tilak Rd"], "locality": "Akola", "postalCode": "444001"},
                "phoneNumbers": {"primaryPhone": "0724 243 0000"}, "websiteUri": "https://sai.example",
                "regularHours": {"periods": [{"openDay": "MONDAY", "openTime": {"hours": 9}, "closeDay": "MONDAY",
                                              "closeTime": {"hours": 21, "minutes": 30}}]},
                "metadata": {"mapsUri": "https://maps.google.com/?cid=1", "placeId": "PID", "hasPendingEdits": True}}]})
        if req.url.host == "businessprofileperformance.googleapis.com":
            def ts(metric, vals):
                return {"dailyMetric": metric, "timeSeries": {"datedValues": [
                    {"date": {"year": 2026, "month": 11, "day": i + 1}, "value": str(v)} for i, v in enumerate(vals)]}}
            return httpx.Response(200, json={"multiDailyMetricTimeSeries": [{"dailyMetricTimeSeries": [
                ts("BUSINESS_IMPRESSIONS_MOBILE_SEARCH", [10, 20, 30]), ts("BUSINESS_IMPRESSIONS_DESKTOP_MAPS", [5]),
                ts("CALL_CLICKS", [1, 2]), ts("WEBSITE_CLICKS", [])]}]})
        return httpx.Response(404)
    gbp.set_client(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    yield {"seen": seen, "mode": mode}
    gbp.set_client(None)


def test_locations_are_read_through_account_then_location_with_a_read_mask(g):
    rows = asyncio.run(gbp.locations("default"))
    r = rows[0]
    assert r["location"] == "locations/222" and r["title"] == "Sai Medical" and r["account"] == "Sai Stores"
    assert r["address"] == "Tilak Rd, Akola, 444001" and r["phone"] == "0724 243 0000"
    assert r["hours"] == ["Mon 09:00-21:30"] and r["edit_pending"] is True
    loc_call = [q for q in g["seen"] if q.url.host.startswith("mybusinessbusinessinformation")][0]
    assert loc_call.url.path == "/v1/accounts/111/locations" and "readMask" in str(loc_call.url)
    assert all(q.headers["authorization"] == "Bearer TOK" for q in g["seen"])


def test_numbers_request_shape_and_totals(g):
    r = asyncio.run(gbp.numbers("default", "locations/222", 30, today=date(2026, 11, 4)))
    q = g["seen"][0]
    assert q.url.path == "/v1/locations/222:fetchMultiDailyMetricsTimeSeries"
    s = str(q.url)
    assert "dailyRange.startDate.day=5" in s and "dailyRange.endDate.day=3" in s and "dailyRange.endDate.month=11" in s
    assert s.count("dailyMetrics=") == len(gbp.METRICS)
    assert r["from"] == "2026-10-05" and r["to"] == "2026-11-03"
    assert r["times_shown"] == 65 and r["shown_where"]["Shown in Search (phone)"] == 60
    assert r["actions"]["Tapped Call"] == 3 and r["actions"]["Opened the website"] == 0 and r["has_data"] is True


def test_no_data_reads_as_none_not_invented(g, monkeypatch):
    def empty(req):
        return httpx.Response(200, json={})
    gbp.set_client(httpx.AsyncClient(transport=httpx.MockTransport(empty)))
    r = asyncio.run(gbp.numbers("default", "locations/222", 7))
    assert r["has_data"] is False and r["times_shown"] == 0


def test_an_unapproved_project_is_named_not_guessed_around(g):
    g["mode"].update(status=429, st="RESOURCE_EXHAUSTED", msg="Quota exceeded for quota metric ... limit 0")
    with pytest.raises(gbp.GbpError) as e:
        asyncio.run(gbp.locations("default"))
    assert "quota 0" in str(e.value) and "Basic API Access" in str(e.value)


def test_missing_scope_and_disabled_api_have_their_own_messages(g):
    g["mode"].update(status=403, st="PERMISSION_DENIED", msg="Request had insufficient authentication scopes.")
    with pytest.raises(gbp.GbpError) as e:
        asyncio.run(gbp.locations("default"))
    assert "business.manage" in str(e.value)
    g["mode"].update(status=403, st="PERMISSION_DENIED", msg="Business Profile API has not been used in project 1 before or it is disabled")
    with pytest.raises(gbp.GbpError) as e:
        asyncio.run(gbp.locations("default"))
    assert "enable" in str(e.value)


def test_no_google_login_says_so(env, monkeypatch):
    monkeypatch.setattr(google_auth, "credentials_for", lambda t, scopes=None: None)
    with pytest.raises(gbp.GbpError):
        asyncio.run(gbp.locations("default"))


def test_bad_location_and_days_are_refused_before_any_call(g):
    for loc, days in (("abc", 30), ("locations/222", 0), ("locations/222", 9999)):
        with pytest.raises(gbp.GbpError):
            asyncio.run(gbp.numbers("default", loc, days))
    assert not g["seen"]


def test_it_is_read_only_and_stores_nothing(g):
    asyncio.run(gbp.locations("default"))
    asyncio.run(gbp.numbers("default", "locations/222", 7))
    assert {q.method for q in g["seen"]} == {"GET"}
    import inspect
    src = inspect.getsource(gbp)
    assert "session(" not in src and "Base" not in src, "Business Profile content must never be written to our database"


def test_tools_are_owner_only_and_registered(g):
    from app.agent import maps_tools
    from app.agent.tools import TOOLS, HANDLERS, Ctx, ToolError
    assert "gbp_locations" in {t["name"] for t in TOOLS} and "gbp_numbers" in HANDLERS
    r = asyncio.run(maps_tools.gbp_numbers(Ctx(tenant_id="default", conversation_id="c"), days=7))
    assert r["location"] == "locations/222", "one listing -> chosen automatically"
    with pytest.raises(ToolError):
        asyncio.run(maps_tools.gbp_locations(Ctx(tenant_id="default", conversation_id="c", actor="staff:1")))
