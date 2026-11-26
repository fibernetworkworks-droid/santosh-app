"""v0.999.205 BRAND, REDESIGNED (owner: "NOW DO SAME FOR BRAND SECTION" -> design claude.ai/artifact/9KiLgKxN4xkWGL4rrJZx6H
-> "GO BUILD"): name on screen (shown in the corner or not), colour with a contrast check, the logo shared with the poster
Brand kit, the closing card (line + logo / QR code / both / nothing) drawn into the real video, a preview, words to keep
(kept as written or always becomes one word in a language), and Use my Brand kit (only what she ticks comes in)."""
from __future__ import annotations

import io
import os
import re
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from app.interactive import hub as H
from app.interactive import studio as S
from tests.test_v0999_172_interactive_chat import ix, ix_server   # noqa: F401  (fixtures)

ROOT = Path(__file__).resolve().parents[1]


def _client():
    from app.main import app
    return TestClient(app)


def _png(w=400, h=300, color=(46, 111, 142)):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (w, h), color).save(b, format="PNG")
    return b.getvalue()


def test_brand_settings_and_the_closing_card(ix):
    cl = _client()
    info = cl.get("/api/interactive/hub/brand").json()
    assert info["brand"]["show_name"] is True and info["brand"]["card"] == "logo" and info["glossary_max"] == 200
    assert cl.put("/api/interactive/hub/brand", json={"name": "Bright Smile", "color": "#2e6f8e", "card": "qr"}).status_code == 422  # QR needs an address
    assert cl.put("/api/interactive/hub/brand", json={"name": "x", "qr_url": "brightsmile.example"}).status_code == 422        # not a full address
    assert cl.put("/api/interactive/hub/brand", json={"name": "x", "card": "banner"}).status_code == 422
    b = cl.put("/api/interactive/hub/brand", json={"name": "Bright Smile", "color": "#2e6f8e", "closing": "Book a check-up today",
                                                   "card": "qr", "qr_url": "https://brightsmile.example/book", "show_name": False}).json()
    assert b == {"name": "Bright Smile", "closing": "Book a check-up today", "color": "#2E6F8E", "show_name": False,
                 "card": "qr", "qr_url": "https://brightsmile.example/book"}
    # an old-style save (name / closing / colour only) keeps the new keys
    b = cl.put("/api/interactive/hub/brand", json={"name": "Bright Smile Dental", "color": "#2E6F8E", "closing": "Book today"}).json()
    assert b["card"] == "qr" and b["qr_url"].endswith("/book") and b["show_name"] is False
    # the closing card picture: a QR on a white tile, the same picture the video gets
    r = cl.get("/api/interactive/hub/brand/card")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    from PIL import Image
    im = Image.open(io.BytesIO(r.content))
    assert im.size[0] > 300 and im.getpixel((14, im.size[1] // 2))[:3] == (255, 255, 255)
    assert cl.get("/api/interactive/hub/brand/card?card=none").status_code == 204
    assert cl.get("/api/interactive/hub/brand/card?card=logo").status_code == 204                      # no logo yet
    # into the video: the corner name follows show_name, the closing card carries the picture
    p = S.draft("default", "Clinic hours")
    spec, files = S.spec_for("default", {**S._load("default")["projects"][0], "brand": "Bright Smile Dental", "closing": "Book today"}, True)
    assert spec["brand"]["name"] == "" and spec["brand"]["color"] == "#2E6F8E"
    assert spec["cta"] == {"text": "Book today", "image": "assets/cta.png"} and files[-1]["name"] == "assets/cta.png"
    assert Path(files[-1]["path"]).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    cl.put("/api/interactive/hub/brand", json={"name": "Bright Smile Dental", "color": "#2E6F8E", "show_name": True, "card": "none"})
    spec, files = S.spec_for("default", {**S._load("default")["projects"][0], "brand": "Bright Smile Dental", "closing": "Book today"}, True)
    assert spec["brand"]["name"] == "Bright Smile Dental" and spec["cta"] == {"text": "Book today"} and not any(f["name"] == "assets/cta.png" for f in files)
    assert p["id"]


def test_logo_kit_and_words(ix):
    from app.brand import service as BS
    cl = _client()
    assert cl.get("/api/interactive/hub/brand/logo").status_code == 404
    BS.save_kit("default", name="Bright Smile Dental", tagline="Smile every day", colors={"primary": "#2E6F8E"},
                contact={"website": "brightsmile.example"})
    BS.set_logo("default", data=_png())
    info = cl.get("/api/interactive/hub/brand").json()
    k = info["kit"]
    assert k["name"] == "Bright Smile Dental" and k["color"] == "#2E6F8E" and k["logo"] is True and k["website"] == "https://brightsmile.example"
    assert info["logo"]["on"] and info["logo"]["px"] == [400, 300]
    assert cl.get("/api/interactive/hub/brand/logo").headers["content-type"] in ("image/png", "image/jpeg")
    # only the ticked parts come in
    assert cl.post("/api/interactive/hub/brand/kit", json={"fields": []}).status_code == 422
    r = cl.post("/api/interactive/hub/brand/kit", json={"fields": ["name", "logo", "qr"]}).json()
    assert r["brand"]["name"] == "Bright Smile Dental" and r["brand"]["card"] == "both" and r["brand"]["qr_url"] == "https://brightsmile.example"
    assert r["brand"]["closing"] == "" and r["brand"]["color"] == ""                                      # not ticked, not changed
    both = cl.get("/api/interactive/hub/brand/card").content
    from PIL import Image
    assert Image.open(io.BytesIO(both)).size[0] > Image.open(io.BytesIO(cl.get("/api/interactive/hub/brand/card?card=qr").content)).size[0]
    # removing the logo takes it out of the kit too, and the card falls back to the QR
    r = cl.delete("/api/interactive/hub/brand/logo").json()
    assert r["logo"]["on"] is False and r["brand"]["card"] == "qr" and BS.kit("default")["logo"] is False
    # words to keep: kept as written, or always one word in a language
    g = cl.post("/api/interactive/hub/glossary", json={"term": "Bright Smile Dental"}).json()
    assert g[0]["mode"] == "keep"
    assert cl.post("/api/interactive/hub/glossary", json={"term": "check-up", "mode": "as", "to": "revisión"}).status_code == 422
    g = cl.post("/api/interactive/hub/glossary", json={"term": "check-up", "mode": "as", "to": "revisión", "lang": "es"}).json()
    assert g[0] == {**g[0], "term": "check-up", "mode": "as", "to": "revisión", "lang": "es"}
    assert cl.get("/api/interactive/hub/brand").json()["glossary_count"] == 2


def test_the_page_code_is_wired():
    root = ROOT / "app" / "static" / "console"
    js = (root / "interactive.js").read_text("utf-8")
    css = (root / "interactive2.css").read_text("utf-8")
    assert subprocess.run(["node", "--check", str(root / "interactive.js")], capture_output=True).returncode == 0
    blk = js[js.index("brand (v0.999.205"):js.index("// ---- projects (v0.999.")]
    drawn = set(re.findall(r'data-a="([a-z]+)"', blk))
    cases = set(re.findall(r"case '([a-z]+)':", js))
    assert drawn <= cases, drawn - cases
    assert "brandsave" not in js and 'id="hxBrandF"' not in js                       # the old form is gone
    for r in ("/brand/card", "/brand/logo", "/brand/kit", "/glossary"):
        assert r in js, r
    for c in (".hx-brgrid", ".hx-brtog", ".hx-brsw", ".hx-brcon", ".hx-brfr", ".hx-brcta", ".hx-brgr", ".hx-brkr"):
        assert f"#hxRoot {c}" in css, c


def _until(ok, wait=8.0):
    import time
    end = time.time() + wait
    while time.time() < end:
        if ok():
            return
        time.sleep(0.15)
    assert ok()


def test_brand_in_a_real_browser(ix_server):
    from app.brand import service as BS
    base, browser, key = ix_server
    shots = os.environ.get("HOOLA_SHOTS")
    errors: list[str] = []
    BS.save_kit("default", name="Bright Smile Dental", colors={"primary": "#2E6F8E"}, contact={"website": "brightsmile.example"})
    BS.set_logo("default", data=_png())
    for vp in ({"width": 1440, "height": 900}, {"width": 390, "height": 844}):
        ctx = browser.new_context(viewport=vp)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/?v=interactive")
        pg.wait_for_selector("#hxRoot .hx-side [data-p=brand]", state="attached", timeout=25000)
        if vp["width"] < 900:
            pg.click("#hxRoot .hx-menu")
        pg.click("#hxRoot .hx-side [data-p=brand]")
        pg.wait_for_selector("#hxRoot .hx-brpage #hxBrName", timeout=15000)
        if vp["width"] > 900:
            assert pg.is_disabled("[data-a=brsave]")
            pg.fill("#hxBrName", "Smile Clinic")
            _until(lambda: "Smile Clinic" in pg.inner_text(".hx-brpn"))                        # the preview follows her typing
            assert not pg.is_disabled("[data-a=brsave]")
            pg.click(".hx-brsw[data-val='#F2B544']") if pg.locator(".hx-brsw[data-val='#F2B544']").count() else None
            pg.fill("#hxBrHex", "#FFE9A8")
            _until(lambda: "hard to read" in pg.inner_text("#hxBrCon"))
            pg.fill("#hxBrHex", "#2E6F8E")
            _until(lambda: "read well" in pg.inner_text("#hxBrCon"))
            pg.click("[data-a=brshow]")
            assert pg.locator(".hx-brpn").count() == 0
            pg.click("[data-a=brcard][data-val=both]")
            pg.fill("#hxBrQr", "https://smile.example/book")
            pg.fill("#hxBrClose", "Book a visit today")
            _until(lambda: pg.locator("#hxBrCard:not([hidden])").count() == 1, 10)               # the real closing card picture
            pg.click("[data-a=brshape][data-val=tall]")
            assert pg.locator(".hx-brfr.tall").count() == 2
            if shots:
                pg.screenshot(path=f"{shots}/ix205-brand-1440.png", full_page=True)
            pg.click("[data-a=brsave]")
            _until(lambda: (S._load("default").get("brand") or {}).get("qr_url") == "https://smile.example/book")
            b = S._load("default")["brand"]
            assert b["name"] == "Smile Clinic" and b["card"] == "both" and b["show_name"] is False and b["color"] == "#2E6F8E"
            # words to keep, with a language
            pg.select_option("#hxGloMode", "as")
            pg.fill("#hxGlo", "check-up")
            pg.fill("#hxGloTo", "revisión")
            pg.select_option("#hxGloLang", "es")
            pg.click("[data-a=gloadd]")
            _until(lambda: "in Spanish" in pg.inner_text(".hx-brgl"))
            # Use my Brand kit brings only what is ticked
            pg.click("[data-a=brkit]")
            pg.wait_for_selector(".hx-brkit", timeout=5000)
            if shots:
                pg.wait_for_timeout(700)
                pg.screenshot(path=f"{shots}/ix205-brand-kit.png")
            for f in ("color", "logo", "qr"):
                if pg.is_checked(f"[data-brkit={f}]"):
                    pg.uncheck(f"[data-brkit={f}]")
            pg.check("[data-brkit=name]")
            pg.click("[data-a=brkitgo]")
            _until(lambda: S._load("default")["brand"]["name"] == "Bright Smile Dental")
            assert S._load("default")["brand"]["qr_url"] == "https://smile.example/book"
        else:
            assert pg.evaluate("document.documentElement.scrollWidth") <= 392
            if shots:
                pg.wait_for_timeout(900)
                pg.screenshot(path=f"{shots}/ix205-brand-390.png", full_page=True)
                pg.locator(".hx-brgadd").scroll_into_view_if_needed()
                pg.wait_for_timeout(300)
                pg.screenshot(path=f"{shots}/ix205-brand-390-end.png")
        ctx.close()
    assert not errors, errors
