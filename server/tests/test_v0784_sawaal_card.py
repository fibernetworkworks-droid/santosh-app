"""v0.784 SAWAAL CARD (L3 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L3"): before a Studio Build, up to four design
questions with options she can SEE (feel, colours, type, the top of the home page), all from Hoola's own library;
skipped when her words already decide the design; her picks become look 1."""
import json
import os
import pathlib

from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0407_ek_dimaag import arch_env  # noqa: F401  (fixture: the architect + the site fake AI)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

CON = pathlib.Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def _on(monkeypatch):
    monkeypatch.setenv("STUDIO_DESIGN_QUESTIONS", "true")
    from app.config import get_settings
    get_settings.cache_clear()


def test_questions_come_from_the_library_and_skip_when_her_words_decide(monkeypatch):
    _on(monkeypatch)
    from app.site import designq as D
    from app.site import taxonomy as TX
    q = D.questions("Sharma Sweets mithai dukaan ki website in Akola")
    assert not q["skip"] and [x["kind"] for x in q["questions"]] == ["style", "palette", "fonts", "hero"]
    pools = {"style": TX.STYLES, "palette": TX.PALETTES, "fonts": TX.FONTS, "hero": TX.HEROES}
    for x in q["questions"]:
        ids = [o["id"] for o in x["options"]]
        assert len(ids) == 4 == len(set(ids)) and all(i in pools[x["kind"]] for i in ids), (x["kind"], ids)
    assert all(len(o["colours"]) == 5 for o in q["questions"][1]["options"])
    assert len({o["wire"] for o in q["questions"][3]["options"]}) >= 3              # the fronts really look different
    for words, why in (("clinic website, blue and white", "colour"), ("bakery site, colours #C2410C", "colour code"),
                       ("coaching class like my screenshot", "screenshot"), ("cafe site with Playfair Display", "font"),
                       ("a bold modern gym website", "style"), ("mithai shop, laal aur peela", "colour")):
        got = D.questions(words)
        assert got["skip"] and why in got["why"] and got["questions"] == [], (words, got)
    monkeypatch.setenv("STUDIO_DESIGN_QUESTIONS", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert D.questions("Sharma Sweets mithai dukaan")["skip"]                       # the switch turns the card off


def test_her_picks_become_a_design_ref_only_from_library_ids():
    from app.site import designq as D
    from app.site import taxonomy as TX
    r = D.ref_from({"style": "warm_local", "palette": "midnight_gold", "fonts": "playfair_lato", "hero": "big_type"})
    assert r["source"] == "answers" and r["style"] == "warm_local" and r["fonts"] == "playfair_lato"
    assert r["overrides"]["primary"] == TX.PALETTES["midnight_gold"]["primary"] and r["dark"] is True
    assert r["hero"] == "big_type" and "midnight gold" in r["notes"]
    assert D.ref_from({"style": "<script>", "palette": "nope", "fonts": "", "hero": "../x"}) is None
    assert D.ref_from(None) is None and D.ref_from("warm_local") is None
    only = D.ref_from({"palette": "paper_ink"})
    assert only["overrides"]["bg"] == TX.PALETTES["paper_ink"]["bg"] and only["hero"] == ""


def test_routes_questions_font_and_build_carries_the_picks(site_env, monkeypatch):
    _on(monkeypatch)
    from app.main import app
    from app.site import service as S
    c = TestClient(app)
    q = c.get("/api/site-design/questions", params={"brief": "Sharma Sweets mithai dukaan ki website"}).json()
    assert not q["skip"] and len(q["questions"]) == 4
    url = next(o["head_url"] for o in q["questions"][2]["options"] if o["head_url"])
    f = c.get(url)
    assert f.status_code == 200 and f.headers["content-type"] == "font/woff2" and len(f.content) > 1000
    for bad in ("..%2F..%2Fconfig.py", "x.woff2", "inter-latin-400.ttf"):
        assert c.get("/api/site-design/font/" + bad).status_code == 404
    pal = q["questions"][1]["options"][1]["id"]
    v = c.post("/api/sites", json={"brief": "Sharma Sweets mithai dukaan ki website", "name": "Sharma Sweets",
                                   "design": {"style": "festive_traditional", "palette": pal, "fonts": "yatra_hind",
                                              "hero": "big_type"}}).json()
    ref = json.loads(S._load(v["id"]).facts)["design_ref"]
    assert ref["source"] == "answers" and ref["palette_id"] == pal and ref["hero"] == "big_type"
    w = c.post("/api/sites", json={"brief": "Gupta Kirana ki website"}).json()          # no picks = no design_ref
    assert "design_ref" not in json.loads(S._load(w["id"]).facts)


def test_look_one_is_built_from_her_picks(site_env):
    from app.site import designq as D
    from app.site import service as S
    from app.site import taxonomy as TX
    tok = D.PENDING.set(D.ref_from({"style": "luxury_dark", "palette": "midnight_gold", "hero": "big_type"}))
    try:
        v = S.new(T, "Sharma Sweets mithai dukaan ki website", name="Sharma Sweets", answers={"phone": "9876543210"})
    finally:
        D.PENDING.reset(tok)
    S.approve_plan(T, v["id"])
    looks = json.loads(S._load(v["id"]).looks)
    assert len(looks) == 3 and looks[0]["label"] == "Your choices" and looks[0]["style"] == "luxury_dark"
    p = TX.PALETTES["midnight_gold"]
    assert looks[0]["tokens"]["bg"] == p["bg"] and looks[0]["tokens"]["primary"] == p["primary"]
    assert not looks[1].get("mine") and not looks[2].get("mine")                   # two Hoola alternatives stay
    assert "PENDING" not in json.dumps(looks) and D.PENDING.get() is None           # nothing leaks to the next site


def test_studio_source_wiring():
    js = (CON / "webstudio.js").read_text(encoding="utf-8")
    css = (CON / "webstudio.css").read_text(encoding="utf-8")
    i = js.index("if (kind === 'ask') {")
    assert js.index("await askDesign(t)", i) < js.index("drawPending(plan, t)", i)   # the card comes before the wait
    assert "if (design) body.design = design" in js and "/api/site-design/questions?brief=" in js
    assert "Skip, Hoola picks" in js and "Build with these" in js and "[Hoola template #" in js
    assert ".qopt:has(input:checked)" in css and "prefers-reduced-motion:reduce){.wsq{animation:none}" in css
    assert "backdrop-filter:blur" not in css[css.index("v0.784 SAWAAL CARD"):]      # CRISP TEXT: no blur under words


def test_question_card_in_a_real_browser(arena_server, arch_env, monkeypatch):
    _on(monkeypatch)
    from app.site import checks as C
    monkeypatch.setattr(C, "run", lambda *a, **k: (_ for _ in ()).throw(C.CheckError("no screenshots in this test")))
    base, browser, key = arena_server
    shots = os.environ.get("CONSOLE_SHOTS")
    errors, bodies = [], []
    for width in (1440, 390):
        ctx = browser.new_context(viewport={"width": width, "height": 900})
        ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: bodies.append(r.post_data) if r.method == "POST" and r.url.endswith("/api/sites") else None)
        page.goto(base + "/console/web")
        page.wait_for_selector("#wsAsk", timeout=20000)
        page.fill("#wsAsk", "Sharma Sweets mithai dukaan ki website, online order WhatsApp par")
        page.keyboard.press("Enter")
        page.wait_for_selector("#wsQ", timeout=10000)
        assert page.locator("#wsQ fieldset").count() == 4 and page.locator("#wsQ .qopt").count() == 16
        assert page.locator("#wsQ input:checked").count() == 4                      # one choice ready in each
        wide = page.evaluate("""() => [...document.querySelectorAll('#wsQ *, .qbar')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 5).map(e => e.className + ' ' + Math.round(e.getBoundingClientRect().right))""")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (width, wide, page.evaluate("[document.documentElement.scrollWidth, innerWidth]"))
        page.wait_for_function("document.fonts.check(\"16px 'hq-yatra_hind-h'\") || document.fonts.status === 'loaded'")
        if shots:
            page.wait_for_timeout(900)
            page.screenshot(path=f"{shots}/sawaal-{width}.png", full_page=True)
        if width == 390:                                                             # Back = her words stay in the box
            page.click("#wsQ [data-q='back']")
            page.wait_for_selector("#wsAsk")
            assert "Sharma Sweets" in page.input_value("#wsAsk")
            ctx.close()
            continue
        page.click("#wsQ .qk-palette .qopt >> nth=2")
        page.click("#wsQ .qk-hero .qopt >> nth=1")
        pal = page.get_attribute("#wsQ .qk-palette .qopt >> nth=2 >> input", "value")
        hero = page.get_attribute("#wsQ .qk-hero .qopt >> nth=1 >> input", "value")
        page.click("#wsQ button[type=submit]")
        page.wait_for_selector("#ws .lks button", timeout=120000)
        body = json.loads(next(b for b in bodies if b))
        assert body["design"]["palette"] == pal and body["design"]["hero"] == hero and body["deep"] is True
        assert "Your choices" in page.inner_text("#ws .lks")
        if shots:
            page.screenshot(path=f"{shots}/sawaal-looks.png")
        ctx.close()
    assert not errors, errors
