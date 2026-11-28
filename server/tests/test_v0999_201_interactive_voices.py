"""v0.999.201 VOICES, REDESIGNED (owner: "NOW DO SAME FOR VOICES SECTION" -> design claude.ai/artifact/FaMDEFsqTVCJsv6tF4ptE6
-> "GO BUILD"): the voice her videos speak in at the top, find a voice by describing it (best matches first, the why said),
filters, a sample in the language she picks, favourites shared with Hoola Vocal, a voice put into several videos at once (only the
voice changes, free), a voice that is not connected says so."""
from __future__ import annotations

import io
import os
import re
import subprocess
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from app.interactive import studio as S
from app.interactive import voice as VO
from tests.test_v0999_172_interactive_chat import DRAFT, ix, ix_server   # noqa: F401  (fixtures)

ROOT = Path(__file__).resolve().parents[1]

LIB = [
    {"id": "hv_charon", "name": "Charon", "gender": "male", "tone": "Informative, deep", "accent": "", "age": "middle", "use": "", "engine": "gemini",
     "tier": "standard", "ready": True, "langs": [], "any": True, "color": 0},
    {"id": "hv_aoede", "name": "Aoede", "gender": "female", "tone": "Breezy, warm", "accent": "", "age": "", "use": "", "engine": "gemini",
     "tier": "standard", "ready": True, "langs": [], "any": True, "color": 1},
    {"id": "ev_george", "name": "George", "gender": "male", "tone": "Warm storyteller", "accent": "British", "age": "older", "use": "narration",
     "engine": "eleven", "tier": "premium", "ready": True, "langs": ["en"], "any": True, "color": 2},
    {"id": "ev_lily", "name": "Lily", "gender": "female", "tone": "Bright, young", "accent": "American", "age": "young", "use": "ads",
     "engine": "eleven", "tier": "premium", "ready": False, "langs": ["en"], "any": True, "color": 3},
]


def _wav() -> bytes:
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 4000)
    return b.getvalue()


def _fake(monkeypatch):
    from app.vocal import service as V
    real_voices = VO.voices

    def voices(tenant):
        d = V._load(tenant)
        return {"mine": [{"id": "vc_me", "name": "Meghana", "kind": "clone", "engine": "eleven", "tier": "premium", "ready": True, "langs": [], "any": True, "color": 4}],
                "library": LIB, "favs": list(d.get("favs") or []), "default": "hv_aoede",
                "sample_lines": {"en": "Hello! This is how I will sound in your videos.", "es": "¡Hola! Así sonaré en tus vídeos."}}
    monkeypatch.setattr(VO, "voices", voices)
    ids = {v["id"] for v in LIB} | {"vc_me"}

    def info(tenant, vid):
        if vid not in ids:
            raise VO.VoiceError("That voice was not found.")
        return {"id": vid, "name": vid, "engine": "gemini", "tier": "standard"}
    monkeypatch.setattr(VO, "voice_info", info)
    heard = []

    async def preview(tenant, voice, lang="en"):
        heard.append((voice, lang))
        return _wav()
    monkeypatch.setattr(V, "preview", preview)
    monkeypatch.setattr(V, "voice_fav", lambda tenant, vid, on=True: _fav(V, tenant, vid, on))
    return real_voices, heard


def _fav(V, tenant, vid, on):
    d = V._load(tenant)
    favs = [x for x in (d.get("favs") or []) if x != vid] + ([vid] if on else [])
    d["favs"] = favs
    V._store(tenant, d)
    return {"favs": favs}


def test_the_voice_list_carries_sample_lines_and_ages(ix):
    from app.vocal import service as V
    r = VO.voices("default")
    assert "sample_lines" in r and r["sample_lines"].get("en") == V.PREVIEW["en"]
    for v in r["library"]:
        assert "age" in v and "use" in v


def test_a_voice_goes_into_several_videos(ix, monkeypatch):
    _fake(monkeypatch)
    a = S.draft("default", "Spring sale on every plant")
    b = S.draft("default", "New opening hours from Monday")
    c = _client()
    r = c.post("/api/interactive/x/voices/apply", json={"voice": "hv_charon", "ids": [a["id"], b["id"], "nope"]})
    assert r.status_code == 200 and sorted(r.json()["done"]) == sorted([a["id"], b["id"]]) and r.json()["skipped"][0]["id"] == "nope"
    ps = {p["id"]: p for p in S._load("default")["projects"]}
    assert ps[a["id"]]["voice"] == "hv_charon" and ps[b["id"]]["voice"] == "hv_charon"
    assert ps[a["id"]]["scenes"] == a["scenes"]                       # only the voice changed
    assert c.post("/api/interactive/x/voices/apply", json={"voice": "hv_none", "ids": [a["id"]]}).status_code == 404
    assert c.post("/api/interactive/x/voices/apply", json={"voice": "", "ids": [a["id"]]}).status_code == 422
    assert c.post("/api/interactive/x/voices/apply", json={"voice": "hv_charon", "ids": []}).status_code == 422


def _client():
    from app.main import app
    return TestClient(app)


def test_the_page_code_is_wired():
    root = ROOT / "app" / "static" / "console"
    js = (root / "interactive.js").read_text("utf-8")
    css = (root / "interactive2.css").read_text("utf-8")
    assert subprocess.run(["node", "--check", str(root / "interactive.js")], capture_output=True).returncode == 0
    blk = js[js.index("voices (v0.999.201"):js.index("// ------------------------------------------------------------------ pages ---")]
    drawn = set(re.findall(r'data-a="([a-z]+)"', blk))
    cases = set(re.findall(r"case '([a-z]+)':", js))
    assert drawn <= cases, drawn - cases
    assert "Vv.library.slice(0, 80)" not in js                                  # the old flat list is gone
    for r in ("/api/vocal/voice/preview?id=", "/api/vocal/voices/fav", "/voices/apply"):
        assert r in js, r
    for c in (".hx-vocur", ".hx-vodesc", ".hx-vol", ".hx-vor", ".hx-voside", ".hx-vopick", ".hx-vtier"):
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
    pg.wait_for_selector("#hxRoot .hx-side [data-p=voices]", state="attached", timeout=25000)
    if vp["width"] < 900:
        pg.click("#hxRoot .hx-menu")
    pg.click("#hxRoot .hx-side [data-p=voices]")
    pg.wait_for_selector("#hxRoot .hx-vol", timeout=15000)


def test_voices_in_a_real_browser(ix_server, monkeypatch):
    base, browser, key = ix_server
    shots = os.environ.get("HOOLA_SHOTS")
    errors: list[str] = []
    _, heard = _fake(monkeypatch)
    a = S.draft("default", "Spring sale on every plant")
    S.save("default", a["id"], {"title": "Spring sale at Bloom"})
    b = S.draft("default", "New opening hours from Monday")
    S.save("default", b["id"], {"title": "New hours from Monday"})
    for vp in ({"width": 1440, "height": 900}, {"width": 390, "height": 844}):
        ctx = browser.new_context(viewport=vp)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        _open(pg, base, vp)
        assert pg.locator(".hx-vor").count() == 5
        if vp["width"] > 900:
            assert "Aoede" in pg.inner_text(".hx-vocur") and "Hoola picks it" in pg.inner_text(".hx-vocur")
            # describe a voice: best matches first, the why said
            pg.fill("#hxVoq", "calm older man, storyteller")
            _until(lambda: pg.locator(".hx-vor").first.inner_text().startswith("G") or "George" in pg.locator(".hx-vor").first.inner_text())
            assert "matches" in pg.locator(".hx-vor").first.inner_text()
            assert pg.locator(".hx-vor:has-text('Aoede')").count() == 0          # a woman's voice is not a match for "man"
            pg.fill("#hxVoq", "")
            pg.click(".hx-avbar [data-val=premium]")
            assert pg.locator(".hx-vor").count() == 2 and "Not connected" in pg.inner_text(".hx-vor:has-text('Lily')")
            pg.click(".hx-avbar [data-val=all]")
            # a favourite is shared with Vocal
            pg.click(".hx-vor:has-text('Charon') [data-a=vofav]")
            _until(lambda: pg.locator(".hx-avbar [data-val=fav] .hx-num").inner_text() == "1")
            from app.vocal import service as V
            assert "hv_charon" in (V._load("default").get("favs") or [])
            pg.click(".hx-avbar [data-val=fav]")
            assert pg.locator(".hx-vor").count() == 1
            pg.click(".hx-avbar [data-val=all]")
            # a sample in the language she picks
            pg.click(".hx-vor:has-text('Charon') [data-a=vosel]")
            pg.click(".hx-voside [data-a=volang]")
            pg.wait_for_selector("[role=menu]", timeout=5000)
            pg.keyboard.type("Spanish")
            pg.wait_for_timeout(300)
            pg.locator("[role=menuitem]:has-text('Spanish'), [role=menuitemradio]:has-text('Spanish')").first.click()
            _until(lambda: "Así sonaré" in pg.inner_text(".hx-voside"))
            pg.click(".hx-voside [data-a=voplay]")
            _until(lambda: ("hv_charon", "es") in heard)
            # use for my videos, then put it in two videos
            pg.click(".hx-voside [data-a=vouse]")
            _until(lambda: "Charon" in pg.inner_text(".hx-vocur"))
            pg.click(".hx-voside [data-a=voput]")
            pg.wait_for_selector("#hxDlg .hx-vopick", timeout=5000)
            pg.check(f"[data-vop='{a['id']}']")
            pg.check(f"[data-vop='{b['id']}']")
            assert "2 videos chosen" in pg.inner_text("#hxDlg")
            if shots:
                pg.wait_for_timeout(400)
                pg.screenshot(path=f"{shots}/ix201-put-1440.png")
            pg.click("[data-a=voputgo]")
            _until(lambda: pg.locator("#hxDlg").count() == 0)
            assert {p["voice"] for p in S._load("default")["projects"] if p["id"] in (a["id"], b["id"])} == {"hv_charon"}
            _until(lambda: "In 2 of your videos" in pg.inner_text(".hx-voside"))
        if shots:
            pg.wait_for_timeout(400)
            pg.screenshot(path=f"{shots}/ix201-voices-{vp['width']}.png", full_page=True)
        assert pg.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 1
        ctx.close()
    assert not errors, errors
