"""v0.999.202 LIVE AGENTS, REDESIGNED (owner: "NOW DO SAME FOR LIVE AGENTS SECTION" -> design
claude.ai/artifact/MiwxCvC2zVJACEeEaGT4wb -> "GO BUILD"): every question kept on its agent (from Try it or her website), whether
her facts held the answer, this week's numbers, the questions it could not answer with "Add the answer" (added to its facts) or
"Not needed", a builder in four steps beside Try it and Questions, the website window."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from app.interactive import live as LV
from app.interactive import studio as S
from tests.test_v0999_172_interactive_chat import DRAFT, ix, ix_server   # noqa: F401  (fixtures)

ROOT = Path(__file__).resolve().parents[1]
FACTS = "Bloom Florist, 14 Rua Augusta, Lisbon. Open 9 am to 9 pm, closed Tuesdays. Bouquets from 24 euros. Delivery 8 euros."


def _brain(system, prompt):
    q = prompt.lower()
    if "delivery" in q:
        return {"answer": "Delivery inside the city is 8 euros.", "known": True}
    if "sunday" in q:
        return {"answer": "I don't have that information. Please ask the shop directly.", "known": False}
    if "parking" in q:
        return {"answer": "Parking costs 3 euros an hour.", "known": True}      # a number she never wrote
    return {"answer": "We open at 9 am.", "known": True}


def _client():
    from app.main import app
    return TestClient(app)


def test_questions_are_kept_with_whether_the_facts_held_them(ix, monkeypatch):
    monkeypatch.setattr(LV, "_think", _brain)
    a = LV.agent_save("default", {"name": "Shop helper", "knows": FACTS, "lang": "en"})
    speak = lambda t, l: b"RIFF" + b"\x00" * 60    # noqa: E731
    r = LV.ask("default", a["id"], "How much is delivery?", speak=speak)
    assert r["known"] is True and "8 euros" in r["answer"]
    assert LV.ask("default", a["id"], "Do you deliver on Sunday?", speak=speak)["known"] is False
    p = LV.ask("default", a["id"], "Is there parking?", speak=speak)
    assert p["known"] is False and "3 euros" not in p["answer"]                # a made-up number is never said, and counted as not known
    ag = LV.agents("default")["agents"][0]
    assert ag["asked_week"] == 3 and ag["missed_week"] == 2 and "log" not in ag
    assert [m["q"] for m in ag["misses"]] == ["Is there parking?", "Do you deliver on Sunday?"]
    c = _client()
    qs = c.get(f"/api/interactive/x/live/questions?id={a['id']}").json()["questions"]
    assert len(qs) == 3 and qs[0]["src"] == "try"
    sun = next(x for x in qs if "Sunday" in x["q"])
    r = c.post("/api/interactive/x/live/learn", json={"id": a["id"], "qid": sun["id"], "answer": "Yes, Sundays 10 am to 2 pm."})
    assert r.status_code == 200 and "Q: Do you deliver on Sunday?\nA: Yes, Sundays 10 am to 2 pm." in r.json()["knows"]
    assert [m["q"] for m in r.json()["misses"]] == ["Is there parking?"]
    park = next(x for x in qs if "parking" in x["q"])
    assert c.post("/api/interactive/x/live/dismiss", json={"id": a["id"], "qid": park["id"]}).json()["misses"] == []
    assert c.post("/api/interactive/x/live/learn", json={"id": a["id"], "qid": "lq_none", "answer": "x y"}).status_code == 404
    assert c.post("/api/interactive/x/live/learn", json={"id": a["id"], "qid": park["id"], "answer": ""}).status_code == 422


def test_a_website_question_is_marked_as_from_the_website(ix, monkeypatch):
    monkeypatch.setattr(LV, "_think", _brain)
    monkeypatch.setattr(LV.VO, "speaker", lambda *a, **k: (lambda t, l: b"RIFF" + b"\x00" * 60))
    a = LV.agent_save("default", {"name": "Shop helper", "knows": FACTS, "lang": "en"})
    pub = LV.publish("default", a["id"], True, ["bloom.shop"])
    LV.public_ask(pub["token"], "Do you deliver on Sunday?", "https://bloom.shop", "1.2.3.4")
    assert LV.questions("default", a["id"])["questions"][0]["src"] == "web"


def test_the_page_code_is_wired():
    root = ROOT / "app" / "static" / "console"
    js = (root / "interactive.js").read_text("utf-8")
    css = (root / "interactive2.css").read_text("utf-8")
    assert subprocess.run(["node", "--check", str(root / "interactive.js")], capture_output=True).returncode == 0
    blk = js[js.index("live agents (v0.999.202"):js.index("// ------------------------------------------------------------------ pages ---")]
    drawn = set(re.findall(r'data-a="([a-z]+)"', blk))
    cases = set(re.findall(r"case '([a-z]+)':", js))
    assert drawn <= cases, drawn - cases
    assert "hxLiveF" not in js and "UI.pub &&" not in js                        # the old form is gone
    for r in ("/live/questions?id=", "/live/learn", "/live/dismiss", "/live/publish", "/live/ask", "/api/vocal/voice/preview?id="):
        assert r in js, r
    for c in (".hx-lvks", ".hx-lvgrid", ".hx-lvc", ".hx-lvmiss", ".hx-lvform", ".hx-lvtry", ".hx-lvlog", ".hx-lvcode"):
        assert f"#hxRoot {c}" in css, c


def _until(ok, wait=8.0):
    import time
    end = time.time() + wait
    while time.time() < end:
        if ok():
            return
        time.sleep(0.15)
    assert ok()


def _open(pg, base, vp):
    pg.goto(base + "/console/?v=interactive")
    pg.wait_for_selector("#hxRoot .hx-side [data-p=live]", state="attached", timeout=25000)
    if vp["width"] < 900:
        pg.click("#hxRoot .hx-menu")
    pg.click("#hxRoot .hx-side [data-p=live]")
    pg.wait_for_selector("#hxRoot .hx-lvpage", timeout=15000)


def test_live_agents_in_a_real_browser(ix_server, monkeypatch):
    base, browser, key = ix_server
    shots = os.environ.get("HOOLA_SHOTS")
    errors: list[str] = []
    monkeypatch.setattr(LV, "_think", _brain)
    monkeypatch.setattr(LV.VO, "speaker", lambda *a, **k: (lambda t, l: b"RIFF" + b"\x00" * 60))
    for vp in ({"width": 1440, "height": 900}, {"width": 390, "height": 844}):
        ctx = browser.new_context(viewport=vp)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        _open(pg, base, vp)
        if vp["width"] > 900:
            assert pg.locator(".hx-avfirst").count() == 1
            pg.click("[data-a=livenew]")
            pg.wait_for_selector(".hx-lvform", timeout=5000)
            assert "Save the agent first" in pg.inner_text(".hx-lvtry")
            pg.fill("[data-lv=name]", "Shop helper")
            pg.fill("[data-lv=opening]", "Hello! Ask me about flowers or delivery.")
            pg.fill("[data-lv=knows]", FACTS)
            assert "24" in pg.inner_text("#hxLvNums") and "8" in pg.inner_text("#hxLvNums")
            pg.click("[data-a=livesave]")
            _until(lambda: "Saved" in pg.inner_text(".hx-lvhd"))
            assert S._load("default")["agents"][0]["name"] == "Shop helper"
            # try it: one from the facts, one it could not answer
            pg.fill("#hxTryIn", "How much is delivery?")
            pg.keyboard.press("Enter")
            _until(lambda: "From your facts" in pg.inner_text("#hxTry"))
            pg.fill("#hxTryIn", "Do you deliver on Sunday?")
            pg.click("[data-a=liveask]")
            _until(lambda: "Not in your facts" in pg.inner_text("#hxTry"))
            if shots:
                pg.wait_for_timeout(400)
                pg.screenshot(path=f"{shots}/ix202-build-1440.png", full_page=True)
            pg.click("#hxTry [data-a=lvlearn]")
            pg.wait_for_selector("#hxLvAns", timeout=5000)
            assert "Do you deliver on Sunday?" in pg.inner_text("#hxDlg")
            pg.fill("#hxLvAns", "Yes, on Sundays from 10 am to 2 pm.")
            pg.click("[data-a=lvlearnsave]")
            _until(lambda: "Yes, on Sundays" in pg.input_value("[data-lv=knows]"))
            pg.click("[data-a=lvtab][data-val=qs]")
            _until(lambda: "Answer added" in pg.inner_text(".hx-lvqs"))
            # her website
            pg.click(".hx-lvhd [data-a=lvweb]")
            pg.wait_for_selector("#hxLvSite", timeout=5000)
            pg.fill("#hxLvSite", "https://bloom.shop/home")
            pg.keyboard.press("Enter")
            _until(lambda: "bloom.shop" in pg.inner_text(".hx-lvsites"))
            pg.click("[data-a=lvpub]")
            pg.wait_for_selector(".hx-lvcode", timeout=8000)
            assert "data-agent=" in pg.inner_text(".hx-lvcode")
            if shots:
                pg.wait_for_timeout(400)
                pg.screenshot(path=f"{shots}/ix202-web-1440.png")
            pg.click("[data-a=lvpub]")                                          # Done
            pg.click("[data-a=liveback]")
            pg.wait_for_selector(".hx-lvc", timeout=5000)
            assert "On your website" in pg.inner_text(".hx-lvc") and "2" in pg.inner_text(".hx-lvks")
        else:
            assert pg.locator(".hx-lvc").count() == 1
        if shots:
            pg.wait_for_timeout(400)
            pg.screenshot(path=f"{shots}/ix202-live-{vp['width']}.png", full_page=True)
        assert pg.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 1
        ctx.close()
    assert not errors, errors
