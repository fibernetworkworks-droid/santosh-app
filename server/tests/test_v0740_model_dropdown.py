"""v0.740 MODEL DROPDOWN (owner: "IN WEB CONSOLE LETS USER CHOOSE THE MODEL VIA DROPDOWN"): each user picks the chat
model from the owner's list in the console composer; her turns run on it, through the v0.739 model profile."""
from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import gz, txt  # noqa: F401
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

FIX = Path(__file__).parent / "fixtures"
GLM = json.loads((FIX / "or_z-ai_glm-5.3-flash.json").read_text())
DS = json.loads((FIX / "or_deepseek_deepseek-chat-v3.1.json").read_text())
NOTOOLS = copy.deepcopy(DS)
for _e in NOTOOLS["data"]["endpoints"]:
    _e["supported_parameters"] = [p for p in _e["supported_parameters"] if p not in ("tools", "tool_choice")]
ANS = {"z-ai/glm-5.3-flash": GLM, "deepseek/deepseek-chat-v3.1": DS, "acme/notools": NOTOOLS}


@pytest.fixture()
def dd(env, monkeypatch, tmp_path):
    from app.agent import modelprofile
    from app.config import get_settings
    for k, v in {"MODEL_PROFILE": "true", "CHAT_MODEL_CHOICE": "true", "MODEL_PROFILE_DIR": str(tmp_path / "mp"),
                 "MODEL_CHOICE_DIR": str(tmp_path / "mc"), "GLM_API_KEY": "k", "CHAT_LLM": "glm",
                 "GLM_BASE_URL": "https://openrouter.ai/api/v1", "GLM_MODEL": "z-ai/glm-5.3-flash",
                 "CHAT_MODELS": "deepseek/deepseek-chat-v3.1,acme/notools"}.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    modelprofile._reset_for_tests()
    monkeypatch.setattr(modelprofile, "refresh_in_background", lambda model="": None)

    def get(url, headers=None, timeout=None):
        for slug, data in ANS.items():
            if f"/models/{slug}/endpoints" in url:
                return httpx.Response(200, json=data, request=httpx.Request("GET", url))
        return httpx.Response(404, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", get)
    for m in ANS:
        modelprofile.refresh(model=m)
    yield
    modelprofile._reset_for_tests()
    get_settings.cache_clear()


def test_the_list_is_the_owners_and_described_from_each_models_own_list(dd):
    from app import modelchoice as mc
    v = mc.view("default")
    assert v["available"] and [m["id"] for m in v["models"]] == ["z-ai/glm-5.3-flash", "deepseek/deepseek-chat-v3.1",
                                                                  "acme/notools"]
    glm, ds, nt = v["models"]
    assert glm["default"] and glm["selected"] and "image" in glm["reads"] and glm["pickable"]
    assert ds["reads"] == ["text"] and ds["pickable"] and not ds["selected"]
    assert nt["pickable"] is False and "no tools" in nt["note"]


def test_pick_is_per_user_and_checked(dd):
    from app import modelchoice as mc
    mc.choose("default", "deepseek/deepseek-chat-v3.1")
    assert mc.chosen("default") == "deepseek/deepseek-chat-v3.1" and mc.chosen("someone_else") == ""
    with pytest.raises(mc.ChoiceError, match="not on this server"):
        mc.choose("default", "openai/gpt-9-ultra")          # never a model the owner did not allow
    with pytest.raises(mc.ChoiceError, match="no tools"):
        mc.choose("default", "acme/notools")
    mc.choose("default", "z-ai/glm-5.3-flash")              # the default = no stored choice
    assert mc.chosen("default") == ""


def test_a_removed_model_falls_back_to_the_default(dd, monkeypatch):
    from app import modelchoice as mc
    from app.config import get_settings
    mc.choose("default", "deepseek/deepseek-chat-v3.1")
    monkeypatch.setenv("CHAT_MODELS", "")
    get_settings.cache_clear()
    assert mc.chosen("default") == ""


def test_her_turn_runs_on_her_pick(dd, gz, monkeypatch):  # noqa: F811
    from app import modelchoice as mc
    from app.agent import llm, santosh
    mc.choose("default", "deepseek/deepseek-chat-v3.1")
    seen = []

    async def fake(brain, system, tools, messages, max_tokens):
        url, model, label, h, extra = llm._target(brain)
        seen.append((model, llm.glm_reads_images(brain)))
        return [txt("ok")], "end_turn", {}
    monkeypatch.setattr(llm, "_openai_create", fake)
    monkeypatch.setattr(llm, "_openai_stream", lambda brain, s, t, m, mt, *a, **k: fake(brain, s, t, m, mt))
    out = asyncio.run(santosh.run_turn(gz["conv"], "hello", tenant_id="default"))
    assert "ok" in out and seen and seen[0] == ("deepseek/deepseek-chat-v3.1", False)   # its model + its own abilities
    assert llm.MODEL_NOW.get() == ""                         # nothing leaks out of her turn


def test_routes_need_the_key_and_say_why_when_not_offered(dd, monkeypatch):
    from app.config import get_settings
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    v = c.get("/api/model/choices").json()
    assert v["available"] and len(v["models"]) == 3
    assert c.put("/api/model/choice", json={"model": "deepseek/deepseek-chat-v3.1"}).json()["selected"] == \
        "deepseek/deepseek-chat-v3.1"
    assert c.put("/api/model/choice", json={"model": "nope/nope"}).status_code == 400
    monkeypatch.setenv("CHAT_LLM", "claude")                 # v0.741: offered on any OpenAI-style chat, not on Claude
    get_settings.cache_clear()
    v = c.get("/api/model/choices").json()
    assert v["available"] is False and "Claude" in v["reason"]
    monkeypatch.setenv("API_KEY", "k-test-1")
    get_settings.cache_clear()
    assert c.get("/api/model/choices").status_code == 401


def test_console_has_the_dropdown():
    root = Path(__file__).parents[1] / "app" / "static" / "console"
    html, js, css = (root / "v2.html").read_text(), (root / "v2.js").read_text(), (root / "v2.css").read_text()
    assert 'id="modelBtn"' in html and 'aria-haspopup="menu"' in html
    assert "/api/model/choices" in js and "'/api/model/choice'" in js and "HoolaMenu.open(b, items" in js
    assert "#app #composer .modelb" in css and "@container composer (max-width:360px){ #app #composer .modelb .mname" in css


CHOICES = {"available": True, "reason": "", "selected": "z-ai/glm-5.3-flash", "models": [
    {"id": "z-ai/glm-5.3-flash", "name": "Z.ai: GLM 5.3 Flash", "free": False, "reads": ["image", "text", "video"],
     "tools": True, "context": 1048576, "default": True, "selected": True, "pickable": True, "note": ""},
    {"id": "nvidia/nemotron-3.5-super-vl:free", "name": "NVIDIA: Nemotron 3.5 Super VL (free)", "free": True,
     "reads": ["image", "text", "video"], "tools": True, "context": 1000000, "default": False, "selected": False,
     "pickable": True, "note": ""},
    {"id": "acme/notools", "name": "Acme: No Tools", "free": True, "reads": ["text"], "tools": False, "context": 0,
     "default": False, "selected": False, "pickable": False, "note": "This model takes no tools, so Hoola cannot work with it."}]}


def test_dropdown_in_a_real_browser(arena_server):  # noqa: F811
    import os
    base, browser, key = arena_server
    picked = []
    for w in (1440, 700, 420):
        ctx = browser.new_context(viewport={"width": w, "height": 860})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))

        def choices(route):
            route.fulfill(json=CHOICES)

        def choice(route):
            body = json.loads(route.request.post_data or "{}")
            picked.append(body.get("model"))
            data = copy.deepcopy(CHOICES)
            for m in data["models"]:
                m["selected"] = m["id"] == body.get("model")
            data["selected"] = body.get("model")
            CHOICES.update(data)
            route.fulfill(json=data)
        pg.route("**/api/model/choices", choices)
        pg.route("**/api/model/choice", choice)
        pg.goto(base + "/console/")
        pg.wait_for_selector("#modelBtn:not([hidden])")
        row = pg.evaluate("""()=>{const r=document.querySelector('#composer .row').getBoundingClientRect(),
            b=document.getElementById('modelBtn').getBoundingClientRect(),
            s=document.getElementById('sendBtn').getBoundingClientRect();
            return {rl:r.left,rr:r.right,bl:b.left,br:b.right,bh:b.height,st:s.top,bt:b.top,label:document.querySelector('#modelBtn .mname').textContent}}""")
        assert row["bl"] >= row["rl"] - 1 and row["br"] <= row["rr"] + 1, (w, row)     # inside the typing box
        assert row["bh"] >= 28, (w, row)
        if w == 1440:
            assert "GLM 5.3 Flash" in row["label"] and "Z.ai" not in row["label"]
            pg.click("#modelBtn")
            pg.wait_for_selector("text=Nemotron 3.5 Super VL")
            if os.environ.get("CONSOLE_SHOTS"):
                pg.screenshot(path=os.path.join(os.environ["CONSOLE_SHOTS"], "v0740_dropdown.png"))
            assert pg.locator("text=This model takes no tools").count() == 1                # shown, not pickable
            pg.click("text=Nemotron 3.5 Super VL")
            for _ in range(50):
                if "Nemotron" in pg.locator("#modelBtn .mname").text_content():
                    break
                pg.wait_for_timeout(100)
            assert "Nemotron" in pg.locator("#modelBtn .mname").text_content()
        assert not errs, (w, errs)
        ctx.close()
    assert picked == ["nvidia/nemotron-3.5-super-vl:free"]
