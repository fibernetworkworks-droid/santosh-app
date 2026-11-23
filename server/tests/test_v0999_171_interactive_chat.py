"""v0.999.171 THE INTERACTIVE CHAT, REDESIGNED (owner: "MAKE THE INTERACTIVE CHAT SECTION MORE ADVANCE, PREMIUM, USER
FRIENDLY ... WE ARE DEVELOPING IT FOR WORLD NOT JUST FOR INDIA" -> design canvas claude.ai/artifact/5wm914F3jEgnNNfNr3rXPn
-> "GO BUILD"): the kind of video she picks reaches the script, Auto language by default, the price shown before anything
is planned, every engine priced for one draft, the planner written for the whole world, and the page itself walked in a
real browser at computer and phone width."""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time as _t
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.interactive import live as LV
from app.interactive import studio as S

DRAFT = {"title": "Bem-vindo ao Café Azul", "closing": "Até já",
         "scenes": [{"say": "Bem-vindo ao Café Azul!", "look": {"kind": "title", "text": "Café Azul"}},
                    {"say": "Entre, sinta-se em casa.", "look": {"kind": "none"}},
                    {"say": "Prove o nosso pastel de nata, feito todas as manhãs.", "look": {"kind": "none"}}]}
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def ix(env, monkeypatch, tmp_path):
    monkeypatch.setenv("INTERACTIVE_PAGE", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setattr(S, "_root", lambda: tmp_path)
    seen = []

    def brain(system, prompt):
        seen.append((system, prompt))
        return json.loads(json.dumps(DRAFT))
    monkeypatch.setattr(S, "_brain", brain)
    S._JOBS.clear()
    LV._VISITS.clear()
    yield seen
    S._JOBS.clear()
    get_settings.cache_clear()


def test_the_kind_reaches_the_script_and_the_planner_is_global(ix):
    p = S.draft("default", "Welcome new guests to my café in Lisbon", lang="pt", kind="explainer")
    system, prompt = ix[-1]
    assert "Style: Explainer" in prompt and "Language: Portuguese" in prompt
    assert "Indian" not in system and "anywhere in the world" in system
    assert p["kind"] == "explainer" and p["lang"] == "pt"
    q = S.draft("default", "Spring sale on all plants, as a reel", shape="reel")
    assert q["kind"] == "reel" and q["aspect"] == "9:16"
    S.draft("default", "Just a plain video about my shop", kind="nonsense")
    assert "Style:" not in ix[-1][1]
    from app.interactive import hub as H
    assert "Indian" not in H._TR_SYSTEM


def test_tool_takes_the_kind_and_the_chat_knows_auto():
    from app import interactivechat as IC
    from app.agent import create_tools as CT
    props = next(t for t in CT.CREATE_TOOLS if t["name"] == "create_studio")["input_schema"]["properties"]
    assert props["kind"]["enum"] == ["presenter", "explainer", "reel", "product", "lesson"]
    assert "Language 'auto'" in IC.RULES and "kind=" in IC.RULES
    assert "webfetch" in IC.FAMILIES
    assert S.KIND_SHAPE == {"reel": "reel", "product": "product"}


def test_estimate_and_compare_routes(ix):
    from app.main import app
    c = TestClient(app)
    e = c.get("/api/interactive/x/estimate?engine=kling&seconds=30").json()
    assert e["engine"] == "kling" and e["face_credits"] > 0 and e["seconds"] == 30 and e["key"]
    short = c.get("/api/interactive/x/estimate?engine=kling&seconds=15").json()
    assert short["face_credits"] < e["face_credits"]
    assert c.get("/api/interactive/x/estimate?engine=hoola&seconds=999").json()["seconds"] == 90    # length capped like a draft
    p = S.draft("default", "Welcome new guests to my café in Lisbon", lang="pt")
    r = c.get(f"/api/interactive/x/compare?id={p['id']}").json()
    ids = [x["id"] for x in r["engines"]]
    assert "hoola" in ids and "kling" in ids and r["chosen"] == p["engine"]
    by = {x["id"]: x for x in r["engines"]}
    assert by["kling_pro"]["credits"] > by["kling"]["credits"] and by["hoola"]["face_credits"] == 0
    assert all(x["what"] for x in r["engines"])
    assert c.get("/api/interactive/x/compare?id=iv_nope").status_code in (404, 409, 400)


def test_page_code_is_global_and_wired():
    root = ROOT / "app" / "static" / "console"
    js = (root / "interactive.js").read_text("utf-8")
    css = (root / "interactive2.css").read_text("utf-8")
    assert subprocess.run(["node", "--check", str(root / "interactive.js")], capture_output=True).returncode == 0
    assert "Diwali" not in js and "lang: 'auto'" in js and "Auto · matches what you write" in js
    for k in ("presenter", "explainer", "reel", "product", "lesson", "translate"):
        assert f"['{k}'," in js
    for a in ("'kind'", "'ideag'", "'from'", "'attach'", "'openv'", "'say'", "'morelang'", "'ipick'", "'flay'", "'hear'",
              "'cmp'", "'pvtab'", "'pvscene'", "'pvplay'", "'pvwhich'", "'subdl'", "'openchat'"):
        assert f"case {a}:" in js, a
    assert "/estimate?" in js and "/compare?id=" in js and "/api/vocal/hear" in js and "settingsNote" in js
    for c in (".hx-kinds", ".hx-plan", ".hx-scg", ".hx-prow", ".hx-pbox", ".hx-pv", ".hx-vgrid", ".hx-starts"):
        assert f"#hxRoot {c}" in css, c


# ------------------------------------------------------------------ the page in a real browser
@pytest.fixture
def ix_server(ix, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        _t.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        try:
            browser = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as e:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(e)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_the_chat_in_a_real_browser(ix_server):
    base, browser, key = ix_server
    shots = os.environ.get("HOOLA_SHOTS")
    errors: list[str] = []
    for vp in ({"width": 1440, "height": 900}, {"width": 390, "height": 844}):
        ctx = browser.new_context(viewport=vp)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}'); if (!localStorage.getItem('hx.langv2')) localStorage.setItem('hx.set', JSON.stringify({{lang: 'hi'}}))")   # an old browser that kept Hindi
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/?v=interactive")
        pg.wait_for_selector("#hxTopR [data-a=newchat]", timeout=25000)
        pg.wait_for_timeout(1500)                                   # Interactive opens on her last chat; then New video
        pg.click("#hxTopR [data-a=newchat]")
        pg.wait_for_selector("#hxRoot .hx-kinds", timeout=25000)
        # the old India default became Auto, the ideas are from around the world
        assert "Auto" in pg.inner_text("#hxChips")
        assert "Lisbon" in pg.inner_text(".hx-ideas") and "Diwali" not in pg.inner_text("#hxRoot")
        pg.click(".hx-kind.k-reel")
        assert pg.get_attribute(".hx-kind.k-reel", "aria-checked") == "true"
        assert "9:16" in pg.inner_text("#hxChips")
        pg.click(".hx-gtabs button:has-text('Teaching')")
        pg.click(".hx-idea >> nth=1")
        assert "photosynthesis" in pg.input_value("#hxAsk")
        assert "German" in pg.inner_text("#hxChips")
        pg.wait_for_function("document.querySelector('#hxEst') && /credit/.test(document.querySelector('#hxEst').textContent)", timeout=8000) if vp["width"] > 900 else None
        if shots:
            pg.screenshot(path=f"{shots}/ix171-home-{vp['width']}.png", full_page=True)
        # a plan in this chat: the plan card with its scenes, rows and price; the preview beside it
        conv = pg.evaluate("fetch('/api/interactive/chat', {headers: {Authorization: 'Bearer ' + localStorage.getItem('hoola.console.token')}}).then(r => r.json()).then(j => j.id)")
        S.draft("default", "Welcome new guests to my café in Lisbon, with English subtitles", lang="pt", chat=conv, kind="presenter")
        pg.goto(base + "/console/?v=interactive")
        pg.wait_for_selector("#hxRoot .hx-plan .hx-scg", timeout=25000)
        assert pg.locator(".hx-sct").count() == 3
        txt = pg.inner_text(".hx-plan")
        assert "Portuguese" in txt and "Total" in txt and "Make the video" in txt and "Compare engines" in txt
        assert pg.locator(".hx-sugg .hx-chip").count() >= 3
        pg.click(".hx-sct >> nth=2")
        assert "pastel de nata" in pg.inner_text("#hxPv")
        pg.click("#hxPv [data-a=pvtab][data-val=subs]")
        assert "00:00:00,000 -->" in pg.inner_text(".hx-srt")
        pg.click("#hxPv [data-a=pvtab][data-val=script]")
        assert pg.locator(".hx-pvscript textarea").count() == 3
        pg.click(".hx-plan [data-a=cmp]")
        pg.wait_for_selector("text=Price for this", timeout=8000)
        pg.keyboard.press("Escape")
        wide = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert wide <= 1, f"sideways scroll {wide}px at {vp['width']}"
        if shots:
            pg.screenshot(path=f"{shots}/ix171-plan-{vp['width']}.png", full_page=True)
        ctx.close()
    assert not errors, errors
