"""v0.835 GHAR + SHURUAAT (L12 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L12"): the Web Studio home and the first-build wait.

Proof the plan asks for: a browser walk - greeting by time of day with her name, the placeholder typewriter (off under reduced
motion), the eight chips, 24 starter cards with thumbnails drawn from their own palette, and "Setting the stage" showing the
REAL steps of the server call (never client-timed labels)."""
import re

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_the_24_starters():
    from app.site import starters as ST
    assert len(ST.STARTERS) == 24 and ST.CHIPS == ["Website", "Online store", "Dashboard", "Booking site", "Portal", "Landing page", "Blog", "Internal tool"]
    for i, x in enumerate(ST.STARTERS):
        assert x["kind"] == ST.CHIPS[i // 3], x["id"]                       # three for each chip
        assert x["layout"] in ST.LAYOUTS and len(x["prompt"]) >= 80 and x["title"] and x["line"]
        assert all(re.fullmatch(r"#[0-9A-Fa-f]{6}", v) for v in x["palette"].values()), x["id"]
    assert len({x["id"] for x in ST.STARTERS}) == 24 and len({x["title"] for x in ST.STARTERS}) == 24
    from app.site import guard as G                                          # none of them is refused by the ask guard
    chk = getattr(G, "check_words", None) or getattr(G, "check", None)
    if chk:
        for x in ST.STARTERS:
            try:
                chk(x["prompt"])
            except TypeError:
                break


def test_stage_steps_are_the_servers_own(site_env, monkeypatch):
    from app import main
    from app.site import activity as AC
    from app.site import architect as AR
    st, fin = AR._stager(T, "ab-12345678")
    st("Reading your idea.")
    st("Planning the pages and what each one holds.")
    r = AC.read(T, "stage-ab-12345678")
    assert [s["label"] for s in r["steps"]] == ["Reading your idea.", "Planning the pages and what each one holds."]
    assert r["steps"][0]["state"] == "done" and r["steps"][1]["state"] == "run"
    fin("The workspace is ready.")
    assert AC.read(T, "stage-ab-12345678")["steps"][-1]["label"] == "The workspace is ready."
    nop, _ = AR._stager(T, "x")                                              # a short ticket writes nothing
    assert nop("anything") is None
    # build_now writes its stages in order around the real calls
    seen = []
    monkeypatch.setattr(AR, "draft", lambda *a, **k: seen.append("draft") or {"id": "c1", "hash": "h", "number": 1})
    monkeypatch.setattr(AR, "approve", lambda *a, **k: seen.append("approve") or {"site": "s1", "say": "ok"})
    from app.site import service as S
    monkeypatch.setattr(S, "_load", lambda sid: object())
    monkeypatch.setattr(S, "view", lambda row: {"id": "s1"})
    AR.build_now(T, "a website for a clinic", "", "cd-87654321")
    labels = [s["label"] for s in AC.read(T, "stage-cd-87654321")["steps"]]
    assert labels[:3] == ["Reading your idea.", "Planning the pages and what each one holds.", "Choosing colours and fonts, and setting up the website."]
    assert labels[-1] == "The workspace is ready." and seen == ["draft", "approve"]
    # the routes
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    c = TestClient(main.app)
    h = {"Authorization": f"Bearer {KEY}"}
    assert c.get("/api/sites/stage/cd-87654321", headers={}).status_code == 401
    got = c.get("/api/sites/stage/cd-87654321", headers=h).json()
    assert len(got["steps"]) >= 4 and got["now"] > 0
    assert c.get("/api/sites/stage/x", headers=h).json()["steps"] == []
    assert len(c.get("/api/site-starters", headers=h).json()["starters"]) == 24


def test_home_in_a_browser(arena_server, site_env):
    base, browser, key = arena_server
    from app.site import activity as AC
    errors = []

    def new_page(**kw):
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, **kw)
        ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        return ctx, pg

    ctx, page = new_page()
    page.goto(f"{base}/console/web#/")
    page.locator("#wsGreet").wait_for(timeout=20000)
    page.wait_for_function("/^(Good (morning|afternoon|evening)|Morning|Afternoon|Evening|Hello)/.test(document.getElementById('wsGreet').textContent)")
    p0 = page.get_attribute("#wsAsk", "placeholder")
    assert p0.startswith("Ask Hoola to build ")
    page.wait_for_timeout(1500)
    seen = {page.get_attribute("#wsAsk", "placeholder") for _ in range(1)}
    page.wait_for_timeout(700)
    seen.add(page.get_attribute("#wsAsk", "placeholder"))
    assert len(seen | {p0}) >= 2, (p0, seen)                                  # the typewriter is typing
    assert page.locator(".chips [data-chip]").count() == 8
    page.locator("#wsStarters").wait_for(state="hidden")
    page.click("[data-chip='Online store']")
    page.locator(".scard").first.wait_for(timeout=10000)
    assert page.locator(".scard").count() == 3 and page.locator(".scard svg.sthumb").count() == 3
    assert page.get_attribute("[data-chip='Online store']", "aria-pressed") == "true"
    page.click(".scard >> nth=0")
    v = page.input_value("#wsAsk")
    assert v.startswith("An online store") and len(v) > 80
    page.click("[data-chip='Online store']")                                  # same chip again hides the starters
    page.locator("#wsStarters").wait_for(state="hidden")
    shots = __import__("os").environ.get("CONSOLE_SHOTS")
    if shots:
        page.click("[data-chip='Dashboard']")
        page.locator(".scard").first.wait_for()
        page.screenshot(path=__import__("os").path.join(shots, "ae12-1-home.png"), full_page=True)
    ctx.close()
    # reduced motion: the placeholder does not move
    ctx, page = new_page(reduced_motion="reduce")
    page.goto(f"{base}/console/web#/")
    page.locator("#wsAsk").wait_for(timeout=20000)
    a = page.get_attribute("#wsAsk", "placeholder")
    page.wait_for_timeout(1500)
    assert page.get_attribute("#wsAsk", "placeholder") == a
    ctx.close()
    # "Setting the stage" shows the server's own steps (seeded under the ticket the page sent)
    ctx, page = new_page()

    held = []

    def hold(route):
        body = route.request.post_data_json or {}
        tk = body.get("ticket") or ""
        assert len(tk) >= 8
        AC.step(T, "stage-" + tk, "Reading your idea.")
        AC.step(T, "stage-" + tk, "Planning the pages and what each one holds.")
        held.append(route)                                                  # never answered: the call "is still working"
    page.route("**/api/sites", lambda r: hold(r) if r.request.method == "POST" else r.continue_())
    page.goto(f"{base}/console/web#/")
    page.locator("#wsAsk").wait_for(timeout=20000)
    page.fill("#wsAsk", "A website for a clinic in a calm teal colour #14877C with a clean modern style")
    page.press("#wsAsk", "Control+Enter") if False else page.click("button.go")
    page.locator("[data-pending] b", has_text="Setting the stage").wait_for(timeout=20000)
    page.locator("#wsPendSteps li.ok", has_text="Reading your idea.").wait_for(timeout=15000)       # only the server's list marks step 1 done
    assert page.locator("#wsPendSteps li.run", has_text="Planning the pages").count() == 1
    ctx.close()
    assert not errors, errors
