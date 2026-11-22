"""v0.999.116 ULTIMATE PC PLAN P6 - the PC Jobs page in a real browser: every job step by step with the screen it saw and
the click marked, save a good job as a routine, run a routine, her PC rules saved (light + dark, phone width)."""
from __future__ import annotations

import base64
import io
import types

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401


def _png():
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (400, 250), (240, 240, 250)).save(b, "PNG")
    return b.getvalue()


def _record(tmp):
    from app.pc import trace
    op = types.SimpleNamespace(id="pcop_page1", tenant="default", conv="c1", task="Subscribe ops@example.org on the practice site",
                               kind="hoola_pc", device_id="d1", step=0, action="", window="Practice", frame=_png(), thought="",
                               thought_fresh=False, brain="q", status="running", summary="", reason="", elems={})
    trace.start(op)
    steps = [("open_url", {"url": "https://p/shadow"}, {}, "Opening the page"),
             ("page_type", {"ref": 2, "text": "ops@example.org"}, {2: "input 'Work email'"}, "Filling field #2"),
             ("click", {"x": 200, "y": 125}, {}, "Clicking")]
    for tool, a, el, act in steps:
        op.step += 1
        op.elems, op.action, op.thought, op.thought_fresh = el, act, "I see the form", True
        trace.step(op, tool, a)
    op.status, op.summary = "done", "Subscribed."
    trace.finish(op)


def test_pc_jobs_page_in_a_real_browser(arena_server, tmp_path, monkeypatch):  # noqa: F811
    base, browser, key = arena_server
    monkeypatch.setenv("PC_TRACE_DIR", str(tmp_path / "trace"))
    monkeypatch.setenv("PC_ROUTINES_DIR", str(tmp_path / "routines"))
    monkeypatch.setenv("PC_RULES_DIR", str(tmp_path / "rules"))
    _record(tmp_path)
    errors = []
    for scheme, width in (("light", 1280), ("dark", 390)):
        ctx = browser.new_context(color_scheme=scheme, viewport={"width": width, "height": 900})
        ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}'); }} catch (e) {{}}")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "/console/pcjobs")
        page.wait_for_selector(".pj-row")
        assert "Subscribe ops@example.org" in page.inner_text(".pj-list")
        page.click(".pj-row")
        page.wait_for_selector(".pj-step")
        assert page.locator(".pj-step").count() == 3
        page.wait_for_selector(".pj-shot img")
        page.wait_for_selector(".pj-mark")                                # the pixel click is marked on its screen
        assert "Thinking: I see the form" in page.inner_text(".pj-steps")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        if scheme == "light":
            page.once("dialog", lambda d: d.accept("Newsletter"))
            page.click("#save")
            page.wait_for_selector(".hc-toast:not([hidden])")
            assert "Saved 'Newsletter'" in page.inner_text(".hc-toast")
            page.goto(base + "/console/pcjobs#/routines")
            page.wait_for_selector(".pj-card[data-id]")
            assert page.input_value(".pj-card input") == "ops@example.org"
            page.goto(base + "/console/pcjobs#/rules")
            page.wait_for_selector("#never")
            page.fill("#never", "bet365.com")
            page.fill("#notes", "Never order on Sundays")
            page.click("#rules button[type=submit]")
            page.wait_for_selector(".hc-toast:not([hidden])")
            assert "1 never" in page.inner_text(".hc-toast")
        ctx.close()
    assert not errors, errors
    from app.pc import guard
    assert guard.get("default")["notes"] == ["Never order on Sundays"]


def test_the_page_is_linked_and_served(env):
    from pathlib import Path
    from fastapi.testclient import TestClient
    from app.main import app
    r = TestClient(app).get("/console/pcjobs")
    assert r.status_code == 200 and "pcjobs.js" in r.text and "script-src 'self'" in r.headers["content-security-policy"]
    js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "computer.js").read_text()
    assert 'href="/console/pcjobs"' in js
