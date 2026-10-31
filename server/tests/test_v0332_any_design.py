"""v0.330 ANY DESIGN (web design Phase 6 step 2): (1) free-form sections - beyond the 30 library types, the site map
and her own words can add a section Opus designs from a name ("EMI calculator"), at most 3 a page; (2) interactive
pieces in the site runtime that sections use by attribute (tabs, slider, filter, switch, calculator incl. a loan EMI),
checked in a real browser; (3) ONE design kit per site (.k-* components from the look's art direction) that every
section is told to use; its cleaner keeps only kit rules so it can never restyle the header, footer or another section."""
import json
import threading
import functools
import http.server
import socketserver

import pytest

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_free_form_sections_in_the_site_map():
    from app.site import library as L
    from app.site import service as S
    from app.site import sitemap as SM
    from app.site import taxonomy as TX
    br = L.brief("bank_dsa") if "bank_dsa" in L.fields() else L.brief(sorted(L.fields())[0])
    raw = {"pages": [{"slug": "home", "sections": [{"type": "hero"}]},
                     {"slug": "loans", "title": "Loans", "sections": [
                         {"type": "custom", "name": "EMI calculator", "design": "amount, rate, months -> EMI"},
                         {"type": "custom", "name": "EMI Calculator"},                       # same key: once
                         {"type": "custom", "design": "no name: dropped"},
                         {"type": "custom", "name": "Compare home loan plans"},
                         {"type": "custom", "name": "Documents you need"},
                         {"type": "custom", "name": "A fourth one"},                         # over the 3 a page
                         {"type": "faq"}]}]}
    plan = SM.clean(raw, br, S.make_plan(br, {}), 20)
    loans = next(p for p in plan["pages"] if p["slug"] == "loans")
    types = [s["type"] for s in loans["sections"]]
    assert types == ["hero", "custom_emi_calculator", "custom_compare_home_loan_plans", "custom_documents_you_need", "faq"]
    emi = loans["sections"][1]
    assert emi["label"] == "EMI calculator" and "months" in emi["design"]
    assert TX.is_section("custom_emi_calculator") and not TX.is_section("custom_") and not TX.is_section("nope")
    assert TX.label_of("custom_size_guide") == "Size guide" and TX.label_of({"type": "faq"}) == TX.SECTIONS["faq"]["label"]


def test_her_words_add_a_free_form_section(site_env):
    from app.site import service as S
    v = S.new(T, "Sharma Sweets mithai dukaan ki website", name="Sharma Sweets", answers={"phone": "9876543210"})
    S.approve_plan(T, v["id"])
    S.choose_look(T, v["id"], 0)
    site_env.change = {"say": "Order calculator jod raha hoon.", "add": [
        {"page": "home", "type": "custom", "name": "Order calculator", "instruction": "kg x price for 3 sweets, total"}]}
    S.change(T, v["id"], "home par ek order calculator daalo")
    r = S._load(v["id"])
    assert r.status == "ready", r.error
    home = next(p for p in json.loads(r.plan)["pages"] if p["slug"] == "home")
    sec = next(s for s in home["sections"] if s["type"] == "custom_order_calculator")
    assert sec["label"] == "Order calculator" and "kg x price" in sec["design"]
    assert ("section", "s-home-custom-order-calculator") in site_env.calls
    page = (S._assemble_live(r) / "index.html").read_text()
    assert 'id="s-home-custom-order-calculator"' in page


def test_kit_cleaner_keeps_only_kit_rules():
    from app.site import kit as K
    css = """@import url(https://evil.example/x.css);
    .k-btn{background:var(--c-primary);color:var(--c-on-primary);min-height:44px}
    .k-btn:hover,.k-btn:focus-visible{transform:translateY(-1px)}
    .k-card .k-title::after{content:"";background:url(https://evil.example/a.png)}
    body{background:red} #s-home-hero{display:none} .hs-head{display:none} .k-card .hs-x{color:red}
    .k-card,header{color:red} [data-x]{} *{margin:0}
    @media (min-width:768px){.k-title{font-size:3rem} footer{display:none}}
    @font-face{font-family:x;src:url(x.woff2)} @keyframes k-rise{from{opacity:0}to{opacity:1}} @keyframes bad{}"""
    out = K.clean(css)
    assert ".k-btn{background:var(--c-primary)" in out and ".k-btn:hover,.k-btn:focus-visible" in out
    assert "@media (min-width:768px){.k-title{font-size:3rem}}" in out and "@keyframes k-rise" in out
    for bad in ("evil.example", "body{", "#s-home-hero", ".hs-head", ".hs-x", "header", "*{", "footer", "font-face", "@import", "@keyframes bad"):
        assert bad not in out, bad
    assert "url(" not in out


def test_build_makes_one_kit_and_every_section_hears_of_it(site_env, monkeypatch):
    monkeypatch.setenv("SITE_KIT", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.site import ai as AI
    from app.site import kit as K
    from app.site import service as S
    prompts, kits = [], []

    def fake(system, prompt, max_tokens=6000, kind="build", **kw):
        if system.startswith(K.KIT_SYSTEM[:40]):
            kits.append(prompt)
            return {"css": ".k-btn{background:var(--c-primary);min-height:44px} body{color:red} .k-card{border-radius:var(--radius)}",
                    "notes": {"k-btn": "main action", "k-card": "every boxed item"}}
        prompts.append(prompt)
        return site_env(system, prompt, max_tokens, kind)
    monkeypatch.setattr(AI, "ask_json", fake)
    v = S.new(T, "Sharma Sweets mithai dukaan ki website", name="Sharma Sweets", answers={"phone": "9876543210"})
    S.approve_plan(T, v["id"])
    n_before = len(prompts)
    S.choose_look(T, v["id"], 0)
    r = S._load(v["id"])
    assert r.status == "ready", r.error
    assert len(kits) == 1
    kit = json.loads(r.look)["kit"]
    assert kit["parts"] == ["k-btn", "k-card"] and "body{" not in kit["css"]
    built = prompts[n_before:]
    assert built and all("SITE DESIGN KIT" in p and ".k-btn = main action" in p for p in built if "SECTION_ID" in p)
    css = (S._assemble_live(r) / "assets" / "site.css").read_text()
    assert ".k-btn{background:var(--c-primary)" in css and "body{color:red}" not in css
    site_env.change = {"say": "ok", "sections": [{"key": "home__hero", "instruction": "bada heading"}]}
    S.change(T, v["id"], "hero ka heading bada karo")
    assert len(kits) == 1                                                        # one kit per site, not per change
    get_settings.cache_clear()


PIECES = """<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="site.css"></head><body>
<section class="hs" id="t"><div data-hoola-tabs><div><button data-tab="veg">Veg</button><button data-tab="sweet">Sweets</button>
<button data-tab="drink">Drinks</button></div><div data-panel="veg">V</div><div data-panel="sweet">S</div><div data-panel="drink">D</div></div>
<div data-hoola-filter><button data-filter="all">All</button><button data-filter="cake">Cakes</button>
<article data-cat="cake party">Cake</article><article data-cat="sweet">Laddoo</article></div>
<div data-hoola-toggle><button data-set="month">Monthly</button><button data-set="year">Yearly</button>
<span data-when="month">499</span><span data-when="year">4999</span></div>
<form data-hoola-calc="sum" data-base="50"><input name="kaju" type="number" value="2" data-rate="900">
<label><input type="checkbox" data-add="120"> box</label><output data-calc-out></output></form>
<form data-hoola-calc="emi"><input name="amount" value="100000"><input name="rate" value="12"><input name="months" value="12">
<output data-calc-out></output><output data-calc-total></output><output data-calc-interest></output></form>
<div data-hoola-carousel style="width:300px"><div class="hs-track"><article style="height:60px">1</article><article>2</article>
<article>3</article><article>4</article></div></div></section><script src="hoola-site.js"></script></body></html>"""


def test_interactive_pieces_work_in_a_real_browser(tmp_path):
    sync_api = pytest.importorskip("playwright.sync_api")
    import os
    import shutil
    from app.site import build as B
    shutil.copy(B.ASSETS / "hoola-site.js", tmp_path / "hoola-site.js")
    (tmp_path / "site.css").write_text(":root{--c-line:#ddd;--c-bg:#fff;--c-ink:#111;--c-primary:#a33;--c-on-primary:#fff}"
                                       + (B.ASSETS / "hoola-site.css").read_text())
    (tmp_path / "index.html").write_text(PIECES)
    H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path))
    H.log_message = lambda *a: None
    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_api.sync_playwright() as p:
            try:
                b = p.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
            except Exception as e:
                pytest.skip(f"no Chromium: {str(e)[:60]}")
            pg = b.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/")
            vis = lambda sel: pg.is_visible(sel)                                   # noqa: E731
            # tabs: first shown, click + arrow keys move, ARIA wired
            assert vis('[data-panel="veg"]') and not vis('[data-panel="sweet"]')
            pg.click('[data-tab="sweet"]')
            assert vis('[data-panel="sweet"]') and not vis('[data-panel="veg"]')
            pg.focus('[data-tab="sweet"]')
            pg.keyboard.press("ArrowRight")
            assert vis('[data-panel="drink"]') and pg.get_attribute('[data-tab="drink"]', "aria-selected") == "true"
            assert pg.get_attribute('[data-panel="drink"]', "role") == "tabpanel"
            # filter
            pg.click('[data-filter="cake"]')
            assert vis('[data-cat="cake party"]') and not vis('[data-cat="sweet"]')
            pg.click('[data-filter="all"]')
            assert vis('[data-cat="sweet"]')
            # switch
            assert vis('[data-when="month"]') and not vis('[data-when="year"]')
            pg.click('[data-set="year"]')
            assert vis('[data-when="year"]') and pg.get_attribute('[data-set="year"]', "aria-pressed") == "true"
            # calculators: 50 + 2 x 900 = 1,850, + box 120 = 1,970; EMI on 1,00,000 at 12% for 12 months = 8,885
            sums = 'form[data-hoola-calc="sum"] output'
            assert pg.inner_text(sums) == "₹1,850"
            pg.check('form[data-hoola-calc="sum"] input[type=checkbox]')
            assert pg.inner_text(sums) == "₹1,970"
            emi = 'form[data-hoola-calc="emi"]'
            assert pg.inner_text(f"{emi} [data-calc-out]") == "₹8,885"
            assert pg.inner_text(f"{emi} [data-calc-total]") == "₹1,06,619" and pg.inner_text(f"{emi} [data-calc-interest]") == "₹6,619"
            pg.fill(f'{emi} [name="months"]', "24")
            assert pg.inner_text(f"{emi} [data-calc-out]") == "₹4,707"
            # slider: arrows added, 'previous' starts disabled, 'next' moves the track
            assert pg.is_disabled(".hs-car-prev") and not pg.is_disabled(".hs-car-next")
            pg.click(".hs-car-next")
            pg.wait_for_function("document.querySelector('.hs-track').scrollLeft > 0")
            assert not errs, errs
            b.close()
    finally:
        srv.shutdown()


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.337.0"
    assert "0.337.0+377" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
