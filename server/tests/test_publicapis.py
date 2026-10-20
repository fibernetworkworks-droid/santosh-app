"""v0.47 Public APIs catalog + safe calls + keys that never reach the model + remembered recipes."""
import asyncio
import json

import httpx
import pytest


def test_catalog_loaded_and_search_understands_hinglish(env):
    from app.publicapis import service as pa
    assert len(pa.catalog()) > 2000
    w = pa.find("mausam", limit=5)
    assert w["results"] and any(r["cat"] == "Weather" for r in w["results"])
    free = pa.find("currency exchange", auth="none", limit=8)["results"]
    assert free and all(r["free_no_key"] for r in free)
    assert any("IFSC" in r["name"] or "ifsc" in r["desc"].lower() for r in pa.find("ifsc bank")["results"])
    cats = {c["cat"] for c in pa.categories()}
    assert {"Weather", "Government", "Finance"} <= cats


def _mock(handler, monkeypatch):
    from app.publicapis import service as pa
    from app import web
    monkeypatch.setattr(pa, "_transport", httpx.MockTransport(handler))
    monkeypatch.setattr(web, "_public_host", lambda host: None)


def test_call_get_only_public_https_and_recipe_remembered(env, monkeypatch):
    from app.publicapis import service as pa
    seen = []

    def handler(req):
        seen.append(req)
        return httpx.Response(200, json={"rates": {"INR": 83.1}, "base": "USD"})
    _mock(handler, monkeypatch)
    api = pa.find("currency exchange", auth="none", limit=1)["results"][0]["id"]
    out = asyncio.run(pa.call("default", "https://api.example.org/v1/latest", {"base": "USD"}, api))
    assert out["status"] == 200 and out["json"]["rates"]["INR"] == 83.1 and seen[0].method == "GET"
    again = pa.find("currency exchange", auth="none", limit=5)["results"]
    hit = [r for r in again if r["id"] == api][0]
    assert hit["worked_before"][0]["call"] == "https://api.example.org/v1/latest?base={}"
    with pytest.raises(pa.ApiError):
        asyncio.run(pa.call("default", "http://api.example.org/x"))           # not https
    from app import web
    monkeypatch.setattr(web, "_public_host", lambda host: (_ for _ in ()).throw(web.WebError("private")))
    with pytest.raises(pa.ApiError):
        asyncio.run(pa.call("default", "https://127.0.0.1/admin"))


def test_owner_key_is_added_on_the_server_and_never_shown(env, monkeypatch):
    from app.publicapis import service as pa
    got = {}

    def handler(req):
        got["url"], got["h"] = str(req.url), dict(req.headers)
        return httpx.Response(200, json={"ok": True})
    _mock(handler, monkeypatch)
    keyed = pa.find("weather", auth="key", limit=1)["results"][0]["id"]
    with pytest.raises(pa.ApiError) as e:
        asyncio.run(pa.call("default", "https://api.w.example/now", {"q": "Akola"}, keyed))
    assert "Public APIs" in str(e.value)
    pa.save_key("default", keyed, "SECRET123", "query", "appid")
    out = asyncio.run(pa.call("default", "https://api.w.example/now", {"q": "Akola"}, keyed))
    assert "appid=SECRET123" in got["url"] and "SECRET123" not in json.dumps(out)
    rec = pa.recipes_for([keyed])[keyed][0]
    assert "SECRET" not in rec["call"] and "appid" not in rec["params"]
    pa.save_key("default", keyed, "HDRKEY99", "header", "X-Api-Key")
    asyncio.run(pa.call("default", "https://api.w.example/now", None, keyed))
    assert got["h"].get("x-api-key") == "HDRKEY99"
    assert pa.list_keys("default")[0]["api_id"] == keyed and "HDRKEY99" not in json.dumps(pa.list_keys("default"))
    with pytest.raises(pa.ApiError):     # the model can't sneak a key in without an api id
        asyncio.run(pa.call("default", "https://api.w.example/now?api_key=abc"))


def test_tools_registered_and_api(env):
    from fastapi.testclient import TestClient
    from app.agent.tools import HANDLERS
    from app.main import app
    from app.voice import VOICE_TOOL_NAMES
    assert {"api_find", "api_docs", "api_call"} <= set(HANDLERS) and "api_call" in VOICE_TOOL_NAMES
    with TestClient(app) as c:
        r = c.get("/api/publicapis", params={"q": "holidays"}).json()
        assert r["total"] > 2000 and r["results"]
        aid = r["results"][0]["id"]
        assert c.put(f"/api/publicapis/{aid}/key", json={"key": "abcd1234"}).json()["saved"]
        assert c.get("/api/publicapis/keys").json()["keys"][0]["api_id"] == aid
        assert c.delete(f"/api/publicapis/{aid}/key").json()["deleted"]
        assert c.get("/api/publicapis").json()["categories"]
