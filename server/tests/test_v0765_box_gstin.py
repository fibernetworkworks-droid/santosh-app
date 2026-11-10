"""v0.765 GSTIN JAANCH (owner: "business-gstinapi"): GSTIN checks in the box on ONE server key (GSTINAPI_API_KEY,
header x-api-key per its docs), PAID per lookup - a GSTIN that fails its check digit is refused before any call, the
provider's own sandbox GSTIN is allowed, {"success": false} is read as a failure, and the day's paid calls for all users
are capped (GSTIN_DAILY_CALLS). Offline (MockTransport)."""
import asyncio
from urllib.parse import parse_qs, urlparse

import httpx

from app.config import get_settings
from app.publicapis import box as BX
from app.publicapis import service as S


def _mock(monkeypatch, handler):
    from app import web
    monkeypatch.setattr(S, "_transport", httpx.MockTransport(handler))
    monkeypatch.setattr(web, "_public_host", lambda host: None)


def test_verify_header_check_digit_and_sandbox(env, monkeypatch):
    seen = []
    monkeypatch.setattr(get_settings(), "gstinapi_api_key", "gak_test1234")
    _mock(monkeypatch, lambda req: (seen.append(req), httpx.Response(200, json={
        "success": True, "data": {"legal_name": "CENTRAL WAREHOUSING CORPORATION", "status": "Active"}}))[1])
    r = asyncio.run(BX.call("t1", "verify gstin", {"gstin": "33aaacc1206d1zn"}, api="gstin_verify"))
    assert r["ok"] and seen[0].url.path == "/v1/gstin/33AAACC1206D1ZN" and seen[0].headers["x-api-key"] == "gak_test1234"
    assert "gak_test" not in str(r) and "PAID" in r["note_for_you"]
    r = asyncio.run(BX.call("t1", "verify gstin", {"gstin": "33AAACC1206D1ZM"}, api="gstin_verify"))   # wrong check digit
    assert not r["ok"] and len(seen) == 1 and "fails its check" in r["tried"][0]["skipped"]
    assert asyncio.run(BX.call("t1", "verify", {"gstin": "00AAAAA0000A1ZT"}, api="gstin_verify"))["ok"]


def test_compliance_defaults_to_this_financial_year_and_success_false_is_a_failure(env, monkeypatch):
    seen = []
    monkeypatch.setattr(get_settings(), "gstinapi_api_key", "gak_test1234")
    _mock(monkeypatch, lambda req: (seen.append(str(req.url)), httpx.Response(200, json={"success": False,
                                                                                      "error": "GSTIN not found"}))[1])
    r = asyncio.run(BX.call("t1", "filing compliance", {"gstin": "33AAACC1206D1ZN"}, api="gstin_compliance"))
    fy = parse_qs(urlparse(seen[0]).query)["fy"][0]
    assert len(fy) == 7 and fy[4] == "-" and not r["ok"] and "GSTIN not found" in r["tried"][0]["error"]


def test_gstin_daily_cap(env, monkeypatch):
    seen = []
    monkeypatch.setattr(get_settings(), "gstinapi_api_key", "gak_test1234")
    monkeypatch.setattr(get_settings(), "gstin_daily_calls", 1)
    _mock(monkeypatch, lambda req: (seen.append(req), httpx.Response(200, json={"success": True, "data": {}}))[1])
    assert asyncio.run(BX.call("t1", "verify", {"gstin": "33AAACC1206D1ZN"}, api="gstin_verify"))["ok"]
    r = asyncio.run(BX.call("t2", "verify", {"gstin": "33AAACC1206D1ZN"}, api="gstin_verify"))
    assert not r["ok"] and len(seen) == 1 and "GSTIN_DAILY_CALLS" in r["tried"][0]["error"]


def test_a_weaker_recipe_answering_says_what_failed(env, monkeypatch):
    """v0.766 (her live test): 'gstin compliance' on a free gstinapi account got a 403 (credit pack only) and the box
    quietly answered with gstin_verify - ok:true, as if it were the compliance answer. Now it says what failed."""
    monkeypatch.setattr(get_settings(), "gstinapi_api_key", "gak_test1234")

    def h(req):
        if "/compliance" in req.url.path or "/returns" in req.url.path:
            return httpx.Response(403, json={"error": "This endpoint is available to accounts that have bought a credit pack."})
        return httpx.Response(200, json={"success": True, "data": {"legal_name": "X", "status": "Active"}})
    _mock(monkeypatch, h)
    r = asyncio.run(BX.call("t1", "gstin compliance", {"gstin": "33AAACC1206D1ZN"}))
    assert r["ok"] and r["api"]["recipe"] == "gstin_verify" and "gstin_compliance" in r["instead_of"]
    assert "NOT WHAT SHE ASKED FOR" in r["note_for_you"] and "credit pack" in r["note_for_you"]
    r = asyncio.run(BX.call("t1", "verify gstin", {"gstin": "33AAACC1206D1ZN"}, api="gstin_verify"))
    assert r["ok"] and "instead_of" not in r and "NOT WHAT" not in r["note_for_you"]
