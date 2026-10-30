"""v0.262.0 EVERY MODEL, PRICE FIRST (video Phase 1): every model in her picker, and the price of every video before it is made."""
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"

# The real pricing_skus shapes in OpenRouter's live video list (29 Oct 2026)
LIVE = [
    {"id": "alibaba/wan-3.0", "name": "Alibaba: Wan 3.0", "supported_resolutions": ["480p", "720p", "1080p"],
     "supported_durations": list(range(2, 31)), "pricing_skus": {"duration_seconds_480p": "0.05", "duration_seconds_720p": "0.1",
                                                              "duration_seconds_1080p": "0.2"}},
    {"id": "google/veo-3.1-fast", "name": "Google: Veo 3.1 Fast", "supported_resolutions": ["720p", "1080p", "4K"],
     "supported_durations": [4, 6, 8],
     "pricing_skus": {"duration_seconds_with_audio": "0.12", "duration_seconds_with_audio_4k": "0.30",
                      "duration_seconds_without_audio": "0.10", "duration_seconds_with_audio_720p": "0.10",
                      "duration_seconds_without_audio_4k": "0.25", "duration_seconds_without_audio_720p": "0.08"}},
    {"id": "runway/gen-4.5", "name": "Runway: Gen-4.5", "supported_resolutions": ["720p"], "supported_durations": list(range(2, 11)),
     "pricing_skus": {"cents_per_second_output": "12"}},
    {"id": "x-ai/grok-imagine-video-1.5", "name": "SpaceXAI: Grok Imagine Video 1.5", "supported_resolutions": ["480p", "720p", "1080p"],
     "supported_durations": list(range(1, 16)),
     "pricing_skus": {"cents_per_image_input": "1", "cents_per_video_output_second_480p": "8",
                      "cents_per_video_output_second_720p": "14", "cents_per_video_output_second_1080p": "25"}},
    {"id": "bytedance/seedance-1-5-pro", "name": "ByteDance: Seedance 1.5 Pro", "supported_resolutions": ["480p", "720p", "1080p"],
     "supported_durations": list(range(4, 13)), "pricing_skus": {"video_tokens": "0.0000024", "video_tokens_without_audio": "0.0000012"}},
    {"id": "kwaivgi/kling-v3.0-pro", "name": "Kling: Kling 3.0 Pro", "supported_resolutions": ["720p"], "supported_durations": list(range(3, 16)),
     "pricing_skus": {"duration_seconds": "0.112", "duration_seconds_with_audio": "0.168", "text_to_video_duration_seconds_720p": "0.112",
                      "image_to_video_duration_seconds_720p": "0.112"}},
    {"id": "runway/aleph-2", "name": "Runway: Aleph 2.0", "pricing_skus": {"cents_per_second_output": "28", "minimum_cents_per_generation": "56"}},
    {"id": "heygen/avatar-iv", "name": "HeyGen: Avatar IV", "supported_resolutions": ["720p", "1080p"], "pricing_skus": {"duration_seconds": "0.05"}},
]


def test_parse_skus_reads_every_live_shape():
    from app.studio import catalog as c
    by = {d["id"]: c.parse_skus(d["pricing_skus"], d.get("supported_resolutions")) for d in LIVE}
    assert by["alibaba/wan-3.0"][0] == {"480p": 0.05, "720p": 0.1, "1080p": 0.2}
    w, wo, _ = by["google/veo-3.1-fast"]
    assert w == {"4k": 0.30, "720p": 0.10, "1080p": 0.12} and wo == {"4k": 0.25, "720p": 0.08, "1080p": 0.10}
    assert by["runway/gen-4.5"][0] == {"720p": 0.12}                         # cents, not dollars
    assert by["x-ai/grok-imagine-video-1.5"][0] == {"480p": 0.08, "720p": 0.14, "1080p": 0.25}   # image INPUT price skipped
    w, wo, _ = by["bytedance/seedance-1-5-pro"]                                # tokens: width x height x 24 / 1024 per second
    assert w["1080p"] == pytest.approx(0.0000024 * 48_600, rel=1e-3) and wo["480p"] == pytest.approx(0.0000012 * 9_607, rel=1e-3)
    w, wo, _ = by["kwaivgi/kling-v3.0-pro"]                                    # unmarked next to "_with_audio" = the silent rate
    assert w == {"720p": 0.168} and wo["720p"] == 0.112
    assert by["runway/aleph-2"][2] == pytest.approx(0.56)                      # minimum per generation


def test_rate_picks_the_resolution_and_the_sound():
    from app.studio import catalog as c
    m = {"usd_by_res": {"720p": 0.10, "1080p": 0.12, "4k": 0.30}, "usd_by_res_noaudio": {"720p": 0.08}, "usd_per_s": 0.5}
    assert c.rate(m, "1080p") == 0.12 and c.rate(m, "2160p") == 0.30 and c.rate(m, "480p") == 0.10 and c.rate(m, "2k") == 0.30
    assert c.rate(m, "720p", audio=False) == 0.08
    assert c.rate({"usd_per_s": 0.2}, "720p") == 0.2


def _studio(tmp_path, monkeypatch, live=True):
    from app.studio import studio as stmod
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    st = stmod.Studio(tmp_path / "st")

    async def fake_list():
        return LIVE
    st.providers["openrouter"].list_models = fake_list
    if live:
        asyncio.run(st.models_sync())
    return st


def test_models_sync_brings_live_models_and_prices(tmp_path, monkeypatch):
    st = _studio(tmp_path, monkeypatch)
    assert st.models["or-wan-3"]["usd_by_res"]["1080p"] == 0.2 and st.models["or-wan-3"]["price_live"]
    assert st.models["or-wan-3"]["allowed_durations"][-1] == 30
    gen = next(k for k, m in st.models.items() if m.get("model") == "runway/gen-4.5")
    assert st.models[gen]["usd_by_res"] == {"720p": 0.12}
    al = next(k for k, m in st.models.items() if m.get("model") == "runway/aleph-2")
    assert st.models[al]["min_usd"] == pytest.approx(0.56)
    assert "4k" in st.models["or-veo-3.1-fast"]["resolutions"] and st.synced_at


def _project(st, prefs=None):
    st.create("p1", aspect="16:9", style="ad", language="English", brief="chai ad")
    st.storyboard_set("p1", [{"kind": "scene", "prompt": "Steam over a kulhad of chai", "duration": 8},
                             {"kind": "product", "prompt": "The chai cup turns", "duration": 6}])
    if prefs:
        p = st.load("p1")
        p["prefs"] = prefs
        st.save(p)


def test_her_model_and_resolution_drive_the_estimate(tmp_path, monkeypatch):
    st = _studio(tmp_path, monkeypatch)
    _project(st, {"model": "or-veo-3.1-fast", "resolution": "4k"})
    e = st.estimate("p1", "final")
    assert {r["model"] for r in e["shots"]} == {"or-veo-3.1-fast"}
    assert {r["resolution"] for r in e["shots"]} == {"4k"}
    assert e["usd"] == pytest.approx(8 * 0.30 + 6 * 0.30)                      # Veo allows 4/6/8 s
    # a scene's own model wins over the film's
    st.shot_update("p1", st.load("p1")["shots"][1]["id"], {"model": "or-wan-3"})
    e = st.estimate("p1", "final")
    assert [r["model"] for r in e["shots"]] == ["or-veo-3.1-fast", "or-wan-3"]
    # a model that cannot run here (no key) falls back to Hoola Auto instead of failing
    p = st.load("p1")
    p["prefs"] = {"model": "gemini-omni-flash"}
    st.save(p)
    assert st.pref_model(st.load("p1")) is None


def test_minimum_charge_counts(tmp_path, monkeypatch):
    st = _studio(tmp_path, monkeypatch)
    al = next(k for k, m in st.models.items() if m.get("model") == "runway/aleph-2")
    st.models[al].update(durations=[2, 10], resolutions=["720p"], aspects=["16:9"], usd_by_res={"720p": 0.1})
    _project(st, {"model": al})
    st.storyboard_set("p1", [{"kind": "scene", "prompt": "x", "duration": 2}])
    assert st.estimate("p1", "final")["usd"] == pytest.approx(0.56)            # 2 s x 0.10 < the 0.56 minimum


def test_price_card_is_itemised_and_matches_the_run_cap(env, monkeypatch, tmp_path):
    from app.studio import service as ss
    st = _studio(tmp_path, monkeypatch)
    _project(st, {"model": "or-wan-3", "resolution": "1080p"})
    q = ss.quote(st, st.load("p1"), "final")
    assert [r["name"] for r in q["rows"]] == ["Wan 3.0", "Wan 3.0"] and [r["seconds"] for r in q["rows"]] == [8, 6]
    k = env["settings"].studio_usd_inr
    assert q["rows"][0]["inr_per_s"] == pytest.approx(0.2 * k, abs=0.01)
    assert q["cap_usd"] == pytest.approx(14 * 0.2) and sum(r["inr"] for r in q["rows"]) == pytest.approx(14 * 0.2 * k, abs=0.2)


def test_catalogue_and_live_price_endpoints(env, monkeypatch, tmp_path):
    from app import main
    from app.studio import service as ss
    st = _studio(tmp_path, monkeypatch)
    monkeypatch.setattr(ss, "studio_sync", lambda tenant: st)
    with TestClient(main.app) as c:
        d = c.get("/api/studio/models").json()
        names = {m["name"]: m for m in d["models"]}
        # ready live models, the key that switches others on, the rest of the market, and what is not offered
        assert names["Runway Gen-4.5"]["ready"] and names["Runway Gen-4.5"]["inr_per_s"]["720p"] == pytest.approx(0.12 * d["usd_inr"], abs=0.01)
        assert names["Grok Imagine Video 1.5"]["status"] == "ready"
        assert names["Gemini Omni 1.1 Flash"]["status"] == "needs_key" and "GEMINI_API_KEY" in names["Gemini Omni 1.1 Flash"]["why"]
        assert names["Kling 4.0"]["status"] == "coming" and names["Vidu Q4"]["status"] == "coming"
        assert names["Avatar IV"]["status"] == "coming" and not names["Avatar IV"]["ready"]
        assert not any("Aleph" in n for n in names)                               # edit-only models are not new-clip models
        assert {x["name"] for x in d["not_offered"]} >= {"Sora 2 (OpenAI)", "Utopai X"}
        top = [m["name"] for m in d["models"] if m["tier"] == "top" and m["ready"]]
        assert top.index("Wan 3.0") < top.index("Veo 3.1 Fast") < top.index("Runway Gen-4.5")   # leaderboard order
        r = c.post("/api/studio/price", json={"model": "or-veo-3.1-fast", "seconds": 7, "resolution": "4k", "takes": 2}).json()
        assert r["seconds"] == 8 and r["resolution"] == "4k" and r["usd"] == pytest.approx(8 * 0.30 * 2) and "seconds" in r["changed"]
        r = c.post("/api/studio/price", json={"model": "or-veo-3.1-fast", "seconds": 8, "resolution": "720p", "audio": False}).json()
        assert r["usd"] == pytest.approx(8 * 0.08)
        auto = c.post("/api/studio/price", json={"seconds": 10, "resolution": "1080p"}).json()
        assert auto["auto"] and auto["model"] in st.models and auto["usd"] > 0
        assert c.post("/api/studio/price", json={"model": "nope"}).status_code == 400


def test_new_project_keeps_her_picks_and_shots_take_a_model():
    src = (ROOT / "server" / "app" / "main.py").read_text()
    new = src[src.index("class StudioNew(BaseModel):"):src.index("class StudioPlan(BaseModel):")]
    assert "model: str = Field(" in new and "resolution: str = Field(" in new
    assert '"model": body.model,' in src and '"resolution": body.resolution' in src
    shot = src[src.index("class StudioShot(BaseModel):"):src.index("class StudioMusic(BaseModel):")]
    assert "model: str | None" in shot
    sets = src[src.index("class StudioSettings(BaseModel):"):src.index("class StudioAddShot(BaseModel):")]
    assert "model: str | None" in sets and "resolution: str | None" in sets


def test_console_picker_live_price_and_itemised_card():
    js, css = (CON / "studio.js").read_text(), (CON / "studio.css").read_text()
    for k in ('<div class="picker" id="picker" hidden></div>', "async function picker(ctx)", "function compareHTML()",
              "'/api/studio/models'", "'/api/studio/price'", "data-pickmodel", "data-vres", "data-vaudio", "data-vtake",
              "data-pmodel", "data-pres", "data-smodel", "data-dnewmodel", "Compare up to 3 models", "Hoola Auto",
              "You are never charged more than", "Haan, make it · ${inr(a.inr)}", "class=\"aprows\"", "money(rateAt(m, res) * s.duration)"):
        assert k in js, k
    assert "id=\"vidPrev\"" in js and "newClip(true)" in js                      # the free preview stays one tap
    for k in (".picker{", ".mcard{", ".mprice{", ".cmp{", ".pricebox{", ".aprows{"):
        assert k in css, k
    assert css.count("{") == css.count("}")
