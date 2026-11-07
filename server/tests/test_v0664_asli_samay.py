"""v0.664 ASLI SAMAY: the website is built in front of her (owner: "NOT JUST A PREVIEW A REAL TIME BUILDING" -> "GO R1 TO R5").

R1 every section Opus writes is streamed into a live slot (same request, same tokens; the saved section is unchanged)
R2 the Studio's live canvas = the real site with each section growing in its place (half-written code never runs)
R3 the code typing out + parallel sections, each in its own tab
R4 the three looks grow side by side; after the pick the chosen look stays on screen
R5 a change to a built site streams over the current site, then 'New version ready' + before / after
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0407_ek_dimaag import arch_env  # noqa: F401  (fixture: the architect + the site fake AI)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

JS = Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "webstudio.js"
CANVAS = Path(__file__).resolve().parents[1] / "app" / "site" / "assets" / "hoola-build.js"


def test_partial_json_only_grows():
    from app.site import stream as ST
    full = json.dumps({"html": "<section id='s-home-hero'><h1>Sharma — \"Sweets\"</h1>\n<p>a\\b</p></section>",
                       "css": "#s-home-hero h1{color:red}", "js": "", "notes": "x"})
    prev = ""
    for i in range(1, len(full) + 1):
        h = ST.partial(full[:i], "html")
        assert h.startswith(prev), (i, prev, h)            # a half-arrived escape is never shown half-decoded
        prev = h
    assert prev == json.loads(full)["html"] and ST.partial(full, "css") == "#s-home-hero h1{color:red}"
    assert ST.partial('```json\n{"notes": "x", "ht', "html") == ""


class _Stream:
    def __init__(self, pieces, final):
        self.text_stream, self._final = iter(pieces), final

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self._final


def test_streamed_request_feeds_the_slot_and_returns_the_same_answer(monkeypatch):
    from app.config import get_settings
    from app.site import ai as AI
    from app.site import stream as ST
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    get_settings.cache_clear()
    body = json.dumps({"html": "<section id='s-home-hero'><h1>Hello world</h1></section>", "css": "h1{}", "js": ""})
    pieces = [body[i:i + 7] for i in range(0, len(body), 7)]
    seen, created = [], []
    final = SimpleNamespace(content=[SimpleNamespace(type="text", text=body)])

    def stream(**kw):
        seen.append(kw)
        return _Stream(pieces, final)
    client = SimpleNamespace(messages=SimpleNamespace(stream=stream, create=lambda **kw: created.append(kw) or final))
    monkeypatch.setattr(AI, "_app_client", lambda: client)
    monkeypatch.setattr(ST, "FEED_EVERY_S", 0)
    sid = "site_stream_test"
    with ST.watch(sid, "home__hero", "Home → Hero", "home"):
        out = AI.ask_json(AI.SECTION_SYSTEM, "x", 9000, "build")
    assert out["html"].startswith("<section") and len(seen) == 1 and not created     # streamed, not create()
    assert seen[0]["model"] and seen[0]["max_tokens"]                                 # the same request
    snap = ST.snapshot(sid)
    assert snap["slots"][0]["html"] == json.loads(body)["html"] and snap["slots"][0]["state"] == "write"
    ST.finish(sid, "home__hero", True, html="<section>checked</section>", css="")
    assert ST.snapshot(sid)["slots"][0]["state"] == "done" and ST.snapshot(sid)["slots"][0]["html"] == "<section>checked</section>"
    # outside a live section (a plan, a critique...) nothing streams
    AI.ask_json(AI.SECTION_SYSTEM, "x", 9000, "build")
    assert len(created) == 1
    # the switch turns it off
    monkeypatch.setenv("SITE_LIVE_STREAM", "false")
    get_settings.cache_clear()
    with ST.watch(sid, "home__about", "Home → About", "home"):
        AI.ask_json(AI.SECTION_SYSTEM, "x", 9000, "build")
    assert len(created) == 2 and len(seen) == 1


def test_retry_resets_and_a_failure_is_shown_as_failed():
    from app.site import stream as ST
    sid = "site_stream_retry"
    try:
        with ST.watch(sid, "home__menu", "Home → Menu", "home"):
            ST.feed('{"html": "<section>half', force=True)
            assert ST.snapshot(sid)["slots"][0]["html"] == "<section>half"
            ST.reset()
            assert ST.snapshot(sid)["slots"][0]["html"] == "" and ST.snapshot(sid)["slots"][0]["state"] == "think"
            raise RuntimeError("model busy")
    except RuntimeError:
        pass
    assert ST.snapshot(sid)["slots"][0]["state"] == "error"
    snap = ST.wait(sid, ST.snapshot(sid)["seq"], 0.2)          # nothing new: the wait times out with no slots
    assert snap["slots"] == []


def _built(site_env, monkeypatch, full=False):
    monkeypatch.setenv("SITE_FULL_LOOKS", "true" if full else "false")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.site import checks as C
    from app.site import service as S
    monkeypatch.setattr(C, "run", lambda *a, **k: (_ for _ in ()).throw(C.CheckError("no screenshots in this test")))
    from app.main import app
    c = TestClient(app)
    v = S.new(T, "mithai dukaan ki website, online order WhatsApp par", "", name="Sharma Sweets")
    assert c.post(f"/api/sites/{v['id']}/plan", json={}).status_code == 200
    return c, S, v


def test_sections_stream_and_the_canvas_pages(site_env, monkeypatch):
    from app.site import stream as ST
    c, S, v = _built(site_env, monkeypatch)
    sid = v["id"]
    slots = ST.snapshot(sid)["slots"]
    looks = [x for x in slots if x["look"] >= 0]
    assert looks and all(x["key"].startswith(f"look{x['look']}:") and x["kind"] == "look" and x["state"] == "done" for x in looks)
    assert len(ST.looks(sid)) == 3 and all(lk["tokens"] for lk in ST.looks(sid))
    tok = S.get(T, sid)["preview"].rsplit("/api/site-preview/", 1)[1].strip("/")
    r = c.get(f"/api/site-preview/{tok}/__build/__look/1/")                 # a look's canvas: its own colours, its slots
    assert r.status_code == 200 and 'data-slot="look1:home__hero"' in r.text and "__build.js" in r.text
    assert c.get(f"/api/site-preview/{tok}/__build/__look/7/").status_code == 404
    js = c.get(f"/api/site-preview/{tok}/__build.js")
    assert js.status_code == 200 and "application/javascript" in js.headers["content-type"]
    # before the build: every page of the canvas has a place for each section still to come
    r = c.get(f"/api/site-preview/{tok}/__build/")
    assert r.status_code == 200 and "hb-wait" in r.text
    assert c.post(f"/api/sites/{sid}/look", json={"index": 0}).status_code == 200
    g = S.get(T, sid)
    built = [x for x in ST.snapshot(sid)["slots"] if x["look"] < 0]
    pages = {p["slug"] for p in g["plan"]["pages"]}
    assert built and {x["page"] for x in built} <= pages and all(x["state"] == "done" and x["html"] for x in built)
    assert all("→" in x["label"] for x in built)
    r = c.get(f"/api/site-preview/{tok}/__build/")
    assert 'class="hb-slot"' in r.text and "hb-wait" not in r.text                     # everything written now
    # the saved site carries no canvas marks
    live = c.get(f"/api/site-preview/{tok}/")
    assert "data-slot" not in live.text and "__build.js" not in live.text
    # an earlier version can be shown (before / after)
    assert c.get(f"/api/site-preview/{tok}/__v/1/").status_code == 200
    assert c.get(f"/api/site-preview/{tok}/__v/9/").status_code == 404


def test_live_route_sends_growing_text_as_additions(site_env, monkeypatch):
    from app.main import sites_live
    from app.site import stream as ST
    c, S, v = _built(site_env, monkeypatch)
    sid = v["id"]
    ST.clear(sid)
    monkeypatch.setattr(ST, "FEED_EVERY_S", 0)

    async def read(n):
        resp = await sites_live(sid, 0, T)
        out = []
        it = resp.body_iterator

        def writer():
            time.sleep(0.2)
            with ST.watch(sid, "home__menu", "Home → Menu", "home"):
                ST.feed('{"html": "<section>Ras', force=True)
                time.sleep(0.15)
                ST.feed('{"html": "<section>Rasmalai</section>", "css": "a{}"', force=True)
                time.sleep(0.15)
                ST.finish(sid, "home__menu", True, html="<section>Rasmalai checked</section>", css="a{}")
        threading.Thread(target=writer, daemon=True).start()
        async for chunk in it:
            if chunk.startswith("data:"):
                out.append(json.loads(chunk[5:]))
            if len(out) >= n:
                break
        await it.aclose()
        return out
    evs = asyncio.run(asyncio.wait_for(read(4), 10))
    menu = [s for e in evs for s in e["slots"] if s["key"] == "home__menu"]
    grow = [s for s in menu if "ha" in s]
    assert grow and grow[0]["ha"] == "malai</section>" and grow[0]["ho"] == len("<section>Ras")
    assert menu[-1]["state"] == "done" and menu[-1]["h"] == "<section>Rasmalai checked</section>"


def test_canvas_and_studio_markers():
    c = CANVAS.read_text()
    assert "ev.source !== P" in c and "querySelectorAll(BAD)" in c and "script,iframe,object,embed" in c
    assert "indexOf('on') === 0" in c and "javascript:" in c                  # handlers and javascript: links removed
    js = JS.read_text()
    assert "/live?since=" in js and "Authorization: 'Bearer ' + TOKEN" in js and 'sandbox="allow-scripts"' in js
    assert "function liveView(pane, v)" in js and "__build/__look/" in js and "data-lpage" in js and "data-lcode" in js
    assert "compareView" in js and "__v/${Number(jd.from)}/" in js and "New version v" in js
    assert 'data-live="follow"' in js and 'data-live="code"' in js


def _slow_fake(monkeypatch, per=0.06, n=10):
    """The fake Opus answers a live section in pieces, like the real stream (other calls answer at once)."""
    from app.site import ai as AI
    from app.site import stream as ST
    real = AI.ask_json

    def ask(system, prompt, max_tokens=6000, kind="build", *a, **k):
        out = real(system, prompt, max_tokens, kind)
        if ST.current() and out.get("html"):
            text = json.dumps(out)
            step = max(1, len(text) // n)
            for i in range(step, len(text) + step, step):
                ST.feed(text[:i], force=True)
                time.sleep(per)
        return out
    monkeypatch.setattr(AI, "ask_json", ask)


def test_live_build_in_a_browser(arena_server, arch_env, monkeypatch):
    base, browser, key = arena_server
    monkeypatch.setenv("SITE_FULL_LOOKS", "false")
    monkeypatch.setenv("SITE_PARALLEL", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.site import checks as C
    monkeypatch.setattr(C, "run", lambda *a, **k: (_ for _ in ()).throw(C.CheckError("no screenshots")))
    _slow_fake(monkeypatch)
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(base + "/console/web")
    page.wait_for_selector("#wsAsk", timeout=20000)
    page.fill("#wsAsk", "Sharma Sweets mithai dukaan ki website, online order WhatsApp par")
    page.keyboard.press("Enter")
    # R4: the three looks grow side by side
    page.wait_for_selector("#ws .lgrid iframe[data-look='2']", timeout=60000)
    assert page.locator("#ws .lgrid iframe[data-live]").count() == 3
    seen_look = False
    for _ in range(80):
        for i in range(3):
            if page.frame_locator(f"#ws iframe[data-look='{i}']").locator(".hb-live, .hb-new").count():
                seen_look = True
        if seen_look or page.locator("#ws .lks button").count():
            break
        page.wait_for_timeout(150)
    assert seen_look, "no look grew on screen"
    page.wait_for_selector("#ws .lks button", timeout=120000)
    # R1-R3: pick a look -> the site grows page by page, the code types out
    page.click("#ws [data-act='pick-look']")
    page.wait_for_selector("#ws iframe[data-live][data-look='-1']", timeout=30000)
    page.click("#ws [data-live='code']")
    page.wait_for_selector("#wsLCode", timeout=10000)
    lengths, code = [], []
    canvas = page.frame_locator("#ws iframe[data-live]")
    for _ in range(120):
        if not page.locator("#ws iframe[data-live]").count():
            break
        try:
            n = canvas.locator(".hb-live").first.evaluate("e => e.textContent.length") if canvas.locator(".hb-live").count() else -1
        except Exception:
            n = -1
        lengths.append(n)
        code.append(len(page.inner_text("#wsLCode")) if page.locator("#wsLCode").count() else 0)
        if len([x for x in lengths if x > 0]) > 12:
            break
        page.wait_for_timeout(120)
    grew = any(b > a > 0 for a, b in zip(lengths, lengths[1:]))
    assert grew, lengths
    assert max(code) > 40, code
    assert page.locator("#wsLPages button").count() >= 3
    assert canvas.locator(".hb-tag").count() >= 1 or page.locator("#ws .lbar b").count()
    # no script of a half-written section ran in the canvas, and the canvas never reached the Studio
    assert page.evaluate("typeof window.__hb_ran") == "undefined"
    page.wait_for_selector("#ws #wsPane .url", timeout=180000)                     # built: the normal preview
    sid = page.url.split("#/site/")[1].split("/")[0]
    # R5: a change to the built site streams over it, then 'New version ready' + before / after
    from app.site import service as S
    g = S.get(T, sid)
    k = S.sec_key("home", g["plan"]["pages"][0]["sections"][-1]["type"])

    def change():
        S._save(sid, status="building", stage="build")
        S.run_build(sid, only=[k], note="change")
    threading.Thread(target=change, daemon=True).start()
    page.wait_for_selector("#ws iframe[data-live][data-look='-1']", timeout=30000)
    page.wait_for_selector("#ws .okbar:has-text('New version v2 is ready')", timeout=120000)
    page.click("#ws [data-act='compare']")
    page.wait_for_selector("#ws .cmp iframe", timeout=10000)
    srcs = page.eval_on_selector_all("#ws .cmp iframe", "fs => fs.map(f => f.getAttribute('src'))")
    assert len(srcs) == 2 and "/__v/1/" in srcs[0] and "__v/" not in srcs[1]
    ctx.close()
    errors = [e for e in errors if "The document is sandboxed" not in e]
    assert not errors, errors
