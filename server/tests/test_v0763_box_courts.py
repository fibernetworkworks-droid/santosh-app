"""v0.763 ADALAT (owner: "eCourtsIndia"): Indian court data in the box on ONE server key sent as
Authorization: Bearer (the API's docs), PAID per call - so a value that cannot be right is refused before any call, and
the day's paid calls for ALL users are capped (ECOURTS_DAILY_CALLS). Offline (MockTransport)."""
import asyncio

import httpx

from app.config import get_settings
from app.publicapis import box as BX
from app.publicapis import service as S


def _mock(monkeypatch, handler):
    from app import web
    monkeypatch.setattr(S, "_transport", httpx.MockTransport(handler))
    monkeypatch.setattr(web, "_public_host", lambda host: None)


def _keyed(monkeypatch, cap=30):
    monkeypatch.setattr(get_settings(), "ecourtsindia_api_key", "eci_live_test0000000000000000000000000000")
    monkeypatch.setattr(get_settings(), "ecourts_daily_calls", cap)


def test_case_by_cnr_bearer_header_slimmed_and_marked_paid(env, monkeypatch):
    seen = []
    _keyed(monkeypatch)
    big = {"data": {"courtCaseData": {"caseNumber": "202400248072016", "cnr": "DLHC010351552024", "caseStatus": "Pending",
                                      "nextHearingDate": "2026-11-20", "petitioners": ["A", "B"],
                                      "hearingHistory": [{"date": f"2025-0{i}-01", "purpose": "x" * 900} for i in range(1, 9)],
                                      "orders": [{"html": "y" * 50_000}]}}, "meta": {"request_id": "r1"}}

    def handler(req):
        seen.append(req)
        return httpx.Response(200, json=big)
    _mock(monkeypatch, handler)
    r = asyncio.run(BX.call("t1", "case status", {"cnr": "dlhc010351552024"}, api="court_case"))
    assert r["ok"] and seen[0].url.path == "/api/partner/case/DLHC010351552024"
    assert seen[0].headers["authorization"] == "Bearer eci_live_test0000000000000000000000000000"
    assert "eci_live" not in str(r) and "PAID" in r["note_for_you"]
    d = r["data"]
    assert d["caseStatus"] == "Pending" and len(d["hearingHistory"]) == 6 and len(d["hearingHistory"][0]["purpose"]) == 301
    assert len(str(d)) < 12_000


def test_a_wrong_cnr_or_no_name_costs_nothing(env, monkeypatch):
    seen = []
    _keyed(monkeypatch)
    _mock(monkeypatch, lambda req: (seen.append(req), httpx.Response(200, json={}))[1])
    r = asyncio.run(BX.call("t1", "case", {"cnr": "12345"}, api="court_case"))
    assert not r["ok"] and seen == [] and "does not look right" in r["tried"][0]["skipped"]
    r = asyncio.run(BX.call("t1", "search", {}, api="court_search"))
    assert not r["ok"] and seen == [] and "needs one of" in r["tried"][0]["skipped"]


def test_the_daily_cap_stops_paid_calls_for_everyone(env, monkeypatch):
    seen = []
    _keyed(monkeypatch, cap=2)
    _mock(monkeypatch, lambda req: (seen.append(req), httpx.Response(200, json={"data": {"results": [{"cnr": "X"}]}}))[1])
    for tenant in ("t1", "t2"):
        assert asyncio.run(BX.call(tenant, "cases", {"litigants": "Ramesh"}, api="court_search"))["ok"]
    r = asyncio.run(BX.call("t3", "cases", {"litigants": "Ramesh"}, api="court_search"))
    assert not r["ok"] and len(seen) == 2 and "ECOURTS_DAILY_CALLS" in r["tried"][0]["error"]
