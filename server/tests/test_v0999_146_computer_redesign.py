"""v0.999.145 HOOLA COMPUTER REDESIGN (her canvas -> "GO BUILD THE DESIGN"): home with both computers, one 'give a job'
box that can let Hoola choose, recent jobs / routines / her rules, the step strip and 'Move to my PC' in a workspace,
Connect your PC for Windows / Mac / Linux."""
from __future__ import annotations

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture arena_server needs)


def test_let_hoola_choose(env, monkeypatch):
    from app import computer as C
    monkeypatch.setattr(C, "_paired", lambda t: [{"id": "d1", "name": "Office laptop", "online": True, "os": "Windows 11"}])
    monkeypatch.setattr(C, "mine_on", lambda t: True)
    assert C.choose("t", "Check my UAN on epfindia.gov.in")["which"] == "mine"
    assert C.choose("t", "Search TESCO on find-and-update.company-information.service.gov.uk")["which"] == "hoola"
    monkeypatch.setattr(C, "_paired", lambda t: [{"id": "d1", "name": "Office laptop", "online": False}])
    out = C.choose("t", "Check my UAN on epfindia.gov.in")
    assert out["which"] == "hoola" and "not on" in out["why"]
    st = C.status("t")
    assert set(st["mine"]["downloads"]) == {"windows", "mac", "linux"} and "chrome" in st["mine"]


def _shot(pg, name):
    import os
    d = os.environ.get("HOOLA_SHOTS")
    if d:
        pg.screenshot(path=f"{d}/{name}.png", full_page=True)


def _ctx(browser, key, scheme="light", width=1440):
    ctx = browser.new_context(viewport={"width": width, "height": 980}, color_scheme=scheme, device_scale_factor=1)
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs: list[str] = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    return ctx, pg, errs


def test_the_redesign_in_a_real_browser(arena_server):  # noqa: F811
    import httpx
    base, browser, key = arena_server
    h = {"Authorization": "Bearer " + key}
    chat = httpx.post(base + "/api/computer/hoola/chats", headers=h, timeout=20).json()["id"]
    run = {"session_id": "pcop_r1", "task": "Search GSTIN 27AAGCB1286Q1ZL", "step": 6, "steps_max": 64, "status": "working",
           "thought": "Typing the GSTIN into the search box", "pc": "Hoola PC 2", "conv": chat, "from": "", "started": 1}
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        ctx, pg, errs = _ctx(browser, key, scheme, width)
        sent = []

        def status(r):
            d = r.fetch().json()
            d["hoola"].update(online=True, running=dict(run))
            d["mine"].update(on=True, online=True, chrome=True, background=True,
                             devices=[{"id": "d1", "name": "Office laptop", "online": True, "os": "Windows 11", "version": "1.10.0"}])
            r.fulfill(json=d)
        pg.route("**/api/computer", status)
        pg.route("**/api/pc/trace?*", lambda r: r.fulfill(json={"jobs": [
            {"job": "pcop_a", "task": "Filled the vendor form on SAM.gov", "status": "done", "kind": "hoola_pc", "steps": 17, "started": 100, "ended": 141},
            {"job": "pcop_b", "task": "EPFO UAN status", "status": "partial", "kind": "her_pc", "steps": 2, "started": 100, "ended": 105}]}))
        pg.route("**/api/pc/routines", lambda r: r.fulfill(json={"routines": [{"id": "rt1", "name": "Contact form", "blanks": [{"name": "Full name"}], "runs": 3}]}))
        pg.route("**/api/pc/rules", lambda r: r.fulfill(json={"never": ["a.com", "b.com"], "ask": ["c.com"], "notes": []}))
        pg.route("**/api/pc/trace/pcop_r1", lambda r: r.fulfill(json={"steps_list": [
            {"n": i, "t": 10 + i * 1.5, "tool": "page_click", "action": a} for i, a in enumerate(
                ["Opened GST portal", "Closed cookie banner", "Search Taxpayer", "Typed GSTIN 1", "Pressing Search"], 1)]}))
        pg.route("**/api/browser/**", lambda r: r.fulfill(status=404, json={"detail": "no screen"}))
        try:
            pg.goto(base + "/console/computer#/")
            pg.wait_for_selector(".hc-pcard")
            assert pg.locator(".hc-pcard").count() == 2
            assert "Typing the GSTIN" in pg.locator(".hc-thought").first.inner_text()
            assert pg.locator(".hc-livepill").count() == 1 and "Online · Office laptop" in pg.locator(".hc-pill").inner_text()
            pg.wait_for_function("() => document.querySelectorAll('#jobs li b').length === 2")
            assert "Contact form" in pg.locator("#routines").inner_text()
            assert "2 never-open sites · 1 ask-first site" in pg.locator("#ruleLine").inner_text()
            assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "no sideways scroll"
            _shot(pg, f"home-{scheme}-{width}")
            if width > 400 and scheme == "light":
                # the give-a-job box: Hoola chooses, a chat on that computer gets her words, the page opens it
                pg.route("**/api/computer/choose", lambda r: r.fulfill(json={"which": "mine", "why": "epfindia.gov.in refuses cloud computers, so it runs on your PC"}))
                pg.route("**/api/computer/mine/chats", lambda r: r.fulfill(json={"id": "cmine1", "reused": False}) if r.request.method == "POST" else r.continue_())

                def msg(r):
                    if r.request.method == "POST":
                        sent.append(r.request.post_data_json["text"])
                        return r.fulfill(status=202, json={"accepted": True})
                    return r.fulfill(json={"messages": []})
                pg.route("**/api/conversations/cmine1/**", msg)
                pg.locator("#ask").fill("Check my UAN on epfindia.gov.in")
                pg.locator(".hc-go").click()
                pg.wait_for_function("() => location.hash.startsWith('#/mine/cmine1')")
                assert sent == ["Check my UAN on epfindia.gov.in"]
            # the Hoola PC workspace: steps under the screen; a refusal shows Move to my PC
            pg.route(f"**/api/conversations/{chat}/messages*", lambda r: r.fulfill(json={"messages": [
                {"id": 1, "role": "user", "text": "Check my UAN on epfindia.gov.in", "at": "2026-11-22T10:00:00"},
                {"id": 2, "role": "assistant", "text": "NOT OPENED: epfindia.gov.in refuses cloud computers. This job needs HER own PC.", "at": "2026-11-22T10:00:05"}]}))
            pg.route(f"**/api/conversations/{chat}/result", lambda r: r.fulfill(json={"status": "partial", "needs_you": False, "line": "", "made": []}))
            run["conv"] = "other"         # the running task belongs to another chat: this chat is idle
            pg.goto(f"{base}/console/computer#/hoola/{chat}")
            pg.wait_for_selector(".hck-txt", timeout=15000)        # the chat column draws (it was blank: the live check wiped it)
            pg.wait_for_function("() => document.querySelectorAll('.hck-bub').length === 1", timeout=8000)
            pg.wait_for_selector("#steps .hc-stp", timeout=15000)
            assert pg.locator("#steps .hc-stp").count() == 5 and "Pressing Search" in pg.locator("#steps .now").inner_text()
            pg.wait_for_selector("#move:not([hidden]) #moveBtn", timeout=15000)
            _shot(pg, f"hoola-{scheme}-{width}")
            run["conv"] = chat
            # Connect your PC: three systems, each with its own download
            pg.goto(base + "/console/computer#/connect")
            pg.wait_for_selector(".hc-os")
            pg.locator("[data-os=mac]").click()
            assert "Hoola-Desktop-mac.zip" in pg.locator("#dl").get_attribute("href")
            pg.locator("[data-os=linux]").click()
            assert "linux" in pg.locator("#dl").get_attribute("href")
            _shot(pg, f"connect-{scheme}-{width}")
            assert not errs, errs
        finally:
            ctx.close()
