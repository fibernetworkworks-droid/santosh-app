"""v0.725 PAGE CARD (owner, screenshot of "Build an interactive web UI · Page": "DONT HAVE A TIMING AND WORK IN PROGRESS
ETC --- SHOW ME HERE A PREMIUM AND PERFECT CARD" -> preview -> GO): the page card shows the real step, a live clock,
Stop while it is made; a picture, what it holds, version, how long it took, Share + Open when ready; the reason in
plain words + Try again when it could not be made."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

CON = Path(__file__).resolve().parents[1] / "app/static/console"


def test_builder_reports_real_steps_and_time(env, monkeypatch):
    from app import artifacts
    from app.events import bus
    seen = []
    monkeypatch.setattr(bus, "publish", lambda c, k, p: seen.append((k, dict(p))))

    async def fake_llm(system, prompt, max_tokens=16000):
        return "TITLE: NetMitra dashboard\nSUMMARY: 5 screens on demo data\n<!doctype html><html><head><title>NetMitra</title></head><body>" + "<p>Dashboard tickets renewals</p>" * 12 + "</body></html>"
    monkeypatch.setattr(artifacts, "_llm", fake_llm)
    a = artifacts.create("default", "c1", "Build an interactive web UI for NetMitra")
    asyncio.run(artifacts._build(a.id, "Build an interactive web UI for NetMitra"))
    stages = [p["stage"] for k, p in seen if k == "artifact"]
    assert stages[:3] == ["writing", "checking", "done"], stages
    last = [p for k, p in seen if k == "artifact"][-1]
    assert last["status"] == "ready" and last["build_s"] is not None and last["started_at"] and last["now"]
    assert seen[0][1]["started_at"]                      # the card's clock starts with the build


def test_a_failure_is_said_in_plain_words(env, monkeypatch):
    from app import artifacts
    from app.events import bus
    seen = []
    monkeypatch.setattr(bus, "publish", lambda c, k, p: seen.append((k, dict(p))))

    async def broken(system, prompt, max_tokens=16000):
        raise asyncio.TimeoutError()
    monkeypatch.setattr(artifacts, "_llm", broken)
    a = artifacts.create("default", "c1", "a page")
    asyncio.run(artifacts._build(a.id, "a page"))
    last = [p for k, p in seen if k == "artifact"][-1]
    assert last["status"] == "failed" and last["stage"] == "failed"
    assert last["error"] == "The page maker took too long and was stopped."
    assert "Error" not in last["error"]                  # never a Python class name


def test_stop_cancels_the_build(env, monkeypatch):
    from app import artifacts
    from app.events import bus
    seen = []
    monkeypatch.setattr(bus, "publish", lambda c, k, p: seen.append((k, dict(p))))

    async def slow(system, prompt, max_tokens=16000):
        await asyncio.sleep(30)
    monkeypatch.setattr(artifacts, "_llm", slow)

    async def go():
        a = artifacts.create("default", "c1", "a page")
        t = artifacts.start_build(a.id, "a page")
        await asyncio.sleep(0.05)
        assert artifacts.stop("default", a.id) is True
        try:
            await t
        except asyncio.CancelledError:
            pass
        return a.id
    aid = asyncio.run(go())
    last = [p for k, p in seen if k == "artifact"][-1]
    assert last["stage"] == "stopped" and last["status"] == "failed" and last["error"] == "Stopped by you."
    assert artifacts.stop("default", aid) is False       # nothing running any more


def test_the_card_in_the_code():
    js = (CON / "v2.js").read_text()
    assert "if (kind === 'artifact' && p && p.id) { pageCard(p, live); return; }" in js
    assert "usually 20–90 s" in js and "data-stop" in js and "data-retry" in js and "data-share" in js
    assert "Date.now() + skew - t0" in js                # the clock reads the SERVER's time
    css = (CON / "v2.css").read_text()
    assert "#app .cd.hmpage{" in css and "prefers-reduced-motion" in css


def test_the_card_in_a_real_browser(arena_server):
    import httpx
    from app.db import Message, now, session
    from app.events import bus
    base, browser, key = arena_server
    h = {"Authorization": f"Bearer {key}"}
    cid = httpx.post(base + "/api/conversations", headers=h, timeout=20).json()["id"]
    with session() as s:
        s.add(Message(conversation_id=cid, role="user", content="SHOW ME WEB INTERFACE OF NETMITRA",
                      display="SHOW ME WEB INTERFACE OF NETMITRA", in_history=True))
        s.commit()
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/")
    pg.get_by_text("SHOW ME WEB INTERFACE OF NETMITRA").first.click()
    pg.wait_for_timeout(1500)
    t0 = (now() - timedelta(seconds=65)).isoformat()
    base_p = {"id": "art_demo1", "title": "NetMitra dashboard", "version": 0, "summary": "", "error": "",
              "shared": False, "started_at": t0, "now": now().isoformat(), "build_s": None}
    bus.publish(cid, "artifact", {**base_p, "status": "building", "stage": "writing"})
    pg.wait_for_timeout(1400)
    b = pg.evaluate("""()=>{const c=document.querySelectorAll('.hmpage');const e=c[0];
      return {n:c.length, pill:e?.querySelector('.hp-pill')?.textContent, clock:e?.querySelector('[data-clock]')?.textContent,
        step:e?.querySelector('[data-step]')?.textContent, stop:!!e?.querySelector('[data-stop]'),
        now:e?.querySelector('.hp-st.now')?.textContent, done:e?.querySelectorAll('.hp-st.done').length}}""")
    assert b["n"] == 1 and b["pill"] == "Building" and b["stop"], b
    assert b["clock"] in ("1:05", "1:06", "1:07"), b      # counted from the server's start time
    assert b["step"] == "Writing the page" and b["now"].endswith("Writing the page") and b["done"] == 1, b
    bus.publish(cid, "artifact", {**base_p, "status": "building", "stage": "checking"})
    pg.wait_for_timeout(500)
    assert pg.evaluate("()=>document.querySelector('.hmpage [data-step]').textContent") == "Checking it opens"
    bus.publish(cid, "artifact", {**base_p, "status": "ready", "stage": "done", "version": 1, "build_s": 47,
                                  "summary": "5 screens: Dashboard, Tickets, Renewals, Churn Radar, Outages"})
    pg.wait_for_timeout(600)
    r = pg.evaluate("""()=>{const c=document.querySelectorAll('.hmpage');const e=c[0];
      return {n:c.length, pill:e.querySelector('.hp-pill').textContent, foot:e.querySelector('.hp-foot')?.textContent,
        open:!!e.querySelector('[data-open]'), share:!!e.querySelector('[data-share]'), clock:!!e.querySelector('[data-clock]'),
        sub:e.querySelector('.hp-sub').textContent}}""")
    ctx.close()
    assert r["n"] == 1, r                                 # the same card changed, no second card
    assert r["pill"] == "Ready" and r["open"] and r["share"] and not r["clock"], r
    assert "Version 1" in r["foot"] and "0:47" in r["foot"] and "Churn Radar" in r["sub"], r
    assert not errs, errs


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.725.0")
