"""v0.760 SHARE BHAV (owner: "proceed" on Twelve Data + Alpha Vantage): Indian share prices in the box on ONE server key
each; a 200 that is really a refusal (Alpha Vantage "Information", Twelve Data status error) counts as a failure so the
next recipe answers. Offline (MockTransport)."""
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


def test_nse_quote_on_the_twelve_data_key(env, monkeypatch):
    seen = []
    monkeypatch.setattr(get_settings(), "twelvedata_api_key", "td-key-1234")
    _mock(monkeypatch, lambda req: (seen.append(str(req.url)), httpx.Response(200, json={
        "symbol": "RELIANCE", "exchange": "NSE", "currency": "INR", "close": "1420.5"}))[1])
    r = asyncio.run(BX.call("t1", "reliance share price", {"symbol": "RELIANCE"}))
    assert r["ok"] and r["api"]["recipe"] == "stock_price" and r["data"]["close"] == "1420.5"
    q = parse_qs(urlparse(seen[0]).query)
    assert q["apikey"] == ["td-key-1234"] and q["exchange"] == ["NSE"] and "td-key-1234" not in str(r)


def test_a_200_refusal_falls_back_to_alpha_vantage_bse(env, monkeypatch):
    seen = []
    monkeypatch.setattr(get_settings(), "twelvedata_api_key", "td-key-1234")
    monkeypatch.setattr(get_settings(), "alphavantage_api_key", "av-key-1234")

    def handler(req):
        seen.append(str(req.url))
        if "twelvedata" in req.url.host:
            return httpx.Response(200, json={"code": 403, "status": "error", "message": "pro plan only"})
        return httpx.Response(200, json={"Global Quote": {"01. symbol": "RELIANCE.BSE", "05. price": "1419.00"}})
    _mock(monkeypatch, handler)
    r = asyncio.run(BX.call("t1", "reliance share price bse", {"symbol": "RELIANCE"}))
    assert r["ok"] and r["api"]["recipe"] == "stock_price_bse" and "pro plan only" in r["tried"][0]["error"]
    assert parse_qs(urlparse(seen[-1]).query)["symbol"] == ["RELIANCE.BSE"]
    _mock(monkeypatch, lambda req: httpx.Response(200, json={"Information": "rate limit 25 a day"}))
    r = asyncio.run(BX.call("t1", "share price bse", {"symbol": "TCS"}, api="stock_price_bse"))
    assert not r["ok"] and "rate limit" in r["tried"][0]["error"]
