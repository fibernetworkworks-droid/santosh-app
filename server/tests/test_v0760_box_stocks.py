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
        if "alphavantage" in req.url.host:                 # v0.761 order: Alpha Vantage first; its 200 refusal
            return httpx.Response(200, json={"Note": "25 calls a day used up"})
        return httpx.Response(200, json={"symbol": "RELIANCE", "exchange": "NSE", "close": "1420.5"})
    _mock(monkeypatch, handler)
    r = asyncio.run(BX.call("t1", "reliance share price", {"symbol": "RELIANCE"}))
    assert r["ok"] and r["api"]["recipe"] == "stock_price" and "25 calls" in r["tried"][0]["error"]
    assert parse_qs(urlparse(seen[0]).query)["symbol"] == ["RELIANCE.BSE"]
    _mock(monkeypatch, lambda req: httpx.Response(200, json={"Information": "rate limit 25 a day"}))
    r = asyncio.run(BX.call("t1", "share price bse", {"symbol": "TCS"}, api="stock_price_bse"))
    assert not r["ok"] and "rate limit" in r["tried"][0]["error"]


def test_v0761_alpha_vantage_first_history_slimmed_and_the_apis_own_404_message(env, monkeypatch):
    seen = []
    monkeypatch.setattr(get_settings(), "twelvedata_api_key", "td-key-1234")
    monkeypatch.setattr(get_settings(), "alphavantage_api_key", "av-key-1234")
    series = {f"2026-11-{d:02d}": {"1. open": "1", "4. close": str(d), "5. volume": "9"} for d in range(30, 0, -1)}

    def handler(req):
        seen.append(str(req.url))
        if "twelvedata" in req.url.host:
            return httpx.Response(404, json={"code": 404, "status": "error", "message": "available on the Grow plan"})
        if "TIME_SERIES_DAILY" in str(req.url):
            return httpx.Response(200, json={"Meta Data": {"2. Symbol": "TCS.BSE"}, "Time Series (Daily)": series})
        return httpx.Response(200, json={"Global Quote": {"05. price": "1323.90"}})
    _mock(monkeypatch, handler)
    r = asyncio.run(BX.call("t1", "reliance share price", {"symbol": "RELIANCE"}))
    assert r["ok"] and r["api"]["recipe"] == "stock_price_bse" and len(seen) == 1         # Alpha Vantage goes first
    r = asyncio.run(BX.call("t1", "tcs history", {"symbol": "TCS", "days": "5"}, api="stock_history_bse"))
    d = r["data"]
    assert r["ok"] and d["shown"] == 5 and d["days"][0] == {"date": "2026-11-30", "open": "1", "close": "30", "volume": "9"}
    r = asyncio.run(BX.call("t1", "price", {"symbol": "TCS"}, api="stock_price"))
    assert not r["ok"] and "Grow plan" in r["tried"][0]["error"]                           # the API's own words
