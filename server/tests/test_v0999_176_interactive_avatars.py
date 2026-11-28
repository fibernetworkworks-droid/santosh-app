"""v0.999.176 AVATARS, REDESIGNED (owner: "NOW DO SAME FOR AVATHAR SECTION - MAKE IT ADVANCE, PREMIUM AND PERECT" -> design
claude.ai/artifact/D5nT24BS35LP5KpAmHKqoy -> "GO BUILD"): her faces as cards with their consent record and where they are used,
a side panel per face (rename, default, test video, remove), a face from a photo (whose face, size checked), a face made by AI
(no real person, priced first, refused for famous people), a video twin explained."""
from __future__ import annotations

import io
import os
import re
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from app.interactive import studio as S
from tests.test_v0999_172_interactive_chat import DRAFT, ix, ix_server   # noqa: F401  (fixtures)

ROOT = Path(__file__).resolve().parents[1]


def _png(w: int, h: int, color=(180, 140, 100)) -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (w, h), color).save(b, "PNG")
    return b.getvalue()


def _client():
    from app.main import app
    return TestClient(app)


def test_a_photo_face_records_whose_face_and_checks_the_size(ix, tmp_path):
    small, good = tmp_path / "s.png", tmp_path / "g.png"
    small.write_bytes(_png(200, 260))
    good.write_bytes(_png(600, 750))
    try:
        S.add_avatar("default", "Tiny", str(small), consent=True)
        raise AssertionError("a tiny photo was taken")
    except S.StudioError as e:
        assert "too small (200 x 260)" in str(e)
    try:
        S.add_avatar("default", "Kunal", str(good), consent=True, who="agreed")
        raise AssertionError("no person named")
    except S.StudioError as e:
        assert "name of the person who agreed" in str(e)
    a = S.add_avatar("default", "Kunal", str(good), consent=True, who="agreed", person="Kunal Rao")
    assert a["who"] == "agreed" and a["person"] == "Kunal Rao" and (a["width"], a["height"]) == (600, 750)
    assert "Kunal Rao agreed" in a["consent"] and a["kind"] == "photo"
    me = S.add_avatar("default", "Meghana", str(good), consent=True)
    assert me["who"] == "me" and me["person"] == "" and "her own face" in me["consent"]
    c = _client()
    r = c.patch("/api/interactive/studio/avatar", json={"id": me["id"], "name": "  Meghana   S "})
    assert r.status_code == 200 and r.json()["name"] == "Meghana S"
    assert c.patch("/api/interactive/studio/avatar", json={"id": me["id"], "name": " "}).status_code == 422
    assert c.patch("/api/interactive/studio/avatar", json={"id": "av_none", "name": "X"}).status_code == 404


def test_an_ai_face_is_priced_refused_for_famous_people_and_kept_as_ai(ix, monkeypatch):
    from app.create import jobs, service as cs
    c = _client()
    monkeypatch.setattr(cs, "ready", lambda: {"image": False, "song": False, "voice": False, "dub": False})
    q = c.get("/api/interactive/studio/avatar/ai/quote").json()
    assert q["ready"] is False and q["credits"] >= 1 and q["count"] == 4
    assert c.post("/api/interactive/studio/avatar/ai", json={"describe": "a teacher"}).status_code == 409
    monkeypatch.setattr(cs, "ready", lambda: {"image": True, "song": False, "voice": False, "dub": False})
    assert c.post("/api/interactive/studio/avatar/ai", json={"describe": "", "age": "", "look": ""}).status_code == 422
    r = c.post("/api/interactive/studio/avatar/ai", json={"describe": "looks exactly like Shah Rukh Khan the actor"})
    assert r.status_code == 422 and "real, well-known people" in r.json()["detail"]
    p = S.ai_face_prompt("a calm woman", "30s", "expert", "shop")
    assert "invented, made-up person who does not exist" in p and photogen_ok(p) and "in their thirties" in p and "shop" in p
    # keep one of her pictures as a face
    it = jobs.keep("default", "image", "AI face", ".png", _png(512, 640), {"prompt": p})
    row = c.post("/api/interactive/studio/avatar/keep", json={"item_id": it["id"], "name": "Asha (AI)"}).json()
    assert row["kind"] == "ai" and row["ai"] is True and row["consent_at"] == "" and "not a real person" in row["consent"]
    assert S.photo_path("default", row["id"]).is_file()
    assert c.post("/api/interactive/studio/avatar/keep", json={"item_id": "nope", "name": "X"}).status_code == 404
    song = jobs.keep("default", "song", "A song", ".mp3", b"ID3....", {})
    assert c.post("/api/interactive/studio/avatar/keep", json={"item_id": song["id"], "name": "X"}).status_code == 422


def photogen_ok(p):
    from app import photogen
    return photogen.problem(p) == ""          # Hoola's own wording never trips the picture engine's famous-person filter


def test_the_page_code_is_wired():
    root = ROOT / "app" / "static" / "console"
    js = (root / "interactive.js").read_text("utf-8")
    css = (root / "interactive2.css").read_text("utf-8")
    assert subprocess.run(["node", "--check", str(root / "interactive.js")], capture_output=True).returncode == 0
    blk = js[js.index("avatars (v0.999.176"):js.index("// ------------------------------------------------------------------ pages ---")]
    drawn = set(re.findall(r'data-a="([a-z]+)"', blk))
    cases = set(re.findall(r"case '([a-z]+)':", js))
    for k in ("avadd", "avai", "avtwin"):
        assert f"case '{k}':" in js, k
    assert drawn <= cases, drawn - cases
    assert "hxAvForm" not in js and "avSave()" not in js                         # the old inline form is gone
    for r in ("/avatar/ai/quote?count=4", "/avatar/ai`", "/avatar/keep", "'PATCH', `${S}/avatar`", "/api/create/jobs/", "/api/create/items/"):
        assert r in js, r
    for c in (".hx-avways", ".hx-avgrid", ".hx-avc2", ".hx-avp", ".hx-avside", ".hx-avrec", ".hx-avdrop", ".hx-avwho", ".hx-aipicks"):
        assert f"#hxRoot {c}" in css, c


def _open(pg, base, vp):
    pg.goto(base + "/console/?v=interactive")
    pg.wait_for_selector("#hxRoot .hx-side [data-p=avatars]", state="attached", timeout=25000)
    if vp["width"] < 900:
        pg.click("#hxRoot .hx-menu")
    pg.click("#hxRoot .hx-side [data-p=avatars]")
    pg.wait_for_selector("#hxRoot .hx-avpage", timeout=15000)


def test_avatars_in_a_real_browser(ix_server, monkeypatch, tmp_path):
    base, browser, key = ix_server
    shots = os.environ.get("HOOLA_SHOTS")
    errors: list[str] = []
    from app import photogen
    from app.create import service as cs
    monkeypatch.setattr(cs, "ready", lambda: {"image": True, "song": False, "voice": False, "dub": False})
    made = []

    def fake_make(prompt, images=None, aspect="", quality="fast", consent=False):
        made.append(prompt)
        return {"png": _png(400, 500, (120 + 30 * len(made), 110, 200)), "model": "test", "aspect": "4:5", "quality": "fast", "edit": False, "cost_inr": 3}
    monkeypatch.setattr(photogen, "make", fake_make)
    photo = tmp_path / "me.png"
    photo.write_bytes(_png(800, 1000))
    tiny = tmp_path / "tiny.png"
    tiny.write_bytes(_png(120, 150))
    for vp in ({"width": 1440, "height": 900}, {"width": 390, "height": 844}):
        ctx = browser.new_context(viewport=vp)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        _open(pg, base, vp)
        if vp["width"] > 900:
            assert pg.locator(".hx-avfirst").count() == 1 and pg.locator(".hx-avway").count() == 3
            if shots:
                pg.wait_for_timeout(300)
                pg.screenshot(path=f"{shots}/ix176-empty-1440.png", full_page=True)
            # a video twin says what it needs
            pg.click(".hx-avway[data-a=avtwin]")
            pg.wait_for_selector("#hxDlg .hx-dlg", timeout=5000)
            assert "Needs an engine" in pg.inner_text("#hxDlg")
            pg.keyboard.press("Escape")
            # a face from a photo: too small first, then a good one, someone who agreed
            pg.click(".hx-avway[data-a=avadd]")
            pg.wait_for_selector("#hxDlg .hx-avdrop", timeout=5000)
            pg.set_input_files("#hxAvPh", str(tiny))
            pg.wait_for_selector("#hxDlg .hx-avcks", timeout=5000)
            _until(lambda: "Too small" in pg.inner_text("#hxDlg"))
            assert pg.locator("[data-a=avphsave]").is_disabled()
            pg.set_input_files("#hxAvPh", str(photo))
            _until(lambda: "Big enough" in pg.inner_text("#hxDlg"))
            pg.fill("#hxAvNm", "Kunal")
            pg.check("input[name=hxAvWho][value=agreed]")
            pg.wait_for_selector("#hxAvPer", timeout=5000)
            pg.fill("#hxAvPer", "Kunal Rao")
            assert pg.locator("[data-a=avphsave]").is_disabled()          # not ticked yet
            pg.check("#hxAvOk")
            if shots:
                pg.wait_for_timeout(400)
                pg.screenshot(path=f"{shots}/ix176-photo-1440.png")
            pg.click("[data-a=avphsave]")
            pg.wait_for_selector(".hx-avc2", timeout=15000)
            a = S._load("default")["avatars"][0]
            assert a["name"] == "Kunal" and a["person"] == "Kunal Rao" and a["who"] == "agreed"
            assert "Kunal Rao agreed" in pg.inner_text(".hx-avc2")
            # a face made by AI
            pg.click(".hx-avway[data-a=avai]")
            pg.wait_for_selector("#hxAiD", timeout=5000)
            _until(lambda: "credit" in pg.inner_text("[data-a=aimake]"))
            pg.fill("#hxAiD", "A friendly woman, simple teal kurta")
            pg.click("[data-a=aiopt][data-k=behind][data-val=shop]")
            assert pg.input_value("#hxAiD") == "A friendly woman, simple teal kurta"     # kept through the repaint
            pg.click("[data-a=aimake]")
            try:
                pg.wait_for_selector(".hx-aipick", timeout=20000)
            except Exception:
                raise AssertionError(pg.inner_text("#hxDlg"))
            assert pg.locator(".hx-aipick").count() == 4 and "teal kurta" in made[0] and "shop" in made[0]
            pg.click(".hx-aipick >> nth=1")
            pg.fill("#hxAiNm", "Asha (AI)")
            if shots:
                pg.wait_for_timeout(500)
                pg.screenshot(path=f"{shots}/ix176-ai-1440.png")
            pg.click("[data-a=aikeep]")
            _until(lambda: pg.locator(".hx-avc2").count() == 2)
            assert S._load("default")["avatars"][0]["kind"] == "ai"
            # filters, search, the side panel: rename, default, test video
            pg.click(".hx-avbar [data-val=ai]")
            assert pg.locator(".hx-avc2").count() == 1
            pg.click(".hx-avbar [data-val=all]")
            pg.fill("#hxAvq", "kun")
            assert pg.locator(".hx-avc2").count() == 1
            pg.fill("#hxAvq", "")
            pg.click(".hx-avc2:has-text('Kunal')")
            assert "Kunal Rao agreed" in pg.inner_text(".hx-avside")
            pg.click(".hx-avside [data-a=avren]")
            pg.fill("#hxAvRn", "Kunal R")
            pg.click("[data-a=avrensave]")
            _until(lambda: "Kunal R" in pg.inner_text(".hx-avside h2"))
            pg.click(".hx-avside [data-a=avdefault]")
            _until(lambda: pg.locator(".hx-avc2 .hx-avdef").count() == 1)
            if shots:
                pg.wait_for_timeout(500)
                pg.screenshot(path=f"{shots}/ix176-avatars-1440.png", full_page=True)
            pg.click(".hx-avside [data-a=avtest]")
            pg.wait_for_selector("#hxRoot .hx-edb", timeout=15000)
            p = S._load("default")["projects"][0]
            assert p["avatar_id"] == S._load("default")["avatars"][1]["id"]
        else:
            assert pg.locator(".hx-avc2").count() == 2 and pg.locator(".hx-avc2 .hx-avdef").count() == 0   # default is per browser
            if shots:
                pg.wait_for_timeout(400)
                pg.screenshot(path=f"{shots}/ix176-avatars-390.png", full_page=True)
        assert pg.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 1
        ctx.close()
    assert not errors, errors


def _until(ok, wait=8.0):
    import time
    end = time.time() + wait
    while time.time() < end:
        if ok():
            return
        time.sleep(0.15)
    assert ok()
