"""v0.999.208 ENGINES, REDESIGNED (owner: "NOW DO SAME FOR ENGINES SECTION" -> design claude.ai/artifact/QzR1tQ2n8v4zyjxdiTU7yG
-> "GO BUILD"): her three defaults, every engine of a job priced for one length the way the Make price card prices it,
cards saying Ready / Default / Not connected in plain words (never a key name), a panel per engine with its price at each
length and her videos on it, and the B-roll shot maker with its price first."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from app.interactive import engines as EN
from app.interactive import studio as S
from tests.test_v0999_172_interactive_chat import ix, ix_server   # noqa: F401  (fixtures)

ROOT = Path(__file__).resolve().parents[1]


def _client():
    from app.main import app
    return TestClient(app)


def test_prices_for_a_length_match_the_make_price(ix, monkeypatch):
    monkeypatch.setenv("KIE_API_KEY", "test-only")
    cl = _client()
    r = cl.get("/api/interactive/x/engines/prices?job=video&seconds=30").json()
    assert r["seconds"] == 30 and r["job"] == "video"
    by = {e["id"]: e for e in r["engines"]}
    assert set(by) == {e["id"] for e in EN.ENGINES if e["job"] == "video"}
    assert by["kling"]["face_credits"] == EN.quote("kling", 30.0)["face_credits"] == 1515
    assert by["kling"]["credits"] == 1515 + r["voice_credits"]                  # the same price the Make card shows
    assert by["hoola"]["face_credits"] == 0                                      # only the voice
    assert by["wan_s2v"]["too_long"] is True and by["kling"]["too_long"] is False
    live = cl.get("/api/interactive/x/engines/prices?job=live&seconds=300").json()
    assert live["voice_credits"] == 0 and {e["id"] for e in live["engines"]} == {e["id"] for e in EN.ENGINES if e["job"] == "live"}
    assert cl.get("/api/interactive/x/engines/prices?job=film&seconds=30").status_code in (409, 422)
    # the rows say what an engine needs in plain words, never a key name
    rows = cl.get("/api/interactive/x/engines").json()["engines"]
    k = next(e for e in rows if e["id"] == "kling")
    assert k["ready"] and k["need"] == "" and k["max_s"] == 300
    off = next(e for e in rows if e["id"] == "runway")
    assert not off["ready"] and "server's settings" in off["need"] and "_KEY" not in off["need"]
    assert next(e for e in rows if e["id"] == "voice_only")["need"] == ""


def test_one_engine_panel(ix, monkeypatch):
    monkeypatch.setenv("KIE_API_KEY", "test-only")
    cl = _client()
    p = S.draft("default", "Summer offers at the bakery", engine="kling")
    r = cl.get("/api/interactive/x/engines/one?id=kling").json()
    assert r["engine"]["id"] == "kling" and r["engine"]["ready"]
    assert [x["seconds"] for x in r["prices"]] == [15, 30, 60, 180, 300]
    assert all(x["credits"] == x["face"] + x["voice"] for x in r["prices"])
    assert r["prices"][1]["face"] == 1515 and not any(x["too_long"] for x in r["prices"])
    assert [v["id"] for v in r["videos"]] == [p["id"]]
    w = cl.get("/api/interactive/x/engines/one?id=wan_s2v").json()
    assert [x["too_long"] for x in w["prices"]] == [False, True, True, True, True]
    assert cl.get("/api/interactive/x/engines/one?id=gemini_broll").json()["prices"][0]["seconds"] == 4
    assert cl.get("/api/interactive/x/engines/one?id=nope").status_code == 404
    # a default can only be an engine that is ready
    assert cl.put("/api/interactive/x/engines/default", json={"id": "runway"}).status_code == 409
    d = cl.put("/api/interactive/x/engines/default", json={"id": "kling"}).json()["defaults"]
    assert d["video"] == "kling"


def test_the_page_code_is_wired():
    root = ROOT / "app" / "static" / "console"
    js = (root / "interactive.js").read_text("utf-8")
    css = (root / "interactive2.css").read_text("utf-8")
    assert subprocess.run(["node", "--check", str(root / "interactive.js")], capture_output=True).returncode == 0
    blk = js[js.index("engines (v0.999.208"):js.index("// ---- brand (v0.999.207")]
    drawn = set(re.findall(r'data-a="([a-z]+)"', blk))
    cases = set(re.findall(r"case '([a-z]+)':", js))
    assert drawn <= cases, drawn - cases
    assert "engines() { return enPage(); }" in js and '<table class="hx-table"><thead><tr><th>Engine</th>' not in js
    for r in ("/engines/prices", "/engines/one", "/engines/default", "/broll/quote"):
        assert r in js, r
    for c in (".hx-endefs", ".hx-engrid", ".hx-encard", ".hx-enchip", ".hx-enlad", ".hx-enfacts", ".hx-enshg", ".hx-enbr"):
        assert f"#hxRoot {c}" in css, c


def _until(ok, wait=8.0):
    import time
    end = time.time() + wait
    while time.time() < end:
        if ok():
            return
        time.sleep(0.15)
    assert ok()


def test_engines_in_a_real_browser(ix_server, monkeypatch):
    monkeypatch.setenv("KIE_API_KEY", "test-only")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    base, browser, key = ix_server
    shots = os.environ.get("HOOLA_SHOTS")
    errors: list[str] = []
    mine = S.draft("default", "Summer offers at the bakery", engine="kling")["title"]
    for vp in ({"width": 1440, "height": 900}, {"width": 390, "height": 844}):
        ctx = browser.new_context(viewport=vp)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/?v=interactive")
        pg.wait_for_selector("#hxRoot .hx-side [data-p=engines]", state="attached", timeout=25000)
        if vp["width"] < 900:
            pg.click("#hxRoot .hx-menu")
        pg.click("#hxRoot .hx-side [data-p=engines]")
        pg.wait_for_selector("#hxRoot .hx-enpage .hx-encard", timeout=15000)
        _until(lambda: "1,515" in pg.inner_text(".hx-engrid"))                     # the price for 30 s, from the server
        assert "_KEY" not in pg.inner_text(".hx-enpage")
        if vp["width"] > 900:
            assert "Too long" in pg.inner_text(".hx-engrid")                          # Wan stops at 15 s
            pg.click("[data-a=enlen][data-val='15']")
            n15 = f"{EN.quote('kling', 15.0)['face_credits']:,}"
            _until(lambda: n15 in pg.inner_text(".hx-engrid"))
            pg.click("[data-a=enready]")
            assert "Runway avatar" not in pg.inner_text(".hx-engrid")
            pg.click("[data-a=enready]")
            if shots:
                pg.wait_for_timeout(500)
                pg.screenshot(path=f"{shots}/ix208-engines-1440.png", full_page=True)
            # make Kling the default, from its card
            pg.click(".hx-encard:has-text('Kling AI Avatar') >> nth=0 >> [data-a=edef]")
            _until(lambda: (S._load("default").get("engines") or {}).get("video") == "kling")
            _until(lambda: "Kling AI Avatar" in pg.inner_text(".hx-endef.on"))
            # one engine: price by length and her videos on it
            pg.click(".hx-encard.def [data-a=enone]")
            pg.wait_for_selector(".hx-enone .hx-enlad", timeout=8000)
            _until(lambda: mine in pg.inner_text(".hx-enone"))
            assert "5 min" in pg.inner_text(".hx-enlad")
            if shots:
                pg.wait_for_timeout(500)
                pg.screenshot(path=f"{shots}/ix208-engines-one.png")
            pg.click(".hx-enone [data-a=dlgx] >> nth=0")
            # a not connected engine says how, in plain words
            pg.click(".hx-encard:has-text('Runway avatar') [data-a=enone] >> nth=0")
            _until(lambda: "server's settings" in pg.inner_text(".hx-enone"))
            pg.click(".hx-enone [data-a=dlgx] >> nth=0")
            # B-roll: the price before Make the shot
            pg.click("[data-a=etab][data-val=broll] >> nth=0")
            pg.wait_for_selector("#hxBr", timeout=5000)
            _until(lambda: "credits" in pg.inner_text(".hx-enpr"))
            assert not pg.is_disabled("[data-a=brmake]")
            if shots:
                pg.wait_for_timeout(400)
                pg.screenshot(path=f"{shots}/ix208-engines-broll.png", full_page=True)
        else:
            assert pg.evaluate("document.documentElement.scrollWidth") <= 392
            if shots:
                pg.wait_for_timeout(700)
                pg.screenshot(path=f"{shots}/ix208-engines-390.png", full_page=True)
        ctx.close()
    assert not errors, errors
