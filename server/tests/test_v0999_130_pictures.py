"""v0.999.130 D7 PICTURES (docs/WEB_DESIGN_ENGINE_PLAN.md phase D7, the part left open: "pictures not yet"): on a
website written in React she clicks a picture and puts one of HER website's photos there (one she has, or a new upload),
takes the photo away (the design's own picture shows), or writes what it shows - by code only, Rs 0. Her picture is
kept as data with her words and survives every later write. Only her own photos ever go into a page."""
from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.appengine import edits as ED
from tests.test_v0814_app_engine import ae_env  # noqa: F401  (fixture)
from tests.test_v0999_76_edit import _on, _page, _sec_code, rx_site  # noqa: F401  (fixtures)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[2]


def _jpeg(colour=(200, 80, 40)) -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (900, 600), colour).save(b, "JPEG")
    return b.getvalue()


def _hero(RX, sid):
    return next(s for s in RX.sections(T, sid)["sections"] if s["block"] == "hero" and not s["left_out"])


# ---------------------------------------------------------------- 1. the writer: only her photo, only where a picture is
def test_pictures_are_found_and_only_her_photos_go_in():
    from app.appengine import writer as W
    p = {"title": "Our work", "photo": {"src": "", "alt": "The shop", "label": "Shop"},
         "items": [{"title": "Bread", "photo": ""}], "photos": [{"src": "./photos/a.webp", "alt": "Oven"}],
         "image": "", "imageAlt": "Kitchen", "logo": "./logo.png", "href": "/contact"}
    found = {".".join(map(str, x["path"])): x for x in W.pictures_of(p)}
    assert set(found) == {"photo", "items.0.photo", "photos.0", "image"}                  # never the logo or a link
    assert found["photo"]["alt_ok"] and not found["items.0.photo"]["alt_ok"] and found["image"]["alt_ok"]
    assert W.set_picture(p, ["items", 0, "photo"], "./photos/bread-1.webp") and p["items"][0]["photo"] == "./photos/bread-1.webp"
    assert W.set_picture(p, ["photos", 0], "", "An empty oven") and p["photos"][0] == {"src": "", "alt": "An empty oven"}
    assert W.set_picture(p, ["image"], None, "Our kitchen") and p["imageAlt"] == "Our kitchen"
    for bad in ("https://elsewhere.example/x.jpg", "../../etc/passwd", "./photos/a.png", "javascript:alert(1)"):
        assert not W.set_picture(p, ["photo"], bad), bad                                  # never an outside picture
    assert not W.set_picture(p, ["href"], "./photos/a.webp")                              # never a place with no picture
    assert not W.set_picture(p, ["title"], "./photos/a.webp")
    assert not W.set_picture(p, ["nothing", "here"], "./photos/a.webp")


# ---------------------------------------------------------------- 2. her photo, by clicking the picture
def test_her_photo_goes_in_free_and_survives_every_write(rx_site):
    from app.site import rxedit as RX
    from app.site import service as S
    sid, ref = rx_site
    hero = _hero(RX, sid)
    assert hero["pictures"] and hero["pictures"][0]["path"] == ["photo"] and hero["pictures"][0]["src"] == ""
    with pytest.raises(RX.EditError):                                                     # not one of her photos yet
        RX.picture(T, sid, hero["sec"], ["photo"], "shop-front")
    name = S.add_photo(T, sid, _jpeg(), "", "Our clinic front", "")["name"]
    got = RX.sections(T, sid)
    assert any(p["name"] == name and p["src"] == f"./photos/{name}.webp" for p in got["photos"])
    res = RX.picture(T, sid, hero["sec"], ["photo"], name, "The front of our clinic")
    assert res["calls"] == 0 and res["inr"] == 0.0                                        # Rs 0: no model call
    code = _sec_code(_page(ref), hero["sec"])
    assert f"./photos/{name}.webp" in code and "The front of our clinic" in code
    e = ED.edits(T, ref)
    assert e["pictures"][hero["sec"]][0]["path"] == ["photo"] and e["pictures"][hero["sec"]][0]["src"] == f"./photos/{name}.webp"
    assert _hero(RX, sid)["hers"]
    RX.refresh(T, sid)                                                                    # a later write keeps her picture
    assert f"./photos/{name}.webp" in _sec_code(_page(ref), hero["sec"])
    assert RX.picture(T, sid, hero["sec"], ["photo"], name)["say"] == "Nothing changed."
    # take it away: the design's own picture shows; Undo brings it back
    RX.picture(T, sid, hero["sec"], ["photo"], "")
    assert f"./photos/{name}.webp" not in _sec_code(_page(ref), hero["sec"])
    RX.undo(T, sid)
    assert f"./photos/{name}.webp" in _sec_code(_page(ref), hero["sec"])
    RX.undo(T, sid)
    assert not ED.edits(T, ref)["pictures"]                  # back to the writer's own choice (her photos in her order)


def test_the_wrong_picture_is_refused(rx_site):
    from app.site import rxedit as RX
    from app.site import service as S
    sid, ref = rx_site
    hero = _hero(RX, sid)
    name = S.add_photo(T, sid, _jpeg(), "", "Waiting room", "")["name"]
    with pytest.raises(RX.EditError):
        RX.picture(T, sid, hero["sec"], ["headline"], name)                               # not a picture's place
    with pytest.raises(RX.EditError):
        RX.picture(T, sid, "home:99", ["photo"], name)                                     # not a section on the page
    with pytest.raises(RX.EditError):
        RX.picture(T, sid, hero["sec"], ["photo"], "../../../etc/passwd")
    with pytest.raises(RX.EditError):
        RX.picture(T, sid, hero["sec"], ["photo"])                                         # nothing asked
    with pytest.raises(RX.EditError):
        RX.picture(T, sid, hero["sec"], ["photo"], None, "x" * 201)                        # a description, not an essay
    with pytest.raises(RX.EditError):
        RX.picture("someone_else", sid, hero["sec"], ["photo"], name)                      # only her own site
    assert not ED.edits(T, ref).get("pictures")


def test_a_new_upload_goes_straight_into_its_place(rx_site):
    from app.site import rxedit as RX
    from app.site import service as S
    sid, ref = rx_site
    sec = next(s for s in RX.sections(T, sid)["sections"] if len(s["pictures"]) > 1 and not s["left_out"])
    slot = sec["pictures"][1]
    out = RX.upload_picture(T, sid, sec["sec"], slot["path"], _jpeg((20, 120, 90)), "Doctor at work")
    assert out["photo"] and out["calls"] == 0
    assert out["photo"] in [p["name"] for p in json.loads(S._load(sid).photos)]           # kept with her photos
    from app.appengine import writer as W
    assert f"./photos/{out['photo']}.webp" in _sec_code(_page(ref, W._slug_comp(sec["page"]) + ".tsx"), sec["sec"])
    with pytest.raises(RX.EditError):
        RX.upload_picture(T, sid, sec["sec"], slot["path"], b"not a picture at all", "")  # the same photo check


# ---------------------------------------------------------------- 3. the chat: the same exact edit, never a rewrite
def test_the_chat_changes_a_picture_exactly(rx_site):
    from app.agent import site_tools as ST
    from app.site import rxedit as RX
    from app.site import service as S
    sid, ref = rx_site
    name = S.add_photo(T, sid, _jpeg(), "", "Reception", "")["name"]
    block = RX.chat_block(T, sid)
    assert "[pictures: photo=none" in block and f"Her website's photos: {name}" in block and "picture" in block
    props = next(t for t in ST.SITE_TOOLS if t["name"] == "website")["input_schema"]["properties"]
    assert {"picture", "photo_name", "alt"} <= set(props)
    hero = _hero(RX, sid)
    ctx = SimpleNamespace(tenant_id=T, conversation_id="", actor="owner")
    out = ST._act(ctx, "rx_edit", {"site": sid, "sec": hero["sec"], "picture": "photo", "photo_name": name})
    assert out["calls"] == 0 and f"./photos/{name}.webp" in _sec_code(_page(ref), hero["sec"])
    out = ST._act(ctx, "rx_edit", {"site": sid, "sec": hero["sec"], "picture": "photo", "alt": "Our reception desk"})
    assert "Our reception desk" in _sec_code(_page(ref), hero["sec"])


# ---------------------------------------------------------------- 4. the preview: a click on a picture names it
def test_clicking_a_picture_in_the_preview_names_it(tmp_path):
    """preview.js in a real Chromium: in site mode a click on her photo or on the design's stand-in sends the section,
    the picture's address / description and its place among the section's pictures."""
    import http.server
    import socketserver
    import threading
    (tmp_path / "preview.js").write_text((ROOT / "server/app/appengine/preview.js").read_text())
    (tmp_path / "a.png").write_bytes(__import__("base64").b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="))
    (tmp_path / "page.html").write_text("""<!doctype html><html><head><script src="preview.js"></script></head><body>
      <main><div data-sec="home:0" class="contents" style="display:contents"><section data-block="hero" data-variant="split">
      <h1>Fresh bread</h1><img id="p" src="./photos/oven.webp" alt="Our oven" style="width:200px;height:100px;display:block">
      <div id="s" role="img" aria-label="The shop" style="width:200px;height:100px"><span>The shop</span></div></section></div></main></body></html>""")
    (tmp_path / "top.html").write_text("""<!doctype html><html><body><iframe id="f" src="page.html" style="width:800px;height:500px"></iframe>
      <script>window.got=[];addEventListener('message',e=>{if(e.data&&e.data.hoola==='ae')window.got.push(e.data)});</script></body></html>""")

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(tmp_path), **k)

        def log_message(self, *a):
            pass
    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        from playwright.sync_api import sync_playwright
        from app.appengine import speed as SP
        with sync_playwright() as pw:
            b = SP._browser(pw)
            pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/top.html")
            pg.wait_for_function("window.got.some(m => m.t === 'ready')")
            fr = pg.frame_locator("#f")
            pg.evaluate("document.getElementById('f').contentWindow.postMessage({hoola:'ae-cmd',t:'mode',mode:'site'},'*')")
            pg.wait_for_timeout(150)
            fr.locator("#p").click()
            pg.wait_for_function("window.got.filter(m => m.t === 'sec-pick').length === 1")
            fr.locator("#s span").click()                                                   # her click on the stand-in's label
            pg.wait_for_function("window.got.filter(m => m.t === 'sec-pick').length === 2")
            a, s = [m for m in pg.evaluate("window.got") if m["t"] == "sec-pick"]
            assert a["sec"] == "home:0" and a["tag"] == "img" and a["pic"] == {"src": "./photos/oven.webp", "alt": "Our oven", "n": 0}
            assert s["pic"] == {"src": "", "alt": "The shop", "n": 1} and s["text"] == ""
            fr.locator("h1").click()                                                        # words stay words
            pg.wait_for_function("window.got.filter(m => m.t === 'sec-pick').length === 3")
            w = [m for m in pg.evaluate("window.got") if m["t"] == "sec-pick"][2]
            assert "pic" not in w and w["text"] == "Fresh bread"
            b.close()
    finally:
        srv.shutdown()


def test_the_studio_has_the_picture_panel_and_routes():
    js = (ROOT / "server/app/static/console/webstudio.js").read_text()
    for x in ("rxPicPanel", "rxSlot", 'data-act="rx-pic-use"', 'data-act="rx-pic-none"', 'data-form="rx-pic-up"',
              'data-form="rx-pic-alt"', 'data-act="rx-pics"', "rxDo('picture'", "/rx/picture/upload", "pic: d.pic"):
        assert x in js, x
    main = (ROOT / "server/app/main.py").read_text()
    assert "/api/sites/{ref}/rx/picture\"" in main and "/api/sites/{ref}/rx/picture/upload" in main
    assert ".rxphotos" in (ROOT / "server/app/static/console/webstudio.css").read_text()
    plan = (ROOT / "docs/WEB_DESIGN_ENGINE_PLAN.md").read_text()
    assert "pictures not yet" not in plan and "pictures BUILT v0.999.130" in plan
