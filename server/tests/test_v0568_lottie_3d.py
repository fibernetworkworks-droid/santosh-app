"""v0.568 LOTTIE + 3D HERO on her website: lottie-web's LIGHT player (MIT, SVG, no eval) and a three.js r187 bundle (MIT)
served from the site itself and loaded only on pages that use them; built-in animations in the site's own colours, her own
Lottie files checked before they are kept, five house 3D scenes chosen by name, every library seen by the OSV gate."""
import http.server
import json
import socketserver
import threading
from pathlib import Path

import pytest

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

ASSETS = Path(__file__).resolve().parents[1] / "app" / "site" / "assets"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.858.0"


def test_the_vendored_libraries_are_what_they_say():
    lot = (ASSETS / "vendor" / "lottie_light.min.js").read_text()
    three = (ASSETS / "vendor" / "three-hero.js").read_text()
    assert lot.startswith("/*! lottie-web v5.13.0") and 'version="5.13.0"' in lot
    assert three.startswith("/*! Hoola 3D hero") and "three.js r187" in three[:200] and 'var Lr="187"' in three[:400]
    for js in (lot, three):
        assert "eval(" not in js and "new Function(" not in js          # the site CSP stays script-src 'self'
        assert "http://" not in js[:200]
    assert len(three) < 700_000 and len(lot) < 200_000
    assert (ASSETS / "vendor" / "three.LICENSE.txt").read_text().startswith("The MIT License")
    assert "MIT" in (ASSETS / "vendor" / "lottie-web.LICENSE.md").read_text()
    assert "three-hero.js" in (ASSETS / "vendor" / "REBUILD.md").read_text()
    notices = (Path(__file__).resolve().parents[2] / "THIRD_PARTY_NOTICES.md").read_text()
    assert "lottie-web 5.13.0" in notices and "three.js r187" in notices
    src = (ASSETS / "src" / "hero3d.src.js").read_text()
    for scene in ("orb(", "knot(", "particles(", "waves(", "blocks("):
        assert scene in src
    assert "prefers-reduced-motion" in src and "IntersectionObserver" in src and "data-hoola-3d-off" in src


def test_built_in_animations_are_real_lottie_in_two_placeholder_colours():
    from app.site import lottie as LT
    for nm in LT.BUILTINS:
        doc = LT.builtin(nm)
        assert all(k in doc for k in ("v", "w", "h", "fr", "ip", "op", "layers")) and doc["layers"]
        flat = json.dumps(doc)
        assert "[1, 0, 1, 1]" in flat                                       # the site's --c-primary goes here
        LT.check(json.dumps(doc).encode())                                  # passes her-file rules too
    with pytest.raises(LT.LottieError):
        LT.builtin("rocket")


def test_her_lottie_file_is_checked_before_it_is_kept(tmp_path):
    from app.site import lottie as LT
    good = LT.builtin("pulse")
    good["layers"][0]["ks"]["o"]["x"] = "var $bm_rt = time * 10;"          # an expression (code)
    doc, notes = LT.check(json.dumps(good).encode())
    assert "$bm_rt" not in json.dumps(doc) and "x" not in doc["layers"][0]["ks"]["o"]
    assert any("expressions hata" in n for n in notes)
    for bad, why in ((b"not json", "JSON"), (json.dumps({"v": "5"}).encode(), "zaroori"),
                     (json.dumps({**LT.builtin("dots"), "assets": [{"id": "i", "p": "https://x.example/a.png", "u": ""}]}).encode(), "server"),
                     (b"{" + b" " * 1_600_000 + b"}", "1.5 MB")):
        with pytest.raises(LT.LottieError) as e:
            LT.check(bad)
        assert why in str(e.value)
    ok = {**LT.builtin("dots"), "assets": [{"id": "i", "p": "data:image/png;base64,iVBORw0KGgo=", "u": "images/"}]}
    doc, _ = LT.check(json.dumps(ok).encode())
    assert doc["assets"][0]["u"] == "" and doc["assets"][0]["e"] == 1
    out = LT.store(tmp_path, "meri-dukaan", json.dumps(LT.builtin("wave")).encode())
    assert out["name"] == "meri-dukaan" and out["seconds"] == 2.0 and LT.hers(tmp_path) == ["meri-dukaan"]
    for name in ("check", "Bad Name", "x"):
        with pytest.raises(LT.LottieError):
            LT.store(tmp_path, name, json.dumps(LT.builtin("wave")).encode())
    html, used, prob = LT.expand('<div data-hoola-lottie="check"></div><div data-hoola-lottie="ghost"></div>', "../", {"check"})
    assert used == {"check"} and 'data-src="../assets/lottie/check.json"' in html
    assert "data-hoola-lottie-missing" in html and prob == ["animation 'ghost' nahi hai"]


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def _serve(root: Path):
    class S(socketserver.ThreadingTCPServer):
        allow_reuse_address, daemon_threads = True, True
    srv = S(("127.0.0.1", 0), lambda *a, **k: _Quiet(*a, directory=str(root), **k))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_a_built_page_with_animations_and_a_3d_hero_really_plays(site_env):
    from app.site import build as B
    from app.site import gates as G
    from app.site import lottie as LT
    from app.site import service as S
    from app.appmaker import gates as AG
    v = S.new(T, "Sharma Sweets mithai dukaan ki website", name="Sharma Sweets", answers={"phone": "9876543210"})
    S.approve_plan(T, v["id"])
    S.choose_look(T, v["id"], 0)
    r = S._load(v["id"])
    S.add_lottie(T, v["id"], json.dumps(LT.builtin("sparkle")).encode(), "", "meri-chamak")
    assert "HER ANIMATIONS (use with data-hoola-lottie): meri-chamak" in S._photos_line(S._load(v["id"]))
    k = next(k for k in S._sections(r) if k.startswith("home__hero"))
    f = S._sec_path(r, k)
    sec = json.loads(f.read_text())
    sec["html"] = sec["html"].replace("</section>", '<div class="hero3d" data-hoola-3d="orb" aria-hidden="true"></div>'
                                      '<div data-hoola-lottie="check" data-loop="false" aria-hidden="true"></div>'
                                      '<div data-hoola-lottie="meri-chamak" aria-hidden="true"></div>'
                                      '<div data-hoola-lottie="nope"></div></section>', 1)
    f.write_text(json.dumps(sec))
    out = S._assemble_live(S._load(v["id"]))
    home = (out / "index.html").read_text()
    lot_i, site_i = home.index("assets/vendor/lottie_light.min.js"), home.index("assets/hoola-site.js")
    assert lot_i < site_i                                                   # the player is there before the page code
    assert '<script type="module" src="assets/vendor/three-hero.js"></script>' in home
    assert 'data-src="assets/lottie/check.json"' in home and "data-hoola-lottie-missing" in home
    files = sorted(p.name for p in (out / "assets" / "lottie").iterdir() if p.suffix != ".gz")
    assert files == ["check.json", "meri-chamak.json"]                     # only the ones used
    assert (out / "assets" / "vendor" / "three-hero.js").exists() and (out / "assets" / "vendor" / "lottie_light.min.js").exists()
    other = next(p for p in out.rglob("index.html") if p != out / "index.html")
    assert "three-hero.js" not in other.read_text() and "lottie_light" not in other.read_text()   # other pages stay light
    # the library gate sees both and asks OSV about the exact versions
    assert {(d["name"], d["version"]) for d in G.found_libraries(out)} >= {("three", "0.187.0"), ("lottie-web", "5.13.0")}
    AG.set_osv(lambda deps: [[] for _ in deps])
    try:
        assert all(x["state"] == "pass" for x in G.gate_libraries(out))
    finally:
        AG.set_osv(None)
    res = G.scan(out, S._ctx(S._load(v["id"])), {"source": "hoola", "blocking": []}, S.form_endpoint(r))
    assert not [x for x in res["rows"] if x["state"] == "fail" and x["gate"] != "libraries"]

    from playwright.sync_api import sync_playwright
    from app.site import checks as C
    srv = _serve(out)
    try:
        with sync_playwright() as p:
            br = C._launch(p)
            for motion in ("no-preference", "reduce"):
                ctx = br.new_context(reduced_motion=motion)
                pg = ctx.new_page()
                errors = []
                pg.on("pageerror", lambda e: errors.append(str(e)))
                pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/", wait_until="load")
                pg.wait_for_selector("[data-hoola-lottie='check'][data-hoola-lottie-on] svg path", state="attached", timeout=15000)
                pg.wait_for_selector("[data-hoola-lottie='meri-chamak'][data-hoola-lottie-on] svg", state="attached", timeout=15000)
                svg = pg.inner_html("[data-hoola-lottie='check']")
                assert "rgb(255,0,255)" not in svg.replace(" ", "") and "#ff00ff" not in svg.lower()   # recoloured to her site
                pg.wait_for_function("document.querySelector('[data-hoola-3d]').hasAttribute('data-hoola-3d-on') || "
                                     "document.querySelector('[data-hoola-3d]').hasAttribute('data-hoola-3d-off')", timeout=20000)
                on = pg.get_attribute("[data-hoola-3d]", "data-hoola-3d-on")
                if on is not None:                                         # WebGL here (software): a real canvas was drawn
                    assert pg.eval_on_selector("[data-hoola-3d] canvas", "c => c.width > 0 && c.height > 0")
                assert not errors, errors
                ctx.close()
            br.close()
    finally:
        srv.shutdown()


def test_routes_tool_and_the_writer_rules(site_env):
    import asyncio
    from fastapi.testclient import TestClient
    from app.agent.site_tools import SITE_HANDLERS
    from app.main import app
    from app.site import ai as AI
    from app.site import lottie as LT
    from app.site import service as S
    from tests.test_life import conv_ctx
    v = S.new(T, "Sharma Sweets mithai dukaan ki website", name="Sharma Sweets")
    c = TestClient(app)
    r = c.post(f"/api/sites/{v['id']}/lottie", files={"file": ("a.json", json.dumps(LT.builtin("wave")).encode(), "application/json")},
               data={"name": "namaste"})
    assert r.status_code == 200 and r.json()["name"] == "namaste"
    assert c.post(f"/api/sites/{v['id']}/lottie", files={"file": ("a.json", b"nope", "application/json")},
                  data={"name": "x2"}).status_code == 400
    lst = c.get(f"/api/sites/{v['id']}/lottie").json()
    assert lst["hers"] == ["namaste"] and "check" in lst["builtins"] and "orb" in lst["scenes_3d"]
    from app.mailbox import service as ms
    orig = ms.load_files
    ms.load_files = lambda tenant, refs: [("b.json", "application/json", json.dumps(LT.builtin("dots")).encode())]
    try:
        got = asyncio.run(SITE_HANDLERS["website"](conv_ctx(), "animation", site=v["id"], file_id="f_1", name="chal-raha"))
    finally:
        ms.load_files = orig
    assert got["name"] == "chal-raha"
    src = Path(AI.__file__).read_text()
    for w in ('data-hoola-lottie="NAME"', "pulse", "sparkle", 'data-hoola-3d="orb|knot|particles|', "at most ONE per page",
              "never write WebGL"):
        assert w in src, w
    css = (ASSETS / "hoola-site.css").read_text()
    assert "[data-hoola-3d]{position:relative" in css and "aspect-ratio:16/10" in css and "[data-hoola-lottie]{display:inline-block" in css
    js = (ASSETS / "hoola-site.js").read_text()
    assert "function lotties()" in js and "lotties(); }" in js and "loadAnimation" in js and "goToAndStop" in js
