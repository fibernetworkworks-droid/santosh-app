"""v0.308 STUDIO APIS: which real engine behind Create is on - checked with one FREE call per provider, keys never shown."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]


def _run(monkeypatch, handler, **keys):
    from app.config import get_settings
    from app.studio import apis
    s = get_settings()
    for k in ("gemini_api_key", "openrouter_api_key", "anthropic_api_key", "sync_api_key", "fal_key", "ark_api_key"):
        monkeypatch.setattr(s, k, keys.get(k, ""))
    real = httpx.AsyncClient
    monkeypatch.setattr(apis.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    apis._CACHE.clear()
    return asyncio.run(apis.report(fresh=True))


def test_ready_refused_missing_and_never_the_key(monkeypatch):
    seen = []

    def handler(req: httpx.Request):
        seen.append((req.method, req.url.host, req.url.path))
        if "openrouter" in req.url.host:
            return httpx.Response(200, json={"data": {"limit_remaining": 12.5}})
        if "googleapis" in req.url.host:
            return httpx.Response(400, json={"error": {"status": "INVALID_ARGUMENT", "details": [{"reason": "API_KEY_INVALID"}]}})
        return httpx.Response(401, json={"error": "bad"})
    r = _run(monkeypatch, handler, openrouter_api_key="sk-or-SECRET1", gemini_api_key="AIza-SECRET2",
             anthropic_api_key="sk-ant-SECRET3", sync_api_key="sync-SECRET4")
    st = {e["id"]: (e["state"], e["detail"]) for e in r["engines"]}
    assert st["openrouter"] == ("ready", "credit left $12.50")
    assert st["gemini"][0] == "refused" and st["anthropic"][0] == "refused"
    assert st["sync"][0] == "unchecked" and st["fal"][0] == "missing" and st["ark"][0] == "missing"
    assert all(m == "GET" for m, _, _ in seen)                                   # free listing calls only, never a job
    assert {p for _, _, p in seen} <= {"/api/v1/key", "/v1beta/models", "/v1/models"}
    blob = json.dumps(r)
    assert "SECRET" not in blob                                                  # no key ever in the report
    f = {x["name"]: x for x in r["features"]}
    assert f["Video clips"]["ready"] and not f["Pictures"]["ready"] and "Google Gemini" in f["Pictures"]["why"]
    assert f["Lip sync"]["ready"]                                                # a set key without a free check counts


def test_unreachable_provider(monkeypatch):
    def handler(req):
        raise httpx.ConnectError("down", request=req)
    r = _run(monkeypatch, handler, gemini_api_key="k")
    assert next(e for e in r["engines"] if e["id"] == "gemini")["state"] == "unreachable"


def test_route_cli_and_vps_job():
    main = (ROOT / "server" / "app" / "main.py").read_text()
    assert '@app.get("/api/studio/apis", dependencies=[Depends(require_key)])' in main
    assert 'apis._CACHE.get("at", 0) > time.time() - 60' in main               # Check again at most once a minute
    wf = (ROOT / ".github" / "workflows" / "vps-ops.yml").read_text()
    assert "- studio_apis" in wf and ".venv/bin/python -m app.studio.apis" in wf
    assert "sed -E" not in wf.split("studio_apis)")[1].split(";;")[0]            # names only, values never read out


def test_engines_page():
    js = (ROOT / "server" / "app" / "static" / "console" / "studio.js").read_text()
    css = (ROOT / "server" / "app" / "static" / "console" / "studio.css").read_text()
    assert "['engines', 'Engines', 'sliders']" in js and "V.engines = () =>" in js and "'/api/studio/apis'" in js
    assert "Never paste a key into the chat" in js
    blk = css[css.index("v0.308 ENGINES"):]
    assert ".eg-card{" in blk and ".ed{" not in blk and ".bad{" not in blk   # no clash with the editor's .ed / red .bad
