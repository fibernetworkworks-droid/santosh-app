"""v0.263.0 VIDEO PHASE 2: prices kept current, estimate vs actual (never above the card), her own clips per model,
Hoola Auto by quality / value / lowest price, and the same shot by 2-3 models on one price card."""
import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from .test_v0262_every_model import LIVE, _project, _studio

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"


def test_auto_modes_pick_quality_value_or_price(tmp_path, monkeypatch):
    st = _studio(tmp_path, monkeypatch)
    s = {"kind": "scene"}
    q = st.model_for(s, "final", None, None, ("quality", "1080p"))
    ready = [m for m in st.models and __import__("app.studio.catalog", fromlist=["x"]).ROUTES["scene"]["final"]
             if m in st.models and st.providers[st.models[m]["provider"]].ready()]
    assert q == ready[0]                                           # best ready model for the shot, as before
    from app.studio import catalog as c
    cheap = st.model_for(s, "final", None, None, ("cheap", "1080p"))
    assert c.rate(st.models[cheap], "1080p") == min(c.rate(st.models[m], "1080p") for m in ready)
    value = st.model_for(s, "final", None, None, ("value", "1080p"))
    assert value in ready[:3] and c.rate(st.models[value], "1080p") == min(c.rate(st.models[m], "1080p") for m in ready[:3])
    # the film's auto mode reaches the estimate
    _project(st, {"auto": "cheap", "resolution": "1080p"})
    assert {r["model"] for r in st.estimate("p1", "final")["shots"] if r["model"] != "or-minimax-h3"} <= set(ready)


def test_compare_makes_each_shot_with_each_model_on_one_card(env, tmp_path, monkeypatch):
    from app.studio import service as ss
    st = _studio(tmp_path, monkeypatch)
    _project(st, {"resolution": "720p"})
    sid = st.load("p1")["shots"][0]["id"]
    q = ss.quote(st, st.load("p1"), "final", [sid], 1, None, ["or-wan-3", "or-veo-3.1-fast"])
    assert [r["model"] for r in q["rows"]] == ["or-wan-3", "or-veo-3.1-fast"] and q["compare"] == ["or-wan-3", "or-veo-3.1-fast"]
    assert q["cap_usd"] == pytest.approx(8 * 0.1 + 8 * 0.10)       # Wan 3.0 720p 0.1/s, Veo Fast 720p 0.10/s (8 s allowed)
    # the run makes one job per model, each capped by its own line
    started = []

    async def no_run(project, jid):
        started.append(jid)
    st._run_job = no_run
    r = asyncio.run(st.generate("p1", "final", [sid], 1, None, None, 0, ["or-wan-3", "or-veo-3.1-fast"]))
    jobs = st.load("p1")["jobs"]
    assert r["started"] == 2 and sorted(jobs[j]["model"] for j in r["jobs"]) == ["or-veo-3.1-fast", "or-wan-3"]
    assert all(jobs[j]["compare"] for j in r["jobs"])
    with pytest.raises(ss.StudioJobError):
        asyncio.run(ss.generate("default", "p1", "final", [sid], 1, None, "", ["or-wan-3"]))   # 2-3 models only


def test_she_never_pays_above_the_card_and_sees_estimate_vs_actual(env):
    from app.studio import service as ss
    p = {"approvals": {"a": {"status": "approved", "usd": 2.0}, "b": {"status": "rejected", "usd": 9}},
         "variants": {"s1": [{"quality": "final", "est_usd": 1.0, "actual_usd": 1.3, "cost_usd": 1.3, "billed_usd": 1.0},
                             {"quality": "final", "est_usd": 1.0, "actual_usd": 0.7, "cost_usd": 0.7, "billed_usd": 0.7},
                             {"quality": "preview", "cost_usd": 0}]}}
    k = env["settings"].studio_usd_inr
    m = ss.money_of(p)
    assert m["approved_inr"] == pytest.approx(2.0 * k, abs=0.1) and m["billed_inr"] == pytest.approx(1.7 * k, abs=0.1)
    assert m["actual_inr"] == pytest.approx(2.0 * k, abs=0.1) and m["saved_inr"] == pytest.approx(0.3 * k, abs=0.1)
    assert m["takes"] == 2
    src = (ROOT / "server" / "app" / "studio" / "studio.py").read_text()
    assert 'v["billed_usd"] = round(min(v["cost_usd"], j["cost_est"]), 4)' in src


def test_price_moves_are_recorded_across_restarts(tmp_path, monkeypatch):
    _studio(tmp_path, monkeypatch)                                  # first read: the saved list to compare against
    moved = json.loads(json.dumps(LIVE))
    moved[0]["pricing_skus"]["duration_seconds_1080p"] = "0.15"    # Wan 3.0 1080p 0.20 -> 0.15

    async def fake_list():
        return moved
    from app.studio import studio as stmod
    st2 = stmod.Studio(tmp_path / "st")                             # a restart: the new process compares with the saved list
    st2.providers["openrouter"].list_models = fake_list
    asyncio.run(st2.models_sync())
    ch = [c for c in st2.price_changes if c["model"] == "or-wan-3"]
    assert ch and ch[-1]["resolution"] == "1080p" and ch[-1]["old_usd"] == 0.2 and ch[-1]["new_usd"] == 0.15
    assert json.loads((tmp_path / "st" / "price_changes.json").read_text())[-1]["new_usd"] == 0.15


def test_models_endpoint_refreshes_stale_prices_and_shows_her_clips(env, tmp_path, monkeypatch):
    from app import main
    from app.studio import service as ss
    st = _studio(tmp_path, monkeypatch, live=False)
    calls = []
    orig = st.models_sync

    async def counting():
        calls.append(1)
        return await orig()
    st.models_sync = counting

    async def get_st(tenant):
        return st
    monkeypatch.setattr(ss, "studio", get_st)
    monkeypatch.setattr(ss, "studio_sync", lambda tenant: st)
    monkeypatch.setattr(ss, "_her_clips", lambda tenant, s, per=3: {"or-wan-3": [{"url": "/x.mp4", "project": "p1"}]})
    with TestClient(main.app) as c:
        d = c.get("/api/studio/models").json()
        assert calls == [1]                                         # never read -> read now
        assert next(m for m in d["models"] if m["key"] == "or-wan-3")["mine"][0]["url"] == "/x.mp4"
        c.get("/api/studio/models")
        assert calls == [1]                                         # fresh -> not again
        r = c.post("/api/studio/price", json={"seconds": 8, "resolution": "1080p", "auto": "cheap"}).json()
        assert r["auto_mode"] == "cheap" and "lowest price" in r["why"]
        assert c.post("/api/studio/price", json={"auto": "nope"}).status_code == 422


def test_console_phase2_pieces():
    js, css = (CON / "studio.js").read_text(), (CON / "studio.css").read_text()
    for k in ("data-amode", "onAuto", "onCompare", "data-cmpgo", "Make them side by side", "data-uncompare",
              "compare: !preview && VID.compare.length > 1 ? VID.compare : null", "'__cmp'", "class=\"pchg\"",
              "Your clips with it", "function moneyLine(mo)", "provider charged", "auto: VID.auto"):
        assert k in js, k
    for k in (".amodes{", ".mine video{", ".pchg{", ".cmpgo{", ".moneyl{"):
        assert k in css, k


def test_a_model_that_cannot_make_the_resolution_gets_the_closest_not_the_lowest():
    from app.studio import catalog as c
    assert c.nearest_res("1080p", ["480p", "720p"]) == "720p"       # was 480p (the model's first resolution)
    assert c.nearest_res("768p", ["720p", "1080p"]) == "1080p"      # ties go up
    assert c.nearest_res("720p", ["2K"]) == "2k"
    src = (ROOT / "server" / "app" / "studio" / "studio.py").read_text()
    assert 'res = catalog.nearest_res(want if want and quality != "preview" else q["resolution"], cfg["resolutions"])' in src
