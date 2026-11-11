"""v0.747 HOOLA INTERACTIVE (owner: "a perfect Hoola Interactive page in console, same as HeyGen, with HyperFrames
in it end to end" -> the approved canvas -> "go"): one line -> scenes -> a real make job over the film pipeline,
numbers only from her words, consent-gated photo avatars, her videos kept, and the page walked in a real browser."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.interactive import studio as S
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

DRAFT = {"title": "Diwali offer", "closing": "Order today",
         "scenes": [{"say": "Is Diwali, apni mithas double karein.", "look": {"kind": "title", "text": "Diwali offer"}},
                    {"say": "Kaju katli par 20 percent ki chhoot.", "look": {"kind": "price", "new": "Rs 512", "old": "Rs 640"}},
                    {"say": "Teen saal se sabse pasand.", "look": {"kind": "bar_chart", "bars": [{"label": "2024", "value": "300"}, {"label": "2025", "value": "900"}]}},
                    {"say": "Station Road par aaiye.", "look": {"kind": "lower_third", "title": "Station Road", "sub": "Akola"}}]}
ASK = "A Diwali offer video for my sweet shop - 20% off kaju katli, now Rs 512 instead of Rs 640"


@pytest.fixture()
def iv(env, monkeypatch, tmp_path):
    monkeypatch.setenv("INTERACTIVE_PAGE", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setattr(S, "_root", lambda: tmp_path)
    monkeypatch.setattr(S, "_brain", lambda system, prompt: json.loads(json.dumps(DRAFT)))
    S._JOBS.clear()
    yield tmp_path
    S._JOBS.clear()


def client():
    return TestClient(__import__("app.main", fromlist=["app"]).app)


def test_draft_keeps_only_her_numbers(iv):
    p = S.draft("default", ASK)
    price, chart = p["scenes"][1], p["scenes"][2]
    assert price["look"]["new"] == "Rs 512" and price["needs"] == ""              # 512 and 640 are in her words
    assert chart["needs"] == "Needs your numbers" and all(b["value"] == "" for b in chart["look"]["bars"])   # 300 / 900 invented
    assert [b["label"] for b in chart["look"]["bars"]] == ["2024", "2025"]
    assert S.problems(p) == ["Scene 3 needs your numbers."]
    with pytest.raises(S.StudioError, match="needs your numbers"):
        S.make("default", p["id"])
    sc = [dict(s) for s in p["scenes"]]
    sc[2] = {"say": sc[2]["say"], "look": {"kind": "bar_chart", "bars": [{"label": "2024", "value": "300"}, {"label": "2025", "value": "900"}]}}
    p2 = S.save("default", p["id"], {"scenes": sc})                               # her own edit is trusted
    assert S.problems(p2) == [] and p2["scenes"][2]["look"]["bars"][1]["value"] == "900"


def test_looks_are_drawn_into_the_composition_and_plain_films_are_unchanged():
    from app.studio import avatar as av
    spec = {"shape": "talking_head", "silent": True, "scenes": [{"say": s["say"], "look": s["look"]} for s in DRAFT["scenes"]]}
    parts = av.validate_spec(spec)
    plan = av.timing_plan(parts["sentences"], [2.0] * 4, [1.5] * 4, None)
    html = av.build_html(parts, plan)
    assert html.count('id="look-') == 4 and 'class="bar"' in html and "Rs 512" in html and "line-through" in html
    assert 'tl.from("#look-2 .bar"' in html and "Math.random" not in html and "Date.now" not in html
    assert av.build_html(parts, plan) == html                                       # deterministic
    plain = av.validate_spec({"shape": "talking_head", "silent": True, "script": "Ek. Do."})
    plan2 = av.timing_plan(plain["sentences"], [2.0, 2.0], [1.5, 1.5], None)
    assert "look-" not in av.build_html(plain, plan2)
    with pytest.raises(Exception, match="at least two bars"):
        av.validate_spec({"shape": "reel", "silent": True, "scenes": [{"say": "x", "look": {"kind": "bar_chart", "bars": [{"label": "a", "value": "1"}]}}]})


def test_make_job_shows_real_steps_and_keeps_the_video(iv, tmp_path):
    mp4 = tmp_path / "out.mp4"
    mp4.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"0" * 100)
    seen = {}

    def film(tenant, spec, files=None, out_name="", on_stage=None, cancel=None):
        seen["spec"] = spec
        for k, d in (("voice", "1 of 4 lines"), ("align", "9 s of speech"), ("draw", "4 scenes, 9 s")):
            on_stage(k, d)
        return {"ok": True, "mp4_path": str(mp4), "duration_s": 9.1, "scenes": 4, "words_estimated": False}

    p = S.draft("default", ASK)
    sc = p["scenes"][:2]                                                            # drop the chart scene
    S.save("default", p["id"], {"scenes": sc})
    S.make("default", p["id"], film=film)
    for _ in range(200):
        v = S.job_view("default", p["id"])
        if v["done"]:
            break
        time.sleep(0.01)
    assert v["status"] == "ready" and [s["k"] for s in v["steps"] if s["at"] is not None] == ["voice", "align", "draw", "save", "done"]
    assert next(s for s in v["steps"] if s["k"] == "voice")["detail"] == "1 of 4 lines"
    got = S.project("default", p["id"])
    assert got["status"] == "ready" and got["video"]["duration"] == 9.1 and S.video_path("default", p["id"]).is_file()
    assert seen["spec"]["scenes"][1]["look"]["kind"] == "price" and seen["spec"]["cta"] == {"text": "Order today"}


def test_stop_keeps_nothing_and_failures_say_why(iv):
    gate = threading.Event()

    def slow(tenant, spec, files=None, out_name="", on_stage=None, cancel=None):
        on_stage("voice", "")
        gate.wait(2)
        if cancel.is_set():
            from app.studio.frames import FramesError
            raise FramesError("Stopped. Nothing was kept.")
        return {"ok": False, "errors": ["font missing"]}

    p = S.draft("default", ASK)
    S.save("default", p["id"], {"scenes": p["scenes"][:2]})
    S.make("default", p["id"], film=slow)
    with pytest.raises(S.StudioError, match="already being made"):
        S.make("default", p["id"], film=slow)
    assert S.stop("default", p["id"])
    gate.set()
    for _ in range(200):
        if S.job_view("default", p["id"])["done"]:
            break
        time.sleep(0.01)
    assert S.job_view("default", p["id"])["status"] == "stopped"
    assert S.project("default", p["id"])["status"] == "draft" and not S.video_path("default", p["id"]).exists()
    gate.set()
    S.make("default", p["id"], film=slow)
    for _ in range(200):
        if S.job_view("default", p["id"])["done"]:
            break
        time.sleep(0.01)
    pr = S.project("default", p["id"])
    assert pr["status"] == "failed" and "font missing" in pr["error"]


def test_photo_avatar_needs_consent_and_a_real_photo(iv, tmp_path):
    png = tmp_path / "upload"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 40)
    with pytest.raises(S.StudioError, match="consent"):
        S.add_avatar("default", "Priya", str(png), filename="me.png")
    fake = tmp_path / "x"
    fake.write_bytes(b"MZ not a photo")
    with pytest.raises(S.StudioError, match="not a real photo"):
        S.add_avatar("default", "Priya", str(fake), consent=True, filename="me.png")
    a = S.add_avatar("default", "Priya", str(png), consent=True, filename="me.png")
    p = S.draft("default", ASK, avatar_id=a["id"])
    spec, files = S.spec_for("default", p, silent=True)
    assert spec["avatar"] == "assets/avatar.png" and Path(files[0]["path"]).is_file()
    assert S.photo_path("other", a["id"]) is None                                  # tenant-scoped
    assert S.remove_avatar("default", a["id"]) and S.project("default", p["id"])["avatar_id"] == ""


def test_routes_are_key_protected_and_switch_gated(iv, monkeypatch):
    c = client()
    st = c.get("/api/interactive/studio/status").json()
    assert st["enabled"] and "draw" in st and "voice" in st
    p = c.post("/api/interactive/studio/draft", json={"ask": ASK}).json()
    assert p["id"].startswith("iv_") and len(p["scenes"]) == 4
    got = c.get(f"/api/interactive/studio/project?id={p['id']}").json()
    assert got["problems"] == ["Scene 3 needs your numbers."]
    assert c.post("/api/interactive/studio/make", json={"id": p["id"]}).status_code == 409
    assert c.get("/api/interactive/studio/video?id=" + p["id"]).status_code == 404
    assert c.get("/api/interactive/studio/project?id=nope").status_code == 404
    assert c.get("/api/console/config").json()["interactive"] is True
    assert c.delete(f"/api/interactive/studio/project?id={p['id']}").json()["ok"]
    monkeypatch.setenv("INTERACTIVE_PAGE", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert c.get("/api/interactive/studio/list").status_code == 403


LIST = {"running": "", "avatars": [{"id": "av_1", "name": "Priya", "kind": "photo", "lang": "hi"}], "projects": [
    {"id": "iv_a", "title": "Diwali offer", "shape": "reel", "status": "ready", "lang": "hi", "aspect": "9:16", "scenes": [],
     "video": {"duration": 31, "size": 7000000, "made_s": 124, "aspect": "9:16"}, "updated": "2026-11-10T10:00:00"},
    {"id": "iv_b", "title": "<b>Menu</b>", "shape": "talking_head", "status": "draft", "lang": "hi", "aspect": "16:9", "scenes": [{}],
     "updated": "2026-11-09T10:00:00"}]}
PROJ = {"id": "iv_b", "title": "<b>Menu</b>", "shape": "talking_head", "status": "draft", "lang": "hi", "aspect": "16:9",
        "avatar_id": "", "brand": "", "closing": "", "items": [], "ask": "x", "problems": ["Scene 2 needs your numbers."],
        "scenes": [{"say": "Namaste.", "look": {"kind": "title", "text": "Namaste"}, "needs": ""},
                   {"say": "Teen saal.", "look": {"kind": "bar_chart", "bars": [{"label": "2024", "value": ""}, {"label": "2025", "value": ""}]}, "needs": "Needs your numbers"}]}
STATUS = {"enabled": True, "draw": True, "voice": False, "whisper": False, "busy": False, "running": "",
          "langs": {"hi": "Hindi", "en": "English"}, "shapes": ["talking_head", "product", "reel"]}


OVERVIEW = {**LIST, "brand": {"name": "Sharma Traders", "closing": "", "color": "#7C3AED"}, "glossary": [], "trash": [], "brains": [],
            "templates": [{"id": "tp_offer", "name": "Festival offer", "group": "Offers", "shape": "talking_head", "mine": False,
                           "count": 3, "variables": ["shop", "price"], "scenes": []}],
            "usage": {"month": "2026-11", "videos": 1, "minutes": 0.5, "stored": 1, "kept_max": 40, "by_language": [], "recent": []},
            "limits": {"batch": 20, "trash_days": 30},
            "status": {**STATUS, "connected": {"video": True, "voice": False, "twin": False, "ai_face": False, "voice_clone": False,
                                               "dub_outside_video": False, "live_stream": False, "api": False}}}


def test_the_page_in_a_real_browser(arena_server):  # noqa: F811
    """v0.772: the page is its own full screen with its own sidebar. Every one of the twelve pages opens without a
    script error, her text is never run as HTML, what is not connected is SAID, and a missing number blocks Generate."""
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route("**/api/console/config", lambda r: r.fulfill(json={"app": "Hoola", "v2": True, "stream": True, "sessions": True,
                                                                   "panel": True, "projects": True, "human": True, "interactive": True}))
    pg.route("**/api/interactive/hub/overview", lambda r: r.fulfill(json=OVERVIEW))
    pg.route("**/api/interactive/studio/project?id=iv_b", lambda r: r.fulfill(json=PROJ))
    pg.route("**/api/interactive/studio/photo?id=av_1", lambda r: r.fulfill(body=b"", content_type="image/png"))
    pg.goto(base + "/console/")
    pg.wait_for_selector("#composer")
    pg.wait_for_selector(".sn[data-v='interactive']")
    pg.locator(".sn[data-v='interactive']").click()
    pg.wait_for_selector("#hiRoot .hi-hero")
    assert pg.locator("#hiRoot .hi-rb[data-p]").count() == 12                       # its own sidebar, twelve pages
    import os
    shots = os.environ.get("CONSOLE_SHOTS")
    if shots:
        pg.screenshot(path=f"{shots}/hi-home.png")
    home = pg.locator("#hiRoot").text_content()
    assert "What video should Hoola make?" in home and "Diwali offer" in home and "<b>Menu</b>" in home
    assert "Voice engine is not set up" in home                                     # said, not hidden
    assert pg.locator("#hiRoot b:has-text('Menu')").count() == 0                    # her title is text, never markup
    for page, said in [("avatars", "Priya"), ("voices", "Not connected on this server yet"), ("studio", "Menu"),
                       ("templates", "Festival offer"), ("brand", "Sharma Traders"), ("translate", "Translate the lines"),
                       ("live", "Not connected on this server yet"), ("apps", "Not connected yet"), ("projects", "Diwali offer"),
                       ("developers", "not open"), ("settings", "kept on this server")]:
        pg.locator(f"#hiRoot .hi-rb[data-p='{page}']").click()
        pg.wait_for_function("p => document.querySelector('#hiRoot .hi-rb[aria-current=page]')?.dataset.p === p", arg=page)
        assert said in pg.locator("#hiView").text_content(), page
        assert pg.evaluate("document.querySelector('#hiView').scrollWidth <= document.querySelector('#hiView').clientWidth + 1"), page
    pg.locator("#hiRoot .hi-rb[data-p='studio']").click()
    pg.locator("#hiRoot .hi-av", has_text="Menu").click()
    pg.wait_for_selector("#hiRoot .hi-scene")
    st = pg.locator("#hiRoot").text_content()
    assert pg.locator("#hiRoot .hi-scene").count() == 2 and "Needs your numbers" in st and "Scene 2 needs your numbers." in st
    assert pg.locator("#hiMake").is_disabled()
    if shots:
        pg.screenshot(path=f"{shots}/hi-editor.png")
    pg.locator("#hiRoot .hi-rb[data-a='back']").click()                             # Console: back to the chat
    pg.wait_for_function("document.querySelector('#hiRoot').hidden === true")
    assert not errs, errs
    ctx.close()
