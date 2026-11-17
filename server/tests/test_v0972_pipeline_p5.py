"""v0.972 HOOLA PIPELINE P5 - Hoola Code, background jobs and the studios on the Box (fake models only, no network).

Hoola Code: each coding call asks the Box for its kind of work (code HIGH, plan / summarise LOW), her composer pick is
a pin, a failing model hands over to the backups (at most two changes) and a banned one is off for the day; the fixed
dev_qwen_model stays the fallback (Box off / pipeline_code off / no tables). Background: routine / wake / long-job turns
go through the Box ranked for reliability. Studios: the Box orders the video / picture models the studio can run; the
studio keeps its own engine and price card."""
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib

import pytest

_spec = importlib.util.spec_from_file_location(
    "_p1", pathlib.Path(__file__).with_name("test_v0961_pipeline_choose.py"))
_p1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_p1)


def _doc():
    d = _p1.doc()
    d["tables"]["plan"] = {"same_as": "reason"}
    d["tables"]["summarise"] = copy.deepcopy(d["tables"]["chat"])
    d["tables"]["video.make"] = _p1._table({"ULTRA": [], "MAX": [_p1._m("bytedance/seedance-2.5", 30)],
                                            "HIGH": [_p1._m("google/veo-3.1-fast", 55),
                                                     _p1._m("alibaba/wan-3.0", 60)],
                                            "MID": [_p1._m("bytedance/seedance-2.0-fast", 90)], "LOW": []})
    d["tables"]["image.make"] = _p1._table({"ULTRA": [], "MAX": [], "HIGH": [_p1._m("google/gemini-3-pro-image", 55)],
                                            "MID": [_p1._m("google/gemini-3.1-flash-image", 85)], "LOW": []})
    return d


def _st(monkeypatch, **env):
    from app.config import get_settings
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()


@pytest.fixture
def box(env, tmp_path, monkeypatch):
    _st(monkeypatch, PIPELINE_DIR=str(tmp_path / "pl"), PIPELINE_ON="true", CHAT_GRAPH="false", DEV_BRAIN="qwen",
        OPENROUTER_API_KEY="or-key")
    from app.pipeline import store, turnbox as T, box as B
    from app.pipeline import surfaces as SF
    store.root().mkdir(parents=True, exist_ok=True)
    (store.root() / "current.json").write_text(json.dumps(_doc()))
    T._TABLES.update({"mtime": None, "doc": None})
    T._OUT.clear()
    T._DEAD.clear()
    B._STICKY.clear()
    SF._SAID.clear()
    from app.devsahayak import brain as DB
    DB.PICK.model, DB.PICK.effort = "", ""
    DB.session(None)
    monkeypatch.setattr(DB, "CLIENT", None)
    yield T
    DB.PICK.model, DB.PICK.effort = "", ""
    DB.session(None)
    T._DEAD.clear()
    T._OUT.clear()
    from app.config import get_settings
    get_settings.cache_clear()


def _answer(text="Done."):
    return {"choices": [{"finish_reason": "stop", "message": {"content": text}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 3}}


def _post(monkeypatch, script, seen):
    from app.devsahayak import brain as DB

    def post(url, body, headers, timeout):
        seen.append(body["model"])
        r = script.get(body["model"], _answer())
        if isinstance(r, Exception):
            raise r
        return r
    monkeypatch.setattr(DB, "QWEN_POST", post)


TOOLS = [{"name": "read_file", "description": "read", "input_schema": {"type": "object", "properties": {}}}]


# ------------------------------------------------------------------ Hoola Code
def test_a_coding_step_runs_on_the_box_model(box, monkeypatch):
    from app.devsahayak import brain as DB
    seen: list = []
    _post(monkeypatch, {}, seen)
    blocks, _ = DB.call("You are Hoola Code.", [{"role": "user", "content": "fix the login bug"}], TOOLS)
    assert blocks[0]["text"] == "Done."
    assert seen == ["a/high1"]                          # code starts at HIGH, score first


def test_each_kind_of_coding_call_gets_its_own_level(box, monkeypatch):
    from app.devsahayak import brain as DB
    seen: list = []
    _post(monkeypatch, {}, seen)
    with DB.part("summarise"):
        DB.call("Summarise.", [{"role": "user", "content": "the session"}], [])
    with DB.part("plan"):
        DB.call("Plan.", [{"role": "user", "content": "the ask"}], TOOLS)
    assert seen == ["a/low1", "a/low1"]                 # compaction and the plan pass start at LOW


def test_her_words_raise_the_level(box, monkeypatch):
    from app.devsahayak import brain as DB
    import types
    seen: list = []
    _post(monkeypatch, {}, seen)
    DB.session(types.SimpleNamespace(id="D-1", text="Fix the production payment bug before we deploy"))
    DB.call("x", [{"role": "user", "content": "go"}], TOOLS)
    assert seen == ["a/max1"]                           # costly (production / payment / deploy) -> MAX


def test_her_composer_pick_is_a_pin(box, monkeypatch):
    from app.devsahayak import brain as DB
    seen: list = []
    _post(monkeypatch, {}, seen)
    DB.PICK.model = "c/mid3"
    DB.call("x", [{"role": "user", "content": "fix it"}], TOOLS)
    assert seen == ["c/mid3"]
    DB.PICK.model = "claude-haiku-5-5"                   # a Claude name means nothing on the OpenRouter brain
    DB.call("x", [{"role": "user", "content": "fix it"}], TOOLS)
    assert seen[-1] == "a/high1"


def test_a_failing_model_hands_over_and_a_banned_one_is_off(box, monkeypatch):
    from app.devsahayak import brain as DB
    seen: list = []
    _post(monkeypatch, {"a/high1": DB.QwenError('OpenRouter answered 403: {"error":{"message":"Model a/high1 is banned"}}')},
          seen)
    blocks, _ = DB.call("x", [{"role": "user", "content": "fix it"}], TOOLS)
    assert blocks[0]["text"] == "Done."
    assert seen[0] == "a/high1" and seen[1] != "a/high1"
    assert box.health()["a/high1"]["paused"] is True    # banned: off for the day
    seen.clear()
    DB.call("x", [{"role": "user", "content": "again"}], TOOLS)
    assert "a/high1" not in seen                         # the next call starts on a backup


def test_at_most_two_changes(box, monkeypatch):
    from app.devsahayak import brain as DB
    seen: list = []
    err = DB.QwenError("OpenRouter answered 404: no endpoints found")
    _post(monkeypatch, {m: err for m in ("a/high1", "a/high2", "b/high3", "c/high4", "a/max1", "b/max2")}, seen)
    with pytest.raises(DB.QwenError):
        DB.call("x", [{"role": "user", "content": "fix it"}], TOOLS)
    assert len(seen) == 3                               # the model + two backups, then the error goes up


def test_her_key_or_credit_is_never_blamed_on_a_model(box, monkeypatch):
    from app.devsahayak import brain as DB
    seen: list = []
    _post(monkeypatch, {"a/high1": DB.QwenError("OpenRouter answered 402: insufficient credits")}, seen)
    with pytest.raises(DB.QwenError):
        DB.call("x", [{"role": "user", "content": "fix it"}], TOOLS)
    assert seen == ["a/high1"]                           # no backup asked: another model will not fix her credit
    assert "a/high1" not in box._DEAD


@pytest.mark.parametrize("env_off", [{"PIPELINE_CODE": "false"}, {"PIPELINE_ON": "false"}])
def test_the_fixed_model_is_the_fallback_switch(box, monkeypatch, env_off):
    from app.devsahayak import brain as DB
    seen: list = []
    _post(monkeypatch, {}, seen)
    _st(monkeypatch, **env_off)
    DB.call("x", [{"role": "user", "content": "fix it"}], TOOLS)
    assert seen == ["qwen/qwen3.8-27b"]                  # dev_qwen_model, exactly as before


def test_no_tables_keeps_the_fixed_model(box, monkeypatch):
    from app.devsahayak import brain as DB
    from app.pipeline import store
    (store.root() / "current.json").unlink()
    box._TABLES.update({"mtime": None, "doc": None})
    seen: list = []
    _post(monkeypatch, {}, seen)
    DB.call("x", [{"role": "user", "content": "fix it"}], TOOLS)
    assert seen == ["qwen/qwen3.8-27b"]


def test_callers_mark_their_kind():
    root = pathlib.Path(__file__).resolve().parents[1] / "app" / "devsahayak"
    assert 'B.part("summarise")' in (root / "engine.py").read_text()      # compaction
    assert "B.session(t)" in (root / "engine.py").read_text()             # the round
    loop = (root / "loop.py").read_text()
    assert '_B.PART.kind = "plan"' in loop and '_B.PART.kind = "check"' in loop
    assert 'B.part("summarise")' in (root / "memory.py").read_text()
    assert 'B.part("summarise")' in (root / "around.py").read_text()


# ------------------------------------------------------------------ background turns
def test_background_turns_go_through_the_box(box, monkeypatch):
    from app.agent import llm, providers
    monkeypatch.setattr(llm, "cheap_brain", lambda: "glm")
    monkeypatch.setattr(providers, "ready", lambda m: True)
    tok = llm.MODEL_NOW.set("")
    try:
        b = box.begin("conv_bg", "t1", "Aaj ki sales ka chhota summary bhejo", actor="routine")
        assert b is not None and b["sheet"]["surface"] == "background"
        assert b["sheet"]["parts"][0]["applied"] is True
        box.end(b, "Summary: 3 orders.")
        _st(monkeypatch, PIPELINE_BACKGROUND="false")
        b = box.begin("conv_bg", "t1", "Aaj ki sales ka chhota summary bhejo", actor="routine")
        assert b["sheet"]["parts"][0]["applied"] is False
        assert "pipeline_background is off" in b["sheet"]["parts"][0]["not_applied"]
        box.end(b, "x")
    finally:
        llm.MODEL_NOW.reset(tok)


def test_background_ranks_reliability_first_and_waits_longer():
    from app.pipeline import choose as C, handover as H
    assert C.ORDER["background"][0] == "reliability"
    assert H.first_word_limit("background") > H.first_word_limit("chat")


# ------------------------------------------------------------------ studios
def test_video_studio_takes_the_box_order_of_its_own_models(box):
    from app.pipeline import surfaces as SF
    ready = ["or-wan-3", "gemini-omni-flash", "or-seedance-2"]
    names = {"or-wan-3": ["alibaba/wan-3.0"], "gemini-omni-flash": ["gemini-omni-1.1-flash"],
             "or-seedance-2": ["bytedance/seedance-2.0"]}
    o = SF.studio_order("video.make", "HIGH", ready, names)
    assert o["order"][0] == "or-wan-3" and o["box"] == "alibaba/wan-3.0"
    # a model the tables rank higher but the studio cannot run is never forced; unknown ones keep their place after
    o = SF.studio_order("video.make", "HIGH", ["gemini-omni-flash", "or-seedance-2-fast"],
                        {"or-seedance-2-fast": ["bytedance/seedance-2.0-fast"]})
    assert o["order"] == ["or-seedance-2-fast", "gemini-omni-flash"]


def test_video_model_for_uses_the_box_and_the_price_card_follows(box, monkeypatch):
    from app.studio import studio as SS, catalog
    st = SS.Studio.__new__(SS.Studio)
    st.models = catalog.MODELS

    class P:
        def ready(self):
            return True
    st.providers = {k: P() for k in ("openrouter", "fal", "byteplus", "gemini", "google", "sync", "offline")}
    m = st.model_for({"kind": "scene"}, "final", None, None, ("quality", "1080p"))
    assert m == "or-wan-3"                                # the Box's HIGH video model among the ready ones
    _st(monkeypatch, PIPELINE_STUDIOS="false")
    m = st.model_for({"kind": "scene"}, "final", None, None, ("quality", "1080p"))
    assert m == catalog.ROUTES["scene"]["final"][0]       # the route's own first, as before


def test_image_studio_order(box, monkeypatch):
    from app import photogen
    monkeypatch.setattr(photogen, "_GOOD", {})
    assert photogen.models_for("best")[0] == "gemini-3-pro-image"
    assert photogen.models_for("fast")[0] == "gemini-3.1-flash-image"     # the Box's MID picture model first
    _st(monkeypatch, PIPELINE_STUDIOS="false")
    assert photogen.models_for("fast") == photogen.FAST


def test_switches_and_version():
    from app.config import Settings
    f = Settings.model_fields
    assert f["pipeline_code"].default is True
    assert f["pipeline_background"].default is True
    assert f["pipeline_studios"].default is True
    assert f["pipeline_on"].default is False              # the Box itself stays off until P7
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.980.0")
