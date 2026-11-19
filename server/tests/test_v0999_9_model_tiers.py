"""v0.999.9 MODEL TIERS (owner: "GO BUILD THE TIERS"): ULTRA / HIGH / MEDIUM / LOW per user, the price ceiling on
every OpenRouter call of a known model, and the tier reaching the writer, helpers, calls, long jobs, Hoola Code, the
Web Studio and the video studio."""
from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def tz(env, monkeypatch, tmp_path):
    from app.config import get_settings
    for k, v in {"MODEL_TIER_DIR": str(tmp_path / "mt"), "GLM_API_KEY": "k", "CHAT_LLM": "glm",
                 "GLM_BASE_URL": "https://openrouter.ai/api/v1", "GLM_MODEL": "z-ai/glm-5.3-flash",
                 "MODEL_TIERS": "true", "MODEL_PRICE_CAP": "true"}.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_every_job_has_four_tiers_two_companies_and_a_price():
    from app import tiers as T
    for job, row in T.TABLE.items():
        assert list(row) == T.ORDER, job
        for tier, ids in row.items():
            assert len(ids) == 2, (job, tier)
            assert ids[0].split("/")[0] != ids[1].split("/")[0], (job, tier, ids)   # a backup from another company
            for mid in ids:
                assert mid in T.PRICE, mid
    assert set(T.KIND_JOB.values()) <= set(T.TABLE)
    assert set(T.VIDEO) == set(T.ORDER) and set(T.COST) == set(T.ORDER)


def test_ultra_needs_her_yes_and_the_choice_is_kept_per_user(tz):
    from app import tiers as T
    assert T.chosen("a") == ""
    with pytest.raises(T.TierError) as e:
        T.set_tier("a", "ultra")
    assert "credit" in str(e.value).lower() and T.chosen("a") == ""
    v = T.set_tier("a", "ultra", confirm_ultra=True)
    assert v["selected"] == "ultra" and T.chosen("a") == "ultra" and T.chosen("b") == ""
    T.set_tier("a", "medium")
    assert T.chosen("a") == "medium"
    T.set_tier("a", "")
    assert T.chosen("a") == ""
    with pytest.raises(T.TierError):
        T.set_tier("a", "gold")


def test_tiers_are_not_offered_without_openrouter(tz, monkeypatch):
    from app import tiers as T
    from app.config import get_settings
    monkeypatch.setenv("CHAT_LLM", "claude")
    get_settings.cache_clear()
    ok, why = T.offered()
    assert not ok and "OpenRouter" in why
    assert T.chosen("a") == ""


def test_the_price_ceiling_is_the_makers_price_plus_a_quarter(tz):
    from app import tiers as T
    c = T.cap("z-ai/glm-5.3")
    assert c == {"prompt": 1.75, "completion": 5.5}
    assert T.cap("openrouter:z-ai/glm-5.3") == c
    assert T.cap("acme/unknown") is None
    ex = T.with_cap("z-ai/glm-5.3", {"reasoning": {"effort": "low"}, "provider": {"sort": "latency"}})
    assert ex["provider"] == {"sort": "latency", "max_price": c} and ex["reasoning"] == {"effort": "low"}
    assert T.with_cap("acme/unknown", {"x": 1}) == {"x": 1}


def test_llm_adds_the_ceiling_only_for_openrouter_and_drops_it_when_refused(tz):
    from app.agent import llm
    ex = llm._priced("GLM (OpenRouter)", "deepseek/deepseek-v4.1-flash-1017", {})
    assert ex["provider"]["max_price"] == {"prompt": 0.375, "completion": 1.5}
    assert llm._priced("GLM", "deepseek/deepseek-v4.1-flash-1017", {}) == {}
    body = {"model": "m", "provider": {"sort": "latency", "max_price": {"prompt": 1}}}
    assert llm._cap_refused(404, '{"error":{"message":"No endpoints found matching your data policy"}}', body)
    assert not llm._cap_refused(500, "No endpoints", body)
    assert not llm._cap_refused(404, "No endpoints", {"model": "m"})
    assert llm._uncap(body) == {"model": "m", "provider": {"sort": "latency"}}


def test_a_call_no_provider_can_serve_under_the_ceiling_is_asked_again_without_it(tz, monkeypatch):
    from app.agent import llm
    seen = []

    class C:
        async def post(self, url, json=None, headers=None, **k):
            seen.append(json)
            if "max_price" in (json.get("provider") or {}):
                return httpx.Response(404, text='{"error":{"message":"No endpoints found that can handle the '
                                                'requested parameters"}}', request=httpx.Request("POST", url))
            return httpx.Response(200, json={"ok": True}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm, "_client", lambda: C())
    body = {"model": "z-ai/glm-5.3", "provider": {"max_price": {"prompt": 1.75, "completion": 5.5}}}
    r = asyncio.run(llm._post_with_retry("https://openrouter.ai/api/v1/chat/completions", body, {}, "GLM (OpenRouter)"))
    assert r.status_code == 200 and len(seen) == 2 and "provider" not in seen[1]


def test_the_box_uses_her_tier_for_each_kind_of_work(tz):
    from app import tiers as T
    pick = {"model": {"id": "z-ai/glm-5.3", "route": "openrouter"}, "backups": [{"id": "qwen/qwen3.8-27b"}],
            "level_used": "MID", "why": []}
    out = T.apply_box(pick, "high", "reason", {"models": {}}, {"level": "MID", "surface": "chat"})
    assert out["model"]["id"] == "z-ai/glm-5.3-flash" and out["backups"][0]["id"] == "google/gemini-3.8-flash"
    assert out["backups"][-1]["id"] == "z-ai/glm-5.3"            # the tables' pick stays as the last safety
    assert any("tier HIGH" in w for w in out["why"])
    # a live call answers on the tier's call model
    call = T.apply_box(pick, "low", "chat", {"models": {}}, {"level": "MID", "surface": "call"})
    assert call["model"]["id"] == "anthropic/claude-haiku-5.5"
    # a model that cannot read a picture is passed over for a picture part
    doc = {"models": {"anthropic/claude-fable-5": {"outs": ["text"], "ins": ["text"], "tools": True}}}
    pic = T.apply_box(pick, "ultra", "read.image", doc, {"level": "ULTRA", "surface": "chat"})
    assert pic["model"]["id"] == "google/gemini-3.8-flash"
    # a kind the tiers do not cover keeps the Box's own pick
    assert T.apply_box(pick, "high", "image.make", {}, {"level": "MID"}) == pick


def test_the_writer_of_a_chat_is_the_tiers_chat_model(tz):
    from app.pipeline import writer as WR
    assert WR.fixed("medium") == ["z-ai/glm-5.3", "deepseek/deepseek-v4.1-flash-1017"]   # v0.999.11
    assert WR.fixed("") == WR.fixed()


def test_video_studio_starts_from_her_tier_and_her_own_choice_wins(tz):
    from app import tiers as T
    assert T.video_prefs("a") == {}
    T.set_tier("a", "low")
    assert T.video_prefs("a") == {"quality": "draft", "auto": "cheap", "resolution": "480p"}
    from app.studio import service as SS
    merged = SS._clean_prefs({**T.video_prefs("a"), **{"resolution": "1080p"}})
    assert merged["quality"] == "draft" and merged["auto"] == "cheap" and merged["resolution"] == "1080p"


def test_web_studio_and_hoola_code_follow_her_tier(tz):
    from app import tiers as T
    from app import usage
    from app.site import ai as SA
    T.set_tier("shop", "high")
    with usage.scope("shop", "site"):
        assert SA.web_model() == "anthropic/claude-sonnet-5.5"
    with usage.scope("other", "site"):
        assert SA.web_model() == (SA.get_settings().web_qwen_model or "qwen/qwen3.8-27b")
    from app.devsahayak import brain as DB

    class Task:
        text, id, tenant_id = "fix the test", "t1", "shop"
    DB.session(Task())
    assert DB.PART.tier == "high"
    DB.session(None)
    assert DB.PART.tier == ""


def test_the_routes_show_the_tiers_and_refuse_ultra_without_her_yes(tz):
    from app.main import app
    c = TestClient(app)
    v = c.get("/api/model/tier").json()
    assert v["available"] and [t["id"] for t in v["tiers"]] == ["ultra", "high", "medium", "low"]
    assert v["selected"] == "" and "credit" in v["ultra_warning"].lower()
    hi = next(t for t in v["tiers"] if t["id"] == "high")
    assert hi["models"]["chat"][0] == {"id": "google/gemini-4-hydrogen", "rs_step": 3.17}   # v0.999.11
    assert c.put("/api/model/tier", json={"tier": "ultra"}).status_code == 400
    assert c.put("/api/model/tier", json={"tier": "ultra", "confirm_ultra": True}).json()["selected"] == "ultra"
    assert c.put("/api/model/tier", json={"tier": ""}).json()["selected"] == ""


def test_the_console_menu_offers_the_tiers_above_the_models():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "app/static/console/v2.js").read_text()
    assert "/api/model/tier" in js and "confirm_ultra" in js and "function ultraAsk(" in js   # v0.999.23 the tier sheet
    assert "wins over the tier" not in js                                                    # no model list any more
