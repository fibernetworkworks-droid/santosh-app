"""v0.567 KOI BHI DESIGN (web Step 7 part 3 = W9): her website starts from HER design - a screenshot (colours measured,
design read), her Figma file (her token, sealed), or her OWN old website (ownership proven first) -> a preview -> her tap
-> look 1 is hers in Hoola's kit; plus rich pieces (quiz, configurator, comparison, scroll-driven motion)."""
import io
import json
import os
from pathlib import Path

import httpx
import pytest

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.648.0"


def _png(blocks, size=(400, 300)):
    """A picture made of known colour bands: [(hex, share)]."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", size, "#FFFFFF")
    dr = ImageDraw.Draw(im)
    y = 0
    for hx, share in blocks:
        h = int(size[1] * share)
        dr.rectangle([0, y, size[0], y + h], fill=hx)
        y += h
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _near(a, b, tol=6):
    return all(abs(int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) <= tol for i in (1, 3, 5))


def _near_any(a, opts):
    return any(_near(a, o) for o in opts)


def test_colours_are_measured_and_given_roles():
    from app.site import inspire as IN
    pic = _png([("#FAF7F2", 0.62), ("#1B1B1F", 0.18), ("#E8590C", 0.12), ("#1C7ED6", 0.08)])
    cols = IN.image_colours(pic)
    assert _near(cols[0][0], "#FAF7F2") and cols[0][1] > 0.5                        # median-cut: within a step or two
    roles = IN.roles_from(cols)
    assert _near(roles["bg"], "#FAF7F2") and _near(roles["ink"], "#1B1B1F") and not roles["dark"]
    assert _near_any(roles["primary"], ("#E8590C", "#1C7ED6")) and _near_any(roles["accent"], ("#E8590C", "#1C7ED6"))
    assert not _near(roles["primary"], roles["accent"])
    dark = IN.roles_from(IN.image_colours(_png([("#0E0F14", 0.7), ("#F2F2F2", 0.2), ("#9B5CFF", 0.1)])))
    assert dark["dark"] and _near(dark["ink"], "#F2F2F2") and _near(dark["primary"], "#9B5CFF")


def test_type_maps_to_a_pair_hoola_ships():
    from app.site import inspire as IN
    from app.site import taxonomy as T_
    assert IN.font_kind("Playfair Display") == "serif" and IN.font_kind("Nunito") == "rounded"
    assert IN.font_kind("Bebas Neue") == "display" and IN.font_kind("Helvetica Neue") == "sans"
    assert IN.font_pair("serif", "Fraunces") == "fraunces_inter"                  # Hoola has her exact family
    assert IN.font_pair("serif", "Garamond") in IN.HEAD_KIND["serif"]
    for k in IN.HEAD_KIND.values():
        assert all(x in T_.FONTS for x in k)
    assert IN.pick_style("serif", True, 4, False) == "luxury_dark" and IN.pick_style("sans", False, 0, False) == "minimal_swiss"
    assert IN.pick_style("sans", False, 8, False, "warm_local") == "warm_local"


def test_a_screenshot_gives_a_style_never_its_words(site_env, monkeypatch):
    from app.site import ai as AI
    from app.site import inspire as IN
    seen = {}

    def vision(system, prompt, max_tokens=6000, kind="build", images=None, effort=""):
        seen["images"] = images
        assert "NEVER copy any text" in system
        return {"style": "bold_modern", "head_kind": "display", "radius_px": 18, "primary": "#E8590C",
                "sections": ["hero", "Our Services", "reviews", "nonsense"], "notes": "Big type, bold blocks",
                "name": "Rival Sweets", "phone": "9999999999"}
    monkeypatch.setattr(AI, "ask_json", vision)
    pic = _png([("#FAF7F2", 0.6), ("#1B1B1F", 0.2), ("#E8590C", 0.2)])
    ref = IN.from_screenshot(T, data=pic)
    assert len(seen["images"]) == 1 and seen["images"][0][:2] == b"\xff\xd8"      # sent as a JPEG copy
    assert ref["style"] == "bold_modern" and ref["head_kind"] == "display" and ref["radius"] == 18
    assert _near(ref["overrides"]["bg"], "#FAF7F2") and ref["overrides"]["fonts"] in IN.HEAD_KIND["display"]
    assert ref["sections"] == ["hero", "services_grid", "reviews"]
    flat = json.dumps(ref)
    assert "Rival" not in flat and "9999999999" not in flat                          # nothing read off the picture is kept
    # no model: the measured colours still make a usable reference
    monkeypatch.setattr(AI, "ask_json", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    ref2 = IN.from_screenshot(T, data=pic)
    assert _near(ref2["overrides"]["bg"], "#FAF7F2") and "not available" in ref2["read_by"]
    with pytest.raises(IN.InspireError):
        IN.from_screenshot(T, data=b"not an image")


def _figma_doc():
    def solid(hx):
        return [{"type": "SOLID", "color": {"r": int(hx[1:3], 16) / 255, "g": int(hx[3:5], 16) / 255, "b": int(hx[5:7], 16) / 255}}]
    box = {"width": 1440, "height": 900}
    return {"name": "Sharma Sweets site", "document": {"children": [{"type": "CANVAS", "children": [
        {"type": "FRAME", "name": "Home", "fills": solid("#FFF8EE"), "absoluteBoundingBox": {"width": 1440, "height": 4000},
         "children": [
             {"type": "FRAME", "name": "Hero", "cornerRadius": 12, "fills": solid("#B4231A"), "absoluteBoundingBox": box, "children": [
                 {"type": "TEXT", "characters": "Since 1962, Akola's sweet shop", "style": {"fontFamily": "Playfair Display", "fontSize": 64}}]},
             {"type": "FRAME", "name": "Our Services", "cornerRadius": 12, "fills": solid("#FFF8EE"), "children": [
                 {"type": "TEXT", "characters": "Kaju katli, peda, ladoo", "style": {"fontFamily": "Inter", "fontSize": 18}}]},
             {"type": "FRAME", "name": "Testimonials", "cornerRadius": 12, "children": []},
             {"type": "FRAME", "name": "Contact us", "fills": solid("#2B2118"), "absoluteBoundingBox": {"width": 1440, "height": 300}}]}]}]}}


def test_her_figma_file_with_her_sealed_token(site_env, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a-very-long-random-secret-for-tests-0123456789")
    from app.config import get_settings
    get_settings.cache_clear() if hasattr(get_settings, "cache_clear") else None
    from app.db import session
    from app.site import inspire as IN
    with pytest.raises(IN.InspireError) as e:
        IN.from_figma(T, "https://www.figma.com/design/AbCdEfGhIjKlMn/Site")
    assert e.value.code == 409                                                       # no token yet: never asked in chat
    with pytest.raises(IN.InspireError):
        IN.set_figma_token(T, "short")
    tok = "figd_" + "x" * 40
    assert IN.set_figma_token(T, tok)["hint"] == "...xxxx"
    with session() as s:
        row = s.get(IN.SiteFigmaKey, T)
        assert row.token_enc and tok not in row.token_enc                             # sealed, never stored plain
    assert IN.figma_status(T) == {"linked": True, "hint": "...xxxx"}
    calls = []

    def handler(req):
        calls.append(req)
        if req.headers.get("X-Figma-Token") != tok:
            return httpx.Response(403)
        return httpx.Response(200, json=_figma_doc())
    IN.set_transport(httpx.MockTransport(handler))
    try:
        ref = IN.from_figma(T, "https://www.figma.com/design/AbCdEfGhIjKlMn/Site?node-id=1")
        assert calls[0].url.path == "/v1/files/AbCdEfGhIjKlMn"
        assert ref["source"] == "figma" and ref["head_kind"] == "serif" and ref["fonts"] == "playfair_lato"
        assert ref["radius"] == 12 and ref["overrides"]["bg"] == "#FFF8EE" and ref["overrides"]["primary"] == "#B4231A"
        assert ref["sections"][:4] == ["hero", "services_grid", "reviews", "contact_block"]
        assert "Kaju katli, peda, ladoo" in ref["content"]["texts"]                  # HER words from HER file may be used
        IN.forget_figma(T)
        assert IN.figma_status(T)["linked"] is False
    finally:
        IN.set_transport(None)
    with pytest.raises(IN.InspireError):
        IN.figma_key("https://example.com/not-figma")


def _old_site(meta_token=""):
    from PIL import Image
    big = io.BytesIO()
    Image.new("RGB", (800, 600), "#B4231A").save(big, "JPEG")
    tiny = io.BytesIO()
    Image.new("RGB", (40, 40), "#000000").save(tiny, "PNG")
    meta = f'<meta name="hoola-own" content="{meta_token}">' if meta_token else ""
    pages = {
        "/": f"""<html><head><title>Sharma Sweets | Akola</title>{meta}<link rel="stylesheet" href="/s.css">
            <style>.x{{color:#2B2118}}</style></head><body><nav><a href="/about">About</a><a href="/sweets">Sweets</a>
            <a href="/private/admin">Admin</a><a href="https://other.example/x">Out</a></nav>
            <h1>Fresh mithai since 1962</h1><p>Sharma Sweets makes kaju katli, peda and ladoo every morning in Akola with pure ghee.</p>
            <a href="tel:+91 98765 43210">Call</a><a href="mailto:hello@sharmasweets.in">Mail</a>
            <img src="/img/shop.jpg" alt="Our shop front"><img src="/img/icon-cart.png" alt=""><img src="https://cdn.other.example/x.jpg">
            <footer>Main Road, Akola, Maharashtra 444001</footer></body></html>""",
        "/about": "<html><head><title>About</title></head><body><h2>Our story</h2><p>Three generations of Sharma family halwais have served Akola since 1962.</p></body></html>",
        "/sweets": "<html><head><title>Sweets</title></head><body><h2>Kaju Katli</h2><h2>Malai Peda</h2><ul><li>Kaju katli 1 kg</li></ul></body></html>",
        "/private/admin": "<html><body>SECRET</body></html>",
    }
    css = "body{font-family:'Playfair Display',serif;background:#FFF8EE;color:#2B2118}.btn{background:#B4231A;border-radius:6px}"
    fetched = []

    def handler(req):
        p = req.url.path
        fetched.append(p)
        if p == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
        if p == "/s.css":
            return httpx.Response(200, text=css, headers={"content-type": "text/css"})
        if p == "/img/shop.jpg":
            return httpx.Response(200, content=big.getvalue(), headers={"content-type": "image/jpeg"})
        if p == "/img/icon-cart.png":
            return httpx.Response(200, content=tiny.getvalue(), headers={"content-type": "image/png"})
        if p in pages:
            return httpx.Response(200, text=pages[p], headers={"content-type": "text/html; charset=utf-8"})
        return httpx.Response(404)
    return handler, fetched


@pytest.fixture
def public_dns(monkeypatch):
    import socket
    from app.appmaker import connect as CN
    monkeypatch.setattr(CN, "_RESOLVE", lambda host, port: [(socket.AF_INET, 0, 0, "", ("93.184.216.34", port))])
    from app.site import dns as D
    monkeypatch.setattr(D, "lookup", lambda name, type_="A": {})
    yield


def test_her_old_site_only_after_she_proves_it_is_hers(site_env, public_dns, monkeypatch):
    from app.site import inspire as IN
    handler, fetched = _old_site()
    IN.set_transport(httpx.MockTransport(handler))
    try:
        with pytest.raises(IN.InspireError) as e:
            IN.from_site(T, "https://sharmasweets.in")
        assert e.value.code == 403
        pr = e.value.extra["proof"]
        assert pr["txt_name"] == "_hoola-own.sharmasweets.in" and pr["txt_value"].startswith("hoola-own-")
        assert fetched == ["/"]                                                       # nothing else read before the proof
        assert IN.own_token(T, "www.sharmasweets.in") == IN.own_token(T, "sharmasweets.in") != IN.own_token("other", "sharmasweets.in")
        handler, fetched = _old_site(IN.own_token(T, "sharmasweets.in"))
        IN.set_transport(httpx.MockTransport(handler))
        ref = IN.from_site(T, "sharmasweets.in")
        assert "/private/admin" not in fetched                                        # robots.txt respected
        assert not any("other.example" in f for f in fetched)
        c = ref["content"]
        assert c["name"] == "Sharma Sweets" and c["phone"] == "9876543210" and c["email"] == "hello@sharmasweets.in"
        assert "444001" in c["address"] and "Three generations" in c["about"] and "Kaju Katli" in c["services"]
        photos = ref["_photos"]
        assert len(photos) == 1 and photos[0]["about"] == "Our shop front"           # icon + tiny + other site's photo left out
        assert ref["head_kind"] == "serif" and ref["radius"] == 6
        assert ref["overrides"]["bg"] in ("#FFF8EE", "#2B2118") and ref["overrides"].get("primary") == "#B4231A"
        # a TXT record proves it too
        handler, fetched = _old_site()
        IN.set_transport(httpx.MockTransport(handler))
        from app.site import dns as D
        monkeypatch.setattr(D, "lookup", lambda name, type_="A": {"1.1.1.1": [IN.own_token(T, "sharmasweets.in")]}
                            if name == "_hoola-own.sharmasweets.in" and type_ == "TXT" else {})
        assert IN.from_site(T, "https://www.sharmasweets.in")["content"]["name"] == "Sharma Sweets"
    finally:
        IN.set_transport(None)


def test_preview_then_her_tap_makes_look_one_hers(site_env, public_dns, monkeypatch):
    from app.site import inspire as IN
    from app.site import service as S
    v = S.new(T, "Sharma Sweets mithai dukaan ki website", name="Sharma Sweets", answers={"phone": "9876543210"})
    S.approve_plan(T, v["id"])
    before = S._load(v["id"])
    assert len(json.loads(before.looks)) == 3 and not any(x.get("mine") for x in json.loads(before.looks))
    from app.site import ai as AI
    real = AI.ask_json
    monkeypatch.setattr(AI, "ask_json", lambda system, prompt, *a, **k: (
        {"style": "luxury_dark", "head_kind": "serif", "radius_px": 2, "primary": "#C9A227", "sections": ["hero", "reviews"],
         "notes": "Gold on black"} if "VISUAL SYSTEM" in system else real(system, prompt, *a, **k)))
    pv = IN.read(T, "screenshot", data=_png([("#0B0B0E", 0.7), ("#F4EFE6", 0.2), ("#C9A227", 0.1)]))
    assert pv["token"] and "Pehla look isi design se" in pv["say"]
    assert S._load(v["id"]).looks == before.looks                                    # a preview changes nothing
    out = IN.use(T, pv["token"], v["id"])
    assert out["remade_looks"]
    r = S._load(v["id"])
    looks = json.loads(r.looks)
    assert looks[0]["mine"] and looks[0]["label"] == "Aapke design se" and looks[0]["style"] == "luxury_dark"
    tk = looks[0]["tokens"]
    assert _near(tk["bg"], "#0B0B0E") and tk["radius"] == 2 and _near(tk["primary"], "#C9A227")
    assert tk["head"] in [__import__("app.site.taxonomy", fromlist=["T"]).FONTS[k]["head"] for k in IN.HEAD_KIND["serif"]]
    assert len(looks) == 3 and not looks[1].get("mine") and not looks[2].get("mine")    # two Hoola alternatives stay
    assert json.loads(r.facts)["design_ref"]["source"] == "screenshot"
    with pytest.raises(IN.InspireError):
        IN.use(T, "bad token!!", v["id"])


def test_a_new_site_from_her_old_site_keeps_her_words_and_photos(site_env, public_dns):
    from app.site import inspire as IN
    from app.site import service as S
    handler, _ = _old_site(IN.own_token(T, "sharmasweets.in"))
    IN.set_transport(httpx.MockTransport(handler))
    try:
        pv = IN.read(T, "site", "https://sharmasweets.in")
    finally:
        IN.set_transport(None)
    assert "Sharma Sweets" in pv["say"] and "1 photos" in pv["say"]
    out = IN.use(T, pv["token"])
    r = S._load(out["site"])
    f = json.loads(r.facts)
    assert out["photos_added"] == 1 and len(json.loads(r.photos)) == 1
    assert f["phone"] == "9876543210" and f["design_ref"]["source"] == "site" and r.name == "Sharma Sweets"


def test_routes_and_the_tool(site_env, public_dns):
    import asyncio
    from fastapi.testclient import TestClient
    from app.agent.site_tools import SITE_HANDLERS
    from app.main import app
    from app.site import inspire as IN
    from tests.test_life import conv_ctx
    c = TestClient(app)
    assert c.get("/api/site-design/figma").json()["linked"] is False
    assert c.put("/api/site-design/figma", json={"token": "nope"}).status_code == 400
    r = c.post("/api/site-design/read", files={"file": ("shot.png", _png([("#FFFFFF", 0.8), ("#E8590C", 0.2)]), "image/png")})
    assert r.status_code == 200 and r.json()["token"]
    handler, _ = _old_site()
    IN.set_transport(httpx.MockTransport(handler))
    try:
        r = c.post("/api/site-design/read", json={"source": "site", "url": "https://sharmasweets.in"})
        assert r.status_code == 403 and r.json()["proof"]["meta"].startswith('<meta name="hoola-own"') and r.json()["detail"]
        got = asyncio.run(SITE_HANDLERS["website"](conv_ctx(), "design_from", source="site", url="https://sharmasweets.in"))
        assert got["proof"]["txt_name"] == "_hoola-own.sharmasweets.in"
    finally:
        IN.set_transport(None)
    src = (Path(__file__).resolve().parents[1] / "app" / "agent" / "site_tools.py").read_text()
    assert '"design_use"}' in src                                               # her tap only (owner), like choosing a look


def test_rich_pieces_survive_the_cleaner_and_work_in_a_browser(site_env):
    from app.site import build as B
    html = """<section><form data-hoola-quiz><fieldset data-q><legend>Kitne log?</legend>
      <label><input type="radio" name="q1" data-result="small"> 1-2</label><label><input type="radio" name="q1" data-result="big"> 10+</label></fieldset>
      <fieldset data-q><legend>Kab?</legend><label><input type="radio" name="q2" data-result="big"> Shaadi</label>
      <label><input type="radio" name="q2" data-result="small"> Ghar</label></fieldset><p data-quiz-msg></p>
      <button type="submit">See</button><div data-result-panel="small">Half kg box</div><div data-result-panel="big">Party tray</div></form>
      <form data-hoola-config data-base="100"><fieldset><legend>Size</legend>
      <label><input type="radio" name="s" data-add="0" data-label="Half kg" checked> Half kg</label>
      <label><input type="radio" name="s" data-add="400" data-label="1 kg" data-show="big"> 1 kg</label></fieldset>
      <img data-config-show="big" alt="big box"><span data-config-summary></span><output data-calc-out></output>
      <textarea></textarea><button type="submit">Send</button></form>
      <div data-hoola-compare-table><button type="button" data-compare-diff aria-pressed="false">Diff</button>
      <table><tbody><tr><th>Ghee</th><td>Yes</td><td>Yes</td></tr><tr><th>Box</th><td>Plain</td><td>Gift</td></tr></tbody></table></div>
      <div data-m="scrub">x</div></section>"""
    out, _css, _js, problems = B.sanitize_section("s-home-quiz", {"html": html})
    assert not problems or problems == []
    for keep in ("data-hoola-quiz", "data-result-panel", "data-hoola-config", "data-config-show", "data-add", "data-hoola-compare-table",
                 "data-compare-diff", 'data-m="scrub"'):
        assert keep in out, keep
    from playwright.sync_api import sync_playwright
    from app.site import checks as C
    js = (B.ASSETS / "hoola-site.js").read_text()
    with sync_playwright() as p:
        br = C._launch(p)
        pg = br.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.set_content(f"<html><body>{out}<form data-hoola-form><textarea name='message'></textarea></form><script>{js}</script></body></html>")
        assert pg.eval_on_selector_all("[data-result-panel]", "els => els.every(e => e.hidden)")
        pg.click("form[data-hoola-quiz] button[type=submit]")
        assert "answer every question" in pg.inner_text("[data-quiz-msg]")
        pg.check("input[name=q1][data-result=big]")
        pg.check("input[name=q2][data-result=big]")
        pg.click("form[data-hoola-quiz] button[type=submit]")
        assert pg.is_visible("[data-result-panel=big]") and not pg.is_visible("[data-result-panel=small]")
        assert not pg.is_visible("[data-config-show=big]") and pg.inner_text("form[data-hoola-config] output") == "₹100"
        pg.check("input[name=s][data-add='400']")
        assert pg.is_visible("[data-config-show=big]") and pg.inner_text("form[data-hoola-config] output") == "₹500"
        assert pg.inner_text("[data-config-summary]") == "1 kg"
        pg.click("form[data-hoola-config] button[type=submit]")
        assert "1 kg" in pg.input_value("form[data-hoola-form] textarea")             # the choice goes to her enquiry form
        pg.click("[data-compare-diff]")
        assert not pg.is_visible("tr:has-text('Ghee')") and pg.is_visible("tr:has-text('Box')")
        assert not errors, errors
        br.close()
    css = (B.ASSETS / "hoola-site.css").read_text()
    assert "animation-timeline:view()" in css and "prefers-reduced-motion: no-preference" in css


def test_the_writer_is_told_about_the_new_pieces_and_tokens_take_her_fonts():
    from app.site import ai as AI
    from app.site import build as B
    g = AI.RUNTIME_GUIDE if hasattr(AI, "RUNTIME_GUIDE") else ""
    src = Path(AI.__file__).read_text()
    for w in ("data-hoola-quiz", "data-hoola-config", "data-hoola-compare-table", 'data-m="scrub"', "HER own products"):
        assert w in src, w
    tk = B.tokens("editorial_calm", "paper_ink", None, {"fonts": "playfair_lato", "radius": 14, "primary": "#B4231A"})
    assert tk["head"] == "Playfair Display" and tk["radius"] == 14 and tk["primary"] == "#B4231A"
    assert B.tokens("editorial_calm", "paper_ink", None, {"fonts": "not_a_pair"})["head"] == "DM Serif Display"   # v0.606 style default
    assert g is not None
