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
    script error, her text is never run as HTML, what is not connected is SAID, and a missing number blocks Generate.
    v0.785 PREMIUM PASS: one heading per page, no raw browser dropdown, nothing in the editor wraps onto a second
    line, a picture that cannot load shows initials, the sidebar folds, the entrance motion ends by itself."""
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(getattr(e, "stack", "") or e)[:400]))
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
        pg.wait_for_timeout(1000)
        pg.screenshot(path=f"{shots}/hi-home.png", full_page=False)
    home = pg.locator("#hiRoot").text_content()
    assert "What video should Hoola make?" in home and "Diwali offer" in home and "<b>Menu</b>" in home
    assert "Voice engine is not set up" in home                                     # said, not hidden
    assert pg.locator("#hiRoot b:has-text('Menu')").count() == 0                    # her title is text, never markup
    assert pg.locator("#hiRoot .hi-top, #hiRoot #hiTtl").count() == 0                 # no second title bar
    assert pg.evaluate("document.querySelector('#hiRoot').dataset.slim") == "0"
    pg.set_viewport_size({"width": 1366, "height": 660})                            # a small laptop: the whole sidebar fits, no scrolling
    assert pg.evaluate("(r => r.scrollHeight <= r.clientHeight + 1)(document.querySelector('#hiRail'))")
    pg.set_viewport_size({"width": 1280, "height": 900})
    pg.wait_for_function("() => !document.querySelector('#hiView').classList.contains('hi-in')")   # the entrance ends by itself
    pg.locator("#hiRoot .hi-sel[data-a='eg']").first.click()                        # a starter line fills the box
    assert pg.locator("#hiLine").input_value() == "A festival offer for my shop"
    for page, said in [("avatars", "Priya"), ("voices", "Not connected on this server yet"), ("studio", "Menu"),
                       ("templates", "Festival offer"), ("brand", "Sharma Traders"), ("translate", "Translate the lines"),
                       ("live", "Not connected on this server yet"), ("apps", "Not connected yet"), ("projects", "Diwali offer"),
                       ("developers", "not open"), ("settings", "kept on this server")]:
        pg.locator(f"#hiRoot .hi-rb[data-p='{page}']").click()
        pg.wait_for_function("p => document.querySelector('#hiRoot .hi-rb[aria-current=page]')?.dataset.p === p", arg=page)
        assert said in pg.locator("#hiView").text_content(), page
        assert pg.evaluate("document.querySelector('#hiView').scrollWidth <= document.querySelector('#hiView').clientWidth + 1"), page
        assert pg.locator("#hiRoot h1").count() == 1, page                          # the title is said once, not twice
        assert pg.evaluate("[...document.querySelectorAll('#hiRoot select')].every(s => getComputedStyle(s).appearance === 'none'"
                           " && s.closest('.hi-pick, .hi-f'))"), page                # every dropdown is drawn, none is the raw browser one
        if shots:
            pg.wait_for_timeout(1000)
            pg.screenshot(path=f"{shots}/hi-{page}.png")
    pg.locator("#hiRoot .hi-rb[data-p='projects']").click()
    pg.locator("#hiRoot .hi-tab", has_text="Drafts").click()                        # v0.787: a tab click must stay on the page - the console
    assert pg.evaluate("document.querySelector('#hiRoot').hidden") is False            # sends any click on [data-v] to go(), which threw her back to chat
    assert "Menu" in pg.locator("#hiView").text_content()
    assert "data-v=" not in (Path(__file__).resolve().parents[1] / "app/static/console/interactive.js").read_text()
    pg.locator("#hiRoot .hi-rb[data-p='avatars']").click()
    pg.wait_for_function("() => document.querySelectorAll('#hiRoot img[data-av]').length === 0")   # the empty picture became initials
    assert "PR" in pg.locator("#hiRoot .hi-face").first.text_content()
    pg.locator("#hiRoot .hi-rb[data-p='studio']").click()
    pg.locator("#hiRoot .hi-av", has_text="Menu").click()
    pg.wait_for_selector("#hiRoot .hi-scene")
    st = pg.locator("#hiRoot").text_content()
    assert pg.locator("#hiRoot .hi-scene").count() == 2 and "Needs your numbers" in st and "Scene 2 needs your numbers." in st
    assert pg.locator("#hiMake").is_disabled()
    one_row = "s => { const t = [...document.querySelectorAll(s)].map(e => Math.round(e.getBoundingClientRect().top + e.getBoundingClientRect().height / 2)); return Math.max(...t) - Math.min(...t) <= 3; }"
    assert pg.evaluate(f"({one_row})('#hiRoot .hi-tt button')")                     # the five tool tabs sit on ONE row
    assert pg.evaluate(f"({one_row})('#hiRoot .hi-edhead > *')")                    # back, title, saved, Save as template, Generate: one row
    assert pg.evaluate(f"({one_row})('#hiRoot .hi-scene:nth-of-type(2) .hd > *')")  # the scene that needs numbers: its header does not wrap
    assert pg.evaluate("document.querySelector('#hiRoot').dataset.slim") == "1"     # the editor opens with the sidebar folded
    assert pg.locator("#hiRoot .hi-sc .mini b", has_text="Namaste").count() == 1    # a scene thumbnail shows the scene's own words
    pg.locator("#hiRoot [data-a='slim']").click()                                   # her own choice wins
    assert pg.evaluate("document.querySelector('#hiRoot').dataset.slim") == "0"
    pg.locator("#hiRoot [data-a='slim']").click()
    pg.locator("#hiRoot .hi-trans [aria-label='Next scene']").click()               # previous / next under the stage
    assert "Scene 2 of 2" in pg.locator("#hiRoot .hi-stag").text_content()
    if shots:
        pg.wait_for_timeout(1000)
        pg.screenshot(path=f"{shots}/hi-editor.png")
        pg.locator("#hiRoot .hi-sc").nth(1).click()
        pg.wait_for_timeout(800)
        pg.screenshot(path=f"{shots}/hi-editor2.png")
        pg.evaluate("document.documentElement.setAttribute('data-theme','dark')")
        pg.wait_for_timeout(300)
        pg.screenshot(path=f"{shots}/hi-editor-dark.png")
        pg.locator("#hiRoot .hi-rb[data-p='home']").click()
        pg.wait_for_timeout(1000)
        pg.screenshot(path=f"{shots}/hi-home-dark.png")
        pg.evaluate("document.querySelector('#hiView').scrollTop = 620")
        pg.wait_for_timeout(200)
        pg.screenshot(path=f"{shots}/hi-home2-dark.png")
        pg.evaluate("document.documentElement.removeAttribute('data-theme')")
        pg.set_viewport_size({"width": 1366, "height": 660})
        pg.wait_for_timeout(300)
        pg.screenshot(path=f"{shots}/hi-home-laptop.png")
        pg.set_viewport_size({"width": 400, "height": 800})
        pg.wait_for_timeout(300)
        pg.screenshot(path=f"{shots}/hi-home-phone.png")
        pg.set_viewport_size({"width": 1280, "height": 900})
    pg.locator("#hiRoot .hi-rb[data-a='back']").click()                             # Console: back to the chat
    pg.wait_for_function("document.querySelector('#hiRoot').hidden === true")
    assert not errs, errs
    ctx.close()


def test_the_premium_pass_keeps_the_console_rules():
    """v0.785: the page's styles stay inside the console's one stylesheet and its type rules, motion can be switched
    off, and no class name of the page is one the console already styles (.top / .tag / .live leaked into it)."""
    import pathlib
    import re
    con = pathlib.Path(__file__).resolve().parents[1] / "app" / "static" / "console"
    css = (con / "v2.css").read_text()
    blk = css[css.index("v0.775 HOOLA INTERACTIVE, PREMIUM PASS"):css.index("@media (prefers-reduced-motion:reduce){ :is(#hiRoot,#hvRoot)") + 240]
    assert "backdrop-filter" not in blk and "text-transform" not in blk
    assert not re.search(r"font(-weight)?:\s*(700|800|900)\b", blk)                 # nothing above 600
    assert not re.search(r"font-size:\s*(9|10|11)(\.\d+)?px", blk)                  # nothing under 12px
    assert ":is(#hiRoot,#hvRoot) *,:is(#hiRoot,#hvRoot) *::before,:is(#hiRoot,#hvRoot) *::after{animation:none!important;transition:none!important}" in blk
    assert not re.search(r"animation:[^;}]*\b(both|forwards)\b", blk) and "var(--logo)" not in blk   # no held animation; Sora stays on the logo
    assert blk.count("infinite") == 2                                               # only "working now": the live chip and the running step
    for line in blk.splitlines():                                                   # every rule of the page is scoped to the page
        if "{" in line and not line.lstrip().startswith(("@", "/*", "}", "from", "0%", "radial", "linear", "box-shadow", "background")) and "#hiRoot" not in line.split("{")[0] and "#hvRoot" not in line.split("{")[0]:
            assert line.startswith("  ") or line.strip().startswith(("--", "display", "transition")), line[:80]
    js = (con / "interactive.js").read_text()
    for bad in ('class="top"', 'class="tag ', 'hi-chip live', 'hi-pill', 'font-weight:700'):
        assert bad not in js, bad
    assert "if (R) closeMenu()" in (con / "studio.js").read_text()                  # Create Studio no longer throws on a resize before it is opened
