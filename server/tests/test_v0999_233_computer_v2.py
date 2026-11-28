"""v0.999.233 COMPUTER V2 (her prototype "a job on each computer, step by step" -> "GO"): one top bar with both computers,
a hub that asks, picks the machine and says why, the machine's screen with Hoola's pointer + thought, the job's checklist
and the yes / not-now card answered on the page; Connect your PC for Windows / Mac / Linux. (Grew from the v0.999.145
redesign test.)"""
from __future__ import annotations

import types

from fastapi.testclient import TestClient

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


def test_her_yes_is_answered_from_the_job_panel(env, monkeypatch):
    from app.main import app
    from app.pc import operator as pcop
    c = TestClient(app)
    op = pcop.Op(id="pcop_y1", tenant="default", conv="c1", task="Pay the GST challan", kind="hoola_pc")
    op.task_obj = types.SimpleNamespace(done=lambda: False)
    monkeypatch.setitem(pcop.OPS, op.id, op)
    assert c.post("/api/computer/task/pcop_y1/decide", json={"yes": True}).status_code == 409    # nothing waits yet
    import asyncio
    op.decision = asyncio.Event()
    op.pending = {"id": "ap1", "what": "Pay Rs 1,200 on the GST portal"}
    op.status = "needs_confirm"
    run = c.get("/api/computer").json()["hoola"]["running"]
    assert run["pending"] == {"id": "ap1", "what": "Pay Rs 1,200 on the GST portal"}
    assert c.post("/api/computer/task/pcop_y1/decide", json={"yes": True, "id": "old"}).status_code == 409   # an old card
    r = c.post("/api/computer/task/pcop_y1/decide", json={"yes": False, "id": "ap1"})
    assert r.status_code == 200 and r.json() == {"ok": True, "yes": False}
    assert op.approved is False and op.decision.is_set()
    assert c.post("/api/computer/task/pcop_none/decide", json={"yes": True}).status_code == 404


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


def test_computer_v2_in_a_real_browser(arena_server):  # noqa: F811
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
            {"n": i, "t": 10 + i * 1.5, "tool": "page_click", "action": a, "args": {"x": 100 * i, "y": 60 * i}} for i, a in enumerate(
                ["Opened GST portal", "Closed cookie banner", "Search Taxpayer", "Typed GSTIN 1", "Pressing Search"], 1)]}))
        pg.route("**/api/browser/**", lambda r: r.fulfill(status=404, json={"detail": "no screen"}))
        try:
            pg.goto(base + "/console/computer#/")
            pg.wait_for_selector(".cx-machine")
            assert pg.locator(".cx-machine").count() == 2 and pg.locator(".cx-tabs a").count() == 2
            assert "Office laptop" in pg.locator(".cx-tabs").inner_text()
            assert "Typing the GSTIN" in pg.locator(".cx-mthought").first.inner_text()
            assert "Chrome connected" in pg.locator("[data-machine=mine]").inner_text()
            pg.wait_for_function("() => document.querySelectorAll('#jobs li.cx-job').length === 2")
            assert "Done" in pg.locator("#jobs li.cx-job.ok").inner_text() and "41 s" in pg.locator("#jobs li.cx-job.ok").inner_text()
            assert "Contact form" in pg.locator("#routines").inner_text()
            assert "2 never-open sites · 1 ask-first site" in pg.locator("#ruleLine").inner_text()
            assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "no sideways scroll"
            _shot(pg, f"home-{scheme}-{width}")
            if width > 400 and scheme == "light":
                # the give-a-job box: Hoola chooses, says why, lights the machine up, and her words go to its chat
                pg.route("**/api/computer/choose", lambda r: r.fulfill(json={"which": "mine", "why": "epfindia.gov.in refuses cloud computers, so it runs on your PC"}))
                pg.route("**/api/computer/mine/chats", lambda r: r.fulfill(json={"id": "cmine1", "reused": False}) if r.request.method == "POST" else r.continue_())

                def msg(r):
                    if r.request.method == "POST":
                        sent.append(r.request.post_data_json["text"])
                        return r.fulfill(status=202, json={"accepted": True})
                    return r.fulfill(json={"messages": []})
                pg.route("**/api/conversations/cmine1/**", msg)
                pg.locator("#ask").fill("Check my UAN on epfindia.gov.in")
                pg.locator(".cx-go").click()
                pg.wait_for_selector("#route:not([hidden])")
                assert "refuses cloud computers" in pg.locator("#route").inner_text()
                assert pg.locator("[data-machine=mine].chosen").count() == 1
                _shot(pg, "home-route")
                pg.wait_for_function("() => location.hash.startsWith('#/mine/cmine1')")
                assert sent == ["Check my UAN on epfindia.gov.in"]
            # the Hoola PC screen while a job of this chat runs: checklist, pointer at the last click, her yes card
            run.update(conv=chat, status="needs_confirm", pending={"id": "ap9", "what": "Submit the search form on the GST portal"})
            answered = []
            pg.route("**/api/computer/task/pcop_r1/decide", lambda r: (answered.append(r.request.post_data_json), r.fulfill(json={"ok": True, "yes": True}))[1])
            pg.route(f"**/api/conversations/{chat}/messages*", lambda r: r.fulfill(json={"messages": [
                {"id": 1, "role": "user", "text": "Search GSTIN 27AAGCB1286Q1ZL", "at": "2026-11-22T10:00:00"}]}))
            pg.route(f"**/api/conversations/{chat}/result", lambda r: r.fulfill(json={"status": "working", "needs_you": True, "line": "", "made": []}))
            import io
            from PIL import Image
            png = io.BytesIO(); Image.new("RGB", (1280, 800), (236, 240, 246)).save(png, "PNG")
            pg.route("**/api/browser/pcop_r1/live", lambda r: r.fulfill(json={"seq": 3, "url": "https://services.gst.gov.in/services/searchtp"}))
            pg.route("**/api/browser/pcop_r1/frame", lambda r: r.fulfill(body=png.getvalue(), content_type="image/png"))
            pg.goto(f"{base}/console/computer#/hoola/{chat}")
            pg.wait_for_selector("#steps li.done", timeout=15000)
            pg.wait_for_selector("#ptr:not([hidden])", timeout=15000)          # Hoola's pointer sits where it last clicked
            assert pg.locator("#stUrl").inner_text() == "services.gst.gov.in"
            box, img = pg.locator("#ptr").bounding_box(), pg.locator("#stView img").bounding_box()
            assert abs(box["x"] + 3 - (img["x"] + 500 * img["width"] / 1280)) < 4, (box, img)
            assert pg.locator("#steps li.done").count() == 5
            assert "Search GSTIN" in pg.locator("#jobTitle").inner_text()
            pg.wait_for_selector("#approve:not([hidden])", timeout=15000)
            assert "Submit the search form" in pg.locator("#approve").inner_text()
            assert "Typing the GSTIN" in pg.locator("#stThink").inner_text()
            _shot(pg, f"hoola-{scheme}-{width}")
            pg.locator("#approve [data-yes='1']").click()
            pg.wait_for_function("() => document.querySelector('#approve').hidden", timeout=8000)
            assert answered == [{"yes": True, "id": "ap9"}]
            run.update(status="working"); run.pop("pending", None)
            # an idle chat whose last answer was a refusal shows Move to my PC
            pg.route(f"**/api/conversations/{chat}/messages*", lambda r: r.fulfill(json={"messages": [
                {"id": 1, "role": "user", "text": "Check my UAN on epfindia.gov.in", "at": "2026-11-22T10:00:00"},
                {"id": 2, "role": "assistant", "text": "NOT OPENED: epfindia.gov.in refuses cloud computers. This job needs HER own PC.", "at": "2026-11-22T10:00:05"}]}))
            pg.route(f"**/api/conversations/{chat}/result", lambda r: r.fulfill(json={"status": "partial", "needs_you": False, "line": "", "made": []}))
            run["conv"] = "other"
            pg.goto(f"{base}/console/computer#/hoola/{chat}")
            pg.wait_for_selector(".hck-txt", timeout=15000)        # the chat column draws (it was blank: the live check wiped it)
            pg.wait_for_function("() => document.querySelectorAll('.hck-bub').length === 1", timeout=8000)
            pg.wait_for_selector("#move:not([hidden]) #moveBtn", timeout=15000)
            assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "no sideways scroll"
            run["conv"] = chat
            # your PC: the Chrome tab group with Hoola's own tab and the banner with Stop
            pg.goto(f"{base}/console/computer#/mine")
            pg.wait_for_selector(".cx-chrome.tabs")
            _shot(pg, f"mine-{scheme}-{width}")
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
